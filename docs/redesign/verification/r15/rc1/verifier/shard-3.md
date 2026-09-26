# RC1 gate round 2: adversarial sample verifier, shard 3

- Candidate: `81fbfe910d472ecd154fa62e42d86bce213a697e` (`git rev-parse HEAD` in `scratchpad/rc1-4c6dfe8-fix-int`, which stayed read-only).
- Own sidecar: source run on :52603 with data dir `scratchpad/rc1-data-rc1-vshard-3`, a fresh `cp -R` of rc1-seed-data. Sleep pid 90202, worker 90203. `/health` was ok.
- Frontend checks ran in a `git archive` copy of the candidate at `scratchpad/vshard3r2/cand`, with node_modules symlinked and no `.vite`, so nothing was written into the candidate.
- Local model: two Delegate runs on llama3.1:8b, each under `/tmp/vysted-r15-ollama.lock`. No paid spend.
- Inputs used: the register entries at the candidate sha, the running sidecar, screener.in and the code. I did not read any rc1 evidence or VERDICTS.

## Register status of the 24 picks (at the candidate sha)

| Status | Ids |
|---|---|
| fixed (certify) | UI-046, UI-048, DATA-076, DATA-078, AGENT-074, LIFECYCLE-023, DATA-092, DATA-094, DATA-096 |
| not_a_defect | DATA-080 |
| blocked_tier4 | UI-044 |
| needs_gui | UI-084 |
| open (low) | AGENT-070, AGENT-072, UI-066, UI-068, UI-070, CODE-PLATFORM-042, UI-082, CODE-PLATFORM-044, CODE-PLATFORM-046 |
| not in register | RESEARCH-058, RESEARCH-060, RESEARCH-062 (the register's RESEARCH ids stop at 042) |

The sample list calls these entries certified, but only nine of them are status `fixed`. The other ids have no fixed claim that could be refuted. For each of them I checked that its register status is still accurate at the candidate, and I recorded the verdict as `inconclusive (not certified)`.

## Certified entries

**R15-UI-046: holds.**
- Code: `listWorkspaces()` filters out `isReservedLayoutName` (`src/lib/workspace.ts:738-739`). `saveWorkspace` and `deleteWorkspace` go through `userWorkspaceName`, which throws `Names starting with "__" are reserved`. SettingsPanel and WorkspaceDialog are the only callers of `listWorkspaces`.
- Live: `GET :52603/workspace` returns `["__autosave__"]` on the sidecar, and that slot is hidden in the UI.
- `workspace.test.ts` passes.
- Adjacent (fresh surface): the MCP `list_workspaces` and `get_workspace` tools 404 on every call. See finding 1.

**R15-UI-048: holds.**
- The settings bundle carries `chartDefaults` (symbol, timeframe, indicators). It is persisted through the workspace `settings` slice via `toBundle`/`setAll`, and `parseChartDefaults` guards older blobs.
- `ChartPanel` reads it at mount (`ChartPanel.tsx:277-294`). The Star "Make default" button writes it.
- `settings.test.ts` and `ChartPanel.test.tsx` pass (191/191 across the 8 files I ran).

**R15-DATA-076: holds.**
- `get_quarterly_yoy` prefers exchange-filed periods (`source` nse/bse) and uses Yahoo only as a labelled fallback.
- Fresh cases, run in-process with the worktree venv and my own data dir:
  - `TITAN.NS` gives revenue_growth 0.29250, earnings_growth 0.62878, source `nse`, periods 2026-06-30 vs 2025-06-30.
  - `TATACONSUM.NS` gives source `nse`.
  - `DAL.BO` gives 0.452, source `bse`.
- Outside witness: screener.in TITAN consolidated shows Sales 21,356 (Jun 2026) against 16,523 (Jun 2025), which is 0.2925. Net profit is 1,777 against 1,091, which is 0.6288. Both match exactly.

**R15-DATA-078: holds.**
- `docs/BLUEPRINT.md:266` now reads "yfinance fallback (no API key needed…; R15-DATA-078 — alpha_vantage was never built and is dropped…)".
- A grep across docs and code (excluding verification, archive and CHANGELOG) finds no remaining alpha_vantage promise.
- `src/lib/format.ts:267-268` only maps a provider label.

**R15-AGENT-074: holds.**
- Code: `_on_round_usage(usage, used_model, used_provider)` prices at the resolved provider (`run_manager.py:217-222`), and the runtime passes `run.provider_id` (`agent_runtime.py:2900`).
- Entry repro: `POST :52603/agents/copilot/runs {"prompt":"What is the latest price of MSFT?","model":"llama3.1:8b","budget":{"maxSteps":1}}` with no provider. Result: `provider: null`, tokens 7594, `spend_usd 0.0`, status `error` with "step ceiling 1 reached". Before the fix this would have been $0.038 at $5/M.
- Fresh case (resume, which always passes provider=None): `POST /runs/8ba2ebf3…/resume` gives tokens 15196, `spend_usd 0.0`. Before the fix it would have been $0.076.

**R15-LIFECYCLE-023: holds for its claim and fix_shape.**
- Every dockview panel is wrapped in `PanelErrorBoundary` through `withPanelErrorBoundaries(collectPanelComponents(modules))` (`PanelHost.tsx:216`). It shows "This panel crashed.", Reload panel and Copy error.
- `createRoot` passes `onCaughtError`/`onUncaughtError`, which go to `diag_log_line` (`main.tsx`). `PanelHost.test.tsx` passes.
- Adjacent (fresh case): the agent dock is not a dockview panel and has no boundary. A render throw in ChatSidebar still blanks the whole cockpit. See finding 2.

**R15-DATA-092: holds.**
- The Region section hint reads: "Number formatting, plus which market's symbol resolver, trading calendar, macro/news providers and screener universe the sidecar uses."
- The row reads `Defaults to ${regionConfig(DEFAULT_REGION).label}` (India), and `regionConfig` falls back to DEFAULT_REGION.
- Checked against the sidecar: `get_region()` feeds `resolve.py`, `fundamentals.py:103`, `provider_registry.py:326` (routing), `news_provider.py:413`, `screener.py:120` and `macro_router`.
- Freshness is per instrument (R15-UI-090). Region still decides which listing a bare symbol routes to, and therefore which calendar applies, so the copy is not factually wrong.
- `grep "United States|only affects number"` finds no stale copy.

**R15-DATA-094: holds.**
- `GET :52603/news/sources/status` with `X-Vysted-Newsapi-Key: R15CANARY-newsapi-fake` returns `{"newsapi":"unauthorized"}`.
- Fresh key `0123456789abcdef0123456789abcdef` also returns `unauthorized`. With no key it returns `absent`.
- `/news` carries `x-news-sources: rss=ok;newsapi=unauthorized`.
- Marketplace `configure()` calls `probeNewsApiKeyOrThrow` before it saves (`marketplace.ts:39-55, :207-208`). NewsFeedPanel probes on mount/refresh and badges `unauthorized`/`error` (`NewsFeedPanel.tsx:248-275`).
- `marketplace.test.ts` passes.

**R15-DATA-096: holds.**
- `/income`, `/balance`, `/cashflow` and `/ratings` go through `_cached` at a 6h TTL, keyed per listing and per period.
- Live: the first `/fundamentals/MSFT/income` took 0.52 s and the second 0.00 s, and a `fundamentals:MSFT:income:annual` row is in data_cache.
- `data_cache.set` evicts rows beyond `MAX_ROWS` (20,000), oldest first, and SQLite runs through `asyncio.to_thread`.
- Fresh in-process check on a temp db with MAX_ROWS=3 and 6 sets: size 3, X0 evicted, X5 kept.

## Not certified (no fixed claim)

- **DATA-080 (not_a_defect): holds.** A grep for segment, revenue mix/split and operational metric in `specs/001-agent-native-redesign/spec.md`, `docs/BLUEPRINT.md` and the constitution returns 0 hits.
- **UI-044 (blocked_tier4): status accurate.** The `DisclaimerFlow.tsx:45-50` hydrate IIFE still has no catch, and `refreshFirstLaunchAck` (`store/safety.ts:39-42`) does not catch either.
- **UI-084 (needs_gui): GUI skipped per the lead note.** `agent-dock.test.ts` passes.
- **Open lows: all still reproduce by code, so their status is accurate.**
  - AGENT-070: the name check `event.name == "research"` is still there.
  - AGENT-072: buffett.json still declares 3 tools.
  - UI-066: no error variant.
  - UI-068: no loading slot or keyboard sort.
  - UI-070: no export/import.
  - CP-042: greeks still builds its own engine.
  - CP-044: `async def stream_chat` is still abstract.
  - CP-046: `moduleForPlugin` calls getters with no try.
  - UI-082: only the residual remains (a 260-char name returns a clear 400; there is no input maxLength).
- **RESEARCH-058/060/062: these ids do not exist in the register.**

## Adjacent findings

1. **Medium: MCP `list_workspaces`/`get_workspace` are dead.** `sidecar/services/mcp_server.py:255, :263` call `/workspaces` and `/workspaces/{id}`, but `routers/workspace.py:21` mounts `prefix="/workspace"`. Live fastmcp call: `ToolError: Client error '404 Not Found' for url 'http://sidecar/workspaces'`. `test_mcp_server.py` only asserts the tool names.
2. **Medium: the chat dock has no error boundary.** Proof by a scratch vitest (kept at `scratchpad/vshard3r2/chatthrow-proof.tsx.txt`, never committed): with ChatSidebar throwing, `host.innerHTML` becomes `""` and the boundary-guarded "portfolio panel" sibling is gone. The cause is that `page.tsx:273-275` has AgentDock wrapping PanelHost and `AgentDock.tsx:117` renders `<ChatSidebar />` unguarded.

Findings file: `findings/rc1-vshard-3.json`.
