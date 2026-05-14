"""Indicators router — STUB owned by Teammate A (Phase 1.B, chart panel).

Teammate A replaces the ``_status`` placeholder with technical-indicator
computation endpoints consumed by the chart panel. Compute indicators
server-side (numpy/pandas already available via yfinance) and return them in a
shape the chart panel can overlay. This file is already mounted by
``app.create_app`` — only edit this file, not ``app.py``.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("/_status")
def status() -> dict[str, str]:
    """Placeholder so the router mounts cleanly; Teammate A replaces this."""
    return {"status": "stub", "router": "indicators", "owner": "teammate-a"}
