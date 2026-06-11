"""R9 Track A — the web_search agent tool: ONE retrieval resolution path.

Retrieval is ONE local lane shared by BOTH research tiers (the tier governs
where RESEARCH routes, never where retrieval happens). The routing matrix
below locks every cell — {explicit tier_a/tier_b} × {legacy R7 ids} ×
{legacy pre-R8 headers} × {no headers} × {custom URL or not} × {managed
SearXNG READY or not} — asserting the chosen backend id per cell with the
registry and the in-process manager mocked. It EXTENDS R8's matrix (never
shrunk); the R8 cells whose semantics R9 deliberately changed are called out
inline (there is no user-facing keyless tier anymore — t1_local folds into
tier_a, so a READY managed instance now serves it).

Rule 1 (extends R8 D20/D25): tier_a → SearXNG READY ? searxng :
``keyless-fallback`` (the honest id Team C's nudge banner keys off) — never an
error state. A stopped SearXNG NEVER yields "no web backend".
"""

from __future__ import annotations

import asyncio
import contextlib

import pytest

import config
from services.agent_tools.web_search import KEYLESS_FALLBACK_BACKEND_ID, _web_search
from services.search.base import Citation, SearchError, SearchResponse, SearchResult

MANAGED_URL = "http://127.0.0.1:8888"


class _FakeBackend:
    def __init__(self, backend: str = "searxng") -> None:
        self.backend = backend

    async def search(self, query: str, *, options=None) -> SearchResponse:  # noqa: ANN001
        return SearchResponse(
            results=[SearchResult(url="https://x.com/a", title="A", snippet="snip")],
            citations=[Citation(url="https://x.com/a", title="A", excerpt="snip")],
            backend=self.backend,
            query=query,
        )


def _run(coro):
    return asyncio.run(coro)


@contextlib.contextmanager
def _request(
    *,
    r7: str | None = None,
    legacy: str | None = None,
    searxng_url: str | None = None,
    openrouter_key: str | None = None,
):
    """Set the full per-request search header state; reset on exit (the
    middleware contract — nothing leaks across requests)."""
    r7_token = config.set_request_research_search_tier(r7)
    search_tokens = config.set_request_search(tier=legacy, searxng_url=searxng_url)
    or_token = config.set_request_openrouter_search_key(openrouter_key)
    try:
        yield
    finally:
        config.reset_request_openrouter_search_key(or_token)
        config.reset_request_search(search_tokens)
        config.reset_request_research_search_tier(r7_token)


def _stub_registry(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """A registry.resolve stub with REAL availability semantics: ``searxng``
    needs a URL, the keyless floor always resolves, dead R7 ids resolve to
    None. Records every call (id + kwargs) so a test can assert WHICH lane was
    consulted and WITH WHAT URL."""
    from services.search import registry

    calls: list[dict] = []

    def _resolve(active_id, **kw):  # noqa: ANN001, ANN003
        calls.append({"id": active_id, **kw})
        if active_id == "searxng" and kw.get("searxng_url"):
            return _FakeBackend("searxng")
        if active_id in ("keyless", "ddg"):
            return _FakeBackend(active_id)
        return None

    monkeypatch.setattr(registry, "resolve", _resolve)
    return calls


def _set_manager_ready(monkeypatch: pytest.MonkeyPatch, ready: bool) -> None:
    """Pin the in-process managed-SearXNG state: READY → the managed base URL,
    else ``None`` (the instant ``ready_base_url()`` read the resolver uses)."""
    from services import searxng_manager

    monkeypatch.setattr(
        searxng_manager.manager,
        "ready_base_url",
        lambda: MANAGED_URL if ready else None,
    )


def _stub_detect(monkeypatch: pytest.MonkeyPatch, result: str | None) -> dict:
    """Stub the network autodetect (services.search.searxng.detect_searxng) —
    the R9 hot path must NEVER reach it (the manager read is in-process)."""
    from services.search import searxng

    seen: dict = {"called": False}

    async def _fake_detect(base=None, *, client=None):  # noqa: ANN001, ANN202
        seen["called"] = True
        return result

    monkeypatch.setattr(searxng, "detect_searxng", _fake_detect)
    return seen


# --- The R9 routing matrix ----------------------------------------------------
#
# Each cell: (r7 tier header, legacy tier header, openrouter key, custom
# searxng url, manager READY) → the backend id the tool result must carry.
# ``None`` r7 + ``None`` legacy = the no-headers cell.

CUSTOM_URL = "http://10.0.0.5:8080"
FALLBACK = KEYLESS_FALLBACK_BACKEND_ID

MATRIX = [
    # Explicit tier_a — managed instance when READY, else the SILENT honest
    # keyless fallback (never an error state).
    ("tier_a", None, None, None, True, "searxng"),
    ("tier_a", None, None, None, False, FALLBACK),
    # Explicit tier_a with a custom URL — that instance, manager moot.
    ("tier_a", None, None, CUSTOM_URL, True, "searxng"),
    ("tier_a", None, None, CUSTOM_URL, False, "searxng"),
    # Explicit tier_b — retrieval STAYS local (only research routes to the
    # research model); the key changes nothing about retrieval.
    ("tier_b", None, "sk-or-1", None, True, "searxng"),
    ("tier_b", None, "sk-or-1", None, False, FALLBACK),
    ("tier_b", None, None, None, True, "searxng"),
    ("tier_b", None, None, None, False, FALLBACK),
    # Legacy R7 ids fold in: t1_local/t2_searxng → tier_a. (R9 semantics
    # change, deliberate: there is no user-facing keyless tier, so a READY
    # managed instance now serves an old explicit-t1 client too.)
    ("t1_local", None, None, None, True, "searxng"),
    ("t1_local", None, None, None, False, FALLBACK),
    ("t2_searxng", None, None, None, True, "searxng"),
    ("t2_searxng", None, None, None, False, FALLBACK),
    ("t2_searxng", None, None, CUSTOM_URL, True, "searxng"),
    ("t2_searxng", None, None, CUSTOM_URL, False, "searxng"),
    # Legacy R7 t3_hosted → tier_b; the hosted SCRAPER is dead, retrieval is
    # local — with or without the key, with a READY manager or not.
    ("t3_hosted", None, "sk-or-1", None, True, "searxng"),
    ("t3_hosted", None, "sk-or-1", None, False, FALLBACK),
    ("t3_hosted", None, None, None, True, "searxng"),
    ("t3_hosted", None, None, None, False, FALLBACK),
    # Legacy pre-R8 byok-exa — the Exa lane is DELETED; maps across the key
    # boundary (tier_b with a key, tier_a without), retrieval local either way.
    (None, "byok-exa", "sk-or-1", None, True, "searxng"),
    (None, "byok-exa", "sk-or-1", None, False, FALLBACK),
    (None, "byok-exa", None, None, True, "searxng"),
    (None, "byok-exa", None, None, False, FALLBACK),
    # Legacy local-searxng with an explicit URL — that instance, manager moot.
    (None, "local-searxng", None, CUSTOM_URL, True, "searxng"),
    (None, "local-searxng", None, CUSTOM_URL, False, "searxng"),
    # Legacy local-searxng without a URL — tier_a lanes.
    (None, "local-searxng", None, None, True, "searxng"),
    (None, "local-searxng", None, None, False, FALLBACK),
    # Legacy native — THE confirmed R7 bug cell stays pinned: a READY managed
    # SearXNG is never bypassed.
    (None, "native", None, None, True, "searxng"),
    (None, "native", None, None, False, FALLBACK),
    # No headers at all (fresh client / non-HTTP entrypoint): the tier_a lanes.
    (None, None, None, None, True, "searxng"),
    (None, None, None, None, False, FALLBACK),
]


@pytest.mark.parametrize(
    ("r7", "legacy", "or_key", "searxng_url", "ready", "expected"),
    MATRIX,
)
def test_routing_matrix(
    monkeypatch: pytest.MonkeyPatch,
    r7: str | None,
    legacy: str | None,
    or_key: str | None,
    searxng_url: str | None,
    ready: bool,
    expected: str,
) -> None:
    _stub_registry(monkeypatch)
    _set_manager_ready(monkeypatch, ready)
    # No cell may reach the network autodetect; stub it dark so a cell that
    # wrongly probes fails loudly below.
    seen = _stub_detect(monkeypatch, None)

    with _request(r7=r7, legacy=legacy, searxng_url=searxng_url, openrouter_key=or_key):
        out = _run(_web_search({"query": "nvidia earnings"}))

    assert out["ok"] is True, out
    assert out["backend"] == expected
    assert seen["called"] is False


def test_matrix_did_not_shrink_from_r8() -> None:
    # R8 pinned 14 matrix cells; the brief mandates extending, never shrinking.
    assert len(MATRIX) >= 29


def test_default_lane_uses_the_managed_instances_own_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The managed lane resolves SearXNG with the manager's reported base URL —
    not a guessed port."""
    calls = _stub_registry(monkeypatch)
    _set_manager_ready(monkeypatch, True)

    with _request():
        out = _run(_web_search({"query": "x"}))

    assert out["ok"] is True and out["backend"] == "searxng"
    searxng_calls = [c for c in calls if c["id"] == "searxng"]
    assert searxng_calls and searxng_calls[0]["searxng_url"] == MANAGED_URL


def test_custom_url_wins_over_the_managed_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _stub_registry(monkeypatch)
    _set_manager_ready(monkeypatch, True)

    with _request(searxng_url=CUSTOM_URL):
        out = _run(_web_search({"query": "x"}))

    assert out["ok"] is True and out["backend"] == "searxng"
    searxng_calls = [c for c in calls if c["id"] == "searxng"]
    assert searxng_calls[0]["searxng_url"] == CUSTOM_URL


def test_searxng_search_time_failure_degrades_to_keyless_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rule 1 resilience: a SearXNG instance that RESOLVES but fails at search
    time (stopped container / dead custom URL) degrades ONCE to the keyless
    floor with the honest fallback id — never an error state, and no banner can
    claim SearXNG served the run."""
    from services.search import registry

    class _DeadSearxng:
        async def search(self, query, *, options=None):  # noqa: ANN001, ANN201
            raise SearchError("SearXNG unreachable at http://…")

    def _resolve(active_id, **kw):  # noqa: ANN001, ANN003
        if active_id == "searxng" and kw.get("searxng_url"):
            return _DeadSearxng()
        if active_id == "keyless":
            return _FakeBackend("keyless")
        return None

    monkeypatch.setattr(registry, "resolve", _resolve)
    _set_manager_ready(monkeypatch, True)

    with _request(r7="tier_a"):
        out = _run(_web_search({"query": "x"}))

    assert out["ok"] is True
    assert out["backend"] == KEYLESS_FALLBACK_BACKEND_ID


def test_keyless_fallback_id_never_claims_searxng(monkeypatch: pytest.MonkeyPatch) -> None:
    """The fallback result's id is the FALLBACK id even though the keyless
    backend reports its own engine-tagged id internally."""
    from services.search import registry

    def _resolve(active_id, **kw):  # noqa: ANN001, ANN003
        if active_id == "keyless":
            return _FakeBackend("keyless:brave")  # engine-tagged internal id
        return None

    monkeypatch.setattr(registry, "resolve", _resolve)
    _set_manager_ready(monkeypatch, False)

    with _request(r7="tier_a"):
        out = _run(_web_search({"query": "x"}))

    assert out["backend"] == KEYLESS_FALLBACK_BACKEND_ID


def test_ddg_defensive_floor_is_stamped_as_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services.search import registry

    # Should the keyless module ever fail to import, the bare ddg floor serves —
    # still stamped with the honest fallback id (it IS the fallback position).
    def _resolve(active_id, **_kw):  # noqa: ANN001, ANN003
        return _FakeBackend("ddg") if active_id == "ddg" else None

    monkeypatch.setattr(registry, "resolve", _resolve)
    _set_manager_ready(monkeypatch, False)
    with _request():
        out = _run(_web_search({"query": "nvidia earnings"}))
    assert out["ok"] is True
    assert out["backend"] == KEYLESS_FALLBACK_BACKEND_ID
    assert out["results"][0]["url"] == "https://x.com/a"


# --- Existing contract — unchanged behaviours ---------------------------------


def test_missing_query_is_rejected() -> None:
    out = _run(_web_search({}))
    assert out["ok"] is False and "error" in out


def test_honest_message_when_even_ddg_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.search import registry

    # Defensive path: if EVERY backend (including the ddg floor) fails to resolve,
    # the handler still returns an honest message rather than a fabricated source.
    monkeypatch.setattr(registry, "resolve", lambda *a, **k: None)
    _set_manager_ready(monkeypatch, False)
    with _request():
        out = _run(_web_search({"query": "nvidia earnings"}))
    assert out["ok"] is False
    assert "Unlimited" in out["message"] or "Settings" in out["message"]
    assert "search" in out["message"].lower()


def test_dispatch_returns_results_and_citations(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.search import registry

    monkeypatch.setattr(registry, "resolve", lambda *a, **k: _FakeBackend("searxng"))
    with _request(searxng_url=CUSTOM_URL):
        out = _run(_web_search({"query": "nvidia", "num_results": 3, "category": "financial"}))
    assert out["ok"] is True
    assert out["backend"] == "searxng"
    assert out["results"][0]["url"] == "https://x.com/a"
    assert out["citations"][0] == {"url": "https://x.com/a", "title": "A", "excerpt": "snip"}


def test_search_error_becomes_human_message(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.search import registry

    class _Boom:
        backend = "keyless"

        async def search(self, query, *, options=None):  # noqa: ANN001, ANN201
            raise SearchError("keyless web search failed upstream (503).")

    def _resolve(active_id, **_kw):  # noqa: ANN001, ANN003
        return _Boom() if active_id == "keyless" else None

    monkeypatch.setattr(registry, "resolve", _resolve)
    _set_manager_ready(monkeypatch, False)
    with _request():
        out = _run(_web_search({"query": "x"}))
    assert out["ok"] is False and "503" in out["message"]
    # A plain SearchError (no typed reason) defaults to "unreachable" so the
    # brief reports an honest no-backend miss rather than a transient throttle.
    assert out["reason"] == "unreachable"


def test_search_error_forwards_typed_rate_limit_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WS3: a SearchError tagged ``reason="rate_limited"`` (a transient throttle)
    is surfaced on the failed dict so the brief shows "rate-limited, retrying"
    instead of the false "no backend configured" banner. Pinned on the floor
    lane (no headers, manager down) — the fast-path distinction survives R9."""
    from services.search import registry
    from services.search.base import SEARCH_REASON_RATE_LIMITED

    class _Throttled:
        backend = "ddg"

        async def search(self, query, *, options=None):  # noqa: ANN001, ANN201
            raise SearchError(
                "keyless web search is rate-limiting right now — retry shortly",
                reason=SEARCH_REASON_RATE_LIMITED,
            )

    def _resolve(active_id, **_kw):  # noqa: ANN001, ANN003
        return _Throttled() if active_id in ("keyless", "ddg") else None

    monkeypatch.setattr(registry, "resolve", _resolve)
    _set_manager_ready(monkeypatch, False)
    with _request():
        out = _run(_web_search({"query": "x"}))
    assert out["ok"] is False
    assert out["reason"] == "rate_limited"


def test_searxng_rate_limit_does_not_silently_degrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only an UNREACHABLE SearXNG degrades to the floor; a typed rate-limit is
    surfaced honestly (transient — the instance is alive, retry is the fix)."""
    from services.search import registry
    from services.search.base import SEARCH_REASON_RATE_LIMITED

    class _Throttled:
        async def search(self, query, *, options=None):  # noqa: ANN001, ANN201
            raise SearchError("SearXNG throttled", reason=SEARCH_REASON_RATE_LIMITED)

    def _resolve(active_id, **kw):  # noqa: ANN001, ANN003
        if active_id == "searxng" and kw.get("searxng_url"):
            return _Throttled()
        if active_id == "keyless":
            return _FakeBackend("keyless")
        return None

    monkeypatch.setattr(registry, "resolve", _resolve)
    _set_manager_ready(monkeypatch, True)
    with _request():
        out = _run(_web_search({"query": "x"}))
    assert out["ok"] is False
    assert out["reason"] == "rate_limited"


def test_web_search_in_catalog_and_registered() -> None:
    import services.agent_tools as agent_tools
    from services.agent_tools import catalog, registry_v0_6_0

    assert "web_search" in catalog.CAPABILITY_CATALOG
    cap = catalog.CAPABILITY_CATALOG["web_search"]
    assert cap.read_only is True and cap.domain == "research"
    registry_v0_6_0.register_v0_6_0_tools()
    assert "web_search" in agent_tools.registered_tools()
