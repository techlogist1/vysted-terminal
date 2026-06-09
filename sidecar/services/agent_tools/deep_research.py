"""Deep-research engine — the DEEP/HEAVY half of the ONE ``research`` capability.

This module is NO LONGER a registered agent tool. After the R4 research collapse
(FR-115 / SC-028) there is exactly ONE user-facing + model-facing research
capability — ``research`` (see :mod:`services.agent_tools.research`) — with depth
as an INTERNAL escalation arg (``quick`` | ``deep`` | ``heavy``). This module
supplies the deep/heavy engine behind ``depth in {"deep", "heavy"}`` via
:func:`run_deep_brief`; the ``research`` handler calls it directly. There is no
second tool name, no second catalog capability, and no user-visible ``/deep``.

Three backends:

- **native** (default) — runs the built-in deep-research loop against the SAME
  model the user is talking to (via :func:`config.get_llm_creds` + the one-shot
  :func:`services.llm.oneshot.complete` seam), metered by a
  :class:`~services.budget_guard.BudgetGuard`. No extra key, no extra cost.
- **perplexity** — OPT-IN-PER-RUN, PAID. Only runs when the caller EXPLICITLY
  passes ``backend="perplexity"`` AND the user has configured a Perplexity key;
  it is NEVER auto-selected (the catalog default is ``native`` and the Settings
  ContextVar only ever resolves to ``native``/``perplexity`` on an explicit user
  opt-in). With no key it returns an honest "needs a key" message.
- **sonar** — OPT-IN-PER-RUN, PAID (R7 Component 3): the SAME sonar family
  routed through OpenRouter on the user's OpenRouter BYOK key
  (:mod:`services.research.sonar`) — one key unlocks both hosted search and the
  one-call research lane. Same never-auto-selected guarantee; the key rides the
  request only (``config.get_openrouter_search_key()`` / explicit ``api_key``).

One deep LOOP (S-9): :mod:`services.research.iter` is THE deep loop
(``run_iter_research`` for ``deep``, ``run_heavy_research`` for ``heavy``).
:mod:`services.research.deep` (``run_deep_research``, single-pass) is the INTERNAL
helper module (iter reuses its tested helpers verbatim) AND the belt-and-suspenders
FALLBACK only — it is no longer reachable as a user/model ``mode`` and never runs
on the normal path; iter's abort→synthesize covers degradation. There is no
user-reachable second deep loop.

The research service is imported lazily inside the call so the module imports
cleanly before the service lands and the tests can monkeypatch each seam in place.
"""

from __future__ import annotations

from typing import Any

#: How many researcher agents the native loop may fan out to per round. Bounds
#: the BudgetGuard step ceiling alongside ``rounds`` below.
_MAX_RESEARCHERS = 3

#: Per-LLM-call wall-clock cap (seconds) for the research loop. An LLM adapter
#: carries no per-stream timeout, so without this a slow "thinking" model could
#: stall ONE plan/distill/reflect/synthesis call for minutes (the cause of the
#: 8-minutes-unfinished bug). 60s is generous for a real completion yet bounds a
#: hang; the per-ROUND guard in deep/iter is the authoritative wall enforcement,
#: this is defense-in-depth at the single-call layer. On timeout the loop gets the
#: partial text and degrades gracefully.
_LLM_CALL_TIMEOUT_SECS = 60.0

#: ``angles`` for the Heavy panel. ``deep`` runs the single-agent iter loop
#: (angles=1); ``heavy`` fans out to ``_MAX_ANGLES`` parallel explorers. Kept in
#: lockstep with ``iter._MIN_ANGLES`` / ``iter._MAX_ANGLES``.
_MIN_HEAVY_ANGLES = 2
_MAX_ANGLES = 3

_PERPLEXITY_NEEDS_KEY = (
    "Perplexity deep research needs an API key (opt-in, paid). Add it in "
    "Settings, or use the built-in deep research."
)
_SONAR_NEEDS_KEY = (
    "The hosted Sonar research lane needs an OpenRouter API key (opt-in, paid). "
    "Add it in Settings, or use the built-in deep research."
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
    activity surface shows an honest "running on X" line — never a silent engine
    swap the user can't see. No-ops outside an agent invocation (no sink wired) and
    never raises (a cosmetic line must not break a run). The ``engine`` kind renders
    un-truncated in :file:`ResearchActivity.tsx`.
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


async def _run_perplexity(query: str, key: str | None) -> dict[str, Any]:
    """Run the opt-in-per-run paid Perplexity backend, or honest-fail without a key.

    NEVER auto-selects Perplexity — the caller already chose ``backend=perplexity``
    explicitly per-run. Without a configured key, returns the "needs a key" message.
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


async def _run_sonar(query: str, key: str | None, model: str | None = None) -> dict[str, Any]:
    """Run the opt-in-per-run paid OpenRouter Sonar lane, or honest-fail without a key.

    NEVER auto-selects — the caller already chose ``backend="sonar"`` explicitly
    per-run (R7 Component 3). The OpenRouter key resolution order is: explicit
    ``api_key`` arg → the per-request hosted-search key ContextVar → the active
    LLM creds when the user is actually ON OpenRouter. Without any key it
    returns the "needs a key" message; the key is never logged or echoed.
    """
    import config
    from services.research import sonar

    api_key = key or config.get_openrouter_search_key()
    if not api_key:
        creds = config.get_llm_creds()
        # Only reuse the active key if the user is actually on OpenRouter.
        if creds is not None and creds[0] == "openrouter":
            api_key = creds[2]

    if not sonar.is_configured(api_key):
        return {"ok": False, "message": _SONAR_NEEDS_KEY}

    resolved_model = sonar.resolve_model(model)
    _emit_backend_step(f"Perplexity Sonar via OpenRouter — {resolved_model} (paid)")
    backend = sonar.OpenRouterSonarBackend(api_key, model=resolved_model)
    brief = await backend.research(query, region=config.get_region())
    out = brief.to_dict()
    out["ok"] = True
    out.setdefault("cost_estimate_usd", sonar.estimate_cost_usd(query, resolved_model))
    out["backend"] = "sonar"
    return out


async def _run_loop(
    *,
    angles: int,
    query: str,
    llm_call: Any,
    rounds: int,
    wall: int,
) -> Any:
    """Run THE one deep loop, returning a ``ResearchBrief``.

    - ``angles >= 2`` → Heavy mode: an expert PANEL of parallel iter explorers +
      a synthesis agent (test-time scaling).
    - otherwise → the IterResearch loop: a central evolving report + per-round
      workspace reconstruction (no context bloat).

    The iter/heavy loops are designed never to raise (budget breach →
    abort→synthesize); a belt-and-suspenders ``except`` still drops to the proven
    single-pass ``run_deep_research`` (the NAMED internal fallback — never a
    user/model-reachable mode) so the default path can never error out. Budget
    scales with the angle fan-out so the panel stays inside one ceiling.
    """
    import config
    from services import agent_tools
    from services.budget_guard import BudgetGuard
    from services.research import deep
    from services.research import iter as iter_research
    from services.search.extract import visit_for_research

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
        # R7: each researcher reads the TOP web result's full page (bs4
        # main-content extraction over the same impersonation-capable transport
        # as the T1 engines); the loop fences it as untrusted before the prompt.
        "visit": visit_for_research,
    }
    if angles >= _MIN_HEAVY_ANGLES:
        return await iter_research.run_heavy_research(query, angles=angles, **common)
    try:
        return await iter_research.run_iter_research(query, **common)
    except Exception:  # pragma: no cover — iter never raises; fall back regardless
        # The NAMED single-pass fallback (S-9): not a parallel user-reachable
        # loop, only the catch-all so the deep path can never error out.
        return await deep.run_deep_research(query, **common)


def _engine_label(provider: str, model: str, angles: int) -> str:
    """Honest engine line naming the loop that actually ran."""
    if angles >= _MIN_HEAVY_ANGLES:
        return f"Your active model — {provider}/{model} · Heavy mode ({angles} parallel angles)"
    return f"Your active model — {provider}/{model} · IterResearch (evolving report)"


async def _run_native(query: str, rounds: int, wall: int, angles: int) -> dict[str, Any]:
    """Run the built-in deep-research loop against the user's active model."""
    import config
    from services.llm import oneshot

    creds = config.get_llm_creds()
    if creds is None:
        return {"ok": False, "message": _NO_MODEL}
    provider, model, key = creds

    _emit_backend_step(_engine_label(provider, model, angles))

    async def llm_call(messages: list[dict[str, Any]]) -> str:
        return await oneshot.complete(
            provider, model, key, messages, timeout=_LLM_CALL_TIMEOUT_SECS
        )

    brief = await _run_loop(angles=angles, query=query, llm_call=llm_call, rounds=rounds, wall=wall)
    out = brief.to_dict()
    out["ok"] = True
    out["backend"] = "native"
    out["mode"] = "heavy" if angles >= _MIN_HEAVY_ANGLES else "deep"
    return out


async def run_deep_brief(
    query: str,
    *,
    depth: str = "deep",
    rounds: Any = 3,
    wall_seconds: Any = 120,
    backend: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Run a budgeted deep/heavy research brief for ``query`` — the DEEP engine
    behind the ONE ``research`` capability.

    Args:
        query: What to research (already validated/non-blank by the caller).
        depth: ``"deep"`` (single-agent iter loop) or ``"heavy"`` (the expert
            panel of parallel angles). Anything else is treated as ``"deep"``.
        rounds: Research rounds, clamped to ``[1, 5]`` (default 3).
        wall_seconds: Wall-clock budget, clamped to ``[30, 300]`` (default 120).
        backend: ``"native"`` (default), ``"perplexity"`` (opt-in-per-run,
            paid), or ``"sonar"`` (opt-in-per-run, paid — the same sonar family
            through OpenRouter on the user's OpenRouter key; R7 Component 3).
            When ``None`` the user's Settings selection (Track 5) is read from
            the ContextVar; it only ever resolves to native unless the user
            explicitly opted into a paid lane for the run. NEVER auto-selects a
            paid backend.
        api_key: Optional key for the opt-in Perplexity/Sonar backends, when not
            reused from the active credentials.

    Returns the brief dict (``ok: True``) or ``{"ok": False, "message": ...}``.
    """
    rounds_i = _clamp(rounds, 1, 5, 3)
    wall = _clamp(wall_seconds, 30, 300, 120)
    angles = _MAX_ANGLES if str(depth).strip().lower() == "heavy" else 1

    # The user's Settings selection (Track 5) is authoritative when the caller does
    # not pass an explicit backend. Defaults to native; Perplexity (opt-in-per-run,
    # paid) is never auto-selected — the Settings ContextVar only ever holds
    # "perplexity" after the user explicitly opted in for the run.
    import config

    resolved_backend = (
        str(backend or config.get_deep_research_backend() or "native").strip().lower()
    )

    if resolved_backend == "perplexity":
        return await _run_perplexity(query, api_key)
    if resolved_backend in ("sonar", "openrouter-sonar"):
        return await _run_sonar(query, api_key)
    return await _run_native(query, rounds_i, wall, angles)


__all__ = ["run_deep_brief"]
