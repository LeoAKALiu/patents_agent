"""Repository package - persistence-agnostic data access layer.

Repositories wrap the storage backend (currently ``SQLiteStore``) behind a
consistent interface so service modules can operate without knowing the
underlying storage implementation.

Future: when SQLAlchemy ORM models are introduced, repositories will switch
to SQLAlchemy sessions while keeping the same method signatures.
"""
