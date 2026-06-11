"""Tests for the R10 India screener track (E4 dead).

Covers: the three full-market universes (counts / suffixes / dedupe / NSE
preference), ``india_symbol_meta``, the ``resolve_universe`` branches, the
bundled sector map + the regenerate script's hand mapping, the cheap-criteria
prune extraction (OR trees never prune), the wall budget (expiry → honest
partial with ``budget_exhausted`` skips and the ledger invariant),
cancellation (finalize, don't vanish), the sharesOutstanding v7 mapping, and
the ``POST /screener/run/stream`` SSE frames via the httpx ASGI transport.

No live network: the v7 endpoint rides the ``reset_for_tests(MockTransport)``
seam; the registry is monkeypatched.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app import create_app
from models.fundamentals import Fundamentals
from models.market import Quote
from models.screener import (
    CriterionGroup,
    NumericThresholdCriterion,
    ScreenerRequest,
    ScreenerUniverse,
    StringEqCriterion,
)
from services import data_cache, fundamentals_store, screener, screener_universe_india
from services import yahoo_batch_provider as yb


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path) -> None:
    data_cache.reset_for_tests(tmp_path / "india_test_cache.db")
    fundamentals_store.reset_for_tests(tmp_path / "fundamentals_test.db")
    yb.reset_for_tests()
    yield
    data_cache.reset_for_tests(None)
    fundamentals_store.reset_for_tests(None)
    yb.reset_for_tests()


# ---------------------------------------------------------------------------
# Universes — counts / suffixes / dedupe
# ---------------------------------------------------------------------------


def test_nse_all_every_master_row_suffixed_and_unique() -> None:
    universe = screener_universe_india.load_india_universe("nse-all")
    assert universe.id == "nse-all"
    assert universe.asset_class == "equity"
    assert len(universe.symbols) > 2500  # ~2,675 in the bundled master
    assert all(s.endswith(".NS") for s in universe.symbols)
    assert len(set(universe.symbols)) == len(universe.symbols)
    assert "RELIANCE.NS" in universe.symbols


def test_bse_all_active_scrips_suffixed_and_unique() -> None:
    universe = screener_universe_india.load_india_universe("bse-all")
    assert universe.id == "bse-all"
    assert len(universe.symbols) > 4500  # ~4,873 Active in the bundled master
    assert all(s.endswith(".BO") for s in universe.symbols)
    assert len(set(universe.symbols)) == len(universe.symbols)
    assert "RELIANCE.BO" in universe.symbols


def test_india_all_union_prefers_nse_listing() -> None:
    nse = screener_universe_india.load_india_universe("nse-all")
    bse = screener_universe_india.load_india_universe("bse-all")
    union = screener_universe_india.load_india_universe("india-all")
    assert len(union.symbols) > len(nse.symbols)
    assert len(set(union.symbols)) == len(union.symbols)
    # Dual-listings screen once, on NSE.
    assert "RELIANCE.NS" in union.symbols
    assert "RELIANCE.BO" not in union.symbols
    # No base ticker appears under both suffixes.
    ns_bases = {s[:-3] for s in union.symbols if s.endswith(".NS")}
    bo_bases = {s[:-3] for s in union.symbols if s.endswith(".BO")}
    assert not (ns_bases & bo_bases)
    # Sanity: the union is NSE + the BSE-only tail.
    bse_only = {s[:-3] for s in bse.symbols} - {s[:-3] for s in nse.symbols}
    assert len(union.symbols) == len(nse.symbols) + len(bse_only)


@pytest.mark.asyncio
async def test_resolve_universe_india_branches() -> None:
    for universe_id in ("nse-all", "bse-all", "india-all"):
        universe = await screener.resolve_universe(universe_id)
        assert universe.id == universe_id
        assert universe.symbols


def test_india_symbol_meta_joins_masters() -> None:
    rel = screener_universe_india.india_symbol_meta("RELIANCE.NS")
    assert rel is not None
    assert rel["exchange"] == "NSE"
    assert rel["scrip_code"] == "500325"  # joined from the BSE master
    assert rel["isin"] == "INE002A01018"
    rel_bo = screener_universe_india.india_symbol_meta("RELIANCE.BO")
    assert rel_bo is not None
    assert rel_bo["exchange"] == "BSE"
    assert rel_bo["group"] == "A"
    # Bare symbol prefers the NSE listing, mirroring india-all.
    bare = screener_universe_india.india_symbol_meta("RELIANCE")
    assert bare is not None and bare["exchange"] == "NSE"
    assert screener_universe_india.india_symbol_meta("NOTASYMBOL123") is None


# ---------------------------------------------------------------------------
# Sector map — bundled JSON + the regenerate script's hand table
# ---------------------------------------------------------------------------


def test_sector_map_bundled_with_honest_coverage() -> None:
    coverage = screener_universe_india.sector_map_coverage()
    assert coverage["records"] > 4000
    assert coverage["with_sector"] > 500
    assert coverage["with_shares"] > 4000
    seed = screener_universe_india.sector_seed_for("RELIANCE.NS")
    assert seed is not None
    assert seed["sector"] == "Energy"
    assert seed["sector_source"] == "bse"
    assert seed["isin"] == "INE002A01018"
    assert seed["shares_outstanding"] and seed["shares_outstanding"] > 1e9


def test_industry_hand_table_covers_live_vocabulary() -> None:
    from services.resolver_masters.regenerate_india_sectors import (
        _INDUSTRY_NEW_TO_YAHOO,
        map_industry_to_sector,
    )

    yahoo_11 = {
        "Technology",
        "Financial Services",
        "Healthcare",
        "Consumer Cyclical",
        "Consumer Defensive",
        "Industrials",
        "Basic Materials",
        "Energy",
        "Utilities",
        "Communication Services",
        "Real Estate",
    }
    for industry, sector in _INDUSTRY_NEW_TO_YAHOO.items():
        assert sector is None or sector in yahoo_11, industry
    assert map_industry_to_sector("Information Technology") == "Technology"
    assert map_industry_to_sector("IT - Software") == "Technology"  # legacy string
    assert map_industry_to_sector("Diversified") is None
    assert map_industry_to_sector("Some Unknown Industry") is None  # never a guess
    assert map_industry_to_sector(None) is None


# ---------------------------------------------------------------------------
# Cheap-prune extraction — OR trees never prune
# ---------------------------------------------------------------------------


def test_cheap_prune_criteria_flat_list_keeps_only_cheap() -> None:
    cheap = screener._cheap_prune_criteria(
        [
            StringEqCriterion(field="sector", operator="eq", value="Technology"),
            NumericThresholdCriterion(field="market_cap", operator="gt", value=1e9),
            NumericThresholdCriterion(field="roe", operator="gt", value=0.2),  # info tier
        ],
        None,
    )
    fields = [c.field for c in cheap]
    assert fields == ["sector", "market_cap"]


def test_cheap_prune_criteria_or_tree_never_prunes() -> None:
    group = CriterionGroup(
        combinator="or",
        criteria=[
            StringEqCriterion(field="sector", operator="eq", value="Technology"),
            NumericThresholdCriterion(field="roe", operator="gt", value=0.2),
        ],
    )
    assert screener._cheap_prune_criteria([], group) == []


def test_cheap_prune_criteria_recurses_nested_and_only() -> None:
    group = CriterionGroup(
        combinator="and",
        criteria=[
            StringEqCriterion(field="sector", operator="eq", value="Technology"),
            CriterionGroup(
                combinator="and",
                criteria=[NumericThresholdCriterion(field="pe_ratio", operator="lt", value=30.0)],
            ),
            CriterionGroup(
                combinator="or",
                criteria=[NumericThresholdCriterion(field="market_cap", operator="gt", value=1e9)],
            ),
        ],
    )
    fields = [c.field for c in screener._cheap_prune_criteria([], group)]
    # The OR subtree contributes nothing; the nested AND leaf does.
    assert fields == ["sector", "pe_ratio"]


def test_group_supersedes_flat_criteria_for_pruning() -> None:
    # The flat list is INACTIVE when a group is present — pruning on it could
    # narrow incorrectly.
    flat = [StringEqCriterion(field="sector", operator="eq", value="Technology")]
    group = CriterionGroup(combinator="or", criteria=[])
    assert screener._cheap_prune_criteria(flat, group) == []


# ---------------------------------------------------------------------------
# Engine-level prune soundness — prefiltered runs only WIDEN
# ---------------------------------------------------------------------------


def _fake_universe(universe_id: str, symbols: list[str]):
    async def _resolve(uid, custom_symbols=None):  # noqa: ANN001, ARG001
        return ScreenerUniverse(
            id=universe_id, label=universe_id, symbols=symbols, asset_class="equity"
        )

    return _resolve


def _v7_row(symbol: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "symbol": symbol,
        "longName": f"{symbol} Ltd",
        "regularMarketPrice": 1000.0,
        "regularMarketChange": 5.0,
        "regularMarketChangePercent": 0.5,
        "regularMarketVolume": 500_000,
        "currency": "INR",
        "marketCap": 1e12,
        "trailingPE": 20.0,
        "sharesOutstanding": 1e9,
    }
    row.update(overrides)
    return row


def _install_v7(rows_by_symbol: dict[str, dict[str, object]]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="crumb")
        if request.url.path.endswith("/v7/finance/quote"):
            requested = (request.url.params.get("symbols") or "").split(",")
            result = [rows_by_symbol[s] for s in requested if s in rows_by_symbol]
            return httpx.Response(200, json={"quoteResponse": {"result": result}})
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_seeded_sector_prefilter_prunes_before_any_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A seeded sector lets the prefilter prune; pruned symbols count as
    evaluated (they failed a real criterion), never as skips."""
    symbols = ["TECH.NS", "BANK.NS"]
    monkeypatch.setattr(screener, "resolve_universe", _fake_universe("nse-all", symbols))
    await fundamentals_store.seed_universe(
        [
            {"symbol": "TECH.NS", "sector": "Technology", "sector_source": "seed"},
            {"symbol": "BANK.NS", "sector": "Financial Services", "sector_source": "seed"},
        ]
    )
    swept: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="crumb")
        if request.url.path.endswith("/v7/finance/quote"):
            requested = (request.url.params.get("symbols") or "").split(",")
            swept.extend(requested)
            return httpx.Response(
                200, json={"quoteResponse": {"result": [_v7_row(s) for s in requested]}}
            )
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))

    request = ScreenerRequest(
        universe="nse-all",
        criteria=[StringEqCriterion(field="sector", operator="eq", value="Technology")],
        limit=100,
    )
    result = await screener.run_screener(request)
    assert [r.symbol for r in result.rows] == ["TECH.NS"]
    # BANK.NS was pruned by its fresh seeded sector — never fetched.
    assert "BANK.NS" not in swept
    # Pruned-by-criterion is evaluated-as-failed, not a skip.
    assert result.evaluated_count == 2
    assert result.skipped_count == 0
    assert result.partial is False
    assert result.coverage == "screened 2 of 2 — 0 unavailable"
    assert result.freshness and "quotes_as_of" in result.freshness


@pytest.mark.asyncio
async def test_prune_never_narrows_null_sector_still_screened(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A symbol with NO seeded sector must NOT be pruned by a sector criterion
    — enrichment resolves it (prune may only widen)."""
    symbols = ["UNSEEDED.NS"]
    monkeypatch.setattr(screener, "resolve_universe", _fake_universe("nse-all", symbols))
    _install_v7({s: _v7_row(s) for s in symbols})

    async def fake_fund(symbol: str) -> Fundamentals:
        return Fundamentals(symbol=symbol, sector="Technology", provider="yf")

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_fund)

    request = ScreenerRequest(
        universe="nse-all",
        criteria=[StringEqCriterion(field="sector", operator="eq", value="Technology")],
        limit=100,
    )
    result = await screener.run_screener(request)
    assert [r.symbol for r in result.rows] == ["UNSEEDED.NS"]
    assert result.skipped_count == 0


# ---------------------------------------------------------------------------
# Wall budget — expiry → honest partial; cancellation → finalize
# ---------------------------------------------------------------------------


class _HangingTransport(httpx.AsyncBaseTransport):
    """A v7 endpoint that never answers inside the test's wall budget."""

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="crumb")
        await asyncio.sleep(30.0)
        return httpx.Response(200, json={"quoteResponse": {"result": []}})


@pytest.mark.asyncio
async def test_wall_expiry_finalizes_partial_with_ledger_invariant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    symbols = [f"S{i}.NS" for i in range(5)]
    monkeypatch.setattr(screener, "resolve_universe", _fake_universe("nse-all", symbols))
    yb.reset_for_tests(_HangingTransport())

    request = ScreenerRequest(universe="nse-all", criteria=[], limit=100)
    result = await screener.run_screener(request, wall_budget_s=0.3)
    assert result.partial is True
    assert result.rows == []
    assert result.evaluated_count == 0
    # SC-034 invariant holds on partials too.
    assert result.skipped_count == len(result.skip_details) == 5
    assert {d.reason for d in result.skip_details} == {"budget_exhausted"}
    assert result.coverage == "screened 0 of 5 — 5 unavailable"
    # The wall actually bounded the run (no 30 s hang).
    assert result.duration_ms < 10_000


@pytest.mark.asyncio
async def test_wall_expiry_keeps_completed_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    """A sweep cut mid-flight keeps every completed chunk — evaluated rows +
    budget_exhausted skips for the rest."""
    fast = [f"F{i}.NS" for i in range(3)]
    slow = [f"X{i}.NS" for i in range(3)]
    monkeypatch.setattr(screener, "resolve_universe", _fake_universe("nse-all", fast + slow))
    # Pre-warm the fast symbols so only the slow ones need the (hanging) sweep.
    for sym in fast:
        await fundamentals_store.upsert_v7(
            sym,
            Fundamentals(symbol=sym, market_cap=1e12, pe_ratio=10.0, provider="t"),
            Quote(
                symbol=sym,
                price=100.0,
                change=0.0,
                change_percent=0.0,
                volume=1.0,
                currency="INR",
                timestamp=datetime.now(tz=UTC),
                provider="t",
            ),
        )
    yb.reset_for_tests(_HangingTransport())

    request = ScreenerRequest(universe="nse-all", criteria=[], limit=100)
    result = await screener.run_screener(request, wall_budget_s=0.3)
    assert result.partial is True
    assert {r.symbol for r in result.rows} == set(fast)
    assert result.evaluated_count == 3
    assert result.skipped_count == len(result.skip_details) == 3
    assert {d.symbol for d in result.skip_details} == set(slow)
    assert {d.reason for d in result.skip_details} == {"budget_exhausted"}
    assert result.coverage == "screened 3 of 6 — 3 unavailable"


@pytest.mark.asyncio
async def test_cancellation_finalizes_partial_instead_of_vanishing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    symbols = [f"S{i}.NS" for i in range(4)]
    monkeypatch.setattr(screener, "resolve_universe", _fake_universe("nse-all", symbols))
    yb.reset_for_tests(_HangingTransport())

    request = ScreenerRequest(universe="nse-all", criteria=[], limit=100)
    task = asyncio.create_task(screener.run_screener(request))
    await asyncio.sleep(0.1)
    task.cancel()
    result = await task  # the engine finalizes — no CancelledError escapes
    assert result.partial is True
    assert result.skipped_count == len(result.skip_details) == 4
    assert {d.reason for d in result.skip_details} == {"budget_exhausted"}


@pytest.mark.asyncio
async def test_progress_callback_fires_per_phase(monkeypatch: pytest.MonkeyPatch) -> None:
    symbols = ["AAA.NS", "BBB.NS"]
    monkeypatch.setattr(screener, "resolve_universe", _fake_universe("nse-all", symbols))
    _install_v7({s: _v7_row(s) for s in symbols})

    frames: list[tuple[str, int, int, str]] = []

    def on_progress(phase: str, done: int, total: int, detail: str) -> None:
        frames.append((phase, done, total, detail))

    request = ScreenerRequest(universe="nse-all", criteria=[], limit=100)
    result = await screener.run_screener(request, on_progress=on_progress)
    assert result.result_count == 2
    phases = [f[0] for f in frames]
    assert phases[0] == "universe"
    assert "sweep" in phases
    assert phases[-1] == "evaluate"
    sweep = next(f for f in frames if f[0] == "sweep")
    assert "sweeping quotes" in sweep[3]


@pytest.mark.asyncio
async def test_agent_step_sink_receives_progress_frames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inside an agent tool dispatch the engine bridges progress to the step
    sink so chat renders a live 'sweeping quotes …' trace (the screener_run
    seam — no tool-code change needed)."""
    import config

    symbols = ["AAA.NS", "BBB.NS"]
    monkeypatch.setattr(screener, "resolve_universe", _fake_universe("nse-all", symbols))
    _install_v7({s: _v7_row(s) for s in symbols})

    steps: list[object] = []
    token = config.set_step_sink(steps.append)
    try:
        request = ScreenerRequest(universe="nse-all", criteria=[], limit=100)
        result = await screener.run_screener(request)
    finally:
        config.reset_step_sink(token)
    assert result.result_count == 2
    details = [getattr(s, "detail", "") for s in steps]
    assert any("sweeping quotes" in d for d in details)
    assert all(getattr(s, "kind", "") == "tool" for s in steps)


def test_universe_route_resolves_india_ids(client) -> None:  # noqa: ANN001
    response = client.get("/screener/universe", params={"id": "india-all"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "india-all"
    assert len(body["symbols"]) > 5000
    assert "RELIANCE.NS" in body["symbols"]


# ---------------------------------------------------------------------------
# sharesOutstanding v7 mapping
# ---------------------------------------------------------------------------


def test_fundamentals_from_v7_maps_shares_outstanding() -> None:
    fundamentals = yb.fundamentals_from_v7(_v7_row("RELIANCE.NS", sharesOutstanding=6.77e9))
    assert fundamentals.shares_outstanding == 6.77e9
    # Absent → honest None, never fabricated.
    row = _v7_row("X.NS")
    row.pop("sharesOutstanding")
    assert yb.fundamentals_from_v7(row).shares_outstanding is None


# ---------------------------------------------------------------------------
# SSE — POST /screener/run/stream via the httpx ASGI transport
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_stream_emits_progress_then_result(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fund(symbol: str) -> Fundamentals:
        return Fundamentals(symbol=symbol, market_cap=1e12, pe_ratio=10.0, provider="t")

    def fake_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return Quote(
            symbol=symbol,
            price=50.0,
            change=0.0,
            change_percent=0.0,
            volume=1.0,
            currency="USD",
            timestamp=datetime.now(tz=UTC),
            provider="t",
        )

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_fund)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_quote)

    transport = httpx.ASGITransport(app=create_app())
    frames: list[dict] = []
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/screener/run/stream",
            json={"universe": "custom", "custom_symbols": ["AAA", "BBB"], "criteria": []},
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    frames.append(json.loads(line[len("data: ") :]))

    events = [f["event"] for f in frames]
    assert events[-1] == "result"
    assert "progress" in events
    progress = next(f for f in frames if f["event"] == "progress")
    # Mirrors ScreenerProgressFrame in types/screener.ts.
    assert set(progress) == {"event", "phase", "done", "total", "detail"}
    result = frames[-1]
    assert result["result_count"] == 2
    assert result["partial"] is False
    assert {r["symbol"] for r in result["rows"]} == {"AAA", "BBB"}
    assert result["coverage"] == "screened 2 of 2 — 0 unavailable"
