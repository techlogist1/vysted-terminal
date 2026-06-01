"""Agent tool — ``deep_research`` (multi-round, budgeted research loop).

Drives a bounded, multi-researcher deep-research run and returns a structured
:class:`~services.research.deep.ResearchBrief` as a dict. Two backends:

- **native** (default) — runs the built-in deep-research loop
  (:func:`services.research.deep.run_deep_research`) against the SAME model the
  user is talking to (via :func:`config.get_llm_creds` + the one-shot
  :func:`services.llm.oneshot.complete` seam), metered by a
  :class:`~services.budget_guard.BudgetGuard`. No extra key, no extra cost.
- **perplexity** — OPT-IN, PAID. Only runs when the user has explicitly
  configured a Perplexity key; this handler NEVER auto-selects Perplexity. With
  no key it returns an honest "needs a key" message naming exactly what unlocks
  it.

The research service is built in parallel; everything from it is imported lazily
inside the call so the module imports cleanly before the service lands and the
tests can monkeypatch each seam in place.
"""

from __future__ import annotations

from typing import Any

from services.agent_tools import register_tool

#: How many researcher agents the native loop may fan out to per round. Bounds
#: the BudgetGuard step ceiling alongside ``rounds`` below.
_MAX_RESEARCHERS = 3

_PERPLEXITY_NEEDS_KEY = (
    "Perplexity deep research needs an API key (opt-in, paid). Add it in "
    "Settings, or use the built-in deep research."
)
_TONGYI_NEEDS_KEY = (
    "Tongyi-DeepResearch runs remotely via OpenRouter (it's a 30B-A3B model — too "
    "large to host on this device). Add an OpenRouter key in Settings, or use the "
    "built-in deep research."
)
_NO_MODEL = "No model configured for deep research."


def _clamp(value: Any, lo: int, hi: int, default: int) -> int:
    """Coerce ``value`` to an int in ``[lo, hi]``, falling back to ``default``."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


async def _run_perplexity(query: str, key: str | None) -> dict[str, Any]:
    """Run the opt-in paid Perplexity backend, or honest-fail without a key.

    NEVER auto-selects Perplexity — the caller already chose ``backend=perplexity``
    explicitly. Without a configured key, returns the "needs a key" message.
    """
    import config
    from services.research import perplexity

    api_key = key or None
    if not api_key:
        creds = config.get_llm_creds()
        # Only reuse the active key if the user is actually on Perplexity.
        if creds is not None and creds[0] == "perplexity":
            api_key = creds[2]

    if not perplexity.is_configured(api_key):
        return {"ok": False, "message": _PERPLEXITY_NEEDS_KEY}

    backend = perplexity.PerplexityDeepBackend(api_key)
    brief = await backend.research(query, region=config.get_region())
    out = brief.to_dict()
    out["ok"] = True
    out.setdefault("cost_estimate_usd", perplexity.estimate_cost_usd(query))
    out["backend"] = "perplexity"
    return out


async def _run_tongyi(query: str, key: str | None, rounds: int, wall: int) -> dict[str, Any]:
    """Run the built-in deep loop with its LLM bound to OpenRouter's Tongyi model.

    Reuses :func:`deep.run_deep_research` (so the live step-log still streams to the
    activity surface — Track A) but drives plan/synthesis through OpenRouter's
    Tongyi-DeepResearch model — runtime-probed, with a live Qwen-A3B fallback
    (Track C / FINDINGS §2.4). OPT-IN + BYOK: needs an OpenRouter key (reused from
    the active creds when the user is already on OpenRouter), never auto-selected.
    """
    import config
    from services.budget_guard import BudgetGuard
    from services.llm import oneshot
    from services.research import deep, tongyi

    api_key = key or None
    if not api_key:
        creds = config.get_llm_creds()
        # Reuse the active key only when the user is already talking via OpenRouter.
        if creds is not None and creds[0] == "openrouter":
            api_key = creds[2]
    if not tongyi.is_configured(api_key):
        return {"ok": False, "message": _TONGYI_NEEDS_KEY}

    model = await tongyi.resolve_model(api_key)  # probe Tongyi slug → Qwen-A3B fallback

    from services import agent_tools

    async def llm_call(messages: list[dict[str, Any]]) -> str:
        return await oneshot.complete("openrouter", model, api_key, messages)

    budget = BudgetGuard(
        max_steps=rounds * (_MAX_RESEARCHERS + 2),
        max_wall_seconds=wall,
    )
    brief = await deep.run_deep_research(
        query,
        region=config.get_region(),
        tool_call=agent_tools.invoke_tool,
        llm_call=llm_call,
        budget=budget,
        on_step=config.get_step_sink(),
        max_researchers=_MAX_RESEARCHERS,
    )
    out = brief.to_dict()
    out["ok"] = True
    out["backend"] = "tongyi"
    out["model"] = model
    out["provenance"] = f"{tongyi.PROVENANCE_NOTE} · {model}"
    out.setdefault("cost_estimate_usd", tongyi.estimate_cost_usd(query))
    return out


async def _run_native(query: str, rounds: int, wall: int) -> dict[str, Any]:
    """Run the built-in deep-research loop against the user's active model."""
    import config
    from services.budget_guard import BudgetGuard
    from services.llm import oneshot
    from services.research import deep

    creds = config.get_llm_creds()
    if creds is None:
        return {"ok": False, "message": _NO_MODEL}
    provider, model, key = creds

    async def llm_call(messages: list[dict[str, Any]]) -> str:
        return await oneshot.complete(provider, model, key, messages)

    from services import agent_tools

    budget = BudgetGuard(
        max_steps=rounds * (_MAX_RESEARCHERS + 2),
        max_wall_seconds=wall,
    )
    # Forward each step LIVE to the runtime's step-sink (Track A) so the agent
    # surface animates a "working" trace while this multi-second loop runs. The
    # sink is ``None`` outside an agent invocation (tests / direct calls) — the
    # loop still records every step into the returned brief regardless.
    brief = await deep.run_deep_research(
        query,
        region=config.get_region(),
        tool_call=agent_tools.invoke_tool,
        llm_call=llm_call,
        budget=budget,
        on_step=config.get_step_sink(),
        max_researchers=_MAX_RESEARCHERS,
    )
    out = brief.to_dict()
    out["ok"] = True
    out["backend"] = "native"
    return out


async def _deep_research(args: dict[str, Any]) -> dict[str, Any]:
    """Run a budgeted multi-round deep-research brief for ``query``.

    Args:
        query: What to research. Required.
        rounds: Research rounds, clamped to ``[1, 5]`` (default 3).
        wall_seconds: Wall-clock budget, clamped to ``[30, 300]`` (default 120).
        backend: ``"native"`` (default, built-in), ``"perplexity"`` (opt-in,
            paid), or ``"tongyi"`` (frontier deep-research via OpenRouter, opt-in
            — needs an OpenRouter key). The opt-in backends are never auto-selected.
        api_key: Optional key for the chosen opt-in backend (Perplexity /
            OpenRouter), when not reused from the active credentials.

    Returns the brief dict (``ok: True``) or ``{"ok": False, "message": ...}``.
    """
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {
            "ok": False,
            "message": "Deep research needs a query — tell me what to look into.",
        }
    query = query.strip()

    rounds = _clamp(args.get("rounds", 3), 1, 5, 3)
    wall = _clamp(args.get("wall_seconds", 120), 30, 300, 120)
    backend = str(args.get("backend") or "native").strip().lower()

    if backend == "perplexity":
        return await _run_perplexity(query, args.get("api_key"))
    if backend == "tongyi":
        return await _run_tongyi(query, args.get("api_key"), rounds, wall)
    return await _run_native(query, rounds, wall)


def register() -> None:
    """Register the ``deep_research`` tool in the package registry."""
    register_tool("deep_research", _deep_research)


__all__ = ["_deep_research", "register"]
