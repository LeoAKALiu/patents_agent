# Patent Skill Borrowing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Embed selected process discipline from `handsomestWei/patent-disclosure-skill` into PatentAgent's existing workflow without adding a new flow or Office conversion scope.

**Architecture:** Add five bounded backend-first enhancements: DeepResearch Markdown intake, stricter prior-art discipline, clean disclosure plus internal sidecar exports, revision ledger records, and draft audit rules. Each enhancement reuses existing models and pipeline surfaces instead of creating a parallel skill runtime.

**Tech Stack:** Python 3, FastAPI, Pydantic, SQLiteStore, pytest, React/TypeScript light API type updates.

## Global Constraints

- Existing guided-flow step count and order must not change.
- Do not add `.docx` or `.pptx` to Markdown conversion in this phase.
- DeepResearch intake targets Markdown documents only.
- Do not introduce an external skill runtime or forked prompt-pack loader.
- Official compile and post-draft review gates must remain mandatory for official export.
- Internal evidence, source ledgers, generation logs, self-checks, and revision records must not enter official filing text.
- Existing unrelated dirty files in this worktree must not be reverted or included unless a task explicitly edits them.

---

## File Structure

- Create `backend/app/research/deep_research_intake.py`: deterministic parser for Markdown DeepResearch documents and conversion helpers to `DeepResearchPacket` / `PriorArtHit`.
- Modify `backend/app/evidence_binding.py`: add parsed DeepResearch packet evidence as internal evidence bindings.
- Modify `backend/app/disclosure/generator.py`: append DeepResearch Markdown intake stage results and pass structured evidence context into existing prompts.
- Modify `backend/app/disclosure/prior_art.py`: normalize search terms, enforce one semantic chunk per provider call, dedupe consistently, and surface URL/abstract warnings.
- Modify `backend/app/disclosure/exporter.py`: split clean disclosure markdown/docx from internal sidecar markdown.
- Modify `backend/app/main.py`: expose disclosure sidecar endpoint and revision ledger API; record ledgers when repair/cleanup operations mutate drafts.
- Modify `backend/app/schemas.py`: add `RevisionLedgerRecord` and any minimal request/response model needed for API output.
- Modify `backend/app/storage.py`: add `revision_ledger_records` table plus create/list methods.
- Create `backend/app/revision_ledger.py`: hash and record helpers for revision events.
- Create `backend/app/draft_audit_rules.py`: deterministic quality checks for formulas, Mermaid, URLs, and metadata leakage.
- Modify `backend/app/draft_completion.py`: merge audit rule findings into existing `DraftCompletionRun` issues.
- Modify `frontend/src/api.ts`: add sidecar URL and revision ledger types/functions.
- Test files: create or extend `tests/test_deep_research_intake.py`, `tests/test_deep_research_intake_integration.py`, `tests/test_disclosure_prior_art.py`, `tests/test_disclosure_exporter.py`, `tests/test_revision_ledger.py`, and `tests/test_draft_audit_rules.py`.

---

### Task 1: DeepResearch Markdown Parser

**Files:**
- Create: `backend/app/research/deep_research_intake.py`
- Create: `tests/test_deep_research_intake.py`

**Interfaces:**
- Produces: `is_deep_research_markdown_material(file_name: str, text: str) -> bool`
- Produces: `parse_deep_research_markdown(project_id: str, text: str, *, source_label: str = "") -> DeepResearchPacket`
- Produces: `parse_deep_research_materials(materials: Iterable[ProjectMaterial]) -> list[DeepResearchPacket]`
- Produces: `packet_prior_art_hits(packet: DeepResearchPacket) -> list[PriorArtHit]`

- [ ] **Step 1: Write parser tests**

```python
# tests/test_deep_research_intake.py
from backend.app.research.deep_research_intake import (
    is_deep_research_markdown_material,
    packet_prior_art_hits,
    parse_deep_research_markdown,
)
from backend.app.schemas import ProjectMaterial
from backend.app.research.deep_research_intake import parse_deep_research_materials


DEEP_RESEARCH_MD = """
# DeepResearch: 图像缺陷识别

## 现有技术
- CN123456789A 一种图像缺陷检测方法 https://patents.google.com/patent/CN123456789A
  摘要：公开了基于神经网络的图像缺陷检测，但未涉及实时闭环反馈。

## 差异点
- 本方案将检测结果实时回写至采集策略，形成闭环反馈。

## 权利要求约束
- 独立权利要求需要限定闭环反馈的数据流，避免纯功能性概括。

## 证据缺口
- 需要补充闭环反馈降低误检率的工程样例。

## 风险
- 现有技术可能组合通用神经网络检测和反馈控制。
"""


def test_is_deep_research_markdown_material_detects_markdown_report() -> None:
    assert is_deep_research_markdown_material("deepresearch.md", DEEP_RESEARCH_MD)
    assert is_deep_research_markdown_material("research.markdown", DEEP_RESEARCH_MD)
    assert not is_deep_research_markdown_material("notes.txt", DEEP_RESEARCH_MD)
    assert not is_deep_research_markdown_material("notes.md", "普通会议纪要")


def test_parse_deep_research_markdown_builds_internal_packet() -> None:
    packet = parse_deep_research_markdown("project-1", DEEP_RESEARCH_MD, source_label="deepresearch.md")

    assert packet.status == "completed"
    assert packet.project_id == "project-1"
    assert packet.internal_only is True
    assert packet.evidence_ledger
    assert packet.evidence_ledger[0]["publication_number"] == "CN123456789A"
    assert packet.evidence_ledger[0]["url"] == "https://patents.google.com/patent/CN123456789A"
    assert "实时回写" in packet.differentiators[0]
    assert "闭环反馈的数据流" in packet.claim_drafting_constraints[0]
    assert "工程样例" in packet.suggested_completion_tasks[0]
    assert packet.findings
    assert {finding.category for finding in packet.findings} >= {
        "prior_art_cluster",
        "differentiator",
        "claim_constraint",
        "evidence_gap",
        "warning",
    }


def test_packet_prior_art_hits_converts_ledger_entries() -> None:
    packet = parse_deep_research_markdown("project-1", DEEP_RESEARCH_MD, source_label="deepresearch.md")

    hits = packet_prior_art_hits(packet)

    assert len(hits) == 1
    assert hits[0].source == "DeepResearch Markdown"
    assert hits[0].publication_number == "CN123456789A"
    assert hits[0].abstract and "实时闭环反馈" in hits[0].abstract


def test_parse_deep_research_markdown_handles_unrecognized_markdown() -> None:
    packet = parse_deep_research_markdown("project-1", "# 普通文档\n\n没有研究结构。", source_label="plain.md")

    assert packet.status == "partial"
    assert packet.warnings
    assert packet.evidence_ledger == []
    assert packet.findings == []


def test_parse_deep_research_materials_filters_markdown_materials() -> None:
    materials = [
        ProjectMaterial(
            id="m1",
            project_id="project-1",
            file_name="deepresearch.md",
            path="data/deepresearch.md",
            file_type="md",
            text=DEEP_RESEARCH_MD,
            status="processed",
        ),
        ProjectMaterial(
            id="m2",
            project_id="project-1",
            file_name="plain.md",
            path="data/plain.md",
            file_type="md",
            text="普通材料",
            status="processed",
        ),
    ]

    packets = parse_deep_research_materials(materials)

    assert len(packets) == 1
    assert packets[0].project_id == "project-1"
```

- [ ] **Step 2: Run parser tests and verify failure**

Run: `pytest tests/test_deep_research_intake.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.research.deep_research_intake'`.

- [ ] **Step 3: Implement parser**

Create `backend/app/research/deep_research_intake.py` with these public functions and deterministic helpers:

```python
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
            refs = _evidence_refs_from_item(item, source_label=source_label)
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


def _evidence_refs_from_item(item: str, *, source_label: str) -> list[DeepResearchEvidenceRef]:
    publication = _publication_number(item)
    url = _url(item)
    if not publication and not url:
        return []
    return [
        DeepResearchEvidenceRef(
            source=source_label or "DeepResearch Markdown",
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
```

- [ ] **Step 4: Run parser tests**

Run: `pytest tests/test_deep_research_intake.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/research/deep_research_intake.py tests/test_deep_research_intake.py
git commit -m "feat: parse deepresearch markdown materials"
```

---

### Task 2: Wire DeepResearch Intake Into Evidence And Disclosure Context

**Files:**
- Modify: `backend/app/evidence_binding.py`
- Modify: `backend/app/disclosure/generator.py`
- Test: `tests/test_deep_research_intake_integration.py`

**Interfaces:**
- Consumes: `parse_deep_research_materials(materials) -> list[DeepResearchPacket]`
- Consumes: `packet_prior_art_hits(packet) -> list[PriorArtHit]`
- Produces: disclosure stage result with `phase == "deep_research_material_intake"`
- Produces: prior-art `EvidenceBinding` entries with `source_type == EvidenceBindingSourceType.PRIOR_ART`

- [ ] **Step 1: Write integration tests**

```python
# tests/test_deep_research_intake_integration.py
from backend.app.disclosure.generator import DisclosureGenerator
from backend.app.disclosure.prior_art import StaticPriorArtProvider
from backend.app.evidence_binding import build_evidence_bindings
from backend.app.llm import FakeLLMClient
from backend.app.schemas import ProjectMaterial, ProjectRecord


DEEP_RESEARCH_MD = """
# DeepResearch

## 现有技术
- CN123456789A 一种图像缺陷检测方法 https://patents.google.com/patent/CN123456789A
  摘要：公开了基于神经网络的图像缺陷检测，但未涉及实时闭环反馈。

## 差异点
- 本方案将检测结果实时回写至采集策略，形成闭环反馈。
"""


def _responses() -> dict[str, str]:
    return {
        "disclosure_scan": '{"summary":"图像缺陷识别","materials_summary":"材料覆盖","technical_keywords":["图像"],"implementation_gaps":[]}',
        "patent_points": '{"candidates":[{"id":"p1","title":"图像缺陷识别方法","technical_problem":"效率低","innovation":"闭环反馈","technical_solution":"采集并检测后实时回写策略","beneficial_effects":["提高效率"],"protection_focus":["方法","系统"],"grantability_score":0.8,"rationale":"完整"}],"selected_candidate_id":"p1"}',
        "prior_art_terms": '["图像 缺陷 神经网络"]',
        "prior_art_relevance": '{"prior_art_differences":"区别在实时反馈。","hits":[],"claim_charts":[]}',
        "disclosure_body": "# 技术交底书",
        "disclosure_mermaid": "flowchart TD\\nA[采集] --> B[反馈]",
        "disclosure_image_prompt": "黑白线稿。",
        "disclosure_self_check": "[]",
    }


def test_deepresearch_material_adds_disclosure_stage_context() -> None:
    project = ProjectRecord(id="p1", name="图像缺陷", draft_text="一种图像缺陷识别方法。")
    material = ProjectMaterial(
        id="m1",
        project_id="p1",
        file_name="deepresearch.md",
        path="data/deepresearch.md",
        file_type="md",
        text=DEEP_RESEARCH_MD,
        status="processed",
    )
    llm = FakeLLMClient(_responses())
    generator = DisclosureGenerator(llm, StaticPriorArtProvider())

    package, stages, warnings = generator.generate(
        project=project,
        materials=[material],
        context_chunks=[],
        max_prior_art_results=0,
    )

    assert any(stage["phase"] == "deep_research_material_intake" for stage in stages)
    assert any("deep_research_intake" in log for log in package.generation_logs)
    body_call = next(call for call in llm.calls if call.stage == "disclosure_body")
    assert "CN123456789A" in body_call.user_prompt
    assert "实时闭环反馈" in body_call.user_prompt
    assert warnings == []


def test_deepresearch_material_becomes_prior_art_evidence_binding() -> None:
    project = ProjectRecord(id="p1", name="图像缺陷", draft_text="一种图像缺陷识别方法。")
    material = ProjectMaterial(
        id="m1",
        project_id="p1",
        file_name="deepresearch.md",
        path="data/deepresearch.md",
        file_type="md",
        text=DEEP_RESEARCH_MD,
        status="processed",
    )

    bindings = build_evidence_bindings(project, materials=[material], disclosures=[], patent_points=[])

    prior_art_bindings = [binding for binding in bindings if binding.source_type == "prior_art"]
    assert prior_art_bindings
    assert prior_art_bindings[0].source_id == "CN123456789A"
    assert prior_art_bindings[0].metadata["url"] == "https://patents.google.com/patent/CN123456789A"
```

- [ ] **Step 2: Run integration tests and verify failure**

Run: `pytest tests/test_deep_research_intake_integration.py -v`

Expected: FAIL because no disclosure stage or binding integration exists.

- [ ] **Step 3: Add DeepResearch packet binding support**

In `backend/app/evidence_binding.py`:

- import `parse_deep_research_materials`;
- add `builder.add_deep_research_packet(packet)` after normal material binding;
- implement `_binding_from_deep_research_entry(entry)`.

The binding must be internal-only and citable when the parsed entry has a URL or publication number.

- [ ] **Step 4: Add disclosure context support**

In `backend/app/disclosure/generator.py`:

- import `parse_deep_research_materials` and `packet_prior_art_hits`;
- parse packets immediately after `material_context = _format_materials(project, materials)`;
- append a `deep_research_material_intake` stage before `project_scan`;
- add formatted packet context to `_points_prompt`, `_terms_prompt`, `_relevance_prompt`, and `_body_prompt` input by extending the existing material/strategic context strings;
- append packet prior-art hits to provider hits before relevance enrichment, then dedupe through the existing prior-art dedupe path from Task 3 when available.

The stage payload shape must be:

```python
{
    "phase": "deep_research_material_intake",
    "payload": {
        "packets": [packet.model_dump(mode="json") for packet in deep_research_packets],
        "prior_art_hit_count": len(markdown_hits),
        "warnings": [warning for packet in deep_research_packets for warning in packet.warnings],
    },
}
```

- [ ] **Step 5: Run integration tests**

Run: `pytest tests/test_deep_research_intake_integration.py -v`

Expected: PASS.

- [ ] **Step 6: Run nearby regression tests**

Run: `pytest tests/test_deep_research.py tests/test_research_evidence.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/evidence_binding.py backend/app/disclosure/generator.py tests/test_deep_research_intake_integration.py
git commit -m "feat: use deepresearch markdown as internal evidence"
```

---

### Task 3: Prior-Art Search Discipline

**Files:**
- Modify: `backend/app/disclosure/prior_art.py`
- Modify: `backend/app/disclosure/generator.py`
- Test: `tests/test_disclosure_prior_art.py`

**Interfaces:**
- Produces: `normalize_search_terms(terms: list[str], *, fallback_text: str = "", max_terms: int = 8) -> list[str]`
- Produces: `dedupe_prior_art_hits(hits: list[PriorArtHit]) -> list[PriorArtHit]`
- Produces: `prior_art_url_warnings(hits: list[PriorArtHit]) -> list[str]`

- [ ] **Step 1: Write prior-art discipline tests**

```python
# tests/test_disclosure_prior_art.py
from backend.app.disclosure.prior_art import (
    PublicPriorArtProvider,
    dedupe_prior_art_hits,
    normalize_search_terms,
    prior_art_url_warnings,
)
from backend.app.schemas import PriorArtHit


def _hit(hit_id: str, publication: str | None, url: str, title: str) -> PriorArtHit:
    return PriorArtHit(
        id=hit_id,
        source="Google Patents",
        query="图像 缺陷",
        title=title,
        publication_number=publication,
        url=url,
        abstract="摘要",
    )


def test_normalize_search_terms_splits_long_sentence_and_caps_to_eight() -> None:
    terms = normalize_search_terms(
        ["一种基于神经网络实时反馈的图像缺陷识别方法及系统"],
        fallback_text="图像缺陷 神经网络 实时反馈 闭环控制 检测策略 误检率 采集调度 权重更新 质量评估",
    )

    assert 2 <= len(terms) <= 8
    assert all(len(term) <= 24 for term in terms)
    assert "图像缺陷" in terms[0]


def test_dedupe_prior_art_hits_prefers_publication_number_then_url() -> None:
    hits = [
        _hit("h1", "CN123456789A", "https://patents.google.com/patent/CN123456789A", "标题A"),
        _hit("h2", "CN123456789A", "https://example.com/duplicate", "标题A重复"),
        _hit("h3", None, "https://patents.google.com/patent/US20240123456A1", "标题B"),
        _hit("h4", None, "https://patents.google.com/patent/US20240123456A1", "标题B重复"),
    ]

    deduped = dedupe_prior_art_hits(hits)

    assert [hit.id for hit in deduped] == ["h1", "h3"]


def test_prior_art_url_warnings_flags_missing_public_urls() -> None:
    warnings = prior_art_url_warnings([
        _hit("h1", "CN123456789A", "", "无 URL"),
        _hit("h2", None, "https://patents.google.com/patent/US20240123456A1", "有 URL"),
    ])

    assert warnings == ["prior_art missing public URL: CN123456789A 无 URL"]


def test_public_provider_calls_cnipa_once_per_normalized_term() -> None:
    class RecordingProvider(PublicPriorArtProvider):
        def __init__(self) -> None:
            super().__init__(cnipa_script=None)
            self.cnipa_terms: list[str] = []
            self.google_terms: list[str] = []

        def _search_cnipa(self, term: str, limit: int):
            self.cnipa_terms.append(term)
            return [], []

        def _search_google_patents(self, term: str, limit: int):
            self.google_terms.append(term)
            return [], []

    provider = RecordingProvider()

    provider.search(["图像缺陷 神经网络 实时反馈 闭环控制"], limit=4)

    assert len(provider.cnipa_terms) >= 2
    assert all(" " not in term.strip(" ") or len(term) <= 24 for term in provider.cnipa_terms)
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_disclosure_prior_art.py -v`

Expected: FAIL because helper functions do not exist.

- [ ] **Step 3: Implement helpers and provider integration**

In `backend/app/disclosure/prior_art.py`:

- rename private `_dedupe_hits` usages to call public `dedupe_prior_art_hits`;
- add `normalize_search_terms` and call it at the beginning of `PublicPriorArtProvider._search`;
- append `prior_art_url_warnings` results to provider warnings before returning;
- keep fallback Google Patents behavior intact.

Rules:

- trim whitespace;
- drop generic terms shorter than 2 CJK characters or less than 3 ASCII characters;
- split long CJK strings from fallback text into adjacent 2 to 4 token chunks;
- cap to `max_terms=8`;
- if normalization still yields one term, keep one term rather than inventing unrelated terms.

- [ ] **Step 4: Ensure relevance prompt receives abstracts**

In `backend/app/disclosure/generator.py`, update `_relevance_prompt` text to explicitly instruct:

```text
凡公开结果含 abstract，必须基于 abstract 概括方案要点、局限和区别，禁止仅凭标题判断。
```

Do not add another LLM stage.

- [ ] **Step 5: Run prior-art tests**

Run: `pytest tests/test_disclosure_prior_art.py tests/test_grantability.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/disclosure/prior_art.py backend/app/disclosure/generator.py tests/test_disclosure_prior_art.py
git commit -m "feat: harden prior art search discipline"
```

---

### Task 4: Split Disclosure Artifacts Into Clean Disclosure And Internal Sidecar

**Files:**
- Modify: `backend/app/disclosure/exporter.py`
- Modify: `backend/app/main.py`
- Modify: `frontend/src/api.ts`
- Test: `tests/test_disclosure_exporter.py`

**Interfaces:**
- Produces: `clean_disclosure_to_markdown(package: DisclosurePackage) -> str`
- Produces: `disclosure_sidecar_to_markdown(package: DisclosurePackage) -> str`
- Produces: `/api/projects/{project_id}/disclosures/{run_id}/sidecar.md`
- Existing `/export.md` and `/export.docx` become clean attorney-facing exports.

- [ ] **Step 1: Write artifact split tests**

```python
# tests/test_disclosure_exporter.py
from backend.app.disclosure.exporter import (
    clean_disclosure_to_markdown,
    disclosure_sidecar_to_markdown,
)
from backend.app.schemas import DisclosurePackage, DisclosureSelfCheckFinding, PatentPointCandidate, PriorArtHit


def _package() -> DisclosurePackage:
    return DisclosurePackage(
        title="一种图像缺陷识别方法",
        summary="摘要",
        materials_summary="材料覆盖",
        candidates=[
            PatentPointCandidate(
                id="p1",
                title="闭环反馈",
                technical_problem="效率低",
                innovation="实时反馈",
                technical_solution="检测后回写采集策略",
                protection_focus=["方法"],
            )
        ],
        selected_candidate_id="p1",
        prior_art_hits=[
            PriorArtHit(
                id="h1",
                source="Google Patents",
                query="图像 缺陷",
                title="一种图像缺陷检测方法",
                publication_number="CN123456789A",
                url="https://patents.google.com/patent/CN123456789A",
                abstract="公开了缺陷检测。",
                differentiators=["缺少闭环反馈"],
            )
        ],
        prior_art_differences="现有技术缺少闭环反馈。",
        body_markdown="# 技术交底书正文\\n\\n## 一、背景\\n正文。",
        mermaid="flowchart TD\\nA-->B",
        image_prompt="黑白线稿",
        self_check_findings=[
            DisclosureSelfCheckFinding(category="url", severity="low", message="URL 存在", suggestion="无")
        ],
        generation_logs=["project_scan: summarized draft", "warning: internal"],
        research_ledger={"entries": [{"provider": "google_patents"}]},
        provider_diagnostics=[{"phase": "post_flight"}],
        research_confidence="medium",
    )


def test_clean_disclosure_excludes_internal_sections() -> None:
    markdown = clean_disclosure_to_markdown(_package())

    assert "技术交底书正文" in markdown
    assert "https://patents.google.com/patent/CN123456789A" in markdown
    assert "Claim Chart" not in markdown
    assert "检索来源台账" not in markdown
    assert "自检结果" not in markdown
    assert "生成日志" not in markdown
    assert "provider_diagnostics" not in markdown
    assert "evidence_id" not in markdown


def test_sidecar_contains_internal_sections() -> None:
    markdown = disclosure_sidecar_to_markdown(_package())

    assert "Claim Chart" in markdown
    assert "检索来源台账" in markdown
    assert "自检结果" in markdown
    assert "生成日志" in markdown
    assert "Google Patents" in markdown
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_disclosure_exporter.py -v`

Expected: FAIL because split functions do not exist.

- [ ] **Step 3: Implement split exporter functions**

In `backend/app/disclosure/exporter.py`:

- make `clean_disclosure_to_markdown` return `package.body_markdown` plus a compact public prior-art URL appendix if the body lacks URLs;
- make `disclosure_sidecar_to_markdown` contain current `disclosure_to_markdown` internal sections;
- keep `disclosure_to_markdown` as an alias to `disclosure_sidecar_to_markdown` only if callers still need backward compatibility;
- update `export_disclosure_docx` to use clean text sections only;
- update `write_disclosure_artifacts` to write:
  - `disclosure.md` as clean;
  - `disclosure-sidecar.md` as internal;
  - `diagram.mmd`;
  - `image-prompt.md`;
  - `disclosure.docx` as clean docx.

- [ ] **Step 4: Add sidecar API endpoint**

In `backend/app/main.py`:

- import `clean_disclosure_to_markdown` and `disclosure_sidecar_to_markdown`;
- update `/export.md` to return `clean_disclosure_to_markdown(package)`;
- add:

```python
@app.get("/api/projects/{project_id}/disclosures/{run_id}/sidecar.md")
def export_disclosure_run_sidecar(project_id: str, run_id: str) -> PlainTextResponse:
    project = _require_project(store, project_id)
    run = _require_disclosure_run(store, project_id, run_id)
    package = _require_disclosure_package(run)
    return PlainTextResponse(
        disclosure_sidecar_to_markdown(package),
        media_type="text/markdown; charset=utf-8",
        headers=_content_disposition_header(f"{project.name}-交底书内部侧车.md"),
    )
```

- [ ] **Step 5: Add frontend URL helper**

In `frontend/src/api.ts`, extend `disclosureExportUrl` to accept `"sidecar"` and return:

```ts
`/api/projects/${projectId}/disclosures/${runId}/sidecar.md`
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_disclosure_exporter.py tests/test_deep_research.py -v`

Expected: PASS.

Run: `npm --prefix frontend run build`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/disclosure/exporter.py backend/app/main.py frontend/src/api.ts tests/test_disclosure_exporter.py
git commit -m "feat: split disclosure exports from sidecar reports"
```

---

### Task 5: Revision Ledger Persistence

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/storage.py`
- Create: `backend/app/revision_ledger.py`
- Test: `tests/test_revision_ledger.py`

**Interfaces:**
- Produces: `RevisionLedgerRecord`
- Produces: `create_revision_record(project_id: str, baseline_package: DraftPackage, updated_package: DraftPackage, *, revision_kind: str, user_intent_summary: str, affected_sections: list[str], prior_art_changed: bool = False, protection_scope_changed: bool = False, artifact_refs: list[str] | None = None) -> RevisionLedgerRecord`
- Produces: `SQLiteStore.create_revision_ledger_record(record: RevisionLedgerRecord) -> RevisionLedgerRecord`
- Produces: `SQLiteStore.list_revision_ledger_records(project_id: str) -> list[RevisionLedgerRecord]`

- [ ] **Step 1: Write storage tests**

```python
# tests/test_revision_ledger.py
from pathlib import Path

from backend.app.revision_ledger import create_revision_record
from backend.app.schemas import DraftPackage
from backend.app.storage import SQLiteStore


def _package(description: str) -> DraftPackage:
    return DraftPackage(
        title="一种方法",
        abstract="摘要",
        claims="1. 一种方法。",
        description=description,
        drawing_description="图1。",
        mermaid="flowchart TD\\nA-->B",
        image_prompt="黑白线稿",
    )


def test_revision_ledger_record_hashes_and_sections() -> None:
    before = _package("旧说明书")
    after = _package("新说明书")

    record = create_revision_record(
        project_id="p1",
        baseline_package=before,
        updated_package=after,
        revision_kind="correction",
        user_intent_summary="修正说明书事实",
        affected_sections=["description"],
        prior_art_changed=False,
        protection_scope_changed=False,
        artifact_refs=["draft-package"],
    )

    assert record.project_id == "p1"
    assert record.baseline_artifact_hash
    assert record.new_artifact_hash
    assert record.baseline_artifact_hash != record.new_artifact_hash
    assert record.affected_sections == ["description"]
    assert record.revision_kind == "correction"


def test_sqlite_store_persists_revision_ledger_records(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "patents.sqlite3")
    before = _package("旧说明书")
    after = _package("新说明书")
    first = create_revision_record(
        project_id="p1",
        baseline_package=before,
        updated_package=after,
        revision_kind="material_merge",
        user_intent_summary="合并 DeepResearch 材料",
        affected_sections=["description", "claims"],
        prior_art_changed=True,
        protection_scope_changed=True,
        artifact_refs=["run:abc"],
    )
    second = create_revision_record(
        project_id="p1",
        baseline_package=after,
        updated_package=_package("第三版说明书"),
        revision_kind="protection_focus",
        user_intent_summary="强化第五章保护点",
        affected_sections=["claims"],
        protection_scope_changed=True,
    )

    store.create_revision_ledger_record(first)
    store.create_revision_ledger_record(second)
    records = store.list_revision_ledger_records("p1")

    assert [record.id for record in records] == [second.id, first.id]
    assert records[0].revision_kind == "protection_focus"
    assert records[1].prior_art_changed is True
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_revision_ledger.py -v`

Expected: FAIL because schema, helper, and storage methods do not exist.

- [ ] **Step 3: Add schema**

In `backend/app/schemas.py`, add:

```python
class RevisionLedgerRecord(BaseModel):
    id: str
    project_id: str
    revision_kind: str = Field(pattern="^(material_merge|correction|protection_focus|post_draft_repair|official_cleanup|completion_patch)$")
    baseline_artifact_hash: str
    new_artifact_hash: str
    user_intent_summary: str = ""
    affected_sections: list[str] = Field(default_factory=list)
    prior_art_changed: bool = False
    protection_scope_changed: bool = False
    artifact_refs: list[str] = Field(default_factory=list)
    created_at: str = ""
```

- [ ] **Step 4: Add helper**

Create `backend/app/revision_ledger.py`:

```python
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from backend.app.schemas import DraftPackage, RevisionLedgerRecord


def draft_package_hash(package: DraftPackage) -> str:
    return hashlib.sha256(package.model_dump_json().encode("utf-8")).hexdigest()


def create_revision_record(
    *,
    project_id: str,
    baseline_package: DraftPackage,
    updated_package: DraftPackage,
    revision_kind: str,
    user_intent_summary: str,
    affected_sections: list[str],
    prior_art_changed: bool = False,
    protection_scope_changed: bool = False,
    artifact_refs: list[str] | None = None,
) -> RevisionLedgerRecord:
    return RevisionLedgerRecord(
        id=uuid.uuid4().hex,
        project_id=project_id,
        revision_kind=revision_kind,
        baseline_artifact_hash=draft_package_hash(baseline_package),
        new_artifact_hash=draft_package_hash(updated_package),
        user_intent_summary=user_intent_summary,
        affected_sections=list(dict.fromkeys(affected_sections)),
        prior_art_changed=prior_art_changed,
        protection_scope_changed=protection_scope_changed,
        artifact_refs=list(artifact_refs or []),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
```

- [ ] **Step 5: Add SQLite table and methods**

In `backend/app/storage.py`:

- import `RevisionLedgerRecord`;
- add `revision_ledger_records` table in `_post_init`;
- add `_ensure_column` calls only if later migration needs them;
- add methods:

```python
def create_revision_ledger_record(self, record: RevisionLedgerRecord) -> RevisionLedgerRecord:
    with self.connection:
        self.connection.execute(
            """
            insert into revision_ledger_records(
                id, project_id, record_json, created_at
            ) values (?, ?, ?, ?)
            """,
            (
                record.id,
                record.project_id,
                json.dumps(record.model_dump(mode="json"), ensure_ascii=False),
                record.created_at,
            ),
        )
    return record


def list_revision_ledger_records(self, project_id: str) -> list[RevisionLedgerRecord]:
    rows = self.connection.execute(
        "select record_json from revision_ledger_records where project_id = ? order by created_at desc, rowid desc",
        (project_id,),
    ).fetchall()
    return [RevisionLedgerRecord.model_validate(json.loads(row["record_json"])) for row in rows]
```

Table DDL:

```sql
create table if not exists revision_ledger_records (
    id text primary key,
    project_id text not null,
    record_json text not null,
    created_at text not null default current_timestamp,
    foreign key(project_id) references projects(id)
);
```

- [ ] **Step 6: Run storage tests**

Run: `pytest tests/test_revision_ledger.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas.py backend/app/storage.py backend/app/revision_ledger.py tests/test_revision_ledger.py
git commit -m "feat: persist draft revision ledger records"
```

---

### Task 6: Record Revision Ledger Events And Expose API

**Files:**
- Modify: `backend/app/main.py`
- Modify: `frontend/src/api.ts`
- Test: `tests/test_revision_ledger_api.py`

**Interfaces:**
- Consumes: `SQLiteStore.create_revision_ledger_record`
- Produces: `GET /api/projects/{project_id}/revision-ledger`
- Produces: revision records for post-draft safe patches, single-issue repair patches, official cleanup, and accepted completion patches.

- [ ] **Step 1: Write API tests**

```python
# tests/test_revision_ledger_api.py
from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app, _repair_patch_store
from backend.app.official_compile import source_draft_hash
from backend.app.schemas import DraftPackage, DraftRepairPatch, PostDraftReviewRun


def _package() -> DraftPackage:
    return DraftPackage(
        title="一种方法",
        abstract="摘要",
        claims="1. 一种方法，其特征在于，包括旧特征。",
        description="说明书包含旧特征。",
        drawing_description="图1。",
        mermaid="flowchart TD\\nA-->B",
        image_prompt="黑白线稿",
    )


def test_revision_ledger_api_lists_records_after_safe_patch(tmp_path) -> None:
    app = create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False)
    client = TestClient(app)
    project = client.post("/api/projects", json={"name": "测试", "draft_text": "一种方法。"}).json()
    project_id = project["id"]
    package = _package()
    app.state.store.update_project_package(project_id, package)

    run = PostDraftReviewRun(
        id="review-1",
        project_id=project_id,
        status="completed",
        providers=["fake"],
        prompt_pack_version="test",
        draft_package_hash=source_draft_hash(package),
        export_allowed=False,
        blocking_issues=[],
        contamination_hits=[],
        logs=[],
    )
    app.state.store.create_post_draft_review_run(run)

    response = client.get(f"/api/projects/{project_id}/revision-ledger")

    assert response.status_code == 200
    assert response.json() == []


def test_revision_ledger_records_single_issue_repair_patch(tmp_path) -> None:
    _repair_patch_store().clear()
    app = create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False)
    client = TestClient(app)
    project = client.post("/api/projects", json={"name": "测试", "draft_text": "一种方法。"}).json()
    project_id = project["id"]
    package = _package(title="一种重复重复方法")
    app.state.store.update_project_package(project_id, package)
    draft_hash = source_draft_hash(package)
    run = PostDraftReviewRun(
        id="review-1",
        project_id=project_id,
        status="completed",
        providers=["fake"],
        prompt_pack_version="test",
        draft_package_hash=draft_hash,
        export_allowed=False,
        blocking_issues=["标题存在重复词汇"],
        contamination_hits=[],
        logs=[],
    )
    app.state.store.create_post_draft_review_run(run)
    patch = DraftRepairPatch(
        id="patch-1",
        issue_id="issue-1",
        project_id=project_id,
        review_run_id=run.id,
        status="proposed",
        target_section="title",
        original="重复重复",
        patched="重复",
        diff_summary="删除重复词",
        risk_notes=[],
        draft_package_hash=draft_hash,
    )
    _repair_patch_store()[patch.id] = patch

    apply_response = client.post(
        f"/api/projects/{project_id}/post-draft-reviews/{run.id}/repair-patches/{patch.id}/apply"
    )
    assert apply_response.status_code == 200

    response = client.get(f"/api/projects/{project_id}/revision-ledger")
    assert response.status_code == 200
    records = response.json()
    assert len(records) == 1
    assert records[0]["revision_kind"] == "post_draft_repair"
    assert records[0]["baseline_artifact_hash"] == draft_hash
    assert records[0]["new_artifact_hash"] == apply_response.json()["current_draft_hash"]
    assert records[0]["affected_sections"] == ["title"]
```

- [ ] **Step 2: Run API tests and verify failure**

Run: `pytest tests/test_revision_ledger_api.py -v`

Expected: FAIL because endpoint does not exist.

- [ ] **Step 3: Add API endpoint**

In `backend/app/main.py`:

```python
@app.get("/api/projects/{project_id}/revision-ledger")
def list_revision_ledger(project_id: str) -> list[dict]:
    _require_project(store, project_id)
    return [record.model_dump(mode="json") for record in store.list_revision_ledger_records(project_id)]
```

- [ ] **Step 4: Record draft mutation events**

In `backend/app/main.py`, after each successful `store.update_project_package(...)` in these flows, create a record:

- single issue repair patch: `revision_kind="post_draft_repair"`;
- post-draft safe patches: `revision_kind="post_draft_repair"`;
- official compile cleanup: `revision_kind="official_cleanup"`;
- completion patch accept and accept-all: `revision_kind="completion_patch"`.

For affected sections, use existing section names from patch or changed-section detection. Use `source_draft_hash(before)` and `source_draft_hash(after)` through `create_revision_record`.

- [ ] **Step 5: Add frontend API types**

In `frontend/src/api.ts`:

```ts
export interface RevisionLedgerRecord {
  id: string;
  project_id: string;
  revision_kind: "material_merge" | "correction" | "protection_focus" | "post_draft_repair" | "official_cleanup" | "completion_patch";
  baseline_artifact_hash: string;
  new_artifact_hash: string;
  user_intent_summary: string;
  affected_sections: string[];
  prior_art_changed: boolean;
  protection_scope_changed: boolean;
  artifact_refs: string[];
  created_at: string;
}

export async function listRevisionLedger(projectId: string): Promise<RevisionLedgerRecord[]> {
  return request<RevisionLedgerRecord[]>(`/api/projects/${projectId}/revision-ledger`);
}
```

- [ ] **Step 6: Run API and TypeScript checks**

Run: `pytest tests/test_revision_ledger.py tests/test_revision_ledger_api.py tests/test_post_draft_review.py -v`

Expected: PASS.

Run: `npm --prefix frontend run build`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/main.py frontend/src/api.ts tests/test_revision_ledger_api.py
git commit -m "feat: record revision ledger events"
```

---

### Task 7: Draft Audit Rules

**Files:**
- Create: `backend/app/draft_audit_rules.py`
- Modify: `backend/app/draft_completion.py`
- Test: `tests/test_draft_audit_rules.py`

**Interfaces:**
- Produces: `audit_draft_package(package: DraftPackage, disclosures: list[DisclosureRun] | None = None) -> list[CompletionIssue]`
- Consumes: existing `CompletionIssue`
- Produces: new issues merged into `DraftCompletionRun.issues`

- [ ] **Step 1: Write audit tests**

```python
# tests/test_draft_audit_rules.py
from backend.app.draft_audit_rules import audit_draft_package
from backend.app.draft_completion import run_draft_completion
from backend.app.schemas import DraftPackage


def _package(description: str, mermaid: str = "flowchart TD\\nA-->B") -> DraftPackage:
    return DraftPackage(
        title="一种方法",
        abstract="摘要",
        claims="1. 一种方法，其特征在于，根据 b^{cpu} 计算权重。",
        description=description,
        drawing_description="图1。",
        mermaid=mermaid,
        image_prompt="黑白线稿",
    )


def test_audit_flags_superscript_resource_dimension() -> None:
    issues = audit_draft_package(_package("公式为 $b^{cpu}=1$。"))

    assert any(issue.category == "format_pollution" and "维度上标" in issue.message for issue in issues)


def test_audit_flags_missing_prior_art_url_in_description() -> None:
    description = "现有技术 CN123456789A 公开了相关方案，但未给出公开 URL。"

    issues = audit_draft_package(_package(description))

    assert any(issue.category == "prior_art_distinction_gap" and "公开 URL" in issue.message for issue in issues)


def test_audit_flags_internal_metadata_in_description() -> None:
    description = "本段包含 evidence_id: E001 和 generation_logs: project_scan。"

    issues = audit_draft_package(_package(description))

    assert any(issue.category == "format_pollution" and "内部元信息" in issue.message for issue in issues)


def test_audit_flags_missing_mermaid_when_prompt_mentions_diagram() -> None:
    package = _package("说明书引用系统框图。", mermaid="")

    issues = audit_draft_package(package)

    assert any(issue.target == "drawing" and "Mermaid" in issue.message for issue in issues)
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_draft_audit_rules.py -v`

Expected: FAIL because module does not exist.

- [ ] **Step 3: Implement audit module**

Create `backend/app/draft_audit_rules.py`:

```python
from __future__ import annotations

import re
import uuid

from backend.app.schemas import CompletionIssue, DisclosureRun, DraftPackage

RESOURCE_SUPERSCRIPT_RE = re.compile(r"\^\{?(?:cpu|mem|io|gpu|peak|latency|throughput)\}?", re.IGNORECASE)
PUBLICATION_RE = re.compile(r"\b(?:CN|WO|US|EP|JP|KR)\s?\d{5,}[A-Z]\d?\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://")
INTERNAL_METADATA_RE = re.compile(
    r"(evidence_id|evidence_refs|research_ledger|generation_logs|provider_diagnostics|self_check|自检结果|检索来源台账)",
    re.IGNORECASE,
)


def audit_draft_package(package: DraftPackage, disclosures: list[DisclosureRun] | None = None) -> list[CompletionIssue]:
    issues: list[CompletionIssue] = []
    combined_text = "\n".join([package.claims, package.description, package.drawing_description])
    if RESOURCE_SUPERSCRIPT_RE.search(combined_text):
        issues.append(_issue(
            category="format_pollution",
            severity="medium",
            target="description",
            message="公式或权利要求中存在资源维度上标写法，建议改为下标加正体维度名。",
            suggested_action="将 b^{cpu}、a^{mem} 等改为 b_{i,\\mathrm{cpu}}、a_{j,\\mathrm{mem}} 等形式，并同步符号表。",
        ))
    if _has_publication_without_url(package.description):
        issues.append(_issue(
            category="prior_art_distinction_gap",
            severity="medium",
            target="prior_art",
            message="说明书现有技术段出现公开号但缺少可核验公开 URL。",
            suggested_action="为每个现有技术条目补充 CNIPA 或 Google Patents 等公开链接。",
        ))
    if INTERNAL_METADATA_RE.search(combined_text):
        issues.append(_issue(
            category="format_pollution",
            severity="high",
            target="export",
            message="草稿包含内部元信息，不能进入正式稿或清洁交底书。",
            suggested_action="删除 evidence/source/log/self-check 等内部字段，保留在内部侧车报告。",
            blocks_submission=True,
        ))
    if _diagram_expected(package) and not package.mermaid.strip():
        issues.append(_issue(
            category="format_pollution",
            severity="low",
            target="drawing",
            message="草稿引用图示但缺少 Mermaid 图。",
            suggested_action="补充可渲染 Mermaid 系统框图或流程图。",
        ))
    return issues


def _has_publication_without_url(text: str) -> bool:
    return bool(PUBLICATION_RE.search(text)) and not URL_RE.search(text)


def _diagram_expected(package: DraftPackage) -> bool:
    text = "\n".join([package.description, package.drawing_description, package.image_prompt])
    return any(marker in text for marker in ("系统框图", "流程图", "图示", "图1", "附图"))


def _issue(
    *,
    category: str,
    severity: str,
    target: str,
    message: str,
    suggested_action: str,
    blocks_submission: bool = False,
) -> CompletionIssue:
    return CompletionIssue(
        id=f"i-audit-{uuid.uuid4().hex[:8]}",
        category=category,
        severity=severity,
        target=target,
        source_refs=["draft_audit_rules"],
        message=message,
        why_it_matters="该问题会影响交底书清洁度、说明书支撑或正式提交成熟度。",
        suggested_action=suggested_action,
        blocks_submission=blocks_submission,
    )
```

- [ ] **Step 4: Integrate into draft completion**

In `backend/app/draft_completion.py`:

- import `audit_draft_package`;
- after `_unverified_scheme_issues`, extend issues with `audit_draft_package(package, disclosures)`;
- keep `_dedupe_issues` after the extension.

- [ ] **Step 5: Add integration assertion**

Extend `tests/test_draft_audit_rules.py` with:

```python
def test_draft_completion_includes_audit_rule_issues() -> None:
    package = _package("说明书包含 evidence_id: E001。")

    run = run_draft_completion(
        project_id="p1",
        package=package,
        filing_reports=[],
        worksheets=[],
        patent_points=[],
        disclosures=[],
        materials=[],
        evidence_bindings=[],
    )

    assert any(issue.source_refs == ["draft_audit_rules"] for issue in run.issues)
```

- [ ] **Step 6: Run audit and completion tests**

Run: `pytest tests/test_draft_audit_rules.py tests/test_draft_completion.py tests/test_draft_completion_api.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/draft_audit_rules.py backend/app/draft_completion.py tests/test_draft_audit_rules.py
git commit -m "feat: add draft audit rules to completion checks"
```

---

### Task 8: Final Regression And Documentation Update

**Files:**
- Modify: `docs/project-design-overview.md`
- Optional modify: `README.md` only if it already documents DeepResearch/free research exports nearby

**Interfaces:**
- Consumes: all prior task commits.
- Produces: updated documentation and final regression evidence.

- [ ] **Step 1: Update documentation**

In `docs/project-design-overview.md`, update the relevant sections to mention:

- Markdown DeepResearch intake enriches internal evidence and prior-art structures;
- disclosure export now separates clean attorney-facing disclosure and internal sidecar;
- revision ledger records draft mutations;
- draft audit rules feed existing quality checks.

Do not claim Office conversion support.

- [ ] **Step 2: Run focused backend regression**

Run:

```bash
pytest \
  tests/test_deep_research_intake.py \
  tests/test_deep_research_intake_integration.py \
  tests/test_disclosure_prior_art.py \
  tests/test_disclosure_exporter.py \
  tests/test_revision_ledger.py \
  tests/test_revision_ledger_api.py \
  tests/test_draft_audit_rules.py \
  tests/test_deep_research.py \
  tests/test_grantability.py \
  tests/test_draft_completion.py \
  tests/test_official_compile.py \
  -v
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run: `npm --prefix frontend run build`

Expected: PASS.

- [ ] **Step 4: Check worktree diff**

Run: `git status --short --branch`

Expected: only files intentionally modified by this plan are dirty, plus any pre-existing unrelated files if they were present before execution.

- [ ] **Step 5: Commit docs and final polish**

```bash
git add docs/project-design-overview.md README.md
git commit -m "docs: document patent skill borrowing enhancements"
```

Skip `README.md` in the `git add` command if it was not changed.

---

## Self-Review

- Spec coverage: Every design module maps to at least one task. DeepResearch intake is Tasks 1-2, prior-art discipline is Task 3, artifact split is Task 4, revision ledger is Tasks 5-6, audit rules are Task 7, docs/regression are Task 8.
- Placeholder scan: No unfinished marker words or open-ended implementation placeholders remain. Each task names files, interfaces, commands, and expected results.
- Type consistency: Public function names introduced in earlier tasks are reused consistently by later tasks: `parse_deep_research_materials`, `packet_prior_art_hits`, `normalize_search_terms`, `dedupe_prior_art_hits`, `clean_disclosure_to_markdown`, `disclosure_sidecar_to_markdown`, `RevisionLedgerRecord`, and `audit_draft_package`.
- Scope check: The plan preserves the existing workflow, excludes Office conversion, and avoids a new skill runtime.
