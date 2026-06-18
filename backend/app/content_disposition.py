"""
Content-Disposition header helper for downloadable file responses.

Produces RFC 6266 / RFC 5987 compliant headers:
  attachment; filename="ascii-safe-fallback"; filename*=UTF-8''percent-encoded-utf8

Preserves the file extension, strips path components (including Windows
separators), sanitizes illegal filename characters, and supports Chinese
project names.
"""

from __future__ import annotations

import os
import re
import urllib.parse


def make_content_disposition(
    filename: str,
    *,
    extension: str | None = None,
) -> str:
    """Build a Content-Disposition header value for a downloadable file.

    ``filename`` is the suggested base name (may include path components
    or non-ASCII characters).  ``extension``, if provided, overrides the
    file extension (without leading dot).

    Returns a header string suitable for use as::

        Response(headers={"Content-Disposition": make_content_disposition(...)})
    """
    # 1. Strip path components (platform-aware).
    cleaned = os.path.basename(filename.replace("\\", "/"))

    # 2. Determine and preserve extension.
    root, ext = os.path.splitext(cleaned)
    if extension is not None:
        ext = f".{extension.lstrip('.')}"
    # Keep the extension on root so we can percent-encode the whole name.
    full_name = f"{root}{ext}"

    # 3. Build ASCII-safe fallback: strip non-ASCII, sanitize illegal chars.
    ascii_safe = _to_ascii_safe(root) + ext

    # 4. Percent-encode the full UTF-8 name for filename*.
    utf8_encoded = _encode_rfc5987(full_name)

    return f'attachment; filename="{ascii_safe}"; filename*=UTF-8\'\'{utf8_encoded}'


_ILLEGAL_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _to_ascii_safe(name: str) -> str:
    """Remove non-ASCII characters and sanitize illegal filename chars."""
    # ASCII-only fallback: keep only ASCII printable, strip illegal chars.
    ascii_only = name.encode("ascii", errors="ignore").decode("ascii")
    # Replace illegal filename chars with underscore.
    safe = _ILLEGAL_FILENAME_RE.sub("_", ascii_only)
    # Collapse multiple underscores and strip leading/trailing dots/spaces/underscores.
    safe = re.sub(r"_+", "_", safe)
    safe = safe.strip("._ ")
    return safe or "download"


def _encode_rfc5987(value: str) -> str:
    """Percent-encode a string for the ``filename*=UTF-8''...`` field."""
    utf8_bytes = value.encode("utf-8")
    return urllib.parse.quote(utf8_bytes, safe="")
