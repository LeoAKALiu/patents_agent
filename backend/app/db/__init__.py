"""Database package - SQLAlchemy 2.0 declarative base, session factory, and migration scaffolding.

This package establishes the ORM foundation for future schema management.
Production storage still uses the existing ``SQLiteStore`` (raw sqlite3); the
SQLAlchemy layer is wired side-by-side so migration tooling can be introduced
without disrupting current data access paths.

Do NOT import ``backend.app.main`` or any API/router modules from here.
"""
