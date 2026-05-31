# Agent-native redesign — P1–P3 build report

_Branch `001-agent-native-redesign`. Build window: 2026-05-31. Lead: Opus; teammate
agents for sidecar data, sidecar budget/runs, and settings. This report is the
per-FR/SC accounting, autonomous-decision trail, gate snapshot, and operator-eyeball
list for the three user-facing phases built on top of the foundation window
(`FOUNDATION_BUILD_REPORT.md`)._

## 1. What shipped

**P1 — agent-centric experience (US1–US4).** A four-mode agent spine — Ask,
Edit-panel, Build, Delegate (⌥1–4, `types/agent-modes.ts`) — with the agent as a
co-equal primary surface (`AgentDock`, `ModeBar`, `AgentHud`, `AgentsRail`) beside the
preserved hand-driven cockpit. **Every agent-proposed mutation routes through a
diff/accept trust gate** (`src/store/proposed-changes.ts`): the four host-actions
(`open_panel`, `set_chart_symbol`, `add_to_watchlist`, `propose_order` — the catalog's
only `read_only=false` capabilities) enqueue a `ProposedChange` and never apply until
explicit accept. Offer-both onboarding keeps the keyboard-only path.

**P2 — framework + visual + marketplace (US5–US7, US10).** A minimal-dark
"cold-instrument" shell (re-valued design tokens; `chart-theme.ts` re-mirrored), a
teaching command palette, and status chrome surfacing sidecar/provider/agent state
(FR-033). The **plugin marketplace is the primary extensibility model**
(`src/lib/marketplace.ts`, `src/store/marketplace.ts`, `src/modules/marketplace/`):
brokers, data providers, panels, and agents are all install/enable/configure/remove
entries under one lifecycle. First-party entries are pre-installed (yfinance + news,
keyless); **no broker is registered at boot** — `bootstrap_default_adapters()` is no
longer called from the sidecar lifespan (FR-051); Kite is the reference broker plugin.

**P3 — data + durable agents (US8/US9, FR-033–042).**

- **Provider-shaped data registry** (`provider_registry.py`) resolves by a standard
  model key + preference order rather than a hardcoded asset-class chain; every result
  carries its serving provider as provenance (FR-035/040).
- **BYOK credentials hub** = the marketplace config form, rendered generically from
  each entry's `credentialFields` (SC-007: zero per-source UI). News is now a
  first-party data plugin (`plugins/vysted-news`) declaring an OPTIONAL NewsAPI key;
  the key is read from the OS keychain and sent as the `X-Vysted-Newsapi-Key` header
  (FR-036), never the body/persisted. RSS is the keyless default ("needs no key").
- **Granular broker reads** (FR-042/SC-012): `GET /brokers/{id}/{positions,holdings,
margins}` return DISTINCT shapes (`sidecar/models/broker_reads.py`,
  `types/broker-reads.ts`) via an adapter `positions_info`/`holdings_info`/
  `margins_info` seam — Kite implements it, others fall back to the account summary.
  Each result is provenance-labeled so paper/synthetic values are badged
  (`BrokerReadsSection`); routes are GET-only, no write/execution path.
- **Durable Delegate runs** (US9): `run_manager.py` + `runs_store.py` (SQLite) +
  `budget_guard.py` + `routers/runs.py`. Runs execute detached and survive the
  launching connection; the frontend `delegate-runs.ts` poller mirrors live
  cost-so-far + status into the agents rail. A **BudgetGuard** enforces four hard
  ceilings (tokens/spend/wall/steps); the first breach aborts the run to `error` with a
  stated reason and a resumable checkpoint (SC-008). `BudgetConfig` sets the ceiling
  before launch; pause/answer/resume is the human-in-the-loop control plane (FR-028).
- **Cursor-grade settings + remappable keybindings** (`src/store/settings.ts`,
  `src/store/keybindings.ts`): exhaustive preferences + user-remappable bindings with
  conflict detection, both persisted in the workspace blob (FR-038/039).

## 2. Per-success-criterion accounting

| SC                                                                         | Status                                                      | Evidence                                                                                                                                |
| -------------------------------------------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| SC-001 conversational populated cockpit                                    | Built; **eyeball** the <2 min / zero-control timing         | Ask/Build host-actions apply via the gate; populated cockpit reachable through chat                                                     |
| SC-002 full workflow, zero agent turns, persists                           | Built; **eyeball** the live workflow                        | command palette + panels + workspace-blob persistence (kept from baseline)                                                              |
| SC-003 100% mutations gated, no auto-apply                                 | **Verified**                                                | diff gate (`proposed-changes.ts`); §6.5 audit 9/9; host-actions are the only `read_only=false` caps; FORBIDDEN-substring grep clean     |
| SC-004 capability reachable by copilot + MCP, same name                    | **Verified**                                                | `test_mcp_catalog_parity` green incl. new `list_runs` MCP tool                                                                          |
| SC-005 multi-round on every provider                                       | **Verified**                                                | `test_agent_runtime` (Gemini name-pairing) green                                                                                        |
| SC-006 0 handlers lack catalog entry                                       | **Verified**                                                | `test_capability_catalog` green                                                                                                         |
| SC-007 new source → hub + registry, 0 per-source UI, provenance            | **Verified (structural)**                                   | `vysted-news` renders via generic `credentialFields`; `provider_registry` resolves by model key + provenance (`test_provider_registry`) |
| SC-008 budget abort 100% + reason + checkpoint + cost visible              | **Verified**                                                | `test_run_manager` asserts breach → `error` + reason + resumable checkpoint; rail shows cost-so-far                                     |
| SC-009 ≤3 taught gestures, palette shortcut ≥90%                           | Built; **eyeball** the onboarding                           | teaching palette + remappable keybindings                                                                                               |
| SC-010 no data leaves machine; secrets never logged/echoed                 | **Verified (structural)**; **eyeball** a full log audit     | keychain is the only credential path; news/broker keys ride headers; `test_<plugin>_router` asserts no echo                             |
| SC-011 every pref configurable; remap + export persist                     | **Verified (structural)**; **eyeball** cross-machine import | `settings.test`, `keybindings.test`, `workspace.test`; bindings persist in the blob                                                     |
| SC-012 distinct real broker reads, labeled, no write path                  | **Verified** (paper + audit); **eyeball** a live broker     | `broker_reads.py` + Kite `*_info` + GET-only audit; `test_kite_granular_reads`; live distinctness needs real creds                      |
| SC-013 broker install/enable/configure/remove via marketplace; no boot reg | **Verified**                                                | `bootstrap_default_adapters()` not called at boot; marketplace lifecycle tests                                                          |
| SC-014 plugin cannot bypass safety gate                                    | **Verified**                                                | read-only-wrapper audits (no write methods / no non-GET routes / `supportsControlPlane=false`); §6.5 host-enforced 9/9                  |
| SC-015 runtime enforces manifest/version + secret resolution               | **Verified**                                                | `plugin-runtime.test` (id/version + `requiredHostVersion` rejected at load; `PluginConfig` secret resolution)                           |

## 3. Autonomous decisions (Tier-2/3)

- **News as a first-party data marketplace plugin** (`vysted-news`) so its NewsAPI key
  renders through the one credentials hub (FR-034/050), vs. a bespoke news-key UI.
  _(Tier-3 — DNA: the marketplace is the single extension model.)_
- **Durable runs = detached sidecar runs + frontend polling**, not websocket
  streaming — durability without a new streaming contract. _(Tier-2.)_
- **BudgetGuard spend = tokens × price-table estimate** (over-estimate is the safe side
  of a hard ceiling); unknown model → `$5/1M` default, never a silent zero for a metered
  provider; Ollama = `$0`. Explicitly an estimate, not a billed figure. _(Tier-3.)_
- **`on_round_usage` callback on `invoke_agent`** to meter every round — lower blast
  radius than a new event type or SSE-consumer change; touches no model/event union.
  _(Tier-2.)_
- **Granular-read dual-case serialization** (camelCase + snake*case on every `GET /runs`
  / launch response) so the snake-only frontend poller works as-written AND the camel
  contract holds. *(Tier-2.)\_
- **Keybindings dedup**: removed the dead `workspace.save` seed (unwired duplicate) and
  repointed its unit test to the wired `platform.save-workspace` command, resolving the
  mod+s conflict the conflict-detector flagged. _(Tier-2.)_
- **HITL autonomous self-pause deferred** (an agent-invoked `ask_user` tool needs a new
  catalog capability + §6.5/parity audits); the explicit pause→answer→resume control
  plane is shipped and tested. _(Tier-3 — within the brief's "if a full HITL handshake
  is too deep, implement pause/answer and document the scope" allowance.)_
- **Version NOT bumped** — all sources read `0.8.0` consistently (nothing stale to fix);
  a bump is a release/merge decision and is premature on an unmerged feature branch.
  **Flagged for the operator** (§5).

## 4. Verification gate snapshot

- **`pnpm ci-local`** (venv-active) — **PASS (exit 0)**: install `--frozen-lockfile` →
  ensure-all-sidecars (3 binaries built) → lint → format:check → typecheck → cargo fmt →
  clippy `-D warnings` → ruff → vitest **743 passed** → cargo test → **pytest 1048
  passed**.
- **`node scripts/smoke-test-sidecars.mjs`** — **PASS (exit 0)**: all three built
  sidecars boot cleanly (main `/health` + screener universe OK; `openbb-mcp` and
  `sec-edgar-mcp` bind their ports and survive the settle window).
- **§6.5 audit** (`test_safety_end_to_end.py`) — **9/9**.
- **Tier-1 LOCKED set** (`types/plugin.ts`, `types/safety.ts`, `types/broker.ts`, the
  safety/broker/audit/kill-switch models, `broker_base.py`, `kill_switch.rs`, the §6.5
  test, `tauri.conf.json`, CI workflows) — **byte-for-byte untouched** (empty
  `git diff` vs. the P2 commit).
- **Read-surface audits** — broker `positions/holdings/margins` are GET-only; no
  `place_/submit_/execute_order`/`auto_approve` in any P3 runs code.

## 5. Operator must-eyeball / decisions

1. **Live UX (SC-001/002/009):** the <2-minute conversational cockpit, the zero-agent-turn
   keyboard workflow, and the ≤3-taught-gesture onboarding need a running app + a human.
2. **Live broker distinctness (SC-012):** real Kite creds are needed to see live
   positions ≠ holdings ≠ margins; the paper-mode synthetic path is tested + badged.
3. **Cross-machine settings export/import (SC-011):** needs two machines.
4. **Visual capture:** the new minimal-dark shell + populated panels at 1920×1080 and
   2560×1440 (the visual-verification convention; the old warm-cockpit anchor is
   superseded).
5. **Genuinely-external plugin load:** static-export compiles plugins in; a never-compiled
   third-party plugin attaches over the stdio-MCP framework path — that runtime-load is
   unexercised here.
6. **Version bump at merge/release:** the redesign warrants a minor/major bump; left to
   the operator (grep the five version sources + `cargo update -p vysted-terminal`).

## 6. Issues carried forward

- **MCP cold-bind ~34 s** isolated (`MCP_PORT_WAIT_SECS=45`); the `--onedir` true fix is
  deferred (pre-existing; see `BLOCKERS.md`).
- **`kill-switch-benchmark.json` churn:** the kill-switch perf test rewrites this
  committed artifact with fresh timing numbers on every run (result stays `PASS`). It was
  reverted out of the P3 commit; the test-hygiene fix (write to a scratch path) is
  pre-existing and out of scope here.
- **HITL autonomous self-pause** (`ask_user` tool) deferred as in §3.

No hard blockers.
