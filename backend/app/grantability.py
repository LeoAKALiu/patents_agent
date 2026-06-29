"""V1.1 PR2: Grantability claim chart and patentability attack analysis.

Generates a structured grantability report from disclosure data, prior-art
hits, deliberation strategy, and draft claims.  Includes:

* Closest prior-art identification and claim charting.
* Novelty distinction analysis with per-feature attacks.
* Inventive-step (obviousness) attack combinations.
* Feature placement: independent-claim required / dependent-claim optional /
  description-only support / should-delete.
* Low-evidence / no-prior-art cases always fail closed.

See :issue:`42`.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from backend.app.schemas import (
    ClaimChartItem,
    DeepResearchPacket,
    DisclosurePackage,
    DisclosureRun,
    DraftPackage,
    FeaturePlacement,
    GrantabilityClaimChartRow,
    GrantabilityReport,
    InventiveStepAttackCombo,
    NoveltyAttack,
    PatentPointCandidate,
    ProjectKnowledgeState,
    PatentStrategyBrief,
    PriorArtHit,
)

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

_EVIDENCE_QUALITY_RANKS: dict[str, int] = {"verified": 3, "unverified": 2, "low": 1}
_ATTACK_STRENGTH_RANKS: dict[str, int] = {"strong": 4, "moderate": 3, "weak": 2, "none": 1}


def generate_grantability_report(
    *,
    project_id: str,
    package: DraftPackage,
    disclosures: list[DisclosureRun],
    patent_points: list[PatentPointCandidate],
    strategy_brief: PatentStrategyBrief | None = None,
    deep_research_packets: list[DeepResearchPacket] | None = None,
    project_knowledge_state: ProjectKnowledgeState | None = None,
) -> GrantabilityReport:
    """Produce a structured grantability analysis for one invention project.

    The report MUST be generated before final official draft export so the
    user can review claim-strength evidence and adjust scope.
    """
    prior_art_hits = _collect_prior_art(disclosures, patent_points, deep_research_packets)
    claim_chart_items = _collect_claim_chart_items(patent_points)

    # 1. Build the claim-chart rows (feature → prior-art mapping).
    rows = _build_claim_chart(claim_chart_items, prior_art_hits, package, patent_points)

    # 2. Extract novelty attacks from the closest prior art.
    novelty_attacks = _build_novelty_attacks(rows, prior_art_hits)

    # 3. Build inventive-step attack combos.
    inventive_step_attacks = _build_inventive_step_attacks(rows, prior_art_hits, strategy_brief)

    # 4. Evidence-quality gating — low-evidence cases fail closed.
    evidence_quality = _aggregate_evidence_quality(prior_art_hits, patent_points, disclosures)
    low_evidence_flags: list[str] = []
    fail_closed = False

    if evidence_quality == "low":
        low_evidence_flags.append(
            "未检索到足够现有技术文献。授权前景分析不能给出高概率结论。"
        )
        fail_closed = True
    elif evidence_quality == "unverified":
        low_evidence_flags.append(
            "部分现有技术引用未经验证（模型生成或文件缺失）。请人工复核后调整授权概率。"
        )

    if not prior_art_hits or len(prior_art_hits) < 2:
        low_evidence_flags.append("现有技术引用数量不足（<2），创造性攻击基础薄弱。")
        fail_closed = True

    knowledge_status = project_knowledge_state.status if project_knowledge_state else None
    knowledge_flags = set(project_knowledge_state.quality_flags if project_knowledge_state else [])

    if project_knowledge_state is None:
        low_evidence_flags.append("项目语料库未就绪，授权前景不能给出高置信结论。")
        fail_closed = True
    elif knowledge_status in {
        "not_started",
        "search_plan_pending",
        "search_running",
        "candidates_pending",
        "corpus_building",
    }:
        low_evidence_flags.append(
            f"项目语料库状态为{knowledge_status}，尚不能支撑高置信授权判断。"
        )
        fail_closed = True
    elif knowledge_status == "stale":
        low_evidence_flags.append("项目语料库已过期，需要补充检索后再确认授权前景。")
        fail_closed = True

    if "synthetic_evidence" in knowledge_flags:
        low_evidence_flags.append("项目语料库仅含合成或占位内容，不能支撑授权前景结论。")
        fail_closed = True
    if "empty_corpus" in knowledge_flags:
        low_evidence_flags.append("项目语料库为空，现有技术证据不足。")
        fail_closed = True
    if "insufficient_corpus" in knowledge_flags:
        low_evidence_flags.append("项目语料库证据不足，需补充检索和入库文献。")
        fail_closed = True
    if project_knowledge_state and project_knowledge_state.document_count < 2:
        low_evidence_flags.append("项目语料库入库文献少于 2 件，现有技术证据不足。")
        fail_closed = True

    # 5. Determine overall grantability status.
    status = _compute_overall_status(
        rows, novelty_attacks, inventive_step_attacks, fail_closed, evidence_quality
    )

    # 6. Build risk summary.
    risk_summary = _build_risk_summary(rows, novelty_attacks, inventive_step_attacks)

    # 7. Recommendation.
    recommendation = _build_recommendation(status, rows, fail_closed, strategy_brief)

    return GrantabilityReport(
        id=uuid.uuid4().hex,
        project_id=project_id,
        status=status,
        overall_assessment=_build_overall_assessment(status, rows, fail_closed, low_evidence_flags),
        closest_prior_art_summary=_closest_prior_art_summary(prior_art_hits),
        claim_chart=rows,
        novelty_attacks=novelty_attacks,
        inventive_step_attacks=inventive_step_attacks,
        risk_summary=risk_summary,
        low_evidence_flags=low_evidence_flags,
        fail_closed=fail_closed,
        recommendation=recommendation,
        source_ledger_citations=_build_source_citations(prior_art_hits, disclosures),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _collect_prior_art(
    disclosures: list[DisclosureRun],
    patent_points: list[PatentPointCandidate],
    deep_research_packets: list[DeepResearchPacket] | None,
) -> list[PriorArtHit]:
    """Gather all prior-art hits from disclosures and deep-research packets."""
    hits: list[PriorArtHit] = []
    seen: set[str] = set()
    for d in disclosures:
        if d.package:
            for hit in d.package.prior_art_hits:
                keys = _prior_art_hit_keys(hit)
                if keys and not keys.intersection(seen):
                    seen.update(keys)
                    hits.append(hit)
    # Optionally pull hits referenced by patent-point claim charts.
    for pt in patent_points:
        for item in pt.claim_chart:
            # Create a synthetic PriorArtHit for chart items with prior-art refs.
            keys = _prior_art_identity_keys(item.prior_art_id, item.prior_art_title)
            if item.prior_art_id and keys and not keys.intersection(seen):
                seen.update(keys)
                hits.append(
                    PriorArtHit(
                        id=item.prior_art_id,
                        source="claim_chart",
                        query="",
                        title=item.prior_art_title,
                        publication_number=None,
                        url="",
                        abstract="",
                    )
                )
    if deep_research_packets:
        for packet in deep_research_packets:
            for finding in packet.findings:
                for ref in finding.evidence:
                    keys = _prior_art_identity_keys(ref.publication_number, ref.title, ref.url)
                    if keys and not keys.intersection(seen):
                        seen.update(keys)
                        hits.append(
                            PriorArtHit(
                                id=ref.publication_number or ref.title,
                                source=ref.source,
                                query=ref.query,
                                title=ref.title,
                                publication_number=ref.publication_number,
                                url=ref.url,
                                abstract="",
                            )
                        )
    return hits


def _prior_art_identity_keys(*values: str | None) -> set[str]:
    keys: set[str] = set()
    for value in values:
        cleaned = (value or "").strip()
        if cleaned:
            keys.add(cleaned.upper())
    return keys


def _prior_art_hit_keys(hit: PriorArtHit) -> set[str]:
    return _prior_art_identity_keys(hit.publication_number, hit.title, hit.id, hit.url)


def _collect_claim_chart_items(
    patent_points: list[PatentPointCandidate],
) -> list[ClaimChartItem]:
    items: list[ClaimChartItem] = []
    for pt in patent_points:
        items.extend(pt.claim_chart)
    return items


def _build_claim_chart(
    chart_items: list[ClaimChartItem],
    prior_art_hits: list[PriorArtHit],
    package: DraftPackage,
    patent_points: list[PatentPointCandidate],
) -> list[GrantabilityClaimChartRow]:
    """Build claim-chart rows mapping each feature to its closest prior art."""
    rows: list[GrantabilityClaimChartRow] = []

    # Derive features from claim chart items + independently from patent points.
    features: dict[str, list[str]] = {}  # feature_text → prior_art_refs
    for item in chart_items:
        all_features = item.overlapping_features + item.differentiating_features
        for feat in all_features:
            if feat not in features:
                features[feat] = []
            if item.prior_art_id:
                features[feat].append(item.prior_art_id)

    # If nothing from chart items, extract features from patent points.
    if not features and patent_points:
        for pt in patent_points:
            # Use protection_focus as feature approximations.
            for focus in pt.protection_focus:
                if focus not in features:
                    features[focus] = []
            # Also use innovation text segments.
            sentences = re.split(r"[。；\n]", pt.innovation)
            for s in sentences:
                s = s.strip()
                if len(s) > 6:
                    if s not in features:
                        features[s] = []

    # If still nothing, extract from claims text.
    if not features:
        claims_text = (package.claims or "").strip()
        if claims_text:
            features[claims_text[:80]] = []

    claim_number = 1
    for feat_text, pa_refs in features.items():
        # Map prior-art refs to titles.
        pa_titles: list[str] = []
        for ref in pa_refs:
            ref_keys = _prior_art_identity_keys(ref)
            matching = [h for h in prior_art_hits if ref_keys.intersection(_prior_art_hit_keys(h))]
            if matching:
                pa_titles.append(matching[0].title or matching[0].id)
            else:
                pa_titles.append(ref)

        # Determine placement.
        placement = _classify_feature_placement(feat_text, patent_points, package)

        # Build novelty attack if closest prior art exists.
        novelty_attack = None
        for pa in prior_art_hits:
            pa_keys = _prior_art_hit_keys(pa)
            if any(_prior_art_identity_keys(ref).intersection(pa_keys) for ref in pa_refs):
                novelty_attack = _build_single_novelty_attack(feat_text, pa)
                break

        # Support status from patent points.
        support_status = _determine_support_status(feat_text, patent_points, package)

        rows.append(
            GrantabilityClaimChartRow(
                claim_ref=str(claim_number),
                feature_text=feat_text,
                feature_placement=placement,
                closest_prior_art_refs=pa_titles[:5],
                novelty_distinction=(
                    novelty_attack.overlap_analysis if novelty_attack else ""
                ),
                novelty_attack=novelty_attack,
                inventive_step_combos=[],
                support_status=support_status,
                overbreadth_risk=_has_overbreadth_risk(feat_text),
                recommended_scope_adjustment=(
                    _scope_advice(placement, support_status)
                ),
            )
        )
        claim_number += 1

    # Second pass: build inventive-step combos.
    _attach_inventive_step_combos(rows, prior_art_hits)

    return rows


def _classify_feature_placement(
    feat_text: str,
    patent_points: list[PatentPointCandidate],
    package: DraftPackage,
) -> FeaturePlacement:
    """Classify where a feature belongs in the claim/description hierarchy."""
    claims_text = (package.claims or "").lower()
    desc_text = (package.description or "").lower()
    feat_lower = feat_text.lower()

    # Check if feature appears (or its segments appear) in claims.
    if _text_appears_in(feat_lower, claims_text):
        # Check for dependent claim markers.
        if any(kw in feat_lower for kw in ("所述", "进一步", "优选", "further", "preferably")):
            return FeaturePlacement.DEPENDENT_CLAIM_OPTIONAL
        return FeaturePlacement.INDEPENDENT_CLAIM_REQUIRED

    # Check if feature is in the description.
    if _text_appears_in(feat_lower, desc_text):
        return FeaturePlacement.DESCRIPTION_ONLY_SUPPORT

    # If feature relates to a patent point with selected=True, try harder.
    for pt in patent_points:
        if pt.selected and (feat_lower in pt.innovation.lower() or feat_lower in pt.technical_solution.lower()):
            if _text_appears_in(pt.innovation.lower(), claims_text) or _text_appears_in(pt.technical_solution.lower(), claims_text):
                return FeaturePlacement.INDEPENDENT_CLAIM_REQUIRED
            if _text_appears_in(pt.innovation.lower(), desc_text) or _text_appears_in(pt.technical_solution.lower(), desc_text):
                return FeaturePlacement.DESCRIPTION_ONLY_SUPPORT

    # Feature not found in claims or description — flag for deletion.
    return FeaturePlacement.SHOULD_DELETE


def _text_appears_in(needle: str, haystack: str) -> bool:
    """Check if needle or any of its significant sub-tokens appears in haystack."""
    if needle in haystack:
        return True
    # Split needle into meaningful tokens (Chinese characters, alphanumeric).
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}", needle)
    if not tokens:
        return False
    # Require at least half of the tokens to appear in the haystack.
    found = sum(1 for t in tokens if t.lower() in haystack)
    return found >= max(1, len(tokens) // 2)


def _determine_support_status(
    feat_text: str,
    patent_points: list[PatentPointCandidate],
    package: DraftPackage,
) -> str:
    """Determine how well a feature is supported by the specification."""
    # Check patent points for evidence.
    for pt in patent_points:
        if feat_text in pt.innovation or feat_text in pt.technical_solution:
            if pt.evidence_status == "verified":
                return "strong"
            if pt.evidence_status == "feasible_unverified":
                return "partial"
    # Fallback: check if feature text appears in description.
    desc = (package.description or "")
    if feat_text in desc:
        # Check for supporting detail markers.
        detail_count = sum(
            1
            for marker in ("数据结构", "字段", "参数", "伪代码", "步骤", "算法", "公式", "实施例")
            if marker in desc
        )
        if detail_count >= 3:
            return "strong"
        if detail_count >= 1:
            return "partial"
        return "weak"
    return "missing"


def _has_overbreadth_risk(feat_text: str) -> bool:
    """Heuristic: very broad functional language without structural detail."""
    broad_markers = ("包括", "包含", "获取", "输出", "基于", "采用", "using", "based on")
    detail_markers = ("结构", "模块", "单元", "阈值", "参数", "步骤S", "module", "parameter")
    has_broad = any(m in feat_text for m in broad_markers)
    has_detail = any(m in feat_text for m in detail_markers)
    return has_broad and not has_detail


def _scope_advice(placement: FeaturePlacement, support_status: str) -> str:
    """Recommended claim-scope adjustment."""
    if placement == FeaturePlacement.SHOULD_DELETE:
        return "建议从权利要求中删除，说明书中保留即可。"
    if support_status == "missing":
        return "缺少说明书支撑，建议缩小范围或补充实施例。"
    if placement == FeaturePlacement.DESCRIPTION_ONLY_SUPPORT:
        return "目前仅在说明书中出现，如为核心特征建议补入权利要求。"
    if support_status == "weak":
        return "支撑较弱，建议限缩或增补实施例。"
    if placement == FeaturePlacement.INDEPENDENT_CLAIM_REQUIRED:
        return "保持独立权利要求位置，确保前序部分清楚限定。"
    return "当前范围适当。"


def _build_single_novelty_attack(
    feat_text: str, prior_art: PriorArtHit
) -> NoveltyAttack:
    """Build a novelty attack for one feature against one prior-art reference."""
    pa_text = (prior_art.abstract or prior_art.title or "").lower()
    feat_lower = feat_text.lower()

    # Simple overlap detection.
    overlap_keywords = []
    for word in re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", feat_lower):
        if len(word) >= 2 and word in pa_text:
            overlap_keywords.append(word)

    if len(overlap_keywords) >= 3:
        strength = "strong"
        analysis = f"现有技术{prior_art.title}已公开{', '.join(overlap_keywords[:3])}等特征，与{feat_text[:30]}高度重叠。"
    elif len(overlap_keywords) >= 1:
        strength = "moderate"
        analysis = f"现有技术{prior_art.title}部分涉及{', '.join(overlap_keywords[:3])}，与{feat_text[:30]}存在一定重叠。"
    else:
        strength = "weak"
        analysis = f"现有技术{prior_art.title}未明显公开{feat_text[:40]}，新颖性攻击基础薄弱。"

    evidence_quality = "verified" if prior_art.publication_number else "low"

    return NoveltyAttack(
        feature_text=feat_text,
        prior_art_title=prior_art.title,
        prior_art_ref=prior_art.publication_number or prior_art.id,
        citation_source=prior_art.source,
        overlap_analysis=analysis,
        attack_strength=strength,
        evidence_quality=evidence_quality,
    )


def _build_novelty_attacks(
    rows: list[GrantabilityClaimChartRow],
    prior_art_hits: list[PriorArtHit],
) -> list[NoveltyAttack]:
    """Collect all novelty attacks from claim-chart rows."""
    attacks: list[NoveltyAttack] = []
    for row in rows:
        if row.novelty_attack is not None:
            attacks.append(row.novelty_attack)
    return attacks


def _build_inventive_step_attacks(
    rows: list[GrantabilityClaimChartRow],
    prior_art_hits: list[PriorArtHit],
    strategy_brief: PatentStrategyBrief | None,
) -> list[InventiveStepAttackCombo]:
    """Build inventive-step (obviousness) attack combinations from prior art."""
    attacks: list[InventiveStepAttackCombo] = []
    if len(prior_art_hits) < 2:
        return attacks

    # Simple pairwise combinations of prior art.
    for i in range(min(len(prior_art_hits), 5)):
        for j in range(i + 1, min(len(prior_art_hits), 5)):
            pa1, pa2 = prior_art_hits[i], prior_art_hits[j]
            combo = _build_combo(pa1, pa2)
            attacks.append(combo)

    return attacks


def _build_combo(pa1: PriorArtHit, pa2: PriorArtHit) -> InventiveStepAttackCombo:
    """Build one inventive-step combo from two prior-art documents."""
    title = f"{pa1.title or 'PA1'} + {pa2.title or 'PA2'} 组合"
    rationale = (
        f"将{pa1.title or '现有技术1'}与{pa2.title or '现有技术2'}结合，"
        f"本领域技术人员在面对相同技术问题时，有动机将两者组合以获得本发明的技术方案。"
    )
    defense = (
        "需要说明组合存在技术障碍（teaching away），"
        "或组合后产生非显而易见的协同效果。"
    )
    return InventiveStepAttackCombo(
        title=title,
        primary_reference=pa1.publication_number or pa1.id,
        secondary_references=[pa2.publication_number or pa2.id],
        combination_rationale=rationale,
        attack_strength="moderate",
        defense_suggestion=defense,
    )


def _attach_inventive_step_combos(
    rows: list[GrantabilityClaimChartRow],
    prior_art_hits: list[PriorArtHit],
) -> None:
    """Attach relevant inventive-step combos to each claim-chart row."""
    if len(prior_art_hits) >= 2:
        combos = []
        for i in range(min(len(prior_art_hits), 3)):
            for j in range(i + 1, min(len(prior_art_hits), 3)):
                pa1, pa2 = prior_art_hits[i], prior_art_hits[j]
                combos.append(_build_combo(pa1, pa2))
        for row in rows:
            row.inventive_step_combos = combos


def _aggregate_evidence_quality(
    prior_art_hits: list[PriorArtHit],
    patent_points: list[PatentPointCandidate],
    disclosures: list[DisclosureRun],
) -> str:
    """Determine the overall evidence-quality tier."""
    if not prior_art_hits and not patent_points:
        return "low"
    # Count verified vs unverified.
    verified = sum(
        1 for h in prior_art_hits if h.publication_number and h.source not in ("claim_chart", "LLM-echo")
    )
    unverified = sum(
        1 for h in prior_art_hits
        if not h.publication_number or h.source in ("claim_chart", "LLM-echo")
    )
    # Also check disclosure research confidence.
    for d in disclosures:
        if d.package and d.package.research_confidence == "high":
            return "verified"
        if d.package and d.package.research_confidence == "medium":
            if verified >= 3:
                return "verified"
            return "unverified"
    if verified >= 3:
        return "verified"
    if verified >= 1:
        return "unverified"
    return "low"


def _compute_overall_status(
    rows: list[GrantabilityClaimChartRow],
    novelty_attacks: list[NoveltyAttack],
    inventive_step_attacks: list[InventiveStepAttackCombo],
    fail_closed: bool,
    evidence_quality: str,
) -> str:
    """Compute the overall grantability status tier."""
    if fail_closed:
        return "uncertain"

    # Count strong attacks.
    strong_novelty = sum(1 for a in novelty_attacks if a.attack_strength == "strong")
    strong_inventive = sum(1 for a in inventive_step_attacks if a.attack_strength == "strong")

    if strong_novelty >= 2 or strong_inventive >= 2:
        return "low"

    moderate_novelty = sum(1 for a in novelty_attacks if a.attack_strength == "moderate")
    moderate_inventive = sum(1 for a in inventive_step_attacks if a.attack_strength == "moderate")

    if moderate_novelty >= 2 or moderate_inventive >= 3:
        return "medium"

    # Check feature placements for independent-claim coverage.
    independent_rows = [
        r for r in rows
        if r.feature_placement == FeaturePlacement.INDEPENDENT_CLAIM_REQUIRED
        and r.support_status != "missing"
    ]
    if independent_rows and evidence_quality == "verified":
        return "high"

    return "medium"


def _build_risk_summary(
    rows: list[GrantabilityClaimChartRow],
    novelty_attacks: list[NoveltyAttack],
    inventive_step_attacks: list[InventiveStepAttackCombo],
) -> dict[str, str]:
    """Build a risk-summary dict."""
    summary: dict[str, str] = {}

    overbreadth_rows = [r for r in rows if r.overbreadth_risk]
    if overbreadth_rows:
        summary["overbreadth_risk"] = (
            f"{len(overbreadth_rows)}个特征存在范围过宽风险，"
            f"建议限缩至具体实施例。"
        )

    weak_support_rows = [r for r in rows if r.support_status in ("weak", "missing")]
    if weak_support_rows:
        summary["support_gap"] = (
            f"{len(weak_support_rows)}个特征缺乏充分说明书支撑。"
        )

    strong_attacks = [a for a in novelty_attacks if a.attack_strength == "strong"]
    if strong_attacks:
        summary["novelty_risk"] = (
            f"{len(strong_attacks)}项特征面临强新颖性攻击，建议缩小保护范围。"
        )

    if inventive_step_attacks:
        strong_inventive = [a for a in inventive_step_attacks if a.attack_strength == "strong"]
        if strong_inventive:
            summary["inventive_step_risk"] = (
                f"{len(strong_inventive)}组现有技术组合形成强创造性攻击。"
            )
        else:
            summary["inventive_step_risk"] = (
                f"{len(inventive_step_attacks)}组现有技术组合需关注创造性风险。"
            )

    should_delete = [r for r in rows if r.feature_placement == FeaturePlacement.SHOULD_DELETE]
    if should_delete:
        summary["placement_issues"] = (
            f"{len(should_delete)}个特征建议从权利要求中删除。"
        )

    return summary


def _build_recommendation(
    status: str,
    rows: list[GrantabilityClaimChartRow],
    fail_closed: bool,
    strategy_brief: PatentStrategyBrief | None,
) -> str:
    """Build the final recommendation text."""
    if fail_closed:
        return (
            "现有技术证据不足，无法给出授权前景结论。建议：\n"
            "1. 补充CNIPA/USPTO/EPO检索，获取更多现有技术文献；\n"
            "2. 明确本发明的区别技术特征；\n"
            "3. 限缩权利要求保护范围至具体实施例。"
        )

    parts: list[str] = []
    if status == "high":
        parts.append("授权前景良好。建议维持现有保护范围并尽早提交。")
    elif status == "medium":
        parts.append("授权前景中等。建议针对性补强说明书支撑和创造性论证。")
    else:
        parts.append("授权前景较低。建议大幅限缩权利要求范围或重新评估技术方案。")

    # Add strategy-aware advice.
    if strategy_brief and strategy_brief.claim_strategy:
        parts.append(f"会审策略：{'; '.join(strategy_brief.claim_strategy[:3])}。")

    independent = [r for r in rows if r.feature_placement == FeaturePlacement.INDEPENDENT_CLAIM_REQUIRED]
    if independent:
        parts.append(f"核心特征（{len(independent)}个）建议保持在独立权利要求中。")

    return "\n".join(parts)


def _build_overall_assessment(
    status: str,
    rows: list[GrantabilityClaimChartRow],
    fail_closed: bool,
    low_evidence_flags: list[str],
) -> str:
    """Build the overall assessment narrative."""
    independent = [r for r in rows if r.feature_placement == FeaturePlacement.INDEPENDENT_CLAIM_REQUIRED]
    dependent = [r for r in rows if r.feature_placement == FeaturePlacement.DEPENDENT_CLAIM_OPTIONAL]
    desc_only = [r for r in rows if r.feature_placement == FeaturePlacement.DESCRIPTION_ONLY_SUPPORT]
    to_delete = [r for r in rows if r.feature_placement == FeaturePlacement.SHOULD_DELETE]

    lines = [
        f"授权前景评估：{status.upper()}",
        f"共识别{len(rows)}个技术特征。",
        f"独立权利要求特征：{len(independent)}个",
        f"从属权利要求特征：{len(dependent)}个",
        f"说明书支撑特征：{len(desc_only)}个",
        f"建议删除特征：{len(to_delete)}个",
    ]
    if fail_closed and low_evidence_flags:
        lines.append("现有技术证据不足，当前仅能输出证据不足结论。")
    return "\n".join(lines)


def _closest_prior_art_summary(prior_art_hits: list[PriorArtHit]) -> str:
    """Build a summary of the closest prior art."""
    if not prior_art_hits:
        return "未检索到现有技术文献。"
    lines = []
    for i, hit in enumerate(prior_art_hits[:5], 1):
        lines.append(
            f"{i}. {hit.title} "
            f"({'CNIPA' if hit.source == 'cnipa' else hit.source}) "
            f"{hit.publication_number or ''}"
        )
    return "\n".join(lines)


def _build_source_citations(
    prior_art_hits: list[PriorArtHit],
    disclosures: list[DisclosureRun],
) -> list[dict]:
    """Build structured source-ledger citations for the report."""
    citations: list[dict] = []
    for hit in prior_art_hits[:10]:
        cit = {
            "title": hit.title,
            "publication_number": hit.publication_number,
            "source": hit.source,
            "url": hit.url,
        }
        citations.append(cit)
    # Also include disclosure research ledger data.
    for d in disclosures:
        if d.package and d.package.research_ledger:
            citations.append({
                "type": "research_ledger",
                "data": d.package.research_ledger,
            })
    return citations


# ---------------------------------------------------------------------------
# Markdown export (for frontend / report rendering)
# ---------------------------------------------------------------------------


def grantability_report_to_markdown(report: GrantabilityReport) -> str:
    """Render a GrantabilityReport to a human-readable Markdown string."""
    lines: list[str] = []

    lines.append(f"# 授权前景分析报告")
    lines.append(f"")
    lines.append(f"**项目ID**: {report.project_id}")
    lines.append(f"**报告ID**: {report.id}")
    lines.append(f"**生成时间**: {report.created_at}")
    lines.append(f"**授权前景**: {report.status.upper()}")
    if report.fail_closed:
        lines.append(f"**⚠ 低证据关闭**: 现有技术证据不足，报告未给出高授权概率结论。")
    lines.append(f"")

    lines.append(f"## 总体评估")
    lines.append(f"")
    lines.append(report.overall_assessment)
    lines.append(f"")

    if report.closest_prior_art_summary:
        lines.append(f"## 最接近现有技术")
        lines.append(f"")
        lines.append(report.closest_prior_art_summary)
        lines.append(f"")

    if report.claim_chart:
        lines.append(f"## 权利要求对照表 (Claim Chart)")
        lines.append(f"")
        lines.append(f"| 特征 | 位置分类 | 最近现有技术 | 新颖性区分 | 支撑状态 | 建议 |")
        lines.append(f"|------|----------|-------------|-----------|---------|------|")
        for row in report.claim_chart:
            pa_refs = ", ".join(row.closest_prior_art_refs[:2]) or "无"
            novelty = row.novelty_distinction[:40] or "—"
            advice = row.recommended_scope_adjustment[:30]
            lines.append(
                f"| {row.feature_text[:30]} | {row.feature_placement.value} | "
                f"{pa_refs[:30]} | {novelty} | {row.support_status} | {advice} |"
            )
        lines.append(f"")

    if report.novelty_attacks:
        lines.append(f"## 新颖性攻击")
        lines.append(f"")
        for i, attack in enumerate(report.novelty_attacks, 1):
            lines.append(f"### 攻击 {i}: {attack.attack_strength.upper()}")
            lines.append(f"- **特征**: {attack.feature_text}")
            lines.append(f"- **对比文献**: {attack.prior_art_title} ({attack.prior_art_ref})")
            lines.append(f"- **证据质量**: {attack.evidence_quality}")
            lines.append(f"- **分析**: {attack.overlap_analysis}")
            lines.append(f"")

    if report.inventive_step_attacks:
        lines.append(f"## 创造性攻击组合")
        lines.append(f"")
        for i, combo in enumerate(report.inventive_step_attacks, 1):
            lines.append(f"### 组合 {i}: {combo.title}")
            lines.append(f"- **强度**: {combo.attack_strength}")
            lines.append(f"- **主要文献**: {combo.primary_reference}")
            lines.append(f"- **次要文献**: {', '.join(combo.secondary_references)}")
            lines.append(f"- **组合理由**: {combo.combination_rationale}")
            lines.append(f"- **防御建议**: {combo.defense_suggestion}")
            lines.append(f"")

    if report.risk_summary:
        lines.append(f"## 风险汇总")
        lines.append(f"")
        for risk_type, detail in report.risk_summary.items():
            lines.append(f"- **{risk_type}**: {detail}")
        lines.append(f"")

    if report.low_evidence_flags:
        lines.append(f"## 低证据标记")
        lines.append(f"")
        for flag in report.low_evidence_flags:
            lines.append(f"- ⚠ {flag}")
        lines.append(f"")

    if report.recommendation:
        lines.append(f"## 建议")
        lines.append(f"")
        lines.append(report.recommendation)

    return "\n".join(lines)
