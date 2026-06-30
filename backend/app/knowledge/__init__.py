"""Patent search provider models and helpers."""

from .patent_search import (
    PatentSearchProvider,
    dedupe_patent_search_hits,
    normalize_publication_number,
    patent_hit_to_candidate,
)

__all__ = [
    "PatentSearchProvider",
    "dedupe_patent_search_hits",
    "normalize_publication_number",
    "patent_hit_to_candidate",
]
