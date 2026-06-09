"""Symbol resolution — free-text / ticker → a concrete instrument (Pass B / B1).

FR-061: resolve a name or ticker to ``(ticker, exchange, region, asset_class)``
keyless-first, locale-ranked, with disambiguation when confidence is low —
"Tata Steel" → TATASTEEL on NSE for an IN session, "GOLDBEES" → the NSE gold ETF.

Design (research §A.3 — keep resolution and data-fetch separate):

  * **Stage 1 — bundled masters (offline, deterministic):** the SEC
    ``company_tickers`` snapshot (US) + the NSE ``EQUITY_L`` + ETF list + the
    full regenerated BSE scrip master, shipped under
    :mod:`services.resolver_masters`. An exact ticker hit is instant; a
    name query is fuzzy-matched and locale-ranked.
  * **Stage 2 — live keyless fallback (best-effort):** only when the masters
    miss, a guarded ``yfinance.Search`` lookup catches names/tickers not in the
    bundle. Network-guarded so it never blocks (and tests of bundled symbols
    never touch the network).

Master hygiene (R7 Component 4)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  * **One canonical row per instrument.** A name listed on BOTH NSE and BSE
    (~2,400 dual-listings) is canonically the **NSE** instrument for trading
    data — the fuzzy-name and autocomplete scans skip the BSE row for a
    dual-listed symbol so one instrument never appears twice. The BSE identity
    is retained: an exact-ticker resolve of a dual-listed name carries the BSE
    row as a secondary candidate (BSE-only fundamentals/announcements live
    there), and an explicit ``.BO`` suffix pins the BSE identity outright.
  * **The exchange field always agrees with the yahoo_symbol suffix.** NSE ↔
    ``.NS``, BSE ↔ ``.BO``, US ↔ no suffix — enforced by construction in the
    three instrument builders (the only places an :class:`Instrument` is made)
    and by the suffix mapping in the live fallback.

Confidence model (the ``score`` carried on every candidate):

  * ``1.0``  — exact ticker hit in a bundled master (deterministic).
  * ``0.97`` — query equals the company's first word ("apple" → "Apple Inc.").
  * ``0.92`` — name prefix match;  ``0.8`` — name substring match.
  * ``< 0.8``— ``SequenceMatcher`` ratio, floored at ``_MIN_NAME_SCORE`` (0.6).
  * ``0.6``  — live ``yfinance.Search`` fallback (never master-deterministic).

  A small same-locale bonus (+0.08) breaks ties before reporting; reported
  scores are clamped to ``[0, 1]``. Anything below
  :data:`DISAMBIGUATION_THRESHOLD` (0.72) asks the agent to disambiguate
  rather than act.

Cheap, hot-path helpers — :func:`is_nse_symbol`, :func:`is_bse_symbol`,
:func:`bse_scrip_code` and :func:`region_hint` — back the provider registry's
region routing and the India providers' self-gating; they are pure dict lookups
over the masters (no fuzzy match, no network). :func:`region_hint` covers the
FULL regenerated BSE+NSE masters: a bare BSE-only micro-cap ticker is decisively
``IN``, which is what makes the ``/history`` route's honest ``in_eod_only``
reason fire for thin BSE listings.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache
from importlib import resources

from services.locale import (
    REGION_GLOBAL,
    REGION_IN,
    REGION_US,
    region_for_suffix,
    strip_exchange_suffix,
)

logger = logging.getLogger(__name__)

# Minimum fuzzy score for a name match to be offered at all. Real matches score
# high — exact 1.0, first-word 0.97, prefix 0.92, substring 0.8 — so the floor is
# set above the noise band where SequenceMatcher gives unrelated strings ~0.5:
# better to return "unresolved" (and let the live lookup / an honest message take
# over) than to load the WRONG instrument on a weak coincidental match.
_MIN_NAME_SCORE = 0.6
# Confidence below which the agent should disambiguate rather than act.
DISAMBIGUATION_THRESHOLD = 0.72
_MAX_CANDIDATES = 6


@dataclass(frozen=True)
class Instrument:
    """One resolved instrument candidate.

    Invariant (master hygiene): ``exchange`` always agrees with the
    ``yahoo_symbol`` suffix — NSE ↔ ``.NS``, BSE ↔ ``.BO``, US ↔ no suffix.
    """

    symbol: str  # bare exchange symbol — GOLDBEES, AAPL, ICONIKSPEV
    name: str
    exchange: str  # NSE | BSE | US
    region: str  # IN | US
    asset_class: str  # equity | etf
    yahoo_symbol: str  # GOLDBEES.NS, ICONIKSPEV.BO, AAPL
    score: float = 1.0


@dataclass(frozen=True)
class Resolution:
    """The result of resolving a query: the best instrument + alternatives."""

    query: str
    best: Instrument | None
    candidates: list[Instrument] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        return self.best.score if self.best else 0.0

    @property
    def needs_disambiguation(self) -> bool:
        return self.best is not None and self.confidence < DISAMBIGUATION_THRESHOLD


# ---------------------------------------------------------------------------
# Master loading (bundled JSON, cached in-process).
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _nse_master() -> dict[str, tuple[str, str]]:
    """``{SYMBOL: (name, type)}`` for NSE equities + ETFs (type EQ | ETF)."""
    raw = _load_master("nse_instruments.json")
    out: dict[str, tuple[str, str]] = {}
    for row in raw.get("instruments", []):
        sym = str(row[0]).strip().upper()
        name = str(row[1]).strip()
        typ = str(row[2]).strip().upper() if len(row) > 2 else "EQ"
        if sym:
            out[sym] = (name, typ)
    return out


@lru_cache(maxsize=1)
def _bse_master() -> dict[str, tuple[str, str, str]]:
    """``{SYMBOL: (name, group, scrip_code)}`` for BSE equities.

    Rows in ``bse_instruments.json`` are ``[SCRIP_CODE, SYMBOL, NAME, GROUP,
    ISIN]``. The micro-cap tail (groups B/X/XT/T/Z) is the coverage NSE never
    listed — keyed by the bare ticker for ``is_bse_symbol``/``region_hint`` and
    carrying the numeric scrip code the BSE quote header endpoint needs.
    """
    raw = _load_master("bse_instruments.json")
    out: dict[str, tuple[str, str, str]] = {}
    for row in raw.get("instruments", []):
        code = str(row[0]).strip() if len(row) > 0 else ""
        sym = str(row[1]).strip().upper() if len(row) > 1 else ""
        name = str(row[2]).strip() if len(row) > 2 else ""
        group = str(row[3]).strip().upper() if len(row) > 3 else ""
        if sym:
            out[sym] = (name, group, code)
    return out


@lru_cache(maxsize=1)
def _us_master() -> dict[str, str]:
    """``{TICKER: name}`` for US-listed companies (SEC snapshot)."""
    raw = _load_master("us_instruments.json")
    out: dict[str, str] = {}
    for row in raw.get("instruments", []):
        sym = str(row[0]).strip().upper()
        name = str(row[1]).strip()
        if sym:
            out[sym] = name
    return out


def _load_master(filename: str) -> dict:
    try:
        with (
            resources.files("services.resolver_masters")
            .joinpath(filename)
            .open("r", encoding="utf-8")
        ) as fp:
            return json.load(fp)
    except (FileNotFoundError, ModuleNotFoundError) as exc:  # pragma: no cover - bundling bug
        logger.error("symbol_resolver: missing bundled master %s: %s", filename, exc)
        return {"instruments": []}


def reset_caches_for_tests() -> None:
    """Drop the in-process master caches (test helper)."""
    _nse_master.cache_clear()
    _bse_master.cache_clear()
    _us_master.cache_clear()


# ---------------------------------------------------------------------------
# Cheap hot-path helpers — pure dict lookups (no fuzzy match, no network).
# ---------------------------------------------------------------------------


def is_nse_symbol(symbol: str) -> bool:
    """True if the bare form of ``symbol`` is a known NSE equity/ETF."""
    return strip_exchange_suffix(symbol) in _nse_master()


def is_us_symbol(symbol: str) -> bool:
    """True if the bare form of ``symbol`` is a known US-listed ticker."""
    return strip_exchange_suffix(symbol).upper() in _us_master()


def is_bse_symbol(symbol: str) -> bool:
    """True if the bare form of ``symbol`` is a known BSE equity (incl. micro-caps)."""
    return strip_exchange_suffix(symbol) in _bse_master()


def bse_scrip_code(symbol: str) -> str | None:
    """Return the numeric BSE scrip code for ``symbol`` (the header endpoint key)."""
    entry = _bse_master().get(strip_exchange_suffix(symbol))
    return entry[2] if entry and entry[2] else None


def region_hint(symbol: str) -> str | None:
    """Infer a symbol's intrinsic region, or ``None`` if it is ambiguous.

    A ``.NS``/``.BO`` suffix is decisive (IN). For a bare ticker, an
    *unambiguous* India membership decides — GOLDBEES is NSE-only → IN, a
    BSE-only micro-cap (present in the BSE master, absent from US) → IN; AAPL is
    US-only → US; a ticker present in BOTH an India master AND the US master
    (e.g. an ADR) returns ``None`` so the user's active locale breaks the tie.
    Used by the provider registry to route a quote/history request to the right
    region's provider.
    """
    suffix_region = region_for_suffix(symbol)
    if suffix_region:
        return suffix_region
    bare = strip_exchange_suffix(symbol)
    in_india = bare in _nse_master() or bare in _bse_master()
    in_us = bare in _us_master()
    if in_india and not in_us:
        return REGION_IN
    if in_us and not in_india:
        return REGION_US
    return None


# ---------------------------------------------------------------------------
# Full resolution (name + ticker, fuzzy, locale-ranked).
# ---------------------------------------------------------------------------


def _suffix_exchange(symbol: str) -> str | None:
    """The exchange a Yahoo-style suffix pins ``symbol`` to, or ``None``.

    Finer-grained than :func:`services.locale.region_for_suffix` (which maps
    both ``.NS`` and ``.BO`` to ``IN``): an explicit ``.BO`` must pin the BSE
    identity, never silently rewrite to the NSE listing.
    """
    upper = symbol.strip().upper()
    if upper.endswith(".NS"):
        return "NSE"
    if upper.endswith(".BO"):
        return "BSE"
    return None


def _instrument_nse(symbol: str, score: float) -> Instrument:
    name, typ = _nse_master()[symbol]
    asset_class = "etf" if typ == "ETF" else "equity"
    return Instrument(
        symbol=symbol,
        name=name,
        exchange="NSE",
        region=REGION_IN,
        asset_class=asset_class,
        yahoo_symbol=f"{symbol}.NS",
        score=score,
    )


def _instrument_bse(symbol: str, score: float) -> Instrument:
    name, _group, _code = _bse_master()[symbol]
    return Instrument(
        symbol=symbol,
        name=name,
        exchange="BSE",
        region=REGION_IN,
        asset_class="equity",
        yahoo_symbol=f"{symbol}.BO",
        score=score,
    )


def _instrument_us(symbol: str, score: float) -> Instrument:
    name = _us_master()[symbol]
    return Instrument(
        symbol=symbol,
        name=name,
        exchange="US",
        region=REGION_US,
        asset_class="equity",
        yahoo_symbol=symbol,
        score=score,
    )


def _locale_bonus(region: str, instrument_region: str) -> float:
    """Small additive bonus so same-locale matches rank first on ties."""
    if region == REGION_GLOBAL:
        return 0.0
    return 0.08 if instrument_region == region else 0.0


def _name_score(query_lc: str, name_lc: str) -> float:
    """Fuzzy name score — exact / first-word / prefix / substring boosted.

    A query that exactly equals the company's *first word* ("apple" →
    "Apple Inc.") beats a mere prefix/substring, so the prominence-ordered
    masters (SEC market-cap order; nifty50-first NSE) then break ties toward the
    well-known instrument — "Apple" → AAPL, not a microcap that also starts "Apple".
    """
    if query_lc == name_lc:
        return 1.0
    first_word = name_lc.split(None, 1)[0] if name_lc else ""
    if query_lc == first_word:
        return 0.97
    if name_lc.startswith(query_lc):
        return 0.92
    if query_lc in name_lc:
        return 0.8
    return SequenceMatcher(None, query_lc, name_lc).ratio()


def resolve(query: str, region: str | None = None) -> Resolution:
    """Resolve ``query`` to an instrument + ranked candidates, locale-aware.

    Exact-ticker matches win outright; otherwise names are fuzzy-matched across
    both masters and ranked with a small same-locale bonus. ``region`` defaults
    to ``US`` ordering when not given.
    """
    region = region or REGION_US
    cleaned = query.strip()
    if not cleaned:
        return Resolution(query=query, best=None, candidates=[])

    upper = strip_exchange_suffix(cleaned)
    suffix_exchange = _suffix_exchange(cleaned)

    candidates: list[Instrument] = []

    # 1. Exact ticker hits (decisive). A .NS suffix pins the NSE identity, a
    #    .BO suffix pins BSE. A bare dual-listed ticker carries BOTH exchanges —
    #    NSE appended first, so the stable sort keeps it preferred on the tied
    #    score (trading data routes NSE; the BSE row is retained for BSE-only
    #    fundamentals/announcements).
    if upper in _nse_master() and suffix_exchange in (None, "NSE"):
        candidates.append(_instrument_nse(upper, 1.0 + _locale_bonus(region, REGION_IN)))
    if upper in _bse_master() and suffix_exchange in (None, "BSE"):
        candidates.append(_instrument_bse(upper, 1.0 + _locale_bonus(region, REGION_IN)))
    if upper in _us_master() and suffix_exchange is None:
        candidates.append(_instrument_us(upper, 1.0 + _locale_bonus(region, REGION_US)))

    if candidates:
        candidates.sort(key=lambda i: i.score, reverse=True)
        best = candidates[0]
        return Resolution(
            query=query,
            best=_clamp(best),
            candidates=[_clamp(c) for c in candidates[:_MAX_CANDIDATES]],
        )

    # 2. Fuzzy name match across the masters (locale-ranked). One canonical row
    #    per instrument: a dual-listed symbol is represented by its NSE row only
    #    (the BSE scan skips symbols the NSE master already carries), so a name
    #    never surfaces twice with two spellings of the same company.
    query_lc = cleaned.lower()
    scored: list[Instrument] = []
    nse_symbols = _nse_master()
    for sym, (name, _typ) in nse_symbols.items():
        s = _name_score(query_lc, name.lower())
        if s >= _MIN_NAME_SCORE:
            scored.append(_instrument_nse(sym, s + _locale_bonus(region, REGION_IN)))
    for sym, (name, _group, _code) in _bse_master().items():
        if sym in nse_symbols:
            continue  # canonical row is the NSE instrument (dual-listed)
        s = _name_score(query_lc, name.lower())
        if s >= _MIN_NAME_SCORE:
            scored.append(_instrument_bse(sym, s + _locale_bonus(region, REGION_IN)))
    for sym, name in _us_master().items():
        s = _name_score(query_lc, name.lower())
        if s >= _MIN_NAME_SCORE:
            scored.append(_instrument_us(sym, s + _locale_bonus(region, REGION_US)))

    scored.sort(key=lambda i: i.score, reverse=True)
    if scored:
        return Resolution(
            query=query,
            best=_clamp(scored[0]),
            candidates=[_clamp(c) for c in scored[:_MAX_CANDIDATES]],
        )

    # 3. Live keyless fallback (best-effort; never blocks).
    live = _live_lookup(cleaned, region)
    if live:
        return Resolution(query=query, best=live, candidates=[live])

    return Resolution(query=query, best=None, candidates=[])


def _clamp(instrument: Instrument) -> Instrument:
    """Clamp a possibly-bonus-inflated score to ``[0, 1]`` for reporting."""
    if instrument.score <= 1.0:
        return instrument
    return Instrument(
        symbol=instrument.symbol,
        name=instrument.name,
        exchange=instrument.exchange,
        region=instrument.region,
        asset_class=instrument.asset_class,
        yahoo_symbol=instrument.yahoo_symbol,
        score=1.0,
    )


def autocomplete(query: str, region: str | None = None, limit: int = 8) -> list[Instrument]:
    """Masters-only, network-free candidate list for on-keystroke autocomplete.

    Matches by ticker-prefix OR name-prefix/substring across both masters,
    locale-ranked, capped at ``limit``. Deliberately skips the fuzzy
    ``SequenceMatcher`` and the live ``yfinance.Search`` fallback that
    :func:`resolve` uses, so it stays a pure in-memory lookup fast enough to fire
    on every keystroke (<100ms over the bundled masters).
    """
    region = region or REGION_US
    bare = strip_exchange_suffix(query).strip()
    if not bare:
        return []
    q_sym = bare.upper()
    q_lc = query.strip().lower()

    def _score(sym: str, name: str) -> float | None:
        if sym == q_sym:
            return 1.0
        if sym.startswith(q_sym):
            return 0.95
        name_lc = name.lower()
        if name_lc.startswith(q_lc):
            return 0.9
        if q_lc in name_lc:
            return 0.8
        return None

    out: list[Instrument] = []
    nse_symbols = _nse_master()
    for sym, (name, _typ) in nse_symbols.items():
        s = _score(sym, name)
        if s is not None:
            out.append(_instrument_nse(sym, s + _locale_bonus(region, REGION_IN)))
    # BSE-only names (the micro-cap tail) — dual-listed symbols are skipped so
    # the canonical NSE row is the one (and only) candidate for that instrument,
    # keeping the list deduplicated and NSE-preferred without a second pass.
    for sym, (name, _group, _code) in _bse_master().items():
        if sym in nse_symbols:
            continue
        s = _score(sym, name)
        if s is not None:
            out.append(_instrument_bse(sym, s + _locale_bonus(region, REGION_IN)))
    for sym, name in _us_master().items():
        s = _score(sym, name)
        if s is not None:
            out.append(_instrument_us(sym, s + _locale_bonus(region, REGION_US)))
    out.sort(key=lambda i: i.score, reverse=True)
    return [_clamp(c) for c in out[:limit]]


def _live_lookup(query: str, region: str) -> Instrument | None:
    """Guarded ``yfinance.Search`` fallback for symbols not in the masters.

    Network/parse failures degrade to ``None`` (the caller surfaces an honest
    "unresolved" — never raw JSON, never a guess). Kept best-effort so the
    bundled-master path stays the fast, deterministic primary.
    """
    try:
        import yfinance as yf

        search = yf.Search(query, max_results=5, news_count=0)
        quotes = getattr(search, "quotes", None) or []
    except Exception as exc:  # noqa: BLE001 - any live-lookup failure is non-fatal
        logger.debug("symbol_resolver: live lookup failed for %r: %s", query, exc)
        return None

    for q in quotes:
        sym = str(q.get("symbol", "")).strip().upper()
        if not sym:
            continue
        name = str(q.get("shortname") or q.get("longname") or sym)
        # The exchange must agree with the suffix (master hygiene): a .BO hit is
        # a BSE identity, never relabelled NSE — the historic contradiction
        # ("NSE" + ICONIKSPEV.BO) broke scrip-code routing downstream.
        exchange = _suffix_exchange(sym)
        if exchange:
            bare = strip_exchange_suffix(sym)
            return Instrument(bare, name, exchange, REGION_IN, "equity", sym, 0.6)
        exch = str(q.get("exchange", "")).upper()
        if exch in {"NMS", "NYQ", "NGM", "ASE", "PCX", "BATS"}:
            return Instrument(sym, name, "US", REGION_US, "equity", sym, 0.6)
    return None


__all__ = [
    "DISAMBIGUATION_THRESHOLD",
    "Instrument",
    "Resolution",
    "autocomplete",
    "bse_scrip_code",
    "is_bse_symbol",
    "is_nse_symbol",
    "is_us_symbol",
    "region_hint",
    "reset_caches_for_tests",
    "resolve",
]
