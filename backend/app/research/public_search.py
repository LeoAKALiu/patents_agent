from __future__ import annotations

import csv
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


PUBLICATION_RE = re.compile(r"\b((?:CN|WO|US|EP|JP|KR)\s?\d{5,}[A-Z]\d?)\b", re.IGNORECASE)


@dataclass(frozen=True)
class SearchTheme:
    id: str
    label: str
    problem: str
    core_terms: list[str]
    ipc_filters: list[str]
    queries: list[str]
    breakthrough_hypotheses: list[str]


@dataclass(frozen=True)
class SearchQuery:
    id: str
    theme_id: str
    provider: str
    query: str
    domain: str = "ip"
    zone: str = "cn"
    language: str = "zh-CN"
    max_results: int = 10


@dataclass(frozen=True)
class SearchPlan:
    topic: str
    themes: list[SearchTheme]
    queries: list[SearchQuery]
    deepresearch_prompts: list[str]
    cnipa_instructions: list[str]


@dataclass
class PublicSearchHit:
    theme_id: str
    title: str
    url: str
    description: str = ""
    provider: str = ""
    score: float = 0.0
    quality_score: float = 0.0
    source: str = ""
    content: str = ""
    publication_number: str = field(default="", init=False)

    def __post_init__(self) -> None:
        self.publication_number = publication_number_from_text(" ".join([self.url, self.title, self.description]))


def build_reverse_modeling_search_plan() -> SearchPlan:
    themes = [
        SearchTheme(
            id="geometry",
            label="多模态逆建模与几何底座",
            problem="既有建筑外立面存在遮挡、非正交墙体、沉降倾斜和单面点云缺失，导致几何底座不能直接算量。",
            core_terms=["既有建筑", "外立面", "逆向建模", "点云", "无人机影像", "SLAM", "非曼哈顿", "墙厚推断"],
            ipc_filters=["G06V", "G06T", "G06F 30/13", "E04G 23/02"],
            queries=[
                "既有建筑 外立面 点云 逆向建模",
                "建筑外立面 点云 影像 融合 重建",
                "非曼哈顿 建筑 点云 墙体 拟合",
                "单面点云 墙厚 推断 BIM",
            ],
            breakthrough_hypotheses=[
                "把非曼哈顿墙体切片和单面点云墙厚实体化绑定到工程算量，而不是泛化为普通三维重建。",
                "将配准误差、局部法向量稳定性和墙厚来源写入后续 IFC 实体置信度。",
            ],
        ),
        SearchTheme(
            id="occlusion_semantics",
            label="抗遮挡构件识别与语义补全",
            problem="树木、防盗网、空调机位和玻璃反光造成点云空洞，传统几何方法漏检门窗、阳台和装饰线条。",
            core_terms=["建筑外立面", "门窗识别", "遮挡", "语义补全", "2D反投3D", "多视角融合", "SAM", "DINOv2"],
            ipc_filters=["G06V", "G06T", "G06N"],
            queries=[
                "建筑外立面 遮挡 构件识别 语义补全",
                "建筑立面 门窗 识别 点云 图像 融合",
                "无人机 图像 建筑 窗户 三维重建",
                "建筑外立面 多视角 语义 融合",
            ],
            breakthrough_hypotheses=[
                "将视觉基础模型的二维构件语义反投到三维墙体几何底座，并形成可算量洞口边界。",
                "用多视角互证和同层构件规律处理遮挡区域，而非单纯提高图像分割精度。",
            ],
        ),
        SearchTheme(
            id="ifc_quantity",
            label="Scan-to-IFC 与工程算量",
            problem="点云或 mesh 模型通常只能展示，缺少墙体、洞口和门窗的 IFC 拓扑关系，不能稳定生成工程量清单。",
            core_terms=["Scan-to-BIM", "Scan-to-IFC", "IFC4", "IfcWall", "IfcOpeningElement", "工程量清单", "洞口扣减"],
            ipc_filters=["G06F 30/13", "G06Q 50/08", "E04G 23/02"],
            queries=[
                "Scan-to-BIM 点云 IFC 工程量",
                "点云 BIM 工程量 自动统计",
                "基于 IFC 工程量 计算 方法",
                "BIM 工程量 清单 编码 知识图谱",
            ],
            breakthrough_hypotheses=[
                "把外立面逆建模构件直接写成 IFC 洞口拓扑和扣减关系，而不是只输出 BIM 模型。",
                "把每一项工程量清单回链到构件来源、识别置信度和人工复核状态。",
            ],
        ),
        SearchTheme(
            id="hitl_quality",
            label="人机协作修正与置信度质检",
            problem="全自动逆建模的低置信区域会影响算量交付，人工全量复核又抵消自动化效率。",
            core_terms=["BIM插件", "Revit插件", "人机协作", "置信度", "热力图", "质量检查", "边界吸附", "构件族替换"],
            ipc_filters=["G06F 3/0484", "G06F 30/13", "G06V", "G06Q 50/08"],
            queries=[
                "BIM 置信度 质量检查 人机协作",
                "点云 BIM 模型 修正 插件",
                "外立面 测量 点云 质量 检测",
                "BIM 工程量 规则 匹配 人工修正",
            ],
            breakthrough_hypotheses=[
                "以工程量影响和识别置信度共同驱动人工复核优先级。",
                "把人工修正日志反向更新 IFC 拓扑、洞口扣减和清单项，而不是只修模型几何。",
            ],
        ),
    ]
    queries: list[SearchQuery] = []
    for theme in themes:
        for index, query in enumerate(theme.queries, start=1):
            queries.append(SearchQuery(id=f"{theme.id}-anysearch-{index}", theme_id=theme.id, provider="anysearch", query=query))
            queries.append(
                SearchQuery(
                    id=f"{theme.id}-google-patents-{index}",
                    theme_id=theme.id,
                    provider="web",
                    query=f"site:patents.google.com {query} 专利",
                )
            )

    return SearchPlan(
        topic="既有建筑外立面逆建模与工程算量",
        themes=themes,
        queries=queries,
        deepresearch_prompts=_deepresearch_prompts(themes),
        cnipa_instructions=[
            "在 CNIPA 高级检索中按主题分别组合关键词、IPC 和申请日范围，不要只做单一关键词检索。",
            "导出字段至少包括申请号、公开号或授权公告号、专利名称、申请人、发明人、IPC、专利类型、申请日、法律状态和全文文件名。",
            "优先下载 XML/TXT 或可复制文字的 PDF；扫描版 PDF 需要 OCR 后再导入本地知识库。",
            "每组主题至少保留最相关的授权文本、审中公开文本、同族文本和被引用较多的基础文本。",
        ],
    )


def publication_number_from_text(text: str) -> str:
    match = PUBLICATION_RE.search(text)
    if not match:
        return ""
    return re.sub(r"\s+", "", match.group(1)).upper()


def deduplicate_hits(hits: list[PublicSearchHit]) -> list[PublicSearchHit]:
    best_by_key: dict[str, PublicSearchHit] = {}
    for hit in hits:
        key = hit.publication_number or _fallback_key(hit)
        current = best_by_key.get(key)
        if current is None or _hit_rank(hit) > _hit_rank(current):
            best_by_key[key] = hit
    return sorted(best_by_key.values(), key=lambda hit: (_theme_order(hit.theme_id), -_hit_rank(hit), hit.title))


def export_research_package(plan: SearchPlan, hits: list[PublicSearchHit], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    deduped = deduplicate_hits(hits)

    queries_json = output_dir / "queries.json"
    candidate_csv = output_dir / "candidate_hits.csv"
    summary_md = output_dir / "research_summary.md"
    deepresearch_prompts_md = output_dir / "deepresearch_prompts.md"
    cnipa_worklist_md = output_dir / "cnipa_worklist.md"

    queries_json.write_text(json.dumps(asdict(plan), ensure_ascii=False, indent=2), encoding="utf-8")
    _write_candidate_csv(candidate_csv, deduped)
    summary_md.write_text(_summary_markdown(plan, deduped), encoding="utf-8")
    deepresearch_prompts_md.write_text(_deepresearch_markdown(plan), encoding="utf-8")
    cnipa_worklist_md.write_text(_cnipa_worklist_markdown(plan), encoding="utf-8")

    return {
        "queries_json": queries_json,
        "candidate_csv": candidate_csv,
        "summary_md": summary_md,
        "deepresearch_prompts_md": deepresearch_prompts_md,
        "cnipa_worklist_md": cnipa_worklist_md,
    }


class AnySearchClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.anysearch.com/v1/search",
        timeout_seconds: int = 12,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("ANYSEARCH_API_KEY")
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def search(self, query: SearchQuery) -> list[PublicSearchHit]:
        payload: dict[str, Any] = {
            "query": query.query,
            "max_results": query.max_results,
            "domains": [query.domain],
            "zone": query.zone,
            "language": query.language,
            "content_types": ["web", "doc"],
        }
        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"AnySearch request failed: HTTP {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"AnySearch request failed: {exc.reason}") from exc

        data = json.loads(raw)
        return parse_anysearch_payload(data, theme_id=query.theme_id)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


def run_anysearch_plan(
    plan: SearchPlan,
    client: AnySearchClient | None = None,
    limit_per_query: int = 10,
    max_queries: int | None = None,
    continue_on_error: bool = True,
) -> tuple[list[PublicSearchHit], list[dict[str, str]]]:
    client = client or AnySearchClient()
    hits: list[PublicSearchHit] = []
    errors: list[dict[str, str]] = []
    queries = [query for query in plan.queries if query.provider == "anysearch"]
    if max_queries is not None:
        queries = queries[:max_queries]
    for query in queries:
        try:
            hits.extend(client.search(SearchQuery(**{**asdict(query), "max_results": limit_per_query})))
        except Exception as exc:
            errors.append({"query_id": query.id, "query": query.query, "error": str(exc)})
            if not continue_on_error:
                raise
    return deduplicate_hits(hits), errors


def parse_anysearch_payload(data: dict[str, Any], theme_id: str) -> list[PublicSearchHit]:
    results = data.get("results")
    if results is None and isinstance(data.get("data"), dict):
        results = data["data"].get("results")
    hits: list[PublicSearchHit] = []
    for item in results or []:
        hits.append(
            PublicSearchHit(
                theme_id=theme_id,
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                description=str(item.get("description") or item.get("content") or ""),
                provider="anysearch",
                score=float(item.get("score") or 0.0),
                quality_score=float(item.get("quality_score") or 0.0),
                source=str(item.get("source", "")),
                content=str(item.get("content", "")),
            )
        )
    return hits


def _deepresearch_prompts(themes: list[SearchTheme]) -> list[str]:
    prompts = []
    for theme in themes:
        prompts.append(
            "\n".join(
                [
                    f"请围绕“{theme.label}”做中国发明专利现有技术调研。",
                    f"技术问题：{theme.problem}",
                    f"关键词：{'、'.join(theme.core_terms)}",
                    f"IPC/CPC：{'、'.join(theme.ipc_filters)}",
                    "请输出：1) 高相关公开/授权专利列表；2) 每件专利的独立权利要求1要点；3) 已覆盖技术特征；4) 可能未充分覆盖的突破口；5) 建议用于 CNIPA 的检索式。",
                    "要求每个结论带公开号、标题、来源链接；无法核验的内容单独列为待核验，不要混入结论。",
                ]
            )
        )
    prompts.append(
        "请综合 CNIPA、Google Patents、WIPO、Espacenet 线索，对“既有建筑外立面逆建模与工程算量”做查重式检索。"
        "重点判断“点云/影像融合、遮挡构件补全、Scan-to-IFC、工程量清单、置信度人机复核”五个要素是否已有单件专利完整覆盖。"
        "输出 claim chart：现有技术文献、独权1要素、与我方方案重合点、差异点、撰写规避建议。"
    )
    return prompts


def _write_candidate_csv(path: Path, hits: list[PublicSearchHit]) -> None:
    fieldnames = [
        "theme_id",
        "publication_number",
        "title",
        "url",
        "provider",
        "score",
        "quality_score",
        "source",
        "description",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for hit in hits:
            writer.writerow(
                {
                    "theme_id": hit.theme_id,
                    "publication_number": hit.publication_number,
                    "title": hit.title,
                    "url": hit.url,
                    "provider": hit.provider,
                    "score": hit.score,
                    "quality_score": hit.quality_score,
                    "source": hit.source,
                    "description": hit.description,
                }
            )


def _summary_markdown(plan: SearchPlan, hits: list[PublicSearchHit]) -> str:
    lines = [
        f"# {plan.topic}公开检索包",
        "",
        "## 检索主题",
        "",
    ]
    for theme in plan.themes:
        lines.extend(
            [
                f"### {theme.label}",
                "",
                f"- 技术问题：{theme.problem}",
                f"- 核心词：{'、'.join(theme.core_terms)}",
                f"- IPC/CPC：{'、'.join(theme.ipc_filters)}",
                f"- 突破口假设：{'；'.join(theme.breakthrough_hypotheses)}",
                "",
            ]
        )
    lines.extend(["## 候选公开文本", ""])
    if not hits:
        lines.append("暂无候选命中；请运行 AnySearch 或导入 CNIPA/Google Patents 导出结果。")
    for hit in hits:
        pub = f"{hit.publication_number} " if hit.publication_number else ""
        lines.append(f"- {pub}{hit.title} ({hit.theme_id}) - {hit.url}")
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "1. 对候选公开文本补全 CNIPA/Google Patents 全文和法律状态。",
            "2. 将元数据和全文整理为 `metadata.csv + fulltext/` 后导入本地知识库。",
            "3. 抽取独立权利要求 1，建立“已有技术覆盖点 vs 我方突破口”的 claim chart。",
        ]
    )
    return "\n".join(lines) + "\n"


def _deepresearch_markdown(plan: SearchPlan) -> str:
    lines = [f"# {plan.topic} DeepResearch 提示词", ""]
    for index, prompt in enumerate(plan.deepresearch_prompts, start=1):
        lines.extend([f"## Prompt {index}", "", prompt, ""])
    return "\n".join(lines)


def _cnipa_worklist_markdown(plan: SearchPlan) -> str:
    lines = [
        f"# {plan.topic} CNIPA 检索工作单",
        "",
        "## 通用导出要求",
        "",
    ]
    for instruction in plan.cnipa_instructions:
        lines.append(f"- {instruction}")
    lines.extend(["", "## 分组检索", ""])
    for theme in plan.themes:
        lines.extend(
            [
                f"### {theme.label}",
                "",
                f"- IPC/CPC：{' OR '.join(theme.ipc_filters)}",
                "- 关键词组合：",
            ]
        )
        for query in theme.queries:
            lines.append(f"  - {query}")
        lines.extend(
            [
                "- 排除：实用新型、外观设计、单纯装饰构件、与建筑无关的通用三维重建。",
                "- 重点下载：独立权利要求、说明书具体实施方式、附图说明、法律状态。",
                "",
            ]
        )
    lines.extend(
        [
            "## 本地入库版本建议",
            "",
            "- 第一批公开专利：`reverse-modeling-public-v1`",
            "- 后续人工筛选高相关专利：`reverse-modeling-public-core-v1`",
        ]
    )
    return "\n".join(lines) + "\n"


def _fallback_key(hit: PublicSearchHit) -> str:
    normalized_url = hit.url.lower().rstrip("/")
    normalized_title = re.sub(r"\s+", "", hit.title.lower())
    return normalized_url or normalized_title


def _hit_rank(hit: PublicSearchHit) -> float:
    return hit.quality_score * 100 + hit.score + min(len(hit.description), 1000) / 10000


def _theme_order(theme_id: str) -> int:
    order = {"geometry": 0, "occlusion_semantics": 1, "ifc_quantity": 2, "hitl_quality": 3}
    return order.get(theme_id, 99)
