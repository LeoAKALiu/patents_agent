from __future__ import annotations

import json

import adversarial_flow_harness as harness
from adversarial_flow_harness import replay_adversarial_trace, run_adversarial_trace


TRACE_COUNT = 20
STEPS_PER_TRACE = 12


def test_adversarial_flow_explorer_preserves_export_invariants_and_writes_trace_artifacts(tmp_path) -> None:
    trace_dir = tmp_path / "trace-artifacts"
    ready_traces = 0

    for seed in range(TRACE_COUNT):
        force_ready = seed % 4 == 0
        trace = run_adversarial_trace(
            seed=seed,
            data_dir=tmp_path / f"trace-{seed}",
            action_count=STEPS_PER_TRACE,
            force_ready=force_ready,
        )
        trace_path = trace.write_json(trace_dir / f"trace-{seed}.json")
        payload = json.loads(trace_path.read_text(encoding="utf-8"))

        assert payload["seed"] == seed
        assert len(payload["actions"]) >= STEPS_PER_TRACE
        assert payload["final_state"]["gates"] == trace.final_state.gates
        if force_ready:
            ready_traces += 1
            assert trace.final_state.export_allowed is True
            assert trace.final_state.gates == {
                "quality": "current",
                "official_compile": "current",
                "post_draft_review": "current",
            }

    assert len(list(trace_dir.glob("trace-*.json"))) == TRACE_COUNT
    assert ready_traces >= 5


def test_adversarial_flow_trace_artifact_can_be_replayed(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=7,
        data_dir=tmp_path / "recorded",
        action_count=8,
        force_ready=True,
    )
    trace_path = trace.write_json(tmp_path / "trace-7.json")

    replayed = replay_adversarial_trace(trace_path, data_dir=tmp_path / "replayed")

    assert trace_path.exists()
    assert json.loads(trace_path.read_text(encoding="utf-8"))["seed"] == 7
    assert len(trace.actions) >= 8
    assert [entry.name for entry in replayed.actions] == [entry.name for entry in trace.actions]
    assert replayed.final_state.gates == trace.final_state.gates
    assert replayed.final_state.export_allowed == trace.final_state.export_allowed


def test_adversarial_flow_harness_can_run_disclosure_and_formula_actions(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=11,
        data_dir=tmp_path / "disclosure-formula",
        action_count=0,
        action_names=("disclosure", "intake", "formula", "quality", "compile", "pass_review"),
        force_ready=False,
    )

    assert [entry.name for entry in trace.actions][:3] == ["disclosure", "intake", "formula"]
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_runtime_control_actions(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=23,
        data_dir=tmp_path / "runtime-actions",
        action_count=0,
        action_names=(
            "deliberation_queued_cancel",
            "deliberation_cancel_exception",
            "intake",
            "quality",
            "compile",
            "formula_cancel_exception",
            "post_review_cancel_retry",
        ),
        force_ready=False,
    )
    payloads = {entry.name: entry.payload for entry in trace.actions}

    assert payloads["deliberation_queued_cancel"]["status"] == "interrupted"
    assert payloads["deliberation_queued_cancel"]["cancel_requested"] is True
    assert payloads["deliberation_cancel_exception"]["status"] == "interrupted"
    assert payloads["deliberation_cancel_exception"]["failure_reason"] == "cancelled"
    assert payloads["deliberation_cancel_exception"]["provider_error_leaked"] is False
    assert payloads["formula_cancel_exception"]["status"] == "interrupted"
    assert payloads["formula_cancel_exception"]["failure_reason"] == "cancelled"
    assert payloads["formula_cancel_exception"]["provider_error_leaked"] is False
    assert payloads["post_review_cancel_retry"]["cancel_status"] == "interrupted"
    assert payloads["post_review_cancel_retry"]["retry_status"] == "completed"
    assert payloads["post_review_cancel_retry"]["retry_of"] == payloads["post_review_cancel_retry"]["cancelled_run_id"]
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_isolated_generated_evidence_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=31,
        data_dir=tmp_path / "generated-evidence-honesty",
        action_count=0,
        action_names=("generated_evidence_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert {"source_id", "source_label", "material_id"} <= set(payload["blocked_patterns"])
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_chinese_generated_evidence_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=37,
        data_dir=tmp_path / "generated-chinese-evidence-honesty",
        action_count=0,
        action_names=("generated_chinese_evidence_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert {"证据编号", "材料编号", "来源标签", "引用来源"} <= set(payload["blocked_patterns"])
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_url_evidence_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=41,
        data_dir=tmp_path / "generated-url-evidence-honesty",
        action_count=0,
        action_names=("generated_url_evidence_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "url" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_bracketed_citation_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=43,
        data_dir=tmp_path / "generated-bracketed-citation-honesty",
        action_count=0,
        action_names=("generated_bracketed_citation_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "bracketed_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_json_wrapper_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=47,
        data_dir=tmp_path / "generated-json-wrapper-honesty",
        action_count=0,
        action_names=("generated_json_wrapper_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert {"claims", "description"} <= set(payload["blocked_patterns"])
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_source_footer_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=53,
        data_dir=tmp_path / "generated-source-footer-honesty",
        action_count=0,
        action_names=("generated_source_footer_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert {"sources", "参考资料", "依据材料"} <= set(payload["blocked_patterns"])
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_parenthetical_citation_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=59,
        data_dir=tmp_path / "generated-parenthetical-citation-honesty",
        action_count=0,
        action_names=("generated_parenthetical_citation_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "parenthetical_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_xml_tag_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=61,
        data_dir=tmp_path / "generated-xml-tag-honesty",
        action_count=0,
        action_names=("generated_xml_tag_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "xml_evidence_tag" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_comment_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=67,
        data_dir=tmp_path / "generated-html-comment-honesty",
        action_count=0,
        action_names=("generated_html_comment_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_comment_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_attribute_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=69,
        data_dir=tmp_path / "generated-html-attribute-honesty",
        action_count=0,
        action_names=("generated_html_attribute_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_attribute_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_class_id_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=137,
        data_dir=tmp_path / "generated-html-class-id-honesty",
        action_count=0,
        action_names=("generated_html_class_id_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_class_id_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_data_value_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=138,
        data_dir=tmp_path / "generated-html-data-value-honesty",
        action_count=0,
        action_names=("generated_html_data_value_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_data_value_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_event_handler_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=139,
        data_dir=tmp_path / "generated-html-event-handler-honesty",
        action_count=0,
        action_names=("generated_html_event_handler_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_event_handler_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_url_attribute_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=142,
        data_dir=tmp_path / "generated-html-url-attribute-honesty",
        action_count=0,
        action_names=("generated_html_url_attribute_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_url_attribute_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_srcset_attribute_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=143,
        data_dir=tmp_path / "generated-html-srcset-attribute-honesty",
        action_count=0,
        action_names=("generated_html_srcset_attribute_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_srcset_attribute_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_meta_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=70,
        data_dir=tmp_path / "generated-html-meta-honesty",
        action_count=0,
        action_names=("generated_html_meta_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_meta_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_markdown_footnote_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=71,
        data_dir=tmp_path / "generated-markdown-footnote-honesty",
        action_count=0,
        action_names=("generated_markdown_footnote_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "markdown_footnote_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_markdown_reference_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=73,
        data_dir=tmp_path / "generated-markdown-reference-honesty",
        action_count=0,
        action_names=("generated_markdown_reference_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "markdown_reference_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_markdown_table_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=77,
        data_dir=tmp_path / "generated-markdown-table-honesty",
        action_count=0,
        action_names=("generated_markdown_table_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "markdown_table_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_yaml_front_matter_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=79,
        data_dir=tmp_path / "generated-yaml-front-matter-honesty",
        action_count=0,
        action_names=("generated_yaml_front_matter_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "yaml_front_matter_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_csv_metadata_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=83,
        data_dir=tmp_path / "generated-csv-metadata-honesty",
        action_count=0,
        action_names=("generated_csv_metadata_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "csv_metadata_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_toml_front_matter_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=89,
        data_dir=tmp_path / "generated-toml-front-matter-honesty",
        action_count=0,
        action_names=("generated_toml_front_matter_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "toml_front_matter_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_ini_section_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=97,
        data_dir=tmp_path / "generated-ini-section-honesty",
        action_count=0,
        action_names=("generated_ini_section_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "ini_section_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_json_ld_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=101,
        data_dir=tmp_path / "generated-html-json-ld-honesty",
        action_count=0,
        action_names=("generated_html_json_ld_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_json_ld_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_json_script_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=136,
        data_dir=tmp_path / "generated-html-json-script-honesty",
        action_count=0,
        action_names=("generated_html_json_script_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_json_script_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_script_text_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=141,
        data_dir=tmp_path / "generated-html-script-text-honesty",
        action_count=0,
        action_names=("generated_html_script_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_script_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_fenced_json_metadata_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=103,
        data_dir=tmp_path / "generated-fenced-json-metadata-honesty",
        action_count=0,
        action_names=("generated_fenced_json_metadata_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "fenced_json_metadata_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_asciidoc_attribute_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=107,
        data_dir=tmp_path / "generated-asciidoc-attribute-honesty",
        action_count=0,
        action_names=("generated_asciidoc_attribute_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "asciidoc_attribute_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_latex_command_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=109,
        data_dir=tmp_path / "generated-latex-command-honesty",
        action_count=0,
        action_names=("generated_latex_command_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "latex_command_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_bibtex_entry_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=113,
        data_dir=tmp_path / "generated-bibtex-entry-honesty",
        action_count=0,
        action_names=("generated_bibtex_entry_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "bibtex_entry_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_rst_directive_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=117,
        data_dir=tmp_path / "generated-rst-directive-honesty",
        action_count=0,
        action_names=("generated_rst_directive_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "rst_directive_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_markdown_list_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=119,
        data_dir=tmp_path / "generated-markdown-list-honesty",
        action_count=0,
        action_names=("generated_markdown_list_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "markdown_list_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_markdown_blockquote_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=121,
        data_dir=tmp_path / "generated-markdown-blockquote-honesty",
        action_count=0,
        action_names=("generated_markdown_blockquote_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "markdown_blockquote_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_markdown_link_title_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=123,
        data_dir=tmp_path / "generated-markdown-link-title-honesty",
        action_count=0,
        action_names=("generated_markdown_link_title_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "markdown_link_title_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_markdown_image_alt_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=124,
        data_dir=tmp_path / "generated-markdown-image-alt-honesty",
        action_count=0,
        action_names=("generated_markdown_image_alt_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "markdown_image_alt_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_image_attribute_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=126,
        data_dir=tmp_path / "generated-html-image-attribute-honesty",
        action_count=0,
        action_names=("generated_html_image_attribute_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_image_attribute_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_accessible_attribute_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=129,
        data_dir=tmp_path / "generated-html-accessible-attribute-honesty",
        action_count=0,
        action_names=("generated_html_accessible_attribute_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_accessible_attribute_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_visible_text_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=125,
        data_dir=tmp_path / "generated-html-visible-text-honesty",
        action_count=0,
        action_names=("generated_html_visible_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_visible_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_hidden_text_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=140,
        data_dir=tmp_path / "generated-html-hidden-text-honesty",
        action_count=0,
        action_names=("generated_html_hidden_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_hidden_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_details_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=142,
        data_dir=tmp_path / "generated-html-details-honesty",
        action_count=0,
        action_names=("generated_html_details_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_details_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_table_cell_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=143,
        data_dir=tmp_path / "generated-html-table-cell-honesty",
        action_count=0,
        action_names=("generated_html_table_cell_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_table_cell_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_list_item_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=144,
        data_dir=tmp_path / "generated-html-list-item-honesty",
        action_count=0,
        action_names=("generated_html_list_item_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_list_item_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_definition_list_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=145,
        data_dir=tmp_path / "generated-html-definition-list-honesty",
        action_count=0,
        action_names=("generated_html_definition_list_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_definition_list_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_code_block_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=146,
        data_dir=tmp_path / "generated-html-code-block-honesty",
        action_count=0,
        action_names=("generated_html_code_block_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_code_block_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_ruby_text_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=147,
        data_dir=tmp_path / "generated-html-ruby-text-honesty",
        action_count=0,
        action_names=("generated_html_ruby_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_ruby_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_phrase_text_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=148,
        data_dir=tmp_path / "generated-html-phrase-text-honesty",
        action_count=0,
        action_names=("generated_html_phrase_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_phrase_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_heading_text_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=149,
        data_dir=tmp_path / "generated-html-heading-text-honesty",
        action_count=0,
        action_names=("generated_html_heading_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_heading_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_sectioning_text_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=150,
        data_dir=tmp_path / "generated-html-sectioning-text-honesty",
        action_count=0,
        action_names=("generated_html_sectioning_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_sectioning_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_form_text_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=151,
        data_dir=tmp_path / "generated-html-form-text-honesty",
        action_count=0,
        action_names=("generated_html_form_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_form_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_embedded_fallback_text_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=152,
        data_dir=tmp_path / "generated-html-embedded-fallback-text-honesty",
        action_count=0,
        action_names=("generated_html_embedded_fallback_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_embedded_fallback_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_blockquote_text_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=153,
        data_dir=tmp_path / "generated-html-blockquote-text-honesty",
        action_count=0,
        action_names=("generated_html_blockquote_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_blockquote_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_edit_text_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=154,
        data_dir=tmp_path / "generated-html-edit-text-honesty",
        action_count=0,
        action_names=("generated_html_edit_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_edit_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_link_text_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=155,
        data_dir=tmp_path / "generated-html-link-text-honesty",
        action_count=0,
        action_names=("generated_html_link_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_link_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_figure_text_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=156,
        data_dir=tmp_path / "generated-html-figure-text-honesty",
        action_count=0,
        action_names=("generated_html_figure_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_figure_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_semantic_container_text_honesty_action(
    tmp_path,
) -> None:
    trace = run_adversarial_trace(
        seed=157,
        data_dir=tmp_path / "generated-html-semantic-container-text-honesty",
        action_count=0,
        action_names=("generated_html_semantic_container_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_semantic_container_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_select_option_text_honesty_action(
    tmp_path,
) -> None:
    trace = run_adversarial_trace(
        seed=158,
        data_dir=tmp_path / "generated-html-select-option-text-honesty",
        action_count=0,
        action_names=("generated_html_select_option_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_select_option_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_textarea_text_honesty_action(
    tmp_path,
) -> None:
    trace = run_adversarial_trace(
        seed=159,
        data_dir=tmp_path / "generated-html-textarea-text-honesty",
        action_count=0,
        action_names=("generated_html_textarea_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_textarea_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_caption_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=128,
        data_dir=tmp_path / "generated-html-caption-honesty",
        action_count=0,
        action_names=("generated_html_caption_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_caption_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_svg_title_desc_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=130,
        data_dir=tmp_path / "generated-svg-title-desc-honesty",
        action_count=0,
        action_names=("generated_svg_title_desc_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "svg_title_desc_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_svg_text_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=131,
        data_dir=tmp_path / "generated-svg-text-honesty",
        action_count=0,
        action_names=("generated_svg_text_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "svg_text_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_style_tag_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=132,
        data_dir=tmp_path / "generated-html-style-tag-honesty",
        action_count=0,
        action_names=("generated_html_style_tag_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_style_tag_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_inline_style_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=133,
        data_dir=tmp_path / "generated-html-inline-style-honesty",
        action_count=0,
        action_names=("generated_html_inline_style_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_inline_style_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_form_field_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=134,
        data_dir=tmp_path / "generated-html-form-field-honesty",
        action_count=0,
        action_names=("generated_html_form_field_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_form_field_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_semantic_metadata_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=135,
        data_dir=tmp_path / "generated-html-semantic-metadata-honesty",
        action_count=0,
        action_names=("generated_html_semantic_metadata_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_semantic_metadata_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_harness_can_run_generated_html_entity_honesty_action(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=127,
        data_dir=tmp_path / "generated-html-entity-honesty",
        action_count=0,
        action_names=("generated_html_entity_honesty",),
        force_ready=True,
    )

    payload = trace.actions[0].payload

    assert payload["generate_status"] == "completed"
    assert payload["compile_status"] == "blocked"
    assert "html_entity_citation" in payload["blocked_patterns"]
    assert payload["export_status_code"] == 409
    assert trace.final_state.gates == {
        "quality": "current",
        "official_compile": "current",
        "post_draft_review": "current",
    }
    assert trace.final_state.export_allowed is True


def test_adversarial_flow_failure_triage_writes_minimized_replay_summary(tmp_path) -> None:
    trace = run_adversarial_trace(
        seed=17,
        data_dir=tmp_path / "failing-recorded",
        action_count=0,
        action_names=("intake", "quality", "compile", "pass_review", "readiness", "edit", "export"),
        force_ready=False,
    )
    trace_path = trace.write_json(tmp_path / "trace-17.json")
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    replay_attempt = 0

    def reproduces(actions: list[harness.TraceAction]) -> bool:
        nonlocal replay_attempt
        replay_attempt += 1
        replayed = harness.replay_adversarial_actions(
            seed=trace.seed,
            actions=actions,
            data_dir=tmp_path / f"shrink-{replay_attempt}",
        )
        return (
            replayed.final_state.export_allowed is False
            and replayed.final_state.gates["official_compile"] == "stale"
            and replayed.final_state.gates["post_draft_review"] == "stale"
        )

    summary_path = harness.write_failure_triage(
        trace_path,
        output_dir=tmp_path / "triage",
        failure_message="official export became stale after source edit",
        reproduces=reproduces,
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    markdown_path = summary_path.with_suffix(".md")
    markdown = markdown_path.read_text(encoding="utf-8")
    minimized_trace = replay_adversarial_trace(
        tmp_path / "triage" / "trace-17-minimized.json",
        data_dir=tmp_path / "minimized-replay",
    )

    assert summary["failure_message"] == "official export became stale after source edit"
    assert summary["original_action_count"] == len(trace.actions)
    assert 0 < summary["minimized_action_count"] < len(trace.actions)
    assert summary["minimized_action_names"] == [action.name for action in minimized_trace.actions]
    assert summary["minimized_actions"] == [
        {"name": action.name, "payload": action.payload}
        for action in minimized_trace.actions
    ]
    assert summary["removed_action_names"] == ["quality", "readiness", "export"]
    assert summary["final_state"]["gates"] == trace.final_state.gates
    assert summary["final_state"]["export_allowed"] == trace.final_state.export_allowed
    assert summary["failure_tags"] == [
        "export_blocked",
        "quality_stale",
        "official_compile_stale",
        "post_draft_review_stale",
    ]
    assert "PYTHONPATH=tests python" in summary["replay_command"]
    assert str(tmp_path / "triage" / "trace-17-minimized.json") in summary["replay_command"]
    assert summary["original_action_category_counts"] == {
        "export_probe": 2,
        "mutation": 1,
        "official_gate": 2,
        "quality_gate": 1,
        "setup": 1,
    }
    assert summary["minimized_action_category_counts"] == {
        "mutation": 1,
        "official_gate": 2,
        "setup": 1,
    }
    assert summary["removed_action_category_counts"] == {
        "export_probe": 2,
        "quality_gate": 1,
    }
    edit_delta = next(delta for delta in trace_payload["action_gate_deltas"] if delta["name"] == "edit")
    assert edit_delta["changed_gates"] == {
        "official_compile": {"before": "current", "after": "stale"},
        "post_draft_review": {"before": "current", "after": "stale"},
        "quality": {"before": "current", "after": "stale"},
    }
    assert edit_delta["export_allowed"] == {"before": True, "after": False}
    assert summary["action_gate_deltas"] == trace_payload["action_gate_deltas"]
    assert [delta["name"] for delta in summary["minimized_action_gate_deltas"]] == summary["minimized_action_names"]
    assert [delta["name"] for delta in summary["removed_action_gate_deltas"]] == summary["removed_action_names"]
    assert minimized_trace.final_state.gates["official_compile"] == "stale"
    assert minimized_trace.final_state.gates["post_draft_review"] == "stale"
    assert markdown_path.exists()
    assert "# Adversarial Failure Triage" in markdown
    assert "official export became stale after source edit" in markdown
    assert "export_blocked, quality_stale, official_compile_stale, post_draft_review_stale" in markdown
    assert "| 0 | intake | setup |" in markdown
    assert "| 3 | edit | mutation |" in markdown
    assert "quality: current -> stale" in markdown
    assert "official_compile: current -> stale" in markdown
    assert "post_draft_review: current -> stale" in markdown
    assert "PYTHONPATH=tests python" in markdown
