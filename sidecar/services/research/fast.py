"""FAST research — the NO-LLM structured bundle (FR-070, US12).

``gather_fast`` is the cheap, deterministic half of the research engine: it does
NOT call an LLM. It resolves the query to a concrete instrument, fans the data
pulls out in PARALLEL (price / fundamentals / news / SEC filings — each isolated
so one provider failure is non-fatal), runs ONE web round, and returns a
structured bundle plus layout hints. The agent then synthesises the prose from
this bundle (prompt-driven, ratified) — keeping the FAST path free of model
spend and the prose under the agent's voice.

Honesty contract (FR-082): when the web-search backend is unconfigured the
``web_search`` tool returns ``ok: False``; this bundle surfaces that as
``web.available = False`` plus an honest ``note`` naming the structured-only
fallback — never an empty section dressed up as "no news" and never a fabricated
source.

The tool layer is INJECTED (``tool_call``) so this module stays testable with a
fake and carries no import-time dependency on the agent-tool registry.
"""

from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from .models import ResearchStep

if TYPE_CHECKING:  # import-light: no runtime dependency (see module docstring)
    from services.research.target import ResearchTarget

#: Injected tool dispatcher — ``await tool_call(name, args) -> dict``.
ToolCall = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

#: Injected step sink — ``on_step(ResearchStep) -> None`` (may be a coroutine).
#: The FAST path is short (≤15s) but the agent surface still animates a live
#: trace from it (Track A) so even the default research mode feels alive. ``None``
#: outside an agent run (tests / direct calls) — emission is then a silent no-op.
OnStep = Callable[[ResearchStep], Any]


async def _emit(on_step: OnStep | None, step: ResearchStep) -> None:
    """Forward one step to the sink, best-effort — a cosmetic trace must NEVER
    break a research pull (a raising/garbled sink is swallowed)."""
    if on_step is None:
        return
    try:
        result = on_step(step)
        if inspect.isawaitable(result):
            await result
    except Exception:  # noqa: BLE001 — the live trace is cosmetic, never fatal
        pass


def _ms(start: float) -> int:
    """Elapsed wall time since ``start`` (a ``perf_counter`` reading) in ms."""
    return int((time.perf_counter() - start) * 1000)


#: Honest fallback line when no web backend answered (web_search ok==False). Kept
#: short + actionable; the longer "how to unlock it" message rides the tool's own
#: ``message`` field, surfaced in ``web.detail`` when present. Used ONLY for a
#: genuine no-backend / unreachable failure — a TRANSIENT throttle gets the
#: rate-limit note below so the brief never falsely claims "no backend".
_NO_WEB_NOTE = "No web-search backend configured — structured data only"

#: Honest note for a TRANSIENT throttle (DDG 202/429): the backend IS configured,
#: it just rate-limited this run. Distinct from ``_NO_WEB_NOTE`` so the brief never
#: tells a keyless user "no backend" when the floor was merely throttled.
_RATE_LIMITED_NOTE = "Web search was rate-limited — retry in a moment"

#: Per-asset-class indicator presets the research-cockpit layout opens with.
#: Equities get trend + momentum (MA/RSI/MACD); ETFs drop MACD (basket, less
#: single-name momentum signal); crypto leans on EMA + VWAP (24/7, intraday).
_INDICATORS_BY_CLASS: dict[str, list[str]] = {
    "equity": ["ma", "volume", "rsi", "macd"],
    "etf": ["ma", "volume", "rsi"],
    "crypto": ["ema", "vwap", "rsi", "volume"],
}
_DEFAULT_INDICATORS = _INDICATORS_BY_CLASS["equity"]


def _suggested_indicators(asset_class: str | None) -> list[str]:
    """Map an instrument's asset class to the cockpit's opening indicator set."""
    key = (asset_class or "").strip().lower()
    if key in ("crypto", "cryptocurrency"):
        key = "crypto"
    elif key in ("etf", "fund"):
        key = "etf"
    return list(_INDICATORS_BY_CLASS.get(key, _DEFAULT_INDICATORS))


async def _safe_call(tool_call: ToolCall, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Invoke one tool, converting ANY failure to an ``ok: False`` dict.

    The parallel fan-out must be non-fatal per leg: a single provider raising
    must not collapse the whole bundle. A raised exception becomes a structured
    ``{"ok": False, "error": ...}`` so the caller treats a crash and a clean
    provider miss the same way.
    """
    try:
        result = await tool_call(name, args)
    except Exception as exc:  # noqa: BLE001 — any tool failure is a soft miss here
        return {"ok": False, "error": f"{name} failed: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": f"{name} returned a non-dict result"}
    return result


def _provider_of(result: dict[str, Any]) -> str | None:
    """Best-effort provenance label from a tool result.

    Structured tools carry their source differently — ``price_data`` puts a
    top-level ``provider``; fundamentals/news/filings nest it under their payload
    or a ``mode``/``source`` field. Pull the first that's present so every
    structured value is provenance-tagged for the FR-041 badge.
    """
    if not isinstance(result, dict):
        return None
    for key in ("provider", "source", "mode"):
        val = result.get(key)
        if isinstance(val, str) and val:
            return val
    # Nested payloads (fundamentals -> {"fundamentals": {...}}, filings ->
    # {"filings": {"items": [{...}]}}). Look one dict-level in, then into the
    # first row of any list found there, so a provider tagged on the rows (SEC
    # filings carry it per item, not at the top) is still surfaced.
    for payload_key in ("fundamentals", "quote", "filings", "news"):
        payload = result.get(payload_key)
        prov = _provider_in(payload)
        if prov is not None:
            return prov
    return None


def _provider_in(payload: Any) -> str | None:
    """Find a provider/source/mode string in a dict, or the first row of a list
    (or a dict's first list value) — one level deep, best-effort."""
    if isinstance(payload, dict):
        for key in ("provider", "source", "mode"):
            val = payload.get(key)
            if isinstance(val, str) and val:
                return val
        for val in payload.values():
            if isinstance(val, list):
                prov = _provider_in(val)
                if prov is not None:
                    return prov
    elif isinstance(payload, list) and payload:
        return _provider_in(payload[0])
    return None


#: Closed reason vocabulary for a FAILED structured leg (R13 JARVIS 2a) — so the
#: model reads the CAUSE of a missing leg, never a bare "unavailable" it can round
#: up to "the world doesn't publish X". A provider/app failure is OUR feed's gap
#: (``provider_error``); a transient throttle is ``rate_limited``; a genuine
#: no-such-instrument is ``not_found``. Absent → the consumer defaults to a gap,
#: never a world-absence claim.
_LEG_REASONS = ("provider_error", "rate_limited", "not_found")
_LEG_RATE_LIMIT_MARKERS = ("rate limit", "rate-limit", "ratelimit", "429", "throttl")
_LEG_NOT_FOUND_MARKERS = ("not found", "no data", "no such", "delisted", "404", "not available")


def _leg_reason(result: dict[str, Any]) -> str:
    """The failed leg's closed-vocabulary reason: the tool's own ``reason`` when
    it is a known token, else inferred from the error/message text."""
    reason = result.get("reason")
    if isinstance(reason, str) and reason in _LEG_REASONS:
        return reason
    text = str(result.get("error") or result.get("message") or "").lower()
    if any(marker in text for marker in _LEG_RATE_LIMIT_MARKERS):
        return "rate_limited"
    if any(marker in text for marker in _LEG_NOT_FOUND_MARKERS):
        return "not_found"
    return "provider_error"


def _structured_value(result: dict[str, Any], payload_key: str) -> dict[str, Any]:
    """Wrap one leg's result as a provenance-tagged structured value.

    Shape: ``{"ok": bool, "provider": str|None, "data": <payload>, "error": ...,
    "reason": ...}`` — uniform across legs so a consumer reads provenance the
    same way for price, fundamentals, news, and filings. A FAILED leg carries a
    closed-vocabulary ``reason`` (R13 JARVIS 2a) so the model narrates the cause
    of the gap, never a silent absence it can round up to a world-absence claim.
    """
    ok = bool(result.get("ok"))
    value: dict[str, Any] = {"ok": ok, "provider": _provider_of(result)}
    if ok:
        # Prefer the named payload; fall back to the whole result minus the
        # bookkeeping keys so an unexpected shape still carries data.
        if payload_key in result:
            value["data"] = result[payload_key]
        else:
            value["data"] = {
                k: v for k, v in result.items() if k not in ("ok", "provider", "source", "mode")
            }
    else:
        value["error"] = result.get("error") or result.get("message") or "unavailable"
        value["reason"] = _leg_reason(result)
    return value


def _apply_dividend_ttm(fund_data: dict[str, Any], ttm: Any) -> None:
    """Thread the trailing-12m PAID result onto the fundamentals leg (R13, D56+).

    A ``DividendTTM`` carries the null-vs-affirmed-zero distinction the raw scalar
    cannot: a ``"paid"`` value is set as before; an ``"affirmed_zero"`` sets the
    field to ``0.0`` with a ``field_meta`` entry LABELED "no dividends paid
    (trailing 12m)" (an honest, stateable zero, not a null); an ``"unavailable"``
    leaves the field null but stamps a ``field_meta`` reason so a consumer reads
    "unknown, and why" rather than a bare, unexplained dash.
    """
    status = getattr(ttm, "status", None)
    if status == "paid" and ttm.value is not None:
        fund_data["dividend_per_share_ttm"] = ttm.value
        _stamp_field_meta(fund_data, "dividend_per_share_ttm", status="ok")
    elif status == "affirmed_zero":
        fund_data["dividend_per_share_ttm"] = 0.0
        _stamp_field_meta(
            fund_data, "dividend_per_share_ttm", status="ok", reason=ttm.reason, label=ttm.reason
        )
    else:  # unavailable — leave the value null, but say why
        _stamp_field_meta(
            fund_data,
            "dividend_per_share_ttm",
            status="unavailable",
            reason=getattr(ttm, "reason", None),
        )


def _stamp_field_meta(
    fund_data: dict[str, Any],
    field: str,
    *,
    status: str,
    reason: str | None = None,
    label: str | None = None,
) -> None:
    """Set one ``field_meta`` entry on the fundamentals wire dict (additive).

    ``field_meta`` rides the fundamentals payload as a plain dict of dicts here
    (not the typed model), so a derived cross-check can annotate a field's coverage
    without re-serialising the whole payload.
    """
    meta = fund_data.get("field_meta")
    if not isinstance(meta, dict):
        meta = {}
        fund_data["field_meta"] = meta
    entry: dict[str, Any] = {"status": status, "provider": "yfinance"}
    if reason is not None:
        entry["reason"] = reason
    if label is not None:
        entry["label"] = label
    meta[field] = entry


async def snapshot_structured(
    tool_call: ToolCall,
    symbol: str,
    *,
    region: str | None = None,
    canonical_name: str | None = None,
) -> dict[str, Any]:
    """A price + fundamentals snapshot as provenance-tagged structured legs.

    Shared by the FAST bundle and the DEEP/iter/heavy briefs (and the Tier B
    research-model lane) so ALL back the frontend metric cards from the same
    uniform ``{ok, provider, data}`` shape. Each leg is pre-wrapped (a single
    provider failure surfaces as ``ok: False`` in that slot, never a crash), so
    this never raises — an empty/failed leg simply renders no card.

    R10 (E8): the ONE metric-semantics hook — the ``derived`` leg
    (:func:`services.research.semantics.derive_semantics`) rides every
    snapshot, so labeled, basis-true metrics and flagged conflicts reach every
    research path through this single seam.

    R11 (D56): the fundamentals leg is augmented with
    ``dividend_per_share_ttm`` — the trailing-12-month dividends actually paid
    (:func:`services.dividend_history.get_dividend_ttm`) — so the derived leg
    can reconcile it against Yahoo's ``dividendRate`` and flag an omitted
    special dividend. The cross-check never raises (it swallows every failure to
    ``None``); an absent figure simply means no reconciliation card.

    R12 (D66): the same pattern for growth — when the provider claims MRQ-YoY
    growth scalars, ``revenue_growth_computed``/``earnings_growth_computed``
    (+ ``growth_computed_quarters``) are computed deterministically from the
    provider's own QUARTERLY income statements
    (:func:`services.growth_check.get_quarterly_yoy`) so the derived leg can
    flag a scalar that contradicts the statements. Disclosure only — the
    provider values are never replaced; missing statements attach nothing.

    R13 (D68/D57): two more disclosure-only cross-checks ride the same fan-out.
    ``ownership_exchange`` (:func:`services.ownership_check.get_exchange_ownership`)
    is the latest NSE/BSE shareholding pattern, reconciled against yfinance's
    ``heldPercentInsiders``/``heldPercentInstitutions`` (which drift materially
    from the exchange filing). ``dividend_declared``
    (:func:`services.dividend_actions.get_declared_unpaid_dividend`) is the
    nearest declared-but-not-yet-paid dividend, separated from the D56 TTM-paid
    figure so a future record date never collapses into "paid". Both never raise
    (every failure becomes ``None``); an absent figure attaches nothing.

    R13 (D70/D71/D72): three more disclosure-only cross-checks ride the same
    fan-out. ``earnings_quality``
    (:func:`services.earnings_quality.get_earnings_quality`) measures the one-off
    distortion in reported net income (the reported-vs-adjusted PE/ROE trap).
    ``range_52w_exchange``
    (:func:`services.research.range_check.get_52w_range`) recomputes the 52-week
    high/low from the app's own exchange-direct history to catch a wrong provider
    pair. ``market_cap_witness``
    (:func:`services.market_cap_witness.get_market_cap_witness`) supplies a
    NON-provider (BSE-derived) share count so the market-cap check is not
    circular. All three never raise; an absent figure attaches nothing.
    """
    from services import (
        dividend_actions,
        earnings_quality,
        growth_check,
        market_cap_witness,
        ownership_check,
    )
    from services.dividend_history import get_dividend_ttm
    from services.research import range_check
    from services.research.semantics import derive_semantics

    price_res, fund_res = await asyncio.gather(
        _safe_call(tool_call, "price_data", {"symbol": symbol}),
        _safe_call(tool_call, "fundamentals", {"symbol": symbol}),
    )
    out = {
        "price": _structured_value(price_res, "quote"),
        "fundamentals": _structured_value(fund_res, "fundamentals"),
    }
    # Cross-check the dividend scalar against corporate-action history and the
    # growth scalars against the quarterly income statements. Use the symbol
    # the fundamentals leg actually resolved to (its ``symbol`` carries the
    # Yahoo listing form) so both checks reconcile against the SAME scalars.
    fund_leg = out["fundamentals"]
    fund_data = fund_leg.get("data") if fund_leg.get("ok") else None
    if isinstance(fund_data, dict):
        resolved = fund_data.get("symbol")
        listing = resolved if isinstance(resolved, str) and resolved else symbol

        async def _yoy() -> growth_check.QuarterlyYoY | None:
            if not growth_check.should_cross_check(fund_data):
                return None
            return await growth_check.get_quarterly_yoy(listing)

        async def _own() -> ownership_check.ExchangeOwnership | None:
            if not ownership_check.should_cross_check(fund_data):
                return None
            return await ownership_check.get_exchange_ownership(listing)

        # R13 (D70/D71/D72): three more disclosure-only cross-checks ride the same
        # fan-out — reported-vs-adjusted earnings (annual income statement), the
        # 52-week range (exchange-direct history), and the market-cap witness (a
        # NON-provider BSE share count). Each is applicability-gated, never raises,
        # and attaches nothing when it has no comparison to make.
        async def _earn() -> earnings_quality.EarningsQuality | None:
            if not earnings_quality.should_cross_check(fund_data):
                return None
            return await earnings_quality.get_earnings_quality(listing)

        async def _range() -> range_check.Range52w | None:
            if not range_check.should_cross_check(fund_data):
                return None
            return await range_check.get_52w_range(listing)

        async def _mcap() -> market_cap_witness.MarketCapWitness | None:
            if not market_cap_witness.should_cross_check(fund_data):
                return None
            return await market_cap_witness.get_market_cap_witness(listing)

        ttm, yoy, own, declared, earn, rng, mcw = await asyncio.gather(
            get_dividend_ttm(listing),
            _yoy(),
            _own(),
            dividend_actions.get_declared_unpaid_dividend(listing),
            _earn(),
            _range(),
            _mcap(),
        )
        _apply_dividend_ttm(fund_data, ttm)
        if yoy is not None:
            if yoy.revenue_growth is not None:
                fund_data["revenue_growth_computed"] = yoy.revenue_growth
            if yoy.earnings_growth is not None:
                fund_data["earnings_growth_computed"] = yoy.earnings_growth
            fund_data["growth_computed_quarters"] = {"mrq": yoy.mrq, "prior": yoy.prior}
        if own is not None:
            fund_data[ownership_check.OWNERSHIP_KEY] = own.as_wire()
        if declared is not None:
            fund_data[dividend_actions.DECLARED_KEY] = declared.as_wire()
        if earn is not None:
            fund_data[earnings_quality.EARNINGS_KEY] = earn.as_wire()
        if rng is not None:
            fund_data[range_check.RANGE_KEY] = rng.as_wire()
        if mcw is not None:
            fund_data[market_cap_witness.MCAP_WITNESS_KEY] = mcw.as_wire()
    out["derived"] = derive_semantics(out, region, canonical_name=canonical_name, symbol=symbol)
    return out


#: How many exchange announcements the IN filings leg fetches (R13 ledger #10)
#: — mirrors :data:`services.research.disclosures._ANNOUNCEMENT_LIMIT`'s order
#: of magnitude without importing a private constant.
_FAST_ANNOUNCEMENTS_LIMIT = 20


async def _filings_leg(tool_call: ToolCall, target: ResearchTarget) -> dict[str, Any]:
    """The filings leg, routed by REGION (R13 ledger #10).

    SEC EDGAR indexes US filings — for an IN-listed target it is the WRONG
    lane (a different jurisdiction's index entirely, and its MCP sidecar can
    independently be down), so an Indian listing routes to the exchange
    announcements feed instead: the SAME ``corporate_announcements`` tool the
    DEEP path already consults for disclosures
    (:func:`services.research.disclosures.gather_floor`) — mirrored here, not
    reimplemented. The US path is UNCHANGED: ``sec_filings_list``, including
    its own honest "sidecar unavailable" shape (:func:`_leg_reason` still
    classifies a down sidecar as ``provider_error``).
    """
    from services.research.relevance import is_india_target

    if is_india_target(target):
        result = await _safe_call(
            tool_call,
            "corporate_announcements",
            {"symbol": target.symbol, "limit": _FAST_ANNOUNCEMENTS_LIMIT},
        )
        value = _structured_value(result, "filings")
        # corporate_announcements carries no top-level provider/source/mode key
        # (unlike sec_filings_list's per-item "sec-edgar" tag) — stamp the
        # exchange feed's own provenance so the FR-041 badge still renders.
        if value.get("ok") and not value.get("provider"):
            value["provider"] = "nse+bse"
        return value
    result = await _safe_call(tool_call, "sec_filings_list", {"symbol": target.symbol})
    return _structured_value(result, "filings")


def _news_row(item: dict[str, Any]) -> dict[str, Any]:
    """Map a ``NewsItem`` wire dict to the relevance gate's row shape."""
    return {
        "title": item.get("title"),
        "excerpt": item.get("summary"),
        "url": item.get("url"),
        "source": item.get("source"),
    }


#: Honest note when the relevance gate drops EVERY item off an ok:True news
#: pull (R13 ledger #9) — never generic filler dressed up as coverage.
def _no_on_entity_news_note(symbol: str, dropped: int) -> str:
    return (
        f"No on-entity news found for {symbol} — {dropped} item(s) returned by "
        "the news feed were off-entity/off-topic and dropped."
    )


def _news_value(result: dict[str, Any], *, target: ResearchTarget) -> dict[str, Any]:
    """The news leg, relevance-gated for a resolved IN equity (R13 ledger #9).

    The ``news`` tool blends region-wide market feeds with a per-symbol Yahoo
    feed keyed by the BARE ticker. For a short/common Indian symbol (META,
    BMW, ...) that per-symbol feed can serve the FOREIGN namesake's own
    stories (Meta Platforms, not the BSE-listed String Metaverse), and the
    region feeds serve generic macro headlines unrelated to any one name —
    both ride back stamped ``ok: True`` with nothing distinguishing on-entity
    from off-entity. Reuse the SAME entity-relevance gate the web-evidence
    loop uses (:func:`services.research.relevance.row_relevant`) — no new
    scoring — to drop off-entity rows; when NOTHING on-entity survives the leg
    stays ``ok: True`` with an empty list and an honest note (never generic
    filler dressed up as coverage).
    """
    value = _structured_value(result, "news")
    if not value.get("ok"):
        return value
    from services.research.relevance import is_india_target, row_relevant

    if not (is_india_target(target) and target.is_equity_like()):
        return value
    items = value.get("data")
    if not isinstance(items, list) or not items:
        return value
    kept = [
        item
        for item in items
        if isinstance(item, dict) and row_relevant(_news_row(item), target=target)
    ]
    if kept:
        value["data"] = kept
    else:
        value["data"] = []
        value["note"] = _no_on_entity_news_note(target.symbol, len(items))
    return value


async def _web_round(tool_call: ToolCall, web_query: str) -> dict[str, Any]:
    """ONE web round → the bundle's honest ``web`` section.

    Surfaces a note plus the tool's own "how to unlock it" message when no
    backend answered — NEVER an empty section pretending to be "no news".
    Distinguishes a TRANSIENT throttle (the backend exists, it was rate-limited
    this run) from a genuine no-backend miss: the former must not claim "no
    backend configured" (that would be a false banner — symptom #2).
    """
    web_res = await _safe_call(tool_call, "web_search", {"query": web_query})
    web_ok = bool(web_res.get("ok"))
    web: dict[str, Any] = {
        "available": web_ok,
        "citations": web_res.get("citations", []) if web_ok else [],
        "results": web_res.get("results", []) if web_ok else [],
    }
    # R9 gate 2: carry the retrieval backend id through the rewrap — the
    # web_search tool stamps "keyless-fallback" here and the published brief's
    # nudge banner keys on it (auto-publish lifts web.backend onto the brief).
    backend = web_res.get("backend")
    if backend:
        web["backend"] = backend
    if not web_ok:
        reason = web_res.get("reason")
        web["reason"] = reason
        web["note"] = _RATE_LIMITED_NOTE if reason == "rate_limited" else _NO_WEB_NOTE
        detail = web_res.get("message") or web_res.get("error")
        if detail:
            web["detail"] = detail
    return web


async def gather_fast(
    query: str,
    *,
    region: str | None = None,
    tool_call: ToolCall,
    on_step: OnStep | None = None,
) -> dict[str, Any]:
    """Pull the FAST structured research bundle for ``query`` (NO LLM).

    Steps:
      1. ``resolve_symbol`` — turn the free-text query into a concrete instrument.
      2. In PARALLEL (``asyncio.gather``, each leg wrapped non-fatal):
         ``price_data``, ``fundamentals``, ``news``, ``sec_filings_list``.
      3. ONE web round: ``web_search`` for "<name> <query> news outlook".

    Returns the bundle described in the unit brief: ``resolved``, a provenance-
    tagged ``structured`` map, an honest ``web`` section (``available=False`` +
    note when no backend answered), and the cockpit ``suggested_layout`` /
    ``suggested_indicators`` hints.

    R8 target contract: resolution happens ONCE via
    :func:`services.research.target.resolve_target` (policy verdict +
    symbol-shape gate). With NO bound target the bundle is WEB-ONLY: zero
    structured calls (a free-text query never rides a ``symbol`` arg),
    ``symbol = ""``, and the honest one-line :data:`NO_INSTRUMENT_NOTE`.
    R10 (D37): an ambiguous resolution returns the explicit "which did you
    mean?" payload instead — no structured pulls, no web spend, no guess.
    """
    from services.research.target import (
        NO_INSTRUMENT_NOTE,
        ResearchDisambiguation,
        resolve_target,
        resolved_payload,
    )

    t0 = time.perf_counter()
    await _emit(on_step, ResearchStep("plan", f'resolving "{query}"'))
    target = await resolve_target(tool_call, query, region=region)

    if isinstance(target, ResearchDisambiguation):
        await _emit(
            on_step,
            ResearchStep("plan", "ambiguous instrument — asking which one was meant", _ms(t0)),
        )
        out = target.payload(query=query)
        out["execution_loop"] = "fast"
        return out

    if target is None:
        await _emit(
            on_step,
            ResearchStep("plan", "no listed instrument matched — web evidence only", _ms(t0)),
        )
        t_web = time.perf_counter()
        await _emit(on_step, ResearchStep("search", f"searching the web for {query}"))
        web = await _web_round(tool_call, f"{query} news outlook")
        _hits = len(web["citations"]) or len(web["results"])
        await _emit(
            on_step,
            ResearchStep(
                "search",
                f"{_hits} web source(s)" if web["available"] else "no web backend",
                _ms(t_web),
                status="ok" if web["available"] else "skipped",
            ),
        )
        await _emit(on_step, ResearchStep("synthesize", "assembling the research bundle"))
        return {
            "ok": True,
            "query": query,
            "resolved": resolved_payload(None),
            "symbol": "",
            "structured": {},
            "web": web,
            "note": NO_INSTRUMENT_NOTE,
            "suggested_layout": "research-cockpit",
            "suggested_indicators": _suggested_indicators(None),
            "execution_loop": "fast",
        }

    resolved = resolved_payload(target)
    symbol = target.symbol
    name = target.name or symbol
    asset_class = target.asset_class
    await _emit(on_step, ResearchStep("plan", f"resolved → {symbol}", _ms(t0)))

    # 2 — parallel structured fan-out. Each leg is pre-wrapped so a single
    # provider failure surfaces as ok:False in that slot, not a gather crash.
    # Price + fundamentals ride snapshot_structured — the ONE seam that also
    # computes the derived metric-semantics leg (R10, E8) for every path.
    # R13 ledger #10: the filings leg is ROUTED by region (:func:`_filings_leg`)
    # — SEC EDGAR for a US listing (unchanged), exchange announcements for an
    # IN one, so the wrong-jurisdiction/wrong-sidecar lane is never consulted
    # for an Indian name.
    t1 = time.perf_counter()
    await _emit(on_step, ResearchStep("tool", f"pulling market data for {symbol}"))
    news_res, filings_value, snapshot = await asyncio.gather(
        _safe_call(tool_call, "news", {"symbols": [symbol]}),
        _filings_leg(tool_call, target),
        snapshot_structured(tool_call, symbol, region=region, canonical_name=target.name),
    )

    # R13 ledger #9: the news leg is relevance-gated for a resolved IN equity
    # (:func:`_news_value`) — off-entity rows (a foreign namesake's feed,
    # generic macro headlines) never count as this instrument's coverage.
    structured = {
        **snapshot,
        "news": _news_value(news_res, target=target),
        "filings": filings_value,
    }
    _ok_legs = sum(
        1
        for leg in ("price", "fundamentals", "news", "filings")
        if (structured.get(leg) or {}).get("ok")
    )
    await _emit(
        on_step,
        ResearchStep("tool", f"pulled {_ok_legs}/4 data sources", _ms(t1)),
    )

    # 3 — ONE web round. The query anchors the instrument: the QUOTED display
    # name pins the engine on the company + the bare ticker for the exact-symbol
    # hits (R13 — the unquoted "{name} {query}" let a famous foreign namesake
    # shadow a ≤3-char ticker). Kept short: no exchange/industry token here (the
    # NORMAL path favours a keyless-engine-friendly query — the DEEP/ULTRA
    # researcher queries carry the exchange anchor). ``name == symbol`` (no
    # display name) drops the redundant quoted duplicate.
    t2 = time.perf_counter()
    await _emit(on_step, ResearchStep("search", f"searching the web for {name}"))
    web_query = (
        f'"{name}" {symbol} {query} news outlook'
        if name and name.upper() != symbol
        else f"{symbol} {query} news outlook"
    )
    web = await _web_round(tool_call, web_query)
    web_ok = web["available"]
    _hits = len(web["citations"]) or len(web["results"])
    await _emit(
        on_step,
        ResearchStep(
            "search",
            f"{_hits} web source(s)" if web_ok else "no web backend — structured only",
            _ms(t2),
            status="ok" if web_ok else "skipped",
        ),
    )
    await _emit(on_step, ResearchStep("synthesize", "assembling the research bundle"))

    return {
        "ok": True,
        "query": query,
        "resolved": resolved,
        "symbol": symbol,
        "structured": structured,
        "web": web,
        "suggested_layout": "research-cockpit",
        "suggested_indicators": _suggested_indicators(asset_class),
        "execution_loop": "fast",
    }


__all__ = ["ToolCall", "gather_fast", "snapshot_structured"]
