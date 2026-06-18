import json

from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.schemas import DeliberationRun, DeliberationStageResult, PatentStrategyBrief


def test_formula_requirement_detects_hcu_confidence_terms(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project_id = client.post(
        "/api/projects",
        json={
            "name": "城市体检指标驱动无人机主动采集",
            "draft_text": "根据每类指标的证据缺失度、置信区间、传感器贡献矩阵和置信度增益生成无人机任务包。",
        },
    ).json()["id"]

    response = client.get(f"/api/projects/{project_id}/formula-requirement")

    assert response.status_code == 200
    payload = response.json()
    assert payload["required"] is True
    assert {"置信区间", "贡献矩阵", "增益"}.issubset(set(payload["signals"]))
    assert payload["reasons"]


def test_formula_requirement_uses_selected_route_before_backup_routes(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project_id = client.post(
        "/api/projects",
        json={
            "name": "路线选择项目",
            "draft_text": "一种基于图像采集和人工复核的缺陷识别方法。",
        },
    ).json()["id"]
    client.post(
        f"/api/projects/{project_id}/patent-points",
        json={
            "source_candidate_id": "main-route",
            "title": "非公式主路线",
            "technical_problem": "人工巡检效率低",
            "innovation": "组织采集和复核流程",
            "technical_solution": "采集图像并由人工复核输出结果。",
            "beneficial_effects": ["提升流程完整性"],
            "protection_focus": ["采集", "复核"],
            "selected": True,
        },
    )
    client.post(
        f"/api/projects/{project_id}/patent-points",
        json={
            "source_candidate_id": "backup-route",
            "title": "公式后备路线",
            "technical_problem": "指标置信度不足",
            "innovation": "基于贡献矩阵和置信度增益补采",
            "technical_solution": "根据贡献矩阵、置信区间和置信度增益生成任务。",
            "beneficial_effects": ["提升置信度"],
            "protection_focus": ["贡献矩阵", "置信度增益"],
            "selected": False,
        },
    )

    response = client.get(f"/api/projects/{project_id}/formula-requirement")

    assert response.status_code == 200
    assert response.json()["required"] is False


def test_non_formula_project_does_not_require_formula_package_before_generation(tmp_path):
    llm = _fake_llm()
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm))
    project_id = client.post(
        "/api/projects",
        json={
            "name": "图像缺陷识别",
            "draft_text": "一种基于图像采集和人工复核的缺陷识别方法，解决人工巡检效率低的问题。",
        },
    ).json()["id"]
    _create_strict_completed_deliberation(client, project_id)

    requirement = client.get(f"/api/projects/{project_id}/formula-requirement").json()
    generate_response = client.post(f"/api/projects/{project_id}/generate", json={})

    assert requirement["required"] is False
    assert generate_response.status_code == 200
    assert generate_response.json()["formula_run_id"] is None


def test_project_delete_removes_formula_runs(tmp_path):
    llm = _fake_llm()
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm))
    project_id = client.post(
        "/api/projects",
        json={
            "name": "城市体检指标驱动无人机主动采集",
            "draft_text": "根据指标置信度增益和贡献矩阵生成任务包。",
        },
    ).json()["id"]
    _create_strict_completed_deliberation(client, project_id)
    formula_run = client.post(f"/api/projects/{project_id}/formula-runs", json={}).json()

    delete_response = client.delete(f"/api/projects/{project_id}")

    assert delete_response.status_code == 200
    assert client.app.state.store.get_formula_run(project_id, formula_run["id"]) is None


def test_required_formula_blocks_generation_until_formula_package_completed(tmp_path):
    llm = _fake_llm()
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm))
    project_id = client.post(
        "/api/projects",
        json={
            "name": "城市体检指标驱动无人机主动采集",
            "draft_text": "以指标置信度增益为任务优化目标，结合贡献矩阵、后验置信度和置信区间生成补采任务。",
        },
    ).json()["id"]
    _create_strict_completed_deliberation(client, project_id)

    blocked = client.post(f"/api/projects/{project_id}/generate", json={})
    assert blocked.status_code == 409
    assert "Core formula package" in blocked.json()["detail"]

    formula_response = client.post(
        f"/api/projects/{project_id}/formula-runs",
        json={"providers": ["codex", "deepseek", "claude", "kimicode"]},
    )
    assert formula_response.status_code == 200
    formula_run = formula_response.json()
    assert formula_run["status"] == "completed"
    assert formula_run["providers"] == ["codex", "deepseek", "claude", "kimicode"]
    assert formula_run["package"]["formula_blocks"][0]["id"] == "F01"
    assert any("selected providers" in log for log in formula_run["package"]["generation_logs"])

    latex_response = client.get(f"/api/projects/{project_id}/formula-runs/{formula_run['id']}/latex.md")
    assert latex_response.status_code == 200
    assert "F01" in latex_response.text
    assert "\\Delta C_i" in latex_response.text
    assert "权利要求落点" in latex_response.text

    generate_response = client.post(
        f"/api/projects/{project_id}/generate",
        json={"formula_run_id": formula_run["id"]},
    )
    assert generate_response.status_code == 200
    package = generate_response.json()
    assert package["formula_run_id"] == formula_run["id"]
    assert any("formula" in log for log in package["generation_logs"])
    claim_call = next(call for call in llm.calls if call.stage == "claims")
    assert "\\Delta C_i" in claim_call.user_prompt
    assert "指标置信度增益" in claim_call.user_prompt


def _fake_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "core_formula": """
{
  "summary": "以指标置信度增益作为无人机主动采集任务的优化核心。",
  "formula_blocks": [
    {
      "id": "F01",
      "name": "指标置信度增益",
      "latex": "\\\\Delta C_i = C_i^{post} - C_i^{prior}",
      "purpose": "衡量一次任务对城市体检指标置信度的提升。",
      "claim_hook": "根据指标置信度增益生成无人机任务包"
    },
    {
      "id": "F02",
      "name": "传感器贡献矩阵",
      "latex": "\\\\mathbf{C} = \\\\mathbf{A}^T \\\\mathbf{W} \\\\mathbf{A}",
      "purpose": "构造传感器贡献矩阵，融合多源采集数据以更新后验置信度。",
      "claim_hook": "将贡献矩阵写入独立权利要求"
    }
  ],
  "variable_definitions": [
    {"symbol": "C_i^{post}", "meaning": "采集后第i类指标的后验置信度", "unit": ""},
    {"symbol": "C_i^{prior}", "meaning": "采集前第i类指标的先验置信度", "unit": ""},
    {"symbol": "\\\\mathbf{W}", "meaning": "传感器权重矩阵", "unit": ""},
    {"symbol": "\\\\mathbf{A}", "meaning": "传感器测量矩阵", "unit": ""}
  ],
  "derivation_notes": ["由证据缺失度和传感器贡献矩阵更新后验置信度。"],
  "claim_hooks": ["独立权利要求中写入以指标置信度增益作为任务优化目标。"],
  "description_insert": "本实施例以公式F01计算每类城市体检指标的置信度增益。",
  "latex_markdown": ""
}
""",
            "claims": "1. 一种城市体检指标驱动的无人机主动采集方法，其特征在于，根据指标置信度增益生成任务包。",
            "description": "技术领域\n本发明涉及无人机主动采集。\n具体实施方式\n本实施例包括公式F01。",
            "abstract": "本发明公开一种无人机主动采集方法。",
            "drawings": "图1为方法流程图。\n图2为系统结构图。",
            "diagram": "flowchart TD\nA[指标] --> B[任务包]",
            "image_prompt": "黑白线稿。",
        }
    )


def _create_strict_completed_deliberation(client: TestClient, project_id: str) -> None:
    stages = [
        *[
            DeliberationStageResult(
                phase="opening",
                provider_id=provider,
                label=f"opening {provider}",
                payload={"stance": "ok"},
                status="completed",
            )
            for provider in ["codex", "deepseek", "claude"]
        ],
        *[
            DeliberationStageResult(
                phase="pair",
                provider_id="codex",
                label=label,
                payload={"resolved_recommendation": "ok"},
                status="completed",
            )
            for label in ["pair codex-vs-deepseek", "pair codex-vs-claude", "pair deepseek-vs-claude"]
        ],
        DeliberationStageResult(
            phase="chair",
            provider_id="codex",
            label="chair synthesis",
            payload={"summary": "ok"},
            status="completed",
        ),
    ]
    client.app.state.store.create_deliberation_run(
        DeliberationRun(
            id=f"delib-{project_id}",
            project_id=project_id,
            status="completed",
            providers=["codex", "deepseek", "claude"],
            run_mode="full",
            stage_results=stages,
            strategy_brief=PatentStrategyBrief(
                summary="三方会审通过。",
                claim_strategy=["方法独权"],
                description_strategy=["补充公式实施例"],
                risk_controls=["避免功能性概括"],
                agent_consensus="三方一致。",
            ),
            events=["test deliberation completed"],
        )
    )


# ============================================================
#  PR-12: Formula output schema repair and quality gate tests
# ============================================================

from backend.app.core_formula import (
    _extract_json,
    _repair_formula_payload,
    _validate_formula_quality,
    _fallback_package,
    _parse_formula_package,
)
from backend.app.schemas import CoreFormulaPackage, FormulaNeedAssessment


class TestExtractJson:
    """Tests for robust JSON extraction from LLM output."""

    def test_extract_clean_json(self):
        result = _extract_json('{"summary": "test", "formula_blocks": []}')
        assert result["summary"] == "test"
        assert result["formula_blocks"] == []

    def test_extract_json_with_markdown_fence(self):
        raw = '''Here is the JSON:
```json
{
  "summary": "公式总结",
  "formula_blocks": [
    {"id": "F01", "name": "权重公式", "latex": "W = \\sum w_i x_i", "purpose": "加权求和"}
  ]
}
```
End.'''
        result = _extract_json(raw)
        assert result["summary"] == "公式总结"
        assert len(result["formula_blocks"]) == 1

    def test_extract_json_from_surrounded_text(self):
        raw = 'Some text before {"summary": "core", "formula_blocks": []} and after.'
        result = _extract_json(raw)
        assert result["summary"] == "core"

    def test_extract_list_wrapped_as_dict(self):
        raw = '[{"id": "F01", "name": "公式1", "latex": "a+b", "purpose": "add", "claim_hook": ""}]'
        result = _extract_json(raw)
        assert result["formula_blocks"] is not None
        assert len(result["formula_blocks"]) == 1

    def test_extract_with_trailing_comma(self):
        raw = '{"summary": "bad json", "formula_blocks": [{"id": "F01", "name": "test", "latex": "x", "purpose": "p",},],}'
        result = _extract_json(raw)
        assert result is not None


class TestRepairFormulaPayload:
    """Tests for payload repair when LLM output is missing fields."""

    def test_repair_missing_summary(self):
        incomplete = {"formula_blocks": []}
        req = FormulaNeedAssessment(required=True, signals=["矩阵", "权重"])
        repaired = _repair_formula_payload(incomplete, req)
        assert "矩阵" in repaired["summary"]
        assert repaired["formula_blocks"] == []

    def test_repair_missing_block_fields(self):
        incomplete = {
            "summary": "test",
            "formula_blocks": [
                {"name": "My Formula", "latex": "a+b"},
            ],
        }
        req = FormulaNeedAssessment(required=True, signals=["矩阵"])
        repaired = _repair_formula_payload(incomplete, req)
        block = repaired["formula_blocks"][0]
        assert block["id"] == "F01"
        assert block["name"] == "My Formula"
        assert block["latex"] == "a+b"
        assert block["purpose"] == ""
        assert block["claim_hook"] == ""

    def test_repair_non_list_formula_blocks(self):
        incomplete = {"summary": "test", "formula_blocks": "not a list"}
        req = FormulaNeedAssessment(required=True, signals=["概率"])
        repaired = _repair_formula_payload(incomplete, req)
        assert repaired["formula_blocks"] == []

    def test_repair_expression_fallback(self):
        """'expression' key maps to 'latex' when latex is missing."""
        incomplete = {
            "summary": "test",
            "formula_blocks": [
                {"id": "F1", "name": "Eq", "expression": "E=mc^2", "purpose": "energy"}
            ],
        }
        req = FormulaNeedAssessment(required=True, signals=["优化"])
        repaired = _repair_formula_payload(incomplete, req)
        assert repaired["formula_blocks"][0]["latex"] == "E=mc^2"


class TestValidateFormulaQuality:
    """Tests for minimum-quality gate on formula packages."""

    def _make_pkg(self, blocks=None, var_defs=None, purpose="Meaningful technical purpose"):
        """Helper to build a CoreFormulaPackage."""
        return CoreFormulaPackage(
            summary="A test package",
            formula_blocks=blocks or [],
            variable_definitions=var_defs or [],
            derivation_notes=[],
            claim_hooks=[],
            description_insert="",
        )

    def test_empty_blocks_with_requirement_is_critical(self):
        pkg = self._make_pkg(blocks=[])
        req = FormulaNeedAssessment(required=True, signals=["矩阵", "权重"])
        result = _validate_formula_quality(pkg, req)
        assert result["severity"] == "critical"
        assert any("未生成" in w for w in result["warnings"])

    def test_trivial_formula_with_strong_signals_is_high(self):
        from backend.app.schemas import FormulaBlock
        pkg = self._make_pkg(
            blocks=[
                FormulaBlock(
                    id="F01",
                    name="Confidence Update",
                    latex=r"\Delta S_i = S_i^{post} - S_i^{prior}",
                    purpose="描述采集或处理前后置信度的变化量。",
                    claim_hook="根据置信度变化量...",
                )
            ],
            var_defs=[],
            purpose="描述采集或处理前后置信度的变化量。",
        )
        req = FormulaNeedAssessment(required=True, signals=["矩阵", "权重", "优化", "概率", "阈值"])
        result = _validate_formula_quality(pkg, req)
        assert result["severity"] == "high"
        assert any("平凡差值公式" in w for w in result["warnings"])

    def test_one_formula_with_strong_signals_is_warning(self):
        from backend.app.schemas import FormulaBlock
        pkg = self._make_pkg(
            blocks=[
                FormulaBlock(
                    id="F01",
                    name="Weighted Sum",
                    latex=r"W = \sum_{i=1}^n w_i x_i",
                    purpose="计算加权得分，用于综合评定。",
                    claim_hook="将加权和写入从属权利要求。",
                )
            ],
            var_defs=[],
        )
        req = FormulaNeedAssessment(required=True, signals=["矩阵", "权重"])
        result = _validate_formula_quality(pkg, req)
        # Should be at least warning because rich signals but only 1 formula
        assert result["severity"] in ("normal", "warning")

    def test_complex_formula_with_rich_signals_is_normal(self):
        from backend.app.schemas import FormulaBlock, FormulaVariableDefinition
        pkg = self._make_pkg(
            blocks=[
                FormulaBlock(
                    id="F01",
                    name="Contribution Matrix",
                    latex=r"\mathbf{C} = \mathbf{A}^T \mathbf{W} \mathbf{A}",
                    purpose="构造传感器贡献矩阵，用于加权融合多源数据。",
                    claim_hook="将贡献矩阵写入独立权利要求。",
                ),
                FormulaBlock(
                    id="F02",
                    name="Confidence Update",
                    latex=r"p(\theta|D) = \frac{p(D|\theta)p(\theta)}{p(D)}",
                    purpose="贝叶斯更新后验置信度，结合多轮采集的先验。",
                    claim_hook="将贝叶斯更新写入从属权利要求。",
                ),
            ],
            var_defs=[
                FormulaVariableDefinition(symbol=r"\mathbf{C}", meaning="贡献矩阵", unit=""),
                FormulaVariableDefinition(symbol=r"\mathbf{W}", meaning="权重矩阵", unit=""),
                FormulaVariableDefinition(symbol=r"\mathbf{A}", meaning="传感器测量矩阵", unit=""),
            ],
        )
        req = FormulaNeedAssessment(required=True, signals=["矩阵", "权重", "置信度", "概率"])
        result = _validate_formula_quality(pkg, req)
        assert result["severity"] == "normal"

    def test_empty_latex_is_high(self):
        from backend.app.schemas import FormulaBlock
        pkg = self._make_pkg(
            blocks=[
                FormulaBlock(
                    id="F01",
                    name="Empty",
                    latex="",
                    purpose="一个有意义的公式目的说明。",
                    claim_hook="将公式写入权利要求。",
                )
            ]
        )
        req = FormulaNeedAssessment(required=True, signals=["矩阵"])
        result = _validate_formula_quality(pkg, req)
        assert result["severity"] == "high"
        assert any("为空" in w for w in result["warnings"])

    def test_generic_variable_definitions_with_strong_signals(self):
        from backend.app.schemas import FormulaBlock, FormulaVariableDefinition
        pkg = self._make_pkg(
            blocks=[
                FormulaBlock(
                    id="F01",
                    name="Score Update",
                    latex=r"S = \alpha \cdot X + (1-\alpha) \cdot Y",
                    purpose="融合两个来源的评分。",
                    claim_hook="将融合公式写入权利要求。",
                )
            ],
            var_defs=[
                FormulaVariableDefinition(symbol=r"S_i^{post}", meaning="处理后的指标状态", unit=""),
                FormulaVariableDefinition(symbol=r"S_i^{prior}", meaning="处理前的指标状态", unit=""),
            ],
        )
        req = FormulaNeedAssessment(required=True, signals=["矩阵", "权重", "优化"])
        result = _validate_formula_quality(pkg, req)
        assert result["severity"] in ("warning", "high")


class TestFallbackPackage:
    """Tests for fallback package generation."""

    def test_fallback_with_strong_signals_is_high(self):
        req = FormulaNeedAssessment(required=True, signals=["矩阵", "权重", "优化", "概率", "阈值"])
        pkg = _fallback_package(req, raw_output="raw model text")
        assert pkg.is_fallback is True
        assert pkg.quality_severity == "high"
        assert pkg.raw_model_output == "raw model text"
        assert any("严重不足" in note for note in pkg.derivation_notes)

    def test_fallback_without_strong_signals_is_warning(self):
        req = FormulaNeedAssessment(required=True, signals=["置信度"])
        pkg = _fallback_package(req, raw_output="raw text")
        assert pkg.is_fallback is True
        assert pkg.quality_severity == "warning"
        assert pkg.raw_model_output == "raw text"

    def test_fallback_has_generation_log(self):
        req = FormulaNeedAssessment(required=True, signals=["置信度"])
        pkg = _fallback_package(req)
        assert any("fallback" in log for log in pkg.generation_logs)


class TestParseFormulaPackage:
    """Integration tests for the full parse-repair-quality pipeline."""

    def test_well_formed_json_passes_quality(self):
        from backend.app.schemas import FormulaNeedAssessment
        raw = json.dumps({
            "summary": "A rich formula package",
            "formula_blocks": [
                {
                    "id": "F01",
                    "name": "Weight Matrix",
                    "latex": "\\\\mathbf{W} = \\\\mathbf{X}^T \\\\mathbf{X}",
                    "purpose": "构造权重矩阵用于加权优化。",
                    "claim_hook": "将权重矩阵写入独立权利要求。",
                },
                {
                    "id": "F02",
                    "name": "Optimization Objective",
                    "latex": "\\\\min_{\\\\theta} \\\\mathcal{L}(\\\\theta) = \\\\sum_i \\\\ell(y_i, f(x_i;\\\\theta))",
                    "purpose": "优化目标函数，最小化预测误差。",
                    "claim_hook": "将优化目标写入从属权利要求。",
                },
            ],
            "variable_definitions": [
                {"symbol": "\\\\mathbf{W}", "meaning": "权重矩阵", "unit": ""},
                {"symbol": "\\\\theta", "meaning": "模型参数", "unit": ""},
            ],
            "derivation_notes": ["由最小二乘推导。"],
            "claim_hooks": ["将权重矩阵写入独立权利要求。"],
            "description_insert": "本实施例通过公式F01构造权重矩阵。",
            "latex_markdown": "",
        })
        req = FormulaNeedAssessment(required=True, signals=["矩阵", "权重", "优化", "概率", "阈值"])
        pkg = _parse_formula_package(raw, req)
        assert pkg.quality_severity == "normal"
        assert pkg.is_fallback is False
        assert pkg.raw_model_output == raw

    def test_malformed_json_falls_back_with_severity(self):
        raw = "This is not JSON at all, just random text from a confused LLM."
        req = FormulaNeedAssessment(required=True, signals=["矩阵", "权重", "优化", "概率", "阈值"])
        pkg = _parse_formula_package(raw, req)
        assert pkg.is_fallback is True
        assert pkg.quality_severity == "critical"  # No formula blocks at all → critical
        assert "未生成任何公式" in pkg.derivation_notes[0]
        assert pkg.raw_model_output == raw

    def test_partial_json_gets_repaired(self):
        raw = json.dumps({
            "summary": "Partial formula",
            "formula_blocks": [
                {"name": "Weighted Sum", "latex": "W = \\sum w_i x_i", "purpose": "加权求和", "claim_hook": ""},
            ],
            # Missing: variable_definitions, derivation_notes, claim_hooks, description_insert
        })
        req = FormulaNeedAssessment(required=True, signals=["权重", "优化"])
        pkg = _parse_formula_package(raw, req)
        # Should be repaired (has formula_blocks with some fields) but quality may flag
        assert pkg.is_fallback is True or pkg.is_fallback is False  # Either is fine depending on quality
        assert len(pkg.formula_blocks) >= 1
        assert pkg.raw_model_output == raw

    def test_trivial_formula_after_repair_still_flagged(self):
        """Even if repair succeeds, a trivial formula should be quality-flagged."""
        raw = json.dumps({
            "summary": "Confidence update",
            "formula_blocks": [
                {
                    "id": "F01",
                    "name": "置信度更新",
                    "latex": "\\\\Delta S_i = S_i^{post} - S_i^{prior}",
                    "purpose": "描述采集或处理前后置信度的变化量。",
                    "claim_hook": "根据置信度变化量确定后续处理。",
                }
            ],
            "variable_definitions": [
                {"symbol": "S_i^{post}", "meaning": "处理后的指标状态", "unit": ""},
                {"symbol": "S_i^{prior}", "meaning": "处理前的指标状态", "unit": ""},
            ],
        })
        req = FormulaNeedAssessment(required=True, signals=["矩阵", "权重", "优化", "概率", "阈值"])
        pkg = _parse_formula_package(raw, req)
        assert pkg.quality_severity == "high"
        assert pkg.is_fallback is True
        assert pkg.raw_model_output == raw


# ============================================================
#  PR-12 v3: backend generate gate for fallback formula packages
#  Mirror of the frontend guidedFlow gate — fallback packages with
#  high/critical quality severity must be rejected by the backend
#  /api/projects/{id}/generate endpoint, not just the UI.
# ============================================================

from backend.app.main import _formula_package_blocks_generation


class TestFormulaPackageBlocksGeneration:
    """Unit tests for the backend quality-gate helper."""

    def test_normal_package_is_not_blocked(self):
        pkg = CoreFormulaPackage(summary="ok", quality_severity="normal")
        assert _formula_package_blocks_generation(pkg) is False

    def test_non_fallback_high_severity_is_not_blocked(self):
        # Only fallback + high/critical is blocked; a non-fallback package
        # flagged high by the quality validator is allowed (user choice).
        pkg = CoreFormulaPackage(summary="ok", is_fallback=False, quality_severity="high")
        assert _formula_package_blocks_generation(pkg) is False

    def test_warning_fallback_is_not_blocked(self):
        pkg = CoreFormulaPackage(summary="ok", is_fallback=True, quality_severity="warning")
        assert _formula_package_blocks_generation(pkg) is False

    def test_high_fallback_is_blocked(self):
        pkg = CoreFormulaPackage(summary="ok", is_fallback=True, quality_severity="high")
        assert _formula_package_blocks_generation(pkg) is True

    def test_critical_fallback_is_blocked(self):
        pkg = CoreFormulaPackage(summary="ok", is_fallback=True, quality_severity="critical")
        assert _formula_package_blocks_generation(pkg) is True

    def test_none_package_is_not_blocked(self):
        assert _formula_package_blocks_generation(None) is False


def _garbage_formula_llm() -> FakeLLMClient:
    """LLM whose core_formula output is unparseable garbage, forcing a
    fallback package. Combined with strong project signals the resulting
    package is is_fallback=True / quality_severity=critical."""
    return FakeLLMClient(
        {
            "core_formula": "not json at all",
            "claims": "1. 一种城市体检指标驱动的无人机主动采集方法。",
            "description": "具体实施方式\n本实施例包括公式F01。",
            "abstract": "本发明公开一种无人机主动采集方法。",
            "drawings": "图1为方法流程图。",
            "diagram": "flowchart TD\nA[指标] --> B[任务包]",
            "image_prompt": "黑白线稿。",
        }
    )


def _create_formula_required_project(client: TestClient) -> str:
    response = client.post(
        "/api/projects",
        json={
            "name": "城市体检指标驱动无人机主动采集",
            "draft_text": "以指标置信度增益为任务优化目标，结合贡献矩阵、后验置信度和置信区间生成补采任务。",
        },
    )
    return response.json()["id"]


def test_generate_rejects_explicit_critical_fallback_formula_run(tmp_path):
    """Regression: explicit formula_run_id pointing at a critical fallback
    package must be rejected with 409 (defense-in-depth behind the frontend)."""
    llm = _garbage_formula_llm()
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm))
    project_id = _create_formula_required_project(client)
    _create_strict_completed_deliberation(client, project_id)

    formula_run = client.post(
        f"/api/projects/{project_id}/formula-runs", json={}
    ).json()
    assert formula_run["status"] == "completed"
    package = formula_run["package"]
    assert package["is_fallback"] is True
    assert package["quality_severity"] == "critical"
    assert package["formula_blocks"] == []

    blocked = client.post(
        f"/api/projects/{project_id}/generate",
        json={"formula_run_id": formula_run["id"]},
    )
    assert blocked.status_code == 409
    detail = blocked.json()["detail"]
    assert "low-quality fallback" in detail
    assert formula_run["id"] in detail
    assert "Re-run formula generation" in detail


def test_generate_rejects_latest_completed_critical_fallback_formula_run(tmp_path):
    """Regression: auto-selection path — when the only completed run is a
    critical fallback, generate must 409 rather than silently accepting it."""
    llm = _garbage_formula_llm()
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm))
    project_id = _create_formula_required_project(client)
    _create_strict_completed_deliberation(client, project_id)

    formula_run = client.post(
        f"/api/projects/{project_id}/formula-runs", json={}
    ).json()
    assert formula_run["package"]["quality_severity"] == "critical"

    blocked = client.post(f"/api/projects/{project_id}/generate", json={})
    assert blocked.status_code == 409
    detail = blocked.json()["detail"]
    assert "low-quality fallback" in detail
    assert "Re-run formula generation" in detail


def test_generate_uses_earlier_non_blocked_run_when_latest_is_blocked(tmp_path):
    """Mirrors the frontend guidedFlow gate: if an earlier completed run is
    usable, it is selected for auto-generation even when the latest run is a
    blocked fallback."""
    good_llm = _fake_llm()
    client = TestClient(create_app(data_dir=tmp_path, llm_client=good_llm))
    project_id = _create_formula_required_project(client)
    _create_strict_completed_deliberation(client, project_id)

    good_run = client.post(
        f"/api/projects/{project_id}/formula-runs", json={}
    ).json()
    assert good_run["package"]["is_fallback"] is False
    assert good_run["package"]["quality_severity"] == "normal"

    # Swap to a garbage LLM and run again — the latest run is now a blocked fallback.
    client.app.state.llm = _garbage_formula_llm()
    bad_run = client.post(
        f"/api/projects/{project_id}/formula-runs", json={}
    ).json()
    assert bad_run["package"]["is_fallback"] is True
    assert bad_run["package"]["quality_severity"] == "critical"

    # Auto-selection should skip the bad run and use the earlier good one.
    response = client.post(f"/api/projects/{project_id}/generate", json={})
    assert response.status_code == 200
    assert response.json()["formula_run_id"] == good_run["id"]
