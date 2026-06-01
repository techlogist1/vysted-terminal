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
from collections.abc import Awaitable, Callable
from typing import Any

#: Injected tool dispatcher — ``await tool_call(name, args) -> dict``.
ToolCall = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

#: Honest fallback line when no web backend answered (web_search ok==False). Kept
#: short + actionable; the longer "how to unlock it" message rides the tool's own
#: ``message`` field, surfaced in ``web.note`` when present.
_NO_WEB_NOTE = "No web-search backend configured — structured data only"

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


def _structured_value(result: dict[str, Any], payload_key: str) -> dict[str, Any]:
    """Wrap one leg's result as a provenance-tagged structured value.

    Shape: ``{"ok": bool, "provider": str|None, "data": <payload>, "error": ...}``
    — uniform across legs so a consumer reads provenance the same way for price,
    fundamentals, news, and filings.
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
    return value


async def gather_fast(
    query: str,
    *,
    region: str | None = None,
    tool_call: ToolCall,
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
    ``suggested_indicators`` hints. Resolution failure short-circuits with
    ``ok: False`` (no point pulling price for an unknown name).
    """
    resolve_args: dict[str, Any] = {"query": query}
    if region:
        resolve_args["region"] = region
    resolved = await _safe_call(tool_call, "resolve_symbol", resolve_args)

    if not resolved.get("ok"):
        return {
            "ok": False,
            "query": query,
            "resolved": resolved,
            "error": resolved.get("message") or resolved.get("error") or "could not resolve query",
        }

    instrument = resolved.get("resolved") or {}
    symbol = instrument.get("symbol") or query
    name = instrument.get("name") or symbol
    asset_class = instrument.get("asset_class")

    # 2 — parallel structured fan-out. Each leg is pre-wrapped so a single
    # provider failure surfaces as ok:False in that slot, not a gather crash.
    price_res, fundamentals_res, news_res, filings_res = await asyncio.gather(
        _safe_call(tool_call, "price_data", {"symbol": symbol}),
        _safe_call(tool_call, "fundamentals", {"symbol": symbol}),
        _safe_call(tool_call, "news", {"symbols": [symbol]}),
        _safe_call(tool_call, "sec_filings_list", {"symbol": symbol}),
    )

    structured = {
        "price": _structured_value(price_res, "quote"),
        "fundamentals": _structured_value(fundamentals_res, "fundamentals"),
        "news": _structured_value(news_res, "news"),
        "filings": _structured_value(filings_res, "filings"),
    }

    # 3 — ONE web round. The query frames the instrument by display name so a
    # web backend ranks on the company, not the bare ticker.
    web_res = await _safe_call(
        tool_call,
        "web_search",
        {"query": f"{name} {query} news outlook"},
    )
    web_ok = bool(web_res.get("ok"))
    web: dict[str, Any] = {
        "available": web_ok,
        "citations": web_res.get("citations", []) if web_ok else [],
        "results": web_res.get("results", []) if web_ok else [],
    }
    if not web_ok:
        # Honest fallback — surface the canonical short note plus the tool's own
        # "how to unlock it" message when it gave one. NEVER an empty section
        # pretending to be "no news".
        web["note"] = _NO_WEB_NOTE
        detail = web_res.get("message") or web_res.get("error")
        if detail:
            web["detail"] = detail

    return {
        "ok": True,
        "query": query,
        "resolved": resolved,
        "symbol": symbol,
        "structured": structured,
        "web": web,
        "suggested_layout": "research-cockpit",
        "suggested_indicators": _suggested_indicators(asset_class),
    }


__all__ = ["ToolCall", "gather_fast"]
