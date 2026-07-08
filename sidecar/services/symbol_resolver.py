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

Confidence + band model (R10 rebuild, E1):

  Every candidate carries a match **band** (the rung that matched) and a raw
  **score** (the reported confidence — never inflated, never clamped):

  * band 6 exact-ticker  — score ``1.0`` (deterministic master hit).
  * band 5 marquee       — curated family alias (``marquee_aliases.json``);
    a primary binds at ``0.97``, a forced-disambiguation family rides ``0.6``.
  * band 4 name-exact    — query equals the (corporate-suffix-stripped) name.
  * band 3 first-word    — one-word query equals the name's first word (0.97).
  * band 2 prefix        — name prefix match (0.92).
  * band 1 substring     — name substring match (0.8).
  * band 0 fuzzy         — ``SequenceMatcher`` ratio (floor 0.6), applied ONLY
    to queries of <= 4 words after cleaning — a long keyword salad never
    scores by whole-string similarity (the Reliance→FRLCY/LNKS class).

  Ranking is the band tie-break ``(band, locale_match, score)`` — a
  cross-locale higher band ALWAYS beats a same-locale lower band; the old
  additive +0.08 locale bonus is gone. Acceptance is NOT decided here: the
  ONE policy lives in :mod:`services.resolution_policy`
  (:data:`DISAMBIGUATION_THRESHOLD` re-exports its ``ACCEPT``).

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
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache
from importlib import resources

from services import provider_health
from services.locale import (
    REGION_GLOBAL,
    REGION_IN,
    REGION_US,
    region_for_suffix,
    strip_exchange_suffix,
)
from services.resolution_policy import (
    ACCEPT as DISAMBIGUATION_THRESHOLD,  # the ONE threshold — re-exported, never redefined
)
from services.resolution_policy import (
    BAND_EXACT_TICKER,
    BAND_FIRST_WORD,
    BAND_FUZZY,
    BAND_MARQUEE,
    BAND_NAME_EXACT,
    BAND_PREFIX,
    BAND_SUBSTRING,
    decide,
)

logger = logging.getLogger(__name__)

# Minimum fuzzy score for a name match to be offered at all. Real matches score
# high — exact 1.0, first-word 0.97, prefix 0.92, substring 0.8 — so the floor is
# set above the noise band where SequenceMatcher gives unrelated strings ~0.5:
# better to return "unresolved" (and let the live lookup / an honest message take
# over) than to load the WRONG instrument on a weak coincidental match.
_MIN_NAME_SCORE = 0.6
# The fuzzy SequenceMatcher rung applies ONLY to queries of <= this many words
# (after cleaning). A longer query scores via its leading-word prefixes (the
# research-target prefix loop) — never via whole-string similarity (E1).
_MAX_FUZZY_WORDS = 4
# The score every non-deterministic candidate rides (live lookup rows, marquee
# forced-disambiguation families) — inside [REJECT, ACCEPT), so the resolution
# policy maps it to "disambiguate", never "bound".
_DISAMBIGUATE_SCORE = 0.6
_MAX_CANDIDATES = 6

# --- live-lookup budget (R11, D58d) -----------------------------------------
# The live yfinance.Search fallback is the ONE runtime network touchpoint in
# the resolver. It gets (a) a small in-process LRU keyed on (query, region) so
# an agent iterating the same unresolved names never re-hits the network, and
# (b) a failure cooldown — after ANY lookup failure the live rung is skipped
# entirely for a short window (returning [] immediately) instead of hammering
# a throttled/blocked upstream once per unresolved query.
_LIVE_CACHE_MAX_ENTRIES = 128
_LIVE_FAILURE_COOLDOWN_SECONDS = 60.0
_live_cache: OrderedDict[tuple[str, str], list[Instrument]] = OrderedDict()
_live_cache_lock = threading.Lock()
_live_cooldown_until = 0.0  # monotonic deadline; 0 = no cooldown

# Leading command verbs the models prepend to a company name ("research
# Reliance") — stripped during query cleaning so the verb never fuzzy-binds an
# unrelated company (REFR — "Research Frontiers Inc"). Only stripped while more
# than one token remains, so a company genuinely named with one of these still
# resolves on its remaining tokens.
#
# A company whose name BEGINS with one of these verbs resolves only on its
# remaining tokens — "Lookup Technologies" matches the substring hit on the
# leftover ("Technologies" → PLTR at 0.8), and "Research Frontiers Inc" reaches
# the substring band instead of name-exact. The R10 review hardening makes this
# SAFE: a substring band (1) never binds outright (resolution_policy.decide
# requires band >= prefix), so the leftover surfaces as a "did you mean?"
# disambiguation, never a silent wrong-entity bind — while "research Reliance"
# still binds RELIANCE (its leftover "Reliance" reaches first-word band 3).
_LEAD_VERBS = frozenset(
    {"research", "analyze", "analyse", "investigate", "explore", "study", "review", "lookup"}
)
_LEAD_FILLERS = frozenset({"on", "about", "into"})
# Punctuation stripped from token EDGES during cleaning ("reliance," →
# "reliance"). Deliberately excludes the dot when it ends an exchange suffix
# (handled by tokenization order: suffixes like ".NS" keep their letters).
_EDGE_PUNCT = ".,;:!?\"'()[]"

# Generic second words that make a two-word query a marquee key by its leading
# word ("tata stock" → "tata").
_GENERIC_SECOND_WORDS = frozenset({"group", "stock", "stocks", "share", "shares"})

# Corporate suffixes stripped from the END of a company name before comparison,
# so "RELIANCE, INC." and "Reliance Industries Limited" both compare on their
# distinctive tokens and locale (not punctuation) breaks the tie.
_CORP_SUFFIXES = frozenset(
    {
        "limited",
        "ltd",
        "inc",
        "incorporated",
        "corp",
        "corporation",
        "company",
        "co",
        "plc",
        "llc",
        "lp",
    }
)


@dataclass(frozen=True)
class Instrument:
    """One resolved instrument candidate.

    Invariant (master hygiene): ``exchange`` always agrees with the
    ``yahoo_symbol`` suffix — NSE ↔ ``.NS``, BSE ↔ ``.BO``, US ↔ no suffix.
    ``band`` records the match rung (see :mod:`services.resolution_policy`);
    ``score`` is the RAW reported confidence — never bonus-inflated, never
    clamped.
    """

    symbol: str  # bare exchange symbol — GOLDBEES, AAPL, ICONIKSPEV
    name: str
    exchange: str  # NSE | BSE | US
    region: str  # IN | US
    asset_class: str  # equity | etf
    yahoo_symbol: str  # GOLDBEES.NS, ICONIKSPEV.BO, AAPL
    score: float = 1.0
    band: int = BAND_FUZZY


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
        # Delegates to the ONE policy so this surface and the agent tool can
        # never disagree (the pre-R10 two-truths defect).
        return self.best is not None and decide(self).outcome == "disambiguate"


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


@lru_cache(maxsize=1)
def _marquee_aliases() -> dict[str, dict]:
    """The curated marquee alias table (R10, E1): family name → primary +
    alternatives, or a forced-disambiguation candidate list."""
    raw = _load_master("marquee_aliases.json", fallback={"aliases": {}})
    aliases = raw.get("aliases")
    return aliases if isinstance(aliases, dict) else {}


def _load_master(filename: str, *, fallback: dict | None = None) -> dict:
    try:
        with (
            resources.files("services.resolver_masters")
            .joinpath(filename)
            .open("r", encoding="utf-8")
        ) as fp:
            return json.load(fp)
    except (FileNotFoundError, ModuleNotFoundError) as exc:  # pragma: no cover - bundling bug
        logger.error("symbol_resolver: missing bundled master %s: %s", filename, exc)
        return fallback if fallback is not None else {"instruments": []}


def reset_caches_for_tests() -> None:
    """Drop the in-process master caches + the live-lookup budget (test helper)."""
    _nse_master.cache_clear()
    _bse_master.cache_clear()
    _us_master.cache_clear()
    _marquee_aliases.cache_clear()
    _reset_live_lookup_for_tests()


def _reset_live_lookup_for_tests() -> None:
    """Drop the live-lookup LRU + cooldown only (cheaper than a master reload)."""
    global _live_cooldown_until
    with _live_cache_lock:
        _live_cache.clear()
        _live_cooldown_until = 0.0


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


def _instrument_nse(symbol: str, score: float, band: int = BAND_FUZZY) -> Instrument:
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
        band=band,
    )


def _instrument_bse(symbol: str, score: float, band: int = BAND_FUZZY) -> Instrument:
    name, _group, _code = _bse_master()[symbol]
    return Instrument(
        symbol=symbol,
        name=name,
        exchange="BSE",
        region=REGION_IN,
        asset_class="equity",
        yahoo_symbol=f"{symbol}.BO",
        score=score,
        band=band,
    )


def _instrument_us(symbol: str, score: float, band: int = BAND_FUZZY) -> Instrument:
    name = _us_master()[symbol]
    return Instrument(
        symbol=symbol,
        name=name,
        exchange="US",
        region=REGION_US,
        asset_class="equity",
        yahoo_symbol=symbol,
        score=score,
        band=band,
    )


def _locale_rank(region: str, instrument_region: str) -> int:
    """1 when the instrument is in the session's locale; GLOBAL prefers none.

    A SORT KEY component only — never added to the reported score (the old
    +0.08 additive bonus inflated a US prefix hit past an NSE first-word hit)."""
    if region == REGION_GLOBAL:
        return 0
    return 1 if instrument_region == region else 0


def _clean_tokens(query: str) -> list[str]:
    """Tokenize a query for matching: trim edge punctuation per token
    ("reliance," → "reliance") and drop leading command verbs ("research
    Reliance" → "Reliance") while more than one token remains."""
    tokens = [t.strip(_EDGE_PUNCT) for t in query.strip().split()]
    tokens = [t for t in tokens if t]
    while len(tokens) > 1 and tokens[0].lower() in _LEAD_VERBS:
        tokens = tokens[1:]
        while len(tokens) > 1 and tokens[0].lower() in _LEAD_FILLERS:
            tokens = tokens[1:]
    return tokens


def _strip_corporate_suffix(name_lc: str) -> str:
    """Drop trailing corporate suffixes + edge punctuation from a name —
    "reliance, inc." → "reliance", "tata steel limited" → "tata steel"."""
    tokens = [t.strip(_EDGE_PUNCT) for t in name_lc.split()]
    tokens = [t for t in tokens if t]
    while len(tokens) > 1 and tokens[-1] in _CORP_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def _name_score(query_lc: str, name_lc: str, query_words: int) -> tuple[int, float] | None:
    """Score a name match as ``(band, raw_score)``, or ``None`` for no match.

    Comparisons run against the corporate-suffix-stripped name so US
    "RELIANCE, INC." and NSE "Reliance Industries Limited" land in the SAME
    band for a one-word query and locale breaks the tie. The fuzzy
    SequenceMatcher rung fires ONLY for queries of <= ``_MAX_FUZZY_WORDS``
    words — a long keyword salad never scores by whole-string similarity (E1).
    """
    if query_lc == name_lc:
        return BAND_NAME_EXACT, 1.0
    stripped = _strip_corporate_suffix(name_lc)
    if query_words > 1 and query_lc == stripped:
        return BAND_NAME_EXACT, 1.0
    if query_words == 1:
        first_word = stripped.split(None, 1)[0] if stripped else ""
        if query_lc == first_word:
            return BAND_FIRST_WORD, 0.97
    if name_lc.startswith(query_lc) or stripped.startswith(query_lc):
        return BAND_PREFIX, 0.92
    if query_lc in name_lc:
        return BAND_SUBSTRING, 0.8
    if query_words <= _MAX_FUZZY_WORDS:
        ratio = SequenceMatcher(None, query_lc, name_lc).ratio()
        if ratio >= _MIN_NAME_SCORE:
            return BAND_FUZZY, ratio
    return None


def _marquee_resolution(query: str, cleaned: str, region: str) -> Resolution | None:
    """The marquee alias stage (after exact-ticker, before fuzzy).

    Applies under IN/GLOBAL when the cleaned query is a one-word family name —
    or a two-word query whose second word is generic ("tata stock"). A primary
    alias binds at 0.97 with its alternatives as candidates; a curated family
    (tata/bajaj/adani/birla) rides ``_DISAMBIGUATE_SCORE`` so the policy FORCES
    an explicit choice. Symbols missing from the masters are skipped (the test
    suite verifies the bundled table against the NSE master).
    """
    if region not in (REGION_IN, REGION_GLOBAL):
        return None
    tokens = cleaned.split()
    if len(tokens) == 1:
        key = tokens[0].lower()
    elif len(tokens) == 2 and tokens[1].lower() in _GENERIC_SECOND_WORDS:
        key = tokens[0].lower()
    else:
        return None
    entry = _marquee_aliases().get(key)
    if not isinstance(entry, dict):
        return None

    def _inst(sym: str, score: float) -> Instrument | None:
        sym = sym.strip().upper()
        if sym in _nse_master():
            return _instrument_nse(sym, score, band=BAND_MARQUEE)
        if sym in _bse_master():
            return _instrument_bse(sym, score, band=BAND_MARQUEE)
        return None

    primary_sym = entry.get("primary")
    if isinstance(primary_sym, str) and primary_sym:
        best = _inst(primary_sym, 0.97)
        if best is None:
            return None
        candidates = [best]
        for alt in entry.get("alternatives") or []:
            inst = _inst(str(alt), _DISAMBIGUATE_SCORE)
            if inst is not None:
                candidates.append(inst)
        return Resolution(query=query, best=best, candidates=candidates[:_MAX_CANDIDATES])

    curated: list[Instrument] = []
    for sym in entry.get("candidates") or []:
        inst = _inst(str(sym), _DISAMBIGUATE_SCORE)
        if inst is not None:
            curated.append(inst)
    if not curated:
        return None
    return Resolution(query=query, best=curated[0], candidates=curated[:_MAX_CANDIDATES])


def resolve(query: str, region: str) -> Resolution:
    """Resolve ``query`` to an instrument + ranked candidates, locale-aware.

    ``region`` is REQUIRED — callers pass ``config.get_region()`` (the old
    silent ``US`` default mis-ranked every IN session). Brief §2 spelled the
    signature ``resolve(query, *, region)``; ``region`` stays positional-or-
    keyword (no bare ``*``) because the unowned ``routers/resolve.py`` calls
    ``asyncio.to_thread(symbol_resolver.resolve, query, active_region)``
    positionally — required-ness is the load-bearing half of the spec, and it
    holds. Stages: exact ticker →
    marquee aliases (IN/GLOBAL) → banded name match → live keyless fallback.
    Ranking is ``(band, locale_match, raw_score)``; reported confidence is the
    raw score — acceptance is the resolution policy's call, not this module's.
    """
    if region not in (REGION_US, REGION_IN, REGION_GLOBAL):
        # An unknown region gets NO locale preference rather than a silent US one.
        region = REGION_GLOBAL
    tokens = _clean_tokens(query)
    if not tokens:
        return Resolution(query=query, best=None, candidates=[])
    cleaned = " ".join(tokens)

    upper = strip_exchange_suffix(cleaned)
    suffix_exchange = _suffix_exchange(cleaned)

    candidates: list[Instrument] = []

    # 1. Exact ticker hits (decisive). A .NS suffix pins the NSE identity, a
    #    .BO suffix pins BSE. A bare dual-listed ticker carries BOTH exchanges —
    #    NSE appended first, so the stable locale sort keeps it preferred
    #    (trading data routes NSE; the BSE row is retained for BSE-only
    #    fundamentals/announcements).
    if upper in _nse_master() and suffix_exchange in (None, "NSE"):
        candidates.append(_instrument_nse(upper, 1.0, band=BAND_EXACT_TICKER))
    if upper in _bse_master() and suffix_exchange in (None, "BSE"):
        candidates.append(_instrument_bse(upper, 1.0, band=BAND_EXACT_TICKER))
    if upper in _us_master() and suffix_exchange is None:
        candidates.append(_instrument_us(upper, 1.0, band=BAND_EXACT_TICKER))

    if candidates:
        candidates.sort(key=lambda i: _locale_rank(region, i.region), reverse=True)
        return Resolution(
            query=query,
            best=candidates[0],
            candidates=candidates[:_MAX_CANDIDATES],
        )

    # 2. Marquee aliases (curated; IN/GLOBAL only) — a family name either binds
    #    its canonical primary or forces a curated disambiguation, never a
    #    silent first-word guess ("Tata" → TCS at a clamped 1.0 was E1).
    marquee = _marquee_resolution(query, cleaned, region)
    if marquee is not None:
        return marquee

    # 3. Banded name match across the masters. One canonical row per
    #    instrument: a dual-listed symbol is represented by its NSE row only
    #    (the BSE scan skips symbols the NSE master already carries), so a name
    #    never surfaces twice with two spellings of the same company.
    query_lc = cleaned.lower()
    n_words = len(tokens)
    scored: list[tuple[int, int, float, Instrument]] = []

    def _append(band_score: tuple[int, float] | None, build, sym: str) -> None:
        if band_score is None:
            return
        band, s = band_score
        inst = build(sym, s, band)
        scored.append((band, _locale_rank(region, inst.region), s, inst))

    nse_symbols = _nse_master()
    for sym, (name, _typ) in nse_symbols.items():
        _append(_name_score(query_lc, name.lower(), n_words), _instrument_nse, sym)
    for sym, (name, _group, _code) in _bse_master().items():
        if sym in nse_symbols:
            continue  # canonical row is the NSE instrument (dual-listed)
        _append(_name_score(query_lc, name.lower(), n_words), _instrument_bse, sym)
    for sym, name in _us_master().items():
        _append(_name_score(query_lc, name.lower(), n_words), _instrument_us, sym)

    # Band tie-break: (band, locale, score) — stable, so the prominence-ordered
    # masters break exact ties toward the well-known instrument. The locale
    # component IS the chooser's region tie-break (R11, D58c / V5): under an IN
    # session a foreign row can never outrank an IN row at the same band, so a
    # disambiguation list for "Reliance Q4 results" leads with RELIANCE (NSE),
    # never FRLCY/FLNCF (US OTC).
    scored.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)
    if scored:
        ranked = [t[3] for t in scored]
        return Resolution(query=query, best=ranked[0], candidates=ranked[:_MAX_CANDIDATES])

    # 4. Live keyless fallback (best-effort; never blocks; never binds — every
    #    row rides _DISAMBIGUATE_SCORE, which the policy maps to disambiguate).
    live = _live_lookup(cleaned, region) or []
    if live:
        return Resolution(query=query, best=live[0], candidates=live[:_MAX_CANDIDATES])

    return Resolution(query=query, best=None, candidates=[])


def autocomplete(query: str, region: str | None = None, limit: int = 8) -> list[Instrument]:
    """Masters-only, network-free candidate list for on-keystroke autocomplete.

    Matches by ticker-prefix OR name-prefix/substring across both masters,
    locale-ranked, capped at ``limit``. Deliberately skips the fuzzy
    ``SequenceMatcher`` and the live ``yfinance.Search`` fallback that
    :func:`resolve` uses, so it stays a pure in-memory lookup fast enough to fire
    on every keystroke (<100ms over the bundled masters).
    """
    region = region or REGION_GLOBAL
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
            out.append(_instrument_nse(sym, s))
    # BSE-only names (the micro-cap tail) — dual-listed symbols are skipped so
    # the canonical NSE row is the one (and only) candidate for that instrument,
    # keeping the list deduplicated and NSE-preferred without a second pass.
    for sym, (name, _group, _code) in _bse_master().items():
        if sym in nse_symbols:
            continue
        s = _score(sym, name)
        if s is not None:
            out.append(_instrument_bse(sym, s))
    for sym, name in _us_master().items():
        s = _score(sym, name)
        if s is not None:
            out.append(_instrument_us(sym, s))
    # Locale breaks ties as a SORT KEY, never an additive score bonus.
    out.sort(key=lambda i: (i.score, _locale_rank(region, i.region)), reverse=True)
    return out[:limit]


def _live_lookup(query: str, region: str) -> list[Instrument]:
    """Guarded ``yfinance.Search`` fallback for symbols not in the masters.

    Collects ALL hits (up to 5) as candidates at :data:`_DISAMBIGUATE_SCORE` —
    a live row is never master-deterministic, so the policy maps it to
    "disambiguate", never "bound". Under an IN session the ``.NS``/``.BO``
    rows rank first. Network/parse failures degrade to ``[]`` (the caller
    surfaces an honest "unresolved" — never raw JSON, never a guess).

    Budgeted (R11, D58d): results — including a successful empty search — are
    LRU-cached per ``(query, region)`` so repeated unresolved queries never
    re-hit the network; ANY failure opens a short module-level cooldown during
    which the live rung returns ``[]`` immediately. Rate-limit-shaped failures
    (``YFRateLimitError``) are reported to :mod:`services.provider_health`
    (the Yahoo family shares one IP reputation across every yfinance path);
    a healthy round-trip reports success.
    """
    global _live_cooldown_until
    key = (query, region)
    with _live_cache_lock:
        cached = _live_cache.get(key)
        if cached is not None:
            _live_cache.move_to_end(key)
            return list(cached)
        if time.monotonic() < _live_cooldown_until:
            return []

    try:
        import yfinance as yf

        search = yf.Search(query, max_results=5, news_count=0)
        quotes = getattr(search, "quotes", None) or []
    except Exception as exc:  # noqa: BLE001 - any live-lookup failure is non-fatal
        with _live_cache_lock:
            _live_cooldown_until = time.monotonic() + _LIVE_FAILURE_COOLDOWN_SECONDS
        if type(exc).__name__ == "YFRateLimitError":
            provider_health.record_rate_limited()
        logger.debug("symbol_resolver: live lookup failed for %r: %s", query, exc)
        return []
    provider_health.record_success()

    out: list[Instrument] = []
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
            out.append(
                Instrument(bare, name, exchange, REGION_IN, "equity", sym, _DISAMBIGUATE_SCORE)
            )
            continue
        exch = str(q.get("exchange", "")).upper()
        if exch in {"NMS", "NYQ", "NGM", "ASE", "PCX", "BATS"}:
            out.append(Instrument(sym, name, "US", REGION_US, "equity", sym, _DISAMBIGUATE_SCORE))
    if region == REGION_IN:
        out.sort(key=lambda i: i.region == REGION_IN, reverse=True)
    with _live_cache_lock:
        _live_cache[key] = list(out)
        _live_cache.move_to_end(key)
        while len(_live_cache) > _LIVE_CACHE_MAX_ENTRIES:
            _live_cache.popitem(last=False)
    return out


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
