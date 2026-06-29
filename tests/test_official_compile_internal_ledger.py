import pytest

from backend.app.official_compile import OfficialDraftCompiler
from backend.app.schemas import DraftPackage


def _draft_package(**overrides: str) -> DraftPackage:
    package = DraftPackage(
        title="一种城市体检指标驱动无人机主动采集方法",
        abstract="本发明公开了一种基于城市体检指标生成无人机采集任务的方法。",
        claims="1. 一种城市体检指标驱动无人机主动采集方法，其特征在于，生成任务包。",
        description="本发明涉及无人机任务规划技术领域，能够根据城市体检指标生成采集任务。",
        drawing_description="图1为本发明方法的流程图。",
        mermaid="flowchart TD\nA-->B",
        image_prompt="黑白线稿",
    )
    return package.model_copy(update=overrides)


@pytest.mark.parametrize(
    ("field", "marker", "pattern"),
    [
        ("description", "revision_ledger: patched claim wording", "revision_ledger"),
        ("claims", "source_ledger: internal source table", "source_ledger"),
        ("abstract", "修订记录：根据复核意见改写摘要", "修订记录"),
    ],
)
def test_compiler_blocks_internal_ledger_markers(field: str, marker: str, pattern: str) -> None:
    package = _draft_package(**{field: f"{marker}\n{getattr(_draft_package(), field)}"})

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(
        item["category"] == "residual_internal_text" and item["pattern"] == pattern
        for item in run.blocked_items
    )
