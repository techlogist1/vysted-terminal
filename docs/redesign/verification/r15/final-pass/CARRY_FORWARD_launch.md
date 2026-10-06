# Final-pass carry-forward to r15-launch (d38b5d1a -> 1fddb2b1)

Judge: carry-forward judge, judgement tier, model `claude-opus-5-5` (Opus 5.5), medium effort. Read-only. No advisor consulted. No GUI, app launch, network, build or test run.

Range: the final pass ran at `d38b5d1a`. The release head is `1fddb2b1` (tag r15-rc2). `d38b5d1a` is an ancestor of `1fddb2b1`. `git diff d38b5d1a 1fddb2b1 -- . ':(exclude)docs'` touches 62 code files: 39 non-test files plus 23 test files. `b796f6a9` and `1fddb2b1` have an empty code diff.

Method: each PASSING observation the final pass made is traced to the functions it exercised. The sources are:
- drive rows marked ok or holds;
- battery `holds` and `ci_pinned` rows;
- reproof/;
- scenarios that passed or held;
- DOCS_VS_REALITY PASS sections.

Findings, needs_gui rows and blocked_env rows are out of scope.

A changed hunk forces a re-run only when it lies on the exercised function and can change what was observed. Hunks that provably preserve behaviour do not force a re-run: an unrelated function in the same file, an additive branch the observation never enters, or the same connect sequence for a healthy DB.

### Evidence that counts as a re-run already done

**At the release head's code.** `stage-c/rc2-failsafe/VERIFY.md` ran at `b796f6a9`, whose code is identical to `1fddb2b1`:
- ci-local: vitest 2048, pytest 4013, cargo 32;
- smoke: 13 agents, toolCount 39;
- Gate 8: 8 passed;
- the 24-entry pin table: 579 passed;
- live checks: LEAD-127 (Halliburton), HAL.NS P/E rebase, VOLERCAR, LEAD-137, LEAD-141 and the Titan brief.

**Earlier shas whose path code is byte-identical to the head.** These are cited only where every file on the observed path is byte-identical; the lead may downgrade them to re-run.
- `fix-r1/VERDICTS.md` at `cac9d206`. `git diff --name-only cac9d206 1fddb2b1` (non-test) lists only:
  - quotes.py;
  - agent_tools/{catalog, deep_research, fundamentals, price_data}.py;
  - correctness_gate.py;
  - exchange_financials.py;
  - nse_provider.py;
  - provider_registry.py;
  - research/{fast, iter, relevance}.py;
  - english_words.txt.gz.

  Every frontend file is identical, and so are symbol_resolver, news_provider, earnings_provider, schema_version, every store, workspace_store, data_cache, main.py and routers/fundamentals.py.
- `rc2-round2/VERIFY.md` at `7f273b03`. After that sha only correctness_gate, exchange_financials, relevance and nse_provider change. The nse_provider change is additive only: `get_issued_size` and `_GET_QUOTE_API_PATH`. The `/quotes` batch path is therefore byte-identical.

**Amended pins.** A ci_pinned row whose pin test was edited in range counts only if the amended pin still asserts the original property. The edits in range are:
- symbol qualification (`TCS` -> `TCS.NS`) in host-actions, workspace and metrics tests;
- mock-shape updates in PortfolioPanel.test.tsx;
- AGENT-091 in context-provider.test.ts, where FINAL-007 changed the currency semantics and the pin still asserts a currency field on both paths;
- `test_fundamentals.py` dropping the NAPEROL zero-mismatch case (FINAL-024);
- `test_schema_version.py` dropping "first boot: nothing to back up" (LIFECYCLE-024).

## Verdicts

| observation group | verdict | hunks cited | reason (40 words or fewer) |
|---|---|---|---|
| REGRESSION.md: ci-local (vitest 2032, pytest 3921) and smoke at d38b5d1a | re-run-already-done-by rc2-failsafe/VERIFY.md | all 62 files | ci-local, smoke and Gate 8 green at b796f6a9, code-identical to 1fddb2b1. |
| composer-chat: controls, stop (AGENT-002), delegate rail and budget, error rows | carries | runs_store `_connect` -> `schema_version.open_migrated` | agent_runtime, run_manager, budget_guard and the chat UI have no hunk. `open_migrated` keeps the connect, row_factory and migrate order for a healthy DB. |
| composer-chat: ASK staging of data writes | carries | host-actions.ts `parseCustomPanels`, custom arrange in `applyIntent`, `write_note` `rawScope`, `applyIntentAsync` | proposed-changes, AUTO_APPLIED_KINDS and the portfolio intents have no hunk. The changed branches are arrange and note scope only. |
| composer-chat: context-provider portfolio snapshots | re-run-already-done-by rc2-failsafe/VERIFY.md (ci-local context-provider.test.ts) | context-provider.ts `extractHoldings`, `portfolioFromStore` (`listingCurrency`) | FINAL-007 changed the semantics. The amended pins are green at b796f6a9. The fix-r1 FINAL-007 jsdom replay ran on a byte-identical frontend. |
| failure-inducer: 401, no-key, network and junk-provider frames; sidecar killed mid-stream; SearXNG status | carries | none on path | The LLM adapters, agent_runtime and search routes have no hunk. |
| failure-inducer: malformed symbols on 9 routes (81 GETs: 57×200, 24×404) | **re-run** | routers/fundamentals.py `get_fundamentals` (ProviderError -> `provider_registry.get_fundamentals_from_filings`); provider_registry `get_fundamentals` (authored not_found), `_with_empty_reason`; symbol_resolver `autocomplete` | A not_found for a known NSE/BSE listing now walks the NSE filings. Statuses and bodies of /fundamentals, statements and autocomplete can change. No replay at the head. |
| failure-inducer: corrupt workspace quarantined | carries | workspace_store `delete_workspace` | The load and quarantine path has no hunk. |
| failure-inducer: corrupt stores (portfolio.db 500 absorbed by fetchLegacyPositions; others booted) | re-run-already-done-by fix-r1/VERDICTS.md FINAL-008 (byte-identical) | schema_version `open_migrated`, `_quarantine`; every store's `_connect` | Corrupt stores are now quarantined by design. fix-r1 drove the corrupt-header and truncate matrices on source and binary: every route returned 200. schema_version and the stores are identical cac9d206->head. |
| failure-inducer: netdown on 30 data routes; batch /quotes drops AAPL | re-run-already-done-by rc2-failsafe/VERIFY.md (FINAL-006 pins) | quotes.py `_on_batch_pool`, `_batch_member_quote`; nse_provider `_Throttle.wait`, `_wait_bulk` | The skip-on-failure loop in `get_quotes` has no hunk. The bulk lane only reorders NSE slots, sleeping outside the lock. |
| onboarding: rows 1-22 (clean-boot GETs, /portfolio/positions `[]`, first-run shell) | carries (boot also re-proved by the rc2-failsafe smoke) | data_cache `ensure_build` (`_holds_user_data`), `_connect` -> `open_migrated` | A clean profile holds no user data, so no backup is taken. fix-r1 LIFECYCLE-024 confirmed no backup on a clean profile (pm3). |
| onboarding row 23: IN cockpit quotes, 4 NSE names via batch | re-run-already-done-by rc2-failsafe/VERIFY.md (FINAL-006 pins) + rc2-round2/VERIFY.md live | quotes.py `_batch_member_quote`; nse_provider `_Throttle` | Same values; only pacing changed. Round 2 measured the 100-name batch and singles under 1.75 s on a byte-identical quote path. |
| onboarding row 24: fundamentals RELIANCE.NS (IN gate) | re-run-already-done-by rc2-failsafe/VERIFY.md | correctness_gate `_rebase_pe_on_filed_eps`, `overlay_filed_periods`, `apply_witnesses`; exchange_financials `trailing`/`_chain` | The main-board P/E is now rebased. Fail-safe live HAL.NS was grounded against screener.in, plus the FINAL-003, DATA-013 and DATA-014 pins. |
| onboarding row 25: ZOMATO -> ETERNAL plus autocomplete | re-run-already-done-by rc2-failsafe/VERIFY.md (ci-local test_resolver_rename `test_autocomplete_lists_the_current_symbol_for_a_retired_ticker`) | symbol_resolver `autocomplete`, `_same_company_key` | The pin runs over the bundled masters, the live data source. fix-r1 FINAL-011 probed autocomplete on a byte-identical resolver. |
| panels-layouts: 299-request HTTP census | **re-run** | the hunks in the malformed-symbols row, plus news_provider `_clean`, earnings_provider `_revenue_currency`/`_optional`, quotes batch | The census bodies come from changed handlers. No census exists at the head. |
| panels-layouts: watchlist 25-name batch | re-run-already-done-by rc2-failsafe/VERIFY.md (FINAL-006 pins) + rc2-round2 live | quotes.py, nse_provider `_Throttle` | Same as onboarding row 23. |
| panels-layouts: news BDL relevance | re-run-already-done-by rc2-failsafe/VERIFY.md (RESEARCH-001 pin; live ACE off-entity note) | relevance `_entity_signals`, `_lowercase_word_use`, `_word_used_as_name`; news_provider `_clean` | `gate_news` changed. Re-proved in-process and live at the head's code. |
| panels-layouts: Equity Overview for RELIANCE, KAYNES and AAPL | re-run-already-done-by rc2-failsafe/VERIFY.md | gate hunks; EquityOverviewPanel `StatementTable` (empty-periods branch) | Non-empty statements render unchanged. IN figures were re-proved (HAL.NS; DATA-001/013/014, FINAL-003 pins). |
| panels-layouts: earnings WIT USD/INR split | re-run-already-done-by fix-r1/VERDICTS.md FINAL-010 (byte-identical) + rc2-failsafe ci-local | earnings_provider `_revenue_currency` | fix-r1 found WIT and INFY in INR and SIFY null live. earnings_provider is identical cac9d206->head. |
| panels-layouts: SEC, analyst ratings, macro, options, yield, backtest, node editor | carries | SecFilingsPanel snapshot payload adds `symbol` (LEAD-077) | The panels' fetch and render paths have no hunk. The SEC hunk only adds a context-bus field. |
| panels-layouts: layout templates, agent arrange labels (AGENT-078), custom arrange | re-run-already-done-by rc2-failsafe/VERIFY.md (ci-local host-actions.test.ts, layout-templates.test.ts) + fix-r1 FINAL-016 | host-actions `parseCustomPanels`, `applyIntent`; layout-templates `applyCustomLayout` -> `{placed, unresolved}` | The template path is unchanged. The custom-arrange label is unchanged when every token resolves. |
| panels-layouts: workspace save, load, corrupt and `.bak` round trip | re-run-already-done-by fix-r1/VERDICTS.md FINAL-031 (byte-identical) + rc2-failsafe ci-local test_workspace | workspace_store `delete_workspace` (`.bak` unlink, `missing_ok`); workspace.ts portfolios restore `setAll(..., region)` | DELETE still returns 204, and a later corrupt file never restores deleted content. |
| portfolio-notes P1 (empty), P4/P4c (delete, edit, header) | carries | PortfolioPanel quote hunks; portfolios `updateHolding` keeps the target's region | The empty portfolio sends 0 requests. The delete, confirm, switch and header handlers have no hunk. |
| portfolio-notes P2 (validation: blank cost, 1e20, "1,000") | re-run-already-done-by rc2-failsafe/VERIFY.md (ci-local portfolios.test.ts) + fix-r1 FINAL-033 | portfolios `validateHolding` (`PLAIN_DECIMAL`, `fieldNumber`) | Every refused input is still refused. The 1e20 message may now be the plain-number error rather than "too large". |
| portfolio-notes P3 (INR math), P6 (mixed currency + CSV), P7 (transport failure + Retry); scenario UI-2 | re-run-already-done-by rc2-failsafe/VERIFY.md (PortfolioPanel.quotes.test.tsx; PortfolioPanel.test.tsx UI-004, DATA-042) + fix-r1 FINAL-001/017 | api.ts `fetchPositionQuotes` (batch, region groups, 120 s); PortfolioPanel backoff, `missingQuotes` | fix-r1 replayed the real panel against a live sidecar on a byte-identical frontend. The later quotes.py delta only sets the bulk lane. |
| portfolio-notes P5b: crypto BTC/USDT | **re-run** | api.ts `fetchPositionQuotes`: crypto now goes through batch `GET /quotes?asset_class=crypto` | No live crypto quote has gone through the new batch path at any later sha. Only the mocked pin PortfolioPanel.test.tsx:342 exists. |
| portfolio-notes P9 (agent host actions), P9b (panel-open currency) | re-run-already-done-by rc2-failsafe/VERIFY.md (host-actions.test.ts AGENT-042/DATA-088; context-provider.test.ts) + fix-r1 FINAL-007 | portfolios `addHolding`/`normalizeHolding` region; context-provider `listingCurrency` | Refusals and position-id targeting are unchanged. The currency now follows the listing. |
| portfolio-notes: sidecar positions routes, legacy import | carries | portfolio_db `_connect` -> `open_migrated` | The healthy-DB path is identical. The routes have no hunk. |
| portfolio-notes: notes N1-N6, T1-T1c, agent write_note N2 | carries | host-actions `applyIntentAsync` -> `writeResolvedNote` | N2 used global/general scopes (`noteScope` -> "", branch skipped) and TCS (matches `TICKER_SHAPED`), so it never reaches `writeResolvedNote`. |
| research-briefs: DEEP Coforge and ULTRA Data Patterns evidence and IN figures | re-run-already-done-by rc2-failsafe/VERIFY.md (relevance pins; live FAST briefs; HAL.NS) | relevance; fast `snapshot_structured`; iter/deep_research `listing_region=target.region`; gate | For an IN target in an IN session, `listing_region` equals the session region (identity). Relevance and IN figures are re-proved at the head's code. |
| research-briefs: verify "0 verified, 5 unverified"; tiering | carries | verify `_parse_verdict` (`_EMPHASIS_EDGE_RE`) | Identical on input without edge emphasis. The test_research_verify pins are green at b796f6a9. |
| research-briefs: citation markers, auto-publish acks, kept_previous, banner, chips, rate-limited note, search status, stop, bad key | carries | none on path | The citation, publish and host-ack code have no hunk. |
| screener: all 27 ok rows (universes, runs, jsdom panel, agent recipe, llama turn) | carries | provider_registry `get_fundamentals` (authored not_found keeps `kind`); fundamentals_store `_connect` -> `open_migrated` | screener `_fetch_pair` goes through `validate_fundamentals` (no hunk), not `apply_witnesses`. not_found still maps to the "not_found" skip. |
| settings-plugins: all ok rows | carries | plugins_store `_connect` -> `open_migrated` | The healthy-DB path is identical. Nothing else on path. |
| scenarios AC-2, AC-3, AC-4, AC-6 (write gate, read surface, durable runs, custom-agent ids) | carries | catalog `_LISTING_REGION` (optional schema property) | The gate, `_NO_TOOL_CUE`, BudgetGuard, run_manager and KNOWN_TOOL_IDS have no hunk. Tool counts are unchanged. |
| scenario AC-5 (MCP toolCount, dict returns, Origin) | re-run-already-done-by rc2-failsafe/VERIFY.md (smoke toolCount 39) | catalog schema; agent_tools `in_region` wrappers | The wrappers return the same dict. The Origin guard has no hunk. |
| scenario DS-1 (US/IN collisions) | re-run-already-done-by rc2-failsafe/VERIFY.md | gate, statements `_with_empty_reason`, LEAD-127 region threading | The DATA-001/013/014 and LEAD-127 pins, and live Halliburton vs HAL.NS, all at the head's code. |
| scenario DS-2 (YASHOPTICS, SUNRAJDI, KARAMTARA) | re-run-already-done-by rc2-failsafe/VERIFY.md | gate `overlay_filed_periods`, `fill_market_cap_from_master`; provider_registry filings fallback | FINAL-003 and FINAL-005 pins plus live VOLERCAR and HAL.NS at the head's code. |
| scenario DS-3 (ADRs) | re-run-already-done-by fix-r1/VERDICTS.md FINAL-010 (WIT); SIFY carries | earnings_provider `_revenue_currency`; gate `_rebase_pe_on_filed_eps` (IN listings only) | SIFY's withheld P/S and P/B ride US-listing paths with no hunk. The WIT currency was re-proved on byte-identical code. The brief-prose half is in the LLM row. |
| scenarios DS-4 and xadv-realuser-1..5, 7 (renames, namesakes, collisions, demergers) | re-run-already-done-by rc2-failsafe/VERIFY.md (resolver pins) + fix-r1 FINAL-002/011 | symbol_resolver `_bse_row_is_same_company` -> `_same_company_key`, `autocomplete` | fix-r1's master sweep flipped only GSTL among 2471 NSE/BSE pairs on a byte-identical resolver. The pins run over the bundled masters. |
| scenarios DS-5, free-investor-1, UI-4 (screener) | carries | as in the screener row | as in the screener row. |
| scenario DS-6 (symbol forms across lanes) | carries | quotes.py bulk lane; news_provider `_clean` | Non-NSE batch members never touch the NSE throttle. Unescaping changes no pass property. |
| scenario DS-7 (ownership reconciliation) | re-run-already-done-by rc2-failsafe/VERIFY.md (FINAL-024 pins) | correctness_gate `reconcile_ownership` (zero-mismatch rule removed) | The within-3pp and beyond-3pp outcomes ride the unchanged 3pp rule. |
| scenarios G8-1..G8-5; reproof gate8 and SAFETY_SURFACE | re-run-already-done-by rc2-failsafe/VERIFY.md (Gate 8: 8 passed) | host-actions.ts; catalog.py (read-only optional property) | No write kind, route or order path was added. |
| scenario LS-1; xadv-keyless-1 (cold boot); xadv-keyless-6 (README "13 agents") | re-run-already-done-by rc2-failsafe/VERIFY.md (smoke) | main.py `run_http` | The smoke built and booted every sidecar at b796f6a9: 13 agents. |
| scenario LS-2 (lifecycle, EOF stop) | carries | main.py `run_http` (SystemExit arm, `os._exit`) | EOF stop runs through `_exit_when_parent_closes_stdin`, which has no hunk. The new arm runs only after uvicorn returns. fix-r1 FINAL-028 covers the port-taken exit. |
| scenario LS-3 (edge probes) | carries | none on path | The LLM error frames, 422 validation and workspace save have no hunk. |
| scenario LS-4 (secrets, licence, banned words) | carries | english_words.txt.gz added; code hunks | Judge's counts-only grep of the range additions found 0 banned-word, 0 banned-phrase and 0 key-shaped hits, and 0 in the decompressed word list. No licence file changed. |
| scenario RS-3 (search status) | carries | none on path | |
| scenario RS-4; xadv-keyless-7 trace (FAST legs on an uncached IN name) | re-run-already-done-by rc2-failsafe/VERIFY.md (live FAST via /mcp research) | fast `snapshot_structured` | The listing region equals the session region here. |
| scenario UI-1; reproof portfolio-roundtrip | re-run-already-done-by rc2-failsafe/VERIFY.md (workspace.test.ts CODE-FRONTEND-001, LIFECYCLE-002 pins) | workspace.ts portfolios restore `setAll(..., region)`; portfolios `normalizeHolding` | Restore now stamps the region. No-rollback is pinned at the head's code. |
| scenarios UI-3, UI-5, UI-6 | carries | none on path (`_label_freshness`, `fitLayoutTemplate`, ProposedChangesReview) | |
| scenarios UI-7, xadv-keyless-2, xadv-keyless-4 (keyless stranger) | carries | news_provider `_clean` | The single quote, history, resolve and Ollama-missing paths have no hunk. /agents=13 was re-proved by smoke. |
| scenario xadv-keyless-8 (default cockpit seeds via batch /quotes) | re-run-already-done-by rc2-failsafe/VERIFY.md (FINAL-006 pins) + rc2-round2 live | quotes.py batch | Same as onboarding row 23. |
| reproof portfolio-gated-write | carries | portfolios `addHolding` region stamp | The staging and accept path has no hunk. |
| DOCS_VS_REALITY (a) version, (b) scripts, (f) no trading offer, (g) banned words, (h) SAFETY §2 | carries | none on path | No version source, package.json, route or gate file changed. Banned words: 0 (see LS-4). |
| **Live LLM-lane samples**: composer-chat persona munger (BDL figures); onboarding row 26; AC-1 passes; DS-3 brief units; RS-1 OpenAI; xadv-keyless-5/7 prose; xadv-realuser-6; reproof clean-run | **re-run** (spot-check) | catalog `_LISTING_REGION` on the price_data/fundamentals schemas (every turn ships all schemas); gate `_rebase_pe_on_filed_eps` | The prompt and the tool outputs the figures were checked against both changed. The grounding code did not. One sample cannot certify a stochastic pass, only catch a schema or grounding break. |
| battery: 365 passing rows (266 holds, 99 ci_pinned) whose register files miss the 62 | carries | none | No changed file is on their path. |
| battery: 126 holds rows whose files intersect, on functions with no hunk or an additive-only branch | carries | per file, as above; e.g. `delete_workspace` (CODE-FRONTEND-004), `ensure_build` (CODE-PLATFORM-077), `_with_empty_reason` on non-empty statements (LEAD-015, DATA-026, DATA-096) | The intersection is file-level. At function level, none of these observations enters a changed branch. |
| battery: 29 holds rows on changed functions (list below) | re-run-already-done-by rc2-failsafe/VERIFY.md (pin table / ci-local); DATA-113 by fix-r1 FINAL-010 | gate, relevance, verify `_parse_verdict`, resolver `_same_company_key`/`autocomplete`, nse_provider `_Throttle`, earnings `_revenue_currency` | Each has a pin green at b796f6a9 on the changed function, or a byte-identical live re-proof. |
| battery: 70 ci_pinned rows whose files intersect | re-run-already-done-by rc2-failsafe/VERIFY.md (ci-local green) | per pin; amended pins listed in Method | The pins run in the suites that were green at b796f6a9. The amended pins still assert the original property. |

The 29 battery rows already re-proved:
- DATA-001, 004, 005, 006, 013, 014, 027 (via the DATA-014 pin), 033, 034, 117;
- RESEARCH-001, 002, 004, 015, 018, 021;
- LIFECYCLE-004, CODE-DATA-005, CODE-RESEARCH-012, LEAD-034, LEAD-050;
- LEAD-059, LEAD-116, CODE-DATA-001, DATA-018, UI-039, CODE-DATA-017;
- DATA-066 and DATA-113.

DATA-004's 50.16 vs 0.00 flag survives the zero-mismatch removal through the 3pp rule.

**Counts by group:** 26 carry, 4 re-run (these share 3 checks), 30 already re-proved. Battery passes (590): 491 carry and 99 already re-proved.

## Re-runs owed before r15-launch

1. **Route replay (malformed-symbol matrix and census).** Start an isolated sidecar at 1fddb2b1 on its own scratch data dir. Re-issue the recorded GET lists with curl:
   - failure-inducer: the 81 malformed-symbol GETs;
   - panels-layouts census: every request to `/fundamentals/{s}`, `/fundamentals/{s}/{income,balance,cashflow}`, `/quotes?symbols=`, `/resolve/autocomplete`, `/news` and `/earnings/{s}/estimates`.

   Pass: no 5xx, every 404 carries a typed `detail`, and every status equals the d38b5d1a record. The only allowed difference is a known NSE/BSE listing that now answers 200 from the FINAL-005 filings fallback.
2. **Portfolio crypto through the batch path (P5b).** Run `curl -H 'X-Vysted-Region: US' 'http://127.0.0.1:<port>/quotes?symbols=BTC%2FUSDT,ETH%2FUSDT&asset_class=crypto'` against the same isolated sidecar. Pass: 2 rows, `symbol` equals the requested spelling, currency USDT, freshness `live`.
3. **LLM spot-check.** Run one `scripts/r15/vy.py invoke copilot` turn on an isolated sidecar at 1fddb2b1, on a port in 52100-52399, with llama3.1:8b and region IN. Prompt: "What are BDL's P/E and market cap?". Pass: a fundamentals or price_data call parses under the schema that now carries `region`, and every figure in the reply equals that tool result.

## Commands run (repo root, read-only)

```
git diff --stat|--name-only d38b5d1a 1fddb2b1 -- . ':(exclude)docs'
git diff --name-only cac9d206 1fddb2b1 -- . ':(exclude)docs' ; git diff --stat 7f273b03 1fddb2b1 -- . ':(exclude)docs'
git diff d38b5d1a 1fddb2b1 -- <each non-test file> ; git diff -U0 ... correctness_gate.py | grep '^@@'
git show 1fddb2b1:{src/lib/host-actions.ts,sidecar/routers/quotes.py,sidecar/services/nse_provider.py,sidecar/main.py,sidecar/services/screener.py,sidecar/services/provider_registry.py}
python3 (battery shards x register-at-d38b5d1.json files x changed files: 227 intersecting rows)
grep over the range additions for the BANNED patterns and key shapes (counts only)
```
