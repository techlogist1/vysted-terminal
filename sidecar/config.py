"""Runtime configuration for the sidecar.

The Tauri core resolves the per-OS application data directory and passes it in
via the ``--data-dir`` CLI argument, which ``main.py`` exports as the
``VYSTED_DATA_DIR`` environment variable. Everything that persists to disk —
the portfolio SQLite database, saved ``.vysted-workspace`` files — derives its
path from :func:`get_data_dir`.

When the sidecar is run outside Tauri (local dev, pytest) the variable is
unset and a ``~/.vysted-terminal`` fallback is used; tests override it with a
temporary directory.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from contextvars import ContextVar
from pathlib import Path
from typing import Any

DATA_DIR_ENV = "VYSTED_DATA_DIR"

# --- Region / locale (Pass B / Pillar A — FR-060) ---------------------------
#
# The frontend already owns the active region (``src/lib/region.ts`` +
# ``store/settings.ts``). Pass B threads it into the sidecar so the provider
# registry, news, screener, and macro handlers shape data for the user's locale
# (the "McDonald's principle", Constitution VIII). The region rides each request
# as the ``X-Vysted-Region`` header (the same per-request transport BYOK secrets
# use — never persisted); a single ASGI middleware in :mod:`app` reads it into
# the per-request ContextVar below, so any code path the request reaches —
# routers *and* the agent tool loop — sees the same region via :func:`get_region`.
#
# The default is ``"IN"`` (R10, E1): the operator's sessions are India-first
# and the old silent ``US`` default mis-ranked every resolver query that
# arrived without a region header. Mirrored by ``DEFAULT_REGION`` in
# ``src/lib/region.ts`` — flip both in the same commit. User Settings still
# override per request; ``VYSTED_REGION`` is a last-resort env fallback for
# non-HTTP entrypoints (CLI / tests).
REGION_ENV = "VYSTED_REGION"
_DEFAULT_REGION = "IN"
_KNOWN_REGIONS = frozenset({"US", "IN", "GLOBAL"})

# Sentinel: the ContextVar is "unset" until a request middleware sets it, which
# lets :func:`get_region` distinguish "no request region" (→ env / default) from
# an explicit ``US`` request without an extra flag.
_REGION_UNSET = ""
_region_ctx: ContextVar[str] = ContextVar("vysted_region", default=_REGION_UNSET)


def normalize_region(value: str | None) -> str:
    """Coerce an arbitrary value to a known region code, defaulting to ``IN``.

    Unknown / empty values fall back to the default rather than raising — a
    malformed ``X-Vysted-Region`` header must never break a data request.
    """
    if not value:
        return _DEFAULT_REGION
    candidate = value.strip().upper()
    return candidate if candidate in _KNOWN_REGIONS else _DEFAULT_REGION


def get_region() -> str:
    """Return the active region for the current request/task.

    Reads the per-request ContextVar set by the region middleware; absent that
    (non-HTTP entrypoints), falls back to ``VYSTED_REGION`` then ``"IN"``. The
    value is always a known region code (``US`` / ``IN`` / ``GLOBAL``).
    """
    current = _region_ctx.get()
    if current in _KNOWN_REGIONS:
        return current
    # ContextVar unset (non-HTTP entrypoint) → env fallback, then default.
    return normalize_region(os.environ.get(REGION_ENV))


def set_request_region(value: str | None) -> object:
    """Set the active region for the current request; returns a reset token.

    The middleware calls this on the way in and resets with the returned token on
    the way out so request-scoped state never leaks between requests.
    """
    return _region_ctx.set(normalize_region(value))


def reset_request_region(token: object) -> None:
    """Restore the region ContextVar to its prior value (middleware teardown)."""
    _region_ctx.reset(token)  # type: ignore[arg-type]


# --- Search config (Pass B / Pillar C — FR-080; R9 two-tier) -----------------
#
# The web-search preference rides each request the same way the region and BYOK
# secrets do — per-request headers read into ContextVars by the region
# middleware, reset on the way out, NEVER logged or persisted.
#
# The LEGACY pre-R8 ``X-Vysted-Search-Tier`` header (``native`` / ``byok-exa`` /
# ``local-searxng``) is still PARSED (third-party REST/MCP callers may send it)
# but only as migration input: :func:`get_effective_research_tier` folds it into
# the R9 two-tier vocabulary (byok-exa → tier_b when an OpenRouter key rides the
# request, else tier_a; everything else → tier_a). The R7 Exa-direct lane and
# its key header are DEAD — no Exa secret is read anymore.
SEARCH_TIER_NATIVE = "native"
_KNOWN_SEARCH_TIERS = frozenset({"native", "byok-exa", "local-searxng"})

_search_tier_ctx: ContextVar[str] = ContextVar("vysted_search_tier", default=SEARCH_TIER_NATIVE)
_searxng_url_ctx: ContextVar[str | None] = ContextVar("vysted_searxng_url", default=None)


def normalize_search_tier(value: str | None) -> str:
    """Coerce a value to a known LEGACY search tier, defaulting to ``native``."""
    if not value:
        return SEARCH_TIER_NATIVE
    candidate = value.strip().lower()
    return candidate if candidate in _KNOWN_SEARCH_TIERS else SEARCH_TIER_NATIVE


def get_search_tier() -> str:
    """The LEGACY per-request search tier — migration input only (see above)."""
    return _search_tier_ctx.get()


def get_searxng_url() -> str | None:
    """The per-request custom SearXNG base URL, or ``None`` (managed instance)."""
    return _searxng_url_ctx.get()


def set_request_search(*, tier: str | None, searxng_url: str | None) -> tuple[object, object]:
    """Set the per-request search config; returns reset tokens (middleware teardown)."""
    return (
        _search_tier_ctx.set(normalize_search_tier(tier)),
        _searxng_url_ctx.set(searxng_url.strip() if searxng_url and searxng_url.strip() else None),
    )


def reset_request_search(tokens: tuple[object, object]) -> None:
    """Restore the search ContextVars to their prior values (middleware teardown)."""
    tier_token, searxng_token = tokens
    _search_tier_ctx.reset(tier_token)  # type: ignore[arg-type]
    _searxng_url_ctx.reset(searxng_token)  # type: ignore[arg-type]


# --- Active LLM credentials (Pass B / Pillar B — deep research) --------------
#
# The agent invocation already carries the provider/model/api_key in its request
# body; ``invoke_agent`` publishes them into a ContextVar so an in-loop research
# tool (``deep_research``) can call the SAME LLM the user is talking to without
# re-plumbing the key through every tool signature. The key is a SECRET: held in
# process memory for the invocation only, set + reset around the agent loop,
# never logged or persisted. Read with :func:`get_llm_creds`.
_llm_creds_ctx: ContextVar[tuple[str, str, str | None] | None] = ContextVar(
    "vysted_llm_creds", default=None
)


def get_llm_creds() -> tuple[str, str, str | None] | None:
    """The active ``(provider, model, api_key)`` for the current agent run, or None."""
    return _llm_creds_ctx.get()


def set_request_llm_creds(provider: str, model: str, api_key: str | None) -> object:
    """Publish the active LLM creds for the run; returns a reset token."""
    return _llm_creds_ctx.set((provider, model, api_key))


def reset_request_llm_creds(token: object) -> None:
    """Clear the active LLM creds (agent-loop teardown)."""
    _llm_creds_ctx.reset(token)  # type: ignore[arg-type]


# --- Deep-research engine selection (Track 5) --------------------------------
#
# The user picks the DEEP engine in Settings (native IterResearch — the default —
# or the opt-in paid Perplexity backend). The frontend publishes the choice on the
# agent-invoke request; ``invoke_agent`` sets it here so the ``deep_research`` tool
# defaults to the chosen backend WITHOUT relying on the model to pass a tool arg
# (authoritative, not LLM-dependent). Task-local: each request is its own asyncio
# task with a copied context, so the choice never leaks across requests.
_deep_research_ctx: ContextVar[str | None] = ContextVar("vysted_deep_research", default=None)


def get_deep_research_backend() -> str | None:
    """The user's selected deep-research backend for this run (``native``/``perplexity``)."""
    return _deep_research_ctx.get()


def set_request_deep_research(backend: str | None) -> object:
    """Publish the deep-research backend for the run; returns a reset token."""
    return _deep_research_ctx.set(backend)


# R7: the composer's three-stop depth slider rides options.research_depth on
# the agent-invoke request. It is the DEFAULT depth for research tool calls in
# that run — an explicit depth arg from the model still wins (the deterministic
# escalation path), and an absent slider value falls back to NORMAL via
# normalize_depth. Mirrors the deep-research pattern above: task-local, never
# cross-request.
_research_depth_ctx: ContextVar[str | None] = ContextVar("vysted_research_depth", default=None)


def get_request_research_depth() -> str | None:
    """The composer-selected research depth for this run, or None."""
    return _research_depth_ctx.get()


def set_request_research_depth(depth: str | None) -> object:
    """Publish the run's default research depth; returns a reset token."""
    return _research_depth_ctx.set(depth)


# The resolved chat model's native web-search capability flag ("native"/"plugin"/
# None), threaded from the frontend catalog via the agent-invoke request. The
# deep-research tier_a lane reads it to gate the B4 dual-channel cross-verify
# with THE same detection truth as the runtime's injection gate
# (services.llm.native_search.native_search_available). Task-local, never
# cross-request — mirrors the depth ContextVar above.
_model_web_search_ctx: ContextVar[str | None] = ContextVar("vysted_model_web_search", default=None)


def get_request_model_web_search() -> str | None:
    """The active chat model's web-search capability flag for this run, or None."""
    return _model_web_search_ctx.get()


def set_request_model_web_search(flag: str | None) -> object:
    """Publish the run's model web-search capability; returns a reset token."""
    return _model_web_search_ctx.set(flag)


# Run-scoped search telemetry (R9 gate 2): the deep-research lane needs to know
# whether ANY retrieval in the run was served by the keyless floor so the
# published brief can carry the honest ``keyless-fallback`` id (the UI's
# setup-Unlimited nudge keys on it). A parent task creates the MUTABLE dict
# before fanning out researchers; child tasks copy the ContextVar but share the
# dict OBJECT, so their mutations are visible to the parent. ``None`` (no
# telemetry begun) keeps the web_search tool zero-overhead outside research.
_search_telemetry_ctx: ContextVar[dict | None] = ContextVar("vysted_search_telemetry", default=None)


def begin_search_telemetry() -> dict:
    """Open a fresh telemetry dict for this run and return it (parent task)."""
    telemetry: dict = {}
    _search_telemetry_ctx.set(telemetry)
    return telemetry


def get_search_telemetry() -> dict | None:
    """The run's shared search-telemetry dict, or None outside a research run."""
    return _search_telemetry_ctx.get()


# --- R9 research-tier selection (two tiers, Track A) --------------------------
#
# R9 collapses the R7/R8 three-tier research model into TWO user-facing tiers:
#
#   ``tier_a`` — "Unlimited (Local)": the managed SearXNG instance as retrieval
#                paired with the active chat model running the built-in research
#                loop. THE default. When SearXNG is not READY, retrieval silently
#                serves the keyless engines and the result/brief carries the
#                honest ``backend="keyless-fallback"`` id — never an error state,
#                and never a user-facing "keyless tier".
#   ``tier_b`` — "Hosted research model": an internet-native research model via
#                OpenRouter owns research at ALL depth stops regardless of the
#                chat model (per-stop model map below). Requires the BYOK
#                OpenRouter key (``X-Vysted-Openrouter-Key`` — a SECRET:
#                keychain-sourced in the renderer, header transport only,
#                process-memory for the request, never persisted or logged).
#
# The selection mirrors the deep-research backend pattern above EXACTLY: the
# frontend persists the choice in Settings and publishes it on each request
# (``X-Vysted-Research-Tier``); the middleware sets it here so any code path the
# request reaches — routers and the agent tool loop — reads the same tier via
# :func:`get_effective_research_tier`. Task-local, reset on request exit, never
# leaks across requests. The legacy R7/R8 spellings (``t1_local`` /
# ``t2_searxng`` / ``t3_hosted``) and the pre-R8 legacy header fold in per the
# migration table; an unknown value floors to ``tier_a`` — the only tier that
# can never surprise-bill or require setup.
SEARCH_TIER_A = "tier_a"
SEARCH_TIER_B = "tier_b"
KNOWN_RESEARCH_SEARCH_TIERS = frozenset({SEARCH_TIER_A, SEARCH_TIER_B})

#: Migration + forgiving aliases: the R7/R8 tier ids and short spellings fold
#: into the two-tier vocabulary so an old client/blob still lands on the
#: intended side of the key/cost boundary rather than silently flooring.
_RESEARCH_TIER_ALIASES: dict[str, str] = {
    # R7/R8 ids — t1/t2 share tier_a's local/keyless privacy class; t3 was the
    # hosted key boundary, which is exactly tier_b's boundary.
    "t1_local": SEARCH_TIER_A,
    "t2_searxng": SEARCH_TIER_A,
    "t3_hosted": SEARCH_TIER_B,
    # Loose spellings the old normalizer tolerated.
    "t1": SEARCH_TIER_A,
    "t2": SEARCH_TIER_A,
    "local": SEARCH_TIER_A,
    "keyless": SEARCH_TIER_A,
    "searxng": SEARCH_TIER_A,
    "a": SEARCH_TIER_A,
    "t3": SEARCH_TIER_B,
    "hosted": SEARCH_TIER_B,
    "openrouter": SEARCH_TIER_B,
    "research-model": SEARCH_TIER_B,
    "b": SEARCH_TIER_B,
}

_research_search_tier_ctx: ContextVar[str | None] = ContextVar(
    "vysted_research_search_tier", default=None
)
_openrouter_search_key_ctx: ContextVar[str | None] = ContextVar(
    "vysted_openrouter_search_key", default=None
)

#: One-shot deprecation note per legacy spelling (rule: config migration is
#: graceful and logged ONCE in the run log — never a user error).
_legacy_tier_notes_emitted: set[str] = set()


def _note_legacy_tier_once(value: str, mapped: str) -> None:
    """Log a single deprecation note the first time a legacy tier id is seen."""
    if value in _legacy_tier_notes_emitted:
        return
    _legacy_tier_notes_emitted.add(value)
    import logging

    logging.getLogger(__name__).info(
        "legacy research-tier value %r received — migrated to %r (R9 two-tier); "
        "update the caller to send tier_a/tier_b",
        value,
        mapped,
    )


def normalize_research_search_tier(value: str | None) -> str:
    """Coerce a value to a known R9 research tier, defaulting to ``tier_a``.

    Unknown / empty values fall back to the local tier_a default rather than
    raising — a malformed header must never break a request, and tier_a is the
    only tier that can never surprise-bill or require setup. Legacy R7/R8
    spellings fold in per the migration table (logged once, never an error).
    """
    if not value:
        return SEARCH_TIER_A
    candidate = value.strip().lower()
    if candidate in KNOWN_RESEARCH_SEARCH_TIERS:
        return candidate
    mapped = _RESEARCH_TIER_ALIASES.get(candidate)
    if mapped is not None:
        _note_legacy_tier_once(candidate, mapped)
        return mapped
    return SEARCH_TIER_A


def get_research_search_tier() -> str | None:
    """The explicitly selected research tier for this request, or ``None``.

    ``None`` means the request carried no ``X-Vysted-Research-Tier`` header —
    callers resolve the default via :func:`get_effective_research_tier`. A
    non-``None`` value is always one of :data:`KNOWN_RESEARCH_SEARCH_TIERS`.
    """
    return _research_search_tier_ctx.get()


def get_effective_research_tier() -> str:
    """The tier this request EFFECTIVELY runs on — always ``tier_a``/``tier_b``.

    The ONE tier-resolution truth (extends R8 D20/D25):

    1. an explicit ``X-Vysted-Research-Tier`` selection (already normalized,
       legacy spellings folded in) is authoritative;
    2. else the LEGACY pre-R8 ``X-Vysted-Search-Tier`` header maps per the
       migration table — ``byok-exa`` (the dead Exa-direct lane) → ``tier_b``
       when an OpenRouter key rides the request (the same key boundary), else
       ``tier_a``; ``local-searxng`` / ``native`` → ``tier_a``;
    3. else ``tier_a`` — the default tier. There is no "no tier" state.
    """
    explicit = _research_search_tier_ctx.get()
    if explicit is not None:
        return explicit
    legacy = _search_tier_ctx.get()
    if legacy == "byok-exa":
        mapped = SEARCH_TIER_B if get_openrouter_search_key() else SEARCH_TIER_A
        _note_legacy_tier_once("byok-exa", mapped)
        return mapped
    if legacy == "local-searxng":
        _note_legacy_tier_once("local-searxng", SEARCH_TIER_A)
        return SEARCH_TIER_A
    return SEARCH_TIER_A


def set_request_research_search_tier(tier: str | None) -> object:
    """Publish the research tier for the request; returns a reset token.

    ``None`` (header absent) stays ``None`` — "no explicit selection" (the
    effective tier then derives from legacy headers or the tier_a default); any
    present value is normalized so downstream readers never see an unknown id.
    """
    return _research_search_tier_ctx.set(
        normalize_research_search_tier(tier) if tier is not None and tier.strip() else None
    )


def reset_request_research_search_tier(token: object) -> None:
    """Restore the research-tier ContextVar (middleware teardown)."""
    _research_search_tier_ctx.reset(token)  # type: ignore[arg-type]


def get_openrouter_search_key() -> str | None:
    """The per-request OpenRouter BYOK key for the tier_b lane, or ``None``.

    A SECRET: keychain-sourced in the renderer, rides the request header only,
    process-memory for the request, never persisted, never logged.
    """
    return _openrouter_search_key_ctx.get()


def set_request_openrouter_search_key(key: str | None) -> object:
    """Publish the per-request OpenRouter key; returns a reset token."""
    return _openrouter_search_key_ctx.set(key.strip() if key and key.strip() else None)


def reset_request_openrouter_search_key(token: object) -> None:
    """Clear the OpenRouter key ContextVar (middleware teardown)."""
    _openrouter_search_key_ctx.reset(token)  # type: ignore[arg-type]


# --- Tier B per-stop research-model map (R9 Track A) ---------------------------
#
# Tier B routes research to a per-depth-stop model (NORMAL / DEEP / ULTRA). The
# frontend publishes the user's map on each request as the
# ``X-Vysted-Research-Models`` header — ordered ``stop=slug`` pairs joined by
# commas (``normal=perplexity/sonar,deep=…,ultra=…``; mirrored by
# ``encodeResearchModels`` in ``src/lib/search-headers.ts``). Parsing is
# defensive and MODEL-AGNOSTIC: any plausible OpenRouter slug is accepted (the
# lead can re-pin defaults without touching routing code); a malformed pair is
# dropped and that stop floors to its default. Task-local like every other
# per-request setting above.
RESEARCH_STOP_NORMAL = "normal"
RESEARCH_STOP_DEEP = "deep"
RESEARCH_STOP_ULTRA = "ultra"
KNOWN_RESEARCH_STOPS = (RESEARCH_STOP_NORMAL, RESEARCH_STOP_DEEP, RESEARCH_STOP_ULTRA)

#: The Tier B per-stop defaults — verified live on OpenRouter 2026-06-11
#: (sonar $1/M in · $1/M out; sonar-reasoning-pro $2/M in · $8/M out;
#: sonar-deep-research $2/M in · $8/M out · $3/M reasoning; all $5/1k searches).
DEFAULT_RESEARCH_MODELS: dict[str, str] = {
    RESEARCH_STOP_NORMAL: "perplexity/sonar",
    RESEARCH_STOP_DEEP: "perplexity/sonar-reasoning-pro",
    RESEARCH_STOP_ULTRA: "perplexity/sonar-deep-research",
}

#: A plausible OpenRouter model slug: sane charset, bounded length. Deliberately
#: loose — routing stays model-agnostic; this only rejects garbage/injection.
_MODEL_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")

_research_models_ctx: ContextVar[dict[str, str] | None] = ContextVar(
    "vysted_research_models", default=None
)


def parse_research_models(value: str | None) -> dict[str, str]:
    """Parse the ``X-Vysted-Research-Models`` header into a FULL per-stop map.

    Defensive: unknown stop names and implausible slugs are dropped; every stop
    always resolves (missing/garbled entries floor to the verified defaults) so
    downstream dispatch never sees a hole. Never raises.
    """
    models = dict(DEFAULT_RESEARCH_MODELS)
    if not value:
        return models
    for pair in value.split(","):
        stop, sep, slug = pair.partition("=")
        if not sep:
            continue
        stop = stop.strip().lower()
        slug = slug.strip()
        if stop in KNOWN_RESEARCH_STOPS and _MODEL_SLUG_RE.match(slug):
            models[stop] = slug
    return models


def get_research_model_for(stop: str) -> str:
    """The Tier B research model for ``stop`` (``normal``/``deep``/``ultra``).

    Reads the per-request map when one was published, else the verified
    defaults; an unknown stop floors to the NORMAL slot (the cheapest — never a
    silent escalation).
    """
    key = (stop or "").strip().lower()
    if key not in KNOWN_RESEARCH_STOPS:
        key = RESEARCH_STOP_NORMAL
    models = _research_models_ctx.get() or DEFAULT_RESEARCH_MODELS
    return models.get(key) or DEFAULT_RESEARCH_MODELS[key]


def set_request_research_models(value: str | None) -> object:
    """Publish the per-request research-model map; returns a reset token.

    ``None``/blank (header absent) stays ``None`` — readers fall back to the
    defaults; a present value is parsed defensively to a FULL map.
    """
    return _research_models_ctx.set(
        parse_research_models(value) if value is not None and value.strip() else None
    )


def reset_request_research_models(token: object) -> None:
    """Clear the research-model map ContextVar (middleware teardown)."""
    _research_models_ctx.reset(token)  # type: ignore[arg-type]


# --- Live research-step sink (Track A — aliveness) ---------------------------
#
# A long research tool (``deep_research`` / ``research``) runs for many seconds
# inside a single agent tool round. The runtime publishes a per-tool-call SINK
# here just before dispatching such a tool; the tool reads it and forwards each
# :class:`~services.research.models.ResearchStep` it produces to the sink, which
# the runtime drains and re-emits as ``research_step`` SSE events so the agent
# surface can animate a live "working" trace. The sink is a plain callable
# (``sink(step) -> None``), set + reset around each tool dispatch, task-local
# (a child task copies it at creation), and ``None`` outside an agent run (so the
# research engine degrades silently to no live trace — the brief still carries
# the full step list). Cosmetic only: it never gates a mutation, never a secret.
_step_sink_ctx: ContextVar[Callable[[Any], None] | None] = ContextVar(
    "vysted_step_sink", default=None
)


def get_step_sink() -> Callable[[Any], None] | None:
    """The active live-step sink for the current tool dispatch, or ``None``."""
    return _step_sink_ctx.get()


def set_step_sink(sink: Callable[[Any], None] | None) -> object:
    """Publish a live-step sink for the current tool dispatch; returns a token."""
    return _step_sink_ctx.set(sink)


def reset_step_sink(token: object) -> None:
    """Clear the live-step sink (per-tool-dispatch teardown)."""
    _step_sink_ctx.reset(token)  # type: ignore[arg-type]


def get_data_dir() -> Path:
    """Return the application data directory, creating it if necessary."""
    raw = os.environ.get(DATA_DIR_ENV)
    path = Path(raw) if raw else Path.home() / ".vysted-terminal"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_workspaces_dir() -> Path:
    """Return the directory holding saved ``.vysted-workspace`` files."""
    path = get_data_dir() / "workspaces"
    path.mkdir(parents=True, exist_ok=True)
    return path
