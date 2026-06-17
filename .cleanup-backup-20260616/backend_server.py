"""PyInstaller entry point for the PatentAgent FastAPI backend.

Run with: backend_server <host> <port> [--log-level warning]

PyInstaller bundles backend.app.main:app; this wrapper parses minimal CLI
args and launches uvicorn. Keeping argv parsing here (instead of relying on
`python -m uvicorn ...`) lets the packaged binary start without a Python
interpreter on the host.
"""
from __future__ import annotations

import sys


def main() -> None:
    args = sys.argv[1:]
    host = "127.0.0.1"
    port = 8000
    log_level = "warning"
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 2
            continue
        if arg == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
            continue
        if arg == "--log-level" and i + 1 < len(args):
            log_level = args[i + 1]
            i += 2
            continue
        if arg.startswith("--"):
            i += 1
            continue
        # First positional token overrides port for backward compat.
        try:
            port = int(arg)
        except ValueError:
            pass
        i += 1

    import uvicorn
    from backend.app.main import app

    uvicorn.run(app, host=host, port=port, log_level=log_level)


if __name__ == "__main__":
    main()
