from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from backend.app.llm import LLMClient
from backend.app.schemas import (
    DeliberationLogEntry,
    DraftPackage,
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


def draft_package_hash(package: DraftPackage) -> str:
    return hashlib.sha256(package.model_dump_json().encode("utf-8")).hexdigest()


def run_post_draft_review(
    *,
    project_id: str,
    package: DraftPackage,
    llm: LLMClient,
    providers: list[str],
) -> PostDraftReviewRun:
    run_id = uuid.uuid4().hex
    package_hash = draft_package_hash(package)
    logs: list[DeliberationLogEntry] = []
    role_results: list[PostDraftReviewRoleResult] = []
    try:
        for role, stage in ROLE_STAGES:
            raw = llm.complete_stage(stage, SYSTEM_PROMPT, _role_prompt(role, package, providers))
            payload = _extract_json(raw)
            result = PostDraftReviewRoleResult.model_validate(payload)
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
        chair_raw = llm.complete_stage(
            "post_draft_chair_synthesis",
            SYSTEM_PROMPT,
            _chair_prompt(package, providers, role_results),
        )
        chair = PostDraftReviewChairResult.model_validate(_extract_json(chair_raw))
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
            draft_package_hash=package_hash,
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
                message=f"post-draft review failed: invalid_json" if isinstance(exc, ValueError) else f"post-draft review failed: {type(exc).__name__}",
                detail=str(exc)[:1200],
                repair_suggestion="检查成稿后会审 agent 是否按 Prompt Pack 输出结构化 JSON，并重试该会审。",
            )
        )
        return PostDraftReviewRun(
            id=run_id,
            project_id=project_id,
            status="failed",
            providers=providers,
            prompt_pack_version=PROMPT_PACK_VERSION,
            draft_package_hash=package_hash,
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


def _role_prompt(role: str, package: DraftPackage, providers: list[str]) -> str:
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

当前成稿：
{package.model_dump_json(ensure_ascii=False, indent=2)}
"""


def _chair_prompt(package: DraftPackage, providers: list[str], role_results: list[PostDraftReviewRoleResult]) -> str:
    return f"""
你是成稿后会审主席，只综合角色 JSON，不重新发散。
如任一角色存在 blocking_issues，除非有明确反证，否则 export_allowed=false。
只输出 JSON，字段必须包含 status, export_allowed, blocking_issues, contamination_hits, claim_1_rewrite, system_claim_rewrite, abstract_rewrite, description_rewrite_tasks, official_safe_patches, attorney_memo, next_actions。

本轮启用 agent：{json.dumps(providers, ensure_ascii=False)}

当前成稿：
{package.model_dump_json(ensure_ascii=False, indent=2)}

角色结果：
{json.dumps([result.model_dump(mode="json") for result in role_results], ensure_ascii=False, indent=2)}
"""


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
