# R15 Stage C: Batch 2 Plan (critical and high)

- **Base:** branch `004-r4-experience-rebuild` at `369faa73affeb0230769ca4e81fc959f17788dda`. The D81 trading removal (`a122dbf`) is already merged, so none of this batch adds trading back.
- **Author:** batch planner (Opus). I opened the code at each cited line before writing any row below. Each mechanism follows the refuter's corrected verdict, not the raw claim.
- **Queue after adjudication:** 16 critical, 103 high, 259 medium, 211 low.
- **Selection:** 40 open entries.
  - All 16 criticals are in.
  - Every entry that shares a **root cause** with a selected entry is also in.
  - The rest are highs in the four named areas (ui-panels, agent-chat, research-search, data-smallcaps). I picked the highs that sit in the same code as the criticals, so each writer works in one seam.
- **Class rule.** A defect class means a shared root cause, not a shared `defect_class` label. The register's labels group mechanisms that have nothing in common. Examples: `upgrade-data-orphaned` groups a portfolio import with a renamed agent tool id, and `invariant-held-by-comment` groups four unrelated invariants. §5 lists each label-mate I did not take and names its different mechanism. Three entries joined the batch on shared root cause under a different label:
  - `R15-CODE-DATA-005` shares its root cause with `DATA-003`.
  - `R15-CODE-PLATFORM-053` shares its root cause with `DATA-042`.
  - `R15-RESEARCH-037` shares its root cause with `RESEARCH-003`.

---

## 0. The 40 entries

| # | Entry | Sev | Areas | Root-cause class | Writer |
|---|---|---|---|---|---|
| 1 | R15-DATA-008 | crit | data-smallcaps, ui-panels | currency-mislabel (statement currency) | W1 |
| 2 | R15-DATA-004 | crit | ui-panels, data-smallcaps, agent-chat | unreconciled-yfinance-scalar | W1 (+W2 EO, +W5 screener labels) |
| 3 | R15-DATA-005 | crit | data-smallcaps, ui-panels | unreconciled-yfinance-scalar | W1 |
| 4 | R15-DATA-013 | high | data-smallcaps, ui-panels | unreconciled-yfinance-scalar | W1 |
| 5 | R15-DATA-014 | high | data-smallcaps, ui-panels | unreconciled-yfinance-scalar | W1 |
| 6 | R15-DATA-006 | crit | data-smallcaps, ui-panels | fabricated-freshness | W1 |
| 7 | R15-DATA-070 | med | ui-panels | fabricated-freshness | W1 |
| 8 | R15-DATA-033 | high | data-smallcaps | nan-passes-gate | W1 |
| 9 | R15-DATA-012 | crit | data-smallcaps, research-search | identity-by-ticker-string | W2 |
| 10 | R15-CODE-DATA-001 | high | data-smallcaps, research-search | identity-by-ticker-string | W2 |
| 11 | R15-DATA-018 | high | research-search, agent-chat, data-smallcaps | rename-lane-unreachable (same lane as #9) | W2 |
| 12 | R15-DATA-001 | crit | data-smallcaps, ui-panels | wrong-entity-ticker-collision | W2 |
| 13 | R15-DATA-002 | crit | ui-panels, data-smallcaps, research-search | wrong-entity-ticker-collision | W2 |
| 14 | R15-DATA-003 | crit | research-search, data-smallcaps | wrong-entity-ticker-collision (India-lane predicate) | W2 |
| 15 | R15-CODE-DATA-005 | med | research-search | same predicate as #14 (duplicated) | W2 (+W3 twin half) |
| 16 | R15-RESEARCH-001 | crit | research-search, data-smallcaps | off-entity-evidence | W3 |
| 17 | R15-RESEARCH-002 | crit | research-search | llm-output-marker-scan | W3 |
| 18 | R15-RESEARCH-034 | low | research-search | llm-output-marker-scan | W3 |
| 19 | R15-RESEARCH-004 | high | research-search | crosscheck-integrity | W3 |
| 20 | R15-RESEARCH-015 | med | research-search | crosscheck-integrity | W3 |
| 21 | R15-RESEARCH-003 | high | research-search | citation-integrity (source numbering) | W3 |
| 22 | R15-RESEARCH-029 | med | research-search, ui-panels | citation-integrity | W3 |
| 23 | R15-RESEARCH-037 | low | research-search | same numbering root as #21 | W3 |
| 24 | R15-AGENT-001 | crit | agent-chat, research-search, data-smallcaps | unit-mislabel-in-model-payload | W3 |
| 25 | R15-CODE-FRONTEND-001 | crit | ui-panels, research-search | workspace-blob-scope-conflation | W4 |
| 26 | R15-LIFECYCLE-002 | high | ui-panels, research-search | restore-discards-user-state | W4 |
| 27 | R15-LIFECYCLE-003 | high | ui-panels, research-search | autosave-restore-race | W4 |
| 28 | R15-CODE-FRONTEND-004 | high | research-search, ui-panels | sidecar-frontend-contract-drift | W4 |
| 29 | R15-CODE-FRONTEND-005 | high | ui-panels, research-search | persisted-slice-registry | W4 |
| 30 | R15-CODE-FRONTEND-018 | med | ui-panels | persisted-slice-registry | W4 |
| 31 | R15-LIFECYCLE-009 | high | ui-panels | upgrade-data-orphaned (portfolio) | W4 |
| 32 | R15-DATA-009 | crit | agent-chat | wrong-metric-math | W5 |
| 33 | R15-DATA-010 | crit | agent-chat | wrong-metric-math | W5 |
| 34 | R15-DATA-011 | crit | ui-panels, agent-chat | wrong-metric-math | W5 |
| 35 | R15-DATA-031 | high | ui-panels | currency-mislabel (panel formatting) | W5 |
| 36 | R15-DATA-042 | high | ui-panels | currency-mislabel (cross-currency weight) | W5 |
| 37 | R15-CODE-PLATFORM-053 | low | none | same root as #36 (D57 held by the caller) | W5 |
| 38 | R15-DATA-043 | high | ui-panels, data-smallcaps | currency-mislabel (screener rank) | W5 |
| 39 | R15-DATA-100 | low | ui-panels | currency-mislabel (hard-coded $) | W5 |
| 40 | R15-DATA-007 | crit | ui-panels, agent-chat | fabricated-metadata | W5 |

Criticals by writer: W1 has 4, W2 has 4, W3 has 3, W4 has 1, W5 has 4.

---

## 1. File ownership: five disjoint sets

Each file belongs to exactly one writer. A writer may **read and import** another writer's module but never edits it.

| Writer | Model | Owns (edits allowed only here) |
|---|---|---|
| **W1 `fundamentals-seam`** | opus | `sidecar/services/yfinance_provider.py`, `sidecar/services/correctness_gate.py`, `sidecar/models/fundamentals.py`, `sidecar/routers/fundamentals.py`, `sidecar/services/company_narrative.py`, `sidecar/services/india_provider.py`, `sidecar/services/bse_provider.py`, `sidecar/services/news_provider.py`, `sidecar/models/news.py`, `sidecar/models/market.py` (only if the quote contract needs it), `sidecar/routers/quotes.py`, **`types/data.ts`**, `src/modules/news/NewsFeedPanel.tsx`. Tests: `test_yfinance_provider.py`, `test_correctness_gate.py`, `test_fundamentals.py`, `test_company_narrative.py`, `test_bse_provider.py`, `test_india_provider.py`, `test_news.py`, `test_news_tool.py`, `src/modules/news/NewsFeedPanel.test.tsx` |
| **W2 `instrument-identity`** | opus | `sidecar/services/symbol_resolver.py`, `sidecar/services/nse_symbol_change.py`, `sidecar/services/resolution_policy.py`, `sidecar/routers/resolve.py`, `sidecar/services/corporate_disclosures.py`, `sidecar/services/ownership_check.py`, `sidecar/services/market_cap_witness.py`, `sidecar/services/dividend_actions.py`, `sidecar/services/research/range_check.py`, **new** `sidecar/services/witness.py`, `sidecar/services/provider_registry.py`, `sidecar/services/openbb_mcp_provider.py`, `src/modules/equity-overview/EquityOverviewPanel.tsx`, `src/modules/equity-overview/api.ts`, `src/lib/sidecar-client.ts`, `src/lib/host-actions.ts` (**only** `openCompanyOverview`), `src/store/equity-command.ts`. Tests: `test_symbol_resolver.py`, `test_resolver_rename.py`, `test_nse_symbol_change.py`, `test_resolve_symbol_tool.py`, `test_corporate_disclosures.py`, `test_ownership_check.py`, `test_market_cap_witness.py`, `test_dividend_actions.py`, `test_range_check.py`, `test_provider_registry.py`, `test_provider_registry_region.py`, `test_openbb_mcp_provider.py`, new `test_witness.py`, `EquityOverviewPanel.test.tsx`, `sidecar-client.test.ts`, `host-actions.test.ts`, `equity-command.test.ts` |
| **W3 `research-integrity`** | opus | `sidecar/services/research/{verify,deep,iter,citecheck,relevance,fast,semantics,finance,disclosures}.py`, `sidecar/agents/copilot.json`, `sidecar/services/research/models.py` (if the derived-value wire needs it), `types/brief.ts`, `src/modules/research/brief-blocks.tsx`, `src/lib/brief-ingest.ts`. Tests: `test_research_{verify,deep,iter,citecheck,relevance,fast,semantics,finance,disclosures}.py`, `brief-blocks.test.ts`, `brief-ingest.test.ts` |
| **W4 `workspace-persistence`** | opus | `src/lib/workspace.ts`, `src/app/page.tsx`, `src/components/PanelHost.tsx`, `src/modules/platform/WorkspaceDialog.tsx`, `src/store/{chart-drawings,keybindings,research-spaces,settings,search-settings,brief,screener,portfolios}.ts`, `src/components/SettingsPanel.tsx`, `src/components/OnboardingFlow.tsx` (only its autosave trigger), `src/modules/portfolio/api.ts`, `sidecar/services/workspace_store.py`, `sidecar/routers/workspace.py`. Tests: `src/lib/workspace.test.ts`, the matching `src/store/*.test.ts`, `sidecar/tests/test_workspace.py` |
| **W5 `surfaces-and-math`** | **sonnet** | `sidecar/services/backtest_engine.py`, `sidecar/services/agent_tools/backtest_summary.py`, `sidecar/services/quant/options.py`, `sidecar/services/screener.py`, `sidecar/models/screener.py` + `types/screener.ts` (only if a note field is needed), `sidecar/services/sec_filings_provider.py`, `sidecar/routers/sec_filings.py`, `src/modules/earnings/{EarningsCalendarPanel,EpsEstimateGrid,EarningsSurpriseChart}.tsx`, `src/modules/analyst-ratings/{IndividualAnalystTable,PriceTargetTimeline}.tsx`, `src/modules/portfolio/{PortfolioPanel.tsx,metrics.ts}`, `src/modules/quant/BondPricerPanel.tsx`, `src/modules/screener/{ScreenerResultsTable,ScreenerCriteriaBuilder,CriterionGroupEditor,ScreenerPresets}.tsx`. Tests: `test_backtest_engine.py`, `test_quant_options.py`, `test_screener.py`, `test_sec_filings_provider.py`, `test_sec_filings_router.py`, and the matching `*.test.tsx` / `metrics.test.ts` |

These files are not in the batch: `CLAUDE.md`, `src-tauri/tauri.conf.json`, `.github/**`, `LICENSE*`, `types/plugin.ts`, `r15-fanout.js`, `docs/**` and `scripts/**`. Writers record nothing in docs. The integrator records the §6 decisions.

### 1.1 Cross-writer contracts (all fixed here)

- **C1 `FieldMeta.status` gains `"flagged"`** (owner W1, in `sidecar/models/fundamentals.py` and `types/data.ts`).
  - Meaning: the value is kept, a cross-check disagrees, and `reason` must name the disagreement and the witness figure.
  - The gate's existing soft flags (currently `ok` plus a reason: the 52-week pair and the market cap) **migrate to `flagged`**, so every flagged value is visibly flagged.
  - `semantics._field_reason` already returns the reason for any status other than withheld or unavailable, so W3 needs no change.
  - W2 renders a visible `flagged` chip beside a *present* value in the EO. Today the chip only appears for null values.
- **C2 `Fundamentals.financial_currency: str | None`** (owner W1, on both sides).
  - It holds the currency of the statement-denominated sizes (`revenue_ttm`, `net_income_ttm`, `free_cash_flow`) when Yahoo's `financialCurrency` differs from the trading `currency`. It is `None` when the two are equal.
  - W2 (EO money rows) and W3 (`brief-blocks.tsx` "Revenue", line ~368) format those fields in `financial_currency ?? currency`.
- **C3 `NewsItem.published_at: datetime | None` / `string | null`** (owner W1, both sides, plus `NewsFeedPanel`).
- **C4 India-listing predicate** (owner W2, in the new `services/witness.py`):
  - `is_india_listing(listing)` is true when the **resolved listing** carries `.NS` or `.BO`. The listing is the Yahoo form that the fundamentals leg and `/fundamentals` already return. Bare-ticker master membership never decides.
  - The NSE-only lane (`dividend_actions`) uses `is_india_listing(listing) and is_nse_symbol(bare)`.
  - `is_block_error(exc)` is the single copy of `_is_blocked`.
  - W1 calls `ownership_check.get_exchange_ownership(fund.symbol)` from `/fundamentals`. `fund.symbol` is the Yahoo listing form, so this is correct under C4.
- **C5 `is_india_target` twin** (owner W3): delete the copy in `research/disclosures.py` and import it from `research/relevance.py`. `relevance.is_india_target` must accept `None`.
- **C6 `openCompanyOverview(symbol, highlightMetric?, region?)`** and `useEquityCommandStore.loadSymbol(symbol, highlightMetric?, region?)` (owner W2). Existing callers stay unchanged.
- **C7** W2's `openbb_mcp_provider` imports `yfinance_provider._yahoo_symbol` (a W1 file) as it is. W1 must not rename that function or change its signature.
- **Type-contract commit rule:**
  - W1's **first commit** contains the complete `types/data.ts` change: C1, C2, C3, and any field W1 adds for its own gate (for example the price its ratios were computed at). W1 also makes the matching model-field additions in that commit, then pushes it immediately.
  - W1 makes **no later edit to `types/data.ts`**. If one proves unavoidable, W1 tells the integrator in its final report.
  - W2 and W3 `git cherry-pick` that one commit before writing consumer code, so their local `tsc` is green. The integrator merges W1 first, and git resolves the identical hunk cleanly.

---

## 2. Per-writer entries (mechanism, then fix, test and files)

For every writer, the first step is: `git reset --hard 369faa73affeb0230769ca4e81fc959f17788dda`, then confirm with `git log -1`.

### W1: `fundamentals-seam` (opus, 8 entries)

Commit 1 is the contract commit from §1.1: C1, C2 and C3 in the models and `types/data.ts`. The gate follows one existing doctrine, from D56, D66 and D68: **disclose, never substitute.** A Yahoo scalar that disagrees with a same-payload or exchange witness becomes `flagged` with the witness figure named. It is never silently swapped for a derived number.

**R15-DATA-008 (critical): SIFY sizes in INR under a USD label**
- **Mechanism:** `yfinance_provider.py:363` sets `currency = info['currency'] or info['financialCurrency']`, which gives the trading currency (USD). Lines `:391-393` copy `totalRevenue`, `netIncomeToCommon` and `freeCashflow`, which Yahoo states in `financialCurrency` (INR). `models/fundamentals.py:55` says the sizes are "in currency". Yahoo's `priceToSalesTrailing12Months` mixes the two bases, so the ratio is off by about 94x.
- **Fix:**
  - Keep `currency` as the trading currency.
  - Set `financial_currency` (C2) when `financialCurrency` differs.
  - Put a withheld stamp on every Yahoo ratio that mixes the two bases. Verify each one against the SIFY fixture: at least `price_to_sales`. Check `price_to_book` and `ev_to_ebitda` too, and withhold them only if they mix bases.
  - Correct the model docstring.
- **Test:** `test_yfinance_provider.py`, SIFY info fixture (USD/INR): revenue is kept with `financial_currency == "INR"` and `price_to_sales` is withheld with a reason. For a case the fix was not written against, a TWD-reporting ADR fixture (TSM shape) behaves the same way.
- **Files:** yfinance_provider.py, models/fundamentals.py, types/data.ts. W2 and W3 render the change (C2).

**R15-DATA-004 (critical): Yahoo insider and institution holdings served as ownership fact**
- **Mechanism:** `yfinance_provider.py:398-399` passes `heldPercentInsiders` and `heldPercentInstitutions` straight through. The exchange witness (`ownership_check.get_exchange_ownership` plus the D68 conflict) is wired only into the research snapshot (`fast.py:352-394`). It never reaches `GET /fundamentals`, the EO, `company_narrative` or the screener.
- **Fix:**
  - In `routers/fundamentals.py`, for an Indian listing, await `ownership_check.get_exchange_ownership(fund.symbol)` (C4; it already never raises and respects its circuit).
  - Mark `held_percent_insiders` as `flagged` when it differs from the exchange `promoter_percent` by more than the existing 3pp band, or when one side is zero and the other is not.
  - Apply the same rule to `held_percent_institutions` against `institutions_percent`. The reason names the exchange figure and its quarter.
  - When the witness cannot run for an Indian listing, flag the field as "unreconciled: exchange shareholding unavailable (insiders ≠ promoter group)".
  - In `company_narrative._source_values` (`:177-178`), include `held_percent_*` only when their meta status is `ok`.
  - The EO chip and label (W2) and the screener labels and preset (W5) follow this contract.
- **Test:** `test_fundamentals.py`, with `get_exchange_ownership` stubbed:
  - DHANBANK: insiders 0.51176 against promoter `None` gives `flagged`.
  - JONJUA: 0.46623 against 29.67 gives `flagged`.
  - A within-band pair (0.7384 against 73.58) stays `ok`.
  - For a case the fix was not written against, the NAPEROL institutions leg (0 against 1.77) gives `flagged`.
  - `test_company_narrative.py`: a flagged insider figure is not a verifiable number.
- **Files:** routers/fundamentals.py, company_narrative.py, correctness_gate.py if the band helper lives there, tests.

**R15-DATA-005 (critical): share basis differs across fields in one payload**
- **Mechanism:** `bookValue`, `priceToBook`, `sharesOutstanding` and `marketCap` are independent passthroughs (`:365,369,372,394`). The gate's market-cap cross-check (`correctness_gate.py:264-280`) prices through `pe × eps`, so it cannot see loss-makers, and its 25% band misses gaps of 8 to 16%.
- **Fix:**
  - Carry the price the provider's ratios were computed at (Yahoo `currentPrice`/`regularMarketPrice` from the same `info`). W1 names the field in commit 1.
  - Add a cross-field pass in `_apply_plausibility_bounds`: compute implied shares as `market_cap / price` and compare with `shares_outstanding`, using a tight band (W1 picks it and documents it; about 5% is the order of magnitude).
  - On divergence, flag `shares_outstanding`, `book_value` and `price_to_book` (the per-share fields on the stale basis) and name both share counts.
  - Use the real price, not `pe × eps`, so loss-makers are covered. Keep `pe × eps` only as the fallback when no price is present.
- **Test:** `test_correctness_gate.py`:
  - VERTEX fixture (shares 74,012,189, market cap 484,039,744, price 3.27, BVPS 1.369, P/B 2.3886): the three fields are `flagged`.
  - For a case the fix was not written against, a loss-maker with `pe_ratio=None` and a stale share count is still flagged.
  - A consistent payload is untouched.
- **Files:** correctness_gate.py, yfinance_provider.py, models/fundamentals.py and types/data.ts (field in commit 1).

**R15-DATA-013 (high): EPS and P/E are stale Yahoo passthroughs**
- **Mechanism:** `eps = trailingEps` and `pe_ratio = trailingPE` (`:366,375`). The same payload's `net_income_ttm / shares_outstanding` gives a different EPS (DAL: 8.9 against 2.04). The gate only checks `pe × eps` against the 52-week band, and a stale pair passes that.
- **Fix:** in the same cross-field pass, compare `eps` with `net_income_ttm / shares_outstanding`. Beyond a small band, flag `eps` and `pe_ratio` and state the payload-implied EPS and the P/E it implies at the ratio price. Do not substitute (§6 D-B2-2).
- **Test:** DAL fixture gives `flagged` with 2.04 in the reason. For a case the fix was not written against, SMR (5.58 against 13.27) is also flagged. A consistent payload stays `ok`.
- **Files:** correctness_gate.py.

**R15-DATA-014 (high): `revenue_ttm` never checked against statements**
- **Mechanism:** `revenue_ttm = totalRevenue` verbatim (`:391`). Nothing compares it with the provider's own income statement or with the implied margin, and nothing labels a TTM built from a half-yearly reporting cadence.
- **Fix:**
  - In `routers/fundamentals.py`, after the gate, fetch the provider's annual income statement for the same listing (`provider_registry.get_income_statement`, called and never edited; W2 owns routing).
  - Flag `revenue_ttm` when it diverges from the latest annual "Total Revenue" beyond a stated band, or when `net_income_ttm / revenue_ttm` falls outside the provider's own `profit_margin` band.
  - When the statement shows fewer than four filed quarters, label the TTM basis in the reason ("annual, not trailing-4Q").
  - A statement failure attaches nothing: absence is honest and never breaks `/fundamentals`.
- **Test:** FUSION fixture (858cr against an annual 1,513cr) gives `flagged`. For a case the fix was not written against, DAL (2.76cr against 9.97cr) is also flagged. A statement-fetch error leaves `revenue_ttm` `ok`.
- **Files:** routers/fundamentals.py, correctness_gate.py (band helper), tests.

**R15-DATA-006 (critical): an 18-month-old print served as today's**
- **Mechanism:** `bse_provider._quote_from_header` (`:506-538`) ignores the header's own `Ason` trade date and stamps `timestamp = most_recent_session(IN)`. `change` is computed against `PrevClose`, which gives "+4.99% today". Because the date is fabricated at the provider, `locale.is_rejectably_stale` (`correctness_gate.py:110`) never sees the real age. If the gate did reject, the fall-through would reach `yfinance.get_quote`, which stamps `timestamp=_utcnow()` (`yfinance_provider.py:262`), the same fabrication again.
- **Fix:**
  - Parse `Ason` into `Quote.timestamp`. When the last trade date is before the most recent session, report `change`/`change_percent` as `0` and state the true last-trade date. The move belongs to that date, not to "today".
  - In `validate_quote`, an exchange-dated last trade (BSE header, NSE) is **served with its true date and labelled stale** by `routers/quotes._label_freshness`, not rejected into a lane that fabricates freshness.
  - `yfinance.get_quote` must stop claiming `now()`. Use the provider's own last-trade time when the snapshot carries one. Otherwise, follow the class rule: no provider stamps now() or today on a price whose trade date it does not know.
  - Stamp price-derived `field_meta.as_of` with the price's trade date where W1's ratio-price field carries it.
- **Test:** `test_bse_provider.py`: a DAL header fixture with `Ason='12 Mar 25 | 16:00'` gives timestamp 2025-03-12, `change == 0`, and quote freshness `stale` through the route. The class case the fix was not written against is DATA-070 below.
- **Files:** bse_provider.py, correctness_gate.py, yfinance_provider.py, routers/quotes.py.

**R15-DATA-070 (medium): undated news stamped now() and sorted first**
- **Mechanism:** `news_provider._parse_struct_time` and `_parse_iso` (`:149-170`) return `_utcnow()` for a missing or malformed date. `published_at` is required (`models/news.py:23`), and `:395` sorts newest first.
- **Fix:**
  - `published_at` becomes optional (C3). Leave it `None` when the date cannot be parsed.
  - Sort with nulls last.
  - `NewsFeedPanel.tsx:130` renders "date unknown".
- **Test:** `test_news.py`: an undated RSS item has `None` and sorts after dated items. `NewsFeedPanel.test.tsx` renders "date unknown".
- **Files:** news_provider.py, models/news.py, types/data.ts (commit 1), NewsFeedPanel.tsx.

**R15-DATA-033 (high): NaN passes the gate**
- **Mechanism:** `validate_quote` and `validate_series` guard with `x <= 0` (`correctness_gate.py:99,133`), which is False for NaN. OHLC values go through bare `float()` (`yfinance_provider.py:285-290`, `india_provider.py:146,195-199`), while the NaN-safe `_num` is used only for volume.
- **Fix:** guard with `not math.isfinite(x) or x <= 0`, and route OHLC through `_num`. Drop a bar whose close is `None`; never emit a NaN bar.
- **Test:** a NaN quote and a NaN last close each fall through to the next provider (registry stub). For a case the fix was not written against, an `india_provider` frame with a NaN OPEN cell yields no NaN in the served bars.
- **Files:** correctness_gate.py, yfinance_provider.py, india_provider.py.

### W2: `instrument-identity` (opus, 7 entries)

This writer owns the whole `wrong-entity-ticker-collision` class (001, 002, 003) and the ticker-string identity class (012, CODE-DATA-001), and pins each class on a case its fix was not written against.

**R15-DATA-012 (critical): the rename lane rewrites unrelated BSE-only tickers**
- **Mechanism:** `_rename_instrument` (`symbol_resolver.py:782-823`) applies `nse_symbol_change.lookup_current(inst.symbol)` to **any** Indian instrument whose ticker string matches an old NSE symbol, including BSE-only rows that NSE's `symbolchange.csv` does not govern. It then sets `exchange=NSE` and `yahoo_symbol=.NS` at confidence 1.0.
- **Fix:**
  - Gate the rewrite on identity. An NSE row always qualifies, because the lane governs NSE.
  - A BSE row is rewritten only when its ISIN equals the ISIN of the renamed-to NSE symbol. Never rewrite a BSE-only row whose ISIN is unknown.
  - Run the identity enrichment **before** the rename lane, so ISINs exist (`:673`).
- **Test:** `test_resolver_rename.py`, via `set_active_map_for_tests`:
  - NSDL (BSE-only) mapped to GUJENERGY is not rewritten.
  - SHREE, HSIL, WORTH and DTIL-shaped rows (ISINs differ) are not rewritten.
  - For a case the fix was not written against, a genuine dual-listed rename (same ISIN) is still rewritten and annotated.
- **Files:** symbol_resolver.py.

**R15-CODE-DATA-001 (high): one company's ISIN and BSE split stamped onto another**
- **Mechanism:** the rules disagree on what makes two rows the same instrument. `_residual_tie` treats the same bare ticker as the same instrument (`resolution_policy.py:92-107`). `_enrich_instrument` joins the NSE row to the BSE master by bare ticker (`symbol_resolver.py:840-879`), so NSE FOCUS carries Focus Business Solution's INE0DXR01010/543312. `corporate_disclosures._merge_bse_split` (`:509-545`) then merges scrip 543312's split into Focus Lighting's patterns.
- **Fix:**
  - Add one `same_instrument(a, b)` predicate in `resolution_policy.py`: ISIN when both carry one, otherwise `(symbol, exchange)`. Use it in `_residual_tie`, in the rename gate and in the candidate dedup.
  - The NSE row's own ISIN comes from the NSE-side sector map, never from the BSE master by ticker.
  - The NSE-to-BSE enrichment join refuses a BSE row whose ISIN (or, when ISINs are missing, whose name) disagrees.
  - `_merge_bse_split` merges only when the BSE scrip for `bare` is the same instrument as the NSE listing. Otherwise the split stays `None`.
  - Do not touch `bse_provider.py` (it is W1's). Guard at the join in `corporate_disclosures`.
- **Test:**
  - `resolve('FOCUS')` yields two instruments with distinct ISINs.
  - `get_shareholding('FOCUS')`: the NSE patterns carry `split_source is None` when the BSE scrip's ISIN differs.
  - For a case the fix was not written against, RELIANCE (same ISIN on both exchanges) still merges.
- **Files:** resolution_policy.py, symbol_resolver.py, corporate_disclosures.py.

**R15-DATA-018 (high): a renamed stock cannot be found by its old ticker**
- **Mechanism:** `_annotate_renamed_symbols` rewrites only what `_resolve_masters` already matched, and returns early when `best is None` (`:811-813`). A refreshed master no longer carries the retired symbol, so the lane can only fire while the master is stale. There is no reverse lookup, so the payload never says "formerly X".
- **Fix:**
  - When the masters find nothing, or bind below ACCEPT, consult `nse_symbol_change.lookup_current(query)` and re-resolve the `renamed_to` symbol with the rename annotation.
  - Apply the same step in `/resolve/autocomplete` (`routers/resolve.py:126`).
  - Add a reverse `lookup_former(symbol)` so the current instrument exposes `former_name`/former symbol.
- **Test:** with an injected map:
  - `resolve('zomato')` and `resolve('ZOMATO')` give ETERNAL, annotated.
  - Autocomplete for ZOMATO lists ETERNAL.
  - For a case the fix was not written against, `SEQUENT` gives VIYASH, and `resolve('VIYASH').former_name` is set.
- **Files:** symbol_resolver.py, nse_symbol_change.py, routers/resolve.py.

**R15-DATA-001 (critical): US statements served under Indian names**
- **Mechanism:**
  - openbb-mcp is declared at rank 10 with no region scope (`provider_registry.py:128-141`).
  - Its `_normalize_symbol` (`openbb_mcp_provider.py:260-262`) only swaps `.` for `-`, so bare `DAL` reaches OpenBB's yfinance backend and comes back as Delta, while `RELIANCE.NS` is mangled to `RELIANCE-NS`.
  - `get_income_statement`, `get_balance_sheet` and `get_cash_flow` run with `validate=None` (`:490-510`).
  - The all-null-shell guard ignores `name` (`:262-285`), so SUMAX serves a US fund's name.
- **Fix:**
  - Route openbb's symbol through `yfinance_provider._yahoo_symbol` (region-aware `.NS`/`.BO`, keeping exchange suffixes; C7). Echo that listing form as `symbol`.
  - Give the three statement accessors an identity validator (a registry closure: returned symbol against the requested listing form).
  - Count `name` as identity in `_FUNDAMENTALS_IDENTITY_FIELDS`.
- **Test:** `test_openbb_mcp_provider.py` and `test_provider_registry_region.py`:
  - In an IN session, a parametrised collision set (DAL, CHTR, SAFE, CSL, ICON, AMAL, SMR, TTC, SUMAX) sends the `.BO`/`.NS` form to the MCP tool (stubbed `_call_tool` captures the arguments).
  - `RELIANCE.NS` passes through unchanged.
  - A name-only shell is not served.
  - For a case the fix was not written against, the same bare `AMAL` in a **US** region reaches the tool as `AMAL`.
- **Files:** openbb_mcp_provider.py, provider_registry.py.

**R15-DATA-002 (critical): a cross-region ticker binds to the session region**
- **Mechanism:** the sidecar honours a per-call `X-Vysted-Region` header (`sidecar-client.ts:168-195`; per-call headers win). However, the EO's `selectCandidate` (`EquityOverviewPanel.tsx:771-775`) drops `candidate.region` and fans out on the bare symbol (`api.ts:101-120`). A typed bare ticker never consults `/resolve`. So NASDAQ:AMAL in an IN session loads Amal Ltd.
- **Fix:**
  - Carry the picked instrument's region through `selectCandidate`, `doLoad`, `loadEquityOverview(symbol, region?)` and every leg (quote, fundamentals, income, balance, cashflow, ratings, narrative) as a per-call `X-Vysted-Region`.
  - Add the optional `region` to `openCompanyOverview` and `equity-command.loadSymbol` (C6).
  - On a typed submit, query `/resolve/autocomplete`. When two or more exact-ticker candidates span regions, show them as a chooser instead of loading.
  - Also apply the C1 and C2 renders here: a `flagged` chip beside present values, money rows in `financial_currency ?? currency`, and the ownership labels "Insiders (Yahoo)" and "Institutions (Yahoo)".
- **Test:**
  - `EquityOverviewPanel.test.tsx`: an overview opened from the NASDAQ:AMAL candidate in an IN session sends `X-Vysted-Region: US` on every leg.
  - A typed `SMR` with a US and a BSE exact candidate shows the chooser and makes no fan-out.
  - For a case the fix was not written against, `openCompanyOverview('AMAL', undefined, 'US')` reaches the same header.
  - Separate tests: a flagged chip renders, and SIFY revenue renders as INR.
  - The sidecar half is covered by the DATA-001 US/IN cases.
- **Files:** EquityOverviewPanel.tsx, equity-overview/api.ts, sidecar-client.ts, host-actions.ts (`openCompanyOverview` only), store/equity-command.ts, tests.

**R15-DATA-003 (critical), R15-CODE-DATA-005 (medium): India-only lanes decided by bare-ticker membership**
- **Mechanism:** `ownership_check.is_applicable` (`:94-104`) decides by bare-ticker membership in the Indian masters. For a US-bound AMAL, `fast.py:352-355` passes `listing='AMAL'`, the BSE shareholding for Amal Ltd is fetched, and `semantics.py:560-575` presents it as the US company's. The same predicate is copied in `market_cap_witness.py:98-107` and `research/range_check.py:121-131`, with an NSE variant in `dividend_actions.py:63-72`. `_is_blocked` is copied in three modules. This duplication is CODE-DATA-005, and it is the reason a fix to one copy is not a fix.
- **Fix:**
  - Add a new `services/witness.py` with `is_india_listing(listing)` (C4: `.NS`/`.BO` on the resolved listing) and `is_block_error(exc)`.
  - Every witness imports these. Delete the local copies.
  - `dividend_actions` uses `is_india_listing and is_nse_symbol(bare)`.
  - `earnings_quality.is_applicable` is universal by design and stays as it is.
  - The `is_india_target` twin half of CODE-DATA-005 is done by W3 (C5).
- **Test:** `test_witness.py`:
  - A US-bound bare `AMAL` gives no exchange ownership (the research snapshot stub has no `ownership_exchange` and no conflict).
  - An identity check: each witness module's predicate **is** `witness.is_india_listing` or `witness.is_block_error`.
  - For a case the fix was not written against, `market_cap_witness` and `range_check` are not applicable to a bare `SMR`, and are applicable to `SMR.BO`.
  - Existing tests that encode the defect are fixed, with the reason logged in the commit body: `test_range_check.py:136` `is_applicable("BI")` becomes `"BI.NS"`, and any others like it.
- **Files:** witness.py, ownership_check.py, market_cap_witness.py, dividend_actions.py, research/range_check.py, tests.

### W3: `research-integrity` (opus, 9 entries)

**R15-RESEARCH-002 (critical), R15-RESEARCH-034 (low): LLM verdicts read by substring scan**
- **Mechanism:** `verify._parse_verdict` (`:102-116`) substring-scans the whole first line for agree or disagree markers. "UNVERIFIED - no source confirms…" matches `confirm` and becomes AGREE. `deep._reflect_says_complete` (`:308-323`) scans the whole reply, so "Price action is not covered yet" counts as complete.
- **Fix:** add one leading-token reader (strip `*:-`, exact-match the first word).
  - `_parse_verdict` checks UNVERIFIED, then DISAGREE, then AGREE, and falls back to the marker scan only when the first word is not a verdict token.
  - `_reflect_says_complete` reads a leading COMPLETE or GAPS token the same way.
- **Test:** `test_research_verify.py`: the three proven UNVERIFIED strings give `unverified`. For a case the fix was not written against, `test_research_deep.py`: "Price action is not covered yet" gives False, and "COMPLETE" gives True.
- **Files:** verify.py, deep.py.

**R15-RESEARCH-004 (high), R15-RESEARCH-015 (medium): ULTRA cross-check mangles figures and overcounts sources**
- **Mechanism (004):** `_extract_claims` (`verify.py:137-158`) reuses `deep._split_subquestions` (`deep.py:179-202`). Its list-marker stripping eats a leading `-` sign and the integer part of `40.5%`. The step label interpolates `len(checks)`.
- **Mechanism (015):** `verify.py:365` already folds the native citation domains into `domains`, and `:373` adds +1 for the same lane.
- **Fix:**
  - Give claims their own splitter. Strip `<digits>.`/`)` only when whitespace and a non-digit follow, and never strip a sign.
  - The step label reports verified, unverified and disagree counts separately.
  - Compute independence as `len(domains) + (1 if native_text and not native_rows else 0)`. "Corroborated across channels" requires the two lanes to rest on different domains.
- **Test:** `'40.5% revenue growth'`, `'-0.4% earnings growth'` and `'67.13953 P/E'` pass through unchanged. For a case the fix was not written against, `'1. 40.5% revenue growth'` becomes `'40.5% revenue growth'`. A claim whose one domain is reached by both lanes gives UNVERIFIED.
- **Files:** verify.py, deep.py.

**R15-RESEARCH-001 (critical): another company's news stated as the target's facts**
- **Mechanism:** `deep._record_structured` (`:376-393`) folds the whole news tool result (a region-wide blend, mostly `symbols: []`) into one "News for <SYM>" source. The R13 #9 relevance gate exists only in `fast._news_value` (`fast.py:476-498`).
- **Fix:**
  - Move the gate into one helper in `relevance.py`, used by both `fast._news_value` and the DEEP/ULTRA structured news leg.
  - Drop off-entity items, keeping the honest "no on-entity news" note.
  - Cite each kept item as its own source.
- **Test:** `test_research_deep.py`: a blended news result (one on-entity item and one off-entity `symbols:[]` item) through the deep structured path. The off-entity item never reaches the researcher context or `brief.sources`. For a case the fix was not written against, the same holds on the ULTRA (`iter`) path.
- **Files:** relevance.py, deep.py, fast.py, iter.py (if ULTRA folds news through its own site).

**R15-RESEARCH-003 (high), R15-RESEARCH-029 (medium), R15-RESEARCH-037 (low): `[n]` markers point at the wrong source**
- **Mechanism:**
  - `_Findings.all_sources()` (`deep.py:356-373`) re-ranks a growing list on every call.
  - `iter._numbered_sources` (`:127-129`) renumbers every round, while the report text keeps markers minted under the earlier numbering. In-range stale markers ship.
  - The merge prompt (`iter.py:1059-1080`) asks the model to "RENUMBER".
  - citecheck validates only numeric ranges, so model-written Sources/References lists and `[n] 1` literals pass through (029).
  - `finance.priority_note` (`:166-174`) reports indices of whatever list it is given (037). Once numbering is stable, it would point at the wrong `[n]` if it re-ranked.
- **Fix:**
  - Number sources append-only at first sight. Ranking affects only the priority hint, never the numbers.
  - `priority_note` takes the **same numbered list** the prompt carries and reports the tier of each actual number. This is the root-cause version of 037's fix; the register's "rank inside priority_note" would break stable numbering (§6 D-B2-7).
  - Remove the RENUMBER instruction.
  - citecheck strips model-authored Sources/References/Merged Sources sections and rewrites or strips `[n]`-literal markers. The rail is the only bibliography.
- **Test:** `test_research_iter.py`: in a two-round run, round 2 inserts primary-tier sources ahead of round 1's. The final brief's `[n]` still resolves to the round-1 URL, and `priority_note` names the primary source's real number for an unranked input. `test_research_citecheck.py`: Kaynes-shaped markdown leaves no References section and no `[n] k` text.
- **Files:** deep.py, iter.py, finance.py, citecheck.py. `brief-ingest.ts` changes only if a `[n]`-literal can still reach the client.

**R15-AGENT-001 (critical): chat narrates fraction values as percent**
- **Mechanism:** `semantics.py` labels fraction values `unit="percent"` (`:392, 569, 584, 889, 1032, 1039, 1068, 1077`). The panel's `formatDerived` (`brief-blocks.tsx:199-205`) multiplies them by 100, so the panel is right. The model reads the raw bundle, where dividend yield is 0.01417 labelled "percent", and says "0.0142%". Market cap reaches the model as a raw rupee float, and the model mis-scales it 10x.
- **Fix:**
  - Emit `unit: "fraction"` for every fraction value; the vocabulary becomes fraction, currency and ratio in `types/brief.ts:82`.
  - Add one Python formatter that emits a `display` string on each derived value the model reads: fraction as `"1.42%"`, INR money scaled to `"₹14,402 cr"`, other money scaled with its code.
  - `prompt_block` and the research tool payload carry `display`. `copilot.json` tells the model to quote `display` verbatim.
  - `formatDerived` handles `fraction`.
  - Apply the C2 render here: brief "Revenue" in `financial_currency ?? currency`.
  - C5: make `relevance.is_india_target` accept `None`, delete the copy in `research/disclosures.py:101-107` and import the shared one.
- **Test:** `test_research_semantics.py`: no derived value carries `unit == "percent"`. A KPIT fixture has dividend yield 0.01417 with display "1.42%" and market cap 144,021,815,296 INR with display "₹14,402 cr". For a case the fix was not written against, a COCHINSHIP growth of 0.024 displays "2.40%", and the payload a model reads contains the display strings. `brief-blocks.test.ts`: `fraction` renders ×100. `test_research_disclosures.py`: identity check that the twin is gone.
- **Files:** semantics.py, copilot.json, types/brief.ts, brief-blocks.tsx, relevance.py, research/disclosures.py.

### W4: `workspace-persistence` (opus, 7 entries)

**R15-CODE-FRONTEND-001 (critical), R15-LIFECYCLE-002 (high): the workspace blob mixes layout with user data**
- **Mechanism:**
  - One `SerializedWorkspace` blob mixes per-workspace state (layout, enabled modules, drawings, `researchSymbol`) with global user data (portfolios, watchlist, notes, settings, keybindings, research archive).
  - `deserializeWorkspace` (`workspace.ts:250-371`) restores both on every `loadWorkspace` (`:430`), and the `page.tsx` subscriptions then autosave the rollback (001).
  - The layout restore runs first and gates every other slice. The unknown-component skip in `restoreLastSessionOrDefault` (`:512-533`) returns before `deserializeWorkspace` runs, and a `fromJSON` throw aborts the rest. The default stores are then autosaved over the user's blob (002).
- **Fix:**
  - Split restore into `applyLayoutSlice` (always) and `applyGlobalSlice` (only on the boot restore of `__autosave__`). A named-workspace load applies the layout slice only.
  - Restore the non-layout slices first and independently, so a layout failure cannot discard them.
  - Strip unknown panel ids from the serialized layout and restore the rest. Move the guard inside restore so `loadWorkspace` gets it too.
  - `workspace_store` keeps one `.bak` on overwrite.
  - Fix the dialog copy (`WorkspaceDialog.tsx:82-84,228-230`) if it still overpromises.
- **Test:**
  - Save a named workspace, change portfolios and notes, then `loadWorkspace(named)`: portfolios and notes are unchanged.
  - For a case the fix was not written against, a blob with an unregistered `broker-connect` panel plus holdings, notes and watchlist restores every non-layout slice and issues no default-state POST.
- **Files:** workspace.ts, page.tsx, PanelHost.tsx, WorkspaceDialog.tsx, workspace_store.py, tests.

**R15-LIFECYCLE-003 (high), R15-CODE-FRONTEND-005 (high), R15-CODE-FRONTEND-018 (medium): autosave races the restore and misses slices**
- **Mechanism:**
  - Ten store subscriptions (`page.tsx:108-181`) call `autosaveLayout` (`workspace.ts:568`) from mount, with no restore gate, no debounce and no single flight. The restore-then-autosave ordering lives in a private timer in `PanelHost` (`:147,164-166`) and a false "debounced" comment (003).
  - Chart drawings, keybindings and research-space memory are serialized but have no trigger (005).
  - Saved screens are not in the blob at all (018; see `store/screener.ts:68`).
  - Adding a persisted slice needs four edits across three files, with three different trigger conventions.
- **Fix:**
  - One `PERSISTED_SLICES` registry in `workspace.ts` (`{key, read, restore, subscribe}`), iterated by `buildWorkspacePayload`, by restore and by a single trigger-wiring loop.
  - Delete `page.tsx:108-181` and the per-store persist helpers (`settings.ts:112-113`, `search-settings.ts:348`, `brief.ts:103`, `SettingsPanel.tsx:493,627`, and the OnboardingFlow trigger).
  - Add `savedScreens` as a slice.
  - Add a module flag `restoreSettled`, set in the `finally` of `restoreLastSessionOrDefault`, that makes autosave a no-op until then.
  - Put a trailing-edge debounce and single flight inside `autosaveLayout`.
  - Delete the private timer in `PanelHost`.
- **Test:**
  - The LC-003 repro inverted (from `r15/census/code/evidence/workspace-layout-repro.test.ts.txt`): zero POSTs during restore, and the first POST after restore carries `researchSymbol` and the research archive.
  - Every `SerializedWorkspace` key has a registered slice, and mutating each slice schedules an autosave.
  - For a case the fix was not written against, `savedScreens` survives serialize, a fresh store and deserialize.
- **Files:** workspace.ts, page.tsx, PanelHost.tsx, store/{chart-drawings,keybindings,research-spaces,settings,search-settings,brief,screener}.ts, SettingsPanel.tsx, OnboardingFlow.tsx.

**R15-CODE-FRONTEND-004 (high): research spaces can never be saved or loaded**
- **Mechanism:** the sidecar accepts only names matching `^[A-Za-z0-9 _-]+$` (`workspace_store.py:32,46`), while `researchSpaceName` always emits `"Research: X"` (`workspace.ts:587-591`). `createResearchSpace` (`:636`) clears and re-tiles the cockpit before the save returns 400, and the sidecar's error detail is discarded.
- **Fix:**
  - Stop rejecting names. The store maps any name to a safe filename by percent-encoding, and the list decodes it. Nothing can escape the workspace directory: `..`, `/`, `\` and NUL are all encoded.
  - `createResearchSpace` saves before it mutates the cockpit, or rolls back on failure, and surfaces the sidecar detail.
- **Test:** `test_workspace.py`: `Research: M&M`, `Research: RELIANCE.NS`, `My Layout (2)` and a Hindi name each round-trip through POST, GET, list and DELETE. For a case the fix was not written against, `../escape` stays inside the directory. Vitest: a failing save leaves the cockpit untouched.
- **Files:** workspace_store.py, routers/workspace.py, workspace.ts.

**R15-LIFECYCLE-009 (high): a v0.8.0 portfolio does not survive the upgrade**
- **Mechanism:** commit 12862d3 moved holdings into the blob with no import step. `deserializeWorkspace` keeps the empty seeded portfolio when the blob has no `portfolios` key (`workspace.ts:295-297`), while `GET /portfolio/positions` still holds the old rows.
- **Fix:** add a one-time import inside the global-slice restore. When the blob has no `portfolios` key and `/portfolio/positions` is non-empty, seed the default portfolio from those rows (symbol, quantity, cost_basis, asset_class, note) and mark the import in the blob so it is idempotent.
- **Test:** a stubbed positions response plus a blob with no portfolios: the holdings appear once. For a case the fix was not written against, a second restore adds no duplicates. A blob with `portfolios: []` does not import.
- **Files:** workspace.ts, modules/portfolio/api.ts, store/portfolios.ts.

### W5: `surfaces-and-math` (sonnet, 9 entries, each fully specified)

**R15-DATA-009 (critical): multi-symbol Sharpe understated by about sqrt(N)**
- **Mechanism:** `_run_single_slice` appends an equity point inside `for bar in bars` (`backtest_engine.py:313,391`), with bars sorted by `(timestamp, symbol)`. N symbols therefore produce N points per date, and `_compute_metrics` (`:251-267`) treats consecutive points as daily returns (`sqrt(252)`, `**252`).
- **Fix:** mark to market **once per timestamp**, after the last bar of that timestamp, so the curve has one point per date. The chart and the walk-forward slices inherit this. Check `agent_tools/backtest_summary.py` for any per-point assumption.
- **Test:** a seeded random walk over 200 dates for N = 1, 2 and 4 with buy-and-hold. The Sharpe equals the date-sampled Sharpe for every N, and the curve length equals the number of dates.
- **Files:** backtest_engine.py, test_backtest_engine.py.

**R15-DATA-010 (critical): the Sortino ratio uses the wrong denominator**
- **Mechanism:** `downside_stdev = pstdev([r for r in returns if r < 0])` (`:259-260`) measures the dispersion among losses, not the deviation below zero.
- **Fix:** `downside_dev = sqrt(sum(min(r,0)**2 for r in returns) / len(returns))`, keeping the `> 0` guard.
- **Test:** returns `[+0.02]*10 + [-0.05, -0.051]` give Sortino 6.35 (±0.01). For a case the fix was not written against, two identical losses give a non-zero Sortino.
- **Files:** backtest_engine.py.

**R15-DATA-011 (critical): binomial theta sign flipped and gamma off**
- **Mechanism:** in `_greeks_fd` (`options.py:121-167`), `theta = -(price_fwd - price_base) * 365`, which negates a decay that is already negative. Gamma is a second difference of CRR NPVs with a 1%-of-spot bump, which straddles lattice nodes and gives 1.4 to 5.6x Black-Scholes, or 0 at odd step counts.
- **Fix:** take delta, gamma and theta from the lattice (`option.delta()`, `.gamma()`, `.theta()` on the `BinomialVanillaEngine` option). Keep finite differences only for vega and rho. I verified that QuantLib returns these for European and American options: gamma 0.018842 and 0.018797 at 200 and 201 steps against 0.018762 for Black-Scholes, and theta -39.81 against -39.68.
- **Test:** an ATM long call has binomial `theta < 0`. `|gamma_bin/gamma_BS - 1| < 0.05` at 200 and at 201 steps. For a case the fix was not written against, an American put's theta is negative and its gamma is within 5% of the European value at 200 steps.
- **Files:** quant/options.py, test_quant_options.py.

**R15-DATA-031 (high): earnings and analyst panels drop the currency**
- **Mechanism:** no production file under `src/modules/earnings` or `analyst-ratings` reads `currency`, although `types/earnings.ts` and `types/analyst.ts` carry it. `fmt`, `eps` and `formatPrice` drop it (`EarningsCalendarPanel.tsx:34-37,360-365`, `EpsEstimateGrid.tsx:25-31`, `IndividualAnalystTable.tsx:69`), `EarningsSurpriseChart.tsx:83` hard-codes `EPS $`, and the Consensus sort compares USD with INR by raw magnitude.
- **Fix:**
  - Thread each row's `currency` through `formatMoney`.
  - Take the chart's unit label from the data's currency.
  - When the visible rows span currencies, sort money columns by `(currency, value)`.
- **Test:** a mixed AAPL (USD) and RELIANCE.NS (INR) fixture: the cells carry currency affixes, and sorting never interleaves currencies. For a case the fix was not written against, the price-target line labels its unit.
- **Files:** the five panel files and their tests.

**R15-DATA-042 (high), R15-CODE-PLATFORM-053 (low): cross-currency weight and concentration**
- **Mechanism:** `metrics.ts:142-150` computes `weight = marketValue / totalMarketValue` and `concentration = max(weight)` across currencies. The D57 rule lives only in the panel (`PortfolioPanel.tsx:400-411,756-777`). `handleExport` (`:470-497`) writes that weight unconditionally and has no Currency column.
- **Fix:**
  - Put the rule in the contract: `weight` and `concentration` are `null` when `mixedCurrencies`.
  - The CSV gets a Currency column (`quote.currency`), and Weight % is blank when the weight is null.
  - The panel reads the null values.
- **Test:** `metrics.test.ts`: a mixed portfolio has weight and concentration null. For a case the fix was not written against, `PortfolioPanel.test.tsx` exports RELIANCE and AAPL with a Currency column and empty Weight %.
- **Files:** metrics.ts, PortfolioPanel.tsx and their tests.

**R15-DATA-043 (high): the screener ranks INR against USD as one number**
- **Mechanism:** `apply_criteria` sorts on raw `market_cap` (`screener.py:396-398`), and the table comparator does `av - bv` (`ScreenerResultsTable.tsx:300-312`), both ignoring `row.currency`. Criterion inputs show no unit. Only the engine docstring (`screener.py:41-43`) says values are in the listing currency.
- **Fix:** no FX layer exists, and this batch adds none (§6 D-B2-4).
  - The sidecar orders a result set that spans currencies by `(currency group, market_cap desc)` and states it in the response's human `coverage` line. Add a field only if none fits, and then mirror it in `types/screener.ts`.
  - The table sorts money columns within currency groups.
  - The criteria builder suffixes money inputs with the universe currency: `india-*` gives INR, `sp500` gives USD, and `custom` gives "listing currency".
  - Also apply DATA-004's labels: `CriterionGroupEditor.tsx:51-52` and `ScreenerCriteriaBuilder.tsx:57-58` become "Insider holding (Yahoo)". The `promoter` preset (`ScreenerPresets.tsx:107-113`) keeps its id, and its name and description become "High insider holding (Yahoo)…". No exchange-promoter field is added (§6 D-B2-8).
- **Test:** `test_screener.py`: a custom `[AAPL, RELIANCE.NS]` universe does not rank RELIANCE above AAPL as one number, and the note is present. Vitest: the grouped sort, and the INR suffix on india-all. For a case the fix was not written against, the price column follows the same grouping.
- **Files:** screener.py, the four screener components and their tests.

**R15-DATA-100 (low): the Bond Pricer hard-codes '$'**
- **Mechanism:** `BondPricerPanel.tsx:301,323,326` hard-code `$`. The pricing arithmetic does not depend on currency.
- **Fix:** add a display-currency select to the form, defaulting to the session region's currency, and format with `formatMoney`. Nothing changes in the request, `models/quant.py` or `types` (§6 D-B2-5).
- **Test:** `BondPricerPanel.test.tsx`: in region IN, prices render with ₹.
- **Files:** BondPricerPanel.tsx and its test.

**R15-DATA-007 (critical): SEC filing detail fabricates identity**
- **Mechanism:** `get_filing` (`sec_filings_provider.py:507-560`) sections with a hard-coded `form_type "10-K"` (`:528`) and then looks for metadata in only the last 40 filings (`:536`). On a miss it builds a synthetic `Filing(form_type="10-K", filed_date=today, company_name="")` and caches it for 24 hours. `edgar_url` takes the ticker in place of the CIK.
- **Fix:**
  - Resolve the metadata **first**.
  - Section with the real `form_type`.
  - Build `edgar_url` from the payload's CIK.
  - Delete the synthetic branch. A miss raises `ProviderError("filing metadata unavailable for <accession>", kind="not_found")`, is not cached, and the route maps it to 404.
- **Test:** an accession outside the list window raises `not_found`, and nothing is cached. For a case the fix was not written against, a 10-Q inside the window is sectioned with `form_type "10-Q"` and its `edgar_url` contains the numeric CIK.
- **Files:** sec_filings_provider.py, routers/sec_filings.py and their tests.

---

## 3. Integrator run order and gates

1. Work in a **scratch worktree** (`git worktree add <scratchpad>/b2-int 004-r4-experience-rebuild`), never in the main repo (rule L21). Run `git branch --show-current` before every merge.
2. Audit each branch through `origin/worktree-agent-b2-<w>`. Check `git merge-base --is-ancestor 369faa7 origin/<branch>`; a stale base means re-dispatch.
3. Merge with `--no-ff` in this order: **W1** (type contract first), **W2**, **W3**, **W5**, **W4**. No file conflicts are expected, because the sets are disjoint. The cherry-picked W1 contract commit on W2 and W3 merges as an identical hunk.
4. Run the gates only after all five are merged, because W2's and W3's frontend tests need W1's types:
   - `export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH`
   - `ruff format --check sidecar && ruff check sidecar`
   - `pnpm format:check`
   - `pnpm ci-local`, in the background with the exit code recorded
   - `node scripts/smoke-test-sidecars.mjs`
5. Grep checks:
   - No `unit="percent"` remains in `semantics.py`.
   - No `form_type="10-K"` literal remains in `get_filing`.
   - No copies of `is_applicable` or `_is_blocked` remain outside `witness.py`, except the universal `earnings_quality.is_applicable`.
   - No `autosaveLayout()` calls remain in `page.tsx`.
6. Record the §6 decisions in `docs/redesign/DECISIONS.md` and `CHANGELOG.md` at merge. Writers do not edit docs.

---

## 4. Deferred to the next batch (file collision or capacity)

| Entry (+ its root-cause mates) | Why not now |
|---|---|
| R15-RESEARCH-009 + R15-AGENT-012 (the same research-metering root) | Threads usage through `deep/iter/verify/citecheck.py`, which W3 owns this batch; W3 is at capacity |
| R15-RESEARCH-006 | Its `verify.py` claim-loop budget collides with W3 |
| R15-RESEARCH-011 + R15-RESEARCH-013 + R15-RESEARCH-041 (provenance-label class) | The class spans `ownership_check.py` (W2), `fast.py` (W3) and `host-actions.ts` (W2), so it cannot be split cleanly |
| R15-DATA-021 | `_merge_bse_split` distance bound; W2 changes the same function for CODE-DATA-001. Do it next on top of that change |
| R15-DATA-015 + R15-DATA-016 (52-week range class) | Collides with `yfinance_provider.py` (W1) and `research/range_check.py` (W2) |
| R15-DATA-038, R15-DATA-039 | `sec_filings_provider.py` belongs to W5 this batch |
| R15-UI-004 + R15-UI-005 (unknown rendered as a value) | `PortfolioPanel.tsx` and `metrics.ts` belong to W5 |
| R15-UI-009 (+R15-UI-025) | `PortfolioPanel.tsx` export path belongs to W5 |
| R15-DATA-047 (+R15-DATA-049) | Collides with the EO (W2) and `yfinance_provider` / `routers/fundamentals` (W1) |
| R15-DATA-034 (+R15-DATA-082), R15-DATA-027, R15-DATA-035, R15-DATA-036, R15-DATA-022 | Collide with `correctness_gate`, `yfinance_provider` and `bse_provider` (W1) and `provider_registry` and `corporate_disclosures` (W2) |
| R15-DATA-017, R15-LIFECYCLE-005, R15-DATA-019, R15-DATA-020 | Collide with `symbol_resolver`, `openbb_mcp_provider` and `corporate_disclosures` (W2) |
| R15-DATA-029 (+R15-DATA-093), R15-UI-090 | Collide with `news_provider` and `routers/quotes` (W1) and the EO (W2) |
| R15-DATA-040, R15-DATA-044, R15-DATA-110, R15-UI-006, R15-UI-007 | Collide with `backtest_engine`, `screener.py` and the screener components (W5) |
| R15-UI-001, R15-CODE-FRONTEND-003 (+014), R15-AGENT-022 (+054), R15-AGENT-024 | Collide with `host-actions.ts` (W2) |
| R15-CODE-FRONTEND-002, R15-AGENT-020 | Collide with `research-spaces.ts` (W4) |

The agent-runtime highs have no file collision here but should go together as one agent-runtime batch next: R15-AGENT-003, AGENT-080, AGENT-019, AGENT-002, AGENT-021, AGENT-008 and AGENT-005.

---

## 5. Label-mates not taken (different root cause, so not the same class)

| Selected | Label-mate | Different mechanism |
|---|---|---|
| RESEARCH-037 (`unguarded-hand-list`) | R15-RESEARCH-036 | `_PROMPT_KEYS` has no drift test. 037 joins through RESEARCH-003's numbering, not through the label |
| CODE-DATA-005 (`duplicated-predicate`) | R15-CODE-DATA-009, R15-CODE-DATA-021 | 009 is Yahoo rate-limit classification across five modules; 021 is `compute_range` building its window twice |
| CODE-PLATFORM-053 (`invariant-held-by-comment`) | R15-CODE-AGENT-027, R15-CODE-PLATFORM-050, R15-RELEASE-009 | 027 is agent_tools test registration; 050 is metrics rows re-joined by index; 009 is the smoke-test MCP budget |
| LIFECYCLE-009 (`upgrade-data-orphaned`) | R15-LIFECYCLE-025 | A renamed agent tool id with no alias; a different store and a different fix |

---

## 6. Tier-3 decisions (the integrator records them; none is Tier-4)

- **D-B2-1:** `FieldMeta.status` gains `flagged`, and the existing soft flags (`ok` plus a reason) migrate to it (C1).
- **D-B2-2:** unreconciled Yahoo scalars (ownership, share basis, EPS/P/E, revenue) are **flagged with the witness figure, never substituted**. This follows D56, D66 and D68 and overrides the register's optional "derived substitution".
- **D-B2-3:** statement sizes carry `financial_currency`. There is no FX conversion, and Yahoo ratios that mix the two bases are withheld.
- **D-B2-4:** the screener ranks within currency groups and labels threshold units. No FX layer is added.
- **D-B2-5:** the Bond Pricer display currency is frontend-only. The pricing request stays currency-free.
- **D-B2-6:** India-only witnesses apply by the resolved listing's `.NS`/`.BO`, never by bare-ticker membership. Tests that encoded bare-ticker membership are corrected, with the reason logged.
- **D-B2-7:** RESEARCH-037 is fixed by computing `priority_note` over the exact numbered list. The register's "rank inside `priority_note`" would break the stable numbering that RESEARCH-003 needs.
- **D-B2-8:** the DATA-004 screener preset is relabelled, not re-pointed at an exchange promoter field. That field does not exist in the screener rows, and building it is a feature, not this fix.
- **D-B2-9:** workspace names are percent-encoded to filenames instead of rejected, and the encoding never lets a name escape the directory.

## 7. Writer ground rules

1. Work in your own isolated worktree and branch (`worktree-agent-b2-<w1..w5>`). Reset to base first, and push after each concrete deliverable.
2. Make one focused commit per entry (or per root-cause pair), as a conventional commit with no emojis, ending with the session's attribution trailer.
3. Tests go only where the repo keeps them: `sidecar/tests`, `src/**/*.test.ts(x)`. Write one focused test per pinned behaviour. Never delete, skip or weaken a test. If a test encodes the defect, fix it and give the reason in the commit body.
4. Before every Python commit, run `ruff format <files> && ruff check sidecar`. Before every TypeScript push, run `pnpm format:check`, `pnpm typecheck` and your vitest files.
5. Do not refactor beyond the entry, and add no flags or defensive code for cases that cannot happen. Anything odd you notice outside your entries goes into your final report's `issues[]`, not into the diff.
6. Never re-add trading, and never touch the Tier-1 files. Read no `R15_BRIEF*.md` and nothing under `r15/local/`.
