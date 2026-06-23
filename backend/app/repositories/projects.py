"""Project repository - persistence layer for project CRUD and related entities.

Wraps ``SQLiteStore`` project operations behind a stable interface so service
modules can be tested without a live database and the storage backend can be
swapped later without touching business logic.

The repository is a **wrapper**, not a replacement.  It delegates every call
to the underlying ``SQLiteStore`` which owns the raw sqlite3 connection,
schema migrations, and row marshalling.
"""

from __future__ import annotations

from typing import Any

from backend.app.schemas import (
    PatentPointCandidate,
    ProjectMaterial,
    ProjectRecord,
)
from backend.app.storage import SQLiteStore


class ProjectRepository:
    """Data access for project entities.

    Parameters
    ----------
    store : SQLiteStore
        The raw storage backend.  The repository does not own the connection
        lifecycle - it only delegates read/write operations.
    """

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    # -- projects ----------------------------------------------------------

    def list_all(self) -> list[ProjectRecord]:
        """Return all projects ordered by most-recently-updated first."""
        return self._store.list_projects()

    def get_by_id(self, project_id: str) -> ProjectRecord | None:
        """Return a single project or ``None`` when not found."""
        return self._store.get_project(project_id)

    def create(self, project: ProjectRecord) -> ProjectRecord:
        """Persist a new project and return it (refreshed from storage)."""
        return self._store.create_project(project)

    def update(self, project_id: str, updates: dict[str, Any]) -> ProjectRecord | None:
        """Apply partial updates to an existing project."""
        return self._store.update_project(project_id, updates)

    def delete(self, project_id: str) -> bool:
        """Delete a project and all its related rows.  Returns ``True`` when a
        row was actually deleted."""
        return self._store.delete_project(project_id)

    # -- materials ---------------------------------------------------------

    def list_materials(self, project_id: str) -> list[ProjectMaterial]:
        """Return materials attached to a project, newest-first."""
        return self._store.list_project_materials(project_id)

    def add_material(self, material: ProjectMaterial) -> ProjectMaterial:
        """Persist a project material record."""
        return self._store.add_project_material(material)

    # -- patent points -----------------------------------------------------

    def list_patent_points(self, project_id: str) -> list[PatentPointCandidate]:
        """Return patent points for a project, selected-first then newest."""
        return self._store.list_project_patent_points(project_id)

    def get_patent_point(
        self, project_id: str, point_id: str
    ) -> PatentPointCandidate | None:
        """Return a single patent point or ``None``."""
        return self._store.get_project_patent_point(project_id, point_id)

    def add_patent_point(
        self, project_id: str, point: PatentPointCandidate
    ) -> PatentPointCandidate:
        """Insert or replace a patent point for a project."""
        return self._store.add_project_patent_point(project_id, point)

    def delete_patent_point(self, project_id: str, point_id: str) -> bool:
        """Delete a patent point.  Returns ``True`` when a row was deleted."""
        return self._store.delete_project_patent_point(project_id, point_id)
