from __future__ import annotations

import re
from urllib.parse import unquote, urlparse


PUBLIC_PATENT_HOSTS = frozenset(
    {
        "patents.google.com",
        "cnipa.gov.cn",
        "epub.cnipa.gov.cn",
        "wipo.int",
        "patentscope.wipo.int",
        "espacenet.com",
        "worldwide.espacenet.com",
        "epo.org",
    }
)

URL_PATTERN = re.compile(r"https?://\S+")
PUBLICATION_NUMBER_RE = re.compile(r"\b(?:CN|WO|US|EP|JP|KR)\s?\d{5,}[A-Z]\d?\b", re.IGNORECASE)


def normalize_url(url: str) -> str:
    return url.strip().rstrip(".,;:)]}>。！？）】")


def is_supported_public_patent_url(url: str) -> bool:
    hostname = (urlparse(normalize_url(url)).hostname or "").lower()
    if not hostname:
        return False
    return any(hostname == allowed or hostname.endswith(f".{allowed}") for allowed in PUBLIC_PATENT_HOSTS)


def clean_prior_art_url_for_prompt(url: str, publication_number: str | None = None) -> str:
    normalized = normalize_url(url or "")
    if not normalized or not is_supported_public_patent_url(normalized):
        return ""
    if public_url_publication_mismatch(publication_number or "", normalized):
        return ""
    return normalized


def sanitize_patent_like_urls_for_public_text(text: str) -> str:
    if not text:
        return text
    return "\n".join(_sanitize_patent_like_urls_in_line(line) for line in text.splitlines())


def public_url_publication_mismatch(publication: str, url: str) -> bool:
    normalized_publication = normalize_publication(publication)
    if not normalized_publication:
        return False
    alias = publication_from_public_url(url)
    return bool(alias and alias != normalized_publication)


def publication_from_public_url(url: str) -> str:
    if not is_supported_public_patent_url(url):
        return ""
    match = PUBLICATION_NUMBER_RE.search(unquote(normalize_url(url)))
    if not match:
        return ""
    return normalize_publication(match.group(0))


def normalize_publication(value: str) -> str:
    return re.sub(r"\s+", "", value or "").upper()


def _sanitize_patent_like_urls_in_line(line: str) -> str:
    matches = list(URL_PATTERN.finditer(line))
    if not matches:
        return line

    output: list[str] = []
    last_index = 0
    for match in matches:
        raw_url = match.group(0)
        normalized_url = normalize_url(raw_url)
        output.append(line[last_index:match.start()])
        if _should_remove_public_text_url(line, match, normalized_url):
            output.append(_trailing_url_punctuation(raw_url, normalized_url))
        else:
            output.append(raw_url)
        last_index = match.end()
    output.append(line[last_index:])
    return "".join(output)


def _should_remove_public_text_url(line: str, match: re.Match[str], normalized_url: str) -> bool:
    if not normalized_url or not _looks_patent_like_url(normalized_url):
        return False
    if not is_supported_public_patent_url(normalized_url):
        return True
    publication_context = _publication_context_for_url(line, match)
    return public_url_publication_mismatch(publication_context, normalized_url)


def _publication_context_for_url(line: str, match: re.Match[str]) -> str:
    before = line[: match.start()]
    after = line[match.end() :]
    before_matches = list(PUBLICATION_NUMBER_RE.finditer(before))
    if before_matches:
        return before_matches[-1].group(0)
    after_match = PUBLICATION_NUMBER_RE.search(after)
    return after_match.group(0) if after_match else ""


def _looks_patent_like_url(url: str) -> bool:
    parsed = urlparse(normalize_url(url))
    path = unquote(parsed.path or "").lower()
    decoded = unquote(url)
    return bool(PUBLICATION_NUMBER_RE.search(decoded) or "/patent/" in path)


def _trailing_url_punctuation(raw_url: str, normalized_url: str) -> str:
    if normalized_url and raw_url.startswith(normalized_url):
        return raw_url[len(normalized_url) :]
    return ""
