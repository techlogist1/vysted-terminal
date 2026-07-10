"""v0.5.0 agent tool — ``fundamentals``.

Migrated from v0.5.0's flat ``agent_tools.py`` with no behaviour change.
Registered via :func:`register` from
:func:`services.agent_tools.register_v0_5_0_tools` at sidecar startup
and from ``app.create_app``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from services.agent_tools import register_tool

#: One retry after a short backoff (R8 structured parity): the live failure
#: was a single transient provider hiccup turning into a brief that claimed
#: P/E "not available" while the equity panel — same provider_registry —
#: rendered it. A second attempt half a second later usually succeeds.
_RETRY_BACKOFF_SECS = 0.5

#: Closed reason vocabulary for a fundamentals-leg failure (R13 JARVIS 2a) — so
#: the model narrates the CAUSE, never a bare "unavailable" it can round up to a
#: world-absence claim. ``rate_limited``: the provider throttled THIS run (retry
#: helps); ``not_found``: the symbol did not resolve to a covered instrument;
#: ``provider_error``: an app-side / provider fetch failure — OUR feed's gap,
#: never proof the world does not publish the data.
_REASON_RATE_LIMITED = "rate_limited"
_REASON_NOT_FOUND = "not_found"
_REASON_PROVIDER_ERROR = "provider_error"

_RATE_LIMIT_MARKERS = (
    "rate limit",
    "rate-limit",
    "ratelimit",
    "429",
    "too many requests",
    "throttl",
)
_NOT_FOUND_MARKERS = ("not found", "no data", "no such", "unknown symbol", "delisted", "404")


def _classify_reason(error_text: str | None) -> str:
    """Map a provider/registry error string onto the closed reason vocabulary."""
    text = (error_text or "").lower()
    if any(marker in text for marker in _RATE_LIMIT_MARKERS):
        return _REASON_RATE_LIMITED
    if any(marker in text for marker in _NOT_FOUND_MARKERS):
        return _REASON_NOT_FOUND
    return _REASON_PROVIDER_ERROR


@dataclass(frozen=True)
class _FetchResult:
    fundamentals: Any | None
    error: str | None


async def _fetch_once(symbol: str) -> _FetchResult:
    """One ``provider_registry.get_fundamentals`` call, error captured (never raised)."""
    from services import provider_registry
    from services.errors import ProviderError

    try:
        fundamentals = await provider_registry.get_fundamentals(symbol)
    except ProviderError as exc:
        return _FetchResult(None, f"provider error: {exc}")
    except Exception as exc:  # noqa: BLE001
        return _FetchResult(None, f"unexpected error: {exc}")
    return _FetchResult(fundamentals, None)


@dataclass(frozen=True)
class _Canonicalization:
    """The ONE resolution-policy verdict on a model-supplied symbol.

    ``canonical_symbol`` is set only when the policy confidently ``bound`` a
    DIFFERENT yahoo-style symbol than the one supplied — a re-fetch under
    that symbol is worth trying. ``honest_not_found`` is set only when the
    policy found plausible-but-not-confident candidates (``disambiguate``) —
    those ride the tool result instead of a bare provider echo. Neither set
    (both ``None``) means "the resolver has nothing to add" — the original
    provider error stands unchanged (R10/R11's D46 substring-band hardening:
    a fuzzy/substring hit NEVER silently binds, and an outright miss is not
    manufactured into a false "unresolved" claim about a symbol the bundled
    US/NSE/BSE masters simply don't cover).
    """

    canonical_symbol: str | None = None
    note: str | None = None
    honest_not_found: dict[str, Any] | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)


def _instrument_candidate(instrument: Any) -> dict[str, Any]:
    return {
        "symbol": instrument.yahoo_symbol,
        "name": instrument.name,
        "exchange": instrument.exchange,
    }


def _canonicalize(symbol: str) -> _Canonicalization:
    """Run ``symbol`` through the ONE resolution policy (R10 ``decide``).

    Never reimplements matching — same seam as ``resolve_symbol``
    (:mod:`services.symbol_resolver` + :mod:`services.resolution_policy`).
    A confident ``bound`` verdict at a different symbol is a correctable
    typo (R12: the SIMPLEXREA.BO / SIMPLXREA.BO symbol-typo cascade); a
    ``disambiguate`` verdict carries candidates worth surfacing instead of a
    bare 404; an ``unresolved`` verdict means the bundled masters have
    nothing to say — never treated as proof the symbol itself is invalid.
    """
    import config
    from services import resolution_policy, symbol_resolver

    region = config.get_region()
    resolution = symbol_resolver.resolve(symbol, region=region)
    decision = resolution_policy.decide(resolution)

    if decision.outcome == "bound" and decision.instrument is not None:
        resolved = decision.instrument.yahoo_symbol
        if resolved.strip().upper() == symbol.strip().upper():
            return _Canonicalization()
        return _Canonicalization(
            canonical_symbol=resolved,
            note=f"resolved {symbol!r} → {resolved!r}",
        )

    if decision.outcome == "disambiguate" and decision.candidates:
        candidates = [_instrument_candidate(c) for c in decision.candidates]
        listed = ", ".join(f"{c['symbol']} ({c['name']})" for c in candidates[:6])
        return _Canonicalization(
            honest_not_found={
                "ok": False,
                "error": (
                    f"{symbol!r} did not resolve to one known instrument — did you mean: {listed}?"
                ),
                "reason": _REASON_NOT_FOUND,
                "candidates": candidates,
            },
            candidates=candidates,
        )

    return _Canonicalization()


async def _fundamentals(args: dict[str, Any]) -> dict[str, Any]:
    """Return valuation ratios + a company profile for ``symbol``.

    The Strategy Critic uses fundamentals to challenge value/growth
    strategy assumptions — e.g. flagging that a "value" backtest is
    really a high-beta backtest because the universe's average P/B
    ratio is sky-high.

    Args:
        symbol: Ticker. Required.

    Falls back through the same registry path as ``GET /fundamentals``;
    openbb-mcp when bundled, yfinance otherwise. The registry's
    fundamentals path is async (it awaits the openbb-mcp client). One
    transient provider exception gets ONE retry (0.5s backoff) before the
    honest ``ok: False`` — a single hiccup must not read as "no data exists".

    R12 (symbol-typo cascade): a model-supplied symbol that fails BOTH
    attempts is run through the resolution policy (:func:`_canonicalize`)
    before the failure is returned. A confidently-``bound`` different
    symbol gets ONE corrective re-fetch, surfaced via a ``note`` field on
    success ("resolved 'SIMPLEXREA.BO' -> 'SIMPLXREA.BO'") — never silent,
    so a narrative built on the result can say what happened. A
    ``disambiguate`` verdict returns the candidates instead of a bare
    provider 404 echo. A symbol the resolver has no opinion on (including
    one genuinely outside the bundled US/NSE/BSE masters) keeps the
    original provider error untouched — the resolver's silence is never
    read as "this symbol does not exist". The already-correct/first-try
    path never touches the resolver at all (unchanged fast path).
    """
    symbol = args.get("symbol")
    if not isinstance(symbol, str) or not symbol:
        return {"ok": False, "error": "missing or non-string symbol"}

    last_error: str = "unavailable"
    for attempt in (0, 1):
        result = await _fetch_once(symbol)
        if result.error is None:
            assert result.fundamentals is not None
            return {
                "ok": True,
                "fundamentals": result.fundamentals.model_dump(by_alias=True, mode="json"),
            }
        last_error = result.error
        if attempt == 0:
            await asyncio.sleep(_RETRY_BACKOFF_SECS)

    canonicalization = _canonicalize(symbol)
    if canonicalization.honest_not_found is not None:
        return canonicalization.honest_not_found

    if canonicalization.canonical_symbol is not None:
        corrected = await _fetch_once(canonicalization.canonical_symbol)
        if corrected.error is None:
            assert corrected.fundamentals is not None
            return {
                "ok": True,
                "fundamentals": corrected.fundamentals.model_dump(by_alias=True, mode="json"),
                "note": canonicalization.note,
            }
        last_error = corrected.error

    return {"ok": False, "error": last_error, "reason": _classify_reason(last_error)}


def register() -> None:
    """Register the ``fundamentals`` tool in the package registry."""
    register_tool("fundamentals", _fundamentals)


__all__ = ["_fundamentals", "register"]
