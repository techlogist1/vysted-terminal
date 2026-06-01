"""In-house intent + planning — the OpenCode fallback (FINDINGS §2.1 / §4.1).

Phase 0 ruled OpenCode out as an embedded reasoning engine: it owns the agent
loop by design and its permission gate would sit *upstream* of §6.5, inverting
the safety architecture. The verified path keeps OUR loop and adds a small,
dependency-free reasoning layer the spine supervises:

- :func:`classify_intent` — deterministic natural-language → intent
  (``read`` / ``edit`` / ``build`` / ``research``), so the agent infers what the
  user wants from plain language instead of a mode picker (Track B). No LLM, no
  network — instant, offline, and fully testable.
- :func:`decompose` — LLM-backed decomposition of a COMPOUND request ("open
  three things and research X") into an ordered step plan the existing
  diff/accept gate approves (Track B multi-step). The LLM call is injected
  (``llm_call``) so it is testable with a fake; a malformed/empty model reply
  degrades to a single research/answer step (never dead-ends — Principle VIII).

This module is intentionally free of imports from the agent loop / catalog so it
stays unit-testable and import-cheap; callers map :class:`PlanStep` actions onto
the real host-actions/tools.
"""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Intent classification (deterministic — Track B mode-collapse)
# ---------------------------------------------------------------------------

#: The inferred intents. ``read`` is the safe default (read-only, no mutation):
#: an Ask-style question. ``edit`` tweaks the current cockpit (one mutation).
#: ``build`` assembles/arranges a multi-panel workspace. ``research`` kicks off
#: the research engine (FAST/DEEP). These map onto the server-side tool gate the
#: way the old four modes did — ``read`` stays read-only.
Intent = str  # one of: "read" | "edit" | "build" | "research"

INTENTS: tuple[str, ...] = ("read", "edit", "build", "research")

# Signal phrases per intent, scored by match. Ordered most- to least-specific.
# Word-boundary regexes so "research" doesn't match inside "researcher's", etc.
_RESEARCH_SIGNALS = (
    r"\bresearch\b",
    r"\bdeep[- ]?dive\b",
    r"\bdue diligence\b",
    r"\binvestment thesis\b",
    r"\bthesis\b",
    r"\boutlook\b",
    r"\bshould i (buy|sell|invest)\b",
    r"\bbull case\b",
    r"\bbear case\b",
    r"\bcatalysts?\b",
    r"\banalyze\b",
    r"\bbrief on\b",
    r"\bwrite[- ]?up\b",
)
_BUILD_SIGNALS = (
    r"\bset ?up\b",
    r"\bbuild\b",
    r"\barrange\b",
    r"\blay ?out\b",
    r"\bcockpit\b",
    r"\bworkspace\b",
    r"\bdashboard\b",
    r"\bopen (a |the |my )?\w+ (and|,)",  # "open chart and watchlist"
    r"\bpull up\b",
    r"\bshow me (a|the|my) \w+ (and|,|next to|beside|alongside)",
    r"\bcompare\b",
    r"\bside[- ]?by[- ]?side\b",
    r"\bone .* (here|left|right|top|bottom).* (other|another|one)",
)
_EDIT_SIGNALS = (
    r"\badd\b",
    r"\bremove\b",
    r"\bchange\b",
    r"\bswitch (to|the)\b",
    r"\bset (the )?(chart|symbol|timeframe|indicator)\b",
    r"\bopen\b",
    r"\bclose\b",
    r"\bfocus\b",
    r"\bdraw\b",
    r"\bwatchlist\b",
    r"\bindicators?\b",
    r"\btimeframe\b",
)
# Read/ask cues — questions, definitions, explanations. Lowest mutation.
_READ_SIGNALS = (
    r"\bwhat('?s| is| are| was)\b",
    r"\bwhy\b",
    r"\bhow (do|does|much|many|to)\b",
    r"\bexplain\b",
    r"\bdefine\b",
    r"\btell me about\b",
    r"\bwho (is|are)\b",
    r"\bwhen (is|was|did)\b",
    r"\bsummariz",
    r"\?\s*$",
)

_SIGNAL_TABLE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("research", _RESEARCH_SIGNALS),
    ("build", _BUILD_SIGNALS),
    ("edit", _EDIT_SIGNALS),
    ("read", _READ_SIGNALS),
)

# Compound cues bump "build" — multiple distinct actions in one breath.
_COMPOUND_CUES = (
    r"\band then\b",
    r"\b, then\b",
    r"\balso\b",
    r"\bafter that\b",
    r"\bnext\b",
)
# Panel/surface nouns that, when several appear, signal a multi-panel build.
_PANEL_NOUNS = (
    "chart",
    "watchlist",
    "news",
    "portfolio",
    "screener",
    "macro",
    "earnings",
    "filings",
    "brief",
    "overview",
)


@dataclass(slots=True)
class IntentResult:
    """A classified intent + why. ``confidence`` is 0–1 (heuristic, not calibrated);
    ``signals`` lists the matched cues so a caller can explain / debug the choice.
    ``mutates`` mirrors the old mode flag — ``read`` is the only non-mutating one."""

    intent: Intent
    confidence: float
    signals: list[str] = field(default_factory=list)
    compound: bool = False

    @property
    def mutates(self) -> bool:
        return self.intent != "read"

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "confidence": round(self.confidence, 3),
            "signals": self.signals,
            "compound": self.compound,
            "mutates": self.mutates,
        }


def classify_intent(text: str, _context: dict[str, Any] | None = None) -> IntentResult:
    """Infer the user's intent from plain language — no LLM, no network.

    Scores each intent by how many of its signal phrases the text matches, with a
    most-specific-wins ordering (research > build > edit > read) on ties. A
    compound request (several panel nouns, or an "and then …" chain) is nudged to
    ``build`` so a multi-step assembly isn't mistaken for a single edit. Empty or
    cue-less text defaults to ``read`` — the safe, read-only intent.
    """
    raw = (text or "").strip()
    if not raw:
        return IntentResult("read", 0.0, [], False)
    lowered = raw.lower()

    scores: dict[str, int] = {i: 0 for i in INTENTS}
    matched: dict[str, list[str]] = {i: [] for i in INTENTS}
    for intent, patterns in _SIGNAL_TABLE:
        for pat in patterns:
            if re.search(pat, lowered):
                scores[intent] += 1
                matched[intent].append(pat)

    # Compound detection: an "and then" chain OR ≥2 distinct panel nouns.
    panel_hits = sum(1 for n in _PANEL_NOUNS if re.search(rf"\b{n}\b", lowered))
    has_chain = any(re.search(c, lowered) for c in _COMPOUND_CUES)
    compound = has_chain or panel_hits >= 2
    if compound:
        scores["build"] += 2  # a multi-surface ask is a build, not a lone edit

    # `read` is the RESIDUAL intent: an action intent (research/build/edit) with
    # ANY signal wins over read, even when the phrasing is also a question
    # ("what's the bull case?" is research, not a read). Read only wins when no
    # action intent matched at all. Ties among action intents break by the
    # most-specific ordering of the table (research > build > edit).
    order = {intent: rank for rank, (intent, _) in enumerate(_SIGNAL_TABLE)}
    action_intents = ("research", "build", "edit")
    action_best = max(action_intents, key=lambda i: (scores[i], -order[i]))
    if scores[action_best] > 0:
        best = action_best
        # Confidence among action intents that matched (ignore read cues).
        action_total = sum(scores[i] for i in action_intents) or 1
        confidence = min(0.95, 0.45 + 0.5 * (scores[best] / action_total))
        return IntentResult(best, confidence, matched[best], compound)
    if scores["read"] > 0:
        # A question/definition with no action cue — a genuine read.
        return IntentResult("read", min(0.9, 0.5 + 0.1 * scores["read"]), matched["read"], compound)
    # No cue matched at all → a bare statement: default to read.
    return IntentResult("read", 0.35, [], compound)


# ---------------------------------------------------------------------------
# Compound decomposition (LLM-backed — Track B multi-step)
# ---------------------------------------------------------------------------

#: The action vocabulary a plan step may use. Callers map these onto the real
#: host-actions / tools; kept as a documented constant so the planner has no
#: import dependency on the catalog and the prompt stays in lock-step.
PLAN_ACTIONS: tuple[str, ...] = (
    "open_panel",
    "set_chart_symbol",
    "set_chart_indicators",
    "add_to_watchlist",
    "arrange_layout",
    "research",
    "deep_research",
    "answer",
)

#: Injected one-shot completion — ``await llm_call(prompt) -> str``.
LlmCall = Callable[[str], Awaitable[str]]

_MAX_STEPS = 8


@dataclass(slots=True)
class PlanStep:
    """One ordered step in a decomposed plan. ``action`` is one of
    :data:`PLAN_ACTIONS`; ``args`` are best-effort (a caller validates against the
    real tool schema); ``rationale`` is a short human line for the activity log."""

    action: str
    args: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"action": self.action, "args": self.args, "rationale": self.rationale}


@dataclass(slots=True)
class Plan:
    """A decomposed plan for a compound request. ``ok`` is False only when the
    request was empty; an LLM failure still yields a usable single-step fallback
    (never a dead-end)."""

    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    note: str | None = None

    @property
    def ok(self) -> bool:
        return bool(self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "note": self.note,
        }


def _build_prompt(goal: str, context: dict[str, Any] | None) -> str:
    ctx = ""
    if context:
        focused = context.get("focusedSymbol") or context.get("focused_symbol")
        if focused:
            ctx = f'\nThe user is currently looking at {focused}; "this"/"it" means {focused}.'
    actions = ", ".join(PLAN_ACTIONS)
    return (
        "You are JARVIS, a finance terminal's planner. Decompose the user's request "
        "into an ordered list of concrete steps the terminal will execute. Use ONLY "
        f"these action verbs: {actions}.\n"
        "- open_panel{panel}: chart|watchlist|news|portfolio|screener|macro|earnings|brief\n"
        "- set_chart_symbol{symbol}; set_chart_indicators{indicators:[...]}\n"
        "- add_to_watchlist{symbol}; arrange_layout{pattern}: "
        "single-focus|research-cockpit|compare|macro-scan\n"
        "- research{query} (fast) or deep_research{query} (thorough); "
        "answer{} for a pure question\n"
        f"{ctx}\n"
        f'Request: "{goal}"\n\n'
        'Reply with ONLY a JSON array, each item {"action","args","rationale"}. '
        "Keep it minimal — only the steps the request actually needs, in order. "
        "No prose, no code fences."
    )


def _coerce_steps(raw: Any) -> list[PlanStep]:
    """Parse the model's JSON into validated steps; drop anything malformed."""
    steps: list[PlanStep] = []
    if not isinstance(raw, list):
        return steps
    for item in raw:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action", "")).strip()
        if action not in PLAN_ACTIONS:
            continue
        args = item.get("args")
        if not isinstance(args, dict):
            args = {}
        steps.append(PlanStep(action=action, args=args, rationale=str(item.get("rationale", ""))))
        if len(steps) >= _MAX_STEPS:
            break
    return steps


def _extract_json_array(text: str) -> Any:
    """Pull the first JSON array out of a model reply (tolerant of stray prose /
    code fences the prompt asked it to omit but a weak model may still emit)."""
    text = text.strip()
    # Strip a ```json … ``` fence if present.
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return None


async def decompose(
    goal: str,
    *,
    llm_call: LlmCall,
    context: dict[str, Any] | None = None,
) -> Plan:
    """Decompose a compound request into an ordered :class:`Plan` via the LLM.

    Robust by construction: a non-JSON / empty / malformed reply degrades to a
    single fallback step (``research`` for a research-leaning ask, else
    ``answer``) so the agent NEVER dead-ends on a planning miss (Principle VIII).
    The LLM call is injected, so this is unit-testable with a scripted fake.
    """
    goal = (goal or "").strip()
    if not goal:
        return Plan(goal="", steps=[], note="empty request")

    fallback_action = "research" if classify_intent(goal).intent == "research" else "answer"
    fallback = Plan(
        goal=goal,
        steps=[PlanStep(fallback_action, {"query": goal} if fallback_action == "research" else {})],
        note=None,
    )

    try:
        reply = await llm_call(_build_prompt(goal, context))
    except Exception as exc:  # noqa: BLE001 — planning is best-effort, never fatal
        fallback.note = f"planner unavailable ({exc}); answering directly"
        return fallback

    steps = _coerce_steps(_extract_json_array(reply or ""))
    if not steps:
        fallback.note = "planner returned no usable steps; answering directly"
        return fallback
    return Plan(goal=goal, steps=steps, note=None)


__all__ = [
    "INTENTS",
    "PLAN_ACTIONS",
    "Intent",
    "IntentResult",
    "Plan",
    "PlanStep",
    "classify_intent",
    "decompose",
]
