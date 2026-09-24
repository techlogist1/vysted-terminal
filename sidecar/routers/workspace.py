"""Workspace router — save/list/load/delete ``.vysted-workspace`` files.

Owned by Teammate D (Phase 1.B, platform). The sidecar owns workspace
persistence so the frontend never needs filesystem access; the actual file I/O
lives in ``services.workspace_store``. A workspace body is opaque JSON — the
frontend serialises the dockview layout and the modules ``enabled`` map into it
and the sidecar stores it as-is. This file is already mounted by
``app.create_app`` — only edit this file, not ``app.py``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services import workspace_store
from services.workspace_store import WorkspaceNameError, WorkspaceNotFoundError

router = APIRouter(prefix="/workspace", tags=["workspace"])


def _storage_failure(action: str, exc: OSError) -> HTTPException:
    """A disk failure (read-only dir, disk full) as a 507 naming the cause, so the
    frontend can show why nothing is being saved (R15-CODE-FRONTEND-019)."""
    return HTTPException(
        status_code=507, detail=f"Could not {action} the workspace: {exc.strerror or exc}"
    )


class SaveWorkspaceRequest(BaseModel):
    """Body for ``POST /workspace``: a name plus the opaque workspace JSON.

    ``workspace`` is free-form — the sidecar persists it without interpreting
    it. The frontend puts the dockview layout and the modules ``enabled`` map in
    there; the contract for that shape lives in ``src/lib/workspace.ts``.
    """

    name: str
    workspace: dict[str, Any] = Field(default_factory=dict)


@router.get("")
def list_workspaces() -> list[str]:
    """Return the names of every saved workspace."""
    return workspace_store.list_workspaces()


@router.get("/{name:path}")
def get_workspace(name: str) -> dict[str, Any]:
    """Return the stored JSON for one workspace."""
    try:
        return workspace_store.load_workspace(name)
    except OSError as exc:
        raise _storage_failure("read", exc) from exc
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Workspace {name!r} not found.") from exc
    except WorkspaceNameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("", status_code=200)
def save_workspace(request: SaveWorkspaceRequest) -> dict[str, str]:
    """Persist a workspace, overwriting any existing one with the same name."""
    try:
        workspace_store.save_workspace(request.name, request.workspace)
    except OSError as exc:
        raise _storage_failure("write", exc) from exc
    except WorkspaceNameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "saved", "name": request.name.strip()}


@router.delete("/{name:path}", status_code=204)
def delete_workspace(name: str) -> None:
    """Delete a saved workspace."""
    try:
        workspace_store.delete_workspace(name)
    except OSError as exc:
        raise _storage_failure("delete", exc) from exc
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Workspace {name!r} not found.") from exc
    except WorkspaceNameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
