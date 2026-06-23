# Database migrations (Alembic)

## Status

Alembic is installed as a dependency and the SQLAlchemy declarative base is
scaffolded in ``backend/app/db/base.py``.  **No migrations have been
generated yet.**  The production storage layer still uses the raw-sqlite3
``SQLiteStore`` in ``backend/app/storage.py``.

## When you are ready to migrate

1. Define ORM models as subclasses of ``Base`` in the relevant domain
   package (e.g. ``backend/app/repositories/models.py``).
2. Run ``alembic init backend/app/db/migrations`` to create the Alembic
   environment, then customize ``env.py`` to point at the local SQLite file.
3. Generate the initial migration:

   .. code-block:: bash

      alembic revision --autogenerate -m "initial schema"

4. Apply:

   .. code-block:: bash

      alembic upgrade head

## Design constraints

- **No destructive migration runs automatically.**  Every migration must be
  reviewed and applied deliberately.
- **No cloud or multi-user assumptions.**  The database is a local SQLite
  file owned by a single desktop process.
- **Existing data must survive migration.**  The first migration must be
  additive (new tables / columns) and must preserve all rows currently
  readable through ``SQLiteStore``.
