"""Tests for the read-only /resolve router (FR-101, SC-023).

The route backs the chat ``@TICKER`` mention surface: a query resolves to one
concrete instrument + ranked candidates, locale-aware. These tests assert the
wire shape, locale routing (IN vs US), and the graceful "no match" / empty-query
degrade (``ok: false`` with HTTP 200, never a 500).
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import _RegionMiddleware
from routers import resolve
from services import symbol_resolver


@pytest.fixture
def client() -> TestClient:
    """A TestClient over a minimal app: just the resolve router + region MW.

    Self-contained so the suite passes before the lead registers the router in
    ``app.py``. ``_RegionMiddleware`` is the same one the production app mounts,
    so the ``X-Vysted-Region`` → ``config.get_region()`` path is genuinely
    exercised.
    """
    app = FastAPI()
    app.include_router(resolve.router)
    app.add_middleware(_RegionMiddleware)
    return TestClient(app)


def test_resolve_goldbees_in_locale(client: TestClient) -> None:
    # GOLDBEES is an NSE-only gold ETF — an explicit IN region resolves it on NSE.
    resp = client.get("/resolve", params={"q": "GOLDBEES", "region": "IN"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["region"] == "IN"
    resolved = body["resolved"]
    assert resolved["symbol"] == "GOLDBEES"
    assert resolved["exchange"] == "NSE"
    assert resolved["region"] == "IN"
    assert resolved["asset_class"] == "etf"
    assert resolved["yahoo_symbol"] == "GOLDBEES.NS"
    assert 0.0 <= resolved["confidence"] <= 1.0
    assert body["needs_disambiguation"] is False
    assert len(body["candidates"]) >= 1


def test_resolve_aapl_defaults_to_us(client: TestClient) -> None:
    # No region param + no header → request region defaults to US; AAPL resolves
    # to the US listing.
    resp = client.get("/resolve", params={"q": "AAPL"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["region"] == "US"
    resolved = body["resolved"]
    assert resolved["symbol"] == "AAPL"
    assert resolved["exchange"] == "US"
    assert resolved["region"] == "US"
    assert resolved["yahoo_symbol"] == "AAPL"


def test_resolve_honours_region_header(client: TestClient) -> None:
    # The active region rides X-Vysted-Region; the route echoes it back.
    resp = client.get("/resolve", params={"q": "AAPL"}, headers={"X-Vysted-Region": "IN"})
    assert resp.status_code == 200
    assert resp.json()["region"] == "IN"


def test_resolve_query_param_overrides_header(client: TestClient) -> None:
    resp = client.get(
        "/resolve",
        params={"q": "AAPL", "region": "US"},
        headers={"X-Vysted-Region": "IN"},
    )
    assert resp.status_code == 200
    assert resp.json()["region"] == "US"


def test_resolve_empty_query_is_ok_false_not_500(client: TestClient) -> None:
    resp = client.get("/resolve", params={"q": ""})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["resolved"] is None
    assert body["candidates"] == []
    assert isinstance(body["message"], str) and body["message"]


def test_resolve_missing_query_param_is_ok_false(client: TestClient) -> None:
    # ``q`` defaults to "" so an omitted param degrades, not 422.
    resp = client.get("/resolve")
    assert resp.status_code == 200
    assert resp.json()["ok"] is False


def test_resolve_garbage_is_ok_false_not_500(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force the live-lookup fallback to miss so the test is deterministic and
    # never touches the network: a true no-match degrades to ok:false / HTTP 200.
    monkeypatch.setattr(symbol_resolver, "_live_lookup", lambda *_a, **_k: None)
    resp = client.get("/resolve", params={"q": "zzzzqqqxxx123notathing", "region": "US"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["resolved"] is None
    assert body["needs_disambiguation"] is False
    assert body["candidates"] == []


def test_resolve_normalizes_bad_region_to_us(client: TestClient) -> None:
    # A garbage region override must never break the request — it normalizes.
    resp = client.get("/resolve", params={"q": "AAPL", "region": "nonsense"})
    assert resp.status_code == 200
    assert resp.json()["region"] == "US"


def test_resolve_is_read_only_get(client: TestClient) -> None:
    # The mention surface is read-only: the route accepts GET and rejects POST.
    assert client.post("/resolve", params={"q": "AAPL"}).status_code == 405


def test_resolve_iconikspev_consistent_bse_identity(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R7 Component 4 acceptance — the live defect was exchange 'NSE' with
    yahoo_symbol 'ICONIKSPEV.BO' at confidence 0.6 (a live-lookup contradiction).
    With the regenerated BSE master the route answers deterministically: a
    consistent BSE identity at confidence 1.0, masters-only (no network)."""
    monkeypatch.setattr(
        symbol_resolver,
        "_live_lookup",
        lambda *_a, **_k: pytest.fail("live lookup fired for a bundled-master symbol"),
    )
    resp = client.get("/resolve", params={"q": "ICONIKSPEV", "region": "IN"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    resolved = body["resolved"]
    assert resolved["symbol"] == "ICONIKSPEV"
    assert resolved["exchange"] == "BSE"
    assert resolved["region"] == "IN"
    assert resolved["yahoo_symbol"] == "ICONIKSPEV.BO"
    assert resolved["confidence"] == 1.0
    assert body["needs_disambiguation"] is False
    # Wire-level hygiene: every candidate's exchange agrees with its suffix.
    for c in body["candidates"]:
        suffix = {"NSE": ".NS", "BSE": ".BO", "US": ""}[c["exchange"]]
        assert c["yahoo_symbol"] == c["symbol"] + suffix


def test_resolve_dual_listed_carries_both_exchanges(client: TestClient) -> None:
    """A dual-listed name resolves NSE-first but the BSE row rides the candidate
    list (retained for BSE-only fundamentals/announcements)."""
    resp = client.get("/resolve", params={"q": "RELIANCE", "region": "IN"})
    body = resp.json()
    assert body["ok"] is True
    assert body["resolved"]["exchange"] == "NSE"
    assert body["resolved"]["yahoo_symbol"] == "RELIANCE.NS"
    exchanges = [c["exchange"] for c in body["candidates"]]
    assert "NSE" in exchanges and "BSE" in exchanges
    assert exchanges.index("NSE") < exchanges.index("BSE")


def test_autocomplete_route_mobile_first_hit_is_route(client: TestClient) -> None:
    """Autocomplete acceptance: 'Route Mobile' still → ROUTE (NSE canonical row)
    with the full BSE master in the masters-only scan."""
    resp = client.get("/resolve/autocomplete", params={"q": "Route Mobile", "region": "IN"})
    assert resp.status_code == 200
    cands = resp.json()["candidates"]
    assert cands and cands[0]["symbol"] == "ROUTE"
    assert cands[0]["exchange"] == "NSE"
