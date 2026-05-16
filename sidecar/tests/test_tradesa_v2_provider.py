"""Tests for ``services.tradesa_v2_provider`` — wrapper + read-only audit.

The Tradesa V2 Supabase project is never reached live; instead a fake
``Client`` records every ``.table().select()...execute()`` chain the
provider builds and returns canned row dicts. Assertions cover:

  1. **Read-only audit**: no method on ``TradesaV2Provider`` starts with a
     forbidden write prefix. This is one of three defense-in-depth layers
     (BLUEPRINT §6.5 #2 precedent) enforcing the v0.6.5 read-only contract.
  2. **Method-to-table routing**: each public method hits the right table
     with the right filter / order / limit, so a refactor that swaps a
     table name fails loudly.
  3. **Schema mapping**: row dicts that contain unexpected fields raise
     pydantic ``ValidationError`` via ``extra='forbid'``.
  4. **Graceful degradation**: client init failure, upstream errors, and
     empty responses all surface as ``TradesaProviderError`` with the right
     ``status`` literal.
  5. **Connection probe**: heartbeat staleness classifier returns the
     right ``TradesaConnectionStatus`` for fresh / stale / missing / error.
  6. **Cache reuse**: ``bot_settings`` and ``sentinel_block_counts`` hit
     ``data_cache`` on the second call.
"""

from __future__ import annotations

import asyncio
import inspect
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from services import data_cache
from services.tradesa_v2_provider import (
    _FORBIDDEN_METHOD_PREFIXES,
    TradesaProviderError,
    TradesaV2Provider,
)

# ---------------------------------------------------------------------------
# Fake supabase Client
# ---------------------------------------------------------------------------


class _Response:
    """Minimal stand-in for the supabase-py response object."""

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Builder:
    """Stand-in for supabase-py's query builder — records the chain."""

    def __init__(self, owner: _FakeClient, table: str) -> None:
        self._owner = owner
        # Public introspection fields the test reads — named ``_*`` to avoid
        # colliding with the supabase-py builder method names of the same
        # bare token (``order``, ``limit``).
        self._table = table
        self._columns: str = "*"
        self._filters: list[tuple[str, str, Any]] = []
        self._order_spec: tuple[str, bool] | None = None
        self._limit_val: int | None = None

    # ----- supabase-py chain methods (mutating; return self) ---------

    def select(self, columns: str) -> _Builder:
        self._columns = columns
        return self

    def eq(self, col: str, value: Any) -> _Builder:
        self._filters.append((col, "eq", value))
        return self

    def gt(self, col: str, value: Any) -> _Builder:
        self._filters.append((col, "gt", value))
        return self

    def gte(self, col: str, value: Any) -> _Builder:
        self._filters.append((col, "gte", value))
        return self

    def in_(self, col: str, value: Any) -> _Builder:
        self._filters.append((col, "in_", value))
        return self

    def order(self, col: str, *, desc: bool = False) -> _Builder:
        self._order_spec = (col, desc)
        return self

    def limit(self, n: int) -> _Builder:
        self._limit_val = n
        return self

    # ----- Back-compat properties for assertion readability ----------

    @property
    def table(self) -> str:
        return self._table

    @property
    def filters(self) -> list[tuple[str, str, Any]]:
        return self._filters

    @property
    def columns(self) -> str:
        return self._columns

    @property
    def order_spec(self) -> tuple[str, bool] | None:
        """Assertion-side accessor for the stored order clause."""
        return self._order_spec

    @property
    def limit_val(self) -> int | None:
        return self._limit_val

    def execute(self) -> _Response:
        return self._owner._answer_for(self)


class _FakeClient:
    """Stand-in for the supabase-py Client. Captures every chain it builds."""

    def __init__(self) -> None:
        self.chains: list[_Builder] = []
        self.responses: dict[str, list[dict[str, Any]]] = {}
        self.error_on: set[str] = set()

    def respond(self, table: str, rows: list[dict[str, Any]]) -> None:
        self.responses[table] = rows

    def raise_on(self, table: str) -> None:
        self.error_on.add(table)

    def table(self, name: str) -> _Builder:
        builder = _Builder(self, name)
        self.chains.append(builder)
        return builder

    def _answer_for(self, builder: _Builder) -> _Response:
        if builder.table in self.error_on:
            raise RuntimeError(f"simulated supabase failure on {builder.table}")
        return _Response(self.responses.get(builder.table, []))


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> _FakeClient:
    """Install a fake supabase Client + return it for assertions."""
    fc = _FakeClient()

    def _fake_create_client(_url: str, _key: str) -> _FakeClient:
        return fc

    # Patch at the lazy-import site inside the provider so the test does not
    # require supabase-py to be importable.
    import sys
    import types

    if "supabase" not in sys.modules:
        fake_module = types.ModuleType("supabase")
        fake_module.create_client = _fake_create_client  # type: ignore[attr-defined]
        sys.modules["supabase"] = fake_module
    else:
        monkeypatch.setattr("supabase.create_client", _fake_create_client)

    return fc


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    """Each test runs against an empty data cache (avoids cross-test bleed)."""
    asyncio.get_event_loop().run_until_complete(data_cache.clear())
    yield
    asyncio.get_event_loop().run_until_complete(data_cache.clear())


def _provider() -> TradesaV2Provider:
    return TradesaV2Provider("https://example.supabase.co", "fake-service-role-key")


# ---------------------------------------------------------------------------
# 1. Read-only audit invariant
# ---------------------------------------------------------------------------


def test_no_write_methods_on_provider_surface() -> None:
    """Audit: no public method name starts with a forbidden write prefix.

    This is one of the three defense-in-depth layers enforcing v0.6.5's
    read-only contract (type-gate at the wrapper, audit at the class,
    contract at the router). New write methods would either fail this
    test or have to deliberately bypass the grep — both visible signals.
    """
    methods = [
        name
        for name, _ in inspect.getmembers(TradesaV2Provider, predicate=callable)
        if not name.startswith("_")
    ]
    forbidden = [
        name for name in methods for prefix in _FORBIDDEN_METHOD_PREFIXES if name.startswith(prefix)
    ]
    assert not forbidden, (
        f"Tradesa V2 wrapper is read-only by API surface (v0.6.5 brief); "
        f"forbidden methods detected: {forbidden}"
    )


def test_compute_settings_drift_is_pure_function() -> None:
    """``compute_settings_drift`` is a non-async classifier — no I/O path."""
    method = inspect.getattr_static(TradesaV2Provider, "compute_settings_drift")
    assert not asyncio.iscoroutinefunction(method)


# ---------------------------------------------------------------------------
# 2. Constructor + validation
# ---------------------------------------------------------------------------


def test_constructor_rejects_empty_url() -> None:
    with pytest.raises(ValueError, match="URL must be non-empty"):
        TradesaV2Provider("", "key")


def test_constructor_rejects_empty_key() -> None:
    with pytest.raises(ValueError, match="key must be non-empty"):
        TradesaV2Provider("https://x.supabase.co", "")


# ---------------------------------------------------------------------------
# 3. Method-to-table routing
# ---------------------------------------------------------------------------


def test_list_open_trades_hits_trades_table_with_open_filter(fake_client: _FakeClient) -> None:
    fake_client.respond("trades", [])
    asyncio.get_event_loop().run_until_complete(_provider().list_open_trades(limit=25))
    chain = fake_client.chains[0]
    assert chain.table == "trades"
    assert ("status", "eq", "open") in chain.filters
    assert chain.order_spec == ("opened_at", True)
    assert chain.limit_val == 25


def test_list_closed_trades_filters_status_closed(fake_client: _FakeClient) -> None:
    fake_client.respond("trades", [])
    asyncio.get_event_loop().run_until_complete(_provider().list_closed_trades())
    assert ("status", "eq", "closed") in fake_client.chains[0].filters


def test_list_decisions_targets_decisions_table(fake_client: _FakeClient) -> None:
    fake_client.respond("decisions", [])
    asyncio.get_event_loop().run_until_complete(_provider().list_decisions())
    assert fake_client.chains[0].table == "decisions"


def test_list_meta_agent_runs_optionally_filters_kind(fake_client: _FakeClient) -> None:
    fake_client.respond("meta_agent_runs", [])
    asyncio.get_event_loop().run_until_complete(_provider().list_meta_agent_runs(kind="director"))
    assert ("kind", "eq", "director") in fake_client.chains[0].filters


def test_get_bot_health_latest_orders_descending_limit_1(fake_client: _FakeClient) -> None:
    fake_client.respond("bot_health", [])
    asyncio.get_event_loop().run_until_complete(_provider().get_bot_health_latest())
    chain = fake_client.chains[0]
    assert chain.table == "bot_health"
    assert chain.order_spec == ("recorded_at", True)
    assert chain.limit_val == 1


def test_list_kill_switch_events_orders_descending(fake_client: _FakeClient) -> None:
    fake_client.respond("kill_switch_events", [])
    asyncio.get_event_loop().run_until_complete(_provider().list_kill_switch_events())
    assert fake_client.chains[0].order_spec == ("fired_at", True)


def test_list_sentinel_blocks_targets_correct_table(fake_client: _FakeClient) -> None:
    fake_client.respond("sentinel_block_counts", [])
    asyncio.get_event_loop().run_until_complete(_provider().list_sentinel_blocks())
    assert fake_client.chains[0].table == "sentinel_block_counts"


# ---------------------------------------------------------------------------
# 4. Schema mapping (extra='forbid')
# ---------------------------------------------------------------------------


def test_decision_row_with_extra_field_raises(fake_client: _FakeClient) -> None:
    fake_client.respond(
        "decisions",
        [
            {
                "id": "abc",
                "action": "HOLD",
                "instrument": "BTCUSDT",
                "leverage": 4,
                "confidence": 0.5,
                "rationale": "x" * 30,
                "timestamp": "2026-05-17T12:00:00Z",
                "created_at": 1_747_488_000_000,
                "rogue_field": "shape-drift",
            }
        ],
    )
    with pytest.raises(ValidationError, match="rogue_field|extra_forbidden|forbid"):
        asyncio.get_event_loop().run_until_complete(_provider().list_decisions())


def test_decision_row_happy_path_maps_to_model(fake_client: _FakeClient) -> None:
    fake_client.respond(
        "decisions",
        [
            {
                "id": "abc",
                "action": "OPEN_LONG",
                "instrument": "BTCUSDT",
                "size_pct": 0.07,
                "leverage": 4,
                "stop_loss_pct": 0.03,
                "trailing_mode": "step_up",
                "confidence": 0.78,
                "rationale": "long entry on RSI hook",
                "timestamp": "2026-05-17T12:00:00Z",
                "created_at": 1_747_488_000_000,
            }
        ],
    )
    decisions = asyncio.get_event_loop().run_until_complete(_provider().list_decisions())
    assert len(decisions) == 1
    assert decisions[0].action == "OPEN_LONG"
    assert decisions[0].size_pct == 0.07


# ---------------------------------------------------------------------------
# 5. Graceful degradation — supabase / client / row failure paths
# ---------------------------------------------------------------------------


def test_supabase_query_error_raises_typed_provider_error(fake_client: _FakeClient) -> None:
    fake_client.raise_on("trades")
    with pytest.raises(TradesaProviderError) as exc_info:
        asyncio.get_event_loop().run_until_complete(_provider().list_open_trades())
    assert exc_info.value.status == "supabase-error"
    assert "trades" in str(exc_info.value)


def test_client_init_failure_surfaces_supabase_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """If supabase.create_client raises, we translate to TradesaProviderError."""
    import sys
    import types

    failing_module = types.ModuleType("supabase")

    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("auth failed")

    failing_module.create_client = _boom  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "supabase", failing_module)

    provider = _provider()
    with pytest.raises(TradesaProviderError) as exc_info:
        asyncio.get_event_loop().run_until_complete(provider.list_open_trades())
    assert exc_info.value.status == "supabase-error"


# ---------------------------------------------------------------------------
# 6. Connection probe / heartbeat classification
# ---------------------------------------------------------------------------


def _heartbeat_row(seconds_ago: float, status: str = "running") -> dict[str, Any]:
    when = datetime.now(UTC) - timedelta(seconds=seconds_ago)
    return {
        "recorded_at": when.isoformat(),
        "service": "tradesa-bot",
        "status": status,
        "detail": None,
        "fd_count": 32,
        "thread_count": 8,
        "uptime_s": 3600.0,
    }


def test_probe_connection_healthy_with_fresh_heartbeat(fake_client: _FakeClient) -> None:
    fake_client.respond("bot_health", [_heartbeat_row(30)])
    fake_client.respond(
        "bot_settings",
        [
            {"key": "is_demo_mode", "value": "true"},
            {"key": "kill_switch_engaged", "value": "false"},
        ],
    )
    state = asyncio.get_event_loop().run_until_complete(_provider().probe_connection())
    assert state.status == "healthy"
    assert state.heartbeat_age_s is not None and state.heartbeat_age_s < 60
    assert state.bot_mode == "paper"
    assert state.kill_switch_engaged is False


def test_probe_connection_bot_offline_when_heartbeat_stale(fake_client: _FakeClient) -> None:
    fake_client.respond("bot_health", [_heartbeat_row(900)])  # 15 min ago
    fake_client.respond("bot_settings", [])
    state = asyncio.get_event_loop().run_until_complete(_provider().probe_connection())
    assert state.status == "bot-offline"
    assert state.heartbeat_age_s is not None and state.heartbeat_age_s > 300


def test_probe_connection_bot_offline_when_no_heartbeat_rows(fake_client: _FakeClient) -> None:
    fake_client.respond("bot_health", [])
    state = asyncio.get_event_loop().run_until_complete(_provider().probe_connection())
    assert state.status == "bot-offline"
    assert "never reported" in state.message.lower()


def test_probe_connection_supabase_error_when_query_fails(fake_client: _FakeClient) -> None:
    fake_client.raise_on("bot_health")
    state = asyncio.get_event_loop().run_until_complete(_provider().probe_connection())
    assert state.status == "supabase-error"


def test_probe_connection_partial_when_recorded_at_missing(fake_client: _FakeClient) -> None:
    fake_client.respond(
        "bot_health",
        [
            {
                "service": "tradesa-bot",
                "status": "running",
                "detail": None,
                "fd_count": 32,
                "thread_count": 8,
                "uptime_s": 3600.0,
                # recorded_at deliberately missing
            }
        ],
    )
    state = asyncio.get_event_loop().run_until_complete(_provider().probe_connection())
    assert state.status == "partial"


# ---------------------------------------------------------------------------
# 7. Cache reuse
# ---------------------------------------------------------------------------


def test_bot_settings_cached_on_second_call(fake_client: _FakeClient) -> None:
    fake_client.respond(
        "bot_settings",
        [
            {
                "key": "leverage_default",
                "value": "4",
                "description": "default leverage",
                "updated_at": "2026-05-17T12:00:00Z",
                "changed_by": "operator",
            }
        ],
    )
    p = _provider()
    asyncio.get_event_loop().run_until_complete(p.list_bot_settings())
    asyncio.get_event_loop().run_until_complete(p.list_bot_settings())
    # Exactly one supabase chain — second call served from data_cache.
    chains_on_bot_settings = [c for c in fake_client.chains if c.table == "bot_settings"]
    assert len(chains_on_bot_settings) == 1


def test_sentinel_blocks_cached(fake_client: _FakeClient) -> None:
    fake_client.respond("sentinel_block_counts", [])
    p = _provider()
    asyncio.get_event_loop().run_until_complete(p.list_sentinel_blocks())
    asyncio.get_event_loop().run_until_complete(p.list_sentinel_blocks())
    chains = [c for c in fake_client.chains if c.table == "sentinel_block_counts"]
    assert len(chains) == 1


# ---------------------------------------------------------------------------
# 8. Settings drift detection
# ---------------------------------------------------------------------------


def test_drift_detects_value_change() -> None:
    from models.tradesa_v2 import TradesaBotSetting

    previous = [
        TradesaBotSetting(
            key="leverage_default",
            value="3",
            description=None,
            updated_at="2026-05-16T00:00:00Z",
            changed_by="operator",
        ),
    ]
    current = [
        TradesaBotSetting(
            key="leverage_default",
            value="4",
            description=None,
            updated_at="2026-05-17T00:00:00Z",
            changed_by="operator",
        ),
    ]
    drifts = _provider().compute_settings_drift(previous, current)
    assert len(drifts) == 1
    assert drifts[0].key == "leverage_default"
    assert drifts[0].previous_value == "3"
    assert drifts[0].current_value == "4"


def test_drift_returns_empty_when_no_change() -> None:
    from models.tradesa_v2 import TradesaBotSetting

    setting = TradesaBotSetting(
        key="leverage_default",
        value="4",
        description=None,
        updated_at="2026-05-17T00:00:00Z",
        changed_by="operator",
    )
    drifts = _provider().compute_settings_drift([setting], [setting])
    assert drifts == []


def test_drift_treats_new_key_as_drift() -> None:
    from models.tradesa_v2 import TradesaBotSetting

    new_setting = TradesaBotSetting(
        key="brand_new_key",
        value="x",
        description=None,
        updated_at="2026-05-17T00:00:00Z",
        changed_by="bootstrap",
    )
    drifts = _provider().compute_settings_drift([], [new_setting])
    assert len(drifts) == 1
    assert drifts[0].previous_value is None
    assert drifts[0].current_value == "x"


# ---------------------------------------------------------------------------
# 9. Cost rollup
# ---------------------------------------------------------------------------


def test_cost_today_uses_precomputed_rollup_when_available(fake_client: _FakeClient) -> None:
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    fake_client.respond(
        "meta_agent_tokens_cost",
        [
            {
                "date": today,
                "by_model": {"deepseek-v3-pro": 0.12, "gemini-2-flash": 0.03},
                "total_usd": 0.15,
            }
        ],
    )
    rollup = asyncio.get_event_loop().run_until_complete(_provider().get_cost_today())
    assert rollup.total_usd == pytest.approx(0.15)
    assert rollup.by_model["deepseek-v3-pro"] == pytest.approx(0.12)


def test_cost_today_falls_back_to_runs_when_rollup_missing(fake_client: _FakeClient) -> None:
    fake_client.respond("meta_agent_tokens_cost", [])
    fake_client.respond(
        "meta_agent_runs",
        [
            {"model": "deepseek-v3-pro", "cost_usd": 0.10},
            {"model": "deepseek-v3-pro", "cost_usd": 0.02},
            {"model": "gemini-2-flash", "cost_usd": 0.03},
        ],
    )
    rollup = asyncio.get_event_loop().run_until_complete(_provider().get_cost_today())
    assert rollup.total_usd == pytest.approx(0.15)
    assert rollup.by_model["deepseek-v3-pro"] == pytest.approx(0.12)
