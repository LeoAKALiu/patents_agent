#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-$(command -v python3)}"
RUN_FULL=0
SKIP_SMOKE=0
SKIP_DOM_SMOKE=0
REQUIRE_CLEAN=0

usage() {
  cat <<'EOF'
Usage: scripts/package_dmg.sh [options]

Build a local PatentAgent macOS DMG from the current checkout and write a
single handoff report under .artifacts/dmg/.

Options:
  --full             Run scripts/v1_smoke.sh before packaging. Use for PR/release handoff.
  --skip-smoke       Build and hdiutil-verify the DMG, but skip DMG smoke and DOM smoke.
  --skip-dom-smoke   Run DMG smoke, but skip env-gated Tauri DOM smoke.
  --require-clean    Fail if the worktree has local changes.
  -h, --help         Show this help.

Default mode is a fast local handoff:
  source identity -> stale volume detach -> Tauri DMG build -> identity copy
  -> hdiutil verify -> DMG smoke -> Tauri DOM smoke -> report.md
EOF
}

while (($#)); do
  case "$1" in
    --full)
      RUN_FULL=1
      ;;
    --skip-smoke)
      SKIP_SMOKE=1
      SKIP_DOM_SMOKE=1
      ;;
    --skip-dom-smoke)
      SKIP_DOM_SMOKE=1
      ;;
    --require-clean)
      REQUIRE_CLEAN=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

cd "$ROOT_DIR"

if [[ -x /opt/homebrew/bin/node && -x /opt/homebrew/bin/npm ]]; then
  export PATH="/opt/homebrew/bin:${PATH}"
fi

BRANCH="$(git branch --show-current)"
SHORT_SHA="$(git rev-parse --short HEAD)"
FULL_SHA="$(git rev-parse HEAD)"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
ARTIFACT_DIR="${ROOT_DIR}/.artifacts/dmg/${TIMESTAMP}-${SHORT_SHA}"
LOG_FILE="${ARTIFACT_DIR}/package.log"
REPORT_FILE="${ARTIFACT_DIR}/report.md"
SMOKE_JSON="${ARTIFACT_DIR}/tauri_dmg_smoke.json"
DOM_SMOKE_REPORT="${ARTIFACT_DIR}/tauri_dom_smoke.json"

mkdir -p "$ARTIFACT_DIR"

log() {
  printf '\n[package-dmg] %s\n' "$*" | tee -a "$LOG_FILE"
}

run() {
  log "+ $*"
  set +e
  "$@" 2>&1 | tee -a "$LOG_FILE"
  local status=${PIPESTATUS[0]}
  set -e
  return "$status"
}

run_capture() {
  local output_path="$1"
  shift
  log "+ $*"
  set +e
  "$@" 2>&1 | tee -a "$LOG_FILE" > "$output_path"
  local status=${PIPESTATUS[0]}
  set -e
  cat "$output_path" >> "$LOG_FILE"
  return "$status"
}

json_value() {
  local expression="$1"
  "$PYTHON_BIN" -c "import json; from pathlib import Path; data=json.loads(Path('src-tauri/tauri.conf.json').read_text()); print(${expression})"
}

version_from_tauri_config() {
  json_value "data['version']"
}

tauri_arch() {
  case "$(uname -m)" in
    arm64) printf 'aarch64' ;;
    x86_64) printf 'x64' ;;
    *) uname -m ;;
  esac
}

latest_dmg() {
  "$PYTHON_BIN" - "${ROOT_DIR}/src-tauri/target/release/bundle/dmg" <<'PY'
import sys
from pathlib import Path

directory = Path(sys.argv[1])
if not directory.is_dir():
    raise SystemExit(0)

candidates = [path for path in directory.glob("PatentAgent_*.dmg") if path.is_file()]
if candidates:
    print(max(candidates, key=lambda path: path.stat().st_mtime))
PY
}

STATUS_SHORT="$(git status --short --branch)"
DIRTY_FILES="$(git status --short)"
DIFF_STAT="$(git diff --stat || true)"
DIRTY_LABEL="no"
if [[ -n "$DIRTY_FILES" ]]; then
  DIRTY_LABEL="yes"
fi

if [[ "$REQUIRE_CLEAN" == "1" && "$DIRTY_LABEL" == "yes" ]]; then
  printf 'Worktree is dirty; rerun without --require-clean or commit/stash changes.\n' >&2
  git status --short >&2
  exit 1
fi

log "source: ${BRANCH}@${SHORT_SHA}"
log "worktree dirty: ${DIRTY_LABEL}"
printf '%s\n' "$STATUS_SHORT" > "${ARTIFACT_DIR}/git-status.txt"
printf '%s\n' "$DIFF_STAT" > "${ARTIFACT_DIR}/git-diff-stat.txt"

VERSION="$(version_from_tauri_config)"
ARCH="$(tauri_arch)"
DEFAULT_DMG="${ROOT_DIR}/src-tauri/target/release/bundle/dmg/PatentAgent_${VERSION}_${ARCH}.dmg"
IDENTITY_DMG="${ARTIFACT_DIR}/PatentAgent_${VERSION}_${SHORT_SHA}_${TIMESTAMP}_${ARCH}.dmg"
BUILD_RESULT="not-run"
VERIFY_RESULT="not-run"
SMOKE_RESULT="skipped"
DOM_SMOKE_RESULT="skipped"
SMOKE_DIR=""
SHA256_VALUE=""
SIZE_VALUE=""

log "checking packaging prerequisites"
if ! run "$PYTHON_BIN" -m PyInstaller --version; then
  printf 'PyInstaller is required. Install packaging deps with: %s -m pip install -e ".[packaging]"\n' "$PYTHON_BIN" >&2
  exit 1
fi
export PYTHON="$PYTHON_BIN"
log "using Python for Tauri beforeBuildCommand: ${PYTHON}"

if [[ "$RUN_FULL" == "1" ]]; then
  run scripts/v1_smoke.sh
fi

log "detaching stale /Volumes/PatentAgent if present"
if hdiutil info | grep -q '/Volumes/PatentAgent'; then
  if run hdiutil detach /Volumes/PatentAgent; then
    log "detached stale /Volumes/PatentAgent"
  elif run hdiutil detach -force /Volumes/PatentAgent; then
    log "force-detached stale /Volumes/PatentAgent"
  else
    printf 'Unable to detach stale /Volumes/PatentAgent. Close any running PatentAgent app and retry.\n' >&2
    exit 1
  fi
else
  log "no stale /Volumes/PatentAgent mount found"
fi

TAURI_BUILD=(cargo tauri build --bundles dmg --ci)
if ! cargo tauri --version >/dev/null 2>&1; then
  TAURI_BUILD=(npm exec --yes --package @tauri-apps/cli@^2 -- tauri build --bundles dmg --ci)
fi

log "building Tauri DMG"
rm -f "$DEFAULT_DMG"
if run "${TAURI_BUILD[@]}"; then
  BUILD_RESULT="pass"
else
  BUILD_RESULT="tauri-build-failed"
  BUNDLE_SCRIPT="${ROOT_DIR}/src-tauri/target/release/bundle/dmg/bundle_dmg.sh"
  MACOS_BUNDLE_DIR="${ROOT_DIR}/src-tauri/target/release/bundle/macos"
  VOLICON="${ROOT_DIR}/src-tauri/target/release/bundle/dmg/icon.icns"
  if [[ -f "$BUNDLE_SCRIPT" && -d "${MACOS_BUNDLE_DIR}/PatentAgent.app" ]]; then
    log "Tauri build returned non-zero; trying generated bundle_dmg.sh fallback"
    rm -f "$DEFAULT_DMG"
    run bash "$BUNDLE_SCRIPT" \
      --volname PatentAgent \
      --volicon "$VOLICON" \
      --skip-jenkins \
      "$DEFAULT_DMG" \
      "$MACOS_BUNDLE_DIR"
    BUILD_RESULT="pass-with-bundle-dmg-fallback"
  else
    printf 'Tauri build failed before an app bundle and bundle_dmg.sh were available. See %s\n' "$LOG_FILE" >&2
    exit 1
  fi
fi

if [[ ! -f "$DEFAULT_DMG" ]]; then
  FOUND_DMG="$(latest_dmg || true)"
  if [[ -n "$FOUND_DMG" && -f "$FOUND_DMG" ]]; then
    DEFAULT_DMG="$FOUND_DMG"
  else
    printf 'No DMG artifact found after build. See %s\n' "$LOG_FILE" >&2
    exit 1
  fi
fi

cp "$DEFAULT_DMG" "$IDENTITY_DMG"

log "verifying identity DMG"
run hdiutil verify "$IDENTITY_DMG"
VERIFY_RESULT="pass"
SHA256_VALUE="$(shasum -a 256 "$IDENTITY_DMG" | awk '{print $1}')"
SIZE_VALUE="$(du -h "$IDENTITY_DMG" | awk '{print $1}')"

if [[ "$SKIP_SMOKE" == "0" ]]; then
  log "running DMG smoke"
  run_capture "$SMOKE_JSON" "$PYTHON_BIN" scripts/tauri_dmg_smoke.py "$IDENTITY_DMG" --keep-artifacts
  SMOKE_RESULT="pass"
  SMOKE_DIR="$("$PYTHON_BIN" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("smoke_dir",""))' "$SMOKE_JSON")"

  if [[ "$SKIP_DOM_SMOKE" == "0" ]]; then
    SMOKE_APP="${SMOKE_DIR}/PatentAgent.app"
    SMOKE_EXECUTABLE="${SMOKE_APP}/Contents/MacOS/patentagent-tauri"
    if [[ -x "$SMOKE_EXECUTABLE" ]]; then
      log "running Tauri DOM smoke"
      run env \
        PATENTAGENT_TAURI_DOM_SMOKE=1 \
        PATENTAGENT_TAURI_DOM_SMOKE_REPORT="$DOM_SMOKE_REPORT" \
        "$SMOKE_EXECUTABLE"
      DOM_SMOKE_RESULT="pass"
    else
      printf 'Smoke app executable not found: %s\n' "$SMOKE_EXECUTABLE" >&2
      exit 1
    fi
  fi
fi

cat > "$REPORT_FILE" <<EOF
# PatentAgent DMG Handoff

- Source: ${BRANCH}@${SHORT_SHA}
- Full SHA: ${FULL_SHA}
- Worktree dirty: ${DIRTY_LABEL}
- Git status: \`${STATUS_SHORT}\`
- Intentional local changes: see \`${ARTIFACT_DIR}/git-diff-stat.txt\`
- Mode: $([[ "$RUN_FULL" == "1" ]] && printf 'full' || printf 'dev')
- Build result: ${BUILD_RESULT}
- DMG verify: ${VERIFY_RESULT}
- DMG smoke: ${SMOKE_RESULT}
- Tauri DOM smoke: ${DOM_SMOKE_RESULT}
- DMG: ${IDENTITY_DMG}
- Size: ${SIZE_VALUE}
- SHA256: ${SHA256_VALUE}
- Build log: ${LOG_FILE}
- DMG smoke JSON: ${SMOKE_JSON}
- DMG smoke dir: ${SMOKE_DIR:-not-run}
- Tauri DOM smoke report: $([[ -f "$DOM_SMOKE_REPORT" ]] && printf '%s' "$DOM_SMOKE_REPORT" || printf 'not-run')

## Notes

- This script packages the current checkout. If the worktree is dirty, the DMG represents \`HEAD + local changes\`.
- The identity-bearing DMG under \`.artifacts/dmg/\` is the handoff artifact. The default Tauri DMG filename may be overwritten by later builds.
- \`pass-with-bundle-dmg-fallback\` means Tauri created the app bundle but the generated DMG wrapper had to be run directly with \`--skip-jenkins\`.
- This does not claim Developer ID signing, notarization, stapling, GitHub release creation, or auto-update readiness.
EOF

log "handoff report: ${REPORT_FILE}"
log "identity DMG: ${IDENTITY_DMG}"
log "sha256: ${SHA256_VALUE}"
