from __future__ import annotations

import os
from pathlib import Path

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app


def _fake_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": "好的，根据您提供的交底书，权利要求1描述了一种旧的方法。\n*(注：内部备注)**",
            "description": "本发明颠覆了固定航线模式，并通过置信度热力图生成无人机采集任务。",
            "drawings": "图1为系统流程图。",
            "diagram": "flowchart TD\nA[城市体检指标] --> B[置信度热力图] --> C[无人机任务包]",
            "abstract": "本发明公开一种按置信度主动采集的方法。",
            "image_prompt": "黑白线稿，展示城市体检指标、置信度热力图和无人机任务包。",
            "post_draft_claims_reviewer": """
{
  "role": "claims_reviewer",
  "status": "blocked",
  "blocking_issues": ["权利要求1含内部引导语 好的，根据"],
  "contamination_hits": ["好的，根据", "注：内部备注"],
  "rewrite_suggestions": ["替换为干净权利要求。"],
  "official_safe_patches": [],
  "attorney_memo": []
}
""",
            "post_draft_spec_cleaner": """
{
  "role": "spec_cleaner",
  "status": "blocked",
  "blocking_issues": ["标题存在重复词汇方法方法"],
  "contamination_hits": ["方法方法"],
  "rewrite_suggestions": ["删除重复词汇。"],
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
  "status": "blocked",
  "export_allowed": false,
  "blocking_issues": ["标题存在重复词汇方法方法", "权利要求1含内部引导语 好的，根据"],
  "contamination_hits": ["好的，根据", "方法方法", "注：内部备注"],
  "claim_1_rewrite": "",
  "system_claim_rewrite": "",
  "abstract_rewrite": "",
  "description_rewrite_tasks": [],
  "official_safe_patches": [],
  "attorney_memo": [],
  "next_actions": ["修复 blocking 后重新会审。"]
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

app = create_app(data_dir=DATA_DIR, llm_client=_fake_llm(), load_env_file=False)
