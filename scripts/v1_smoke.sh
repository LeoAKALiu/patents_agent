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
PY
  then
    return
  fi

  if [[ "${PATENTAGENT_SKIP_INSTALL:-0}" == "1" ]]; then
    log "Skipping Python dependency install because PATENTAGENT_SKIP_INSTALL=1"
    return
  fi

  log "Installing Python dev dependencies into the active Python environment"
  if "$PYTHON_BIN" -m pip install -e ".[dev]"; then
    return
  fi

  log "Active Python refused package installation; creating local .venv"
  run "$PYTHON_BIN" -m venv .venv
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
  run "$PYTHON_BIN" -m pip install --upgrade pip
  run "$PYTHON_BIN" -m pip install -e ".[dev]"
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

run_electron_smoke_if_feasible() {
  if [[ "${PATENTAGENT_SKIP_ELECTRON_SMOKE:-0}" == "1" ]]; then
    log "Skipping Electron launch smoke because PATENTAGENT_SKIP_ELECTRON_SMOKE=1"
    return
  fi

  if [[ -z "${PATENTAGENT_ELECTRON_BIN:-}" ]]; then
    if ! (cd desktop && node - <<'NODE' >/dev/null 2>&1
const fs = require("node:fs");
const electron = require("electron");
if (typeof electron !== "string" || !fs.existsSync(electron)) {
  process.exit(1);
}
NODE
    ); then
      log "Skipping Electron launch smoke: Electron binary unavailable (approve/rebuild Electron install scripts, or set PATENTAGENT_ELECTRON_BIN)"
      return
    fi
  fi

  local uname_s
  uname_s="$(uname -s)"
  if [[ "$uname_s" == "Linux" && -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
    if command -v xvfb-run >/dev/null 2>&1; then
      log "Running Electron launch smoke through xvfb-run"
      (cd desktop && xvfb-run -a npm run smoke)
    else
      log "Skipping Electron launch smoke: Linux display server unavailable and xvfb-run not installed"
    fi
  else
    log "Running Electron launch smoke"
    (cd desktop && npm run smoke)
  fi
}

cd "$ROOT_DIR"

ensure_python_deps

run "$PYTHON_BIN" -m pytest -q
run "$PYTHON_BIN" scripts/v1_api_smoke.py

ensure_node_runtime
ensure_npm_deps frontend
run npm --prefix frontend test -- --run
run npm --prefix frontend run build

if [[ -f desktop/package.json ]]; then
  ensure_npm_deps desktop
  run npm --prefix desktop run build
  run_electron_smoke_if_feasible
else
  log "Skipping desktop checks: desktop/package.json not present"
fi

log "v1 smoke completed successfully"
