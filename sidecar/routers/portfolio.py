"""Portfolio router — STUB owned by Teammate B (Phase 1.B, tabular panels).

Teammate B replaces the ``_status`` placeholder with positions CRUD backed by a
local SQLite database under ``config.get_data_dir()`` (the ``Position`` /
``PositionInput`` models are already defined in ``models/portfolio.py``). The
portfolio panel computes P&L by joining positions against live quotes. This file
is already mounted by ``app.create_app`` — only edit this file, not ``app.py``.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/_status")
def status() -> dict[str, str]:
    """Placeholder so the router mounts cleanly; Teammate B replaces this."""
    return {"status": "stub", "router": "portfolio", "owner": "teammate-b"}
