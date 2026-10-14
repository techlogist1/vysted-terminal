# rc1 gate round 5 — adversarial sample verifier, shard 3 (rc1-vshard-3, Opus)

Candidate: `633f844071d972b337f4c3526d86555c80df0568` (worktree `scratchpad/rc1-round-5-9bc600e-fix-int`, HEAD checked, read-only; no edits/installs/builds in it).
Own sidecar :52603 from worktree source (data dir `scratchpad/rc1-round-5-data-rc1-vshard-3`, MCP ports 52153/52154 read-only), stopped at end.
Frontend: scratch vitest copy `scratchpad/vs3-vitest` (src/types/plugins/styles/configs/sidecar/config rsynced from the worktree, node_modules symlinked). Candidate pinned vitest there: 20 files / 408 tests green (`shard-3-raw/frontend-pinned-vitest.txt`).
Python fresh cases: scratch scripts outside the worktree, run with cwd `worktree/sidecar`, `PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 .venv/bin/python`.
Raw evidence: `verifier/shard-3-raw/`. Ollama lock taken once (LIFECYCLE-013), one call per hold, trap-released. No OpenAI-direct spend.

## Tally

22 hold, 2 refuted (claim-level, not certified): R15-DATA-060, R15-AGENT-044. 0 inconclusive. 5 adjacent new defects (1 medium, 4 low).

## Verdicts

| id | verdict | own repro | fresh variant | evidence |
|---|---|---|---|---|
| R15-DATA-060 | **refuted (claim-level)** | SIFY shareholding/announcements/results 200; shareholding `coverage: covered`, `provider: sec-20f` (83.78% family) | IBN and HDB (US ADRs, each with a current 20-F carrying a 5%+ holders table: IBN 0000950103-26-010820 "MAJOR SHAREHOLDERS" SBI MF 6.3 / Deutsche Bank depositary 16.0, pct-then-shares order; HDB 0001193125-26-322004 "PRINCIPAL SHAREHOLDERS") → parse returns `[]`, route answers bare `not_applicable` "Indian exchange disclosures do not apply", no 20-F note. WIT works. | DATA-060-repro.txt, DATA-060-fresh.txt, DATA-060-fresh-20f-parse.txt |
| R15-DATA-076 | holds | TCS/ICICIBANK/SBIN/DALBHARAT `get_quarterly_yoy` source=nse (exchange-filed) | TCS revenue +13.93% = screener.in (72,275 vs 63,437); ICICIBANK filed 6.9% vs Yahoo 11.4% → independent witness | DATA-076-growth.txt |
| R15-LEAD-015 | holds | DHANBANK quarterly gaps ['2025-09-30']; annual labels ISO | synthetic two consecutive missing quarters + missing annual year both marked | LEAD-015.txt |
| R15-LIFECYCLE-013 | holds | ollama llama3.1:8b run breached at 7600 tokens; resume stays ollama/llama3.1:8b (`/api/ps` [llama3.1:8b]), 15208 over 2 steps | keyless openai run resumes on openai | LIFECYCLE-013-ollama.txt, LIFECYCLE-013-keyless.txt |
| R15-UI-040 | holds | pinned tests green | paused run adopted then polled to done; network-throw cancel leaves run running | UI-040-fresh-vitest.txt |
| R15-AGENT-034 | holds | `{}` / all-null snake_case budget floored to 120000 / $1 / 600 s / 12 | 0 and negative → 422 for camelCase and snake_case | AGENT-034.txt |
| R15-UI-023 | holds | pinned green | indicator failure on timeframe change; overlays cleared during slow load; SAR vs new symbol's closes | UI-023-fresh-vitest.txt |
| R15-UI-026 | holds | pinned green | added row survives in-flight poll; INF→INFY on Enter; backoff reset | UI-026-fresh-vitest.txt, UI-026-autocomplete.txt |
| R15-UI-031 | holds | pinned green | three loads settle in reverse: superseded rejection hidden, agent context newest. (No AbortController — fix_shape parenthetical only; superseded results are dropped by token.) | UI-031-fresh-vitest.txt |
| R15-RESEARCH-024 | holds | live DDG rows carry bare host | SearXNG-shaped payload carries date + host through `_record_web`/`to_dict` | RESEARCH-024.txt |
| R15-RESEARCH-026 | holds | pinned green | EUR/JPY = `formatCompactMoney`; unknown currency → "currency unknown" on revenue and dividend | RESEARCH-026-fresh-vitest.txt |
| R15-RESEARCH-033 | holds | pinned green | 2 of 3 explorers crash (TimeoutError, KeyError) → 2 error steps + 2 warning logs | RESEARCH-033.txt |
| R15-AGENT-041 | holds | pinned green | `write_note` replace undone to original; `portfolio_update_position` undone to prior lot | AGENT-041-fresh-vitest.txt |
| R15-AGENT-043 | holds | pinned green | "Wrote 2 of 4 screener criteria; dropped revenue_growth: value must be a number; roe: unknown operator \"approx\"" + ack `dropped` | AGENT-043-fresh-vitest.txt |
| R15-AGENT-044 | **refuted (claim-level)** | blank-row harm fixed: `/resolve?q=MAZAGONDOCK` → resolved None, 0 candidates → add fails "did not resolve to a listing" | register fix_shape/test: "on no confident match return a failed ack with the suggestion. Test: MAZAGONDOCK resolves to MAZDOCK or fails with a suggestion." The entry's own symbol fails with **no** suggestion (zero candidates) although "Mazagon Dock" resolves to MAZDOCK at 0.92; the pinned test (host-actions.test.ts:201-223) enshrines the no-suggestion path. HINDAERONAUTICS→HAL, ZOMATOLTD→ETERNAL do suggest; RELIANCEIND suggests NV20BEES/RPOWER, not RELIANCE. | AGENT-044-resolve.txt |
| R15-LIFECYCLE-023 | holds | pinned: throwing panel → crash card, sibling renders, Reload remounts | throw after a click (state-driven), throw in `useEffect`, persistent throw on Reload re-shows the card; sibling intact; clicky panel recovers. Wired: `PanelHost.tsx:216` `withPanelErrorBoundaries`, `main.tsx` `onCaughtError`/`onUncaughtError` → `diag_log_line` (`lib.rs:380`, registered :512) | LIFECYCLE-023-fresh-vitest.txt |
| R15-RESEARCH-032 | holds | pinned: status 500 shows reason; visibilitychange re-reads | 60 s slow poll alone (no focus/visibility) moves Ready→Error with "container exited (137)"; refused fetch → "SearXNG status unavailable: The data engine is not responding…"; recovery clears the error. Live `/search/searxng/status` re-derives (`degraded`, engines blocked) | RESEARCH-032-fresh-vitest.txt, RESEARCH-032-live.txt |
| R15-UI-012 | holds | live bodies: invoke 422 array, 404 `{"detail":"unknown agent: 'nope'"}` | live `/llm/chat` 3-field 422 → "provider: Field required; model: Field required; messages: Field required"; non-JSON 500 → "sidecar returned 500"; mid-stream death → unreachable sentence | UI-012-live.txt, UI-012-fresh-vitest.txt |
| R15-UI-019 | holds | pinned green (ready local model → no banner; dismissal survives remount with stubbed refreshBanner) | dismissal survives a relaunch through the REAL keychain-backed `refreshBanner` (store reset to initial state); never-dismissed control shows the banner | UI-019-fresh-vitest.txt |
| R15-UI-049 | holds | pinned green | dead ollama + anthropic key → anthropic; ready ollama kept; user picks deepseek during the probe → not overwritten; second key after promotion → keyed default unchanged. Default persists via workspace blob (`workspace.ts:348-356`); `/key` uses the same KeyEntryDialog | UI-049-fresh-vitest.txt |
| R15-UI-057 | holds | bogus key with trailing space → "rejected this key" | tab+newline, 5 providers (openai, anthropic, groq, deepseek, gemini) → "rejected this key"; KeyEntryDialog trims | UI-057.txt |
| R15-UI-029 | holds | pinned green | catalog SidecarError(0) → "Could not load featured series." + Retry, no skeleton; Retry succeeds → featured rows | UI-030-UI-029-fresh-vitest.txt |
| R15-UI-030 | holds | pinned green | keyless FRED 502 mount default = one request (no retry over 60 s); rapid tabs imf→world-bank→fred = exactly one request each with that tab's id; live: every tab default is its catalog head and loads (ECB/IMF/WB 200, FRED keyless 502 with key sentence) | UI-030-UI-029-fresh-vitest.txt, UI-030-live.txt |
| R15-AGENT-030 | holds | `error_frame(RuntimeError('runs_store: database connection is closed'))` → code `internal`, "The terminal hit an internal error.", detail "RuntimeError: …"; used by both router guards (`agents.py:110`, llm router) | `humanize(None, …)` on RuntimeError/OperationalError('database is locked')/KeyError/ValueError/TypeError → `unknown` (no network/parse misclass by substring); ConnectionError class → network | AGENT-030.txt |

Commands: every row above ran at checkout `633f844071d972b337f4c3526d86555c80df0568`; exact commands are at the head of each raw file (vitest rows: `scratchpad/vs3run.sh <ENTRY> <test>` → `vitest run --reporter=verbose <test>` in the scratch copy; live rows: `curl http://127.0.0.1:52603/...`; python rows: in-process against worktree sidecar source).

## Adjacent (new defects, not the certified entries)

1. **medium — near R15-UI-029.** `store/macro.ts` `search` still swallows every error into `[]` (catch at ~:120), so a failed search renders "No matching series — No results for \"unemployment\" on fred." Live: keyless `/macro/search?q=unemployment&provider=fred` → 502 with the FRED-key sentence; FRED is the default tab, so every fresh-install search on it claims a false empty. Evidence: UI-030-UI-029-fresh-vitest.txt (adjacent case), UI-030-live.txt.
2. **low — near R15-AGENT-030.** `services/llm/ollama.py:206-210, 279-283` defensive `except Exception` → `humanize("ollama", exc)`: an internal error inside the adapter reads "Something went wrong with Ollama." (code unknown) — blames the provider. Evidence: AGENT-030.txt.
3. **low — near R15-RESEARCH-032.** `lib/hardware-fit.ts:63-74` `fetchLocalModelRecommendation` uses a raw `fetch` and collapses every failure (incl. a 500 with a reason) to `null`; onboarding (`OnboardingFlow.tsx:646`) then says "Couldn't reach the local engine to check your hardware."
4. **low — near R15-RESEARCH-024.** `services/research/perplexity.py:180` and `sonar.py:201` `ResearchSource(...)` never set `published_at` although Perplexity `search_results` carry a date.
5. **low — near R15-AGENT-044.** `/resolve?q=RELIANCEIND` suggests NV20BEES / RPOWER / RS / QTZM, not RELIANCE — a failed add's candidates can mislead. Evidence: AGENT-044-resolve.txt.
