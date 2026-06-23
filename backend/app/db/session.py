"""SQLAlchemy session factory - local, single-file SQLite only.

No pooling, no multi-process, no cloud assumptions.  The session factory is
designed for a single-user desktop application where one FastAPI process owns
the SQLite file.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool


def create_session_factory(db_path: str | Path) -> sessionmaker[Session]:
    """Return a ``sessionmaker`` bound to a local SQLite file.

    The caller is responsible for calling ``factory()`` to obtain a session
    and for closing the session when done.  This factory is intended to be
    stored on the application's ``app.state`` for injection into repositories
    when the ORM path is activated.

    Parameters
    ----------
    db_path : str or Path
        Absolute path to the SQLite database file.  The directory must exist.

    Returns
    -------
    sessionmaker
        Configured session factory (SQLAlchemy 2.0-style).  ``autoflush`` and
        ``expire_on_commit`` are disabled because the desktop app runs in a
        single-thread with no concurrent access.
    """
    engine = create_engine(
        f"sqlite:///{Path(db_path).resolve()}",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
