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
        try:
            text = read_document_text(path)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(
                f"Failed to read {suffix} material \"{path.name}\": {exc}"
            ) from exc
        if suffix == ".docx" and not text.strip():
            raise ValueError(
                f"DOCX material \"{path.name}\" contains no extractable text. "
                "If the document has text, please re-save it as a standard .docx file."
            )
    elif suffix in {".pptx", ".ppsx"}:
        text = _read_pptx_text(path)
    else:
        raise ValueError(
            f"Unsupported project material file type \"{suffix}\". "
            f"Supported types: .txt, .md, .markdown, .pdf, .docx, .pptx, .ppsx."
        )
    normalized = _normalize_text(text)
    if len(normalized) < 20:
        warnings.append(
            "材料文本较短（不足20字符），可能不足以支撑专利点挖掘。"
            "建议上传包含技术方案、模块/步骤描述的完整文档。"
        )
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
