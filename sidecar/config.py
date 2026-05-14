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
from pathlib import Path

DATA_DIR_ENV = "VYSTED_DATA_DIR"


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
