# R15 Stage C: Batch 7 Verdicts (fresh-context verifier)

- **Merge target:** `worktree-agent-batch-7-int@b7f7023f7d31d9110ad631d70a2a03dc7e33d02d` (base `1a19d26`).
- **Verifier:** Opus, fresh context. Every verdict below comes from the running sidecar, the vitest-executed
  frontend path, or the outside world (screener.in, NSE/BSE, SEC EDGAR, OpenRouter, a local webhook receiver).
  None comes from reading the diff.
- **Tally:** 52 entries claimed (51 delivered plus CODE-PLATFORM-018 as verify-only). Result: **50 certified, 1 needs GUI (UI-022), 1 not certified (AGENT-045)**, 0 not-a-defect proposals.
  LEAD-005, AGENT-046 and CODE-PLATFORM-021 were not delivered. They stay open and are listed as not certified
  ("not claimed").

## Rig

- Scratch worktree `batch-7-verify` at `origin/worktree-agent-batch-7-int` (detached, `b7f7023`), `sidecar/.venv` and
  `node_modules` symlinked from the integrator's `batch-7-int` worktree (same lockfiles).
- Data dir `batch-7-verify-data`, copied from `vysted-iso/data` (keyless ISO profile, never the operator's live dir).
- Main sidecar from source on `127.0.0.1:52310`, stdin held by a sleep pipe. openbb-mcp on the ISO stack's `:52153`.
  sec-edgar-mcp: the ISO `:52154` binary timed out on every SEC listing, so the sidecar was restarted against a fresh
  `batch-7-int` sec-edgar-mcp build on `:52324`. It timed out the same way, because SEC's `browse-edgar` and
  directory endpoints returned 503 after about 10 s for the whole session. `data.sec.gov` and the Archives documents
  answered 200. See DATA-060.
- Models: local `llama3.1:8b` via Ollama for the delegate-run entries. OpenRouter free slugs only where Ollama cannot
  do the job: the delegate planner skips `ollama` by design (`_PLANNER_PROVIDERS`), so AGENT-039's plan half ran on
  `nvidia/nemotron-3-super-120b-a12b:free`. Two earlier free slugs failed: `llama-3.3-70b:free` was unavailable
  and `qwen3.8-27b:free` / `gemma-4-31b:free` returned "free pool busy". Each launch is logged to the spend ledger
  as `free: true`. OpenAI-direct: not used.
- Scratch vitest files were written into the scratch worktree only (`zz-b7v-*.test.ts(x)`, never committed). They
  drive the real stores and components, and where marked "live" they fetch from `:52310` through a mocked
  `get_sidecar_port`.

## Chain observed at the target

| Gate | Result |
| ---- | ------ |
| `pnpm exec vitest run` (full, at `b7f7023`) | 129 files, 1565 tests passed, EXIT 0 |
| `pnpm typecheck` / `pnpm lint` / `pnpm format:check` (at `b7f7023`) | EXIT 0 / 0 / 0 |
| `pytest` (sidecar, full, at `b7f7023`) | 2826 passed, 1 skipped, EXIT 0 |
| `ruff check` / `ruff format --check` (sidecar) | "All checks passed!" / "412 files already formatted" |
| `pnpm ci-local` (integrator, `02946d6`; `b7f7023` adds only a TS mapping + test and a comment) | `CI_EXIT=0` (`b7int-ci-2.log`: 2826 passed) |
| `node scripts/smoke-test-sidecars.mjs` (integrator, built binaries) | `SMOKE_EXIT=0`, all three sidecars booted and torn down |
| Frozen-binary quant no-orphan (verifier re-run, see CODE-PLATFORM-018) | verifier re-ran the integrator's `b7int-quant-live.py` on the `batch-7-int` binary: EOF exit 0 and SIGTERM exit −15, 4 processes before, **0 left** after both; `/health` worst 0.224 s / 0.014 s during a 20k-step binomial price |

## Per-entry evidence

### W1: India exchange data

- **R15-DATA-014: certified.** `GET /fundamentals/DAL` returns `revenue_ttm` 99,700,000 (9.97 Cr), which equals
  screener.in's "Revenue: 9.97 Cr". The field has provider `bse` and label "standalone, sum of 4 filed quarters to
  2026-06-30", and the reason says "the provider's 27,600,000 disagrees with it — not served". The case the fix was
  not written against is FUSION: 1,714.42 Cr from NSE's filed `RevenueFromOperations`, with Yahoo's 858 Cr
  disclosed. screener.in shows 1,699 Cr, and its per-quarter figures are reclassified (Jun-25: screener 442, filed
  434.43). `net_income_ttm` is 168.51 Cr against screener's 169. JONJUA, a half-yearly SME filer, is flagged
  "annual, not trailing-4Q".
- **R15-DATA-027: certified.** The agent `fundamentals` tool over MCP returns 9.97 Cr for `DAL.BO` with provider
  `bse`. `AAPL` stays `yfinance`, so the lane is not tried outside India. Fresh case TCS: provider `nse`,
  consolidated, a sum of 4 filed quarters, Q1 FY26 revenue 63,437 Cr (TCS's public figure). The first TCS call fell
  back to Yahoo, flagged, because the lane returned `None` on a transient NSE miss. The retry served NSE (see Issues).
- **R15-DATA-076: certified.** DAL `revenue_growth` is 0.452 from `bse`, "period to 2026-06-30 vs the same period
  to 2025-06-30", which matches screener's 7.26 / 5.00 − 1. For FUSION, Yahoo's 128.1% is disclosed as "not served"
  against the filed 5.46%.
- **R15-LEAD-004: certified.** With no lane, TCS's TTM reason reads "the provider's quarterly statements show only 3
  quarter(s) … spans a provider gap", not "half-yearly". JONJUA keeps "half-yearly" from its filed periods. DHANBANK,
  a quarterly filer, sums 4 filed quarters.
- **R15-LEAD-015: certified.** `GET /fundamentals/DHANBANK/income?period=quarterly` returns
  `gaps: ["2025-09-30"]` and a null value on every line for that period. Annual labels are ISO on openbb
  (`2026-03-31 …`) and on yfinance (in-process `get_income_statement('DHANBANK.NS','annual')` →
  `['2026-03-31', …]`).
- **R15-DATA-050: certified.** `/disclosures/results` answers 200 with BSE events for JONJUA (Results 2026-08-12, as
  in the register's BSE truth), DAL and ELCIDIN (the BSE Q1 FY27 filing on 2026-08-13 is present). The fresh case
  CHTR (BSE SME) also answers 200 with 4 events. All four returned 502 before.
- **R15-DATA-060: certified.** SIFY `shareholding`/`announcements`/`results` and AAPL `shareholding` answer 200
  `coverage: "not_applicable"` with a note. The agent tools answer `ok: true` with the same fields. The 20-F lane:
  the sidecar route could not list filings because sec-edgar-mcp `get_recent_filings` timed out on SEC's 503ing
  `browse-edgar`, and the route said so honestly in `note`. Running `attach_major_shareholders` in-process with only
  the listing step replaced by the same filing from `data.sec.gov/submissions` returned `coverage: "covered"`,
  `provider: "sec-20f"` and SIFY's four holders: 67.98 + 7.90 + 7.56 + 0.34 = 83.78%, the register's "83.78% family
  control". The fresh case WIT, parsed from its live 20-F: Azim H. Premji 72.62, Hasham 17.99, Prazim 20.60,
  Zash 21.00, Azim Premji Trust 6.49, which matches Item 7.A exactly.

### W4: research funnel

- **R15-RESEARCH-019: certified.** `run_deep_research` with the real `visit_for_research` against a live 403 host
  emits `ResearchStep(status="error", "visit failed: https://www.investing.com/… (HTTP 403)")`. An SSRF target
  gives "blocked non-public or non-http(s) URL".
- **R15-DATA-075: certified.** A real BSE attachment that answers 404 on `AttachLive` (curl) and 200 on
  `AttachHis`: `fetch_page(<AttachLive url>)` returns `ok` with the PDF text ("Unit No. 101, VIP Plaza …").
- **R15-RESEARCH-033: certified.** In `run_heavy_research` with explorer 2 raising, the step "explorer angle 2 (What
  are TCS margins?) failed: RuntimeError: explorer boom" is emitted and logged, and the brief still returns.
- **R15-RESEARCH-020: certified.** The register repro (SearXNG with a 40-row stub, `numResults: 3`) gives 3 results
  and 3 citations, where it gave 40/8. Live MCP `web_search num_results=3` on the keyless Brave tier gives 3/3.
- **R15-RESEARCH-021: certified.** "BAJFINANCE 200 DMA breakout as stock nears record" scores 1.0, where the register
  had 0.0. "BAJFINANCE 52-week high" also scores 1.0. Fresh: "KPITTECH 200 DMA test" scores 1.0.
- **R15-RESEARCH-022: certified.** The register stub (a DDG challenge row) now raises `SearchError(rate_limited)`
  "DuckDuckGo: blocked (challenge page)", and the breaker records a failure (1). Before, it was a healthy empty
  answer.
- **R15-RESEARCH-023: certified.** The register's Route Mobile "All rights reserved" row is kept (1 row). A challenge
  row is still blocked.
- **R15-RESEARCH-038: certified.** One search that fails both attempts (2 engine calls) leaves the breaker `closed`
  with 1 failure. A second failed search opens it.
- **R15-RESEARCH-024: certified.** A SearXNG row with `publishedDate` passes through `web_search._dispatch` as
  `{domain: "reuters.com", published_at: "2026-07-17T10:05:00"}` and through `_record_web` into a `ResearchSource`
  with `published_at`. Live keyless rows carry a bare host (`sahi.com`, `livemint.com`), never "web". In the
  frontend, `publish_brief` → BriefPanel's Sources rail renders "2026-07-17". That path needs the reviewer's
  `b7f7023` mapping.
- **R15-UI-038: certified.** A legacy Sonar source (`domain: "sec.gov (via Perplexity Sonar)"`) badges as FILING,
  because the URL host now wins. New Sonar rows carry the provenance in `provider`.
- **R15-UI-092: certified.** Markdown citing `[47]` against 2 sources renders one inert chip
  (aria "citation not in sources") and a Sources header reading "1 broken citation".
- **R15-RESEARCH-026: certified.** An INR market cap card renders "₹591B", which is `formatCompactMoney(…, "INR")`,
  Equity Overview's formatter. A null currency renders "4.48T · currency unknown".

### W2: delegate runs

- **R15-CODE-AGENT-010: certified.** On the done run `eb4715cf`, `cancel`, `resume`, `start` and `answer` each return
  409 "run '…' is done; it cannot become …". An unknown run returns 404. The row is unchanged.
- **R15-AGENT-034: certified.** `budget: {}` is stored as 120000 tokens / $1.0 / 600 s / 12 steps.
  `maxSteps: 0` returns 422.
- **R15-AGENT-037: certified.** `maxTokens: 1000` with "Use the price_data tool …" ends after 1 step with no tool
  activity, `error` "token ceiling 1000 reached (7259 used)", and checkpoint `turns: []`.
- **R15-AGENT-038: certified.** A one-shot answer under `maxSteps: 1` ends `done` "completed (step ceiling 1 reached
  (1 taken) on the final round)".
- **R15-AGENT-074: certified.** A launch that omits the provider (copilot's default is Ollama) with `llama3.1:8b`
  prices 7,234 tokens at `spend_usd: 0.0`. Before the fix, the $5/M default would give $0.036.
- **R15-AGENT-036: certified.** Checkpoints are `{prompt, turns}` in order, e.g.
  `[get_terminal_state → {…}]` then `OK`. For the ask_user run, the prompt is followed by `[ask_user → Which ticker
  …]` and then the user turn "MSFT please".
- **R15-AGENT-035, R15-LIFECYCLE-013: certified.** Resuming the breached run `7ca064e4` keeps `provider: ollama`,
  `model: llama3.1:8b` (Ollama `/api/ps` shows llama3.1:8b, not the agent default qwen2.5:7b). Cost accumulates
  from 7,259 to 14,526 tokens and 2 steps. A dummy `X-LLM-Api-Key` sent on answer appears in no log line, no DB
  column and no `GET /runs` body.
- **R15-LIFECYCLE-012: certified.** The run `508692a9` was killed mid-flight (stdin EOF on the sidecar) while its row
  read `running`, 1 step and 7,277 tokens. The checkpoint was already non-null, 539 bytes written at the round,
  not at exit. On restart, `GET /runs/508692a9…` reads `error` "interrupted by sidecar restart". It resumes (200)
  and then cancels (200, `cancelled`).
- **R15-UI-040: certified.** Live scratch vitest: `adoptSidecarRuns()` against `:52310` adopts only the live
  sidecar-only run (`527ee6a4`, running, ollama). `cancelDelegateRun` on a done run returns
  `{ok: false, "Cancel failed (HTTP 409) — retry."}` and the row stays `running`, so the cancel is not optimistic.
- **R15-CODE-AGENT-011: certified.** A delegate run told to ask pauses with `question` "Which ticker would you like
  to get a price for?". `POST /answer` "MSFT please" resumes it: `resolve_symbol` MSFT, then `price_data` MSFT,
  then `done`.
- **R15-AGENT-039: certified.** On nemotron-3-super:free, a compound launch parks `planned` with 5 steps
  ("plan ready: start or discard it"). `POST /runs/{id}/start` with the key header runs it to `done`, and the typed
  activity rows read compare_symbols ok, add_to_watchlist staged, set_chart_symbol staged. The activity half also
  ran live on Ollama (price_data NVDA/AMD, compare_symbols).

### W3: unattended, chart, workspace

- **R15-AGENT-023: certified.** A saved workflow (`data.fetch_quote` AAPL → `action.webhook`) was scheduled
  `interval` every 5 min at 17:37:13. It fired unattended at 17:42:27 and again at 17:47:28, never in between, and
  the local receiver got `{workflow, node, value: <AAPL quote>}` each time. `lastStatus` is "ok". `everyMinutes: 1`
  returns 422. `GET /workflow/webhooks` lists only refs. The URL does not appear in `workflows.db` or the sidecar
  log.
- **R15-CODE-PLATFORM-018: certified.** Frozen `batch-7-int` binary: a 20k-step American binomial prices while
  `/health` stays fast (worst 0.224 s under EOF, 0.014 s under TERM). stdin EOF exits 0 and SIGTERM exits −15, with
  4 processes before and 0 leftover after both. Source sidecar: pool workers 75557/75558 were gone 6 s after stdin
  EOF, and workers 76149/76150 were gone 6 s after SIGTERM. No `multiprocessing` process was left running.
- **R15-UI-020: certified (vitest-executed).** In ChartPanel with a persisted view (TCS.NS 1wk), a RELIANCE drawing
  is not shown, and it appears once RELIANCE.NS loads. The view is written to the store and the workspace blob
  (`chartViews` round-trip test).
- **R15-UI-022: needs GUI.** The click path is pinned in vitest against a mocked chart (anchor from
  `coordinateToPrice`, off-bar logical index, Text prompt, locked delete disabled). The actual placement on the
  lightweight-charts canvas cannot be seen headless. A GUI check (native event injection, not chrome-devtools)
  must confirm four things. (1) A trendline or horizontal line clicked mid-candle, well away from the close,
  renders at the clicked y. (2) A click to the right of the last bar places a visible drawing. (3) The Text tool
  asks for a label and shows the typed text, not "label". (4) A locked drawing's row delete control is disabled
  and the drawing survives a click on it.
- **R15-UI-023: certified (vitest-executed).** A rejected `/indicators` after a symbol change removes every old
  overlay series ("indicators down (502)"). Indicators do not draw before their own symbol's candles land.
- **R15-UI-031: certified (vitest-executed).** In EquityOverview with AAPL then TCS.NS commanded and AAPL settling
  first, AAPL is never shown and the spinner holds until TCS.NS lands.
- **R15-CODE-FRONTEND-017: certified.** The census's original proof P1
  (`census/code/evidence/frontend-stores-proof.test.ts.txt`), replayed at the target, leaves `activeIdentifier`
  as MSFT. It was AAPL. A late AAPL error after MSFT is ready leaves MSFT ready. The earnings 7-day/30-day case is
  pinned.
- **R15-UI-026: certified.** Scratch vitest on the real panel: ZZTEST added during an in-flight poll shows at once,
  and a removed SPY does not reappear when the stale poll lands. Stale-candidate Enter and backoff/hidden pause are
  pinned.
- **R15-CODE-FRONTEND-019: certified.** The live sidecar with its workspaces dir set to `chmod 555` answers 507 "Could
  not write the workspace: Permission denied". Real `autosaveLayout()` against it gives no error after 2 failures,
  "Autosave failed (HTTP 507: Could not write the workspace: Permission denied)." after 3, and `null` after
  recovery.
- **R15-DATA-090: certified.** Truncating `b7v-ws` and then running `GET` serves the `.bak` (v1) and moves the file to
  `.corrupt-1790251709085`. The next save leaves `.bak` parseable. A non-dict body returns 422.
- **R15-UI-046: certified.** The live `listWorkspaces()` returns `["b7v-ws"]` even though the sidecar lists
  `__autosave__`. `saveWorkspace("__x")` and `deleteWorkspace("__autosave__")` both throw "Names starting with "__"
  are reserved".

### W5: agent writes and portfolio

- **R15-AGENT-043: certified.** A fresh malformed leaf (`pe_ratio lt "cheap"`) gives "Wrote 1 of 2 screener
  criteria; dropped pe_ratio: value must be a number — review and Run", and the ack has
  `dropped: ["pe_ratio: value must be a number"]`.
- **R15-AGENT-041: certified.** `portfolio_delete_position` accepted, then the holdings are `[]`. Undo brings back the
  same id `h-98e47d66…`, with status `undone`. `remove_from_watchlist TCS` followed by Undo restores
  `[AAPL, TCS, INFY]` at the original index.
- **R15-AGENT-032: certified (vitest-executed).** Under AUTO, a failing auto-apply writes "Couldn't apply: …" and no
  "Applied:" line, and the change stays pending.
- **R15-UI-017: certified (vitest-executed).** A send with no key leaves no user turn, keeps the prompt and shows
  "No API key for …". The keyless-Ollama branch also returns before `appendUser`.
- **R15-AGENT-044: certified.** Live `/resolve` through `applyHostActionAsync`: "Mazagon Dock" gives "Added MAZDOCK
  to your watchlist (resolved from "MAZAGON DOCK")". "MAZAGONDOCK" fails and adds no row. "Cochin Shipyard" adds
  COCHINSHIP.
- **R15-AGENT-045: not certified.** See the reason in `VERDICTS.json`.
- **R15-UI-034, R15-UI-035, R15-UI-036, R15-UI-037: certified (vitest-executed).** The real PortfolioPanel covers
  four checks. Edit, switch portfolio, then Save gives "are required" and the portfolios are unchanged. Delete works
  in a portfolio switched to after mount. Quotes refetch on the 5 s interval, and the totals title reads "Oldest
  quote in these totals: …". The labels read "Avg cost / share" (placeholder "per share") and the column
  "Avg cost".

## Not certified

- **R15-AGENT-045.** The entry's exact repro still reads as a quote failure. MCP
  `compare_symbols {"symbols": ["COCHINSHIP", "MAZAGONDOCK"]}` returns
  `{"ok": false, "message": "fewer than two symbols resolved — 1 of 2 returned a quote"}`. `_compare_one` does build
  the "unresolved name: 'MAZAGONDOCK' is not a known ticker…" entry: it shows with 3 symbols, and "Mazagon Dock"
  binds to MAZDOCK. But `_compare_symbols` drops every per-symbol error when fewer than two resolve, and a
  two-symbol comparison is the entry's case. The model still reads a missing quote. The writer's test calls
  `_compare_one` only. Fix: include the per-symbol `error`/`candidates` in the `ok: false` payload (or its
  message). Pin it with the two-symbol call.
- **R15-LEAD-005, R15-AGENT-046, R15-CODE-PLATFORM-021.** Not claimed, because they were not delivered this batch.
  They stay open.

## Proposed not-a-defect / out-of-scope

None proposed by the plan or the writers. D-B7-9 (drawing drag-edit not built) is a scope note inside UI-022, not a
closure claim.

## Issues found outside the entries

1. The exchange lane (`exchange_financials.get_filed_periods`) caches only successes. A transient NSE miss on the
   first `/fundamentals/TCS` served Yahoo, flagged, and the next call served NSE. That is honest, but the panel
   can show different providers on consecutive loads.
2. The BudgetGuard prices an unknown model, including every OpenRouter `:free` slug, at the default rate. The
   AGENT-039 run on `nemotron-3-super-120b-a12b:free` recorded `spend_usd: 0.12979` for 64,895 tokens. That is
   phantom spend against a $1 ceiling on a free model. It is the same family as AGENT-074, but a different root
   cause (the model table, not the provider).
3. SEC `browse-edgar` and the directory listings returned 503 for the whole session, so every sec-edgar-mcp
   listing timed out ("The read operation timed out") while `data.sec.gov/submissions` answered in about 0.2 s. The
   20-F lane (and `/sec/filings`) depend on that one listing path.
4. `sec_ownership` returns nested beneficial-ownership rows as filed (WIT: Premji 72.62% includes the Hasham,
   Prazim and Zash rows). A consumer that sums the rows over-counts. A note on the lane would help.
5. The frozen-binary checks and the quote timestamps in the webhook payloads show `Quote.timestamp` stamped at
   fetch time (LEAD-005, still open).
