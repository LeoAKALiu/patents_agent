from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-v4-pro"
    embedding_model: str = "local-hash-128"
    data_dir: Path = Path("data")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
    )


# Precedence for the desktop backend data directory.
#
# 1. ``PATENTAGENT_BACKEND_DATA_DIR`` is the explicit, namespaced override that
#    QA and the Tauri sidecar use to point the backend at a temporary
#    directory so packaged app launches cannot accidentally write into
#    ``~/Library/Application Support/xin.liubo.patentagent`` (issue #PR-7).
# 2. ``DATA_DIR`` is the existing sidecar convention used by the Rust
#    supervisor.  It is honored as a fallback so the production Tauri build
#    keeps working without changes.
# 3. The Pydantic default (``data`` relative to the working directory) is the
#    last resort and is only used by tests and the corpus CLI.
BACKEND_DATA_DIR_ENV: tuple[str, ...] = (
    "PATENTAGENT_BACKEND_DATA_DIR",
    "DATA_DIR",
)

# ``PATENTAGENT_QA_PROFILE`` lets QA scripts tag the backend as a QA run so the
# health endpoint and the Tauri sidecar can surface "QA mode" instead of
# silently inheriting production settings.  It is intentionally opt-in: the
# only thing that turns it on is the explicit override env, never a default.
QA_PROFILE_ENV = "PATENTAGENT_QA_PROFILE"

# ``PATENTAGENT_INSTANCE_ID`` is exported by the Tauri supervisor so the
# backend, the instance lockfile, and the ``/api/health`` diagnostics block
# all report the *same* per-launch identifier.  Without it the uvicorn entry
# point (``backend.app.main:app``) would surface ``instance_id: null`` even
# though Tauri generated one, which is exactly the truthfulness gap PR-7
# closes.
INSTANCE_ID_ENV = "PATENTAGENT_INSTANCE_ID"

# ``PATENTAGENT_BACKEND_PORT`` mirrors the ``--port`` the Tauri supervisor
# binds the uvicorn child to.  The backend cannot otherwise discover its own
# listen port, so the diagnostics block would report ``backend_port: null``.
# Exported by Rust in ``start_backend_with_python``.
BACKEND_PORT_ENV = "PATENTAGENT_BACKEND_PORT"


def _resolve_env_data_dir() -> Path | None:
    for env_name in BACKEND_DATA_DIR_ENV:
        value = os.environ.get(env_name)
        if value:
            return Path(value).expanduser()
    return None


def _env_data_dir_source() -> str | None:
    for env_name in BACKEND_DATA_DIR_ENV:
        if os.environ.get(env_name):
            return env_name
    return None


def resolve_backend_data_dir(explicit: str | os.PathLike[str] | None = None) -> Path:
    """Return the data directory for the backend, applying documented precedence.

    ``explicit`` wins over everything; tests use it to inject a temporary
    directory.  When ``explicit`` is ``None`` the function looks at
    :data:`BACKEND_DATA_DIR_ENV` in order and finally falls back to
    ``Path("data")``.
    """

    if explicit is not None:
        return Path(explicit).expanduser()
    env_value = _resolve_env_data_dir()
    if env_value is not None:
        return env_value
    return Path("data")


def data_dir_source(explicit: str | os.PathLike[str] | None = None) -> str:
    """Return a short label explaining which path provided the active data dir.

    The frontend surfaces this string in the diagnostics panel so QA can
    distinguish a launch with an explicit override from one that silently
    inherited the production application support directory.
    """

    if explicit is not None:
        return "explicit"
    env_source = _env_data_dir_source()
    if env_source is not None:
        return env_source
    return "default"


def resolve_qa_profile(explicit: bool | None = None) -> bool:
    """Return whether the current backend is running in QA-profile mode.

    Tests pass ``True``/``False`` explicitly; the production backend only
    treats ``PATENTAGENT_QA_PROFILE=1`` / ``true`` / ``yes`` as opt-in.  The
    flag is intentionally not auto-enabled by data_dir_source because
    ``DATA_DIR`` may legitimately point at the production directory in
    regression tests.
    """

    if explicit is not None:
        return bool(explicit)
    raw = os.environ.get(QA_PROFILE_ENV)
    if not raw:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def resolve_instance_id(explicit: str | None = None) -> str | None:
    """Return the per-launch instance id, honoring explicit > env > None.

    The Tauri supervisor generates an id once in ``setup`` and exports it via
    :data:`INSTANCE_ID_ENV` so the uvicorn child, the instance lockfile, and
    the ``/api/health`` diagnostics all agree.  Tests inject ``explicit``;
    the uvicorn entry point relies on the env fallback.  An empty/whitespace
    env value is treated as unset so a misconfigured launch surfaces
    ``None`` rather than a blank string.
    """

    if explicit is not None:
        return explicit
    raw = os.environ.get(INSTANCE_ID_ENV)
    if raw is None:
        return None
    raw = raw.strip()
    return raw or None


def resolve_backend_port(explicit: int | None = None) -> int | None:
    """Return the backend listen port, honoring explicit > env > None.

    Mirrors :func:`resolve_instance_id`: the Tauri supervisor exports
    :data:`BACKEND_PORT_ENV` so the backend can report the port it was bound
    to.  A non-integer or out-of-range env value is ignored (returns
    ``None``) rather than crashing the diagnostics path.
    """

    if explicit is not None:
        return explicit
    raw = os.environ.get(BACKEND_PORT_ENV)
    if not raw:
        return None
    try:
        port = int(raw)
    except (TypeError, ValueError):
        return None
    if 0 < port <= 65535:
        return port
    return None


def build_settings(
    *,
    load_env_file: bool = True,
    data_dir: str | os.PathLike[str] | None = None,
) -> Settings:
    """Construct a :class:`Settings` honoring the documented precedence.

    ``data_dir`` (positional/named) wins over env vars and the Pydantic
    default.  When omitted the function applies the env precedence itself so
    tests and the Tauri supervisor can simply call this with no args.
    """

    if load_env_file:
        settings = Settings()
    else:
        settings = Settings(_env_file=None)
    resolved = resolve_backend_data_dir(data_dir)
    settings.data_dir = resolved
    return settings
