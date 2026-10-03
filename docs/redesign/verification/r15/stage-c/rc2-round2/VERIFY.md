# rc2 round-2 fresh verifier: r15-rc2-int at 7f273b03

Verifier: claude-opus-5-5 (judgement tier, fresh context). I wrote no product code and consulted no advisor.
- Worktree: `scratchpad/rc2-verify`, detached at `7f273b036c5870d07eea08f0696a6d56e17c84ca`.
- Scope base: `aeeffae0` (= code `e5c62bd3`; `git diff e5c62bd3 aeeffae0 -- . ':(exclude)docs'` is empty).
- Raw logs are under `scratchpad/`: `rc2v-chain.log`, `rc2v-gate8.txt`, `rc2v-pins-{py,fe}.log`, `rc2v-f001.txt`, and `rc2v-live/` for every live JSON and text file cited below.

## Verdicts

| entry | verdict | failed stated-repro step |
|---|---|---|
| R15-FINAL-005 | **CERTIFIED** | none |
| R15-FINAL-006 | **CERTIFIED** | none |
| R15-LEAD-136 | **NOT CERTIFIED** | Class repro, fresh common-word name TITAN (Titan Company). "Tech titan Elon Musk unveils new rocket" scores 1.00 keep=True. |
| Overall (gate: (1)-(4) and (5a)) | **CERTIFIED** | Steps (1), (2), (3), (4) and (5a) all hold. LEAD-136 is refused on its own row. |

## (1) Scope and safety

`git diff --stat aeeffae0 7f273b03 -- . ':(exclude)docs'` gives **55 files changed, 2875 insertions(+), 306 deletions(-)**:
- Sidecar: services, routers, models, and tests (`test_final_data_fundamentals`, `test_nse_throttle`, `test_quotes`, `test_research_relevance`, ...).
- `sidecar/services/resolver_masters/english_words.txt.gz` (new, 659,150 bytes).
- Frontend: portfolio/host-actions/workspace/context-provider/SEC/equity-overview, plus `types/data.ts` (+2).

Safety surface: `git diff --name-only aeeffae0 7f273b03 -- src/store/proposed-changes.ts types/proposed-change.ts src/store/agent-autonomy.ts sidecar/services/agent_runtime.py sidecar/services/planner.py sidecar/services/action_ledger.py sidecar/tests/test_no_trading_surface.py docs/SAFETY_ARCHITECTURE.md src/modules/chat/ProposedChangesReview.tsx src-tauri .github LICENSE COMMERCIAL_LICENSE.md CLAUDE.md types/plugin.ts` returns **EMPTY**.

`src/lib/host-actions.ts` changes in three places (FINAL-016 and FINAL-030 from cac9d206):
- `parseCustomPanels` accepts a comma string.
- A custom arrange reports what it `placed` and fails when it placed nothing.
- A `write_note` whose scope is not ticker-shaped goes through `writeResolvedNote`. That function does `GET /resolve` and then calls the same `applyIntent` with the resolved scope.

None of these adds an apply path:
- `applyIntentAsync` has one production caller, `src/store/proposed-changes.ts:145`, the gate's apply step.
- `applyHostActionAsync` has no production caller.
- AUTO_APPLIED_KINDS is unchanged (panel/chart/watchlist).
- A note is still applied only through the review gate.

## (2) Chain (verify worktree)

- `pnpm install --frozen-lockfile`: INSTALL_EXIT=0
- `node scripts/ensure-all-sidecars.mjs`: ENSURE_EXIT=0. All 3 binaries were built from 7f273b03.
- `PATH=<wt>/sidecar/.venv/bin:$PATH pnpm ci-local`: **CI_EXIT=0**
  - vitest: `Test Files 170 passed (170)`, `Tests 2048 passed (2048)`
  - cargo test: `32 passed; 0 failed`
  - pytest: `3989 passed, 1 skipped, 4 warnings in 234.48s`
- The coverage ratchet rewrote `vitest.config.ts`, so I ran `git restore vitest.config.ts`. The tree is clean.
- `node scripts/smoke-test-sidecars.mjs`: **SMOKE_EXIT=0**
  - "vysted-sidecar version OK (0.9.0)", "/agents roster OK (13 agents)", "/mcp/status OK (ready=true, toolCount=39)"
  - openbb-mcp and sec-edgar-mcp bound
  - "all sidecars booted cleanly"

## (3) Gate 8

`cd sidecar && .venv/bin/python -m pytest tests/test_no_trading_surface.py -q` gives `8 passed, 1 warning in 1.23s`.

## (4) Fixed entries on touched files: pinned tests at the candidate

Selection: from the main checkout's `vysted-r15-register.json`, every `fixed` entry whose `files` intersect `git diff --name-only aeeffae0 7f273b03`, plus R15-LEAD-127, plus the 26 round-1 certified ids from `fix-r1/VERDICTS.json`. That gives **219 entries**. All 26 round-1 ids are `fixed` in the register.

How I found each entry's pins: test files that name the id, plus test files cited in the entry's closure_evidence, note or evidence. For the 13 code entries with no id-named test, I used the colocated tests:
- host-actions, proposed-changes, workspace, notes, CommandPalette, chart-sync, ChartPanel, screener, PortfolioPanel
- `test_portfolio`, `test_provider_registry{,_region}`, `test_workflow_router`

The map is in `scratchpad/rc2v-map.json`.

- pytest, 86 pinned files batched: **`1908 passed, 4 warnings in 81.34s`, PY_EXIT=0**
- vitest, 54 pinned files batched: **`Test Files 53 passed (53)`, `Tests 962 passed (962)`, FE_EXIT=0**. 53 test files ran from the 54 listed paths.
- Docs-only entries (FINAL-021/022/023/035/037, CODE-PLATFORM-074 doc half): `git diff --stat cac9d206 7f273b03` on SIDECAR_API.md, RELEASE_RUNBOOK.md, MCP_INTEGRATION.md and R12_HAND_TESTING_GUIDE.md is empty. They hold as certified.
- `src-tauri` is unchanged, so the cargo part of CODE-PLATFORM-074 is covered by cargo test in (2).

**Verdict: holds for all 219, regressed 0.** This includes R15-LEAD-127 and all 26 round-1 entries: FINAL-001/002/003/004/007/008/009/010/011/016/017/021/022/023/024/027/028/030/031/033/035/037, LEAD-060/071/077 and LIFECYCLE-024.

## (5) Live: own stack from the candidate's built binaries

Stack setup:
- Ports: main `:52970`, openbb-mcp `:52971`, sec-edgar-mcp `:52972`. All three are the worktree's `src-tauri/binaries/*` built at 7f273b03, so the onefile bundling of the new word list was exercised too.
- Data dir: `scratchpad/rc2-verify-data`, seeded from `final-seed-data`.
- `dev-keystore.json` read exactly `{"secrets": {}, "migrated": true}`.
- Region IN via the `X-Vysted-Region: IN` header and the default session.
- `/health`: `version 0.9.0`, `openbb-mcp: available`. The log never shows "missing bundled english_words".
- Every research call ran inside `mkdir /tmp/vysted-r15-ollama.lock` and released it with `rmdir`.

Teardown: I killed sleep pids 82950, 82957 and 82963. Workers 82949, 82956 and 82962 exited, and nothing listens on 52970-52972.

### (5a) R15-LEAD-127 on the merged lineage: HOLDS

| query (session IN) | resolved | structured price | structured fundamentals | outside world |
|---|---|---|---|---|
| Halliburton | HAL / HALLIBURTON CO / US | **31.85 USD** (yfinance) | **Halliburton Company**, USD, P/E 16.68, mcap 26.54B | https://stockanalysis.com/stocks/hal/: "$31.85 on October 2, 2026 … Market Cap $26.54 billion … PE 16.70" |
| Hindustan Aeronautics (control) | HAL / Hindustan Aeronautics Limited / IN | **4601.0 INR** | **HAL.NS**, Hindustan Aeronautics Limited, INR, P/E 33.01, mcap 3.077T | |

The control's first run timed out at the 6 s box. That run overlapped my pinned-test batch, and the timeout is the known R15-LEAD-128. The re-run is shown above (`r-Hindustan_Aeronautics-2.json`).

The Halliburton brief's news leg still carries "India's Hindustan Aeronautics posts strong quarterly results…". This is the residual the LEAD-127 verifier already recommended filing (news leg not region-scoped), unchanged from base.

### (5b) R15-FINAL-005: CERTIFIED

`GET /fundamentals/<sym>` (IN). Raw responses are in `rc2v-live/f005-*.json`.

| name | HTTP | revenue_ttm | net_income_ttm | eps | pe | market_cap | provenance |
|---|---|---|---|---|---|---|---|
| VOLERCAR | 200 | 54.70 Cr | 3.30 Cr | 2.95 | 73.27 @216.3 | 241.5 Cr | as_of 2026-06-30. Label: "standalone, sum of 3 periods to 2026-06-30; 2025-07-01..2025-09-30 derived as the filed half-year 2025-04-01..2025-09-30 less its filed quarter 2025-04-01..2025-06-30". P/E and market cap are `derived`, with basis_note. |
| YASHOPTICS | 200 | 53.99 Cr | 9.05 Cr | 3.65 | 37.10 @135.4 | 335.6 Cr | 2 filed half-years to 2026-03-31 |
| GANESHIN | 200 | 835.55 Cr | 76.17 Cr | 17.83 | 4.86 @86.65 | 370.2 Cr | consolidated, 2 filed half-years to 2026-03-31 |
| SUMAX | 404 | n/a | | | | | detail: "No data provider covers fundamentals for this NSE Emerge (SME) listing. The exchange holds no results filing to build them from." |
| QUALIANCE | 404 | n/a | | | | | same typed detail |
| **CURIS (fresh)** | 200 | 60.63 Cr | 6.92 Cr | 11.11 | 18.59 @206.5 | 128.6 Cr | 2 filed half-years to 2026-03-31 |
| **E2ERAIL (fresh)** | 200 | null | null | null | null | null | Each field is `unavailable` with a reason. Example: "not published by the data provider; the NSE filings (newest period to 2026-03-31) do not cover a trailing 12 months — insufficient filed periods". pe and market_cap name the missing EPS. |

Statements: income and balance for VOLERCAR, SUMAX and CURIS all return 200 with `periods []` and `reason: "No data provider covers financial statements for this NSE Emerge (SME) listing."`. That is a typed reason, not a silent empty response.

Grounding (screener.in, fetched 3 Oct 2026):

| name | screener.in | our values |
|---|---|---|
| VOLERCAR (https://www.screener.in/company/VOLERCAR/) | price 216, mcap 241 Cr, P/E 73.0; FY26 sales 52.84 Cr; Jun-25 12.35 Cr; derived Sep-25 13.89 Cr (H1 26.24 less 12.35) | FY26 + Q1FY27 − Q1FY26 = 54.70 Cr; mcap and P/E match |
| YASHOPTICS (https://www.screener.in/company/YASHOPTICS/) | price 135, mcap 335 Cr, P/E 37.0, FY26 sales 53.99 / NP 9.05 / EPS 3.65 | match |
| GANESHIN (https://www.screener.in/company/GANESHIN/) | price 86.6, mcap 379 Cr, P/E 5.15, consolidated FY26 sales 832 / NP 71 / EPS 16.58 | Revenue is within 0.4%. Our 76.17 Cr / 17.83 are the XBRL `FourD` figures the writer quoted, and include minority share. mcap is 2.3% off. |
| CURIS (https://www.screener.in/company/CURIS/) | sales 60.63 Cr, NP 6.92 Cr, mcap 167 Cr, P/E 24.1, EPS 8.56 | Revenue and NI match. **mcap and P/E are 23% off** (candidate new entry N2 below). |

Why this is certified on the stated repro:
- VOLERCAR, the refused instance, now serves values with provenance, grounded against the filing-derived screener figures.
- YASHOPTICS and GANESHIN serve values.
- SUMAX and QUALIANCE return a typed not-covered reason in `detail`, which is the sentence the panel shows (`sidecar-client.ts` `extractSidecarDetail`). The words "check the symbol" are gone from it.
- Every null headline field on E2ERAIL carries a typed reason.
- Both statement lanes carry a typed reason.

### (5b) R15-FINAL-006: CERTIFIED

This replays the round-1 verifier's load:
- The batch is the 100 cold NSE names in `fr1v/vt/sym100b.json`, sent as one `GET /quotes?asset_class=equity&symbols=…` the way the portfolio sends it.
- I timed fresh singles the writer did not use, each as `GET /quotes/<sym>?asset_class=equity` (`rc2v-live/f006-run1.txt`).
- Script: `rc2v-live/f006-load.py`.

```
21:35:43 idle NTPC.NS 200 36.670s provider=bse      (NSE path failed upstream, fell back to BSE)
21:35:49 idle POWERGRID.NS 200 6.437s provider=nse_direct
21:35:51 idle COALINDIA.NS 200 1.471s provider=nse_direct
21:35:57 loaded TATASTEEL.NS 200 0.691s
21:35:59 loaded JSWSTEEL.NS 200 0.828s
21:36:00 loaded HEROMOTOCO.NS 200 0.868s
21:36:03 loaded BRITANNIA.NS 200 1.751s
21:36:05 loaded CIPLA.NS 200 0.709s
21:38:42 batch 200 100/100 resolved in 170.9s
21:38:43 idle-after BPCL.NS 200 1.164s
21:38:44 idle-after IOC.NS 200 1.138s
21:38:45 idle-after TECHM.NS 200 1.177s
batch2 (warm, next refresh) 200 9.367s — 100/100 priced
```

- Loaded singles: **0.69-1.75 s**.
- Idle nse_direct singles: 1.14-1.47 s (median 1.17 s), with one 6.4 s outlier. NTPC's 36.7 s idle went through the BSE fallback after an upstream NSE failure.
- 2 x the median idle latency is 2.34 s. The worst loaded single is 1.75 s, which meets the target. Against the round-1 verifier's base, loaded singles were 15.0-21.2 s.
- The server returned 100/100 on the batch, and the warm next refresh was 100/100 in 9.4 s.
- Grounding: TATASTEEL served 178.0 INR EOD. https://www.screener.in/company/TATASTEEL/consolidated/ shows "₹178 … October 1, 2026 (close price)".
- I read the diff. The bulk lane keeps the slot set, so the pacing rate is unchanged. Each lane has its own session and lock. `test_an_interactive_call_is_admitted_ahead_of_a_queued_bulk_batch` is green in the (2) and (4) runs.

### (5b) R15-LEAD-136: NOT CERTIFIED

Live research FAST under IN (`rc2v-live/r-Campus_Activewear.json`, `r-Safari_Industries.json`):
- **Campus Activewear**: resolves to CAMPUS. News `data []`, note "No on-entity news found for CAMPUS — 1 item(s) returned by the news feed were off-entity/off-topic and dropped". The dropped item is a DU campus-harassment story.
- **Safari Industries**: resolves to SAFARI. News `data []`.
- Web search timed out at 8 s in both runs, so web results were empty and no web headline could leak in. Filings are all the company's own.
- So neither brief contains an unrelated common-word headline. That is weak positive evidence, because both feeds were nearly empty.

In-process, at the candidate's `relevance.entity_match` and `row_relevant`, with the economictimes URL the writer's tests use (`rc2v-live/l136-relprobe.txt`):

```
CAMPUS  0.25 keep=False  Campus placements surge as IT hiring revives | 1.00 keep=True Campus Activewear Q2 profit rises 18%
SAFARI  0.25 keep=False  Apple Safari update fixes security flaw      | 1.00 keep=True Safari Industries shares rise after Q1 results
ETERNAL 0.25 keep=False  The eternal debate: growth vs value investing| 1.00 keep=True Eternal shares rise as Blinkit orders grow
FOCUS   0.25 keep=False  Investors focus on Fed minutes               | 1.00 keep=True Focus Lighting Q1 results
RAIN (fresh, NSE, not curated, in list)  0.25 keep=False Rain lashes Mumbai, trains delayed | 0.25 keep=False Monsoon rain deficit hits kharif sowing | 1.00 keep=True Rain Industries Q2 loss narrows | 1.00 keep=True RAIN shares surge 8%
RELIANCE / INFY / ROUTE controls unchanged (1.00 kept; "Best route to the airport" 0.25 dropped)
TITAN (fresh; resolves TITAN / Titan Company Limited / NSE / IN; not curated; NOT in the bundled list)
   1.00 keep=True  Tech titan Elon Musk unveils new rocket
   1.00 keep=True  Media titan Murdoch steps down
   1.00 keep=True  Titan submersible inquiry report released
CUPID (fresh; Cupid Limited; not in list)  1.00 keep=True  Cupid's arrow: Valentine's Day spending hits record
```

**Failed step: the class repro.** TITAN is an NSE ticker that is an ordinary English word ("titan", lowercase, used as a common noun in "Tech titan Elon Musk…"), and it is not in COMMON_WORD_TICKERS. It still scores 1.00 keep=True on unrelated headlines, which is exactly the claim's shape.

Root cause: the rule's property is "in the bundled web2 list". web2 lists only the capitalised "Titan" (and "Cupid"), and the bundler drops capitalised entries as proper nouns. So common words that also exist as proper nouns fall outside the property. The rule still depends on a list, just a different one. The three stated instances, FOCUS and the controls hold.

A fix would need a word property that does not drop words because a capitalised form exists. One option is to fold case and drop a word only when no lowercase form exists anywhere, not just in web2. Another is a frequency list such as wordfreq. A third is to treat any alphabetic Indian ticker without an anchor as prose unless a non-word name token corroborates it.

## Candidate new entries (beyond the stated repros; none refuses an entry)

| id | proposed severity | finding |
|---|---|---|
| N1 | medium | **The copilot/research `fundamentals` tool bypasses the SME filings path.** MCP `fundamentals {"symbol":"VOLERCAR"}` returns `{"ok": false, "error": "provider error: No data provider covers fundamentals for this NSE Emerge (SME) listing.", "reason": "not_found"}`, while REST `/fundamentals/VOLERCAR` serves revenue/EPS/P/E/mcap. `get_fundamentals_from_filings` is called only from `routers/fundamentals.py:120`. So the agent and research briefs tell the user there is no data for a listing the panel prices (`rc2v-live/f005-mcp-*.json`). |
| N2 | high | **Derived SME market cap and P/E use the weighted-average share count implied by NI/EPS, which understates post-IPO listings.** CURIS is served market_cap 128.6 Cr (206.5 x 6,225,293 implied) and P/E 18.59, both status `ok` and `derived`. screener.in shows mcap 167 Cr and P/E 24.1, so we are 23% off (EPS 11.11 summed filed half-years vs 8.56 on the current count). Most SME names IPO'd recently, so the writer's own `ponytail:` ceiling bites systematically. Wrong money figure with a stated basis. |
| N3 | low | SUMAX and QUALIANCE `/fundamentals` still answer **404** with `"action": "Check the symbol or series id."` in the wire body, although the `detail` is the typed SME reason. The panel shows only `detail`, but MCP and other clients get a "check the symbol" next step for a real listing. On the writer's yfinance-only source run these names got a 200 shell. Under the shipped openbb-mcp configuration they 404. |
| N4 | medium | **A fully cold 100-name NSE batch takes 170.9 s server-side, which is over the 120 s `QUOTES_BATCH_TIMEOUT_MS`.** The portfolio's first refresh aborts client-side, and the next refresh (warm, 9.4 s) prices 100/100. The writer recorded this as a residual (base 124.9 s, fix 128.0 s). I measured 170.9 s. |
| N5 | medium | LEAD-136 sibling: proper-noun-shaped NSE word tickers missing from the bundled list (TITAN, CUPID, TRENT, APOLLO, LINCOLN, NILE, MAZDA, ...) keep the pre-fix behaviour. If LEAD-136's re-fix uses a broader property this folds in. Otherwise file it separately. |
| (known) | medium | The LEAD-127 news leg is not region-scoped. The Halliburton brief's news is HAL-India's results, as already recommended by the LEAD-127 verifier. |
