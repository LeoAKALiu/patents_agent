from backend.app.rag import LocalVectorIndex
from backend.app.schemas import PatentChunk, SectionType


def test_vector_search_prefers_same_domain_and_section_without_mixing_claims():
    index = LocalVectorIndex()
    chunks = [
        PatentChunk(
            id="claim-ai",
            document_id="doc-a",
            section_type=SectionType.CLAIMS,
            text="一种图像缺陷识别方法，包括训练神经网络模型并输出检测结果。",
            ordinal=1,
            metadata={"domain": "ai"},
        ),
        PatentChunk(
            id="abstract-ai",
            document_id="doc-a",
            section_type=SectionType.ABSTRACT,
            text="本发明公开了一种图像缺陷识别系统。",
            ordinal=2,
            metadata={"domain": "ai"},
        ),
        PatentChunk(
            id="claim-civil",
            document_id="doc-b",
            section_type=SectionType.CLAIMS,
            text="一种混凝土梁施工方法，包括模板安装和浇筑养护。",
            ordinal=1,
            metadata={"domain": "civil"},
        ),
    ]
    index.add(chunks)

    results = index.search("图像 神经网络 缺陷 检测 方法", section_type=SectionType.CLAIMS, limit=2)

    assert [result.chunk.id for result in results] == ["claim-ai", "claim-civil"]
    assert all(result.chunk.section_type == SectionType.CLAIMS for result in results)
    assert results[0].score > results[1].score
