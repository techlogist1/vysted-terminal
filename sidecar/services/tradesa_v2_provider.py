"""Tradesa V2 wrapper provider — v0.6.5 read-only Supabase passthrough.

Tradesa V2 (techlogist1/tradesa) has no REST API: its operator interface is
Telegram-only. Its remote-sync state lives in a Supabase project the bot
writes to via ``bridge/supabase_sync.py`` (service_role). This module is the
sidecar-side wrapper Vysted Terminal uses to read that state on the
operator's behalf.

Architectural commitments (BLUEPRINT §3.3 + v0.6.5 brief):

- **Read-only by API surface.** Every public method is a select. There is
  no ``insert_*`` / ``update_*`` / ``delete_*`` / ``upsert_*`` on this
  class, even though the service-role key has full power. A grep-time
  audit asserts this (see :mod:`tests.test_tradesa_v2_provider`).
- **Credentials never leak to the renderer.** The provider receives the
  Supabase URL + service-role-key from the OS keychain at first call,
  stores them in process memory only, and never exposes a getter. The
  router does not echo credentials back.
- **Graceful degradation.** Any Supabase failure is translated into a
  ``TradesaConnectionState`` with a status of ``"supabase-error"`` and a
  human-readable message — Vysted Terminal never crashes on a Tradesa V2
  outage. Heartbeat staleness > 5 minutes maps to ``"bot-offline"``.
- **TTL cache** via :mod:`services.data_cache` shields rate-limited
  upstreams. Conservative TTLs (5s for live tables, 60s for
  ``bot_settings``).

Tradesa V2 ships with RLS deferred to its v0.1.7.0 milestone (see
``CHANGES.md`` in techlogist1/tradesa). Until then, the service-role key
is the operator's chosen external-access path. When RLS lands, this
provider swaps to anon-key + Auth — the API surface is unchanged.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from models.tradesa_v2 import (
    TradesaBotHealth,
    TradesaBotSetting,
    TradesaConnectionState,
    TradesaConnectionStatus,
    TradesaCostRollup,
    TradesaDecision,
    TradesaDiscoveryHypothesis,
    TradesaKillSwitchEvent,
    TradesaMetaAgentRun,
    TradesaReflectionNote,
    TradesaSentinelBlock,
    TradesaSettingsDrift,
    TradesaTrade,
    TradesaTuningProposal,
)
from services import data_cache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache namespaces + TTLs
# ---------------------------------------------------------------------------

_NS = "tradesa-v2"
"""Cache-key namespace so a `data_cache.invalidate("tradesa-v2:")` clears
everything this provider stashed without touching other Phase 6 caches."""

# TTLs picked from Tradesa V2 cadence: bot_settings hot-reloads every 55s
# on the bot side, so 60s is the longest we can wait without showing stale
# config to the operator. Live tables (decisions, trades, health) bypass
# the cache so the panels reflect the freshest state.
_TTL_BOT_SETTINGS_S = 60.0
_TTL_SENTINEL_BLOCKS_S = 5.0
_TTL_COST_ROLLUP_S = 30.0

# Heartbeat-staleness threshold for "bot-offline" classification — matches
# Tradesa V2's seven-watchers staleness-floor design (12h on the bot side,
# but the bot also writes a "starting" heartbeat every 30s minimum). 5
# minutes is a conservative middle ground: catches a hung scheduler
# without misclassifying a busy decision tick as offline.
_HEARTBEAT_STALENESS_S = 300.0


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TradesaProviderError(Exception):
    """Raised when the Tradesa V2 wrapper cannot serve a request.

    Carries a ``status`` field matching ``TradesaConnectionStatus`` so the
    router can map it cleanly to a connection-state response. We never let
    a raw supabase / httpx exception escape — the router treats this class
    as the canonical "Tradesa V2 is unreachable" signal.
    """

    def __init__(self, status: TradesaConnectionStatus, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class TradesaV2Provider:
    """Supabase passthrough wrapper for Tradesa V2 — read-only.

    A new instance is created per (url, key) pair. The router caches the
    instance keyed on a hash of the credentials so the underlying
    supabase-py Client (which keeps an httpx pool open) is reused across
    requests.

    The supabase-py Client itself is constructed lazily on the first
    call so that an unauthenticated state surfaces cleanly via
    :meth:`probe_connection` without paying the import cost.
    """

    def __init__(self, url: str, service_role_key: str) -> None:
        if not url:
            raise ValueError("Tradesa V2 Supabase URL must be non-empty")
        if not service_role_key:
            raise ValueError("Tradesa V2 service-role key must be non-empty")
        self._url = url
        self._service_role_key = service_role_key
        self._client: Any | None = None

    # ----- Internals --------------------------------------------------

    def _get_client(self) -> Any:
        """Return the supabase-py Client, building it on first use."""
        if self._client is None:
            try:
                # Lazy import keeps the cold-start cost off the
                # "unauthenticated" path — the router can return that
                # state without touching supabase-py at all.
                from supabase import create_client
            except ImportError as exc:
                raise TradesaProviderError(
                    "supabase-error",
                    f"supabase-py not installed: {exc}",
                ) from exc
            try:
                self._client = create_client(self._url, self._service_role_key)
            except Exception as exc:
                # supabase-py wraps a wide range of failures (httpx errors,
                # URL parse, auth) — any of these means we can't talk to
                # the upstream. Translate to our canonical error.
                raise TradesaProviderError(
                    "supabase-error",
                    f"supabase client init failed: {exc}",
                ) from exc
        return self._client

    def _select(
        self,
        table: str,
        *,
        columns: str = "*",
        filters: list[tuple[str, str, Any]] | None = None,
        order_by: tuple[str, bool] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Run a select against ``table`` with the given filters.

        ``filters`` is a list of (column, op, value) tuples where ``op`` is
        the supabase-py builder method name (``"eq"``, ``"gt"``, etc.).
        Returns the raw row dicts; the typed callers map them through the
        Pydantic models.

        Every public method goes through this helper — there is no other
        path to the supabase client from the public surface, which keeps
        the read-only invariant in one place.
        """
        client = self._get_client()
        try:
            builder = client.table(table).select(columns)
            for column, op, value in filters or []:
                builder = getattr(builder, op)(column, value)
            if order_by is not None:
                col, desc = order_by
                builder = builder.order(col, desc=desc)
            if limit is not None:
                builder = builder.limit(limit)
            response = builder.execute()
        except TradesaProviderError:
            raise
        except Exception as exc:
            raise TradesaProviderError(
                "supabase-error",
                f"supabase {table} select failed: {exc}",
            ) from exc
        data = getattr(response, "data", None) or []
        if not isinstance(data, list):
            raise TradesaProviderError(
                "supabase-error",
                f"unexpected response shape from {table}: {type(data).__name__}",
            )
        return data

    # ----- Public API (read-only) -------------------------------------

    async def probe_connection(self) -> TradesaConnectionState:
        """Probe Tradesa V2's Supabase + heartbeat freshness.

        Returns a ``TradesaConnectionState`` regardless of outcome — this
        method never raises. The router maps the status into HTTP 200 even
        for degraded states, because "is the bot alive" is what the plugin
        ALWAYS wants to know without paying a try/except for it.
        """
        now_ms = int(datetime.now(UTC).timestamp() * 1000)

        # Step 1: probe Supabase reachability via the heartbeat read.
        try:
            rows = self._select(
                "bot_health",
                order_by=("recorded_at", True),
                limit=1,
            )
        except TradesaProviderError as exc:
            return TradesaConnectionState(
                status=exc.status,
                message=exc.message,
                checked_at=now_ms,
            )

        if not rows:
            return TradesaConnectionState(
                status="bot-offline",
                message="No heartbeat rows in bot_health — Tradesa V2 has never reported.",
                checked_at=now_ms,
            )

        # Step 2: classify heartbeat staleness.
        latest = rows[0]
        recorded_at_raw = latest.get("recorded_at")
        if not recorded_at_raw:
            return TradesaConnectionState(
                status="partial",
                message="bot_health row missing recorded_at — Tradesa V2 schema drift?",
                checked_at=now_ms,
            )
        try:
            recorded_at = _parse_iso(recorded_at_raw)
        except ValueError as exc:
            return TradesaConnectionState(
                status="partial",
                message=f"bot_health recorded_at unparseable: {exc}",
                checked_at=now_ms,
            )
        age_s = (datetime.now(UTC) - recorded_at).total_seconds()
        last_heartbeat_at = int(recorded_at.timestamp() * 1000)

        # Step 3: read kill-switch + mode flags from bot_settings (best-effort).
        bot_mode, kill_switch_engaged = await _read_runtime_flags(self)

        if age_s > _HEARTBEAT_STALENESS_S:
            return TradesaConnectionState(
                status="bot-offline",
                message=f"Heartbeat is {age_s:.0f}s old (threshold {_HEARTBEAT_STALENESS_S:.0f}s).",
                checked_at=now_ms,
                last_heartbeat_at=last_heartbeat_at,
                heartbeat_age_s=age_s,
                bot_mode=bot_mode,
                kill_switch_engaged=kill_switch_engaged,
            )

        return TradesaConnectionState(
            status="healthy",
            message=f"Tradesa V2 heartbeat fresh ({age_s:.0f}s ago).",
            checked_at=now_ms,
            last_heartbeat_at=last_heartbeat_at,
            heartbeat_age_s=age_s,
            bot_mode=bot_mode,
            kill_switch_engaged=kill_switch_engaged,
        )

    async def list_open_trades(self, limit: int = 50) -> list[TradesaTrade]:
        rows = self._select(
            "trades",
            filters=[("status", "eq", "open")],
            order_by=("opened_at", True),
            limit=limit,
        )
        return [TradesaTrade.model_validate(r) for r in rows]

    async def list_closed_trades(self, limit: int = 100) -> list[TradesaTrade]:
        rows = self._select(
            "trades",
            filters=[("status", "eq", "closed")],
            order_by=("closed_at", True),
            limit=limit,
        )
        return [TradesaTrade.model_validate(r) for r in rows]

    async def list_decisions(self, limit: int = 100) -> list[TradesaDecision]:
        rows = self._select(
            "decisions",
            order_by=("timestamp", True),
            limit=limit,
        )
        return [TradesaDecision.model_validate(r) for r in rows]

    async def list_meta_agent_runs(
        self,
        limit: int = 100,
        kind: str | None = None,
    ) -> list[TradesaMetaAgentRun]:
        filters: list[tuple[str, str, Any]] = []
        if kind is not None:
            filters.append(("kind", "eq", kind))
        rows = self._select(
            "meta_agent_runs",
            filters=filters,
            order_by=("started_at", True),
            limit=limit,
        )
        return [TradesaMetaAgentRun.model_validate(r) for r in rows]

    async def get_bot_health_latest(self) -> TradesaBotHealth | None:
        rows = self._select(
            "bot_health",
            order_by=("recorded_at", True),
            limit=1,
        )
        if not rows:
            return None
        return TradesaBotHealth.model_validate(rows[0])

    async def list_bot_settings(self) -> list[TradesaBotSetting]:
        """Return every row from ``bot_settings`` (cached 60s).

        ``bot_settings`` hot-reloads on the Tradesa V2 side every 55s, so
        a 60s TTL is the tightest the wrapper can be while still meaningful.
        """
        cache_key = f"{_NS}:bot_settings:all"
        cached = await data_cache.get(cache_key, _TTL_BOT_SETTINGS_S)
        if cached is not None:
            return [TradesaBotSetting.model_validate(r) for r in cached]
        rows = self._select("bot_settings", order_by=("key", False))
        await data_cache.set(cache_key, rows)
        return [TradesaBotSetting.model_validate(r) for r in rows]

    async def list_sentinel_blocks(self) -> list[TradesaSentinelBlock]:
        cache_key = f"{_NS}:sentinel:blocks"
        cached = await data_cache.get(cache_key, _TTL_SENTINEL_BLOCKS_S)
        if cached is not None:
            return [TradesaSentinelBlock.model_validate(r) for r in cached]
        rows = self._select(
            "sentinel_block_counts",
            order_by=("today_count", True),
        )
        await data_cache.set(cache_key, rows)
        return [TradesaSentinelBlock.model_validate(r) for r in rows]

    async def list_kill_switch_events(self, limit: int = 50) -> list[TradesaKillSwitchEvent]:
        rows = self._select(
            "kill_switch_events",
            order_by=("fired_at", True),
            limit=limit,
        )
        return [TradesaKillSwitchEvent.model_validate(r) for r in rows]

    async def list_tuning_proposals(self, limit: int = 50) -> list[TradesaTuningProposal]:
        rows = self._select(
            "tuning_proposals",
            order_by=("proposed_at", True),
            limit=limit,
        )
        return [TradesaTuningProposal.model_validate(r) for r in rows]

    async def list_discovery_hypotheses(
        self,
        limit: int = 50,
    ) -> list[TradesaDiscoveryHypothesis]:
        rows = self._select(
            "discovery_hypotheses",
            order_by=("proposed_at", True),
            limit=limit,
        )
        return [TradesaDiscoveryHypothesis.model_validate(r) for r in rows]

    async def list_reflection_notes(self, limit: int = 50) -> list[TradesaReflectionNote]:
        rows = self._select(
            "reflection_notes",
            order_by=("created_at", True),
            limit=limit,
        )
        return [TradesaReflectionNote.model_validate(r) for r in rows]

    async def get_cost_today(self) -> TradesaCostRollup:
        """Return today's LLM cost rollup from ``meta_agent_tokens_cost``.

        Cached 30s — the bot updates this row at most every brain tick.
        Falls back to computing from raw ``meta_agent_runs`` if the
        precomputed rollup row is missing (Tradesa V2 v0.2.0+ ships the
        rollup; older snapshots may not have it yet).
        """
        today_iso = datetime.now(UTC).strftime("%Y-%m-%d")
        cache_key = f"{_NS}:cost-today:{today_iso}"
        cached = await data_cache.get(cache_key, _TTL_COST_ROLLUP_S)
        if cached is not None:
            return TradesaCostRollup.model_validate(cached)

        # Try the precomputed rollup table first.
        rollup_rows = self._select(
            "meta_agent_tokens_cost",
            filters=[("date", "eq", today_iso)],
            limit=1,
        )
        if rollup_rows:
            rollup = TradesaCostRollup.model_validate(rollup_rows[0])
            await data_cache.set(cache_key, rollup.model_dump(mode="json"))
            return rollup

        # Fallback: derive from meta_agent_runs.
        run_rows = self._select(
            "meta_agent_runs",
            columns="model,cost_usd",
            filters=[("started_at", "gte", f"{today_iso}T00:00:00Z")],
        )
        by_model: dict[str, float] = {}
        total = 0.0
        for row in run_rows:
            model = str(row.get("model", "unknown"))
            cost = float(row.get("cost_usd", 0.0) or 0.0)
            by_model[model] = by_model.get(model, 0.0) + cost
            total += cost
        rollup = TradesaCostRollup(date=today_iso, by_model=by_model, total_usd=total)
        await data_cache.set(cache_key, rollup.model_dump(mode="json"))
        return rollup

    def compute_settings_drift(
        self,
        previous: list[TradesaBotSetting],
        current: list[TradesaBotSetting],
    ) -> list[TradesaSettingsDrift]:
        """Diff two ``bot_settings`` snapshots and return the drift list.

        Pure function — no I/O, no cache. The router persists the previous
        snapshot in ``data_cache`` under a stable key and passes both
        snapshots in. Returned drift covers keys in ``current`` whose
        ``value`` or ``changed_by`` differs from ``previous``, plus keys
        that appear in ``current`` but not ``previous`` (new keys).
        """
        prev_by_key = {s.key: s for s in previous}
        drifts: list[TradesaSettingsDrift] = []
        for setting in current:
            previous_value = prev_by_key[setting.key].value if setting.key in prev_by_key else None
            if previous_value != setting.value:
                drifts.append(
                    TradesaSettingsDrift(
                        key=setting.key,
                        previous_value=previous_value,
                        current_value=setting.value,
                        changed_at=setting.updated_at,
                        changed_by=setting.changed_by,
                    )
                )
        return drifts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_iso(raw: str) -> datetime:
    """Parse an ISO-8601 string, tolerating Postgres "+00" or trailing Z."""
    s = raw.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    elif len(s) >= 3 and s[-3] == "+" and s[-2:].isdigit():
        s = s + ":00"
    return datetime.fromisoformat(s).astimezone(UTC)


async def _read_runtime_flags(
    provider: TradesaV2Provider,
) -> tuple[Any | None, bool | None]:
    """Best-effort read of paper/live mode + kill-switch flag from bot_settings.

    Returns ``(bot_mode, kill_switch_engaged)``. Both may be ``None`` if
    the bot has not stamped the row yet (early-boot) or the key is missing.
    Failures here do NOT propagate — the connection probe just reports
    them as ``None`` and the panel renders a "—" placeholder.
    """
    try:
        rows = provider._select(
            "bot_settings",
            columns="key,value",
            filters=[("key", "in_", ["is_demo_mode", "kill_switch_engaged"])],
        )
    except TradesaProviderError:
        return None, None

    bot_mode = None
    kill_switch_engaged = None
    for row in rows:
        key = row.get("key")
        raw_value = str(row.get("value", "")).strip().strip('"').lower()
        if key == "is_demo_mode":
            # Tradesa V2 paper mode = Bybit Demo. The wire value is
            # "true"/"false" — coerce to the typed literal.
            bot_mode = "paper" if raw_value in {"true", "1", "yes"} else "live"
        elif key == "kill_switch_engaged":
            kill_switch_engaged = raw_value in {"true", "1", "yes", "engaged"}
    return bot_mode, kill_switch_engaged


# ---------------------------------------------------------------------------
# Audit invariant — read-only API surface
# ---------------------------------------------------------------------------

_FORBIDDEN_METHOD_PREFIXES: tuple[str, ...] = (
    "insert_",
    "update_",
    "delete_",
    "upsert_",
    "write_",
    "place_",
    "submit_",
    "execute_",
    "create_",
)
"""Method prefixes that must NEVER appear on ``TradesaV2Provider``.

The wrapper is read-only by API surface (BLUEPRINT §6.5 + v0.6.5 operator
brief). The audit test in ``tests/test_tradesa_v2_provider.py`` walks the
class via :func:`dir` and asserts no public attribute starts with any of
these prefixes. Adding a new read method is fine; adding a write method
fails the audit. This is one of the three defense-in-depth layers (type
gate at the method level, audit assertion at the class level, contract
gate at the router level — see :mod:`routers.tradesa_v2`).
"""
