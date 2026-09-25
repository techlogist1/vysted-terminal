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
import contextlib
import json
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
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
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMErrorEvent,
    LLMHeartbeatEvent,
    LLMMessage,
    LLMProviderId,
    LLMResearchStepEvent,
    LLMThinkingEvent,
    LLMToolResultEvent,
    LLMToolUseEvent,
    LLMUsage,
)
from services import action_ledger, agent_tools, budget_guard, model_registry
from services.agent_tools import catalog
from services.agent_tools.schemas import openai_tools
from services.llm import get_provider, native_search, oneshot, scrub_adapter_options
from services.llm.base import (
    IDLE_TIMEOUT_S,
    LOCAL_IDLE_TIMEOUT_S,
    LLMStreamEvent,
    is_length_finish,
)
from services.llm.openai import INVALID_ARGS_SENTINEL
from services.planner import classify_intent, decompose
from services.search.scrub import wrap_untrusted

#: Host-action steps a plan may PRE-STAGE into the diff/accept gate (the planner
#: vocabulary minus research/answer, which execute inside the loop).
_STAGEABLE_PLAN_ACTIONS = frozenset(
    {
        "open_panel",
        "set_chart_symbol",
        "set_chart_indicators",
        "add_to_watchlist",
        "arrange_layout",
        "open_company_overview",
    }
)

#: Read-safe panel host-actions RETAINED on a READ intent (locked Decision 4): a
#: read question may still ground itself by pulling up the relevant chart / index /
#: layout. No ``data-write`` action (portfolio, notes, screens, saved layouts) is
#: in this set, so a read turn can never edit the user's tracked portfolio.
_READ_SAFE_PANEL_ACTIONS = frozenset(
    {
        "open_panel",
        "set_chart_symbol",
        "set_chart_indicators",
        "arrange_layout",
        "add_to_watchlist",
        "open_company_overview",
    }
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


#: Shared terminal-capabilities preamble appended to every first-party agent's
#: system prompt at LOAD time (D21 deliverable 2 — the persona JSON keeps its
#: voice; the loader tells it about its hands). Mirrors what the copilot's own
#: prompt teaches: the agent CAN drive the cockpit, and it must narrate
#: dispatched-vs-proposed truthfully so chat claims always match real panel state.
TERMINAL_CAPABILITIES_PREAMBLE = (
    "## Terminal capabilities\n"
    "You are operating inside the Vysted terminal, and your analysis comes with "
    "hands — you CAN drive the cockpit with tools, never claim otherwise. You can "
    "open, close, or focus panels (open_panel / close_panel / focus_panel — "
    "open_panel takes an optional symbol so a symbol-aware panel like "
    "equity-overview or the chart opens ON that company, never empty), load a "
    "symbol into the chart (set_chart_symbol), apply chart indicators "
    "(set_chart_indicators), open a company's full overview (open_company_overview "
    "— always pass the symbol), arrange the cockpit layout (arrange_layout), add "
    "or remove watchlist symbols (add_to_watchlist / remove_from_watchlist), "
    "publish a research brief (publish_brief), stage screener filters for the "
    "user to review and run (write_screener_filters), save a screen or the "
    "layout (save_screen / save_layout), maintain the user's LOCAL tracked "
    "portfolio (portfolio_add_position / portfolio_update_position / "
    "portfolio_delete_position — manual holdings the user tracks), "
    "write notes (write_note), switch the market region (set_region), and run "
    "the research tool for a grounded, cited workup. When showing something on "
    "screen would help the user, do it.\n"
    "Narrate these actions truthfully, matching each tool result: a result that "
    "says dispatched means the action was SENT to the panel — verify with "
    "get_terminal_state before claiming completion (panel state is "
    "authoritative, never your tool call); a result that says "
    "awaiting_user_review means it is STAGED for the user's review — say "
    "you proposed it, never claim it is done; a result that reports a failure "
    "means it did NOT happen — say plainly what could not be done. Vysted has "
    "no brokerage connection: you cannot place, stage or simulate trades. If "
    "the user asks to buy or sell, say so plainly and offer to research it or "
    "to track the holding in their local portfolio (portfolio_add_position).\n"
    # R15-AGENT-090: a fact no tool can return (an ADR ratio) was stated and
    # cited to "fundamentals data". The deterministic backstop for the ratio
    # case is _guard_ratio_claims, applied to every sentence _consume_round
    # releases.
    "Unavailable facts: a figure, ratio, date or other specific fact that no "
    "tool result you received contains is UNAVAILABLE. Say plainly that the "
    "terminal's data does not include it, never state a value for it, and never "
    "attribute it to a tool, a data feed or any source (e.g. an ADR ratio when "
    "no result carries one).\n"
    "Stay consistent across turns: when a figure you are about to state "
    "materially contradicts a PRIOR STATED VALUE listed in the terminal context "
    "(the same symbol + metric you stated earlier this session), do NOT silently "
    "switch — acknowledge both openly, state the new figure alongside the prior "
    "one, and explain the change (a new quarter, a different provider, or a "
    "correction). Silently flipping a number the user already saw reads as an "
    "error, not an update."
)


def _grant_first_party_hands(spec: AgentSpec) -> AgentSpec:
    """Union a first-party agent's tools with the catalog's default grant.

    Lead decision D21 (locked) + R10 E5: persona = voice + analytical style
    ONLY. The JSON files keep each persona's voice/specialty tools; at LOAD
    time every first-party agent's effective allow-list is unioned with the
    catalog's :func:`~services.agent_tools.catalog.default_grant_tool_ids`
    projection — the FULL internal capability set, not a hand-picked
    host-actions+research slice — so correctness never again depends on an
    agent JSON staying in sync with the catalog (the E5 "I don't have a
    backtesting tool" drift). Custom agents (the agents_store fallback in
    :func:`get_agent`) are NOT unioned; their authors pick tools.

    §6.5 is untouched: this widens the ALLOW-list only. Every host action
    still rides the proposed-changes gate for EVERY agent, and the read-only
    mode gate in :func:`invoke_agent` strips mutating tools from read turns
    exactly as before.
    """
    merged = list(spec.tools)
    seen = set(merged)
    for tool_id in catalog.default_grant_tool_ids():
        if tool_id not in seen:
            seen.add(tool_id)
            merged.append(tool_id)
    # Tell the persona about its hands (deliverable 2): the shared
    # terminal-capabilities note rides every first-party system prompt at the
    # loader level — the JSON voice text stays untouched on disk. Guarded so a
    # double application (or a prompt that already carries it) stays idempotent.
    prompt = spec.system_prompt
    if TERMINAL_CAPABILITIES_PREAMBLE not in prompt:
        prompt = f"{prompt}\n\n{TERMINAL_CAPABILITIES_PREAMBLE}"
    return spec.model_copy(update={"tools": merged, "system_prompt": prompt})


def _load_schema() -> dict[str, Any]:
    """Read the AgentSpec JSON Schema; raise loudly if missing or malformed.

    The ``defaultProvider`` enum is filled from the model registry here — the
    JSON carries none, so it can never go stale (R15-CODE-AGENT-016).
    """
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        schema = json.load(handle)
    schema["properties"]["defaultProvider"]["enum"] = list(model_registry.provider_ids())
    return schema


def _discover_specs(
    agents_dir: Path = AGENTS_DIR,
) -> tuple[dict[str, AgentSpec], list[dict[str, str]]]:
    """Enumerate the agents directory and return validated :class:`AgentSpec`s.

    Malformed files log a warning and are skipped — they MUST NOT block the
    rest of the roster from loading. Tests rely on partial-load resilience.
    Every skipped file (or a missing directory/schema) is also returned as
    ``{file, reason}`` so ``/health`` can name a shrunken roster (R15-LIFECYCLE-014).
    """
    degraded: list[dict[str, str]] = []
    if not agents_dir.exists():
        logger.error("agents directory not found at %s; no agents will load", agents_dir)
        return {}, [{"file": agents_dir.name, "reason": "agents directory not found"}]
    try:
        schema = _load_schema()
    except FileNotFoundError:
        logger.error("agent schema not found at %s; no agents will load", SCHEMA_PATH)
        return {}, [{"file": SCHEMA_PATH.name, "reason": "agent schema not found"}]
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
            degraded.append({"file": path.name, "reason": f"failed to read JSON: {exc}"})
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
            reason = "; ".join(f"{list(e.path) or '<root>'}: {e.message}" for e in errors)
            degraded.append({"file": path.name, "reason": f"schema violation: {reason}"})
            continue
        try:
            spec = AgentSpec.model_validate(payload)
        except Exception as exc:  # pragma: no cover — schema covers this
            logger.warning("agent %s: pydantic validation failed (%s)", path.name, exc)
            degraded.append({"file": path.name, "reason": f"validation failed: {exc}"})
            continue
        if spec.id in specs:
            logger.warning("agent %s: duplicate id %r; keeping first", path.name, spec.id)
            degraded.append({"file": path.name, "reason": f"duplicate id {spec.id!r}"})
            continue
        # D21 loader-level parity: every first-party agent gets the copilot's
        # host actions + research, derived from the catalog — the JSON stays
        # the persona's voice/specialty. Custom agents (the agents_store
        # fallback in get_agent) are NOT unioned; their authors pick tools.
        specs[spec.id] = _grant_first_party_hands(spec)
    return specs, degraded


# Cached at module import — refreshes on a deliberate :func:`reload` call.
_specs, _degraded = _discover_specs()


def degraded_agents() -> list[dict[str, str]]:
    """The agent files the last load skipped, as ``{file, reason}`` (``[]`` when whole)."""
    return list(_degraded)


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
    global _specs, _degraded
    _specs, _degraded = _discover_specs(agents_dir)


# ---------------------------------------------------------------------------
# Invocation
# ---------------------------------------------------------------------------


#: Hard cap on prior-stated-value claims rendered into the preamble (R13 JARVIS
#: 3b) — the frontend already trims to the recent window; this bounds token cost.
_MAX_PREAMBLE_CLAIMS = 12


def _fmt_claim_value(value: float) -> str:
    """Compact rendering of a stated figure for the preamble."""
    magnitude = abs(value)
    if magnitude != 0 and (magnitude >= 1e12 or magnitude < 1e-4):
        return f"{value:.4g}"
    if magnitude >= 1000:
        return f"{value:,.2f}"
    return f"{value:.4g}"


def _render_prior_stated_values(claims: Any) -> str | None:
    """The "PRIOR STATED VALUES" line (R13 JARVIS 3b): a compact, capped list of
    figures the agent STATED this session so a materially-contradicting new value
    is reconciled openly, never silently switched. ``None`` when there is nothing
    to state — a thin/garbled claims list never renders a half line.
    """
    if not isinstance(claims, list) or not claims:
        return None
    parts: list[str] = []
    for claim in claims[-_MAX_PREAMBLE_CLAIMS:]:
        if not isinstance(claim, dict):
            continue
        metric = claim.get("metric")
        value = claim.get("value")
        symbol = claim.get("symbol") or "?"
        if not isinstance(metric, str) or not isinstance(value, (int, float)):
            continue
        if isinstance(value, bool):
            continue
        when = ""
        stated = claim.get("statedAt")
        if isinstance(stated, (int, float)) and not isinstance(stated, bool):
            try:
                when = " @" + datetime.fromtimestamp(stated / 1000, UTC).strftime("%H:%M")
            except (ValueError, OverflowError, OSError):
                when = ""
        parts.append(f"{symbol} {metric}={_fmt_claim_value(float(value))}{when}")
    if not parts:
        return None
    return "PRIOR STATED VALUES (this session): " + "; ".join(parts)


def _render_terminal_preamble(ts: dict[str, Any]) -> str:
    """Render the structured ``TerminalState`` into a SHORT labelled preamble.

    Detail (every open chart, the full watchlist) is pulled on demand via the
    ``get_terminal_state`` tool — this stays terse so per-turn token cost is
    bounded. The deixis sentence is the highest-leverage line: it lets "is this
    cheap?" resolve to the focused chart ticker.
    """
    focused = ts.get("focusedSymbol")
    lines = ["## What the user is looking at"]
    # Research-space anchor (S-19): when the user is inside a per-stock research
    # space, lead with its symbol + the prior-research memory so the agent
    # "remembers" what it investigated here last time and stays on-topic.
    rs = ts.get("researchSpace")
    if isinstance(rs, dict) and rs.get("symbol"):
        sym = rs["symbol"]
        prior = rs.get("priorTurns") or 0
        lines.append(
            f"Research space: dedicated to {sym}. Treat {sym} as the subject of "
            "this conversation unless the user names another symbol."
        )
        memory = rs.get("memory")
        if isinstance(memory, str) and memory.strip():
            lines.append(f"Prior research memory: {memory.strip()}")
        elif prior:
            lines.append(f"This space has {prior} prior conversation turn(s) on {sym}.")
        prior_values = _render_prior_stated_values(rs.get("claims"))
        if prior_values:
            lines.append(prior_values)
    # "Focused" is the panel the user last touched (its dockview id), not the
    # first chart in the list (R15-AGENT-051).
    focused_panel = ts.get("focusedPanel")
    charts = [c for c in ts.get("charts") or [] if isinstance(c, dict)]
    focused_chart = next((c for c in charts if c.get("panelId") == focused_panel), None)
    shown = focused_chart or (charts[0] if charts else None)
    if shown is not None:
        ind = ", ".join(shown.get("indicators") or []) or "no indicators"
        label = "Focused chart" if focused_chart is not None else "Chart"
        lines.append(f"{label}: {shown.get('symbol')} ({shown.get('timeframe')}, {ind}).")
    if focused_panel and focused_chart is None:
        # Its symbol, when it has one, is the snapshot's focusedSymbol (the
        # "this" line below).
        lines.append(f"Focused panel: {focused_panel}.")
    wl = ts.get("watchlist") or {}
    if wl.get("symbols"):
        lines.append("Watchlist: " + ", ".join(wl["symbols"][:12]) + ".")
    pf = ts.get("portfolio")
    if pf:
        tv = pf.get("totalValue")
        # null total = the panel was closed so no live quotes were joined — say
        # so honestly rather than reporting a fabricated 0 (E3/E6).
        tv_str = (
            f"total value {tv}"
            if tv is not None
            else "total value not marked-to-market (open the Portfolio panel for live values)"
        )
        lines.append(f"Portfolio: {pf.get('positionCount', 0)} positions, {tv_str}.")
    if ts.get("openPanels"):
        lines.append("Open panels: " + ", ".join(ts["openPanels"]) + ".")
    vp = ts.get("viewport")
    if isinstance(vp, dict) and isinstance(vp.get("width"), (int, float)) and vp["width"] > 0:
        w = int(vp["width"])
        if w < 1180:
            fit = "compact — show the ESSENTIALS (chart + brief), not a 4-panel cockpit"
        elif w < 1500:
            fit = "standard — a 3-4 panel cockpit fits"
        else:
            fit = "wide — full multi-panel layouts fit comfortably"
        lines.append(f"Viewport: {w}px wide ({fit}).")
    if focused:
        lines.append(
            f'When the user says "this" or "it", they mean {focused} '
            "unless they name another symbol. Never invent figures — call a tool to fetch them."
        )
    return "\n".join(lines)


#: How much of the focused symbol's note the preamble quotes; the full (capped)
#: text is one ``read_notes`` call away.
_NOTE_EXCERPT_CHARS = 300


def _notes_of(snapshot: AgentContextSnapshot | None) -> dict[str, Any]:
    """The ``__notes__`` entry (C2): ``{"general": str, "bySymbol": {SYM: str}}``,
    each note already capped by the client. Empty when absent or malformed."""
    if snapshot is None or not isinstance(snapshot.by_source, dict):
        return {}
    notes = snapshot.by_source.get("__notes__")
    return notes if isinstance(notes, dict) else {}


def _note_for(notes: dict[str, Any], scope: str) -> tuple[str, str]:
    """``(scope label, note text)`` for a ``read_notes`` scope: 'global' (or
    'general' / empty) is the general note, anything else a symbol's."""
    key = scope.strip().upper()
    if key in ("", "GLOBAL", "GENERAL"):
        text = notes.get("general")
        return "global", text if isinstance(text, str) else ""
    by_symbol = notes.get("bySymbol")
    text = by_symbol.get(key) if isinstance(by_symbol, dict) else None
    return key, text if isinstance(text, str) else ""


def _render_notes_line(notes: dict[str, Any], focused: Any) -> str | None:
    """One line naming the scopes that hold a note, plus an excerpt of the
    focused symbol's note, so the agent knows the user's thesis exists
    (R15-AGENT-020: notes were write-only for the agent)."""
    scopes = []
    if _note_for(notes, "global")[1].strip():
        scopes.append("global")
    by_symbol = notes.get("bySymbol")
    if isinstance(by_symbol, dict):
        scopes += sorted(k for k, v in by_symbol.items() if isinstance(v, str) and v.strip())
    if not scopes:
        return None
    line = f"User notes exist for: {', '.join(scopes)} (read them with read_notes)."
    if isinstance(focused, str) and focused.strip():
        label, text = _note_for(notes, focused)
        if label != "global" and text.strip():
            excerpt = " ".join(text.split())
            if len(excerpt) > _NOTE_EXCERPT_CHARS:
                excerpt = excerpt[:_NOTE_EXCERPT_CHARS] + "..."
            line += f' Their note on {label}: "{excerpt}"'
    return line


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
        preamble = _render_terminal_preamble(terminal)
        notes_line = _render_notes_line(_notes_of(snapshot), terminal.get("focusedSymbol"))
        return f"{preamble}\n{notes_line}" if notes_line else preamble
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


#: The newest history the model sees verbatim (R15-AGENT-040); older turns
#: fold into one summary message instead of silently falling off a window.
_HISTORY_VERBATIM_MESSAGES = 8
_HISTORY_VERBATIM_CHARS = 24_000
#: How much of each older user ask the summary keeps.
_FOLDED_ASK_CHARS = 300
_HISTORY_SUMMARY_HEAD = "Earlier in this conversation (older turns, summarised):"
#: The client's compact trailer lines on an assistant turn (its tool steps and
#: its failure), carried verbatim into the summary.
_HISTORY_TRAILER_PREFIXES = ("[tool steps:", "[failed:")
#: The notice tool that marks a compaction, so the transcript renders its marker.
HISTORY_NOTICE_TOOL = "history"


def _coerce_history(raw: Any) -> tuple[list[LLMMessage], int]:
    """Coerce ``options["history"]`` (a list of {role, content} dicts) into
    LLMMessages, dropping anything malformed.

    The newest turns stay verbatim within a message and character budget,
    starting on a user turn. Anything older folds into ONE separate, stable
    "Earlier in this conversation" message placed before them: each older user
    ask (truncated) and each assistant turn's tool-step and failure trailer
    verbatim. Deterministic, no extra LLM call. Returns the messages and how
    many were folded (R15-AGENT-040: the old ``[-10:]`` dropped the rest).
    """
    if not isinstance(raw, list):
        return [], 0
    turns: list[LLMMessage] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content:
            turns.append(LLMMessage(role=role, content=content))
    keep = used = 0
    for message in reversed(turns):
        if keep >= _HISTORY_VERBATIM_MESSAGES or (
            keep and used + len(message.content) > _HISTORY_VERBATIM_CHARS
        ):
            break
        keep += 1
        used += len(message.content)
    while keep and turns[len(turns) - keep].role != "user":
        keep -= 1
    older, recent = turns[: len(turns) - keep], turns[len(turns) - keep :]
    if not older:
        return recent, 0
    lines = [_HISTORY_SUMMARY_HEAD]
    for message in older:
        if message.role == "user":
            ask = " ".join(message.content.split())
            if len(ask) > _FOLDED_ASK_CHARS:
                ask = ask[:_FOLDED_ASK_CHARS] + "..."
            lines.append(f"- The user asked: {ask}")
        else:
            lines += [
                f"- {line.strip()}"
                for line in message.content.splitlines()
                if line.strip().startswith(_HISTORY_TRAILER_PREFIXES)
            ]
    return [LLMMessage(role="user", content="\n".join(lines)), *recent], len(older)


def _render_session_preamble() -> str:
    """Anchor the turn in the SERVER clock + the user's locale and forbid answering
    a time-sensitive question from (stale) training memory.

    The model's training data is frozen at a cutoff; "today"/"now"/"latest"/a
    price/market-state must be fetched live, never recalled. This line-group is
    prepended as a system message so it leads every turn — the highest-leverage
    fix for the "answers from memory" failure (symptom #1)."""
    now = datetime.now(UTC)
    today = now.strftime("%Y-%m-%d")
    weekday = now.strftime("%A")
    region = config.get_region()
    return (
        f"Current date: {today} ({weekday}). Session locale: {region}.\n"
        'Your training data is STALE. For anything time-sensitive ("today", "now", '
        '"latest", "current", "this week", a price, market state, or breaking news) '
        "you MUST call a tool to fetch live data before answering — never answer from "
        "memory. If you cannot fetch it, say so plainly; do not invent specifics."
    )


def _compose_messages(
    spec: AgentSpec,
    prompt: str,
    context: AgentContextSnapshot | None,
    history: list[LLMMessage] | None = None,
) -> list[LLMMessage]:
    """Build the system + context + history + user message list for the call."""
    messages: list[LLMMessage] = [LLMMessage(role="system", content=spec.system_prompt)]
    messages.append(LLMMessage(role="system", content=_render_session_preamble()))
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
#: The note that opens the capped final round (R15-AGENT-003, D-B3-6).
_CAPPED_ROUND_NOTE = (
    "The tool budget for this turn is exhausted: do not call any more tools. "
    "Answer the user now from the results you already have, and say plainly "
    "what is still missing."
)
#: The honest close when the capped round still produced no text.
_CAPPED_ROUND_CLOSE = (
    f"I stopped after {_MAX_TOOL_ROUNDS} tool rounds without reaching a final answer. "
    "Ask me to continue, or narrow the request."
)
#: Per-run web-search cap (FR-081) — bounds per-search billing during a multi-round
#: research run, for BOTH the native tier (the searches each round's usage
#: reports are counted; the provider gets the remaining budget as max_uses and
#: no native search once it is spent, R15-AGENT-049) and the BYOK/local
#: `web_search` tool (counted in the loop; further calls return a cap-reached
#: message instead of dispatching).
_WEB_SEARCH_CAP = 5


def _native_search_enabled(
    provider_id: str, model_web_search: str | None, model: str | None = None
) -> bool:
    """Decide whether THIS turn rides the provider's native server-side search.

    Delegates to :func:`services.llm.native_search.native_search_available` —
    THE one detection truth (R9 Track A interface; Team B's tier_a cross-verify
    reads the same function, so the two surfaces can never disagree). WS5
    semantics: the provider-level provider (anthropic) always qualifies;
    OpenAI, Groq and Gemini are per-MODEL (R15-AGENT-005); OpenRouter is gated
    per-MODEL on the resolved model's :attr:`LLMModelOption.web_search` flag
    (``"native"`` → ride it; ``"plugin"`` is OpenRouter's billed plugin, never
    auto-enabled; ``"none"``/unknown keeps the local tool — the FR-082
    fallback, which never fabricates).
    """
    return native_search.native_search_available(provider_id, model_web_search, model)


#: Research tool(s) whose result the runtime auto-publishes to the brief panel.
#: After the R4 collapse (FR-115) there is ONE research tool; depth (quick/deep/
#: heavy) is an internal arg on it, so every depth auto-publishes through here.
_RESEARCH_TOOLS = ("research",)
#: Tools whose result carries a raw ``Fundamentals`` dump or statement the model
#: reads only through its money displays (R15-AGENT-001 class, rc1-scenarios:5).
_FUNDAMENTALS_TOOLS = ("fundamentals", "compare_symbols", "financial_statements")


LocalToolHandler = Any  # async (dict) -> dict, bound per-invocation

#: Headroom (seconds) the research outer guard adds above the engine's own
#: wall budget (E7) — the guard is a backstop for a WEDGED engine, never a
#: second scheduler racing a healthy run.
_RESEARCH_GUARD_EXTRA_SECONDS = 90.0

#: Per-depth wall floors for the research guard, covering BOTH engines: the
#: tier_a depth-profile walls (deep 120 / ultra 360) AND the tier_b hosted
#: research-model walls (normal 120 / deep 300 / ultra 480) — the guard takes
#: the max so it can never fire before a legitimately-running engine finishes.
_RESEARCH_WALL_FLOOR_SECONDS = {"normal": 120.0, "deep": 300.0, "ultra": 480.0}


def _research_guard_seconds(args: Any) -> float:
    """The research tool's outer timeout: ``wall_seconds + 90`` from its args.

    Resolves the effective depth exactly as the handler does (the MAX of the
    model's arg and the composer-slider floor), takes the larger of the
    explicit ``wall_seconds`` arg, the depth profile's wall, and the per-depth
    engine floor, then adds the guard headroom.
    """
    from services.research import depth as depth_mod

    arg_map = args if isinstance(args, dict) else {}
    rank = {depth_mod.DEPTH_NORMAL: 0, depth_mod.DEPTH_DEEP: 1, depth_mod.DEPTH_ULTRA: 2}
    model_depth = depth_mod.normalize_depth(arg_map.get("depth"))
    slider_depth = depth_mod.normalize_depth(config.get_request_research_depth())
    depth = model_depth if rank[model_depth] >= rank[slider_depth] else slider_depth
    try:
        wall = float(arg_map.get("wall_seconds"))
    except (TypeError, ValueError):
        wall = 0.0
    profile_wall = float(depth_mod.profile_for(depth).wall_seconds)
    floor = _RESEARCH_WALL_FLOOR_SECONDS.get(depth, 120.0)
    return max(wall, profile_wall, floor) + _RESEARCH_GUARD_EXTRA_SECONDS


def _tool_timeout_seconds(event: LLMToolUseEvent) -> float | None:
    """The dispatch wall budget for one registry tool call (E7); ``None`` = none."""
    if event.name == "research":
        return _research_guard_seconds(event.input)
    return catalog.timeout_for(event.name)


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

    R10 (E7): registry tools run under their catalog ``timeout_seconds`` (the
    ``research`` guard derives from its args) via ``asyncio.wait_for`` — a
    timed-out tool returns an honest message with a per-domain next step and
    the loop CONTINUES; host-action locals + per-invocation reads are exempt
    (frontend round-trips / in-memory).
    """
    name = event.name
    # WS8 Step 1: the adapter could not parse/validate/repair this call's
    # arguments. Surface the structured error keyed on the call id (mirrors the
    # "tool not found" convention) so the model self-corrects next round —
    # NEVER dispatch with coerced-to-{} args.
    if isinstance(event.input, dict) and INVALID_ARGS_SENTINEL in event.input:
        payload = {"ok": False, "error": str(event.input[INVALID_ARGS_SENTINEL])}
        try:
            return json.dumps(payload, default=str)
        except (TypeError, ValueError):  # pragma: no cover — defensive
            return str(payload)
    try:
        if local_tools and name in local_tools:
            payload: dict[str, Any] = await local_tools[name](event.input)
        elif agent_tools.is_registered(name):
            timeout = _tool_timeout_seconds(event)
            if timeout is not None:
                try:
                    payload = await asyncio.wait_for(
                        agent_tools.invoke_tool(name, event.input), timeout
                    )
                except TimeoutError:
                    payload = {
                        "ok": False,
                        "error": "timeout",
                        "message": (
                            f"{name} timed out after {int(timeout)}s — "
                            f"{catalog.timeout_hint_for(name)}"
                        ),
                    }
            else:
                payload = await agent_tools.invoke_tool(name, event.input)
        else:
            payload = {"ok": False, "error": f"tool {name!r} is not available in this build"}
    except Exception as exc:  # noqa: BLE001 — surface failures to the model
        payload = {"ok": False, "error": f"tool {name!r} raised: {exc}"}
    try:
        return json.dumps(payload, default=str)
    except (TypeError, ValueError):
        return str(payload)


#: Schema types a small model often sends as a JSON *string* (R15-AGENT-024:
#: ``criteria: "[{...}]"``; R15-AGENT-093: ``max_strikes: "10"``), mapped to
#: the exact Python types the parsed string may have. bool is not an int here.
_JSON_STRING_TYPES: dict[str, tuple[type, ...]] = {
    "array": (list,),
    "object": (dict,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
}


def _reject_json_constant(name: str) -> float:
    """``json.loads`` hook: ``"NaN"``/``"Infinity"`` are not numbers a tool takes."""
    raise ValueError(name)


def _normalise_tool_args(event: LLMToolUseEvent) -> None:
    """The ONE runtime argument check, for every adapter (D-B3-4).

    Validation used to live only in the OpenAI adapter, so a host action with a
    missing required field (``portfolio_add_position`` with no ``cost_basis``)
    reached the UI, which coerced it to 0 (R15-AGENT-022). Runs on every
    ``tool_use`` before it is yielded, and mutates ``event.input`` in place:

    - an explicit ``null`` means "not given" and is dropped, so it reads as a
      missing field rather than a type error;
    - an ``array``/``object`` param sent as a JSON string is parsed, kept only
      when the parsed type matches (R15-AGENT-024: local 8B models send
      ``write_screener_filters.criteria`` as a string and the host drops it),
      and so is an ``integer``/``number``/``boolean`` param sent as an exact
      JSON literal string (R15-AGENT-093: ``max_strikes: "10"``);
    - the args are validated against the catalog ``input_schema``; on failure
      the input is replaced by :data:`INVALID_ARGS_SENTINEL` with a
      model-readable reason, which ``_dispatch_tool`` returns as
      ``{ok: false, error}`` without running the handler.

    No schema default is filled (C2): an omitted optional arg stays omitted.
    An unknown tool is left to ``_dispatch_tool``'s "not available" result.
    """
    args = event.input
    cap = catalog.CAPABILITY_CATALOG.get(event.name)
    if cap is None or INVALID_ARGS_SENTINEL in args:
        return
    for key in [k for k, v in args.items() if v is None]:
        del args[key]
    properties = cap.input_schema.get("properties") or {}
    for key, value in args.items():
        expected = (properties.get(key) or {}).get("type")
        if expected not in _JSON_STRING_TYPES or not isinstance(value, str):
            continue
        try:
            parsed = json.loads(value, parse_constant=_reject_json_constant)
        except ValueError:
            continue
        if type(parsed) in _JSON_STRING_TYPES[expected]:
            args[key] = parsed
    validator_cls = jsonschema.validators.validator_for(cap.input_schema)
    error = jsonschema.exceptions.best_match(validator_cls(cap.input_schema).iter_errors(args))
    if error is None:
        return
    if error.validator == "required" and not error.path and cap.kind == "host_action":
        missing = next(f for f in error.validator_value if f not in error.instance)
        reason = (
            f"invalid arguments for {event.name}: missing {missing} — ask the user "
            "for it; do not guess"
        )
    else:
        reason = f"invalid arguments for {event.name}: {error.message}; call again with valid args"
    event.input = {INVALID_ARGS_SENTINEL: reason}


#: Context admission (D-B4-1, R15-AGENT-008). Estimates are chars/4: no
#: tokenizer ships in the sidecar, and Ollama's usage only counts uncached tokens.
_CHARS_PER_TOKEN = 4
#: A tool result the model reads is cut past this on a lane with no window: above
#: the largest captured hosted research result (~42 KB, r15 surface/research-briefs),
#: so a normal research result is never cut there.
_RESULT_CHAR_CEILING = 64_000
#: On a window-bound lane one tool result may fill 1/N of the window.
_RESULT_WINDOW_SHARE = 8
#: On a window-bound lane 1/N of the window stays free for the answer.
_ANSWER_RESERVE_SHARE = 8
#: What an older tool result becomes when the round would not fit the window.
_ELIDED_RESULT = (
    "[earlier tool result elided to fit the model's context window — call the tool "
    "again if you still need it]"
)


def _message_chars(message: LLMMessage) -> int:
    meta = len(json.dumps(message.metadata, default=str)) if message.metadata else 0
    return len(message.content) + meta


def _estimate_tokens(messages: list[LLMMessage], tool_ids: list[str]) -> int:
    """The round's prompt size in tokens: the tool schemas sent plus every message."""
    chars = len(json.dumps(openai_tools(tool_ids))) + sum(_message_chars(m) for m in messages)
    return chars // _CHARS_PER_TOKEN


def _window_tool_subset(tool_ids: list[str], messages: list[LLMMessage], window: int) -> list[str]:
    """Send only the always-on domains plus the cued specialists when the full
    schema set and system prompt would take over half the window.

    This replaces the lane's silent head truncation with a deliberate subset;
    the agent's allow-list itself is unchanged (D21).
    """
    system_chars = sum(len(m.content) for m in messages if m.role == "system")
    if len(json.dumps(openai_tools(tool_ids))) + system_chars <= window * _CHARS_PER_TOKEN // 2:
        return tool_ids
    recent = " ".join(m.content for m in [m for m in messages if m.role == "user"][-3:]).lower()
    keep = set(catalog.ALWAYS_ON_DOMAINS) | {
        domain
        for domain, cues in catalog.DOMAIN_CUES.items()
        if any(re.search(r"\b" + re.escape(cue), recent) for cue in cues)
    }
    subset = [t for t in tool_ids if catalog.domain_of(t) in keep]
    logger.debug(
        "context admission: window=%d, sending %d of %d tools (domains %s)",
        window,
        len(subset),
        len(tool_ids),
        sorted(keep),
    )
    return subset


def _fit_to_window(messages: list[LLMMessage], tool_ids: list[str], window: int) -> None:
    """Elide the oldest tool results until the round fits the window minus the
    answer reserve. The latest round's results and every non-tool message (the
    user prompt included) are never touched."""
    budget = (window - window // _ANSWER_RESERVE_SHARE) * _CHARS_PER_TOKEN
    total = _estimate_tokens(messages, tool_ids) * _CHARS_PER_TOKEN
    last_call = max(
        (
            i
            for i, m in enumerate(messages)
            if m.role == "assistant" and m.metadata and m.metadata.get("tool_calls")
        ),
        default=0,
    )
    for message in messages[:last_call]:
        if total <= budget:
            return
        if message.role == "tool" and message.content != _ELIDED_RESULT:
            total -= len(message.content) - len(_ELIDED_RESULT)
            message.content = _ELIDED_RESULT


def _model_facing_content(tool_name: str, result_str: str, window: int | None = None) -> str:
    """The tool message the MODEL reads, split from the raw result (D-B3-5).

    A research, fundamentals, compare or statement result's money scalars become their
    semantics displays, so a small model cannot mis-scale a raw rupee float or
    read a statement size in the wrong currency (R15-AGENT-001). A tool whose
    catalog entry is ``untrusted_text`` (web, news, disclosures, research) is
    fenced with ``wrap_untrusted``, so injected instructions in a page read as
    data in a turn that also holds write tools (R15-AGENT-021). The panel view
    (auto-publish) keeps parsing the raw, unfenced ``result_str``.
    """
    content = result_str
    if tool_name in _RESEARCH_TOOLS:
        from services.agent_tools import research

        content = research.model_content(content)
    elif tool_name in _FUNDAMENTALS_TOOLS:
        from services.agent_tools import research

        content = research.fundamentals_content(content)
    # Size cap (R15-AGENT-008): a share of the window when the lane has one,
    # else a ceiling no normal result reaches. Cut before the untrusted fence
    # so the fence stays whole.
    limit = window * _CHARS_PER_TOKEN // _RESULT_WINDOW_SHARE if window else _RESULT_CHAR_CEILING
    if len(content) > limit:
        content = (
            f"{content[:limit]}…[{len(content) - limit} chars elided — call again with a "
            "narrower query or a smaller limit]"
        )
    if catalog.is_untrusted_text(tool_name):
        content = wrap_untrusted(tool_name, content)
    return content


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

#: A heartbeat frame goes out after this much silence while the runtime waits on
#: a provider or a tool, so the chat's stall watchdog can tell a slow turn from
#: a dead one (R15-AGENT-025).
_HEARTBEAT_SECONDS = 10.0
#: The planner pre-pass runs before the turn's first frame; past this it is
#: skipped and the turn proceeds without a visible plan (R15-AGENT-025).
_PLANNER_TIMEOUT_SECONDS = 20.0


async def _relay_provider(stream: AsyncIterator[Any], idle: float) -> AsyncIterator[Any]:
    """Relay one provider round from a producer task so the wait is timed.

    A heartbeat goes out every :data:`_HEARTBEAT_SECONDS` of silence; after
    ``idle`` seconds with no provider event the relay ends the round with an
    error frame instead of waiting on the socket (R15-AGENT-025). A failure in
    the stream re-raises here; closing the relay cancels the provider call.
    """
    queue: asyncio.Queue[Any] = asyncio.Queue()

    async def _produce() -> None:
        try:
            async for event in stream:
                queue.put_nowait(event)
        finally:
            queue.put_nowait(_STEP_SENTINEL)

    task = asyncio.create_task(_produce())
    quiet = 0.0
    try:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), _HEARTBEAT_SECONDS)
            except TimeoutError:
                quiet += _HEARTBEAT_SECONDS
                if quiet >= idle:
                    yield LLMErrorEvent(
                        message="The provider went quiet and did not finish the answer.",
                        action="Retry, or switch the composer to a different model.",
                        detail=f"no provider event for {int(idle)}s",
                        code="provider_idle",
                    )
                    return
                yield LLMHeartbeatEvent()
                continue
            if item is _STEP_SENTINEL:
                await task
                return
            quiet = 0.0
            yield item
    finally:
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


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
) -> AsyncIterator[LLMResearchStepEvent | LLMHeartbeatEvent | _ToolDone]:
    """Dispatch a tool, streaming any live research steps it emits, then yield a
    terminal :class:`_ToolDone` carrying the JSON result string (Track A).

    A long research run (``research`` at depth=deep/heavy) pushes
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
            try:
                item = await asyncio.wait_for(queue.get(), _HEARTBEAT_SECONDS)
            except TimeoutError:
                yield LLMHeartbeatEvent()  # a quiet tool is still running
                continue
            if item is _STEP_SENTINEL:
                break
            index += 1
            yield _step_event(tool_call, item, index)
        yield _ToolDone(await task)
    finally:
        # The consumer closed us mid-tool (Stop / SSE disconnect -> aclose()):
        # cancel the tool so its research / LLM / web calls stop spending now.
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        config.reset_step_sink(token)


def _auto_open_backtest_event(
    tool_call: LLMToolUseEvent, result_str: str
) -> LLMToolUseEvent | None:
    """Synthetic ``open_panel(backtest, run_id)`` after a successful
    ``run_custom_backtest`` (C1, R15-AGENT-011).

    The tool tells the model the result renders in the backtest panel; this
    makes it so, the way :func:`_auto_publish_event` does for research: it rides
    the same proposed-changes gate and is never dispatched back to the model.
    ``None`` for a failed run, so no panel opens on nothing.
    """
    try:
        payload = json.loads(result_str)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict) or not payload.get("ok") or not payload.get("runId"):
        return None
    return LLMToolUseEvent(
        tool_call_id=f"auto-backtest-{tool_call.tool_call_id}",
        name="open_panel",
        input={"panel": "backtest", "run_id": payload["runId"]},
    )


def _auto_publish_event(tool_call: LLMToolUseEvent, result_str: str) -> LLMToolUseEvent | None:
    """A synthetic ``publish_brief`` carrying the research tool's ``brief`` verbatim.

    Only the MODEL sees the research result, and a weak local model may never
    call ``publish_brief``, so the runtime emits this after every successful
    research round. It rides the SAME proposed-changes gate as a model-issued
    publish (AUTO applies it, review queues it) and is idempotent with one
    (``setBrief`` replaces). The research tool owns the brief's shape (C6,
    R15-CODE-AGENT-008); a result with no ``brief`` publishes nothing.
    """
    try:
        payload = json.loads(result_str)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    brief = payload.get("brief") if isinstance(payload, dict) and payload.get("ok") else None
    if not isinstance(brief, dict):
        return None
    return LLMToolUseEvent(
        tool_call_id=f"{tool_call.tool_call_id}__autobrief",
        name="publish_brief",
        input=brief,
    )


#: The truncation notice for an answer cut at the model's output ceiling.
_LENGTH_NOTICE = (
    "The answer hit the model's output limit and was cut off. Ask me to continue for the rest."
)
_RETRY_ACTION = "Retry, or switch the composer to a different model."


def _unfinished_round_error(streamed_text: bool, model: str) -> LLMErrorEvent:
    """The error frame for a round that never finished (R15-AGENT-026): the
    provider closed with no terminator, so a partial answer is not a complete one
    and an empty one is not an answer. The chat renders it with Retry."""
    if streamed_text:
        return LLMErrorEvent(
            message="The provider closed the stream before the answer finished.",
            action=_RETRY_ACTION,
            detail=f"no finish reason from {model}",
            code="truncated",
        )
    return _empty_response_error(model)


def _empty_response_error(model: str) -> LLMErrorEvent:
    return LLMErrorEvent(
        message="The model returned an empty answer.",
        action=_RETRY_ACTION,
        detail=f"no text and no tool call from {model}",
        code="empty_response",
    )


#: The ``research_step`` kind of every runtime notice (C9, R15-AGENT-031): the
#: chat branches on it, so notice copy can change without breaking the chip.
NOTICE_STEP_KIND = "notice"
#: The Delegate-only pause capability (FR-028): ``run_manager`` stops the turn
#: on it and parks the run ``paused`` with the question.
ASK_USER_TOOL = "ask_user"
#: The notice ``invoke_agent`` yields when ``on_round_usage`` refused another
#: round: the round's tool calls were NOT dispatched (R15-AGENT-037).
HALT_NOTICE_TOOL = "run_halt"
#: The notice ``invoke_agent`` yields when the agent names a tool id the
#: catalog no longer has, under any alias (R15-LIFECYCLE-025).
RETIRED_TOOLS_NOTICE_TOOL = "retired_tools"

#: End-of-stream ack grace (E3.3): the frontend's ``POST /agents/actions/ack``
#: is an async HTTP round-trip racing the stream's close, so the divergence
#: check polls the ledger briefly before declaring a publish unconfirmed.
#: Module-level so tests can shrink it to ~0.
_ACK_GRACE_SECONDS = 0.8
_ACK_POLL_SECONDS = 0.1


def _ack_brief(entry: dict[str, Any] | None) -> dict[str, Any]:
    """The applied-brief identity dict off an ack entry, or ``{}``."""
    brief = entry.get("brief") if isinstance(entry, dict) else None
    return brief if isinstance(brief, dict) else {}


def _ack_symbol(entry: dict[str, Any] | None) -> str | None:
    """The normalised symbol an ack's brief identity names, or ``None``."""
    sym = _ack_brief(entry).get("symbol")
    return sym.strip().upper() if isinstance(sym, str) and sym.strip() else None


def _ack_brief_label(entry: dict[str, Any] | None) -> str:
    """``" (SYMBOL, N sources)"`` from the ack's applied-brief identity, else
    ``""`` — names what is ACTUALLY on screen so a notice is concrete, not the
    old hardcoded "richer brief" claim (R13 JARVIS 1c)."""
    brief = _ack_brief(entry)
    sym = brief.get("symbol")
    count = brief.get("source_count")
    parts: list[str] = []
    if isinstance(sym, str) and sym.strip():
        parts.append(sym.strip().upper())
    if isinstance(count, (int, float)) and not isinstance(count, bool):
        n = int(count)
        parts.append(f"{n} source{'' if n == 1 else 's'}")
    return f" ({', '.join(parts)})" if parts else ""


def _superseded_by_later_apply(pos: int, entries: list[tuple[str, dict[str, Any] | None]]) -> bool:
    """True when a LATER entry is an APPLIED publish of the same panel/symbol.

    The brief panel is single-slot: once a later publish of the SAME symbol (or
    of an unknown symbol — the slot is occupied either way) lands ``applied``,
    it is the artifact on screen, so this earlier non-applied call is SUPERSEDED,
    not a real divergence. Suppressing its notice kills tonight's false
    contradiction — a per-call ``kept_previous`` chip firing while the panel
    already shows the later, successful publish (R13 JARVIS 1c).
    """
    this_symbol = _ack_symbol(entries[pos][1])
    for _cid, entry in entries[pos + 1 :]:
        if not entry or entry.get("status") != "applied":
            continue
        later_symbol = _ack_symbol(entry)
        if this_symbol is None or later_symbol is None or later_symbol == this_symbol:
            return True
    return False


async def _publish_divergence_notices(publish_calls: list[str]) -> list[LLMResearchStepEvent]:
    """The end-of-stream read-back (E3.3): one quiet notice per publish whose
    panel outcome DIVERGED from the dispatched optimism.

    Checks the ack ledger for every ``publish_brief`` tool call of this turn:
    no ack → "the panel did not confirm"; ``kept_previous`` → the panel kept the
    artifact already on screen (NAMED from the ack — never the old hardcoded
    "richer brief" claim); ``failed`` → the apply failed. A call SUPERSEDED by a
    later successful publish of the same panel/symbol in the SAME turn emits
    NOTHING (:func:`_superseded_by_later_apply`) — the panel shows the applied
    one, so a per-call contradiction would lie (R13 JARVIS 1c). Each rides a
    ``research_step`` with ``step_kind="notice"`` (C9): the frontend renders it
    as a transcript chip by KIND, never by matching this copy (R15-AGENT-031).
    """
    deadline = time.monotonic() + _ACK_GRACE_SECONDS
    pending = {cid for cid in publish_calls if action_ledger.get(cid) is None}
    while pending and time.monotonic() < deadline:
        await asyncio.sleep(_ACK_POLL_SECONDS)
        pending = {cid for cid in pending if action_ledger.get(cid) is None}
    entries = [(cid, action_ledger.take(cid)) for cid in publish_calls]
    notices: list[LLMResearchStepEvent] = []
    for index, (call_id, entry) in enumerate(entries, start=1):
        status = entry.get("status") if entry else None
        if status == "applied":
            continue  # the optimistic dispatch was right; nothing to say.
        # A later successful publish of the same panel/symbol already replaced
        # whatever this call did — suppress the false contradiction.
        if _superseded_by_later_apply(index - 1, entries):
            continue
        label = _ack_brief_label(entry)
        if entry is None:
            detail = (
                "The brief panel did not confirm the publish — treat it as NOT "
                "rendered until get_terminal_state shows it."
            )
            step_status = "error"
        elif status == "kept_previous":
            detail = (
                f"The panel kept the brief already on screen{label} — this publish "
                "did not replace it; do not claim the new one rendered."
            )
            step_status = "ok"
        else:  # failed / unknown status — the apply did not land.
            detail = f"The brief panel reported the publish failed{label}."
            step_status = "error"
        notices.append(
            LLMResearchStepEvent(
                tool_call_id=call_id,
                tool="publish_brief",
                step_kind=NOTICE_STEP_KIND,
                detail=detail,
                status=step_status,
                index=index,
            )
        )
    return notices


def _staged_actions_notice(staged: list[LLMToolUseEvent]) -> LLMResearchStepEvent | None:
    """One deterministic notice naming every host action this turn STAGED for
    review (R15-AGENT-033): under ASK the model may still narrate "I've set BDL
    on your chart", so the transcript states what actually happened."""
    if not staged:
        return None
    summaries = []
    for call in staged:
        args = call.input if isinstance(call.input, dict) else {}
        target = next(
            (
                args[k]
                for k in ("symbol", "panel", "scope", "pattern")
                if isinstance(args.get(k), str)
            ),
            None,
        )
        summaries.append(f"{call.name} {target}" if target else call.name)
    return LLMResearchStepEvent(
        tool_call_id=staged[-1].tool_call_id,
        tool="host_action",
        step_kind=NOTICE_STEP_KIND,
        detail=(
            "Staged for your review, not applied yet: "
            + "; ".join(summaries)
            + ". Accept it below to apply."
        ),
        status="ok",
    )


def _result_status(result_str: str) -> Any:
    """The ``status`` field of a JSON tool result, or ``None``."""
    try:
        payload = json.loads(result_str)
    except (TypeError, ValueError):
        return None
    return payload.get("status") if isinstance(payload, dict) else None


def _tool_result_event(tool_call: LLMToolUseEvent, result_str: str) -> LLMToolResultEvent:
    """The outcome of one dispatched call (R15-CODE-AGENT-033): not ok when the
    result is a dict with ``ok: false`` or a truthy ``error``."""
    try:
        payload = json.loads(result_str)
    except (TypeError, ValueError):
        payload = None
    failed = isinstance(payload, dict) and (
        payload.get("ok") is False or bool(payload.get("error"))
    )
    reason = (payload.get("error") or payload.get("message")) if failed else None
    return LLMToolResultEvent(
        tool_call_id=tool_call.tool_call_id,
        name=tool_call.name,
        ok=not failed,
        error=str(reason)[:200] if reason else None,
    )


async def _end_of_turn_notices(
    autonomy: str | None,
    publish_brief_calls: list[str],
    staged_actions: list[LLMToolUseEvent],
) -> list[LLMResearchStepEvent]:
    """The notices that precede the turn's terminator, whichever way it ends."""
    notices: list[LLMResearchStepEvent] = []
    # E3.3 end-of-stream read-back: under AUTO a publish was DISPATCHED
    # optimistically — surface any divergence the panel acked (or never acked).
    if autonomy == "auto" and publish_brief_calls:
        notices.extend(await _publish_divergence_notices(publish_brief_calls))
    staged = _staged_actions_notice(staged_actions)
    if staged is not None:
        notices.append(staged)
    return notices


_HOST_ACTION_IDS: frozenset[str] | None = None


def _host_action_ids() -> frozenset[str]:
    """The host-action tool ids (lazy + cached — avoids an import cycle at
    module load, since the schemas module reaches back through the catalog)."""
    global _HOST_ACTION_IDS
    if _HOST_ACTION_IDS is None:
        from services.agent_tools.schemas import HOST_ACTION_TOOLS

        _HOST_ACTION_IDS = frozenset(HOST_ACTION_TOOLS)
    return _HOST_ACTION_IDS


async def _await_host_action_acks(call_ids: list[str]) -> None:
    """Grace-bounded poll of the ack ledger for a set of dispatched host-action
    call ids (E3.3 pattern, R13 JARVIS 1b).

    Returns once every id carries an ack or the shared ``_ACK_GRACE_SECONDS``
    window closes — the in-loop read-back then rewrites each tool-result from the
    real outcome instead of the optimistic "dispatched". One window covers the
    whole round's host actions (not one wait per call) so the loop never stalls.
    """
    deadline = time.monotonic() + _ACK_GRACE_SECONDS
    pending = {cid for cid in call_ids if action_ledger.get(cid) is None}
    while pending and time.monotonic() < deadline:
        await asyncio.sleep(_ACK_POLL_SECONDS)
        pending = {cid for cid in pending if action_ledger.get(cid) is None}


def _grounded_host_action_result(tool_call: LLMToolUseEvent, entry: dict[str, Any] | None) -> str:
    """Rewrite a dispatched host-action's tool-result from the panel's real ack
    (R13 JARVIS 1b) so the model's NEXT narration is grounded, never optimistic.

    No ack in the grace window → an explicit "dispatched, not yet confirmed —
    verify before claiming success" (strengthened from today's soft advisory).
    ``applied`` → confirmed (the model may state it done); ``kept_previous`` /
    ``failed`` → say plainly it did NOT render. The ``detail`` names the action +
    symbol/panel (from the ack, falling back to the call args) so the grounded
    result is concrete.
    """
    action = tool_call.name
    args = tool_call.input if isinstance(tool_call.input, dict) else {}
    ack_detail = entry.get("detail") if isinstance(entry, dict) else None
    ack_detail = ack_detail if isinstance(ack_detail, dict) else {}
    descriptor: dict[str, Any] = {"action": action}
    for key in ("symbol", "panel"):
        val = ack_detail.get(key)
        if not (isinstance(val, str) and val):
            candidate = args.get(key)
            val = candidate if isinstance(candidate, str) and candidate else None
        if val:
            descriptor[key] = val
    if entry is None:
        payload: dict[str, Any] = {
            "ok": True,
            "status": "dispatched_unconfirmed",
            "detail": descriptor,
            "note": (
                "Dispatched to the panel but NOT yet confirmed — verify with "
                "get_terminal_state before claiming success; do not report it as done."
            ),
        }
    else:
        status = entry.get("status")
        if status == "applied":
            payload = {
                "ok": True,
                "status": "applied",
                "detail": descriptor,
                "note": "The panel confirmed this applied — you may state it as done.",
            }
        elif status == "kept_previous":
            payload = {
                "ok": True,
                "status": "kept_previous",
                "detail": descriptor,
                "note": (
                    "The panel KEPT its previous state (a richer artifact or a stale "
                    "run superseded this) — do NOT claim this change rendered."
                ),
            }
        elif status == "staged":
            # D-B3-2: AUTO does not skip review for this kind; it waits in the
            # user's review queue. Not applied, and not a failure either.
            payload = {
                "ok": True,
                "status": "staged",
                "detail": descriptor,
                "note": (
                    "Staged in the user's review queue, awaiting their review — it has "
                    "NOT been applied yet. Tell the user you proposed it; do not claim "
                    "it is done."
                ),
            }
        else:  # failed / unknown — an honest non-application.
            payload = {
                "ok": False,
                "status": status or "failed",
                "detail": descriptor,
                "note": "The panel reported this did NOT apply — say plainly it did not happen.",
            }
    try:
        return json.dumps(payload, default=str)
    except (TypeError, ValueError):  # pragma: no cover — defensive
        return str(payload)


def _build_local_tools(
    snapshot: AgentContextSnapshot | None,
    autonomy: str | None = None,
) -> dict[str, LocalToolHandler]:
    """Per-invocation tool handlers that need request scope or drive the host.

    ``get_terminal_state`` / ``get_portfolio`` return state passed in the request
    (the sidecar can't read the frontend's stores). The host-action tools return
    a synthetic result carrying a ``host_action`` directive whose narration tracks
    the user's autonomy: with ``autonomy="auto"`` the action is
    DISPATCHED to the panel (the frontend's auto-apply lands it asynchronously),
    so the result says ``dispatched`` and tells the model to VERIFY with
    ``get_terminal_state`` before claiming completion — panel state is
    authoritative, never the tool call (E3.3: the old "applied … past tense"
    optimism preceded ``applyHostAction``, whose guards can keep prior state).
    Otherwise (``ask`` / unknown) the action is STAGED in the diff/accept trust
    gate (FR-010), reports ``awaiting_user_review``, and the model must say it
    *proposed* the change, not that it happened. The frontend honours the same
    split (proposed-changes auto-applies under AUTO and stages otherwise), so
    this narration matches what actually lands.
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

    notes = _notes_of(snapshot)

    async def _read_notes(args: dict[str, Any]) -> dict[str, Any]:
        scope, text = _note_for(notes, str(args.get("scope") or ""))
        if not text.strip():
            return {
                "ok": True,
                "scope": scope,
                "note": "",
                "empty": True,
                "message": f"The user has no {scope} note.",
            }
        return {"ok": True, "scope": scope, "note": text, "empty": False}

    local: dict[str, LocalToolHandler] = {
        "get_terminal_state": _terminal_state,
        "get_portfolio": _portfolio,
        "read_notes": _read_notes,
    }

    def _make_host_action(tool_id: str) -> LocalToolHandler:
        async def _handler(args: dict[str, Any]) -> dict[str, Any]:
            if autonomy == "auto":
                # Auto-apply on: the frontend WILL land
                # it — but it has not confirmed yet (E3.3: the old "applied …
                # past tense" claim preceded applyHostAction, whose guards can
                # keep prior state). Honest narration: dispatched, verify.
                return {
                    "ok": True,
                    "status": "dispatched",
                    "note": "Dispatched to the panel — verify with get_terminal_state "
                    "before claiming completion; panel state is authoritative.",
                    "host_action": {"type": tool_id, "args": args},
                }
            return {  # ask / unknown -> current behavior
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


async def _compound_plan(
    provider_id: str,
    resolved_model: str,
    api_key: str | None,
    prompt: str,
    context_snapshot: AgentContextSnapshot | None,
) -> LLMAgentPlanEvent | None:
    """The ordered plan for a COMPOUND request, or ``None`` (Track 6 #2).

    Best-effort: a single-step request, a planner failure or a timeout returns
    ``None`` and never raises.
    """
    if not classify_intent(prompt).compound:
        return None
    try:

        async def _plan_llm_call(p: str) -> str:
            return await oneshot.complete(
                provider_id,
                resolved_model,
                api_key,
                [{"role": "user", "content": p}],
                timeout=_PLANNER_TIMEOUT_SECONDS,
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
            return LLMAgentPlanEvent(goal=plan.goal, steps=steps, note=plan.note)
    except Exception:  # noqa: BLE001 — the plan is best-effort; never break a turn
        logger.debug("planner pre-pass skipped (non-fatal)", exc_info=True)
    return None


def _resolve_tool_surface(
    spec: AgentSpec, mode: str, prompt: str
) -> tuple[list[str], bool, list[str]]:
    """The turn's allow-list, whether it is read-only, and the retired tool ids.

    The allow-list is finally sent to the provider. A stored agent may still
    name a renamed tool by its old id (resolved) or a removed one (dropped, and
    returned so the caller says it once) (R15-LIFECYCLE-025).
    """
    tool_ids, retired_tools = catalog.resolve_tool_ids(spec.tools)
    # Resolve whether this turn is READ-ONLY. The collapsed "agent" mode (Track B)
    # has no Ask/Edit/Build picker — it INFERS the intent from the prompt
    # (deterministic, no LLM) and gates a READ intent to read-only tools exactly as
    # the old "Ask" mode did, so the §6.5-adjacent read-only line survives the
    # mode-collapse. Legacy "ask" stays read-only for back-compat; everything else
    # (agent-with-edit/build intent, delegate, legacy edit/build) keeps the full set.
    inferred_intent: str | None = None
    if mode == "agent":
        intent = classify_intent(prompt)
        inferred_intent = intent.intent
        # Strip writes only on a POSITIVE read cue (D-B3-3): classify_intent
        # defaults cue-less text ("I bought 10 INFY at 1500", "Remember that…")
        # to read, which removed the exact write tool the user asked for. A
        # cue-less prompt keeps the full set; data writes still stage for review.
        read_only = inferred_intent == "read" and bool(intent.signals)
    else:
        read_only = mode == "ask"
    if read_only:
        # Strip every mutating capability SERVER-SIDE so a read turn can never drive
        # the host or write the user's data — enforced here, not in the adapter, so an
        # external MCP client can't bypass it.
        #
        # Decision 4 (pre-approved): on an INFERRED read intent under the collapsed
        # "agent" mode, RETAIN a small read-safe panel allow-list (open_panel /
        # set_chart_symbol / set_chart_indicators / arrange_layout / add_to_watchlist)
        # so a read question can still GROUND itself by pulling up the relevant chart
        # / index (e.g. "how's the market" -> set_chart_symbol on SPY). Data-write
        # actions STAY stripped on a read intent (§6.5); data/search read tools were never
        # stripped (read_only=True). The legacy "ask" mode keeps the STRICT gate
        # (full strip) for back-compat — only the inferred-read path is loosened.
        keep_panel_actions = inferred_intent == "read"
        tool_ids = [
            t
            for t in tool_ids
            if catalog.is_read_only(t) is True
            or (keep_panel_actions and t in _READ_SAFE_PANEL_ACTIONS)
        ]
    return tool_ids, read_only, retired_tools


def _select_native_search(provider_id: str, model: str, model_web_search: str | None) -> bool:
    """Whether this turn rides the model's native server-side search.

    R9 (two-tier truth): on tier_a the model's native search COMPOUNDS with the
    local retrieval lane (Team B's loop cross-verifies between the channels),
    so a native-capable model rides its own search. tier_b ignores chat-model
    native search ENTIRELY — the hosted research model owns research and the
    local web_search tool stays for plain retrieval, so the chat model's
    server-side search never double-runs (or double-bills) a tier_b session.
    """
    return config.get_effective_research_tier() != config.SEARCH_TIER_B and (
        _native_search_enabled(provider_id, model_web_search, model)
    )


async def _plan_prepass(
    provider_id: str,
    mode: str,
    read_only: bool,
    model: str,
    api_key: str | None,
    prompt: str,
    context_snapshot: AgentContextSnapshot | None,
) -> LLMAgentPlanEvent | None:
    """The visible plan for this turn, or ``None`` (Track 6 #2).

    Only a non-read-only agent-mode turn on a planner-capable provider plans; a
    weak local model is skipped entirely (the loop's preamble-driven path
    stands). The plan's host-action steps come back flagged ``staged``.
    """
    if read_only or not _planner_enabled(provider_id, mode):
        return None
    return await _compound_plan(provider_id, model, api_key, prompt, context_snapshot)


async def plan_delegate_run(
    agent_id: str,
    prompt: str,
    *,
    provider: LLMProviderId | None,
    model: str | None,
    api_key: str | None,
    context_snapshot: AgentContextSnapshot | None,
) -> LLMAgentPlanEvent | None:
    """The plan a Delegate launch waits on for the user's Start (R15-AGENT-039).

    The same pre-pass a foreground turn shows, on the same capable models; a
    weak local model or a single-step request gets ``None`` and starts directly.
    """
    spec = get_agent(agent_id)
    if spec is None:
        return None
    provider_id = _resolve_provider_id(spec, provider)
    if provider_id not in _PLANNER_PROVIDERS:
        return None
    return await _compound_plan(
        provider_id, _resolve_model(spec, model), api_key, prompt, context_snapshot
    )


@dataclass
class _RunSetup:
    """A turn's per-run options, resolved once before its first round."""

    provider_id: str
    model: str
    adapter: Any
    tool_ids: list[str]
    read_only: bool
    local_tools: dict[str, LocalToolHandler]
    messages: list[LLMMessage]
    window: int | None
    #: Adapter kwargs only: everything the runtime owns is popped and scrubbed.
    opts: dict[str, Any]
    #: Retired-tool and folded-history notices, yielded before anything else.
    notices: list[LLMResearchStepEvent]


#: R15-AGENT-090: the one sentence an untraced depositary-ratio claim becomes.
RATIO_UNAVAILABLE = "The ADR-to-ordinary-share ratio is not available from this session's sources."
_NUMBER_WORDS = (
    "one", "two", "three", "four", "five", "six",
    "seven", "eight", "nine", "ten", "eleven", "twelve",
)  # fmt: skip
_NUM = r"(?:\d[\d,]*(?:\.\d+)?|" + "|".join(_NUMBER_WORDS) + ")"
_RATIO_OPERAND = r"(?:\d{1,3}|" + "|".join(_NUMBER_WORDS) + ")"
_CLAIM_TERM = re.compile(
    r"\b(?:ADRs?|ADSs?|American Depositary|depositary|conversion ratio)\b", re.IGNORECASE
)
_SOURCE_TERM = re.compile(r"\b(?:ADRs?|ADSs?|American Depositary|depositary|Repr)\b", re.IGNORECASE)
_CLAIM_NUMBERS = re.compile(
    rf"\b({_NUM})\s+(?:ordinary|equity|underlying|common)\s+shares?\b"
    rf"|\b({_RATIO_OPERAND})\s*(?::|-for-|\s+to\s+)\s*({_RATIO_OPERAND})\b",
    re.IGNORECASE,
)
_ANY_NUMBER = re.compile(rf"\b{_NUM}\b", re.IGNORECASE)
#: Without one of these, an N:M / N to M next to "ADR" is a price range or a
#: clock time, not a ratio claim.
_RATIO_CUE = re.compile(r"\b(?:ratio|represents?|equals?|each|converts?)\b|-for-", re.IGNORECASE)
#: A sentence (with its trailing whitespace) of released prose.
_SENTENCE = re.compile(r".*?(?:[.!?]\s+|\n\s*|\Z)", re.DOTALL)
#: Where held prose may be released: after a sentence end or a line break.
_SENTENCE_BOUNDARY = re.compile(r"[.!?]\s+|\n")


def _norm_number(token: str) -> str:
    token = token.lower().replace(",", "")
    return str(_NUMBER_WORDS.index(token) + 1) if token in _NUMBER_WORDS else token


def _ratio_claim_traced(sentence: str, tool_results: list[str]) -> bool:
    """False for a depositary-ratio claim no tool result carries (R15-AGENT-090).

    A sentence claims a ratio when it names a depositary term and a count of
    ordinary/underlying shares or an N:M / N-for-M / N to M ratio. It is traced
    when one tool result names a depositary term (``Repr`` covers the listing
    style "Each Repr 6 Ords") and carries every claimed number.
    ponytail: per-sentence regex; a claim split over two sentences slips past,
    and one sourced from a provider's native server-side search (never a tool
    result here) is replaced. A claim extractor if more claim types need it.
    """
    if not _CLAIM_TERM.search(sentence):
        return True
    matches = _CLAIM_NUMBERS.findall(sentence)
    if not _RATIO_CUE.search(sentence):
        matches = [m for m in matches if m[0]]  # share counts only
    claimed = {_norm_number(n) for match in matches for n in match if n}
    if not claimed:
        return True
    return any(
        _SOURCE_TERM.search(result)
        and claimed <= {_norm_number(n) for n in _ANY_NUMBER.findall(result)}
        for result in tool_results
    )


def _guard_ratio_claims(text: str, tool_results: list[str]) -> str:
    """``text`` with each untraced depositary-ratio sentence replaced by
    :data:`RATIO_UNAVAILABLE`, its surrounding whitespace kept."""
    out: list[str] = []
    for match in _SENTENCE.finditer(text):
        sentence = match.group()
        if sentence.strip() and not _ratio_claim_traced(sentence, tool_results):
            lead = sentence[: len(sentence) - len(sentence.lstrip())]
            sentence = lead + RATIO_UNAVAILABLE + sentence[len(sentence.rstrip()) :]
        out.append(sentence)
    return "".join(out)


@dataclass
class _TurnState:
    """What the rounds of one turn carry forward."""

    rounds: int = 0
    web_search_calls: int = 0  # per-run cap on the BYOK/local web_search tool (FR-081)
    native_searches: int = 0  # native server-side searches run this turn (R15-AGENT-049)
    # The turn's spend over every round (C11): None once any round is unpriced.
    turn_spend: float | None = 0.0
    # R10 (E2): the latest research execution record of THIS invoke. When the
    # model issues its own publish_brief without an ``execution`` (it almost
    # never echoes the big record), the tracked record is injected so the
    # panel's mode/depth badges always key on what actually ran.
    last_research_execution: dict[str, Any] | None = None
    # R10 (E3.3): every publish_brief tool_call_id of this turn (model-issued
    # AND synthetic) — checked against the ack ledger at end-of-stream so a
    # publish the panel never confirmed gets an honest divergence notice.
    publish_brief_calls: list[str] = field(default_factory=list)
    # Host actions this turn staged for review (awaiting_user_review), named in
    # one end-of-turn notice (R15-AGENT-033).
    staged_actions: list[LLMToolUseEvent] = field(default_factory=list)
    # Any prose streamed this turn (every round): a turn that ends with none
    # is an empty answer, never a silent success (R15-AGENT-026).
    turn_text: bool = False
    # Every tool result string of the run: the ratio-claim guard traces a
    # released sentence against them (R15-AGENT-090).
    tool_results: list[str] = field(default_factory=list)


@dataclass
class _Round:
    """One provider round: what it streamed and how it ended."""

    capped: bool
    pending_tools: list[LLMToolUseEvent] = field(default_factory=list)
    # WS8 Step 4: accumulate this round's reasoning_content (DeepSeek-reasoner
    # streams its chain-of-thought as thinking events) so it can be echoed on
    # the reconstructed assistant tool-use turn for a well-formed multi-round
    # reasoner. Empty for non-reasoner providers (no thinking events).
    reasoning_parts: list[str] = field(default_factory=list)
    streamed_text: bool = False
    round_error: bool = False
    #: The turn's terminator went out: the turn is over.
    ended: bool = False


def _prepare_run(
    spec: AgentSpec,
    prompt: str,
    context_snapshot: AgentContextSnapshot | None,
    api_key: str | None,
    provider: LLMProviderId | None,
    model: str | None,
    options: dict[str, Any] | None,
    mode: str,
    autonomy: str | None,
) -> _RunSetup:
    """Resolve the turn's provider, model, tools and messages; publish the run's
    task-local settings; pop every option the runtime owns (R15-CODE-AGENT-009)."""
    provider_id = _resolve_provider_id(spec, provider)
    resolved_model = _resolve_model(spec, model)
    opts = dict(options or {})
    history, folded = _coerce_history(opts.pop("history", None))
    tool_ids, read_only, retired_tools = _resolve_tool_surface(spec, mode, prompt)

    # Web-search tier dispatch (FR-080/081/WS5). On the NATIVE tier, ride the
    # model's own server-side search when THIS model supports it (the adapter
    # injects it via the `web_search` kwarg, capped at _WEB_SEARCH_CAP) and
    # WITHHOLD the BYOK/local `web_search` tool so search isn't double-run.
    # The provider-level native provider (anthropic) always qualifies; Groq
    # (Compound only) and Gemini (Gemini 3 alongside function tools) are
    # per-MODEL (R15-AGENT-005); OpenAI is per-MODEL (chat-completions serves
    # native search only on its *-search-preview models — a `web_search` tools
    # entry 400s elsewhere), and OpenRouter is gated PER-MODEL on the resolved model's
    # `web_search` capability ("native"), threaded from the frontend catalog as
    # `modelWebSearch` (keyless — no network on the hot path). Otherwise (BYOK/
    # local tier, a non-native provider, or an OpenRouter model that is plugin-/
    # none-capable) keep the `web_search` tool — it routes to Exa/SearXNG, or
    # returns an honest "unavailable" when nothing is configured (FR-082; never
    # fabricates).
    model_web_search = opts.pop("modelWebSearch", None)
    if isinstance(model_web_search, str):
        model_web_search = model_web_search.strip().lower() or None
    else:
        model_web_search = None
    # Publish for the run so the tier_a deep-research lane can gate the B4
    # dual-channel cross-verify on the SAME capability truth (task-local).
    config.set_request_model_web_search(model_web_search)
    if _select_native_search(provider_id, resolved_model, model_web_search):
        opts["web_search"] = True
        opts["web_search_max_uses"] = _WEB_SEARCH_CAP
        tool_ids = [t for t in tool_ids if t != "web_search"]

    local_tools = _build_local_tools(context_snapshot, autonomy)
    messages = _compose_messages(spec, prompt, context_snapshot, history)
    notices: list[LLMResearchStepEvent] = []
    if retired_tools:
        logger.warning("agent %s names retired tool(s): %s", spec.id, ", ".join(retired_tools))
        notices.append(
            LLMResearchStepEvent(
                tool_call_id="",
                tool=RETIRED_TOOLS_NOTICE_TOOL,
                step_kind=NOTICE_STEP_KIND,
                detail=f"Tool {', '.join(retired_tools)} is no longer available; "
                "this agent runs without it.",
                status="error",
            )
        )
    if folded:
        notices.append(
            LLMResearchStepEvent(
                tool_call_id="",
                tool=HISTORY_NOTICE_TOOL,
                step_kind=NOTICE_STEP_KIND,
                detail=f"Older turns summarised: the {folded} earliest messages of this "
                "thread were folded into a summary of your asks, tool steps and failures.",
                status="ok",
            )
        )
    adapter = get_provider(provider_id)
    # Context admission (R15-AGENT-008): only a window-bound lane subsets tools
    # and elides old results; hosted lanes (no window) send the full set. The
    # window is an optional capability: an adapter that declares none has none.
    context_window = getattr(adapter, "context_window", None)
    window = context_window(resolved_model) if context_window else None
    if window:
        tool_ids = _window_tool_subset(tool_ids, messages, window)
    # ask_user belongs to the Delegate MODE, not to an agent's allow-list
    # (R15-CODE-AGENT-011): every Delegate run can pause for the user (its
    # driver parks the run on the call), on every lane; a live turn asks in
    # prose, so it is never offered there.
    tool_ids = [t for t in tool_ids if t != ASK_USER_TOOL]
    if mode == "delegate":
        tool_ids.append(ASK_USER_TOOL)

    # Publish the active LLM creds for the run so the in-loop research tool's deep
    # path can call the SAME model the user is talking to. Task-local (each request
    # is its own asyncio task with a copied context), so it does not leak across
    # requests; the key stays process-memory-only.
    config.set_request_llm_creds(provider_id, resolved_model, api_key)

    # Publish the user's selected deep-research engine (Track 5) so the research
    # tool's deep path defaults to it without the model passing a backend arg.
    # Task-local like the creds above.
    dr_backend = opts.pop("deepResearchBackend", None)
    config.set_request_deep_research(
        dr_backend.strip().lower() if isinstance(dr_backend, str) and dr_backend.strip() else None,
    )
    # R7: the composer's depth slider rides `options.research_depth`
    # (normal|deep|ultra). Popped so it never leaks into adapter kwargs
    # (OpenAI-shaped clients TypeError on unknown kwargs) and published as the
    # run's DEFAULT research depth — an explicit model-passed depth still wins.
    # ``depth`` is a TOLERANT ALIAS (a composer/older-client spelling): pop it
    # too so it can never ride ``**opts`` into the SDK and crash the whole round
    # ("AsyncCompletions.create() got an unexpected keyword argument depth"); the
    # explicit ``research_depth`` wins when both are present.
    req_depth = opts.pop("research_depth", None)
    depth_alias = opts.pop("depth", None)
    effective_depth = req_depth if isinstance(req_depth, str) and req_depth.strip() else depth_alias
    config.set_request_research_depth(
        effective_depth.strip().lower()
        if isinstance(effective_depth, str) and effective_depth.strip()
        else None,
    )
    return _RunSetup(
        provider_id=provider_id,
        model=resolved_model,
        adapter=adapter,
        tool_ids=tool_ids,
        read_only=read_only,
        local_tools=local_tools,
        messages=messages,
        window=window,
        # The runtime popped everything it owns above; only adapter kwargs ride
        # ``**opts`` into stream_chat (the one allowlist, R15-CODE-AGENT-005).
        opts=scrub_adapter_options(opts),
        notices=notices,
    )


def _open_round(run: _RunSetup, turn: _TurnState) -> _Round:
    """Ready the messages and search budget for the turn's next provider round."""
    # The capped final round (D-B3-6, R15-AGENT-003): tools stay offered
    # (Anthropic rejects a tool_use/tool_result history with no `tools`),
    # but the model is told to answer now, and any tool call it still makes
    # is dropped — never yielded to the UI (AUTO would apply it), never
    # dispatched, never recorded — so announced == dispatched.
    capped = turn.rounds >= _MAX_TOOL_ROUNDS
    if capped:
        run.messages.append(LLMMessage(role="system", content=_CAPPED_ROUND_NOTE))
    if run.window:
        _fit_to_window(run.messages, run.tool_ids, run.window)
    if run.opts.get("web_search"):
        if turn.native_searches >= _WEB_SEARCH_CAP:
            run.opts.pop("web_search")
            run.opts.pop("web_search_max_uses", None)
        else:
            run.opts["web_search_max_uses"] = _WEB_SEARCH_CAP - turn.native_searches
    return _Round(capped=capped)


async def _consume_round(
    stream: AsyncIterator[Any],
    run: _RunSetup,
    turn: _TurnState,
    rnd: _Round,
    autonomy: str | None,
    on_round_usage: Callable[[LLMUsage, str, str], bool] | None,
) -> AsyncIterator[LLMStreamEvent]:
    """Relay one provider round, collecting its tool calls into ``rnd``.

    Ends the turn (``rnd.ended``) on a final terminator, a budget halt or a
    stream that closed without one; otherwise the round's tool calls are
    pending for :func:`_dispatch_round`.

    Prose is held and released a sentence at a time, each sentence checked by
    :func:`_guard_ratio_claims` (R15-AGENT-090); what is held is released
    before any other event but a heartbeat, so the relay order is kept.
    """
    held: list[str] = []  # the provider's delta texts not yet released

    def _release(chunks: list[str]) -> list[LLMDeltaEvent]:
        text = "".join(chunks)
        guarded = _guard_ratio_claims(text, turn.tool_results)
        if guarded.strip():
            rnd.streamed_text = True
            turn.turn_text = True
        # Untouched prose keeps the provider's chunking.
        return [LLMDeltaEvent(text=c) for c in (chunks if guarded == text else [guarded]) if c]

    async for event in stream:
        if isinstance(event, LLMDeltaEvent):
            held.append(event.text)
            text = "".join(held)
            cut = max((m.end() for m in _SENTENCE_BOUNDARY.finditer(text)), default=0)
            if cut:
                # What was held had no boundary, so a new one ends in the newest chunk.
                newest = held.pop()
                split = len(newest) - (len(text) - cut)
                for delta in _release([*held, newest[:split]]):
                    yield delta
                held = [newest[split:]]
            continue
        if held and not isinstance(event, LLMHeartbeatEvent):
            for delta in _release(held):
                yield delta
            held = []
        if isinstance(event, LLMThinkingEvent):
            rnd.reasoning_parts.append(event.text)
            yield event
            continue
        if isinstance(event, LLMToolUseEvent):
            if rnd.capped:
                continue
            # The runtime owns tool-call identity (R15-AGENT-046, D-B9-5):
            # provider ids are never trusted (Ollama sends '', Gemini reuses
            # `name_index` in every stream, so a late ack from an earlier turn
            # would ground this one). Every call gets a fresh id before the
            # tool-use turn, the tool result or any derived id uses it.
            event.tool_call_id = f"call_{uuid.uuid4().hex}"
            _normalise_tool_args(event)
            if event.name in _host_action_ids() and INVALID_ARGS_SENTINEL in event.input:
                # Never hand the UI a host action with invalid args (it would
                # stage or AUTO-apply a coerced change). It still dispatches,
                # so the model gets the {ok: false, error} result to act on.
                rnd.pending_tools.append(event)
                continue
            # R10 (E2): a model-issued publish_brief without an execution
            # record inherits the run's tracked record before anything
            # downstream (frontend, dispatch) sees the event.
            if (
                event.name == "publish_brief"
                and isinstance(event.input, dict)
                and "execution" not in event.input
                and turn.last_research_execution is not None
            ):
                event.input["execution"] = turn.last_research_execution
            if event.name == "publish_brief":
                turn.publish_brief_calls.append(event.tool_call_id)
            rnd.pending_tools.append(event)
            yield event
            continue
        if isinstance(event, LLMDoneEvent):
            if event.usage is not None:
                turn.native_searches += event.usage.web_search_requests or 0
            round_spend = budget_guard.spend_usd(run.provider_id, run.model, event.usage)
            turn.turn_spend = (
                None
                if round_spend is None or turn.turn_spend is None
                else turn.turn_spend + round_spend
            )
            event.spend_usd = None if turn.turn_spend is None else round(turn.turn_spend, 6)
            # Per-round cost signal (FR-026): fire BEFORE we either swallow
            # this terminator (mid-run) or yield it (final), so the budget
            # guard sees every round's usage, not just the last one.
            may_continue = (
                on_round_usage(event.usage or LLMUsage(), run.model, run.provider_id)
                if on_round_usage is not None
                else True
            )
            if rnd.pending_tools and not may_continue:
                yield LLMResearchStepEvent(
                    tool_call_id="",
                    tool=HALT_NOTICE_TOOL,
                    step_kind=NOTICE_STEP_KIND,
                    detail=f"Stopped before running {len(rnd.pending_tools)} tool call(s).",
                    status="error",
                )
                rnd.ended = True
                yield event
                return
            # If tools fired this round and we have budget left, swallow the
            # per-round terminator and loop. Otherwise this is the final
            # terminator and the SSE consumer needs it.
            if rnd.pending_tools and turn.rounds < _MAX_TOOL_ROUNDS:
                return
            async for final in _finish_turn(event, run, turn, rnd, autonomy):
                yield final
            return
        if isinstance(event, LLMErrorEvent):
            rnd.round_error = True
        yield event
    for delta in _release(held):
        yield delta
    # Provider closed without a terminator — emit one so the SSE framing stays
    # well-formed for the consumer.
    async for final in _finish_unterminated(run, turn, rnd, autonomy):
        yield final


async def _finish_turn(
    done: LLMDoneEvent,
    run: _RunSetup,
    turn: _TurnState,
    rnd: _Round,
    autonomy: str | None,
) -> AsyncIterator[LLMStreamEvent]:
    """The end-of-turn notices, errors and terminator after a final ``done``."""
    rnd.ended = True
    if rnd.capped and not rnd.streamed_text:
        yield LLMDeltaEvent(text=_CAPPED_ROUND_CLOSE)
        turn.turn_text = True
    if is_length_finish(done.finish_reason):
        yield LLMResearchStepEvent(
            tool_call_id="",
            tool="runtime",
            step_kind=NOTICE_STEP_KIND,
            detail=_LENGTH_NOTICE,
            status="error",
        )
    for notice in await _end_of_turn_notices(
        autonomy, turn.publish_brief_calls, turn.staged_actions
    ):
        yield notice
    # R11 (V2 evidence): a provider content-filter finish leaves the user with
    # an unexplained refusal (DeepSeek V4 Flash answers host-action asks with a
    # foreign-language refusal + finish_reason "content_filter" and zero tool
    # calls — live capture in verification/r11/v2-redrive/). Say so honestly.
    if done.finish_reason == "content_filter":
        yield LLMErrorEvent(
            message="The model declined this request — its provider flagged the content.",
            action="Rephrase the request, or switch the composer to a different model.",
            detail=f"finish_reason=content_filter from {run.model}",
            code="content_filter",
        )
    elif not turn.turn_text:
        yield _empty_response_error(run.model)
    done.context_window = run.window
    yield done


async def _finish_unterminated(
    run: _RunSetup,
    turn: _TurnState,
    rnd: _Round,
    autonomy: str | None,
) -> AsyncIterator[LLMStreamEvent]:
    """End a turn whose provider closed the round without a ``done``."""
    rnd.ended = True
    closed_capped = rnd.capped and not rnd.streamed_text
    if closed_capped:
        yield LLMDeltaEvent(text=_CAPPED_ROUND_CLOSE)
    for notice in await _end_of_turn_notices(
        autonomy, turn.publish_brief_calls, turn.staged_actions
    ):
        yield notice
    # A provider that closed without a terminator and without saying why did
    # not finish: say so, with Retry (R15-AGENT-026).
    if not rnd.round_error and not closed_capped:
        yield _unfinished_round_error(rnd.streamed_text, run.model)
    yield LLMDoneEvent()


async def _dispatch_round(
    run: _RunSetup,
    turn: _TurnState,
    rnd: _Round,
    autonomy: str | None,
    on_tool_result: Callable[[LLMToolUseEvent, str], None] | None,
) -> AsyncIterator[LLMStreamEvent]:
    """Dispatch the round's tool calls and append their turns to the messages.

    Yields each tool's live steps, its ``tool_result`` outcome and any synthetic
    brief/backtest event; under AUTO, each dispatched host action's result is
    then rewritten from the panel's real ack.
    """
    # Reconstruct the assistant tool-use turn FIRST so the provider can
    # associate each tool result with its call: Anthropic requires the
    # tool_use block to precede the tool_result; OpenAI requires the
    # assistant `tool_calls` array. Carried in `metadata` (no contract
    # change to LLMMessage); each adapter rebuilds its native shape.
    #
    # WS8 Step 4 (deepseek-reasoner guard — LOW-RISK ECHO default):
    # deepseek-reasoner returns its chain-of-thought in a separate
    # ``reasoning_content`` field, and a multi-round tool turn is better
    # formed when the assistant turn that issued the tool call carries that
    # reasoning rather than empty content. We ECHO the round's reasoning back
    # on the reconstructed turn for reasoner models ONLY; non-reasoner
    # providers stream no thinking events so this stays content="" and their
    # behaviour is unchanged. NEEDS-MANUAL-CHECK: the echo-vs-steer-to-
    # deepseek-chat choice is UNVERIFIED here — it needs a live
    # deepseek-reasoner MULTI-ROUND repro (cannot run in this environment).
    # Echo is the conservative default (additive, reasoner-gated).
    reconstructed_content = ""
    if "reasoner" in run.model.lower() and rnd.reasoning_parts:
        reconstructed_content = "".join(rnd.reasoning_parts)
    run.messages.append(
        LLMMessage(
            role="assistant",
            content=reconstructed_content,
            metadata={
                "tool_calls": [
                    {
                        "id": tc.tool_call_id,
                        "name": tc.name,
                        "input": tc.input,
                        # Echoed back by the adapter that set it (Gemini's
                        # thought signature, R15-AGENT-006).
                        **({"provider_meta": tc.provider_meta} if tc.provider_meta else {}),
                    }
                    for tc in rnd.pending_tools
                ]
            },
        )
    )
    # Dispatch every pending tool and append tool-result messages keyed on the
    # call ids.
    # E3.3 read-back (R13 JARVIS 1b): (tool_call, tool_result_msg) pairs for
    # this round's NON-ORDER host actions dispatched under AUTO autonomy —
    # rewritten from the panel's real ack after the dispatch loop so the
    # model's next narration is grounded, not the optimistic "dispatched".
    host_action_readbacks: list[tuple[LLMToolUseEvent, LLMMessage]] = []
    _host_ids = _host_action_ids()
    for tool_call in rnd.pending_tools:
        if tool_call.name == "web_search":
            # FR-081: bound per-search billing per run.
            turn.web_search_calls += 1
        if tool_call.name == "web_search" and turn.web_search_calls > _WEB_SEARCH_CAP:
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
            # (Track A — a long deep research round is no longer silent), then
            # take the JSON result string from the terminal _ToolDone.
            result_str = ""
            async for item in _dispatch_tool_with_progress(tool_call, run.local_tools):
                if isinstance(item, _ToolDone):
                    result_str = item.result
                else:
                    yield item
        tool_result_msg = LLMMessage(
            role="tool",
            # The model reads its own view (money as displays); the raw
            # result_str still feeds auto-publish and the execution record.
            content=_model_facing_content(tool_call.name, result_str, run.window),
            tool_call_id=tool_call.tool_call_id,
            # Carry the tool NAME alongside the id: Gemini pairs a
            # function_response to its call by name (not id), so a
            # tool-result message with no name serialises name="" and
            # breaks Gemini multi-round tool use. Anthropic/OpenAI key by
            # tool_call_id and ignore this. (FR-024 / closes the §4 break.)
            metadata={"name": tool_call.name},
        )
        run.messages.append(tool_result_msg)
        turn.tool_results.append(result_str)
        yield _tool_result_event(tool_call, result_str)
        if on_tool_result is not None:
            on_tool_result(tool_call, result_str)
        if tool_call.name in _host_ids and _result_status(result_str) == "awaiting_user_review":
            turn.staged_actions.append(tool_call)
        # Queue a host action dispatched under AUTO for the grounded
        # read-back below. An invalid-args call was never dispatched to the
        # panel, so its {ok: false, error} result stands as is.
        if (
            autonomy == "auto"
            and tool_call.name in _host_ids
            and INVALID_ARGS_SENTINEL not in tool_call.input
        ):
            host_action_readbacks.append((tool_call, tool_result_msg))
        # Auto-publish the brief deterministically (Track 3): the full brief
        # is in result_str but only the model sees it. Emit a synthetic
        # publish_brief so the panel ALWAYS renders — even when a weak model
        # never calls it — riding the existing review/AUTO gate. The model is
        # told (in its prompt) it need not publish; a duplicate is idempotent.
        if tool_call.name in _RESEARCH_TOOLS:
            try:
                _research_payload = json.loads(result_str)
            except (json.JSONDecodeError, ValueError, TypeError):
                _research_payload = None
            if isinstance(_research_payload, dict) and isinstance(
                _research_payload.get("execution"), dict
            ):
                turn.last_research_execution = _research_payload["execution"]
            auto_brief = _auto_publish_event(tool_call, result_str)
            if auto_brief is not None:
                turn.publish_brief_calls.append(auto_brief.tool_call_id)
                yield auto_brief
        # Only where this turn may drive panels (a strict read turn may not).
        if tool_call.name == "run_custom_backtest" and "open_panel" in run.tool_ids:
            auto_open = _auto_open_backtest_event(tool_call, result_str)
            if auto_open is not None:
                yield auto_open
    # Grounded host-action read-back (R13 JARVIS 1b): ONE grace-bounded poll
    # of the ack ledger for this round's dispatched host actions, then
    # rewrite each tool-result from the panel's REAL outcome (applied /
    # kept_previous / failed / not-yet-confirmed) so the model's NEXT stream
    # narrates the ground truth instead of the optimistic "dispatched".
    if host_action_readbacks:
        await _await_host_action_acks([tc.tool_call_id for tc, _ in host_action_readbacks])
        for tc, msg in host_action_readbacks:
            # Each ack is consumed by its last reader: a publish's is read
            # again by the end-of-turn divergence check (R15-AGENT-046).
            read = (
                action_ledger.get
                if tc.tool_call_id in turn.publish_brief_calls
                else action_ledger.take
            )
            msg.content = _grounded_host_action_result(tc, read(tc.tool_call_id))


async def invoke_agent(
    agent_id: str,
    prompt: str,
    context_snapshot: AgentContextSnapshot | None = None,
    api_key: str | None = None,
    provider: LLMProviderId | None = None,
    model: str | None = None,
    options: dict[str, Any] | None = None,
    mode: str = "ask",
    autonomy: str | None = None,
    on_round_usage: Callable[[LLMUsage, str, str], bool] | None = None,
    on_tool_result: Callable[[LLMToolUseEvent, str], None] | None = None,
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
    it is called with ``(usage, model, provider)`` — the RESOLVED model and
    provider, so a provider-less launch is priced at its real rate
    (R15-AGENT-074) — at EVERY round's ``done``, and returns whether the loop may
    continue. ``False`` on a round with tool calls stops the turn BEFORE they are
    dispatched: a :data:`HALT_NOTICE_TOOL` notice and the round's terminator are
    yielded and nothing else is sent (R15-AGENT-037). A round that ended with a
    final answer finishes normally whatever it returns.

    ``on_tool_result`` is called with ``(tool_call, result_str)`` after each
    dispatched tool, so a Delegate run can checkpoint the step.
    """
    spec = get_agent(agent_id)
    if spec is None:
        yield LLMErrorEvent(message=f"unknown agent: {agent_id!r}")
        yield LLMDoneEvent()
        return
    run = _prepare_run(
        spec, prompt, context_snapshot, api_key, provider, model, options, mode, autonomy
    )
    for notice in run.notices:
        yield notice

    # Visible plan-then-execute pre-pass (Track 6 #2): for a COMPOUND request on
    # a capable model, surface the ordered plan up front with its host-action
    # steps pre-staged into the diff/accept gate. ADVISORY only: the tool loop
    # below still drives execution; this never blocks, never raises, and on a
    # weak local model it is skipped entirely.
    plan_event = await _plan_prepass(
        run.provider_id, mode, run.read_only, run.model, api_key, prompt, context_snapshot
    )
    if plan_event is not None:
        yield plan_event

    turn = _TurnState()
    idle = LOCAL_IDLE_TIMEOUT_S if run.provider_id == "ollama" else IDLE_TIMEOUT_S
    while True:
        rnd = _open_round(run, turn)
        stream = _relay_provider(
            run.adapter.stream_chat(
                messages=run.messages,
                model=run.model,
                api_key=api_key,
                tool_ids=run.tool_ids,
                **run.opts,
            ),
            idle,
        )
        # aclosing: a consumer's aclose() reaches each phase at once, as it
        # did when the phases were inline.
        async with contextlib.aclosing(
            _consume_round(stream, run, turn, rnd, autonomy, on_round_usage)
        ) as events:
            async for event in events:
                yield event
        if rnd.ended:
            return
        async with contextlib.aclosing(
            _dispatch_round(run, turn, rnd, autonomy, on_tool_result)
        ) as events:
            async for event in events:
                yield event
        # At the cap the next iteration is the capped final round (see
        # _open_round): it streams the answer and exits on its terminator.
        turn.rounds += 1
