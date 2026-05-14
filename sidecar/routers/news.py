"""News router — STUB owned by Teammate C (Phase 1.B, news feed).

Teammate C replaces the ``_status`` placeholder with news endpoints: fetch from
RSS + NewsAPI (key optional), score each item with a lexicon-based sentiment
service (vaderSentiment is in requirements.txt), and filter by watchlist
symbols. The ``NewsItem`` model — including the ``sentiment`` /
``sentiment_label`` fields — is already defined in ``models/news.py``. This file
is already mounted by ``app.create_app`` — only edit this file, not ``app.py``.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/_status")
def status() -> dict[str, str]:
    """Placeholder so the router mounts cleanly; Teammate C replaces this."""
    return {"status": "stub", "router": "news", "owner": "teammate-c"}
