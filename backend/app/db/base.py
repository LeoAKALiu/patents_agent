"""SQLAlchemy 2.0 declarative base with naming conventions for local SQLite.

This module is intended as a migration foundation.  Tables will be defined as
subclasses of ``Base`` when the schema is ported from raw sqlite3 to ORM
models.  Until then, production storage continues to use ``SQLiteStore``.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


CONSTRAINT_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy ORM models."""

    metadata = MetaData(naming_convention=CONSTRAINT_NAMING_CONVENTION)
