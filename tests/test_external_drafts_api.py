from fastapi.testclient import TestClient
from docx import Document

from backend.app.external_drafts import create_external_draft_source, parse_external_draft_source
from backend.app.main import create_app
from backend.app.schemas import DraftPackage, ProjectRecord
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


def test_external_draft_api_creates_source_runs_intake_and_confirms_package(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project = client.post(
        "/api/projects",
        json={"name": "外部稿项目", "draft_text": "外部初稿导入项目。"},
    ).json()

    source_response = client.post(
        f"/api/projects/{project['id']}/external-drafts",
        json={
            "source_type": "pasted_text",
            "file_name": "draft.txt",
            "text": (
                "发明名称\n一种外部稿处理方法\n"
                "说明书\n本发明涉及专利初稿处理。\n"
            ),
        },
    )
    assert source_response.status_code == 200
    source = source_response.json()
    assert source["content_hash"]

    intake_response = client.post(f"/api/projects/{project['id']}/external-drafts/{source['id']}/intake-runs")
    assert intake_response.status_code == 200
    intake = intake_response.json()
    assert intake["status"] == "needs_review"
    assert intake["parsed_package"]["title"] == "一种外部稿处理方法"

    blank_confirm_response = client.post(
        f"/api/projects/{project['id']}/external-draft-intake-runs/{intake['id']}/confirm",
        json={
            "title": "一种外部稿处理方法",
            "abstract": "本发明公开一种外部稿处理方法。",
            "claims": "   ",
            "description": "本发明涉及专利初稿处理。",
            "drawing_description": "图1为外部稿处理流程图。",
        },
    )
    assert blank_confirm_response.status_code == 422

    confirm_response = client.post(
        f"/api/projects/{project['id']}/external-draft-intake-runs/{intake['id']}/confirm",
        json={
            "title": "一种外部稿处理方法",
            "abstract": "本发明公开一种外部稿处理方法。",
            "claims": "1. 一种外部稿处理方法，其特征在于，解析外部专利初稿并生成工作稿。",
            "description": "本发明涉及专利初稿处理。系统保存原始稿并生成内部工作稿。",
            "drawing_description": "图1为外部稿处理流程图。",
        },
    )
    assert confirm_response.status_code == 200
    confirmed = confirm_response.json()
    assert confirmed["status"] == "completed"
    assert confirmed["working_draft_hash"]

    project_after = client.get(f"/api/projects/{project['id']}").json()
    assert project_after["package"]["title"] == "一种外部稿处理方法"
    assert "保存原始稿" in project_after["package"]["description"]

    list_sources = client.get(f"/api/projects/{project['id']}/external-drafts").json()
    assert list_sources["sources"][0]["id"] == source["id"]

    list_runs = client.get(f"/api/projects/{project['id']}/external-drafts/{source['id']}/intake-runs").json()
    assert list_runs["runs"][0]["id"] == intake["id"]

    get_run_response = client.get(f"/api/projects/{project['id']}/external-draft-intake-runs/{intake['id']}")
    assert get_run_response.status_code == 200
    assert get_run_response.json()["id"] == intake["id"]


def test_external_draft_docx_upload_creates_source(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project = client.post(
        "/api/projects",
        json={"name": "DOCX外部稿", "draft_text": "DOCX外部稿导入。"},
    ).json()
    docx_path = tmp_path / "external.docx"
    document = Document()
    document.add_paragraph("权利要求书")
    document.add_paragraph("1. 一种DOCX导入方法。")
    document.add_paragraph("说明书")
    document.add_paragraph("本发明涉及DOCX解析。")
    document.save(docx_path)

    response = client.post(
        f"/api/projects/{project['id']}/external-drafts/upload",
        files={
            "file": (
                "external.docx",
                docx_path.read_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["source_type"] == "docx_file"
    assert "DOCX导入方法" in response.json()["raw_text"]


def test_external_draft_confirmed_package_runs_quality_and_bundle_report(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project = client.post(
        "/api/projects",
        json={"name": "外部稿提质", "draft_text": "外部初稿导入项目。"},
    ).json()
    client.app.state.store.update_project_package(
        project["id"],
        DraftPackage(
            title="一种外部稿提质方法",
            abstract="本发明公开一种外部稿提质方法。",
            claims="1. 一种方法，其特征在于，接收外部初稿并生成修改建议。",
            description="本实施例接收外部初稿。",
            drawing_description="图1为流程图。",
            mermaid="",
            image_prompt="",
            review_findings=[],
            citations=[],
            generation_logs=["external_draft_intake: confirmed from run run-1"],
        ),
    )

    completion_response = client.post(f"/api/projects/{project['id']}/completion-runs")
    assert completion_response.status_code == 200

    score_response = client.post(f"/api/projects/{project['id']}/score-improvement", json={"max_rounds": 1})
    assert score_response.status_code == 200

    compile_response = client.post(f"/api/projects/{project['id']}/official-compile-runs", json={})
    assert compile_response.status_code == 200
    assert compile_response.json()["status"] in {"completed", "blocked"}

    report_response = client.get(f"/api/projects/{project['id']}/external-draft-review-bundle/report.md")
    assert report_response.status_code == 200
    assert "EXTERNAL_DRAFT_REVIEW_BUNDLE" in report_response.text
    assert "initial_score" in report_response.text
    assert "official_compile_run_id" in report_response.text


def test_external_draft_review_bundle_pairs_intake_run_with_its_source(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project = client.post(
        "/api/projects",
        json={"name": "外部稿配对", "draft_text": "外部初稿导入项目。"},
    ).json()

    source_with_run = client.post(
        f"/api/projects/{project['id']}/external-drafts",
        json={
            "source_type": "pasted_text",
            "file_name": "with-run.txt",
            "text": (
                "发明名称\n一种外部稿处理方法\n"
                "权利要求书\n1. 一种外部稿处理方法。\n"
                "说明书\n本发明涉及专利初稿处理。\n"
            ),
        },
    ).json()
    intake = client.post(
        f"/api/projects/{project['id']}/external-drafts/{source_with_run['id']}/intake-runs"
    ).json()
    newer_source = client.post(
        f"/api/projects/{project['id']}/external-drafts",
        json={
            "source_type": "pasted_text",
            "file_name": "newer-without-run.txt",
            "text": "发明名称\n一种后续外部稿\n说明书\n本发明涉及后续稿。",
        },
    ).json()

    report_response = client.get(f"/api/projects/{project['id']}/external-draft-review-bundle/report.md")

    assert report_response.status_code == 200
    assert f"- source_id: {source_with_run['id']}" in report_response.text
    assert f"- intake_run_id: {intake['id']}" in report_response.text
    assert f"- source_id: {newer_source['id']}" not in report_response.text
