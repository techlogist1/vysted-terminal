"""Portfolio Pydantic models.

``Position`` is the stored record (manual entry in v1.0 — broker connection is
Phase 5). The portfolio service (Teammate B, Phase 1.B) computes P&L by joining
positions against live quotes. Mirrored by hand in ``types/data.ts`` — keep in
sync (see CLAUDE.md Gotchas).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


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
    # gt=0 rejects zero and negative quantities; le=1e12 rejects absurd inputs
    # (1e15 shares is ~100x the entire US equity float — no legitimate position
    # could reach it; cap chosen to be defensible without constraining any real
    # use-case including large-lot institutional or crypto fractional qty).
    quantity: float = Field(..., gt=0, le=1e12)
    # ge=0 rejects negative cost basis (economically meaningless for a long
    # position); no upper cap — zero-cost (e.g. vested shares) is valid.
    cost_basis: float = Field(..., ge=0)
    asset_class: str = "equity"
    opened_at: datetime | None = None
    note: str | None = None
