from fastapi.testclient import TestClient
import json

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.schemas import (
    ClaimDefenseWorksheet,
    DraftPackage,
    EvidenceBinding,
    EvidenceBindingSourceType,
    EvidenceVerificationStatus,
    FeatureRecord,
)


class RaisingLLMClient:
    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        raise RuntimeError("provider timeout")


def test_claim_defense_worksheet_records_feature_classifications():
    feature = FeatureRecord(
        feature_id="f1",
        text="IFC洞口扣减拓扑与工程量清单回链",
        classification="core_combo",
        claim_refs=["1"],
        description_refs=["说明书第5段"],
        figure_refs=["图4"],
        prior_art_refs=["CN119131262A"],
        risk_tags=["组合创造性"],
    )
    worksheet = ClaimDefenseWorksheet(
        id="w1",
        project_id="p1",
        status="draft",
        source="generated_package",
        feature_records=[feature],
        defense_recommendations=["独权中应组合主张IFC洞口扣减与清单回链。"],
        support_gaps=["缺少IfcRelVoidsElement伪代码片段。"],
    )

    assert worksheet.feature_records[0].classification == "core_combo"
    assert worksheet.support_gaps == ["缺少IfcRelVoidsElement伪代码片段。"]


from backend.app.storage import SQLiteStore


def test_store_persists_claim_defense_worksheet_history(tmp_path):
    store = SQLiteStore(tmp_path / "patents_agent.sqlite3")
    older = ClaimDefenseWorksheet(id="w1", project_id="p1", source="draft", notes=["old"])
    newer = ClaimDefenseWorksheet(id="w2", project_id="p1", source="generated_package", notes=["new"])

    store.create_claim_defense_worksheet(older)
    store.create_claim_defense_worksheet(newer)

    worksheets = store.list_claim_defense_worksheets("p1")
    assert [worksheet.id for worksheet in worksheets] == ["w2", "w1"]
    assert store.get_claim_defense_worksheet("p1", "w2").notes == ["new"]


def test_claim_defense_rules_extract_feature_records_without_llm():
    from backend.app.claim_defense import generate_claim_defense_worksheet

    worksheet = generate_claim_defense_worksheet(
        project_id="p1",
        package=_package_with_claims(),
        disclosures=[],
        patent_points=[],
        llm=None,
    )

    assert worksheet.source == "generated_package"
    assert worksheet.feature_records
    assert any("IFC洞口扣减拓扑" in record.text for record in worksheet.feature_records)
    assert any("工程量清单回链" in record.text for record in worksheet.feature_records)
    assert worksheet.defense_recommendations


def test_claim_defense_api_persists_multiple_versions(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False))
    project_id = client.post(
        "/api/projects",
        json={"name": "防线工作表测试", "draft_text": "一种建筑外立面逆建模方法。"},
    ).json()["id"]
    point_response = client.post(
        f"/api/projects/{project_id}/patent-points",
        json={
            "title": "IFC洞口扣减拓扑与工程量清单回链",
            "technical_problem": "既有工程量统计缺少可核验的洞口扣减依据。",
            "innovation": "将IFC洞口扣减拓扑与工程量清单回链形成闭环校验。",
            "technical_solution": "解析IfcRelVoidsElement关系，生成洞口扣减拓扑，并将扣减结果回链至工程量清单。",
            "beneficial_effects": ["提高工程量清单核验可靠性"],
            "protection_focus": ["IFC洞口扣减拓扑", "工程量清单回链"],
            "evidence_status": "verified",
            "source_type": "user",
            "feasibility_basis": "已有IFC样例和清单核验脚本。",
        },
    )
    assert point_response.status_code == 200
    client.app.state.store.update_project_package(project_id, _package_with_claims())

    first = client.post(f"/api/projects/{project_id}/claim-defense-worksheets")
    second = client.post(f"/api/projects/{project_id}/claim-defense-worksheets")

    assert first.status_code == 200
    assert second.status_code == 200
    list_response = client.get(f"/api/projects/{project_id}/claim-defense-worksheets")
    assert list_response.status_code == 200
    worksheets = list_response.json()["worksheets"]
    assert len(worksheets) == 2
    detail_response = client.get(f"/api/projects/{project_id}/claim-defense-worksheets/{worksheets[0]['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["feature_records"]


def test_claim_defense_invalid_llm_output_falls_back_to_rules():
    from backend.app.claim_defense import generate_claim_defense_worksheet

    worksheet = generate_claim_defense_worksheet(
        project_id="p1",
        package=_package_with_claims(),
        disclosures=[],
        patent_points=[],
        llm=FakeLLMClient({"claim_defense_features": "not-json"}),
    )

    assert worksheet.feature_records
    assert "LLM特征抽取失败" in worksheet.notes[0]


def test_claim_defense_valid_llm_output_is_merged_with_rule_features():
    from backend.app.claim_defense import generate_claim_defense_worksheet

    worksheet = generate_claim_defense_worksheet(
        project_id="p1",
        package=_package_with_claims(),
        disclosures=[],
        patent_points=[],
        llm=FakeLLMClient(
            {
                "claim_defense_features": json.dumps(
                    {
                        "feature_records": [
                            {
                                "feature_id": "llm-1",
                                "text": "LLM补充的从属防线特征",
                                "classification": "dependent_fallback",
                                "claim_refs": ["3"],
                            }
                        ]
                    },
                    ensure_ascii=False,
                )
            }
        ),
    )

    texts = [record.text for record in worksheet.feature_records]
    assert any("LLM补充的从属防线特征" in text for text in texts)
    assert any("IFC洞口扣减拓扑" in text for text in texts)
    assert any("工程量清单回链" in text for text in texts)


def test_claim_defense_attaches_evidence_refs_when_supplied():
    from backend.app.claim_defense import generate_claim_defense_worksheet

    package = DraftPackage(
        title="声学视觉融合巡检方法",
        abstract="通过声学异常窗口触发视觉局部复检。",
        claims="1. 一种巡检方法，其特征在于，声学异常窗口触发视觉局部复检。",
        description="说明书记载声学异常窗口触发视觉局部复检的执行流程。",
        drawing_description="图1示出声学异常窗口触发视觉局部复检流程。",
        mermaid="",
        image_prompt="",
    )
    worksheet = generate_claim_defense_worksheet(
        project_id="p1",
        package=package,
        disclosures=[],
        patent_points=[],
        llm=None,
        evidence_bindings=[
            EvidenceBinding(
                evidence_id="E100",
                source_type=EvidenceBindingSourceType.PRIOR_ART,
                source_id="CN100A",
                source_label="一种声学巡检方法",
                quote="未公开声学异常窗口触发视觉局部复检",
                confidence=0.74,
                verification_status=EvidenceVerificationStatus.RETRIEVED,
                citable=True,
            ),
            EvidenceBinding(
                evidence_id="M100",
                source_type=EvidenceBindingSourceType.PROJECT_MATERIAL,
                source_id="material-1",
                source_label="实验记录.md",
                quote="声学异常窗口触发视觉局部复检",
                confidence=0.82,
                verification_status=EvidenceVerificationStatus.USER_PROVIDED,
            ),
            EvidenceBinding(
                evidence_id="P100",
                source_type=EvidenceBindingSourceType.PATENT_POINT,
                source_id="point-1",
                source_label="声学窗口触发视觉复检",
                quote="声学异常窗口触发视觉局部复检",
                confidence=0.55,
                verification_status=EvidenceVerificationStatus.FEASIBLE_UNVERIFIED,
            ),
        ],
    )

    record = next(item for item in worksheet.feature_records if "声学异常窗口触发视觉局部复检" in item.text)
    assert record.evidence_refs == ["E100", "M100", "P100"]
    assert "prior_art:CN100A" in record.source_refs
    assert "project_material:material-1" in record.source_refs
    assert "patent_point:point-1" in record.source_refs
    assert record.prior_art_refs == ["CN100A"]
    assert "M100" in record.support_explanation
    assert "P100" in record.support_explanation
    assert "不升级为已验证支撑" in record.support_explanation


def test_claim_defense_model_generated_evidence_does_not_upgrade_classification():
    from backend.app.claim_defense import generate_claim_defense_worksheet

    package = DraftPackage(
        title="普通采集方法",
        abstract="采集设备温度。",
        claims="1. 一种采集方法，其特征在于，读取设备温度数据。",
        description="说明书记载读取设备温度数据。",
        drawing_description="",
        mermaid="",
        image_prompt="",
    )
    worksheet = generate_claim_defense_worksheet(
        project_id="p1",
        package=package,
        disclosures=[],
        patent_points=[],
        llm=None,
        evidence_bindings=[
            EvidenceBinding(
                evidence_id="E200",
                source_type=EvidenceBindingSourceType.PATENT_POINT,
                source_id="model-point",
                source_label="模型建议",
                quote="读取设备温度数据",
                confidence=0.95,
                verification_status=EvidenceVerificationStatus.MODEL_GENERATED,
            )
        ],
    )

    record = next(item for item in worksheet.feature_records if "读取设备温度数据" in item.text)
    assert record.evidence_refs == ["E200"]
    assert record.classification == "known_base"
    assert "不升级为已验证支撑" in record.support_explanation


def test_claim_defense_api_falls_back_when_llm_is_missing(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project_id = client.post(
        "/api/projects",
        json={"name": "未配置LLM防线测试", "draft_text": "一种建筑外立面逆建模方法。"},
    ).json()["id"]
    client.app.state.store.update_project_package(project_id, _package_with_claims())

    response = client.post(f"/api/projects/{project_id}/claim-defense-worksheets")

    assert response.status_code == 200
    worksheet = response.json()
    assert worksheet["feature_records"]
    assert not worksheet["notes"] or "LLM特征抽取失败" in worksheet["notes"][0]


def test_claim_defense_api_creates_draft_source_without_package(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False))
    project_id = client.post(
        "/api/projects",
        json={"name": "草稿防线测试", "draft_text": "一种建筑外立面逆建模方法。"},
    ).json()["id"]

    response = client.post(f"/api/projects/{project_id}/claim-defense-worksheets")

    assert response.status_code == 200
    worksheet = response.json()
    assert worksheet["source"] == "draft"
    assert worksheet["defense_recommendations"]
    assert worksheet["support_gaps"]

    list_response = client.get(f"/api/projects/{project_id}/claim-defense-worksheets")
    assert list_response.status_code == 200
    assert list_response.json()["worksheets"][0]["id"] == worksheet["id"]


def test_claim_defense_api_falls_back_on_provider_runtime_failure(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=RaisingLLMClient(), load_env_file=False))
    project_id = client.post(
        "/api/projects",
        json={"name": "Provider失败防线测试", "draft_text": "一种建筑外立面逆建模方法。"},
    ).json()["id"]
    client.app.state.store.update_project_package(project_id, _package_with_claims())

    response = client.post(f"/api/projects/{project_id}/claim-defense-worksheets")

    assert response.status_code == 200
    worksheet = response.json()
    assert worksheet["feature_records"]
    assert "LLM特征抽取失败" in worksheet["notes"][0]


def _package_with_claims() -> DraftPackage:
    return DraftPackage(
        title="建筑外立面逆建模工程量校验方法",
        abstract="本发明公开一种将IFC洞口扣减拓扑与工程量清单回链结合的逆建模方法。",
        claims=(
            "1. 一种建筑外立面逆建模工程量校验方法，其特征在于，"
            "解析IFC模型中的IfcRelVoidsElement关系以形成IFC洞口扣减拓扑，"
            "并将洞口扣减结果与工程量清单回链，形成闭环校验。\n"
            "2. 根据权利要求1所述的方法，其中根据增量更新结果输出置信度。"
        ),
        description=(
            "说明书第5段记载：解析IFC模型中的IfcRelVoidsElement关系以形成IFC洞口扣减拓扑。"
            "说明书第6段记载：将洞口扣减结果与工程量清单回链，形成闭环校验。"
        ),
        drawing_description="图1示出IFC洞口扣减拓扑与工程量清单回链流程。",
        mermaid="flowchart TD\nA[IFC]-->B[洞口扣减拓扑]\nB-->C[工程量清单回链]",
        image_prompt="IFC opening deduction topology bill of quantities backlink",
    )
