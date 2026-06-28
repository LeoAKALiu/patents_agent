from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from typing import Any

from backend.app.schemas import (
    DeepResearchEvidenceRef,
    DeepResearchFinding,
    DeepResearchPacket,
    PriorArtHit,
    ProjectMaterial,
)

PUBLICATION_RE = re.compile(r"\b((?:CN|WO|US|EP|JP|KR)\s?\d{5,}[A-Z]\d?)\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s)>\]]+")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")

SECTION_CATEGORY_BY_KEYWORD: tuple[tuple[tuple[str, ...], str], ...] = (
    (("现有技术", "prior art", "公开文献", "专利"), "prior_art_cluster"),
    (("差异", "区别", "differentiator", "novelty"), "differentiator"),
    (("权利要求", "claim", "保护范围", "约束"), "claim_constraint"),
    (("证据缺口", "缺口", "需补充", "实验"), "evidence_gap"),
    (("风险", "warning", "创造性攻击", "规避"), "warning"),
    (("任务", "completion", "补强"), "completion_task"),
)


def is_deep_research_markdown_material(file_name: str, text: str) -> bool:
    suffix_ok = file_name.lower().endswith((".md", ".markdown"))
    if not suffix_ok:
        return False
    lowered = text.lower()
    signals = ("deepresearch", "deep research", "现有技术", "差异点", "证据缺口", "权利要求约束")
    return sum(1 for signal in signals if signal.lower() in lowered) >= 2


def parse_deep_research_materials(materials: Iterable[ProjectMaterial]) -> list[DeepResearchPacket]:
    packets: list[DeepResearchPacket] = []
    for material in materials:
        if material.status != "processed":
            continue
        if not is_deep_research_markdown_material(material.file_name, material.text):
            continue
        packets.append(
            parse_deep_research_markdown(
                material.project_id,
                material.text,
                source_label=material.file_name,
            )
        )
    return packets


def parse_deep_research_markdown(project_id: str, text: str, *, source_label: str = "") -> DeepResearchPacket:
    sections = _split_sections(text)
    findings: list[DeepResearchFinding] = []
    evidence_refs: list[DeepResearchEvidenceRef] = []
    differentiators: list[str] = []
    constraints: list[str] = []
    tasks: list[str] = []
    warnings: list[str] = []

    for heading, body in sections:
        category = _category_for_heading(heading)
        if category is None:
            continue
        bullets = _bullet_items(body)
        if not bullets and body.strip():
            bullets = [_clean(body)]
        for item in bullets:
            refs = _evidence_refs_from_item(item)
            evidence_refs.extend(refs)
            finding = DeepResearchFinding(
                id=f"dr-{uuid.uuid4().hex[:10]}",
                category=category,
                title=_title_from_item(item),
                summary=item,
                severity="high" if category == "warning" else "medium",
                suggested_action=_suggested_action(category, item),
                evidence=refs,
            )
            findings.append(finding)
            if category == "differentiator":
                differentiators.append(item)
            elif category == "claim_constraint":
                constraints.append(item)
            elif category in {"evidence_gap", "completion_task"}:
                tasks.append(item)
            elif category == "warning":
                warnings.append(item)

    ledger = [_ledger_entry(ref, index) for index, ref in enumerate(_dedupe_refs(evidence_refs), start=1)]
    if not findings and not ledger:
        return DeepResearchPacket(
            status="partial",
            project_id=project_id,
            warnings=[f"DeepResearch Markdown was not recognized: {source_label or 'inline markdown'}"],
            generation_logs=["deep_research_intake: no structured sections recognized"],
        )

    return DeepResearchPacket(
        status="completed" if ledger or findings else "partial",
        project_id=project_id,
        queries_run=[],
        differentiators=differentiators,
        claim_drafting_constraints=constraints,
        suggested_completion_tasks=tasks,
        warnings=warnings,
        evidence_ledger=ledger,
        findings=findings,
        provider_chain=["deep_research_markdown"],
        generation_logs=[f"deep_research_intake: parsed {len(findings)} findings from {source_label or 'markdown'}"],
        internal_only=True,
    )


def packet_prior_art_hits(packet: DeepResearchPacket) -> list[PriorArtHit]:
    hits: list[PriorArtHit] = []
    for entry in packet.evidence_ledger:
        url = str(entry.get("url") or "")
        title = str(entry.get("title") or entry.get("publication_number") or "DeepResearch prior art")
        if not url and not entry.get("publication_number"):
            continue
        hits.append(
            PriorArtHit(
                id=str(entry.get("evidence_id") or uuid.uuid4().hex),
                source="DeepResearch Markdown",
                query=str(entry.get("matched_query") or ""),
                title=title,
                publication_number=entry.get("publication_number") or None,
                url=url,
                abstract=str(entry.get("snippet") or "") or None,
                relevance_summary=str(entry.get("snippet") or ""),
            )
        )
    return hits


def _split_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current_heading = ""
    current_lines: list[str] = []
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            if current_heading or current_lines:
                sections.append((current_heading, current_lines))
            current_heading = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_heading or current_lines:
        sections.append((current_heading, current_lines))
    return [(heading, "\n".join(lines).strip()) for heading, lines in sections]


def _category_for_heading(heading: str) -> str | None:
    lowered = heading.lower()
    for keywords, category in SECTION_CATEGORY_BY_KEYWORD:
        if any(keyword.lower() in lowered for keyword in keywords):
            return category
    return None


def _bullet_items(body: str) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    for line in body.splitlines():
        if re.match(r"^\s*(?:[-*+]|\d+[.、．])\s+", line):
            if current:
                items.append(_clean(" ".join(current)))
            current = [re.sub(r"^\s*(?:[-*+]|\d+[.、．])\s+", "", line).strip()]
        elif current and line.strip():
            current.append(line.strip())
    if current:
        items.append(_clean(" ".join(current)))
    return [item for item in items if item]


def _evidence_refs_from_item(item: str) -> list[DeepResearchEvidenceRef]:
    publication = _publication_number(item)
    url = _url(item)
    if not publication and not url:
        return []
    return [
        DeepResearchEvidenceRef(
            source="DeepResearch Markdown",
            title=_title_from_item(item),
            publication_number=publication,
            url=url,
            relevance=item,
        )
    ]


def _publication_number(text: str) -> str | None:
    match = PUBLICATION_RE.search(text)
    return re.sub(r"\s+", "", match.group(1)).upper() if match else None


def _url(text: str) -> str:
    match = URL_RE.search(text)
    return match.group(0).rstrip("，。；;") if match else ""


def _title_from_item(item: str) -> str:
    stripped = re.sub(URL_RE, "", item)
    stripped = re.sub(PUBLICATION_RE, "", stripped)
    stripped = re.sub(r"摘要[:：].*$", "", stripped).strip(" -：:")
    return _clean(stripped)[:80] or "DeepResearch finding"


def _suggested_action(category: str, item: str) -> str:
    actions = {
        "prior_art_cluster": "用于现有技术对比，写入内部证据台账。",
        "differentiator": "优先映射到权利要求区别特征和说明书实施例。",
        "claim_constraint": "用于权利要求策略和保护范围约束。",
        "evidence_gap": "提交前补充材料、实验、实施例或工程样例。",
        "warning": "作为内部风险，不进入正式提交稿。",
        "completion_task": "转为初稿完善任务。",
    }
    return actions.get(category, item[:120])


def _dedupe_refs(refs: list[DeepResearchEvidenceRef]) -> list[DeepResearchEvidenceRef]:
    seen: set[str] = set()
    out: list[DeepResearchEvidenceRef] = []
    for ref in refs:
        key = (ref.publication_number or ref.url or ref.title).upper()
        if key in seen:
            continue
        seen.add(key)
        out.append(ref)
    return out


def _ledger_entry(ref: DeepResearchEvidenceRef, index: int) -> dict[str, Any]:
    return {
        "evidence_id": f"DR{index:03d}",
        "provider": "deep_research_markdown",
        "source": ref.source or "DeepResearch Markdown",
        "title": ref.title,
        "url": ref.url,
        "publication_number": ref.publication_number,
        "snippet": ref.relevance,
        "matched_query": ref.query,
        "confidence": 0.75 if ref.url or ref.publication_number else 0.45,
        "citable": bool(ref.url or ref.publication_number),
    }


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
