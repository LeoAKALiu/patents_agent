"""Corpus service - business logic for corpus document management.

Wraps store and index operations so the corpus router stays thin.
The existing ``CorpusImportService`` from ``backend.app.corpus.pipeline``
handles import job orchestration; this module provides the query wrappers.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from backend.app.patent_parser import chunk_document, make_patent_document, read_document_text
from backend.app.schemas import PatentChunk


def import_corpus_document(
    *,
    stored_path: Path,
    store,
    index,
) -> dict:
    """Read a patent document from disk, chunk it, and persist."""
    try:
        text = read_document_text(stored_path)
    except ValueError as exc:
        raise exc

    safe_name = stored_path.name
    document = make_patent_document(uuid.uuid4().hex, safe_name, text)
    chunks = [PatentChunk(**chunk) for chunk in chunk_document(document)]
    store.add_document(document, chunks)
    index.add(chunks)
    return {
        "document": document.model_dump(mode="json"),
        "chunks_count": len(chunks),
        "warnings": [],
    }
