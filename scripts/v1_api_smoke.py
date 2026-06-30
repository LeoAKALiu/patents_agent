#!/usr/bin/env python3
"""Deterministic v1 release API smoke against checked-in golden samples.

This script intentionally uses an in-process FastAPI TestClient and a local fake
LLM implementation. It never reads `.env`, never calls a live LLM API, and keeps
all runtime data in a temporary directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.main import STRICT_DELIBERATION_PROVIDERS, create_app
from backend.app.grantability import generate_grantability_report
from backend.app.schemas import (
    ClaimChartItem,
    DeepResearchEvidenceRef,
    DeepResearchFinding,
    DeepResearchPacket,
    DeliberationRun,
    DeliberationStageResult,
    DisclosurePackage,
    DisclosureRun,
    DraftPackage,
    MoatScores,
    PatentPointCandidate,
    ProjectKnowledgeState,
    PatentStrategyBrief,
    PatentType,
    PriorArtHit,
)

SAMPLE_DIR = ROOT / "samples"

SAMPLES = {
    "invention": SAMPLE_DIR / "invention_ai_monitoring.md",
    "utility_model": SAMPLE_DIR / "utility_model_structure.md",
    "external_draft": SAMPLE_DIR / "external_draft_invention.md",
    "sensing_inspection": SAMPLE_DIR / "sensing_inspection_quality.md",
    "algorithmic": SAMPLE_DIR / "algorithmic_route_planning.md",
}

TREND_FIELDS = (
    "authorization_stability",
    "support_strength",
    "prior_art_distinction",
    "official_hygiene",
    "overall",
)

DRAFTING_QUALITY_FIELDS = (
    "evidence_binding_rate",
    "core_feature_support_rate",
    "unsupported_core_feature_count",
    "unverified_effect_leak_count",
    "dependent_fallback_depth",
    "embodiment_density",
    "patch_delta",
)

LOOP_OBJECTIVE = "final patent draft quality"
LOOP_STANDARD = "full-process stability and reliability"
LOOP_GATE_GROUPS = {
    "stability": (
        "quality_trend_present",
        "official_export_hygiene",
    ),
    "reliability": (
        "official_export_blocked_before_compile",
        "official_export_blocked_before_review",
        "post_draft_review_unlocks_export",
    ),
    "final_draft_quality": (
        "research_evidence_count",
        "grantability_report_present",
        "evidence_binding_rate",
        "core_feature_support_rate",
        "unverified_effect_leak_count",
    ),
}

CORE_FEATURE_CLASSES = {"core_combo", "differentiator", "support_needed"}

OFFICIAL_EXPORT_FORBIDDEN_MARKERS = (
    "generation_logs",
    "image_prompt",
    "Mermaid",
    "```",
    "prompt",
    "support_gap",
    "DRAFT_COMPLETION_REPORT",
    "EXTERNAL_DRAFT_REVIEW_BUNDLE",
)


@dataclass(frozen=True)
class GoldenCase:
    workflow: str
    category: str
    sample: str
    project_name: str
    patent_type: PatentType = PatentType.INVENTION
    source: str = "idea"


@dataclass(frozen=True)
class ResearchSeed:
    point_title: str
    technical_problem: str
    innovation: str
    technical_solution: str
    beneficial_effects: tuple[str, ...]
    protection_focus: tuple[str, ...]
    prior_art: tuple[tuple[str, str, str, str], ...]
    differentiator: str


GOLDEN_CASES = (
    GoldenCase(
        workflow="software",
        category="software",
        sample="invention",
        project_name="施工场景边缘AI安全监控",
    ),
    GoldenCase(
        workflow="sensing_inspection",
        category="sensing_inspection",
        sample="sensing_inspection",
        project_name="声学视觉融合设备巡检方法",
    ),
    GoldenCase(
        workflow="mechanical_device",
        category="mechanical_device",
        sample="utility_model",
        project_name="可调节边缘AI摄像机防护安装支架",
        patent_type=PatentType.UTILITY_MODEL,
    ),
    GoldenCase(
        workflow="algorithmic",
        category="algorithmic",
        sample="algorithmic",
        project_name="多约束任务路径规划方法",
    ),
    GoldenCase(
        workflow="external_draft",
        category="external_draft",
        sample="external_draft",
        project_name="外部稿导入留痕方法",
        source="external_draft",
    ),
)

RESEARCH_SEEDS: dict[str, ResearchSeed] = {
    "software": ResearchSeed(
        point_title="边缘侧安全告警证据留痕",
        technical_problem="施工视频告警难以在遮挡场景中保留可复核证据。",
        innovation="将风险评分、轨迹片段、检测框和处置状态绑定为同一告警事件。",
        technical_solution="边缘设备识别目标后计算风险评分，超过阈值时保存证据帧、轨迹片段和处置状态。",
        beneficial_effects=("减少误报争议", "提高安全事件闭环效率"),
        protection_focus=("风险评分触发", "证据帧绑定", "处置状态闭环"),
        prior_art=(
            ("CN118201001A", "一种施工现场视频安全监控方法", "Google Patents", "公开视频识别和告警推送。"),
            ("CN117998877A", "一种危险区域人员检测系统", "CNIPA", "公开危险区域人员识别和阈值告警。"),
        ),
        differentiator="现有技术未将风险评分、证据帧、轨迹片段和处置状态绑定为同一可复核事件。",
    ),
    "sensing_inspection": ResearchSeed(
        point_title="声学视觉融合的设备巡检置信修正",
        technical_problem="单一视觉巡检在遮挡和反光条件下容易漏检设备异常。",
        innovation="用声学异常窗口触发视觉局部复检，并根据双源一致性修正异常置信度。",
        technical_solution="采集设备声纹和图像，定位声学异常窗口，调取同时间视觉区域进行复检并输出融合置信度。",
        beneficial_effects=("提高隐蔽异常召回率", "降低单源误判"),
        protection_focus=("声学异常窗口", "视觉局部复检", "双源置信修正"),
        prior_art=(
            ("CN116610234A", "一种基于声音的设备故障检测方法", "CNIPA", "公开声纹异常检测。"),
            ("CN115442019A", "工业设备视觉巡检方法", "Google Patents", "公开图像缺陷检测和巡检记录。"),
        ),
        differentiator="现有技术未公开由声学异常窗口驱动视觉局部复检并进行双源置信修正。",
    ),
    "mechanical_device": ResearchSeed(
        point_title="可调支架的快拆锁止与理线防护",
        technical_problem="施工现场摄像机安装支架角度调整慢，线缆外露且防护不足。",
        innovation="旋转支撑臂、俯仰调节座、快拆锁止件和闭合式理线槽组合。",
        technical_solution="固定底座连接旋转支撑臂，端部设置俯仰调节座和快拆锁止件，线缆经卡扣盖板闭合。",
        beneficial_effects=("提升安装调节效率", "降低线缆损伤风险"),
        protection_focus=("旋转支撑臂", "俯仰调节座", "快拆锁止件", "理线槽"),
        prior_art=(
            ("CN214991122U", "一种可调节摄像机支架", "CNIPA", "公开底座和角度调节结构。"),
            ("CN217333456U", "一种带防护罩的监控安装结构", "Google Patents", "公开防护罩和安装座。"),
        ),
        differentiator="现有结构未将快拆锁止、角度刻度、导水防护和闭合理线槽组合到同一支架。",
    ),
    "algorithmic": ResearchSeed(
        point_title="多约束任务路径规划的冲突回退",
        technical_problem="移动任务调度在电量、时间窗和禁行区变化时容易产生不可执行路径。",
        innovation="将时间窗、电量余量和禁行区冲突编码为统一惩罚向量，并在冲突升高时触发候选路径回退。",
        technical_solution="生成候选路径集，计算多约束惩罚向量，对超阈值路径执行局部回退和任务重排。",
        beneficial_effects=("提高路径可执行性", "降低重规划耗时"),
        protection_focus=("惩罚向量", "冲突阈值", "候选路径回退", "任务重排"),
        prior_art=(
            ("CN113887426A", "一种移动机器人路径规划方法", "CNIPA", "公开栅格路径规划和避障。"),
            ("CN114781998A", "多任务调度路径优化方法", "Google Patents", "公开任务优先级和路径优化。"),
        ),
        differentiator="现有技术未将电量、时间窗和禁行区冲突统一为惩罚向量后触发候选路径回退。",
    ),
    "external_draft": ResearchSeed(
        point_title="外部稿章节确认与正式稿隔离",
        technical_problem="外部草稿导入后容易把内部批注和格式污染带入正式提交稿。",
        innovation="解析外部稿章节后生成确认快照，并将质量问题作为侧车报告而非正式稿正文。",
        technical_solution="导入外部稿，解析摘要、权利要求和说明书，人工确认后进入正式稿编译和成稿会审。",
        beneficial_effects=("降低正式稿污染风险", "保留审阅留痕"),
        protection_focus=("章节解析", "确认快照", "侧车报告隔离"),
        prior_art=(
            ("CN112345678A", "一种文档章节自动识别方法", "CNIPA", "公开章节标题识别。"),
            ("CN113456789A", "一种文档审阅痕迹处理方法", "Google Patents", "公开批注处理和版本记录。"),
        ),
        differentiator="现有技术未将外部稿确认快照、质量侧车报告和正式稿哈希会审组合使用。",
    ),
}


class V1SmokeLLM:
    """Small stage-aware fake LLM for the v1 smoke.

    The backend only requires an object with complete_stage(stage, system, user).
    Responses are valid deterministic patent text/JSON and contain no credential
    or network dependencies.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(
            {
                "stage": stage,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )
        utility_model = "实用新型" in system_prompt or "utility_model" in user_prompt or "结构" in user_prompt
        sensing = "声学" in user_prompt or "巡检" in user_prompt or "振动" in user_prompt
        algorithmic = "路径规划" in user_prompt or "任务重排" in user_prompt or "禁行区" in user_prompt

        if stage == "core_formula":
            if algorithmic:
                return _json(
                    {
                        "summary": "以多约束惩罚向量固定候选路径回退触发关系。",
                        "formula_blocks": [
                            {
                                "id": "F01",
                                "name": "路径惩罚向量",
                                "latex": "P=w_tT+w_eE+w_zZ",
                                "purpose": "描述时间窗偏离、电量不足和禁行区冲突对路径可执行性的贡献。",
                                "claim_hook": "根据惩罚向量与阈值比较触发候选路径回退。",
                            }
                        ],
                        "variable_definitions": [
                            {"symbol": "T", "meaning": "时间窗偏离量", "unit": "分钟"},
                            {"symbol": "E", "meaning": "电量安全余量缺口", "unit": ""},
                            {"symbol": "Z", "meaning": "禁行区冲突因子", "unit": ""},
                        ],
                        "derivation_notes": ["惩罚向量用于限定可执行路径的选择逻辑。"],
                        "claim_hooks": ["将冲突阈值和候选路径回退写入独立权利要求。"],
                        "description_insert": "本实施例根据F01计算路径惩罚向量，并在惩罚向量超过阈值时执行局部回退和任务重排。",
                        "latex_markdown": "# 核心公式\n\nF01: $P=w_tT+w_eE+w_zZ$。",
                        "generation_logs": ["v1 smoke fake algorithmic formula package"],
                    }
                )
            if sensing:
                return _json(
                    {
                        "summary": "以声学异常窗口和视觉复检结果修正设备异常置信度。",
                        "formula_blocks": [
                            {
                                "id": "F01",
                                "name": "融合异常置信度",
                                "latex": "S=\\lambda A+(1-\\lambda)V",
                                "purpose": "描述声学异常得分和视觉复检得分对最终置信度的贡献。",
                                "claim_hook": "根据融合置信度输出巡检异常事件。",
                            }
                        ],
                        "variable_definitions": [
                            {"symbol": "A", "meaning": "声学异常得分", "unit": ""},
                            {"symbol": "V", "meaning": "视觉复检得分", "unit": ""},
                            {"symbol": "\\lambda", "meaning": "融合权重", "unit": ""},
                        ],
                        "derivation_notes": ["融合置信度用于限定双源巡检判定逻辑。"],
                        "claim_hooks": ["将声学窗口触发视觉复检写入方法独权。"],
                        "description_insert": "本实施例根据F01计算融合异常置信度，并在超过阈值时生成设备巡检异常事件。",
                        "latex_markdown": "# 核心公式\n\nF01: $S=\\lambda A+(1-\\lambda)V$。",
                        "generation_logs": ["v1 smoke fake sensing formula package"],
                    }
                )
            return _json(
                {
                    "summary": "以风险评分固定施工安全告警触发关系。",
                    "formula_blocks": [
                        {
                            "id": "F01",
                            "name": "风险评分关系",
                            "latex": "R=\\alpha C+\\beta T+\\gamma D",
                            "purpose": "描述目标置信度、停留时间和危险源距离对告警风险的贡献。",
                            "claim_hook": "根据风险评分与阈值比较生成告警事件。",
                        }
                    ],
                    "variable_definitions": [
                        {"symbol": "C", "meaning": "目标识别置信度", "unit": ""},
                        {"symbol": "T", "meaning": "目标在危险区域内的停留时间", "unit": "秒"},
                        {"symbol": "D", "meaning": "目标与危险源边界的距离因子", "unit": ""},
                    ],
                    "derivation_notes": ["公式用于限定告警触发逻辑，具体权重可按项目配置。"],
                    "claim_hooks": ["将风险评分和阈值比较写入从属权利要求。"],
                    "description_insert": "本实施例可根据F01计算风险评分，并在风险评分超过阈值时生成告警事件。",
                    "latex_markdown": "# 核心公式\n\nF01: $R=\\alpha C+\\beta T+\\gamma D$。",
                    "generation_logs": ["v1 smoke fake formula package"],
                }
            )

        if stage == "claims":
            if utility_model:
                return (
                    "1. 一种可调节边缘监控安装支架，其特征在于，包括固定底座、旋转支撑臂、"
                    "俯仰调节座、防护罩、理线槽和快拆锁止件，所述旋转支撑臂与所述固定底座"
                    "转动连接，所述俯仰调节座设置在所述旋转支撑臂的端部。\n"
                    "2. 根据权利要求1所述的安装支架，其特征在于，所述旋转支撑臂设有角度刻度和限位槽。\n"
                    "3. 根据权利要求1所述的安装支架，其特征在于，所述防护罩顶部设置导水坡。\n"
                    "4. 根据权利要求1所述的安装支架，其特征在于，所述理线槽通过卡扣盖板闭合。"
                )
            if algorithmic:
                return (
                    "1. 一种多约束任务路径规划方法，其特征在于，包括：获取任务点、时间窗、电量状态和禁行区配置；"
                    "生成多个候选路径；计算包含时间窗偏离、电量安全余量缺口和禁行区冲突因子的惩罚向量；"
                    "当所述惩罚向量超过阈值时执行候选路径回退和任务重排。\n"
                    "2. 根据权利要求1所述的方法，其特征在于，所述候选路径回退包括恢复到最近可执行节点并重新评估剩余任务。\n"
                    "3. 根据权利要求1所述的方法，其特征在于，所述电量安全余量缺口根据返航距离和任务能耗估计确定。\n"
                    "4. 根据权利要求1所述的方法，其特征在于，输出路径版本、回退原因和重排后的任务序列。"
                )
            if sensing:
                return (
                    "1. 一种声学视觉融合的设备巡检方法，其特征在于，包括：采集设备运行声学信号和巡检图像；"
                    "识别声学异常窗口；基于所述声学异常窗口调取对应时间段的视觉局部区域进行复检；"
                    "根据声学异常得分和视觉复检得分生成融合异常置信度。\n"
                    "2. 根据权利要求1所述的方法，其特征在于，所述声学异常窗口由声纹频带能量变化确定。\n"
                    "3. 根据权利要求1所述的方法，其特征在于，所述视觉局部区域对应设备铭牌、连接部或磨损部位。\n"
                    "4. 根据权利要求1所述的方法，其特征在于，巡检结果包括融合异常置信度、证据图像和声学片段。"
                )
            return (
                "1. 一种施工场景边缘AI安全监控方法，其特征在于，包括：接收施工现场视频流；"
                "识别人员目标、设备目标和安全防护目标；基于危险源配置、目标轨迹和风险评分生成告警事件；"
                "将告警事件与证据帧、检测框、轨迹片段和处置状态关联存储。\n"
                "2. 根据权利要求1所述的方法，其特征在于，所述风险评分根据目标识别置信度、停留时间和危险源距离确定。\n"
                "3. 根据权利要求1所述的方法，其特征在于，所述目标轨迹包括同一人员在多个摄像头下的时间连续位置。\n"
                "4. 根据权利要求1所述的方法，其特征在于，所述处置状态包括待确认、已派发、已复核和已关闭。"
            )

        if stage == "description":
            if utility_model:
                return (
                    "技术领域\n本实用新型涉及施工现场摄像机安装结构。\n"
                    "背景技术\n施工现场摄像机需要在多种基面上快速安装并保持视角稳定。\n"
                    "实用新型内容\n本实用新型通过固定底座、旋转支撑臂、俯仰调节座和防护罩形成可调节安装结构。\n"
                    "附图说明\n图1为安装支架整体结构示意图。图2为快拆锁止件局部结构示意图。\n"
                    "具体实施方式\n固定底座通过螺栓固定在立柱上，旋转支撑臂绕水平转轴调节方向，"
                    "俯仰调节座沿弧形滑槽调节摄像机角度，理线槽容纳电源线和网线。"
                )
            if algorithmic:
                return (
                    "技术领域\n本发明涉及移动任务调度和路径规划技术领域。\n"
                    "背景技术\n多任务设备在时间窗、电量和禁行区同时变化时容易产生不可执行路径。\n"
                    "发明内容\n本发明通过候选路径、惩罚向量、冲突阈值和局部回退生成可执行任务路径。\n"
                    "附图说明\n图1为任务路径规划流程图。图2为候选路径回退结构示意图。\n"
                    "具体实施方式\n系统读取任务点和约束配置，生成候选路径，计算时间窗偏离、电量缺口和禁行区冲突，"
                    "当惩罚向量超过阈值时回退到最近可执行节点并重排剩余任务。"
                )
            if sensing:
                return (
                    "技术领域\n本发明涉及工业设备巡检和多模态异常检测技术领域。\n"
                    "背景技术\n仅依赖视觉巡检在遮挡、反光和局部噪声条件下容易漏检设备异常。\n"
                    "发明内容\n本发明通过声学异常窗口触发视觉局部复检，并根据双源结果修正异常置信度。\n"
                    "附图说明\n图1为声学视觉融合巡检流程图。图2为异常窗口和视觉区域关联示意图。\n"
                    "具体实施方式\n巡检系统采集声学信号和图像，识别声学异常窗口，调取同时间视觉局部区域，"
                    "计算融合异常置信度并输出包含声学片段和证据图像的巡检事件。"
                )
            return (
                "技术领域\n本发明涉及施工安全智能监控技术领域。\n"
                "背景技术\n施工现场视频告警需要在遮挡和多摄像头条件下保留可复核证据。\n"
                "发明内容\n本发明通过目标识别、轨迹关联、风险评分和证据留痕生成可复核的安全告警事件。\n"
                "附图说明\n图1为安全监控方法流程图。图2为告警事件数据结构图。\n"
                "具体实施方式\n边缘设备接收多路视频，识别人员、设备和防护目标，结合危险源配置计算风险评分，"
                "当风险评分超过阈值时生成告警事件，并保存证据帧、检测框、轨迹片段和处置状态。"
            )

        if stage == "abstract":
            if utility_model:
                return "本实用新型公开一种可调节边缘监控安装支架，能够实现摄像机视角调节、防护和线缆收纳。"
            if algorithmic:
                return "本发明公开一种多约束任务路径规划方法，能够在冲突升高时执行候选路径回退和任务重排。"
            if sensing:
                return "本发明公开一种声学视觉融合的设备巡检方法，能够通过双源复检提高异常识别可靠性。"
            return "本发明公开一种施工场景边缘AI安全监控方法，能够生成可复核的安全告警事件并关联保存证据数据。"

        if stage == "drawings":
            if utility_model:
                return "图1为安装支架整体结构示意图。图2为快拆锁止件局部结构示意图。"
            if algorithmic:
                return "图1为任务路径规划流程图。图2为候选路径回退结构示意图。"
            if sensing:
                return "图1为声学视觉融合巡检流程图。图2为异常窗口和视觉区域关联示意图。"
            return "图1为安全监控方法流程图。图2为告警事件与证据数据的关联结构图。"

        if stage == "diagram":
            return "flowchart TD\nA[接收输入] --> B[生成草稿]\nB --> C[质量检查]\nC --> D[正式导出]"

        if stage == "image_prompt":
            return "黑白专利线稿，展示关键模块和数据流。"

        if stage == "review":
            return _json(
                [
                    {
                        "category": "支持性",
                        "severity": "low",
                        "message": "权利要求与说明书主要技术特征一致。",
                        "suggestion": "提交前补充项目实测数据和附图标号。",
                        "evidence": "权利要求1和具体实施方式",
                    }
                ]
            )

        if stage == "post_draft_claims_reviewer":
            return _json(
                {
                    "role": "claims_reviewer",
                    "status": "passed",
                    "blocking_issues": [],
                    "contamination_hits": [],
                    "rewrite_suggestions": ["权利要求1保留输入、处理、输出闭环。"],
                    "official_safe_patches": [],
                    "attorney_memo": ["提交前由代理人复核从属权利要求层级。"],
                }
            )

        if stage == "post_draft_spec_cleaner":
            return _json(
                {
                    "role": "spec_cleaner",
                    "status": "passed",
                    "blocking_issues": [],
                    "contamination_hits": [],
                    "rewrite_suggestions": ["说明书保留正式章节。"],
                    "official_safe_patches": [],
                    "attorney_memo": ["未发现内部草稿污染。"],
                }
            )

        if stage == "post_draft_technical_hardness":
            return _json(
                {
                    "role": "technical_hardness",
                    "status": "passed",
                    "blocking_issues": [],
                    "contamination_hits": [],
                    "rewrite_suggestions": ["提交前补充实验或样机数据。"],
                    "official_safe_patches": [],
                    "attorney_memo": ["技术效果需要以证据材料支撑。"],
                }
            )

        if stage == "post_draft_chair_synthesis":
            return _json(
                {
                    "status": "passed",
                    "export_allowed": True,
                    "blocking_issues": [],
                    "contamination_hits": [],
                    "claim_1_rewrite": "",
                    "system_claim_rewrite": "",
                    "abstract_rewrite": "",
                    "description_rewrite_tasks": ["提交前统一附图标号。"],
                    "official_safe_patches": [],
                    "attorney_memo": ["成稿会审通过，仍需正式法律复核。"],
                    "next_actions": ["导出正式稿并交由代理人审阅。"],
                }
            )

        raise KeyError(f"Unhandled v1 smoke LLM stage: {stage}")


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _sample(name: str) -> str:
    path = SAMPLES[name]
    if not path.exists():
        raise AssertionError(f"missing sample: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if len(text) < 200:
        raise AssertionError(f"sample is unexpectedly short: {path}")
    return text


def _ok(response, label: str, expected_status: int = 200) -> Any:
    if response.status_code != expected_status:
        raise AssertionError(f"{label}: expected {expected_status}, got {response.status_code}: {response.text[:1000]}")
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        return response.json()
    return response.text


def _seed_completed_deliberation(client: TestClient, project_id: str) -> str:
    providers = list(STRICT_DELIBERATION_PROVIDERS)
    stages = [
        *[
            DeliberationStageResult(
                phase="opening",
                provider_id=provider,
                label=f"opening {provider}",
                payload={"stance": "v1 smoke ready"},
                status="completed",
            )
            for provider in providers
        ],
        *[
            DeliberationStageResult(
                phase="pair",
                provider_id="codex",
                label=label,
                payload={"resolved_recommendation": "strict release path accepted"},
                status="completed",
            )
            for label in [f"pair {provider_a}-vs-{provider_b}" for provider_a, provider_b in combinations(providers, 2)]
        ],
        DeliberationStageResult(
            phase="chair",
            provider_id="codex",
            label="chair synthesis",
            payload={"summary": "v1 smoke strict deliberation completed"},
            status="completed",
        ),
    ]
    run_id = f"v1-smoke-delib-{project_id}"
    app_state = getattr(client.app, "state")
    app_state.store.create_deliberation_run(
        DeliberationRun(
            id=run_id,
            project_id=project_id,
            status="completed",
            providers=providers,
            run_mode="full",
            stage_results=stages,
            strategy_brief=PatentStrategyBrief(
                summary="v1 smoke 会审策略：以风险评分、阈值和证据留痕支撑权利要求。",
                claim_strategy=["方法独权覆盖视频输入、目标识别、风险评分和证据留痕闭环。"],
                description_strategy=["说明书补充风险评分变量、证据帧和处置状态的数据结构。"],
                risk_controls=["未验证效果仅作为可行实施方式表达。"],
                agent_consensus=f"{'、'.join(providers)} 会审同意进入确定性 v1 smoke 生成路径。",
            ),
            events=["v1 smoke deliberation seeded without external agents"],
        )
    )
    return run_id


def _prior_art_hits(case: GoldenCase) -> list[PriorArtHit]:
    seed = RESEARCH_SEEDS[case.category]
    return [
        PriorArtHit(
            id=publication_number.lower(),
            source=source,
            query=f"{case.project_name} {seed.point_title}",
            title=title,
            publication_number=publication_number,
            url=f"https://patents.google.com/patent/{publication_number}",
            abstract=abstract,
            relevance_summary=f"golden prior art for {case.workflow}",
            differentiators=[seed.differentiator],
        )
        for publication_number, title, source, abstract in seed.prior_art
    ]


def _seed_research_bundle(client: TestClient, project_id: str, case: GoldenCase) -> tuple[DisclosureRun, PatentPointCandidate]:
    seed = RESEARCH_SEEDS[case.category]
    hits = _prior_art_hits(case)
    point = PatentPointCandidate(
        id=f"{case.workflow}-point",
        title=seed.point_title,
        technical_problem=seed.technical_problem,
        innovation=seed.innovation,
        technical_solution=seed.technical_solution,
        beneficial_effects=list(seed.beneficial_effects),
        protection_focus=list(seed.protection_focus),
        grantability_score=0.78,
        rationale="v1.1 deterministic golden seed",
        evidence_status="verified",
        source_type="user",
        feasibility_basis="golden sample fixture with checked-in prior-art references",
        moat_scores=MoatScores(
            scope_width=0.62,
            designaround_difficulty=0.58,
            feasibility=0.82,
            support_strength=0.74,
            prior_art_distance=0.66,
            strategic_value=0.7,
        ),
        claim_chart=[
            ClaimChartItem(
                prior_art_id=hits[0].publication_number or hits[0].id,
                prior_art_title=hits[0].title,
                overlapping_features=[seed.protection_focus[0]],
                differentiating_features=[seed.differentiator],
                claim_drafting_advice="在独立权利要求中保留区别特征，并用从属权利要求承接工程参数。",
            )
        ],
        selected=True,
    )
    disclosure = DisclosureRun(
        id=f"{case.workflow}-disclosure",
        project_id=project_id,
        status="completed",
        max_prior_art_results=8,
        package=DisclosurePackage(
            title=f"{case.project_name}技术交底书",
            summary=seed.technical_solution,
            materials_summary="v1.1 deterministic golden sample",
            candidates=[point],
            selected_candidate_id=point.id,
            prior_art_hits=hits,
            prior_art_differences=seed.differentiator,
            body_markdown=f"# {case.project_name}技术交底书\n\n{seed.technical_solution}\n\n## 现有技术差异\n{seed.differentiator}",
            mermaid="flowchart TD\nA[技术输入] --> B[区别特征]\nB --> C[权利要求布局]",
            image_prompt="黑白专利线稿，展示关键模块连接关系。",
            research_ledger={
                "total_hits": len(hits),
                "entries": [
                    {
                        "provider": hit.source,
                        "status": "ok",
                        "retained_count": 1,
                        "publication_number": hit.publication_number,
                    }
                    for hit in hits
                ],
            },
            provider_diagnostics=[
                {
                    "phase": "post_flight",
                    "available_providers": sorted({hit.source for hit in hits}),
                    "skipped_providers": [],
                    "active_chain": sorted({hit.source for hit in hits}),
                    "warnings": [],
                }
            ],
            research_confidence="medium",
        ),
        stage_results=[
            {
                "phase": "research_ledger",
                "total_hits": len(hits),
                "provider_count": len({hit.source for hit in hits}),
            }
        ],
        events=["v1.1 golden research seed persisted without live providers"],
    )
    app_state = getattr(client.app, "state")
    app_state.store.add_project_patent_point(project_id, point)
    app_state.store.create_disclosure_run(disclosure)
    return disclosure, point


def _deep_research_packet(project_id: str, case: GoldenCase) -> DeepResearchPacket:
    seed = RESEARCH_SEEDS[case.category]
    hits = _prior_art_hits(case)
    return DeepResearchPacket(
        status="completed",
        cycles=1,
        project_id=project_id,
        query_plan=[f"{case.project_name} {seed.point_title}"],
        queries_run=[f"{case.project_name} {seed.point_title}"],
        differentiators=[seed.differentiator],
        claim_drafting_constraints=["区别特征必须进入独立权利要求或强从属权利要求。"],
        findings=[
            DeepResearchFinding(
                id=f"{case.workflow}-finding",
                category="differentiator",
                title=seed.point_title,
                summary=seed.differentiator,
                evidence=[
                    DeepResearchEvidenceRef(
                        source=hit.source,
                        query=hit.query,
                        title=hit.title,
                        publication_number=hit.publication_number,
                        url=hit.url,
                        relevance=hit.relevance_summary,
                    )
                    for hit in hits
                ],
            )
        ],
        generation_logs=["v1.1 deterministic deep-research packet; no live provider used"],
    )


def _golden_project_knowledge_state(project_id: str, case: GoldenCase) -> ProjectKnowledgeState:
    document_count = len(RESEARCH_SEEDS[case.category].prior_art)
    return ProjectKnowledgeState(
        project_id=project_id,
        status="ready",
        document_count=document_count,
        candidate_count=document_count,
        claim_coverage=1.0,
        fulltext_coverage=1.0,
        quality_flags=["verified_golden_evidence"],
    )


def _prepare_official_export(client: TestClient, project_id: str, label: str) -> dict[str, Any]:
    blocked_before_compile = client.get(f"/api/projects/{project_id}/official-export.md")
    if blocked_before_compile.status_code != 409:
        raise AssertionError(
            f"{label} official export should be blocked before compile, got {blocked_before_compile.status_code}"
        )

    compile_run = _ok(client.post(f"/api/projects/{project_id}/official-compile-runs", json={}), f"{label} official compile")
    if compile_run["status"] != "completed":
        raise AssertionError(f"{label} official compile did not complete: {compile_run}")

    blocked_before_review = client.get(f"/api/projects/{project_id}/official-export.md")
    if blocked_before_review.status_code != 409:
        raise AssertionError(
            f"{label} official export should be blocked before post-draft review, got {blocked_before_review.status_code}"
        )

    post_review = _ok(client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}), f"{label} post-draft review")
    if post_review["status"] != "completed" or post_review["export_allowed"] is not True:
        raise AssertionError(f"{label} post-draft review did not allow export: {post_review}")

    official_md = _ok(client.get(f"/api/projects/{project_id}/official-export.md"), f"{label} official markdown export")
    if "权利要求书" not in official_md or "附图说明" not in official_md:
        raise AssertionError(f"{label} official export missing required sections")
    forbidden_hits = [marker for marker in OFFICIAL_EXPORT_FORBIDDEN_MARKERS if marker in official_md]
    if forbidden_hits:
        raise AssertionError(f"{label} official export contains internal markers: {forbidden_hits}")
    return {
        "compile_id": compile_run["id"],
        "post_draft_review_id": post_review["id"],
        "official_package_hash": compile_run.get("official_package_hash", ""),
        "official_text_hash": hashlib.sha256(official_md.encode("utf-8")).hexdigest(),
        "gates": {
            "official_export_blocked_before_compile": {
                "passed": True,
                "expected": "409",
                "actual": str(blocked_before_compile.status_code),
                "detail": blocked_before_compile.json().get("detail", ""),
            },
            "official_export_blocked_before_review": {
                "passed": True,
                "expected": "409",
                "actual": str(blocked_before_review.status_code),
                "detail": blocked_before_review.json().get("detail", ""),
            },
            "post_draft_review_unlocks_export": {
                "passed": True,
                "expected": "export_allowed=true",
                "actual": str(post_review["export_allowed"]).lower(),
            },
            "official_export_hygiene": {
                "passed": True,
                "expected": "no internal markers",
                "actual": "clean",
            },
        },
    }


def _create_standard_project(client: TestClient, case: GoldenCase) -> str:
    project = _ok(
        client.post(
            "/api/projects",
            json={
                "name": case.project_name,
                "draft_text": _sample(case.sample),
                "patent_type": case.patent_type.value,
            },
        ),
        f"{case.workflow} create project",
    )
    return project["id"]


def _create_external_draft_project(client: TestClient, case: GoldenCase) -> str:
    project = _ok(
        client.post(
            "/api/projects",
            json={
                "name": case.project_name,
                "draft_text": "外部初稿导入 v1 smoke 项目。",
                "patent_type": "invention",
            },
        ),
        f"{case.workflow} create project",
    )
    project_id = project["id"]
    source = _ok(
        client.post(
            f"/api/projects/{project_id}/external-drafts",
            json={
                "source_type": "pasted_text",
                "file_name": f"{case.sample}.md",
                "text": _sample(case.sample),
            },
        ),
        f"{case.workflow} source",
    )
    intake = _ok(
        client.post(f"/api/projects/{project_id}/external-drafts/{source['id']}/intake-runs"),
        f"{case.workflow} intake",
    )
    parsed = intake["parsed_package"]
    if not parsed or not parsed["claims"] or not parsed["description"]:
        raise AssertionError(f"{case.workflow} parser did not recover required sections: {intake}")

    confirmed = _ok(
        client.post(
            f"/api/projects/{project_id}/external-draft-intake-runs/{intake['id']}/confirm",
            json={
                "title": parsed["title"] or "一种施工安全视频告警事件留痕方法",
                "abstract": parsed["abstract"] or "本发明公开一种施工安全视频告警事件留痕方法。",
                "claims": parsed["claims"],
                "description": parsed["description"],
                "drawing_description": parsed["drawing_description"] or "图1为方法流程图。",
            },
        ),
        f"{case.workflow} confirm",
    )
    if confirmed["status"] != "completed":
        raise AssertionError(f"{case.workflow} confirm did not complete: {confirmed}")
    return project_id


def _generate_standard_package(client: TestClient, project_id: str, case: GoldenCase) -> dict[str, Any]:
    if case.patent_type == PatentType.UTILITY_MODEL:
        requirement = _ok(
            client.get(f"/api/projects/{project_id}/formula-requirement"),
            f"{case.workflow} formula requirement",
        )
        if requirement["required"] is not False:
            raise AssertionError(f"{case.workflow} should skip formula requirement: {requirement}")
        package = _ok(client.post(f"/api/projects/{project_id}/generate", json={}), f"{case.workflow} generate")
        if package["deliberation_run_id"] is not None:
            raise AssertionError(f"{case.workflow} unexpectedly required deliberation")
        return package

    deliberation_id = _seed_completed_deliberation(client, project_id)
    formula_requirement = _ok(
        client.get(f"/api/projects/{project_id}/formula-requirement"),
        f"{case.workflow} formula requirement",
    )
    formula_id = None
    if formula_requirement["required"]:
        formula_run = _ok(
            client.post(f"/api/projects/{project_id}/formula-runs", json={}),
            f"{case.workflow} formula run",
        )
        if formula_run["status"] != "completed" or not formula_run["package"]:
            raise AssertionError(f"{case.workflow} formula run incomplete: {formula_run}")
        formula_id = formula_run["id"]

    payload: dict[str, str] = {"deliberation_run_id": deliberation_id}
    if formula_id:
        payload["formula_run_id"] = formula_id
    package = _ok(client.post(f"/api/projects/{project_id}/generate", json=payload), f"{case.workflow} generate")
    if package["deliberation_run_id"] != deliberation_id:
        raise AssertionError(f"{case.workflow} package did not retain deliberation id")
    return package


def _run_quality_checks(client: TestClient, project_id: str, label: str) -> dict[str, Any]:
    _ok(client.post(f"/api/projects/{project_id}/review"), f"{label} review")
    _ok(client.post(f"/api/projects/{project_id}/filing-readiness"), f"{label} filing readiness")
    _ok(client.post(f"/api/projects/{project_id}/claim-defense-worksheets"), f"{label} claim defense")
    return _ok(client.post(f"/api/projects/{project_id}/completion-runs"), f"{label} completion run")


def _project_package(client: TestClient, project_id: str) -> DraftPackage:
    app_state = getattr(client.app, "state")
    project = app_state.store.get_project(project_id)
    if not project or not project.package:
        raise AssertionError(f"project {project_id} has no generated package")
    return project.package


def _grantability_summary(client: TestClient, project_id: str, case: GoldenCase) -> dict[str, Any]:
    app_state = getattr(client.app, "state")
    report = generate_grantability_report(
        project_id=project_id,
        package=_project_package(client, project_id),
        disclosures=app_state.store.list_disclosure_runs(project_id),
        patent_points=app_state.store.list_project_patent_points(project_id),
        strategy_brief=PatentStrategyBrief(
            summary="v1.1 quality gate strategy: preserve verified differentiators and fail closed on weak evidence.",
            claim_strategy=["独立权利要求覆盖主区别特征，从属权利要求承接工程参数。"],
            description_strategy=["说明书补充证据状态、实施例和替代方式。"],
            risk_controls=["未验证效果不得写成已验证事实。"],
        ),
        deep_research_packets=[_deep_research_packet(project_id, case)],
        project_knowledge_state=_golden_project_knowledge_state(project_id, case),
    )
    if not report.claim_chart:
        raise AssertionError(f"{case.workflow} grantability report has no claim chart")
    if report.fail_closed:
        raise AssertionError(f"{case.workflow} grantability report failed closed despite golden evidence: {report}")
    return {
        "id": report.id,
        "status": report.status,
        "fail_closed": report.fail_closed,
        "claim_chart_rows": len(report.claim_chart),
        "novelty_attacks": len(report.novelty_attacks),
        "inventive_step_attacks": len(report.inventive_step_attacks),
        "low_evidence_flags": report.low_evidence_flags,
    }


def _workflow_result(
    *,
    case: GoldenCase,
    project_id: str,
    completion_run: dict[str, Any],
    export_result: dict[str, Any],
    grantability: dict[str, Any],
    disclosure: DisclosureRun,
) -> dict[str, Any]:
    scorecard = completion_run["scorecard"]
    trend = {field: scorecard[field] for field in TREND_FIELDS}
    drafting_quality = _drafting_quality_metrics(completion_run)
    research_hit_count = len(disclosure.package.prior_art_hits if disclosure.package else [])
    gates = {
        "research_evidence_count": {
            "passed": research_hit_count >= 2,
            "expected": ">=2",
            "actual": str(research_hit_count),
        },
        "grantability_report_present": {
            "passed": grantability["claim_chart_rows"] > 0 and not grantability["fail_closed"],
            "expected": "claim_chart_rows>0 and fail_closed=false",
            "actual": f"rows={grantability['claim_chart_rows']} fail_closed={grantability['fail_closed']}",
        },
        "quality_trend_present": {
            "passed": all(isinstance(trend[field], int) for field in TREND_FIELDS),
            "expected": ",".join(TREND_FIELDS),
            "actual": json.dumps(trend, ensure_ascii=False),
        },
        "evidence_binding_rate": {
            "passed": drafting_quality["evidence_binding_rate"] >= 0.1,
            "expected": ">=0.1",
            "actual": str(drafting_quality["evidence_binding_rate"]),
        },
        "core_feature_support_rate": {
            "passed": drafting_quality["core_feature_support_rate"] >= 0.4,
            "expected": ">=0.4",
            "actual": str(drafting_quality["core_feature_support_rate"]),
        },
        "unverified_effect_leak_count": {
            "passed": drafting_quality["unverified_effect_leak_count"] == 0,
            "expected": "0",
            "actual": str(drafting_quality["unverified_effect_leak_count"]),
        },
        **export_result["gates"],
    }
    failed_gates = [name for name, gate in gates.items() if not gate["passed"]]
    if failed_gates:
        raise AssertionError(f"{case.workflow} failed gates: {failed_gates}")
    return {
        "workflow": case.workflow,
        "category": case.category,
        "project_id": project_id,
        "official_compile_id": export_result["compile_id"],
        "post_draft_review_id": export_result["post_draft_review_id"],
        "official_package_hash": export_result["official_package_hash"],
        "official_text_hash": export_result["official_text_hash"],
        "research_evidence_count": research_hit_count,
        "research_confidence": disclosure.package.research_confidence if disclosure.package else "low",
        "grantability": grantability,
        "quality_trend": trend,
        "drafting_quality": drafting_quality,
        "gates": gates,
    }


def _drafting_quality_metrics(completion_run: dict[str, Any]) -> dict[str, Any]:
    rows = completion_run.get("support_matrix") or []
    issues = completion_run.get("issues") or []
    patches = completion_run.get("patches") or []
    core_rows = [row for row in rows if row.get("feature_classification") in CORE_FEATURE_CLASSES]
    rows_with_evidence = [row for row in rows if row.get("evidence_refs")]
    supported_core = [row for row in core_rows if row.get("completion_status") in {"supported", "partial"}]
    unsupported_core = [row for row in core_rows if row.get("completion_status") == "missing"]
    structural_rows = [
        row
        for row in rows
        if row.get("description_refs")
        or row.get("embodiment_refs")
        or row.get("formula_refs")
        or row.get("data_structure_refs")
        or row.get("pseudo_code_refs")
    ]
    unverified_leaks = [
        issue
        for issue in issues
        if issue.get("category") == "unverified_scheme_gap" and issue.get("blocks_submission")
    ]
    official_safe_evidence_patches = [
        patch
        for patch in patches
        if patch.get("can_enter_official_draft") and patch.get("evidence_refs")
    ]
    sidecar_patches = [patch for patch in patches if patch.get("patch_kind") == "sidecar_only"]
    return {
        "evidence_binding_rate": _ratio(len(rows_with_evidence), len(rows)),
        "core_feature_support_rate": _ratio(len(supported_core), len(core_rows)),
        "unsupported_core_feature_count": len(unsupported_core),
        "unverified_effect_leak_count": len(unverified_leaks),
        "dependent_fallback_depth": sum(1 for row in rows if row.get("feature_classification") == "dependent_fallback"),
        "embodiment_density": _ratio(len(structural_rows), len(rows)),
        "patch_delta": len(official_safe_evidence_patches) - len(sidecar_patches),
    }


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 3)


def run_golden_case(client: TestClient, case: GoldenCase) -> dict[str, Any]:
    if case.source == "external_draft":
        project_id = _create_external_draft_project(client, case)
    else:
        project_id = _create_standard_project(client, case)
        _generate_standard_package(client, project_id, case)

    disclosure, _point = _seed_research_bundle(client, project_id, case)
    completion_run = _run_quality_checks(client, project_id, case.workflow)
    export_result = _prepare_official_export(client, project_id, case.workflow)
    if case.source == "external_draft":
        bundle = _ok(
            client.get(f"/api/projects/{project_id}/external-draft-review-bundle/report.md"),
            f"{case.workflow} review bundle",
        )
        if "EXTERNAL_DRAFT_REVIEW_BUNDLE" not in bundle:
            raise AssertionError(f"{case.workflow} review bundle missing marker")
    grantability = _grantability_summary(client, project_id, case)
    return _workflow_result(
        case=case,
        project_id=project_id,
        completion_run=completion_run,
        export_result=export_result,
        grantability=grantability,
        disclosure=disclosure,
    )


def _classify_failure(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}".lower()
    provider_markers = ("provider", "api key", "deepseek", "not configured", "unavailable")
    environment_markers = ("no module named", "permission denied", "node", "npm", "missing sample")
    if any(marker in text for marker in provider_markers):
        return "unavailable_provider"
    if any(marker in text for marker in environment_markers):
        return "environment"
    return "code"


def _loop_quality_signature(workflow: dict[str, Any]) -> dict[str, Any]:
    """Return the stable quality surface for loop repeatability checks."""

    gates = workflow.get("gates") or {}
    grantability = workflow.get("grantability") or {}
    return {
        "workflow": workflow.get("workflow", ""),
        "category": workflow.get("category", ""),
        "official_text_hash": workflow.get("official_text_hash", ""),
        "research_evidence_count": workflow.get("research_evidence_count", 0),
        "research_confidence": workflow.get("research_confidence", ""),
        "grantability": {
            "status": grantability.get("status"),
            "fail_closed": grantability.get("fail_closed"),
            "claim_chart_rows": grantability.get("claim_chart_rows"),
            "novelty_attacks": grantability.get("novelty_attacks"),
            "inventive_step_attacks": grantability.get("inventive_step_attacks"),
            "low_evidence_flags": grantability.get("low_evidence_flags"),
        },
        "quality_trend": {field: (workflow.get("quality_trend") or {}).get(field) for field in TREND_FIELDS},
        "drafting_quality": {
            field: (workflow.get("drafting_quality") or {}).get(field) for field in DRAFTING_QUALITY_FIELDS
        },
        "gates": {
            name: {
                "passed": gate.get("passed"),
                "actual": gate.get("actual"),
            }
            for name, gate in sorted(gates.items())
        },
    }


def _loop_repeatability_failures(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    baseline_by_workflow: dict[str, dict[str, Any]] = {}
    drifted_workflows: set[str] = set()
    failures: list[dict[str, str]] = []
    for workflow in results:
        workflow_id = str(workflow.get("workflow", ""))
        if not workflow_id or workflow_id in drifted_workflows:
            continue
        signature = _loop_quality_signature(workflow)
        baseline = baseline_by_workflow.setdefault(workflow_id, signature)
        if signature != baseline:
            drifted_workflows.add(workflow_id)
            failures.append(
                {
                    "workflow": workflow_id,
                    "category": str(workflow.get("category", "")),
                    "classification": "code",
                    "message": f"loop repeatability drift detected for workflow {workflow_id}",
                }
            )
    return failures


def _loop_gate_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    for group, names in LOOP_GATE_GROUPS.items():
        gate_rows: list[dict[str, Any]] = []
        for name in names:
            values = [
                (workflow.get("gates") or {}).get(name)
                for workflow in results
                if name in (workflow.get("gates") or {})
            ]
            passed = sum(1 for gate in values if gate and gate.get("passed"))
            gate_rows.append(
                {
                    "name": name,
                    "passed": passed,
                    "total": len(values),
                    "all_passed": bool(values) and passed == len(values),
                }
            )
        grouped[group] = {
            "gates": gate_rows,
            "all_passed": all(row["all_passed"] for row in gate_rows),
        }
    return grouped


def _build_report(
    results: list[dict[str, Any]],
    failures: list[dict[str, str]],
    *,
    repeat_count: int = 1,
    repeatability_failures: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    categories = sorted({case.category for case in GOLDEN_CASES})
    repeatability_failures = list(repeatability_failures or [])
    return {
        "suite": "v1.1 deterministic quality gate",
        "deterministic": True,
        "live_provider_tests": "opt-in only; default suite uses TestClient and V1SmokeLLM",
        "passed": not failures and not repeatability_failures,
        "summary": {
            "expected_workflows": len(GOLDEN_CASES) * repeat_count,
            "completed_workflows": len(results),
            "failed_workflows": len(failures),
            "execution_failures": len(failures),
            "repeatability_failures": len(repeatability_failures),
            "total_failures": len(failures) + len(repeatability_failures),
            "repeat_count": repeat_count,
            "categories": categories,
            "trend_fields": list(TREND_FIELDS),
            "drafting_quality_fields": list(DRAFTING_QUALITY_FIELDS),
        },
        "loop_engineering": {
            "objective": LOOP_OBJECTIVE,
            "standard": LOOP_STANDARD,
            "gate_groups": _loop_gate_summary(results),
            "repeatability_failures": repeatability_failures,
        },
        "workflows": results,
        "failures": failures,
    }


def _render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# PatentAgent v1.1 deterministic quality gate",
        "",
        f"- passed: {str(report['passed']).lower()}",
        f"- deterministic: {str(report['deterministic']).lower()}",
        f"- live_provider_tests: {report['live_provider_tests']}",
        f"- completed_workflows: {report['summary']['completed_workflows']}/{report['summary']['expected_workflows']}",
        f"- failed_workflows: {report['summary']['failed_workflows']}",
        f"- repeatability_failures: {report['summary']['repeatability_failures']}",
        f"- categories: {', '.join(report['summary']['categories'])}",
        "",
        "## Loop Engineering Gates",
        "",
        f"- objective: {report['loop_engineering']['objective']}",
        f"- standard: {report['loop_engineering']['standard']}",
        f"- repeat_count: {report['summary']['repeat_count']}",
        "",
    ]
    for group, summary in report["loop_engineering"]["gate_groups"].items():
        lines.append(f"### {group}")
        for gate in summary["gates"]:
            lines.append(f"- {gate['name']}: {gate['passed']}/{gate['total']}")
        lines.append("")
    if report["loop_engineering"]["repeatability_failures"]:
        lines.append("### repeatability_failures")
        for failure in report["loop_engineering"]["repeatability_failures"]:
            lines.append(f"- {failure['workflow']}: {failure['message']}")
        lines.append("")
    lines.extend(
        [
            "## Workflows",
            "",
        ]
    )
    for workflow in report["workflows"]:
        lines.extend(
            [
                f"### {workflow['workflow']}",
                "",
                f"- category: {workflow['category']}",
                f"- project_id: {workflow['project_id']}",
                f"- research_evidence_count: {workflow['research_evidence_count']}",
                f"- research_confidence: {workflow['research_confidence']}",
                f"- grantability_status: {workflow['grantability']['status']}",
                f"- official_package_hash: {workflow['official_package_hash']}",
                f"- official_text_hash: {workflow.get('official_text_hash', '')}",
                "- quality_trend:",
            ]
        )
        for field in TREND_FIELDS:
            lines.append(f"  - {field}: {workflow['quality_trend'][field]}")
        lines.append("- drafting_quality:")
        for field in DRAFTING_QUALITY_FIELDS:
            lines.append(f"  - {field}: {workflow['drafting_quality'][field]}")
        lines.extend(["- gates:"])
        for name, gate in workflow["gates"].items():
            lines.append(f"  - {name}: {'pass' if gate['passed'] else 'fail'} ({gate['actual']})")
        lines.append("")
    if report["failures"]:
        lines.extend(["## Failures", ""])
        for failure in report["failures"]:
            lines.extend(
                [
                    f"- workflow: {failure['workflow']}",
                    f"  classification: {failure['classification']}",
                    f"  message: {failure['message']}",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def _write_report(report_dir: Path, report: dict[str, Any]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "v1_1_quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (report_dir / "v1_1_quality_report.md").write_text(
        _render_markdown_report(report),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic PatentAgent v1.1 golden E2E quality gates.")
    parser.add_argument("--report-dir", type=Path, help="Directory for v1.1 quality JSON/Markdown reports.")
    parser.add_argument("--json", action="store_true", help="Print the full report JSON to stdout.")
    parser.add_argument(
        "--repeat-count",
        type=int,
        default=1,
        help="Run each golden workflow this many times and fail if stable quality signatures drift.",
    )
    args = parser.parse_args(argv)
    if args.repeat_count < 1:
        parser.error("--repeat-count must be >= 1")

    for name in SAMPLES:
        _sample(name)

    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for round_index in range(1, args.repeat_count + 1):
        with tempfile.TemporaryDirectory(prefix=f"patentagent-v1-smoke-r{round_index}-") as data_dir:
            client = TestClient(
                create_app(
                    data_dir=Path(data_dir),
                    llm_client=V1SmokeLLM(),
                    load_env_file=False,
                )
            )
            health = _ok(client.get("/api/health"), "health")
            if health["ok"] is not True or health["llm_configured"] is not True:
                raise AssertionError(f"unexpected health payload: {health}")

            for case in GOLDEN_CASES:
                try:
                    result = run_golden_case(client, case)
                    result["loop_round"] = round_index
                    results.append(result)
                except Exception as exc:  # keep running so the report lists all failing workflows.
                    failures.append(
                        {
                            "workflow": case.workflow,
                            "category": case.category,
                            "classification": _classify_failure(exc),
                            "message": str(exc),
                        }
                    )

    repeatability_failures = _loop_repeatability_failures(results)

    report = _build_report(
        results,
        failures,
        repeat_count=args.repeat_count,
        repeatability_failures=repeatability_failures,
    )
    if args.report_dir:
        _write_report(args.report_dir, report)

    all_failures = failures + repeatability_failures
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    if all_failures:
        print("v1.1 deterministic quality gate failed")
        for failure in all_failures:
            print(f"- {failure['workflow']}: {failure['classification']}: {failure['message']}")
        return 1

    print("v1.1 deterministic quality gate passed")
    print("v1 API smoke passed")
    for result in results:
        print(
            f"- {result['workflow']}: project={result['project_id']} "
            f"official_compile={result['official_compile_id']} overall={result['quality_trend']['overall']}"
        )
    if args.report_dir:
        print(f"report: {args.report_dir / 'v1_1_quality_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
