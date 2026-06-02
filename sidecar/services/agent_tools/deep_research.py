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

#: ``angles`` at or above this triggers Heavy mode (the expert panel). Below it,
#: the single-agent loop runs. ``_MAX_ANGLES`` caps the panel width. Kept in
#: lockstep with ``iter._MIN_ANGLES`` / ``iter._MAX_ANGLES``.
_MIN_HEAVY_ANGLES = 2
_MAX_ANGLES = 3

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


def _emit_backend_step(detail: str) -> None:
    """Surface which deep-research ENGINE actually ran, as a live research step.

    Rides the existing step-sink → ``research_step`` SSE channel (Track A) so the
    activity surface shows an honest "running on X" line — never a silent fallback
    (the Tongyi-vs-Qwen case the user must be able to see). No-ops outside an agent
    invocation (no sink wired) and never raises (a cosmetic line must not break a
    run). The ``engine`` kind renders un-truncated in :file:`ResearchActivity.tsx`.
    """
    import config

    sink = config.get_step_sink()
    if sink is None:
        return
    from services.research.models import ResearchStep

    try:
        sink(ResearchStep(kind="engine", detail=detail))
    except Exception:  # pragma: no cover — cosmetic; must never break a run
        pass


def _device_phrase() -> str:
    """``"on this NNGB device (fit-scorer RED)"`` from the live device profile.

    Sourced from :func:`hardware_fit.detect_device` so the RAM figure is correct
    on every machine (not a hardcoded "16GB"); degrades to a generic phrase if
    detection is unavailable.
    """
    try:
        from services.hardware_fit import detect_device

        ram_gib = round(detect_device().ram_bytes / (1024**3))
        return f"on this {ram_gib}GB device (fit-scorer RED)"
    except Exception:  # pragma: no cover — detection is best-effort
        return "locally (fit-scorer RED)"


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

    _emit_backend_step("Perplexity — sonar-deep-research (paid)")
    backend = perplexity.PerplexityDeepBackend(api_key)
    brief = await backend.research(query, region=config.get_region())
    out = brief.to_dict()
    out["ok"] = True
    out.setdefault("cost_estimate_usd", perplexity.estimate_cost_usd(query))
    out["backend"] = "perplexity"
    return out


async def _run_tongyi(
    query: str, key: str | None, rounds: int, wall: int, mode: str = "iter", angles: int = 1
) -> dict[str, Any]:
    """Run the built-in deep loop with its LLM bound to OpenRouter's Tongyi model.

    Reuses the shared :func:`_run_loop` (iter / heavy / single — so the live
    step-log still streams to the activity surface, Track A) but drives
    plan/synthesis through OpenRouter's
    Tongyi-DeepResearch model — runtime-probed, with a live Qwen-A3B fallback
    (Track C / FINDINGS §2.4). OPT-IN + BYOK: needs an OpenRouter key (reused from
    the active creds when the user is already on OpenRouter), never auto-selected.
    """
    import config
    from services.llm import oneshot
    from services.research import tongyi

    api_key = key or None
    if not api_key:
        creds = config.get_llm_creds()
        # Reuse the active key only when the user is already talking via OpenRouter.
        if creds is not None and creds[0] == "openrouter":
            api_key = creds[2]
    if not tongyi.is_configured(api_key):
        return {"ok": False, "message": _TONGYI_NEEDS_KEY}

    model = await tongyi.resolve_model(api_key)  # probe Tongyi slug → Qwen-A3B fallback

    # Honest engine line: name the model actually used and, when the dedicated
    # Tongyi slug isn't routing, say WHY (device too small + slug unrouted) so the
    # fallback is never silent.
    if model == tongyi.TONGYI_SLUG:
        _emit_backend_step(f"Tongyi-DeepResearch-30B-A3B via OpenRouter ({model})")
    else:
        _emit_backend_step(
            f"{model} (fallback) — Tongyi-DeepResearch-30B-A3B can't host "
            f"{_device_phrase()} and OpenRouter isn't routing the "
            f"{tongyi.TONGYI_SLUG} slug yet"
        )

    async def llm_call(messages: list[dict[str, Any]]) -> str:
        return await oneshot.complete("openrouter", model, api_key, messages)

    brief = await _run_loop(
        mode=mode, angles=angles, query=query, llm_call=llm_call, rounds=rounds, wall=wall
    )
    out = brief.to_dict()
    out["ok"] = True
    out["backend"] = "tongyi"
    out["model"] = model
    out["mode"] = "heavy" if angles >= _MIN_HEAVY_ANGLES else mode
    out["provenance"] = f"{tongyi.PROVENANCE_NOTE} · {model}"
    out.setdefault("cost_estimate_usd", tongyi.estimate_cost_usd(query))
    return out


async def _run_loop(
    *,
    mode: str,
    angles: int,
    query: str,
    llm_call: Any,
    rounds: int,
    wall: int,
) -> Any:
    """Pick + run the research loop, returning a ``ResearchBrief``.

    - ``angles >= 2`` → Heavy mode: an expert PANEL of parallel iter explorers +
      a synthesis agent (test-time scaling).
    - ``mode == "iter"`` (default) → the IterResearch loop: a central evolving
      report + per-round workspace reconstruction (no context bloat).
    - ``mode == "single"`` → the legacy single-pass loop (explicit fallback).

    The iter/heavy loops are designed never to raise (budget breach →
    abort→synthesize); a belt-and-suspenders ``except`` still drops to the proven
    single-pass ``run_deep_research`` so the default path can never error out.
    Budget scales with the angle fan-out so the panel stays inside one ceiling.
    """
    import config
    from services import agent_tools
    from services.budget_guard import BudgetGuard
    from services.research import deep
    from services.research import iter as iter_research

    step_factor = angles if angles >= _MIN_HEAVY_ANGLES else 1
    budget = BudgetGuard(
        max_steps=step_factor * rounds * (_MAX_RESEARCHERS + 2),
        max_wall_seconds=wall,
    )
    common = {
        "region": config.get_region(),
        "tool_call": agent_tools.invoke_tool,
        "llm_call": llm_call,
        "budget": budget,
        # Forward each step LIVE to the runtime's step-sink (Track A) so the agent
        # surface animates a "working" trace — including the parallel angle
        # exploration in Heavy mode. ``None`` outside an agent invocation.
        "on_step": config.get_step_sink(),
        "max_researchers": _MAX_RESEARCHERS,
    }
    if angles >= _MIN_HEAVY_ANGLES:
        return await iter_research.run_heavy_research(query, angles=angles, **common)
    if mode == "single":
        return await deep.run_deep_research(query, **common)
    try:
        return await iter_research.run_iter_research(query, **common)
    except Exception:  # pragma: no cover — iter never raises; fall back regardless
        return await deep.run_deep_research(query, **common)


def _engine_label(provider: str, model: str, mode: str, angles: int) -> str:
    """Honest engine line naming the loop that actually ran."""
    if angles >= _MIN_HEAVY_ANGLES:
        return f"Your active model — {provider}/{model} · Heavy mode ({angles} parallel angles)"
    if mode == "single":
        return f"Your active model — {provider}/{model} · single-pass"
    return f"Your active model — {provider}/{model} · IterResearch (evolving report)"


async def _run_native(query: str, rounds: int, wall: int, mode: str, angles: int) -> dict[str, Any]:
    """Run the built-in deep-research loop against the user's active model."""
    import config
    from services.llm import oneshot

    creds = config.get_llm_creds()
    if creds is None:
        return {"ok": False, "message": _NO_MODEL}
    provider, model, key = creds

    _emit_backend_step(_engine_label(provider, model, mode, angles))

    async def llm_call(messages: list[dict[str, Any]]) -> str:
        return await oneshot.complete(provider, model, key, messages)

    brief = await _run_loop(
        mode=mode, angles=angles, query=query, llm_call=llm_call, rounds=rounds, wall=wall
    )
    out = brief.to_dict()
    out["ok"] = True
    out["backend"] = "native"
    out["mode"] = "heavy" if angles >= _MIN_HEAVY_ANGLES else mode
    return out


async def _deep_research(args: dict[str, Any]) -> dict[str, Any]:
    """Run a budgeted multi-round deep-research brief for ``query``.

    Args:
        query: What to research. Required.
        rounds: Research rounds, clamped to ``[1, 5]`` (default 3).
        wall_seconds: Wall-clock budget, clamped to ``[30, 300]`` (default 120).
        mode: ``"iter"`` (default) runs the IterResearch loop — a central evolving
            report + per-round workspace reconstruction; ``"single"`` runs the
            legacy single-pass loop.
        angles: ``1`` (default) runs one agent; ``2``–``3`` runs Heavy mode — an
            expert PANEL of that many parallel research angles synthesised into one
            brief (more cost, deeper coverage).
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
    mode = str(args.get("mode") or "iter").strip().lower()
    if mode not in ("iter", "single"):
        mode = "iter"
    angles = _clamp(args.get("angles", 1), 1, _MAX_ANGLES, 1)
    # ``heavy: true`` is an ergonomic alias for the default panel width.
    if args.get("heavy") is True and angles < _MIN_HEAVY_ANGLES:
        angles = _MAX_ANGLES
    backend = str(args.get("backend") or "native").strip().lower()

    if backend == "perplexity":
        return await _run_perplexity(query, args.get("api_key"))
    if backend == "tongyi":
        return await _run_tongyi(query, args.get("api_key"), rounds, wall, mode, angles)
    return await _run_native(query, rounds, wall, mode, angles)


def register() -> None:
    """Register the ``deep_research`` tool in the package registry."""
    register_tool("deep_research", _deep_research)


__all__ = ["_deep_research", "register"]
