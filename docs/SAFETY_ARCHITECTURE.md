# Vysted Terminal — Safety Architecture (BLUEPRINT §6.5)

> **Status (2026-05-16, v0.5.0 release):** the dedicated §6.5 8-point safety
> audit suite (`sidecar/tests/test_safety_end_to_end.py`) passes 9/9. Capture
> artifacts live in `docs/screenshots/v0.5.0/safety-audit/`. Live execution
> capability is ENABLED; the conditional-revert clause stays available for
> v0.5.1 if any subsequent audit fails.

Vysted Terminal v0.5.0 places live orders against real brokerage accounts.
BLUEPRINT §6.5 prescribes eight non-negotiable safeguards; each is enforced
in code, at the architectural level rather than by convention, and verified
by the dedicated audit suite that gates each release.

This document is the cross-cutting reference: per-guarantee implementation
file:line pointers, capture-artifact paths, and the revert procedure if any
guarantee fails a future audit.

## The 8 non-negotiables

| #   | Guarantee               | Enforcement                                                      | Audit artifact                                                   |
| --- | ----------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------- |
| 1   | Paper mode default      | `BrokerAdapter.__init__` hard-codes `_mode = "paper"`            | `safety-audit/paper-default-proof.log`                           |
| 2   | Every order confirmed   | `_place_confirmed` is private; only `confirm_and_place` calls it | `safety-audit/no-bypass-proof.log`                               |
| 3   | Position-size limits    | `propose_order` raises `BrokerError` before any broker call      | `safety-audit/position-limit-proof.log`                          |
| 4   | Append-only audit log   | SQLite triggers `RAISE(ABORT)` on UPDATE/DELETE                  | `safety-audit/append-only-proof.log`                             |
| 5   | Global kill switch < 2s | `KillSwitchBus.fire` instruments p50/p95/max; benchmark gate     | `safety-audit/kill-switch-benchmark.json`                        |
| 6   | AI-order gate           | Agent tool registry refuses placement; propose→confirm only      | `safety-audit/ai-order-gate-proof.log`                           |
| 7   | Read-only mode          | `_read_only` flag checked in `propose_order` + at confirm        | `safety-audit/read-only-proof.log`                               |
| 8   | Layered disclaimers     | First-launch + per-broker (keychain) + per-session (sidecar)     | `safety-audit/disclaimer-flow-proof.log` + `static-ip-proof.log` |

## #1 — Paper mode is the hard-coded default

**File**: `sidecar/services/broker_base.py:107` — `self._mode: BrokerMode = "paper"`
inside `BrokerAdapter.__init__`.

**Why architectural, not by convention**: there is no constructor argument
that flips the default. The ONLY path to live mode is `await
adapter.set_mode("live")`, which is gated by the UI's first-live-order
disclaimer (`src/modules/safety/DisclaimerFlow.tsx`).

**Verification**: `test_safety_end_to_end.py::test_audit_1_paper_mode_default`
walks all seven adapter classes + the parametrised ccxt adapter and
asserts `mode == "paper"` immediately after construction. A grep across
`sidecar/services/brokers/` for any `_mode = "live"` line must be empty.

## #2 — Every order is confirmed (no bypass path)

**File**: `sidecar/services/broker_base.py:182` — `BrokerAdapter.propose_order`
returns a `BrokerOrderProposal` and writes an `order-proposed` audit row.

**File**: `sidecar/services/broker_base.py:259` — `BrokerAdapter.confirm_and_place`
requires `human_confirmed: bool`. When `human_confirmed=False` it writes an
`order-declined` audit row and raises `BrokerError`. When `human_confirmed=True`
it re-checks the kill switch + read-only flag, then calls
`_place_confirmed`.

**Architectural property**: `_place_confirmed` is the only method that
actually talks to the broker SDK; it's private (leading underscore by
convention, enforced by inspection grep in `test_audit_2`) and the only
production call site is `confirm_and_place`. There is no path from any
caller — including AI agents and workflow nodes — that places an order
without `human_confirmed=True` being passed in.

## #3 — Position-size limits configurable per plugin

**File**: `sidecar/services/broker_base.py:78` — `BrokerAdapter.DEFAULT_LIMITS`:

- `maxOrderValueAccountCurrency = 10_000`
- `maxPercentOfAccount = 10.0`
- `maxPositionSizePerSymbol = 1_000`
- `dailyLossCircuitBreaker = 2_000`

**Enforcement**: `propose_order` raises `BrokerError` BEFORE any broker
API call if the proposed `quantity * limit_price` exceeds the cap.

**Configurability**: each plugin can override `DEFAULT_LIMITS` at class
definition time; users can raise per-broker limits in plugin settings
(audit-logged as `mode-changed` rows). The `dailyLossCircuitBreaker` is
the canonical example — it flips the adapter to `read_only=True` when
realised + unrealised losses cross the threshold for the day.

## #4 — Audit log append-only at the DB level

**Files**:

- `sidecar/models/audit_log.py:23` — `AUDIT_LOG_DDL` with two triggers:
  - `audit_orders_no_update` BEFORE UPDATE → `RAISE(ABORT, "audit log is append-only: UPDATE not permitted")`
  - `audit_orders_no_delete` BEFORE DELETE → `RAISE(ABORT, "audit log is append-only: DELETE not permitted")`
- `sidecar/services/audit_log.py:55` — writer connection helper
- `sidecar/services/audit_log.py:72` — reader connection helper (`PRAGMA query_only=ON`)

**Why DB-level not convention**: even if a broker adapter mistakenly issued
an UPDATE/DELETE, SQLite would refuse the statement at the driver level.
The trigger fires before the row is touched. The reader connection
additionally enforces `query_only=ON` so a misconfigured reader role
cannot accidentally write either.

**Capture**: `append-only-proof.log` records the literal exception
messages from real `UPDATE` and `DELETE` attempts.

## #5 — Global kill switch < 2s, instrumented

**File**: `sidecar/services/kill_switch.py:104` — `KillSwitchBus.fire`
records `perf_counter_ns` at fire time, dispatches to every subscriber via
`asyncio.gather`, captures per-subscriber ack times, computes p50 / p95 /
max into `KillSwitchFireResult`.

**Mandatory subscribers**: every `BrokerAdapter.__init__` subscribes
(`sidecar/services/broker_base.py:110`); workflow runs subscribe per-run;
pending-proposal handlers subscribe when a proposal is created. There is
no way to instantiate an adapter that skips subscription.

**Audit budget**: the dedicated audit asserts `max_ack_ms < 2000`.
Real measured ack time on the v0.5.0 release configuration (7 brokers +
3 workflows + 2 pending proposals = 12 subscribers): **max_ack_ms ≈ 20 ms**
(p50 ≈ 11 ms, p95 ≈ 20 ms). Capture in `kill-switch-benchmark.json`.

**OS-wide trigger**: in addition to the in-window toolbar button, Vysted
registers `CmdOrCtrl+Shift+K` as an OS-wide keyboard shortcut via
`tauri-plugin-global-shortcut` (`src-tauri/src/kill_switch.rs`). The
shortcut fires even when Vysted is not the focused application.

## #6 — AI-order gate

**Tightened from BLUEPRINT in v0.5.0 (Tier-3 operator-brief override):**
the BLUEPRINT mentions an "optional auto-approve mode" that "exists but
is off by default and must be enabled explicitly, per agent." v0.5.0
ships **NO auto-approve mode at all**. AI agents and workflows can
RECOMMEND orders but CANNOT place them — every order placement is
operator-initiated through the same human-confirmation gate.

**Files**:

- `sidecar/services/agent_tools.py:41` — tool registry. No
  `place_order` / `submit_order` / `execute_order` tool exists. The
  registry only ships `backtest_summary`, `price_data`, `fundamentals`.
- `sidecar/services/broker_base.py:182` — `propose_order` accepts
  `source="ai-agent" | "workflow"` and writes an audit row, but does NOT
  place. The proposal lands in the pending-orders inbox (frontend
  `src/store/orders.ts`).
- `src/modules/safety/OrderConfirmationDialog.tsx` — renders the
  AI-variant of the dialog with Confirm DISABLED by default and a
  banner naming the originating agent. The user must check
  "I reviewed this AI-proposed order" to enable Confirm. No auto-approve
  checkbox is exposed.

**Verification**: `test_audit_6_ai_order_gate` confirms (a) no
order-placing tool is registered, (b) AI-proposed order goes through the
propose → confirm flow, (c) confirm with `human_confirmed=False` raises

- writes `order-declined`, (d) grep for `auto_approve` / `autoApprove`
  assignment patterns finds zero hits.

## #7 — Read-only mode at adapter boundary

**File**: `sidecar/services/broker_base.py:184` — `propose_order` checks
`self._read_only` and raises `BrokerError` BEFORE any other gate, BEFORE
audit-log write, BEFORE broker SDK call.

**File**: `sidecar/services/broker_base.py:269` — `confirm_and_place`
re-checks `read_only` after the human confirms; race-condition safe.

**Use cases**:

- User toggles read-only via `/brokers/{id}/read-only`.
- Kill switch fire sets `_read_only = True` on every adapter (the bus
  handler in `_on_kill_switch`).
- Daily-loss circuit breaker (per `PositionLimits.dailyLossCircuitBreaker`)
  flips to read-only when realised + unrealised loss exceeds the cap.

## #8 — Layered disclaimers

Three surfaces, three storage backends:

| Surface                      | Stored where                                      | Reset condition       |
| ---------------------------- | ------------------------------------------------- | --------------------- |
| First-launch TOS             | OS keychain `broker:_meta:first-launch-tos`       | User deletes app data |
| Per-broker first-connect     | OS keychain `broker:<id>:_meta:first-connect-ack` | User deletes app data |
| First-live-order-per-session | Sidecar in-memory `disclaimer_session`            | Sidecar restart       |

**Files**:

- `src/lib/keychain.ts:30` — `KEYCHAIN_NAMESPACES.broker(id, field)`
  builds the canonical secret-id string.
- `sidecar/services/disclaimer_session.py` — in-memory session store.
- `sidecar/routers/safety.py:115` — `POST /safety/disclaimer-ack` records
  the session ack; audit-logged as `disclaimer-ack`.
- `src/modules/safety/DisclaimerFlow.tsx` — the three UI surfaces.

**Static-IP UX (Kite Connect)**: SEBI/NSE retail-algo compliance (in
effect 2026-04-01) requires a registered static IP for order placement.
The plugin (`src/modules/broker-connect/kite-static-ip-banner.tsx`)
polls `/safety/static-ip-status?configured=<ip>` when Kite is in live
mode. Mismatch → banner; match → no banner; the order placement path
does NOT pre-block (a user behind VPN/VPS with the correct static IP
may still succeed).

## Conditional revert procedure (if any future audit fails)

Operator-brief mandated path. Per the v0.5.0 plan §"Conditional revert":

If `test_safety_end_to_end.py` fails any of audits 1–8 against a new
build:

1. The affected broker's live capability reverts to **read-only-forced**:
   set the adapter's `_read_only = True` in its `__init__` regardless of
   user setting; override `_place_confirmed` to raise:
   ```python
   raise BrokerError(
       f"{self.BROKER_ID}: live execution disabled pending safety-layer "
       "audit fix in v0.5.1 (audit failure: <specific guarantee>)"
   )
   ```
2. **The other brokers and the safety layer foundation still ship.** The
   audit log, kill switch, propose → confirm flow, and read-only paths
   stay live for the unaffected brokers.
3. `BLOCKERS.md` gets a v0.5.1 entry naming the specific safety gap and
   the fix path.
4. `CHANGELOG.md` records the carry-forward at the affected version's
   entry.

The brokers can ship without live execution; **the safety layer cannot
ship broken.**

## Foundation file map

| File                                      | Role                                                                          |
| ----------------------------------------- | ----------------------------------------------------------------------------- |
| `types/safety.ts`                         | Wire-level contracts (TS, foundation-frozen)                                  |
| `types/broker.ts`                         | Broker wire contracts (foundation-frozen)                                     |
| `sidecar/models/safety.py`                | Pydantic mirrors of `types/safety.ts`                                         |
| `sidecar/models/broker.py`                | Pydantic mirrors of `types/broker.ts`                                         |
| `sidecar/models/audit_log.py`             | `AUDIT_LOG_DDL` with append-only triggers                                     |
| `sidecar/services/audit_log.py`           | Writer + reader connection roles; append/tail/export                          |
| `sidecar/services/kill_switch.py`         | `KillSwitchBus` with instrumented `fire`                                      |
| `sidecar/services/broker_base.py`         | `BrokerAdapter` ABC with all 8 enforcements                                   |
| `sidecar/services/static_ip_detector.py`  | Public IP detection helper                                                    |
| `sidecar/services/disclaimer_session.py`  | Session-scoped ack store                                                      |
| `sidecar/routers/safety.py`               | `/safety/*` HTTP surfaces                                                     |
| `src-tauri/src/kill_switch.rs`            | OS-wide `CmdOrCtrl+Shift+K` shortcut + IPC                                    |
| `src/store/safety.ts`                     | Frontend safety state                                                         |
| `src/store/orders.ts`                     | Pending-order proposals inbox                                                 |
| `src/modules/safety/*.tsx`                | KillSwitchToolbar / OrderConfirmationDialog / DisclaimerFlow / AuditLogViewer |
| `src/modules/broker-connect/*.tsx`        | BrokerConnectPanel / BrokerOrderEntry / kite-static-ip-banner                 |
| `sidecar/tests/test_safety_end_to_end.py` | The dedicated audit suite this doc describes                                  |

## Sources

- BLUEPRINT.md §6.4 — Execution liability
- BLUEPRINT.md §6.5 — Safety architecture for execution (8 non-negotiables)
- `docs/superpowers/plans/2026-05-16-phase-4-5-mega-sprint.md` — the v0.5.0 plan
- `docs/BROKER_INTEGRATIONS.md` — per-broker setup + credentials
