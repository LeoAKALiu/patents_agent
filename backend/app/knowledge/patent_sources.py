from __future__ import annotations

from backend.app.schemas import (
    AgentSearchPlan,
    CnipaQueryPack,
    CnipaQueryPackStrategy,
    PatentSourceCapability,
    SearchIntent,
)

CNIPA_OFFICIAL_EXPORT_SOURCE = "cnipa_official_export"
CNIPA_AUTHORIZED_API_SOURCE = "cnipa_authorized_api"
CNIPA_LEGACY_EPUB_SOURCE = "cnipa_epub"
WIPO_PATENTSCOPE_SOURCE = "wipo_patentscope"
GOOGLE_PATENTS_SOURCE = "google_patents"


def list_patent_source_capabilities() -> list[PatentSourceCapability]:
    return [
        PatentSourceCapability(
            source_id=CNIPA_OFFICIAL_EXPORT_SOURCE,
            display_name="CNIPA 官方导出",
            jurisdictions=["CN"],
            modes=["official_export"],
            availability="manual_import",
            trusted_patent_source=True,
            evidence_origin="official_export",
            setup_hint="从 CNIPA 官方检索系统导出 CSV/XLSX/ZIP 后导入 GrantAtlas。",
        ),
        PatentSourceCapability(
            source_id=CNIPA_LEGACY_EPUB_SOURCE,
            display_name="CNIPA EPUB legacy helper",
            jurisdictions=["CN"],
            modes=["live_search"],
            availability="config_required",
            trusted_patent_source=True,
            evidence_origin="legacy_helper",
            setup_hint="高级遗留辅助检索能力，需在常规工作流之外单独配置后启用。",
        ),
        PatentSourceCapability(
            source_id=WIPO_PATENTSCOPE_SOURCE,
            display_name="WIPO Patentscope",
            jurisdictions=["WO"],
            modes=["live_search"],
            availability="available",
            trusted_patent_source=True,
            evidence_origin="public_web",
            setup_hint="用于国际公开文献补充检索。",
        ),
        PatentSourceCapability(
            source_id=GOOGLE_PATENTS_SOURCE,
            display_name="Google Patents",
            jurisdictions=["CN", "WO", "US", "EP"],
            modes=["live_search"],
            availability="config_required",
            trusted_patent_source=True,
            evidence_origin="public_web",
            setup_hint="通过 PATENT_ENABLE_GOOGLE_PATENTS_FALLBACK 显式启用。",
        ),
        PatentSourceCapability(
            source_id=CNIPA_AUTHORIZED_API_SOURCE,
            display_name="CNIPA 授权 API",
            jurisdictions=["CN"],
            modes=["authorized_api"],
            availability="unavailable",
            trusted_patent_source=True,
            evidence_origin="authorized_api",
            setup_hint="获得正式接口授权后接入。",
        ),
    ]


def build_cnipa_query_pack(intent: SearchIntent | None, plan: AgentSearchPlan | None) -> CnipaQueryPack:
    project_id = plan.project_id if plan else (intent.project_id if intent else "")
    plan_id = plan.id if plan else ""
    intent_id = intent.id if intent else (plan.intent_id if plan else "")
    filters = plan.filters if plan else {}
    strategies = [
        CnipaQueryPackStrategy(
            strategy_group_id=group.id,
            label=group.label,
            purpose=group.purpose,
            queries=list(group.queries),
        )
        for group in (plan.strategy_groups if plan else [])
    ]
    return CnipaQueryPack(
        project_id=project_id,
        plan_id=plan_id,
        intent_id=intent_id,
        technical_object=intent.technical_object if intent else "",
        technical_problem=intent.technical_problem if intent else "",
        technical_means=intent.technical_means if intent else "",
        keywords_zh=list(intent.keywords_zh if intent else []),
        negative_keywords=list(intent.negative_keywords if intent else []),
        ipc_candidates=list(intent.ipc_candidates if intent else []),
        cpc_candidates=list(intent.cpc_candidates if intent else []),
        date_range=str(filters.get("date_range") or (intent.date_range if intent else "")),
        strategies=strategies,
    )
