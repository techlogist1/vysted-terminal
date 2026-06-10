"""Pass B (B3) — the web_search agent tool + the agent-runtime native dispatch.

R8 (settings-truth): backend selection is ONE resolution path
(``web_search._resolve_backend``). The routing matrix below locks every cell:
{explicit-R7 t1/t2/t3} × {legacy-only byok-exa/local-searxng/native} ×
{no headers} × {managed SearXNG READY / not} — asserting the chosen backend per
cell with the registry and the in-process manager mocked.
"""

from __future__ import annotations

import asyncio
import contextlib

import pytest

import config
from services.agent_tools.web_search import _web_search
from services.search.base import Citation, SearchError, SearchResponse, SearchResult

MANAGED_URL = "http://127.0.0.1:8888"


class _FakeBackend:
    def __init__(self, backend: str = "exa") -> None:
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
    exa_key: str | None = None,
    searxng_url: str | None = None,
    openrouter_key: str | None = None,
    engine: str | None = None,
):
    """Set the full per-request search header state; reset on exit (the
    middleware contract — nothing leaks across requests)."""
    r7_token = config.set_request_research_search_tier(r7)
    search_tokens = config.set_request_search(tier=legacy, exa_key=exa_key, searxng_url=searxng_url)
    or_token = config.set_request_openrouter_search_key(openrouter_key)
    engine_token = config.set_request_hosted_search_engine(engine)
    try:
        yield
    finally:
        config.reset_request_hosted_search_engine(engine_token)
        config.reset_request_openrouter_search_key(or_token)
        config.reset_request_search(search_tokens)
        config.reset_request_research_search_tier(r7_token)


def _stub_registry(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """A registry.resolve stub with REAL availability semantics: ``exa`` needs a
    key, ``searxng`` needs a URL, ``hosted`` needs an OpenRouter key, the
    keyless floor always resolves. Records every call (id + kwargs) so a test
    can assert WHICH lane was consulted and WITH WHAT credential/URL."""
    from services.search import registry

    calls: list[dict] = []

    def _resolve(active_id, **kw):  # noqa: ANN001, ANN003
        calls.append({"id": active_id, **kw})
        if active_id == "exa" and kw.get("exa_key"):
            return _FakeBackend("exa")
        if active_id == "searxng" and kw.get("searxng_url"):
            return _FakeBackend("searxng")
        if active_id == "hosted" and kw.get("openrouter_key"):
            return _FakeBackend("hosted")
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
    """Stub the network autodetect (services.search.searxng.detect_searxng)."""
    from services.search import searxng

    seen: dict = {"called": False, "base": "unset"}

    async def _fake_detect(base=None, *, client=None):  # noqa: ANN001, ANN202
        seen["called"] = True
        seen["base"] = base
        return result

    monkeypatch.setattr(searxng, "detect_searxng", _fake_detect)
    return seen


# --- The R8 routing matrix ----------------------------------------------------
#
# Each cell: (r7 tier, legacy tier, exa key, searxng url, openrouter key,
# manager READY) → the backend id the resolver must choose. ``None`` r7 + None
# legacy = the no-headers cell (the middleware leaves the legacy ContextVar at
# its ``native`` default).

MATRIX = [
    # Explicit R7 t1 — the keyless floor, NEVER the managed instance (the user
    # explicitly chose keyless; using their docker instance would be surprise
    # routing).
    ("t1_local", None, None, None, None, True, "keyless"),
    ("t1_local", None, None, None, None, False, "keyless"),
    # Explicit R7 t3 — hosted with a key, regardless of the manager.
    ("t3_hosted", None, None, None, "sk-or-1", True, "hosted"),
    ("t3_hosted", None, None, None, "sk-or-1", False, "hosted"),
    # Legacy byok-exa with a key — the Exa-direct lane wins over a READY manager.
    (None, "byok-exa", "exa-k", None, None, True, "exa"),
    (None, "byok-exa", "exa-k", None, None, False, "exa"),
    # Legacy byok-exa WITHOUT a key — falls through to the default: managed
    # instance when READY, else the keyless floor.
    (None, "byok-exa", None, None, None, True, "searxng"),
    (None, "byok-exa", None, None, None, False, "keyless"),
    # Legacy local-searxng with an explicit URL — that instance, manager moot.
    (None, "local-searxng", None, "http://10.0.0.5:8080", None, True, "searxng"),
    (None, "local-searxng", None, "http://10.0.0.5:8080", None, False, "searxng"),
    # Legacy native — THE confirmed R7 bug cell: a READY managed SearXNG was
    # bypassed and the run floored to keyless. Now: managed when READY.
    (None, "native", None, None, None, True, "searxng"),
    (None, "native", None, None, None, False, "keyless"),
    # No headers at all (fresh client / non-HTTP entrypoint): same default lane.
    (None, None, None, None, None, True, "searxng"),
    (None, None, None, None, None, False, "keyless"),
]


@pytest.mark.parametrize(
    ("r7", "legacy", "exa_key", "searxng_url", "or_key", "ready", "expected"),
    MATRIX,
)
def test_routing_matrix(
    monkeypatch: pytest.MonkeyPatch,
    r7: str | None,
    legacy: str | None,
    exa_key: str | None,
    searxng_url: str | None,
    or_key: str | None,
    ready: bool,
    expected: str,
) -> None:
    _stub_registry(monkeypatch)
    _set_manager_ready(monkeypatch, ready)
    # The matrix cells above never need the network autodetect; stub it dark so
    # a cell that wrongly reaches it fails loudly (returns no instance).
    _stub_detect(monkeypatch, None)

    with _request(
        r7=r7, legacy=legacy, exa_key=exa_key, searxng_url=searxng_url, openrouter_key=or_key
    ):
        out = _run(_web_search({"query": "nvidia earnings"}))

    assert out["ok"] is True, out
    assert out["backend"] == expected


def test_default_lane_uses_the_managed_instances_own_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The (c) default lane resolves SearXNG with the manager's reported base
    URL — not a guessed port."""
    calls = _stub_registry(monkeypatch)
    _set_manager_ready(monkeypatch, True)

    with _request():
        out = _run(_web_search({"query": "x"}))

    assert out["ok"] is True and out["backend"] == "searxng"
    searxng_calls = [c for c in calls if c["id"] == "searxng"]
    assert searxng_calls and searxng_calls[0]["searxng_url"] == MANAGED_URL


def test_default_lane_reads_manager_in_process_no_network_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default lane must NOT call the network autodetect — the manager's
    state is an instant in-process read."""
    _stub_registry(monkeypatch)
    _set_manager_ready(monkeypatch, True)
    seen = _stub_detect(monkeypatch, None)

    with _request():
        out = _run(_web_search({"query": "x"}))

    assert out["backend"] == "searxng"
    assert seen["called"] is False


def test_r7_t2_explicit_uses_provided_url_over_everything(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _stub_registry(monkeypatch)
    _set_manager_ready(monkeypatch, True)
    seen = _stub_detect(monkeypatch, None)

    with _request(r7="t2_searxng", searxng_url="http://10.0.0.5:8080"):
        out = _run(_web_search({"query": "x"}))

    assert out["ok"] is True and out["backend"] == "searxng"
    searxng_calls = [c for c in calls if c["id"] == "searxng"]
    assert searxng_calls[0]["searxng_url"] == "http://10.0.0.5:8080"
    assert seen["called"] is False  # explicit URL → no autodetect


def test_r7_t2_explicit_autodetects_when_no_url(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_registry(monkeypatch)
    seen = _stub_detect(monkeypatch, MANAGED_URL)

    with _request(r7="t2_searxng"):
        out = _run(_web_search({"query": "x"}))

    assert seen["called"] is True
    assert out["ok"] is True and out["backend"] == "searxng"
    searxng_calls = [c for c in calls if c["id"] == "searxng"]
    assert searxng_calls[0]["searxng_url"] == MANAGED_URL


def test_r7_t2_explicit_fails_honestly_when_nothing_reachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An EXPLICIT t2 that cannot be served names the unlock — never a silent
    re-route to the keyless floor (C.1)."""
    _stub_registry(monkeypatch)
    _set_manager_ready(monkeypatch, False)
    _stub_detect(monkeypatch, None)

    with _request(r7="t2_searxng"):
        out = _run(_web_search({"query": "x"}))

    assert out["ok"] is False
    assert "SearXNG" in out["message"] and "t2" in out["message"]


def test_r7_t3_explicit_fails_honestly_without_openrouter_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_registry(monkeypatch)
    _set_manager_ready(monkeypatch, True)  # a READY manager must NOT mask the t3 miss

    with _request(r7="t3_hosted"):
        out = _run(_web_search({"query": "x"}))

    assert out["ok"] is False
    assert "OpenRouter" in out["message"]


def test_legacy_searxng_lane_autodetect_flows_into_resolve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy local-searxng with no URL probes the autodetect (managed instance
    first, then the conventional ports) and resolves with the detected URL."""
    calls = _stub_registry(monkeypatch)
    seen = _stub_detect(monkeypatch, "http://localhost:8888")

    with _request(legacy="local-searxng"):
        out = _run(_web_search({"query": "x"}))

    assert seen["called"] is True
    assert out["ok"] is True and out["backend"] == "searxng"
    searxng_calls = [c for c in calls if c["id"] == "searxng"]
    assert searxng_calls[0]["searxng_url"] == "http://localhost:8888"


def test_legacy_searxng_lane_floors_when_detection_finds_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_registry(monkeypatch)
    _set_manager_ready(monkeypatch, False)
    _stub_detect(monkeypatch, None)

    with _request(legacy="local-searxng"):
        out = _run(_web_search({"query": "x"}))

    assert out["ok"] is True and out["backend"] == "keyless"


# --- Existing contract (pre-R8) — unchanged behaviours ------------------------


def test_missing_query_is_rejected() -> None:
    out = _run(_web_search({}))
    assert out["ok"] is False and "error" in out


def test_honest_message_when_even_ddg_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.search import registry

    # Defensive path: if EVERY backend (including the ddg floor) fails to resolve,
    # the handler still returns an honest message rather than a fabricated source.
    monkeypatch.setattr(registry, "resolve", lambda *a, **k: None)
    _set_manager_ready(monkeypatch, False)
    with _request(legacy="byok-exa"):
        out = _run(_web_search({"query": "nvidia earnings"}))
    assert out["ok"] is False
    assert "Exa" in out["message"] or "SearXNG" in out["message"]
    assert "search" in out["message"].lower()


def test_ddg_is_the_keyless_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.search import registry

    # byok-exa tier with no key: exa/searxng/keyless resolve to None, so the
    # bare DuckDuckGo floor serves the query — web search is never dark.
    def _resolve(active_id, **_kw):  # noqa: ANN001, ANN003
        return _FakeBackend("ddg") if active_id == "ddg" else None

    monkeypatch.setattr(registry, "resolve", _resolve)
    _set_manager_ready(monkeypatch, False)
    with _request(legacy="byok-exa"):
        out = _run(_web_search({"query": "nvidia earnings"}))
    assert out["ok"] is True
    assert out["backend"] == "ddg"
    assert out["results"][0]["url"] == "https://x.com/a"


def test_dispatch_returns_results_and_citations(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.search import registry

    monkeypatch.setattr(registry, "resolve", lambda *a, **k: _FakeBackend("exa"))
    with _request(legacy="byok-exa", exa_key="exa-k"):
        out = _run(_web_search({"query": "nvidia", "num_results": 3, "category": "financial"}))
    assert out["ok"] is True
    assert out["backend"] == "exa"
    assert out["results"][0]["url"] == "https://x.com/a"
    assert out["citations"][0] == {"url": "https://x.com/a", "title": "A", "excerpt": "snip"}


def test_search_error_becomes_human_message(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.search import registry

    class _Boom:
        backend = "exa"

        async def search(self, query, *, options=None):  # noqa: ANN001, ANN201
            raise SearchError("Exa rejected the key (401) — check your Exa API key.")

    monkeypatch.setattr(registry, "resolve", lambda *a, **k: _Boom())
    with _request(legacy="byok-exa", exa_key="exa-k"):
        out = _run(_web_search({"query": "x"}))
    assert out["ok"] is False and "401" in out["message"]
    # WS3: a plain SearchError (no typed reason) defaults to "unreachable" so the
    # brief reports an honest no-backend miss rather than a transient throttle.
    assert out["reason"] == "unreachable"


def test_search_error_forwards_typed_rate_limit_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WS3: a SearchError tagged ``reason="rate_limited"`` (a transient throttle)
    is surfaced on the failed dict so the brief shows "rate-limited, retrying"
    instead of the false "no backend configured" banner. Pinned on the DEFAULT
    lane (no headers, keyless floor) — the fast-path distinction must survive
    the R8 single-resolution rewrite."""
    from services.search import registry
    from services.search.base import SEARCH_REASON_RATE_LIMITED

    class _Throttled:
        backend = "ddg"

        async def search(self, query, *, options=None):  # noqa: ANN001, ANN201
            raise SearchError(
                "keyless web search is rate-limiting right now — retry shortly",
                reason=SEARCH_REASON_RATE_LIMITED,
            )

    monkeypatch.setattr(registry, "resolve", lambda *a, **k: _Throttled())
    _set_manager_ready(monkeypatch, False)
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
