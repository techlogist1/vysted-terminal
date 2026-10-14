# R15 Stage C: Batch 2 Verdicts (fresh-context verifier)

- **Target:** `worktree-agent-batch-2-int@16f2a5eb120053b0839ea1936991958ee0f085e5` (base `369faa7`).
- **Verifier:** Opus, fresh context. Evidence comes from the running app and the outside world, not from the diff.
- **Rig:** a scratch worktree of the target, with its own sidecar booted from source on `127.0.0.1:52310`. The data dir was a `sqlite .backup` copy of `vysted-iso/data`. MCP env pointed at `:52153`/`:52154`. For the latency A/B only, a base-code (`369faa7`) sidecar ran on `:52311` against a second copy.
- **LLM lanes:** local `llama3.1:8b` for agent-side entries (AGENT-001, RESEARCH-004/029 ULTRA). OpenAI `gpt-4o-mini` ran twice under the vy.py guard (about $0.008 total) for the DEEP originals (RESEARCH-003, RESEARCH-001). The local lane is documented to time out DEEP synthesis (research-briefs/EVIDENCE.md, 2 of 2 runs).
- **Frontend:** scratch vitest files (never committed, removed with the worktree) drove the real modules against the live `:52310` sidecar with real `fetch`.

## Verdict: approve

| Result        | Count | Entries                                   |
| ------------- | ----- | ----------------------------------------- |
| Certified     | 37    | listed below                              |
| Not certified | 3     | R15-DATA-005, R15-DATA-014, R15-AGENT-001 |
| needs_gui     | 0     | none                                      |

No entry was proposed as not-a-defect or out-of-scope, so there was nothing to concur with or refuse. Nothing certified reintroduces a defect. One performance cost is flagged below as issue 1. It is not blocking.

## Chain (re-run at 16f2a5e in the scratch worktree)

| Gate                        | Result                              |
| --------------------------- | ----------------------------------- |
| pytest (sidecar)            | 2360 passed, 1 skipped, EXIT 0      |
| vitest                      | 121 files, 1419 tests passed, EXIT 0 |
| tsc --noEmit                | EXIT 0                              |
| prettier --check .          | clean, EXIT 0                       |
| eslint .                    | EXIT 0                              |
| grep: `unit="percent"`      | none left in semantics.py           |
| grep: `autosaveLayout()` in page.tsx | none                       |
| grep: `_is_blocked` copies  | none (one `witness.is_block_error`) |
| Tier-1 files / trading re-add | untouched / none                  |

## Per-entry evidence

### W1: fundamentals seam

- **R15-DATA-008: certified.**
  - Live `GET /fundamentals/SIFY` (US) returns `currency USD` and `financial_currency INR`, with `revenue_ttm 46,506,049,536`.
  - `price_to_sales` and `ev_to_ebitda` are withheld with the reason "mixes bases: trades in USD, reports in INR".
  - The live EO renders "Revenue (TTM) ₹46.5B" and "Market cap $1.01B".
- **R15-DATA-004: certified.** Live IN results:
  - DHANBANK insiders 51.18% is flagged: "promoter group: 0.00%, quarter 2026-06-30".
  - JONJUA 46.62% is flagged against 29.67%.
  - VERTEX 77.68% is flagged against 36.43%.
  - NAPEROL institutions 0.00% is flagged against 1.77%.
  - DHOOTTRANS is flagged "unreconciled: exchange shareholding unavailable".
  - The live EO row reads "Insiders (Yahoo) +51.18% flagged".
  - The narrative exclusion is covered by pytest only, because this profile has no AI key.
- **R15-DATA-013: certified.** Live results:
  - DAL eps 8.9 and P/E 5.60 are flagged "net income / shares = 2.04 … P/E 24.5". Screener shows Mkt Cap 25.0 Cr and Profit 1.02 Cr, which is P/E about 24.5.
  - SMR 5.58 is flagged against 13.27.
  - JNPR 0.70 is flagged against 0.92.
  - DHOOTTRANS: Yahoo EPS has moved to 20.33, 4% from 21.17, inside the stated 5% band.
- **R15-DATA-005: NOT certified.**
  - VERTEX shares, book value and P/B are flagged "74,012,189 vs 148,024,384 implied". ONC is flagged at 8%.
  - JNPR still reproduces live: book_value 70.02 and P/B 3.82 are served ok. 70.02 is equity divided by the pre-IPO 488,989,292 shares, while shares_outstanding is the post-IPO 568,998,442.
  - JUMBO still reproduces live: book_value 54.361 is served ok. Its own balance sheet gives 477,377,000 / 8,373,700 = 57.01.
- **R15-DATA-014: NOT certified.**
  - FUSION is flagged: "858cr diverges 43% from FY2026 1,513cr". JONJUA is labelled "annual, not trailing-4Q".
  - DAL is still served ok at revenue_ttm 2.76cr, while screener.in on 2026-09-23 shows "Revenue: 9.97 Cr". The provider's own FY2026 Total Revenue is 20,668,000, so the witness agrees with the wrong figure.
  - The DAL test fixture stubs an annual of 99,700,000 that does not exist.
- **R15-DATA-006: certified.**
  - Live `GET /quotes/DAL` returns `timestamp 2025-03-12`, `change 0.0` and `freshness stale`.
  - BSE `getScripHeaderData` 539681 returns `Ason '12 Mar 25 | 16:00'`, `LTP 49.88`, `PrevClose 47.51`.
  - `/fundamentals/DAL` price fields are `as_of 2025-03-12`.
  - Class case: see DATA-070.
- **R15-DATA-070: certified.**
  - End-to-end `fetch_news` over an RSS feed with undated and malformed items returns the dated items newest first, then the undated ones with `published_at None`.
  - The NewsFeedPanel "date unknown" test passes.
- **R15-DATA-033: certified.**
  - A NaN quote, an inf quote and a NaN last close are each rejected by the gate with `CorrectnessError`, so they fall through to the next provider.
  - Fresh case: an india_provider frame with a NaN OPEN cell drops that bar and serves no NaN.

### W2: instrument identity

- **R15-DATA-012: certified.**
  - In process, with an injected NSDL→GUJENERGY row, `resolve('NSDL','IN')` returns BSE NSDL (ISIN INE301O01023) with `rename None`.
  - Live on today's map, which holds SHREE→AJMERA, HSIL→AGI, WORTH→WORTHPERI and DTIL→DPTL: each resolves to its own company with no rename.
  - A genuine rename still works: ZOMATO→ETERNAL.
- **R15-CODE-DATA-001: certified.**
  - Live `/resolve?q=FOCUS` offers two candidates: NSE Focus Lighting (no ISIN) and BSE Focus Business Solution (INE0DXR01010 / 543312). BSE ComHeadernew 543312 confirms INE0DXR01010 is IT software.
  - `/disclosures/shareholding?symbol=FOCUS` has `split_source None`. The pre-fix cached row had to be dropped first; see issue 2.
  - Fresh case: RELIANCE still merges, with `split_source BSE`.
- **R15-DATA-018: certified.**
  - Live `/resolve?q=zomato` and `?q=ZOMATO` both return ETERNAL with the rename note. Autocomplete for ZOMATO lists ETERNAL.
  - SEQUENT returns VIYASH, and `/resolve?q=VIYASH` has `former_name SEQUENT`.
  - The agent's `resolve_symbol` tool, with the map loaded, binds 'Zomato' to ETERNAL at confidence 1.0.
- **R15-DATA-001: certified.** Live IN income statements:
  - DAL, CHTR, SAFE, CSL, ICON, AMAL, SMR and TTC each come back as their `.BO` listing with March fiscal years in INR scale. DAL revenue is 2.07cr, not Delta's 41-53B.
  - DAL balance and cashflow are both `DAL.BO`.
  - US AMAL returns `AMAL` with December periods. `RELIANCE.NS` passes through unchanged.
  - SUMAX returns a 404 "No instrument matches" instead of a US fund's name.
- **R15-DATA-002: certified.** The live EO was driven through jsdom with real fetch against `:52310` in an IN session:
  - Picking "Amalgamated Financial Corp." sent `X-Vysted-Region: US` on all 7 legs.
  - The panel shows "Amalgamated Financial Corp. 47.29 USD", with no Amal Ltd.
  - A typed `smr` shows the chooser "SMR Jewels Ltd BSE / NUSCALE POWER Corp US" with 0 fan-out calls.
- **R15-DATA-003: certified.**
  - A live research `snapshot_structured('AMAL', region US)` carries no `ownership_exchange`, no promoter figure and no 71.35.
  - The control, `AMAL.BO` in IN, carries promoter 71.35 from BSE.
  - `is_applicable` is false for AMAL and SMR and true for AMAL.BO and SMR.BO.
- **R15-CODE-DATA-005: certified.**
  - `ownership_check`, `market_cap_witness` and `range_check` each bind `is_applicable` to `witness.is_india_listing`.
  - `is_block_error` has one copy. `is_india_target` has one copy, and `research/disclosures.py` imports it.
  - Residual outside the register repro: the `_row_value` twin remains (issue 8).

### W3: research integrity

- **R15-RESEARCH-001: certified.**
  - The live BDL news feed returned 131 region-wide items. All were dropped with the honest note, and no generic "News for BDL" feed source was added.
  - The original offending item (Sterling and Wilson Rs 985 cr, `symbols: []`) is dropped. An on-entity BDL order item is kept and cited as its own source.
  - The live DEEP BDL run on gpt-4o-mini produced a brief with 25 sources, all BDL, and no Sterling, solar or 985 content.
- **R15-RESEARCH-002: certified.**
  - All three proven UNVERIFIED strings, plus `**UNVERIFIED**: sources confirm nothing`, parse as `unverified`.
  - DISAGREE and AGREE parse correctly.
  - Live ULTRA rows render UNVERIFIED and DISAGREEMENT honestly.
- **R15-RESEARCH-034: certified.**
  - `_reflect_says_complete('Price action is not covered yet')` returns False.
  - `'COMPLETE'` returns True, and `'no gaps'` now returns True.
- **R15-RESEARCH-004: certified.** The live ULTRA Kaynes run on llama3.1:8b (the original repro):
  - The cross-check rows read `40.5%`, `-0.4%`, `-24.4%`, `₹23,246 cr` and `53.46%`. Before the fix they read `5%`, `4%` and `13953`.
  - The step reads "checked 5 numeric claim(s): 0 verified, 4 unverified, 1 disagreement(s)".
- **R15-RESEARCH-015: certified.**
  - When one domain is reached by both lanes, the result is `unverified`, "only 1 independent source(s)", `corroborated False`.
  - Control: distinct lane domains give `agree`, `corroborated True`.
- **R15-RESEARCH-003: certified.**
  - A Blue Star-shaped findings list keeps price at [6] and fundamentals at [7] after round 2 adds 5 primary filings, and the round-1 prefix is unchanged.
  - The live DEEP Blue Star run on gpt-4o-mini published 29 rail sources. Its markers [11] and [18] are in range and topical, and no marker points at the Change-in-Directorate PDF.
- **R15-RESEARCH-029: certified.**
  - `citecheck` over the real r3-ultra-kaynes markdown strips 9 bibliography and `[n]` items, leaving no `[n]` literals and no References or Merged Sources.
  - The live ULTRA step reports "1 model-written source list(s)/[n] literal(s)" stripped. The published body has no `[n]` literals and no bibliography.
- **R15-RESEARCH-037: certified.** `priority_note` on an unranked list names the real numbers: "primary [2]; tier-1 press [3]".
- **R15-AGENT-001: NOT certified.** The fresh case, "research Bharat Electronics" on local llama3.1:8b:
  - Chat said "Market Cap: ₹2,895,037 cr". That is 10x high.
  - The payload display said `₹289,504 cr`, and screener shows ₹2,90,636 Cr.
  - The KPIT original is now correct (1.42%, ₹14,346 cr), and all derived units are fraction or currency. The money half still depends on the model obeying the prompt.

### W4: workspace persistence

All results here come from real `src/lib/workspace.ts` against the live `:52310` sidecar with real fetch.

- **R15-LIFECYCLE-003: certified.**
  - With the triggers wired at mount, the restore issued 0 POSTs (only `GET /workspace/__autosave__`).
  - After edits, the blob on disk carries `researchSymbol TCS`, the research space `Research: TCS` and holdings TCS.
- **R15-CODE-FRONTEND-005: certified.** In the same run, the disk blob carries the chart drawing `d1` and the keybinding `palette.open: mod+shift+p`.
- **R15-CODE-FRONTEND-018: certified.** The disk blob carries `savedScreens ["Cheap tech"]`.
- **R15-CODE-FRONTEND-001: certified.** After save "Swing b2v", a change of portfolios and notes, then `loadWorkspace`, the live state is still HDFCBANK and "week 2 notes".
- **R15-LIFECYCLE-002: certified.**
  - A live `__autosave__` blob with a registered chart plus two broker panels restores with `panels ['chart']`.
  - Holdings INFY, the notes and the watchlist INFY are restored, and 0 POSTs were issued.
- **R15-CODE-FRONTEND-004: certified.**
  - Live POST, GET, list and DELETE round-trip "Research: NVDA", "Research: RELIANCE.NS", "Research: M&M", "My Layout (2)", a Hindi name, `../escape` and `a/b\c`.
  - Files are stored encoded inside `workspaces/`, and nothing escaped the directory.
  - A live `createResearchSpace('nvda')` and `('M&M')` both save, list and load.
- **R15-LIFECYCLE-009: certified.**
  - Three v0.8.0 rows were POSTed to the live `/portfolio/positions`. A portfolios-less blob then imports RELIANCE.NS 10 @2890.55, TCS.NS 5 @3400 and BTC/USDT 0.05 @60000, and the import is saved.
  - On relaunch there are no duplicates and the ledger is not read.

### W5: surfaces and math

- **R15-DATA-009: certified.** A seeded random walk of 200 dates gives curve points = 200 for N=1, 2 and 4. The engine Sharpe equals an independently computed date-sampled Sharpe (1.155, 1.412, 2.536).
- **R15-DATA-010: certified.**
  - The register series gives Sortino 6.3521. An independent textbook computation also gives 6.3521; the pre-fix value was 261.93.
  - Two identical losses give 4.32, not 0.
- **R15-DATA-011: certified.** Live `POST /quant/option/price`:
  - Binomial theta is -39.81, against Black-Scholes -39.68 (the pre-fix value was +39.84).
  - Gamma is 0.01909, 0.01892, 0.01884, 0.01880 and 0.01879 at 50, 100, 200, 201 and 500 steps, against Black-Scholes 0.018762.
  - An American put has theta -2.25.
- **R15-DATA-031: certified.**
  - The EarningsCalendar vitest cases pass: EPS carries its currency affix and the sort never interleaves currencies.
  - With lightweight-charts mocked, the series titles are "Surprise (EPS ₹)" and "Price Target (₹)" for INR data.
  - The live earnings route cannot yet serve an INR row (RELIANCE.NS becomes RELIANCE-NS, which comes back empty), as the refuter noted.
- **R15-DATA-042: certified.** The CSV test passes: it has a Currency column and a blank Weight % when currencies are mixed.
- **R15-CODE-PLATFORM-053: certified.** Live quotes (RELIANCE.NS in INR, AAPL in USD) through `buildPortfolioSummary` give `mixedCurrencies true`, `concentration null` and weights `[null, null]`.
- **R15-DATA-043: certified.**
  - Live `/screener/run` on the custom list [AAPL, RELIANCE.NS, MSFT, TCS.NS] has the coverage line "spans INR, USD — ranked within each currency".
  - The live result in the real table stays currency-contiguous under the default, mcap-toggled and price sorts.
  - The criteria-builder vitest shows "Market cap (INR)" and "Insider holding (Yahoo)".
- **R15-DATA-100: certified.** Live bond pricing in region IN renders "₹1,060.58" with no `$`.
- **R15-DATA-007: certified.**
  - After the pre-fix cached row was dropped (see issue 2), live `/sec/filings/0000320193-23-000077` returns 404 "filing metadata unavailable".
  - Fresh case: the in-window 10-Q 0000320193-26-000020 returns `form_type 10-Q`, `company_name Apple Inc.`, `filed 2026-07-31` and `edgar_url …/data/320193/…`.

## Issues (outside the entries, not in the diff)

1. **/fundamentals latency.** `correctness_gate.apply_witnesses` runs uncached on every call. That means the exchange shareholding for `.NS`/`.BO`, plus two yfinance statement fetches for a yfinance-served payload.
   - An A/B on the same machine for TCS, INFY, ITC, HDFCBANK and SBIN over 3 rounds: base median 2.1 / 2.1 / 2.9 s against batch-2 median 4.0 / 3.9 / 8.5 s, with a maximum of 18 s.
   - US symbols showed no difference.
   - `/fundamentals` is now the EO's long pole, and it adds exchange and Yahoo calls per load.
   - Suggested next step: cache the ownership witness per listing (it changes quarterly).
2. **Pre-fix cache rows survive the upgrade for up to 24 h.**
   - The fabricated `sec:filing:*` rows (10-K, filed "today", company '') and FOCUS's merged `disclosures:shareholding` split were still served by the fixed code from `data_cache`, until those keys were deleted in the verifier's copy.
3. **The DATA-014 DAL test encodes a world that does not exist.** It stubs `test_fundamentals.py:455-457` with a provider annual of 99.7M. Yahoo's real FY2026 figure for DAL.BO is 20.67M.
4. **The "TTM basis: only N filed quarter(s) (e.g. a half-yearly filer) — annual, not trailing-4Q" flag fires on quarterly filers** whose Yahoo quarterly frame is sparse: JUMBO 3, FUSION 3, DHOOTTRANS 1. The reason text can be wrong about the filer.
5. **`yfinance_provider.get_quote` still stamps `timestamp=_utcnow()`.** The plan asked for this to stop. It is bounded, because `fast_info` errors when there are no recent bars: DAL.BO raises instead of fabricating.
6. **The SEC sectioner returns 0 sections even with the correct form type.** This is pre-existing: the pre-fix cached rows also had 0. Filing detail only resolves within the issuer's last 40 filings, so AAPL's 10-K 0000320193-25-000079 now returns 404 (DATA-038/039, deferred).
7. **The EO labels a mixed-basis withheld P/S as "withheld — implausible".** The wording is generic, and the reason is only in the tooltip.
8. **The `_row_value` twin remains** in `growth_check.py:85` and `earnings_quality.py:134`. CODE-DATA-005's title names it, but its repro does not.
9. **`docs/redesign/DECISIONS.md` carries two rows with id D85.** This is pre-existing and was surfaced by the prettier pass.
10. **The AGENT-001 residual.** The research tool payload still carries the raw `fundamentals.market_cap` float next to the derived display.
