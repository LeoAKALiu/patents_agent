"""Tests for the SQLAlchemy database session scaffold."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.pool import NullPool

from backend.app.db.base import Base
from backend.app.db.session import create_session_factory


def test_declarative_base_uses_stable_naming_convention() -> None:
    convention = Base.metadata.naming_convention

    assert convention["ix"] == "ix_%(column_0_label)s"
    assert convention["uq"] == "uq_%(table_name)s_%(column_0_name)s"
    assert convention["ck"] == "ck_%(table_name)s_%(constraint_name)s"
    assert convention["fk"] == (
        "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
    )
    assert convention["pk"] == "pk_%(table_name)s"


def test_create_session_factory_uses_local_sqlite_path(tmp_path: Path) -> None:
    db_path = tmp_path / "patents_agent.sqlite3"
    factory = create_session_factory(db_path)

    engine = factory.kw["bind"]
    assert Path(engine.url.database) == db_path.resolve()
    assert isinstance(engine.pool, NullPool)
    assert factory.kw["autoflush"] is False
    assert factory.kw["expire_on_commit"] is False


def test_create_session_factory_returns_usable_sessions(tmp_path: Path) -> None:
    factory = create_session_factory(tmp_path / "patents_agent.sqlite3")

    with factory() as session:
        assert session.execute(text("select 1")).scalar_one() == 1
