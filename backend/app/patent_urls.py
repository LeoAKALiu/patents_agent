from __future__ import annotations

from urllib.parse import urlparse


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


def normalize_url(url: str) -> str:
    return url.strip().rstrip(".,;:)]}>。！？）】")


def is_supported_public_patent_url(url: str) -> bool:
    hostname = (urlparse(normalize_url(url)).hostname or "").lower()
    if not hostname:
        return False
    return any(hostname == allowed or hostname.endswith(f".{allowed}") for allowed in PUBLIC_PATENT_HOSTS)
