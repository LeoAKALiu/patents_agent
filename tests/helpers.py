from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.schemas import KnowledgeReadinessRun


def seed_knowledge_ready(client: TestClient, project_id: str, score: int = 86) -> KnowledgeReadinessRun:
    run = KnowledgeReadinessRun(
        id=f"knowledge-ready-{project_id}",
        project_id=project_id,
        status="completed",
        providers=["codex", "gemini", "claude"],
        score=score,
        score_before_bonus=score,
        threshold=80,
        proceed_allowed=score > 80,
        deep_research_report_uploaded=True,
        processed_material_count=1,
        related_reference_count=0,
        corpus_document_count=0,
        corpus_chunk_count=0,
        role_results=[],
        blocking_issues=[] if score > 80 else ["知识完备度评分需大于 80 分。"],
        recommendations=[],
    )
    client.app.state.store.create_knowledge_readiness_run(run)
    return run
