from __future__ import annotations

import zipfile

from backend.app.corpus.filters import is_ai_software_invention
from backend.app.corpus.metadata import parse_metadata_table
from backend.app.corpus.pipeline import CorpusImportService
from backend.app.patent_parser import extract_claims
from backend.app.rag import LocalVectorIndex
from backend.app.storage import SQLiteStore


def test_parse_cnipa_csv_metadata_and_filter_ai_software_inventions(tmp_path):
    csv_path = tmp_path / "metadata.csv"
    csv_path.write_text(
        "申请号,授权公告号,专利名称,申请人,发明人,IPC分类号,专利类型,申请日,法律状态,文件名\n"
        "202310000001.0,CN116000001B,一种图像缺陷识别方法,某科技公司,张三,G06V 10/82,发明授权,2023-01-01,授权,cn116000001b.txt\n"
        "202320000002.0,CN219000002U,一种检测装置,某科技公司,李四,G06V 10/00,实用新型,2023-02-01,授权,cn219000002u.txt\n",
        encoding="utf-8",
    )

    rows = parse_metadata_table(csv_path)

    assert rows[0]["application_number"] == "202310000001.0"
    assert rows[0]["grant_number"] == "CN116000001B"
    assert rows[0]["title"] == "一种图像缺陷识别方法"
    assert rows[0]["applicants"] == ["某科技公司"]
    assert rows[0]["ipc"] == ["G06V 10/82"]
    assert rows[0]["source_file_name"] == "cn116000001b.txt"
    assert is_ai_software_invention(rows[0], "利用神经网络模型进行图像缺陷识别")
    assert not is_ai_software_invention(rows[1], "利用神经网络模型进行图像缺陷识别")


def test_extract_claims_records_references_and_claim_category():
    claims_text = """
1. 一种图像缺陷识别方法，其特征在于，包括采集图像、训练神经网络模型并输出缺陷位置。
2. 根据权利要求1所述的方法，其特征在于，所述训练包括构建样本集。
3. 一种图像缺陷识别系统，其特征在于，包括处理器和存储器。
4. 一种计算机可读存储介质，其上存储有计算机程序。
"""

    claims = extract_claims(claims_text)

    assert [claim.number for claim in claims] == [1, 2, 3, 4]
    assert claims[0].kind == "independent"
    assert claims[0].category == "method"
    assert claims[1].references == [1]
    assert claims[2].category == "system"
    assert claims[3].category == "medium"


def test_corpus_import_service_imports_zip_deduplicates_and_reports_quality(tmp_path):
    store = SQLiteStore(tmp_path / "db.sqlite3")
    index = LocalVectorIndex()
    archive_path = tmp_path / "cnipa-export.zip"
    patent_text = """一种图像缺陷识别方法
摘要
本发明公开了一种基于神经网络模型的图像缺陷识别方法。
权利要求书
1. 一种图像缺陷识别方法，其特征在于，包括采集待检测图像、训练神经网络模型并输出缺陷位置。
2. 根据权利要求1所述的方法，其特征在于，所述训练包括构建缺陷样本集。
说明书
技术领域
本发明涉及人工智能图像检测技术领域。
背景技术
现有检测方式依赖人工经验。
发明内容
本发明解决缺陷检测效率低的问题。
附图说明
图1为本发明的方法流程图。
具体实施方式
系统采集图像、训练模型并输出检测结果。
"""
    non_ai_text = """一种桌面清洁结构
摘要
本发明公开了一种机械清洁结构。
权利要求书
1. 一种桌面清洁结构，其特征在于，包括刷体。
说明书
具体实施方式
刷体沿桌面移动。
"""
    metadata = (
        "申请号,授权公告号,专利名称,申请人,发明人,IPC分类号,专利类型,申请日,法律状态,文件名\n"
        "202310000001.0,CN116000001B,一种图像缺陷识别方法,某科技公司,张三,G06V 10/82,发明授权,2023-01-01,授权,cn116000001b.txt\n"
        "202310000001.0,CN116000001B,一种图像缺陷识别方法,某科技公司,张三,G06V 10/82,发明授权,2023-01-01,授权,duplicate.txt\n"
        "202310000003.0,CN116000003B,一种桌面清洁结构,某机械公司,王五,A47L 11/00,发明授权,2023-03-01,授权,cn116000003b.txt\n"
        "202320000004.0,CN219000004U,一种检测装置,某科技公司,赵六,G06V 10/00,实用新型,2023-04-01,授权,utility.txt\n"
    )
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("metadata.csv", metadata)
        archive.writestr("cn116000001b.txt", patent_text)
        archive.writestr("duplicate.txt", patent_text)
        archive.writestr("cn116000003b.txt", non_ai_text)
        archive.writestr("utility.txt", patent_text)

    service = CorpusImportService(store=store, index=index, data_dir=tmp_path / "data")
    job = service.create_job(
        source_type="cnipa_export",
        source_name="CNIPA",
        query="G06V 神经网络 图像缺陷",
        domain="ai_software",
        version_name="ai-software-v1",
    )
    service.add_input(job.id, archive_path)
    completed = service.run_job(job.id)

    assert completed.status == "completed"
    assert completed.quality_report is not None
    assert completed.quality_report.imported_documents == 1
    assert completed.quality_report.duplicate_documents == 1
    assert completed.quality_report.filtered_documents == 2
    assert completed.quality_report.section_coverage["claims"] == 1.0
    assert completed.quality_report.indexed_chunks >= 5

    documents = store.list_documents()
    assert len(documents) == 1
    assert documents[0].metadata["version_name"] == "ai-software-v1"
    assert documents[0].metadata["grant_number"] == "CN116000001B"
    assert documents[0].metadata["claims"][1]["references"] == [1]
    assert store.list_corpus_versions()[0].document_count == 1

    results = index.search("图像缺陷识别 神经网络 方法", limit=3)
    assert any(result.chunk.section_type.value == "claims" for result in results)


def test_corpus_import_allows_same_patent_in_different_versions(tmp_path):
    store = SQLiteStore(tmp_path / "db.sqlite3")
    index = LocalVectorIndex()
    patent_path = tmp_path / "cn116000001b.txt"
    patent_path.write_text(
        """一种图像缺陷识别方法
摘要
本发明公开了一种基于神经网络模型的图像缺陷识别方法。
权利要求书
1. 一种图像缺陷识别方法，其特征在于，包括采集待检测图像、训练神经网络模型并输出缺陷位置。
说明书
技术领域
本发明涉及人工智能图像检测技术领域。
背景技术
现有检测方式依赖人工经验。
发明内容
本发明解决缺陷检测效率低的问题。
附图说明
图1为本发明的方法流程图。
具体实施方式
系统采集图像、训练模型并输出检测结果。
""",
        encoding="utf-8",
    )

    service = CorpusImportService(store=store, index=index, data_dir=tmp_path / "data")
    first = service.create_job(version_name="public-v1", source_type="seed", domain="ai_software")
    service.add_input(first.id, patent_path)
    first_done = service.run_job(first.id)
    second = service.create_job(version_name="public-v2", source_type="seed", domain="ai_software")
    service.add_input(second.id, patent_path)
    second_done = service.run_job(second.id)

    assert first_done.imported_documents == 1
    assert second_done.imported_documents == 1
    assert store.get_corpus_stats("public-v1")["document_count"] == 1
    assert store.get_corpus_stats("public-v2")["document_count"] == 1
