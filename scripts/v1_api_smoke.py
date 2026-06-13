#!/usr/bin/env python3
"""Deterministic v1 release API smoke against checked-in golden samples.

This script intentionally uses an in-process FastAPI TestClient and a local fake
LLM implementation. It never reads `.env`, never calls a live LLM API, and keeps
all runtime data in a temporary directory.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.main import create_app
from backend.app.schemas import DeliberationRun, DeliberationStageResult, PatentStrategyBrief

SAMPLE_DIR = ROOT / "samples"

SAMPLES = {
    "invention": SAMPLE_DIR / "invention_ai_monitoring.md",
    "utility_model": SAMPLE_DIR / "utility_model_structure.md",
    "external_draft": SAMPLE_DIR / "external_draft_invention.md",
}


class V1SmokeLLM:
    """Small stage-aware fake LLM for the v1 smoke.

    The backend only requires an object with complete_stage(stage, system, user).
    Responses are valid deterministic patent text/JSON and contain no credential
    or network dependencies.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(
            {
                "stage": stage,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )
        utility_model = "实用新型" in system_prompt or "utility_model" in user_prompt or "结构" in user_prompt

        if stage == "core_formula":
            return _json(
                {
                    "summary": "以风险评分固定施工安全告警触发关系。",
                    "formula_blocks": [
                        {
                            "id": "F01",
                            "name": "风险评分关系",
                            "latex": "R=\\alpha C+\\beta T+\\gamma D",
                            "purpose": "描述目标置信度、停留时间和危险源距离对告警风险的贡献。",
                            "claim_hook": "根据风险评分与阈值比较生成告警事件。",
                        }
                    ],
                    "variable_definitions": [
                        {"symbol": "C", "meaning": "目标识别置信度", "unit": ""},
                        {"symbol": "T", "meaning": "目标在危险区域内的停留时间", "unit": "秒"},
                        {"symbol": "D", "meaning": "目标与危险源边界的距离因子", "unit": ""},
                    ],
                    "derivation_notes": ["公式用于限定告警触发逻辑，具体权重可按项目配置。"],
                    "claim_hooks": ["将风险评分和阈值比较写入从属权利要求。"],
                    "description_insert": "本实施例可根据F01计算风险评分，并在风险评分超过阈值时生成告警事件。",
                    "latex_markdown": "# 核心公式\n\nF01: $R=\\alpha C+\\beta T+\\gamma D$。",
                    "generation_logs": ["v1 smoke fake formula package"],
                }
            )

        if stage == "claims":
            if utility_model:
                return (
                    "1. 一种可调节边缘监控安装支架，其特征在于，包括固定底座、旋转支撑臂、"
                    "俯仰调节座、防护罩、理线槽和快拆锁止件，所述旋转支撑臂与所述固定底座"
                    "转动连接，所述俯仰调节座设置在所述旋转支撑臂的端部。\n"
                    "2. 根据权利要求1所述的安装支架，其特征在于，所述旋转支撑臂设有角度刻度和限位槽。\n"
                    "3. 根据权利要求1所述的安装支架，其特征在于，所述防护罩顶部设置导水坡。\n"
                    "4. 根据权利要求1所述的安装支架，其特征在于，所述理线槽通过卡扣盖板闭合。"
                )
            return (
                "1. 一种施工场景边缘AI安全监控方法，其特征在于，包括：接收施工现场视频流；"
                "识别人员目标、设备目标和安全防护目标；基于危险源配置、目标轨迹和风险评分生成告警事件；"
                "将告警事件与证据帧、检测框、轨迹片段和处置状态关联存储。\n"
                "2. 根据权利要求1所述的方法，其特征在于，所述风险评分根据目标识别置信度、停留时间和危险源距离确定。\n"
                "3. 根据权利要求1所述的方法，其特征在于，所述目标轨迹包括同一人员在多个摄像头下的时间连续位置。\n"
                "4. 根据权利要求1所述的方法，其特征在于，所述处置状态包括待确认、已派发、已复核和已关闭。"
            )

        if stage == "description":
            if utility_model:
                return (
                    "技术领域\n本实用新型涉及施工现场摄像机安装结构。\n"
                    "背景技术\n施工现场摄像机需要在多种基面上快速安装并保持视角稳定。\n"
                    "实用新型内容\n本实用新型通过固定底座、旋转支撑臂、俯仰调节座和防护罩形成可调节安装结构。\n"
                    "附图说明\n图1为安装支架整体结构示意图。图2为快拆锁止件局部结构示意图。\n"
                    "具体实施方式\n固定底座通过螺栓固定在立柱上，旋转支撑臂绕水平转轴调节方向，"
                    "俯仰调节座沿弧形滑槽调节摄像机角度，理线槽容纳电源线和网线。"
                )
            return (
                "技术领域\n本发明涉及施工安全智能监控技术领域。\n"
                "背景技术\n施工现场视频告警需要在遮挡和多摄像头条件下保留可复核证据。\n"
                "发明内容\n本发明通过目标识别、轨迹关联、风险评分和证据留痕生成可复核的安全告警事件。\n"
                "附图说明\n图1为安全监控方法流程图。图2为告警事件数据结构图。\n"
                "具体实施方式\n边缘设备接收多路视频，识别人员、设备和防护目标，结合危险源配置计算风险评分，"
                "当风险评分超过阈值时生成告警事件，并保存证据帧、检测框、轨迹片段和处置状态。"
            )

        if stage == "abstract":
            if utility_model:
                return "本实用新型公开一种可调节边缘监控安装支架，能够实现摄像机视角调节、防护和线缆收纳。"
            return "本发明公开一种施工场景边缘AI安全监控方法，能够生成可复核的安全告警事件并关联保存证据数据。"

        if stage == "drawings":
            if utility_model:
                return "图1为安装支架整体结构示意图。图2为快拆锁止件局部结构示意图。"
            return "图1为安全监控方法流程图。图2为告警事件与证据数据的关联结构图。"

        if stage == "diagram":
            return "flowchart TD\nA[接收输入] --> B[生成草稿]\nB --> C[质量检查]\nC --> D[正式导出]"

        if stage == "image_prompt":
            return "黑白专利线稿，展示关键模块和数据流。"

        if stage == "review":
            return _json(
                [
                    {
                        "category": "支持性",
                        "severity": "low",
                        "message": "权利要求与说明书主要技术特征一致。",
                        "suggestion": "提交前补充项目实测数据和附图标号。",
                        "evidence": "权利要求1和具体实施方式",
                    }
                ]
            )

        if stage == "post_draft_claims_reviewer":
            return _json(
                {
                    "role": "claims_reviewer",
                    "status": "passed",
                    "blocking_issues": [],
                    "contamination_hits": [],
                    "rewrite_suggestions": ["权利要求1保留输入、处理、输出闭环。"],
                    "official_safe_patches": [],
                    "attorney_memo": ["提交前由代理人复核从属权利要求层级。"],
                }
            )

        if stage == "post_draft_spec_cleaner":
            return _json(
                {
                    "role": "spec_cleaner",
                    "status": "passed",
                    "blocking_issues": [],
                    "contamination_hits": [],
                    "rewrite_suggestions": ["说明书保留正式章节。"],
                    "official_safe_patches": [],
                    "attorney_memo": ["未发现内部草稿污染。"],
                }
            )

        if stage == "post_draft_technical_hardness":
            return _json(
                {
                    "role": "technical_hardness",
                    "status": "passed",
                    "blocking_issues": [],
                    "contamination_hits": [],
                    "rewrite_suggestions": ["提交前补充实验或样机数据。"],
                    "official_safe_patches": [],
                    "attorney_memo": ["技术效果需要以证据材料支撑。"],
                }
            )

        if stage == "post_draft_chair_synthesis":
            return _json(
                {
                    "status": "passed",
                    "export_allowed": True,
                    "blocking_issues": [],
                    "contamination_hits": [],
                    "claim_1_rewrite": "",
                    "system_claim_rewrite": "",
                    "abstract_rewrite": "",
                    "description_rewrite_tasks": ["提交前统一附图标号。"],
                    "official_safe_patches": [],
                    "attorney_memo": ["成稿会审通过，仍需正式法律复核。"],
                    "next_actions": ["导出正式稿并交由代理人审阅。"],
                }
            )

        raise KeyError(f"Unhandled v1 smoke LLM stage: {stage}")


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _sample(name: str) -> str:
    path = SAMPLES[name]
    if not path.exists():
        raise AssertionError(f"missing sample: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if len(text) < 200:
        raise AssertionError(f"sample is unexpectedly short: {path}")
    return text


def _ok(response, label: str, expected_status: int = 200) -> Any:
    if response.status_code != expected_status:
        raise AssertionError(f"{label}: expected {expected_status}, got {response.status_code}: {response.text[:1000]}")
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        return response.json()
    return response.text


def _seed_completed_deliberation(client: TestClient, project_id: str) -> str:
    stages = [
        *[
            DeliberationStageResult(
                phase="opening",
                provider_id=provider,
                label=f"opening {provider}",
                payload={"stance": "v1 smoke ready"},
                status="completed",
            )
            for provider in ["codex", "gemini", "claude"]
        ],
        *[
            DeliberationStageResult(
                phase="pair",
                provider_id="codex",
                label=label,
                payload={"resolved_recommendation": "strict release path accepted"},
                status="completed",
            )
            for label in ["pair codex-vs-gemini", "pair codex-vs-claude", "pair gemini-vs-claude"]
        ],
        DeliberationStageResult(
            phase="chair",
            provider_id="codex",
            label="chair synthesis",
            payload={"summary": "v1 smoke strict deliberation completed"},
            status="completed",
        ),
    ]
    run_id = f"v1-smoke-delib-{project_id}"
    app_state = getattr(client.app, "state")
    app_state.store.create_deliberation_run(
        DeliberationRun(
            id=run_id,
            project_id=project_id,
            status="completed",
            providers=["codex", "gemini", "claude"],
            run_mode="full",
            stage_results=stages,
            strategy_brief=PatentStrategyBrief(
                summary="v1 smoke 会审策略：以风险评分、阈值和证据留痕支撑权利要求。",
                claim_strategy=["方法独权覆盖视频输入、目标识别、风险评分和证据留痕闭环。"],
                description_strategy=["说明书补充风险评分变量、证据帧和处置状态的数据结构。"],
                risk_controls=["未验证效果仅作为可行实施方式表达。"],
                agent_consensus="三方会审同意进入确定性 v1 smoke 生成路径。",
            ),
            events=["v1 smoke deliberation seeded without external agents"],
        )
    )
    return run_id


def _prepare_official_export(client: TestClient, project_id: str, label: str) -> str:
    compile_run = _ok(client.post(f"/api/projects/{project_id}/official-compile-runs", json={}), f"{label} official compile")
    if compile_run["status"] != "completed":
        raise AssertionError(f"{label} official compile did not complete: {compile_run}")

    post_review = _ok(client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}), f"{label} post-draft review")
    if post_review["status"] != "completed" or post_review["export_allowed"] is not True:
        raise AssertionError(f"{label} post-draft review did not allow export: {post_review}")

    official_md = _ok(client.get(f"/api/projects/{project_id}/official-export.md"), f"{label} official markdown export")
    if "权利要求书" not in official_md or "附图说明" not in official_md:
        raise AssertionError(f"{label} official export missing required sections")
    return compile_run["id"]


def run_invention_flow(client: TestClient) -> dict[str, str]:
    project = _ok(
        client.post(
            "/api/projects",
            json={
                "name": "施工场景边缘AI安全监控",
                "draft_text": _sample("invention"),
                "patent_type": "invention",
            },
        ),
        "invention create project",
    )
    project_id = project["id"]
    deliberation_id = _seed_completed_deliberation(client, project_id)

    formula_requirement = _ok(client.get(f"/api/projects/{project_id}/formula-requirement"), "invention formula requirement")
    formula_id = None
    if formula_requirement["required"]:
        formula_run = _ok(client.post(f"/api/projects/{project_id}/formula-runs", json={}), "invention formula run")
        if formula_run["status"] != "completed" or not formula_run["package"]:
            raise AssertionError(f"invention formula run incomplete: {formula_run}")
        formula_id = formula_run["id"]

    payload: dict[str, str] = {"deliberation_run_id": deliberation_id}
    if formula_id:
        payload["formula_run_id"] = formula_id
    package = _ok(client.post(f"/api/projects/{project_id}/generate", json=payload), "invention generate")
    if package["deliberation_run_id"] != deliberation_id:
        raise AssertionError("invention package did not retain deliberation id")

    _ok(client.post(f"/api/projects/{project_id}/review"), "invention review")
    _ok(client.post(f"/api/projects/{project_id}/filing-readiness"), "invention filing readiness")
    _ok(client.post(f"/api/projects/{project_id}/claim-defense-worksheets"), "invention claim defense")
    _ok(client.post(f"/api/projects/{project_id}/completion-runs"), "invention completion run")
    compile_id = _prepare_official_export(client, project_id, "invention")
    return {"project_id": project_id, "compile_id": compile_id}


def run_utility_model_flow(client: TestClient) -> dict[str, str]:
    project = _ok(
        client.post(
            "/api/projects",
            json={
                "name": "可调节边缘AI摄像机防护安装支架",
                "draft_text": _sample("utility_model"),
                "patent_type": "utility_model",
            },
        ),
        "utility model create project",
    )
    project_id = project["id"]
    requirement = _ok(client.get(f"/api/projects/{project_id}/formula-requirement"), "utility formula requirement")
    if requirement["required"] is not False:
        raise AssertionError(f"utility model should skip formula requirement: {requirement}")

    package = _ok(client.post(f"/api/projects/{project_id}/generate", json={}), "utility generate")
    if package["deliberation_run_id"] is not None:
        raise AssertionError("utility model package unexpectedly required deliberation")

    _ok(client.post(f"/api/projects/{project_id}/completion-runs"), "utility completion run")
    compile_id = _prepare_official_export(client, project_id, "utility")
    return {"project_id": project_id, "compile_id": compile_id}


def run_external_draft_flow(client: TestClient) -> dict[str, str]:
    project = _ok(
        client.post(
            "/api/projects",
            json={
                "name": "外部稿导入留痕方法",
                "draft_text": "外部初稿导入 v1 smoke 项目。",
                "patent_type": "invention",
            },
        ),
        "external draft create project",
    )
    project_id = project["id"]
    source = _ok(
        client.post(
            f"/api/projects/{project_id}/external-drafts",
            json={
                "source_type": "pasted_text",
                "file_name": "external_draft_invention.md",
                "text": _sample("external_draft"),
            },
        ),
        "external draft source",
    )
    intake = _ok(
        client.post(f"/api/projects/{project_id}/external-drafts/{source['id']}/intake-runs"),
        "external draft intake",
    )
    parsed = intake["parsed_package"]
    if not parsed or not parsed["claims"] or not parsed["description"]:
        raise AssertionError(f"external draft parser did not recover required sections: {intake}")

    confirmed = _ok(
        client.post(
            f"/api/projects/{project_id}/external-draft-intake-runs/{intake['id']}/confirm",
            json={
                "title": parsed["title"] or "一种施工安全视频告警事件留痕方法",
                "abstract": parsed["abstract"] or "本发明公开一种施工安全视频告警事件留痕方法。",
                "claims": parsed["claims"],
                "description": parsed["description"],
                "drawing_description": parsed["drawing_description"] or "图1为方法流程图。",
            },
        ),
        "external draft confirm",
    )
    if confirmed["status"] != "completed":
        raise AssertionError(f"external draft confirm did not complete: {confirmed}")

    _ok(client.post(f"/api/projects/{project_id}/completion-runs"), "external draft completion run")
    compile_id = _prepare_official_export(client, project_id, "external draft")
    bundle = _ok(
        client.get(f"/api/projects/{project_id}/external-draft-review-bundle/report.md"),
        "external draft review bundle",
    )
    if "EXTERNAL_DRAFT_REVIEW_BUNDLE" not in bundle:
        raise AssertionError("external draft review bundle missing marker")
    return {"project_id": project_id, "compile_id": compile_id}


def main() -> int:
    for name in SAMPLES:
        _sample(name)

    with tempfile.TemporaryDirectory(prefix="patentagent-v1-smoke-") as data_dir:
        client = TestClient(
            create_app(
                data_dir=Path(data_dir),
                llm_client=V1SmokeLLM(),
                load_env_file=False,
            )
        )
        health = _ok(client.get("/api/health"), "health")
        if health["ok"] is not True or health["llm_configured"] is not True:
            raise AssertionError(f"unexpected health payload: {health}")

        results = {
            "invention": run_invention_flow(client),
            "utility_model": run_utility_model_flow(client),
            "external_draft": run_external_draft_flow(client),
        }

    print("v1 API smoke passed")
    for workflow, result in results.items():
        print(f"- {workflow}: project={result['project_id']} official_compile={result['compile_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
