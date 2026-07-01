#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-$(command -v python3)}"

# macOS developer machines often have a stale /usr/local/bin/node earlier in
# PATH. Prefer Homebrew's modern Node/npm when present; Vite/Vitest require a
# current Node runtime.
if [[ -x /opt/homebrew/bin/node && -x /opt/homebrew/bin/npm ]]; then
  export PATH="/opt/homebrew/bin:${PATH}"
fi

log() {
  printf '\n[v1-smoke] %s\n' "$*"
}

run() {
  log "$*"
  "$@"
}

ensure_python_deps() {
  if "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import fastapi  # noqa: F401
import httpx  # noqa: F401
import pytest  # noqa: F401
import docx  # noqa: F401
import PyInstaller  # noqa: F401
PY
  then
    return
  fi

  if [[ "${PATENTAGENT_SKIP_INSTALL:-0}" == "1" ]]; then
    log "Skipping Python dependency install because PATENTAGENT_SKIP_INSTALL=1"
    return
  fi

  log "Installing Python dev dependencies into the active Python environment"
  if "$PYTHON_BIN" -m pip install -e ".[dev,packaging]"; then
    return
  fi

  log "Active Python refused package installation; creating local .venv"
  run "$PYTHON_BIN" -m venv .venv
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
  run "$PYTHON_BIN" -m pip install --upgrade pip
  run "$PYTHON_BIN" -m pip install -e ".[dev,packaging]"
}

ensure_npm_deps() {
  local workspace="$1"
  if [[ "${PATENTAGENT_SKIP_INSTALL:-0}" == "1" ]]; then
    log "Skipping npm install for ${workspace} because PATENTAGENT_SKIP_INSTALL=1"
    return
  fi

  if [[ -f "${workspace}/package-lock.json" && ! -d "${workspace}/node_modules" ]]; then
    log "Installing npm dependencies in ${workspace}"
    (cd "$workspace" && npm ci)
  fi
}

ensure_node_runtime() {
  local major
  major="$(node -p 'Number(process.versions.node.split(".")[0])' 2>/dev/null || echo 0)"
  if (( major < 20 )); then
    printf 'v1 smoke requires Node >=20 for Vite/Vitest; found: ' >&2
    node --version >&2 || true
    return 1
  fi
}

ensure_tauri_resource_placeholders() {
  # `cargo check` runs Tauri's build script, which validates resource paths in
  # tauri.conf.json. Clean source worktrees do not have the PyInstaller
  # one-folder sidecar output yet, so provide the directory shape needed for
  # Rust checks. If a generated sidecar already exists, the smoke can continue;
  # the sidecar build step refreshes it before cargo checks run.
  # Packaging still builds the real sidecar before producing a DMG.
  local sidecar_dir="build/backend/patentagent-backend"
  local executable_path="${sidecar_dir}/patentagent-backend"
  if [[ -f "$sidecar_dir" ]]; then
    log "Replacing legacy Tauri sidecar file placeholder with a directory placeholder"
    rm -f "$sidecar_dir"
  fi

  if [[ -x "$executable_path" ]]; then
    log "Using existing Tauri sidecar resource directory"
    return
  fi

  log "Preparing Tauri resource placeholder directory for cargo checks"
  mkdir -p "$sidecar_dir"
  if [[ ! -e "$executable_path" ]]; then
    printf '#!/bin/sh\nexit 0\n' > "$executable_path"
  fi
  chmod +x "$executable_path"
}

run_tauri_smoke_if_present() {
  if [[ ! -f src-tauri/Cargo.toml ]]; then
    log "Skipping Tauri checks: src-tauri/Cargo.toml not present"
    return
  fi

  if [[ "${PATENTAGENT_SKIP_TAURI_SMOKE:-0}" == "1" ]]; then
    log "Skipping Tauri checks because PATENTAGENT_SKIP_TAURI_SMOKE=1"
    return
  fi

  run env PYTHON="$PYTHON_BIN" scripts/build_backend_sidecar.sh
  run cargo check --manifest-path src-tauri/Cargo.toml
  run cargo test --manifest-path src-tauri/Cargo.toml
}

cd "$ROOT_DIR"

ensure_python_deps

run "$PYTHON_BIN" -m pytest -q
V1_1_REPORT_DIR="${PATENTAGENT_V1_1_REPORT_DIR:-${ROOT_DIR}/.artifacts/v1.1.0-quality}"
V1_1_REPEAT_COUNT="${PATENTAGENT_V1_1_REPEAT_COUNT:-2}"
run "$PYTHON_BIN" scripts/v1_api_smoke.py --repeat-count "$V1_1_REPEAT_COUNT" --report-dir "$V1_1_REPORT_DIR"

ensure_node_runtime
ensure_npm_deps frontend
run npm --prefix frontend test -- --run
run npm --prefix frontend run build
ensure_tauri_resource_placeholders
run_tauri_smoke_if_present

log "v1 smoke completed successfully"
