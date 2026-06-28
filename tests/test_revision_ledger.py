from pathlib import Path

from backend.app.revision_ledger import create_revision_record
from backend.app.schemas import DraftPackage
from backend.app.storage import SQLiteStore


def _package(description: str) -> DraftPackage:
    return DraftPackage(
        title="一种方法",
        abstract="摘要",
        claims="1. 一种方法。",
        description=description,
        drawing_description="图1。",
        mermaid="flowchart TD\nA-->B",
        image_prompt="黑白线稿",
    )


def test_revision_ledger_record_hashes_and_sections() -> None:
    before = _package("旧说明书")
    after = _package("新说明书")

    record = create_revision_record(
        project_id="p1",
        baseline_package=before,
        updated_package=after,
        revision_kind="correction",
        user_intent_summary="修正说明书事实",
        affected_sections=["description"],
        prior_art_changed=False,
        protection_scope_changed=False,
        artifact_refs=["draft-package"],
    )

    assert record.project_id == "p1"
    assert record.baseline_artifact_hash
    assert record.new_artifact_hash
    assert record.baseline_artifact_hash != record.new_artifact_hash
    assert record.affected_sections == ["description"]
    assert record.revision_kind == "correction"


def test_sqlite_store_persists_revision_ledger_records(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "patents.sqlite3")
    before = _package("旧说明书")
    after = _package("新说明书")
    first = create_revision_record(
        project_id="p1",
        baseline_package=before,
        updated_package=after,
        revision_kind="material_merge",
        user_intent_summary="合并 DeepResearch 材料",
        affected_sections=["description", "claims"],
        prior_art_changed=True,
        protection_scope_changed=True,
        artifact_refs=["run:abc"],
    )
    second = create_revision_record(
        project_id="p1",
        baseline_package=after,
        updated_package=_package("第三版说明书"),
        revision_kind="protection_focus",
        user_intent_summary="强化第五章保护点",
        affected_sections=["claims"],
        protection_scope_changed=True,
    )

    store.create_revision_ledger_record(first)
    store.create_revision_ledger_record(second)
    records = store.list_revision_ledger_records("p1")

    assert [record.id for record in records] == [second.id, first.id]
    assert records[0].revision_kind == "protection_focus"
    assert records[1].prior_art_changed is True
