"""Pass B (B1) — the resolve_symbol agent tool + its catalog projection."""

from __future__ import annotations

import asyncio

from services.agent_tools import catalog
from services.agent_tools.resolve_symbol import _resolve_symbol


def test_resolve_symbol_in_catalog_and_projected() -> None:
    assert "resolve_symbol" in catalog.CAPABILITY_CATALOG
    cap = catalog.CAPABILITY_CATALOG["resolve_symbol"]
    assert cap.read_only is True
    assert cap.kind == "read_handler"
    assert "resolve_symbol" in catalog.internal_tool_ids()
    assert "resolve_symbol" in catalog.mcp_tool_ids()  # auto-projected to MCP


def test_resolve_symbol_tool_resolves_name() -> None:
    out = asyncio.run(_resolve_symbol({"query": "Tata Steel", "region": "IN"}))
    assert out["ok"] is True
    assert out["resolved"]["symbol"] == "TATASTEEL"
    assert out["resolved"]["exchange"] == "NSE"
    assert out["region"] == "IN"


def test_resolve_symbol_tool_unknown_returns_human_message(monkeypatch) -> None:  # noqa: ANN001
    from services import symbol_resolver

    monkeypatch.setattr(symbol_resolver, "_live_lookup", lambda query, region: None)
    out = asyncio.run(_resolve_symbol({"query": "zzzqqnotreal"}))
    assert out["ok"] is False
    assert "message" in out and "resolve" in out["message"].lower()


def test_resolve_symbol_tool_missing_query() -> None:
    out = asyncio.run(_resolve_symbol({}))
    assert out["ok"] is False
    assert "error" in out


def test_resolve_symbol_tool_never_blocks_the_event_loop(monkeypatch) -> None:  # noqa: ANN001
    """R15-AGENT-010: a slow resolver (a master miss falls through to a blocking
    live Search) runs on a worker thread, so a concurrent coroutine still ticks."""
    import time

    from services import symbol_resolver

    def slow_resolve(query: str, region: str) -> symbol_resolver.Resolution:
        time.sleep(0.5)
        return symbol_resolver.Resolution(query=query, best=None, candidates=[])

    monkeypatch.setattr(symbol_resolver, "resolve", slow_resolve)

    async def main() -> float:
        start = time.monotonic()

        async def tick() -> float:
            await asyncio.sleep(0.05)
            return time.monotonic() - start

        _, ticked = await asyncio.gather(_resolve_symbol({"query": "infosys"}), tick())
        return ticked

    assert asyncio.run(main()) < 0.3


def test_tool_instrument_is_the_router_payload_including_rename(monkeypatch) -> None:  # noqa: ANN001
    """R15-CODE-DATA-003: the tool and ``/resolve`` project one ``Instrument`` through
    the same payload — rename provenance and confidence rounding included."""
    from datetime import date

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from routers import resolve
    from services import nse_symbol_change

    async def _no_refresh() -> None:
        return None

    monkeypatch.setattr(nse_symbol_change, "schedule_refresh", _no_refresh)
    monkeypatch.setattr(nse_symbol_change, "_ist_today", lambda: date(2026, 7, 10))
    nse_symbol_change.set_active_map_for_tests(
        {
            "GUJGASLTD": nse_symbol_change.SymbolChange(
                "GUJGASLTD", "GUJENERGY", date(2026, 7, 1), "GUJARAT ENERGY LIMITED"
            )
        }
    )
    try:
        tool = asyncio.run(_resolve_symbol({"query": "GUJGASLTD", "region": "IN"}))["resolved"]
        app = FastAPI()
        app.include_router(resolve.router)
        routed = TestClient(app).get("/resolve", params={"q": "GUJGASLTD", "region": "IN"})
    finally:
        nse_symbol_change.reset_for_tests()
    router_payload = routed.json()["resolved"]
    assert tool["rename"]["effective_date"] == "2026-07-01"
    assert {key: router_payload[key] for key in tool} == tool
