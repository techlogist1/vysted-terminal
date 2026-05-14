"""Workspace persistence — ``.vysted-workspace`` files on disk.

The sidecar owns workspace persistence so the frontend never needs filesystem
access. A workspace is opaque JSON — ``{ name, layout, enabledModules, ... }`` —
serialised by the frontend (the dockview layout plus the modules ``enabled``
map). The store treats the body as a free-form mapping: it does not validate or
interpret the layout, it only persists it under :func:`config.get_workspaces_dir`.

Each workspace is one ``<name>.vysted-workspace`` file (JSON). Names are
sanitised to a single path component so a workspace name can never escape the
workspaces directory.
"""

from __future__ import annotations

import json
import re
from typing import Any

from config import get_workspaces_dir

WORKSPACE_SUFFIX = ".vysted-workspace"

# A workspace name maps to exactly one file; anything that is not a safe,
# single-segment filename component is rejected so a name cannot traverse out
# of the workspaces directory.
_SAFE_NAME = re.compile(r"^[A-Za-z0-9 _-]+$")


class WorkspaceNameError(ValueError):
    """Raised when a workspace name is empty or contains unsafe characters."""


class WorkspaceNotFoundError(KeyError):
    """Raised when a requested workspace file does not exist."""


def _validate_name(name: str) -> str:
    """Return ``name`` if it is a safe single-segment filename, else raise."""
    cleaned = name.strip()
    if not cleaned or not _SAFE_NAME.match(cleaned):
        raise WorkspaceNameError(
            f"Invalid workspace name {name!r}: use letters, digits, spaces, "
            "hyphens, or underscores."
        )
    return cleaned


def _path_for(name: str):
    """Return the on-disk path for a validated workspace ``name``."""
    return get_workspaces_dir() / f"{_validate_name(name)}{WORKSPACE_SUFFIX}"


def list_workspaces() -> list[str]:
    """Return the names of all saved workspaces, sorted alphabetically."""
    workspaces_dir = get_workspaces_dir()
    names = [
        path.name[: -len(WORKSPACE_SUFFIX)]
        for path in workspaces_dir.glob(f"*{WORKSPACE_SUFFIX}")
        if path.is_file()
    ]
    return sorted(names)


def save_workspace(name: str, workspace: dict[str, Any]) -> None:
    """Persist ``workspace`` as ``<name>.vysted-workspace``, overwriting any prior."""
    path = _path_for(name)
    path.write_text(json.dumps(workspace, indent=2), encoding="utf-8")


def load_workspace(name: str) -> dict[str, Any]:
    """Return the stored JSON for ``name``; raise if it does not exist."""
    path = _path_for(name)
    if not path.is_file():
        raise WorkspaceNotFoundError(name)
    return json.loads(path.read_text(encoding="utf-8"))


def delete_workspace(name: str) -> None:
    """Delete the ``<name>.vysted-workspace`` file; raise if it does not exist."""
    path = _path_for(name)
    if not path.is_file():
        raise WorkspaceNotFoundError(name)
    path.unlink()
