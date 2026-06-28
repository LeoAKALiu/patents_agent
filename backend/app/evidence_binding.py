"""Internal evidence binding helpers for draft-quality workflows.

The bindings built here are supporting metadata for quality analysis, patch
generation, and attorney review. They are intentionally not part of the
official draft export surface.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from backend.app.research.deep_research_intake import parse_deep_research_materials
from backend.app.schemas import (
    DeepResearchPacket,
    DisclosurePackage,
    DisclosureRun,
    EvidenceBinding,
    EvidenceBindingSourceType,
    EvidenceVerificationStatus,
    FormulaRun,
    PatentPointCandidate,
    PriorArtHit,
    ProjectMaterial,
    ProjectRecord,
)


def normalize_evidence_label(value: Any) -> str:
    """Return a deterministic label used for indexing and matching."""

    return " ".join(str(value or "").strip().split()).upper()


def build_evidence_bindings(
    project: ProjectRecord,
    materials: Iterable[ProjectMaterial],
    disclosures: Iterable[DisclosureRun],
    patent_points: Iterable[PatentPointCandidate],
    formula_runs: Iterable[FormulaRun] | None = None,
) -> list[EvidenceBinding]:
    """Build a deterministic, side-effect-free evidence list for a project."""

    builder = _EvidenceBindingBuilder()
    project_id = project.id
    material_list = list(materials)

    for disclosure in disclosures:
        if disclosure.project_id and disclosure.project_id != project_id:
            continue
        if disclosure.package is None:
            continue
        builder.add_disclosure(disclosure)

    for material in material_list:
        if material.project_id and material.project_id != project_id:
            continue
        builder.add_material(material)

    for packet in parse_deep_research_materials(material_list):
        if packet.project_id and packet.project_id != project_id:
            continue
        builder.add_deep_research_packet(packet)

    for point in patent_points:
        builder.add_patent_point(point)

    for formula_run in formula_runs or []:
        if formula_run.project_id and formula_run.project_id != project_id:
            continue
        builder.add_formula_run(formula_run)

    return builder.bindings


def bindings_by_label(bindings: Iterable[EvidenceBinding]) -> dict[str, list[EvidenceBinding]]:
    """Index evidence by all stable labels a caller may cite."""

    index: dict[str, list[EvidenceBinding]] = defaultdict(list)
    for binding in bindings:
        for label in _binding_labels(binding):
            normalized = normalize_evidence_label(label)
            if normalized and binding not in index[normalized]:
                index[normalized].append(binding)
    return dict(index)


def evidence_refs_for_text(
    text: str,
    bindings: Iterable[EvidenceBinding],
    min_confidence: float = 0.6,
) -> list[str]:
    """Return evidence ids whose labels or quotes are present in ``text``."""

    normalized_text = normalize_evidence_label(text)
    refs: list[str] = []
    seen: set[str] = set()
    for binding in bindings:
        if not binding.evidence_id or binding.confidence < min_confidence:
            continue
        if _binding_matches_text(binding, normalized_text):
            if binding.evidence_id not in seen:
                refs.append(binding.evidence_id)
                seen.add(binding.evidence_id)
    return refs


class _EvidenceBindingBuilder:
    def __init__(self) -> None:
        self.bindings: list[EvidenceBinding] = []
        self._ids: set[str] = set()
        self._dedupe: dict[str, str] = {}
        self._counters: dict[str, int] = defaultdict(int)

    def add_disclosure(self, disclosure: DisclosureRun) -> None:
        package = disclosure.package
        if package is None:
            return
        for entry in _iter_research_entries(disclosure):
            self._add(_binding_from_research_entry(entry), dedupe_key=_prior_art_key_from_entry(entry))
        for hit in package.prior_art_hits:
            self._add(_binding_from_prior_art_hit(hit), dedupe_key=_prior_art_key_from_hit(hit))
        self._add(_binding_from_disclosure(disclosure, package), dedupe_key=f"disclosure:{disclosure.id}")

    def add_material(self, material: ProjectMaterial) -> None:
        if not (material.text.strip() or material.file_name.strip()):
            return
        self._add(_binding_from_material(material), dedupe_key=f"material:{material.id}")

    def add_deep_research_packet(self, packet: DeepResearchPacket) -> None:
        for entry in packet.evidence_ledger:
            self._add(
                _binding_from_deep_research_entry(entry),
                dedupe_key=_prior_art_key_from_entry(entry),
            )

    def add_patent_point(self, point: PatentPointCandidate) -> None:
        if not (point.title.strip() or point.technical_solution.strip() or point.innovation.strip()):
            return
        self._add(_binding_from_patent_point(point), dedupe_key=f"patent_point:{point.id}")

    def add_formula_run(self, formula_run: FormulaRun) -> None:
        package = formula_run.package
        if package is None:
            return
        if package.summary.strip():
            self._add(
                EvidenceBinding(
                    evidence_id=self._next_id("F"),
                    source_type=EvidenceBindingSourceType.FORMULA,
                    source_id=formula_run.id,
                    source_label="core formula summary",
                    quote=_clip(package.summary),
                    confidence=0.5,
                    verification_status=EvidenceVerificationStatus.MODEL_GENERATED,
                    internal_only=True,
                    metadata={"formula_run_id": formula_run.id},
                ),
                dedupe_key=f"formula:{formula_run.id}:summary",
            )
        for block in package.formula_blocks:
            self._add(
                EvidenceBinding(
                    evidence_id=self._next_id("F"),
                    source_type=EvidenceBindingSourceType.FORMULA,
                    source_id=block.id,
                    source_label=block.name or block.id,
                    quote=_clip(" ".join(part for part in (block.latex, block.purpose, block.claim_hook) if part)),
                    confidence=0.5,
                    verification_status=EvidenceVerificationStatus.MODEL_GENERATED,
                    internal_only=True,
                    metadata={"formula_run_id": formula_run.id, "latex": block.latex},
                ),
                dedupe_key=f"formula:{formula_run.id}:{block.id}",
            )

    def _add(self, binding: EvidenceBinding | None, *, dedupe_key: str = "") -> None:
        if binding is None:
            return
        normalized_key = normalize_evidence_label(dedupe_key)
        if normalized_key and normalized_key in self._dedupe:
            return
        evidence_id = binding.evidence_id or self._next_id("B")
        if evidence_id in self._ids:
            evidence_id = self._next_id(evidence_id.rstrip("0123456789") or "B")
        stored = binding.model_copy(update={"evidence_id": evidence_id})
        self.bindings.append(stored)
        self._ids.add(stored.evidence_id)
        if normalized_key:
            self._dedupe[normalized_key] = stored.evidence_id

    def _next_id(self, prefix: str) -> str:
        while True:
            self._counters[prefix] += 1
            candidate = f"{prefix}{self._counters[prefix]:03d}"
            if candidate not in self._ids:
                return candidate


def _binding_from_research_entry(entry: dict[str, Any]) -> EvidenceBinding | None:
    source_id = _first_text(entry, "publication_number", "url", "evidence_id", "title")
    if not source_id:
        return None
    title = _first_text(entry, "title", "publication_number", "url", "evidence_id")
    source = _first_text(entry, "source", "provider")
    query = _first_text(entry, "matched_query", "query")
    quote = _first_text(entry, "snippet", "abstract_snippet", "relevance", "summary", "title")
    confidence = _confidence(entry.get("confidence"), default=0.65)
    publication_number = _clean_text(entry.get("publication_number"))
    url = _clean_text(entry.get("url"))
    citable = bool(entry.get("citable", True))
    metadata = _compact_dict(
        {
            "publication_number": publication_number,
            "url": url,
            "source": source,
            "provider": _clean_text(entry.get("provider")),
            "query": query,
            "title": title,
        }
    )
    return EvidenceBinding(
        evidence_id=_clean_text(entry.get("evidence_id")),
        source_type=EvidenceBindingSourceType.PRIOR_ART,
        source_id=source_id,
        source_label=title,
        quote=_clip(quote),
        confidence=confidence,
        verification_status=EvidenceVerificationStatus.RETRIEVED,
        internal_only=True,
        citable=citable,
        metadata=metadata,
    )


def _binding_from_prior_art_hit(hit: PriorArtHit) -> EvidenceBinding:
    source_id = hit.publication_number or hit.url or hit.id
    quote = "；".join(hit.differentiators) or hit.relevance_summary or hit.abstract or hit.title
    return EvidenceBinding(
        source_type=EvidenceBindingSourceType.PRIOR_ART,
        source_id=source_id,
        source_label=hit.title or source_id,
        quote=_clip(quote),
        confidence=0.65,
        verification_status=EvidenceVerificationStatus.RETRIEVED,
        internal_only=True,
        citable=True,
        metadata=_compact_dict(
            {
                "hit_id": hit.id,
                "publication_number": hit.publication_number,
                "url": hit.url,
                "source": hit.source,
                "query": hit.query,
                "title": hit.title,
                "differentiators": hit.differentiators,
            }
        ),
    )


def _binding_from_deep_research_entry(entry: dict[str, Any]) -> EvidenceBinding | None:
    binding = _binding_from_research_entry(entry)
    if binding is None:
        return None
    citable = bool(binding.metadata.get("url") or binding.metadata.get("publication_number"))
    if not citable:
        return None
    return binding.model_copy(
        update={
            "internal_only": True,
            "citable": citable,
        }
    )


def _binding_from_disclosure(disclosure: DisclosureRun, package: DisclosurePackage) -> EvidenceBinding | None:
    quote = _clip(" ".join(part for part in (package.summary, package.materials_summary) if part))
    if not (package.title.strip() or quote):
        return None
    return EvidenceBinding(
        source_type=EvidenceBindingSourceType.DISCLOSURE,
        source_id=disclosure.id,
        source_label=package.title or disclosure.id,
        quote=quote,
        confidence=_research_confidence(package.research_confidence),
        verification_status=EvidenceVerificationStatus.MODEL_GENERATED,
        internal_only=True,
        citable=False,
        metadata={"research_confidence": package.research_confidence},
    )


def _binding_from_material(material: ProjectMaterial) -> EvidenceBinding:
    return EvidenceBinding(
        source_type=EvidenceBindingSourceType.PROJECT_MATERIAL,
        source_id=material.id,
        source_label=material.file_name or material.id,
        quote=_clip(material.text),
        confidence=0.8 if material.status == "processed" else 0.45,
        verification_status=EvidenceVerificationStatus.USER_PROVIDED,
        internal_only=True,
        citable=False,
        metadata=_compact_dict(
            {
                "file_name": material.file_name,
                "file_type": material.file_type,
                "path": material.path,
                "status": material.status,
                "warnings": material.warnings,
            }
        ),
    )


def _binding_from_patent_point(point: PatentPointCandidate) -> EvidenceBinding:
    status = _point_status(point.evidence_status)
    quote = _clip(
        " ".join(
            part
            for part in (
                point.technical_problem,
                point.innovation,
                point.technical_solution,
                "；".join(point.beneficial_effects),
            )
            if part
        )
    )
    return EvidenceBinding(
        source_type=EvidenceBindingSourceType.PATENT_POINT,
        source_id=point.id,
        source_label=point.title or point.id,
        quote=quote,
        confidence=_point_confidence(status),
        verification_status=status,
        internal_only=True,
        citable=False,
        metadata=_compact_dict(
            {
                "source_type": point.source_type,
                "selected": point.selected,
                "support_gaps": point.support_gaps,
                "experiment_needed": point.experiment_needed,
                "protection_focus": point.protection_focus,
            }
        ),
    )


def _iter_research_entries(disclosure: DisclosureRun) -> Iterable[dict[str, Any]]:
    package = disclosure.package
    if package is not None:
        yield from _entries_from_payload(package.research_ledger)
    for result in disclosure.stage_results:
        yield from _entries_from_payload(result)


def _entries_from_payload(payload: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(payload, dict):
        return
    entries = payload.get("entries")
    if isinstance(entries, list):
        for entry in entries:
            if _looks_like_research_entry(entry):
                yield entry
    evidence_ledger = payload.get("evidence_ledger")
    if isinstance(evidence_ledger, list):
        for entry in evidence_ledger:
            if _looks_like_research_entry(entry):
                yield entry
    for key in ("payload", "packet", "deep_research_packet", "result", "research_packet"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            yield from _entries_from_payload(nested)


def _looks_like_research_entry(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    return bool(_first_text(entry, "publication_number", "url", "title", "evidence_id"))


def _prior_art_key_from_entry(entry: dict[str, Any]) -> str:
    return "prior_art:" + _first_text(entry, "publication_number", "url", "title", "evidence_id")


def _prior_art_key_from_hit(hit: PriorArtHit) -> str:
    return "prior_art:" + (hit.publication_number or hit.url or hit.title or hit.id)


def _binding_labels(binding: EvidenceBinding) -> list[str]:
    labels = [binding.evidence_id, binding.source_id, binding.source_label]
    for key in ("publication_number", "url", "title", "source", "provider", "hit_id", "file_name"):
        value = binding.metadata.get(key)
        if isinstance(value, str):
            labels.append(value)
    return labels


def _binding_matches_text(binding: EvidenceBinding, normalized_text: str) -> bool:
    for label in _binding_labels(binding):
        normalized = normalize_evidence_label(label)
        if len(normalized) >= 3 and normalized in normalized_text:
            return True
    quote = normalize_evidence_label(binding.quote)
    if len(quote) >= 6 and quote in normalized_text:
        return True
    for fragment in _quote_fragments(binding.quote):
        if fragment in normalized_text:
            return True
    return False


def _quote_fragments(quote: str) -> Iterable[str]:
    normalized = normalize_evidence_label(quote)
    for separator in ("。", "；", ";", "，", ",", ".", "\n"):
        normalized = normalized.replace(separator, "|")
    for fragment in normalized.split("|"):
        fragment = fragment.strip()
        if len(fragment) >= 6:
            yield fragment
        for prefix in ("未公开", "没有公开", "未记载", "公开了", "公开", "记载了", "记载"):
            if fragment.startswith(prefix):
                trimmed = fragment[len(prefix):].strip()
                if len(trimmed) >= 6:
                    yield trimmed


def _point_status(value: str) -> EvidenceVerificationStatus:
    try:
        return EvidenceVerificationStatus(value)
    except ValueError:
        return EvidenceVerificationStatus.MODEL_GENERATED


def _point_confidence(status: EvidenceVerificationStatus) -> float:
    if status == EvidenceVerificationStatus.VERIFIED:
        return 0.9
    if status == EvidenceVerificationStatus.FEASIBLE_UNVERIFIED:
        return 0.55
    if status == EvidenceVerificationStatus.NEEDS_EXPERIMENT:
        return 0.35
    return 0.3


def _research_confidence(value: str) -> float:
    if value == "high":
        return 0.7
    if value == "medium":
        return 0.55
    return 0.4


def _confidence(value: Any, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0.0, min(1.0, parsed))


def _first_text(values: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _clean_text(values.get(key))
        if value:
            return value
    return ""


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clip(value: str, limit: int = 600) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip()


def _compact_dict(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value not in ("", None, [], {})}
