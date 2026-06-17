from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from pydantic import ValidationError

from backend.app.llm import LLMClient
from backend.app.schemas import (
    DeliberationLogEntry,
    OfficialDraftPackage,
    PostDraftReviewChairResult,
    PostDraftReviewRoleResult,
    PostDraftReviewRun,
)


PROMPT_PACK_VERSION = "post-draft-review-v1"
ROLE_STAGES = (
    ("claims_reviewer", "post_draft_claims_reviewer"),
    ("spec_cleaner", "post_draft_spec_cleaner"),
    ("technical_hardness", "post_draft_technical_hardness"),
)

SYSTEM_PROMPT = (
    "你是提交前专利代理审稿 agent。禁止输出隐藏推理过程。"
    "只输出符合要求的 JSON，不输出 Markdown 或自然语言解释。"
    "必须区分 official_text、attorney_memo 和 system_trace；attorney_memo 不得进入正式申请文件。"
)
ROLE_LIST_FIELDS = (
    "blocking_issues",
    "contamination_hits",
    "rewrite_suggestions",
    "official_safe_patches",
    "attorney_memo",
)
CHAIR_LIST_FIELDS = (
    "blocking_issues",
    "contamination_hits",
    "description_rewrite_tasks",
    "official_safe_patches",
    "attorney_memo",
    "next_actions",
)
CHAIR_STRING_FIELDS = ("claim_1_rewrite", "system_claim_rewrite", "abstract_rewrite")
STATUS_ALIASES = {
    "pass": "passed",
    "passed": "passed",
    "clean": "passed",
    "ok": "passed",
    "ok_to_file": "passed",
    "success": "passed",
    "warning": "needs_revision",
    "warn": "needs_revision",
    "needs_revision": "needs_revision",
    "needsrevision": "needs_revision",
    "revision_required": "needs_revision",
    "requires_revision": "needs_revision",
    "blocking": "blocked",
    "blocked": "blocked",
    "block": "blocked",
    "failed": "blocked",
    "fail": "blocked",
    "rejected": "blocked",
}
ROLE_ALIASES = {
    "claims": "claims_reviewer",
    "claim_reviewer": "claims_reviewer",
    "claims_reviewer": "claims_reviewer",
    "spec": "spec_cleaner",
    "specification_cleaner": "spec_cleaner",
    "spec_cleaner": "spec_cleaner",
    "technical": "technical_hardness",
    "technical_reviewer": "technical_hardness",
    "technical_hardness": "technical_hardness",
}


def package_hash_for_review(package: OfficialDraftPackage) -> str:
    return package.official_package_hash or hashlib.sha256(package.model_dump_json().encode("utf-8")).hexdigest()


def run_post_draft_review(
    *,
    project_id: str,
    package: OfficialDraftPackage,
    llm: LLMClient,
    providers: list[str],
    official_compile_run_id: str,
) -> PostDraftReviewRun:
    run_id = uuid.uuid4().hex
    package_hash = package_hash_for_review(package)
    source_hash = package.source_draft_hash
    logs: list[DeliberationLogEntry] = []
    role_results: list[PostDraftReviewRoleResult] = []
    current_stage = "post_draft_review"
    try:
        for role, stage in ROLE_STAGES:
            current_stage = stage
            try:
                raw = llm.complete_stage(stage, SYSTEM_PROMPT, _role_prompt(role, package, providers))
                payload = _extract_json(raw)
                payload, repair_notes = _repair_role_payload(payload, expected_role=role)
                if repair_notes:
                    logs.append(_schema_repair_log(provider_id=role, notes=repair_notes))
                result = PostDraftReviewRoleResult.model_validate(payload)
            except Exception as role_exc:
                # A single reviewer that errors at any point — LLM call failure
                # (ConfigError/RuntimeError/timeout), unparseable JSON, or a
                # schema mismatch the repair pass cannot fix — is downgraded to
                # a blocked result so the review completes (fail-closed: export
                # stays blocked) and the other reviewers' findings are preserved.
                logs.append(
                    DeliberationLogEntry(
                        level="error",
                        phase="post_draft_review",
                        provider_id=role,
                        message=f"{role} failed, downgraded to blocked",
                        detail=_failure_detail(role_exc, stage),
                    )
                )
                result = PostDraftReviewRoleResult(
                    role=role,
                    status="blocked",
                    blocking_issues=[f"{role} 角色执行失败（{role_exc}），已降级为 blocked。"],
                )
            role_results.append(result)
            logs.append(
                DeliberationLogEntry(
                    level="info",
                    phase="post_draft_review",
                    provider_id=role,
                    message=f"{role} completed",
                    detail=json.dumps(result.model_dump(mode="json"), ensure_ascii=False)[:1200],
                )
            )
        current_stage = "post_draft_chair_synthesis"
        try:
            chair_raw = llm.complete_stage(
                "post_draft_chair_synthesis",
                SYSTEM_PROMPT,
                _chair_prompt(package, providers, role_results),
            )
            chair_payload, repair_notes = _repair_chair_payload(_extract_json(chair_raw))
            if repair_notes:
                logs.append(_schema_repair_log(provider_id="chair", notes=repair_notes))
            chair = PostDraftReviewChairResult.model_validate(chair_payload)
        except Exception as chair_exc:
            # Chair synthesis is guarded the same way as reviewer roles: an LLM
            # error, unparseable JSON, or schema mismatch downgrades to a blocked
            # chair so the run completes fail-closed instead of crashing. The
            # reviewer findings already collected are still surfaced.
            logs.append(
                DeliberationLogEntry(
                    level="error",
                    phase="post_draft_chair_synthesis",
                    provider_id="chair",
                    message="chair synthesis failed, downgraded to blocked",
                    detail=_failure_detail(chair_exc, "post_draft_chair_synthesis"),
                )
            )
            chair = PostDraftReviewChairResult(
                status="blocked",
                export_allowed=False,
                blocking_issues=["主席综合裁决执行失败，已降级为 blocked，请重试。"],
            )
        blocking_issues = _dedupe([*chair.blocking_issues, *[issue for result in role_results for issue in result.blocking_issues]])
        contamination_hits = _dedupe([*chair.contamination_hits, *[hit for result in role_results for hit in result.contamination_hits]])
        export_allowed = bool(chair.export_allowed and not blocking_issues and not contamination_hits and chair.status == "passed")
        if not export_allowed and chair.status == "passed":
            chair = chair.model_copy(update={"status": "blocked", "export_allowed": False})
        return PostDraftReviewRun(
            id=run_id,
            project_id=project_id,
            status="completed",
            providers=providers,
            prompt_pack_version=PROMPT_PACK_VERSION,
            draft_package_hash=source_hash,
            official_compile_run_id=official_compile_run_id,
            official_package_hash=package_hash,
            role_results=role_results,
            chair_result=chair,
            export_allowed=export_allowed,
            blocking_issues=blocking_issues,
            contamination_hits=contamination_hits,
            logs=logs,
        )
    except Exception as exc:
        logs.append(
            DeliberationLogEntry(
                level="error",
                phase="post_draft_review",
                provider_id="system",
                message=_failure_message(exc),
                detail=_failure_detail(exc, current_stage),
                repair_suggestion=_failure_repair_suggestion(exc),
            )
        )
        return PostDraftReviewRun(
            id=run_id,
            project_id=project_id,
            status="failed",
            providers=providers,
            prompt_pack_version=PROMPT_PACK_VERSION,
            draft_package_hash=source_hash,
            official_compile_run_id=official_compile_run_id,
            official_package_hash=package_hash,
            export_allowed=False,
            logs=logs,
        )


def post_draft_review_to_markdown(run: PostDraftReviewRun) -> str:
    lines = [
        "# POST_DRAFT_REVIEW_REPORT",
        "",
        f"- run_id: {run.id}",
        f"- project_id: {run.project_id}",
        f"- status: {run.status}",
        f"- export_allowed: {str(run.export_allowed).lower()}",
        f"- prompt_pack_version: {run.prompt_pack_version}",
        f"- draft_package_hash: {run.draft_package_hash}",
        f"- providers: {', '.join(run.providers) or 'default'}",
        "",
        "## Blocking Issues",
        "",
    ]
    lines.extend(f"- {issue}" for issue in run.blocking_issues)
    if not run.blocking_issues:
        lines.append("- 无")
    lines.extend(["", "## Contamination Hits", ""])
    lines.extend(f"- {hit}" for hit in run.contamination_hits)
    if not run.contamination_hits:
        lines.append("- 无")
    lines.extend(["", "## Role Results", ""])
    for result in run.role_results:
        lines.extend(
            [
                f"### {result.role}",
                "",
                f"- status: {result.status}",
                f"- blocking_issues: {'；'.join(result.blocking_issues) or '无'}",
                f"- contamination_hits: {'；'.join(result.contamination_hits) or '无'}",
                f"- rewrite_suggestions: {'；'.join(result.rewrite_suggestions) or '无'}",
                f"- attorney_memo: {'；'.join(result.attorney_memo) or '无'}",
                "",
            ]
        )
    if run.chair_result:
        chair = run.chair_result
        lines.extend(
            [
                "## Chair Synthesis",
                "",
                f"- status: {chair.status}",
                f"- export_allowed: {str(chair.export_allowed).lower()}",
                f"- claim_1_rewrite: {chair.claim_1_rewrite or '无'}",
                f"- system_claim_rewrite: {chair.system_claim_rewrite or '无'}",
                f"- abstract_rewrite: {chair.abstract_rewrite or '无'}",
                f"- description_rewrite_tasks: {'；'.join(chair.description_rewrite_tasks) or '无'}",
                f"- official_safe_patches: {'；'.join(chair.official_safe_patches) or '无'}",
                f"- attorney_memo: {'；'.join(chair.attorney_memo) or '无'}",
                f"- next_actions: {'；'.join(chair.next_actions) or '无'}",
                "",
            ]
        )
    lines.extend(["## Logs", ""])
    for log in run.logs:
        lines.append(f"- [{log.level}] {log.phase}/{log.provider_id}: {log.message} {log.detail}")
    return "\n".join(lines).strip() + "\n"


def _role_prompt(role: str, package: OfficialDraftPackage, providers: list[str]) -> str:
    focus = {
        "claims_reviewer": "重点审查权利要求1、从属层次、系统/设备/介质一致性。",
        "spec_cleaner": "重点审查正式申请文本污染、内部提示泄漏、说明书支撑和绝对化表述。",
        "technical_hardness": "重点审查公式、贡献矩阵、任务包、约束、后验更新、无人机控制动作。",
    }[role]
    return f"""
请执行成稿后会审角色：{role}。
{focus}
只输出 JSON，字段必须包含 role, status, blocking_issues, contamination_hits, rewrite_suggestions, official_safe_patches, attorney_memo。

本轮启用 agent：{json.dumps(providers, ensure_ascii=False)}

当前正式稿：
{package.model_dump_json(ensure_ascii=False, indent=2)}
"""


def _chair_prompt(package: OfficialDraftPackage, providers: list[str], role_results: list[PostDraftReviewRoleResult]) -> str:
    return f"""
你是成稿后会审主席，只综合角色 JSON，不重新发散。
如任一角色存在 blocking_issues，除非有明确反证，否则 export_allowed=false。
只输出 JSON，字段必须包含 status, export_allowed, blocking_issues, contamination_hits, claim_1_rewrite, system_claim_rewrite, abstract_rewrite, description_rewrite_tasks, official_safe_patches, attorney_memo, next_actions。

本轮启用 agent：{json.dumps(providers, ensure_ascii=False)}

当前正式稿：
{package.model_dump_json(ensure_ascii=False, indent=2)}

角色结果：
{json.dumps([result.model_dump(mode="json") for result in role_results], ensure_ascii=False, indent=2)}
"""


def _repair_role_payload(payload: dict[str, Any], *, expected_role: str) -> tuple[dict[str, Any], list[str]]:
    repaired = dict(payload)
    notes: list[str] = []

    raw_role = repaired.get("role")
    normalized_role = _normalize_role(raw_role, expected_role)
    if normalized_role != raw_role:
        notes.append(f"role {raw_role!r}->{normalized_role!r}")
        repaired["role"] = normalized_role

    _repair_status(repaired, notes)
    _repair_list_fields(repaired, ROLE_LIST_FIELDS, notes)
    return repaired, notes


def _repair_chair_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    repaired = dict(payload)
    notes: list[str] = []

    _repair_status(repaired, notes)
    _repair_bool_field(repaired, "export_allowed", notes)
    _repair_list_fields(repaired, CHAIR_LIST_FIELDS, notes)
    _repair_string_fields(repaired, CHAIR_STRING_FIELDS, notes)
    return repaired, notes


def _repair_status(payload: dict[str, Any], notes: list[str]) -> None:
    if "status" not in payload:
        payload["status"] = "needs_revision"
        notes.append("status missing, defaulted to 'needs_revision'")
        return
    raw_status = payload["status"]
    normalized = _normalize_status(raw_status)
    if normalized != raw_status:
        # Flag unknown statuses so new LLM output patterns are visible and the
        # alias table can be extended; known-alias mappings stay terse.
        is_alias = isinstance(raw_status, str) and _enum_key(raw_status) in STATUS_ALIASES
        marker = "" if is_alias else " (unknown status, fell back to default)"
        notes.append(f"status {raw_status!r}->{normalized!r}{marker}")
        payload["status"] = normalized


def _repair_bool_field(payload: dict[str, Any], field: str, notes: list[str]) -> None:
    if field not in payload:
        return
    raw_value = payload[field]
    normalized = _coerce_bool(raw_value)
    if normalized is not raw_value:
        notes.append(f"{field} {raw_value!r}->{normalized!r}")
        payload[field] = normalized


def _repair_list_fields(payload: dict[str, Any], fields: tuple[str, ...], notes: list[str]) -> None:
    for field in fields:
        if field not in payload:
            continue
        raw_value = payload[field]
        normalized = _coerce_string_list(raw_value)
        if normalized != raw_value:
            notes.append(f"{field} {type(raw_value).__name__}->list[str]")
            payload[field] = normalized


def _repair_string_fields(payload: dict[str, Any], fields: tuple[str, ...], notes: list[str]) -> None:
    for field in fields:
        if field not in payload:
            continue
        raw_value = payload[field]
        normalized = _coerce_text(raw_value)
        if normalized != raw_value:
            notes.append(f"{field} {type(raw_value).__name__}->str")
            payload[field] = normalized


def _normalize_role(value: object, expected_role: str) -> str:
    if value is None or _coerce_text(value).strip() == "":
        return expected_role
    key = _enum_key(_coerce_text(value))
    return ROLE_ALIASES.get(key, expected_role if key not in ROLE_ALIASES.values() else key)


def _normalize_status(value: object) -> object:
    if value is None:
        return "needs_revision"
    text = _coerce_text(value).strip()
    if text == "":
        return "needs_revision"
    key = _enum_key(text)
    mapped = STATUS_ALIASES.get(key)
    if mapped is not None:
        return mapped
    # The LLM sometimes returns a status outside the known aliases (e.g. a
    # free-form phrase or a Chinese label). Passing it through verbatim makes
    # model_validate reject the whole payload and fail the review. Fall back to
    # the safe "needs_revision" bucket so the review completes and surfaces the
    # reviewer's blocking_issues instead of crashing on schema validation.
    # `key` is already lower-cased/normalized by _enum_key.
    if key in {"passed", "needs_revision", "blocked"}:
        return key
    return "needs_revision"


def _enum_key(text: str) -> str:
    return text.strip().replace("-", "_").replace(" ", "_").lower()


def _coerce_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in (_coerce_text(item).strip() for item in value) if item]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        parsed = _try_parse_json_scalar(stripped)
        if parsed is not stripped:
            return _coerce_string_list(parsed)
        return [stripped]
    return [_coerce_text(value)]


def _try_parse_json_scalar(value: str) -> object:
    if not (value.startswith("[") or value.startswith("{")):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _coerce_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _coerce_bool(value: object) -> object:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y", "是"}:
            return True
        if lowered in {"false", "0", "no", "n", "否"}:
            return False
    return value


def _schema_repair_log(*, provider_id: str, notes: list[str]) -> DeliberationLogEntry:
    return DeliberationLogEntry(
        level="warn",
        phase="post_draft_review",
        provider_id=provider_id,
        message="post-draft schema repair applied",
        detail="; ".join(notes)[:1200],
        repair_suggestion="Agent output used schema variants; normalized common enum/type drift before validation.",
    )


def _failure_message(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "post-draft review failed: schema_validation"
    if isinstance(exc, ValueError):
        return "post-draft review failed: invalid_json"
    return f"post-draft review failed: {type(exc).__name__}"


def _failure_detail(exc: Exception, stage: str) -> str:
    if isinstance(exc, ValidationError):
        errors = []
        for item in exc.errors():
            path = ".".join(str(part) for part in item.get("loc", ())) or "<root>"
            errors.append(f"{stage}.{path}: {item.get('msg', 'invalid value')}")
        return "; ".join(errors)[:1200]
    return f"{stage}: {str(exc)}"[:1200]


def _failure_repair_suggestion(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "自动修复后仍不符合成稿会审 JSON schema；按 detail 中的 schema path 修正字段类型或枚举值后重试。"
    return "检查成稿后会审 agent 是否按 Prompt Pack 输出结构化 JSON，并重试该会审。"


def _extract_json(raw: str) -> dict[str, Any]:
    stripped = raw.strip()
    candidates = [stripped]
    if "```" in stripped:
        candidates.extend(part.replace("json", "", 1).strip() for part in stripped.split("```") if "{" in part)
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first >= 0 and last > first:
        candidates.append(stripped[first : last + 1])
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            continue
    raise ValueError("invalid_json: post-draft review output is not JSON")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
