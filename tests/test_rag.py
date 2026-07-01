import json
import os
import subprocess
import sys
from pathlib import Path

from backend.app.rag import LocalVectorIndex, create_vector_index
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


def test_chroma_hash_embedding_is_stable_across_python_hash_seeds():
    code = (
        "import json;"
        "from backend.app.rag import _hash_embedding;"
        "print(json.dumps(_hash_embedding('图像 neural 图像 缺陷', 32)))"
    )

    def embedding_for_seed(seed: str) -> list[float]:
        env = {**os.environ, "PYTHONHASHSEED": seed}
        output = subprocess.check_output([sys.executable, "-c", code], cwd=Path.cwd(), env=env, text=True)
        return json.loads(output)

    assert embedding_for_seed("1") == embedding_for_seed("2")


def test_vector_index_can_be_forced_local_for_test_suites(tmp_path, monkeypatch):
    monkeypatch.setenv("PATENTS_AGENT_VECTOR_INDEX", "local")

    index = create_vector_index(tmp_path / "chroma")

    assert isinstance(index, LocalVectorIndex)
