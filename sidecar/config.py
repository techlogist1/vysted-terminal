"""Runtime configuration for the sidecar.

The Tauri core resolves the per-OS application data directory and passes it in
via the ``--data-dir`` CLI argument, which ``main.py`` exports as the
``VYSTED_DATA_DIR`` environment variable. Everything that persists to disk —
the portfolio SQLite database, saved ``.vysted-workspace`` files — derives its
path from :func:`get_data_dir`.

When the sidecar is run outside Tauri (local dev, pytest) the variable is
unset and a ``~/.vysted-terminal`` fallback is used; tests override it with a
temporary directory.
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from pathlib import Path

DATA_DIR_ENV = "VYSTED_DATA_DIR"

# --- Region / locale (Pass B / Pillar A — FR-060) ---------------------------
#
# The frontend already owns the active region (``src/lib/region.ts`` +
# ``store/settings.ts``). Pass B threads it into the sidecar so the provider
# registry, news, screener, and macro handlers shape data for the user's locale
# (the "McDonald's principle", Constitution VIII). The region rides each request
# as the ``X-Vysted-Region`` header (the same per-request transport BYOK secrets
# use — never persisted); a single ASGI middleware in :mod:`app` reads it into
# the per-request ContextVar below, so any code path the request reaches —
# routers *and* the agent tool loop — sees the same region via :func:`get_region`.
#
# The default is ``"US"`` so every existing caller (and every test that does not
# set a region) behaves exactly as before. ``VYSTED_REGION`` is a last-resort
# env fallback for non-HTTP entrypoints (CLI / tests).
REGION_ENV = "VYSTED_REGION"
_DEFAULT_REGION = "US"
_KNOWN_REGIONS = frozenset({"US", "IN", "GLOBAL"})

# Sentinel: the ContextVar is "unset" until a request middleware sets it, which
# lets :func:`get_region` distinguish "no request region" (→ env / default) from
# an explicit ``US`` request without an extra flag.
_REGION_UNSET = ""
_region_ctx: ContextVar[str] = ContextVar("vysted_region", default=_REGION_UNSET)


def normalize_region(value: str | None) -> str:
    """Coerce an arbitrary value to a known region code, defaulting to ``US``.

    Unknown / empty values fall back to the default rather than raising — a
    malformed ``X-Vysted-Region`` header must never break a data request.
    """
    if not value:
        return _DEFAULT_REGION
    candidate = value.strip().upper()
    return candidate if candidate in _KNOWN_REGIONS else _DEFAULT_REGION


def get_region() -> str:
    """Return the active region for the current request/task.

    Reads the per-request ContextVar set by the region middleware; absent that
    (non-HTTP entrypoints), falls back to ``VYSTED_REGION`` then ``"US"``. The
    value is always a known region code (``US`` / ``IN`` / ``GLOBAL``).
    """
    current = _region_ctx.get()
    if current in _KNOWN_REGIONS:
        return current
    # ContextVar unset (non-HTTP entrypoint) → env fallback, then default.
    return normalize_region(os.environ.get(REGION_ENV))


def set_request_region(value: str | None) -> object:
    """Set the active region for the current request; returns a reset token.

    The middleware calls this on the way in and resets with the returned token on
    the way out so request-scoped state never leaks between requests.
    """
    return _region_ctx.set(normalize_region(value))


def reset_request_region(token: object) -> None:
    """Restore the region ContextVar to its prior value (middleware teardown)."""
    _region_ctx.reset(token)  # type: ignore[arg-type]


def get_data_dir() -> Path:
    """Return the application data directory, creating it if necessary."""
    raw = os.environ.get(DATA_DIR_ENV)
    path = Path(raw) if raw else Path.home() / ".vysted-terminal"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_workspaces_dir() -> Path:
    """Return the directory holding saved ``.vysted-workspace`` files."""
    path = get_data_dir() / "workspaces"
    path.mkdir(parents=True, exist_ok=True)
    return path
