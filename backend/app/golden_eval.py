from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from backend.app.generator import PatentDraftGenerator
from backend.app.llm import LLMClient
from backend.app.schemas import (
    DraftPackage,
    EvalPatentResult,
    GoldenEvalReport,
    GoldenEvalSummary,
    InventionBrief,
)

# --- Gate check ---

_MIN_SECTION_LENGTH = 20


def _gate_check(package: DraftPackage) -> tuple[bool, list[str]]:
    """① 结构化校验门禁：返回 (pass, warnings)。"""
    warnings: list[str] = []

    cs = package.claims_struct
    if cs is None:
        return False, ["claims_struct is None — generation did not produce structured claims"]

    indies = [c for c in cs.claims if c.kind == "independent"]
    if not indies:
        return False, ["no independent claim found"]

    for c in indies:
        if len(c.features) < 2:
            warnings.append(f"claim {c.number} (independent) has fewer than 2 features")

    ds = package.description_struct
    if ds is not None:
        for label, text in [
            ("技术领域", ds.technical_field),
            ("背景技术", ds.background),
            ("发明内容", ds.summary),
            ("具体实施方式", ds.embodiments),
        ]:
            if len((text or "").strip()) < _MIN_SECTION_LENGTH:
                warnings.append(f"{label} section too short (< {_MIN_SECTION_LENGTH} chars)")

    if package.abstract_struct is not None and len(package.abstract_struct.abstract) > 300:
        warnings.append("abstract exceeds 300 characters")

    return True, warnings


# --- InventionBrief construction ---

_TECH_FIELD_LABELS = {
    "ai_software": "人工智能软件方法",
    "mechanical": "机械结构",
    "electronics": "电学电路",
    "chemical": "化学工艺",
}

_STEP_VERBS = ["采集", "获取", "解析", "训练", "检索", "生成", "输出", "审核", "导出", "检测", "提取", "调节", "控制"]

_EFFECT_KEYWORDS = ["提高", "降低", "提升", "减少", "避免", "实现"]


def _find_section(text: str, pattern: str) -> str:
    """Extract the section body following a heading that matches `pattern`."""
    m = re.search(rf"({pattern})\s*\n", text)
    if not m:
        return ""
    start = m.end()
    next_heading = re.search(r"\n(技术领域|背景技术|技术背景|发明内容|技术方案|附图说明|具体实施方式|权利要求)", text[start:])
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end].strip()


def _construct_invention_brief(entry: dict) -> InventionBrief:
    """Construct an InventionBrief from a golden-set patent entry."""
    inp = entry["input"]
    desc = inp.get("description_full", "")

    technical_field = _TECH_FIELD_LABELS.get(entry.get("technical_field", ""), "人工智能软件方法")

    bg = _find_section(desc, "背景技术|技术背景")
    technical_problem = bg[:80] if bg else "现有技术存在改进空间。"

    summary = _find_section(desc, "发明内容|技术方案")
    technical_solution = summary[:500] if summary else desc[:500]

    beneficial_effects: list[str] = []
    for line in desc.split("\n"):
        line = line.strip()
        if any(kw in line for kw in _EFFECT_KEYWORDS) and len(line) > 10:
            beneficial_effects.append(line[:200])
            if len(beneficial_effects) >= 3:
                break

    key_steps: list[str] = []
    for verb in _STEP_VERBS:
        if verb in desc:
            key_steps.append(verb)
        if len(key_steps) >= 5:
            break

    return InventionBrief(
        title=entry["title"],
        technical_field=technical_field,
        technical_problem=technical_problem,
        technical_solution=technical_solution,
        beneficial_effects=beneficial_effects or ["提升系统性能"],
        key_steps=key_steps or ["获取输入数据", "生成输出结果"],
    )


# --- SAS (Structure Alignment Score) ---


def _sas(package: DraftPackage, gold: dict) -> tuple[float, dict[str, float]]:
    """② 结构对齐度评分，0-1，确定性计算。"""
    gen_claims = package.claims_struct.claims if package.claims_struct else []
    gold_claims = gold["ground_truth"]["claims"]

    gen_n = len(gen_claims)
    gold_n = len(gold_claims)
    claims_count_align = min(gen_n, gold_n) / max(gen_n, gold_n) if max(gen_n, gold_n) > 0 else 0.0

    gen_indies = [c for c in gen_claims if c.kind == "independent"]
    gold_indies = [c for c in gold_claims if c["kind"] == "independent"]
    gen_indie_ratio = len(gen_indies) / gen_n if gen_n > 0 else 0.0
    gold_indie_ratio = len(gold_indies) / gold_n if gold_n > 0 else 0.0
    independent_ratio_align = 1.0 - abs(gen_indie_ratio - gold_indie_ratio)

    gen_categories = {c.category for c in gen_claims if c.category}
    gold_categories = {c.get("category", "other") for c in gold_claims}
    category_coverage = len(gen_categories & gold_categories) / len(gold_categories) if gold_categories else 1.0

    ds = package.description_struct
    section_count = 0
    if ds is not None:
        for text in [ds.technical_field, ds.background, ds.summary, ds.embodiments]:
            if len((text or "").strip()) >= _MIN_SECTION_LENGTH:
                section_count += 1
    section_completeness = section_count / 4.0

    detail = {
        "claims_count_align": round(claims_count_align, 4),
        "independent_ratio_align": round(independent_ratio_align, 4),
        "category_coverage": round(category_coverage, 4),
        "section_completeness": round(section_completeness, 4),
    }
    score = (
        0.30 * claims_count_align
        + 0.25 * independent_ratio_align
        + 0.25 * category_coverage
        + 0.20 * section_completeness
    )
    return round(score, 4), detail


# --- CCS (Content Coverage Score) ---


def _extract_nouns(text: str, min_len: int = 2) -> set[str]:
    """Extract potential noun phrases (Chinese characters ≥ min_len) from text."""
    cleaned = re.sub(r"[^一-鿿]", " ", text)
    words = [w.strip() for w in cleaned.split() if len(w.strip()) >= min_len]
    result = set(words)
    for seg in re.findall(r"[一-鿿]{3,}", text):
        for i in range(len(seg) - min_len + 1):
            result.add(seg[i:i + min_len])
    stopwords = {"所述", "包括", "用于", "以及", "其中", "一种", "涉及", "进行", "通过", "可以", "步骤", "模块"}
    return {w for w in result if w not in stopwords and len(w) >= min_len}


def _extract_topic_terms(text: str, top_n: int = 5) -> list[str]:
    """Extract top-N topic terms by frequency from text."""
    nouns = _extract_nouns(text, min_len=3)
    freq: dict[str, int] = {}
    for noun in nouns:
        freq[noun] = freq.get(noun, 0) + 1
    scored = sorted(freq.items(), key=lambda x: (len(x[0]), x[1]), reverse=True)
    return [term for term, _ in scored[:top_n]]


def _ccs(package: DraftPackage, gold: dict) -> tuple[float, dict[str, float]]:
    """③ 信息覆盖度评分，0-1，确定性计算。"""
    gold_claims = gold["ground_truth"]["claims"]
    gold_desc = gold["ground_truth"]["description_sections"]

    gold_nouns: set[str] = set()
    for c in gold_claims:
        for feat in c.get("features", []):
            gold_nouns |= _extract_nouns(feat)

    gen_text = ""
    if package.claims_struct:
        for c in package.claims_struct.claims:
            gen_text += " " + " ".join(c.features)
    if package.description:
        gen_text += " " + package.description

    gen_nouns = _extract_nouns(gen_text)

    if gold_nouns:
        key_noun_recall = len(gold_nouns & gen_nouns) / len(gold_nouns)
    else:
        key_noun_recall = 1.0

    gold_title = gold.get("title", "")
    gold_summary = gold_desc.get("summary", "")
    gold_topic = _extract_topic_terms(gold_title + " " + gold_summary)
    gen_desc = ""
    if package.description_struct:
        gen_desc = " ".join([
            package.description_struct.technical_field,
            package.description_struct.summary,
        ])
    gen_topic_terms = _extract_nouns(gen_desc, min_len=3)

    if gold_topic:
        topic_term_recall = len(set(gold_topic) & gen_topic_terms) / len(gold_topic)
    else:
        topic_term_recall = 1.0

    detail = {
        "key_noun_recall": round(key_noun_recall, 4),
        "topic_term_recall": round(topic_term_recall, 4),
    }
    score = 0.6 * key_noun_recall + 0.4 * topic_term_recall
    return round(score, 4), detail


# --- LLM-as-Judge (optional, requires EVAL_LLM_API_KEY) ---

_JUDGE_DIMENSIONS = {
    "clarity": (
        "清楚",
        "专利法第26条第4款：权利要求应当清楚地限定要求专利保护的范围。"
        "评分标准：5=权项边界清晰、特征无歧义、步骤顺序明确；1=功能性概括、缺少步骤顺序、输入输出不明确。",
    ),
    "support": (
        "支持",
        "实施细则第20条第2款：独立权利要求应当从整体上反映发明或者实用新型的技术方案，记载解决技术问题的必要技术特征。"
        "说明书应当充分公开发明。"
        "评分标准：5=每个权项特征在说明书中有明确对应实施例；1=权项特征在说明书中无对应段落。",
    ),
    "effect": (
        "技术效果",
        "审查指南第二部分第四章：发明或者实用新型的技术效果应当是技术方案必然产生的，或者由实验数据证明的。"
        "评分标准：5=有益效果具体、与区别特征明确关联；1=定性空洞、定量无据。",
    ),
    "cleanliness": (
        "清洁度",
        "系统独有维度：生成文本应不含AI开场白、meta段落、样板签名或内部会审痕迹。"
        "评分标准：5=完全清洁，无任何污染；1=含大量AI痕迹或内部meta。",
    ),
}

_JUDGE_SYSTEM_PROMPT = (
    "你是CNIPA发明专利实质审查员，熟悉审查指南。"
    "请对以下两段专利文本进行双盲对比评分，你不知道哪段是生成文本、哪段是授权文本。"
    '只输出JSON：{"score_a": N, "score_b": N, "reason_a": "...", "reason_b": "..."}'
)


def _llm_judge(
    gen_text: str,
    gold_text: str,
    dimension: str,
    domain_keywords: str,
    judge_llm: LLMClient,
) -> float | None:
    """④ Run a single-dimension LLM-as-Judge double-blind scoring. Returns the gen-side score (1-5)."""
    if dimension not in _JUDGE_DIMENSIONS:
        return None

    dim_label, guideline = _JUDGE_DIMENSIONS[dimension]

    import random
    is_swapped = random.choice([True, False])
    text_a = gold_text if is_swapped else gen_text
    text_b = gen_text if is_swapped else gold_text

    user_prompt = (
        f"【评分维度】{dim_label}\n"
        f"【审查指南依据】{guideline}\n"
        f"【技术领域关键词】{domain_keywords}\n\n"
        f"【文本A】\n{text_a[:3000]}\n\n"
        f"【文本B】\n{text_b[:3000]}"
    )

    try:
        payload = judge_llm.complete_stage_json(dimension, _JUDGE_SYSTEM_PROMPT, user_prompt)
        score_a = float(payload.get("score_a", 0))
        score_b = float(payload.get("score_b", 0))
        return float(score_b if is_swapped else score_a)
    except Exception:
        return None


# --- GoldenSetEvaluator ---


class GoldenSetEvaluator:
    """Load a golden-set of authorized patents and evaluate a generator against them."""

    def __init__(self, golden_set_dir: Path, judge_llm: LLMClient | None = None) -> None:
        self.golden_set_dir = Path(golden_set_dir)
        self.judge_llm = judge_llm

    # ---- loading ----

    def load_golden_set(self) -> list[dict]:
        """Load manifest and all referenced JSON files. Silently skips missing files."""
        manifest_path = self.golden_set_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Golden-set manifest not found: {manifest_path}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries: list[dict] = []
        for entry in manifest.get("entries", []):
            patent_file = self.golden_set_dir / f"{entry['id']}.json"
            if not patent_file.exists():
                continue
            try:
                data = json.loads(patent_file.read_text(encoding="utf-8"))
                entries.append(data)
            except (json.JSONDecodeError, KeyError):
                continue
        return entries

    # ---- top-level ----

    def run(self, generator: PatentDraftGenerator) -> GoldenEvalReport:
        """Run evaluation on all golden-set entries and produce a report."""
        entries = self.load_golden_set()
        run_id = uuid.uuid4().hex[:12]
        per_patent: list[EvalPatentResult] = []

        for entry in entries:
            try:
                result = self.run_one(entry, generator)
            except Exception:
                result = EvalPatentResult(
                    patent_id=entry.get("id", "unknown"),
                    title=entry.get("title", "unknown"),
                    technical_field=entry.get("technical_field", "unknown"),
                    gate_pass=False,
                    gate_warnings=[f"unexpected error evaluating patent: {entry.get('id', 'unknown')}"],
                    sas=0.0,
                    ccs=0.0,
                )
            per_patent.append(result)

        n = len(per_patent)
        sas_avg = sum(r.sas for r in per_patent) / n if n > 0 else 0.0
        ccs_avg = sum(r.ccs for r in per_patent) / n if n > 0 else 0.0
        gate_pass_count = sum(1 for r in per_patent if r.gate_pass)
        gate_pass_rate = gate_pass_count / n if n > 0 else 0.0
        total_warnings = sum(len(r.gate_warnings) for r in per_patent)

        # Aggregate LLM-Judge averages
        llm_judge_avg: dict[str, float] | None = None
        if self.judge_llm is not None:
            dims = ["clarity", "support", "effect", "cleanliness"]
            llm_judge_avg = {}
            for dim in dims:
                scored = [r.llm_judge[dim] for r in per_patent if r.llm_judge and r.llm_judge.get(dim) is not None]
                llm_judge_avg[dim] = round(sum(scored) / len(scored), 2) if scored else 0.0

        summary = GoldenEvalSummary(
            sas_avg=round(sas_avg, 4),
            ccs_avg=round(ccs_avg, 4),
            gate_pass_rate=round(gate_pass_rate, 4),
            pass_=sas_avg >= 0.6 and ccs_avg >= 0.5 and gate_pass_rate >= 0.9,
            warnings=total_warnings,
            llm_judge_avg=llm_judge_avg,
        )

        return GoldenEvalReport(
            run_id=run_id,
            commit="",
            golden_set_version="v1",
            summary=summary,
            per_patent=per_patent,
        )

    def run_one(self, entry: dict, generator: PatentDraftGenerator) -> EvalPatentResult:
        """Evaluate a single golden-set patent entry against the generator."""
        brief = _construct_invention_brief(entry)
        package = generator.generate(brief, [])
        gate_pass, gate_warnings = _gate_check(package)
        sas_score, sas_detail = _sas(package, entry)
        ccs_score, ccs_detail = _ccs(package, entry)

        # LLM-Judge (optional)
        llm_judge: dict[str, float | None] | None = None
        if self.judge_llm is not None:
            gen_claims = package.claims
            gold_claims_text = "\n".join(
                f"{c['number']}. {c.get('preamble', '')} {' '.join(c.get('features', []))}"
                for c in entry["ground_truth"]["claims"]
            )
            domain_keywords = ", ".join(_extract_topic_terms(
                entry.get("title", "") + " " + entry["ground_truth"]["description_sections"].get("technical_field", "")
            ))
            llm_judge = {}
            for dim in ["clarity", "support", "effect", "cleanliness"]:
                gold_text = gold_claims_text if dim in ("clarity", "cleanliness") else (
                    entry["ground_truth"]["description_sections"].get("summary", "")
                    + " " + entry["ground_truth"]["description_sections"].get("embodiments", "")
                )
                gen_text = gen_claims if dim in ("clarity", "cleanliness") else (
                    (package.description_struct.summary if package.description_struct else "")
                    + " " + (package.description_struct.embodiments if package.description_struct else "")
                )
                llm_judge[dim] = _llm_judge(gen_text, gold_text, dim, domain_keywords, self.judge_llm)

        return EvalPatentResult(
            patent_id=entry["id"],
            title=entry["title"],
            technical_field=entry.get("technical_field", "unknown"),
            gate_pass=gate_pass,
            gate_warnings=gate_warnings,
            sas=sas_score,
            sas_detail=sas_detail,
            ccs=ccs_score,
            ccs_detail=ccs_detail,
            llm_judge=llm_judge,
        )
