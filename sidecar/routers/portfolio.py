"""Portfolio router — the legacy positions ledger (``services.portfolio_db``).

Holdings are owned by the workspace blob (the frontend portfolios store), for
the panel and the agent alike. The app reads ``GET /portfolio/positions`` once,
to import holdings saved before they moved into the blob (R15-LIFECYCLE-009);
no app surface writes this ledger, so the router is GET-only (R15-CODE-PLATFORM-021).
This file is mounted by ``app.create_app``.
"""

from __future__ import annotations

from fastapi import APIRouter

from models.portfolio import Position
from services import portfolio_db

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/positions")
def list_positions() -> list[Position]:
    """Return every stored position."""
    return portfolio_db.list_positions()
