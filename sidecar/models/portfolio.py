"""Portfolio Pydantic models.

``Position`` is the stored record (manual entry in v1.0 — broker connection is
Phase 5). The portfolio service (Teammate B, Phase 1.B) computes P&L by joining
positions against live quotes. Mirrored by hand in ``types/data.ts`` — keep in
sync (see CLAUDE.md Gotchas).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Position(BaseModel):
    """A single held position, persisted in the local SQLite database."""

    id: int | None = None
    symbol: str
    quantity: float
    cost_basis: float
    asset_class: str = "equity"
    opened_at: datetime | None = None
    note: str | None = None


class PositionInput(BaseModel):
    """Payload for creating or updating a position (no server-assigned id)."""

    symbol: str
    quantity: float
    cost_basis: float
    asset_class: str = "equity"
    opened_at: datetime | None = None
    note: str | None = None
