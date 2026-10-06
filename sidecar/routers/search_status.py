"""Search tier status router — the honest per-engine T1 surface (R7 Component 1).

``GET /search/status`` reports the keyless tier's per-engine circuit-breaker
state and cooldown remaining, so the UI can render "DuckDuckGo cooling down
(24s)" while Brave/Mojeek keep serving — instead of a fake global "web search
is down" banner the moment one engine throttles.

Read-only, keyless, no credentials involved.
"""

from __future__ import annotations

from fastapi import APIRouter

from services.search.keyless import tier_status

router = APIRouter(tags=["search"])


@router.get("/search/status")
def search_status() -> dict[str, object]:
    """The live T1 keyless-tier status: per-engine breaker state + cooldowns."""
    return tier_status()
