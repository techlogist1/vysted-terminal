"""Deep-research engine — the engine room behind the ONE ``research`` capability.

This module is NO LONGER a registered agent tool. After the R4 research collapse
(FR-115 / SC-028) there is exactly ONE user-facing + model-facing research
capability — ``research`` (see :mod:`services.agent_tools.research`) — with depth
as an INTERNAL escalation arg. R7 names the depths ``normal`` | ``deep`` |
``ultra`` (legacy ``quick``/``heavy`` map onto them forever); the canonical
profile table lives in :mod:`services.research.depth` — rounds, researcher
fan-out, panel width, report cap, wall budget, coverage strictness, the finance
``site:`` bias, and the ULTRA cross-check all scale from there. This module
supplies the engine behind ``depth in {"deep", "ultra"}`` via
:func:`run_deep_brief`; the ``research`` handler calls it directly. There is no
second tool name, no second catalog capability, and no user-visible ``/deep``.

R9 (Track A) adds the **Tier B research-model lane**
(:func:`run_research_model_brief`): with ``researchTier == tier_b`` an
internet-native research model via OpenRouter owns research at ALL depth stops
regardless of the chat model — per-stop model dispatch
(:func:`config.get_research_model_for`), citations mapped from OpenAI-style
``url_citation`` annotations (+ the ``citations[]`` url-list fallback), the
honest ``backend="research-model:<model-id>"`` id on the brief AND the live
steps, and a generous per-stop wall clock (ULTRA can take minutes). The
``research`` handler routes to it at the tool boundary; this module never
self-selects it.

Three per-run backends (tier_a):

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

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # import-light: the profile type only rides annotations
    from services.research.depth import DepthProfile

#: Per-LLM-call wall-clock cap (seconds) for the research loop. An LLM adapter
#: carries no per-stream timeout, so without this a slow "thinking" model could
#: stall ONE plan/distill/reflect/synthesis call for minutes (the cause of the
#: 8-minutes-unfinished bug). 60s is generous for a real completion yet bounds a
#: hang; the per-ROUND guard in deep/iter is the authoritative wall enforcement,
#: this is defense-in-depth at the single-call layer. On timeout the loop gets the
#: partial text and degrades gracefully.
_LLM_CALL_TIMEOUT_SECS = 60.0

#: The panel threshold: a profile with ``angles >= 2`` runs Heavy mode. Kept in
#: lockstep with ``iter._MIN_ANGLES``; the actual per-depth angle counts live in
#: ``services.research.depth.PROFILES`` (the ONE knob table).
_MIN_HEAVY_ANGLES = 2

#: Reserved wall (seconds) for the ULTRA cross-check round — carved OUT of the
#: profile wall so the heavy panel can never starve the verification round.
_CROSS_CHECK_RESERVE_SECS = 90

_PERPLEXITY_NEEDS_KEY = (
    "Perplexity deep research needs an API key (opt-in, paid). Add it in "
    "Settings, or use the built-in deep research."
)
_SONAR_NEEDS_KEY = (
    "The hosted Sonar research lane needs an OpenRouter API key (opt-in, paid). "
    "Add it in Settings, or use the built-in deep research."
)
_RESEARCH_MODEL_NEEDS_KEY = (
    "The hosted research model (Tier B) needs an OpenRouter API key. Add one in "
    "Settings → Research, or switch back to Unlimited (Local). I won't invent "
    "sources."
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
    profile: DepthProfile,
    query: str,
    llm_call: Any,
    rounds: int,
    wall: int,
    native_search: Any = None,
) -> Any:
    """Run THE one deep loop at the profile's knobs, returning a ``ResearchBrief``.

    - ``profile.angles >= 2`` (ULTRA) → Heavy mode: an expert PANEL of parallel
      iter explorers + a synthesis agent (test-time scaling), then the numeric
      CROSS-CHECK verification round (:mod:`services.research.verify`) when the
      profile asks for it.
    - otherwise (DEEP) → the IterResearch loop: a central evolving report +
      per-round workspace reconstruction (no context bloat).

    Every knob — researcher fan-out, report cap, coverage strictness
    (``min_web_domains``), the finance ``site:`` bias — comes from the ONE
    depth table (:data:`services.research.depth.PROFILES`).

    The iter/heavy loops are designed never to raise (budget breach →
    abort→synthesize); a belt-and-suspenders ``except`` still drops to the proven
    single-pass ``run_deep_research`` (the NAMED internal fallback — never a
    user/model-reachable mode) so the default path can never error out. Budget
    scales with the angle fan-out so the panel stays inside one ceiling, with
    headroom budgeted for the ULTRA cross-check round.
    """
    import config
    from services import agent_tools
    from services.budget_guard import BudgetGuard
    from services.research import deep
    from services.research import iter as iter_research
    from services.search.extract import visit_for_research

    heavy = profile.angles >= _MIN_HEAVY_ANGLES
    step_factor = profile.angles if heavy else 1
    # R9 (V14, third live skip): the cross-check round gets a RESERVED wall
    # slice — under a shared pot the heavy panel always consumed it and the
    # verification round (ULTRA's point) skipped honestly every run. The panel
    # runs against wall minus the reserve; the cross-check gets its own guard.
    cross_reserve = _CROSS_CHECK_RESERVE_SECS if (heavy and profile.cross_check) else 0
    budget = BudgetGuard(
        max_steps=step_factor * rounds * (profile.researchers + 2)
        + (2 if profile.cross_check else 0),
        max_wall_seconds=max(60, wall - cross_reserve),
    )
    region = config.get_region()
    on_step = config.get_step_sink()
    common = {
        "region": region,
        "tool_call": agent_tools.invoke_tool,
        "llm_call": llm_call,
        "budget": budget,
        # Forward each step LIVE to the runtime's step-sink (Track A) so the agent
        # surface animates a "working" trace — including the parallel angle
        # exploration in Heavy mode. ``None`` outside an agent invocation.
        "on_step": on_step,
        "max_researchers": profile.researchers,
        # R7: each researcher reads the TOP web result's full page (bs4
        # main-content extraction over the same impersonation-capable transport
        # as the T1 engines); the loop fences it as untrusted before the prompt.
        "visit": visit_for_research,
        # R7 depth knobs (Component 4): report cap, coverage strictness, and the
        # finance site: query bias all scale from the depth profile.
        "report_char_cap": profile.report_char_cap or None,
        "min_web_domains": profile.min_web_domains or 1,
        "site_bias": profile.site_bias,
    }
    if heavy:
        brief = await iter_research.run_heavy_research(query, angles=profile.angles, **common)
        if profile.cross_check:
            from services.research.verify import cross_check

            brief = await cross_check(
                brief,
                region=region,
                tool_call=agent_tools.invoke_tool,
                llm_call=llm_call,
                budget=BudgetGuard(max_steps=6, max_wall_seconds=_CROSS_CHECK_RESERVE_SECS),
                on_step=on_step,
                min_domains=max(2, profile.min_web_domains),
                # R9 B4 (lead integration): the tier_a dual-channel cross-verify.
                # ``None`` (no native-capable chat model, or tier_b which never
                # reaches this lane) keeps the single-lane behavior byte-identical.
                native_search=native_search,
            )
        return brief
    try:
        return await iter_research.run_iter_research(query, **common)
    except Exception:  # pragma: no cover — iter never raises; fall back regardless
        # The NAMED single-pass fallback (S-9): not a parallel user-reachable
        # loop, only the catch-all so the deep path can never error out. It takes
        # the shared researcher/coverage knobs but has no working report to cap.
        common.pop("report_char_cap", None)
        return await deep.run_deep_research(query, **common)


def _engine_label(provider: str, model: str, profile: DepthProfile) -> str:
    """Honest engine line naming the loop that actually ran."""
    if profile.angles >= _MIN_HEAVY_ANGLES:
        label = f"Heavy mode ({profile.angles} parallel angles"
        if profile.cross_check:
            label += " + cross-check"
        label += ")"
        return f"Your active model — {provider}/{model} · {label}"
    return f"Your active model — {provider}/{model} · IterResearch (evolving report)"


async def _run_native(query: str, profile: DepthProfile, rounds: int, wall: int) -> dict[str, Any]:
    """Run the built-in deep-research loop against the user's active model."""
    import config
    from services.llm import oneshot

    creds = config.get_llm_creds()
    if creds is None:
        return {"ok": False, "message": _NO_MODEL}
    provider, model, key = creds

    _emit_backend_step(_engine_label(provider, model, profile))

    async def llm_call(messages: list[dict[str, Any]]) -> str:
        return await oneshot.complete(
            provider, model, key, messages, timeout=_LLM_CALL_TIMEOUT_SECS
        )

    # R9 B4 (lead integration): on this tier_a lane, a native-search-capable
    # chat model compounds as a SECOND verification channel — the loop's
    # cross-check round re-checks claims through both SearXNG retrieval and the
    # model's own search (Track A detection truth + invocation channel, Track B
    # dual-channel verdicts). tier_b never reaches this lane (research.py routes
    # it to the hosted research model first), so no tier check is needed here.
    from services.llm import native_search as native_search_mod

    native_search = None
    model_web_search = config.get_request_model_web_search()
    if native_search_mod.native_search_available(provider, model_web_search):

        async def native_search(prompt: str) -> dict[str, Any]:
            return await native_search_mod.native_search_oneshot(
                provider, model, key, prompt, model_web_search=model_web_search
            )

    # R9 gate 2: open the run-scoped search telemetry BEFORE the loop fans out
    # researchers (child tasks share the dict object), so a keyless-floor
    # retrieval anywhere in the run surfaces on the published brief.
    telemetry = config.begin_search_telemetry()

    brief = await _run_loop(
        profile=profile,
        query=query,
        llm_call=llm_call,
        rounds=rounds,
        wall=wall,
        native_search=native_search,
    )
    out = brief.to_dict()
    out["ok"] = True
    # The honest backend id: "native" names the chat-model engine; when ANY
    # retrieval in the run was served by the keyless floor the brief carries
    # "keyless-fallback" instead — the UI's setup-Unlimited nudge keys on it.
    # ...and ONLY when SearXNG never served this run — one flaked search on a
    # working managed instance must not nudge the user to set up what runs.
    out["backend"] = (
        "keyless-fallback"
        if telemetry.get("keyless_fallback_searches") and not telemetry.get("searxng_searches")
        else "native"
    )
    # ``mode`` keeps the legacy loop naming the brief contract renders; ``depth``
    # carries the R7 surface naming (normal/deep/ultra) for new consumers.
    out["mode"] = "heavy" if profile.angles >= _MIN_HEAVY_ANGLES else "deep"
    out["depth"] = profile.depth
    return out


async def run_deep_brief(
    query: str,
    *,
    depth: str = "deep",
    rounds: Any = None,
    wall_seconds: Any = None,
    backend: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Run a budgeted deep/ultra research brief for ``query`` — the DEEP engine
    behind the ONE ``research`` capability.

    Args:
        query: What to research (already validated/non-blank by the caller).
        depth: ``"deep"`` (single-agent iter loop) or ``"ultra"`` (the expert
            panel + cross-check). Legacy ``"heavy"`` maps to ultra; any other
            value (including ``"normal"``/``"quick"`` — the fast pass belongs to
            the ``research`` handler, not this engine) is treated as ``"deep"``.
        rounds: Research rounds, clamped to ``[1, 5]``; ``None`` takes the depth
            profile's default (deep 3, ultra 4).
        wall_seconds: Wall-clock budget, clamped to ``[30, 300]``; ``None``
            takes the depth profile's default (deep 120, ultra 240).
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
    from services.research import depth as depth_mod

    profile = depth_mod.profile_for(depth)
    if profile.loop == "fast":
        # This engine serves the deep lanes only — a caller that reached it with
        # a fast-pass depth gets the DEEP profile, never a silent ultra upgrade.
        profile = depth_mod.PROFILES[depth_mod.DEPTH_DEEP]
    rounds_i = _clamp(rounds, 1, 5, profile.rounds)
    wall = _clamp(wall_seconds, 30, 300, profile.wall_seconds)

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
    return await _run_native(query, profile, rounds_i, wall)


# ---------------------------------------------------------------------------
# Tier B — the hosted research-model lane (R9 Track A)
# ---------------------------------------------------------------------------

#: The honest backend-id prefix every Tier B brief and step carries —
#: ``research-model:<openrouter-model-id>``. Team C's UI keys off it.
RESEARCH_MODEL_BACKEND_PREFIX = "research-model:"

#: Per-stop wall clocks (seconds) for the one-call research model. ULTRA on
#: sonar-deep-research can take MINUTES — the brief mandates a generous (>=360s)
#: ceiling; normal/deep are single search-grounded (reasoning) completions.
_RESEARCH_MODEL_WALL_SECONDS: dict[str, float] = {
    "normal": 120.0,
    "deep": 300.0,
    "ultra": 480.0,
}

#: Heartbeat cadence for the live progress steps while the one HTTP call runs —
#: honest "still working" lines, since a vendor one-call lane exposes no
#: internal stage events to stream.
_RESEARCH_MODEL_HEARTBEAT_SECS = 20.0

#: Coarse per-stop pre-run cost bands (USD) — ESTIMATES shown with the brief,
#: never billed amounts (OpenRouter's pass-through metering is authoritative).
#: normal ≈ one search-grounded completion; deep adds reasoning; ultra is the
#: multi-step deep-research band (verified pricing in ``config``'s defaults).
_RESEARCH_MODEL_COST_BANDS: dict[str, tuple[float, float, float]] = {
    # (base, per_char, ceiling)
    "normal": (0.01, 0.00001, 0.05),
    "deep": (0.05, 0.00005, 0.15),
    "ultra": (0.25, 0.00015, 0.40),
}

_RESEARCH_MODEL_PROVENANCE = "via hosted research model (OpenRouter)"


def _research_model_stop(depth: str) -> str:
    """Normalize a depth spelling to the per-stop key (normal/deep/ultra)."""
    from services.research import depth as depth_mod

    return depth_mod.normalize_depth(depth)


def estimate_research_model_cost_usd(query: str, stop: str) -> float:
    """Coarse per-run USD estimate for one Tier B call at ``stop`` — an
    ESTIMATE flagged as such on the brief, never a billed amount."""
    base, per_char, ceiling = _RESEARCH_MODEL_COST_BANDS.get(
        stop, _RESEARCH_MODEL_COST_BANDS["normal"]
    )
    length = len((query or "").strip())
    return round(min(base + length * per_char, ceiling), 4)


def _research_model_http_error(status: int) -> str:
    """Translate an OpenRouter HTTP status into a clean, key-free human message."""
    if status in (401, 403):
        return (
            "OpenRouter rejected the request — check that your OpenRouter API "
            "key is valid and active."
        )
    if status == 402:
        return (
            "OpenRouter reports insufficient credits for the research run — top "
            "up your account to use the hosted research model."
        )
    if status == 429:
        return "OpenRouter rate limit reached — slow down or check your plan's quota."
    if status == 400:
        return "OpenRouter could not process the research request (bad query or parameters)."
    if status >= 500:
        return "OpenRouter is temporarily unavailable (server error) — try again shortly."
    return f"The hosted research model request failed with HTTP {status}."


def _research_model_message(body: dict[str, Any]) -> dict[str, Any]:
    """The first choice's message dict, or ``{}`` — never raises on a thin body."""
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return {}
    first = choices[0]
    if not isinstance(first, dict):
        return {}
    message = first.get("message")
    return message if isinstance(message, dict) else {}


def _research_model_sources(body: dict[str, Any]) -> list[Any]:
    """Map citations to ``ResearchSource`` — annotations first, url-list fallback.

    The PRIMARY path is the existing OpenAI ``url_citation`` normalizer over
    ``choices[0].message.annotations`` (the same citation path every
    OpenAI-shaped backend uses); the top-level / message-level ``citations[]``
    plain-url list catches anything the annotations missed. Merged,
    de-duplicated by url, order-preserved; every source carries the
    research-model provenance in its ``domain`` label.
    """
    import httpx

    from services.llm.native_search import normalize_openai
    from services.research.models import ResearchSource

    sources: list[Any] = []
    seen: set[str] = set()

    def _domain_of(url: str) -> str | None:
        try:
            host = httpx.URL(url).host
        except (httpx.InvalidURL, ValueError, TypeError):
            return None
        if not host:
            return None
        return host[4:] if host.startswith("www.") else host

    def _add(url: str, title: str = "", excerpt: str = "") -> None:
        url = (url or "").strip()
        if not url or url in seen:
            return
        seen.add(url)
        host = _domain_of(url)
        domain = f"{host} ({_RESEARCH_MODEL_PROVENANCE})" if host else _RESEARCH_MODEL_PROVENANCE
        sources.append(
            ResearchSource(
                url=url,
                title=(title or host or url).strip(),
                excerpt=(excerpt or "").strip(),
                domain=domain,
            )
        )

    message = _research_model_message(body)
    for record in normalize_openai(message.get("annotations")):
        _add(record.get("url", ""), record.get("title", ""), record.get("excerpt", ""))
    for container in (body, message):
        citations = container.get("citations")
        if isinstance(citations, list):
            for entry in citations:
                if isinstance(entry, str):
                    _add(entry)
    return sources


def _make_step(kind: str, detail: str) -> Any:
    """A :class:`ResearchStep` for the Tier B trace (collected + sunk live)."""
    from services.research.models import ResearchStep

    return ResearchStep(kind=kind, detail=detail)


async def run_research_model_brief(
    query: str,
    *,
    depth: str = "normal",
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Run ONE Tier B research call — the hosted research model owns this run.

    Dispatches the per-stop model (``config.get_research_model_for``; an
    explicit ``model`` arg wins — model-AGNOSTIC: any plausible OpenRouter slug
    routes) via OpenRouter chat-completions on the user's BYOK key. The key
    resolution order is: explicit ``api_key`` arg → the per-request
    ``X-Vysted-Openrouter-Key`` ContextVar → the active LLM creds when the user
    is actually ON OpenRouter. Without a key it returns the honest "needs a
    key" message naming the unlock — never a silent demotion to another lane
    (the key boundary, D25).

    Streams progress honestly: an ``engine`` step naming
    ``research-model:<model-id>`` up front, then heartbeat steps while the
    (potentially minutes-long on ULTRA) call runs. The brief AND every step
    carry the ``research-model:<model-id>`` backend id — evidence that research
    routed to the research model regardless of the chat model.
    """
    import asyncio
    import time

    import httpx

    import config
    from services.search.base import SearchError

    key = (api_key or "").strip() or config.get_openrouter_search_key()
    if not key:
        creds = config.get_llm_creds()
        # Only reuse the active key if the user is actually on OpenRouter.
        if creds is not None and creds[0] == "openrouter":
            key = creds[2]
    if not key:
        return {"ok": False, "message": _RESEARCH_MODEL_NEEDS_KEY}

    text = (query or "").strip()
    if not text:
        return {"ok": False, "message": "Research needs a query — tell me what to look into."}

    stop = _research_model_stop(depth)
    resolved_model = (model or "").strip() or config.get_research_model_for(stop)
    backend_id = f"{RESEARCH_MODEL_BACKEND_PREFIX}{resolved_model}"
    wall = _RESEARCH_MODEL_WALL_SECONDS.get(stop, _RESEARCH_MODEL_WALL_SECONDS["normal"])

    sink = config.get_step_sink()
    steps: list[Any] = []

    def _step(kind: str, detail: str) -> None:
        step = _make_step(kind, detail)
        steps.append(step)
        if sink is not None:
            try:
                sink(step)
            except Exception:  # pragma: no cover — cosmetic; never breaks a run
                pass

    _step("engine", f"{backend_id} — hosted research model ({stop} stop, via OpenRouter)")

    started = time.monotonic()

    async def _heartbeat() -> None:
        # Honest "still working" cadence — a vendor one-call lane exposes no
        # internal stages, so elapsed time is the truthful progress signal
        # (ULTRA on a deep-research model can legitimately take minutes).
        while True:
            await asyncio.sleep(_RESEARCH_MODEL_HEARTBEAT_SECS)
            elapsed = int(time.monotonic() - started)
            _step("engine", f"{backend_id} — still researching ({elapsed}s elapsed)")

    payload: dict[str, Any] = {
        "model": resolved_model,
        "messages": [{"role": "user", "content": text}],
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(wall, connect=10.0)

    heartbeat = asyncio.create_task(_heartbeat())
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers
            )
        response.raise_for_status()
        body: dict[str, Any] = response.json()
    except httpx.HTTPStatusError as exc:
        return {"ok": False, "message": _research_model_http_error(exc.response.status_code)}
    except httpx.HTTPError:
        return {"ok": False, "message": "Could not reach OpenRouter — check your network."}
    except ValueError:
        return {"ok": False, "message": "OpenRouter returned a response that could not be parsed."}
    except SearchError as exc:  # defensive — keep the human message
        return {"ok": False, "message": str(exc)}
    finally:
        heartbeat.cancel()

    content = _research_model_message(body).get("content")
    markdown = content.strip() if isinstance(content, str) else ""
    if not markdown:
        return {"ok": False, "message": "The hosted research model returned an empty brief."}

    sources = _research_model_sources(body)
    elapsed_total = int(time.monotonic() - started)
    _step("synthesize", f"{backend_id} — brief synthesised ({elapsed_total}s)")

    from services.research.models import ResearchBrief

    brief = ResearchBrief(
        query=text,
        symbol="",
        # ``mode`` keeps the legacy fast/deep naming the brief contract renders;
        # ``depth`` (below) carries the per-stop truth for new consumers.
        mode="fast" if stop == "normal" else "deep",
        markdown=markdown,
        sources=sources,
        steps=steps,
        source_count=len(sources),
        cost={
            "tokens": None,
            "spend_usd": estimate_research_model_cost_usd(text, stop),
            "steps": None,
            "estimate": True,
            "provider": _RESEARCH_MODEL_PROVENANCE,
        },
        web_available=bool(sources),
        note=None,
    )
    out = brief.to_dict()
    out["ok"] = True
    out["backend"] = backend_id
    out["depth"] = stop
    return out


__all__ = [
    "RESEARCH_MODEL_BACKEND_PREFIX",
    "estimate_research_model_cost_usd",
    "run_deep_brief",
    "run_research_model_brief",
]
