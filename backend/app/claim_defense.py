from __future__ import annotations

import json
import re
import uuid
from typing import Any

from backend.app.llm import LLMClient
from backend.app.schemas import (
    ClaimDefenseWorksheet,
    DisclosureRun,
    DraftPackage,
    FeatureRecord,
    PatentPointCandidate,
)


COMBO_MARKERS = ("关系", "映射", "矩阵", "记录", "闭环", "回链", "增量", "置信度", "阈值", "规则", "状态", "任务", "证据")
VALID_CLASSIFICATIONS = {
    "known_base",
    "differentiator",
    "core_combo",
    "dependent_fallback",
    "support_needed",
}


def generate_claim_defense_worksheet(
    *,
    project_id: str,
    package: DraftPackage | None,
    disclosures: list[DisclosureRun],
    patent_points: list[PatentPointCandidate],
    llm: LLMClient | None,
) -> ClaimDefenseWorksheet:
    notes: list[str] = []
    feature_records = _extract_rule_features(package, disclosures, patent_points)
    feature_records.extend(_try_llm_features(project_id, package, disclosures, patent_points, llm, notes))

    feature_records = _dedupe_records(feature_records)
    feature_records = [
        _normalize_record(record, index, package, disclosures, patent_points)
        for index, record in enumerate(feature_records, start=1)
    ]
    support_gaps = _support_gaps(feature_records)

    return ClaimDefenseWorksheet(
        id=uuid.uuid4().hex,
        project_id=project_id,
        source="generated_package" if package else "draft",
        feature_records=feature_records,
        defense_recommendations=_defense_recommendations(feature_records),
        support_gaps=support_gaps,
        notes=notes,
    )


def _try_llm_features(
    project_id: str,
    package: DraftPackage | None,
    disclosures: list[DisclosureRun],
    patent_points: list[PatentPointCandidate],
    llm: LLMClient | None,
    notes: list[str],
) -> list[FeatureRecord]:
    if not llm:
        return []
    system = (
        "你是专利权利要求防线工作表助手。只抽取human-in-loop特征记录，"
        "不要改写正式权利要求。返回JSON对象，字段feature_records为数组。"
    )
    prompt = json.dumps(
        {
            "project_id": project_id,
            "claims": package.claims if package else "",
            "description": package.description if package else "",
            "drawing_description": package.drawing_description if package else "",
            "patent_points": [point.model_dump(mode="json") for point in patent_points],
            "disclosures": [
                run.package.model_dump(mode="json")
                for run in disclosures
                if run.package is not None
            ],
            "allowed_classifications": sorted(VALID_CLASSIFICATIONS),
        },
        ensure_ascii=False,
    )
    try:
        raw = llm.complete_stage("claim_defense_features", system, prompt)
        payload = json.loads(raw)
        records_payload = payload.get("feature_records")
        if not isinstance(records_payload, list):
            raise ValueError("feature_records must be a list")
        return [_record_from_payload(item) for item in records_payload]
    except Exception:
        notes.append("LLM特征抽取失败，已降级为规则抽取。")
        return []


def _record_from_payload(item: Any) -> FeatureRecord:
    if not isinstance(item, dict):
        raise ValueError("feature record must be an object")
    data = dict(item)
    data.setdefault("feature_id", f"f-{uuid.uuid4().hex[:8]}")
    data.setdefault("classification", "known_base")
    data.setdefault("claim_refs", [])
    data.setdefault("description_refs", [])
    data.setdefault("figure_refs", [])
    data.setdefault("prior_art_refs", [])
    data.setdefault("risk_tags", [])
    return FeatureRecord.model_validate(data)


def _extract_rule_features(
    package: DraftPackage | None,
    disclosures: list[DisclosureRun],
    patent_points: list[PatentPointCandidate],
) -> list[FeatureRecord]:
    records: list[FeatureRecord] = []
    if package:
        for claim_ref, fragment in _claim_fragments(package.claims):
            if len(fragment) < 6:
                continue
            records.append(
                FeatureRecord(
                    feature_id=f"f-{uuid.uuid4().hex[:8]}",
                    text=fragment,
                    classification=_classify_text(fragment, patent_points, disclosures),
                    claim_refs=[claim_ref] if claim_ref else [],
                    description_refs=_description_refs(fragment, package),
                    figure_refs=_figure_refs(fragment, package),
                    risk_tags=_risk_tags(fragment),
                )
            )

    for point in patent_points:
        for text in [point.title, point.innovation, point.technical_solution, *point.protection_focus]:
            if text:
                records.append(
                    FeatureRecord(
                        feature_id=f"f-{uuid.uuid4().hex[:8]}",
                        text=_clean_text(text),
                        classification=_classify_text(text, patent_points, disclosures),
                        description_refs=_point_support_refs(point),
                        risk_tags=_risk_tags(text),
                    )
                )

    for run in disclosures:
        if not run.package:
            continue
        for candidate in run.package.candidates:
            records.append(
                FeatureRecord(
                    feature_id=f"f-{uuid.uuid4().hex[:8]}",
                    text=_clean_text(candidate.innovation or candidate.title),
                    classification=_classify_text(candidate.innovation or candidate.title, patent_points, disclosures),
                    description_refs=[f"disclosure:{run.id}"],
                    risk_tags=_risk_tags(candidate.innovation or candidate.title),
                )
            )

    return records


def _claim_fragments(claims: str) -> list[tuple[str, str]]:
    fragments: list[tuple[str, str]] = []
    for line in claims.splitlines():
        text = _clean_text(line)
        if not text:
            continue
        claim_ref = ""
        match = re.match(r"^(\d+)[.、．]\s*(.*)$", text)
        if match:
            claim_ref = match.group(1)
            text = match.group(2)
        for part in re.split(r"[；;。]", text):
            part = _clean_text(part)
            if part:
                fragments.append((claim_ref, part))
    return fragments


def _classify_text(text: str, patent_points: list[PatentPointCandidate], disclosures: list[DisclosureRun]) -> str:
    if _has_combo_marker(text):
        return "core_combo"
    if _matches_differentiator(text, patent_points, disclosures):
        return "differentiator"
    if re.search(r"根据权利要求|其中|进一步|优选", text):
        return "dependent_fallback"
    return "known_base"


def _matches_differentiator(
    text: str,
    patent_points: list[PatentPointCandidate],
    disclosures: list[DisclosureRun],
) -> bool:
    haystack = text.lower()
    terms: list[str] = []
    for point in patent_points:
        terms.extend([point.title, point.innovation, point.technical_solution, *point.protection_focus])
    for run in disclosures:
        if not run.package:
            continue
        terms.append(run.package.prior_art_differences)
        for candidate in run.package.candidates:
            terms.extend([candidate.title, candidate.innovation, candidate.technical_solution, *candidate.protection_focus])
        for hit in run.package.prior_art_hits:
            terms.extend(hit.differentiators)
    for term in terms:
        term = _clean_text(term)
        if len(term) >= 4 and (term.lower() in haystack or haystack in term.lower()):
            return True
    return False


def _normalize_record(
    record: FeatureRecord,
    index: int,
    package: DraftPackage | None,
    disclosures: list[DisclosureRun],
    patent_points: list[PatentPointCandidate],
) -> FeatureRecord:
    classification = record.classification if record.classification in VALID_CLASSIFICATIONS else "known_base"
    inferred = _classify_text(record.text, patent_points, disclosures)
    if classification == "known_base" and inferred != "known_base":
        classification = inferred

    description_refs = list(record.description_refs)
    if not description_refs and package:
        description_refs = _description_refs(record.text, package)
    if not description_refs:
        description_refs = _disclosure_refs(record.text, disclosures)

    risk_tags = list(dict.fromkeys([*record.risk_tags, *_risk_tags(record.text)]))
    if classification in {"differentiator", "core_combo"} and not description_refs:
        classification = "support_needed"
        risk_tags.append("说明书支撑不足")

    return record.model_copy(
        update={
            "feature_id": record.feature_id or f"f{index}",
            "text": _clean_text(record.text),
            "classification": classification,
            "description_refs": description_refs,
            "figure_refs": record.figure_refs or (_figure_refs(record.text, package) if package else []),
            "risk_tags": list(dict.fromkeys(risk_tags)),
        }
    )


def _description_refs(text: str, package: DraftPackage) -> list[str]:
    refs: list[str] = []
    for marker in _support_markers(text):
        if marker and marker in package.description:
            refs.append(f"说明书支持:{marker}")
    return list(dict.fromkeys(refs))


def _figure_refs(text: str, package: DraftPackage) -> list[str]:
    if any(marker in package.drawing_description or marker in package.mermaid for marker in _support_markers(text)):
        return ["附图说明/流程图"]
    return []


def _disclosure_refs(text: str, disclosures: list[DisclosureRun]) -> list[str]:
    refs: list[str] = []
    for run in disclosures:
        if run.package and any(marker in run.package.body_markdown for marker in _support_markers(text)):
            refs.append(f"disclosure:{run.id}")
    return refs


def _point_support_refs(point: PatentPointCandidate) -> list[str]:
    refs = []
    if point.feasibility_basis:
        refs.append("patent_point:feasibility_basis")
    if point.evidence_status == "verified":
        refs.append("patent_point:verified")
    return refs


def _support_markers(text: str) -> list[str]:
    tokens = [token for token in re.split(r"[\s,，、；;。:：()（）]+", text) if len(token) >= 3]
    markers = [marker for marker in COMBO_MARKERS if marker in text]
    return [*tokens[:8], *markers]


def _risk_tags(text: str) -> list[str]:
    tags: list[str] = []
    if _has_combo_marker(text):
        tags.append("组合创造性")
    if "置信度" in text or "增量" in text:
        tags.append("效果支撑")
    if "回链" in text or "闭环" in text:
        tags.append("规避设计关注")
    return tags


def _support_gaps(feature_records: list[FeatureRecord]) -> list[str]:
    gaps = [
        f"{record.feature_id}: {record.text}"
        for record in feature_records
        if record.classification == "support_needed"
    ]
    return gaps or ["未发现阻断性说明书支撑缺口。"]


def _defense_recommendations(feature_records: list[FeatureRecord]) -> list[str]:
    has_core = any(record.classification in {"core_combo", "differentiator"} for record in feature_records)
    has_support_needed = any(record.classification == "support_needed" for record in feature_records)
    if has_core or has_support_needed:
        return [
            "独立权利要求应围绕组合特征组织，优先覆盖可核验的输入、处理规则、状态更新和输出关系。",
            "避免将单一功能点作为唯一发明核心，应保留从属权利要求作为退守层级。",
        ]
    return ["需补充披露材料或现有技术差异说明后，再形成权利要求防线。"]


def _dedupe_records(records: list[FeatureRecord]) -> list[FeatureRecord]:
    seen: set[str] = set()
    deduped: list[FeatureRecord] = []
    for record in records:
        key = _clean_text(record.text)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(record.model_copy(update={"text": key}))
    return deduped


def _has_combo_marker(text: str) -> bool:
    return any(marker in text for marker in COMBO_MARKERS)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip(" ，,。；;")
