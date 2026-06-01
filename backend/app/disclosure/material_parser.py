from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from backend.app.patent_parser import read_document_text


def read_project_material_text(path: Path) -> tuple[str, list[str]]:
    suffix = path.suffix.lower()
    warnings: list[str] = []
    if suffix in {".txt", ".md", ".markdown", ".pdf", ".docx"}:
        text = read_document_text(path)
    elif suffix in {".pptx", ".ppsx"}:
        text = _read_pptx_text(path)
    else:
        raise ValueError(f"Unsupported project material file type: {suffix}")
    normalized = _normalize_text(text)
    if len(normalized) < 20:
        warnings.append("材料文本较短，可能不足以支撑专利点挖掘。")
    return normalized, warnings


def _read_pptx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            slide_names = sorted(
                name
                for name in archive.namelist()
                if name.startswith("ppt/slides/slide") and name.endswith(".xml")
            )
            lines: list[str] = []
            for slide_name in slide_names:
                xml = archive.read(slide_name)
                root = ElementTree.fromstring(xml)
                slide_lines = [
                    node.text.strip()
                    for node in root.iter()
                    if node.tag.endswith("}t") and node.text and node.text.strip()
                ]
                if slide_lines:
                    lines.append(f"## {Path(slide_name).stem}")
                    lines.extend(slide_lines)
            text = "\n".join(lines)
    except (zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise ValueError(f"PPTX material is not readable: {exc}") from exc
    if not text.strip():
        raise ValueError("PPTX material contains no extractable text.")
    return text


def _normalize_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text.strip())

