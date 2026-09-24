# R15 Stage C: Batch 8 Plan (1 high, 44 mediums, 2 class-mate lows; 0 proposed not-a-defect)

- **Base:** branch `004-r4-experience-rebuild` at `b47ed2ddc0f3429d7966583cabba9daa279c07db` (batch-8 adjudication `c69929b`, then two docs-only rc1-gate commits `bb23341`/`b47ed2d`; no code differs from `c69929b`). D81 is merged: nothing here re-adds trading, orders, brokers or a paper account.
- **Author:** batch planner (Opus). Every row below was written after opening the code it names at this base. Mechanisms follow the corrected verdicts (refuter corrections, batch-7 not-certified notes), not the raw claims. Line numbers are at base.
- **Queue at base:** 0 critical, 3 high, 150 medium, 206 low. The rc1 gate plan (`r15/tooling/RC1_GATE_PLAN.md`) runs after batches 8 and 9, so batch 9 is the last Stage C batch: every deferral below names what batch 9 needs.
- **Selection: 47 entries in 5 writer sets (all opus).**
  - **High.** `LIFECYCLE-001` is taken (it shares `start_main_sidecar` with `LIFECYCLE-010` and `UI-014`; batch 7 deferred it only for GUI proof, and it is pinned here by a Rust test with the packaged-launch check recorded as needs-GUI). `AGENT-007` and `AGENT-017` stay deferred (funded live lanes, §4).
  - **Carried from batch 7:** `AGENT-045` (not certified: the two-symbol payload drops per-symbol errors), `LEAD-005`, `AGENT-046`, `CODE-PLATFORM-021` (not delivered).
  - **Batch-7 §4 deferrals taken now:** the error-layer cluster (`UI-012`, `UI-014`, `LIFECYCLE-010`, `LIFECYCLE-011`, `CODE-PLATFORM-011`, `UI-013`, `UI-015`, `UI-030`, `UI-029`, `UI-019`, `UI-049`, `UI-057`); `AGENT-061` + `DATA-061`; `CODE-AGENT-008` + `RESEARCH-027`; `CODE-RESEARCH-003`; `AGENT-055` + `AGENT-056`; `DATA-081` + `UI-053`; `LIFECYCLE-014`; `AGENT-081`; the resolver set minus `DATA-059`/`DATA-052` (`DATA-058`, `LIFECYCLE-019`, `UI-039`, `CODE-DATA-002`, `CODE-DATA-003`, `DATA-051`).
  - **New this batch:** `AGENT-028`, `AGENT-030`, `LIFECYCLE-022`, `LIFECYCLE-023`, `CODE-AGENT-004`, `CODE-AGENT-006`, `CODE-AGENT-007`, `LEAD-019`, `DATA-084`, `DATA-085`, `DATA-086`; two lows taken as root-cause mates: `RESEARCH-032` (with `CODE-PLATFORM-011`), `CODE-AGENT-016` (with `CODE-AGENT-006`/`-007`).
  - **Why 47, not 60.** Every candidate past these either collides with a file a set here owns (§4) or needs a decision/data run that does not fit (DATA-059). Five opus writers at 8-12 entries, with two large entries each, is what batches 2-7 proved deliverable (batch 7: 50 of 55).
- **Class rule.** A class is a shared root cause, not a shared label. Taken together:
  - `UI-012` + `UI-014` + `CODE-PLATFORM-011` + `RESEARCH-032`: the one place a failure becomes a legible message covers only `sidecarGet`'s non-2xx; transport failures, the SSE non-2xx body and every non-GET verb re-derive (or skip) it.
  - `LIFECYCLE-010` + `LIFECYCLE-011` (+ `UI-014`'s Rust leg): the sidecar status is written once at boot; spawn failure, crash and later outages never reach it.
  - `UI-013` + `AGENT-028` + `UI-057`: provider readiness is a boolean that erases why (key invalid vs sidecar/provider unreachable vs model not pulled), with two untrimmed entry points. `UI-019` + `UI-049` ride the same readiness predicate (keyed provider vs reachable model) in the same files.
  - `UI-015` + `UI-030` + `UI-029`: the cold-boot retry hook cannot tell a transient failure from a deterministic one because callers flatten or swallow the error.
  - `DATA-061` + `AGENT-061`: `ProviderError.kind` is dropped (app handler, 27 `except ProviderError` blocks in 7 routers, the agent tool) and re-derived by substring.
  - `UI-053` + `DATA-081`: a `/` in a path parameter never routes (Starlette decodes `%2F` before matching).
  - `CODE-AGENT-006` + `CODE-AGENT-007` + `CODE-AGENT-016` (low): a hand copy of `model_registry.json` (TS tables, the llm base URLs, the agent schema's provider enum).
  - `LIFECYCLE-019` + `LIFECYCLE-022`: an upstream failure is recorded as a legitimate state (today's refresh done; a holiday) and never retried.
  - `DATA-085` + `DATA-086` (+ `DATA-084`): the Macro panel's provider adapters turn upstream shapes/failures into plausible data.
- **Label-mates not taken (different root cause):** `LIFECYCLE-021` (registry fall-through counting, `StatusChrome.tsx` is W2's), `UI-033`/`UI-044` (swallowed-error label; different files; UI-044 is Tier-4-flagged), `UI-082`, `UI-089`, `UI-076`, `DATA-108`, `CODE-DATA-022`, `CODE-PLATFORM-038`, `LEAD-006`/`LEAD-020`.
- **proposed_not_defect:** none. Every selected entry reproduces at base.
- **Models:** all five sets are opus (Rust boot, error classification, provider readiness, data providers, resolver, agent runtime, research funnel).

---

## 0. The 47 entries

| # | Entry | Sev | Root-cause class / mechanism | Writer |
|---|---|---|---|---|
| 1 | R15-LIFECYCLE-001 | high | MCP joins + main sidecar spawn run inside `setup()` on the main thread | W1 |
| 2 | R15-LIFECYCLE-010 | med | `SidecarPort==0`/spawn failure never reaches the renderer; 120 s blind wait | W1 |
| 3 | R15-UI-014 | med | transport failure passes as WebKit "Load failed"; child `Terminated` dropped | W1 |
| 4 | R15-LIFECYCLE-011 | med | `sidecarStatus` is a one-shot boot latch | W1 |
| 5 | R15-UI-012 | med | SSE non-2xx renders the raw FastAPI body | W1 |
| 6 | R15-CODE-PLATFORM-011 | med | the shared client is GET-only; non-GET callers hand-roll parsing | W1 |
| 7 | R15-RESEARCH-032 | low | Settings SearXNG/hardware private fetch client, one-shot sample | W1 |
| 8 | R15-LIFECYCLE-023 | med | no React error boundary; one panel throw blanks the cockpit | W1 |
| 9 | R15-UI-013 | med | three boolean validation clients erase why validation failed | W2 |
| 10 | R15-AGENT-028 | med | Ollama validates "daemon up", not "model pulled"; no route on `model_not_pulled` | W2 |
| 11 | R15-UI-057 | med | Settings key dialog never trims; route never strips | W2 |
| 12 | R15-UI-049 | med | only onboarding promotes a newly keyed provider to default | W2 |
| 13 | R15-UI-019 | med | banner gates on "has a BYOK key" not "a model is reachable"; dismissal unpersisted | W2 |
| 14 | R15-CODE-AGENT-006 | med | static TS model tables are authoritative at runtime | W2 |
| 15 | R15-AGENT-055 | med | one template id = four different layouts; catalog prose drifts | W2 |
| 16 | R15-AGENT-056 | med | `arrange_layout` default/unknown = factory reset (drawings, modules) | W2 |
| 17 | R15-AGENT-081 | med | `open_company_overview` highlight never consumed, result claims it was | W2 |
| 18 | R15-DATA-061 | med | `ProviderError.kind` flattened to 502; raw library text; network → "no data" | W3 |
| 19 | R15-AGENT-061 | med | fundamentals tool re-derives `kind` by substring | W3 |
| 20 | R15-AGENT-030 | med | router last-resort SSE guard blames the provider/network by substring | W3 |
| 21 | R15-UI-053 | med | `/macro/{series_id}` cannot carry IMF ids with `/` | W3 |
| 22 | R15-DATA-081 | med | crypto pairs: slash in path; asset class dropped between panels | W3 |
| 23 | R15-LEAD-005 | med | yfinance `get_quote` stamps `timestamp=_utcnow()` | W3 |
| 24 | R15-UI-015 | med | retry hook retries deterministic failures; News copies the loop | W3 |
| 25 | R15-UI-030 | med | Macro provider-tab switch routed through the cold-boot retry hook | W3 |
| 26 | R15-UI-029 | med | `loadCatalog` swallows; picker error/Retry UI unreachable | W3 |
| 27 | R15-DATA-058 | med | fuzzy band sorts all IN rows above a better US row; cap truncates it | W4 |
| 28 | R15-LIFECYCLE-019 | med | failed rename-master fetch stamped as today's refresh | W4 |
| 29 | R15-LIFECYCLE-022 | med | primary bhavcopy 404 skips the fallback and is cached as a holiday | W4 |
| 30 | R15-UI-039 | med | autocomplete skips rename + enrichment stages | W4 |
| 31 | R15-CODE-DATA-002 | med | banded fuzzy master scan re-runs on every resolve | W4 |
| 32 | R15-CODE-DATA-003 | med | Instrument wire projection hand-copied in router and tool | W4 |
| 33 | R15-DATA-051 | med | BSE group / NSE SME type dropped; no face value | W4 |
| 34 | R15-AGENT-045 | med | `compare_symbols` drops per-symbol errors when < 2 resolve | W4 |
| 35 | R15-CODE-PLATFORM-021 | med | sidecar positions ledger keeps write routes no surface calls | W4 |
| 36 | R15-DATA-084 | med | `row.get("value") or …` drops a real 0.0 observation | W4 |
| 37 | R15-DATA-085 | med | World Bank title branch unreachable (`callable(info.items)`) | W4 |
| 38 | R15-DATA-086 | med | World Bank search swallows failure into curated rows, cached 6 h | W4 |
| 39 | R15-CODE-AGENT-008 | med | runtime decodes the research payload variants to build the brief | W5 |
| 40 | R15-RESEARCH-027 | med | FAST gathers sequentially, witness legs have no timeout | W5 |
| 41 | R15-AGENT-046 | med | runtime mints ids only when empty/seen this turn; cross-run reuse | W5 |
| 42 | R15-CODE-AGENT-004 | med | Gemini usage omits thoughts + tool-use-prompt tokens | W5 |
| 43 | R15-LEAD-019 | med | an unlisted `:free` slug is priced at `DEFAULT_RATE_PER_M` | W5 |
| 44 | R15-LIFECYCLE-014 | med | a bad/missing agent JSON silently shrinks the roster | W5 |
| 45 | R15-CODE-RESEARCH-003 | med | `run_deep_research` is a drifted second deep loop behind an except | W5 |
| 46 | R15-CODE-AGENT-007 | med | DeepSeek/xAI/OpenRouter base URLs are literals beside the registry | W5 |
| 47 | R15-CODE-AGENT-016 | low | `_schema.json` provider enum is a stale copy (no `openrouter`) | W5 |

---

## 1. File ownership: five disjoint sets

A file belongs to exactly one writer. Test files follow their subject. Anything outside your list goes to `issues[]`.

- **W1 `sidecar-lifecycle-transport`:** `src-tauri/src/lib.rs`, `src-tauri/src/openbb_mcp.rs`, `src-tauri/src/sec_edgar_mcp.rs`, `src/lib/sidecar-client.ts` (+`.test.ts`), `src/modules/chat/streaming.ts` (+`streaming.test.ts`), `src/store/app.ts` (+ new `src/store/app.test.ts`), `src/lib/delegate-runs.ts` (+`.test.ts`), `src/modules/agent-builder/AgentBuilderPanel.tsx` (+ test), `src/components/SettingsPanel.tsx` (+`.test.tsx`), `src/lib/hardware-fit.ts`, `src/components/PanelHost.tsx` (+ test), `src/main.tsx`.
- **W2 `provider-readiness-host-actions`:** new `src/lib/provider-validation.ts` (+`.test.ts`), `src/components/StatusChrome.tsx` (+`.test.tsx`), `src/modules/chat/ChatSidebar.tsx`, `src/components/OnboardingFlow.tsx`, `src/components/KeyEntryDialog.tsx`, `src/components/OnboardingBanner.tsx`, `src/store/llm-providers.ts`, `src/store/provider-keys.ts`, `src/store/model-selection.ts` (+`.test.ts`), `src/store/onboarding.ts` (dismissal marker, if needed), `sidecar/services/llm/ollama.py`, `sidecar/routers/llm.py`, `sidecar/models/llm.py`, `sidecar/tests/test_llm_router.py`, `sidecar/tests/test_llm_ollama.py`; `src/lib/layout-templates.ts` (+`.test.ts`), `src/lib/menu-bridge.ts`, `src/store/workspace.ts` (+ test), `src/lib/host-actions.ts` (+`.test.ts`), `sidecar/services/agent_tools/catalog.py`, new `sidecar/config/layout_templates.json`, `src/modules/equity-overview/EquityOverviewPanel.tsx` (+ test), new `src/modules/equity-overview/metrics.ts` (the highlightable metric ids), `src/store/equity-command.ts`, `sidecar/tests/test_capability_catalog.py` (only if a count moves).
- **W3 `data-error-honesty`:** `sidecar/app.py`, `sidecar/services/errors.py`, `sidecar/services/yfinance_provider.py`, `sidecar/routers/{fundamentals,earnings,macro,disclosures,sec_filings,screener,crypto,history,quotes,indicators}.py`, `sidecar/services/agent_tools/fundamentals.py`, tests `test_errors.py`, `test_yfinance_provider.py`, `test_history.py`, `test_quotes.py`, `test_macro_router.py`, `test_fundamentals_tool.py` (+ new route-mapper test); `src/lib/use-sidecar-retry.ts` (+ test), `src/modules/macro/MacroPanel.tsx`, `src/store/macro.ts` (+`.test.ts`), `src/modules/macro/MacroSeriesPicker.tsx`, `src/modules/news/NewsFeedPanel.tsx`, `src/modules/earnings/EarningsCalendarPanel.tsx`, `src/modules/sec/SecFilingsPanel.tsx`, `src/modules/screener/ScreenerPanel.tsx`, `src/store/sec.ts`, `src/modules/watchlist/WatchlistPanel.tsx`, `src/modules/chart/ChartPanel.tsx`, `src/modules/chart/api.ts`, `src/store/chart-command.ts`, `src/store/symbols.ts`, `src/modules/portfolio/PortfolioPanel.tsx`, `src/modules/portfolio/api.ts`.
- **W4 `resolver-exchange-lanes`:** `sidecar/services/symbol_resolver.py`, `sidecar/routers/resolve.py`, `sidecar/services/agent_tools/resolve_symbol.py`, `sidecar/services/nse_symbol_change.py`, `sidecar/services/nse_bhavcopy.py`, `sidecar/services/fundamentals_warm.py` (only if the bhavcopy contract needs it), `sidecar/services/resolver_masters/{regenerate_bse_master.py,regenerate_nse_master.py,bse_instruments.json,nse_instruments.json}`, `sidecar/services/agent_tools/compare_symbols.py`, `sidecar/routers/portfolio.py`, `sidecar/services/portfolio_db.py`, `sidecar/models/portfolio.py`, `sidecar/models/__init__.py`, `sidecar/services/openbb_mcp_provider.py`, `sidecar/services/macro/world_bank_provider.py`, `sidecar/services/macro/macro_router.py`; tests `test_symbol_resolver.py`, `test_resolve_router.py`, `test_resolve_symbol_tool.py`, `test_resolver_rename.py`, `test_nse_symbol_change.py`, `test_nse_bhavcopy.py`, `test_compare_symbols.py`, `test_portfolio.py`, `test_openbb_mcp_provider.py`, `test_macro_providers.py`, `test_macro_cache.py`.
- **W5 `agent-runtime-research`:** `sidecar/services/agent_runtime.py`, `sidecar/services/agent_tools/research.py`, `sidecar/services/research/fast.py`, `sidecar/services/research/deep.py`, `sidecar/services/research/iter.py` (only if a deep helper moves), `sidecar/services/agent_tools/deep_research.py`, `sidecar/services/research/__init__.py` (docstring), `sidecar/services/action_ledger.py` (only if the mint change needs it), `sidecar/services/llm/gemini.py`, `sidecar/services/llm/__init__.py`, `sidecar/services/model_registry.py`, `sidecar/config/model_registry.json`, `sidecar/services/budget_guard.py`, `sidecar/agents/_schema.json`, `sidecar/routers/health.py`, `scripts/smoke-test-sidecars.mjs`; tests `test_agent_runtime.py`, `test_research_fast.py`, `test_research_tools.py`, `test_research_deep.py`, `test_research_iter.py`, `test_b5_runtime_synthesis.py`, `test_b6_research_funnel.py`, `test_llm_gemini.py`, `test_budget_guard.py`, `test_health.py`, new `test_llm_registry_parity.py`.

**Contracts (frozen; a writer codes against them, the integrator checks them):**
- **C1 (W1, consumed by W3 and W2).** `SidecarError(0, "The data engine is not responding — it may have stopped. Restart Vysted.")` is the transport-failure error from `sidecarGet`/`sidecarRequest`/`consumeSseStream`'s fetch; `SidecarError(503, …)` stays "not ready yet". W3's retry classifier treats a non-`SidecarError` (a raw `TypeError`, pre-W1), status `0` and status `503` as transient and everything else as deterministic, so it is correct before and after W1 merges.
- **C2 (W1).** `sidecarRequest<T>(method: "GET"|"POST"|"PUT"|"DELETE", path: string, opts?: { params?, body?, headers?, signal? }): Promise<T>` in `sidecar-client.ts`; `sidecarGet` delegates to it (same headers: region, search headers, per-call headers); a 204 resolves `undefined`. Non-2xx → `SidecarError(status, extractSidecarDetail(body, statusText))`.
- **C3 (W1 → W3's hook, W2's StatusChrome).** `useAppStore.sidecarStatus` now moves both ways (`connected` → `error` on a connection-level failure; `error` → `connected` on any success or a re-probe). `sidecarError` carries the reason (spawn failure text, "The data engine stopped", or the transport message). The hook's existing re-arm-on-`connected` edge and StatusChrome's `sidecarStatus` dep need no API change.
- **C4 (W2).** `POST /llm/keys/validate` body `{provider, api_key?, base_url?, model?}` (key stripped at the route); response `{ok: bool, reason: null|"invalid"|"not_configured"|"unreachable"|"model_not_pulled", detail: str|null}`. The one frontend reader is `src/lib/provider-validation.ts` `validateProvider(provider, {apiKey?, model?, signal?}) -> Promise<{ok, reason, detail}>`, where a sidecar the client cannot reach is `reason:"unreachable"` with detail naming the data engine.
- **C5 (W3).** A data-route failure body stays `{"detail": "<human sentence>"}` (a STRING, so `extractSidecarDetail`/`SidecarError` keep working) plus additive `"code"` (the kind: `rate_limited|not_found|network|provider_error`) and `"action"`; statuses `rate_limited→429`, `not_found→404`, `network→503`, unclassified→`502`.
- **C6 (W5).** A research tool result carries `brief`: exactly the dict `_auto_publish_event` builds today as `brief_input` (snake_case keys `query, symbol, mode, depth, execution, markdown, sources, structured, cost, web_available, note, web_reason, backend`), or the disambiguation input; the runtime publishes it verbatim. The frontend `briefFromInput` contract is unchanged.
- **C7 (W5).** `/health` gains `agents_degraded: [{file, reason}]` (additive; `[]` when the roster loaded whole). No TS type change.
- **C8 (W2).** `sidecar/config/layout_templates.json` = `{ "<template-id>": { "panels": ["<role>", …], "summary": "<one line>" } }` for `single-focus`, `research-cockpit`, `compare`, `macro-scan` (+ the menu modes' roles). Loaded by `catalog.py` and imported by `layout-templates.ts` (precedent: `marketplace.ts` imports plugin manifests; `config/` is bundled whole by `ensure-sidecar.mjs:183-188`).
- **C9 (W4).** The resolve payload (router and tool, one `instrument_payload`) adds `board: "SME"|"mainboard"|null`, `exchange_group: str|null`, `face_value: float|null`. Additive; no TS mirror exists (the picker reads `symbol/name/exchange`).

---

## 2. Per-writer entries (mechanism, then fix, test and files)

### W1: `sidecar-lifecycle-transport` (opus, 8 entries, 1 high)

**Priority order:** C2 `sidecarRequest` + UI-014/UI-012 (push first: W3's classifier and the class pins build on it) → LIFECYCLE-011 → LIFECYCLE-010 + LIFECYCLE-001 (Rust) → CODE-PLATFORM-011 migrations → RESEARCH-032 → LIFECYCLE-023.

**R15-UI-012 + R15-UI-014 + R15-CODE-PLATFORM-011 + R15-RESEARCH-032: one class (the error layer covers only GET's non-2xx).**
- **Mechanism (confirmed at base).**
  - `sidecarGet` humanizes a non-2xx through `extractSidecarDetail` (`sidecar-client.ts:48-72`, `:197-205`), but its `fetch` (`:194`) is unguarded, so a dead engine rejects with WebKit's bare `TypeError: Load failed`; `resolveAndAwaitReady` swallows transport errors only while probing (`:130-137`).
  - `consumeSseStream`'s non-2xx branch (`streaming.ts:291-294`) throws `safeReadDetail(response)` (`:443-450`), the raw body text (`{"detail":[...]}`), into the transcript; its `fetch` (`:281-286`) is also unguarded.
  - `sidecarGet` is the only verb (`:154`). `delegate-runs.ts` hand-rolls seven `fetch` sites (`:91,149,275,364,404,428,450`; the start path at `:177-184` was already humanized in batch 7); `AgentBuilderPanel.tsx:85-100` keeps `detail` only when it is a string (a 422 array becomes "request failed (422)"), `:107` delete, `:152` tool-ids.
  - RESEARCH-032: `SettingsPanel.tsx:697-725` (`fetchSearxngStatus`, `postSearxngAction`) and `hardware-fit.ts:44-55` collapse every failure (including a 500 with a reason) to `null` = "sidecar not connected", and the status is sampled once on mount (`:783-793`; the 3 s poll runs only while pulling/starting, `:796-812`), so a container that dies while the panel is open stays "Ready".
- **Fix (D-B8-4).**
  - C2: `sidecarRequest` in `sidecar-client.ts`; `sidecarGet` delegates. Both fetches (and the SSE fetch) catch a transport rejection → C1 `SidecarError(0, …)`. The SSE non-2xx branch parses the JSON and runs `extractSidecarDetail(parsed, \`sidecar returned ${status}\`)`; a transport failure mid-stream ends with that same human message (code `sidecar_unreachable` on the error the handler receives).
  - Migrate `delegate-runs.ts` (all seven sites) and `AgentBuilderPanel.tsx` (create/update/delete/tool-ids) to `sidecarRequest`; delete their local parsing.
  - RESEARCH-032: `fetchSearxngStatus`/`postSearxngAction`/`fetchHardwareReport` go through `sidecarGet`/`sidecarRequest`; the section renders the `SidecarError` message (a 500's reason, or C1's unreachable sentence) instead of "sidecar not connected"; it re-fetches on `visibilitychange`/`focus` and on a slow poll (60 s) while mounted, keeping the 3 s transition poll.
  - Do not touch `validateProvider` (`:218-243`): W2 retires its callers; the integrator deletes the orphan after both merge (§3).
- **Test.** `sidecar-client.test.ts`: a rejected `fetch` → `SidecarError` status 0 with the sentence; a 422 array through `sidecarRequest("POST", …)` → `"field: msg"`. `streaming.test.ts`: non-2xx with a string `detail` and with a 422 array → `onError` message is the humanized text, never the JSON. **Class pin on a case the fix was not written against:** `delegate-runs.test.ts` cancel (`DELETE /runs/{id}`) answering a 409 `{"detail":"run already finished"}` → the rail's run detail reads that sentence. `SettingsPanel.test.tsx`: status 500 `{"detail":"docker daemon not reachable"}` → the panel shows that reason, not "not connected"; a `visibilitychange` re-fetch flips a stale "Ready" to the new state.
- **Files.** `sidecar-client.ts`, `streaming.ts`, `delegate-runs.ts`, `AgentBuilderPanel.tsx`, `SettingsPanel.tsx`, `hardware-fit.ts` + tests.

**R15-LIFECYCLE-011 + R15-LIFECYCLE-010 + R15-UI-014 (Rust leg): the status is written once at boot.**
- **Mechanism (confirmed at base).**
  - `useAppStore.connectSidecar` (`store/app.ts:24-34`) is the only writer, called once from `page.tsx:45`; nothing re-probes. `use-sidecar-retry.ts:119-135` re-arms on a `-> connected` edge that can therefore fire at most once per app lifetime.
  - `SidecarPort(u16)` is managed before the spawn (`lib.rs:22-23`, `:444-445`); every failure arm of `start_main_sidecar` (`:202-226`) logs and returns; `get_sidecar_port` (`:281-283`) keeps returning the picked port, so the renderer probes a port nothing will bind for 120 s (`sidecar-client.ts:124-143`) and then says "did not become ready in time" with no reason. A port-0 pick is interpolated as `http://127.0.0.1:0`.
  - The drain loop drops `CommandEvent::Terminated` (`lib.rs:229-240`, `_ => {}`): a sidecar crash is never signalled.
- **Fix (D-B8-2, D-B8-3).**
  - Rust: replace `SidecarPort(u16)` with `SidecarStatus(Mutex<{port, state: Starting|Ready|Failed, reason: Option<String>}>)`; every failure arm and the port-0 pick set `Failed(reason)`; the port-wait thread sets `Ready`/`Failed("did not come up on port N")`; `Terminated` sets `Failed("the data engine stopped (exit code …)")` and emits `vysted://sidecar-terminated` with the reason. `get_sidecar_port` keeps its name and returns the struct (no capability change: `build.rs` has no app-command manifest). No auto-respawn (separate decision).
  - Renderer: `resolvePortToBaseUrl` reads the struct; `Failed` → throw `SidecarError(0, reason)` immediately (no 120 s probe); `Starting` → probe as today.
  - `app.ts` becomes the status owner of record: `sidecar-client` reports reachability through a tiny subscription it exports (`onSidecarReachability(listener)`, no import of the store, avoiding the `app.ts ⇄ sidecar-client.ts` cycle); a C1 failure sets `error` + `sidecarError` and nulls `readyPromise`; any success sets `connected`. While `error`, a 20 s `/health` re-probe runs (stops on success); the terminated event sets `error` with its reason.
- **Test.** Rust (`lib.rs` `#[cfg(test)]`): the spawn-failure path (sidecar command missing) yields `Failed(reason)` through a pure helper the failure arms call. Vitest `app.test.ts`: a connection-refused `sidecarGet` flips `connected → error`; a later success flips back to `connected` and a panel hooked with the (unchanged) `useRetryOnSidecarReady` re-runs its load (the class case: a hook consumer the fix was not written for). `sidecar-client.test.ts`: `get_sidecar_port` → `{state:"failed", reason}` throws that reason at once, without a `/health` probe.
- **Files.** `lib.rs`, `sidecar-client.ts`, `store/app.ts` + tests.

**R15-LIFECYCLE-001 (high): MCP joins run on the main thread.**
- **Mechanism (confirmed at base).** `setup()` (`lib.rs:440-495`) spawns the two MCP supervisors on threads and then `join`s both (`:482-483`) before `start_main_sidecar(app, port)` (`:491`); Tauri runs `setup` inside the event loop's Ready callback on the main thread, so the loop is frozen for the whole bind window (each supervisor waits `MCP_PORT_WAIT_SECS × MCP_PORT_WAIT_ATTEMPTS`, `openbb_mcp.rs:151-171`). The join exists only so the env vars (`VYSTED_OPENBB_MCP_PORT`, set at `openbb_mcp.rs:94-95` right after the port pick) are settled before the sidecar spawn inherits them.
- **Fix (D-B8-1).** Split each MCP `spawn` into `start` (pick port, set env vars, spawn the child, drain its output; fast) and `supervise` (the bind wait; on failure kill + `register_unavailable`). `setup()` runs, on ONE background thread: start both MCPs → `start_main_sidecar(&AppHandle, port)` immediately (env vars already set) → supervise both MCPs concurrently. `setup()` returns at once. `start_main_sidecar` takes `&AppHandle`. The sidecar needs no change: a call before the MCP binds fails fast and marks the provider down until the next call succeeds (R15-LIFECYCLE-005, `openbb_mcp_provider.py:157`, `:250`); a never-binding MCP now costs one refused loopback connect per call before the registry falls back, where before the sidecar skipped it — acceptable, and it is what lets a late bind attach; no port file (the register's "resolve late" becomes "known before spawn"). The `--onedir` conversion stays the Tier-1 operator follow-up.
- **Test.** Rust: the orchestration is one function taking the three step closures; a test with stub `start`/`supervise` closures that sleep 2 s asserts the function returns in < 200 ms and that the main-sidecar step ran after both `start` steps and before any `supervise` finished. Needs-GUI record: the packaged cold launch paints the window during the MCP bind (the verifier records it; no GUI here).
- **Files.** `lib.rs`, `openbb_mcp.rs`, `sec_edgar_mcp.rs`.

**R15-LIFECYCLE-023: no error boundary.**
- **Mechanism (confirmed at base).** No `ErrorBoundary`/`componentDidCatch`/`onUncaughtError` anywhere under `src/`; `PanelHost.tsx:121` passes `collectPanelComponents(modules)` straight to `DockviewReact` (`:210`); `main.tsx:17` `createRoot` has no error options. One render throw unmounts the root.
- **Fix (D-B8-9).** Wrap each component in the `components` map in a class `PanelErrorBoundary` ("This panel crashed" + Reload panel (remount via key) + Copy error); `createRoot(…, { onUncaughtError, onCaughtError })` forwards the stack to a new `diag_log_line(line: String)` Tauri command in `lib.rs` (writes through the existing `diag_eprintln!`, R15-LIFECYCLE-008) — the release build has no console.
- **Test.** Vitest: `PanelHost` with a module whose panel throws → that panel shows the boundary, a sibling panel still renders.
- **Files.** `PanelHost.tsx`, `main.tsx`, `lib.rs` + test.

### W2: `provider-readiness-host-actions` (opus, 9 entries)

**Priority order:** UI-013 + AGENT-028 + UI-057 (C4 first) → UI-019 + UI-049 → CODE-AGENT-006 → AGENT-056 → AGENT-055 → AGENT-081.

**R15-UI-013 + R15-AGENT-028 + R15-UI-057: provider readiness is a boolean that erases why.**
- **Mechanism (confirmed at base).**
  - Three clients for one endpoint: `sidecar-client.ts:226-243` `validateProvider` (boolean; used by `StatusChrome.tsx:96` and `ChatSidebar.tsx:804`), `OnboardingFlow.tsx:73-89` `validateKey` (boolean), `KeyEntryDialog.tsx:175-189` `postValidate` (keeps `detail`). A stopped sidecar or unreachable provider therefore reads as "That key wasn't accepted" (onboarding) or opens onboarding with "No AI model is set up yet" (`ChatSidebar.tsx:804-813`). No timeout; Cancel is disabled while validating (`KeyEntryDialog.tsx:158-165`).
  - `OllamaAdapter.validate_key` (`ollama.py:269-278`) returns `False` for every exception (a stopped daemon = "no key") and `True` whenever `client.list()` answers, even with the selected model absent. The route (`routers/llm.py:99-111`) returns `ok/detail` only; a key with a trailing newline reaches the SDK as a header error labelled "transport error" (`:106-108`).
  - AGENT-028: `errors.py`'s `_BODY_RULES` already map an Ollama 404 "pull/not found" to `model_not_pulled` (errors.py ~`:191-198`), but no frontend path routes on it, and the validate gate passes because the daemon is up.
  - UI-057: `KeyEntryDialog.handleSave` sends `key` untrimmed (`:64-86`); onboarding trims.
- **Fix (D-B8-5, C4).**
  - Sidecar: `LLMKeyValidationRequest` gains `model: str | None`; the route strips `api_key` (and treats `""` as none) and answers `{ok, reason, detail}`: an adapter/SDK transport failure → `unreachable`; a keyless provider whose daemon is down → `unreachable`; a daemon up with the selected model not in `list()` → `model_not_pulled`; no key for a keyed provider → `not_configured`; rejected key → `invalid`. `OllamaAdapter.validate_key` distinguishes connection errors from `ResponseError` (the route needs the reason, so it returns/raises typed rather than `False`).
  - Frontend: new `src/lib/provider-validation.ts` `validateProvider(provider, {apiKey?, model?, signal?})` with `AbortSignal.timeout(15000)`, the one reader of C4 (its own POST, reading the body with `extractSidecarDetail`; a rejected fetch → `unreachable` "the data engine is not responding"). Callers: StatusChrome's `useProviderReady` (probe cache keyed on `ok`), ChatSidebar's gate (opens onboarding only on `not_configured`; on `model_not_pulled` opens onboarding at the existing "Download & use" step, `OnboardingFlow.tsx:490-502`; on `unreachable`/`invalid` states the reason in the status line and keeps the prompt), OnboardingFlow (`validateKey` deleted), KeyEntryDialog (`postValidate` deleted; `key.trim()` before validate + `setSecret`; Cancel aborts an in-flight validation).
- **Test.** `test_llm_router.py`: `"<key>\n"` reaches the adapter as `"<key>"`; an adapter raising `httpx.ConnectError` → `reason:"unreachable"`. `test_llm_ollama.py`: daemon with an empty model list and `model="qwen2.5:7b"` → `model_not_pulled`; a refused connection → `unreachable`. `provider-validation.test.ts`: each reason; a rejected fetch → `unreachable`. **Class pin (not written against):** a ChatSidebar test where the validate call rejects (sidecar down) does NOT open onboarding and says the data engine is not responding.
- **Files.** `ollama.py`, `routers/llm.py`, `models/llm.py`, `provider-validation.ts`, `StatusChrome.tsx`, `ChatSidebar.tsx`, `OnboardingFlow.tsx`, `KeyEntryDialog.tsx` + tests.

**R15-UI-019 + R15-UI-049: the readiness predicate is "has a BYOK key", and only onboarding promotes a keyed lane.**
- **Mechanism (confirmed at base).** `OnboardingBanner.tsx:21-33` shows when `probed && !hasAnyKey && !dismissed`; `dismissed` is component state, so a working local-model user sees "add a cloud provider key — or run a local model" on every launch. `useLLMProvidersStore` defaults `defaultProviderId: "ollama"` (`llm-providers.ts:128-130`) and only the onboarding Cloud step calls `setDefaultProviderId`; saving a key in Settings or `/key` leaves the keyless default in place.
- **Fix.** Banner gates on "no keyed provider AND the default keyless lane is not ready" (the C4 helper's probe, shared with StatusChrome's cache), and persists dismissal with the onboarding "seen" marker (`store/onboarding.ts`). On a successful key save (KeyEntryDialog `onSaved`, the `/key` path through the same dialog/store action), promote the keyed provider when the current default is keyless and not ready (never over a user-chosen keyed default), with a status note "Default provider is now X".
- **Test.** Banner test: Ollama default + model ready + no keys → no banner; dismissal survives a remount. Store test: default `ollama` not ready, key saved for `openrouter` → default becomes `openrouter`; default already `anthropic` (keyed) → unchanged.
- **Files.** `OnboardingBanner.tsx`, `provider-keys.ts`, `llm-providers.ts`, `KeyEntryDialog.tsx`, `store/onboarding.ts` + tests.

**R15-CODE-AGENT-006 (with W5's CODE-AGENT-007/-016): a hand copy of the model registry.**
- **Mechanism (confirmed at base).** `DEFAULT_MODEL_BY_PROVIDER`/`KNOWN_MODELS_BY_PROVIDER` are literals (`model-selection.ts:26-60`); `resolveModel` (`:113-118`) and the restore prune `isKnownModel` (`:69-77`) read them, not the live `/llm/providers` rows, so a `default_model` edit in `model_registry.json` ships stale and a JSON-only model is pruned on restore. `llm-providers.ts` `DEFAULT_PROVIDERS` is a third copy.
- **Fix (D-B8-6).** Import `sidecar/config/model_registry.json` in `model-selection.ts` and `llm-providers.ts` and derive `DEFAULT_PROVIDERS`, `DEFAULT_MODEL_BY_PROVIDER`, `KNOWN_MODELS_BY_PROVIDER` from it (the JSON import has no module-load cycle, unlike the `DEFAULT_PROVIDERS.map` the current comment warns about); `resolveModel` prefers the live provider row's `defaultModel` when present.
- **Test.** `model-selection.test.ts`: the three tables equal the JSON projection; a registry fixture whose `default_model` changed resolves to the new default with no override.
- **Files.** `model-selection.ts`, `llm-providers.ts` + test.

**R15-AGENT-056: the agent's default arrange is a factory reset.**
- **Mechanism (confirmed at base).** `host-actions.ts:901` defaults `pattern` to `"default"`; the dispatch's fallthrough (`:1497-1498`) calls `resetToDefaultLayout`, which does `setEnabledMap({})` and wipes every chart drawing and view (`store/workspace.ts:153-165`) while its interface doc says "clears layout customisations" (`:82`); catalog.py's `arrange_layout` enum defaults to `"default"` (~`:1299-1309`). Under AUTO it applies without review.
- **Fix (D-B8-7).** A layout-only `resetLayout()` store action (clear + default panels; drawings, views and module enablement kept); the agent default/unknown branch calls it; `resetToDefaultLayout` stays the explicit Settings/menu factory reset and its interface doc says what it clears; the proposal/gate text for the agent branch says "Reset the panel arrangement (drawings and modules kept)".
- **Test.** `host-actions.test.ts`: `arrange_layout({})` and `{pattern:"bogus"}` keep a drawing and a disabled module. `store/workspace.test.ts`: `resetToDefaultLayout` (the explicit Settings/menu path) still clears both, so the two actions stay distinct.
- **Files.** `store/workspace.ts`, `host-actions.ts`, `catalog.py` + tests.

**R15-AGENT-055: one template id, four layouts.**
- **Mechanism (confirmed at base).** `planLayout` (`layout-templates.ts:173-259`) and the menu's `MODE_PLANS` (`:638-679`) use the same ids for different layouts (`single-focus` = maximized chart vs chart+watchlist+news; `compare` = one maximized chart vs chart+equity-overview; `research-cockpit` with vs without news); `applyResearchSpaceLayout` (`:713-752`) and `essentialsResearchPlan` (`:371-392`) are third/fourth research variants. The menu payload ids are fossils (`:630-637` comment). catalog.py's arrange description is prose ("dual charts", heatmap) not derived from any plan (~`:1285-1295`; `:236-258` admits no heatmap panel exists).
- **Fix (D-B8-7, C8).** One plan per template id (the agent's meaning wins: it is the documented tool contract); the menu's four modes become explicit role ids (`technical`, `fundamental`, `macro`, `compare-desk`) in the same table, and `menu-bridge.ts` maps the Rust payload fossils (`single-focus`, `research-cockpit`, `macro-scan`, `compare`) to them once (no `lib.rs` change). The research-space and essentials variants stay (they are fit-downgrades), named for what they are. `sidecar/config/layout_templates.json` (C8) lists each agent template's panel roles; `layout-templates.ts` builds each plan's panel list from it (positions stay in TS) and catalog.py builds the arrange description and enum from it, so the tool never promises a panel the host does not place.
- **Test.** Vitest: for every C8 template, `planLayout(t)` places exactly the JSON roles; every menu fossil id maps to one plan. Pytest (`test_capability_catalog.py` or the catalog test): the arrange description names exactly the JSON panels for each template and no "heatmap"/"dual chart".
- **Files.** `layout-templates.ts`, `menu-bridge.ts`, `catalog.py`, `sidecar/config/layout_templates.json` + tests.

**R15-AGENT-081: the highlight argument is never consumed.**
- **Mechanism (confirmed at base).** `openCompanyOverview(symbol, highlightMetric)` (`host-actions.ts:284-296`) stores `highlightMetric` in `equity-command.ts:21-33`; no file under `src/modules/equity-overview/` reads it; the result (`host-actions.ts:1500-1510`, "spotlighting …") and the proposal preview (`:1127`) are composed from the input.
- **Fix (D-B8-8).** The equity-overview module exports its highlightable metric ids (the keys its rows render; one list the panel and the host action share). `EquityOverviewPanel` consumes `command.highlightMetric`: scrolls the matching row into view and applies a transient accent ring (`data-highlighted`). Host-action results are synchronous (`done(label)`, `host-actions.ts:821`), so the result and the proposal preview are composed from that shared list, not the raw input: a known metric → "spotlighting P/E"; an unknown one → "opened X's overview — Y is not a metric on that panel" (the model reads the truth either way).
- **Test.** Panel test: a command with `highlightMetric:"pe_ratio"` marks that row `data-highlighted`. `host-actions.test.ts`: an unknown metric's result says it is not on the panel; a known one names it.
- **Files.** `EquityOverviewPanel.tsx`, new `equity-overview/metrics.ts`, `equity-command.ts`, `host-actions.ts` + tests.

### W3: `data-error-honesty` (opus, 9 entries)

**Priority order:** DATA-061 + AGENT-061 (C5 mapper first) → AGENT-030 → LEAD-005 → UI-053 + DATA-081 → UI-015 + UI-030 + UI-029.

**R15-DATA-061 + R15-AGENT-061: one class (`ProviderError.kind` dropped and re-derived).**
- **Mechanism (confirmed at base).**
  - `ProviderError(message, kind=None)` knows only `rate_limited` (`errors.py:26-40`). The app handler maps every uncaught `ProviderError` to `502 {"detail": str(exc)}` (`app.py:348-351`). 27 route blocks re-map it (`crypto` 1, `disclosures` 5, `earnings` 4, `fundamentals` 4, `macro` 5, `screener` 3, `sec_filings` 5); only `fundamentals.get_fundamentals` reads `kind` (`routers/fundamentals.py:110-121`); its siblings (income/balance/cashflow/ratings) are kind-blind 502s.
  - yfinance: `_provider_error` (`yfinance_provider.py:53-65`) classifies only the rate limit; a nonexistent ticker surfaces yfinance's internal `'PriceHistory' object has no attribute '_dividends'` (raw library text in a 502, live `GET /quotes/MAZAGONDOCK`); yfinance 1.3.0 hides history exceptions by default (`YfConfig.debug.hide_exceptions`), so a network outage returns an EMPTY frame (`get_history`, `:375-378`), which `correctness_gate.EmptySeriesError` + the history route's downgrade (`routers/history.py` `get_history`) turn into a clean 200 "No price data" while `/health` stays green.
  - The `in_eod_only` sub-claim is already fixed at base (`_empty_series_reason` gates on a KNOWN IN listing, R15-DATA-064); not in scope.
  - AGENT-061: `_fetch_once` (`agent_tools/fundamentals.py:60-73`) stringifies the exception; `_classify_reason` (`:44-51`) guesses from markers none of the real not_found messages carry (the registry's `kind="not_found"` "no provider returned usable …", yfinance's "no company record"), so a missing instrument reads `provider_error`.
- **Fix (D-B8-10, C5).**
  - `ProviderError.kind: Literal["rate_limited", "not_found", "network"] | None`. One mapper beside it (`errors.provider_error_response(exc) -> (status, body)`): 429/404/503/502 with the C5 body (human sentence + `code` + `action`; the raw text only in the sidecar log). The app handler calls it; delete the 27 route blocks that only re-map (keep any block that does something else, e.g. a coverage answer, and route its failure through the same mapper).
  - yfinance: `_provider_error` classifies `YFTickerMissingError`/`YFPricesMissingError`/`YFTzMissingError` and the library-internal `AttributeError` on a missing ticker as `not_found`, and transport exceptions (`requests`/`curl_cffi`/`httpx`/`ConnectionError`/`Timeout` by type name, as `_is_rate_limited` does) as `network`. `get_history` surfaces history exceptions for its own call (not a process-wide config flip) so a transport failure raises `kind="network"` instead of returning an empty frame; the empty-series downgrade stays for a genuinely empty series.
  - Agent tool: `_fetch_once` carries `exc.kind`; `_classify_reason` reads it first, markers only when `kind is None`.
- **Test.** New `test_provider_error_mapper.py` with TestClient: a route raising each kind → 429/404/503/502 and the C5 body (detail is a string, no library text). **Class pin on routes the fix was not written against:** `GET /earnings/{symbol}` with a `rate_limited` provider → 429; `GET /macro/{id}` with a FRED `not_found` → 404 (both formerly flattened by their own blocks). `test_yfinance_provider.py`: a stubbed ticker raising `AttributeError("'PriceHistory' object has no attribute '_dividends'")` → `not_found`; a stubbed history raising a connection error → `network` (no empty series). `test_fundamentals_tool.py`: the registry's `kind="not_found"` error and yfinance's not_found both classify `not_found`.
- **Files.** `errors.py`, `app.py`, the 7 routers + `history.py`, `yfinance_provider.py`, `agent_tools/fundamentals.py` + tests. `ChartPanel.tsx` renders the 503/`network` sentence instead of "No price data" (it already shows the SidecarError message on error; confirm, do not restyle).

**R15-AGENT-030: the router last-resort guard blames the provider.**
- **Mechanism (confirmed at base).** Adapters humanize their own failures (`ollama.py`, `openai.py`, … call `humanize`), so what reaches the SSE routers' `except Exception` (`routers/llm.py:141-145`, `routers/agents.py:105-110`) is a runtime/tool/store fault; `error_frame` (`errors.py:434-452`) runs `humanize(None, exc)`, whose heuristics match `"connect"`/`"timeout"` anywhere in `str(exc)` (`errors.py` ~`:335-352`), so `RuntimeError("database connection is closed")` becomes "Could not reach the AI provider — check your network".
- **Fix (D-B8-11).** `error_frame` (used only by the two router guards) emits `code:"internal"`, message "The terminal hit an internal error.", detail = `type: message`; `humanize`'s exception heuristics match on the class name only (the adapters' own calls keep classifying `ConnectError`/`APIConnectionError`/`ReadTimeout` by class). No router edit needed.
- **Test.** `test_errors.py`: `error_frame(RuntimeError("database connection is closed"))` → `code:"internal"`; `humanize("openai", httpx.ConnectError("x"))` still → `network`; a `ValueError("connection pool timeout")` via `humanize` no longer says network.
- **Files.** `errors.py`, `test_errors.py`.

**R15-LEAD-005: the yfinance quote is dated now().**
- **Mechanism (confirmed at base).** `get_quote` builds `Quote(timestamp=_utcnow())` (`yfinance_provider.py:356`) from `fast_info`; only yfinance does this (every other provider dates the quote from its bar or trade time). `fast_info.last_price` is computed from the ticker's history fetch, whose metadata carries `regularMarketTime`.
- **Fix (D-B8-13).** Date the quote by `Ticker.get_history_metadata()["regularMarketTime"]` (public API; populated by the same fetch that produced the price), else the last price bar's timestamp. `Quote.timestamp` stays required: the price always comes from one of those two sources, so there is no third case to invent.
- **Test.** `test_yfinance_provider.py`: a closed-market fixture whose metadata `regularMarketTime` is two days old → `timestamp` equals it; the class case the fix was not written against: metadata without `regularMarketTime` → the last bar's time.
- **Files.** `yfinance_provider.py` + test.

**R15-UI-053 + R15-DATA-081: one class (a `/` in a path parameter never routes).**
- **Mechanism (confirmed at base).**
  - `routers/macro.py:71` `@router.get("/{series_id}")`; every IMF catalog id carries `/` (`imf_provider.py:44-68`, `IFS/A.US.NGDP_R_K_IX`); `macro.ts` sends `encodeURIComponent(seriesId)`; Starlette decodes `%2F` before matching → 404. Same for `/quotes/{symbol}` (`quotes.py:50`), `/history/{symbol}` (`history.py:67`), `/indicators/{symbol}` (`indicators.py:39`) with `BTC/USDT`.
  - DATA-081's other half: asset class is not part of the symbol identity between panels. The watchlist row click calls `openCompanyOverview(row.entry.symbol)` (`WatchlistPanel.tsx:539-541`) for a crypto row (equity overview has no crypto path); the chart calls `sidecarApi.history(symbol, timeframe)` with the equity default (`ChartPanel.tsx:408`, compare `:1047`) and `chart-command.ts` carries no asset class; a portfolio lot entered as `BTC/USDT` quotes through `/quotes/BTC%2FUSDT` (404) and its cost is formatted in the region currency.
- **Fix (D-B8-12).** `{series_id:path}`/`{symbol:path}` converters on the four routes (declare `/macro/search` and `/macro/catalog` before the path route). A slash pair (`BASE/QUOTE`) is the app's crypto notation (`symbols.ts:17-27` DEFAULT_SYMBOLS), so one helper `assetClassOf(symbol)` in `src/store/symbols.ts` gives the identity everywhere a symbol crosses panels: a crypto watchlist row loads the chart (not the equity overview); the chart passes the asset class to history, compare and indicators; the portfolio quotes a crypto lot with `assetClass:"crypto"` and formats its cost in the pair's quote currency (USDT), never the region currency.
- **Test.** `test_macro_router.py`: `GET /macro/IFS%2FA.US.NGDP_R_K_IX?provider=imf` reaches the IMF provider (stubbed) → 200; `/macro/search` still routes. `test_quotes.py`/`test_history.py`: `BTC%2FUSDT` with `asset_class=crypto` → 200. **Class pin not written against:** `GET /indicators/BTC%2FUSDT?asset_class=crypto` → the route matches (stub). Vitest: a crypto watchlist row click loads the chart with the crypto class; a `BTC/USDT` portfolio lot is priced and shows no `₹`.
- **Files.** `routers/macro.py`, `quotes.py`, `history.py`, `indicators.py`, `WatchlistPanel.tsx`, `ChartPanel.tsx`, `chart/api.ts`, `chart-command.ts`, `symbols.ts`, `PortfolioPanel.tsx`, `portfolio/api.ts` + tests.

**R15-UI-015 + R15-UI-030 + R15-UI-029: the retry hook cannot tell transient from deterministic.**
- **Mechanism (confirmed at base).**
  - `useRetryOnSidecarReady` retries every rejection 12 times with backoff (`use-sidecar-retry.ts:78-110`); its contract makes callers re-throw a plain `Error` (`MacroPanel.tsx:38-47`: `throw new Error(status.error)`), so a deterministic 502 (a keyless fresh install hitting `/macro`) is hammered for ~50 s with loading/error flicker. `NewsFeedPanel.tsx:214-251` hand-rolls the same loop; Earnings (`:110-119`), SEC (`SecFilingsPanel.tsx:62-72`, `sec.ts:241-243`) and Screener (`:104-111`) flatten likewise.
  - UI-030: `useRetryOnSidecarReady(loadDefault, [provider, seriesId])` (`MacroPanel.tsx:48`) re-arms the cold-boot loop on every user tab/series change.
  - UI-029: `macro.ts` `loadCatalog` swallows every error and resolves (`:127-137`), so `MacroSeriesPicker`'s error + Retry UI (`:140-170`) never renders and the skeleton pulses forever.
- **Fix (D-B8-14, C1).** The hook retries only transient failures (C1: a non-`SidecarError`, status 0 or 503) and settles on anything else (one attempt, error state). The store actions keep the original error (the `SidecarError` status rides the status entry) and the panels' wrappers re-throw it, never a flattened `Error`. `MacroPanel`: the hook covers the mount default only; provider/series changes call `loadSeries` once (and a tab switch picks that provider's default id). `NewsFeedPanel` uses the hook instead of its copy. `loadCatalog` records `catalogError` in state; the picker renders it with Retry.
- **Test.** Hook test: a `SidecarError(502)` → exactly one attempt and the error state; a `TypeError` (and `SidecarError(0)`) → retries. Macro panel test: switching the provider tab issues one request. Picker test: `loadCatalog` failing → error + Retry visible. **Class pin not written against:** the Screener panel with a 502 makes one request.
- **Files.** `use-sidecar-retry.ts`, `MacroPanel.tsx`, `macro.ts`, `MacroSeriesPicker.tsx`, `NewsFeedPanel.tsx`, `EarningsCalendarPanel.tsx`, `SecFilingsPanel.tsx`, `ScreenerPanel.tsx`, `sec.ts` + tests.

### W4: `resolver-exchange-lanes` (opus, 12 entries; five are small)

**Priority order:** CODE-DATA-003 (one payload, C9) → UI-039 → DATA-051 → DATA-058 → CODE-DATA-002 → LIFECYCLE-019 + LIFECYCLE-022 → AGENT-045 → CODE-PLATFORM-021 → DATA-084/085/086.

**R15-CODE-DATA-003 + R15-UI-039 + R15-DATA-051: the identity payload is hand-copied, partial and bypassed.**
- **Mechanism (confirmed at base).**
  - The router's `_instrument_payload` (`routers/resolve.py:27-55`: confidence rounded to 4 places, the `rename` block with `effective_date`/`note`) and the tool's `_instrument_dict` (`agent_tools/resolve_symbol.py:25-41`: 3 places, no `rename`) are two hand copies that already drifted.
  - `autocomplete` (`symbol_resolver.py:1210-1268`) builds rows straight from the masters; only a retired query gets the annotated current instrument, other rows skip `_rename_instrument`/`_enrich_instrument`, yet `/resolve/autocomplete` (`routers/resolve.py:126`) projects them through the payload that promises `isin`/`bse_code`/`industry`/`former_name` (always null) and can list a retired ticker (GUJGASLTD) unannotated.
  - DATA-051: `_bse_master` reads the BSE group (`:313-334`, rows `[CODE, SYMBOL, NAME, GROUP, ISIN, STATUS]`; `M`/`MT`/`MS` = SME) and every use discards it (`_group`); the NSE master's type `SM` (Emerge) is likewise unused for identity; no equity `face_value` exists (the masters' regenerators drop the exchange lists' face-value column: `regenerate_bse_master.py:175`, `regenerate_nse_master.py:120`).
- **Fix (D-B8-15, C9).** One `instrument_payload(inst)` in `symbol_resolver` used by the router and the tool (the tool drops nothing it does not need by name). Autocomplete rows pass `_rename_instrument` + `_enrich_instrument` (both exist). The payload adds `board` (`"SME"` for BSE `M*` groups or NSE `SM`, else `"mainboard"`; `null` for US), `exchange_group` (the raw BSE group), `face_value`: extend both regenerators with the face-value column (NSE `EQUITY_L.csv` " FACE VALUE", BSE ListOfScripData `FACE_VALUE`), rerun them (network; commit the regenerated JSON and name the `_generated` date), and read it in `_nse_master`/`_bse_master` (older 3/6-column rows stay readable).
- **Test.** `test_resolve_symbol_tool.py`: for a renamed fixture the tool dict is a subset of the router payload INCLUDING `rename` (the drift pin). `test_resolver_rename.py`: `autocomplete("GUJGAS")` lists GUJENERGY annotated as renamed from GUJGASLTD, never the bare retired row; enriched `isin` is set for an NSE row. `test_resolve_router.py`: SMR (BSE `MT`) → `board:"SME"`; ELCIDIN → `face_value` as the master carries it.
- **Files.** `symbol_resolver.py`, `routers/resolve.py`, `agent_tools/resolve_symbol.py`, `resolver_masters/regenerate_{bse,nse}_master.py`, `resolver_masters/{bse,nse}_instruments.json` + tests.

**R15-DATA-058: a better foreign fuzzy match is truncated out.**
- **Mechanism (corrected verdict).** The name matcher scans the US master (`:873`) and SIFY scores 0.913 against 0.80 for the best IN row, but the stray `(ADR)` token keeps the query out of the exact/canonical bands, so every row is `BAND_FUZZY`; the sort key `(band, locale, score)` (`:881`) under an IN session ranks every IN fuzzy row above SIFY and `_MAX_CANDIDATES = 6` (`:121`) cuts it.
- **Fix (D-B8-15).** Keep R11 D58c (locale-first order within a band: an IN session still LEADS with IN rows), and reserve the last candidate slot for the best-scoring cross-region row of the top band when it outscores every in-region row of that band and would otherwise be cut. No reordering of `best`.
- **Test.** `test_symbol_resolver.py`: `resolve("Sify Technologies Ltd (ADR)", "IN")` candidates include SIFY. **Not written against:** a US company name plus a stray token under IN (e.g. `"Infosys Ltd ADR"` must still lead with INFY on NSE; `"Wipro ADR"` keeps WIT among candidates when it outscores).
- **Files.** `symbol_resolver.py` + test.

**R15-CODE-DATA-002: the fuzzy scan is not memoized.**
- **Mechanism (confirmed at base).** The masters are `lru_cache`d, but `_resolve_masters` re-scores ~17.9k names with `SequenceMatcher` on every call (`:866-881`); it is not pure as a whole (step 3b reads the async rename map, step 4 is the live lookup, the masters refresh at runtime via `refresh_masters`).
- **Fix.** Memoize only the pure banded scan (extract the step-3 scoring into `_scan_names(query_lc, n_words, region, suffix_exchange)`, `@lru_cache(maxsize=2048)`), cleared in `refresh_masters()` and `reset_caches_for_tests()`; the retired-symbol step, the live lookup, rename and enrichment stay outside the memo.
- **Test.** A second identical `resolve()` makes zero `SequenceMatcher` calls (patched counter) and returns an equal `Resolution`; after `refresh_masters()` the scan runs again.
- **Files.** `symbol_resolver.py` + test.

**R15-LIFECYCLE-019 + R15-LIFECYCLE-022: an upstream failure is recorded as a legitimate state.**
- **Mechanism (confirmed at base).**
  - `_refresh_guarded` stamps `_refreshed_on = today` in `finally` (`nse_symbol_change.py:454-460`) whether or not `fetch_latest` loaded anything (it returns `None` on failure without raising), so `schedule_refresh` (`:463-476`) never retries that IST day; the failure log prints `str(exc)`, empty for httpx timeouts (`:401-402`); nothing tells `/resolve` the rename lane is off.
  - `nse_bhavcopy._fetch_day` returns `"missing"` on the PRIMARY 404 before trying the fallback host (`:345-348`: "the fallback host would 404 identically"), and `fetch_latest` writes the empty holiday marker for every past-date `missing` (`:388-394`) with no log, so a moved archive path reads as a week of holidays (7-day TTL).
- **Fix (D-B8-16).** Rename lane: stamp `_refreshed_on` only after a non-`None` load (fresh or stale-cache hydrate); a failure schedules a bounded retry (backoff, e.g. 1, 5, 15 min, then the next day); log `type(exc).__name__`; `/resolve` answers `rename_lane: "unavailable"` while the map is empty. Bhavcopy: a primary 404 tries the fallback once; a past weekday is marked a holiday only when it is on the NSE holiday table (`services/locale.py`) — otherwise it is not cached, and after N consecutive non-holiday weekday 404s one WARNING names the URL.
- **Test.** `test_nse_symbol_change.py`: first download `ConnectTimeout`, then `schedule_refresh` after the backoff → two attempts and the map loaded. `test_nse_bhavcopy.py`: primary 404 + fallback rows → `fetch_latest` returns the fallback data and writes no empty marker; a non-holiday weekday with both 404 → no holiday marker. **Class case not written against:** the rename lane's stale-cache hydrate counts as loaded (no retry storm when the network is down but a recent cache exists).
- **Files.** `nse_symbol_change.py`, `nse_bhavcopy.py`, `routers/resolve.py` + tests (`fundamentals_warm.py` only if the bhavcopy return shape changes; it should not).

**R15-AGENT-045 (carried; batch-7 not certified): the two-symbol failure drops the per-symbol reasons.**
- **Mechanism (batch-7 verifier).** `_compare_one` now builds the right "unresolved name: MAZAGONDOCK …" entry, but `_compare_symbols` returns `{ok: False, message: "fewer than two symbols resolved — 1 of 2 returned a quote"}` without `symbols` (`compare_symbols.py:250-258`), which is exactly the two-symbol repro.
- **Fix.** The `ok: False` payload carries `symbols: results` and a message that names each failed input with its own reason (and `candidates` when ambiguous).
- **Test.** `test_compare_symbols.py`: `["COCHINSHIP", "MAZAGONDOCK"]` with MAZAGONDOCK unresolvable → the message says unresolved name, not "no quote". **Not written against:** a 3-symbol call where two fail → both reasons present.
- **Files.** `compare_symbols.py` + test.

**R15-CODE-PLATFORM-021 (carried): the positions ledger keeps write routes.**
- **Mechanism (confirmed at base).** Holdings live in the workspace blob; `host-actions.ts` no longer syncs to the sidecar (`f37543d`); the only reader is the legacy import `GET /portfolio/positions` (`workspace.ts:932-946`, `portfolio/api.ts:65-70`). `routers/portfolio.py:25-45` still serves POST/PUT/DELETE backed by `portfolio_db` writers, with no caller.
- **Fix (D-B8-17).** Delete the three write routes and the service writers they alone use; keep `GET /positions` and the reader; fix the module docstrings (`portfolio_db.py`, `models/portfolio.py`, the `models/__init__.py` re-export if it names a deleted type). Tests of the deleted writers go with them (logged in the commit); the GET test seeds rows with SQL, not a production writer.
- **Test.** `test_portfolio.py`: `POST/PUT/DELETE /portfolio/positions` → 405; `GET` still returns seeded legacy rows.
- **Files.** `routers/portfolio.py`, `portfolio_db.py`, `models/portfolio.py`, `models/__init__.py` + test.

**R15-DATA-084 + R15-DATA-085 + R15-DATA-086: Macro provider adapters dress failures and shapes up as data.**
- **Mechanism (confirmed at base).** `openbb_mcp_provider.py:550` `row.get("value") or row.get(series_id)` drops a real `0.0`. `world_bank_provider.py:205` guards `callable(info.items)` but `items` is a list, so the title branch never runs and every series is titled with its raw code. `world_bank_provider.search` (`:228-260`) turns an upstream failure into the curated rows scored like hits, and `macro_router.search` (`:150-160`) caches that for 6 h.
- **Fix (D-B8-18).** `row["value"] if "value" in row else row.get(series_id)`; read `info.items[0]` without the callable guard; `search` raises `ProviderError` (kind `network` for transport) like FRED/IMF, and `macro_router` caches only a result from a successful upstream call (never an empty list).
- **Test.** `test_openbb_mcp_provider.py`: a `0.0` observation survives. `test_macro_providers.py`: a wbgapi-shaped `info` → the human title. `test_macro_cache.py`: a failing search raises and writes no cache row.
- **Files.** `openbb_mcp_provider.py`, `macro/world_bank_provider.py`, `macro/macro_router.py` + tests.

### W5: `agent-runtime-research` (opus, 9 entries)

**Priority order:** AGENT-046 → CODE-AGENT-004 + LEAD-019 → CODE-AGENT-007 + CODE-AGENT-016 → LIFECYCLE-014 → CODE-AGENT-008 (C6) → RESEARCH-027 → CODE-RESEARCH-003 (last: the largest deletion).

**R15-AGENT-046 (carried): ids are minted only when empty or seen this turn.**
- **Mechanism (batch-6/7 verifier, confirmed at base).** `invoke_agent` mints `call_<uuid>` only `if not event.tool_call_id or event.tool_call_id in seen_call_ids` (`agent_runtime.py:2063-2065`), and `seen_call_ids` starts empty per invocation (`:2021`). Gemini's per-stream `set_chart_symbol_0` reused in the next turn is therefore kept, and a late ack recorded for turn 1 (`action_ledger.record`, process-global, 600 s TTL) grounds turn 2's call. `action_ledger.take` (consume-once) already exists.
- **Fix (D-B8-21).** The runtime mints every tool-call id (drop the condition and `seen_call_ids`); provider ids are never identity. Derived ids (`__autobrief`, `auto-backtest-`) inherit uniqueness.
- **Test.** `test_agent_runtime.py`: two `invoke_agent` turns whose fake adapter emits the same Gemini-style id; an ack recorded for turn 1's minted id arriving during turn 2 does not ground turn 2's call. **Not written against:** an Ollama round with two calls whose ids are both `""` → two distinct ids and both acks resolve.
- **Files.** `agent_runtime.py` + test.

**R15-CODE-AGENT-004 + R15-LEAD-019: the BudgetGuard meter is wrong at the adapter and the price table.**
- **Mechanism (confirmed at base).** `gemini.py:181-186` reports `input_tokens=prompt_token_count`, `output_tokens=candidates_token_count`; google-genai bills `thoughts_token_count` and `tool_use_prompt_token_count` too, so a thinking round is under-metered. `budget_guard.price_per_million` (`:62-80`) falls back to `DEFAULT_RATE_PER_M` for a model with no table row, so an OpenRouter `…:free` slug records spend against a real ceiling (batch-7 verifier, live AGENT-039 run).
- **Fix (D-B8-22).** `output = candidates + thoughts`, `input = prompt + tool_use_prompt` (None-safe). An OpenRouter model id ending `:free` prices at `0.0` (OpenRouter's own convention; one rule in `price_per_million`, not a row per slug).
- **Test.** `test_llm_gemini.py`: usage `thoughts=6000, candidates=800` → `output_tokens == 6800`, and a BudgetGuard with a 5000-token ceiling trips on it. `test_budget_guard.py`: `("openrouter", "nvidia/nemotron-3-super-120b-a12b:free")` → 0.0; a priced OpenRouter slug keeps its rate.
- **Files.** `gemini.py`, `budget_guard.py` + tests.

**R15-CODE-AGENT-007 + R15-CODE-AGENT-016 (with W2's CODE-AGENT-006): a hand copy of the registry.**
- **Mechanism (confirmed at base).** `llm/__init__.py:33-47` hardcodes DeepSeek/xAI/OpenRouter base URLs beside a "must match the registry" comment while `PROVIDER_INFO` (`:54-64`) already derives from `model_registry`. `agents/_schema.json:39` enumerates seven provider ids (no `openrouter`), so an agent JSON with `defaultProvider: "openrouter"` fails schema validation and is skipped with a warning (`agent_runtime._discover_specs`, `:255-270`); `models/custom_agent.py` already derives its allow-list from the registry.
- **Fix (D-B8-6).** `model_registry.default_base_url_for(provider)` beside `default_model_for`; the three constants come from it. The schema's provider enum is filled from `model_registry.provider_ids()` when `_load_schema` reads it (the JSON keeps no enum, or the loader overwrites it; pick one and say so in the file).
- **Test.** New `test_llm_registry_parity.py`: a monkeypatched registry base URL reaches `get_provider("deepseek")`; the loaded schema's provider enum equals `set(model_registry.provider_ids())`; an agent JSON with `defaultProvider: "openrouter"` loads.
- **Files.** `llm/__init__.py`, `model_registry.py`, `agents/_schema.json`, `agent_runtime.py` + test.

**R15-LIFECYCLE-014: a bad or missing agent JSON silently shrinks the roster.**
- **Mechanism (confirmed at base).** `_discover_specs` (`agent_runtime.py:243-285`) returns `{}` for a missing dir with no log and skips a malformed file with a WARNING; the packaged app keeps no log a user can read; `/agents` answers 200 with the shorter roster. The smoke test already asserts `/agents` count > 0 (`smoke-test-sidecars.mjs:44-46`).
- **Fix (D-B8-23, C7).** Keep skipped files and reasons in a module-level list; ERROR log a missing agents dir; `/health` (`routers/health.py:12-27`) adds `agents_degraded`; the smoke test also asserts `agents_degraded == []`.
- **Test.** `test_health.py` (or `test_agent_runtime.py`): a temp agents dir with one bad JSON → `/health.agents_degraded` names that file and reason; a clean dir → `[]`.
- **Files.** `agent_runtime.py`, `routers/health.py`, `scripts/smoke-test-sidecars.mjs` + test.

**R15-CODE-AGENT-008: the runtime decodes the research tool's private payload.**
- **Mechanism (confirmed at base).** `_auto_publish_event` (`agent_runtime.py:1184-1325`) knows `web.citations` OR `web.results`, `excerpt` OR `snippet`, top-level vs nested `web_available`, the FAST web note/reason, `_LOOP_TO_MODE_DEPTH`/`_RESEARCH_MODEL_STOP_TO_MODE_DEPTH` (`:1135-1157`) and `briefFromInput`'s snake_case keys; a research payload rename silently empties the brief's sources (the sources-block comment records one such regression).
- **Fix (D-B8-19, C6).** The research tool (`agent_tools/research.py`, where `_stamp_execution` already attaches the execution record, `:100-137`) builds `brief` from its own engine payload: the payload-variant knowledge and the loop→(mode, depth) tables move there. `_auto_publish_event` publishes `payload["brief"]` (or the disambiguation input) verbatim and keeps only its gate conditions (ok, execution present). The MCP/tool result gains an additive key.
- **Test.** `test_research_tools.py`: for a FAST payload (citations only under `web`), a DEEP payload (top-level `sources`) and a research-model payload, the tool's `brief` has non-empty `sources` and the right `mode`/`depth`. `test_agent_runtime.py`: the auto-published input equals `brief` byte for byte.
- **Files.** `agent_tools/research.py`, `agent_runtime.py` + tests.

**R15-RESEARCH-027: NORMAL research runs 33-38 s against the ≤ 15 s target (FR-070).**
- **Mechanism (confirmed at base).** `gather_fast` awaits the structured fan-out (`fast.py:549-553`) and only then runs the one web round (`:575-590`), although the web query needs only the resolved target; inside the fan-out, `snapshot_structured` awaits price+fundamentals and then seven witness legs (`:278-345`) with no per-leg timeout; nothing measures leg latency.
- **Fix (D-B8-19).** Run the web round concurrently with the structured fan-out; wrap each witness leg in its own timeout (a timed-out leg is dropped like a failed one and named in a step, as the existing per-leg isolation does); stamp `latency_ms` on each leg's step. The brief still auto-publishes the moment the tool returns (before the model's prose turn), so the cockpit lands at max(gather, web) instead of their sum; no mid-tool publish channel is added.
- **Test.** `test_research_fast.py`: one witness stub sleeping 20 s and a web stub sleeping 2 s → `gather_fast` returns within the leg budget + margin, that leg is reported timed out, and the web round's start precedes the fan-out's end.
- **Files.** `research/fast.py` + test.

**R15-CODE-RESEARCH-003: a drifted second deep loop behind an except.**
- **Mechanism (confirmed at base).** `deep.run_deep_research` (`deep.py:1167-~1500`) is a second plan→researchers→reflect loop (without iter's R13 adaptive round slice and observed-latency wall) reached only from `_single_pass_fallback` (`deep_research.py:322-335`) when `run_iter_research`/`run_heavy_research` raise (`:297`, `:320`), which they never do by design; on that path it would re-run a full, differently-behaving deep loop.
- **Fix (D-B8-20).** Delete `run_deep_research` and `_single_pass_fallback`; an unexpected iter/heavy exception returns the honest failure result (`ok: False`, the reason, the `execution` record stamped with it), never a second loop. Keep every `deep.py` helper iter/heavy import. Fix the `deep.py`, `research/__init__.py` and `deep_research.py` docstrings.
- **Tests (state rules).** `test_research_deep.py`'s subject is deleted: tests that pin behaviour iter still owns (synthesis truncation note, budget abort→synthesize, etc.) move to `test_research_iter.py` against `run_iter_research`; tests of the deleted loop alone are removed, each named with the reason in the commit. `test_b5_runtime_synthesis.py`'s `deep` parametrization and `test_b6_research_funnel.py`/`test_research_iter.py`'s fallback monkeypatches are retargeted to the new failure result. **Pin:** an iter stub that raises → the tool returns `ok: False` with the reason and no second loop runs.
- **Files.** `research/deep.py`, `agent_tools/deep_research.py`, `research/__init__.py` (docstring) + the tests above.

---

## 3. Integrator run order and gates

**Stall rule (all roles).** No single tool call may run longer than ~120 s. `pnpm ci-local`, full pytest/vitest, cargo, PyInstaller builds, sidecar boots and soak waits start detached (`nohup <cmd> > <log> 2>&1 &` or `run_in_background`) and are polled with separate short calls (`sleep 60; tail -n 5 <log>`); never an `until … sleep` loop inside one call, never a foreground whole-suite pytest. Emit a tool call at least every 2 minutes.

1. Work in a scratch worktree (`git worktree add <scratchpad>/b8-int 004-r4-experience-rebuild`), never the main repo (it holds uncommitted `CLAUDE.md` and ledger edits). Run `git branch --show-current` before every merge.
2. Audit each branch through `origin/worktree-agent-batch-8-<Wn>-<name>`: `git merge-base --is-ancestor b47ed2d origin/<branch>` (stale base → re-dispatch) and `git diff --stat b47ed2d..origin/<branch>` touches only that writer's §1 files.
3. Merge `--no-ff` in this order, running that writer's pytest and vitest files (detached) after each:
   - **W4** — sidecar-only; the regenerated masters land first.
   - **W5** — `agent_runtime.py`/research; run `test_agent_runtime*.py`, `test_agents_router.py`, `test_capability_catalog.py`, `test_mcp_catalog_parity.py`, `test_mcp_server.py`, `test_research_*.py`, `test_b5_*`, `test_b6_*`, `test_health.py`.
   - **W3** — `app.py`/`errors.py`/routers + panels; run every router test (`test_*_router.py`, `test_quotes.py`, `test_history.py`) since the 27 blocks moved to one mapper.
   - **W2** — before W1: it moves every `validateProvider` caller to `src/lib/provider-validation.ts`; run the catalog/MCP parity tests again (the arrange description changed).
   - **W1** — Rust + transport last (widest blast radius).
   - **The one integrator edit:** after W1, `grep -rn "validateProvider" src` must show only `provider-validation.ts` and its test; delete the orphaned boolean `validateProvider` from `sidecar-client.ts` (base `:218-243`) in the W1 merge commit, then `pnpm typecheck`. Nothing else is edited by the integrator.
4. Gates after all five (export `PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH` first; everything long detached):
   - `ruff format --check sidecar && ruff check sidecar`; `pnpm format:check`, `pnpm lint`, `pnpm typecheck`.
   - `cargo fmt --check`, clippy `-D warnings`, `cargo test` (W1 changes Rust).
   - `node scripts/ensure-all-sidecars.mjs --force` (all three on Python 3.13; `config/layout_templates.json` rides the existing `config/` `--add-data`), `pnpm ci-local` with the exit code recorded, `node scripts/smoke-test-sidecars.mjs` (now also asserts `agents_degraded == []`).
5. Grep checks:
   - `app.py`'s `ProviderError` handler calls the one mapper; `grep -c "except ProviderError" sidecar/routers/*.py` is 0 except blocks that do more than re-map (each named in W3's commit); `errors.error_frame` emits `code: "internal"`.
   - `routers/macro.py`, `quotes.py`, `history.py`, `indicators.py` declare `:path`; `/macro/search` and `/macro/catalog` are declared before `/{series_id:path}`.
   - `yfinance_provider.py` has no `timestamp=_utcnow()`.
   - `agent_runtime.py` has no `in seen_call_ids` (every call minted) and no `_LOOP_TO_MODE_DEPTH`; `deep.py` has no `run_deep_research`; `deep_research.py` has no `_single_pass_fallback`.
   - `llm/__init__.py` has no `https://` literal; `agents/_schema.json` has no hand-written provider list (or the loader overwrites it, as W5 states).
   - `model-selection.ts` has no provider→model literal table; it imports `model_registry.json`.
   - `store/workspace.ts` has a layout-only reset and `host-actions.ts`'s arrange fallthrough calls it, never `resetToDefaultLayout`.
   - `src/` has exactly one reader of `/llm/keys/validate` (`provider-validation.ts`); `KeyEntryDialog.tsx` trims.
   - `sidecar-client.ts` exports `sidecarRequest`; `delegate-runs.ts`, `AgentBuilderPanel.tsx`, `SettingsPanel.tsx`, `hardware-fit.ts` contain no `fetch(`; `streaming.ts` has no `safeReadDetail` returning raw text into an error.
   - `lib.rs` has no `.join()` of the MCP threads inside `setup`; the drain loop handles `CommandEvent::Terminated`.
   - `routers/portfolio.py` has no `@router.post`/`put`/`delete`.
   - `nse_symbol_change.py` sets `_refreshed_on` only after a successful load; `nse_bhavcopy.py`'s primary 404 path tries the fallback.
6. Record the §6 decisions in `docs/redesign/DECISIONS.md` and `CHANGELOG.md` at merge; writers do not edit docs.
7. Certification notes: `LIFECYCLE-001` certifies on the Rust orchestration test + a needs-GUI record for the packaged cold launch (window paints during the MCP bind); `LIFECYCLE-010`/`UI-014` certify on the cargo/vitest pins, with the live crash signal in the running app recorded as needs-GUI; `DATA-061` on live `curl` of a nonexistent ticker (404, no library text) and a network-down run (503 on `/history`); `UI-053` on live `GET /macro/IFS%2FA.US.NGDP_R_K_IX?provider=imf`; `DATA-051` on live `/resolve?q=SMR` (`board: "SME"`, `face_value`); `RESEARCH-027` on one live NORMAL run's step `latency_ms` and wall time; `CODE-AGENT-008` on one live FAST research through `invoke_agent` whose published brief carries its web sources.

---

## 4. Deferred to batch 9 (with reason)

**Highs.**
- **`AGENT-007` + `AGENT-017`.** The eval loop and the default-model swap are proven only on live pass^k across provider lanes; the default lanes are unfunded (DECISIONS_FOR_OPERATOR 2.1) and no Anthropic/Gemini key exists (D35). Operator-attended.

**Classes that collide with a set here.**
- **`RESEARCH-028` + `LIFECYCLE-018` (SearXNG honesty; hot-path docker derivation).** They share `searxng_manager.py`/`web_search.py`; `LIFECYCLE-018`'s root fix is one line in the `app.py` lifespan (W3 owns `app.py` for the C5 mapper) and `RESEARCH-028` renders the new `degraded` state in the `SettingsPanel.tsx` SearXNG section that W1 reworks for `RESEARCH-032`. Batch 9: one writer, on top of W1's `sidecarRequest` and refetch.
- **`AGENT-049` (native-search metering).** Needs a per-round search count on the LLM wire models (`models/llm.py`, W2's for C4) and the loop counter in `agent_runtime.py` (W5's).
- **Fundamentals-profile set: `DATA-048`, `DATA-054`, `DATA-055`, `LEAD-016`, with `DATA-052`.** All render in `EquityOverviewPanel.tsx` (W2, `AGENT-081`) and change `yfinance_provider.py`/`routers/fundamentals.py` (W3, `DATA-061`/`LEAD-005`) and `types/data.ts`. Batch 9: one data writer (basis, periods, listing date, ROCE, sector from the exchange map).
- **Keybinding class: `UI-016`, `CODE-FRONTEND-016`, `UI-027`, `UI-086`.** `ChatSidebar.tsx` (W2) and `SettingsPanel.tsx` (W1).
- **`AGENT-053` (context-bus coverage).** `NewsFeedPanel.tsx`/`EarningsCalendarPanel.tsx`/`SecFilingsPanel.tsx` (W3) and `EquityOverviewPanel.tsx` (W2).
- **`LIFECYCLE-021` (label-mate of LIFECYCLE-022).** Its chrome notice lives in `StatusChrome.tsx` (W2).
- **`DATA-062`, `DATA-065`, `DATA-066`, `DATA-068`.** `routers/quotes.py`/`history.py`/`earnings.py` (W3).
- **`UI-032`.** `SecFilingsPanel.tsx`/`sec.ts` (W3).
- **`UI-018`.** `AgentBuilderPanel.tsx`/`SettingsPanel.tsx` (W1), `PortfolioPanel.tsx` (W3).
- **`CODE-AGENT-005`.** `routers/llm.py` (W2) and `agent_runtime.py` (W5).
- **`LIFECYCLE-025`.** `catalog.py` (W2) and `agent_runtime.py` (W5).
- **`CROSS-PLATFORM-004`.** `menu-bridge.ts`/`ChatSidebar.tsx` (W2), `lib.rs` (W1).
- **`UI-028` + `UI-051` (quant units and currency; they share `OptionPricerPanel.tsx`).** No collision; left for capacity. Batch 9.

**Needs a decision or a data run first.**
- **`DATA-059` (former-name index; US ISIN/CUSIP).** No free bulk source exists for US ISIN/CUSIP (a licensing question), and a SEC former-name index needs an offline regeneration run over every US CIK; the `private/pvt` suffix half is small but shares the resolver file with W4 at capacity. Batch 9 with a recorded sourcing decision.
- **`CODE-PLATFORM-017` (+ `CODE-PLATFORM-066`, low).** A Tier-3 grammar decision (`^`, rounding, ternary) for the one server evaluator; batch 9.
- **`LEAD-018` (nemotron reasoning leak).** The evidence has no captured response and the OpenAI adapter already routes `reasoning`/`reasoning_content` to thinking events; batch 9 needs a live capture first.

Every other open high/medium stays in the queue for batch 9 unchanged (none was adjudicated here).

## 5. proposed_not_defect

None. Every selected entry reproduces at base.

## 6. Tier-3 decisions (the integrator records them; none is Tier-4)

- **D-B8-1.** Boot: MCP ports are picked and their env vars set before the main sidecar spawns; the MCP bind waits run on background threads and `setup()` returns at once; a not-yet-bound MCP reads as a failed call (down until the next success). No port file. (LIFECYCLE-001)
- **D-B8-2.** The sidecar status is a typed Rust state `{port, state, reason}` behind the unchanged `get_sidecar_port` command; a terminated child emits `vysted://sidecar-terminated`; no auto-respawn this batch. (LIFECYCLE-010, UI-014)
- **D-B8-3.** The error layer writes `sidecarStatus` (a connection failure → `error`, any success → `connected`); a 20 s `/health` re-probe runs only while `error`. `SidecarError(0)` means the engine is unreachable. (LIFECYCLE-011, UI-014)
- **D-B8-4.** One client verb `sidecarRequest`; `sidecarGet` and the SSE non-2xx path use the same detail extraction. Migrated now: delegate runs, the agent builder, Settings' SearXNG/hardware sections; the remaining hand-rolled sites migrate as they are touched. (CODE-PLATFORM-011, UI-012, RESEARCH-032)
- **D-B8-5.** Provider validation answers `{ok, reason, detail}` (`invalid | not_configured | unreachable | model_not_pulled`) through one frontend helper with a 15 s timeout; onboarding opens only for `not_configured`/`model_not_pulled`; keys are trimmed at both entry points and stripped at the route; a newly keyed provider is promoted when the default is keyless and not ready; the banner asks "is a model reachable", with dismissal persisted. (UI-013, AGENT-028, UI-057, UI-049, UI-019)
- **D-B8-6.** `model_registry.json` is the one source: the TS model tables import it; the llm base URLs and the agent schema's provider enum derive from it. (CODE-AGENT-006, CODE-AGENT-007, CODE-AGENT-016)
- **D-B8-7.** Layout: one plan per template id (the agent tool's meaning); the menu modes have their own role ids with the Rust payload fossils mapped once; `config/layout_templates.json` feeds both the TS planner and the catalog description; the agent's default/unknown arrange is a layout-only reset (drawings and modules kept); the factory reset stays for Settings/menu. (AGENT-055, AGENT-056)
- **D-B8-8.** `open_company_overview` highlight: the panel spotlights a known metric; the result names the metric only when the panel has it. (AGENT-081)
- **D-B8-9.** Every dockview panel renders inside an error boundary; uncaught React errors reach the diagnostics log through a `diag_log_line` command. (LIFECYCLE-023)
- **D-B8-10.** `ProviderError.kind ∈ {rate_limited, not_found, network, None}`; one mapper → 429/404/503/502 with `{detail: <human sentence>, code, action}`; route re-map blocks deleted; yfinance classifies missing tickers and transport failures; a network failure is never downgraded to an empty series. (DATA-061, AGENT-061)
- **D-B8-11.** The SSE routers' last-resort guard is `code: "internal"`; `humanize`'s exception heuristics read class names only. (AGENT-030)
- **D-B8-12.** Path parameters that carry identifiers are `:path`; a slash pair is crypto (one `assetClassOf` helper); crypto rows open the chart; crypto costs format in the quote currency. (UI-053, DATA-081)
- **D-B8-13.** A yfinance quote is dated by `regularMarketTime` from the same fetch, else its last bar; never now(). (LEAD-005)
- **D-B8-14.** The cold-boot retry hook retries only transient failures; user-driven loads are explicit single requests; store actions keep the original error. (UI-015, UI-030, UI-029)
- **D-B8-15.** Resolver: one `instrument_payload`; autocomplete passes rename + enrichment; identity carries `board`/`exchange_group`/`face_value` from regenerated masters; the last candidate slot is reserved for a better cross-region fuzzy match (D58c ordering kept); the pure name scan is memoized and cleared on master refresh. (CODE-DATA-003, UI-039, DATA-051, DATA-058, CODE-DATA-002)
- **D-B8-16.** A failed upstream fetch is never recorded as a legitimate state: the rename lane retries with backoff and reports `rename_lane: unavailable`; a bhavcopy primary 404 tries the fallback and only a calendar holiday is cached as one. (LIFECYCLE-019, LIFECYCLE-022)
- **D-B8-17.** The sidecar positions ledger is GET-only (the legacy import). (CODE-PLATFORM-021)
- **D-B8-18.** Macro adapters: a real `0.0` is data; World Bank titles come from `info.items`; a failed search raises and is not cached. (DATA-084, DATA-085, DATA-086)
- **D-B8-19.** The research tool returns the brief it publishes; the runtime publishes it verbatim. FAST runs the web round alongside the structured fan-out, each witness leg is timed and time-boxed. (CODE-AGENT-008, RESEARCH-027)
- **D-B8-20.** The single-pass deep fallback is deleted; an unexpected iter/heavy exception is an honest failure result. (CODE-RESEARCH-003)
- **D-B8-21.** The runtime mints every tool-call id. (AGENT-046)
- **D-B8-22.** Gemini usage counts thinking and tool-use-prompt tokens; an OpenRouter `:free` model prices at 0. (CODE-AGENT-004, LEAD-019)
- **D-B8-23.** Agent roster load failures surface on `/health` as `agents_degraded` and fail the smoke test. (LIFECYCLE-014)

## 7. Writer ground rules

1. **Worktree.** Your own isolated worktree and branch `worktree-agent-batch-8-<Wn>-<name>` (e.g. `worktree-agent-batch-8-W3-data-error-honesty`). First `git reset --hard b47ed2ddc0f3429d7966583cabba9daa279c07db` and confirm with `git log -1`. Never the main worktree. Push after each concrete deliverable. If your branch already exists from an earlier attempt (a restart), read its log and continue from it.
2. **Stall rule.** No tool call longer than ~120 s: long pytest/vitest/ruff-over-everything/cargo/builds/sidecar boots run detached and are polled in separate short calls. Run your own test files in the foreground only when they finish well inside the limit.
3. **Commits.** One focused commit per entry or root-cause group, conventional, no emojis, ending with the session's attribution trailer.
4. **Tests.** Only where the repo keeps them (`sidecar/tests`, `src/**/*.test.ts(x)`, `src-tauri` `#[cfg(test)]`), one focused test per pinned behaviour; where a class is involved, pin the case the fix was not written against (named above). Never delete, skip or weaken a test to get green; a test that encodes the defect is fixed with the reason in the commit; a test whose subject this plan deletes (W4's write routes, W5's `run_deep_research`) is retargeted where the behaviour survives and otherwise removed with the reason named in the commit. Never special-case code to satisfy a test. Scratch scripts never become tests. Live captures become add-only fixtures, never live calls in a test.
5. **Checks before committing.** Export the PATH line from §3. Python: `ruff format <files> && ruff format --check sidecar && ruff check sidecar`. TypeScript: `pnpm format:check`, `pnpm typecheck`, `pnpm lint` and your vitest files. Rust (W1): `cargo fmt --check`, clippy `-D warnings`, `cargo test` (detached).
6. **Scope.** Touch only your §1 files and honour C1–C9 exactly (names, signatures, wire keys). A needed change elsewhere goes into `issues[]` with the exact line. No refactoring beyond the entry, no flags or defensive code for cases that cannot happen; pre-existing oddities outside the entry go to `issues[]`.
7. **Hard limits.** Never re-add trading. Never touch `CLAUDE.md`, `src-tauri/tauri.conf.json`, `.github/`, `LICENSE*`, `types/plugin.ts`, `r15-fanout.js`, `docs/` or the register. Read no `R15_BRIEF*.md` and nothing under `r15/local/`. No GUI. Never print, log or commit a secret (W2's keys in validation requests and tests use fake values only).
