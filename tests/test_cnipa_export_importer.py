from pathlib import Path
from zipfile import ZipFile

from openpyxl import Workbook

from backend.app.knowledge.cnipa_export import (
    CnipaExportImportContext,
    parse_cnipa_official_export_file,
)


def _context() -> CnipaExportImportContext:
    return CnipaExportImportContext(
        project_id="p-1",
        plan_id="plan-1",
        import_ledger_id="ledger-1",
        query="城市体检 智能体",
        strategy_group_id="cnipa-official-export",
    )


def test_parse_cnipa_csv_export_maps_fields(tmp_path: Path):
    path = tmp_path / "cnipa.csv"
    path.write_text(
        "公开公告号,专利名称,申请人,公开日,摘要,IPC\n"
        "CN112233445A,城市体检智能体任务编排方法,示例公司,2024-01-01,公开了一种任务编排方法。,G06Q\n",
        encoding="utf-8-sig",
    )

    result = parse_cnipa_official_export_file(path, context=_context())

    assert result.parsed_count == 1
    assert result.raw_file_hash
    assert result.hits[0].source == "cnipa_official_export"
    assert result.hits[0].publication_number == "CN112233445A"
    assert result.hits[0].title == "城市体检智能体任务编排方法"
    assert result.hits[0].applicant == "示例公司"
    assert result.hits[0].ipc == ["G06Q"]
    assert result.hits[0].metadata["raw_file_hash"] == result.raw_file_hash
    assert result.hits[0].metadata["import_ledger_id"] == "ledger-1"
    assert result.hits[0].metadata["source_file_name"] == "cnipa.csv"
    assert result.hits[0].metadata["row_number"] == 2


def test_parse_cnipa_xlsx_export_maps_fields(tmp_path: Path):
    path = tmp_path / "cnipa.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["申请公布号", "名称", "专利权人", "摘要"])
    sheet.append(["CN998877665A", "可信复核系统", "示例研究院", "公开了一种可信复核系统。"])
    workbook.save(path)

    result = parse_cnipa_official_export_file(path, context=_context())

    assert result.parsed_count == 1
    assert result.hits[0].publication_number == "CN998877665A"
    assert result.hits[0].title == "可信复核系统"
    assert result.hits[0].applicant == "示例研究院"


def test_parse_cnipa_zip_export_reads_nested_tables_and_warns_on_pdf(tmp_path: Path):
    csv_path = tmp_path / "inner.csv"
    csv_path.write_text(
        "申请号,题名,摘要\nCN202410000001,城市体检证据链方法,公开了一种证据链复核方法。\n",
        encoding="utf-8",
    )
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 scanned placeholder")
    zip_path = tmp_path / "cnipa.zip"
    with ZipFile(zip_path, "w") as archive:
        archive.write(csv_path, "metadata/inner.csv")
        archive.write(pdf_path, "docs/scan.pdf")

    result = parse_cnipa_official_export_file(zip_path, context=_context())

    assert result.row_count == 1
    assert result.parsed_count == 1
    assert result.hits[0].application_number == "CN202410000001"
    assert any("scan.pdf" in warning for warning in result.warnings)


def test_parse_cnipa_export_rejects_rows_without_identifier_or_title(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text("申请人,公开日\n示例公司,2024-01-01\n", encoding="utf-8")

    result = parse_cnipa_official_export_file(path, context=_context())

    assert result.parsed_count == 0
    assert result.failures[0].code == "missing_required_fields"
