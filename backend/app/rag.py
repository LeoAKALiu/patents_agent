from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from backend.app.schemas import PatentChunk, SearchResult, SectionType


class LocalVectorIndex:
    """Small deterministic lexical index used for tests and offline fallback."""

    def __init__(self) -> None:
        self._chunks: list[PatentChunk] = []
        self._vectors: dict[str, Counter[str]] = {}

    def add(self, chunks: list[PatentChunk]) -> None:
        for chunk in chunks:
            self._chunks.append(chunk)
            self._vectors[chunk.id] = _vectorize(chunk.text)

    def search(
        self,
        query: str,
        section_type: SectionType | None = None,
        limit: int = 5,
        version_name: str | None = None,
    ) -> list[SearchResult]:
        query_vector = _vectorize(query)
        results: list[SearchResult] = []
        for chunk in self._chunks:
            if section_type and chunk.section_type != section_type:
                continue
            if version_name and chunk.metadata.get("version_name") != version_name:
                continue
            score = _cosine(query_vector, self._vectors[chunk.id])
            results.append(SearchResult(chunk=chunk, score=score))
        results.sort(key=lambda result: result.score, reverse=True)
        return results[:limit]


class ChromaVectorIndex:
    """Chroma-backed local persistent index with deterministic local embeddings."""

    def __init__(self, persist_dir: Path) -> None:
        import chromadb

        self.client = chromadb.PersistentClient(path=str(persist_dir))
        self.collection = self.client.get_or_create_collection(
            name="patent_chunks",
            embedding_function=_ChromaHashEmbedding(),
        )

    def add(self, chunks: list[PatentChunk]) -> None:
        if not chunks:
            return
        self.collection.upsert(
            ids=[chunk.id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[_flatten_metadata(chunk) for chunk in chunks],
        )

    def search(
        self,
        query: str,
        section_type: SectionType | None = None,
        limit: int = 5,
        version_name: str | None = None,
    ) -> list[SearchResult]:
        where_clauses: list[dict[str, str]] = []
        if section_type:
            where_clauses.append({"section_type": section_type.value})
        if version_name:
            where_clauses.append({"meta_version_name": version_name})
        if len(where_clauses) == 1:
            where = where_clauses[0]
        elif len(where_clauses) > 1:
            where = {"$and": where_clauses}
        else:
            where = None
        raw = self.collection.query(query_texts=[query], n_results=limit, where=where)
        ids = raw.get("ids", [[]])[0]
        documents = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0] if raw.get("distances") else [0.0 for _ in ids]
        results: list[SearchResult] = []
        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
            chunk = PatentChunk(
                id=chunk_id,
                document_id=str(metadata.get("document_id", "")),
                section_type=SectionType(str(metadata.get("section_type", SectionType.OTHER.value))),
                text=text,
                ordinal=int(metadata.get("ordinal", 0)),
                metadata={key.removeprefix("meta_"): value for key, value in metadata.items() if key.startswith("meta_")},
            )
            score = 1.0 / (1.0 + float(distance))
            results.append(SearchResult(chunk=chunk, score=score))
        return results


VectorIndex = LocalVectorIndex | ChromaVectorIndex


def create_vector_index(persist_dir: Path) -> VectorIndex:
    try:
        return ChromaVectorIndex(persist_dir)
    except Exception:
        return LocalVectorIndex()


def _vectorize(text: str) -> Counter[str]:
    lowered = text.lower()
    words = re.findall(r"[a-z0-9_]+", lowered)
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", lowered)
    bigrams = ["".join(chinese_chars[i : i + 2]) for i in range(max(0, len(chinese_chars) - 1))]
    return Counter(words + chinese_chars + bigrams)


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(left[token] * right.get(token, 0) for token in left)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _flatten_metadata(chunk: PatentChunk) -> dict[str, str | int | float | bool]:
    metadata: dict[str, str | int | float | bool] = {
        "document_id": chunk.document_id,
        "section_type": chunk.section_type.value,
        "ordinal": chunk.ordinal,
    }
    for key, value in chunk.metadata.items():
        if isinstance(value, (str, int, float, bool)):
            metadata[f"meta_{key}"] = value
    return metadata


class _ChromaHashEmbedding:
    def __call__(self, input: list[str]) -> list[list[float]]:
        return [_hash_embedding(text) for text in input]


def _hash_embedding(text: str, dimensions: int = 128) -> list[float]:
    vector = [0.0] * dimensions
    for token, count in _vectorize(text).items():
        vector[hash(token) % dimensions] += float(count)
    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [value / norm for value in vector]
