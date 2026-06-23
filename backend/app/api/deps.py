"""Shared FastAPI dependencies for the router layer.

All dependencies read from ``request.app.state`` so routers never need to
import the application module directly - avoiding circular imports while
keeping endpoint handlers testable.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from backend.app.desktop_config import DesktopConfig
from backend.app.llm import LLMClient
from backend.app.rag import LocalVectorIndex
from backend.app.schemas import ProjectRecord
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


def get_index(request: Request) -> LocalVectorIndex:
    """Return the local vector index from application state."""
    return request.app.state.index


def get_corpus_service(request: Request) -> object:
    """Return the corpus import service from application state."""
    return request.app.state.corpus_service


def require_project(project_id: str, store: SQLiteStore) -> ProjectRecord:
    """Return the project or raise 404."""
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project
