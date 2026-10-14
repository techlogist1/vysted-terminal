# Vysted Terminal — Agent-Write Safety (BLUEPRINT §6.5)

> **Status (D81, 23 Sep 2026):** trading was removed from the product
> permanently — no broker connectivity, order placement or simulated account
> exists anywhere. This document now describes the safety model for the
> capability that remains: the agent writing to the user's own workspace
> (panels, chart, watchlist, the tracked portfolio, notes, screens, layouts,
> settings). The no-trading invariant is pinned by
> `sidecar/tests/test_no_trading_surface.py`. History of the removed
> execution-safety model is in `CHANGELOG.md` and in git before the removal
> commit.

Vysted Terminal has no brokerage connection. It cannot place, stage or
simulate a trade, and it has no simulated account. What it _can_ do is act
on the user's local workspace — open panels, set the chart symbol, edit the
watchlist, add or edit tracked-portfolio positions, write notes, save
screens and layouts, and change a small set of settings. BLUEPRINT §6.5
covers the safety model for that write surface.

## 1. What the terminal can and cannot change

- **Cannot**: connect to a broker, place/stage/simulate an order, or read or
  write a simulated brokerage account. There is no code path anywhere in the
  product that does any of this.
- **Can**: run the 18 catalog host actions, grouped by kind:

| Kind         | Host actions                                                                                                                     |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| `panel`      | `open_panel`, `close_panel`, `focus_panel`, `arrange_layout`, `open_company_overview`, `publish_brief`, `write_screener_filters` |
| `chart`      | `set_chart_symbol`, `set_chart_indicators`                                                                                       |
| `watchlist`  | `add_to_watchlist`, `remove_from_watchlist`                                                                                      |
| `data-write` | `portfolio_add_position`, `portfolio_update_position`, `portfolio_delete_position`, `write_note`, `save_layout`, `save_screen`   |
| `settings`   | `set_region`                                                                                                                     |

## 2. The proposed-changes gate

**Files**: `src/store/proposed-changes.ts`, `src/lib/host-actions.ts`,
`src/modules/chat/ProposedChangesReview.tsx`.

Every host action the agent wants to run is staged as a `ProposedChange`
before it lands. Under ASK autonomy, every kind is staged for the user to
accept or reject in the review bar. Under AUTO autonomy, only the
`AUTO_APPLIED_KINDS` set (`panel`, `chart`, `watchlist`) auto-applies on
enqueue; `data-write` and `settings` always wait in the review queue under
either autonomy setting. A persisted AUTO autonomy setting restores with the
workspace blob (`src/lib/workspace.ts`).

## 3. Honest narration and read-back

`sidecar/services/agent_runtime.py` `_build_local_tools` reports each host
action back to the model as `awaiting_user_review` (staged, ASK) or
`dispatched` (sent to the panel, AUTO; the model must verify with
`get_terminal_state` before claiming it landed) — the agent is never told a
change landed when it is still pending. `services/action_ledger.py` is the
in-process read-back store behind `POST /agents/actions/ack`: the frontend
acks how each host action really resolved (`applied` / `kept_previous` /
`failed`, including a rejected change), and the runtime emits an honest
divergence notice at end of stream when a dispatched publish was never
confirmed or the panel kept the previous brief.

## 4. Read-intent strip

On a read turn the runtime strips every mutating tool SERVER-SIDE before the
model sees its tool list (`sidecar/services/agent_runtime.py` `invoke_agent`),
so an external MCP client cannot bypass it. The read intent comes from
`sidecar/services/planner.py` `classify_intent`; whether a tool is mutating
comes from the capability catalog's `read_only` flag. On an inferred read
intent a small read-safe panel allow-list (`_READ_SAFE_PANEL_ACTIONS`:
`open_panel`, `set_chart_symbol`, `set_chart_indicators`, `arrange_layout`,
`add_to_watchlist`) survives so a read answer can still pull up the relevant
chart; those still ride the proposed-changes gate. No `data-write` action
(tracked portfolio, notes, screens, saved layouts) is in that set
(`test_toolbelt_integrity.py`).

## 5. No hands on its own leash

`catalog.FORBIDDEN_TOOL_SUBSTRINGS` (`place_order`, `submit_order`,
`execute_order`, `auto_approve`) may never appear in a capability id; it is
asserted by `test_capability_catalog.py`, the per-module tool tests and the
Gate-8 test (`test_no_trading_surface.py`, which also rejects any
order/broker/margin/trade/paper/kill-switch/audit-shaped id on the catalog,
`TOOL_SCHEMAS`, the custom-agent allow-list, the registry and the MCP
surface). `sidecar/tests/test_toolbelt_integrity.py` additionally forbids any
capability over the agent's own leash (autonomy, keychain, credentials,
secrets).

## 6. Spend ceiling

`sidecar/services/budget_guard.py` `BudgetGuard` meters every round of a
durable Delegate run (tokens, spend, wall-clock, steps) via
`invoke_agent`'s `on_round_usage` callback. The first ceiling breach aborts
the run to `error` with a stated reason and a resumable checkpoint. A
running run can also be stopped directly: `POST /runs/{id}/cancel`.

## 7. Plugins

Plugin safety is host-enforced, not plugin-authored. The
**read-only-wrapper rule** — the contract for any future data-source plugin
— stays exactly as it was under the trading design, because it never
depended on trading:

1. No `insert_/update_/delete_/place_/submit_/execute_/create_…` method on
   the provider's public surface (`inspect.getmembers` audit).
2. No non-GET route on the plugin's router (`router.routes` audit).
3. `capabilities.supportsControlPlane = false`.

## 8. Secrets

BYOK credentials live in the OS keychain (Tauri `keychain_set/get/delete`).
The sidecar cannot read the keychain; the renderer passes a secret in the
request only where a plugin needs one (a header, never the body), and it is
never logged, echoed, or persisted beyond process memory. Transport is
loopback-only.

## 9. Accepted gaps (stated explicitly)

- **No durable record of agent writes.** The former append-only audit log
  (`audit_orders`) existed only to record order placement; it went with the
  feature (§10). The surviving read-back (`action_ledger.py`) is process
  memory with a 10-minute TTL — a host action applied under AUTO autonomy
  has no durable trail after that window. Tracked separately as
  R15-CODE-FRONTEND-013.
- **No stop control for AUTO beyond reject or run-cancel.** There is no
  kill switch any more (§10) and no per-action pause; the available control
  is rejecting a staged change under ASK, or cancelling a running Delegate
  run. Tracked separately as R15-CODE-FRONTEND-008.

## 10. History: what D81 removed

Operator Tier-4 sign-off, 23 Sep 2026 (`docs/redesign/DECISIONS_FOR_OPERATOR.md`
2.3–2.5). The former eight order non-negotiables (paper-mode default,
confirm-before-place, position-size limits, append-only audit log, kill
switch, AI-order gate, read-only mode, layered disclaimers) existed
exclusively to gate broker order placement. The census that decided this
(`docs/redesign/verification/r15/stage-c/REMOVAL_PLAN.md` §0) found:

- the kill-switch bus's only subscriber was `BrokerAdapter.__init__`;
- the only readers of `is_fired` were the order gates;
- nothing in the UI ever fired the kill switch or listened for its event;
- every writer of the append-only audit table was a trading path.

With no orders left, there was nothing left for any of these mechanisms to
gate, so they were deleted rather than kept as dead weight: the broker
adapters and registry, `broker_base.py`, `kill_switch.py`,
`services/audit_log.py`, `disclaimer_session.py`,
`static_ip_detector.py`, the `/brokers/*` and `/safety/*` routers, the
`PositionLimits` settings (`maxPercentOfAccount`,
`dailyLossCircuitBreaker` — never exposed in any settings UI), the
broker-connect and order-review panels, and the OS-wide kill-switch
shortcut. Full inventory, evidence and file-by-file disposition:
`docs/redesign/verification/r15/stage-c/REMOVAL_PLAN.md`. The removal
commits themselves are the reference for exact prior behaviour; reverting
them restores the whole trading layer, but that is not a decision this doc
makes.

## Sources

- BLUEPRINT.md §6.4 — Liability
- BLUEPRINT.md §6.5 — Agent-write safety
- `docs/redesign/verification/r15/stage-c/REMOVAL_PLAN.md` — the D81 removal
  plan and evidence
- `docs/redesign/DECISIONS_FOR_OPERATOR.md` — 2.3, 2.4, 2.5 (closed)
