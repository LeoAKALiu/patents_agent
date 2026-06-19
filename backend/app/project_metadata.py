from __future__ import annotations

from backend.app.schemas import ProjectRecord


def format_project_metadata_block(project: ProjectRecord) -> str:
    rows = [
        ("技术领域", project.technical_field),
        ("背景技术", project.background),
        ("技术痛点", project.pain_point),
        ("结构化技术方案", project.technical_solution),
        ("结构化创新点", project.innovation),
        ("实施例", project.embodiments),
        ("有益效果", project.beneficial_effects),
    ]
    lines = [f"- {label}: {value.strip()}" for label, value in rows if value and value.strip()]
    return "\n".join(lines) if lines else "（未填写）"
