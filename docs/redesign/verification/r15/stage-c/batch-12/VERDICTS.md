# R15 Stage C: Batch 12 Verdicts (fresh-context verifier, Opus)

- **Merge target:** `worktree-agent-batch-12-int@3d588a292b08b56c5a09767ce7bb56d615a91699`, checked out in a scratch worktree outside the repo.
- **Stack:** that worktree's main sidecar, run from source on `127.0.0.1:52310` with a copy of `vysted-iso/data`. openbb-mcp was on :52153 and sec-edgar-mcp on :52154. Local model: llama3.1:8b via ollama. Free lane: `nvidia/nemotron-3-super-120b-a12b:free`. No paid calls.
- **Chain, at the merge target:**
  - pytest (full): 3194 passed, 1 skipped.
  - vitest (full): 152 files, 1829 tests passed.
  - `pnpm lint` (now `eslint . && audit-design-tokens`): exit 0.
  - `pnpm typecheck`: exit 0.
  - `pnpm format:check`: exit 0.
  - `ruff format --check`: exit 0.
  - `ruff check`: exit 0.
- **Result:** 19 certified, 3 not certified (RESEARCH-007, DOCS-017, AGENT-090), 0 needs_gui. No writer proposed a not_a_defect or out_of_scope. CODE-AGENT-033 was deferred by the planner and not assessed.
- **Verdict: approve.** Nothing certified regressed. The three not-certified entries are partial fixes that leave the product no worse than base.

## Certified

**R15-DATA-002 (critical).**
- Frontend: the vitest-executed path passes the acceptance tests:
  - `CommandPalette.test.tsx`: "a cross-region ticker pick charts the region of the listing actually picked".
  - `chart-command.test.ts`: "carries an optional region".
  - `ChartPanel.test.tsx`: "a host command's picked region rides the chart's history and indicator calls". This is the class pin on the indicator leg.
- Sidecar leg, live:
  - `/history/AMAL` with `X-Vysted-Region: US` returns yfinance, last close 47.21 (Amalgamated Financial).
  - `IN` returns nse_direct 687.65 (Amal Ltd).
- An unset per-call region is dropped by `sidecarRequest` (`value !== undefined`), so the session region still applies to every other call.

**R15-RESEARCH-002 (critical).**
- `_parse_verdict` now reads the three original repro lines and all six labelled forms from the acceptance as `unverified`. `Verdict: DISAGREE…` reads `disagree` and `Verdict: AGREE…` reads `agree`.
- Fresh cases the fix was not written against: `Status: DISAGREE — … sources agree it is lower`, `> **UNVERIFIED**: … sources confirm revenue`, `2) DISAGREE - …` and `Result - UNVERIFIED, sources agree only on revenue` all parse correctly.
- Reflect: `[GAPS] …` → False, `1. COMPLETE - …` → True. `GAPS: margins are complete…` → False and `**Assessment:** GAPS remain` → False.

**R15-AGENT-019.**
- `classify_intent`:
  - "Can you log 10 TCS at 3400 in my portfolio?", "Can you record that I hold 20 ITC at 410?" and the class pin "Could you enter 5 HDFCBANK at 1600 into my portfolio?" → `edit`.
  - Fresh cases: "Would you mind noting down 15 WIPRO at 250 for me?" and "Can you add 3 NVDA at 180 to my holdings?" → `edit`.
  - Controls "what is P/E?" and "How is my portfolio doing?" stay `read` (stripped).
- Live llama3.1:8b (autonomy auto) on the repro prompt called `portfolio_add_position {TCS, 10, 3400}`. `/portfolio/positions` stayed `[]`, so the write was staged for the host, not applied, and the §6.5 gate is intact.

**R15-DATA-043.**
- Live `/screener/run` on custom [AAPL, RELIANCE.NS, MSFT, TCS.NS], market_cap desc, limit 2 → [RELIANCE.NS INR, AAPL USD]. Coverage reads "spans INR, USD — ranked within each currency".
- Fresh case: 6 mixed symbols, asc, limit 3 → [INFY.NS, TCS.NS, MSFT]. The round-robin is per currency and the note is present.

**R15-LEAD-010.**
- Live: AAPL 10-K `0000320193-21-000105` opened with no `form_type` hint → 200, 10-K, 2021-09-25. Before the fix this 404'd.
- `/sections?form_type=10-K` returns the Business section.
- Fresh case: MSFT 10-Q `0001564590-22-035087`, the oldest in a 12-row 10-Q list, opened unhinted → 200, 10-Q, period 2022-09-30 (19 s).
- Aside: `/sections` for that 10-Q returns `[]`. Section parsing covers only 10-K items; this predates the batch.

**R15-UI-090.**
- Live at 11:07 IST on Friday, during NSE hours. `/quotes/^NSEI`, `^BSESN`, `^NSEBANK`, class pin `^CNXIT` and `^INDIAVIX` are all `freshness: live` under both `X-Vysted-Region: IN` and `US`.
- `AAPL` (US closed) reads `eod` under both regions, so the entry title's original symptom is also gone.

**R15-AGENT-092.**
- Live delegate runs, same write_note prompt, llama3.1:8b:
  - With `budget.maxTokens=1000`: status `error`, "token ceiling 1000 reached (7631 used)", `host_actions: []`.
  - Control run with the default budget: `done`, `host_actions` = [write_note …]. Dispatched host actions still reach the proposed-changes gate, so the fix causes no regression.

**R15-AGENT-093.**
- `_normalise_tool_args` against the real catalog:
  - `option_chain max_strikes "10"` → 10, and `"ten"` → the invalid-args sentinel.
  - Class pin `screener_run limit "25"` → 25.
  - Fresh case `news limit "5"` → 5.
  - Fresh case `sec_insider_transactions limit "5"` → 5, while `"5.0"` is still rejected for an integer.
- No catalog property uses a list-valued `type`, so the dict lookup cannot hit an unhashable key.
- A live llama run typed the call as text instead of emitting a tool call, which is a known llama3.1 behaviour and not this path.

**R15-AGENT-027.**
- The original repro rows now map to insufficient_credit, context_overflow, context_overflow (groq 413) and ollama_not_running.
- Live: a real httpx ConnectError to a closed port gives "Ollama is not running". A real httpx ReadTimeout against the running ollama gives "Ollama is not responding" with no internet or network copy.
- Fresh cases: a Gemini "input token count … exceeds the maximum number of tokens allowed" variant → context_overflow; OpenRouter 403 "doesn't have any credits" → insufficient_credit; together 404 `model_decommissioned` → model_not_found. A real DNS failure to a non-Ollama provider still correctly gives network copy.

**R15-CODE-PLATFORM-013.**
- vitest "toggling a bridged plugin module routes through the marketplace lifecycle, not setModuleEnabled directly" passes: `disable('vysted-example')` is called and `enabled['plugin:vysted-example']` is never false.
- The only remaining `setModuleEnabled('plugin:…')` callers are the lifecycle owner's bridge and unbridge in `plugin-bootstrap.ts`.
- GUI follow-up, not required for this acceptance: toggle the plugin off in Settings, relaunch, and confirm it stays off.

**R15-DATA-059.**
- Live `/resolve`: ONC → former_name 'BeiGene, Ltd.', SIFY → 'SIFY LTD'. Fresh case: META → 'Facebook Inc'.
- TCI (US) keeps no Indian identity: bse_code and isin are null.
- Residual: `isin` is still null for US instruments. The writer's could-not stands with evidence: CUSIP is CGS-licensed, SEC `company_tickers` has no ISIN, and neither 13(f) nor GLEIF has a ticker key. The acceptance makes the ISIN asserts conditional on the master carrying ISINs.

**R15-DATA-068.**
- Live `GET /fundamentals/AAPL/ratings` twice returns the same `as_of` both times: 2026-09-25T00:11:43Z, the cache row's write time, not now().
- An uncached MSFT stamps the fetch time.
- `types/data.ts` mirrors the field, and the Equity Overview renders `As of …` (`data-testid="equity-ratings-as-of"`).

**R15-DOCS-018.**
- Section 3.3 now names `nse_direct` 15, `nse` (jugaad) 20 and `bse` 25, region IN, ahead of yfinance 50. These match `provider_registry.py`.
- The yfinance bullet is region-qualified.
- Nit, not blocking: "fundamentals … still hit it first" ignores openbb-mcp at rank 10 when it is available. Live, `/fundamentals/AAPL` and `TCS.NS` were served by yfinance because openbb-mcp returned incomplete fundamentals.

**R15-LEAD-028.**
- Live: `/quotes/506597.BO` → AMAL 683.9 INR from bse, and `/quotes/544774.BO` → SMR 92.65 from bse.
- `/history/506597.BO` → 27 bars from bse.
- Fresh case: `500325.BO` → RELIANCE from bse.

**R15-RELEASE-007.**
- `pnpm lint` passes, and the design audit is clean on 372 files.
- Negative case, the entry's repro: injecting `gap-1.5 px-[7px] text-[12px]` into `brief-blocks.tsx` makes the audit report 3 violations and `pnpm lint` exit 1. The file was restored afterwards.

**R15-DATA-112.**
- Live repro [MANIKA.NS, RELIANCE.NS, TCS.NS]: desc → [RELIANCE, TCS, MANIKA], and asc → [TCS, RELIANCE, MANIKA]. The null row sorts last in both directions.

**R15-DATA-113.**
- Live `/earnings/WIT/estimates`: revenue_estimate_mean 244.2B with `revenue_currency: INR` (≈ ₹24,400 cr for the quarter, which matches Wipro's scale) and `currency: USD` for EPS.
- The history and surprises rows also carry `revenue_currency: INR`, which is the class pin.
- Fresh cases: TSM → TWD (1.45T), HDB → INR, AAPL → USD.
- `EpsEstimateGrid` labels revenue with `revenue_currency`.

**R15-DATA-114.**
- Live at 11:09 IST: three consecutive `/quant/option/chain/NIFTY` calls all returned 200 with as_of 2026-09-24. NSE was probed for today (404) only once; calls 2 and 3 took 0.03 s with no NSE request.
- Simulated failure: `_fetch_fo_day` forced to `failed`, with 2026-09-24 cached. Three calls served 2026-09-24 with a single probe of today.

**R15-DATA-115.**
- Live `/history/AMAL.BO?range=1y` → bse, 256 bars from 2025-09-10. Before the fix, nse_direct returned 28 bars.
- Class pin: `RELIANCE.BO` → bse.
- Control: `AMAL.NS` → nse_direct, 28 bars.

## Not certified

**R15-RESEARCH-007.**
- The acceptance URLs and the controls pass.
- Fresh cases still rank PRIMARY: `ir.firebaseapp.com`, `investors.web.app`, `ir.azurewebsites.net`, `ir.onrender.com`, `ir.fly.dev`, `ir.glitch.me`, `investors.notion.site`, `ir.webflow.io`, `ir.herokuapp.com`.
- ccSLD hosts also rank PRIMARY: `www.investors.co.uk`, `ir.co.in`, `investors.com.au`. This is the original investors.com mechanism on a two-part TLD, and the three-label check cannot see it.
- The class is "the IR label is not on a company-registrable domain". The fix needs a Public Suffix List lookup that includes the private section, not a longer denylist.

**R15-DOCS-017.**
- The sp500 count, snapshot date and universe names are correct.
- nse-all is stated as "EQ + ETF, ~2,675". The code loads 3,506 symbols: EQ 2584 + ETF 351 + SM 571.
- The number was copied from a stale docstring at `screener_universe_india.py:6`. This is the same drift class the entry is about.
- Fix: state the counts from `load_india_universe` (nse-all 3,506 including NSE Emerge SME; bse-all 5,042; india-all 5,891), or drop the count.

**R15-AGENT-090.**
- The repro prompt on llama3.1:8b fabricated a ratio in 3 of 5 runs:
  - Run 1: "10 ordinary shares".
  - Run 4: "approximately 144869230 ordinary shares", reasoned from the fundamentals result's shares-outstanding field.
  - Run 5: "1 ordinary share".
- Truth is 1 ADS = 6 ordinary shares.
- Runs 2 and 3 obeyed the new preamble rule.
- The free nemotron model now web-searches the ratio (it found "Each Repr 6 Ords") instead of citing fundamentals, but both of its runs hit an upstream 5xx before the final answer.
- The prompt rule helps but does not close the entry. No deterministic guard landed; a ponytail note records the ceiling.

## Issues found (not in this batch's scope; for the backlog)

1. The SEC `/sections` route returns `[]` for 10-Q filings (for example MSFT `0001564590-22-035087`). Section parsing covers only 10-K items.
2. `/quotes/500325.BO` reports `volume: 2.19` for RELIANCE on BSE. This looks like a unit (lakh) or partial-day artifact in the bse lane.
3. For "SIFY's TTM revenue in USD", llama3.1:8b answered in INR (₹4,651 cr) without converting or saying it had not.
4. `screener_universe_india.py:6` has a stale docstring count (~2,675) and `models/screener.py:34` has a stale comment count (~2.7k / 4.9k).
