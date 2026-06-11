import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path


HELPER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap_v1_agent_pipeline.py"


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
