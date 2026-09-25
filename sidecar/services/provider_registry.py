"""Provider registry — the single dispatch point routers call into.

Routers never import a concrete provider directly; they call the registry, which
resolves the right provider for each request. FR-035/FR-053: dispatch is no
longer a hardcoded ``if asset_class`` switch — it is a resolver keyed by a
STANDARD MODEL KEY (``quote``, ``ohlcv``, ``fundamentals``, ``income_statement``,
…) that walks installed providers in a PREFERENCE ORDER, trying each until one
succeeds. ``asset_class`` becomes a resolution *hint*, not the switch.

This mirrors :mod:`services.agent_tools.catalog`'s "declare once, project to
many": a small in-module table of :class:`ProviderDeclaration` rows (id, the
model-keys it serves, a preference rank, a credential/availability gate, the
asset-class hints it answers) is the single source of truth. :func:`active_providers`
(surfaced at ``/health``) is DERIVED from that table — never a hand-maintained dict.

Provenance lives on every result model (the ``provider`` field each provider
sets). The resolver never overwrites it: whichever provider actually served the
request (after any fallback) is the one named in the field.

The public accessor signatures are UNCHANGED so every router stays untouched:
``get_quote``/``get_history`` stay synchronous (their providers — ccxt, yfinance
— are sync, and callers wrap them in ``asyncio.to_thread``); the openbb-backed
methods stay ``async``. Two resolvers — one sync, one async — share the same
declaration table and the same preference-order fallthrough.
"""

from __future__ import annotations

import asyncio
import calendar
import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from itertools import pairwise
from statistics import median_low
from typing import Any, Literal

import config
from models.fundamentals import (
    AnalystRating,
    BalanceSheet,
    CashFlowStatement,
    FinancialStatement,
    Fundamentals,
    IncomeStatement,
)
from models.market import MacroSeries, OHLCVSeries, Quote
from services import (
    bse_provider,
    ccxt_provider,
    correctness_gate,
    india_provider,
    nse_provider,
    openbb_mcp_provider,
    provider_health,
    symbol_resolver,
    yfinance_provider,
)
from services.errors import ProviderError

DEFAULT_CRYPTO_EXCHANGE = "binance"

_log = logging.getLogger(__name__)

# Standard model keys — the resolver's routing vocabulary (FR-035). Every public
# accessor maps to exactly one. Asset class is a *hint* layered on top, not a key.
ModelKey = Literal[
    "quote",
    "ohlcv",
    "fundamentals",
    "income_statement",
    "balance_sheet",
    "cash_flow",
    "analyst_rating",
    "macro_series",
]

# Statement depth (R15-DATA-026). Periods are ISO period-end dates for annual and
# quarterly alike, missing expected periods marked by :func:`_mark_gaps` (R15-LEAD-015).
StatementPeriod = Literal["annual", "quarterly"]


# ---------------------------------------------------------------------------
# Provider declarations — declared once, projected to the resolver + /health.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProviderDeclaration:
    """One installed data provider — the single declaration the resolver reads.

    ``serves`` maps each model-key it can answer to the bound accessor (sync or
    async). ``rank`` is the preference order *within* a model-key (lower wins).
    ``requires`` is a no-arg predicate gating availability (e.g. an MCP plugin
    being bundled); when it returns ``False`` the provider is skipped entirely.
    ``asset_classes`` narrows which asset-class hints the provider answers
    (empty = any). ``region`` narrows which locales the provider serves (empty =
    any region) — the seam that routes an NSE request to the India provider and
    keeps it out of a US request (FR-060/064).
    """

    id: str
    serves: dict[str, Callable[..., Any]]
    rank: int = 100
    requires: Callable[[], bool] | None = None
    asset_classes: frozenset[str] = field(default_factory=frozenset)
    region: frozenset[str] = field(default_factory=frozenset)

    def available(self) -> bool:
        return self.requires is None or bool(self.requires())

    def serves_asset_class(self, asset_class: str | None) -> bool:
        return not self.asset_classes or asset_class is None or asset_class in self.asset_classes

    def serves_region(self, region: str | None) -> bool:
        return not self.region or region is None or region in self.region


# The ``serves`` callables and ``requires`` predicates dispatch through the
# provider MODULE at invocation time (``lambda *a: module.fn(*a)``) rather than
# binding the function object at declaration time — so the live attribute is
# always used (and tests that monkeypatch a provider module reach the resolver).
_PROVIDERS: tuple[ProviderDeclaration, ...] = (
    # crypto market data — preferred for the crypto asset-class hint only.
    ProviderDeclaration(
        id="ccxt",
        rank=10,
        asset_classes=frozenset({"crypto"}),
        serves={
            "quote": lambda symbol: ccxt_provider.get_ticker(DEFAULT_CRYPTO_EXCHANGE, symbol),
            "ohlcv": lambda symbol, timeframe, range_=None: ccxt_provider.get_ohlcv(
                DEFAULT_CRYPTO_EXCHANGE, symbol, timeframe, range_
            ),
        },
    ),
    # openbb-mcp — preferred for fundamentals/statements/analyst/macro when bundled.
    ProviderDeclaration(
        id="openbb-mcp",
        rank=10,
        requires=lambda: openbb_mcp_provider.is_available(),
        serves={
            "fundamentals": lambda symbol: openbb_mcp_provider.get_fundamentals(symbol),
            "income_statement": lambda symbol, period="annual": (
                openbb_mcp_provider.get_income_statement(symbol, period)
            ),
            "balance_sheet": lambda symbol, period="annual": openbb_mcp_provider.get_balance_sheet(
                symbol, period
            ),
            "cash_flow": lambda symbol, period="annual": openbb_mcp_provider.get_cash_flow(
                symbol, period
            ),
            "analyst_rating": lambda symbol: openbb_mcp_provider.get_analyst_rating(symbol),
            "macro_series": lambda series_id, provider=None: openbb_mcp_provider.get_macro_series(
                series_id, provider=provider
            ),
        },
    ),
    # nse_direct — the exchange-direct anti-bot lane (curl_cffi cookie dance,
    # R7 Component 2), region-scoped to IN and ranked ABOVE the jugaad lane
    # (nse, 20): when www.nseindia.com serves us directly we prefer the
    # first-party EOD rows; any block/throttle/circuit-open falls through to
    # jugaad → bse → gated yfinance. Serves quote + ohlcv only.
    ProviderDeclaration(
        id="nse_direct",
        rank=15,
        requires=lambda: nse_provider.is_available(),
        asset_classes=frozenset({"equity"}),
        region=frozenset({"IN"}),
        serves={
            "quote": lambda symbol: nse_provider.get_quote(symbol),
            "ohlcv": lambda symbol, timeframe, range_=None: nse_provider.get_history(
                symbol, timeframe, range_
            ),
        },
    ),
    # nse (jugaad-data) — the keyless India equity/ETF default, region-scoped to
    # IN and ranked ABOVE yfinance so a `.NS`/`.BO` request is served by the
    # locale-correct EOD source, not documented-unreliable yfinance (#2612/#2055).
    # Serves quote + ohlcv only; IN fundamentals fall through to yfinance.
    ProviderDeclaration(
        id="nse",
        rank=20,
        requires=lambda: india_provider.is_available(),
        asset_classes=frozenset({"equity"}),
        region=frozenset({"IN"}),
        serves={
            "quote": lambda symbol: india_provider.get_quote(symbol),
            "ohlcv": lambda symbol, timeframe, range_=None: india_provider.get_history(
                symbol, timeframe, range_
            ),
        },
    ),
    # bse — the keyless India MICRO-CAP EOD default (the B/X/XT/T/Z groups NSE
    # never listed), region-scoped to IN and ranked BETWEEN nse (20) and yfinance
    # (50): a bare BSE-only ticker (or a `.BO` request) resolves to IN and is
    # served EOD from the daily BhavCopy cache, not documented-unreliable yfinance
    # (#2612/#2055). Serves quote + ohlcv only (mirrors nse); IN fundamentals fall
    # through to yfinance. nse still wins for a dual-listed name (lower rank).
    ProviderDeclaration(
        id="bse",
        rank=25,
        requires=lambda: bse_provider.is_available(),
        asset_classes=frozenset({"equity"}),
        region=frozenset({"IN"}),
        serves={
            "quote": lambda symbol: bse_provider.get_quote(symbol),
            "ohlcv": lambda symbol, timeframe, range_=None: bse_provider.get_history(
                symbol, timeframe, range_
            ),
        },
    ),
    # yfinance — the broad equity default + fallback for fundamentals/statements/
    # analyst when openbb-mcp is absent or errors. No macro equivalent. Serves any
    # region (the US default *and* the gated last-resort for IN behind `nse`).
    ProviderDeclaration(
        id="yfinance",
        rank=50,
        asset_classes=frozenset({"equity"}),
        serves={
            "quote": lambda symbol: yfinance_provider.get_quote(symbol),
            "ohlcv": lambda symbol, timeframe, range_=None: yfinance_provider.get_history(
                symbol, timeframe, range_
            ),
            "fundamentals": lambda symbol: yfinance_provider.get_fundamentals(symbol),
            "income_statement": lambda symbol, period="annual": (
                yfinance_provider.get_income_statement(symbol, period)
            ),
            "balance_sheet": lambda symbol, period="annual": yfinance_provider.get_balance_sheet(
                symbol, period
            ),
            "cash_flow": lambda symbol, period="annual": yfinance_provider.get_cash_flow(
                symbol, period
            ),
            "analyst_rating": lambda symbol: yfinance_provider.get_analyst_rating(symbol),
        },
    ),
)


# A validator applied to a provider's result before it is accepted (the
# correctness gate, FR-063). It returns the value on success or raises a
# CorrectnessError (a ProviderError) to advance to the next provider.
Validator = Callable[[Any], Any]

# An acceptor decides whether a VALID result is also COMPLETE enough to return,
# or whether the registry should try the next (richer) provider. Distinct from a
# Validator: a validator rejects a WRONG result (raises → fall through); an
# acceptor declines an INCOMPLETE-but-correct result (returns False → try next,
# but keep it as the fallback if no richer provider exists). Used for the
# openbb→yfinance fundamentals enrichment below.
Acceptor = Callable[[Any], bool]

# The profitability / financial-health / growth fields the screener's numeric
# criteria + the curated presets rely on. openbb-mcp serves valuation (pe,
# market-cap, dividend) but does not populate these, so a fundamentals result
# with NONE of them is treated as "incomplete" — the registry falls through to
# the richer yfinance path that does populate them (fixing the empty screener /
# equity overview + the 5 empty presets). Kept as a tuple so the acceptor below
# and any future caller share one definition.
_SCREENER_GRADE_FIELDS: tuple[str, ...] = (
    "roe",
    "roa",
    "profit_margin",
    "operating_margin",
    "gross_margin",
    "debt_to_equity",
    "current_ratio",
    "quick_ratio",
    "revenue_growth",
    "earnings_growth",
)


def _fundamentals_screener_complete(result: Any) -> bool:
    """True when a fundamentals result carries at least one screener-grade field.

    A result missing ALL of :data:`_SCREENER_GRADE_FIELDS` (the openbb-mcp case
    for nearly every symbol) is incomplete → the registry tries the next provider
    (yfinance), which populates them. If every provider is sparse, the highest-
    ranked partial is still returned (never a hard failure)."""
    return any(getattr(result, field, None) is not None for field in _SCREENER_GRADE_FIELDS)


# The identity / metadata fields that are NOT real data. A Fundamentals whose
# every OTHER field is None is an all-null SHELL (openbb-mcp's every-field-None
# case for an uncovered symbol) — never a real result. A bare ``name`` is
# identity, not data: a name-only shell for SUMAX carried a US fund's name.
_FUNDAMENTALS_IDENTITY_FIELDS: frozenset[str] = frozenset(
    {"symbol", "name", "provider", "growth_basis", "field_meta"}
)


def _fundamentals_has_data(result: Any) -> bool:
    """True when a fundamentals result carries at least one non-null DATA field.

    Guards against serving an all-null shell as success (FR-063 / R13 D3): the
    accept-fallback keeps the highest-ranked INCOMPLETE result when no provider is
    screener-complete, but a result with ZERO non-null data fields (everything
    None except symbol/provider/growth_basis/field_meta) is not real data at all —
    it must degrade to the last provider error, not a dishonest all-null 200. A
    partial-but-real result (even one non-null field) is still servable."""
    fields = getattr(type(result), "model_fields", None)
    names = fields.keys() if fields else ()
    return any(
        name not in _FUNDAMENTALS_IDENTITY_FIELDS and getattr(result, name, None) is not None
        for name in names
    )


def _effective_region(symbol: str | None, region: str | None) -> str:
    """Resolve the region a request should route to.

    Precedence: an explicit ``region`` arg → the symbol's intrinsic region (a
    ``.NS`` suffix or an unambiguous master membership) → the active request
    region (``config.get_region()``). So ``GOLDBEES`` routes to IN even in a US
    session, while an ambiguous bare ticker defers to the user's locale.
    """
    if region:
        return config.normalize_region(region)
    if symbol:
        hint = symbol_resolver.region_hint(symbol)
        if hint:
            return hint
    return config.get_region()


def _candidates(
    model_key: ModelKey, asset_class: str | None, region: str | None
) -> list[ProviderDeclaration]:
    """Installed providers serving ``model_key`` for the ``asset_class`` +
    ``region`` hints, in preference order (lower rank first)."""
    matched = [
        p
        for p in _PROVIDERS
        if model_key in p.serves
        and p.available()
        and p.serves_asset_class(asset_class)
        and p.serves_region(region)
    ]
    return sorted(matched, key=lambda p: p.rank)


def _no_provider_error(
    model_key: ModelKey, asset_class: str | None, region: str | None
) -> ProviderError:
    detail = ", ".join(
        part
        for part in (
            f"asset_class={asset_class!r}" if asset_class else "",
            f"region={region!r}" if region else "",
        )
        if part
    )
    return ProviderError(
        f"no provider available for {model_key!r}" + (f" ({detail})" if detail else "")
    )


def _resolve_sync(
    model_key: ModelKey,
    asset_class: str | None,
    region: str | None,
    validate: Validator | None,
    /,
    *args: Any,
    accept: Acceptor | None = None,
) -> Any:
    """Walk SYNC providers for ``model_key`` in preference order, returning the
    first result that passes the correctness gate. A :class:`ProviderError` (or a
    gate :class:`CorrectnessError`) from one provider falls through to the next;
    the last error (or a no-provider error) propagates.

    ``accept`` gates completeness exactly as in :func:`_resolve_async`: a valid
    result it declines is kept as the fallback while the next provider is tried,
    and the highest-ranked such result is served only when no provider yields an
    accepted one (R15-DATA-071: a partial BSE range no longer ends the walk).

    Provenance is left untouched — the serving provider's ``provider`` field is
    whatever it wrote."""
    candidates = _candidates(model_key, asset_class, region)
    if not candidates:
        raise _no_provider_error(model_key, asset_class, region)
    last_exc: Exception | None = None
    best_incomplete: Any = None
    have_incomplete = False
    for provider in candidates:
        try:
            result = provider.serves[model_key](*args)
            validated = validate(result) if validate is not None else result
        except Exception as exc:  # noqa: BLE001 - any provider failure falls through
            last_exc = exc
            _fell_through(provider.id, model_key, exc)
            continue
        provider_health.record_served(provider.id, model_key)
        if accept is None or accept(validated):
            return validated
        if not have_incomplete:
            best_incomplete = validated
            have_incomplete = True
            _log.info(
                "provider %s returned an incomplete %s; trying next for richer data",
                provider.id,
                model_key,
            )
    if have_incomplete:
        return best_incomplete
    assert last_exc is not None
    raise last_exc


def _fell_through(provider_id: str, model_key: str, exc: Exception) -> None:
    """Log and count a fall-through (R15-LIFECYCLE-021). A ``not_found`` — the
    provider answered that it does not list this instrument or series — is a
    routing miss, not a failing upstream, so it is not counted. ``exc`` may be
    a non-:class:`ProviderError` (R15-CODE-DATA-008: any provider exception
    falls through, not just a clean one), so ``kind`` is read defensively."""
    _log.warning("provider %s failed for %s, falling through: %s", provider_id, model_key, exc)
    if getattr(exc, "kind", None) != "not_found":
        provider_health.record_fallthrough(provider_id, model_key, str(exc))


async def _resolve_async(
    model_key: ModelKey,
    asset_class: str | None,
    region: str | None,
    validate: Validator | None,
    /,
    *args: Any,
    accept: Acceptor | None = None,
    fallback_ok: Acceptor | None = None,
) -> Any:
    """Walk providers for ``model_key`` in preference order, awaiting async
    accessors and running sync ones on a worker thread (these resolvers back
    fundamentals/statements/analyst/macro — openbb-mcp async first, yfinance
    sync fallback). A sync yfinance fetch is network plus pandas parsing, and
    run inline it held the event loop for every request and every deep-crawl
    fetch (R15-LIFECYCLE-026). The correctness gate is applied to each result
    before acceptance.

    ``accept`` (optional) gates COMPLETENESS, not correctness: when a result is
    valid but ``accept`` returns False (e.g. openbb fundamentals missing every
    screener-grade field), the registry keeps it as a fallback and tries the next
    (richer) provider; the first such partial is returned only if no later
    provider yields an accepted result. ``accept=None`` preserves the original
    "first valid wins" behaviour for every other model-key.

    ``fallback_ok`` (optional) gates the LAST-RESORT partial: if every provider
    was merely incomplete and ``fallback_ok(best_incomplete)`` is False (e.g. an
    all-null fundamentals shell), the incomplete result is NOT served — the last
    provider error (or an honest not_found) is raised instead (R13 D3). A missing
    ``fallback_ok`` keeps the previous "any incomplete beats an error" behaviour.

    Provenance is left untouched (see :func:`_resolve_sync`)."""
    candidates = _candidates(model_key, asset_class, region)
    if not candidates:
        raise _no_provider_error(model_key, asset_class, region)
    last_exc: Exception | None = None
    best_incomplete: Any = None
    have_incomplete = False
    for provider in candidates:
        try:
            # Every accessor is a lambda, so whether it is sync is only known by
            # calling it: an async provider just builds its coroutine on the
            # thread, which is then awaited here on the loop.
            result = await asyncio.to_thread(provider.serves[model_key], *args)
            resolved = await result if inspect.isawaitable(result) else result
            validated = validate(resolved) if validate is not None else resolved
        except Exception as exc:  # noqa: BLE001 - any provider failure falls through
            last_exc = exc
            _fell_through(provider.id, model_key, exc)
            continue
        provider_health.record_served(provider.id, model_key)
        if accept is None or accept(validated):
            return validated
        # Valid but INCOMPLETE for this model-key — remember the highest-ranked
        # partial and try the next provider for richer data.
        if not have_incomplete:
            best_incomplete = validated
            have_incomplete = True
            _log.info(
                "provider %s returned an incomplete %s; trying next for richer data",
                provider.id,
                model_key,
            )
    if have_incomplete:
        if fallback_ok is None or fallback_ok(best_incomplete):
            return best_incomplete
        # The only survivor is an unusable shell (e.g. an all-null fundamentals
        # result) — degrade honestly rather than serve it as a 200 (R13 D3).
        if last_exc is not None:
            raise last_exc
        raise ProviderError(
            f"no provider returned usable {model_key!r} data for the request",
            kind="not_found",
        )
    assert last_exc is not None
    raise last_exc


# ---------------------------------------------------------------------------
# Public accessors — UNCHANGED signatures so every router stays untouched.
# ---------------------------------------------------------------------------


def get_quote(symbol: str, asset_class: str = "equity", region: str | None = None) -> Quote:
    """Return the latest quote; resolved by the ``quote`` model-key. Synchronous
    (callers run it on a thread) — its providers (ccxt, yfinance, nse) are sync.

    ``region`` (default: inferred from the symbol then the active request region)
    routes between the US (yfinance) and IN (nse) equity providers; the
    correctness gate validates every result before acceptance (FR-062/063). A
    crypto quote skips only the session-staleness leg: crypto trades around the
    clock, off any exchange calendar."""
    eff = _effective_region(symbol, region)
    validate = _quote_validator(symbol, eff, check_staleness=asset_class != "crypto")
    return _resolve_sync("quote", asset_class, eff, validate, symbol)


def get_history(
    symbol: str,
    timeframe: str,
    range_: str | None = None,
    asset_class: str = "equity",
    region: str | None = None,
) -> OHLCVSeries:
    """Return an OHLCV series; resolved by the ``ohlcv`` model-key. Synchronous.

    A series flagged ``partial`` (e.g. a cold-cache BSE range) does not end the
    walk: the next lane is tried for the full range, and the partial is served,
    still flagged, only when no lane is complete (R15-DATA-071)."""
    eff = _effective_region(symbol, region)
    return _resolve_sync(
        "ohlcv",
        asset_class,
        eff,
        _series_validator(symbol, eff),
        symbol,
        timeframe,
        range_,
        accept=lambda series: not series.partial,
    )


async def get_fundamentals(symbol: str, region: str | None = None) -> Fundamentals:
    """Return valuation ratios + company profile. Prefers openbb-mcp, but falls
    through to yfinance both on a ProviderError AND when openbb returns a result
    with no screener-grade fields (roe/margins/debt/growth) — see
    :func:`_fundamentals_screener_complete`. This is what fills the screener,
    the equity overview, and the curated presets with real ratios.

    ``fallback_ok=_fundamentals_has_data`` refuses to serve an all-null shell as
    success (R13 D3): if the only surviving result is empty of real data, the
    last provider error (or an honest not_found → 404) is raised instead."""
    eff = _effective_region(symbol, region)
    return await _resolve_async(
        "fundamentals",
        "equity",
        eff,
        _fundamentals_validator(symbol, eff),
        symbol,
        accept=_fundamentals_screener_complete,
        fallback_ok=_fundamentals_has_data,
    )


#: A period end this close to the expected one is that period (fiscal calendars
#: that end on a weekday, not a month end, land a few days off).
_GAP_TOLERANCE_DAYS = 45


def _months_back(end: date, months: int) -> date:
    """The month end ``months`` before ``end``'s month."""
    year, month = divmod(end.year * 12 + end.month - 1 - months, 12)
    return date(year, month + 1, calendar.monthrange(year, month + 1)[1])


def _mark_gaps[S: FinancialStatement](statement: S) -> S:
    """Insert an explicit gap period wherever an expected period is missing
    between two served ones (R15-LEAD-015).

    The expected step is the statement's own cadence (the smaller median gap
    between period ends: 3 months quarterly, 6 half-yearly, 12 annual), so a
    half-yearly filer's missing quarters are not gaps. Each gap is listed in
    ``periods`` and ``gaps`` with a null value in every line; a statement
    whose labels are not ISO dates, or with too few periods to show a
    cadence, is returned unchanged."""
    try:
        ends = sorted({date.fromisoformat(p) for p in statement.periods}, reverse=True)
    except ValueError:
        return statement
    if len(ends) < 3:
        return statement
    step = max(1, round(median_low((a - b).days for a, b in pairwise(ends)) / 30.44))
    gaps: list[date] = []
    for newer, older in pairwise(ends):
        expected = _months_back(newer, step)
        while (expected - older).days > _GAP_TOLERANCE_DAYS:
            gaps.append(expected)
            expected = _months_back(expected, step)
    if not gaps:
        return statement
    labels = [d.isoformat() for d in gaps]
    periods = sorted([*statement.periods, *labels], reverse=True)
    lines = [
        line.model_copy(update={"values": {**line.values, **dict.fromkeys(labels)}})
        for line in statement.lines
    ]
    return statement.model_copy(
        update={"periods": periods, "lines": lines, "gaps": sorted(labels, reverse=True)}
    )


async def get_income_statement(
    symbol: str, region: str | None = None, period: StatementPeriod = "annual"
) -> IncomeStatement:
    """Return the income statement excerpt for ``symbol`` (``period`` annual or quarterly)."""
    return _mark_gaps(
        await _resolve_async(
            "income_statement",
            "equity",
            _effective_region(symbol, region),
            _statement_validator(symbol),
            symbol,
            period,
        )
    )


async def get_balance_sheet(
    symbol: str, region: str | None = None, period: StatementPeriod = "annual"
) -> BalanceSheet:
    """Return the balance sheet excerpt for ``symbol`` (``period`` annual or quarterly)."""
    return _mark_gaps(
        await _resolve_async(
            "balance_sheet",
            "equity",
            _effective_region(symbol, region),
            _statement_validator(symbol),
            symbol,
            period,
        )
    )


async def get_cash_flow(
    symbol: str, region: str | None = None, period: StatementPeriod = "annual"
) -> CashFlowStatement:
    """Return the cash-flow statement excerpt for ``symbol`` (``period`` annual or quarterly)."""
    return _mark_gaps(
        await _resolve_async(
            "cash_flow",
            "equity",
            _effective_region(symbol, region),
            _statement_validator(symbol),
            symbol,
            period,
        )
    )


async def get_analyst_rating(symbol: str, region: str | None = None) -> AnalystRating:
    """Return aggregated analyst ratings for ``symbol``."""
    return await _resolve_async(
        "analyst_rating", "equity", _effective_region(symbol, region), None, symbol
    )


async def get_macro_series(series_id: str, provider: str | None = None) -> MacroSeries:
    """Return a macro time-series by id (FRED-style).

    Macro has no yfinance equivalent — when openbb-mcp is not bundled the
    resolver finds no provider and raises a clean :class:`ProviderError`, which
    the ``/macro`` router translates into its existing 501 response."""
    return await _resolve_async("macro_series", None, None, None, series_id, provider)


# --- Correctness-gate validators (closures binding the requested symbol+region) ---


def _quote_validator(symbol: str, region: str, *, check_staleness: bool = True) -> Validator:
    return lambda result: correctness_gate.validate_quote(
        result, symbol, region, check_staleness=check_staleness
    )


def _series_validator(symbol: str, region: str) -> Validator:
    return lambda result: correctness_gate.validate_series(result, symbol, region)


def _fundamentals_validator(symbol: str, region: str) -> Validator:
    return lambda result: correctness_gate.validate_fundamentals(result, symbol, region)


def _statement_validator(symbol: str) -> Validator:
    """Reject a statement for any listing other than the one requested.

    Both statement providers fetch the Yahoo listing form of ``symbol`` and echo
    it, so the returned ``symbol`` must equal that form exactly, suffix included.
    A bare ``DAL`` answered for an IN request (``DAL.BO``) is another company's
    statement (Delta's, not Dynamic Archistructures'), not a match.
    """
    listing = yfinance_provider._yahoo_symbol(symbol)

    def _validate(result: Any) -> Any:
        returned = str(getattr(result, "symbol", "") or "").strip().upper()
        if returned != listing:
            provider = getattr(result, "provider", None)
            raise correctness_gate.CorrectnessError(
                f"correctness gate: provider {provider!r} returned a statement for "
                f"{returned!r}, requested listing {listing!r} (identity mismatch)"
            )
        return result

    return _validate


# ---------------------------------------------------------------------------
# /data-sources (C19) — DERIVED from the declarations, same as /health below.
# ---------------------------------------------------------------------------


def declarations() -> list[dict[str, Any]]:
    """Serialize every provider declaration for the ``GET /data-sources``
    contract (C19). Additive — the resolver's own dispatch above is untouched.

    This is the SAME table :func:`active_providers` and the resolver read, so
    the frontend marketplace can derive each provider's served model-keys +
    preference rank from here instead of hand-maintained catalog metadata that
    drifts from it (R15-CODE-PLATFORM-072 / R15-DATA-077)."""
    return [
        {
            "id": p.id,
            "keys": sorted(p.serves),
            "rank": p.rank,
            "available": p.available(),
            "asset_classes": sorted(p.asset_classes),
            "region": sorted(p.region),
        }
        for p in _PROVIDERS
    ]


# ---------------------------------------------------------------------------
# /health — DERIVED from the declarations (FR-053), never a hand-kept dict.
# ---------------------------------------------------------------------------


def active_providers() -> dict[str, str]:
    """Report which provider currently backs each model-key, derived from the
    declaration table + each provider's current availability. The first
    (preferred + available) provider per model-key is named; a lower-ranked
    available fallback is noted; an unavailable-only key reports 'unavailable'.
    A provider whose recent calls keep falling through is named as failing, not
    as primary (R15-LIFECYCLE-021): availability is importability, not liveness."""
    report: dict[str, str] = {}
    model_keys = sorted({k for p in _PROVIDERS for k in p.serves})
    for model_key in model_keys:
        ranked = sorted((p for p in _PROVIDERS if model_key in p.serves), key=lambda p: p.rank)
        available = [p.id for p in ranked if p.available()]
        if not available:
            report[model_key] = "unavailable"
            continue
        failing = [p for p in available if provider_health.is_failing(p, model_key)]
        healthy = [p for p in available if p not in failing] or available
        notes = [f"{', '.join(healthy[1:])} fallback"] if healthy[1:] else []
        if failing and healthy is not available:
            notes.append(f"{', '.join(failing)} failing")
        report[model_key] = f"{healthy[0]} ({'; '.join(notes)})" if notes else healthy[0]
    # Keep the openbb-mcp availability line the existing /health consumers read.
    report["openbb-mcp"] = "available" if openbb_mcp_provider.is_available() else "unavailable"
    return report


__all__ = [
    "DEFAULT_CRYPTO_EXCHANGE",
    "ModelKey",
    "ProviderDeclaration",
    "active_providers",
    "declarations",
    "get_analyst_rating",
    "get_balance_sheet",
    "get_cash_flow",
    "get_fundamentals",
    "get_history",
    "get_income_statement",
    "get_macro_series",
    "get_quote",
]
