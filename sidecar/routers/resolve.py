"""Resolve router — read-only, locale-aware ticker/name resolution (FR-101).

Backs the chat ``@TICKER`` mention surface: free text or a bare ticker resolves
to one concrete instrument (``symbol`` / ``exchange`` / ``region`` /
``asset_class`` / ``yahoo_symbol``) plus ranked candidates, scored locale-first.
The frontend mention picker calls ``GET /resolve?q=GOLDBEES`` (with the active
region riding the ``X-Vysted-Region`` header → ``config.get_region()``, or an
explicit ``&region=`` override) and renders the resolved instrument inline.

Read-only by construction: GET only, no mutation, no credentials. A blank or
garbage query degrades to ``{"ok": false, ...}`` with HTTP 200 (never a 500), so
the picker can show an honest "no match" without error-handling noise.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query

from config import get_region, normalize_region
from services import nse_symbol_change, resolution_policy, symbol_resolver

router = APIRouter(prefix="/resolve", tags=["resolve"])


def _instrument_payload(instrument: symbol_resolver.Instrument) -> dict[str, object]:
    """Project an :class:`Instrument` to the wire shape the picker consumes."""
    payload: dict[str, object] = {
        "symbol": instrument.symbol,
        "name": instrument.name,
        "exchange": instrument.exchange,
        "region": instrument.region,
        "asset_class": instrument.asset_class,
        "yahoo_symbol": instrument.yahoo_symbol,
        "confidence": round(instrument.score, 4),
        # R13 additive identity enrichment — read-only ISIN / scrip / industry
        # join. Null when the bundled data does not carry it (US names, an
        # uncovered micro-cap), never fabricated.
        "isin": instrument.isin,
        "bse_code": instrument.bse_code,
        "industry": instrument.industry,
        "former_name": instrument.former_name,
    }
    # R12 (D66): a symbol answered as its CURRENT form carries explicit rename
    # provenance — the picker can badge "renamed from …", never a silent swap.
    if instrument.rename is not None:
        payload["rename"] = {
            "renamed_from": instrument.rename.renamed_from,
            "renamed_to": instrument.rename.renamed_to,
            "effective_date": instrument.rename.effective_date,
            "note": instrument.rename.note,
        }
    return payload


@router.get("")
async def resolve_symbol(
    q: str = Query("", description="Free-text name or ticker to resolve."),
    region: str | None = Query(
        None,
        description="Override region (US | IN | GLOBAL); defaults to the request region.",
    ),
) -> dict[str, object]:
    """Resolve ``q`` to one instrument + ranked candidates, locale-aware.

    ``region`` defaults to the active request region (``config.get_region()``,
    set from the ``X-Vysted-Region`` header); an explicit query param overrides
    it. An empty/garbage query returns ``ok: false`` with HTTP 200 — never a 500.
    The resolution runs on a worker thread: the bundled-master path is a pure
    dict/fuzzy lookup, but a miss can fall through to a guarded (blocking)
    ``yfinance.Search``, which must not block the event loop.
    """
    active_region = normalize_region(region) if region else get_region()

    query = q.strip()
    if not query:
        return {
            "ok": False,
            "query": q,
            "region": active_region,
            "message": "Empty query — nothing to resolve.",
            "resolved": None,
            "needs_disambiguation": False,
            "candidates": [],
        }

    # Self-activate the rename lane: a cheap, once-per-day, non-blocking refresh
    # of the symbol-change map (no network on the hot path). See the module for
    # the recommended lifespan hook that also covers the agent/search paths.
    await nse_symbol_change.schedule_refresh()

    resolution = await asyncio.to_thread(symbol_resolver.resolve, query, active_region)

    # ONE policy everywhere (R10, D37): the mention picker honors the SAME
    # acceptance decision as the research target binding and every agent tool —
    # an ambiguous marquee name ("Tata") offers a chooser, never a silent guess,
    # and a substring/fuzzy hit is offered for disambiguation, never bound.
    decision = resolution_policy.decide(resolution)

    if decision.outcome == "unresolved":
        return {
            "ok": False,
            "query": query,
            "region": active_region,
            "message": f"No instrument matched {query!r}.",
            "resolved": None,
            "needs_disambiguation": False,
            "candidates": [_instrument_payload(c) for c in decision.candidates],
        }

    return {
        "ok": True,
        "query": query,
        "region": active_region,
        "resolved": (
            _instrument_payload(decision.instrument)
            if decision.outcome == "bound" and decision.instrument is not None
            else None
        ),
        "needs_disambiguation": decision.outcome == "disambiguate",
        "candidates": [_instrument_payload(c) for c in decision.candidates],
    }


@router.get("/autocomplete")
async def autocomplete_symbols(
    q: str = Query("", description="Partial name or ticker to autocomplete."),
    region: str | None = Query(None, description="Override region (US | IN | GLOBAL)."),
    limit: int = Query(8, ge=1, le=20, description="Max candidates to return."),
) -> dict[str, object]:
    """On-keystroke autocomplete: a fast, masters-only, network-free candidate
    list (ticker-prefix or name match, locale-ranked). Distinct from ``/resolve``
    — no fuzzy/live-lookup fallback, so it stays keystroke-fast. Empty query → an
    empty list (HTTP 200), never a 500."""
    active_region = normalize_region(region) if region else get_region()
    query = q.strip()
    if not query:
        return {"query": q, "region": active_region, "candidates": []}
    await nse_symbol_change.schedule_refresh()
    candidates = await asyncio.to_thread(symbol_resolver.autocomplete, query, active_region, limit)
    return {
        "query": query,
        "region": active_region,
        "candidates": [_instrument_payload(c) for c in candidates],
    }
