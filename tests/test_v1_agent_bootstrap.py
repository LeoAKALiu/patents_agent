import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path


HELPER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap_v1_agent_pipeline.py"
RELEASE_HANDOFF_PATH = Path(__file__).resolve().parents[1] / "docs" / "release" / "v1.1.0-release-handoff.md"


def load_helper():
    spec = importlib.util.spec_from_file_location("bootstrap_v1_agent_pipeline", HELPER_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_label_commands_are_idempotent_and_repo_scoped():
    helper = load_helper()

    command = helper.label_command(helper.LABELS[0], repo="LeoAKALiu/patents_agent")

    assert command[:3] == ("gh", "label", "create")
    assert "--force" in command
    assert command[-2:] == ("--repo", "LeoAKALiu/patents_agent")


def test_profile_commands_do_not_clone_or_configure_secrets():
    helper = load_helper()

    commands = [helper.profile_create_command(profile) for profile in helper.PROFILES]
    flattened = "\n".join(helper.quote_command(command) for command in commands)

    assert "--clone" not in flattened
    assert "auth" not in flattened
    assert "api_key" not in flattened.lower()
    assert ".env" not in flattened
    assert "token" not in flattened.lower()


def test_static_plan_contains_no_dispatch_merge_or_secret_setup(tmp_path):
    helper = load_helper()
    args = argparse.Namespace(
        apply=False,
        component=None,
        repo="LeoAKALiu/patents_agent",
        default_workdir=str(tmp_path),
        no_detect=True,
    )

    steps = helper.build_steps(args)
    commands = [step.command for step in steps if step.command]

    assert any(command[:3] == ("gh", "label", "create") for command in commands)
    assert any(command[:3] == ("hermes", "profile", "create") for command in commands)
    assert any(command[:4] == ("hermes", "kanban", "boards", "create") for command in commands)

    for command in commands:
        assert command[:3] != ("hermes", "kanban", "dispatch")
        assert command[:3] != ("gh", "pr", "merge")
        assert command[:2] != ("hermes", "auth")
        assert command[:2] != ("hermes", "model")
        assert "--clone" not in command


def test_cli_static_dry_run_succeeds(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(HELPER_PATH),
            "--no-detect",
            "--component",
            "board",
            "--default-workdir",
            str(tmp_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "DRY-RUN" in result.stdout
    assert "patents-v1" in result.stdout
    assert "no secrets, no auto-merge, no worker dispatch" in result.stdout


def test_v1_1_release_handoff_keeps_release_steps_human_only():
    text = RELEASE_HANDOFF_PATH.read_text(encoding="utf-8")

    assert "HUMAN-ONLY" in text
    assert "must not be executed by default CI" in text
    assert "no-auto-release" in text
    assert "No workflow in this release branch publishes releases, creates tags, uploads artifacts, or enables auto-merge." in text
    assert "gh release create" in text
    assert "git tag -a v1.1.0" in text
    assert "do not run in automation" in text


def test_v1_1_release_handoff_lists_all_kanban_tasks_and_current_prs():
    text = RELEASE_HANDOFF_PATH.read_text(encoding="utf-8")

    for task_id in [
        "t_67475984",
        "t_2676c2a6",
        "t_c56529d6",
        "t_9bd4c74a",
        "t_bf6bd756",
        "t_9bea91f4",
        "t_b3c01694",
        "t_8ccd0572",
    ]:
        assert task_id in text
    for pr_ref in ["#44", "#45", "#46", "#47", "#48", "#49", "#50"]:
        assert pr_ref in text


def test_release_automation_does_not_create_tags_releases_or_merges():
    root = Path(__file__).resolve().parents[1]
    checked_files = [
        *sorted((root / ".github" / "workflows").glob("*.yml")),
        *sorted((root / "scripts").glob("*.py")),
        *sorted((root / "scripts").glob("*.sh")),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in checked_files)

    assert "gh release create" not in combined
    assert "git tag -a" not in combined
    assert "gh pr merge" not in combined
    assert "git push --tags" not in combined
