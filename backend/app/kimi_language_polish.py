from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from backend.app.official_compile import OfficialDraftCompiler, official_package_hash, official_package_to_markdown
from backend.app.schemas import DeliberationLogEntry, DraftPackage, OfficialCompileRun, OfficialDraftPackage


KIMI_LANGUAGE_POLISH_PROVIDER = "kimicode"
KIMI_LANGUAGE_POLISH_PROMPT_VERSION = "kimi-official-language-polish-v1"


async def run_kimi_language_polish(
    *,
    project_id: str,
    source_run: OfficialCompileRun,
    provider_runner: Any,
    workdir: Path,
    trace: bool = False,
    task_timeout_ms: int = 180_000,
) -> OfficialCompileRun:
    run_id = uuid.uuid4().hex
    now = _utc_now_iso()
    source_package = source_run.official_package
    source_hash = source_run.source_draft_hash
    logs = [
        DeliberationLogEntry(
            level="info",
            phase="official_language_polish",
            provider_id=KIMI_LANGUAGE_POLISH_PROVIDER,
            message="kimi official language polish started",
            detail=f"source_compile_run_id={source_run.id}; prompt_pack_version={KIMI_LANGUAGE_POLISH_PROMPT_VERSION}",
        )
    ]
    if not source_package or not source_hash:
        logs.append(
            DeliberationLogEntry(
                level="error",
                phase="official_language_polish",
                provider_id=KIMI_LANGUAGE_POLISH_PROVIDER,
                message="source official compile run is not completed",
                detail="Kimi language polish requires a completed official package.",
            )
        )
        return OfficialCompileRun(
            id=run_id,
            project_id=project_id,
            status="failed",
            source_draft_hash=source_hash,
            logs=logs,
            created_at=now,
            updated_at=now,
        )

    workdir.mkdir(parents=True, exist_ok=True)
    try:
        result = await provider_runner.run_json_task(
            provider_id=KIMI_LANGUAGE_POLISH_PROVIDER,
            prompt=_kimi_language_polish_prompt(source_package),
            workdir=workdir,
            label="kimi official language polish",
            trace=trace,
            task_timeout_ms=task_timeout_ms,
        )
        payload = getattr(result, "payload", {})
        logs.append(
            DeliberationLogEntry(
                level="info",
                phase="official_language_polish",
                provider_id=KIMI_LANGUAGE_POLISH_PROVIDER,
                attempt=getattr(result, "attempts", None),
                message="kimi official language polish completed",
                detail=f"payload_fields={','.join(sorted(payload.keys())) if isinstance(payload, dict) else 'invalid'}",
            )
        )
        return _compile_polished_payload(
            project_id=project_id,
            run_id=run_id,
            source_hash=source_hash,
            payload=payload if isinstance(payload, dict) else {},
            logs=logs,
            created_at=now,
        )
    except Exception as exc:
        logs.append(
            DeliberationLogEntry(
                level="error",
                phase="official_language_polish",
                provider_id=KIMI_LANGUAGE_POLISH_PROVIDER,
                message="kimi official language polish failed",
                detail=f"{type(exc).__name__}: {exc}"[:1200],
                repair_suggestion="检查 KimiCode CLI 是否安装并已登录，或稍后重试成稿语言润色。",
            )
        )
        return OfficialCompileRun(
            id=run_id,
            project_id=project_id,
            status="failed",
            source_draft_hash=source_hash,
            logs=logs,
            created_at=now,
            updated_at=now,
        )


def _compile_polished_payload(
    *,
    project_id: str,
    run_id: str,
    source_hash: str,
    payload: dict[str, Any],
    logs: list[DeliberationLogEntry],
    created_at: str,
) -> OfficialCompileRun:
    draft = DraftPackage(
        title=_payload_text(payload, "title"),
        abstract=_payload_text(payload, "abstract"),
        claims=_payload_text(payload, "claims"),
        description=_payload_text(payload, "description"),
        drawing_description=_payload_text(payload, "drawing_description"),
        mermaid="",
        image_prompt="",
        review_findings=[],
        citations=[],
        generation_logs=[f"official-language-polish: {KIMI_LANGUAGE_POLISH_PROMPT_VERSION}"],
    )
    compiled = OfficialDraftCompiler().compile(project_id=project_id, package=draft)
    notes = list(compiled.sidecar_notes)
    for memo in _payload_list(payload, "attorney_memo"):
        notes.append({"category": "kimi_language_polish", "section": "attorney_memo", "text": memo})
    if compiled.status != "completed" or not compiled.official_package:
        logs.append(
            DeliberationLogEntry(
                level="warn",
                phase="official_language_polish",
                provider_id=KIMI_LANGUAGE_POLISH_PROVIDER,
                message="kimi polished draft blocked by official hygiene checks",
                detail=f"blocked_items={len(compiled.blocked_items)}; contamination_removed={len(compiled.contamination_removed)}",
            )
        )
        return compiled.model_copy(
            update={
                "id": run_id,
                "source_draft_hash": source_hash,
                "sidecar_notes": notes,
                "logs": logs,
                "created_at": created_at,
                "updated_at": created_at,
            }
        )

    polished_package = compiled.official_package.model_copy(
        update={
            "compile_warnings": [*compiled.official_package.compile_warnings, "kimi_language_polished"],
            "source_draft_hash": source_hash,
            "official_package_hash": "",
        }
    )
    polished_hash = official_package_hash(polished_package)
    polished_package.official_package_hash = polished_hash
    logs.append(
        DeliberationLogEntry(
            level="info",
            phase="official_language_polish",
            provider_id=KIMI_LANGUAGE_POLISH_PROVIDER,
            message="kimi official language polish packaged",
            detail=f"official_package_hash={polished_hash}",
        )
    )
    return compiled.model_copy(
        update={
            "id": run_id,
            "source_draft_hash": source_hash,
            "official_package_hash": polished_hash,
            "official_package": polished_package,
            "sidecar_notes": notes,
            "logs": logs,
            "created_at": created_at,
            "updated_at": created_at,
        }
    )


def _payload_text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field, "")
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _payload_list(payload: dict[str, Any], field: str) -> list[str]:
    value = payload.get(field, [])
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    text = str(value).strip()
    return [text] if text else []


def _kimi_language_polish_prompt(package: OfficialDraftPackage) -> str:
    return f"""
你是 KimiCode 中文专利成稿语言润色 agent。
任务：仅优化中国专利正式稿语言，使表述更符合中文专利申请文件习惯。

硬性约束：
- 不新增技术特征，不删除必要技术特征，不改变权利要求保护范围。
- 保留权利要求编号、层级和引用关系；只改善措辞、术语一致性、句式和中文可读性。
- 不输出 Markdown、解释、隐藏推理、prompt、system_trace、attorney_memo 到正式字段。
- attorney_memo 只能放在单独 JSON 字段中，不得混入 title、abstract、claims、description、drawing_description。
- 只返回可被 json.loads 解析的 JSON object。

JSON schema:
{{
  "title": "润色后的题名",
  "abstract": "润色后的摘要",
  "claims": "润色后的权利要求书",
  "description": "润色后的说明书",
  "drawing_description": "润色后的附图说明",
  "attorney_memo": ["内部备注，可为空数组"]
}}

当前正式稿：
{official_package_to_markdown(package)}
""".strip()


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
