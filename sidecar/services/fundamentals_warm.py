"""Background India fundamentals warming — R10, D40.

Started from the FastAPI lifespan beside ``screener.start_warm_precompute``.
Region-aware: the loops only do WORK while ``config.get_region() == "IN"``
(the env-derived region for a background task) — a US install never sweeps
5k Indian symbols. Three responsibilities:

  1. **Boot seed** (<1 s, local-only): every ``india-all`` symbol's identity
     row (exchange / scrip code / ISIN / group / name) + the build-time sector
     map (sector, ``sector_source: "seed"``, shares_outstanding) lands in the
     fundamentals store, so sector prefilters bite before any network fetch.
  2. **v7 sweep** of ``india-all`` every 15 min — stale-or-missing rows only,
     reusing the screener warm loop's exponential 429 backoff discipline
     (``screener._warm_sleep_seconds`` + its constants; never duplicated).
  3. **Deep ``.info`` crawler** — ``fundamentals_store.info_priority(20)``
     per cycle (never-attempted first, market cap desc, then stalest),
     ``Semaphore(4)``, 1.5–3 s jitter between fetches, and it PAUSES while a
     foreground screen runs (the engine brackets every run with
     :func:`screen_started` / :func:`screen_finished`). A FAILED fetch is
     stamped (``mark_info_failure``) so never-succeeding symbols (BSE scrips
     Yahoo doesn't cover) rotate out of the priority head for
     ``TTL_INFO_RETRY_SECONDS`` instead of wedging every cycle.

``stop_warm_fundamentals()`` cancels + awaits both loops (lifespan finally).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import random

from config import get_region
from services import fundamentals_store, provider_registry, yahoo_batch_provider

logger = logging.getLogger(__name__)

#: v7 sweep interval for the India full-market universe.
_SWEEP_INTERVAL_SECONDS = 15 * 60.0
#: Idle re-check interval while the region is not IN (cheap clock check).
_REGION_RECHECK_SECONDS = 60.0
#: Deep-crawler batch per cycle (info_priority limit).
_CRAWL_BATCH = 20
#: Deep-crawler concurrency.
_CRAWL_CONCURRENCY = 4
#: Jittered sleep between deep crawl cycles' individual fetches.
_CRAWL_JITTER_RANGE = (1.5, 3.0)
#: Per-symbol timeout on the deep crawl fetch.
_CRAWL_TIMEOUT_SECONDS = 15.0

# --- Foreground-screen pause gate ----------------------------------------------
#
# The engine sets this around every foreground run; the deep crawler waits
# until the LAST concurrent screen finishes (a counter, not a boolean, so two
# overlapping runs do not un-pause each other's tail).
_screen_depth = 0
_idle_event = asyncio.Event()
_idle_event.set()


def screen_started() -> None:
    """A foreground screener run began — pause the deep crawler."""
    global _screen_depth
    _screen_depth += 1
    _idle_event.clear()


def screen_finished() -> None:
    """A foreground screener run ended — resume the crawler when none remain."""
    global _screen_depth
    _screen_depth = max(0, _screen_depth - 1)
    if _screen_depth == 0:
        _idle_event.set()


def foreground_screen_running() -> bool:
    """True while at least one foreground screener run is in flight."""
    return _screen_depth > 0


def reset_for_tests() -> None:
    """Reset the pause gate (and re-arm its event on the current loop)."""
    global _screen_depth, _idle_event
    _screen_depth = 0
    _idle_event = asyncio.Event()
    _idle_event.set()


# ---------------------------------------------------------------------------
# Boot seed (local-only, <1 s)
# ---------------------------------------------------------------------------


async def seed_india_store() -> int:
    """Seed identity + sector-map rows for every ``india-all`` symbol.

    Local-only (bundled masters + bundled sector map — zero network). Returns
    the number of rows touched. Idempotent: seeds only NULL columns. The
    row-building loop runs on a thread (zero awaits inside it), so the boot
    seed never stalls ``/health`` or a first request."""
    from services import screener_universe_india

    def _build_rows() -> list[dict[str, object]]:
        universe = screener_universe_india.load_india_universe("india-all")
        rows: list[dict[str, object]] = []
        for symbol in universe.symbols:
            meta = screener_universe_india.india_symbol_meta(symbol) or {}
            seed = screener_universe_india.sector_seed_for(symbol) or {}
            rows.append(
                {
                    "symbol": symbol,
                    "name": meta.get("name"),
                    "exchange": meta.get("exchange"),
                    "isin": meta.get("isin") or seed.get("isin"),
                    "scrip_code": meta.get("scrip_code") or seed.get("scrip_code"),
                    "group": meta.get("group"),
                    "sector": seed.get("sector"),
                    "industry": seed.get("industry_raw"),
                    "sector_source": "seed" if seed.get("sector") else None,
                    "shares_outstanding": seed.get("shares_outstanding"),
                }
            )
        return rows

    rows = await asyncio.to_thread(_build_rows)
    touched = await fundamentals_store.seed_universe(rows)
    logger.info("fundamentals warm: seeded %d india rows", touched)
    return touched


# ---------------------------------------------------------------------------
# v7 sweep loop (every 15 min, screener-shared backoff discipline)
# ---------------------------------------------------------------------------


async def _sweep_once() -> bool:
    """One stale-only v7 sweep over ``india-all`` into the store.

    Returns ``True`` when the cycle was rate-limited (the shared
    ``_WARM_THROTTLE_RATIO`` test from the screener warm loop)."""
    from services import screener, screener_universe_india

    universe = screener_universe_india.load_india_universe("india-all")
    stale = await fundamentals_store.stale_symbols(
        universe.symbols,
        quote_ttl=fundamentals_store.TTL_QUOTE_FULL_SECONDS,
    )
    if not stale:
        return False
    rows, failures = await yahoo_batch_provider.fetch_quotes_batch(stale)
    rate_limited = sum(1 for reason in failures.values() if reason == "rate_limited")
    items = []
    for _sym, row in rows.items():
        quote = yahoo_batch_provider.quote_from_v7(row)
        if quote is not None:
            items.append((quote.symbol, yahoo_batch_provider.fundamentals_from_v7(row), quote))
    await fundamentals_store.upsert_v7_batch(items)
    logger.debug(
        "fundamentals warm: swept %d stale india symbols (%d resolved, %d rate-limited)",
        len(stale),
        len(rows),
        rate_limited,
    )
    return rate_limited >= len(stale) * screener._WARM_THROTTLE_RATIO


async def _sweep_loop() -> None:
    """India v7 sweep every 15 min, region-gated, with the screener's shared
    exponential 429 backoff. The boot seed runs on the first IN cycle."""
    from services import screener

    consecutive_throttles = 0
    seeded = False
    try:
        while True:
            if get_region() != "IN":
                await asyncio.sleep(_REGION_RECHECK_SECONDS)
                continue
            if not seeded:
                try:
                    await seed_india_store()
                    seeded = True
                except Exception as exc:  # noqa: BLE001 — seed is best-effort
                    logger.warning("fundamentals warm: seed failed: %s", exc)
            try:
                throttled = await _sweep_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — a sweep cycle is best-effort
                logger.debug("fundamentals warm: sweep cycle failed: %s", exc)
                throttled = False
            if throttled:
                consecutive_throttles += 1
                sleep_s = screener._warm_sleep_seconds(
                    _SWEEP_INTERVAL_SECONDS, consecutive_throttles
                )
                logger.warning(
                    "fundamentals warm: rate-limited (streak=%d); backing off %.0fs",
                    consecutive_throttles,
                    sleep_s,
                )
            else:
                consecutive_throttles = 0
                sleep_s = screener._warm_sleep_seconds(_SWEEP_INTERVAL_SECONDS, 0)
            await asyncio.sleep(sleep_s)
    except asyncio.CancelledError:
        logger.debug("fundamentals warm: sweep loop cancelled")
        raise


# ---------------------------------------------------------------------------
# Deep .info crawler loop
# ---------------------------------------------------------------------------


async def _crawl_once() -> int:
    """One deep-crawl cycle: the next ``info_priority`` batch through the
    registry ``.info`` path into the store. Returns symbols fetched."""
    from services import screener_universe_india

    universe = screener_universe_india.load_india_universe("india-all")
    batch = await fundamentals_store.info_priority(universe.symbols, _CRAWL_BATCH)
    if not batch:
        return 0
    sem = asyncio.Semaphore(_CRAWL_CONCURRENCY)
    fetched = 0

    async def _one(symbol: str) -> None:
        nonlocal fetched
        # Pause point: a foreground screen owns the upstream while it runs.
        await _idle_event.wait()
        async with sem:
            try:
                rich = await asyncio.wait_for(
                    provider_registry.get_fundamentals(symbol),
                    timeout=_CRAWL_TIMEOUT_SECONDS,
                )
            except Exception as exc:  # noqa: BLE001 — the crawler shrugs and moves on
                logger.debug("fundamentals warm: crawl %s failed: %s", symbol, exc)
                # Stamp the failure so the symbol rotates out of the priority
                # head — without this a batch of never-succeeding symbols
                # (e.g. BSE scrips Yahoo doesn't cover) wedges the crawler:
                # every cycle re-selects the same 20, fetches 0, forever.
                await fundamentals_store.mark_info_failure(symbol)
                return
            await fundamentals_store.upsert_info(symbol, rich)
            fetched += 1
            await asyncio.sleep(random.uniform(*_CRAWL_JITTER_RANGE))

    await asyncio.gather(*(_one(s) for s in batch))
    return fetched


async def _crawl_loop() -> None:
    """Deep ``.info`` crawler: region-gated, pause-aware, jittered cycles."""
    try:
        while True:
            if get_region() != "IN":
                await asyncio.sleep(_REGION_RECHECK_SECONDS)
                continue
            await _idle_event.wait()
            try:
                fetched = await _crawl_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — a crawl cycle is best-effort
                logger.debug("fundamentals warm: crawl cycle failed: %s", exc)
                fetched = 0
            # An empty cycle (everything fresh) idles longer than a busy one.
            await asyncio.sleep(
                random.uniform(*_CRAWL_JITTER_RANGE) if fetched else _REGION_RECHECK_SECONDS
            )
    except asyncio.CancelledError:
        logger.debug("fundamentals warm: crawl loop cancelled")
        raise


# ---------------------------------------------------------------------------
# Lifespan API
# ---------------------------------------------------------------------------

_sweep_task: asyncio.Task[None] | None = None
_crawl_task: asyncio.Task[None] | None = None


def start_warm_fundamentals() -> None:
    """Start the India warm workers (idempotent; detached — never blocks boot)."""
    global _sweep_task, _crawl_task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.debug("fundamentals warm: no running loop; workers not started")
        return
    if _sweep_task is None or _sweep_task.done():
        _sweep_task = loop.create_task(_sweep_loop())
    if _crawl_task is None or _crawl_task.done():
        _crawl_task = loop.create_task(_crawl_loop())


async def stop_warm_fundamentals() -> None:
    """Cancel + await both warm workers (lifespan finally — no leaked tasks)."""
    global _sweep_task, _crawl_task
    tasks = [t for t in (_sweep_task, _crawl_task) if t is not None]
    _sweep_task = None
    _crawl_task = None
    for task in tasks:
        task.cancel()
    for task in tasks:
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task


__all__ = [
    "foreground_screen_running",
    "reset_for_tests",
    "screen_finished",
    "screen_started",
    "seed_india_store",
    "start_warm_fundamentals",
    "stop_warm_fundamentals",
]
