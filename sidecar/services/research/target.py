"""ResearchTarget — the ONE instrument binding for a research run (R8).

Root cause of the R8 symbol-truth defects: every research layer re-resolved its
own symbol from whatever text it was handed, so a heavy explorer re-resolved the
FOCUS-AUGMENTED task string ("Saksoft Limited — focus: Analyze revenue growth…")
and either published the whole sentence as ``brief.symbol`` or fuzzy-bound a
WRONG instrument (a Reliance run bound CMTL). This module is the fix:

  - :func:`resolve_target` calls ``resolve_symbol`` exactly ONCE, on the CLEAN
    user query, and binds the result to a frozen :class:`ResearchTarget` — or
    ``None`` when nothing trustworthy matched.
  - A **confidence floor** (:data:`CONFIDENCE_FLOOR`): a fuzzy match below it is
    rejected rather than silently bound to the wrong company.
  - A **symbol-shape gate** (:data:`SYMBOL_SHAPE`): whatever the resolver
    returns must LOOK like a ticker after uppercasing — a sentence can never
    become a "symbol" again.

Every research loop threads the SAME bound target down (heavy explorers receive
it and never re-resolve); all structured tool calls use ``target.symbol``. When
the target is ``None`` the run proceeds web-only with the honest
:data:`NO_INSTRUMENT_NOTE` — zero ``vysted://`` calls with a non-symbol, and
``brief.symbol = ""``.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

#: Injected tool dispatcher — ``await tool_call(name, args) -> dict`` (the same
#: seam the loops use; redefined locally to avoid a circular import with deep).
ToolCall = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

#: Resolver confidence below this is REJECTED — an uncertain fuzzy match must
#: not silently bind research to the wrong instrument.
CONFIDENCE_FLOOR = 0.5

#: A bound symbol must look like a ticker after uppercasing. This gate is what
#: makes "Saksoft Limited — focus: Analyze revenue growth…" structurally unable
#: to ever become a symbol again.
SYMBOL_SHAPE = re.compile(r"^[A-Z0-9][A-Z0-9.\-&]{0,19}$")

#: The honest one-line statement a web-only (no-target) brief carries.
NO_INSTRUMENT_NOTE = "No listed instrument matched this query — web evidence only."


@dataclass(frozen=True, slots=True)
class ResearchTarget:
    """The one instrument a research run is bound to — resolved exactly once.

    ``raw`` carries the full resolver wire reply (candidates, disambiguation
    flag) for the ``structured["resolved"]`` surface; it never participates in
    equality so two targets bound to the same instrument compare equal.
    """

    symbol: str
    name: str
    exchange: str | None
    asset_class: str | None
    confidence: float
    region: str | None
    raw: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    def is_equity_like(self) -> bool:
        """True unless the instrument is explicitly a crypto/fx asset — drives
        the equity-targeted junk filters (crypto hosts are noise for an equity)."""
        kind = (self.asset_class or "").strip().lower()
        return kind not in ("crypto", "cryptocurrency", "fx", "currency", "forex")


def target_from_payload(
    payload: dict[str, Any], *, region: str | None = None
) -> ResearchTarget | None:
    """Bind a ``resolve_symbol`` wire reply to a target, or ``None``.

    Applies the confidence floor and the symbol-shape gate; anything that fails
    either is rejected — research then proceeds web-only rather than bound to a
    wrong or malformed instrument.
    """
    if not isinstance(payload, dict) or not payload.get("ok"):
        return None
    instrument = payload.get("resolved")
    if not isinstance(instrument, dict):
        return None
    symbol = str(instrument.get("symbol") or "").strip().upper()
    if not symbol or SYMBOL_SHAPE.match(symbol) is None:
        return None
    try:
        confidence = float(instrument.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < CONFIDENCE_FLOOR:
        return None
    name = str(instrument.get("name") or "").strip() or symbol
    exchange = instrument.get("exchange")
    asset_class = instrument.get("asset_class")
    inst_region = instrument.get("region")
    return ResearchTarget(
        symbol=symbol,
        name=name,
        exchange=str(exchange) if isinstance(exchange, str) and exchange else None,
        asset_class=str(asset_class) if isinstance(asset_class, str) and asset_class else None,
        confidence=confidence,
        region=(
            str(inst_region) if isinstance(inst_region, str) and inst_region else (region or None)
        ),
        raw=payload,
    )


async def _resolve_once(
    tool_call: ToolCall, query: str, region: str | None
) -> ResearchTarget | None:
    """One resolver call → gated target, or ``None``. Never raises."""
    args: dict[str, Any] = {"query": query}
    if region:
        args["region"] = region
    try:
        payload = await tool_call("resolve_symbol", args)
    except Exception:  # noqa: BLE001 — a resolver crash means "no binding", never an abort
        return None
    if not isinstance(payload, dict):
        return None
    return target_from_payload(payload, region=region)


#: Prefix lengths (in words) tried when the full query does not resolve. Models
#: routinely pass keyword-salad queries ("Route Mobile Q4 FY26 quarterly results
#: revenue profit dividend…") where the COMPANY leads the string — the live R8
#: gate-1 rerun produced exactly this and an unbound, empty run. Longest first
#: so "Route Mobile" wins over a one-word "Route" mis-bind.
_PREFIX_WORDS = (4, 3, 2)


async def resolve_target(
    tool_call: ToolCall, query: str, region: str | None = None
) -> ResearchTarget | None:
    """Resolve the CLEAN user ``query`` to a target — the run's ONE resolution.

    Tries the full query first; when that does not bind (keyword-salad queries
    where only the leading words name the company), falls back to leading-word
    prefixes (4 → 3 → 2 words), accepting the first match that clears the
    confidence floor + shape gate. Never raises; ``None`` means web-only.
    Downstream layers must never re-resolve derived prompt text.
    """
    text = (query or "").strip()
    target = await _resolve_once(tool_call, text, region)
    if target is not None:
        return target
    words = text.split()
    tried = {text.lower()}
    for n in _PREFIX_WORDS:
        if len(words) <= n:
            continue
        prefix = " ".join(words[:n])
        if prefix.lower() in tried:
            continue
        tried.add(prefix.lower())
        target = await _resolve_once(tool_call, prefix, region)
        if target is not None:
            return target
    return None


def resolved_payload(target: ResearchTarget | None) -> dict[str, Any]:
    """The ``structured["resolved"]`` wire dict for a (possibly absent) target.

    A bound target carries its full resolver reply through (candidates and all,
    the shape the frontend's ``deriveAssetClass`` reads); ``None`` is an honest
    ``ok: False`` — never a fabricated instrument.
    """
    if target is None:
        return {"ok": False, "message": NO_INSTRUMENT_NOTE}
    if target.raw:
        return target.raw
    return {
        "ok": True,
        "resolved": {
            "symbol": target.symbol,
            "name": target.name,
            "exchange": target.exchange,
            "region": target.region,
            "asset_class": target.asset_class,
            "confidence": target.confidence,
        },
    }


__all__ = [
    "CONFIDENCE_FLOOR",
    "NO_INSTRUMENT_NOTE",
    "SYMBOL_SHAPE",
    "ResearchTarget",
    "resolve_target",
    "resolved_payload",
    "target_from_payload",
]
