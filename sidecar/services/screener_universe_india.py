"""Full-market India screener universes from the bundled resolver masters (R10, D40).

Resolves the three India universe ids the contracts commit added to
``models/screener.py``:

  - ``nse-all``   — every NSE master row (EQ + ETF) as ``SYMBOL.NS`` (~2,675).
  - ``bse-all``   — BSE master rows with STATUS == "Active" as ``SYMBOL.BO``
    (the liquidity ``group`` is retained in the per-symbol meta).
  - ``india-all`` — the union, NSE listing preferred: a BSE row whose SYMBOL
    also appears in the NSE master is skipped (dual-listings screen once,
    on the deeper-liquidity venue).

The masters are the same bundled JSON snapshots the symbol resolver reads
(``services.resolver_masters`` via :mod:`importlib.resources` — offline,
deterministic, test-stable); ``india_sector_map.json`` rides the same package
and supplies the build-time sector / shares_outstanding seed the fundamentals
store warms from.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from importlib import resources
from typing import Any

from models.screener import ScreenerUniverse, ScreenerUniverseId
from services.errors import ProviderError

logger = logging.getLogger(__name__)

_INDIA_UNIVERSE_IDS: frozenset[str] = frozenset({"nse-all", "bse-all", "india-all"})


def is_india_universe(universe_id: str) -> bool:
    """True for the three full-market India universe ids."""
    return universe_id in _INDIA_UNIVERSE_IDS


def _load_master(filename: str) -> dict[str, Any]:
    try:
        with (
            resources.files("services.resolver_masters")
            .joinpath(filename)
            .open("r", encoding="utf-8")
        ) as fp:
            return json.load(fp)
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise ProviderError(f"missing bundled master {filename!r}") from exc


@lru_cache(maxsize=1)
def _nse_rows() -> list[tuple[str, str, str]]:
    """``[(SYMBOL, name, type)]`` for every NSE master row, master order."""
    raw = _load_master("nse_instruments.json")
    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for row in raw.get("instruments", []):
        sym = str(row[0]).strip().upper()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        name = str(row[1]).strip() if len(row) > 1 else ""
        typ = str(row[2]).strip().upper() if len(row) > 2 else "EQ"
        out.append((sym, name, typ))
    return out


@lru_cache(maxsize=1)
def _bse_rows() -> list[tuple[str, str, str, str, str]]:
    """``[(SYMBOL, name, group, scrip_code, isin)]`` for Active BSE rows,
    master (market-cap prominence) order."""
    raw = _load_master("bse_instruments.json")
    out: list[tuple[str, str, str, str, str]] = []
    seen: set[str] = set()
    for row in raw.get("instruments", []):
        code = str(row[0]).strip() if len(row) > 0 else ""
        sym = str(row[1]).strip().upper() if len(row) > 1 else ""
        name = str(row[2]).strip() if len(row) > 2 else ""
        group = str(row[3]).strip().upper() if len(row) > 3 else ""
        isin = str(row[4]).strip() if len(row) > 4 else ""
        status = str(row[5]).strip() if len(row) > 5 else "Active"
        if not sym or sym in seen or status != "Active":
            continue
        seen.add(sym)
        out.append((sym, name, group, code, isin))
    return out


@lru_cache(maxsize=1)
def _sector_map() -> dict[str, dict[str, Any]]:
    """``{BASE_SYMBOL: record}`` from the bundled ``india_sector_map.json``.

    Best-effort: a missing map degrades to an empty dict (universes still
    resolve; sector seeding just has nothing to seed). Each record carries
    ``isin / scrip_code / industry_raw / sector / sector_source /
    shares_outstanding`` — see ``regenerate_india_sectors.py``."""
    try:
        raw = _load_master("india_sector_map.json")
    except ProviderError as exc:
        logger.warning("screener_universe_india: %s", exc)
        return {}
    out: dict[str, dict[str, Any]] = {}
    for rec in raw.get("records", []):
        sym = str(rec.get("symbol") or "").strip().upper()
        if sym and sym not in out:
            out[sym] = rec
    return out


def sector_map_coverage() -> dict[str, Any]:
    """The honest ``coverage`` header of the bundled sector map (or empty)."""
    try:
        raw = _load_master("india_sector_map.json")
    except ProviderError:
        return {}
    coverage = raw.get("coverage")
    return coverage if isinstance(coverage, dict) else {}


def reset_caches_for_tests() -> None:
    """Drop the in-process master caches (test helper)."""
    _nse_rows.cache_clear()
    _bse_rows.cache_clear()
    _sector_map.cache_clear()


def load_india_universe(universe_id: ScreenerUniverseId) -> ScreenerUniverse:
    """Resolve one of the three full-market India universes from the masters."""
    if universe_id == "nse-all":
        return ScreenerUniverse(
            id="nse-all",
            label="NSE (all listed)",
            symbols=[f"{sym}.NS" for sym, _name, _typ in _nse_rows()],
            asset_class="equity",
        )
    if universe_id == "bse-all":
        return ScreenerUniverse(
            id="bse-all",
            label="BSE (all active)",
            symbols=[f"{sym}.BO" for sym, _n, _g, _c, _i in _bse_rows()],
            asset_class="equity",
        )
    if universe_id == "india-all":
        nse_symbols = {sym for sym, _name, _typ in _nse_rows()}
        symbols = [f"{sym}.NS" for sym, _name, _typ in _nse_rows()]
        symbols += [
            f"{sym}.BO" for sym, _n, _g, _c, _i in _bse_rows() if sym not in nse_symbols
        ]
        return ScreenerUniverse(
            id="india-all",
            label="India (NSE + BSE)",
            symbols=symbols,
            asset_class="equity",
        )
    raise ProviderError(f"not an India universe id: {universe_id!r}")


def india_symbol_meta(symbol: str) -> dict[str, Any] | None:
    """Identity metadata for an India symbol (quote form or bare).

    Returns ``{exchange, scrip_code, isin, name, group}`` or ``None`` when the
    symbol appears in neither master. A ``.NS`` symbol resolves against the NSE
    master (scrip_code/isin/group joined from the BSE master when the same
    ticker is dual-listed); a ``.BO`` symbol against the BSE master; a bare
    symbol prefers the NSE listing, mirroring ``india-all``."""
    upper = symbol.strip().upper()
    base, suffix = upper, None
    if upper.endswith(".NS"):
        base, suffix = upper[:-3], "NS"
    elif upper.endswith(".BO"):
        base, suffix = upper[:-3], "BO"
    if not base:
        return None

    nse = {sym: (name, typ) for sym, name, typ in _nse_rows()}
    bse = {sym: (name, group, code, isin) for sym, name, group, code, isin in _bse_rows()}

    if suffix in (None, "NS") and base in nse:
        name, _typ = nse[base]
        bse_row = bse.get(base)
        return {
            "exchange": "NSE",
            "scrip_code": bse_row[2] if bse_row else None,
            "isin": (bse_row[3] or None) if bse_row else None,
            "name": name,
            "group": bse_row[1] if bse_row else None,
        }
    if suffix in (None, "BO") and base in bse:
        name, group, code, isin = bse[base]
        return {
            "exchange": "BSE",
            "scrip_code": code,
            "isin": isin or None,
            "name": name,
            "group": group,
        }
    return None


def sector_seed_for(symbol: str) -> dict[str, Any] | None:
    """The bundled sector-map record for an India symbol (quote form or bare).

    ``{isin, scrip_code, industry_raw, sector, sector_source,
    shares_outstanding}`` or ``None``. Joined by base ticker (the map keys on
    the BSE ``scrip_id``, which matches the NSE symbol on dual-listings); each
    record also carries the ISIN so callers can cross-check identity."""
    base = symbol.strip().upper()
    if base.endswith((".NS", ".BO")):
        base = base[:-3]
    return _sector_map().get(base)


__all__ = [
    "india_symbol_meta",
    "is_india_universe",
    "load_india_universe",
    "reset_caches_for_tests",
    "sector_map_coverage",
    "sector_seed_for",
]
