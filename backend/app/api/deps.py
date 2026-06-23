"""Shared FastAPI dependencies for the router layer.

All dependencies read from ``request.app.state`` so routers never need to
import the application module directly - avoiding circular imports while
keeping endpoint handlers testable.
"""

from __future__ import annotations

from fastapi import Request

from backend.app.desktop_config import DesktopConfig
from backend.app.llm import LLMClient
from backend.app.settings import Settings
from backend.app.storage import SQLiteStore


def get_settings(request: Request) -> Settings:
    """Return the active ``Settings`` from application state."""
    return request.app.state.settings


def get_store(request: Request) -> SQLiteStore:
    """Return the project SQLite store from application state."""
    return request.app.state.store


def get_llm(request: Request) -> LLMClient:
    """Return the active LLM client from application state."""
    return request.app.state.llm


def get_desktop_config(request: Request) -> DesktopConfig:
    """Return the active desktop config from application state."""
    return request.app.state.desktop_config
