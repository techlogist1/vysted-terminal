"""News Pydantic model.

The sentiment fields are populated by the news service (Teammate C, Phase 1.B);
the provider layer in Phase 1.A leaves them ``None``. Mirrored by hand in
``types/data.ts`` — keep in sync (see CLAUDE.md Gotchas).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class NewsItem(BaseModel):
    """A single news article, optionally tagged with symbols and sentiment."""

    id: str
    title: str
    summary: str | None = None
    url: str
    source: str
    published_at: datetime
    symbols: list[str] = []
    sentiment: float | None = None
    sentiment_label: str | None = None
    provider: str
