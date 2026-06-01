from __future__ import annotations

from typing import Any


AI_SOFTWARE_IPC_PREFIXES = ("G06F", "G06N", "G06V", "G06Q", "H04L")
AI_SOFTWARE_KEYWORDS = (
    "人工智能",
    "神经网络",
    "深度学习",
    "机器学习",
    "图像识别",
    "图像缺陷",
    "数据处理",
    "模型训练",
    "缺陷检测",
    "软件平台",
    "计算机实现方法",
    "模型推理",
    "算法",
)


def is_ai_software_invention(metadata: dict[str, Any], text: str) -> bool:
    if not _is_invention(metadata):
        return False
    ipc_values = _as_list(metadata.get("ipc")) + _as_list(metadata.get("cpc"))
    if any(_matches_ipc_prefix(value) for value in ipc_values):
        return True
    searchable = " ".join(
        [
            str(metadata.get("title", "")),
            str(metadata.get("abstract", "")),
            text[:8000],
        ]
    )
    return any(keyword in searchable for keyword in AI_SOFTWARE_KEYWORDS)


def _is_invention(metadata: dict[str, Any]) -> bool:
    patent_type = str(metadata.get("patent_type", "")).lower()
    title = str(metadata.get("title", ""))
    legal_status = str(metadata.get("legal_status", ""))
    combined = f"{patent_type} {title} {legal_status}"
    if any(term in combined for term in ["实用新型", "外观设计", "utility", "design"]):
        return False
    if not patent_type:
        return True
    return "发明" in patent_type or "invention" in patent_type


def _matches_ipc_prefix(value: str) -> bool:
    normalized = value.upper().replace(" ", "")
    return any(normalized.startswith(prefix) for prefix in AI_SOFTWARE_IPC_PREFIXES)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]
