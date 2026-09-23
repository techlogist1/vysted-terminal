"""Portfolio router — the legacy positions ledger (``services.portfolio_db``).

Holdings are owned by the workspace blob (the frontend portfolios store), for
the panel and the agent alike. The app reads ``GET /portfolio/positions`` once,
to import holdings saved before they moved into the blob (R15-LIFECYCLE-009);
no app surface writes this ledger. This file is mounted by ``app.create_app``.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from models.portfolio import Position, PositionInput
from services import portfolio_db

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


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
