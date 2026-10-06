# rc1-vshard-0 — adversarial sample verifier, shard 0 (gate round 2)

Candidate `81fbfe910d472ecd154fa62e42d86bce213a697e` (worktree `scratchpad/rc1-4c6dfe8-fix-int`, `git rev-parse HEAD` confirmed).
Own sidecars: :52600 (curl / in-process work) and :52396 (vy.py, because vy.py refuses non-GET calls outside 52100-52399). Both ran from the candidate and are now stopped.
The shared :52152 stack runs 4c6dfe8c, not the candidate, so it was not used for verdicts.
Evidence: `verifier/shard-0-evidence/` (logs + `scripts/`). Findings: `findings/rc1-vshard-0.json`. Log: `logs/rc1-vshard-0.md`.

Verdict rule: **refuted** means the literal repro reproduces, or the entry is NOT CERTIFIED because its title or fix_shape fails on a fresh case. The evidence text says which.

## Verdicts

| id | verdict | literal repro | fresh case |
|---|---|---|---|
| R15-DATA-006 | holds | `curl :52600/quotes/DAL?asset_class=equity`: ts 2025-03-12, change 0, freshness stale; fundamentals as_of 2025-03-12 | WHITHAL (BSE 512431, Ason 2023-03-23): ts 2023-03-23, stale, change 0 (`stale_probe.log`) |
| R15-DATA-070 | holds | undated RSS item: published_at None, sorted last | malformed pubDate and NewsAPI item with missing/bad date: None and last; dated items newest-first (`news070.out.log`) |
| R15-DATA-033 | holds | NaN quote and NaN series rejected by the correctness gate | +inf rejected; registry walk with lane A NaN falls through to lane B (2500.0) (`nan033.out.log`) |
| R15-DATA-002 | **refuted (NOT CERTIFIED)** | overview typed/autocomplete path and the chart path carry the region | watchlist pickCandidate drops the picked region (SymbolEntry has no region). IN session: AMAL = Amal Ltd INR 674.4; US: USD 47.58. Row click, screener and agent `openCompanyOverview` pass no region (`data002.log`) |
| R15-CODE-DATA-005 | holds | in-process identity: every checker's is_india_listing / is_block_error is the witness.py function; one is_india_target | is_applicable('AMAL') False, 'AMAL.BO' True |
| R15-DATA-012 | holds | NSDL→GUJENERGY rename injected: resolve keeps NSDL/BSE, rename None, ISIN INE301O01023 | live NSE rename map (1056 rows): all 14 BSE-only collisions resolve to their own BSE listing with matching ISIN; 0 misrouted (`rename012c.log`) |
| R15-RESEARCH-004 | holds | '40.5% …', '-0.4% …', '67.13953 P/E' intact; step reads 0 verified / 3 unverified / 0 disagreement | '1. 12.75x', '- -3.2%', '2) .85 beta', '* 1,234.5 crore' intact; counts correct |
| R15-RESEARCH-015 | **refuted (NOT CERTIFIED)** | same host on both lanes: UNVERIFIED | www.nseindia.com + nsearchives.nseindia.com (one registrable domain) give AGREE across channels. `verify._row_domains` uses `finance.domain_of` (host), not the registrable domain (`verify_015_min.out.log`) |
| R15-RESEARCH-003 | holds | vy.py deep BLUESTARCO: Closing Price [6] → vysted://price, P/E [7] → vysted://fundamentals; list grew 7→8 with stable numbering | VOLTAS deep: two publishes (13 and 8 sources) share the same prefix numbering, append-only. Adjacent defect found (below) |
| R15-CODE-FRONTEND-004 | holds | POST/GET/list/DELETE for 'Research: NVDA', 'Research: M&M', 'RELIANCE.NS' | Hindi name, path traversal, backslash, CON, quotes, %: all percent-encoded and round-trip; createResearchSpace rolls back on a save failure |
| R15-CODE-FRONTEND-005 | holds (static) | PERSISTED_SLICES covers every SerializedWorkspace field; wireAutosaveTriggers is wired in page.tsx | savedScreens / keybindingOverrides / chartDrawings / researchSpaces all registered |
| R15-CODE-FRONTEND-018 | holds (static) | same registry; mutators are immutable | — |
| R15-DATA-007 | holds | 2023 AAPL 10-Q: form 10-Q, filed 2023-08-04, Apple Inc., CIK-based edgar_url | 2016 NVDA 8-K with no hint: honest 404; with form_type=8-K: real metadata; bogus accession: 404 (`data007.log`) |
| R15-DATA-009 | holds | N=1/2/4 equal-weight random walk: curve 200 = dates 200, Sharpe ratio to date-sampled reference 1.000 | N=3, N=5 with walk-forward: 1.000 (`bt009_010.out.log`) |
| R15-DATA-010 | holds | Sortino 6.3521 = textbook | identical losses 15.12, single loss 8.87, all-negative -14.0, each = textbook |
| R15-AGENT-082 | holds | done carries spend_usd (0.037645); footer renders 'N tok · ~$X' | adjacent low (below) |
| R15-LEAD-004 | holds | RELIANCE/TCS/KAYNES/DAL: 'sum of 4 filed quarters' | SME AFCOM/BONDADA/KHAZANCHI: half-yearly label from exchange-filed cadence |
| R15-AGENT-008 | holds | copilot/ollama two-result turn: est 12,714 (29 tools) / 15,914 (43 tools) < num_ctx 16,384; results capped at 8,192 chars + marker | adjacent medium: a 3-result multi-cue round reaches 18,114 > num_ctx (`ctx008.out.log`) |
| R15-AGENT-034 | holds | POST run with budget {} → stored 120000 / 1.0 / 600 / 12 | maxTokens 0 and maxSpendUsd -1 → 422; {maxSteps:3, maxTokens:null} → 3 kept, rest floored; resume floors from the stored budget; BudgetConfig blur restores the default (`agent034.log`) |
| R15-CODE-FRONTEND-002 | **refuted (NOT CERTIFIED)** | fix's own 3 tests pass (tab switch and research-space entry stop the run first; round trip parks the tab) | in a research space, clicking another chat tab (strip always rendered) then leaving the space: space memory = tab B's messages, tab B live = [] (lost); '+' variant: space memory []. Two transcript owners remain (`fe_vitest.log`, `scripts/vshard0-fe002.test.ts`) |
| R15-CODE-FRONTEND-003 | holds | NVDA='my long thesis' + write_note without mode → appended, 'Appended to the NVDA note' | mode null / '' / 'Replace' / 'APPEND' / 'overwrite' / 1 through parse→describe→applyIntentAsync: all append, describe agrees |
| R15-AGENT-045 | **refuted (NOT CERTIFIED)** | ['COCHINSHIP','MAZAGONDOCK'] → ok:false, MAZAGONDOCK "unresolved name" (wording fixed) but fix_shape's own test "compares MAZDOCK" fails | 'Cochin Shipyard'/'Mazagon Dock' → COCHINSHIP/MAZDOCK OK; GARDENREACH / HINDAERO guessed tickers unresolved (`cmp045.log`) |
| R15-AGENT-048 | holds | five schema-failing calls → 2 repairs, 30 s timeout each, usage 210 tok metered into the ledger | hanging provider (timeout scaled to 0.5 s): 2 calls, 1.2 s, ledger [None, None]. A mock that raises bypasses the cap, but the real oneshot never raises, so this is not a finding (`repair048.log`) |
| R15-CODE-AGENT-003 | holds | live openrouter validate_key('not-a-real-key') → False | gemini/xai/groq/deepseek/openai/anthropic fake keys → False; POST /llm/keys/validate → reason invalid, "<Provider> rejected this key."; chat stream error code auth with the key-rejected message for gemini/xai/openrouter (`key003.log`) |

## Refutation commands (checkout 81fbfe91 for all)

- DATA-002: `curl -s localhost:52600/quotes/AMAL -H 'X-Vysted-Region: IN'` then `…US`; `curl -s 'localhost:52600/resolve/autocomplete?q=AMAL'`; static read of `WatchlistPanel.tsx:286-287,562`, `store/symbols.ts:15-18`, `ScreenerResultsTable.tsx:567`, `host-actions.ts:1529,1675`.
- RESEARCH-015: `cd rc1-4c6dfe8-fix-int/sidecar && ./.venv/bin/python3 -u scratchpad/vshard0/verify_015_min.py scratchpad/vshard0/verify_004_015.py` produces "**AGREE (corroborated across channels)** — 40.5% revenue growth (nsearchives.nseindia.com, nseindia.com)".
- CODE-FRONTEND-002: `cd scratchpad/vshard0/fe2 && ./node_modules/.bin/vitest run src/store/vshard0-fe002.test.ts` fails 2/2 (R memory = ['B question'], live = []; newSpace variant R memory = []).
- AGENT-045: `VYSTED_REGION=IN ./.venv/bin/python3 -u scratchpad/vshard0/cmp045.py` → `ok= False … MAZAGONDOCK: unresolved name`.

## Adjacent (new, not refutations)

1. **medium (near RESEARCH-003).** The deep brief cites fundamentals-only figures to exchange PDFs.
   - VOLTAS: "P/E 81.98 (as of September 26, 2026) [2]"; market cap, EPS, dividend yield and 52-week change also go to [2], the BSE Q1 results PDF, while vysted://fundamentals is [12].
   - BLUESTARCO: market cap and revenue TTM go to the results PDFs. It says "P/E Not currently available [7]" even though pe_ratio is 61.74, and the citation audit was skipped for low wall time.
2. **medium (near AGENT-008).** `_fit_to_window` never trims the latest round and only logs at debug level. A multi-cue prompt (43 tools, about 11.6k tokens) plus three capped results comes to an estimated 18,114 tokens, above num_ctx 16,384. Ollama then truncates silently.
3. **low (near AGENT-082).** The footer tokens are the last round's usage (29,375 in + 451 out) while spend_usd is summed over every round.
4. **low (near DATA-007).** 10-Q and 8-K filing detail returns 200 with 0 sections and total_chars 0; a 10-K returns 2 sections.
5. **low (near DATA-009).** A buy sized to exactly the available cash is skipped by float rounding ("have 33333.33, need 33333.33"), so one leg is never bought (`bt_exactcash.log`).

## Not run

- No llama3.1:8b call was made, so no Ollama lock was taken. AGENT-008's acceptance is "by estimate" and was checked in-process against the candidate runtime.
- The GUI was skipped as instructed.
- CODE-FRONTEND-005/018 were verified by static reading only. The fresh frontend cases ran in a scratch copy, never in the candidate worktree.
