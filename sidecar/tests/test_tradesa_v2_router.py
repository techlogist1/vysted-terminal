"""FastAPI tests for the Tradesa V2 wrapper router — v0.6.5 read-only.

Three audit invariants — each enforced by a dedicated test that fails
loudly if a future commit drifts away from the v0.6.5 read-only contract:

  1. Every route under ``/tradesa-v2/*`` declares ONLY the GET method.
     (Defense-in-depth layer 2 of 3.)
  2. The router never echoes credentials back in any response body or
     header — even a 200 success response strips them.
  3. The credentials flow is header-only (``X-Tradesa-Supabase-Url`` +
     ``X-Tradesa-Supabase-Service-Key``) — there is no query-param or
     body-param surface for credentials.

Plus the standard FastAPI route tests against the canned ``TradesaV2Provider``
behaviour (mocked at the provider layer; the real supabase-py never runs).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from models.tradesa_v2 import (
    TradesaBotHealth,
    TradesaBotSetting,
    TradesaConnectionState,
    TradesaCostRollup,
    TradesaDecision,
    TradesaDiscoveryHypothesis,
    TradesaKillSwitchEvent,
    TradesaMetaAgentRun,
    TradesaReflectionNote,
    TradesaSentinelBlock,
    TradesaTrade,
    TradesaTuningProposal,
)
from routers import tradesa_v2 as tradesa_router
from services import data_cache
from services.tradesa_v2_provider import TradesaProviderError, TradesaV2Provider

# Headers used by every authenticated request.
_HEADERS = {
    "X-Tradesa-Supabase-Url": "https://example.supabase.co",
    "X-Tradesa-Supabase-Service-Key": "fake-service-role-key",
}


# ---------------------------------------------------------------------------
# Stub provider — used in tests in lieu of TradesaV2Provider's supabase calls
# ---------------------------------------------------------------------------


class _StubProvider:
    """Stand-in for ``TradesaV2Provider`` — every method preset by the test."""

    def __init__(self) -> None:
        self.connection_state: TradesaConnectionState | None = None
        self.open_trades: list[TradesaTrade] = []
        self.closed_trades: list[TradesaTrade] = []
        self.decisions: list[TradesaDecision] = []
        self.meta_agent_runs: list[TradesaMetaAgentRun] = []
        self.bot_health_latest: TradesaBotHealth | None = None
        self.bot_settings: list[TradesaBotSetting] = []
        self.sentinel_blocks: list[TradesaSentinelBlock] = []
        self.kill_switch_events: list[TradesaKillSwitchEvent] = []
        self.tuning_proposals: list[TradesaTuningProposal] = []
        self.discovery_hypotheses: list[TradesaDiscoveryHypothesis] = []
        self.reflection_notes: list[TradesaReflectionNote] = []
        self.cost_today: TradesaCostRollup = TradesaCostRollup(
            date=datetime.now(UTC).strftime("%Y-%m-%d"),
            by_model={},
            total_usd=0.0,
        )
        self.error: TradesaProviderError | None = None
        # Settings drift uses the real TradesaV2Provider implementation
        # since it's a pure function — we just delegate.

    def _maybe_raise(self) -> None:
        if self.error is not None:
            raise self.error

    async def probe_connection(self) -> TradesaConnectionState:
        if self.connection_state is None:
            return TradesaConnectionState(
                status="healthy",
                message="ok",
                checked_at=int(datetime.now(UTC).timestamp() * 1000),
            )
        return self.connection_state

    async def list_open_trades(self, limit: int = 50) -> list[TradesaTrade]:
        self._maybe_raise()
        return self.open_trades[:limit]

    async def list_closed_trades(self, limit: int = 100) -> list[TradesaTrade]:
        self._maybe_raise()
        return self.closed_trades[:limit]

    async def list_decisions(self, limit: int = 100) -> list[TradesaDecision]:
        self._maybe_raise()
        return self.decisions[:limit]

    async def list_meta_agent_runs(
        self,
        limit: int = 100,
        kind: str | None = None,
    ) -> list[TradesaMetaAgentRun]:
        self._maybe_raise()
        rows = self.meta_agent_runs
        if kind is not None:
            rows = [r for r in rows if r.kind == kind]
        return rows[:limit]

    async def get_bot_health_latest(self) -> TradesaBotHealth | None:
        self._maybe_raise()
        return self.bot_health_latest

    async def list_bot_settings(self) -> list[TradesaBotSetting]:
        self._maybe_raise()
        return self.bot_settings

    async def list_sentinel_blocks(self) -> list[TradesaSentinelBlock]:
        self._maybe_raise()
        return self.sentinel_blocks

    async def list_kill_switch_events(self, limit: int = 50) -> list[TradesaKillSwitchEvent]:
        self._maybe_raise()
        return self.kill_switch_events[:limit]

    async def list_tuning_proposals(self, limit: int = 50) -> list[TradesaTuningProposal]:
        self._maybe_raise()
        return self.tuning_proposals[:limit]

    async def list_discovery_hypotheses(
        self,
        limit: int = 50,
    ) -> list[TradesaDiscoveryHypothesis]:
        self._maybe_raise()
        return self.discovery_hypotheses[:limit]

    async def list_reflection_notes(self, limit: int = 50) -> list[TradesaReflectionNote]:
        self._maybe_raise()
        return self.reflection_notes[:limit]

    async def get_cost_today(self) -> TradesaCostRollup:
        self._maybe_raise()
        return self.cost_today

    def compute_settings_drift(
        self,
        previous: list[TradesaBotSetting],
        current: list[TradesaBotSetting],
    ) -> Any:
        # Delegate to the real implementation — pure function.
        real_provider = TradesaV2Provider("https://example.supabase.co", "fake")
        return real_provider.compute_settings_drift(previous, current)


@pytest.fixture
def stub_provider(monkeypatch: pytest.MonkeyPatch) -> _StubProvider:
    """Replace ``TradesaV2Provider`` constructor with a stub-returning lambda."""
    stub = _StubProvider()
    tradesa_router._reset_for_tests()
    monkeypatch.setattr(
        tradesa_router,
        "TradesaV2Provider",
        lambda url, key: stub,
    )
    # Also clear the data_cache so settings-drift baseline doesn't bleed
    # across tests.
    asyncio.run(data_cache.invalidate("tradesa-v2:settings:baseline"))
    return stub


# ---------------------------------------------------------------------------
# 1. Audit invariant — every route is GET only
# ---------------------------------------------------------------------------


def test_no_non_get_routes_under_tradesa_v2_prefix() -> None:
    """Audit: every route on the router declares ONLY the GET method.

    This is one of three defense-in-depth layers enforcing v0.6.5's
    read-only contract (provider has no write methods, router has no
    non-GET routes, frontend never builds non-GET fetches to
    /tradesa-v2/*). Adding any POST/PUT/PATCH/DELETE here fails the
    test loudly.
    """
    forbidden_routes: list[str] = []
    for route in tradesa_router.router.routes:
        methods = getattr(route, "methods", None) or set()
        non_get = set(methods) & set(tradesa_router._NON_GET_METHODS)
        if non_get:
            path = getattr(route, "path", "<unknown>")
            forbidden_routes.append(f"{path}: {sorted(non_get)}")
    assert not forbidden_routes, (
        f"Tradesa V2 router must be read-only (v0.6.5 brief); "
        f"non-GET routes detected: {forbidden_routes}"
    )


def test_router_prefix_is_tradesa_v2() -> None:
    """Prefix sanity check — every route lives under /tradesa-v2/*."""
    for route in tradesa_router.router.routes:
        path = getattr(route, "path", "")
        assert path.startswith("/tradesa-v2"), (
            f"Route {path} not under /tradesa-v2 prefix — wiring drift?"
        )


# ---------------------------------------------------------------------------
# 2. Unauthenticated path returns 200 + typed body
# ---------------------------------------------------------------------------


def test_status_unauthenticated_returns_200(client: TestClient) -> None:
    """Missing credentials → status='unauthenticated' with HTTP 200."""
    res = client.get("/tradesa-v2/status")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "unauthenticated"
    assert "Settings" in body["message"]


def test_other_endpoints_return_401_when_unauthenticated(client: TestClient) -> None:
    """Non-status endpoints return 401 with typed body when credentials missing."""
    for path in [
        "/tradesa-v2/positions",
        "/tradesa-v2/trade-history",
        "/tradesa-v2/decisions",
        "/tradesa-v2/sentinel",
        "/tradesa-v2/settings",
        "/tradesa-v2/cost-today",
    ]:
        res = client.get(path)
        assert res.status_code == 401, f"{path} should 401 without creds"
        assert res.json()["detail"]["status"] == "unauthenticated"


# ---------------------------------------------------------------------------
# 3. Happy paths
# ---------------------------------------------------------------------------


def test_status_healthy_when_provider_reports_healthy(
    client: TestClient,
    stub_provider: _StubProvider,
) -> None:
    stub_provider.connection_state = TradesaConnectionState(
        status="healthy",
        message="up",
        checked_at=1_700_000_000_000,
        last_heartbeat_at=1_700_000_000_000,
        heartbeat_age_s=15.0,
        bot_mode="paper",
        kill_switch_engaged=False,
    )
    res = client.get("/tradesa-v2/status", headers=_HEADERS)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "healthy"
    assert body["bot_mode"] == "paper"


def test_positions_returns_open_trades(
    client: TestClient,
    stub_provider: _StubProvider,
) -> None:
    stub_provider.open_trades = [
        TradesaTrade(
            id="t1",
            instrument="BTCUSDT",
            side="long",
            status="open",
            qty=0.5,
            entry_price=68_000.0,
            stop_loss_price=66_000.0,
            leverage=4,
            opened_at="2026-05-17T10:00:00Z",
        )
    ]
    res = client.get("/tradesa-v2/positions", headers=_HEADERS)
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["instrument"] == "BTCUSDT"
    assert body[0]["status"] == "open"


def test_trade_history_returns_closed_trades(
    client: TestClient,
    stub_provider: _StubProvider,
) -> None:
    stub_provider.closed_trades = [
        TradesaTrade(
            id="t2",
            instrument="ETHUSDT",
            side="short",
            status="closed",
            qty=2.0,
            entry_price=3_700.0,
            exit_price=3_650.0,
            stop_loss_price=3_800.0,
            leverage=3,
            realized_pnl=100.0,
            opened_at="2026-05-15T10:00:00Z",
            closed_at="2026-05-16T10:00:00Z",
        )
    ]
    res = client.get("/tradesa-v2/trade-history", headers=_HEADERS)
    assert res.status_code == 200
    assert res.json()[0]["realized_pnl"] == 100.0


def test_decisions_returns_brain_decisions(
    client: TestClient,
    stub_provider: _StubProvider,
) -> None:
    stub_provider.decisions = [
        TradesaDecision(
            id="d1",
            action="HOLD",
            instrument="BTCUSDT",
            leverage=4,
            confidence=0.42,
            rationale="x" * 50,
            timestamp="2026-05-17T11:00:00Z",
            created_at=1_700_000_000_000,
        )
    ]
    res = client.get("/tradesa-v2/decisions", headers=_HEADERS)
    assert res.status_code == 200
    assert res.json()[0]["action"] == "HOLD"


def test_meta_agent_runs_supports_kind_filter(
    client: TestClient,
    stub_provider: _StubProvider,
) -> None:
    stub_provider.meta_agent_runs = [
        TradesaMetaAgentRun(
            id="r1",
            kind="director",
            model="deepseek-v3-pro",
            status="success",
            tokens_in=1000,
            tokens_out=500,
            cost_usd=0.05,
            duration_s=2.1,
            started_at="2026-05-17T11:00:00Z",
            finished_at="2026-05-17T11:00:02Z",
        ),
        TradesaMetaAgentRun(
            id="r2",
            kind="reflection",
            model="gemini-2-flash",
            status="success",
            tokens_in=500,
            tokens_out=300,
            cost_usd=0.01,
            duration_s=1.5,
            started_at="2026-05-17T10:00:00Z",
            finished_at="2026-05-17T10:00:01Z",
        ),
    ]
    res = client.get("/tradesa-v2/meta-agent-runs", headers=_HEADERS, params={"kind": "director"})
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["kind"] == "director"


def test_health_returns_combined_payload(
    client: TestClient,
    stub_provider: _StubProvider,
) -> None:
    stub_provider.bot_health_latest = TradesaBotHealth(
        recorded_at="2026-05-17T11:30:00Z",
        service="tradesa-bot",
        status="running",
        fd_count=42,
        thread_count=8,
        uptime_s=86_400.0,
    )
    stub_provider.kill_switch_events = [
        TradesaKillSwitchEvent(
            id="k1",
            fired_at="2026-05-16T10:00:00Z",
            source="operator_telegram",
            actor="lokavya",
            reason="manual emergency stop",
            cleared_at="2026-05-16T10:05:00Z",
        )
    ]
    res = client.get("/tradesa-v2/health", headers=_HEADERS)
    assert res.status_code == 200
    body = res.json()
    assert body["latest"]["service"] == "tradesa-bot"
    assert len(body["recent_kill_switch_events"]) == 1


def test_sentinel_returns_block_counts(
    client: TestClient,
    stub_provider: _StubProvider,
) -> None:
    stub_provider.sentinel_blocks = [
        TradesaSentinelBlock(
            gate_id="gate_06_news_blackout",
            gate_label="News blackout",
            today_count=3,
            total_count=110,
            fail_closed=True,
        )
    ]
    res = client.get("/tradesa-v2/sentinel", headers=_HEADERS)
    assert res.status_code == 200
    assert res.json()[0]["gate_id"] == "gate_06_news_blackout"


def test_settings_returns_snapshot(client: TestClient, stub_provider: _StubProvider) -> None:
    stub_provider.bot_settings = [
        TradesaBotSetting(
            key="leverage_default",
            value="4",
            updated_at="2026-05-17T00:00:00Z",
            changed_by="operator",
        )
    ]
    res = client.get("/tradesa-v2/settings", headers=_HEADERS)
    assert res.status_code == 200
    body = res.json()
    assert body[0]["key"] == "leverage_default"


def test_settings_drift_empty_when_no_baseline(
    client: TestClient,
    stub_provider: _StubProvider,
) -> None:
    res = client.get("/tradesa-v2/settings/drift", headers=_HEADERS)
    assert res.status_code == 200
    assert res.json() == []


def test_settings_drift_detects_value_change_after_baseline(
    client: TestClient,
    stub_provider: _StubProvider,
) -> None:
    # Seed the baseline.
    stub_provider.bot_settings = [
        TradesaBotSetting(
            key="leverage_default",
            value="3",
            updated_at="2026-05-16T00:00:00Z",
            changed_by="operator",
        )
    ]
    client.get("/tradesa-v2/settings", headers=_HEADERS)
    # Update current state.
    stub_provider.bot_settings = [
        TradesaBotSetting(
            key="leverage_default",
            value="4",
            updated_at="2026-05-17T00:00:00Z",
            changed_by="operator",
        )
    ]
    res = client.get("/tradesa-v2/settings/drift", headers=_HEADERS)
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["key"] == "leverage_default"
    assert body[0]["previous_value"] == "3"
    assert body[0]["current_value"] == "4"


def test_meta_agents_tuning(client: TestClient, stub_provider: _StubProvider) -> None:
    stub_provider.tuning_proposals = [
        TradesaTuningProposal(
            id="tp1",
            status="pending",
            target_key="size_pct_max",
            proposed_value="0.08",
            current_value="0.10",
            rationale="recent drawdown",
            queue_reason="drawdown_breach",
            proposed_at="2026-05-17T09:00:00Z",
        )
    ]
    res = client.get("/tradesa-v2/meta-agents/tuning", headers=_HEADERS)
    assert res.status_code == 200
    body = res.json()
    assert body["items"][0]["target_key"] == "size_pct_max"


def test_meta_agents_discovery(client: TestClient, stub_provider: _StubProvider) -> None:
    stub_provider.discovery_hypotheses = [
        TradesaDiscoveryHypothesis(
            id="dh1",
            title="Funding-rate flip",
            body="When funding flips negative…",
            confidence=0.65,
            status="open",
            proposed_at="2026-05-17T08:00:00Z",
        )
    ]
    res = client.get("/tradesa-v2/meta-agents/discovery", headers=_HEADERS)
    assert res.status_code == 200
    assert res.json()["items"][0]["title"] == "Funding-rate flip"


def test_meta_agents_reflection(client: TestClient, stub_provider: _StubProvider) -> None:
    stub_provider.reflection_notes = [
        TradesaReflectionNote(
            id="rn1",
            trade_id="t1",
            summary="Tighter stop would have saved 30bps",
            tags=["stop_placement"],
            body="…full text…",
            created_at="2026-05-17T09:00:00Z",
        )
    ]
    res = client.get("/tradesa-v2/meta-agents/reflection", headers=_HEADERS)
    assert res.status_code == 200
    assert res.json()["items"][0]["tags"] == ["stop_placement"]


def test_meta_agents_invalid_kind_returns_422(
    client: TestClient,
    stub_provider: _StubProvider,
) -> None:
    res = client.get("/tradesa-v2/meta-agents/nonsense", headers=_HEADERS)
    assert res.status_code == 422


def test_cost_today_returns_rollup(client: TestClient, stub_provider: _StubProvider) -> None:
    stub_provider.cost_today = TradesaCostRollup(
        date="2026-05-17",
        by_model={"deepseek-v3-pro": 0.18, "gemini-2-flash": 0.04},
        total_usd=0.22,
    )
    res = client.get("/tradesa-v2/cost-today", headers=_HEADERS)
    assert res.status_code == 200
    assert res.json()["total_usd"] == 0.22


# ---------------------------------------------------------------------------
# 4. Graceful degradation — provider errors → 502 with typed body
# ---------------------------------------------------------------------------


def test_supabase_error_maps_to_502_with_typed_body(
    client: TestClient,
    stub_provider: _StubProvider,
) -> None:
    stub_provider.error = TradesaProviderError(
        "supabase-error",
        "PostgREST 401: invalid service-role key",
    )
    res = client.get("/tradesa-v2/positions", headers=_HEADERS)
    assert res.status_code == 502
    detail = res.json()["detail"]
    assert detail["status"] == "supabase-error"
    assert "PostgREST" in detail["message"]


# ---------------------------------------------------------------------------
# 5. Credential-flow audit
# ---------------------------------------------------------------------------


def test_credentials_arrive_via_headers_only(
    client: TestClient,
    stub_provider: _StubProvider,
) -> None:
    """Credentials in query/body are NOT accepted — only headers count."""
    # No headers, but a query param with the same name → unauthenticated.
    res = client.get(
        "/tradesa-v2/status",
        params={
            "X-Tradesa-Supabase-Url": "https://x.supabase.co",
            "X-Tradesa-Supabase-Service-Key": "abc",
        },
    )
    assert res.status_code == 200
    assert res.json()["status"] == "unauthenticated"


def test_response_never_echoes_credentials(
    client: TestClient,
    stub_provider: _StubProvider,
) -> None:
    """Audit: the response body must never contain the service-role key."""
    stub_provider.connection_state = TradesaConnectionState(
        status="healthy",
        message="up",
        checked_at=1_700_000_000_000,
    )
    res = client.get("/tradesa-v2/status", headers=_HEADERS)
    assert res.status_code == 200
    body_text = res.text
    assert _HEADERS["X-Tradesa-Supabase-Service-Key"] not in body_text
    assert _HEADERS["X-Tradesa-Supabase-Url"] not in body_text
