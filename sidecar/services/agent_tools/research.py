"""Agent tool — ``research`` (the ONE research capability, depth-escalating).

After the R4 research collapse (FR-115 / SC-028) this is the SINGLE user-facing +
model-facing research capability. Depth is an INTERNAL escalation arg, not a user
knob, and "go deeper" escalates the SAME run in place. R7 names the depths
``normal`` | ``deep`` | ``ultra`` (the depth router in
:mod:`services.research.depth` is the ONE source of truth; legacy
``quick``/``heavy`` spellings map onto them forever):

- ``depth="normal"`` (default; legacy ``quick``) → the fast, single-pass gather
  (:func:`services.research.fast.gather_fast`): resolve the symbol + fan out to the
  read-only data tools (news, quotes, fundamentals, filings) plus one web round and
  return one grounded bundle the model summarises. No inner LLM loop.
- ``depth="deep"`` → the IterResearch evolving-report loop (the ONE deep loop),
  ~3 rounds × 3 researchers with the finance ``site:`` bias.
- ``depth="ultra"`` (legacy ``heavy``) → the expert panel of parallel research
  angles with stricter coverage (>=2 independent web domains) plus the numeric
  cross-check verification round.

Depth is per-query and ORTHOGONAL to the research tier (R9: ``tier_a`` /
``tier_b`` ride the request ContextVars; see :mod:`config`). The tier routes at
THIS tool boundary: ``tier_b`` sends EVERY depth stop to the hosted
research-model lane (:func:`services.agent_tools.deep_research.
run_research_model_brief` — per-stop model dispatch via OpenRouter, the user's
setting outranking any model-passed backend arg); ``tier_a`` serves
``deep``/``ultra`` via :func:`services.agent_tools.deep_research.run_deep_brief`
(the internal DEEP engine — no longer a separate tool). The optional
``backend`` (``native`` | ``perplexity`` | ``sonar``) is internal too; the paid
lanes are opt-in-per-run and NEVER auto-selected.

The research/deep-research service is imported lazily inside the call so the module
imports cleanly even before the service lands, and so the test suite can monkeypatch
the service in place.
"""

from __future__ import annotations

import copy
import json
import time
import uuid
from typing import Any

from services.agent_tools import register_tool

#: ``ResearchExecution.loop`` derivation from a LEGACY payload ``mode`` —
#: used only when an engine return carries no ``execution_loop`` key (Team
#: RESOLVE stamps it on every new engine return; this covers an older payload
#: shape so the record is never absent).
_LEGACY_MODE_TO_LOOP = {"fast": "fast", "deep": "iter", "heavy": "heavy"}

_LEGACY_PAYLOAD_REASON = "legacy engine payload"


def _emit_begin_step(run_id: str, depth: str, query: str) -> None:
    """ONE synthetic begin step through the live step sink (R10, D38).

    The frontend keys its in-flight brief state on this exact detail format
    (contract with Team FRONTEND-BRIEF) — change it only in lockstep:
    ``research:begin {run_id} depth={depth} query={query}``. No-ops outside an
    agent run (no sink wired) and never raises.
    """
    import config

    sink = config.get_step_sink()
    if sink is None:
        return
    from services.research.models import ResearchStep

    try:
        sink(
            ResearchStep(
                kind="engine", detail=f"research:begin {run_id} depth={depth} query={query}"
            )
        )
    except Exception:  # pragma: no cover — cosmetic; must never break a run
        pass


def _derive_loop(payload: dict[str, Any]) -> tuple[str, str | None]:
    """Resolve the loop that RAN from the payload; ``(loop, degraded_reason)``.

    Prefers the engine-stamped ``execution_loop`` (Team RESOLVE's contract:
    every engine return carries one of fast/iter/heavy/research-model). A
    payload without it is legacy — the loop derives from the old ``mode``
    field (and the research-model backend prefix) with an explicit
    ``degraded_reason`` so the inference is never silent.
    """
    from services.research.models import EXECUTION_LOOPS

    loop = payload.get("execution_loop")
    if isinstance(loop, str) and loop in EXECUTION_LOOPS:
        return loop, None
    backend = payload.get("backend")
    if isinstance(backend, str) and backend.startswith("research-model:"):
        return "research-model", _LEGACY_PAYLOAD_REASON
    mode = str(payload.get("mode") or "fast").strip().lower()
    return _LEGACY_MODE_TO_LOOP.get(mode, "fast"), _LEGACY_PAYLOAD_REASON


def _stamp_execution(payload: Any, *, run_id: str, requested_depth: str, started_at: float) -> Any:
    """Attach the :class:`ResearchExecution` record to an engine return (E2).

    Stamped from the loop that ACTUALLY RAN, never the request. Degradation
    rule: requested deep/ultra served by the fast loop MUST carry a stated
    reason (the payload's note/web reason when present) — degradation is never
    silent. Non-dict returns pass through untouched (defensive).
    """
    if not isinstance(payload, dict):
        return payload
    from services.research import depth as depth_mod
    from services.research.models import ResearchExecution

    loop, degraded_reason = _derive_loop(payload)
    if requested_depth in (depth_mod.DEPTH_DEEP, depth_mod.DEPTH_ULTRA) and loop == "fast":
        note = payload.get("note")
        web = payload.get("web") if isinstance(payload.get("web"), dict) else None
        web_reason = web.get("reason") if web else None
        stated = note or web_reason or payload.get("message")
        degraded_reason = (
            f"requested {requested_depth} but the fast loop ran — {stated}"
            if stated
            else f"requested {requested_depth} but the fast loop ran (no reason reported)"
        )
    record = ResearchExecution(
        run_id=run_id,
        requested_depth=requested_depth,
        loop=loop,
        backend=payload.get("backend"),
        started_at=started_at,
        finished_at=time.time(),
        degraded_reason=degraded_reason,
    )
    payload["execution"] = record.to_dict()
    return payload


async def _research(args: dict[str, Any]) -> dict[str, Any]:
    """Run research for ``query`` at the requested internal ``depth``.

    ``depth="normal"`` (default) gathers a grounded bundle in one pass;
    ``"deep"``/``"ultra"`` run the budgeted deep loop at the profile's knobs.
    On a missing/blank query returns ``{"ok": False, "message": <human reason>}``
    — never a raw error blob. Every dict return carries the R10
    ``execution`` record (run_id + requested depth + the loop that RAN) —
    the brief's mode/depth badges derive from it and only it (E2).
    """
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {
            "ok": False,
            "message": "Research needs a query — tell me what to look into.",
        }
    query = query.strip()

    import config as app_config
    from services.research import depth as depth_mod

    # The composer slider (request default) is the user's explicit FLOOR; the
    # model may ESCALATE above it (the deterministic "go deeper" path) but never
    # silently demote it. So take the MAX tier of (model arg, slider) — this
    # fixes the slider being overridden by the model filling the schema's
    # default depth arg (R7 seam: `args or ctxvar` let "normal" beat "deep").
    _RANK = {depth_mod.DEPTH_NORMAL: 0, depth_mod.DEPTH_DEEP: 1, depth_mod.DEPTH_ULTRA: 2}
    _model_depth = depth_mod.normalize_depth(args.get("depth"))
    _slider_depth = depth_mod.normalize_depth(app_config.get_request_research_depth())
    depth = _model_depth if _RANK[_model_depth] >= _RANK[_slider_depth] else _slider_depth

    # R10 (E2): mint the run id at the tool boundary and announce the run so
    # the frontend can key its in-flight brief state before any engine work.
    run_id = uuid.uuid4().hex
    started_at = time.time()
    _emit_begin_step(run_id, depth, query)

    # R9 (Track A) tier routing at the tool boundary: on tier_b the hosted
    # research model OWNS research at ALL depth stops regardless of the chat
    # model — including NORMAL (one search-grounded call) — and regardless of
    # any model-passed ``backend`` arg (the user's tier setting outranks the
    # model's tool-arg whims; the depth FLOOR above still applies). tier_a
    # keeps the built-in lanes below. Without a key the lane stops honestly
    # naming the unlock — never a silent demotion (the key boundary, D25).
    if app_config.get_effective_research_tier() == app_config.SEARCH_TIER_B:
        from services.agent_tools.deep_research import run_research_model_brief

        # NOTE: no model passthrough from the LLM's tool args — the user's
        # per-stop Settings map is authoritative (never a surprise model on the
        # user's key); only the explicit api_key arg (internal callers) rides.
        out = await run_research_model_brief(query, depth=depth, api_key=args.get("api_key"))
        return _stamp_execution(out, run_id=run_id, requested_depth=depth, started_at=started_at)

    if depth in (depth_mod.DEPTH_DEEP, depth_mod.DEPTH_ULTRA):
        from services.agent_tools.deep_research import run_deep_brief

        out = await run_deep_brief(
            query,
            depth=depth,
            # ``None`` lets the depth profile supply the default (deep: 3 rounds
            # / 120s; ultra: 4 rounds / 240s); an explicit arg still wins.
            rounds=args.get("rounds"),
            wall_seconds=args.get("wall_seconds"),
            backend=args.get("backend"),
            api_key=args.get("api_key"),
        )
        return _stamp_execution(out, run_id=run_id, requested_depth=depth, started_at=started_at)

    import config
    from services import agent_tools
    from services.research import fast

    out = await fast.gather_fast(
        query,
        region=config.get_region(),
        tool_call=agent_tools.invoke_tool,
        # Forward steps LIVE to the runtime sink (Track A) so even the default
        # normal mode animates a working trace; ``None`` outside an agent run.
        on_step=config.get_step_sink(),
    )
    if isinstance(out, dict):
        out.setdefault("depth", depth_mod.DEPTH_NORMAL)
    return _stamp_execution(out, run_id=run_id, requested_depth=depth, started_at=started_at)


#: Statement-denominated money sizes (the ``Fundamentals`` contract in
#: ``models/fundamentals.py`` plus the semantics statement facts): rendered in
#: ``financial_currency`` when the reporter's statements differ from the
#: trading currency. Every other money field's unit comes from the semantics
#: ``derived`` leg (``unit == "currency"``) of the bundle itself.
_STATEMENT_MONEY_FIELDS = frozenset(
    {
        "revenue_ttm",
        "net_income_ttm",
        "free_cash_flow",
        "reported_net_income",
        "normalized_net_income",
    }
)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def model_view(payload: Any) -> Any:
    """The MODEL-facing projection of a research result (R15-AGENT-001).

    The raw bundle rides next to its displays, and a small model reads the raw
    rupee float (``market_cap = 2895037857792.0``) and mis-scales it 10x. This
    copy replaces every money scalar in ``structured`` with its
    :func:`semantics.display_value` string, so the model can only quote the
    scaled figure. Money fields are the semantics ``derived`` values whose
    ``unit`` is ``currency`` (by key, wherever they recur in the bundle, and in
    the ``sources`` of a conflict on that field) plus the statement sizes.
    Non-money numbers are kept. The panel and auto-publish keep the raw payload.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("structured"), dict):
        return payload
    from services.research.semantics import display_value

    view = copy.deepcopy(payload)
    structured = view["structured"]
    fund_leg = structured.get("fundamentals")
    fund = fund_leg.get("data") if isinstance(fund_leg, dict) else None
    fund = fund if isinstance(fund, dict) else {}
    currency = fund.get("currency") if isinstance(fund.get("currency"), str) else None
    statement_currency = fund.get("financial_currency") or currency
    derived_leg = structured.get("derived")
    derived = derived_leg.get("data") if isinstance(derived_leg, dict) else None
    derived = derived if isinstance(derived, dict) else {}
    money = set(_STATEMENT_MONEY_FIELDS)
    money.update(
        key
        for key, item in derived.items()
        if isinstance(item, dict) and item.get("unit") == "currency"
    )

    def show(field: str | None, value: float) -> str:
        code = statement_currency if field in _STATEMENT_MONEY_FIELDS else currency
        return display_value(value, "currency", code)

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        if node.get("unit") == "currency" and _is_number(node.get("value")):
            node["value"] = node.get("display") or show(None, node["value"])
        conflict_field = node.get("field") if node.get("field") in money else None
        for key, value in node.items():
            if key in money and _is_number(value):
                node[key] = show(key, value)
            elif conflict_field and key == "sources" and isinstance(value, list):
                for source in value:
                    if isinstance(source, dict) and _is_number(source.get("value")):
                        source["value"] = show(conflict_field, source["value"])
            else:
                walk(value)

    walk(structured)
    return view


def model_content(result_str: str) -> str:
    """:func:`model_view` over a serialised research result (the tool message)."""
    try:
        payload = json.loads(result_str)
    except (json.JSONDecodeError, ValueError, TypeError):
        return result_str
    view = model_view(payload)
    if view is payload:
        return result_str
    # ensure_ascii=False: the model reads "₹289,504 cr", not "₹289,504 cr".
    return json.dumps(view, default=str, ensure_ascii=False)


def register() -> None:
    """Register the ``research`` tool in the package registry."""
    register_tool("research", _research)


__all__ = ["_research", "model_content", "model_view", "register"]
