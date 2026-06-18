from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path

from docx import Document

from backend.app.schemas import (
    DeliberationLogEntry,
    DraftPackage,
    OfficialCompileRun,
    OfficialDraftPackage,
    OfficialFigurePlanItem,
)


CROSS_PROJECT_TITLE = "基于边缘端动态推理的无人机飞行中任务调整方法"
REQUIRED_SECTIONS = ("abstract", "claims", "description", "drawing_description")
HARD_GATED_SECTIONS = ("title", *REQUIRED_SECTIONS)
RESIDUAL_INTERNAL_PATTERNS = (
    "support_gap",
    "support_gaps",
    "generation_logs",
    "image_prompt",
    "prompt",
    "diagram",
    "attorney_memo",
    "system_trace",
    "official_safe_patches",
    "好的，下面",
)
INTERNAL_FIELD_RE = re.compile(
    r"""^\s*["']?(image_prompt|prompt|diagram|generation_logs|attorney_memo|system_trace|official_safe_patches)["']?\s*[:：=]""",
    re.IGNORECASE,
)
EMPTY_OFFICIAL_FIELD_RE = re.compile(
    r"""^\s*["']?(title|abstract|claims|description|drawing_description)["']?\s*[:：=]\s*["']?\s*["']?\s*,?\s*$""",
    re.IGNORECASE,
)
JSON_WRAPPER_RE = re.compile(r"^[{}\[\],]+$")
CHINESE_LABEL_RE = re.compile(
    r"""^\s*["']?(撰写说明(?:与支撑不足提示)?|支撑不足提示)["']?\s*[:：]"""
)


def source_draft_hash(package: DraftPackage) -> str:
    return hashlib.sha256(package.model_dump_json().encode("utf-8")).hexdigest()


def official_package_hash(package: OfficialDraftPackage) -> str:
    canonical = package.model_copy(update={"official_package_hash": ""})
    return hashlib.sha256(canonical.model_dump_json().encode("utf-8")).hexdigest()


class OfficialDraftCompiler:
    def compile(self, project_id: str, package: DraftPackage) -> OfficialCompileRun:
        run_id = uuid.uuid4().hex
        now = _utc_now_iso()
        package_hash = source_draft_hash(package)
        contamination_removed: list[dict[str, str]] = []
        sidecar_notes: list[dict[str, str]] = []
        blocked_items: list[dict[str, str]] = []
        logs: list[DeliberationLogEntry] = [
            DeliberationLogEntry(
                level="info",
                phase="official_compile",
                message="official draft compile started",
                detail=f"source_draft_hash={package_hash}",
            )
        ]

        source_text = "\n".join(
            [
                package.title,
                package.abstract,
                package.claims,
                package.description,
                package.drawing_description,
            ]
        )
        if CROSS_PROJECT_TITLE in source_text:
            blocked_items.append(
                {
                    "category": "cross_project_contamination",
                    "section": "draft_package",
                    "pattern": CROSS_PROJECT_TITLE,
                    "message": "Detected title from another project in draft text.",
                }
            )

        cleaned_title = _clean_section(
            section="title",
            text=package.title,
            contamination_removed=contamination_removed,
            sidecar_notes=sidecar_notes,
        )
        cleaned = {
            section: _clean_section(
                section=section,
                text=getattr(package, section),
                contamination_removed=contamination_removed,
                sidecar_notes=sidecar_notes,
            )
            for section in REQUIRED_SECTIONS
        }

        if not cleaned_title.strip():
            blocked_items.append(
                {
                    "category": "empty_required_section",
                    "section": "title",
                    "pattern": "empty_after_cleaning",
                    "message": "title is empty after removing internal contamination.",
                }
            )

        for section, text in cleaned.items():
            if not text.strip():
                blocked_items.append(
                    {
                        "category": "empty_required_section",
                        "section": section,
                        "pattern": "empty_after_cleaning",
                        "message": f"{section} is empty after removing internal contamination.",
                    }
                )

        all_cleaned_text = {"title": cleaned_title, **cleaned}
        for item in contamination_removed:
            if item["section"] not in HARD_GATED_SECTIONS:
                continue
            blocked_items.append(
                {
                    "category": "official_hygiene_contamination",
                    "section": item["section"],
                    "pattern": item["pattern"],
                    "message": "Official draft field contains generator, format, prompt, memo, support-gap, or process-trace text; revise the source draft and recompile.",
                }
            )

        for section, text in all_cleaned_text.items():
            comparable_text = text.lower()
            for pattern in RESIDUAL_INTERNAL_PATTERNS:
                if pattern in comparable_text:
                    blocked_items.append(
                        {
                            "category": "residual_internal_text",
                            "section": section,
                            "pattern": pattern,
                            "message": "Cleaned official text still contains internal drafting text.",
                        }
                    )

        if blocked_items:
            logs.append(
                DeliberationLogEntry(
                    level="warn",
                    phase="official_compile",
                    message="official draft compile blocked",
                    detail=f"blocked_items={len(blocked_items)}",
                )
            )
            return OfficialCompileRun(
                id=run_id,
                project_id=project_id,
                status="blocked",
                source_draft_hash=package_hash,
                contamination_removed=contamination_removed,
                blocked_items=blocked_items,
                sidecar_notes=sidecar_notes,
                logs=logs,
                created_at=now,
                updated_at=now,
            )

        official_package = OfficialDraftPackage(
            title=cleaned_title,
            abstract=cleaned["abstract"],
            claims=cleaned["claims"],
            description=cleaned["description"],
            drawing_description=cleaned["drawing_description"],
            figure_plan=_parse_figure_plan(cleaned["drawing_description"]),
            compile_warnings=[],
            source_draft_hash=package_hash,
        )
        official_hash = official_package_hash(official_package)
        official_package.official_package_hash = official_hash
        logs.append(
            DeliberationLogEntry(
                level="info",
                phase="official_compile",
                message="official draft compile completed",
                detail=f"official_package_hash={official_hash}",
            )
        )
        return OfficialCompileRun(
            id=run_id,
            project_id=project_id,
            status="completed",
            source_draft_hash=package_hash,
            official_package_hash=official_hash,
            official_package=official_package,
            contamination_removed=contamination_removed,
            blocked_items=[],
            sidecar_notes=sidecar_notes,
            logs=logs,
            created_at=now,
            updated_at=now,
        )


def official_package_to_markdown(package: OfficialDraftPackage) -> str:
    lines = [
        f"# {package.title}",
        "",
        "## 摘要",
        package.abstract,
        "",
        "## 权利要求书",
        package.claims,
        "",
        "## 说明书",
        package.description,
        "",
        "## 附图说明",
        package.drawing_description,
    ]
    if package.figure_plan:
        lines.extend(["", "## 附图计划"])
        for item in package.figure_plan:
            lines.append(f"- {item.figure_no}：{item.title}。{item.description}")
    return "\n".join(lines).strip() + "\n"


def export_official_package_docx(package: OfficialDraftPackage, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    doc.add_heading(package.title, level=0)
    _add_docx_section(doc, "摘要", package.abstract)
    _add_docx_section(doc, "权利要求书", package.claims)
    _add_docx_section(doc, "说明书", package.description)
    _add_docx_section(doc, "附图说明", package.drawing_description)
    if package.figure_plan:
        doc.add_heading("附图计划", level=1)
        for item in package.figure_plan:
            doc.add_paragraph(f"{item.figure_no}：{item.title}。{item.description}")
    doc.save(output_path)
    return output_path


def official_compile_run_to_markdown(run: OfficialCompileRun) -> str:
    lines = [
        "# OFFICIAL_COMPILE_RUN",
        "",
        f"- run_id: {run.id}",
        f"- project_id: {run.project_id}",
        f"- status: {run.status}",
        f"- source_draft_hash: {run.source_draft_hash}",
        f"- official_package_hash: {run.official_package_hash}",
        "",
        "## Blocked Items",
    ]
    lines.extend(_dict_item_lines(run.blocked_items))
    lines.extend(["", "## Contamination Removed"])
    lines.extend(_dict_item_lines(run.contamination_removed))
    lines.extend(["", "## Sidecar Notes"])
    lines.extend(_dict_item_lines(run.sidecar_notes))
    if run.official_package:
        lines.extend(["", "## Official Package", "", official_package_to_markdown(run.official_package).strip()])
    lines.extend(["", "## Logs"])
    for log in run.logs:
        lines.append(f"- [{log.level}] {log.phase}: {log.message} {log.detail}".strip())
    return "\n".join(lines).strip() + "\n"


def _clean_section(
    *,
    section: str,
    text: str,
    contamination_removed: list[dict[str, str]],
    sidecar_notes: list[dict[str, str]],
) -> str:
    kept: list[str] = []
    in_fence = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if kept and kept[-1] != "":
                kept.append("")
            continue
        removal = _removal_for_line(line, in_fence)
        if line.startswith("```"):
            in_fence = not in_fence
        if removal:
            item = {
                "category": removal["category"],
                "section": section,
                "pattern": removal["pattern"],
                "text": line,
            }
            contamination_removed.append(item)
            if removal["category"] == "support_gap":
                sidecar_notes.append(item.copy())
            continue
        kept.append(_strip_inline_markdown(line))
    return "\n".join(kept).strip()


def _removal_for_line(line: str, in_fence: bool) -> dict[str, str] | None:
    comparable_line = line.lower()
    if in_fence:
        return {"category": "format_pollution", "pattern": "markdown_fence"}
    if re.search(r"^好的，下面.*撰写", line):
        return {"category": "ai_preface", "pattern": "好的，下面"}
    for pattern in ("support_gap", "support_gaps"):
        if pattern in comparable_line:
            return {"category": "support_gap", "pattern": pattern}
    chinese_match = CHINESE_LABEL_RE.match(line)
    if chinese_match:
        return {"category": "support_gap", "pattern": chinese_match.group(1)}
    if line.startswith("```"):
        return {"category": "format_pollution", "pattern": "markdown_fence"}
    if re.match(r"^#{1,6}\s+", line):
        return {"category": "format_pollution", "pattern": "markdown_heading"}
    if JSON_WRAPPER_RE.match(line):
        return {"category": "format_pollution", "pattern": "json_wrapper"}
    official_field = EMPTY_OFFICIAL_FIELD_RE.match(line)
    if official_field:
        return {"category": "json_wrapper", "pattern": official_field.group(1).lower()}
    internal_field = INTERNAL_FIELD_RE.match(line)
    if internal_field:
        return {"category": "internal_field", "pattern": internal_field.group(1).lower()}
    for pattern in ("根据会审策略", "多 Agent 会审", "多Agent会审", "主席汇总", "deliberation", "generation_logs"):
        if pattern.lower() in comparable_line:
            return {"category": "internal_trace", "pattern": pattern}
    for pattern in ("可能不具备创造性", "禁止直接提交", "存在充分公开风险"):
        if pattern in line:
            return {"category": "unfavorable_statement", "pattern": pattern}
    if _looks_like_mermaid(line):
        return {"category": "format_pollution", "pattern": "mermaid"}
    return None


def _looks_like_mermaid(line: str) -> bool:
    mermaid_starters = (
        "flowchart",
        "graph",
        "sequenceDiagram",
        "classDiagram",
        "stateDiagram",
        "erDiagram",
        "gantt",
    )
    if line.startswith(mermaid_starters):
        return True
    return bool(re.search(r"\w+\s*(-->|---|==>|-.->)\s*\w+", line))


def _strip_inline_markdown(line: str) -> str:
    line = re.sub(r"^\s*#{1,6}\s*", "", line)
    return line.strip()


def _parse_figure_plan(drawing_description: str) -> list[OfficialFigurePlanItem]:
    items: list[OfficialFigurePlanItem] = []
    for line in drawing_description.splitlines():
        match = re.match(r"^(图\d+)(?:为|是)(.+?)(?:。|$)", line.strip())
        if not match:
            continue
        figure_no, title = match.groups()
        items.append(
            OfficialFigurePlanItem(
                figure_no=figure_no,
                title=title.strip(),
                description=line.strip(),
                referenced_sections=["drawing_description"],
            )
        )
    return items


def _add_docx_section(doc: Document, heading: str, text: str) -> None:
    doc.add_heading(heading, level=1)
    for line in text.splitlines() or [""]:
        doc.add_paragraph(line)


def _dict_item_lines(items: list[dict[str, str]]) -> list[str]:
    if not items:
        return ["- 无"]
    return ["- " + "；".join(f"{key}={value}" for key, value in item.items()) for item in items]


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
