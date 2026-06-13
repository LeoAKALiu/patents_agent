#!/usr/bin/env python3
"""Idempotent bootstrap helper for the PatentAgent v1.0.0 agent pipeline.

The helper intentionally stays conservative:
- it does not read, write, copy, or prompt for secrets;
- it does not configure auto-merge;
- it does not dispatch Hermes Kanban workers.

By default the script prints the commands it would run. Pass --apply to execute
label/profile/board setup commands.
"""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class LabelSpec:
    name: str
    color: str
    description: str


@dataclass(frozen=True)
class ProfileSpec:
    name: str
    description: str


@dataclass(frozen=True)
class BoardSpec:
    slug: str
    name: str
    description: str


@dataclass(frozen=True)
class Step:
    component: str
    name: str
    status: str
    command: tuple[str, ...] = ()
    detail: str = ""
    exit_code: int | None = None


LABELS: tuple[LabelSpec, ...] = (
    LabelSpec("v1.0.0", "5319e7", "PatentAgent v1.0.0 release scope"),
    LabelSpec("release-blocker", "b60205", "Blocks the v1.0.0 release train"),
    LabelSpec("agent-managed", "0366d6", "Eligible for the autonomous agent pipeline"),
    LabelSpec("agent-ready", "0e8a16", "Ready for agent planning or implementation"),
    LabelSpec("agent-working", "fbca04", "Currently being handled by an agent worker"),
    LabelSpec("agent-review", "1d76db", "Ready for autonomous review"),
    LabelSpec("agent-approved", "0e8a16", "Autonomous reviewer approved the implementation"),
    LabelSpec("needs-fix", "d93f0b", "Reviewer or CI found required changes"),
    LabelSpec("needs-human", "d73a4a", "Automation must stop and ask a human maintainer"),
    LabelSpec("ready-to-merge", "0e8a16", "Reviewer believes the PR satisfies merge policy"),
    LabelSpec("skip-agent", "ededed", "Automation must ignore this issue or PR"),
    LabelSpec("worker:codex", "bfd4f2", "Route to the Codex planning/review profile"),
    LabelSpec("worker:claude", "bfd4f2", "Route to the Claude issue/docs profile"),
    LabelSpec("worker:deepseek", "bfd4f2", "Route to the DeepSeek backend profile"),
    LabelSpec("worker:qwen", "bfd4f2", "Route to the Qwen frontend/profile"),
    LabelSpec("worker:kimi", "bfd4f2", "Route to the Kimi patent-text profile"),
    LabelSpec("desktop", "c5def5", "Desktop runtime or packaging scope"),
    LabelSpec("electron", "c5def5", "Electron desktop shell scope"),
    LabelSpec("workflow:external-draft", "c5def5", "External draft intake/polish workflow"),
    LabelSpec("workflow:export", "c5def5", "Official export workflow"),
    LabelSpec("patent-type:invention", "c5def5", "Chinese invention patent workflow"),
    LabelSpec("patent-type:utility-model", "c5def5", "Chinese utility model workflow"),
    LabelSpec("quality-gate", "fef2c0", "Quality gate, tests, review, or release verification"),
    LabelSpec("agent-auto-merge", "f9d0c4", "Future opt-in only; not enabled by this helper"),
    LabelSpec("human-approved", "0e8a16", "Explicit human permission for high-risk automation"),
)

PROFILES: tuple[ProfileSpec, ...] = (
    ProfileSpec(
        "codexplanner",
        "Release architecture, task decomposition, branch strategy, complex merge/rebase, and merge-readiness review.",
    ),
    ProfileSpec(
        "claudeissues",
        "Issue writing, acceptance criteria, UX copy, README/CHANGELOG, and release-note drafting.",
    ),
    ProfileSpec(
        "deepseekworker",
        "FastAPI backend, parsing, export gates, pytest failures, and deterministic implementation work.",
    ),
    ProfileSpec(
        "qwenworker",
        "React, TypeScript, Vite, Electron UI, and desktop user-experience implementation.",
    ),
    ProfileSpec(
        "kimiworker",
        "Long-context Chinese patent text review, sample drafts, domain prompts, and legal-text consistency checks.",
    ),
    ProfileSpec(
        "codexreviewer",
        "Final PR review, CI interpretation, merge policy, and release risk assessment.",
    ),
)

BOARD = BoardSpec(
    slug="patents-v1",
    name="PatentAgent v1.0.0",
    description="Autonomous agent pipeline for PatentAgent v1.0.0 Electron desktop release",
)

SAFE_NEXT_STEPS = (
    "Keep the first bootstrap PR as a draft until human review is complete.",
    "Do not enable auto-merge; the agent-auto-merge label is documented for a future phase only.",
    "Run hermes kanban dispatch --dry-run --max 1 before any real dispatch.",
    "Create follow-up Kanban tasks only after the bootstrap helper/docs PR is reviewed.",
)


def quote_command(command: Sequence[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def label_command(label: LabelSpec, repo: str | None = None) -> tuple[str, ...]:
    command: list[str] = [
        "gh",
        "label",
        "create",
        label.name,
        "--color",
        label.color,
        "--description",
        label.description,
        "--force",
    ]
    if repo:
        command.extend(("--repo", repo))
    return tuple(command)


def profile_create_command(profile: ProfileSpec) -> tuple[str, ...]:
    return (
        "hermes",
        "profile",
        "create",
        "--no-alias",
        "--description",
        profile.description,
        profile.name,
    )


def board_init_command() -> tuple[str, ...]:
    return ("hermes", "kanban", "init")


def board_create_command(default_workdir: Path) -> tuple[str, ...]:
    return (
        "hermes",
        "kanban",
        "boards",
        "create",
        BOARD.slug,
        "--name",
        BOARD.name,
        "--description",
        BOARD.description,
        "--default-workdir",
        str(default_workdir),
        "--switch",
    )


def board_switch_command() -> tuple[str, ...]:
    return ("hermes", "kanban", "boards", "switch", BOARD.slug)


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


def run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def discover_repo_root() -> Path:
    result = run(("git", "rev-parse", "--show-toplevel"))
    if result.returncode == 0:
        return Path(result.stdout.strip()).resolve()
    return Path.cwd().resolve()


def profile_exists(profile_name: str) -> bool:
    return run(("hermes", "profile", "show", profile_name)).returncode == 0


def board_exists() -> bool:
    result = run(("hermes", "kanban", "boards", "list", "--json"))
    if result.returncode != 0:
        return False
    try:
        boards = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    return any(board.get("slug") == BOARD.slug and not board.get("archived") for board in boards)


def apply_or_plan(
    component: str,
    name: str,
    command: Sequence[str],
    *,
    apply: bool,
    planned_detail: str = "",
) -> Step:
    command_tuple = tuple(command)
    if not apply:
        return Step(component, name, "planned", command_tuple, planned_detail)

    result = run(command_tuple)
    output = (result.stdout + result.stderr).strip()
    if result.returncode == 0:
        return Step(component, name, "ok", command_tuple, output, result.returncode)
    return Step(component, name, "failed", command_tuple, output, result.returncode)


def ensure_labels(*, apply: bool, repo: str | None) -> list[Step]:
    steps: list[Step] = []
    if apply and not command_available("gh"):
        return [Step("labels", "gh", "failed", detail="GitHub CLI not found; install gh before applying labels.")]

    if apply:
        auth = run(("gh", "auth", "status"))
        if auth.returncode != 0:
            return [
                Step(
                    "labels",
                    "gh-auth",
                    "failed",
                    ("gh", "auth", "status"),
                    "GitHub CLI is not authenticated. Run gh auth login; this helper will not configure credentials.",
                    auth.returncode,
                )
            ]

    for label in LABELS:
        steps.append(
            apply_or_plan(
                "labels",
                label.name,
                label_command(label, repo),
                apply=apply,
                planned_detail="idempotent via gh label create --force",
            )
        )
    return steps


def ensure_profiles(*, apply: bool, no_detect: bool) -> list[Step]:
    hermes_available = command_available("hermes")
    if apply and not hermes_available:
        return [Step("profiles", "hermes", "failed", detail="Hermes CLI not found; install Hermes before applying profiles.")]

    steps: list[Step] = []
    for profile in PROFILES:
        if not no_detect and hermes_available and profile_exists(profile.name):
            steps.append(Step("profiles", profile.name, "exists", detail="profile already exists; creation skipped"))
            continue
        steps.append(
            apply_or_plan(
                "profiles",
                profile.name,
                profile_create_command(profile),
                apply=apply,
                planned_detail="no --clone and no secret/auth configuration",
            )
        )
    return steps


def ensure_board(*, apply: bool, default_workdir: Path, no_detect: bool) -> list[Step]:
    hermes_available = command_available("hermes")
    if apply and not hermes_available:
        return [Step("board", BOARD.slug, "failed", detail="Hermes CLI not found; install Hermes before applying the board.")]

    steps: list[Step] = [
        apply_or_plan(
            "board",
            "kanban-init",
            board_init_command(),
            apply=apply,
            planned_detail="safe to run repeatedly",
        )
    ]

    exists = False if no_detect or not hermes_available else board_exists()
    if exists:
        steps.append(
            apply_or_plan(
                "board",
                BOARD.slug,
                board_switch_command(),
                apply=apply,
                planned_detail="board exists; switch to it",
            )
        )
    else:
        steps.append(
            apply_or_plan(
                "board",
                BOARD.slug,
                board_create_command(default_workdir),
                apply=apply,
                planned_detail="create board if missing and switch to it",
            )
        )
        if no_detect:
            steps.append(
                Step(
                    "board",
                    BOARD.slug,
                    "note",
                    board_switch_command(),
                    "If the board already exists, run this switch command instead of create.",
                )
            )
    return steps


def selected_components(values: Sequence[str] | None) -> set[str]:
    if not values:
        return {"labels", "profiles", "board"}
    return set(values)


def build_steps(args: argparse.Namespace) -> list[Step]:
    default_workdir = Path(args.default_workdir).expanduser().resolve() if args.default_workdir else discover_repo_root()
    components = selected_components(args.component)
    steps: list[Step] = []
    if "labels" in components:
        steps.extend(ensure_labels(apply=args.apply, repo=args.repo))
    if "profiles" in components:
        steps.extend(ensure_profiles(apply=args.apply, no_detect=args.no_detect))
    if "board" in components:
        steps.extend(ensure_board(apply=args.apply, default_workdir=default_workdir, no_detect=args.no_detect))
    return steps


def print_steps(steps: Sequence[Step], *, apply: bool) -> None:
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"{mode}: PatentAgent v1.0.0 agent pipeline bootstrap")
    print("Safety policy: no secrets, no auto-merge, no worker dispatch.")
    print()
    for step in steps:
        print(f"[{step.status}] {step.component}: {step.name}")
        if step.command:
            print(f"  $ {quote_command(step.command)}")
        if step.detail:
            print(f"  {step.detail}")
        if step.exit_code not in (None, 0):
            print(f"  exit_code={step.exit_code}")
    print()
    print("Safe next steps:")
    for item in SAFE_NEXT_STEPS:
        print(f"- {item}")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute the idempotent setup commands. Omit for a dry-run plan.",
    )
    parser.add_argument(
        "--component",
        action="append",
        choices=("labels", "profiles", "board"),
        help="Limit execution to one component. Repeatable. Default: all components.",
    )
    parser.add_argument(
        "--repo",
        help="Optional GitHub repo for gh label commands, e.g. LeoAKALiu/patents_agent.",
    )
    parser.add_argument(
        "--default-workdir",
        help="Default workdir for the patents-v1 Kanban board. Defaults to this git worktree root.",
    )
    parser.add_argument(
        "--no-detect",
        action="store_true",
        help="Do not run read-only discovery commands; print a static idempotent plan.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    steps = build_steps(args)
    print_steps(steps, apply=args.apply)
    if args.apply and any(step.status == "failed" for step in steps):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
