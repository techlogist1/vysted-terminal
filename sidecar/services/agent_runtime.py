"""First-party agent runtime.

Discovers, validates, and invokes the first-party agents shipped under
``sidecar/agents/`` (BLUEPRINT §3.4 roster + AI Strategy Critic per the
Phase-3 plan's Tier-3 §3.4-vs-§4 resolution).

Discovery: every ``<id>.json`` file in the agents directory whose schema
validates against ``_schema.json`` becomes a registered agent at module
import time. A single malformed file disqualifies that one agent without
blocking the rest — the runtime emits a structured log line and continues.

Invocation: :func:`invoke_agent` resolves the agent, composes the LLM
messages list (system prompt + optional context preamble + user prompt),
selects a provider (override or agent default), and yields a stream of
:class:`LLMStreamEvent` Pydantic models. The router serialises them onto
SSE; the MCP server tool aggregates them into a unary string.

The runtime holds no API keys — they ride on the request body and are
passed straight through to the provider adapter. Sidecar never persists.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import jsonschema

import config
from models.agent import (
    AgentContextSnapshot,
    AgentSpec,
)
from models.llm import (
    LLMAgentPlanEvent,
    LLMDoneEvent,
    LLMErrorEvent,
    LLMMessage,
    LLMProviderId,
    LLMResearchStepEvent,
    LLMToolUseEvent,
    LLMUsage,
)
from services import agent_tools, model_registry
from services.agent_tools import catalog
from services.llm import get_provider, native_search, oneshot
from services.llm.base import LLMStreamEvent
from services.planner import classify_intent, decompose

#: Host-action steps a plan may PRE-STAGE into the diff/accept gate (the planner
#: vocabulary minus research/deep_research/answer, which execute inside the loop,
#: and with NO order verb — so a plan never touches the §6.5 path).
_STAGEABLE_PLAN_ACTIONS = frozenset(
    {"open_panel", "set_chart_symbol", "set_chart_indicators", "add_to_watchlist", "arrange_layout"}
)

#: Providers reliable enough at instruction-following for the visible planner. The
#: local ollama/qwen-7b path is unreliable (tool-use + JSON), so it stays on the
#: preamble-driven loop with NO plan surface (graceful degrade, not a worse run).
_PLANNER_PROVIDERS = frozenset({"anthropic", "openai", "gemini", "xai", "openrouter", "deepseek"})


def _planner_enabled(provider_id: str, mode: str) -> bool:
    """True when the visible plan-then-execute pre-pass should run for this turn."""
    return mode == "agent" and provider_id in _PLANNER_PROVIDERS


def _planner_context(snapshot: AgentContextSnapshot | None) -> dict[str, Any] | None:
    """Best-effort planner context — the focused symbol so "this"/"it" resolves.

    Reads the focused panel's context entry for a ``symbol``; returns ``None`` when
    none is found (the planner works fine without it). Never raises.
    """
    if snapshot is None:
        return None
    try:
        by_source = snapshot.by_source or {}
        candidates = [snapshot.focused_source, "chart", "equity-overview"]
        for src in candidates:
            entry = by_source.get(src) if src else None
            if isinstance(entry, dict):
                symbol = entry.get("symbol") or entry.get("ticker")
                if isinstance(symbol, str) and symbol:
                    return {"focusedSymbol": symbol}
    except Exception:  # noqa: BLE001 — context is a best-effort nicety
        return None
    return None


logger = logging.getLogger(__name__)

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
SCHEMA_PATH = AGENTS_DIR / "_schema.json"

#: Sentinel filenames in the agents directory that are NOT agent configs.
_RESERVED = {"_schema.json"}


def _load_schema() -> dict[str, Any]:
    """Read the AgentSpec JSON Schema; raise loudly if missing or malformed."""
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _discover_specs(agents_dir: Path = AGENTS_DIR) -> dict[str, AgentSpec]:
    """Enumerate the agents directory and return validated :class:`AgentSpec`s.

    Malformed files log a warning and are skipped — they MUST NOT block the
    rest of the roster from loading. Tests rely on partial-load resilience.
    """
    if not agents_dir.exists():
        return {}
    try:
        schema = _load_schema()
    except FileNotFoundError:
        logger.error("agent schema not found at %s; no agents will load", SCHEMA_PATH)
        return {}
    validator = jsonschema.Draft7Validator(schema)
    specs: dict[str, AgentSpec] = {}
    for path in sorted(agents_dir.glob("*.json")):
        if path.name in _RESERVED:
            continue
        try:
            with path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("agent %s: failed to read JSON (%s)", path.name, exc)
            continue
        errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
        if errors:
            for err in errors:
                logger.warning(
                    "agent %s: schema violation at %s: %s",
                    path.name,
                    list(err.path) or "<root>",
                    err.message,
                )
            continue
        try:
            spec = AgentSpec.model_validate(payload)
        except Exception as exc:  # pragma: no cover — schema covers this
            logger.warning("agent %s: pydantic validation failed (%s)", path.name, exc)
            continue
        if spec.id in specs:
            logger.warning("agent %s: duplicate id %r; keeping first", path.name, spec.id)
            continue
        specs[spec.id] = spec
    return specs


# Cached at module import — refreshes on a deliberate :func:`reload` call.
_specs: dict[str, AgentSpec] = _discover_specs()


def list_agents() -> list[AgentSpec]:
    """Return every registered first-party agent, ordered by id."""
    return [spec for _, spec in sorted(_specs.items())]


def get_agent(agent_id: str) -> AgentSpec | None:
    """Return one agent's spec, or ``None`` if unknown.

    Resolves first-party agents (the bundled JSON ``_specs``) first, then falls
    back to the SQLite custom-agent store — so user-authored agents (the Custom
    Agent Builder) AND marketplace-registered plugin agents (the agent slice of
    the unified extension model, FR-050) are invokable through the same loop.
    Read-only resolution; the agent's tools are catalog-validated and §6.5 stays
    host-enforced regardless of the spec's origin.
    """
    spec = _specs.get(agent_id)
    if spec is not None:
        return spec
    from services import agents_store

    custom = agents_store.get_agent(agent_id)
    if custom is None:
        return None
    return AgentSpec(
        id=custom.id,
        name=custom.name,
        philosophy=custom.philosophy,
        systemPrompt=custom.system_prompt,
        tools=list(custom.tools),
        defaultProvider=custom.default_provider,
        defaultModel=custom.default_model,
        icon=custom.icon,
    )


def reload(agents_dir: Path = AGENTS_DIR) -> None:
    """Refresh the agent registry from disk; primarily for tests."""
    global _specs
    _specs = _discover_specs(agents_dir)


# ---------------------------------------------------------------------------
# Invocation
# ---------------------------------------------------------------------------


def _render_terminal_preamble(ts: dict[str, Any]) -> str:
    """Render the structured ``TerminalState`` into a SHORT labelled preamble.

    Detail (every open chart, the full watchlist) is pulled on demand via the
    ``get_terminal_state`` tool — this stays terse so per-turn token cost is
    bounded. The deixis sentence is the highest-leverage line: it lets "is this
    cheap?" resolve to the focused chart ticker.
    """
    focused = ts.get("focusedSymbol")
    lines = ["## What the user is looking at"]
    charts = ts.get("charts") or []
    if charts:
        c = charts[0]
        ind = ", ".join(c.get("indicators") or []) or "no indicators"
        lines.append(f"Focused chart: {c.get('symbol')} ({c.get('timeframe')}, {ind}).")
    wl = ts.get("watchlist") or {}
    if wl.get("symbols"):
        lines.append("Watchlist: " + ", ".join(wl["symbols"][:12]) + ".")
    pf = ts.get("portfolio")
    if pf:
        lines.append(
            f"Portfolio: {pf.get('positionCount', 0)} positions, "
            f"total value {pf.get('totalValue', 0)}."
        )
    if ts.get("openPanels"):
        lines.append("Open panels: " + ", ".join(ts["openPanels"]) + ".")
    if focused:
        lines.append(
            f'When the user says "this" or "it", they mean {focused} '
            "unless they name another symbol. Never invent figures — call a tool to fetch them."
        )
    return "\n".join(lines)


def _build_context_preamble(snapshot: AgentContextSnapshot | None) -> str | None:
    """Render the focused panel + per-panel context into a system-prompt blob.

    Prefers the structured ``__terminal__`` snapshot (Phase 10) and renders a
    terse labelled preamble; falls back to the legacy per-source JSON dump for
    any other shape so older callers keep working.
    """
    if snapshot is None:
        return None
    by_source = snapshot.by_source or {}
    terminal = by_source.get("__terminal__")
    if isinstance(terminal, dict):
        return _render_terminal_preamble(terminal)
    if not by_source and snapshot.focused_source is None:
        return None
    sections = ["## Terminal context (read-only — describe accurately, do not invent fields)"]
    if snapshot.focused_source:
        sections.append(f"Focused panel: `{snapshot.focused_source}`")
    if by_source:
        sections.append("Per-panel state:")
        for source, payload in sorted(by_source.items()):
            sections.append(f"- `{source}`: {json.dumps(payload, default=str)}")
    return "\n".join(sections)


def _coerce_history(raw: Any) -> list[LLMMessage]:
    """Coerce ``options["history"]`` (a list of {role, content} dicts) into
    LLMMessages, dropping anything malformed. Bounded by the caller."""
    if not isinstance(raw, list):
        return []
    out: list[LLMMessage] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content:
            out.append(LLMMessage(role=role, content=content))
    return out[-10:]  # cap at ~10 turns to bound tokens


def _compose_messages(
    spec: AgentSpec,
    prompt: str,
    context: AgentContextSnapshot | None,
    history: list[LLMMessage] | None = None,
) -> list[LLMMessage]:
    """Build the system + context + history + user message list for the call."""
    messages: list[LLMMessage] = [LLMMessage(role="system", content=spec.system_prompt)]
    preamble = _build_context_preamble(context)
    if preamble:
        messages.append(LLMMessage(role="system", content=preamble))
    if history:
        messages.extend(history)
    messages.append(LLMMessage(role="user", content=prompt))
    return messages


def _resolve_provider_id(spec: AgentSpec, override: LLMProviderId | None) -> LLMProviderId:
    return override or spec.default_provider


def _resolve_model(spec: AgentSpec, override: str | None) -> str:
    if override:
        return override
    if spec.default_model:
        return spec.default_model
    # Per-provider default from the single-source registry
    # (config/model_registry.json). A last-resort fallback covers a provider
    # somehow absent from the registry so a model id is never empty.
    return model_registry.default_model_for(spec.default_provider) or "gpt-4.1-mini"


#: Hard cap on tool-call rounds in a single invocation. Strategy Critic
#: typically calls one to three tools (backtest_summary + optionally
#: price_data + fundamentals); a runaway agent that loops on the same
#: tool is bounded by this constant.
_MAX_TOOL_ROUNDS = 6
#: Per-run web-search cap (FR-081) — bounds per-search billing during a multi-round
#: research run, for BOTH the native tier (passed as the provider's max_uses) and
#: the BYOK/local `web_search` tool (counted in the loop; further calls return a
#: cap-reached message instead of dispatching).
_WEB_SEARCH_CAP = 5


LocalToolHandler = Any  # async (dict) -> dict, bound per-invocation


async def _dispatch_tool(
    event: LLMToolUseEvent,
    local_tools: dict[str, LocalToolHandler] | None = None,
) -> str:
    """Invoke a tool (per-invocation local handler first, else the global
    registry) and serialise the result to a string.

    Tool handlers return JSON-serialisable dicts; we encode them as a string so
    they ride the existing :class:`LLMMessage` ``content`` field. A handler that
    raises (or an unregistered tool) surfaces a structured error so the model
    recovers gracefully on the next turn rather than crashing the stream.
    """
    name = event.name
    try:
        if local_tools and name in local_tools:
            payload: dict[str, Any] = await local_tools[name](event.input)
        elif agent_tools.is_registered(name):
            payload = await agent_tools.invoke_tool(name, event.input)
        else:
            payload = {"ok": False, "error": f"tool {name!r} is not available in this build"}
    except Exception as exc:  # noqa: BLE001 — surface failures to the model
        payload = {"ok": False, "error": f"tool {name!r} raised: {exc}"}
    try:
        return json.dumps(payload, default=str)
    except (TypeError, ValueError):
        return str(payload)


class _ToolDone:
    """Terminal item from :func:`_dispatch_tool_with_progress` — the JSON result
    string of the completed tool. Distinguished from the live
    :class:`LLMResearchStepEvent`s that precede it (which are forwarded to the
    SSE consumer) so the caller can tell "a step to stream" from "the result"."""

    __slots__ = ("result",)

    def __init__(self, result: str) -> None:
        self.result = result


#: Pushed onto the step queue when the tool task finishes, so the drain loop
#: knows no more live steps are coming.
_STEP_SENTINEL = object()


def _step_event(tool_call: LLMToolUseEvent, step: Any, index: int) -> LLMResearchStepEvent:
    """Build a ``research_step`` SSE event from a tool's emitted step.

    ``step`` is duck-typed: a :class:`~services.research.models.ResearchStep`
    (attributes) or a plain dict — either is accepted so a future tool can emit
    progress without importing the research models.
    """
    if isinstance(step, dict):
        kind = step.get("kind", "tool")
        detail = step.get("detail", "")
        latency = step.get("latency_ms")
        status = step.get("status", "ok")
    else:
        kind = getattr(step, "kind", "tool")
        detail = getattr(step, "detail", "")
        latency = getattr(step, "latency_ms", None)
        status = getattr(step, "status", "ok")
    return LLMResearchStepEvent(
        tool_call_id=tool_call.tool_call_id,
        tool=tool_call.name,
        step_kind=str(kind),
        detail=str(detail),
        latency_ms=latency if isinstance(latency, int) else None,
        status=str(status),
        index=index,
    )


async def _dispatch_tool_with_progress(
    tool_call: LLMToolUseEvent,
    local_tools: dict[str, LocalToolHandler] | None = None,
) -> AsyncIterator[LLMResearchStepEvent | _ToolDone]:
    """Dispatch a tool, streaming any live research steps it emits, then yield a
    terminal :class:`_ToolDone` carrying the JSON result string (Track A).

    A long research tool (``deep_research`` / ``research``) pushes
    :class:`ResearchStep`s onto a queue via the per-dispatch step-sink
    (:func:`config.set_step_sink`, read inside the tool); this generator runs the
    tool as a task and drains the queue, yielding one ``research_step`` event per
    step WHILE the tool runs — turning an otherwise-silent multi-second tool round
    into a live "working" trace. An instant tool emits nothing and this simply
    yields ``_ToolDone`` immediately. The sink is reset on the way out so it never
    leaks into the next dispatch; ``_dispatch_tool`` never raises (it serialises
    failures), so the task result is always a string.
    """
    queue: asyncio.Queue[Any] = asyncio.Queue()
    token = config.set_step_sink(queue.put_nowait)

    async def _run() -> str:
        try:
            return await _dispatch_tool(tool_call, local_tools)
        finally:
            # The drain loop below blocks on the queue — always wake it, even on
            # an (unexpected) cancellation, so the generator can finalise.
            queue.put_nowait(_STEP_SENTINEL)

    task = asyncio.create_task(_run())
    index = 0
    try:
        while True:
            item = await queue.get()
            if item is _STEP_SENTINEL:
                break
            index += 1
            yield _step_event(tool_call, item, index)
        yield _ToolDone(await task)
    finally:
        config.reset_step_sink(token)


def _build_local_tools(
    snapshot: AgentContextSnapshot | None,
) -> dict[str, LocalToolHandler]:
    """Per-invocation tool handlers that need request scope or drive the host.

    ``get_terminal_state`` / ``get_portfolio`` return state passed in the request
    (the sidecar can't read the frontend's stores). The host-action tools return
    a synthetic result carrying a ``host_action`` directive — but the action is
    STAGED for the user's review (the diff/accept trust gate, FR-010), NOT applied
    immediately. So every host action reports ``awaiting_user_review`` (not
    ``applied``): the model must tell the user it *proposed* the change for review,
    never that it already happened. ``propose_order`` is the same shape (§6.5 — the
    AI has no path to ``confirm_and_place``). The frontend stages the directive in
    the proposed-changes queue and applies it only on the user's accept.
    """
    from services.agent_tools.schemas import HOST_ACTION_TOOLS

    terminal: dict[str, Any] | None = None
    if snapshot is not None and isinstance(snapshot.by_source, dict):
        candidate = snapshot.by_source.get("__terminal__")
        if isinstance(candidate, dict):
            terminal = candidate

    async def _terminal_state(_args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "state": terminal or {}}

    async def _portfolio(_args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "portfolio": (terminal or {}).get("portfolio")}

    local: dict[str, LocalToolHandler] = {
        "get_terminal_state": _terminal_state,
        "get_portfolio": _portfolio,
    }

    def _make_host_action(tool_id: str) -> LocalToolHandler:
        async def _handler(args: dict[str, Any]) -> dict[str, Any]:
            if tool_id == "propose_order":
                return {
                    "ok": True,
                    "proposal_created": True,
                    "status": "awaiting_user_review",
                    "host_action": {"type": tool_id, "args": args},
                }
            return {
                "ok": True,
                "status": "awaiting_user_review",
                "staged_for_review": True,
                "note": "Staged in the user's review queue — applies ONLY after they accept it. "
                "Tell the user you proposed this change for review; do not claim it is done.",
                "host_action": {"type": tool_id, "args": args},
            }

        return _handler

    for tid in HOST_ACTION_TOOLS:
        local[tid] = _make_host_action(tid)
    return local


async def invoke_agent(
    agent_id: str,
    prompt: str,
    context_snapshot: AgentContextSnapshot | None = None,
    api_key: str | None = None,
    provider: LLMProviderId | None = None,
    model: str | None = None,
    options: dict[str, Any] | None = None,
    mode: str = "ask",
    on_round_usage: Callable[[LLMUsage, str], None] | None = None,
) -> AsyncIterator[LLMStreamEvent]:
    """Invoke a registered agent and stream its response.

    The runtime dispatches :class:`LLMToolUseEvent`s mid-stream: when a
    provider emits a tool_use block, the event is yielded to the caller
    (so the UI can show "using tool X…"), the corresponding handler in
    :mod:`services.agent_tools` is invoked, the result is pushed back
    into the conversation as a ``role="tool"`` message keyed on the
    ``tool_call_id``, and the provider is re-called for a continuation.
    The loop is capped at :data:`_MAX_TOOL_ROUNDS` to bound a runaway
    tool-spam agent.

    Unknown agent ids surface as a single :class:`LLMErrorEvent` followed
    by a terminal :class:`LLMDoneEvent` so the SSE response always
    closes cleanly — clients only need one terminator.

    ``on_round_usage`` is an optional per-round cost signal (P3 / FR-026): the
    loop normally SWALLOWS each mid-run round's ``done`` usage while it loops on
    tools, so a budget guard could otherwise only see the FINAL usage. When set,
    it is called with ``(usage, model)`` at EVERY round's ``done`` (the swallowed
    mid-run terminators AND the final one), so a detached Delegate-run executor
    can enforce token/spend ceilings MID-run. It does not change the event stream
    — the SSE consumer sees the same frames whether or not the callback is set.
    """
    spec = get_agent(agent_id)
    if spec is None:
        yield LLMErrorEvent(message=f"unknown agent: {agent_id!r}")
        yield LLMDoneEvent()
        return
    provider_id = _resolve_provider_id(spec, provider)
    resolved_model = _resolve_model(spec, model)
    opts = dict(options or {})
    history = _coerce_history(opts.pop("history", None))
    tool_ids = list(spec.tools)  # the allow-list — finally sent to the provider
    # Resolve whether this turn is READ-ONLY. The collapsed "agent" mode (Track B)
    # has no Ask/Edit/Build picker — it INFERS the intent from the prompt
    # (deterministic, no LLM) and gates a READ intent to read-only tools exactly as
    # the old "Ask" mode did, so the §6.5-adjacent read-only line survives the
    # mode-collapse. Legacy "ask" stays read-only for back-compat; everything else
    # (agent-with-edit/build intent, delegate, legacy edit/build) keeps the full set.
    inferred_intent: str | None = None
    if mode == "agent":
        inferred_intent = classify_intent(prompt).intent
        read_only = inferred_intent == "read"
    else:
        read_only = mode == "ask"
    if read_only:
        # Strip every mutating capability SERVER-SIDE so a read turn can never drive
        # the host or propose an order — drops the host-action mutators (open_panel,
        # set_chart_symbol, add_to_watchlist) + propose_order (all read_only=False),
        # keeping read tools + the per-invocation get_terminal_state/get_portfolio.
        # Enforced here, not in the adapter, so an external MCP client can't bypass it.
        tool_ids = [t for t in tool_ids if catalog.is_read_only(t) is True]

    # Web-search tier dispatch (FR-080/081). On the NATIVE tier with a
    # native-capable provider, ride the model's own server-side search (the
    # adapter injects it via the `web_search` kwarg, capped at _WEB_SEARCH_CAP)
    # and WITHHOLD the BYOK/local `web_search` tool so search isn't double-run.
    # Otherwise (BYOK/local tier, or a native-incapable provider) keep the
    # `web_search` tool — it routes to Exa/SearXNG, or returns an honest
    # "unavailable" when nothing is configured (FR-082; never fabricates).
    search_tier = config.get_search_tier()
    if (
        search_tier == config.SEARCH_TIER_NATIVE
        and provider_id in native_search.SUPPORTS_NATIVE_SEARCH
    ):
        opts["web_search"] = True
        opts["web_search_max_uses"] = _WEB_SEARCH_CAP
        tool_ids = [t for t in tool_ids if t != "web_search"]

    local_tools = _build_local_tools(context_snapshot)
    messages = _compose_messages(spec, prompt, context_snapshot, history)
    adapter = get_provider(provider_id)

    # Publish the active LLM creds for the run so an in-loop research tool
    # (deep_research) can call the SAME model the user is talking to. Task-local
    # (each request is its own asyncio task with a copied context), so it does
    # not leak across requests; the key stays process-memory-only.
    config.set_request_llm_creds(provider_id, resolved_model, api_key)

    # --- Visible plan-then-execute pre-pass (Track 6 #2) ---------------------
    # For a COMPOUND request on a capable model, decompose the goal into an
    # ordered plan, surface it (so the user sees the steps up front), and PRE-STAGE
    # the host-action steps into the diff/accept gate. ADVISORY only: the tool loop
    # below still drives execution; this never blocks, never raises, and on a weak
    # local model it is skipped entirely (the loop's preamble-driven path stands).
    if not read_only and _planner_enabled(provider_id, mode) and classify_intent(prompt).compound:
        try:

            async def _plan_llm_call(p: str) -> str:
                return await oneshot.complete(
                    provider_id, resolved_model, api_key, [{"role": "user", "content": p}]
                )

            plan = await decompose(
                prompt,
                llm_call=_plan_llm_call,
                context=_planner_context(context_snapshot),
            )
            if plan.ok and len(plan.steps) > 1:
                steps = [
                    {**step.to_dict(), "staged": step.action in _STAGEABLE_PLAN_ACTIONS}
                    for step in plan.steps
                ]
                yield LLMAgentPlanEvent(goal=plan.goal, steps=steps, note=plan.note)
        except Exception:  # noqa: BLE001 — the plan is best-effort; never break a turn
            logger.debug("planner pre-pass skipped (non-fatal)", exc_info=True)

    rounds = 0
    web_search_calls = 0  # per-run cap on the BYOK/local web_search tool (FR-081)
    while True:
        pending_tools: list[LLMToolUseEvent] = []
        seen_done = False
        async for event in adapter.stream_chat(
            messages=messages,
            model=resolved_model,
            api_key=api_key,
            tool_ids=tool_ids,
            **opts,
        ):
            if isinstance(event, LLMToolUseEvent):
                pending_tools.append(event)
                yield event
                continue
            if isinstance(event, LLMDoneEvent):
                seen_done = True
                # Per-round cost signal (FR-026): fire BEFORE we either swallow
                # this terminator (mid-run) or yield it (final), so the budget
                # guard sees every round's usage, not just the last one.
                if on_round_usage is not None:
                    on_round_usage(event.usage or LLMUsage(), resolved_model)
                # If tools fired this round and we have budget left,
                # swallow the per-round terminator and loop. Otherwise
                # this is the final terminator and the SSE consumer
                # needs it.
                if pending_tools and rounds < _MAX_TOOL_ROUNDS:
                    break
                yield event
                return
            yield event
        if not seen_done:
            # Provider closed without a terminator — emit one so the SSE
            # framing stays well-formed for the consumer.
            yield LLMDoneEvent()
            return
        if not pending_tools:
            return

        # Reconstruct the assistant tool-use turn FIRST so the provider can
        # associate each tool result with its call: Anthropic requires the
        # tool_use block to precede the tool_result; OpenAI requires the
        # assistant `tool_calls` array. Carried in `metadata` (no contract
        # change to LLMMessage); each adapter rebuilds its native shape.
        messages.append(
            LLMMessage(
                role="assistant",
                content="",
                metadata={
                    "tool_calls": [
                        {"id": tc.tool_call_id, "name": tc.name, "input": tc.input}
                        for tc in pending_tools
                    ]
                },
            )
        )
        # Dispatch every pending tool, append tool-result messages keyed
        # on the call ids, and re-enter the loop.
        for tool_call in pending_tools:
            if tool_call.name == "web_search":
                # FR-081: bound per-search billing per run.
                web_search_calls += 1
            if tool_call.name == "web_search" and web_search_calls > _WEB_SEARCH_CAP:
                # Past the cap, return a synthesize-now signal instead of
                # dispatching another search.
                result_str = json.dumps(
                    {
                        "ok": False,
                        "message": (
                            f"web-search cap reached ({_WEB_SEARCH_CAP} searches this "
                            "run) — answer from the sources you already gathered."
                        ),
                    }
                )
            else:
                # Stream any live research steps the tool emits WHILE it runs
                # (Track A — a long deep_research round is no longer silent), then
                # take the JSON result string from the terminal _ToolDone.
                result_str = ""
                async for item in _dispatch_tool_with_progress(tool_call, local_tools):
                    if isinstance(item, _ToolDone):
                        result_str = item.result
                    else:
                        yield item
            messages.append(
                LLMMessage(
                    role="tool",
                    content=result_str,
                    tool_call_id=tool_call.tool_call_id,
                    # Carry the tool NAME alongside the id: Gemini pairs a
                    # function_response to its call by name (not id), so a
                    # tool-result message with no name serialises name="" and
                    # breaks Gemini multi-round tool use. Anthropic/OpenAI key by
                    # tool_call_id and ignore this. (FR-024 / closes the §4 break.)
                    metadata={"name": tool_call.name},
                )
            )
        rounds += 1
        if rounds >= _MAX_TOOL_ROUNDS:
            # Hit the cap — let the next provider stream finalise. The
            # subsequent loop iteration sees no pending tools and exits
            # via the ``not pending_tools`` branch above.
            continue
