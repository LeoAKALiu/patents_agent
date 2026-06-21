#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-$(command -v python3)}"

cd "$ROOT_DIR"

export PYINSTALLER_CONFIG_DIR=build/pyinstaller-cache

printf '[backend-sidecar] using Python: %s\n' "$PYTHON"
"$PYTHON" -m PyInstaller --version

find backend -type d -name __pycache__ -prune -exec rm -rf {} +

"$PYTHON" -m PyInstaller scripts/backend.spec --noconfirm --distpath build/backend --workpath build/pyinstaller-work
