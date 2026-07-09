"""Tests for the NSE symbol-change lane (R12, D66 — an OLD ticker → the CURRENT one).

No test makes a live NSE call: ``httpx`` is mocked at the transport level
(:class:`httpx.MockTransport`) installed on a cold session via
:func:`nse_symbol_change.reset_for_tests` — the same seam as
``test_nse_bhavcopy``. The fixture CSV is a verbatim trim of the real
``symbolchange.csv`` downloaded live from nsearchives 2026-07-10 (the header-less
4-column format), including the finding's ``GUJGASLTD → GUJENERGY`` row, a
self-map, and a two-hop chain.

Surfaces under test:
  - parse: header-less 4 columns, self-maps dropped, keyed by OLD symbol;
  - ``lookup_current``: rename applied once the effective date passed, a
    future-dated change NOT applied, chain followed to the terminal symbol,
    empty map → an honest ``None`` (no-op);
  - ``fetch_latest`` cache round-trip: a second same-day fetch does zero HTTP;
  - a blocked/missing file → ``None`` and an EMPTY in-process map (cold no-op).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import httpx
import pytest

from services import data_cache
from services import nse_symbol_change as sc

_FIXTURE = Path(__file__).parent / "fixtures" / "nse" / "symbolchange_trimmed.csv"


def _fixture_text() -> str:
    return _FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path):
    """Each test gets a cold on-disk cache and a cold HTTP session + map."""
    data_cache.reset_for_tests(tmp_path / "test_cache.db")
    sc.reset_for_tests()
    yield
    data_cache.reset_for_tests(None)
    sc.reset_for_tests()


# ---------------------------------------------------------------------------
# Parse.
# ---------------------------------------------------------------------------


def test_parse_keeps_renames_keyed_by_old_symbol() -> None:
    changes = sc.parse_symbol_change(_fixture_text())
    # The self-map row (761ABCL35A → 761ABCL35A) is dropped; every other OLD
    # symbol is a key.
    assert set(changes) == {"GUJGASLTD", "ASLIND", "AXISNIFTY", "76100ABCL3"}
    guj = changes["GUJGASLTD"]
    assert guj.new_symbol == "GUJENERGY"
    assert guj.effective_date == date(2026, 7, 1)
    assert guj.new_name == "GUJARAT ENERGY LIMITED"


def test_parse_garbage_yields_empty() -> None:
    assert sc.parse_symbol_change("") == {}
    assert sc.parse_symbol_change("<html>blocked</html>") == {}


def test_parse_date_variants() -> None:
    assert sc._parse_date("01-JUL-2026") == date(2026, 7, 1)
    assert sc._parse_date("24-APR-2026") == date(2026, 4, 24)
    assert sc._parse_date("garbage") is None
    assert sc._parse_date("31-XXX-2026") is None


# ---------------------------------------------------------------------------
# lookup_current — the resolver's synchronous, offline seam.
# ---------------------------------------------------------------------------


def test_lookup_current_applies_passed_rename() -> None:
    sc.set_active_map_for_tests(sc.parse_symbol_change(_fixture_text()))
    applied = sc.lookup_current("GUJGASLTD", as_of=date(2026, 7, 10))
    assert applied is not None
    assert applied.renamed_from == "GUJGASLTD"
    assert applied.renamed_to == "GUJENERGY"
    assert applied.effective_date == date(2026, 7, 1)
    assert applied.new_name == "GUJARAT ENERGY LIMITED"


def test_lookup_current_ignores_future_dated_rename() -> None:
    sc.set_active_map_for_tests(sc.parse_symbol_change(_fixture_text()))
    # As of before the effective date the change has not happened yet.
    assert sc.lookup_current("GUJGASLTD", as_of=date(2026, 6, 30)) is None


def test_lookup_current_follows_chain_to_terminal_symbol() -> None:
    sc.set_active_map_for_tests(sc.parse_symbol_change(_fixture_text()))
    # 76100ABCL3 → 761ABCL35A (then a self-map terminates the chain).
    applied = sc.lookup_current("76100ABCL3", as_of=date(2026, 7, 10))
    assert applied is not None
    assert applied.renamed_to == "761ABCL35A"
    assert applied.effective_date == date(2026, 6, 8)


def test_lookup_current_empty_map_is_noop() -> None:
    # A cold app with no data must be an honest no-op.
    assert sc.lookup_current("GUJGASLTD", as_of=date(2026, 7, 10)) is None
    assert sc.lookup_current("ANYTHING") is None


def test_lookup_current_unknown_symbol_returns_none() -> None:
    sc.set_active_map_for_tests(sc.parse_symbol_change(_fixture_text()))
    assert sc.lookup_current("RELIANCE", as_of=date(2026, 7, 10)) is None


# ---------------------------------------------------------------------------
# fetch_latest — download, cache round-trip, missing-file no-op.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_latest_downloads_and_hydrates_map(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sc, "_ist_today", lambda: date(2026, 7, 10))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "nsearchives.nseindia.com"
        return httpx.Response(200, text=_fixture_text())

    sc.reset_for_tests(httpx.MockTransport(handler))
    try:
        changes = await sc.fetch_latest()
        assert changes is not None
        assert changes["GUJGASLTD"].new_symbol == "GUJENERGY"
        # The in-process map is hydrated → the resolver seam works immediately.
        applied = sc.lookup_current("GUJGASLTD")
        assert applied is not None and applied.renamed_to == "GUJENERGY"
    finally:
        await sc.aclose()


@pytest.mark.asyncio
async def test_fetch_latest_second_call_hits_cache_zero_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sc, "_ist_today", lambda: date(2026, 7, 10))
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, text=_fixture_text())

    sc.reset_for_tests(httpx.MockTransport(handler))
    try:
        first = await sc.fetch_latest()
        assert first is not None and calls == 1
    finally:
        await sc.aclose()

    def explode(request: httpx.Request) -> httpx.Response:
        raise AssertionError("cache hit must not touch the network")

    sc.reset_for_tests(httpx.MockTransport(explode))
    try:
        second = await sc.fetch_latest()
        assert second is not None
        assert second["GUJGASLTD"].new_symbol == "GUJENERGY"
        assert calls == 1
    finally:
        await sc.aclose()


@pytest.mark.asyncio
async def test_fetch_latest_missing_file_is_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 404 (or blocked) master → ``None`` and an EMPTY map — the lane is a
    no-op, never a fabricated rename."""
    monkeypatch.setattr(sc, "_ist_today", lambda: date(2026, 7, 10))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    sc.reset_for_tests(httpx.MockTransport(handler))
    try:
        assert await sc.fetch_latest() is None
        assert sc.lookup_current("GUJGASLTD") is None
    finally:
        await sc.aclose()


@pytest.mark.asyncio
async def test_fetch_latest_network_down_serves_recent_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Yesterday's cached as-of keeps the lane working when today's fetch fails
    (a rename is durable, unlike an EOD price)."""
    # Day 1: a successful fetch seeds the cache under 2026-07-09.
    monkeypatch.setattr(sc, "_ist_today", lambda: date(2026, 7, 9))

    def ok(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_fixture_text())

    sc.reset_for_tests(httpx.MockTransport(ok))
    try:
        assert await sc.fetch_latest() is not None
    finally:
        await sc.aclose()

    # Day 2: today's fetch is blocked, but the walk-back finds yesterday's cache.
    monkeypatch.setattr(sc, "_ist_today", lambda: date(2026, 7, 10))

    def blocked(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Access Denied")

    sc.reset_for_tests(httpx.MockTransport(blocked))
    try:
        changes = await sc.fetch_latest()
        assert changes is not None
        assert changes["GUJGASLTD"].new_symbol == "GUJENERGY"
    finally:
        await sc.aclose()
