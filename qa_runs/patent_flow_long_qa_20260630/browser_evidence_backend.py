from __future__ import annotations

import os
from pathlib import Path

from backend.app.agents.adapters.fake import FakeAgentRuntime
from backend.app.llm import FakeLLMClient
from backend.app.main import create_app


def _fake_agent_runtime() -> FakeAgentRuntime:
    return FakeAgentRuntime(
        task_payloads={
            "opening codex": {
                "stance": "Codex 建议以低置信区域热力图触发补采任务作为主线。",
                "claim_scope": ["置信度热力图", "补采任务包", "任务状态回写"],
                "risks": ["需要补充热力图计算规则。"],
                "recommendations": ["将任务状态回写写入独立权利要求闭环。"],
            },
            "opening deepseek": {
                "stance": "DeepSeek 建议限定城市体检无人机补采场景以增强创造性。",
                "claim_scope": ["低置信区域判定", "航线生成", "采集参数配置"],
                "risks": ["避免仅表达业务调度规则。"],
                "recommendations": ["补强阈值判定和航线生成的技术细节。"],
            },
            "opening kimicode": {
                "stance": "KimiCode 建议把补采任务包和回写状态机作为系统权利要求支撑。",
                "claim_scope": ["任务包字段", "状态机", "数据完整性提升"],
                "risks": ["说明书需给出可执行实施例。"],
                "recommendations": ["加入补采覆盖率与重复巡检下降的效果描述。"],
            },
            "pair codex-vs-deepseek": {
                "conflict_level": 0.2,
                "agreements": ["以热力图触发补采任务为主线。"],
                "disagreements": [],
                "resolved_recommendation": "独权覆盖热力图、补采任务包和状态回写。",
            },
            "pair codex-vs-kimicode": {
                "conflict_level": 0.1,
                "agreements": ["系统权利要求需要覆盖状态回写闭环。"],
                "disagreements": [],
                "resolved_recommendation": "说明书补充任务包字段和状态机实施例。",
            },
            "pair deepseek-vs-kimicode": {
                "conflict_level": 0.2,
                "agreements": ["需要技术化航线生成规则。"],
                "disagreements": [],
                "resolved_recommendation": "把阈值判定和航线生成规则写成可执行步骤。",
            },
            "chair synthesis": {
                "summary": "三方一致建议以低置信区域热力图驱动无人机补采任务生成为主线。",
                "claim_strategy": ["方法独权覆盖热力图、补采任务包和状态回写闭环。"],
                "description_strategy": ["补充热力图计算、航线生成规则和任务包字段。"],
                "risk_controls": ["避免纯业务调度表述，加入可执行算法步骤。"],
                "agent_consensus": "会审通过，可进入初稿生成。",
            },
        }
    )


def _fake_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "disclosure_scan": """
{
  "summary": "城市体检无人机补采任务项目",
  "materials_summary": "项目围绕无人机补采任务、低置信区域识别、航线生成和任务状态回写。",
  "technical_keywords": ["无人机补采", "置信度热力图", "任务回写"],
  "implementation_gaps": []
}
""",
            "patent_points": """
{
  "candidates": [
    {
      "id": "browser-point-1",
      "title": "低置信区域驱动的无人机补采任务生成",
      "technical_problem": "城市体检数据在低置信区域容易出现漏采和重复巡检。",
      "innovation": "根据多源指标置信度热力图识别低置信区域并自动生成补采任务包。",
      "technical_solution": "计算城市体检指标的空间置信度热力图，对低于阈值的区域生成补采航线、采集参数和任务回写状态。",
      "beneficial_effects": ["减少重复巡检", "提升低置信区域数据完整性"],
      "protection_focus": ["置信度热力图", "补采任务包", "任务状态回写"],
      "grantability_score": 0.82,
      "rationale": "技术问题、处理链路和效果闭环完整。"
    }
  ],
  "selected_candidate_id": "browser-point-1"
}
""",
            "prior_art_terms": '["无人机 补采 置信度 热力图", "城市体检 低置信 区域 航线"]',
            "prior_art_relevance": """
{
  "prior_art_differences": "区别在于由城市体检指标置信度热力图触发补采任务包，并回写任务状态形成闭环。",
  "hits": [],
  "claim_charts": []
}
""",
            "disclosure_body": (
                "# 技术交底书\n\n"
                "## 技术方案\n"
                "系统计算城市体检指标的空间置信度热力图，对低于阈值的区域生成无人机补采航线、"
                "采集参数和任务回写状态。\n\n"
                "## 有益效果\n"
                "减少重复巡检并提升低置信区域数据完整性。"
            ),
            "disclosure_mermaid": "flowchart TD\nA[城市体检指标] --> B[置信度热力图]\nB --> C[无人机补采任务包]",
            "disclosure_image_prompt": "黑白专利线稿，展示城市体检指标、置信度热力图和无人机补采任务包。",
            "disclosure_self_check": "[]",
            "core_formula": r"""
{
  "summary": "以空间置信度热力图中的低置信区域得分作为补采任务触发依据。",
  "formula_blocks": [
    {
      "id": "F01",
      "name": "低置信区域补采触发分值",
      "latex": "R_i = 1 - C_i,\\quad T_i = \\mathbb{1}(R_i \\ge \\theta)",
      "purpose": "根据区域置信度计算补采风险分值并判定是否生成补采任务。",
      "claim_hook": "根据补采触发分值生成包含航线和采集参数的无人机补采任务包。"
    }
  ],
  "variable_definitions": [
    {"symbol": "C_i", "meaning": "第 i 个城市体检区域的数据置信度", "unit": ""},
    {"symbol": "R_i", "meaning": "第 i 个区域的补采风险分值", "unit": ""},
    {"symbol": "\\theta", "meaning": "补采触发阈值", "unit": ""}
  ],
  "derivation_notes": ["置信度越低，补采风险分值越高；达到阈值时触发补采任务。"],
  "claim_hooks": ["将 F01 写入从属权利要求，限定低置信区域触发补采任务包。"],
  "description_insert": "在一个实施例中，系统计算每个城市体检区域的置信度 C_i，并基于 F01 判定是否生成补采任务。",
  "latex_markdown": ""
}
""",
            "claims": (
                "1. 一种基于低置信区域热力图自动生成无人机补采任务的方法，其特征在于，包括："
                "获取城市体检指标数据并计算各区域的数据置信度；根据所述数据置信度生成空间置信度热力图；"
                "当目标区域的补采风险分值达到补采触发阈值时，生成包含补采航线、采集参数和任务标识的无人机补采任务包；"
                "将所述无人机补采任务包下发至无人机执行端，并在补采数据回传后回写任务状态。"
            ),
            "description": "本发明颠覆了固定航线模式，并通过置信度热力图生成无人机采集任务。",
            "drawings": "图1为系统流程图。",
            "diagram": "flowchart TD\nA[城市体检指标] --> B[置信度热力图] --> C[无人机任务包]",
            "abstract": "本发明公开一种按置信度主动采集的方法。",
            "image_prompt": "黑白线稿，展示城市体检指标、置信度热力图和无人机任务包。",
            "post_draft_claims_reviewer": """
{
  "role": "claims_reviewer",
  "status": "passed",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": [],
  "official_safe_patches": [],
  "attorney_memo": []
}
""",
            "post_draft_spec_cleaner": """
{
  "role": "spec_cleaner",
  "status": "passed",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": [],
  "official_safe_patches": [],
  "attorney_memo": []
}
""",
            "post_draft_technical_hardness": """
{
  "role": "technical_hardness",
  "status": "passed",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": ["补充量化实施例。"],
  "official_safe_patches": [],
  "attorney_memo": []
}
""",
            "post_draft_chair_synthesis": """
{
  "status": "passed",
  "export_allowed": true,
  "blocking_issues": [],
  "contamination_hits": [],
  "claim_1_rewrite": "",
  "system_claim_rewrite": "",
  "abstract_rewrite": "",
  "description_rewrite_tasks": [],
  "official_safe_patches": [],
  "attorney_memo": [],
  "next_actions": ["可以导出正式稿。"]
}
""",
        }
    )


DATA_DIR = Path(
    os.environ.get(
        "PATENTAGENT_QA_DATA_DIR",
        "qa_runs/patent_flow_long_qa_20260630/current-artifacts/browser-smoke-current/data",
    )
)

app = create_app(
    data_dir=DATA_DIR,
    llm_client=_fake_llm(),
    agent_runtime=_fake_agent_runtime(),
    load_env_file=False,
)
