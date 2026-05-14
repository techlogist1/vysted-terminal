"""Portfolio router — manual positions CRUD backed by local SQLite.

Owned by Teammate B (Phase 1.B, tabular panels). Positions are entered manually
in v1.0 — broker connection is Phase 5. Persistence lives in
``services.portfolio_db`` (a SQLite database under ``config.get_data_dir()``);
the portfolio panel computes P&L, weight, and risk metrics in the frontend by
joining these stored positions against live quotes. This file is already
mounted by ``app.create_app`` — only edit this file, not ``app.py``.

The ``_status`` probe is retained alongside the real CRUD endpoints so the
shared ``test_app.py`` mount check (owned by the lead) stays green until every
Phase 1.B teammate's stub is reconciled at merge — a Tier-3 call.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from models.portfolio import Position, PositionInput
from services import portfolio_db

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/_status")
def get_status() -> dict[str, str]:
    """Liveness probe retained for the shared router-mount test."""
    return {"status": "stub", "router": "portfolio", "owner": "teammate-b"}


@router.get("/positions")
def list_positions() -> list[Position]:
    """Return every stored position."""
    return portfolio_db.list_positions()


@router.post("/positions", status_code=status.HTTP_201_CREATED)
def create_position(payload: PositionInput) -> Position:
    """Create a new manually entered position."""
    return portfolio_db.create_position(payload)


@router.put("/positions/{position_id}")
def update_position(position_id: int, payload: PositionInput) -> Position:
    """Overwrite an existing position; 404 if the id is unknown."""
    updated = portfolio_db.update_position(position_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"position {position_id} not found")
    return updated


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_position(position_id: int) -> Response:
    """Delete a position by id; 404 if the id is unknown."""
    if not portfolio_db.delete_position(position_id):
        raise HTTPException(status_code=404, detail=f"position {position_id} not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
