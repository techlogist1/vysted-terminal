"""Workspace persistence — ``.vysted-workspace`` files on disk.

The sidecar owns workspace persistence so the frontend never needs filesystem
access. A workspace is opaque JSON — ``{ name, layout, enabledModules, ... }`` —
serialised by the frontend (the dockview layout plus the modules ``enabled``
map). The store treats the body as a free-form mapping: it does not validate or
interpret the layout, it only persists it under :func:`config.get_workspaces_dir`.

Each workspace is one ``<name>.vysted-workspace`` file (JSON). Any name is
accepted: it is percent-encoded into a single path component, so a name can
never escape the workspaces directory, and decoded back when listed.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

from config import get_workspaces_dir

logger = logging.getLogger(__name__)

WORKSPACE_SUFFIX = ".vysted-workspace"

# Encoded-stem ceiling, in BYTES (not characters): the stem plus the suffix and
# the per-writer temp/backup tails must stay under the 255-byte filename limit
# of every desktop filesystem.
_MAX_STEM_BYTES = 200

# Characters that are unsafe as a filename component on at least one of
# macOS/Windows/Linux (path separators + Windows-reserved punctuation).
# Control characters and NUL are also encoded (checked separately below).
# Everything else — including non-Latin scripts (Devanagari, CJK, …) — is
# kept as its raw UTF-8 bytes: percent-encoding it would triple-to-quadruple
# its byte footprint against the cap for no filesystem-safety benefit
# (R15-UI-082).
_UNSAFE_CHARS = frozenset('/\\:*?"<>|')


class WorkspaceNameError(ValueError):
    """Raised when a workspace name is empty or too long to store."""


class WorkspaceNotFoundError(KeyError):
    """Raised when a requested workspace file does not exist."""


def _filename_stem(name: str) -> str:
    """Map any workspace name to one safe filename component.

    Path separators, Windows-reserved punctuation, control characters, NUL
    and literal ``.`` (which would otherwise let a name spell a dot-segment
    like ``..``) are percent-encoded; every other character — letters,
    digits, spaces and any other Unicode script — stays as its raw UTF-8
    bytes, so the stem never holds a path separator or a dot segment but a
    non-ASCII name isn't penalised against the byte cap below.
    """
    cleaned = name.strip()
    if not cleaned:
        raise WorkspaceNameError("A workspace name is required.")
    encoded = "".join(
        quote(ch, safe="") if ch in _UNSAFE_CHARS or ord(ch) < 0x20 or ord(ch) == 0x7F else ch
        for ch in cleaned
    )
    stem = encoded.replace(".", "%2E")
    stem_bytes = len(stem.encode("utf-8"))
    if stem_bytes > _MAX_STEM_BYTES:
        raise WorkspaceNameError(
            f"Workspace name {cleaned!r} is too long to save "
            f"({stem_bytes} bytes when encoded, max {_MAX_STEM_BYTES})."
        )
    return stem


def _path_for(name: str) -> Path:
    """Return the on-disk path for a workspace ``name``."""
    return get_workspaces_dir() / f"{_filename_stem(name)}{WORKSPACE_SUFFIX}"


def list_workspaces() -> list[str]:
    """Return the names of all saved workspaces, sorted alphabetically."""
    workspaces_dir = get_workspaces_dir()
    names = [
        unquote(path.name[: -len(WORKSPACE_SUFFIX)])
        for path in workspaces_dir.glob(f"*{WORKSPACE_SUFFIX}")
        if path.is_file()
    ]
    return sorted(names)


def save_workspace(name: str, workspace: dict[str, Any]) -> None:
    """Persist ``workspace`` as ``<name>.vysted-workspace``, overwriting any prior.

    The write is ATOMIC: the body is written to a per-writer temp file then
    ``os.replace``-d over the target. The frontend fires several debounced
    autosaves that can land concurrently (provider, model, watchlist, layout …);
    a plain ``write_text`` lets two concurrent writers interleave/truncate the
    same file into invalid JSON (a real observed corruption — ``load_workspace``
    then 500s and the session silently reverts to the default layout). A temp +
    atomic rename makes it last-writer-wins, never a torn file.

    The previous body is kept as ``<name>.vysted-workspace.bak`` (one generation,
    also written atomically) so a bad overwrite never costs the user's holdings,
    watchlist or notes (R15-LIFECYCLE-002).
    """
    path = _path_for(name)
    payload = json.dumps(workspace, indent=2)
    # Unique temp name per writer (pid+id) so two concurrent saves don't clobber
    # each other's temp; same directory so ``os.replace`` is a same-filesystem
    # atomic rename.
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{id(workspace)}.tmp")
    bak_tmp = path.with_name(f"{path.name}.{os.getpid()}.{id(workspace)}.bak.tmp")
    try:
        tmp.write_text(payload, encoding="utf-8")
        if path.is_file():
            if _read_body(path) is None:
                # Never let an unparseable file replace the last good backup.
                _quarantine(path)
            else:
                shutil.copyfile(path, bak_tmp)
                os.replace(bak_tmp, _bak_path(path))
        os.replace(tmp, path)
    finally:
        # If a rename failed (e.g. mid-shutdown), don't leak the temp files.
        for leftover in (tmp, bak_tmp):
            try:
                leftover.unlink(missing_ok=True)
            except OSError:
                pass


def _bak_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.bak")


def _read_body(path: Path) -> dict[str, Any] | None:
    """The file's JSON object, or ``None`` when it is not one (unparseable,
    undecodable, or valid JSON that is not an object)."""
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return body if isinstance(body, dict) else None


def _quarantine(path: Path) -> Path:
    """Move a corrupt file aside as ``<file>.corrupt-<unix ms>`` (kept for recovery)."""
    target = path.with_name(f"{path.name}.corrupt-{int(time.time() * 1000)}")
    os.replace(path, target)
    logger.warning("workspace file %s is corrupt; quarantined as %s", path.name, target.name)
    return target


def load_workspace(name: str) -> dict[str, Any]:
    """Return the stored JSON object for ``name``; raise if it does not exist.

    A corrupt file (truncated, externally edited, or not a JSON object) is
    quarantined as ``.corrupt-<ts>`` (never deleted) and the last good ``.bak``
    is restored in its place and served (R15-DATA-090). With no usable backup
    the workspace is reported missing, so the frontend boots the default — and
    the next save cannot copy the damaged file over the backup.
    """
    path = _path_for(name)
    if not path.is_file():
        raise WorkspaceNotFoundError(name)
    body = _read_body(path)
    if body is not None:
        return body
    _quarantine(path)
    bak = _bak_path(path)
    backup = _read_body(bak) if bak.is_file() else None
    if backup is None:
        raise WorkspaceNotFoundError(name)
    shutil.copyfile(bak, path)
    logger.warning("workspace %r restored from its backup", name)
    return backup


def delete_workspace(name: str) -> None:
    """Delete the ``<name>.vysted-workspace`` file; raise if it does not exist."""
    path = _path_for(name)
    if not path.is_file():
        raise WorkspaceNotFoundError(name)
    path.unlink()
