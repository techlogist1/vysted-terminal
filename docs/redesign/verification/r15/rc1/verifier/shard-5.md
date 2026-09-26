# RC1 verifier — shard 5 (rc1-vshard-5)

Checkout sha: `81fbfe910d472ecd154fa62e42d86bce213a697e` (read-only candidate worktree). Own sidecar on :52605 (data dir copied from rc1-seed-data); agent runs on shared :52152 (rc1-cand 4c6dfe8c; `git diff 4c6dfe8c..81fbfe91` touches only citecheck.py / research iter.py / brief-ingest.ts + tests, so adapters and host actions are byte-identical). Frontend checks ran in a scratch `git archive HEAD` extract with linked node_modules; the candidate stayed clean (`git status --short` empty). Working log: `logs/rc1-vshard-5.md`. Findings: `findings/rc1-vshard-5.json`.

Result: 18 holds, 6 refuted (all not_certified: literal repro holds, a fresh case leaves part of the title/fix_shape unfixed), 0 inconclusive. GUI-only legs were skipped per lead note.

| Entry | Verdict | Command / evidence |
|---|---|---|
| LIFECYCLE-015 | holds | `GET /backtest/runs` newest-first after 6 runs + GET of oldest; fresh process `_backtest_summary` on oldest run ok; 34 in-process puts then summary of first ok |
| AGENT-083 | holds | live MCP client lists 40 tools, 0 of 19 host-action ids, calling one -> `Unknown tool`; spec/MCP docs amended; parity test exists |
| AGENT-084 | holds | HAND_ACTION_INVENTORY + two-way test; llama3.1:8b (lock-held) reached `add_chart_drawing` (rejected for model's own bad args) |
| LEAD-018 | holds | nemotron-3-super on :52152, plain + 4-tool turn: reasoning in thinking events only |
| CODE-PLATFORM-021 | holds | `POST /portfolio/positions` -> 405; router GET-only; pinned in test_no_trading_surface.py |
| UI-010 | holds | 3 literal + 7 fresh bad params -> readable 422; clamp-on-blur + test |
| DATA-055 | **refuted (not_certified)** | `curl -s http://127.0.0.1:52605/fundamentals/SMR` -> `listing_date: null`, `fifty_two_week_change: -0.068` for SMR.BO (first trade 2026-06-08, the entry's own DAT-S2-8 case). `yfinance_provider.py:849` sets listing_date only for `.NS`; `EquityOverviewPanel.tsx:226 listedUnderAYear` keys on it -> "52w" label + 1Y-change row on a 16-week listing. DHOOTTRANS holds. |
| DATA-061 | **refuted (not_certified)** | `curl -s 'http://127.0.0.1:52605/history/QQZZFAKE.NS?timeframe=5m'` (and `.BO`) -> `reason: "in_eod_only"` although `is_nse_symbol`/`is_bse_symbol` are False (`history.py:67-75` treats any suffix as known_in) — the title's "unknown symbol gets 'India is EOD only'" leg. Also `/history/XYZ%2FABC` -> 502 provider_error for an upstream HTTP 404. Literal ZZZZNOTREAL/worldbank cases hold. |
| DATA-068 | holds | `as_of` on ratings/earnings/price-target routes, stable across calls; client 15-min TTL + chip |
| DOCS-017 | holds | loader counts nse-all 3506, bse-all 5042, india-all 5891, sp500 503, nifty50 50 = CURRENT_STATE §3.3 |
| DOCS-018 | **refuted (not_certified)** | `docs/CURRENT_STATE.md:337-340` "(fundamentals and any other region still hit it [yfinance] first)" vs `provider_registry.py:140-158` openbb-mcp rank 10 < yfinance 50 for fundamentals/statements/analyst; live `/health` -> fundamentals `openbb-mcp (yfinance fallback)` |
| DATA-071 | holds | empty bhavcopy cache, 1y on SHRICON/COLINZ/JONJUA.BO -> 8/16/24 bars, `partial: true`, coverage_start set |
| RESEARCH-028 | holds | SearXNG `degraded` with engine reasons; web_search -> keyless-fallback `searxng_degraded`; fresh degraded + throttled research -> `web_reason rate_limited` banner, no false set-up nudge |
| CROSS-PLATFORM-003 | holds | mac fallback `estimated: true`; stubbed kernel32 32/4 GiB -> exact, `estimated: false` |
| LEAD-013 | holds | sp500.json 503 @2026-09-24; none of 14 delisted; BXP/NVR/UDR present; test_sp500_universe.py 4 passed incl. staleness TTL; fresh diff vs live Wikipedia constituents (503) -> 0/0 |
| UI-024 | holds | TaskList/TaskItem + toolbar/slash; WikiLinkNode atom; fresh jsdom markdown round-trip of a task list |
| LEAD-026 | **refuted (not_certified)** | `curl -s http://127.0.0.1:52605/history/QQZZFAKE.NS` (and `.BO`) at 1d -> `reason: null`; `_is_unknown_symbol` (`history.py:40-47`) exempts any suffixed symbol. Bare `/history/ZZZZNOTREAL` -> `unknown_symbol` holds. |
| CODE-RESEARCH-004 | holds | 0 non-test hits for the 6 deleted names; fresh orphan scan -> 0 |
| DATA-004 | holds | DHANBANK insiders flagged vs NSE promoter 0.00%; fresh DHOOTTRANS / SMR / JUMBO flagged, TCS ok |
| DATA-005 | holds | JUMBO/JNPR/VERTEX/ONC BVPS+P/B flagged; fresh DHOOTTRANS/SMR flagged |
| DOCS-004 | holds | PDD banner dead/binding sections + VYSTED_DESIGN pointer; peach `#fab283` = tokens.css:54; citation guard test |
| AGENT-063 | holds | MCP news AAPL 19/19 tagged; BTC/USDT 1 = REST; fresh ETH/USDT 0 (no Ethereum story in feed) |
| CODE-PLATFORM-013 | **refuted (not_certified)** | Literal pins pass (workspace.test 013, SettingsPanel.test 013, plugin-runtime.test 36/36). Fresh: `resetToDefaultLayout()` (`src/store/workspace.ts:184`, from Settings + command palette) runs `setEnabledMap({})`, wiping `plugin:<id>` flags; a plugin disabled in plugins.db comes back. `vitest run src/store/vs5-reset-drift.test.ts` -> `enabled map after reset: {}`, `enabled module ids after reset: ["plugin:vysted-news"]` (AssertionError). Unfixed: fix_shape "one lifecycle owner writes both / derive from runtime state". |
| CODE-PLATFORM-017 | **refuted (not_certified)** | Run path is server-only (holds). Fresh 26-expression parity sweep, server `evaluate_code` vs the inspector's mathjs syntax check + live preview: nested ternary `a > 1 ? 1 : a > 0 ? 2 : 3` editor 2 / server parse error; `round(1.005, 2)` 1.01 / 1.0; `mod`, `5!`, `2 a`, `xor`, `pi`, `true`, `log`, `exp`, `sign` pass the editor with a preview value and fail on run; `a ** 2` editor syntax error / server 9. No shared parity fixture; stale comments remain at `node-registry.ts:183` and `:189-190` ("Evaluation is client-side (sandboxed mathjs)"). |

## Adjacent (new defects, not refutations)

| Near | Severity | Finding |
|---|---|---|
| RESEARCH-028 | high | "KPIT Technologies — latest quarterly results" resolves to BSOFT (Birlasoft, former_name KPIT) at score 1.00, no disambiguation; `/resolve?q=KPIT` -> BSOFT only although KPITTECH exists |
| AGENT-083 | medium | External MCP `save_workflow` overwrites a saved workflow with no confirmation while spec.md:329/:783 call the MCP surface read-only; 8 hand-written tools lack readOnlyHint |
| DATA-068 | low | Earnings drill-down "As of" chip (EarningsCalendarPanel.tsx:447-457) shows client fetchedAt, not server as_of |
| RESEARCH-028 | low | web.detail tells the model to set up SearXNG while it is running (degraded) |
| CODE-RESEARCH-004 | low | test_search_exports.py rglob scans .venv; base.py:109 docstring offers unused preferredDomains |
| DOCS-004 | low | CLAUDE.md still describes a zinc + cool-indigo palette; tokens are pure-neutral + peach (Tier-1 file, report only) |
