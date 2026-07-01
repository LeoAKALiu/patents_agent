from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import ssl
import subprocess
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from socket import timeout as SocketTimeout
from typing import Any, Protocol

import certifi

from backend.app.research.providers import sanitize_untrusted_text
from backend.app.schemas import PatentSearchFilters, PatentSearchHit, PriorArtCandidate, ProviderAttempt


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(*parts: str) -> str:
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def normalize_publication_number(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", "", value).upper()


class PatentSearchProvider(Protocol):
    name: str
    source_id: str

    def available(self) -> tuple[bool, str | None]: ...

    def search(
        self,
        query: str,
        *,
        filters: PatentSearchFilters,
        limit: int,
        ) -> tuple[list[PatentSearchHit], list[str]]: ...


class StaticPatentSearchProvider:
    name = "Static Patent Search"

    def __init__(self, *, source_id: str, hits: list[PatentSearchHit], warnings: list[str] | None = None) -> None:
        self.source_id = source_id
        self._hits = hits
        self._warnings = warnings or []

    def available(self) -> tuple[bool, str | None]:
        return True, None

    def search(
        self,
        query: str,
        *,
        filters: PatentSearchFilters,
        limit: int,
    ) -> tuple[list[PatentSearchHit], list[str]]:
        del filters
        hits = [
            hit.model_copy(update={"query": hit.query or query, "source": self.source_id})
            for hit in self._hits[:limit]
        ]
        return hits, list(self._warnings)


def _urllib_get(url: str, timeout: int) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "patents-agent/0.1"})
    kwargs: dict[str, Any] = {"timeout": timeout}
    if url.lower().startswith("https://") and not (
        os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    ):
        kwargs["context"] = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, **kwargs) as response:
        return response.read(500_000).decode("utf-8", errors="replace")


def parse_google_patents_hits(html: str, query: str) -> list[PatentSearchHit]:
    hits: list[PatentSearchHit] = []
    for match in re.finditer(r'href="(/patent/[^"]+)"[^>]*>(.*?)</a>', html, flags=re.I | re.S):
        href, label = match.groups()
        title = sanitize_untrusted_text(re.sub(r"<[^>]+>", " ", label), max_len=300).strip()
        if len(title) < 4:
            continue
        publication_match = re.search(r"/patent/([^/?#]+)", href)
        publication_number = publication_match.group(1) if publication_match else None
        url = "https://patents.google.com/patent/" + publication_number if publication_number else (
            "https://patents.google.com" + href.split("?")[0]
        )
        hits.append(
            PatentSearchHit(
                id=uuid.uuid4().hex,
                source="google_patents",
                query=query,
                title=title,
                publication_number=publication_number,
                url=url,
            )
        )
    return dedupe_patent_search_hits(hits)


_CJK_QUERY_TRANSLATIONS = {
    "城市体检": "urban health assessment",
    "城市诊断": "urban health assessment",
    "智能体": "agent",
    "多智能体": "multi agent",
    "任务编排": "task orchestration",
    "任务调度": "task scheduling",
    "证据链": "evidence chain",
    "可信复核": "trusted review",
    "复核": "review",
    "工程决策": "engineering decision",
    "低空采集": "low altitude data collection",
    "无人机": "drone UAV",
    "建筑": "building",
    "病害检测": "defect detection",
    "指标": "indicator",
    "置信度": "confidence",
}


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _has_cjk(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", value))


def _patentscope_query_variants(query: str) -> list[str]:
    if not _has_cjk(query):
        return [query]
    translated_terms = [
        translation
        for phrase, translation in _CJK_QUERY_TRANSLATIONS.items()
        if phrase in query
    ]
    translated = " ".join(dict.fromkeys(" ".join(translated_terms).split()))
    return [translated, query] if translated else [query]


def _wipo_publication_number(country: str, raw_number: str, doc_id: str) -> str:
    cleaned = normalize_publication_number(raw_number.replace("/", ""))
    if cleaned and re.match(r"^[A-Z]{2}", cleaned):
        return cleaned
    prefix = re.match(r"^[A-Z]{2}", doc_id or country.strip().upper())
    if cleaned and prefix:
        return prefix.group(0) + cleaned
    return cleaned or normalize_publication_number(doc_id)


def _wipo_date(value: str) -> str:
    value = value.strip()
    match = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", value)
    if not match:
        return value
    day, month, year = match.groups()
    return f"{year}-{month}-{day}"


def _extract_first(pattern: str, text: str) -> str:
    match = re.search(pattern, text, flags=re.I | re.S)
    return _strip_html(match.group(1)) if match else ""


def parse_wipo_patentscope_hits(html: str, query: str) -> list[PatentSearchHit]:
    hits: list[PatentSearchHit] = []
    row_pattern = re.compile(
        r'<tr[^>]+data-ri="\d+"[^>]+data-rk="(?P<doc_id>[^"]+)"(?P<row>.*?)(?=<tr[^>]+data-ri="\d+"[^>]+data-rk=|</tbody>)',
        flags=re.I | re.S,
    )
    for match in row_pattern.finditer(html):
        row = match.group("row")
        doc_id = unescape(match.group("doc_id")).strip()
        title = _extract_first(
            r'<span[^>]+class="[^"]*needTranslation-title[^"]*"[^>]*>.*?<span[^>]+class="[^"]*trans-control[^"]*"[^>]*></span>(.*?)</span>',
            row,
        ) or _extract_first(r'ps-patent-result--title--title[^>]*>(.*?)</div>', row)
        raw_publication = _extract_first(r'ps-patent-result--title--patent-number[^>]*>(.*?)</span>', row)
        country = _extract_first(r'ps-patent-result--title--ctr-pubdate.*?<span[^>]*>(.*?)</span>', row)
        publication_date = _wipo_date(_extract_first(r'resultListTableColumnPubDate[^>]*>(.*?)</span>', row))
        if not publication_date:
            date_block = re.search(r'ps-patent-result--title--ctr-pubdate(?P<block>.*?</div>)', row, flags=re.I | re.S)
            if date_block:
                dates = re.findall(r'<span[^>]*>(.*?)</span>', date_block.group("block"), flags=re.I | re.S)
                publication_date = _wipo_date(_strip_html(dates[-1])) if dates else ""
        if not title and not raw_publication:
            continue
        publication_number = _wipo_publication_number(country, raw_publication, doc_id)
        ipc = _extract_first(r'ps-patent-result--ipc.*?<a[^>]*>(.*?)</a>', row)
        application_number = _extract_first(
            r'Appl\.No.*?<span[^>]+class="[^"]*ps-field--value[^"]*notranslate[^"]*"[^>]*>(.*?)</span>',
            row,
        )
        applicant = _extract_first(r'ps-patent-result--applicant[^>]*>(.*?)</span>', row)
        abstract = _extract_first(r'ps-patent-result--abstract.*?<p[^>]*>(.*?)</p>', row)
        hits.append(
            PatentSearchHit(
                id=uuid.uuid4().hex,
                source="wipo_patentscope",
                query=query,
                title=title or publication_number or doc_id,
                publication_number=publication_number or None,
                application_number=application_number or None,
                applicant=applicant,
                publication_date=publication_date,
                abstract=abstract or None,
                ipc=[ipc] if ipc else [],
                url=f"https://patentscope.wipo.int/search/en/detail.jsf?docId={urllib.parse.quote(doc_id)}",
                metadata={"doc_id": doc_id},
            )
        )
    return dedupe_patent_search_hits(hits)


class CnipaEpubPatentProvider:
    name = "CNIPA EPUB"
    source_id = "cnipa_epub"

    def __init__(self, *, script_path: str | Path | None = None, timeout_seconds: int = 45) -> None:
        configured = os.environ.get("CNIPA_EPUB_SEARCH_SCRIPT")
        resolved = configured if configured else script_path
        self.script_path = Path(resolved) if resolved else None
        self.timeout_seconds = timeout_seconds

    def available(self) -> tuple[bool, str | None]:
        if not self.script_path or not self.script_path.exists():
            return False, "CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search."
        if not (shutil.which("python3") or shutil.which("python")):
            return False, "CNIPA EPUB helper requires a Python executable, but none was found."
        return True, None

    def search(
        self,
        query: str,
        *,
        filters: PatentSearchFilters,
        limit: int,
    ) -> tuple[list[PatentSearchHit], list[str]]:
        del filters
        python = shutil.which("python3") or shutil.which("python")
        if not python or not self.script_path:
            return [], ["CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search."]
        try:
            completed = subprocess.run(
                [python, str(self.script_path), query],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"CNIPA EPUB search timed out for query: {query}") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[:300]
            raise RuntimeError(f"CNIPA EPUB search failed for query {query}: {detail}")
        match = re.search(r"EPUB_HITS_JSON:\s*(\[.*\])", completed.stdout, flags=re.S)
        if not match:
            raise RuntimeError(f"CNIPA EPUB search returned no parseable JSON for query: {query}")
        try:
            raw_hits = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise ValueError(f"CNIPA EPUB JSON parse failed for query {query}: {exc}") from exc
        hits = [
            PatentSearchHit(
                id=uuid.uuid4().hex,
                source="cnipa_epub",
                query=query,
                title=sanitize_untrusted_text(str(raw.get("title") or raw.get("publication_number") or "未命名公开文献"), max_len=300)
                or str(raw.get("title") or raw.get("publication_number") or "未命名公开文献"),
                publication_number=normalize_publication_number(raw.get("publication_number")),
                application_number=raw.get("application_number"),
                applicant=str(raw.get("applicant") or ""),
                publication_date=str(raw.get("publication_date") or ""),
                grant_date=str(raw.get("grant_date") or ""),
                abstract=sanitize_untrusted_text(str(raw.get("abstract"))) if raw.get("abstract") else None,
                ipc=list(raw.get("ipc") or []),
                cpc=list(raw.get("cpc") or []),
                family_id=str(raw.get("family_id") or ""),
                url=str(raw.get("link") or raw.get("url") or ""),
            )
            for raw in raw_hits[:limit]
            if raw.get("link") or raw.get("url")
        ]
        return dedupe_patent_search_hits(hits), []


class WipoPatentscopeProvider:
    name = "WIPO Patentscope"
    source_id = "wipo_patentscope"

    def __init__(self, http_get=None, timeout_seconds: int = 20) -> None:
        self._http_get = http_get or _urllib_get
        self.timeout_seconds = timeout_seconds

    def available(self) -> tuple[bool, str | None]:
        return True, None

    def search(
        self,
        query: str,
        *,
        filters: PatentSearchFilters,
        limit: int,
    ) -> tuple[list[PatentSearchHit], list[str]]:
        del filters
        warnings: list[str] = []
        for provider_query in _patentscope_query_variants(query):
            if not provider_query:
                continue
            url = "https://patentscope.wipo.int/search/en/result.jsf?queryString=" + urllib.parse.quote(provider_query)
            try:
                html = self._http_get(url, self.timeout_seconds)
            except (TimeoutError, SocketTimeout) as exc:
                raise TimeoutError(f"WIPO Patentscope search timed out for query {provider_query}: {exc}") from exc
            except Exception as exc:
                warnings.append(f"WIPO Patentscope search failed for query {provider_query}: {exc}")
                continue
            hits = parse_wipo_patentscope_hits(html, provider_query)[:limit]
            if hits:
                return [
                    hit.model_copy(update={"metadata": {**hit.metadata, "provider_query": provider_query}})
                    for hit in hits
                ], warnings
            warnings.append(f"WIPO Patentscope returned no parseable hits for query: {provider_query}")
        return [], warnings


class GooglePatentsProvider:
    name = "Google Patents"
    source_id = "google_patents"

    def __init__(self, http_get=None, timeout_seconds: int = 20) -> None:
        self._http_get = http_get or _urllib_get
        self.timeout_seconds = timeout_seconds

    def available(self) -> tuple[bool, str | None]:
        return True, None

    def search(
        self,
        query: str,
        *,
        filters: PatentSearchFilters,
        limit: int,
    ) -> tuple[list[PatentSearchHit], list[str]]:
        del filters
        url = "https://patents.google.com/?q=" + urllib.parse.quote(query)
        try:
            html = self._http_get(url, self.timeout_seconds)
        except (TimeoutError, SocketTimeout) as exc:
            raise TimeoutError(f"Google Patents search timed out for query {query}: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Google Patents search failed for query {query}: {exc}") from exc
        hits = parse_google_patents_hits(html, query)[:limit]
        if not hits:
            return [], [f"Google Patents returned no parseable hits for query: {query}"]
        return hits, []


def default_project_patent_providers() -> list[PatentSearchProvider]:
    providers: list[PatentSearchProvider] = [
        CnipaEpubPatentProvider(),
        WipoPatentscopeProvider(),
    ]
    if os.environ.get("PATENT_ENABLE_GOOGLE_PATENTS_FALLBACK", "").lower() in {"1", "true", "yes", "on"}:
        providers.append(GooglePatentsProvider())
    return providers


def _sanitize_candidate_text(value: str | None) -> str:
    return sanitize_untrusted_text(value) if value else ""


def _sanitize_candidate_metadata(value: Any) -> Any:
    if isinstance(value, str):
        return _sanitize_candidate_text(value)
    if isinstance(value, list):
        return [_sanitize_candidate_metadata(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_candidate_metadata(item) for item in value)
    if isinstance(value, dict):
        return {key: _sanitize_candidate_metadata(item) for key, item in value.items()}
    return value


def _dedupe_key(hit: PatentSearchHit) -> str:
    publication = normalize_publication_number(hit.publication_number)
    family = hit.family_id.strip().lower()
    url = hit.url.strip().lower()
    fallback = f"{hit.title.strip().lower()}::{hit.applicant.strip().lower()}::{hit.publication_date[:4]}"
    return publication or family or url or fallback


def _merge_metadata(*values: dict[str, object]) -> dict[str, object]:
    merged: dict[str, object] = {}
    for value in values:
        merged.update(value)
    return merged


def dedupe_patent_search_hits(hits: list[PatentSearchHit]) -> list[PatentSearchHit]:
    retained: list[PatentSearchHit] = []
    by_key: dict[str, int] = {}
    for hit in hits:
        sanitized_hit = hit.model_copy(
            update={
                "title": sanitize_untrusted_text(hit.title, max_len=300) or hit.title,
                "abstract": sanitize_untrusted_text(hit.abstract) if hit.abstract else None,
            }
        )
        key = _dedupe_key(sanitized_hit)
        if key not in by_key:
            by_key[key] = len(retained)
            retained_hit = sanitized_hit.model_copy(
                update={
                    "metadata": {
                        **sanitized_hit.metadata,
                        "provider_sources": [sanitized_hit.source],
                        "source_attempt_ids": [sanitized_hit.provider_attempt_id]
                        if sanitized_hit.provider_attempt_id
                        else [],
                    },
                }
            )
            retained.append(retained_hit)
            continue

        existing = retained[by_key[key]]
        combined_sources = list(
            dict.fromkeys(
                [
                    *existing.metadata.get("provider_sources", []),
                    sanitized_hit.source,
                ]
            )
        )
        combined_attempt_ids = list(
            dict.fromkeys(
                [
                    *existing.metadata.get("source_attempt_ids", []),
                    *( [sanitized_hit.provider_attempt_id] if sanitized_hit.provider_attempt_id else [] ),
                ]
            )
        )
        merged = existing.model_copy(
            update={
                "metadata": _merge_metadata(
                    existing.metadata,
                    {
                        "provider_sources": combined_sources,
                        "source_attempt_ids": combined_attempt_ids,
                    },
                )
            }
        )
        retained[by_key[key]] = merged
    return retained


def run_provider_chain(
    *,
    providers: list[PatentSearchProvider],
    queries: list[tuple[str, str]],
    filters: PatentSearchFilters,
    limit: int,
) -> tuple[list[PatentSearchHit], list[ProviderAttempt], list[str]]:
    all_hits: list[PatentSearchHit] = []
    attempts: list[ProviderAttempt] = []
    warnings: list[str] = []

    if not providers:
        message = "No patent search providers are configured for runtime search."
        warnings.append(message)
        for _strategy_group_id, query in queries:
            timestamp = now_iso()
            attempts.append(
                ProviderAttempt(
                    id=uuid.uuid4().hex,
                    provider="provider_chain",
                    query=query,
                    filters=filters.model_dump(mode="json"),
                    status="skipped",
                    warnings=[message],
                    failure_reason=message,
                    started_at=timestamp,
                    finished_at=timestamp,
                )
            )

    for strategy_group_id, query in queries:
        for provider in providers:
            attempt_id = uuid.uuid4().hex
            started_at = now_iso()
            available, skip_reason = provider.available()
            if not available:
                attempt = ProviderAttempt(
                    id=attempt_id,
                    provider=provider.source_id,
                    query=query,
                    filters=filters.model_dump(mode="json"),
                    status="skipped",
                    warnings=[skip_reason or "provider unavailable"],
                    failure_reason=skip_reason or "provider unavailable",
                    started_at=started_at,
                    finished_at=now_iso(),
                )
                attempts.append(attempt)
                warnings.extend(attempt.warnings)
                continue
            try:
                hits, provider_warnings = provider.search(query, filters=filters, limit=limit)
                tagged_hits = [
                    hit.model_copy(
                        update={
                            "provider_attempt_id": attempt_id,
                            "query": query,
                            "metadata": _merge_metadata(hit.metadata, {"strategy_group": strategy_group_id}),
                        }
                    )
                    for hit in hits
                ]
                attempts.append(
                    ProviderAttempt(
                        id=attempt_id,
                        provider=provider.source_id,
                        query=query,
                        filters=filters.model_dump(mode="json"),
                        status="ok" if tagged_hits else "partial",
                        hit_count=len(tagged_hits),
                        warnings=provider_warnings,
                        started_at=started_at,
                        finished_at=now_iso(),
                    )
                )
                warnings.extend(provider_warnings)
                all_hits.extend(tagged_hits)
            except TimeoutError as exc:
                message = str(exc)
                attempts.append(
                    ProviderAttempt(
                        id=attempt_id,
                        provider=provider.source_id,
                        query=query,
                        filters=filters.model_dump(mode="json"),
                        status="timed_out",
                        warnings=[message],
                        failure_reason=message,
                        started_at=started_at,
                        finished_at=now_iso(),
                    )
                )
                warnings.append(message)
            except Exception as exc:
                message = str(exc)
                attempts.append(
                    ProviderAttempt(
                        id=attempt_id,
                        provider=provider.source_id,
                        query=query,
                        filters=filters.model_dump(mode="json"),
                        status="failed",
                        warnings=[message],
                        failure_reason=message,
                        started_at=started_at,
                        finished_at=now_iso(),
                    )
                )
                warnings.append(message)

    retained_hits = dedupe_patent_search_hits(all_hits)[:limit]
    retained_by_attempt: dict[str, int] = {}
    for hit in retained_hits:
        for attempt_id in hit.metadata.get("source_attempt_ids", []):
            retained_by_attempt[attempt_id] = retained_by_attempt.get(attempt_id, 0) + 1
    finalized_attempts = [
        attempt.model_copy(update={"retained_count": retained_by_attempt.get(attempt.id, 0)})
        for attempt in attempts
    ]
    return retained_hits, finalized_attempts, warnings


def patent_hit_to_candidate(
    hit: PatentSearchHit,
    *,
    project_id: str,
    plan_id: str,
    strategy_group_id: str,
) -> PriorArtCandidate:
    normalized_pub = normalize_publication_number(hit.publication_number)
    sanitized_query = sanitize_untrusted_text(hit.query)
    matched_terms = sanitized_query.split()
    sanitized_metadata = _sanitize_candidate_metadata(hit.metadata)
    if isinstance(sanitized_metadata, dict):
        sanitized_metadata["source_attempt_ids"] = sanitized_metadata.get("source_attempt_ids") or (
            [hit.provider_attempt_id] if hit.provider_attempt_id else []
        )
    else:
        sanitized_metadata = {}
    return PriorArtCandidate(
        id=stable_id(project_id, plan_id, strategy_group_id, hit.source, normalized_pub or hit.url),
        project_id=project_id,
        plan_id=plan_id,
        source=hit.source,
        title=sanitize_untrusted_text(hit.title, max_len=300) or hit.title,
        publication_number=normalized_pub or hit.publication_number,
        application_number=hit.application_number,
        applicant=_sanitize_candidate_text(hit.applicant),
        publication_date=hit.publication_date,
        grant_date=hit.grant_date,
        abstract=sanitize_untrusted_text(hit.abstract) if hit.abstract else None,
        url=hit.url,
        relevance_score=0.0,
        matched_terms=matched_terms,
        ipc=hit.ipc,
        cpc=hit.cpc,
        family_id=hit.family_id,
        fulltext_status="unknown",
        recommended_action="review",
        recommendation_reason="真实专利检索命中，等待全文与相关度复核。",
        metadata={
            **sanitized_metadata,
            "query": sanitized_query,
            "strategy_group": strategy_group_id,
            "normalized_publication_number": normalized_pub,
            "source_attempt_ids": sanitized_metadata.get("source_attempt_ids")
            or ([hit.provider_attempt_id] if hit.provider_attempt_id else []),
        },
        created_at=now_iso(),
    )
