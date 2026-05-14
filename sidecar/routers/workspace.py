"""Workspace router — STUB owned by Teammate D (Phase 1.B, platform).

Teammate D replaces the ``_status`` placeholder with save/list/load/delete
endpoints for ``.vysted-workspace`` JSON files under
``config.get_workspaces_dir()``. The sidecar owns workspace persistence so the
frontend never needs filesystem access. This file is already mounted by
``app.create_app`` — only edit this file, not ``app.py``.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("/_status")
def status() -> dict[str, str]:
    """Placeholder so the router mounts cleanly; Teammate D replaces this."""
    return {"status": "stub", "router": "workspace", "owner": "teammate-d"}
