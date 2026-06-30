from fastapi.testclient import TestClient

from backend.app.deliberation.providers import ProviderTaskResult
from backend.app.official_compile import (
    OfficialDraftCompiler,
)
from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.storage import SQLiteStore
from backend.app.schemas import DraftPackage


def test_compiler_blocks_internal_pollution_in_official_fields():
    package = _draft_package(
        claims="好的，下面撰写权利要求书。\n1. 一种方法。\n\n撰写说明与支撑不足提示 support_gap: 需要补矩阵。",
        description=(
            "## 说明书\n"
            "本发明涉及无人机采集。\n"
            "```mermaid\nflowchart TD\nA-->B\n```\n"
            "generation_logs: claims generated\n"
            "根据会审策略补充。"
        ),
        drawing_description="图1为方法流程图。\nimage_prompt: 黑白线稿。",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "support_gap" for item in run.contamination_removed)
    assert any(item["pattern"] == "image_prompt" for item in run.contamination_removed)
    assert any(item["category"] == "official_hygiene_contamination" for item in run.blocked_items)


def test_compiler_cleans_observed_surface_pollution_without_claiming_dirty_output_clean():
    package = _draft_package(
        title="一种城市体检指标驱动无人机主动采集方法方法",
        claims="好的，根据技术交底书撰写权利要求。\n1. 一种待验证的城市体检指标驱动无人机采集方法。",
        description="主席修订：本发明颠覆固定航线模式，需在提交前补充实验数据。",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "completed"
    assert run.official_package is not None
    official_text = "\n".join(
        [
            run.official_package.title,
            run.official_package.claims,
            run.official_package.description,
        ]
    )
    for term in ("好的，根据", "待验证", "主席修订", "需在提交前补充", "颠覆", "方法方法"):
        assert term not in official_text
    assert {item["pattern"] for item in run.contamination_removed} >= {
        "方法方法",
        "好的，根据",
        "待验证",
        "主席修订",
        "需在提交前补充",
        "颠覆",
    }


def test_compiler_blocks_cross_project_title_contamination():
    package = _draft_package(
        description="本说明书还包括：基于边缘端动态推理的无人机飞行中任务调整方法。"
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["category"] == "cross_project_contamination" for item in run.blocked_items)


def test_compiler_blocks_when_cleaning_empties_required_section():
    package = _draft_package(description="support_gap: 说明书待补充。")

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["category"] == "empty_required_section" for item in run.blocked_items)


def test_compiler_blocks_json_style_prompt_internal_field():
    package = _draft_package(
        drawing_description='图1为方法流程图。\n"prompt": "黑白线稿"',
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "prompt" for item in run.contamination_removed)


def test_compiler_blocks_non_empty_official_json_field_wrappers():
    package = _draft_package(
        claims='{"claims": "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。"}',
        description='{"description": {"technical_field": "本发明涉及无人机任务规划技术领域。"}}',
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    removed_patterns = {item["pattern"] for item in run.contamination_removed}
    assert {"claims", "description"} <= removed_patterns
    assert any(item["category"] == "official_hygiene_contamination" for item in run.blocked_items)


def test_compiler_blocks_chinese_evidence_metadata_aliases_and_markdown_links():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。\n"
            "证据编号：EV-001\n"
            "材料编号：material-1"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。\n"
            "来源标签：实验记录.md\n"
            "引用来源：[CN111111A](https://example.test/patent/CN111111A)"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    removed_patterns = {item["pattern"] for item in run.contamination_removed}
    assert {"证据编号", "材料编号", "来源标签", "引用来源"} <= removed_patterns
    assert any(item["category"] == "official_hygiene_contamination" for item in run.blocked_items)


def test_compiler_blocks_inline_url_and_markdown_link_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包，"
            "其中参数来自[内部实验报告](https://internal.example/reports/exp-1.pdf)。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。"
            "补充材料参见 https://internal.example/materials/source.docx。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "url" for item in run.blocked_items)


def test_compiler_blocks_bracketed_evidence_citation_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包，"
            "其中校准参数依据[evidence:EV-CITY-001]确定。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。"
            "控制器按照采集指标生成任务节点【来源：实验记录.md】。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "bracketed_citation" for item in run.blocked_items)


def test_compiler_blocks_parenthetical_evidence_citation_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包，"
            "其中采集阈值由控制器动态确定（来源：实验记录.md）。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。"
            "任务包包含复核节点 (source: lab-note-001) 和状态记录节点。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "parenthetical_citation" for item in run.blocked_items)


def test_compiler_blocks_xml_evidence_tag_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包，"
            "<source id=\"CN111111A\">内部对比文件</source>。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。"
            "<evidence ref=\"EV-CITY-001\">实验记录</evidence>用于确定采集阈值。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "xml_evidence_tag" for item in run.blocked_items)


def test_compiler_blocks_html_comment_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。"
            "<!-- source: lab-note-001 -->"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。"
            "<!-- 证据：EV-CITY-001 -->控制器根据采集阈值生成任务。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_comment_citation" for item in run.blocked_items)


def test_compiler_blocks_html_attribute_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包，"
            "<span data-source=\"lab-note-001\">采集阈值</span>由控制器动态确定。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。"
            "<section evidence-ref=\"EV-CITY-001\">任务包包含复核节点。</section>"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_attribute_citation" for item in run.blocked_items)


def test_compiler_blocks_html_class_id_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中"
            '<span class="evidence EV-CITY-001">控制器</span>生成任务包。'
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            '<section id="source-lab-note-001">采集日志</section>执行复核。'
        ),
        drawing_description='图1为任务包生成流程图。<div class="来源 实验记录">图1</div>',
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_class_id_citation" for item in run.blocked_items)


def test_compiler_blocks_html_data_value_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中"
            '<span data-note="evidence: EV-CITY-001">控制器</span>生成任务包。'
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            '<section data-review="证据：EV-CITY-002">采集日志</section>执行复核。'
        ),
        drawing_description='图1为任务包生成流程图。<div data-extra="source: lab-note-002">图1</div>',
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_data_value_citation" for item in run.blocked_items)


def test_compiler_blocks_html_event_handler_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中"
            '<button onclick="track(\'evidence: EV-CITY-001\')">控制器</button>生成任务包。'
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            '<span onmouseover="console.log(\'证据：EV-CITY-002\')">采集日志</span>执行复核。'
        ),
        drawing_description='图1为任务包生成流程图。<a href="#fig1" onfocus="note=\'source: lab-note-002\'">图1</a>',
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_event_handler_citation" for item in run.blocked_items)


def test_compiler_blocks_html_url_attribute_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器"
            '<a href="#evidence=EV-CITY-001">生成任务包</a>。'
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            '<iframe src="/preview?证据=EV-CITY-002"></iframe>采集日志执行复核。'
        ),
        drawing_description='图1为任务包生成流程图。<link href="/figures?source=lab-note-002" rel="preload">',
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_url_attribute_citation" for item in run.blocked_items)


def test_compiler_blocks_html_srcset_attribute_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器"
            '<img srcset="/maps-small.png?evidence=EV-CITY-001 1x, /maps-large.png 2x" />生成任务包。'
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            '<source srcset="/preview-small.png?证据=EV-CITY-002 480w, /preview-large.png 960w">采集日志执行复核。'
        ),
        drawing_description='图1为任务包生成流程图。<img srcset="/figures.png?source=lab-note-002 1x">',
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_srcset_attribute_citation" for item in run.blocked_items)


def test_compiler_blocks_html_meta_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包，"
            "<meta name=\"source\" content=\"lab-note-001\">采集阈值由控制器动态确定。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。"
            "<meta property=\"evidence-ref\" content=\"EV-CITY-001\">任务包包含复核节点。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_meta_citation" for item in run.blocked_items)


def test_compiler_blocks_markdown_footnote_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包，"
            "其中采集阈值由控制器动态确定。[^source]\n\n"
            "[^source]: 来源：实验记录.md"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。"
            "任务包包含复核节点。[^1]\n\n"
            "[^1]: source: lab-note-001"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "markdown_footnote_citation" for item in run.blocked_items)


def test_compiler_blocks_markdown_reference_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包，其中采集阈值由控制器动态确定。\n\n"
            "[source]: internal-experiment-record.md"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包包含复核节点。\n\n"
            "[证据]: EV-CITY-001"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "markdown_reference_citation" for item in run.blocked_items)


def test_compiler_blocks_markdown_table_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包，其中采集阈值由控制器动态确定。\n\n"
            "| 字段 | 值 |\n"
            "| source | lab-note-001 |\n"
            "| evidence | EV-CITY-001 |"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包包含复核节点。\n\n"
            "| 字段 | 值 |\n"
            "| 证据 | 实验记录.md |"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "markdown_table_citation" for item in run.blocked_items)


def test_compiler_blocks_yaml_front_matter_evidence_leakage():
    package = _draft_package(
        claims=(
            "---\n"
            "evidence:\n"
            "  - EV-CITY-001\n"
            "---\n"
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。"
        ),
        description=(
            "---\n"
            "证据：\n"
            "  - 实验记录.md\n"
            "---\n"
            "本发明涉及无人机任务规划技术领域。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "yaml_front_matter_citation" for item in run.blocked_items)


def test_compiler_blocks_stripped_yaml_front_matter_evidence_leakage():
    package = _draft_package(
        claims=(
            "evidence:\n"
            "  - EV-CITY-001\n"
            "---\n"
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。"
        ),
        description=(
            "证据：\n"
            "  - 实验记录.md\n"
            "---\n"
            "本发明涉及无人机任务规划技术领域。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "yaml_front_matter_citation" for item in run.blocked_items)


def test_compiler_blocks_toml_front_matter_evidence_leakage():
    package = _draft_package(
        claims=(
            "+++\n"
            'evidence = ["EV-CITY-001"]\n'
            "+++\n"
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。"
        ),
        description=(
            "+++\n"
            '证据 = ["实验记录.md"]\n'
            "+++\n"
            "本发明涉及无人机任务规划技术领域。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "toml_front_matter_citation" for item in run.blocked_items)


def test_compiler_blocks_ini_section_evidence_leakage():
    package = _draft_package(
        claims=(
            "[evidence]\n"
            "id = EV-CITY-001\n"
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。"
        ),
        description=(
            "[证据]\n"
            "编号 = EV-CITY-002\n"
            "本发明涉及无人机任务规划技术领域。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "ini_section_citation" for item in run.blocked_items)


def test_compiler_blocks_html_json_ld_evidence_leakage():
    package = _draft_package(
        claims=(
            '<script type="application/ld+json">\n'
            '{"evidence": "EV-CITY-001", "material": "lab-note-001"}\n'
            "</script>\n"
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。"
        ),
        description=(
            '<script type="application/ld+json">\n'
            '{"证据": "EV-CITY-002", "来源": "实验记录.md"}\n'
            "</script>\n"
            "本发明涉及无人机任务规划技术领域。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_json_ld_citation" for item in run.blocked_items)


def test_compiler_blocks_html_json_script_evidence_leakage():
    package = _draft_package(
        claims=(
            '<script type="application/json" id="draft-evidence">\n'
            '{"evidence": "EV-CITY-001", "material": "lab-note-001"}\n'
            "</script>\n"
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。"
        ),
        description=(
            '<script type="application/json" data-kind="source-map">\n'
            '{"证据": "EV-CITY-002", "来源": "实验记录.md"}\n'
            "</script>\n"
            "本发明涉及无人机任务规划技术领域。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_json_script_citation" for item in run.blocked_items)


def test_compiler_blocks_html_script_text_evidence_leakage():
    package = _draft_package(
        claims=(
            '<script type="text/javascript">\n'
            'window.auditNote = "evidence: EV-CITY-001";\n'
            "</script>\n"
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。"
        ),
        description=(
            '<script type="text/plain">\n'
            "证据：EV-CITY-002\n"
            "</script>\n"
            "本发明涉及无人机任务规划技术领域。"
        ),
        drawing_description=(
            "<script>\n"
            "const source = 'lab-note-002';\n"
            "</script>\n"
            "图1为任务包生成流程图。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_script_text_citation" for item in run.blocked_items)


def test_compiler_blocks_csv_evidence_metadata_leakage():
    package = _draft_package(
        claims=(
            "evidence_id,source_label\n"
            "EV-CITY-001,lab-note-001\n"
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。"
        ),
        description=(
            "证据编号,来源标签\n"
            "EV-CITY-002,实验记录.md\n"
            "本发明涉及无人机任务规划技术领域。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "csv_metadata_citation" for item in run.blocked_items)


def test_compiler_blocks_asciidoc_attribute_evidence_leakage():
    package = _draft_package(
        claims=(
            ":evidence: EV-CITY-001\n"
            ":source-label: lab-note-001\n"
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。"
        ),
        description=(
            ":证据: EV-CITY-002\n"
            ":来源标签: 实验记录.md\n"
            "本发明涉及无人机任务规划技术领域。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "asciidoc_attribute_citation" for item in run.blocked_items)


def test_compiler_blocks_latex_command_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包，"
            r"其中采集阈值由控制器动态确定\cite{source=lab-note-001}。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。"
            r"任务包包含复核节点\footnote{证据: EV-CITY-002}。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "latex_command_citation" for item in run.blocked_items)


def test_compiler_blocks_bibtex_entry_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。\n"
            "@misc{city-source,\n"
            "  note = {source: lab-note-001}\n"
            "}"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。\n"
            "@article{city-evidence,\n"
            "  evidence = {EV-CITY-002}\n"
            "}"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "bibtex_entry_citation" for item in run.blocked_items)


def test_compiler_blocks_rst_directive_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。\n"
            ".. source:: lab-note-001"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。\n"
            ".. evidence:: EV-CITY-002"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "rst_directive_citation" for item in run.blocked_items)


def test_compiler_blocks_markdown_list_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。\n"
            "- evidence: EV-CITY-001\n"
            "- source: lab-note-001"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。\n"
            "* 证据：EV-CITY-002\n"
            "* 来源：实验记录.md"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "markdown_list_citation" for item in run.blocked_items)


def test_compiler_blocks_markdown_blockquote_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。\n"
            "> evidence: EV-CITY-001\n"
            "> source: lab-note-001"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。\n"
            "> 证据：EV-CITY-002\n"
            "> 来源：实验记录.md"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "markdown_blockquote_citation" for item in run.blocked_items)


def test_compiler_blocks_markdown_link_title_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中校准阈值依据"
            '[实验记录](lab-note-001 "evidence: EV-CITY-001")确定。'
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包依据"
            '[采集日志](material-log "证据：EV-CITY-002")生成。'
        ),
        drawing_description='图1为任务包生成流程图。![流程图](figure-1.png "source: lab-note-002")',
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "markdown_link_title_citation" for item in run.blocked_items)


def test_compiler_blocks_markdown_image_alt_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中采集路径由控制器生成，"
            "并输出![evidence: EV-CITY-001](path-plan.png)。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "![证据：EV-CITY-002](collection-log.png)执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。![source: lab-note-002](figure-1.png)",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "markdown_image_alt_citation" for item in run.blocked_items)


def test_compiler_blocks_html_image_attribute_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中采集路径由控制器生成，"
            '<img src="path-plan.png" alt="evidence: EV-CITY-001" />。'
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            '<img src="collection-log.png" title="证据：EV-CITY-002" />执行复核。'
        ),
        drawing_description='图1为任务包生成流程图。<img src="figure-1.png" alt="source: lab-note-002" />',
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_image_attribute_citation" for item in run.blocked_items)


def test_compiler_blocks_html_accessible_attribute_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中采集路径由"
            '<abbr title="evidence: EV-CITY-001">控制器</abbr>生成。'
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            '<span aria-label="证据：EV-CITY-002">采集日志</span>执行复核。'
        ),
        drawing_description='图1为任务包生成流程图。<a href="#fig1" title="source: lab-note-002">图1</a>',
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_accessible_attribute_citation" for item in run.blocked_items)


def test_compiler_blocks_html_visible_text_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中校准阈值由控制器确定"
            "<sup>evidence: EV-CITY-001</sup>。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<span>证据：EV-CITY-002</span>生成。"
        ),
        drawing_description="图1为任务包生成流程图。<small>source: lab-note-002</small>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_visible_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_hidden_text_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器"
            "<template>evidence: EV-CITY-001</template>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<noscript>证据：EV-CITY-002</noscript>采集日志执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<template>source: lab-note-002</template>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_hidden_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_details_summary_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器"
            "<details><summary>source: lab-note-001</summary>生成任务包</details>。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<details open><summary>证据：EV-CITY-002</summary>采集日志</details>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<summary>material: figure-note-002</summary>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_details_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_table_cell_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            "<table><tr><th>source: lab-note-001</th><td>声学阈值</td></tr></table>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<table><tr><td>证据：EV-CITY-002</td><td>采集日志</td></tr></table>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<td>material: figure-note-002</td>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_table_cell_citation" for item in run.blocked_items)


def test_compiler_blocks_html_list_item_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            "<ul><li>source: lab-note-001</li><li>声学阈值</li></ul>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<ol><li>证据：EV-CITY-002</li><li>采集日志</li></ol>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<li>material: figure-note-002</li>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_list_item_citation" for item in run.blocked_items)


def test_compiler_blocks_html_definition_list_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            "<dl><dt>source: lab-note-001</dt><dd>声学阈值</dd></dl>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<dl><dt>证据：EV-CITY-002</dt><dd>采集日志</dd></dl>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<dd>material: figure-note-002</dd>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_definition_list_citation" for item in run.blocked_items)


def test_compiler_blocks_html_code_block_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            "<code>source: lab-note-001</code>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<pre>证据：EV-CITY-002</pre>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<code>material: figure-note-002</code>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_code_block_citation" for item in run.blocked_items)


def test_compiler_blocks_html_ruby_text_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            "<ruby>阈值<rt>source: lab-note-001</rt></ruby>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<ruby>复核<rt>证据：EV-CITY-002</rt></ruby>执行。"
        ),
        drawing_description="图1为任务包生成流程图。<rt>material: figure-note-002</rt>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_ruby_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_phrase_text_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            "<abbr>source: lab-note-001</abbr>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<time>证据：EV-CITY-002</time>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<data>material: figure-note-002</data>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_phrase_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_heading_text_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            "<h2>source: lab-note-001</h2>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<h3>证据：EV-CITY-002</h3>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<h4>material: figure-note-002</h4>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_heading_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_sectioning_text_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            "<section>source: lab-note-001</section>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<header>证据：EV-CITY-002</header>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<footer>material: figure-note-002</footer>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_sectioning_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_form_text_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            "<label>source: lab-note-001</label>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<button>证据：EV-CITY-002</button>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<legend>material: figure-note-002</legend>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_form_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_embedded_fallback_text_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            "<iframe>source: lab-note-001</iframe>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<object>证据：EV-CITY-002</object>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<canvas>material: figure-note-002</canvas>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_embedded_fallback_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_blockquote_text_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            "<blockquote>source: lab-note-001</blockquote>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<blockquote>证据：EV-CITY-002</blockquote>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<blockquote>material: figure-note-002</blockquote>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_blockquote_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_edit_text_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            "<ins>source: lab-note-001</ins>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<del>证据：EV-CITY-002</del>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<s>material: figure-note-002</s>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_edit_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_link_text_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            '<a href="#note-1">source: lab-note-001</a>生成任务包。'
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            '<a href="#note-2">证据：EV-CITY-002</a>执行复核。'
        ),
        drawing_description='图1为任务包生成流程图。<a href="#note-3">material: figure-note-002</a>',
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_link_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_figure_text_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            "<figure>source: lab-note-001</figure>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<figure>证据：EV-CITY-002</figure>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<figure>material: figure-note-002</figure>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_figure_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_semantic_container_text_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            "<address>source: lab-note-001</address>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<dialog>证据：EV-CITY-002</dialog>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<fieldset>material: figure-note-002</fieldset>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_semantic_container_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_select_option_text_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            "<option>source: lab-note-001</option>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<select>证据：EV-CITY-002</select>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<datalist>material: figure-note-002</datalist>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_select_option_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_textarea_text_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器根据"
            "<textarea>source: lab-note-001</textarea>生成任务包。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<textarea>证据：EV-CITY-002</textarea>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<textarea>material: figure-note-002</textarea>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_textarea_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_caption_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中采集路径由控制器生成"
            "<figcaption>evidence: EV-CITY-001</figcaption>。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<caption>证据：EV-CITY-002</caption>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<figcaption>source: lab-note-002</figcaption>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_caption_text_citation" for item in run.blocked_items)


def test_compiler_blocks_svg_title_desc_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器输出"
            "<svg><title>evidence: EV-CITY-001</title></svg>。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<svg><desc>证据：EV-CITY-002</desc></svg>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<svg><title>source: lab-note-002</title></svg>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "svg_title_desc_citation" for item in run.blocked_items)


def test_compiler_blocks_svg_text_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器输出"
            "<svg><text>evidence: EV-CITY-001</text></svg>。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<svg><tspan>证据：EV-CITY-002</tspan></svg>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<svg><text>source: lab-note-002</text></svg>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "svg_text_citation" for item in run.blocked_items)


def test_compiler_blocks_html_style_tag_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器生成任务包"
            "<style>/* evidence: EV-CITY-001 */ .route { color: #111; }</style>。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            "<style>.review::after { content: '证据：EV-CITY-002'; }</style>执行复核。"
        ),
        drawing_description="图1为任务包生成流程图。<style>/* source: lab-note-002 */</style>",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_style_tag_citation" for item in run.blocked_items)


def test_compiler_blocks_html_inline_style_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器"
            '<span style="--evidence: EV-CITY-001;">生成任务包</span>。'
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            '<span style="content: \'证据：EV-CITY-002\';">采集日志</span>执行复核。'
        ),
        drawing_description='图1为任务包生成流程图。<span style="--source: lab-note-002;">图1</span>',
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_inline_style_citation" for item in run.blocked_items)


def test_compiler_blocks_html_form_field_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器生成任务包"
            '<input type="hidden" name="evidence" value="EV-CITY-001" />。'
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            '<input type="hidden" name="证据" value="EV-CITY-002" />执行复核。'
        ),
        drawing_description='图1为任务包生成流程图。<input type="hidden" value="source: lab-note-002" />',
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_form_field_citation" for item in run.blocked_items)


def test_compiler_blocks_html_semantic_metadata_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中控制器"
            '<span itemprop="evidence" content="EV-CITY-001"></span>生成任务包。'
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包根据"
            '<span property="证据" content="EV-CITY-002"></span>采集日志执行复核。'
        ),
        drawing_description='图1为任务包生成流程图。<span itemprop="source" content="lab-note-002"></span>',
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_semantic_metadata_citation" for item in run.blocked_items)


def test_compiler_blocks_html_entity_evidence_leakage():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，其中校准阈值由控制器确定"
            "&lt;evidence ref=&quot;EV-CITY-001&quot;&gt;实验记录&lt;/evidence&gt;。"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。任务包依据"
            "&lt;source&gt;lab-note-001&lt;/source&gt;生成。"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "html_entity_citation" for item in run.blocked_items)


def test_compiler_blocks_source_footer_metadata_lines():
    package = _draft_package(
        claims=(
            "1. 一种城市体检指标驱动无人机采集方法，包括生成任务包。\n"
            "Sources: internal-experiment-record.md"
        ),
        description=(
            "本发明涉及无人机任务规划技术领域。\n"
            "参考资料：实验记录.md\n"
            "依据材料：采集日志-001"
        ),
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    removed_patterns = {item["pattern"] for item in run.contamination_removed}
    assert {"sources", "参考资料", "依据材料"} <= removed_patterns
    assert any(item["category"] == "official_hygiene_contamination" for item in run.blocked_items)


def test_compiler_blocks_case_insensitive_internal_labels_and_memos():
    package = _draft_package(
        description=(
            "本发明涉及无人机任务规划技术领域。\n"
            "attorney_memo: 代理人复核从属权利要求。\n"
            "System_Trace: deliberation payload\n"
            "official_safe_patches: patch-1"
        ),
        drawing_description="图1为方法流程图。\nPrompt: 黑白线稿。",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert {item["pattern"] for item in run.contamination_removed} >= {
        "prompt",
        "attorney_memo",
        "system_trace",
        "official_safe_patches",
    }


def test_compiler_blocks_ai_preface_title_contamination():
    package = _draft_package(title="好的，下面撰写一种方法")

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(
        item["category"] in {"residual_internal_text", "empty_required_section"}
        and item["section"] == "title"
        for item in run.blocked_items
    )


def test_compiler_blocks_inline_prompt_contamination_in_drawing_description():
    package = _draft_package(drawing_description="图1为方法流程图。prompt: 黑白线稿")

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(
        item["category"] == "residual_internal_text"
        and item["section"] == "drawing_description"
        and item["pattern"] == "prompt"
        for item in run.blocked_items
    )


def test_compiler_blocks_inline_prompt_contamination_in_title():
    package = _draft_package(title="一种方法 prompt: 黑白线稿")

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(
        item["category"] == "residual_internal_text"
        and item["section"] == "title"
        and item["pattern"] == "prompt"
        for item in run.blocked_items
    )


def test_compiler_blocks_json_wrapper_only_required_section():
    package = _draft_package(drawing_description='{\n  "prompt": "黑白线稿"\n}')

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(
        item["category"] == "empty_required_section"
        and item["section"] == "drawing_description"
        for item in run.blocked_items
    )


def test_compiler_blocks_empty_official_section_json_wrapper():
    package = _draft_package(drawing_description='{\n  "drawing_description": ""\n}')

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(
        item["category"] in {"empty_required_section", "json_wrapper"}
        and item["section"] == "drawing_description"
        for item in run.blocked_items
    )


def test_sqlite_store_persists_official_compile_run(tmp_path):
    store = SQLiteStore(tmp_path / "store.sqlite3")
    package = _draft_package(claims="1. 一种方法。")
    run = OfficialDraftCompiler().compile(project_id="p1", package=package)
    assert run.status == "completed"
    assert run.official_package is not None
    blocked_run = OfficialDraftCompiler().compile(
        project_id="p1",
        package=_draft_package(description="support_gap: 说明书待补充。"),
    )
    assert blocked_run.status == "blocked"
    failed_run = run.model_copy(update={"id": "failed-official-compile", "status": "failed"})

    stored = store.create_official_compile_run(run)
    store.create_official_compile_run(blocked_run)
    store.create_official_compile_run(failed_run)

    assert stored.created_at
    assert stored.updated_at
    fetched = store.get_official_compile_run("p1", run.id)
    assert fetched is not None
    assert fetched.id == run.id
    assert fetched.official_package is not None
    assert fetched.official_package.title == package.title
    assert fetched.official_package_hash == run.official_package_hash
    assert fetched.contamination_removed == run.contamination_removed
    assert fetched.sidecar_notes == run.sidecar_notes
    assert fetched.logs[0].phase == "official_compile"
    listed = store.list_official_compile_runs("p1")
    assert {item.id for item in listed} == {run.id, blocked_run.id, failed_run.id}
    latest = store.get_latest_completed_official_compile_run("p1")
    assert latest is not None
    assert latest.id == run.id
    latest_for_hash = store.get_latest_completed_official_compile_run_for_hash("p1", run.source_draft_hash)
    assert latest_for_hash is not None
    assert latest_for_hash.id == run.id


def test_official_compile_api_creates_lists_gets_and_exports_report(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package(claims="1. 一种方法。"))

    create_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})

    assert create_response.status_code == 200
    run = create_response.json()
    assert run["status"] == "completed"
    assert run["official_package"]["title"] == "一种城市体检指标驱动无人机主动采集方法"
    assert "1. 一种方法。" in run["official_package"]["claims"]

    list_response = client.get(f"/api/projects/{project_id}/official-compile-runs")
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["current_source_draft_hash"] == run["source_draft_hash"]
    assert [item["id"] for item in listed["runs"]] == [run["id"]]

    detail_response = client.get(f"/api/projects/{project_id}/official-compile-runs/{run['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["official_package_hash"] == run["official_package_hash"]

    report_response = client.get(f"/api/projects/{project_id}/official-compile-runs/{run['id']}/report.md")
    assert report_response.status_code == 200
    assert report_response.headers["content-type"].startswith("text/markdown")
    assert "# OFFICIAL_COMPILE_RUN" in report_response.text
    assert run["id"] in report_response.text
    assert "## Official Package" in report_response.text


def test_official_compile_cleanup_applies_blocked_hygiene_to_source_draft(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    dirty_package = _draft_package(
        claims=(
            "### 权利要求书\n"
            "1. 一种方法，包括生成无人机任务包。\n\n"
            "### support_gaps（提交前需补强的实验或工程材料）"
        ),
        description=(
            "好的，以下是根据您提供的技术交底材料、权利要求书及多智能体会审策略撰写的说明书，并列出 support_gaps。\n"
            "### 说明书\n"
            "#### 技术领域\n"
            "本发明涉及无人机任务规划技术领域。\n"
            "#### 具体实施方式\n"
            "系统依据城市体检指标生成采集任务。"
        ),
        drawing_description="#### 附图说明\n图1为方法流程图。",
    )
    project_id = _create_project_with_package(client, dirty_package)
    blocked_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert blocked_response.status_code == 200
    blocked = blocked_response.json()
    assert blocked["status"] == "blocked"
    assert blocked["contamination_removed"]

    cleanup_response = client.post(
        f"/api/projects/{project_id}/official-compile-runs/{blocked['id']}/apply-cleanup",
        json={},
    )

    assert cleanup_response.status_code == 200
    cleanup = cleanup_response.json()
    assert cleanup["compile_run_id"] == blocked["id"]
    assert cleanup["previous_draft_hash"] == blocked["source_draft_hash"]
    assert cleanup["current_draft_hash"] != blocked["source_draft_hash"]
    assert cleanup["applied_count"] == len(blocked["contamination_removed"])
    cleaned_package = cleanup["package"]
    for field in ("claims", "description", "drawing_description"):
        assert "###" not in cleaned_package[field]
        assert "####" not in cleaned_package[field]
        assert "support_gaps" not in cleaned_package[field]
        assert "好的，以下" not in cleaned_package[field]

    listed = client.get(f"/api/projects/{project_id}/official-compile-runs").json()
    assert listed["current_source_draft_hash"] == cleanup["current_draft_hash"]

    recompile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert recompile_response.status_code == 200
    recompiled = recompile_response.json()
    assert recompiled["status"] == "completed"
    assert recompiled["source_draft_hash"] == cleanup["current_draft_hash"]
    assert recompiled["official_package"]["claims"].startswith("1. 一种方法")


def test_official_compile_cleanup_rejects_stale_blocked_run(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _draft_package(claims="### 权利要求书\n1. 一种方法，包括生成无人机任务包。"),
    )
    blocked = client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()
    assert blocked["status"] == "blocked"
    client.app.state.store.update_project_package(project_id, _draft_package(abstract="修改后的摘要。"))

    response = client.post(
        f"/api/projects/{project_id}/official-compile-runs/{blocked['id']}/apply-cleanup",
        json={},
    )

    assert response.status_code == 409
    assert "stale" in response.json()["detail"]


def test_blocked_compile_cleanup_rechecks_quality_and_unlocks_export_loop(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    dirty_package = _draft_package(
        claims=(
            "### 权利要求书\n"
            "1. 一种城市体检指标驱动的无人机主动采集方法，包括生成任务有向无环图。"
        ),
        description=(
            "### 说明书\n"
            "本发明涉及城市体检智能体任务编排技术领域。\n"
            "### support_gaps（提交前需补强的实验或工程材料）\n"
            "#### 具体实施方式\n"
            "系统依据任务有向无环图调度采集、复核和交付物生成。"
        ),
    )
    project_id = _create_project_with_package(client, dirty_package)

    first_quality = _run_quality_cycle(client, project_id)
    blocked = client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()
    assert blocked["status"] == "blocked"
    assert blocked["source_draft_hash"] == first_quality["filing"]["draft_package_hash"]
    assert blocked["source_draft_hash"] == first_quality["completion"]["draft_package_hash"]

    cleanup = client.post(
        f"/api/projects/{project_id}/official-compile-runs/{blocked['id']}/apply-cleanup",
        json={},
    ).json()
    current_hash = cleanup["current_draft_hash"]
    assert current_hash != blocked["source_draft_hash"]
    stale_quality = client.get(f"/api/projects/{project_id}/filing-readiness").json()
    assert stale_quality["current_source_draft_hash"] == current_hash
    assert stale_quality["reports"][0]["draft_package_hash"] != current_hash

    stale_export = client.get(f"/api/projects/{project_id}/official-export.md")
    assert stale_export.status_code == 409
    assert "stale quality checks" in stale_export.json()["detail"]
    assert "filing_readiness" in stale_export.json()["detail"]
    assert "claim_defense_worksheet" in stale_export.json()["detail"]
    assert "draft_completion" in stale_export.json()["detail"]

    refreshed_quality = _run_quality_cycle(client, project_id)
    assert refreshed_quality["filing"]["draft_package_hash"] == current_hash
    assert refreshed_quality["completion"]["draft_package_hash"] == current_hash

    compiled = client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()
    assert compiled["status"] == "completed"
    assert compiled["source_draft_hash"] == current_hash

    pre_review_export = client.get(f"/api/projects/{project_id}/official-export.md")
    assert pre_review_export.status_code == 409
    assert "Post-draft multi-agent review is required" in pre_review_export.json()["detail"]

    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    assert review["status"] == "completed"
    assert review["export_allowed"] is True
    assert review["official_compile_run_id"] == compiled["id"]

    export = client.get(f"/api/projects/{project_id}/official-export.md")
    assert export.status_code == 200
    assert "权利要求书" in export.text
    assert "support_gaps" not in export.text
    assert "###" not in export.text


def test_post_draft_review_requires_completed_official_compile(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())

    response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    assert response.status_code == 409
    assert "Official draft compile is required" in response.json()["detail"]


def test_post_draft_review_requires_completed_official_compile_for_current_draft(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())
    compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert compile_response.status_code == 200
    client.app.state.store.update_project_package(project_id, _draft_package(abstract="修改后的摘要。"))

    response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    assert response.status_code == 409
    assert "Official draft compile is required" in response.json()["detail"]


def test_post_draft_review_records_official_package_hash_and_unlocks_export(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package(claims="1. 一种方法。"))
    _run_quality_cycle(client, project_id)
    compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert compile_response.status_code == 200
    compile_run = compile_response.json()
    assert compile_run["status"] == "completed"

    review_response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    assert review_response.status_code == 200
    review = review_response.json()
    assert review["status"] == "completed"
    assert review["export_allowed"] is True
    assert review["draft_package_hash"] == compile_run["source_draft_hash"]
    assert review["official_compile_run_id"] == compile_run["id"]
    assert review["official_package_hash"] == compile_run["official_package_hash"]

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")
    assert export_response.status_code == 200
    assert "权利要求书" in export_response.text


def test_official_export_uses_compiled_package_not_raw_draft(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _draft_package(
            claims="1. 一种方法，包括生成任务包。",
            image_prompt="内部绘图提示词。",
            generation_logs=["generation_logs: internal"],
        ),
    )
    _run_quality_cycle(client, project_id)
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    response = client.get(f"/api/projects/{project_id}/official-export.md")

    assert response.status_code == 200
    assert "1. 一种方法，包括生成任务包。" in response.text
    assert "内部绘图提示词" not in response.text
    assert "generation_logs" not in response.text


def test_review_for_previous_compile_run_cannot_unlock_latest_compile(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())
    _run_quality_cycle(client, project_id)
    first_compile = client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()
    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    assert review["export_allowed"] is True
    assert review["official_compile_run_id"] == first_compile["id"]

    second_compile = client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()
    assert second_compile["status"] == "completed"
    assert second_compile["id"] != first_compile["id"]
    assert second_compile["source_draft_hash"] == first_compile["source_draft_hash"]
    assert second_compile["official_package_hash"] == first_compile["official_package_hash"]

    response = client.get(f"/api/projects/{project_id}/official-export.md")

    assert response.status_code == 409
    assert "Post-draft multi-agent review is required" in response.json()["detail"]


def test_kimi_language_polish_creates_new_official_compile_version_and_requires_review(tmp_path):
    provider_runner = _KimiPolishProviderRunner(
        {
            "title": "一种城市体检指标驱动的无人机主动采集方法",
            "abstract": "本发明公开一种依据城市体检指标置信度主动生成采集任务的无人机采集方法。",
            "claims": "1. 一种城市体检指标驱动的无人机主动采集方法，包括获取指标置信度并生成采集任务。",
            "description": "本发明涉及无人机主动采集技术领域。系统依据指标置信度生成采集任务，并输出任务包。",
            "drawing_description": "图1为本发明无人机主动采集方法的流程示意图。",
            "attorney_memo": ["已进行中文专利语言润色，未改变技术边界。"],
        }
    )
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=_review_llm(export_allowed=True),
            provider_runner=provider_runner,
            load_env_file=False,
        )
    )
    project_id = _create_project_with_package(client, _draft_package())
    _run_quality_cycle(client, project_id)
    original_compile = client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()
    passed_review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    assert passed_review["export_allowed"] is True

    response = client.post(
        f"/api/projects/{project_id}/official-compile-runs/{original_compile['id']}/kimi-language-polish",
        json={},
    )

    assert response.status_code == 200
    polished = response.json()
    assert provider_runner.provider_ids == ["kimicode"]
    assert provider_runner.labels == ["kimi official language polish"]
    assert polished["id"] != original_compile["id"]
    assert polished["status"] == "completed"
    assert polished["source_draft_hash"] == original_compile["source_draft_hash"]
    assert polished["official_package_hash"] != original_compile["official_package_hash"]
    assert polished["official_package"]["title"] == "一种城市体检指标驱动的无人机主动采集方法"
    assert polished["official_package"]["claims"].startswith("1. 一种城市体检指标驱动")
    assert polished["official_package"]["compile_warnings"] == ["kimi_language_polished"]
    assert any(note["category"] == "kimi_language_polish" for note in polished["sidecar_notes"])
    assert any(log["provider_id"] == "kimicode" for log in polished["logs"])

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")
    assert export_response.status_code == 409
    assert "Post-draft multi-agent review is required" in export_response.json()["detail"]

    new_review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    assert new_review["export_allowed"] is True
    assert new_review["official_compile_run_id"] == polished["id"]
    assert new_review["official_package_hash"] == polished["official_package_hash"]
    unlocked_export = client.get(f"/api/projects/{project_id}/official-export.md")
    assert unlocked_export.status_code == 200
    assert "城市体检指标驱动的无人机主动采集方法" in unlocked_export.text


def test_official_export_requires_recompile_when_draft_changes(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())
    _run_quality_cycle(client, project_id)
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})
    client.app.state.store.update_project_package(project_id, _draft_package(abstract="修改后的摘要。"))
    _run_quality_cycle(client, project_id)

    response = client.get(f"/api/projects/{project_id}/official-export.md")

    assert response.status_code == 409
    assert "Official draft compile is required for the current draft" in response.json()["detail"]


def _create_project_with_package(client: TestClient, package: DraftPackage) -> str:
    project_id = client.post(
        "/api/projects",
        json={"name": "正式稿编译测试", "draft_text": "一种城市体检指标驱动无人机采集方法。"},
    ).json()["id"]
    client.app.state.store.update_project_package(project_id, package)
    return project_id


def _run_quality_cycle(client: TestClient, project_id: str) -> dict:
    filing_response = client.post(f"/api/projects/{project_id}/filing-readiness")
    assert filing_response.status_code == 200
    worksheet_response = client.post(f"/api/projects/{project_id}/claim-defense-worksheets")
    assert worksheet_response.status_code == 200
    completion_response = client.post(f"/api/projects/{project_id}/completion-runs")
    assert completion_response.status_code == 200
    return {
        "filing": filing_response.json(),
        "worksheet": worksheet_response.json(),
        "completion": completion_response.json(),
    }


def _draft_package(**overrides) -> DraftPackage:
    data = {
        "title": "一种城市体检指标驱动无人机主动采集方法",
        "abstract": "本发明公开了一种无人机主动采集方法。",
        "claims": "1. 一种方法，包括生成无人机任务包。",
        "description": "本发明涉及无人机任务规划技术领域。",
        "drawing_description": "图1为方法流程图。",
        "mermaid": "flowchart TD",
        "image_prompt": "黑白线稿",
        "review_findings": [],
        "citations": [],
        "generation_logs": ["claims generated"],
    }
    data.update(overrides)
    return DraftPackage(**data)


def _review_llm(*, export_allowed: bool) -> FakeLLMClient:
    role_status = "passed" if export_allowed else "blocked"
    chair_status = "passed" if export_allowed else "blocked"
    blocking_issues = [] if export_allowed else ["正式稿存在阻断问题。"]
    return FakeLLMClient(
        {
            "post_draft_claims_reviewer": _role_json("claims_reviewer", role_status, blocking_issues),
            "post_draft_spec_cleaner": _role_json("spec_cleaner", role_status, blocking_issues),
            "post_draft_technical_hardness": _role_json("technical_hardness", role_status, blocking_issues),
            "post_draft_chair_synthesis": f"""
{{
  "status": "{chair_status}",
  "export_allowed": {str(export_allowed).lower()},
  "blocking_issues": {blocking_issues!r},
  "contamination_hits": [],
  "claim_1_rewrite": "",
  "system_claim_rewrite": "",
  "abstract_rewrite": "",
  "description_rewrite_tasks": [],
  "official_safe_patches": [],
  "attorney_memo": ["内部备忘。"],
  "next_actions": []
}}
""".replace("'", '"'),
        }
    )


class _KimiPolishProviderRunner:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.provider_ids: list[str] = []
        self.labels: list[str] = []

    async def run_json_task(self, *, provider_id: str, label: str, **kwargs) -> ProviderTaskResult:
        self.provider_ids.append(provider_id)
        self.labels.append(label)
        return ProviderTaskResult(
            provider_id=provider_id,
            payload=self.payload,
            stdout="{}",
            stderr="",
            attempts=1,
        )


def _role_json(role: str, status: str, blocking_issues: list[str]) -> str:
    return f"""
{{
  "role": "{role}",
  "status": "{status}",
  "blocking_issues": {blocking_issues!r},
  "contamination_hits": [],
  "rewrite_suggestions": [],
  "official_safe_patches": [],
  "attorney_memo": ["内部备忘。"]
}}
""".replace("'", '"')
