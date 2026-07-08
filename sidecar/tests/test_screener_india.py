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


def test_india_symbol_meta_is_constant_time_for_the_boot_seed() -> None:
    """The boot seed calls ``india_symbol_meta`` + ``sector_seed_for`` once per
    ``india-all`` symbol with zero awaits between — rebuilding the master
    lookup dicts per call was O(n²) and blocked the event loop ~4 s (measured)
    against the brief's '<1 s'. With the hoisted lru_cache lookups the whole
    loop runs in ~tens of ms; 1 s is a wide CI margin that still fails the
    quadratic version by 4x."""
    import time as _time

    universe = screener_universe_india.load_india_universe("india-all")
    assert len(universe.symbols) > 5000
    screener_universe_india.india_symbol_meta(universe.symbols[0])  # warm the caches
    start = _time.perf_counter()
    for symbol in universe.symbols:
        screener_universe_india.india_symbol_meta(symbol)
        screener_universe_india.sector_seed_for(symbol)
    assert _time.perf_counter() - start < 1.0


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
async def test_budget_expiry_serves_stale_cached_rows_with_honest_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R11 (D52) — the deliberate successor to the R10 pin that DROPPED stale
    rows. A candidate whose chunk never ran but that has an OLD store row (v7
    stamp beyond the 6 h serving TTL) is now EVALUATED and served on the
    labeled stale/snapshot basis — never presented as fresh: ``data_basis``
    is not "live", ``data_as_of`` dates the values at the old stamp, the
    coverage line discloses the basis, and nothing remains unevaluated (so
    ``partial`` is False — every symbol was screened, honestly labeled)."""
    import contextlib as _ctx
    import sqlite3
    import time as _time

    monkeypatch.setattr(screener, "resolve_universe", _fake_universe("nse-all", ["OLD.NS"]))
    await fundamentals_store.upsert_v7(
        "OLD.NS",
        Fundamentals(symbol="OLD.NS", market_cap=1e12, pe_ratio=10.0, provider="t"),
        Quote(
            symbol="OLD.NS",
            price=100.0,
            change=0.0,
            change_percent=0.0,
            volume=1.0,
            currency="INR",
            timestamp=datetime.now(tz=UTC),
            provider="t",
        ),
    )
    twenty_hours = 20 * 3600
    stale_stamp = _time.time() - twenty_hours
    with _ctx.closing(sqlite3.connect(fundamentals_store._db_path())) as conn:
        conn.execute(
            "UPDATE fundamentals SET v7_updated_at = ?, quote_updated_at = ? WHERE symbol = ?",
            (stale_stamp, stale_stamp, "OLD.NS"),
        )
        conn.commit()
    yb.reset_for_tests(_HangingTransport())  # this run's sweep never lands

    request = ScreenerRequest(universe="nse-all", criteria=[], limit=100)
    result = await screener.run_screener(request, wall_budget_s=0.3)
    assert result.evaluated_count == 1
    assert result.result_count == 1
    row = result.rows[0]
    assert row.symbol == "OLD.NS"
    assert row.data_basis == "snapshot"  # nothing about this row is fresh
    assert row.data_as_of is not None and abs(row.data_as_of - stale_stamp) < 5.0
    assert row.currency == "INR"
    assert result.basis_counts == {"snapshot": 1}
    assert result.skip_details == []
    # Every symbol was evaluated (on a labeled basis) — partial would claim
    # rows remain unevaluated, which is no longer true.
    assert result.partial is False
    assert result.coverage is not None
    assert result.coverage.startswith("screened 1 of 1 — 0 unavailable")
    assert "stale/snapshot basis" in result.coverage


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


@pytest.mark.asyncio
async def test_sse_stream_engine_crash_emits_sanitized_error_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An engine crash terminates the stream with one ``{"event":"error"}``
    frame (mirrors ``ScreenerErrorFrame`` in types/screener.ts) whose message
    is sanitized — no raw provider/debug text reaches the UI."""

    async def explode(request, *, wall_budget_s=120.0, on_progress=None):  # noqa: ANN001, ARG001
        raise RuntimeError("curl_cffi: TLS handshake gobbledygook host=10.0.0.7")

    monkeypatch.setattr("services.screener.run_screener", explode)

    transport = httpx.ASGITransport(app=create_app())
    frames: list[dict] = []
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/screener/run/stream",
            json={"universe": "custom", "custom_symbols": ["AAA"], "criteria": []},
        ) as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    frames.append(json.loads(line[len("data: ") :]))

    assert len(frames) == 1
    error = frames[0]
    assert set(error) == {"event", "message"}
    assert error["event"] == "error"
    assert "gobbledygook" not in error["message"]  # debug-ish provider text stays in the logs
    assert "RuntimeError" in error["message"]


# ---------------------------------------------------------------------------
# R11 (D52/D53) — cold-cache seed serving + circuit-breaker short-circuit
# ---------------------------------------------------------------------------


class _RateLimitedTransport(httpx.AsyncBaseTransport):
    """A v7 endpoint hard-blocking this IP: every quote call answers 429."""

    def __init__(self) -> None:
        self.quote_calls = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="crumb")
        if "/v7/finance/quote" in request.url.path:
            self.quote_calls += 1
            return httpx.Response(429)
        return httpx.Response(200, text="")


async def _seed_three_it_names() -> float:
    """Seed pack rows for a 3-name IT universe; returns the pack as-of."""
    as_of = __import__("time").time() - 16 * 24 * 3600  # a 16-day-old snapshot
    await fundamentals_store.seed_fundamentals(
        [
            {
                "symbol": "SEEDIT1.NS",
                "name": "Seed IT One",
                "currency": "INR",
                "sector": "Technology",
                "sector_source": "seed-pack",
                "seed_as_of": as_of,
                "market_cap": 17e9,
                "pe_ratio": 13.5,
                "roe": 0.19,
            },
            {
                "symbol": "SEEDIT2.NS",
                "name": "Seed IT Two",
                "currency": "INR",
                "sector": "Technology",
                "sector_source": "seed-pack",
                "seed_as_of": as_of,
                "market_cap": 6.7e9,
                "pe_ratio": 19.7,
                "roe": 1.37,
            },
            {
                "symbol": "SEEDFIN.NS",
                "name": "Seed Financial",
                "currency": "INR",
                "sector": "Financial Services",
                "sector_source": "seed-pack",
                "seed_as_of": as_of,
                "market_cap": 50e9,
                "pe_ratio": 8.0,
                "roe": 0.12,
            },
        ]
    )
    return as_of


def _operator_it_criteria() -> list:
    return [
        StringEqCriterion(field="sector", operator="eq", value="Technology"),
        NumericThresholdCriterion(field="market_cap", operator="lt", value=50e9),
        NumericThresholdCriterion(field="pe_ratio", operator="lt", value=20.0),
        NumericThresholdCriterion(field="roe", operator="gt", value=0.15),
    ]


@pytest.mark.asyncio
async def test_cold_cache_throttled_ip_serves_correct_rows_from_seed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The R11 flagship guarantee: a FRESH install on a HARD-BLOCKED IP still
    answers the operator's IT-services query — complete, correct rows served
    from the bundled seed pack, honestly labeled, with the throttle disclosed.
    Never a hang, never a lie, never 0 rows."""
    from services import provider_health

    symbols = ["SEEDIT1.NS", "SEEDIT2.NS", "SEEDFIN.NS"]
    monkeypatch.setattr(screener, "resolve_universe", _fake_universe("nse-all", symbols))
    as_of = await _seed_three_it_names()
    transport = _RateLimitedTransport()
    yb.reset_for_tests(transport)

    async def _throttled_fundamentals(symbol: str):
        from services.errors import ProviderError

        raise ProviderError(f"throttled {symbol}", kind="rate_limited")

    monkeypatch.setattr(screener.provider_registry, "get_fundamentals", _throttled_fundamentals)

    request = ScreenerRequest(universe="nse-all", criteria=_operator_it_criteria(), limit=100)
    result = await screener.run_screener(request, wall_budget_s=20.0)

    assert result.result_count == 2
    assert {r.symbol for r in result.rows} == {"SEEDIT1.NS", "SEEDIT2.NS"}
    assert all(r.data_basis == "snapshot" for r in result.rows)
    assert all(r.currency == "INR" for r in result.rows)
    assert all(r.data_as_of is not None and abs(r.data_as_of - as_of) < 5.0 for r in result.rows)
    assert result.throttled is True
    assert result.basis_counts == {"snapshot": 2}
    assert result.freshness is not None
    assert result.freshness.get("seed_as_of") == pytest.approx(as_of, abs=5.0)
    # Everything evaluated (SEEDFIN failed the criteria honestly) — no skips.
    assert result.evaluated_count == 3
    assert result.skip_details == []
    assert result.partial is False
    assert "stale/snapshot basis" in (result.coverage or "")
    provider_health.reset_for_tests()


@pytest.mark.asyncio
async def test_open_circuit_short_circuits_the_sweep_instantly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With the Yahoo circuit OPEN, a screen never spends its wall on doomed
    calls — the sweep short-circuits without a single HTTP request and the
    result serves from the seed basis in well under the budget."""
    from services import provider_health

    symbols = ["SEEDIT1.NS", "SEEDIT2.NS", "SEEDFIN.NS"]
    monkeypatch.setattr(screener, "resolve_universe", _fake_universe("nse-all", symbols))
    await _seed_three_it_names()
    transport = _RateLimitedTransport()
    yb.reset_for_tests(transport)
    provider_health.record_rate_limited(weight=3.0)  # OPEN before the run
    assert provider_health.is_open() is True

    request = ScreenerRequest(universe="nse-all", criteria=_operator_it_criteria(), limit=100)
    result = await screener.run_screener(request, wall_budget_s=120.0)

    assert transport.quote_calls == 0, "an open circuit must not spend a single v7 call"
    assert result.duration_ms < 10_000
    assert result.throttled is True
    assert result.result_count == 2
    assert all(r.data_basis == "snapshot" for r in result.rows)
    provider_health.reset_for_tests()


@pytest.mark.asyncio
async def test_sustained_429_storm_opens_the_circuit_mid_sweep() -> None:
    """Chunk-level 429 concessions feed the breaker: a sweep over a blocked
    IP opens the circuit so later chunks stop spending."""
    from services import provider_health

    transport = _RateLimitedTransport()
    yb.reset_for_tests(transport)
    for _ in range(3):
        await yb.fetch_quotes_batch(["AAA.NS"])  # each concedes rate_limited
    assert provider_health.is_open() is True
    before = transport.quote_calls
    rows, failures = await yb.fetch_quotes_batch(["BBB.NS", "CCC.NS"])
    assert transport.quote_calls == before, "open circuit spends nothing"
    assert failures == {"BBB.NS": "rate_limited", "CCC.NS": "rate_limited"}
    provider_health.reset_for_tests()
