# Phase 5 Handoff (v0.5.0 → Phase 6)

**Read this first** if you are looking at Phase 5's work. Phase 5 (Broker
Execution + §6.5 Safety Architecture) shipped together with Phase 4 under
one v0.5.0 tag — the mega-sprint compression explained in `CHANGELOG.md`
v0.5.0. This handoff covers Phase 5's slice specifically; Phase 4's is in
`docs/PHASE_4_HANDOFF.md`. The handoff follows the `PHASE_3_HANDOFF.md`
shape that has been the standing convention since v0.4.0.

---

## What Phase 5 shipped (inside v0.5.0)

### Foundation (lead, pre-teammate dispatch)

- **6 broker SDK pins** in `sidecar/requirements.txt`: `dhanhq==2.1.0`,
  `smartapi-python==1.5.5`, `kiteconnect==5.2.0`, `alpaca-py==0.42.0`,
  `ib_async==2.1.0`, `oandapyV20==0.7.2`. ccxt unchanged at 4.5.53.
- **`types/broker.ts`** — `BrokerId` literal union (Dhan / AngelOne /
  Kite / Alpaca / IB / OANDA / ccxt-{bybit,binance,kraken,coinbase}),
  `BrokerMode` (`"paper" | "live"`), `BrokerCapabilities` (with
  `requiresStaticIp` flag — Kite carries `True`), `BrokerOrderSide`,
  `BrokerOrderType`, `BrokerOrderSource` (`"manual" | "ai-agent" |
"workflow"`), `BrokerOrderProposal`, `BrokerOrderResult`,
  `AccountSummary`, `BrokerPosition` (renamed from `Position` to avoid
  colliding with the local-portfolio Position).
- **`types/safety.ts`** — `KillSwitchEvent`, `KillSwitchFireResult` (with
  p50/p95/maxAckMs fields the §6.5 #5 benchmark asserts on),
  `AuditLogEntry`, `AuditLogAction`, `PositionLimits` (with
  `dailyLossCircuitBreaker`), `DisclaimerKind`, `DisclaimerAcknowledgment`,
  `StaticIpStatus`, `AiOrderGateProposal`.
- **`sidecar/models/{broker,safety,audit_log}.py`** — Pydantic mirrors.
  `models/audit_log.py` exports the literal `AUDIT_LOG_DDL` SQL constant
  including the two RAISE(ABORT) triggers on UPDATE/DELETE.
- **`sidecar/services/audit_log.py`** — append-only SQLite store with
  writer + reader connection roles (`PRAGMA query_only=ON` on the
  reader; triggers raise on writer-side UPDATE/DELETE). Public API:
  `append`, `tail`, `range_`, `export_csv`, `count`.
- **`sidecar/services/kill_switch.py`** — async `KillSwitchBus`.
  `fire(reason, fired_by)` dispatches to every subscriber via
  `asyncio.gather`, captures per-subscriber `perf_counter_ns` ack times,
  returns aggregated `KillSwitchFireResult` with p50/p95/max. Idempotent
  on re-fire; reset gated by re-ack route.
- **`sidecar/services/broker_base.py`** — `BrokerAdapter` ABC. The
  constructor hard-codes `_mode = "paper"` and subscribes to the
  kill-switch bus unconditionally. Public surface: `propose_order` →
  `confirm_and_place(human_confirmed: bool)` (re-checks gates at confirm
  time). `_place_confirmed` is the only method that touches the broker
  SDK; private; only callable from `confirm_and_place`. Position limits
  raised before broker call. Kill-switch handler forces read-only +
  audit-logs ack.
- **`sidecar/services/static_ip_detector.py`** — one-shot HTTPx GET to
  `api.ipify.org`. Never raises; returns None on timeout/error.
  `static_ip_status(configured_ip)` composes detected + configured into
  a `StaticIpStatus` with a UI banner message.
- **`sidecar/services/disclaimer_session.py`** — in-memory session-scoped
  store for the first-live-order-per-session ack (resets on sidecar
  restart). The other two disclaimer kinds (first-launch TOS, per-broker
  first-connect) live in the OS keychain.
- **`sidecar/routers/safety.py`** — 8 routes:
  `GET /safety/audit-log` (limit-paginated),
  `GET /safety/audit-log/export.csv` (date-ranged),
  `POST /safety/kill-switch` (fire),
  `POST /safety/kill-switch/reset` (requires acknowledged=true),
  `GET /safety/kill-switch/status`,
  `GET /safety/disclaimer-status`,
  `POST /safety/disclaimer-ack`,
  `GET /safety/static-ip-status?configured=<ip>`.
- **`src-tauri/Cargo.toml`** — `tauri-plugin-global-shortcut = "2"` added.
- **`src-tauri/src/kill_switch.rs`** — registers `CmdOrCtrl+Shift+K` as
  the OS-wide shortcut. Emits a `kill-switch:requested` Tauri event;
  frontend's `useSafetyStore` listens and POSTs to the sidecar's
  `/safety/kill-switch` route. Splits responsibility: Rust owns the OS
  surface, frontend owns the HTTP call (no reqwest dep in Rust). Failure
  to register the shortcut is non-fatal — the toolbar button still works.
- **`src/lib/keychain.ts`** — `KEYCHAIN_NAMESPACES.broker(id, field)`
  added; secret-id format `broker:<id>:<field>` (e.g.
  `broker:alpaca:api_key`). Persisted disclaimer acks reuse the same
  namespace under `broker:_meta:first-launch-tos` and
  `broker:<broker-id>:_meta:first-connect-ack`.

### F9 bundle decision

`pnpm sidecar:build` measured the main sidecar `--onefile` binary post
broker-SDK install: **67.4 MB** (+0.4 MB over v0.4.0's 67 MB; well under
120 MB threshold). **All 7 brokers ship in main sidecar — no subprocess
split required.** The Tauri-Rust-spawn helper (refactored from
`openbb_mcp.rs` precedent) stays available for future broker SDKs that
exceed the threshold.

### Teammate I — India brokers + brokers router + Kite static-IP UX (7 commits)

- `sidecar/services/brokers/{dhan,angelone,kite}.py` — three India
  broker adapters inheriting `BrokerAdapter`. Kite carries
  `CAPABILITIES.requires_static_ip=True`; live-mode toggle fetches
  static-IP status + writes a `mode-changed` audit row whose outcome
  captures matches=ok|static-ip-mismatch.
- `sidecar/services/brokers/__init__.py` — the canonical registry
  package (re-exports all 7 adapter classes; lead hand-merged at G's
  merge to combine with G's minimal version).
- `sidecar/services/brokers/registry.py` — adapter registry + lifecycle.
- `sidecar/routers/brokers.py` — 8-route HTTP surface: connect, account,
  orders (propose), orders/{id}/confirm, mode, read-only, state, cancel.
- `plugins/brokers/{dhan,angelone,kite}/` — VystedPlugin shells.
  `getCommands` (`/connect dhan`, `/dhan-account`, etc.) +
  `executeCommand("place-order"|"halt-trading"|"set-read-only")`.
- `src/modules/broker-connect/kite-static-ip-banner.tsx` + test — polls
  `/safety/static-ip-status?configured=<configured>` when Kite is in
  live mode; renders loading / ok / mismatch / error variants.
- 55 sidecar tests + 26 frontend tests.

### Teammate G — Global brokers (7 commits)

- `sidecar/services/brokers/{alpaca,ib,oanda}.py` — three global broker
  adapters. Alpaca uses `alpaca-py 0.42.0` (NOT the deprecated
  `alpaca-trade-api`). IB uses `ib_async 2.1.0` (NOT `ib_insync`);
  requires TWS or IB Gateway running on `127.0.0.1:7497` (TWS paper) or
  `:4002` (IB Gateway paper) — documented in
  `docs/BROKER_INTEGRATIONS.md`. OANDA uses `oandapyV20 0.7.2`
  (low-maintenance SDK callout).
- Sync SDKs (alpaca-py, oandapyV20) wrapped in `asyncio.to_thread`;
  `ib_async` natively async. No `subprocess.Popen` introduced.
- `plugins/brokers/{alpaca,ib,oanda}/` — VystedPlugin shells with 5
  commands each (connect / account / paper / live / halt) +
  `executeCommand` per the same shape as I.
- `docs/BROKER_INTEGRATIONS.md` — global broker section concatenated
  with I's India broker section at integration time.
- 71 sidecar tests + 22 frontend tests.

### Teammate X — ccxt unified crypto execution (4 commits)

- `sidecar/services/brokers/ccxt_exec.py` — `CcxtExecutionAdapter`
  parametrised by exchange id at construction (`bybit`, `binance`,
  `kraken`, `coinbase`); the `BROKER_ID` is set to `ccxt-<exchange>`
  internally. Capabilities matrix per ccxt class.
- Consumes Phase 1's `sidecar/services/ccxt_provider.py` by COMPOSITION
  only — Phase-1 data layer contract preserved (`git diff` empty on it).
- `plugins/brokers/ccxt-exec/` — VystedPlugin shell with
  `supportsControlPlane=false` on the plugin (order placement goes
  through the safety-gated REST surface; only `/halt ccxt` delegates to
  `/safety/kill-switch`).
- Bybit testnet end-to-end paper-trade produces a full audit trail:
  connection → order-proposed → order-confirmed → order-placed →
  order-cancelled (verified by `sidecar/tests/gen_audit_trail.py`;
  capture in `docs/screenshots/v0.5.0/teammate-x/paper-trade-audit-trail.json`).
- 29 sidecar tests + 11 plugin tests.

### Teammate S — Safety UI surfaces + audit suite (partial: lead-completed)

**Status note**: S's worktree terminated on a "monthly usage limit"
error before pushing its branch. The UI components and stores had
already landed in the lead's main worktree via worktree-sharing (the
agent isolation issue documented in PHASE_4_HANDOFF.md "Coordination
lesson"), so the load-bearing UI surfaces integrated through K's merge
commit. The lead post-merged S's missing deliverables —
`test_safety_end_to_end.py` (9-test dedicated audit suite) and
`docs/SAFETY_ARCHITECTURE.md` — directly from the integrated codebase.

- `src/store/{safety,orders,brokers}.ts` + tests — 23 tests across the
  three stores. `useSafetyStore` tails `/safety/audit-log` + tracks kill
  switch state + disclaimer acks. `useOrdersStore` is the pending-order
  proposals inbox. `useBrokersStore` is the connection-state aggregator.
- `src/modules/safety/{KillSwitchToolbar,OrderConfirmationDialog,
DisclaimerFlow,AuditLogViewer}.tsx` + tests. KillSwitchToolbar listens
  to the Tauri `kill-switch:requested` event AND has its own click
  handler. OrderConfirmationDialog handles manual + AI variants (NO
  auto-approve; per Tier-3 operator-brief tightening). DisclaimerFlow
  surfaces first-launch TOS, per-broker first-connect (both
  keychain-persisted), and first-live-order-per-session (sidecar
  in-memory). AuditLogViewer polls and exports CSV.
- `src/modules/broker-connect/{BrokerConnectPanel,BrokerOrderEntry}.tsx`
  - tests — connect list, status badges, mode badges, manual order entry.
- `sidecar/tests/test_safety_end_to_end.py` (lead-completed) — 9-test
  dedicated audit suite covering all 8 §6.5 non-negotiables; capture
  artifacts in `docs/screenshots/v0.5.0/safety-audit/`.
- `docs/SAFETY_ARCHITECTURE.md` (lead-completed) — cross-cutting
  enforcement reference with file:line pointers + conditional revert
  procedure.

---

## §6.5 audit results

`test_safety_end_to_end.py` 9/9 PASS. Capture artifacts at
`docs/screenshots/v0.5.0/safety-audit/`:

| #   | Guarantee             | Result                                        | Artifact                                        |
| --- | --------------------- | --------------------------------------------- | ----------------------------------------------- |
| 1   | Paper mode default    | PASS (all 7 brokers + ccxt)                   | paper-default-proof.log                         |
| 2   | Every order confirmed | PASS (\_place_confirmed: 1 production caller) | no-bypass-proof.log                             |
| 3   | Position-size limits  | PASS (all 7 raise on violation)               | position-limit-proof.log                        |
| 4   | Audit log append-only | PASS (SQLite triggers raise)                  | append-only-proof.log                           |
| 5   | Kill switch < 2s      | PASS (max 20.08ms / budget 2000ms; 12 subs)   | kill-switch-benchmark.json                      |
| 6   | AI-order gate         | PASS (no place_order tool; no auto_approve)   | ai-order-gate-proof.log                         |
| 7   | Read-only mode        | PASS (all 7 raise in propose_order)           | read-only-proof.log                             |
| 8   | Layered disclaimers   | PASS (session ack records + audit-logs)       | disclaimer-flow-proof.log + static-ip-proof.log |

**Live execution capability is ENABLED in v0.5.0.** Conditional-revert
clause stays available for v0.5.1 (`docs/SAFETY_ARCHITECTURE.md`
"Conditional revert procedure").

---

## Architectural decisions made autonomously (Tier-2/3)

1. **AI-order gate tighter than BLUEPRINT §6.5 #6** (Tier-3). v0.5.0
   ships NO auto-approve mode at all. AI agents and workflows can
   RECOMMEND orders but CANNOT place them; every placement is
   operator-initiated through the same human-confirm gate, per-order,
   not per-session.

2. **Tradesa V2 plugin deferred to v0.5.1 / v0.6.0** (Tier-3). BLUEPRINT
   §7 Phase 5 lists Tradesa V2 + 6 brokers + ccxt; operator brief
   de-scoped Tradesa V2 for v0.5.0 in favour of the 7-broker breadth.
   Foundation contracts (kill switch + audit log + executeCommand
   control plane) are in place; Tradesa V2 becomes plug-in work.

3. **Audit log append-only at DB level via SQLite triggers + connection
   roles** (Tier-3). Not by convention — even a writer connection
   issuing UPDATE/DELETE raises `IntegrityError` with the literal
   trigger message. Reader connection additionally enforces
   `PRAGMA query_only=ON`.

4. **All 7 broker SDKs in main sidecar** (Tier-3, F9). Measured 67.4 MB
   main bundle, well under 120 MB threshold. No subprocess split needed.
   Tauri-Rust-spawn helper stays available for future broker SDKs.

5. **Static-IP detection one-shot, non-blocking** (Tier-3). Kite plugin
   surfaces a banner on mismatch; the order placement path does NOT
   pre-block (a user behind VPN/VPS with the registered IP may still
   succeed; the Kite API rejection at order time surfaces a graceful
   UX dialog through the audit-log path).

6. **Plugin contract held** (Tier-1). `executeCommand` covers broker
   control plane (`"place-order"`, `"halt-trading"`, `"set-read-only"`,
   `"set-mode"`). `git diff v0.4.0..v0.5.0 -- types/plugin.ts` empty.

7. **§6.5 8-point dedicated audit suite as the v0.5.0 release gate**
   (Tier-3). Each test produces a verifiable capture artifact; the audit
   must pass before tag. If a future audit fails, the conditional revert
   procedure in `docs/SAFETY_ARCHITECTURE.md` applies — that broker's
   live capability reverts to read-only-forced, rest still ships.

---

## Known issues carried forward to v0.5.1 (none blocks v0.5.0)

1. **Populated screenshots of S's safety UI surfaces** —
   `docs/screenshots/v0.5.0/teammate-s/` not captured in the v0.5.0
   build window. Non-blocking per CLAUDE.md visual-verification protocol
   (the composed and per-teammate shots from K/N/I/X + audit-suite
   captures cover the load-bearing visual verification).

2. **Tradesa V2 full plugin** (BLUEPRINT §7 Phase 5 scope) — deferred
   to v0.5.1 or v0.6.0 per Tier-3 operator-brief de-scoping.

3. **Live-mode end-to-end verification** — by design, v0.5.0 ships
   paper-mode end-to-end only; the 60-day paper-soak post-tag is the
   live-execution gate.

4. **`OandaAdapter` SDK maintenance** — `oandapyV20` last released
   2021-08; documented in `docs/BROKER_INTEGRATIONS.md`. Users monitor
   SDK security advisories independently. A maintenance audit at each
   release tag will flag reported CVEs.

5. **IB Gateway / TWS dependency** — surfaced cleanly in
   `docs/BROKER_INTEGRATIONS.md`; when neither is running, the IB
   adapter renders a recovery hint in the broker-connect UI rather than
   a stack trace.

---

## Plugin contract status

- **`types/plugin.ts` is unchanged in v0.5.0.** Verified
  `git diff v0.4.0..v0.5.0 -- types/plugin.ts` empty. Tier-1 lock held.
- **`executeCommand` covers the full broker control plane**:
  `"place-order"`, `"halt-trading"`, `"set-read-only"`, `"set-mode"`.
  All seven broker plugins implement this surface uniformly via the
  shell pattern in `plugins/brokers/<id>/index.ts`.
- **`capabilities.contributesPanels` + `getPanels()`** — broker plugins
  do NOT contribute panels in v0.5.0; the BrokerConnectPanel +
  BrokerOrderEntry are HOST surfaces owned by Teammate S. Future
  broker-specific dashboards (Tradesa V2's 9-12 panels for v0.5.1/v0.6.0)
  flow through the existing `contributesPanels` capability.

---

## Phase 6 entry context — where Phase 6 plugs into Phase 5

Per BLUEPRINT §7 Phase 6, the next phase adds: Macro / economic data
panels, SEC filings reader, Earnings calendar, Analyst ratings
aggregator, QuantLib pricing modules, Screener / scanner panel.

Mapping each to existing Phase-5 surfaces:

1. **Macro / economic data panels** — read-only data layer; consumes
   existing `provider_registry` (FRED + ECB + IMF + World Bank routes
   already wired in Phase 1 + openbb-mcp). No broker interaction; no
   §6.5 safety surface needed.

2. **SEC filings reader** — read-only; openbb-mcp SEC provider already
   accessible.

3. **QuantLib pricing modules** — heavy Python dep. Will likely require
   the Tauri-Rust-spawn separate-process pattern (precedent v0.4.0
   `openbb-mcp.rs`; v0.5.0 has no broker subprocess but the helper is
   ready). Apply F9-style bundle-size measurement before deciding.

4. **Screener / scanner panel** — read-only; uses the same data layer +
   indicator engine. No broker side.

5. **Tradesa V2 plugin** (carried forward from Phase 5) — heavy plugin
   work; all six VystedPlugin capabilities; 9-12 panels; real-time
   WebSocket; settings drift + LLM cost tracking. Foundation contracts
   from v0.5.0 are in place.

---

## File / commit pointers for deeper context

- `CHANGELOG.md` v0.5.0 entry — full ship log + decisions + audit results
- `docs/PHASE_4_HANDOFF.md` — companion handoff (Phase 4 slice)
- `docs/SAFETY_ARCHITECTURE.md` — §6.5 enforcement reference
- `docs/BROKER_INTEGRATIONS.md` — per-broker setup + credentials +
  troubleshooting + SDK maintenance callouts
- `docs/superpowers/plans/2026-05-16-phase-4-5-mega-sprint.md` — the
  v0.5.0 plan
- `BLOCKERS.md` — Phase 5.1 / 6 carry-forwards
- `CLAUDE.md` — Phase 5 gotchas appended (worktree contamination, S
  agent usage limit lesson, broker_subprocess_helper precedent)
- **Foundation commits** (lead): 444dd5e, 0c70167, 846885a, 5da3b72,
  b0dc93a, b0b50ac, d837975, 0ee1663
- **Teammate I merge**: `197fc60` (Dhan + Angel One + Kite + brokers
  router + kite-static-ip-banner)
- **Teammate G merge**: `6dc286f` (Alpaca + IB + OANDA + global broker
  shells; also auto-merged S's three stores via worktree sharing)
- **Teammate X merge**: `109e160` (CcxtExecutionAdapter +
  ccxt-exec plugin + Bybit testnet audit trail)
- **Teammate K merge**: `d2fc0b0` (also pulled in S's UI components +
  module registry entries via the same worktree-sharing path)
- **Safety audit + SAFETY_ARCHITECTURE.md**: `e4de55c`

---

## Verification snapshot at handoff

- `pnpm typecheck` / `pnpm lint` / `pnpm format:check` clean.
- `pnpm test` — **406 tests pass** (+194 over v0.4.0's 212).
- `pytest sidecar` — **579 tests pass** (+306 over v0.4.0's 273),
  including the 9-test `test_safety_end_to_end.py` audit suite that
  gates the v0.5.0 release.
- `ruff check sidecar` + `ruff format --check sidecar` clean.
- `cargo fmt --check` + `cargo clippy -- -D warnings` + `cargo test` clean.
- `pnpm sidecar:build` — main sidecar `--onefile` **67.4 MB**.
- `pnpm openbb-mcp-sidecar:build` — unchanged from v0.4.0's 55 MB.
- Total binary footprint ≈ **122 MB**.
- `git diff v0.4.0..v0.5.0 -- types/plugin.ts` **empty**.
- CI green on Win / macOS / Linux.

---

## Coordination lesson for Phase 6+ (Phase 5 slice)

Two integration-time conflicts surfaced during the broker-merge sequence:

1. **`sidecar/services/brokers/__init__.py`** — Teammate I shipped a
   "canonical" version exporting 3 India adapters; Teammate G shipped a
   "minimal" version exporting 3 global adapters. Both wrote `__all__`
   - `from ... import ...` statements. The lead hand-merged into one
     file exporting all 6 adapters + the ccxt adapter (added when X's
     branch merged). Precedent: v0.4.0 `src/store/agents.ts`.

2. **`docs/BROKER_INTEGRATIONS.md`** — I and G both wrote the file from
   scratch. The lead concatenated I's safety architecture overview +
   India broker section with G's global broker section + common-patterns
   - troubleshooting. The doc now covers all 6 brokers; ccxt addition
     landed with X's merge.

**Forward-looking rule for shared "canonical" files** (precedent v0.4.0

- v0.5.0): when two teammates need to write the same file, either (a)
  the plan names ONE primary teammate as owner + others as "extend only,
  do not rewrite", or (b) the secondary teammate's worktree branches
  from the primary's pushed branch instead of from `main`. v0.5.0 plan
  called out the `__init__.py` ownership but the worktree-sharing
  contamination obscured the boundary; cleaner in Phase 6.

The **S agent terminated on a "monthly usage limit"** mid-execution
without pushing its branch. The deliverables were partially salvaged
via worktree sharing (UI components + stores landed); the remaining
audit-suite + safety-architecture doc were lead-completed post-merge.
For Phase 6, agent dispatch should monitor usage-limit proximity and
push intermediate commits more frequently to minimise loss surface.
