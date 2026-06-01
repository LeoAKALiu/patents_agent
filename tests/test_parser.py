from backend.app.patent_parser import extract_claims, split_patent_sections
from backend.app.schemas import SectionType


def test_split_patent_sections_classifies_chinese_patent_headings():
    text = """
摘要
本发明公开了一种基于多模态模型的缺陷识别方法。
权利要求书
1. 一种缺陷识别方法，其特征在于，包括获取图像、提取特征和输出结果。
2. 根据权利要求1所述的方法，其中所述特征包括深度特征。
说明书
技术领域
本发明涉及人工智能检测技术领域。
背景技术
现有方法依赖人工标注。
发明内容
本发明解决识别精度低的问题。
附图说明
图1为本发明的方法流程图。
具体实施方式
如图1所示，系统执行训练和推理步骤。
"""

    sections = split_patent_sections(text)

    assert [section.type for section in sections] == [
        SectionType.ABSTRACT,
        SectionType.CLAIMS,
        SectionType.DESCRIPTION,
        SectionType.TECHNICAL_FIELD,
        SectionType.BACKGROUND,
        SectionType.SUMMARY,
        SectionType.DRAWINGS,
        SectionType.EMBODIMENTS,
    ]
    assert sections[1].heading == "权利要求书"
    assert "深度特征" in sections[1].text


def test_extract_claims_keeps_independent_and_dependent_claim_numbers():
    claims_text = """
1. 一种专利撰写方法，其特征在于，包括：解析技术交底书；生成权利要求。
2. 根据权利要求1所述的方法，其特征在于，所述解析包括识别技术问题。
3. 根据权利要求1所述的方法，其特征在于，所述生成包括输出从属权利要求。
"""

    claims = extract_claims(claims_text)

    assert [claim.number for claim in claims] == [1, 2, 3]
    assert claims[0].kind == "independent"
    assert claims[1].kind == "dependent"
    assert "识别技术问题" in claims[1].text
