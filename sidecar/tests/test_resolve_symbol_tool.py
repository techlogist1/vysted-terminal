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
