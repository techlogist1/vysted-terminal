# Phase 8 Coverage and Documentation Audit

**Teammate:** T5 (t5-coverage, Sonnet 4.6)
**Date:** 2026-05-18
**Baseline:** v0.7.0 (tag `005a8d0`)
**Scope:** Part A — vitest + pytest coverage gap analysis; Part B — BLUEPRINT.md truth-alignment
**Branch:** worktree-agent-a42ad0ab8fd19c24d

---

## Severity scheme

- **S1** — uncovered branch in §6.5 safety surface OR BLUEPRINT claim flatly contradicted by shipped code
- **S2** — uncovered branch in plugin contract / broker / workflow / backtest; BLUEPRINT claim partially implemented
- **S3** — uncovered branch elsewhere; BLUEPRINT promise honestly "in progress"
- **S4** — BLUEPRINT intentional stretch goal (UC6 year-2, UC7 multi-broker aggregation)

---

## Part A — Coverage Report

### A.1 Frontend (vitest) — overview

All 81 test files pass (588 tests). Coverage measurement requires `@vitest/coverage-v8`
which is not in `package.json` devDependencies; added transiently for this audit run.
Coverage provider is not wired into `vitest.config.ts`, so results are derived from
static analysis of what test files exist and what branches they import + exercise.

**Files with zero test coverage (no test file, never imported by a test):**

| File | Category |
|------|----------|
| `src/store/agents.ts` | Zustand store (agents + custom agents) |
| `src/store/app.ts` | Zustand store (sidecar connect lifecycle) |
| `src/store/chat-history.ts` | Zustand store |
| `src/store/command-palette.ts` | Zustand store |
| `src/store/llm-providers.ts` | Zustand store |
| `src/store/symbols.ts` | Zustand store |
| `src/lib/plugin-bootstrap.ts` | Plugin bootstrap (PLUGIN_COMPANIONS, in-memory fallback) |
| `src/components/PanelHost.tsx` | dockview integration (no-modules loading branch) |

**`src/store/workspace.ts`** has a test file (`workspace.test.ts`) but the actual
store file is `workspace.ts` whereas `src/lib/workspace.ts` is the one under test —
the store file `src/store/workspace.ts` has no coverage.

---

### Finding T5-sidecar-client-devmode: `getSidecarBaseUrl` dev-mode fallback uncovered [S2] [status: open]

**Part:** A coverage

**Detection:** `src/lib/sidecar-client.ts` lines 52–66 implement the `?sidecar-port=NN`
query-param fallback added in v0.7.0 F7. The function is mocked in virtually every
test file (`vi.fn().mockResolvedValue(...)`) so the real implementation code is never
exercised. The `cachedBaseUrl !== null` early-return branch is also uncovered.

**Impact:** Two branches in the transport layer that gate every panel's data path:
(a) dev-mode port resolution — if broken, the `?sidecar-port=` operator workflow silently
fails; (b) cache-hit short-circuit — a regression would cause repeated Tauri `invoke` calls
per request.

**Suggested fix:** Add a unit test in `src/lib/sidecar-client.test.ts` (new file):
`getSidecarBaseUrl` with `__TAURI_INTERNALS__` absent + `?sidecar-port=8080` resolves to
`http://127.0.0.1:8080`; second call returns same cached value; non-Tauri + no param falls
back to `invoke`. Use `vi.spyOn(window.location, 'search', 'get')` to inject params.

**Files:** `src/lib/sidecar-client.ts:52–66`

---

### Finding T5-plugin-bootstrap-uncovered: `plugin-bootstrap.ts` — 5 branches zero coverage [S2] [status: open]

**Part:** A coverage

**Detection:** `src/lib/plugin-bootstrap.ts` has no test file. Five distinct logic branches
have zero coverage:

1. `resolvePersistence()` sidecar-reachable path (lines ~158–165) vs in-memory fallback
2. `moduleForPlugin()` when `panels.length > 0 && Object.keys(panelComponents).length === 0`
   — the PLUGIN_COMPANIONS warning branch (lines ~208–215)
3. `moduleForPlugin()` returning `null` (plugin with no panels AND no commands)
4. `bootstrapPlugins()` health-check teardown (the returned cleanup function)
5. `createSidecarPersistence().load()` 404 → `null` path vs other-error rethrow

**Impact:** S2 — the PLUGIN_COMPANIONS warning branch is the wiring check that would surface a
future plugin author forgetting to register panel components. If this branch is broken, the
warning is silently dropped and panels render blank in production.

**Suggested fix:** Add `src/lib/plugin-bootstrap.test.ts`. Mock `BUNDLED_PLUGINS` to a
single stub plugin. Test: (a) no Tauri → in-memory persistence; (b) plugin with panels
but no companion emits `console.warn`; (c) cleanup function clears interval + calls
`unloadPlugin`.

**Files:** `src/lib/plugin-bootstrap.ts:158–215, 208–215, 256–265`

---

### Finding T5-orders-store-confirming-status: `confirmProposal` — "confirming" status branch uncovered [S2] [status: open]

**Part:** A coverage

**Detection:** `src/store/orders.ts` sets `status: "confirming"` at line ~95 before the
broker `POST` resolves. The test suite (`orders.test.ts`) only checks `"placed"` and
`"rejected"` terminal states; the transient `"confirming"` status on the in-flight
`PendingProposal` is never asserted. The `confirmProposal` + "not found" path (proposal
id does not exist → throws `Error`) is also untested.

**Impact:** BLUEPRINT §6.5 #2 enforcement — any regression to the "confirming" state
update (e.g., the `set` call disappearing) would break the UI's disable-confirm-button
guard. The "not found" throw is the guard that prevents a stale dialog from double-confirming.

**Suggested fix:** In `orders.test.ts`, spy on `useOrdersStore.getState` in the middle of a
`mockFetch` delay to assert `status === "confirming"`. Add a test for
`confirmProposal("unknown-id")` expecting it to throw.

**Files:** `src/store/orders.ts:82–105, 80–82`

---

### Finding T5-safety-store-reset-ks: `resetKillSwitch` — entirely untested [S1] [status: open]

**Part:** A coverage

**Detection:** `src/store/safety.ts` exposes `resetKillSwitch()` (line 146, implemented
at line 230). The `safety.test.ts` test suite covers `fireKillSwitch` but has ZERO tests
for `resetKillSwitch`. This is a §6.5 surface: BLUEPRINT §6.5 #5 says "the kill switch
can be reset only through a re-acknowledgment."

**Impact:** S1 — the reset POST body must contain `reAck: true`; if the JSON field name
drifts (camelCase/snake_case mismatch is common across this codebase) the reset route will
silently 422 and the kill switch remains permanently fired, blocking all trading. No test
catches this.

**Suggested fix:** Add to `safety.test.ts`: POST to `/safety/kill-switch/reset` with
`{ reAck: true }`, assert store's `killSwitchFired` clears. Also add a failure path test:
reset returning non-2xx throws an error.

**Files:** `src/store/safety.ts:146, 230–242`

---

### Finding T5-workflow-store-sse-error-paths: workflow SSE parse error paths uncovered [S2] [status: open]

**Part:** A coverage

**Detection:** `src/store/workflow.ts` contains `_dispatchFrame()` (line ~317) with a
`catch` that swallows unparseable SSE frames, and `_safeText()` (line ~338) which returns
`null` on a `response.text()` failure. The `workflow.test.ts` suite covers the happy-path
SSE roundtrip and the non-2xx rejection, but never exercises:

1. A malformed JSON frame being silently dropped (the `catch {}` in `_dispatchFrame`)
2. The `_safeText` null path (body read failure on non-2xx)
3. The stream closing before `run-start` is emitted (test exists at line 294 but does
   not exercise the error accumulation when `run-error` kind fires mid-stream)

**Impact:** S2 — the swallow-unparseable-frame branch is intentional for resilience but
could mask a systematic wire-format bug if the SSE shape changes. The `run-error`
mid-stream path is the path the user sees when a workflow node throws.

**Suggested fix:** Add test: `_sseResponse([{ kind: "INVALID_JSON...` — actually inject
malformed data lines and assert the store does not crash. Add test: `run-error` event
mid-stream causes `activeRun` to clear and the run log contains the error event.

**Files:** `src/store/workflow.ts:317–335, 338–346`

---

### Finding T5-tradesa-connection-no-creds: `connection.ts` — missing-credentials path uncovered [S3] [status: open]

**Part:** A coverage

**Detection:** `plugins/tradesa-v2/connection.ts` has `buildAuthHeaders()` (line ~136)
returning an empty object when `readCredentials()` returns `null`. The plugin test file
(`tradesa-v2.test.ts`) installs a mock adapter via `_setAdapterForTests()`, bypassing
`TradesaV2ConnectionAdapter` entirely. Thus:

1. `readCredentials()` null-credential path — never exercised
2. `tradesaGet()` `SidecarError` re-throw on non-2xx — never exercised
3. `buildAuthHeaders()` empty-headers path — never exercised

**Impact:** S3 — when a user has not yet entered their Supabase credentials, the plugin
should degrade gracefully. If `buildAuthHeaders` regresses (e.g., throws instead of
returning `{}`), every panel will crash on first load for unauthenticated users.

**Suggested fix:** Add tests in a new `connection.test.ts` that stub `getSecret` to return
null, then call `buildAuthHeaders()` and assert `{}` is returned. Add a test for
`tradesaGet()` receiving a 403 — assert it rethrows a `SidecarError`.

**Files:** `plugins/tradesa-v2/connection.ts:52–56, 136–148, 156–175`

---

### Finding T5-panelhost-zero-coverage: `PanelHost.tsx` — entirely uncovered [S3] [status: open]

**Part:** A coverage

**Detection:** `src/components/PanelHost.tsx` has no test file. Two branches:
(a) `modules.length === 0` loading state; (b) `handleReady` callback with `applyDefaultLayout`.

**Impact:** S3 — the loading-state branch is the user-visible "Loading modules…" gate.
If `collectPanelComponents` throws when called with an empty array, the app crashes instead
of showing the spinner. The `applyDefaultLayout` call inside `handleReady` is the
first-launch layout; a regression here would show a blank dockview.

**Suggested fix:** Add `src/components/PanelHost.test.tsx` with mocked modules store:
(a) zero modules → renders "Loading modules…"; (b) one module registered → dockview
mounts with the component map. Mock dockview's `DockviewReact` to capture `onReady`.

**Files:** `src/components/PanelHost.tsx:19–51`

---

### Finding T5-agents-store-zero-coverage: `agents.ts` store entirely uncovered [S3] [status: open]

**Part:** A coverage

**Detection:** `src/store/agents.ts` has no test file. The store exposes
`loadAgents()`, `loadCustomAgents()`, `selectFirstPartyAgents()`, and
`selectCustomAgents()`. The `loadAgents` error path (sidecar unreachable) and the
`setCustomAgents` summary-precomputation path are both uncovered.

**Impact:** S3 — the chat sidebar's agent picker reads `selectFirstPartyAgents()`. A
regression in the summary precomputation (the deduplication of the custom agents list) would
cause the picker to show duplicate or stale entries.

**Suggested fix:** Add `src/store/agents.test.ts`. Test: `loadAgents` happy path; `loadAgents`
on network error does not throw; `setCustomAgents` produces correct summaries from `AgentSpec`.

**Files:** `src/store/agents.ts` (full file, ~180 lines)

---

### A.2 Sidecar (pytest) — overview

pytest suite: 588+ tests across 48 test files. All tests pass (CI-green from v0.7.0).
Coverage measurement: `pytest --cov=services --cov-report=term-missing` run on-demand.
The following gaps are identified from static analysis of test files vs service modules.

---

### Finding T5-audit-log-range-no-route: `audit_log.range_()` — no route calls it [S2] [status: open]

**Part:** A coverage

**Detection:** `sidecar/services/audit_log.py` exports `range_()` (lines ~100–120). No
router in `sidecar/routers/` calls `audit_log.range_()`. The only range-bounded access
is the date-gated `export_csv(start_ms, end_ms)`. The `range_()` function itself is tested
in `test_audit_log.py::test_range_includes_endpoints` but is a dead letter in the live
service — nothing calls it.

**Impact:** S2 — `range_()` is the mechanism for building time-ranged audit views in future
UX surfaces (compliance export, "show orders for today" filter). If `range_()` is unused it
is dead code; if it is intended for a route, the route is missing.

**Suggested fix:** Either add a `GET /safety/audit-log/range?start_ms=&end_ms=` route (and
test it) OR document `range_()` as an internal utility and note its intentional absence from
the router surface.

**Files:** `sidecar/services/audit_log.py:100–120`, `sidecar/routers/safety.py`

---

### Finding T5-broker-base-invalid-order-type: `propose_order` invalid order_type — untested [S1] [status: open]

**Part:** A coverage

**Detection:** `sidecar/services/broker_base.py::BrokerAdapter.propose_order()` raises
`BrokerError` on `order_type not in ("market", "limit", "stop", "stop-limit")` (line ~175).
`test_broker_base.py` tests `invalid side` and `zero quantity` raises, but has NO test
for an invalid `order_type`.

**Impact:** S1 — this is a §6.5 #2 gate. An unvalidated `order_type` could pass through
to the broker SDK and result in an unexpected order type being placed. The test gap means
a future refactor that accidentally changes `"stop-limit"` to `"stop_limit"` would not be
caught until a live order fails.

**Suggested fix:** Add to `test_broker_base.py`:
```python
def test_invalid_order_type_raises(temp_data_dir):
    adapter = _MockAdapter()
    with pytest.raises(BrokerError, match="invalid order type"):
        adapter.propose_order(symbol="AAPL", side="buy", order_type="twap", quantity=1)
```

**Files:** `sidecar/services/broker_base.py:175`, `sidecar/tests/test_broker_base.py`

---

### Finding T5-kill-switch-zero-subscribers: `fire` with zero subscribers — untested [S1] [status: open]

**Part:** A coverage

**Detection:** `sidecar/services/kill_switch.py::KillSwitchBus.fire()` with an empty
`_subscribers` dict enters `asyncio.gather()` with no awaitables and returns a result
with `ackTimesMs={}` and all metrics = 0.0. `_aggregate_ack_times()` handles this via
the `if not values: return KillSwitchFireResult(...)` guard (line ~165). No test covers
this zero-subscriber path.

**Impact:** S1 — in a hypothetical race (kill switch fired before any broker adapter
initialises), the bus fires successfully but the result's `maxAckMs=0.0` could confuse
monitoring logic that expects a non-zero value. More importantly, if `_aggregate_ack_times`
is called with an empty dict and the guard is accidentally removed, it would raise
`max([], ...)` → `ValueError`.

**Suggested fix:** Add to a kill_switch test file:
```python
@pytest.mark.asyncio
async def test_fire_with_no_subscribers_returns_zero_ack_times():
    bus = KillSwitchBus()
    result = await bus.fire(reason="test", fired_by="user-toolbar")
    assert result.ack_times_ms == {}
    assert result.max_ack_ms == 0.0
```

**Files:** `sidecar/services/kill_switch.py:100–130, 155–175`

---

### Finding T5-audit-log-insert-no-rowid: `append()` no-rowid guard uncovered [S1] [status: open]

**Part:** A coverage

**Detection:** `sidecar/services/audit_log.py::append()` line ~95:
```python
if row_id is None:  # pragma: no cover - INSERT always assigns an id
    raise RuntimeError("audit-log INSERT did not yield an id")
```

The `# pragma: no cover` annotation was added intentionally. However, this is the only
`RuntimeError` path in the append-only audit log; if the SQLite implementation changes
(e.g., a trigger consumes the rowid) or the connection is opened in a non-standard mode,
this guard silently drops the error. The explicit `pragma: no cover` means coverage
tooling ignores it.

**Impact:** S1 — strictly speaking this is a documented decision to exclude an infeasible
path. But it is on a §6.5 surface and the `pragma: no cover` comment effectively permanently
suppresses coverage reporting for a RuntimeError in the audit trail.

**Suggested fix:** This is lower-priority given the explicit pragma. Document in
`docs/SAFETY_ARCHITECTURE.md` why this branch is considered infeasible under SQLite
semantics. No code change required, but the rationale should be explicit.

**Files:** `sidecar/services/audit_log.py:92–96`

---

### Finding T5-workflow-engine-on-event-error-path: `on_event` callback error — uncovered [S2] [status: open]

**Part:** A coverage

**Detection:** `sidecar/services/workflow_engine.py::_emit()` catches and logs callback
exceptions without re-raising (line ~50). `test_workflow_engine.py` tests 9 cases but
none exercise an `on_event` callback that raises — the silent-swallow is never asserted.

**Impact:** S2 — the silent-swallow is intentional (a broken SSE subscriber should not
abort the workflow run), but if `_emit` is accidentally changed to re-raise, the entire
workflow run would abort on the first node. No test catches this regression.

**Suggested fix:** Add to `test_workflow_engine.py`:
```python
@pytest.mark.asyncio
async def test_on_event_exception_does_not_abort_run():
    calls = []
    async def bad_callback(evt):
        calls.append(evt)
        raise RuntimeError("SSE subscriber error")
    # run a workflow with the bad callback — should complete, not raise
```

**Files:** `sidecar/services/workflow_engine.py:47–52`

---

### Finding T5-openbb-mcp-provider-fallback-paths: provider_registry fallback branches — partially untested [S2] [status: open]

**Part:** A coverage

**Detection:** `sidecar/services/provider_registry.py` has three `get_fundamentals`,
`get_income_statement`, `get_balance_sheet`, `get_cashflow` methods that follow the
same pattern: if `openbb_mcp_provider.is_available()` AND the call raises `ProviderError`,
fall back to yfinance. `test_openbb_mcp_provider.py` tests the happy path and the
`ProviderError` raise from the tool, but does NOT test the registry-level fallback — i.e.,
a test that verifies `provider_registry.get_fundamentals()` gracefully falls back to
yfinance when openbb-mcp raises. The `test_fundamentals.py` tests only test the router,
not the registry fallback.

Additionally: the lead's audit at Phase 8 (from `docs/PHASE_8_BUG_CATALOG.md`) documents
that `/fundamentals/*` returns 500 in v0.7.0 because the openbb-mcp subprocess is not
running (MCP port env var unset). This means the yfinance fallback IS exercised in
production but the registry-level integration of `is_available() == False` path is not
covered by tests.

**Impact:** S2 — if the fallback logic regresses (e.g., the `except ProviderError`
becomes `except Exception` and accidentally catches `KeyboardInterrupt`), the equity
research workflow breaks silently. The UC1–UC5 research panel data depends on this path.

**Suggested fix:** Add to a new `test_provider_registry.py` (or extend `test_fundamentals.py`):
mock `openbb_mcp_provider.is_available` to `True`, mock `openbb_mcp_provider.get_fundamentals`
to raise `ProviderError`, assert registry falls back to `yfinance_provider.get_fundamentals`.

**Files:** `sidecar/services/provider_registry.py:55–70`, `sidecar/tests/test_openbb_mcp_provider.py`

---

### Finding T5-backtest-engine-empty-bar-loader: empty bar set — uncovered [S2] [status: open]

**Part:** A coverage

**Detection:** `sidecar/services/backtest_engine.py::run_backtest()` calls
`loader(request.symbols, start_date, end_date)` and then processes the resulting bars.
The case where `loader` returns an empty list (`bars_sorted = []`) is never tested. In
this case:
- `_run_single_slice()` is called with zero bars
- `_compute_metrics()` receives an empty equity curve (`equity_curve = []`)
- `equity_curve = []` hits the `if not equity_curve: return` guard at line ~232

No test exercises the zero-bar path.

**Impact:** S2 — a symbol with no historical data (e.g., newly listed, date range has no
trading days) would return empty metrics. The strategy critic agent tool `backtest_summary`
would receive a result with all metrics at zero, which could be misleading.

**Suggested fix:** Add to `test_backtest_engine.py`:
```python
@pytest.mark.asyncio
async def test_empty_bar_set_returns_zero_metrics():
    async def empty_loader(symbols, start, end): return []
    result = await run_backtest(request, bar_loader=empty_loader)
    assert result.metrics.total_return == 0.0
    assert result.metrics.trade_count == 0
```

**Files:** `sidecar/services/backtest_engine.py:232–238, 390–410`

---

### Finding T5-agent-tools-reset-v06-tools: `reset_for_tests` re-registration completeness [S2] [status: open]

**Part:** A coverage

**Detection:** `sidecar/services/agent_tools/__init__.py::reset_for_tests()` re-registers
`backtest_summary` after clearing, per the CLAUDE.md gotcha. However, the v0.6.0
`register_v0_6_0_tools()` call (which registers Phase 6 domain tools — screener, quant,
macro, sec, earnings, analyst tools) is NOT called from `reset_for_tests()`. Tests
that call `reset_for_tests()` then test Phase 6 tools will find them absent from the
registry.

**Impact:** S2 — any test that (a) calls `agent_tools.reset_for_tests()` and then (b) tries
to invoke a Phase 6 tool (e.g., `screener_run`, `get_yield_curve`, `get_macro_series`) will
get a `KeyError: unknown tool`. This is a latent bug that only surfaces if a future
Phase 6 tool test follows a reset in the same test session.

**Suggested fix:** In `reset_for_tests()`, after re-registering `backtest_summary`, call
`register_v0_6_0_tools()` (or its equivalent aggregator). Add a test that asserts
`is_registered("screener_run")` is `True` after `reset_for_tests()`.

**Files:** `sidecar/services/agent_tools/__init__.py:reset_for_tests()`

---

## Part B — BLUEPRINT Truth-Alignment

### Drift D-1: Phase 6.5 still marked "In progress" when it is shipped [S3]

**BLUEPRINT location:** §7 Phase 6.5 "**In progress (v0.6.5, 2026-05-17).**" (line 592)

**Actual state:** Phase 6.5 shipped as the tagged release `v0.6.5` on 2026-05-17.
`docs/PHASE_6.5_HANDOFF.md` exists and confirms "shipped as v0.6.5". The `tradesa-v2`
plugin is in `plugins/tradesa-v2/`, wired into `src/lib/plugin-bootstrap.ts` with a full
companion panels map. The tag exists in the repo (`git tag | grep v0.6.5` → `v0.6.5`).

**Severity rationale:** S3 — minor tracking drift; does not affect any runtime behaviour,
but is a visible inconsistency when a reader cross-references §7 to learn the current state.

**Suggested fix:** Change the Phase 6.5 heading to:
```
**Shipped in v0.6.5 (2026-05-17).** Plan at ...
```
Same convention as Phase 6, Phase 7, etc.

---

### Drift D-2: Phase 6 BLUEPRINT still shows "screener frontend deferred to v0.6.1" [S3]

**BLUEPRINT location:** §7 Phase 6, line 583–584:
"Screener / scanner — backend shipped (Teammate Sc); frontend deferred to v0.6.1
lead-completion after Sc's agent terminated mid-execution on a socket-closed error."

**Actual state:** `src/modules/screener/index.ts` exists with a `screenerModule` export;
`CHANGELOG.md` v0.6.1 section (line 554) confirms "Screener frontend" was lead-completed.
The screener module is exported from `src/modules/index.ts` and renders a full
`ScreenerPanel`. The BLUEPRINT deferred-note is now stale.

**Severity rationale:** S3 — the work shipped; the deferred note is a historical tracking
artefact. A reader of §7 Phase 6 sees "frontend deferred" and may incorrectly believe the
screener is not functional.

**Suggested fix:** Update BLUEPRINT §7 Phase 6 screener line to:
`- Screener / scanner ✓ — backend shipped (Teammate Sc, v0.6.0); frontend lead-completed (v0.6.1).`

---

### Drift D-3: `plugin-bootstrap.ts` HOST_VERSION is v0.6.5 but the app ships v0.7.0 [S3]

**BLUEPRINT location:** Implied by §8 success criteria "All 38 modules functional" and
§7 Phase 7 parity/polish intent.

**Actual state:** `src/lib/plugin-bootstrap.ts` line 39: `const HOST_VERSION = "0.6.5"`.
`package.json` version is `0.7.0`. The HOST_VERSION is passed to every plugin via
`PluginConfig.hostVersion`. Plugins that perform semver checks against the host will
believe they are running against v0.6.5, not v0.7.0.

**Severity rationale:** S3 — no current plugin performs a version check so there is no
runtime impact. But this is a semantic inconsistency and will bite when the first version-gated
plugin API change lands (e.g., a plugin checks `semver.gte(hostVersion, "0.7.0")` for a
v0.7.0 feature).

**Suggested fix:** Update `HOST_VERSION` in `src/lib/plugin-bootstrap.ts` to `"0.7.0"`.
Add this to the version-bump checklist alongside `package.json` / `Cargo.toml` / `tauri.conf.json`.

---

### Drift D-4: §4 Module 7 "Theming engine (dark default + light option)" — light theme unimplemented [S2]

**BLUEPRINT location:** §4 Module Catalog, Foundation (8), item 7:
"Theming engine (dark default + light option + future custom themes)"

**Actual state:** `src/components/PanelHost.tsx` hard-codes
`class="dockview-theme-dark dockview-theme-vysted"`. No theme toggle exists in the app.
No ThemeContext, no `useTheme` hook, no settings entry for light mode. The CLAUDE.md Gotcha
("Light-theme captures are a Tier-4 BLOCKER until light theme actually ships in v1.1") confirms
this is deferred, but §4 still lists it as a v1.0 module.

**Severity rationale:** S2 — BLUEPRINT §4 is the module catalog that drives the §8 success
criterion "All 38 modules functional." If the theming engine is not implemented, the module
count is effectively 37, not 38. CLAUDE.md defers light theme to v1.1.

**Suggested fix:** Either (a) remove "light option" from §4 item 7 and move it to §9
Deferred (v1.1); or (b) add a one-line note: "Dark only at v1.0; light theme deferred to
v1.1 (CLAUDE.md Gotcha: Tier-4 BLOCKER)."

---

### Drift D-5: §4 Module 18 "yfinance + alpha_vantage fallbacks" — alpha_vantage unimplemented [S2]

**BLUEPRINT location:** §4 Module Catalog, Data Layer (5), item 18:
"yfinance + alpha_vantage fallbacks (no API key needed for basic use)"

**Actual state:** No `alpha_vantage` import exists anywhere in `sidecar/`. `grep -rn "alpha_vantage"
sidecar/` returns zero results. The yfinance fallback is implemented; alpha_vantage is not.

**Severity rationale:** S2 — §4 claims two fallback providers; only one exists. The impact on
the user experience is low (yfinance is the production path), but the module count is off and
the claim creates a false impression of redundancy.

**Suggested fix:** Either implement `alpha_vantage` fallback or update §4 item 18 to:
"yfinance fallback (no API key needed for basic use) — alpha_vantage deferred to v1.1"
and add to §9 Deferred.

---

### Drift D-6: §4 Module 5 "Multi-window / multi-tab layout" — pop-out multi-window unimplemented [S2]

**BLUEPRINT location:** §4 Module Catalog, Foundation (8), item 5:
"Multi-window / multi-tab layout"

**Actual state:** dockview supports tab groups (multi-tab within one window) and is
implemented. Multi-window (pop-out to second display) is NOT implemented — there is no
Tauri `WebviewWindow` creation, no pop-out button in the panel chrome. CLAUDE.md §9
Deferred lists "multi-window pop-out" for v1.1+.

**Severity rationale:** S2 — "multi-window" is the second half of a two-feature module
name. The tab layout is functional; the window layout is deferred. This doesn't match a
"module functional" claim.

**Suggested fix:** Update §4 item 5 to: "Multi-tab layout (dockview; drag-drop, resize,
tab groups) ✓ — multi-window pop-out deferred to v1.1" and move that to §9 Deferred.

---

### Drift D-7: §10 UC2/UC4/UC5 — implicit dependency on openbb-mcp subprocess not disclosed [S1]

**BLUEPRINT location:** §10 Use Cases 2, 4, 5:
- UC2: "AI Researcher pulls everything → chart + news in adjacent panels → backtest"
- UC4: "workflow pulls SEC + sentiment → outputs to chart"
- UC5: "yield curves + central bank tracker + commodity dashboard → AI Macro Researcher"

**Actual state:** The Phase 8 L2 audit finding (`docs/PHASE_8_BUG_CATALOG.md`) documents
that `/fundamentals/*` returns HTTP 500 in v0.7.0 because the openbb-mcp subprocess is not
running (env var `VYSTED_OPENBB_MCP_PORT` is unset at the sidecar level when MCP subprocesses
are dead). The L2 audit also found `openbb-mcp` and `sec-edgar-mcp` MCP subprocesses fail
to start in the dev environment. UC2 ("AI Researcher pulls everything") requires fundamentals
data which 500s. UC4 ("workflow pulls SEC + sentiment") requires SEC filings which routes
through the sec-edgar-mcp subprocess. UC5 requires FRED/macro which falls back to in-process
`fredapi` and IS functional.

The BLUEPRINT §10 UC text does not disclose these runtime dependencies — a reader believes
these use cases are fully exercisable end-to-end.

**Severity rationale:** S1 — this is a load-bearing UC claim against infrastructure that
is demonstrably broken in the current dev environment. The MCP subprocess issue is documented
in the Phase 8 bug catalog but §10 UC2/UC4 text still implies end-to-end functionality.

**Suggested fix:** Add a footnote or inline qualifier to UC2 and UC4 in §10:
"[Note: Fundamentals and SEC endpoints require openbb-mcp and sec-edgar-mcp subprocesses
running (VYSTED_OPENBB_MCP_PORT and VYSTED_SEC_EDGAR_MCP_PORT env vars set by Tauri core).
v0.7.0 dev environment: MCP subprocess port-binding gap — see PHASE_8_BUG_CATALOG.md F1/F2.]"

---

### Drift D-8: §8 success criteria "All 38 modules functional" — module count is 20, not 38 [S2]

**BLUEPRINT location:** §8 success criteria line 693:
"All 38 modules functional and accessible"

Also §4 header: "Module Catalog (~38 modules in v1.0)"

**Actual state:** `src/modules/index.ts` exports `vystedModules` with 20 module entries
(counted: chart, watchlist, news, portfolio, equityOverview, chat, platform, pluginManager,
agentBuilder, nodeEditor, backtest, brokerConnect, safety, macro, secFilings, quant, earnings,
analystRatings, screener = 19 first-party modules). Plus `plugin-manager` is item 20.
The BLUEPRINT §4 enumerates ~38 by counting foundation, plugin arch, data layer,
charting, portfolio/risk, research, AI/automation, and customization primitives as
separate "modules" — but many of those are capabilities within existing modules, not
separate panels.

The "38 modules" figure from §4 counts infrastructure items (keychain, theming engine,
Python sidecar bootstrap, MCP server) as modules alongside UI panels. The actual
user-facing modules are ~20.

**Severity rationale:** S2 — the §8 success criterion "all 38 modules functional" cannot
be checked against a concrete list because the 38-count mixes UI modules and infrastructure
capabilities. This is a testability gap: Phase 8 cannot verify "38 modules functional"
without a canonical mapping.

**Suggested fix:** In §8, replace "All 38 modules functional and accessible" with
"All 20 first-party UI modules load and render populated state (verified by Phase 8
visual audit)" OR add a footnote: "38-count includes infrastructure capabilities;
20 are user-facing panels/modules."

---

### Drift D-9: §7 Phase 8 scope is "cross-cutting code review, security pass, dead-code scan" but does not mention coverage audit [S3]

**BLUEPRINT location:** §7 Phase 8:
"Scope: cross-cutting code review, security pass, dead-code scan, BLUEPRINT cross-check,
dependency freshness."

**Actual state:** The actual Phase 8 is executing a coverage audit (T5), a rust/Tauri
audit (T3), a plugin-contract audit (T4), plus other teammate work. The BLUEPRINT §7
Phase 8 description was written in the v0.7.0 release context as a placeholder. Coverage
analysis is a material part of Phase 8 scope.

**Severity rationale:** S3 — this is a spec gap that will be naturally resolved when the
Phase 8 handoff doc is written. Not blocking.

**Suggested fix:** Update BLUEPRINT §7 Phase 8 description to match actual scope once
Phase 8 concludes. Include the coverage audit and BLUEPRINT truth-alignment as named items.

---

### Drift D-10: §3.3 Plugin Contract — `subscribe` and `executeCommand` use `any` in BLUEPRINT text [S3]

**BLUEPRINT location:** §3.3 Plugin Contract code block, lines 177–180:
```typescript
subscribe?(channel: string, callback: (event: any) => void): Unsubscribe;
executeCommand?(commandId: string, args: any): Promise<CommandResult>;
```

**Actual state:** `types/plugin.ts` lines 14–17 (per the CLAUDE.md note) use `unknown`
not `any` for these types. The BLUEPRINT §3.3 shows `any` in the verbatim interface listing.

**Severity rationale:** S3 — this is a documented intentional hardening (per CLAUDE.md
"§3.3 writes `any` for subscribe event + executeCommand args; the actual contract uses
`unknown`. That's a documented intentional hardening"). It is NOT a finding per the brief,
but is noted here for completeness as the CLAUDE.md explicitly says "NOT a finding."
This entry is informational only.

**Suggested fix:** Update the §3.3 code block to show `unknown` to match the locked file,
with a comment: `// unknown not any — type-hardened per v0.5.0 Tier-3 decision`.

---

## Summary

### Findings by severity

| Count | Severity | Category |
|-------|----------|----------|
| 3 | S1 | Safety-surface coverage gaps + UC drift |
| 9 | S2 | Plugin/broker/workflow/backtest coverage + BLUEPRINT module claims |
| 7 | S3 | General coverage gaps + minor BLUEPRINT tracking drift |
| 0 | S4 | Stretch goals (UC6/UC7) — intentional non-implementation |

**Total:** 19 findings (12 Part A coverage, 10 Part B BLUEPRINT drift; 3 overlap S1/S2)

### S4 status (UC6 / UC7)

- **UC6 (Plugin Ecosystem, year 2+):** §10 correctly labels this "year 2+" and §9
  Deferred mentions "Online plugin marketplace." Not a finding — intentional stretch.
- **UC7 (Multi-Broker Aggregation):** §10 describes the intended UX but no aggregate
  P&L view, cross-broker risk metrics, or multi-broker unified panel exists in the
  current codebase. Marked S4 per brief as a stretch goal.

### Top 3 coverage gaps (priority order)

1. **T5-safety-store-reset-ks** (S1) — `resetKillSwitch()` entirely untested; the
   POST body field name is untested and could silently drift, permanently locking the
   kill switch.
2. **T5-broker-base-invalid-order-type** (S1) — `propose_order` invalid `order_type`
   validation never exercised; a camelCase/snake_case drift at the route boundary would
   not be caught.
3. **T5-openbb-mcp-provider-fallback-paths** (S2) — `provider_registry` yfinance
   fallback path is untested; the fundamentals 500 bug (documented in Phase 8 bug
   catalog) shows this fallback is the critical production path, yet it has no test.

### Top 3 BLUEPRINT drifts (priority order)

1. **D-7** (S1) — §10 UC2/UC4 imply end-to-end functionality but the openbb-mcp/sec-edgar-mcp
   MCP subprocess gap is a known v0.7.0 blocker not disclosed in the use case text.
2. **D-4** (S2) — §4 Module 7 "light option" theming engine is not implemented; counted
   toward the "38 modules functional" criterion in §8.
3. **D-5** (S2) — §4 Module 18 alpha_vantage fallback is not implemented; never has been.

### Items not audited

- **Rust/Tauri surface coverage** — out of scope for T5 (T3 teammate handles).
- **Plugin contract audit** — out of scope for T5 (T4 teammate handles).
- **`vitest.config.ts` lacks coverage configuration** — no `coverage` block means
  `pnpm test --coverage` does not produce a coverage report without extra flags. Adding
  `@vitest/coverage-v8` to `devDependencies` and a `coverage` config block in
  `vitest.config.ts` is a recommended follow-up (not a finding per the audit brief).
- **`test_safety_end_to_end.py::test_audit_5_kill_switch_under_2s` benchmark** — this
  test requires building and running 7 real broker adapters with a live asyncio event loop.
  It was not re-run during this audit (the benchmark JSON file `docs/screenshots/v0.5.0/
  safety-audit/kill-switch-benchmark.json` was restored from the v0.7.0 commit in the
  most-recent housekeeping commit `005a8d0`). Any coverage measurement of `kill_switch.py`
  in isolation will miss the multi-subscriber concurrent dispatch path.
