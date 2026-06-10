"""Multi-source research provider chain for ``free_deep_research`` mode.

Patent-specific adaptation of the Odysseus search provider chain
(``services/search/core.py`` + ``services/search/providers.py``). Each provider
normalizes its results into :class:`~backend.app.schemas.PriorArtHit` so the
deep researcher consumes a single uniform shape regardless of backend.

Safety guarantees
-----------------
* **No hard dependency on any external backend.** Providers that need an API
  key are skipped (with a warning) when the key is absent. The research run is
  never failed just because an optional backend is unconfigured.
* **Provider/document text is UNTRUSTED.** Abstracts, web snippets and any
  MCP-fetched document text are sanitized via :func:`sanitize_untrusted_text`
  before they leave a provider. They are only ever placed in the *content*
  position of an LLM user message — never used to build a system/developer
  prompt. This is the prompt-injection boundary for the whole research loop.
* **Graceful degradation.** A provider that raises mid-search returns a warning
  instead of propagating the exception, so one flaky backend cannot abort the
  chain.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from typing import Protocol

from backend.app.schemas import PriorArtHit


DEFAULT_PROVIDER_CHAIN = "patent,arxiv,openalex,semantic_scholar,tavily,exa"


# ---------------------------------------------------------------------------
# HTTP seam (injectable so tests never touch the network)
# ---------------------------------------------------------------------------


class HttpClient(Protocol):
    def get(self, url: str, headers: dict[str, str], timeout: int) -> str: ...

    def post(self, url: str, headers: dict[str, str], body: bytes, timeout: int) -> str: ...


class UrllibHttpClient:
    """Default HTTP client backed by the stdlib. No third-party dependency."""

    def get(self, url: str, headers: dict[str, str], timeout: int) -> str:
        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(2_000_000).decode("utf-8", errors="replace")

    def post(self, url: str, headers: dict[str, str], body: bytes, timeout: int) -> str:
        request = urllib.request.Request(url, headers=headers, data=body, method="POST")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(2_000_000).decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Untrusted-text guard (prompt-injection boundary)
# ---------------------------------------------------------------------------


_INJECTION_MARKERS = (
    "ignore previous",
    "ignore all previous",
    "ignore the above",
    "disregard previous",
    "disregard the above",
    "system prompt",
    "developer prompt",
    "you are now",
    "new instructions",
    "act as",
    "忽略以上",
    "忽略之前",
    "忽略前面",
    "忽略上面",
    "系统提示",
    "你现在是",
    "扮演",
)


def sanitize_untrusted_text(text: str | None, max_len: int = 1200) -> str:
    """Neutralize prompt-injection attempts in provider/document text.

    Untrusted content (paper abstracts, web snippets, MCP-fetched docs) must be
    treated as *data*, never as *instructions*. We:

    * strip control characters and collapse whitespace,
    * defang common injection markers (English + Chinese) by inserting a
      zero-width-free separator so the phrase cannot be read as a directive,
    * bound the length.

    The result is safe to embed as quoted content in an LLM user message.
    """

    if not text:
        return ""
    cleaned = "".join(ch if ch.isprintable() or ch in "\n\t " else " " for ch in str(text))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    lowered = cleaned.lower()
    for marker in _INJECTION_MARKERS:
        if marker in lowered:
            # Re-find case-insensitively and defang every occurrence.
            pattern = re.compile(re.escape(marker), flags=re.IGNORECASE)
            cleaned = pattern.sub(lambda m: "[redacted-instruction]", cleaned)
            lowered = cleaned.lower()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip() + "…"
    return cleaned


def contains_injection_marker(text: str | None) -> bool:
    """True when raw provider text looks like a prompt-injection attempt.

    Used by tests and by the loop to flag — but never execute — suspicious
    document content.
    """

    if not text:
        return False
    lowered = str(text).lower()
    return any(marker in lowered for marker in _INJECTION_MARKERS)


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------


class ResearchProvider(Protocol):
    name: str
    kind: str

    def available(self) -> tuple[bool, str | None]:
        """Return ``(ok, skip_reason)``. ``skip_reason`` is a human warning
        when the provider must be skipped (e.g. missing API key)."""
        ...

    def search(self, queries: list[str], limit: int) -> tuple[list[PriorArtHit], list[str]]:
        ...


def _hit(
    *,
    source: str,
    query: str,
    title: str,
    url: str,
    publication_number: str | None = None,
    abstract: str | None = None,
) -> PriorArtHit:
    return PriorArtHit(
        id=uuid.uuid4().hex,
        source=source,
        query=query,
        title=sanitize_untrusted_text(title, max_len=300) or "未命名文献",
        publication_number=publication_number,
        url=url,
        abstract=sanitize_untrusted_text(abstract) or None,
    )


# ---------------------------------------------------------------------------
# Patent provider (wraps the existing PriorArtProvider — always available)
# ---------------------------------------------------------------------------


class PatentResearchProvider:
    name = "patent"
    kind = "patent"

    def __init__(self, prior_art_provider: object) -> None:
        self._provider = prior_art_provider

    def available(self) -> tuple[bool, str | None]:
        return True, None

    def search(self, queries: list[str], limit: int) -> tuple[list[PriorArtHit], list[str]]:
        try:
            hits, warnings = self._provider.search(queries, limit)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - defensive
            return [], [f"patent provider failed: {exc}"]
        # Re-sanitize titles/abstracts coming from the patent provider too.
        safe_hits = [
            hit.model_copy(
                update={
                    "title": sanitize_untrusted_text(hit.title, max_len=300) or hit.title,
                    "abstract": sanitize_untrusted_text(hit.abstract) or hit.abstract,
                }
            )
            for hit in hits
        ]
        return safe_hits, list(warnings)


# ---------------------------------------------------------------------------
# arXiv provider (official Atom API — no key required)
# ---------------------------------------------------------------------------


class ArxivProvider:
    name = "arxiv"
    kind = "arxiv"
    ENDPOINT = "http://export.arxiv.org/api/query"

    def __init__(self, http: HttpClient, max_results: int = 10, timeout: int = 20) -> None:
        self._http = http
        self._max_results = max_results
        self._timeout = timeout

    def available(self) -> tuple[bool, str | None]:
        return True, None

    def search(self, queries: list[str], limit: int) -> tuple[list[PriorArtHit], list[str]]:
        hits: list[PriorArtHit] = []
        warnings: list[str] = []
        per_query = max(1, min(limit, self._max_results))
        for query in queries:
            url = (
                f"{self.ENDPOINT}?search_query="
                + urllib.parse.quote(f"all:{query}")
                + f"&start=0&max_results={per_query}"
            )
            try:
                raw = self._http.get(url, {"User-Agent": "patents-agent-research/0.1"}, self._timeout)
            except Exception as exc:
                warnings.append(f"arxiv search failed for '{query}': {exc}")
                continue
            try:
                hits.extend(_parse_arxiv_atom(raw, query))
            except Exception as exc:  # pragma: no cover - defensive
                warnings.append(f"arxiv parse failed for '{query}': {exc}")
            if len(hits) >= limit:
                break
        return hits[:limit], warnings


def _parse_arxiv_atom(xml_text: str, query: str) -> list[PriorArtHit]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml_text)
    hits: list[PriorArtHit] = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        id_el = entry.find("atom:id", ns)
        summary_el = entry.find("atom:summary", ns)
        title = (title_el.text or "").strip() if title_el is not None else ""
        url = (id_el.text or "").strip() if id_el is not None else ""
        summary = (summary_el.text or "").strip() if summary_el is not None else ""
        if not title and not url:
            continue
        arxiv_id = url.rsplit("/abs/", 1)[-1] if "/abs/" in url else (url.rsplit("/", 1)[-1] or None)
        hits.append(
            _hit(
                source="arXiv",
                query=query,
                title=title,
                url=url,
                publication_number=arxiv_id or None,
                abstract=summary,
            )
        )
    return hits


# ---------------------------------------------------------------------------
# OpenAlex provider (works API — no key required)
# ---------------------------------------------------------------------------


class OpenAlexProvider:
    name = "openalex"
    kind = "openalex"
    ENDPOINT = "https://api.openalex.org/works"

    def __init__(self, http: HttpClient, max_results: int = 10, timeout: int = 20, mailto: str | None = None) -> None:
        self._http = http
        self._max_results = max_results
        self._timeout = timeout
        self._mailto = mailto or os.environ.get("OPENALEX_MAILTO", "")

    def available(self) -> tuple[bool, str | None]:
        return True, None

    def search(self, queries: list[str], limit: int) -> tuple[list[PriorArtHit], list[str]]:
        hits: list[PriorArtHit] = []
        warnings: list[str] = []
        per_query = max(1, min(limit, self._max_results))
        for query in queries:
            params = {"search": query, "per-page": str(per_query)}
            if self._mailto:
                params["mailto"] = self._mailto
            url = f"{self.ENDPOINT}?" + urllib.parse.urlencode(params)
            try:
                raw = self._http.get(url, {"User-Agent": "patents-agent-research/0.1"}, self._timeout)
            except Exception as exc:
                warnings.append(f"openalex search failed for '{query}': {exc}")
                continue
            try:
                hits.extend(_parse_openalex(raw, query))
            except Exception as exc:  # pragma: no cover - defensive
                warnings.append(f"openalex parse failed for '{query}': {exc}")
            if len(hits) >= limit:
                break
        return hits[:limit], warnings


def _reconstruct_inverted_abstract(inverted: dict | None) -> str:
    if not isinstance(inverted, dict) or not inverted:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted.items():
        if not isinstance(idxs, list):
            continue
        for idx in idxs:
            if isinstance(idx, int):
                positions.append((idx, str(word)))
    positions.sort(key=lambda pair: pair[0])
    return " ".join(word for _, word in positions)


def _parse_openalex(json_text: str, query: str) -> list[PriorArtHit]:
    data = json.loads(json_text)
    results = data.get("results") if isinstance(data, dict) else None
    hits: list[PriorArtHit] = []
    for item in results or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("display_name") or item.get("title") or "")
        openalex_id = str(item.get("id") or "")
        doi = item.get("doi")
        landing = ""
        primary = item.get("primary_location")
        if isinstance(primary, dict):
            landing = str(primary.get("landing_page_url") or "")
        url = landing or (str(doi) if doi else "") or openalex_id
        abstract = _reconstruct_inverted_abstract(item.get("abstract_inverted_index"))
        pub_number = None
        if doi:
            pub_number = str(doi).rsplit("/", 1)[-1] if "/" in str(doi) else str(doi)
        elif openalex_id:
            pub_number = openalex_id.rsplit("/", 1)[-1]
        if not title and not url:
            continue
        hits.append(
            _hit(
                source="OpenAlex",
                query=query,
                title=title,
                url=url or openalex_id,
                publication_number=pub_number,
                abstract=abstract,
            )
        )
    return hits


# ---------------------------------------------------------------------------
# Semantic Scholar provider (optional — skipped without API key)
# ---------------------------------------------------------------------------


class SemanticScholarProvider:
    name = "semantic_scholar"
    kind = "semantic_scholar"
    ENDPOINT = "https://api.semanticscholar.org/graph/v1/paper/search"

    def __init__(self, http: HttpClient, api_key: str | None, max_results: int = 10, timeout: int = 20) -> None:
        self._http = http
        self._api_key = api_key or ""
        self._max_results = max_results
        self._timeout = timeout

    def available(self) -> tuple[bool, str | None]:
        if not self._api_key:
            return False, "semantic_scholar skipped: SEMANTIC_SCHOLAR_API_KEY not set"
        return True, None

    def search(self, queries: list[str], limit: int) -> tuple[list[PriorArtHit], list[str]]:
        hits: list[PriorArtHit] = []
        warnings: list[str] = []
        per_query = max(1, min(limit, self._max_results))
        headers = {"User-Agent": "patents-agent-research/0.1", "x-api-key": self._api_key}
        for query in queries:
            params = {"query": query, "limit": str(per_query), "fields": "title,abstract,url,externalIds"}
            url = f"{self.ENDPOINT}?" + urllib.parse.urlencode(params)
            try:
                raw = self._http.get(url, headers, self._timeout)
            except Exception as exc:
                warnings.append(f"semantic_scholar search failed for '{query}': {exc}")
                continue
            try:
                hits.extend(_parse_semantic_scholar(raw, query))
            except Exception as exc:  # pragma: no cover - defensive
                warnings.append(f"semantic_scholar parse failed for '{query}': {exc}")
            if len(hits) >= limit:
                break
        return hits[:limit], warnings


def _parse_semantic_scholar(json_text: str, query: str) -> list[PriorArtHit]:
    data = json.loads(json_text)
    papers = data.get("data") if isinstance(data, dict) else None
    hits: list[PriorArtHit] = []
    for item in papers or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "")
        url = str(item.get("url") or "")
        abstract = str(item.get("abstract") or "")
        external = item.get("externalIds") if isinstance(item.get("externalIds"), dict) else {}
        pub_number = None
        if external:
            pub_number = str(external.get("DOI") or external.get("ArXiv") or external.get("CorpusId") or "") or None
        if not title and not url:
            continue
        hits.append(
            _hit(
                source="Semantic Scholar",
                query=query,
                title=title,
                url=url,
                publication_number=pub_number,
                abstract=abstract,
            )
        )
    return hits


# ---------------------------------------------------------------------------
# Tavily provider (optional — skipped without API key)
# ---------------------------------------------------------------------------


class TavilyProvider:
    name = "tavily"
    kind = "tavily"
    ENDPOINT = "https://api.tavily.com/search"

    def __init__(self, http: HttpClient, api_key: str | None, max_results: int = 10, timeout: int = 20) -> None:
        self._http = http
        self._api_key = api_key or ""
        self._max_results = max_results
        self._timeout = timeout

    def available(self) -> tuple[bool, str | None]:
        if not self._api_key:
            return False, "tavily skipped: TAVILY_API_KEY not set"
        return True, None

    def search(self, queries: list[str], limit: int) -> tuple[list[PriorArtHit], list[str]]:
        hits: list[PriorArtHit] = []
        warnings: list[str] = []
        per_query = max(1, min(limit, self._max_results))
        headers = {"Content-Type": "application/json", "User-Agent": "patents-agent-research/0.1"}
        for query in queries:
            body = json.dumps(
                {"api_key": self._api_key, "query": query, "max_results": per_query}
            ).encode("utf-8")
            try:
                raw = self._http.post(self.ENDPOINT, headers, body, self._timeout)
            except Exception as exc:
                warnings.append(f"tavily search failed for '{query}': {exc}")
                continue
            try:
                hits.extend(_parse_tavily(raw, query))
            except Exception as exc:  # pragma: no cover - defensive
                warnings.append(f"tavily parse failed for '{query}': {exc}")
            if len(hits) >= limit:
                break
        return hits[:limit], warnings


def _parse_tavily(json_text: str, query: str) -> list[PriorArtHit]:
    data = json.loads(json_text)
    results = data.get("results") if isinstance(data, dict) else None
    hits: list[PriorArtHit] = []
    for item in results or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "")
        url = str(item.get("url") or "")
        content = str(item.get("content") or "")
        if not title and not url:
            continue
        hits.append(_hit(source="Tavily", query=query, title=title or url, url=url, abstract=content))
    return hits


# ---------------------------------------------------------------------------
# Exa provider (optional — skipped without API key)
# ---------------------------------------------------------------------------


class ExaProvider:
    name = "exa"
    kind = "exa"
    ENDPOINT = "https://api.exa.ai/search"

    def __init__(self, http: HttpClient, api_key: str | None, max_results: int = 10, timeout: int = 20) -> None:
        self._http = http
        self._api_key = api_key or ""
        self._max_results = max_results
        self._timeout = timeout

    def available(self) -> tuple[bool, str | None]:
        if not self._api_key:
            return False, "exa skipped: EXA_API_KEY not set"
        return True, None

    def search(self, queries: list[str], limit: int) -> tuple[list[PriorArtHit], list[str]]:
        hits: list[PriorArtHit] = []
        warnings: list[str] = []
        per_query = max(1, min(limit, self._max_results))
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
            "User-Agent": "patents-agent-research/0.1",
        }
        for query in queries:
            body = json.dumps({"query": query, "numResults": per_query, "contents": {"text": True}}).encode("utf-8")
            try:
                raw = self._http.post(self.ENDPOINT, headers, body, self._timeout)
            except Exception as exc:
                warnings.append(f"exa search failed for '{query}': {exc}")
                continue
            try:
                hits.extend(_parse_exa(raw, query))
            except Exception as exc:  # pragma: no cover - defensive
                warnings.append(f"exa parse failed for '{query}': {exc}")
            if len(hits) >= limit:
                break
        return hits[:limit], warnings


def _parse_exa(json_text: str, query: str) -> list[PriorArtHit]:
    data = json.loads(json_text)
    results = data.get("results") if isinstance(data, dict) else None
    hits: list[PriorArtHit] = []
    for item in results or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "")
        url = str(item.get("url") or "")
        text = str(item.get("text") or item.get("snippet") or "")
        if not title and not url:
            continue
        hits.append(_hit(source="Exa", query=query, title=title or url, url=url, abstract=text))
    return hits


# ---------------------------------------------------------------------------
# Optional arXiv MCP adapter (local connector — never on the production path)
# ---------------------------------------------------------------------------


class ArxivMcpProvider:
    """Optional local connector that reads arXiv via an MCP client.

    This is an *opt-in* adapter. The official :class:`ArxivProvider` is the
    default; the MCP variant only activates when a client callable is injected
    (e.g. wired to a locally running arxiv-mcp-server). Paper content returned
    by the MCP client is treated as **untrusted** exactly like every other
    provider — it is sanitized here and never used to build a prompt.

    The injected callable has signature ``client(query: str, limit: int) ->
    list[dict]`` where each dict may carry ``title``, ``url``, ``id`` and
    ``abstract``/``content`` keys.
    """

    name = "arxiv_mcp"
    kind = "arxiv_mcp"

    def __init__(self, mcp_client=None, max_results: int = 10) -> None:
        self._client = mcp_client
        self._max_results = max_results

    def available(self) -> tuple[bool, str | None]:
        if self._client is None:
            return False, "arxiv_mcp skipped: no MCP client connector configured"
        return True, None

    def search(self, queries: list[str], limit: int) -> tuple[list[PriorArtHit], list[str]]:
        if self._client is None:
            return [], ["arxiv_mcp skipped: no MCP client connector configured"]
        hits: list[PriorArtHit] = []
        warnings: list[str] = []
        per_query = max(1, min(limit, self._max_results))
        for query in queries:
            try:
                raw_items = self._client(query, per_query) or []
            except Exception as exc:
                warnings.append(f"arxiv_mcp search failed for '{query}': {exc}")
                continue
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or "")
                url = str(item.get("url") or item.get("id") or "")
                abstract = str(item.get("abstract") or item.get("content") or "")
                # Untrusted document text — flag injection attempts as a warning
                # but never let the text act as an instruction.
                if contains_injection_marker(item.get("abstract")) or contains_injection_marker(
                    item.get("content")
                ):
                    warnings.append(
                        f"arxiv_mcp: suspicious instruction-like text in '{title[:40]}' was neutralized"
                    )
                if not title and not url:
                    continue
                hits.append(
                    _hit(
                        source="arXiv (MCP)",
                        query=query,
                        title=title or url,
                        url=url,
                        publication_number=str(item.get("id") or "") or None,
                        abstract=abstract,
                    )
                )
            if len(hits) >= limit:
                break
        return hits[:limit], warnings


# ---------------------------------------------------------------------------
# Registry / chain builder
# ---------------------------------------------------------------------------


def _env(env: dict[str, str] | None, key: str, default: str = "") -> str:
    source = env if env is not None else os.environ
    return str(source.get(key, default) or "").strip()


def build_provider_chain(
    *,
    patent_provider: object,
    http: HttpClient | None = None,
    env: dict[str, str] | None = None,
    arxiv_mcp_client=None,
) -> tuple[list[ResearchProvider], list[str]]:
    """Construct the ordered, *available* provider chain.

    Reads ``RESEARCH_PROVIDER_CHAIN`` (comma-separated). Providers that are not
    available (missing key / connector) are skipped and explained in the
    returned warnings list. The chain is never empty in practice because the
    ``patent`` provider is always available.
    """

    http = http or UrllibHttpClient()
    chain_spec = _env(env, "RESEARCH_PROVIDER_CHAIN", DEFAULT_PROVIDER_CHAIN) or DEFAULT_PROVIDER_CHAIN
    requested = [name.strip() for name in chain_spec.split(",") if name.strip()]
    arxiv_max = _int_env(env, "ARXIV_MAX_RESULTS", 10)
    per_provider = _int_env(env, "DEEP_RESEARCH_MAX_RESULTS_PER_PROVIDER", 10)

    factories = {
        "patent": lambda: PatentResearchProvider(patent_provider),
        "arxiv": lambda: ArxivProvider(http, max_results=arxiv_max),
        "openalex": lambda: OpenAlexProvider(http, max_results=per_provider),
        "semantic_scholar": lambda: SemanticScholarProvider(
            http, api_key=_env(env, "SEMANTIC_SCHOLAR_API_KEY"), max_results=per_provider
        ),
        "tavily": lambda: TavilyProvider(http, api_key=_env(env, "TAVILY_API_KEY"), max_results=per_provider),
        "exa": lambda: ExaProvider(http, api_key=_env(env, "EXA_API_KEY"), max_results=per_provider),
        "arxiv_mcp": lambda: ArxivMcpProvider(mcp_client=arxiv_mcp_client, max_results=arxiv_max),
    }

    providers: list[ResearchProvider] = []
    warnings: list[str] = []
    for name in requested:
        factory = factories.get(name)
        if factory is None:
            warnings.append(f"research provider '{name}' is not supported; skipped")
            continue
        provider = factory()
        ok, reason = provider.available()
        if not ok:
            warnings.append(reason or f"provider '{name}' unavailable; skipped")
            continue
        providers.append(provider)

    if not providers:
        # Guarantee at least the patent provider so the loop can still run.
        providers.append(PatentResearchProvider(patent_provider))
        warnings.append("no configured research providers available; falling back to patent provider only")

    return providers, warnings


def _int_env(env: dict[str, str] | None, key: str, default: int) -> int:
    try:
        return int(_env(env, key, str(default)) or default)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Chained provider — satisfies DeepResearchSearchProvider
# ---------------------------------------------------------------------------


class ChainedResearchProvider:
    """Fan-out search across the provider chain, merging and de-duplicating.

    Implements the ``search(terms, limit) -> (hits, warnings)`` contract used by
    :class:`~backend.app.research.deep_researcher.PatentDeepResearcher`, so it
    is a drop-in replacement for the single-provider adapter.
    """

    def __init__(self, providers: list[ResearchProvider], chain_warnings: list[str] | None = None) -> None:
        self._providers = providers
        self._chain_warnings = list(chain_warnings or [])
        self.provider_names = [provider.name for provider in providers]

    def search(self, terms: list[str], limit: int) -> tuple[list[PriorArtHit], list[str]]:
        provider_batches: list[list[PriorArtHit]] = []
        warnings: list[str] = list(self._chain_warnings)
        self._chain_warnings = []  # only surface chain-build warnings once
        seen: set[str] = set()
        for provider in self._providers:
            try:
                hits, provider_warnings = provider.search(terms, limit)
            except Exception as exc:  # pragma: no cover - defensive
                warnings.append(f"provider '{provider.name}' raised: {exc}")
                continue
            warnings.extend(provider_warnings)
            batch: list[PriorArtHit] = []
            for hit in hits:
                key = (hit.publication_number or hit.url or hit.title).strip().upper()
                if not key or key in seen:
                    continue
                seen.add(key)
                batch.append(hit)
            if batch:
                provider_batches.append(batch)
        return _round_robin_hits(provider_batches, limit), warnings


def _round_robin_hits(provider_batches: list[list[PriorArtHit]], limit: int) -> list[PriorArtHit]:
    """Balance final results so later providers are not starved by patent hits."""

    merged: list[PriorArtHit] = []
    max_len = max((len(batch) for batch in provider_batches), default=0)
    for index in range(max_len):
        for batch in provider_batches:
            if index >= len(batch):
                continue
            merged.append(batch[index])
            if len(merged) >= limit:
                return merged
    return merged
