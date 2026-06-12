"""Local desktop configuration store (PR6, issue #20).

Persists non-secret LLM settings (provider, base URL, model) and the API key
on the local machine under ``DATA_DIR/desktop-config.json`` with ``0600``
permissions. The API key is **never** returned by ``redacted_view`` — only a
``present`` boolean and a 4-character fingerprint derived from the tail of the
key. The renderer must never receive the raw key.

The configuration is layered on top of ``Settings`` (which reads ``.env`` /
process env). ``effective_settings`` returns whichever value wins for each
field, with ``desktop_config`` taking precedence over environment values.
"""
from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONFIG_FILENAME = "desktop-config.json"
CONFIG_VERSION = 1
API_KEY_FINGERPRINT_LEN = 4
_PROVIDER_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")


class DesktopConfigError(ValueError):
    """Raised when the desktop configuration file is malformed or invalid."""


@dataclass
class DesktopConfig:
    """LLM configuration persisted to the local desktop config file.

    ``api_key`` is stored in-memory only when loaded from disk; ``redacted_view``
    drops it from the response so the renderer never sees the raw value.
    """

    provider: str = "deepseek"
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-pro"
    api_key: str = ""
    updated_at: str = ""
    version: int = CONFIG_VERSION
    extra: dict[str, Any] = field(default_factory=dict)

    def is_api_key_present(self) -> bool:
        return bool(self.api_key)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_provider(provider: str) -> str:
    if not isinstance(provider, str) or not _PROVIDER_PATTERN.match(provider):
        raise DesktopConfigError(
            f"Invalid provider name: {provider!r}; allowed: lowercase, digits, _ or -"
        )
    return provider


def _validate_base_url(base_url: str) -> str:
    if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
        raise DesktopConfigError(
            f"Invalid base_url: {base_url!r}; must start with http:// or https://"
        )
    return base_url.rstrip("/")


def _validate_model(model: str) -> str:
    if not isinstance(model, str) or not model.strip() or len(model) > 128:
        raise DesktopConfigError(f"Invalid model name: {model!r}")
    return model.strip()


def _validate_api_key(api_key: str) -> str:
    if not isinstance(api_key, str):
        raise DesktopConfigError("api_key must be a string")
    if len(api_key) > 4096:
        raise DesktopConfigError("api_key is too long (>4096 chars)")
    return api_key


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON atomically with 0600 perms so the API key file is owner-only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        os.chmod(tmp_name, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def config_path(data_dir: Path) -> Path:
    return Path(data_dir) / CONFIG_FILENAME


def load_desktop_config(data_dir: Path) -> DesktopConfig:
    """Read the desktop config from ``data_dir/desktop-config.json``.

    Returns the defaults when the file does not exist. Raises
    ``DesktopConfigError`` if the file exists but is malformed.
    """
    path = config_path(data_dir)
    if not path.is_file():
        return DesktopConfig()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DesktopConfigError(
            f"desktop config at {path} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise DesktopConfigError(
            f"desktop config at {path} must be a JSON object"
        )
    version = int(raw.get("version", CONFIG_VERSION))
    return DesktopConfig(
        provider=_validate_provider(str(raw.get("provider", "deepseek"))),
        base_url=_validate_base_url(str(raw.get("base_url", "https://api.deepseek.com"))),
        model=_validate_model(str(raw.get("model", "deepseek-v4-pro"))),
        api_key=_validate_api_key(str(raw.get("api_key", ""))),
        updated_at=str(raw.get("updated_at", "")),
        version=version,
        extra={k: v for k, v in raw.items() if k not in {"provider", "base_url", "model", "api_key", "updated_at", "version"}},
    )


def save_desktop_config(data_dir: Path, config: DesktopConfig) -> DesktopConfig:
    """Persist ``config`` to ``data_dir/desktop-config.json`` atomically.

    The returned object has its ``updated_at`` timestamp refreshed. The file is
    written with ``0600`` perms on POSIX systems.
    """
    config.provider = _validate_provider(config.provider)
    config.base_url = _validate_base_url(config.base_url)
    config.model = _validate_model(config.model)
    config.api_key = _validate_api_key(config.api_key)
    config.version = CONFIG_VERSION
    config.updated_at = _now_iso()
    payload = asdict(config)
    _atomic_write_json(config_path(data_dir), payload)
    return config


def api_key_fingerprint(api_key: str) -> str:
    """Return a short, non-reversible label for ``api_key``.

    The fingerprint is the last ``API_KEY_FINGERPRINT_LEN`` characters of the
    key. It is meant to help the user identify *which* key is currently
    configured without exposing the secret. Empty when no key is set.
    """
    if not api_key:
        return ""
    if len(api_key) <= API_KEY_FINGERPRINT_LEN:
        return "•" * len(api_key)
    return "•" * (len(api_key) - API_KEY_FINGERPRINT_LEN) + api_key[-API_KEY_FINGERPRINT_LEN:]


def redacted_view(config: DesktopConfig) -> dict[str, Any]:
    """Return the configuration shape the renderer is allowed to see.

    The raw ``api_key`` is dropped. The renderer is given:
      * ``api_key_present`` (bool) so the UI can render "configured" / "missing"
      * ``api_key_fingerprint`` (short, non-reversible tail label)
    """
    return {
        "provider": config.provider,
        "base_url": config.base_url,
        "model": config.model,
        "api_key_present": config.is_api_key_present(),
        "api_key_fingerprint": api_key_fingerprint(config.api_key),
        "updated_at": config.updated_at,
        "version": config.version,
    }


def apply_update(
    config: DesktopConfig,
    *,
    provider: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    clear_api_key: bool = False,
) -> DesktopConfig:
    """Return a new ``DesktopConfig`` with the requested fields updated.

    Validation runs up front so callers see errors before the file is written.
    """
    new_provider = _validate_provider(provider) if provider is not None else config.provider
    new_base_url = _validate_base_url(base_url) if base_url is not None else config.base_url
    new_model = _validate_model(model) if model is not None else config.model
    if clear_api_key and api_key is not None:
        raise DesktopConfigError("Pass either api_key or clear_api_key, not both.")
    if clear_api_key:
        new_key = ""
    elif api_key is not None:
        new_key = _validate_api_key(api_key)
    else:
        new_key = config.api_key
    return DesktopConfig(
        provider=new_provider,
        base_url=new_base_url,
        model=new_model,
        api_key=new_key,
        version=CONFIG_VERSION,
        updated_at=config.updated_at,
        extra=dict(config.extra),
    )


def effective_settings(
    env_settings: Any,
    desktop_config: DesktopConfig,
) -> dict[str, Any]:
    """Merge env-based ``Settings`` with the desktop config (desktop wins)."""
    env_key = getattr(env_settings, "deepseek_api_key", None) or ""
    env_base = getattr(env_settings, "deepseek_base_url", None) or "https://api.deepseek.com"
    env_model = getattr(env_settings, "llm_model", None) or "deepseek-v4-pro"
    env_provider = "deepseek"
    has_desktop_values = bool(
        desktop_config.updated_at or desktop_config.api_key or desktop_config.extra
    )
    return {
        "provider": desktop_config.provider if has_desktop_values else env_provider,
        "base_url": desktop_config.base_url if has_desktop_values else env_base,
        "model": desktop_config.model if has_desktop_values else env_model,
        "api_key": desktop_config.api_key or env_key,
        "api_key_source": "desktop_config" if desktop_config.api_key else ("env" if env_key else "none"),
    }
