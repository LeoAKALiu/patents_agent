from backend.app.external_drafts import create_external_draft_source, parse_external_draft_source
from backend.app.schemas import ProjectRecord
from backend.app.storage import SQLiteStore


def test_store_persists_external_draft_sources_and_intake_runs(tmp_path):
    db_path = tmp_path / "patents_agent.sqlite3"
    store = SQLiteStore(db_path)
    source = create_external_draft_source(
        project_id="project-1",
        source_type="pasted_text",
        text="权利要求书\n1. 一种方法。\n说明书\n本发明涉及数据处理。",
        file_name="pasted.txt",
    )
    stored_source = store.create_external_draft_source(source)
    run = parse_external_draft_source(project_id="project-1", source=stored_source)
    stored_run = store.create_external_draft_intake_run(run)

    loaded_source = store.get_external_draft_source("project-1", source.id)
    assert loaded_source is not None
    assert loaded_source.content_hash == source.content_hash
    assert store.list_external_draft_sources("project-1")[0].id == source.id

    loaded_run = store.get_external_draft_intake_run("project-1", run.id)
    assert loaded_run is not None
    assert loaded_run.working_draft_hash == run.working_draft_hash
    assert store.list_external_draft_intake_runs("project-1", source.id)[0].id == stored_run.id
    assert store.list_external_draft_intake_runs("project-1")[0].id == stored_run.id

    updated = stored_run.model_copy(update={"status": "completed"})
    returned = store.update_external_draft_intake_run(updated)
    assert returned is not None
    assert returned.status == "completed"
    assert store.get_external_draft_intake_run("project-1", run.id).status == "completed"
    missing = stored_run.model_copy(update={"id": "missing-run"})
    assert store.update_external_draft_intake_run(missing) is None

    reopened = SQLiteStore(db_path)
    reopened_source = reopened.get_external_draft_source("project-1", source.id)
    reopened_run = reopened.get_external_draft_intake_run("project-1", run.id)
    assert reopened_source is not None
    assert reopened_run is not None
    assert reopened_source.raw_text == source.raw_text
    assert reopened_run.status == "completed"


def test_delete_project_removes_external_draft_intake_records(tmp_path):
    store = SQLiteStore(tmp_path / "patents_agent.sqlite3")
    project = store.create_project(
        ProjectRecord(id="project-1", name="外部稿项目", draft_text="一种数据处理方法。")
    )
    source = store.create_external_draft_source(
        create_external_draft_source(
            project_id=project.id,
            source_type="pasted_text",
            text="权利要求书\n1. 一种方法。\n说明书\n本发明涉及数据处理。",
            file_name="pasted.txt",
        )
    )
    run = store.create_external_draft_intake_run(parse_external_draft_source(project_id=project.id, source=source))

    assert store.delete_project(project.id) is True
    assert store.get_external_draft_source(project.id, source.id) is None
    assert store.get_external_draft_intake_run(project.id, run.id) is None
