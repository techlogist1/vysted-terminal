"""ResearchTarget — the ONE instrument binding for a research run (R8/R10).

Root cause of the R8 symbol-truth defects: every research layer re-resolved its
own symbol from whatever text it was handed, so a heavy explorer re-resolved the
FOCUS-AUGMENTED task string ("Saksoft Limited — focus: Analyze revenue growth…")
and either published the whole sentence as ``brief.symbol`` or fuzzy-bound a
WRONG instrument (a Reliance run bound CMTL). This module is the fix:

  - :func:`resolve_target` calls ``resolve_symbol`` exactly ONCE per attempt,
    on the CLEAN user query, and binds the result to a frozen
    :class:`ResearchTarget` — or surfaces an explicit
    :class:`ResearchDisambiguation`, or ``None`` when nothing trustworthy
    matched.
  - R10 (E1): the acceptance verdict comes from the resolver tool's ``status``
    (the ONE policy in :mod:`services.resolution_policy`) — there is no second
    confidence floor here. A resolution the policy did not bind NEVER binds.
  - A **symbol-shape gate** (:data:`SYMBOL_SHAPE`): whatever the resolver
    returns must LOOK like a ticker after uppercasing — a sentence can never
    become a "symbol" again.

Every research loop threads the SAME bound target down (heavy explorers receive
it and never re-resolve); all structured tool calls use ``target.symbol``. When
the target is ``None`` the run proceeds web-only with the honest
:data:`NO_INSTRUMENT_NOTE` — zero ``vysted://`` calls with a non-symbol, and
``brief.symbol = ""``. A :class:`ResearchDisambiguation` makes the loop return
an honest "which did you mean?" payload INSTEAD of researching a guess — no
markdown, no structured pulls, no web spend.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

#: Injected tool dispatcher — ``await tool_call(name, args) -> dict`` (the same
#: seam the loops use; redefined locally to avoid a circular import with deep).
ToolCall = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

#: A bound symbol must look like a ticker after uppercasing. This gate is what
#: makes "Saksoft Limited — focus: Analyze revenue growth…" structurally unable
#: to ever become a symbol again.
SYMBOL_SHAPE = re.compile(r"^[A-Z0-9][A-Z0-9.\-&]{0,19}$")

#: The honest one-line statement a web-only (no-target) brief carries.
NO_INSTRUMENT_NOTE = "No listed instrument matched this query — web evidence only."

#: A 1-word prefix may bind only at the first-word band or above (0.97 —
#: first-word / marquee primary / exact ticker). Weaker one-word evidence
#: (prefix 0.92, substring 0.8) is rejected so a stray leading word can never
#: bind a run to an unrelated company.
_ONE_WORD_PREFIX_MIN_CONFIDENCE = 0.97


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
    #: R13 additive identity enrichment mirrored from the resolver reply — the
    #: anchors the web-query builder + relevance gate use to disambiguate a
    #: ≤3-char ticker (KSE) shadowed by a famous foreign entity. ``None`` when
    #: the bundled data does not carry it (never fabricated).
    isin: str | None = None
    bse_code: str | None = None
    industry: str | None = None
    former_name: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    def is_equity_like(self) -> bool:
        """True unless the instrument is explicitly a crypto/fx asset — drives
        the equity-targeted junk filters (crypto hosts are noise for an equity)."""
        kind = (self.asset_class or "").strip().lower()
        return kind not in ("crypto", "cryptocurrency", "fx", "currency", "forex")


@dataclass(frozen=True, slots=True)
class ResearchDisambiguation:
    """An explicit "which did you mean?" — surfaced INSTEAD of a guessed run.

    ``candidates`` are wire dicts (``symbol`` / ``name`` / ``exchange`` /
    ``score`` / ``yahoo_symbol``) ready for the brief contract's chooser
    (``BriefDisambiguation``, ``types/brief.ts``). ``curated`` marks a marquee
    family (the resolver's hand-curated lists) — preferred over an incidental
    fuzzy disambiguation when both arise while prefix-scanning one query.
    """

    query: str
    candidates: list[dict[str, Any]]
    message: str = ""
    curated: bool = False

    def payload(self, query: str | None = None) -> dict[str, Any]:
        """The dict every research loop returns for a disambiguation — no
        markdown, no structured, no web spend (R10 D37)."""
        return {
            "ok": True,
            "needs_disambiguation": True,
            "query": query if query is not None else self.query,
            "candidates": [dict(c) for c in self.candidates],
            "message": self.message or self._default_message(),
        }

    def _default_message(self) -> str:
        listed = ", ".join(
            f"{c.get('symbol')} ({c.get('name')})" for c in self.candidates[:6] if c.get("symbol")
        )
        return (
            f"{self.query!r} matches more than one listed instrument — which did you mean? {listed}"
        )


def _wire_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Project the resolver reply's candidates to the brief-contract shape."""
    out: list[dict[str, Any]] = []
    for c in payload.get("candidates") or []:
        if not isinstance(c, dict):
            continue
        symbol = str(c.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        score = c.get("confidence") if c.get("confidence") is not None else c.get("score")
        out.append(
            {
                "symbol": symbol,
                "name": str(c.get("name") or symbol),
                "exchange": c.get("exchange"),
                "score": score,
                "yahoo_symbol": c.get("yahoo_symbol"),
            }
        )
    return out


def target_from_payload(
    payload: dict[str, Any], *, region: str | None = None
) -> ResearchTarget | ResearchDisambiguation | None:
    """Map a ``resolve_symbol`` wire reply to the run's resolution outcome.

    Consumes the policy's verdict (``status``): ``"bound"`` builds a target
    (still shape-gated), ``"disambiguate"`` builds the explicit chooser,
    anything else is ``None``. A legacy payload without ``status`` binds only
    at or above the policy's ACCEPT — never the old 0.5 floor.
    """
    if not isinstance(payload, dict):
        return None
    status = payload.get("status")
    if status == "disambiguate":
        return ResearchDisambiguation(
            query=str(payload.get("query") or ""),
            candidates=_wire_candidates(payload),
            message=str(payload.get("message") or ""),
            curated="marquee" in str(payload.get("reason") or "").lower(),
        )
    if status not in (None, "bound"):
        return None
    if not payload.get("ok"):
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
    if status is None:
        # Legacy reply with no policy verdict: only a decisive score binds.
        from services.resolution_policy import ACCEPT

        if confidence < ACCEPT:
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
        isin=_opt_str(instrument.get("isin")),
        bse_code=_opt_str(instrument.get("bse_code")),
        industry=_opt_str(instrument.get("industry")),
        former_name=_opt_str(instrument.get("former_name")),
        raw=payload,
    )


def _opt_str(value: Any) -> str | None:
    """A non-empty string, or ``None`` — the additive enrichment fields never
    carry a fabricated value, so a blank/absent/non-string reads as ``None``."""
    return str(value) if isinstance(value, str) and value.strip() else None


async def _resolve_once(
    tool_call: ToolCall, query: str, region: str | None
) -> ResearchTarget | ResearchDisambiguation | None:
    """One resolver call → gated outcome, or ``None``. Never raises."""
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


#: Prefix lengths (in words) tried when the full query does not bind. Models
#: routinely pass keyword-salad queries ("Route Mobile Q4 FY26 quarterly results
#: revenue profit dividend…") where the COMPANY leads the string. Longest first
#: so "Route Mobile" wins over a one-word "Route" mis-bind; the 1-word rung
#: (R10) lets "RELIANCE.NS <anything>" and "Reliance Q4 results" reach the bare
#: ticker / marquee stage, gated at :data:`_ONE_WORD_PREFIX_MIN_CONFIDENCE`.
_PREFIX_WORDS = (4, 3, 2, 1)


async def resolve_target(
    tool_call: ToolCall, query: str, region: str | None = None
) -> ResearchTarget | ResearchDisambiguation | None:
    """Resolve the CLEAN user ``query`` — the run's ONE resolution.

    Tries the full query first; when that does not bind (keyword-salad queries
    where only the leading words name the company), falls back to leading-word
    prefixes (4 → 3 → 2 → 1 words), accepting the first decisive bind. A
    curated (marquee) disambiguation returns immediately — nothing weaker can
    outrank a hand-curated family chooser; an incidental fuzzy disambiguation
    is remembered and returned only when no prefix binds. Never raises;
    ``None`` means web-only. Downstream layers must never re-resolve derived
    prompt text.
    """
    text = (query or "").strip()
    if not text:
        return None
    words = text.split()
    attempts = [text]
    tried = {text.lower()}
    for n in _PREFIX_WORDS:
        if len(words) <= n:
            continue
        prefix = " ".join(words[:n])
        if prefix.lower() in tried:
            continue
        tried.add(prefix.lower())
        attempts.append(prefix)

    first_disambiguation: ResearchDisambiguation | None = None
    for i, attempt in enumerate(attempts):
        outcome = await _resolve_once(tool_call, attempt, region)
        if isinstance(outcome, ResearchTarget):
            one_word_prefix = i > 0 and len(attempt.split()) == 1
            if one_word_prefix and outcome.confidence < _ONE_WORD_PREFIX_MIN_CONFIDENCE:
                continue
            return outcome
        if isinstance(outcome, ResearchDisambiguation):
            if outcome.curated:
                return outcome
            if first_disambiguation is None:
                first_disambiguation = outcome
    return first_disambiguation


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
            "isin": target.isin,
            "bse_code": target.bse_code,
            "industry": target.industry,
            "former_name": target.former_name,
        },
    }


__all__ = [
    "NO_INSTRUMENT_NOTE",
    "SYMBOL_SHAPE",
    "ResearchDisambiguation",
    "ResearchTarget",
    "resolve_target",
    "resolved_payload",
    "target_from_payload",
]
