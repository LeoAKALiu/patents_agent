#!/usr/bin/env python3
"""Frozen backend entry point for the PatentAgent desktop bundle."""

from __future__ import annotations

import argparse

import uvicorn

from backend.app.main import app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the bundled PatentAgent backend.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--log-level", default="warning")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
