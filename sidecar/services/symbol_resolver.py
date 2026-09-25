"""Symbol resolution — free-text / ticker → a concrete instrument (Pass B / B1).

FR-061: resolve a name or ticker to ``(ticker, exchange, region, asset_class)``
keyless-first, locale-ranked, with disambiguation when confidence is low —
"Tata Steel" → TATASTEEL on NSE for an IN session, "GOLDBEES" → the NSE gold ETF.

Design (research §A.3 — keep resolution and data-fetch separate):

  * **Stage 1 — bundled masters (offline, deterministic):** the SEC
    ``company_tickers`` snapshot (US) + the NSE ``EQUITY_L`` + Emerge + ETF lists
    + the full regenerated BSE scrip master, shipped under
    :mod:`services.resolver_masters` and unioned with a daily runtime refresh of
    the same exchange lists (R15-DATA-017). An exact ticker hit is instant; a
    name query is fuzzy-matched and locale-ranked.
  * **Stage 2 — live keyless fallback (best-effort):** when the masters miss,
    or their best hit is a fuzzy match on generic words only, a guarded
    ``yfinance.Search`` lookup catches names/tickers not in the bundle.
    Network-guarded so it never blocks (and tests of bundled symbols never touch
    the network).

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
from dataclasses import dataclass, field, replace
from difflib import SequenceMatcher
from functools import lru_cache
from importlib import resources

import config
from services import nse_symbol_change, provider_health
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
    same_instrument,
)
from services.resolver_masters import regenerate_bse_master, regenerate_nse_master
from services.resolver_masters.regenerate_bse_master import is_rights_entitlement

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
# A successful EMPTY search expires (R15-DATA-097): the live rung is the path to
# a post-snapshot listing, so a stale negative would hide it until restart.
_LIVE_EMPTY_TTL_SECONDS = 300.0
_live_cache: OrderedDict[tuple[str, str], tuple[float, list[Instrument]]] = OrderedDict()
_live_cache_lock = threading.Lock()
_live_cooldown_until = 0.0  # monotonic deadline; 0 = no cooldown
# A name token found in at least this many master names is generic ("engineering",
# "green", "bank"); a fuzzy best hit sharing only such tokens with the query does
# not stop the live rung (R15-DATA-017). ponytail: a document-frequency cut, not
# a curated list; tune the number if a real name misfires.
_GENERIC_TOKEN_MIN_NAMES = 20

# --- runtime master refresh (R15-DATA-017, D-B5-7) ----------------------------
# The bundled masters are a snapshot; a daily off-hot-path fetch of the same
# exchange lists lands in ``<data-dir>/resolver_masters/`` and the loaders union
# it with the bundled file. Membership never does network I/O at call time.
_REFRESH_INTERVAL_SECONDS = 24 * 60 * 60
# How often the refresh thread checks for a day-old copy (a stat when fresh), so
# a fetch that failed at boot is retried within the hour, not the next day.
_REFRESH_CHECK_SECONDS = 60 * 60
_REFRESH_FETCHERS = {
    "nse_instruments.json": regenerate_nse_master.fetch_master,
    "bse_instruments.json": regenerate_bse_master.fetch_master,
}
_refresh_lock = threading.Lock()
_refresh_thread: threading.Thread | None = None

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
        # R15-DATA-059: a private-to-public conversion ahead of an IPO renames
        # "X Private Limited"/"X Pvt Ltd" to "X Limited" — the SAME company,
        # so the class of query (the old Pvt-Ltd legal name) should bind the
        # current listing generically, not one former-names row per company.
        "private",
        "pvt",
    }
)

# Corporate-name SEAM canonicalization (R13): token spellings that differ only
# cosmetically between a company's legal name and the exchange master
# ("&"⟺"and", "pvt"⟺"private") — normalized symmetrically on BOTH query and name
# so an exact-modulo-suffix legal name ("Bilcare Ltd" vs the master's "Bilcare
# Limited") lands in the name-exact band and binds, instead of scoring fuzzy and
# stranding under the accept band. The Ltd⟺Limited half is handled by the shared
# corporate-suffix strip (both are in ``_CORP_SUFFIXES``).
_NAME_CANON_MAP = {
    "&": "and",
    "pvt": "private",
    "pvt.": "private",
    "&amp;": "and",
}


@dataclass(frozen=True)
class RenameAnnotation:
    """Why an instrument's symbol was answered as its CURRENT (renamed) form.

    Attached (R12, D66) when the NSE symbol-change lane rewrote a retired old
    symbol to its current one — e.g. GUJGASLTD → GUJENERGY effective 2026-07-01.
    ``effective_date`` is an ISO ``YYYY-MM-DD`` string.
    """

    renamed_from: str
    renamed_to: str
    effective_date: str
    note: str


@dataclass(frozen=True)
class Instrument:
    """One resolved instrument candidate.

    Invariant (master hygiene): ``exchange`` always agrees with the
    ``yahoo_symbol`` suffix — NSE ↔ ``.NS``, BSE ↔ ``.BO``, US ↔ no suffix.
    ``band`` records the match rung (see :mod:`services.resolution_policy`);
    ``score`` is the RAW reported confidence — never bonus-inflated, never
    clamped. ``rename`` is set only when the symbol-change lane answered the
    CURRENT symbol for a retired one (never a silent swap — the provenance is
    explicit).
    """

    symbol: str  # bare exchange symbol — GOLDBEES, AAPL, ICONIKSPEV
    name: str
    exchange: str  # NSE | BSE | US
    region: str  # IN | US
    asset_class: str  # equity | etf
    yahoo_symbol: str  # GOLDBEES.NS, ICONIKSPEV.BO, AAPL
    score: float = 1.0
    band: int = BAND_FUZZY
    rename: RenameAnnotation | None = None
    # --- additive identity enrichment (R13) --------------------------------
    # A READ-ONLY join over the bundled BSE master + india_sector_map.json,
    # applied at resolve time (:func:`_enrich_instrument`). Every field stays
    # ``None`` when the bundled data does not carry it — NEVER fabricated. These
    # anchor the entity for the research query builder and the collision-proof
    # relevance gate: a ≤3-char ticker (KSE, ITC) shadowed by a famous foreign
    # entity is disambiguated by its ISIN / exchange / industry, not just its
    # colliding symbol.
    isin: str | None = None  # INE953E01022 (KSE Ltd) — BSE master / sector map
    bse_code: str | None = None  # numeric BSE scrip code (519421) when BSE-listed
    industry: str | None = None  # india_sector_map industry_raw (None for uncovered names)
    former_name: str | None = None  # the retired SYMBOL (NSE ticker rename) or the
    # retired legal NAME (R15-DATA-059 former-name scan match) this listing carried
    board: str | None = None  # "SME" (BSE M* group / NSE Emerge) | "mainboard"; None for US
    exchange_group: str | None = None  # the raw BSE group (A, B, X, M, MT, ...)
    face_value: float | None = None  # listed face value (INR), from the masters


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


def instrument_payload(instrument: Instrument) -> dict[str, object]:
    """The ONE wire shape of an :class:`Instrument` (the ``/resolve`` routes and
    the ``resolve_symbol`` agent tool both project through it)."""
    payload: dict[str, object] = {
        "symbol": instrument.symbol,
        "name": instrument.name,
        "exchange": instrument.exchange,
        "region": instrument.region,
        "asset_class": instrument.asset_class,
        "yahoo_symbol": instrument.yahoo_symbol,
        "confidence": round(instrument.score, 4),
        # R13 additive identity enrichment — read-only ISIN / scrip / industry
        # join. Null when the bundled data does not carry it (US names, an
        # uncovered micro-cap), never fabricated.
        "isin": instrument.isin,
        "bse_code": instrument.bse_code,
        "industry": instrument.industry,
        "former_name": instrument.former_name,
        "board": instrument.board,
        "exchange_group": instrument.exchange_group,
        "face_value": instrument.face_value,
    }
    # R12 (D66): a symbol answered as its CURRENT form carries explicit rename
    # provenance — the picker can badge "renamed from …", never a silent swap.
    if instrument.rename is not None:
        payload["rename"] = {
            "renamed_from": instrument.rename.renamed_from,
            "renamed_to": instrument.rename.renamed_to,
            "effective_date": instrument.rename.effective_date,
            "note": instrument.rename.note,
        }
    return payload


# ---------------------------------------------------------------------------
# Master loading (bundled JSON, cached in-process).
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _nse_master() -> dict[str, tuple[str, str]]:
    """``{SYMBOL: (name, type)}`` for NSE equities, Emerge names and ETFs (type
    EQ | SM | ETF): the bundled master unioned with the runtime-refreshed one (a
    refreshed row wins; bundled order is kept). Rights-entitlement lines are
    skipped."""
    out: dict[str, tuple[str, str]] = {}
    for raw in _master_layers("nse_instruments.json"):
        for row in raw.get("instruments", []):
            sym = str(row[0]).strip().upper()
            name = str(row[1]).strip()
            typ = str(row[2]).strip().upper() if len(row) > 2 else "EQ"
            if sym and not is_rights_entitlement(sym, "", ""):
                out[sym] = (name, typ)
    return out


@lru_cache(maxsize=1)
def _bse_master() -> dict[str, tuple[str, str, str, str]]:
    """``{SYMBOL: (name, group, scrip_code, isin)}`` for BSE equities.

    Rows in ``bse_instruments.json`` are ``[SCRIP_CODE, SYMBOL, NAME, GROUP,
    ISIN, STATUS]``. The micro-cap tail (groups B/X/XT/T/Z) is the coverage NSE
    never listed — keyed by the bare ticker for ``is_bse_symbol``/``region_hint``
    and carrying the numeric scrip code the BSE quote header endpoint needs. The
    ISIN (R13) is the instrument's stable global identity; it rides the resolve
    payload so a BSE-only micro-cap (KSE Ltd, INE953E01022) is anchored to the
    ONE real company, never its foreign-ticker collision.
    """
    out: dict[str, tuple[str, str, str, str]] = {}
    for raw in _master_layers("bse_instruments.json"):
        for row in raw.get("instruments", []):
            code = str(row[0]).strip() if len(row) > 0 else ""
            sym = str(row[1]).strip().upper() if len(row) > 1 else ""
            name = str(row[2]).strip() if len(row) > 2 else ""
            group = str(row[3]).strip().upper() if len(row) > 3 else ""
            isin = str(row[4]).strip().upper() if len(row) > 4 else ""
            if sym and not is_rights_entitlement(sym, group, isin):
                out[sym] = (name, group, code, isin)
    return out


@lru_cache(maxsize=1)
def _india_sector_map() -> dict[str, dict]:
    """``{BASE_SYMBOL: record}`` from bundled ``india_sector_map.json`` (R13).

    The SAME bundled file :mod:`services.screener_universe_india` reads — each
    record carries ``isin / scrip_code / industry_raw / sector / sector_source /
    shares_outstanding``. Read-only join at resolve time; a missing/garbled map
    degrades to ``{}`` so resolution never depends on the sector data. An
    uncovered micro-cap (KSE) is PRESENT with ``industry_raw: None`` — the join
    surfaces that honestly (``industry = None``), never a fabricated sector.
    """
    raw = _load_master("india_sector_map.json", fallback={"records": []})
    out: dict[str, dict] = {}
    for rec in raw.get("records", []):
        if not isinstance(rec, dict):
            continue
        sym = str(rec.get("symbol") or "").strip().upper()
        if sym and sym not in out:
            out[sym] = rec
    return out


@lru_cache(maxsize=1)
def _bse_scrip_index() -> dict[str, str]:
    """``{SCRIP_CODE: SYMBOL}`` for BSE equities (the numeric-code resolve lane).

    A bare all-digit query (a BSE scrip code like ``509470``) is the header
    endpoint's native instrument id — EXACT and unambiguous, since a numeric code
    never appears in the alphabetic NSE/US masters — so it binds the one BSE row
    that carries that code. Built once from the loaded master (which already
    carries the scrip code per row); on a duplicate code the first row wins.
    """
    out: dict[str, str] = {}
    for sym, (_name, _group, code, _isin) in _bse_master().items():
        if code and code not in out:
            out[code] = sym
    return out


@lru_cache(maxsize=2)
def _face_values(filename: str) -> dict[str, float]:
    """``{SYMBOL: face value}`` from a master's ``face_values`` map (bundled, then
    the refreshed copy). A master generated before the map existed adds nothing."""
    out: dict[str, float] = {}
    for raw in _master_layers(filename):
        values = raw.get("face_values")
        if isinstance(values, dict):
            for sym, value in values.items():
                if isinstance(value, int | float):
                    out[str(sym).strip().upper()] = float(value)
    return out


@lru_cache(maxsize=1)
def _nse_listing_dates() -> dict[str, str]:
    """``{SYMBOL: ISO date}`` from the NSE master's ``listing_dates`` map (the
    exchange DATE OF LISTING; bundled, then the refreshed copy)."""
    out: dict[str, str] = {}
    for raw in _master_layers("nse_instruments.json"):
        values = raw.get("listing_dates")
        if isinstance(values, dict):
            out.update({str(sym).strip().upper(): str(day) for sym, day in values.items()})
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


@lru_cache(maxsize=1)
def _former_names() -> dict[str, dict[str, tuple[str, ...]]]:
    """``{"us": {SYMBOL: (former_name, ...)}, "in": {SYMBOL: (former_name, ...)}}``
    from the bundled ``former_names.json`` (R15-DATA-059, generated offline by
    :mod:`services.resolver_masters.regenerate_former_names`).

    Keyed by REGION rather than exchange because the US side is keyed by SEC
    ticker (no NSE/BSE distinction) and the IN side by NSE symbol; a BSE-only
    IN symbol (the manual-seed case) rides the same ``"in"`` bucket. Order per
    symbol follows the source: US newest→oldest (SEC ``formerNames``), IN
    oldest→newest (NSE namechange.csv); a missing/garbled master degrades to
    ``{}`` so resolution never depends on it."""
    raw = _load_master("former_names.json", fallback={"former_names": {}})
    payload = raw.get("former_names")
    out: dict[str, dict[str, tuple[str, ...]]] = {"us": {}, "in": {}}
    if isinstance(payload, dict):
        for region_key in ("us", "in"):
            region_map = payload.get(region_key)
            if not isinstance(region_map, dict):
                continue
            for sym, names in region_map.items():
                if isinstance(names, list) and names:
                    cleaned = tuple(str(n).strip() for n in names if str(n).strip())
                    if cleaned:
                        out[region_key][str(sym).strip().upper()] = cleaned
    return out


def _load_master(filename: str, *, fallback: dict | None = None) -> dict:
    try:
        with (
            resources.files("services.resolver_masters")
            .joinpath(filename)
            .open("r", encoding="utf-8")
        ) as fp:
            return json.load(fp)
    except (OSError, ModuleNotFoundError, ValueError) as exc:  # bundling bug / garbled JSON
        logger.error("symbol_resolver: missing or garbled bundled master %s: %s", filename, exc)
        return fallback if fallback is not None else {"instruments": []}


def _refreshed_master(filename: str) -> dict | None:
    """The runtime-refreshed copy of a bundled master, or ``None``.

    The first call starts the daily background refresh; reading the file is the
    only I/O here (no network on the hot path)."""
    _schedule_master_refresh()
    try:
        raw = json.loads((config.get_data_dir() / "resolver_masters" / filename).read_text("utf-8"))
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def _master_layers(filename: str) -> list[dict]:
    """The bundled master, then its refreshed copy when one exists."""
    refreshed = _refreshed_master(filename)
    bundled = _load_master(filename)
    return [bundled, refreshed] if refreshed else [bundled]


def _schedule_master_refresh() -> None:
    """Start the daily refresh thread once per process (daemon, off the hot path)."""
    global _refresh_thread
    with _refresh_lock:
        if _refresh_thread is None:
            _refresh_thread = threading.Thread(
                target=_refresh_loop, name="resolver-master-refresh", daemon=True
            )
            _refresh_thread.start()


def _refresh_loop() -> None:
    while True:
        refresh_masters()
        time.sleep(_REFRESH_CHECK_SECONDS)


def refresh_masters() -> None:
    """Fetch the NSE and BSE lists into ``<data-dir>/resolver_masters/`` when the
    copy there is missing or a day old, then drop the loader caches so the next
    lookup unions the new rows. A failed fetch keeps the previous copy."""
    folder = config.get_data_dir() / "resolver_masters"
    folder.mkdir(parents=True, exist_ok=True)
    fetched = False
    for filename, fetch in _REFRESH_FETCHERS.items():
        path = folder / filename
        if path.exists() and time.time() - path.stat().st_mtime < _REFRESH_INTERVAL_SECONDS:
            continue
        try:
            master = fetch()
        except (Exception, SystemExit) as exc:  # noqa: BLE001 - the bundled master still serves
            logger.warning("symbol_resolver: master refresh failed for %s: %s", filename, exc)
            continue
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(master, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
        fetched = True
    if fetched:
        _nse_master.cache_clear()
        _bse_master.cache_clear()
        _bse_scrip_index.cache_clear()
        _generic_tokens.cache_clear()
        _face_values.cache_clear()
        _nse_listing_dates.cache_clear()
        _scan_names.cache_clear()


def reset_caches_for_tests() -> None:
    """Drop the in-process master caches + the live-lookup budget (test helper)."""
    _nse_master.cache_clear()
    _bse_master.cache_clear()
    _bse_scrip_index.cache_clear()
    _us_master.cache_clear()
    _marquee_aliases.cache_clear()
    _former_names.cache_clear()
    _india_sector_map.cache_clear()
    _generic_tokens.cache_clear()
    _face_values.cache_clear()
    _nse_listing_dates.cache_clear()
    _scan_names.cache_clear()
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


def is_nse_emerge(symbol: str) -> bool:
    """True if ``symbol`` is an NSE Emerge (SME) listing, which Yahoo serves as
    ``<SYMBOL>-SM.NS`` (R15-DATA-017)."""
    entry = _nse_master().get(strip_exchange_suffix(symbol))
    return entry is not None and entry[1] == "SM"


def is_us_symbol(symbol: str) -> bool:
    """True if the bare form of ``symbol`` is a known US-listed ticker."""
    return strip_exchange_suffix(symbol).upper() in _us_master()


def is_bse_symbol(symbol: str) -> bool:
    """True if the bare form of ``symbol`` is a known BSE equity (incl. micro-caps),
    by ticker OR by its bare numeric scrip code (the header endpoint's native id;
    same 5-6-digit band :func:`resolve` binds at band 1b)."""
    bare = strip_exchange_suffix(symbol)
    if bare.isdigit() and 5 <= len(bare) <= 6:
        return bare in _bse_scrip_index()
    return bare in _bse_master()


def bse_scrip_code(symbol: str) -> str | None:
    """Return the numeric BSE scrip code for ``symbol`` (ticker or bare code
    itself; the header endpoint key)."""
    bare = strip_exchange_suffix(symbol)
    if bare.isdigit() and 5 <= len(bare) <= 6:
        return bare if bare in _bse_scrip_index() else None
    entry = _bse_master().get(bare)
    return entry[2] if entry and entry[2] else None


def bse_symbol_for_code(code: str) -> str | None:
    """Return the canonical BSE ticker for a bare numeric scrip ``code``, or
    ``None`` when the code is unknown — the resolver-side counterpart of
    :func:`bse_scrip_code`, used by data-route callers to canonicalise a
    code-addressed request (:func:`services.bse_provider._require_bse`)."""
    return _bse_scrip_index().get(code)


def nse_listing_date(symbol: str) -> str | None:
    """The NSE DATE OF LISTING (ISO) of ``symbol``'s NSE listing, or ``None``
    for a symbol the NSE master does not list (a BSE-only scrip)."""
    return _nse_listing_dates().get(strip_exchange_suffix(symbol).removesuffix("-SM"))


def dual_listed_bse_code(symbol: str) -> str | None:
    """The BSE scrip code of the NSE listing ``symbol``'s own BSE dual listing.

    ``None`` when ``symbol`` is not an NSE listing, has no BSE row, or the BSE row
    under the same ticker is a different company (NSE FOCUS vs BSE FOCUS) — so a
    BSE lane keyed by that ticker would fetch the other company's filings.
    """
    bare = strip_exchange_suffix(symbol)
    if bare not in _nse_master():
        return None
    return _enrich_instrument(_instrument_nse(bare, 1.0, BAND_EXACT_TICKER)).bse_code


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


def _instrument_nse(symbol: str, score: float, band: int) -> Instrument:
    name, typ = _nse_master()[symbol]
    asset_class = "etf" if typ == "ETF" else "equity"
    return Instrument(
        symbol=symbol,
        name=name,
        exchange="NSE",
        region=REGION_IN,
        asset_class=asset_class,
        yahoo_symbol=f"{symbol}-SM.NS" if typ == "SM" else f"{symbol}.NS",
        score=score,
        band=band,
    )


def _instrument_bse(symbol: str, score: float, band: int) -> Instrument:
    name, _group, _code, _isin = _bse_master()[symbol]
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


def _instrument_us(symbol: str, score: float, band: int) -> Instrument:
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


def _canonical_name(name_lc: str) -> str:
    """Canonicalize a name for the exact-modulo-suffix comparison (R13).

    Normalizes the corporate-name SEAM — "&"⟺"and", "pvt"⟺"private" (via
    :data:`_NAME_CANON_MAP`) — then drops trailing corporate suffixes (so
    "Ltd"⟺"Limited" collapse too). Applied SYMMETRICALLY to query and name so a
    company's own legal name ("bilcare ltd") canonicalizes to the same string as
    the master spelling ("bilcare limited") → "bilcare". Purely an equality key:
    it never loosens fuzzy scoring (that rung is untouched)."""
    tokens = [t.strip(_EDGE_PUNCT) for t in name_lc.split()]
    tokens = [_NAME_CANON_MAP.get(t, t) for t in tokens if t]
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
    if query_words > 1:
        if query_lc == stripped:
            return BAND_NAME_EXACT, 1.0
        # Exact modulo the corporate-suffix seam (Ltd⟺Limited, &⟺and, Pvt⟺Private):
        # a company's own legal name matching the master except for that seam is a
        # NAME-EXACT hit, not a fuzzy one — so "Bilcare Ltd" binds "Bilcare Limited"
        # instead of stranding at 0.846 under the accept band. An equality of
        # canonical keys, so it can only promote a genuine same-name match — the
        # fuzzy rung (the E1 wrong-entity guard) is left untouched.
        query_canon = _canonical_name(query_lc)
        if query_canon and query_canon == _canonical_name(name_lc):
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

    Every candidate is then enriched with its additive identity metadata (R13:
    ISIN, BSE scrip code, industry) — a read-only join, never a fabricator — and
    only then passes through the NSE symbol-change lane (R12, D66), whose
    identity gate needs those ISINs: a resolved OLD symbol whose change date has
    passed is answered as its CURRENT symbol with an explicit
    :class:`RenameAnnotation` — never a silent swap, never onto a different
    company, and an honest no-op when the rename master is unavailable.
    """
    return _annotate_renamed_symbols(_enrich_resolution(_resolve_masters(query, region)))


def _resolve_masters(query: str, region: str) -> Resolution:
    """The banded, locale-ranked master resolution (pre-rename-annotation)."""
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

    # 1b. Bare BSE scrip-code hit — an all-digit 5-6-digit query (optionally a
    #     ``.BO`` form) is the BSE header endpoint's native instrument id: exact
    #     and unambiguous (a numeric code never appears in the alphabetic NSE/US
    #     masters), so it binds the one BSE row carrying that code at band 6.
    if (
        not candidates
        and upper.isdigit()
        and 5 <= len(upper) <= 6
        and suffix_exchange in (None, "BSE")
    ):
        scrip_symbol = _bse_scrip_index().get(upper)
        if scrip_symbol:
            candidates.append(_instrument_bse(scrip_symbol, 1.0, band=BAND_EXACT_TICKER))

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

    query_lc = cleaned.lower()
    ranked = list(_scan_names(query_lc, len(tokens), region, suffix_exchange))

    # 3b. A retired NSE ticker (R15-DATA-018). A refreshed master no longer
    #     carries the old symbol, so a query for it misses (or only fuzzes below
    #     ACCEPT); the NSE symbol-change master still knows it — answer the
    #     current instrument, annotated, before any sub-accept guess or network.
    #     Also runs below a full NAME-EXACT band (R15-DATA-059): the retired
    #     TICKER (e.g. "ZOMATO") can coincide with the RENAMED company's own
    #     former legal name ("Zomato Limited") scoring a merely first-word/
    #     prefix former-name-scan hit — the explicit symbol-rename record wins
    #     over that coincidence; a genuine exact-name match is left alone.
    if (
        not ranked or ranked[0].score < DISAMBIGUATION_THRESHOLD or ranked[0].band < BAND_NAME_EXACT
    ) and suffix_exchange != "BSE":
        retired = _retired_symbol_instrument(upper) if " " not in upper else None
        if retired is not None:
            return Resolution(
                query=query, best=retired, candidates=[retired, *ranked][:_MAX_CANDIDATES]
            )

    if ranked and not _only_generic_overlap(ranked[0], query_lc):
        return Resolution(query=query, best=ranked[0], candidates=_capped(ranked, ranked, region))

    # 4. Live keyless fallback (best-effort; never blocks; never binds — every
    #    row rides _DISAMBIGUATE_SCORE, which the policy maps to disambiguate).
    #    Also run when the best master hit is a fuzzy match on generic words only
    #    ("Sumax Engineering Limited" → six "… Engineering Ltd"): the live rows
    #    join the candidates after the top master hits (R15-DATA-017).
    live = _live_lookup(cleaned, region) or []
    if ranked:
        known = {i.symbol for i in ranked}
        live = [i for i in live if i.symbol not in known]
        merged = ranked[: _MAX_CANDIDATES // 2] + live + ranked[_MAX_CANDIDATES // 2 :]
        return Resolution(query=query, best=ranked[0], candidates=_capped(merged, ranked, region))
    if live:
        return Resolution(query=query, best=live[0], candidates=live[:_MAX_CANDIDATES])

    return Resolution(query=query, best=None, candidates=[])


# ponytail: 256 entries bound the memo (a one-letter query ranks ~12.8k rows); raise it
# if repeat-query hit rates show it evicting hot names.
@lru_cache(maxsize=256)
def _scan_names(
    query_lc: str, n_words: int, region: str, suffix_exchange: str | None
) -> tuple[Instrument, ...]:
    """The banded, locale-ranked name scan over the masters (step 3 of
    :func:`_resolve_masters`). Pure over the loaded masters, so it is memoized
    (R15-CODE-DATA-002: ~17.9k ``SequenceMatcher`` scores per call) and cleared
    whenever the masters change (:func:`refresh_masters`). The retired-symbol
    step, the live lookup, rename and enrichment stay outside the memo."""
    # 3. Banded name match across the masters. One canonical row per
    #    instrument: a dual-listed symbol is represented by its NSE row only
    #    (the BSE scan skips symbols the NSE master already carries), so a name
    #    never surfaces twice with two spellings of the same company.
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
    for sym, (name, _group, _code, _isin) in _bse_master().items():
        if sym in nse_symbols and suffix_exchange != "BSE":
            continue  # canonical row is the NSE instrument (dual-listed), unless .BO pins BSE
        _append(_name_score(query_lc, name.lower(), n_words), _instrument_bse, sym)
    for sym, name in _us_master().items():
        _append(_name_score(query_lc, name.lower(), n_words), _instrument_us, sym)

    # 3a. Former-name match (R15-DATA-059): a query by a company's RETIRED
    #     legal name ("BeiGene" for the listing now named ONC/BeOne Medicines,
    #     "Infosys Technologies Limited" for INFY) scores against the bundled
    #     former-name index the SAME way a current name does, and the resulting
    #     candidate carries ``former_name`` so the match is explained, never
    #     silently indistinguishable from a current-name hit. Iterated in the
    #     MASTER's prominence order (not ``former_names.json``'s own dict
    #     order, which is an arbitrary SEC-crawl/NSE-file order) so the same
    #     "prominence breaks exact ties" invariant below also applies here —
    #     otherwise a company with two US listings sharing one former legal
    #     name (e.g. ONC's Nasdaq line and its BEIGF OTC line, both once
    #     "BeiGene, Ltd.") could tie-break toward the obscure listing.
    former = _former_names()
    former_us = former.get("us", {})
    for sym in _us_master():
        names = former_us.get(sym)
        if not names:
            continue
        for old_name in names:
            band_score = _name_score(query_lc, old_name.lower(), n_words)
            if band_score is None:
                continue
            band, s = band_score
            inst = replace(_instrument_us(sym, s, band), former_name=old_name)
            scored.append((band, _locale_rank(region, inst.region), s, inst))
    former_in = former.get("in", {})
    for sym in nse_symbols:
        names = former_in.get(sym)
        if not names:
            continue
        for old_name in names:
            band_score = _name_score(query_lc, old_name.lower(), n_words)
            if band_score is None:
                continue
            band, s = band_score
            inst = replace(_instrument_nse(sym, s, band), former_name=old_name)
            scored.append((band, _locale_rank(region, inst.region), s, inst))
    for sym in _bse_master():
        if sym in nse_symbols and suffix_exchange != "BSE":
            continue  # same dual-listing rule as the current-name BSE loop above
        names = former_in.get(sym)
        if not names:
            continue
        for old_name in names:
            band_score = _name_score(query_lc, old_name.lower(), n_words)
            if band_score is None:
                continue
            band, s = band_score
            inst = replace(_instrument_bse(sym, s, band), former_name=old_name)
            scored.append((band, _locale_rank(region, inst.region), s, inst))

    # Band tie-break: (band, locale, score) — stable, so the prominence-ordered
    # masters break exact ties toward the well-known instrument. The locale
    # component IS the chooser's region tie-break (R11, D58c / V5): under an IN
    # session a foreign row can never outrank an IN row at the same band, so a
    # disambiguation list for "Reliance Q4 results" leads with RELIANCE (NSE),
    # never FRLCY/FLNCF (US OTC).
    scored.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)
    return tuple(t[3] for t in scored)


def _capped(
    candidates: list[Instrument], ranked: list[Instrument], region: str
) -> list[Instrument]:
    """``candidates`` cut to :data:`_MAX_CANDIDATES`, reserving the last slot for
    the best cross-region row of ``ranked``'s top band when it outscores every
    in-region row of that band and the cut would drop it (R15-DATA-058). The
    locale-first order (D58c) and ``best`` are untouched: an IN session still
    leads with IN rows, but a better US match ("Sify Technologies Ltd (ADR)")
    is never truncated out of the chooser."""
    capped = candidates[:_MAX_CANDIDATES]
    if region == REGION_GLOBAL or not ranked:
        return capped
    top_band = [i for i in ranked if i.band == ranked[0].band]
    in_region = [i.score for i in top_band if i.region == region]
    foreign = [i for i in top_band if i.region != region]
    if not in_region or not foreign:
        return capped
    best_foreign = max(foreign, key=lambda i: i.score)
    if best_foreign.score <= max(in_region) or best_foreign in capped:
        return capped
    return [*capped[: _MAX_CANDIDATES - 1], best_foreign]


@lru_cache(maxsize=1)
def _generic_tokens() -> frozenset[str]:
    """Name tokens common across the masters (see :data:`_GENERIC_TOKEN_MIN_NAMES`)."""
    counts: dict[str, int] = {}
    names = [n for n, _ in _nse_master().values()]
    names += [row[0] for row in _bse_master().values()]
    names += list(_us_master().values())
    for name in names:
        for token in set(_name_tokens(name.lower())):
            counts[token] = counts.get(token, 0) + 1
    return frozenset(t for t, n in counts.items() if n >= _GENERIC_TOKEN_MIN_NAMES)


def _name_tokens(name_lc: str) -> list[str]:
    tokens = (t.strip(_EDGE_PUNCT) for t in name_lc.split())
    return [t for t in tokens if t and t not in _CORP_SUFFIXES]


def _only_generic_overlap(best: Instrument, query_lc: str) -> bool:
    """True when ``best`` is a fuzzy hit sharing no distinctive (non-generic,
    non-corporate-suffix) token with the query."""
    if best.band != BAND_FUZZY:
        return False
    distinctive = set(_name_tokens(query_lc)) - _generic_tokens()
    return not distinctive & set(_name_tokens(best.name.lower()))


# ---------------------------------------------------------------------------
# NSE symbol-change lane (R12, D66) — answer the CURRENT symbol, never stale.
# ---------------------------------------------------------------------------


def _rename_instrument(inst: Instrument) -> Instrument:
    """Rewrite a retired Indian symbol to its CURRENT NSE identity, annotated.

    The rename master is NSE's ``symbolchange.csv``, so the current symbol is
    always an NSE listing and the row it describes is an NSE row. The master is
    keyed by the ticker STRING, which is not an identity: a BSE-only company can
    share a ticker with a retired NSE symbol (BSE SHREE = Shree Marutinandan
    Tubes, NSE SHREE → AJMERA in 2009), and NSE reuses retired tickers (DTIL
    retired to DVL in 2010, reused by Dhunseri Tea). So the rewrite is gated on
    :func:`~services.resolution_policy.same_instrument` (ISIN-first; the resolver
    has enriched every candidate before this lane runs):

      * an NSE row is rewritten unless the renamed-to symbol is itself a listing
        in the NSE master that is a different instrument (the old ticker was
        reused by another company);
      * a BSE row is rewritten only when its ISIN is known and equals the ISIN
        of the renamed NSE instrument — the renamed-to listing when the master
        carries it, else the NSE row of the retired ticker (a dual listing of the
        same company collapses to the ONE current row, R12/D67). A BSE row with
        no ISIN, or with no NSE counterpart, is never rewritten.

    Only Indian instruments are considered (a US ticker that happens to equal an
    NSE old symbol keeps its own identity). The rename applies only when the
    change's effective date has passed; an empty rename map (cold app / no
    network) is an honest no-op, so this returns ``inst`` unchanged and the
    resolver behaves exactly as it did before the lane existed.
    """
    if inst.region != REGION_IN:
        return inst
    applied = nse_symbol_change.lookup_current(inst.symbol)
    if applied is None:
        return inst
    new_symbol = applied.renamed_to.strip().upper()
    if not new_symbol or new_symbol == inst.symbol:
        return inst
    nse = _nse_master()
    target = (
        _enrich_instrument(_instrument_nse(new_symbol, inst.score, inst.band))
        if new_symbol in nse
        else None
    )
    if inst.exchange == "BSE":
        anchor = target
        if anchor is None and inst.symbol in nse:
            anchor = _enrich_instrument(_instrument_nse(inst.symbol, inst.score, inst.band))
        if not inst.isin or anchor is None or not same_instrument(inst, anchor):
            return inst
    elif target is not None and not same_instrument(inst, target):
        return inst
    current = target or replace(
        inst, symbol=new_symbol, exchange="NSE", yahoo_symbol=f"{new_symbol}.NS"
    )
    return _as_renamed(current, inst.symbol, applied, score=inst.score, band=inst.band)


def _as_renamed(
    current: Instrument,
    old_symbol: str,
    applied: nse_symbol_change.AppliedRename,
    *,
    score: float,
    band: int,
) -> Instrument:
    """``current`` answered for the retired ``old_symbol``, with explicit provenance."""
    new_symbol = current.symbol
    effective = applied.effective_date.isoformat()
    return replace(
        current,
        name=applied.new_name or current.name,
        score=score,
        band=band,
        former_name=old_symbol,
        rename=RenameAnnotation(
            renamed_from=old_symbol,
            renamed_to=new_symbol,
            effective_date=effective,
            note=(
                f"{old_symbol} was renamed to {new_symbol} on NSE "
                f"(effective {effective}); the resolver answers the current symbol."
            ),
        ),
    )


def _retired_symbol_instrument(symbol: str) -> Instrument | None:
    """The CURRENT NSE instrument for a retired NSE ticker the masters no longer
    carry (ZOMATO → ETERNAL), annotated — or ``None`` when ``symbol`` is not a
    retired symbol. An exact hit in the official symbol-change master is as
    deterministic as an exact master ticker, so it rides the exact-ticker band.
    """
    applied = nse_symbol_change.lookup_current(symbol)
    if applied is None:
        return None
    new_symbol = applied.renamed_to.strip().upper()
    if new_symbol in _nse_master():
        current = _instrument_nse(new_symbol, 1.0, BAND_EXACT_TICKER)
    else:
        current = Instrument(
            symbol=new_symbol,
            name=applied.new_name or new_symbol,
            exchange="NSE",
            region=REGION_IN,
            asset_class="equity",
            yahoo_symbol=f"{new_symbol}.NS",
        )
    return _as_renamed(current, symbol, applied, score=1.0, band=BAND_EXACT_TICKER)


def _annotate_renamed_symbols(resolution: Resolution) -> Resolution:
    """Apply the rename lane to a resolution's best + candidates, deduped.

    Rewriting can collapse two rows onto the same current listing (an old ticker
    and its new one); a row that is the same instrument
    (:func:`~services.resolution_policy.same_instrument`) on the same exchange as
    an earlier one is dropped, keeping first-seen order so the best stays first.
    A no-op when nothing was renamed.
    """
    if resolution.best is None:
        return resolution
    best = _rename_instrument(resolution.best)
    candidates: list[Instrument] = []
    for cand in [best, *(_rename_instrument(c) for c in resolution.candidates)]:
        if any(c.exchange == cand.exchange and same_instrument(c, cand) for c in candidates):
            continue
        candidates.append(cand)
    return Resolution(
        query=resolution.query,
        best=best,
        candidates=candidates[:_MAX_CANDIDATES],
    )


# ---------------------------------------------------------------------------
# Identity enrichment (R13) — the read-only ISIN / scrip / industry join.
# ---------------------------------------------------------------------------


#: Name-key similarity at or above which an NSE row and the same-ticker BSE row
#: are one company. Measured over the bundled masters: every genuine dual-listed
#: equity whose spellings differ scores >= 0.81 ("Black Rose Inds." / "Black Rose
#: Industries"), while the same-ticker different-company pairs score <= 0.61
#: (FOCUS: Focus Lighting / Focus Business Solution 0.40; KALYANI: Kalyani
#: Commercials / Kalyani Cast-Tech 0.61).
_SAME_COMPANY_NAME_RATIO = 0.75


def _company_name_key(name: str) -> str:
    """A spelling-insensitive key for comparing one company's NSE and BSE names:
    lowercased, ``&`` read as ``and``, a trailing Ltd/Limited dropped, then only
    letters and digits kept ("D.B.Corp Limited" and "D. B. Corp Ltd" → "dbcorp")."""
    tokens = name.lower().replace("&", " and ").split()
    while len(tokens) > 1 and tokens[-1].strip(_EDGE_PUNCT) in ("ltd", "limited"):
        tokens.pop()
    return "".join(ch for ch in "".join(tokens) if ch.isalnum())


def _bse_row_is_same_company(inst: Instrument, bse_entry: tuple[str, str, str, str]) -> bool:
    """True when the BSE master row under ``inst``'s ticker is ``inst``'s own company.

    The NSE master carries no ISIN, so an NSE row's identity can only be joined
    from the BSE row of the same ticker — and the ticker string alone collides
    (NSE FOCUS is Focus Lighting and Fixtures, BSE FOCUS is Focus Business
    Solution, ISIN INE0DXR01010). The join is refused on disagreement: the
    instrument TYPE must agree (an ETF's units carry an ``INF`` ISIN, an equity's
    never do), and for an equity the legal NAMES must agree. An ETF is not
    name-checked — NSE's ETF list carries a scheme code in its name column
    ("NIPINDETFNIFTYBEES"), not a name that can agree or disagree.
    """
    name, _group, _code, isin = bse_entry
    if (inst.asset_class == "etf") != isin.startswith("INF"):
        return False
    if inst.asset_class == "etf":
        return True
    ratio = SequenceMatcher(None, _company_name_key(inst.name), _company_name_key(name)).ratio()
    return ratio >= _SAME_COMPANY_NAME_RATIO


def _enrich_instrument(inst: Instrument) -> Instrument:
    """Attach the additive identity metadata to a resolved instrument.

    A READ-ONLY join, never a fabricator: ``bse_code`` + ``isin`` come from the
    bundled BSE master (the ISIN falls back to the sector map for an NSE-only
    listing), ``industry`` from ``india_sector_map.json`` (``industry_raw``, else
    the broad ``sector``), and ``former_name`` from the NSE rename lane: the
    retired symbol this listing was renamed from (SEQUENT for VIYASH). A field the
    bundled data does not carry stays ``None`` — a group-X micro-cap present in
    the sector map with ``industry_raw: None`` (KSE) surfaces ``industry = None``,
    never an invented sector. Idempotent: returns the same object when nothing to
    add (US tickers, or an already-enriched instrument).

    Both bundled sources are BSE-sourced and keyed by the bare ticker, so for an
    NSE row they describe the NSE company only when the same-ticker BSE row IS
    that company (:func:`_bse_row_is_same_company`). When it is not (NSE FOCUS vs
    BSE FOCUS), the NSE row takes no ISIN, scrip code or industry from them — one
    company's identity is never stamped onto another. A sector-map record that
    carries a BSE scrip code is likewise used for an NSE row only when that code
    is the verified dual listing's; a record with no scrip code is an NSE-side
    enrichment row and applies as is.

    GUARD (R13 hardening — the ISIN-leak fix): this is an INDIAN-identity
    join keyed on the bare ticker STRING alone, which collides across
    exchanges — a US "TCI" candidate sitting beside NSE "TCI" (Transport
    Corporation of India) in the SAME candidate list must never borrow the
    Indian company's ISIN/bse_code/industry just because the ticker text
    matches. Enrichment applies ONLY to an instrument that IS itself an
    Indian listing (``exchange`` NSE/BSE — every IN-region instrument in this
    module carries one of those two, by the master-hygiene invariant above);
    every other candidate keeps its Indian identity fields at their default
    ``None`` (a US row takes only its own SEC former name)."""
    if inst.exchange not in ("NSE", "BSE"):
        if inst.former_name is not None:
            return inst
        # A US listing takes no Indian field, only its own SEC former legal name
        # (R15-DATA-059): the newest one that is not just a respelling of the
        # current name (AAPL's "APPLE INC" beside "Apple Inc.").
        current = _company_name_key(inst.name)
        former = next(
            (
                n
                for n in _former_names()["us"].get(inst.symbol.upper(), ())
                if _company_name_key(n) != current
            ),
            None,
        )
        return inst if former is None else replace(inst, former_name=former)
    bare = strip_exchange_suffix(inst.symbol).upper()
    bse_entry = _bse_master().get(bare)
    record = _india_sector_map().get(bare)
    if inst.exchange == "NSE":
        if bse_entry is not None and not _bse_row_is_same_company(inst, bse_entry):
            bse_entry = None
        record_code = record.get("scrip_code") if record is not None else None
        if record_code and (bse_entry is None or record_code != bse_entry[2]):
            record = None
    bse_code = bse_entry[2] if bse_entry and bse_entry[2] else None
    isin: str | None = bse_entry[3] if bse_entry and bse_entry[3] else None

    industry: str | None = None
    if record is not None:
        if isin is None:
            rec_isin = record.get("isin")
            isin = rec_isin if isinstance(rec_isin, str) and rec_isin else None
        raw_industry = record.get("industry_raw") or record.get("sector")
        industry = raw_industry if isinstance(raw_industry, str) and raw_industry else None

    # The NSE TICKER-rename lane governs NSE symbols (an NSE row, or the
    # verified BSE dual listing of one, exposes the retired SYMBOL it was
    # renamed from) and wins when it has an answer. Otherwise fall back to
    # whatever ``inst.former_name`` already carries (R15-DATA-059): the
    # former-COMPANY-NAME scan (:func:`_scan_names`) stamps it on a match by a
    # retired legal name — the only source for a BSE-only IN row (TTC) or a US
    # instrument (ONC/BeiGene), neither of which the ticker-rename lane covers.
    former_name = (
        nse_symbol_change.lookup_former(bare)
        if inst.exchange == "NSE"
        or (bse_code is not None and dual_listed_bse_code(bare) == bse_code)
        else None
    ) or inst.former_name

    # Board + face value (R15-DATA-051): SME is a BSE M* group (M/MT/MS) or an NSE
    # Emerge listing (type SM). Unknown to the masters (a live-lookup row) → None.
    exchange_group = bse_entry[1] if bse_entry and bse_entry[1] else None
    nse_entry = _nse_master().get(bare) if inst.exchange == "NSE" else None
    board: str | None = None
    face_value: float | None = None
    if nse_entry is not None or bse_entry is not None:
        sme = (nse_entry is not None and nse_entry[1] == "SM") or (exchange_group or "").startswith(
            "M"
        )
        board = "SME" if sme else "mainboard"
        if nse_entry is not None:
            face_value = _face_values("nse_instruments.json").get(bare)
        if face_value is None and bse_entry is not None:
            face_value = _face_values("bse_instruments.json").get(bare)

    enriched = {
        "isin": isin,
        "bse_code": bse_code,
        "industry": industry,
        "former_name": former_name,
        "board": board,
        "exchange_group": exchange_group,
        "face_value": face_value,
    }
    if all(getattr(inst, key) == value for key, value in enriched.items()):
        return inst
    return replace(inst, **enriched)


def _enrich_resolution(resolution: Resolution) -> Resolution:
    """Enrich the best + every candidate of a resolution (R13). No-op on a miss."""
    if resolution.best is None:
        return resolution
    return Resolution(
        query=resolution.query,
        best=_enrich_instrument(resolution.best),
        candidates=[_enrich_instrument(c) for c in resolution.candidates],
    )


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

    # (score, band): each row states its match rung, as resolve() does.
    def _score(sym: str, name: str) -> tuple[float, int] | None:
        if sym == q_sym:
            return 1.0, BAND_EXACT_TICKER
        if sym.startswith(q_sym):
            return 0.95, BAND_PREFIX
        name_lc = name.lower()
        if name_lc.startswith(q_lc):
            return 0.9, BAND_PREFIX
        if q_lc in name_lc:
            return 0.8, BAND_SUBSTRING
        return None

    out: list[Instrument] = []
    nse_symbols = _nse_master()
    for sym, (name, _typ) in nse_symbols.items():
        s = _score(sym, name)
        if s is not None:
            out.append(_instrument_nse(sym, *s))
    # BSE-only names (the micro-cap tail) — dual-listed symbols are skipped so
    # the canonical NSE row is the one (and only) candidate for that instrument,
    # keeping the list deduplicated and NSE-preferred without a second pass.
    for sym, (name, _group, _code, _isin) in _bse_master().items():
        if sym in nse_symbols:
            continue
        s = _score(sym, name)
        if s is not None:
            out.append(_instrument_bse(sym, *s))
    for sym, name in _us_master().items():
        s = _score(sym, name)
        if s is not None:
            out.append(_instrument_us(sym, *s))
    # A retired NSE ticker (ZOMATO) lists its current instrument (ETERNAL) first,
    # annotated — the old symbol is what the user remembers typing.
    retired = (
        _retired_symbol_instrument(q_sym) if not query.strip().upper().endswith(".BO") else None
    )
    if retired is not None:
        out = [i for i in out if (i.symbol, i.exchange) != (retired.symbol, retired.exchange)]
    # Locale breaks ties as a SORT KEY, never an additive score bonus.
    out.sort(key=lambda i: (i.score, _locale_rank(region, i.region)), reverse=True)
    if retired is not None:
        out.insert(0, retired)
    # The same identity stages as :func:`resolve` (enrichment, then the rename
    # lane), deduped the same way, so a row never lists a retired ticker bare or
    # promises identity fields it never filled (R15-UI-039).
    listed: list[Instrument] = []
    for inst in out:
        cand = _rename_instrument(_enrich_instrument(inst))
        if any(c.exchange == cand.exchange and same_instrument(c, cand) for c in listed):
            continue
        listed.append(cand)
        if len(listed) == limit:
            break
    return listed


def _live_lookup(query: str, region: str) -> list[Instrument]:
    """Guarded ``yfinance.Search`` fallback for symbols not in the masters.

    Collects ALL hits (up to 5) as candidates at :data:`_DISAMBIGUATE_SCORE` —
    a live row is never master-deterministic, so the policy maps it to
    "disambiguate", never "bound". Under an IN session the ``.NS``/``.BO``
    rows rank first. Network/parse failures degrade to ``[]`` (the caller
    surfaces an honest "unresolved" — never raw JSON, never a guess).

    Budgeted (R11, D58d): results are LRU-cached per ``(query, region)`` so
    repeated unresolved queries never re-hit the network; a successful EMPTY
    search expires after :data:`_LIVE_EMPTY_TTL_SECONDS` (a stock listed after
    the first miss becomes findable); ANY failure opens a short module-level cooldown during
    which the live rung returns ``[]`` immediately. Rate-limit-shaped failures
    (``YFRateLimitError``) are reported to :mod:`services.provider_health`
    (the Yahoo family shares one IP reputation across every yfinance path);
    a healthy round-trip reports success.
    """
    global _live_cooldown_until
    key = (query, region)
    with _live_cache_lock:
        cached = _live_cache.get(key)
        if cached is not None and (
            cached[1] or time.monotonic() - cached[0] < _LIVE_EMPTY_TTL_SECONDS
        ):
            _live_cache.move_to_end(key)
            return list(cached[1])
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
        _live_cache[key] = (time.monotonic(), list(out))
        _live_cache.move_to_end(key)
        while len(_live_cache) > _LIVE_CACHE_MAX_ENTRIES:
            _live_cache.popitem(last=False)
    return out


__all__ = [
    "DISAMBIGUATION_THRESHOLD",
    "Instrument",
    "RenameAnnotation",
    "Resolution",
    "autocomplete",
    "bse_scrip_code",
    "bse_symbol_for_code",
    "dual_listed_bse_code",
    "instrument_payload",
    "is_bse_symbol",
    "is_nse_emerge",
    "is_nse_symbol",
    "is_us_symbol",
    "region_hint",
    "refresh_masters",
    "reset_caches_for_tests",
    "resolve",
]
