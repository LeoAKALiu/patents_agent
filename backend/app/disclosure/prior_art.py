from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
import uuid
from html import unescape
from pathlib import Path
from typing import Protocol

from backend.app.research.ledger import SourceLedger, citation_snapshot
from backend.app.schemas import PriorArtHit


class PriorArtProvider(Protocol):
    def search(self, terms: list[str], limit: int) -> tuple[list[PriorArtHit], list[str]]:
        ...


class PublicPriorArtProvider:
    def __init__(self, cnipa_script: Path | None = None, timeout_seconds: int = 45) -> None:
        configured = os.environ.get("CNIPA_EPUB_SEARCH_SCRIPT")
        self.cnipa_script = Path(configured) if configured else cnipa_script
        self.timeout_seconds = timeout_seconds

    def search(self, terms: list[str], limit: int) -> tuple[list[PriorArtHit], list[str]]:
        return self._search(terms, limit, ledger=None)

    def search_with_ledger(
        self, terms: list[str], limit: int, ledger: SourceLedger
    ) -> tuple[list[PriorArtHit], list[str]]:
        return self._search(terms, limit, ledger=ledger)

    def _search(
        self, terms: list[str], limit: int, *, ledger: SourceLedger | None
    ) -> tuple[list[PriorArtHit], list[str]]:
        terms = normalize_search_terms(terms, fallback_text=" ".join(terms))
        warnings: list[str] = []
        hits: list[PriorArtHit] = []
        if limit <= 0:
            return [], warnings
        for term in terms[:8]:
            cnipa_hits, cnipa_warnings = self._search_cnipa(term, max(1, limit - len(hits)))
            _record_ledger_attempt(
                ledger,
                provider="cnipa",
                kind="patent",
                query=term,
                hits=cnipa_hits,
                warnings=cnipa_warnings,
            )
            warnings.extend(cnipa_warnings)
            hits.extend(cnipa_hits)
            if len(hits) >= limit:
                deduped = dedupe_prior_art_hits(hits)[:limit]
                return deduped, [*warnings, *prior_art_url_warnings(deduped)]
        if len(hits) < limit:
            for term in terms[:4]:
                google_hits, google_warnings = self._search_google_patents(term, max(1, limit - len(hits)))
                _record_ledger_attempt(
                    ledger,
                    provider="google_patents",
                    kind="patent",
                    query=term,
                    hits=google_hits,
                    warnings=google_warnings,
                )
                warnings.extend(google_warnings)
                hits.extend(google_hits)
                if len(hits) >= limit:
                    break
        deduped = dedupe_prior_art_hits(hits)[:limit]
        return deduped, [*warnings, *prior_art_url_warnings(deduped)]

    def _search_cnipa(self, term: str, limit: int) -> tuple[list[PriorArtHit], list[str]]:
        if not self.cnipa_script or not self.cnipa_script.exists():
            return [], ["CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search."]
        python = shutil.which("python3") or shutil.which("python")
        if not python:
            return [], ["Python executable not found for CNIPA EPUB helper."]
        try:
            completed = subprocess.run(
                [python, str(self.cnipa_script), term],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return [], [f"CNIPA EPUB search timed out for term: {term}"]
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[:300]
            return [], [f"CNIPA EPUB search failed for term {term}: {detail}"]
        match = re.search(r"EPUB_HITS_JSON:\s*(\[.*\])", completed.stdout, flags=re.S)
        if not match:
            return [], [f"CNIPA EPUB search returned no parseable JSON for term: {term}"]
        try:
            raw_hits = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            return [], [f"CNIPA EPUB JSON parse failed for term {term}: {exc}"]
        return [
            _hit_from_mapping(raw, source="CNIPA EPUB", query=term)
            for raw in raw_hits[:limit]
            if raw.get("link") or raw.get("url")
        ], []

    def _search_google_patents(self, term: str, limit: int) -> tuple[list[PriorArtHit], list[str]]:
        url = "https://patents.google.com/?q=" + urllib.parse.quote(term)
        request = urllib.request.Request(url, headers={"User-Agent": "patents-agent/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=min(self.timeout_seconds, 20)) as response:
                html = response.read(500_000).decode("utf-8", errors="replace")
        except Exception as exc:
            return [], [f"Google Patents fallback failed for term {term}: {exc}"]
        hits = parse_google_patents_html(html, term)[:limit]
        if not hits:
            return [], [f"Google Patents returned no parseable hits for term: {term}"]
        return hits, []


class StaticPriorArtProvider:
    def __init__(self, hits: list[PriorArtHit] | None = None, warnings: list[str] | None = None) -> None:
        self.hits = hits or []
        self.warnings = warnings or []

    def search(self, terms: list[str], limit: int) -> tuple[list[PriorArtHit], list[str]]:
        result: list[PriorArtHit] = []
        for hit in self.hits[:limit]:
            if not hit.query and terms:
                result.append(hit.model_copy(update={"query": terms[0]}))
            else:
                result.append(hit)
        return result, list(self.warnings)

    def search_with_ledger(
        self, terms: list[str], limit: int, ledger: SourceLedger
    ) -> tuple[list[PriorArtHit], list[str]]:
        hits, warnings = self.search(terms, limit)
        _record_ledger_attempt(
            ledger,
            provider="static_prior_art",
            kind="patent",
            query="; ".join(terms[:4]),
            hits=hits,
            warnings=warnings,
        )
        return hits, warnings


def parse_cnipa_epub_html(html: str, query: str) -> list[PriorArtHit]:
    hits: list[PriorArtHit] = []
    blocks = _split_cnipa_items(html)
    if not blocks:
        blocks = re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.I | re.S)
    for block in blocks:
        title = _first_match(block, [r'<h1\s+class="title">\s*([^<]+)', r'title="([^"]+)"', r">([^<]{6,200})<"])
        link = _first_match(block, [r'title="(https?://epub\.cnipa\.gov\.cn/patent/[^"]+)"', r'href="([^"]+)"'])
        pub_number = _first_match(
            block,
            [
                r"(?:申请公布号|授权公告号)[：:]\s*</dt>\s*<dd>([^<]+)",
                r"(CN\s*\d{9,}[A-Z]?|ZL\s*\d{9,}\.\d+)",
            ],
        )
        abstract = _extract_cnipa_abstract(block)
        if not title and not pub_number:
            continue
        if link and not link.startswith("http"):
            link = "http://epub.cnipa.gov.cn/" + link.lstrip("/")
        if not link and pub_number:
            link = f"http://epub.cnipa.gov.cn/patent/{pub_number.strip()}"
        if not link:
            continue
        hits.append(
            PriorArtHit(
                id=uuid.uuid4().hex,
                source="CNIPA EPUB",
                query=query,
                title=_plain(title or pub_number or "未命名公开文献"),
                publication_number=_plain(pub_number) if pub_number else None,
                url=link,
                abstract=_plain(abstract) if abstract else None,
            )
        )
    return dedupe_prior_art_hits(hits)


def parse_google_patents_html(html: str, query: str) -> list[PriorArtHit]:
    hits: list[PriorArtHit] = []
    for match in re.finditer(r'href="(/patent/[^"]+)"[^>]*>(.*?)</a>', html, flags=re.I | re.S):
        href, label = match.groups()
        title = _plain(label)
        if len(title) < 4:
            continue
        url = "https://patents.google.com" + href.split("?")[0]
        pub_match = re.search(r"/patent/([^/]+)", href)
        hits.append(
            PriorArtHit(
                id=uuid.uuid4().hex,
                source="Google Patents",
                query=query,
                title=title,
                publication_number=pub_match.group(1) if pub_match else None,
                url=url,
            )
        )
    return dedupe_prior_art_hits(hits)


def normalize_search_terms(terms: list[str], *, fallback_text: str = "", max_terms: int = 8) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    fallback_terms = _candidate_chunks_from_text(fallback_text)

    def add(term: str) -> None:
        cleaned = _clean_term(term)
        if not cleaned or not _is_useful_term(cleaned):
            return
        if len(cleaned) > 24:
            return
        key = cleaned.casefold()
        if key in seen:
            return
        seen.add(key)
        normalized.append(cleaned)

    for raw in terms:
        cleaned = _clean_term(raw)
        if not cleaned:
            continue
        if len(cleaned) <= 24 and _is_useful_term(cleaned):
            add(cleaned)
        else:
            for chunk in _candidate_chunks_from_text(cleaned):
                add(chunk)
        if len(normalized) >= max_terms:
            return normalized[:max_terms]

    if len(normalized) <= 1:
        for chunk in fallback_terms:
            add(chunk)
            if len(normalized) >= max_terms:
                break

    if normalized:
        return normalized[:max_terms]

    for raw in terms:
        cleaned = _clean_term(raw)
        if cleaned:
            return [cleaned[:24].strip()]
    return []


def dedupe_prior_art_hits(hits: list[PriorArtHit]) -> list[PriorArtHit]:
    seen: set[str] = set()
    out: list[PriorArtHit] = []
    for hit in hits:
        publication = (hit.publication_number or "").strip()
        url = (hit.url or "").strip()
        title = (hit.title or "").strip()
        key = publication or url or title
        if not key:
            continue
        normalized_key = key.upper()
        if normalized_key in seen:
            continue
        seen.add(normalized_key)
        out.append(hit)
    return out


def prior_art_url_warnings(hits: list[PriorArtHit]) -> list[str]:
    warnings: list[str] = []
    for hit in hits:
        if (hit.url or "").strip():
            continue
        label = (hit.publication_number or hit.title or hit.id).strip()
        title = (hit.title or "").strip()
        if title and title != label:
            warnings.append(f"prior_art missing public URL: {label} {title}")
        else:
            warnings.append(f"prior_art missing public URL: {label}")
    return warnings


def _split_cnipa_items(html: str) -> list[str]:
    if 'class="item"' not in html and "class='item'" not in html:
        return []
    parts = re.split(r'(<div\s+class=["\']item["\'][^>]*>)', html, flags=re.I)
    return [parts[index] + parts[index + 1] for index in range(1, len(parts) - 1, 2)]


def _extract_cnipa_abstract(block: str) -> str | None:
    match = re.search(r"<dt[^>]*>\s*摘要\s*[：:]\s*</dt>\s*<dd[^>]*>(.*?)</dd>", block, flags=re.I | re.S)
    return match.group(1) if match else None


def _first_match(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I | re.S)
        if match:
            return match.group(1).strip()
    return None


def _plain(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _hit_from_mapping(raw: dict, source: str, query: str) -> PriorArtHit:
    url = str(raw.get("link") or raw.get("url") or "")
    return PriorArtHit(
        id=uuid.uuid4().hex,
        source=source,
        query=query,
        title=str(raw.get("title") or raw.get("pub_number") or raw.get("publication_number") or "未命名公开文献"),
        publication_number=raw.get("pub_number") or raw.get("publication_number"),
        url=url,
        abstract=raw.get("abstract"),
    )


def _candidate_chunks_from_text(text: str) -> list[str]:
    cleaned = _clean_term(text)
    if not cleaned:
        return []
    tokens = [_clean_term(token) for token in re.split(r"[\s,，;；/]+", cleaned)]
    tokens = [token for token in tokens if token and _is_useful_term(token)]
    if len(tokens) >= 2:
        chunks: list[str] = []
        for start in range(len(tokens)):
            for width in (3, 2, 4):
                window = tokens[start : start + width]
                if len(window) < 2:
                    continue
                chunk = " ".join(window).strip()
                if len(chunk) <= 24:
                    chunks.append(chunk)
        return chunks
    if _contains_cjk(cleaned):
        compact = re.sub(r"\s+", "", cleaned)
        core = re.sub(r"^(一种|一个|基于|关于)", "", compact)
        core = re.sub(r"(方法及系统|方法|系统|装置|设备)$", "", core)
        spans = []
        for pattern in (r".{4,8}?缺陷.{0,4}", r".{2,8}?神经网络.{0,4}", r".{2,8}?实时反馈.{0,4}"):
            match = re.search(pattern, core)
            if match:
                spans.append(match.group(0))
        if spans:
            return [span[:24] for span in spans if _is_useful_term(span)]
        if len(core) > 24:
            midpoint = max(2, min(len(core) - 2, len(core) // 2))
            return [core[:midpoint][:24], core[midpoint:][:24]]
    return [cleaned[:24]] if len(cleaned) <= 24 else []


def _clean_term(term: str) -> str:
    term = re.sub(r"\s+", " ", term or "").strip()
    return term.strip(" ,，;；")


def _is_useful_term(term: str) -> bool:
    cjk_count = len(re.findall(r"[\u3400-\u9fff]", term))
    if cjk_count >= 2:
        return True
    ascii_count = len(re.findall(r"[A-Za-z0-9]", term))
    return ascii_count >= 3


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", text))


def _record_ledger_attempt(
    ledger: SourceLedger | None,
    *,
    provider: str,
    kind: str,
    query: str,
    hits: list[PriorArtHit],
    warnings: list[str],
) -> None:
    if ledger is None:
        return

    entry = ledger.start(provider=provider, kind=kind, query=query)
    reason = "; ".join(warnings)[:500]
    lowered_reason = reason.lower()
    if hits:
        entry.mark_ok(
            hit_count=len(hits),
            parsed_count=len(hits),
            dedupe_count=0,
            retained_count=len(hits),
            citations=[citation_snapshot(hit) for hit in hits],
        )
    elif "not configured" in lowered_reason or "executable not found" in lowered_reason:
        entry.mark_skipped(reason or "provider is not configured")
    elif "timed out" in lowered_reason or "timeout" in lowered_reason:
        entry.mark_timeout(reason or "provider timed out")
    elif "failed" in lowered_reason or "parse" in lowered_reason:
        entry.mark_failed(reason or "provider failed")
    else:
        entry.mark_ok(hit_count=0, parsed_count=0, dedupe_count=0, retained_count=0)
