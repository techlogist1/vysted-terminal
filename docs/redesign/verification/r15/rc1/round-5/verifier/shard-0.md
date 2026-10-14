# RC1 gate round 5 — adversarial sample verifier, shard 0 (rc1-vshard-0, Opus)

Candidate sha: `633f844071d972b337f4c3526d86555c80df0568` (read-only worktree `scratchpad/rc1-round-5-9bc600e-fix-int`).
Own sidecar booted from the candidate source on :52600 (seed data copy), stopped at the end via its sleep pid.
Frontend probes ran from a scratch copy of the candidate `src/` (node_modules symlinked); the candidate worktree was never edited or built.
Raw evidence: `verifier/shard-0/` (probe scripts, logs, curl bodies). Findings: `findings/rc1-vshard-0.json`.

Tally: 20 holds, 4 refuted (all "not_certified": literal repro holds, the claim does not), 0 inconclusive. 3 adjacent.

| id | verdict | own repro | fresh variant |
|---|---|---|---|
| R15-DATA-033 | holds | validate_quote/validate_series raise CorrectnessError on NaN, +inf, -inf | in-process `_resolve_sync` with a NaN lane `a` then lane `b` -> "served by b 101.5" |
| R15-DATA-070 | holds | mocked RSS through `fetch_news`: undated + malformed-date items -> `published_at` None, sorted after dated items | malformed-date string item also lands last, rendered "date unknown" |
| R15-DATA-004 | holds | `/fundamentals` IN: DHANBANK insiders 51.18% flagged vs NSE promoter 0.00%, institutions 6.02% flagged vs 14.26%; JONJUA, NAPEROL flagged | ICICIBANK insiders 3.53% flagged vs 0; TCS insiders ok, institutions flagged |
| R15-CODE-DATA-001 | **refuted (not_certified)** | resolve FOCUS: NSE Focus Lighting isin None, BSE Focus Business Solution INE0DXR01010/543312; shareholding split_source None — holds | `/disclosures/announcements?symbol=FOCUS` -> 50 items, **16 exchange=BSE from scrip 543312 (a different company)**: "Closure of Trading Window" 2026-09-26, "Fixed Record Date For 19Th AGM", dividend record date |
| R15-CODE-DATA-005 | **refuted (not_certified, strict)** | `is_applicable`/`_is_blocked` copies gone: witness.py `is_india_listing`/`is_block_error`, identity assignment in ownership_check, market_cap_witness, range_check; one `is_india_target` (relevance.py:602) | title's "_row_value twins" remain: `earnings_quality.py:134` body identical to `growth_check.py:94`, docstring "Mirrors" |
| R15-DATA-001 | holds | DAL -> DAL.BO, CHTR -> CHTR.BO (yfinance) | HAL -> HAL.NS revenue 317.9B INR; IEX -> IEX.NS 6.15B; SUMAX name "SUMAX ENGINEERING LIMITED" INR |
| R15-RESEARCH-029 | **refuted (not_certified)** | Kaynes "Merged Sources" shape stripped (3 removals) | `## Citations`, `**Sources cited:**`, `## Source List`, `## Key sources`, `Further reading:` all removed=0; a 4-item "## Citations" list ships against a 3-row rail through `ensure_citation_integrity`; fix_shape's "ULTRA below min_web_domains -> brief.note" not implemented in iter.py |
| R15-RESEARCH-034 | holds | "Price action is not covered yet" -> False; "No gaps remain" -> True | adjacent: "Complete coverage is not yet achieved" -> True |
| R15-RESEARCH-037 | holds | unranked list blog/reuters/sec/nse -> "primary [3, 4]; tier-1 press [2]" | callers pass the same list the prompt numbers |
| R15-CODE-FRONTEND-018 | holds | saved screen persists in the workspace blob | screen survives relaunch AND a named-workspace load |
| R15-LIFECYCLE-002 | holds | restore of every slice | `fromJSON` throws on a registered layout: all slices still restored, 0 POSTs; the later POST carries holdings + notes |
| R15-LIFECYCLE-003 | holds | autosave gated on restoreSettled | pre-restore change -> 0 POSTs; 5-change burst -> 1 coalesced POST with researchSymbol NVDA + "Research: NVDA" archive |
| R15-DATA-100 | holds | pricer defaults to the region currency | adjacent: region switch while open keeps "$998.10"/USD |
| R15-CODE-PLATFORM-053 | holds | mixed currencies -> concentration/weights null | JPY+EUR portfolio -> null |
| R15-DATA-007 | holds | `GET /sec/filings/0000320193-23-000077?identifier=AAPL` -> form_type 10-Q, filed 2023-08-04, "Apple Inc.", edgar_url on CIK 320193 | MSFT 10-K accession 0000950170-23-035122 under identifier=AAPL -> 404 not_found (no synthetic 10-K); under MSFT -> 10-K 2023-07-27 MICROSOFT CORP; agent tool returns ok:false on ProviderError |
| R15-AGENT-022 | holds | null/omitted cost_basis -> "missing cost_basis — ask the user for it; do not guess" | "about 1500" -> type error; card shows "no price", string cost not applied |
| R15-AGENT-024 | holds | stringified criteria -> list of 3 | screener_run stringified parses; adjacent: group-only write_screener_filters rejected |
| R15-AGENT-047 | holds | truncated ollama/groq fragments -> invalid-args sentinel | JSON array args -> sentinel; runtime keeps it |
| R15-CODE-FRONTEND-008 | holds | AUTO_APPLIED_KINDS = panel/chart/watchlist drives both proposed-changes.ts:124 and the hint | save_screen/save_layout/write_note/portfolio are data-write; set_region settings |
| R15-CODE-FRONTEND-014 | holds | noteScope global | 'GLOBAL ' and 'General' -> general; saveLayoutName uses the active layout |
| R15-UI-001 | holds | agent replace into open NVDA note shows | keystroke kept; select-all+delete persists ""; unmount inside the debounce flushes |
| R15-AGENT-018 | holds | mocked Ollama stream content `{"name":"write_note","parameters":{...}}` -> LLMToolUseEvent `leaked_<uuid>` | JSON split across chunks after prose (prose streamed, call rescued, trailing fake "Done!" dropped); fenced block with stringified `arguments`; `price_data(symbol="ZOMATO.NS")` call syntax; non-offered name stays text |
| R15-CODE-AGENT-003 | holds | `POST /llm/keys/validate` fake keys openrouter/gemini/xai/groq/openai -> ok:false reason invalid | real Gemini ClientError 400 humanizes to auth "The Google Gemini API key was rejected"; xAI, deepseek map to auth |
| R15-UI-008 | holds | OpenRouter fake key -> invalid | OnboardingFlow.tsx:341-350 returns before `setSecret` when `!result.ok` |

## Refutation records

### R15-CODE-DATA-001 (not_certified)
- checkout: `633f844071d972b337f4c3526d86555c80df0568`
- command: `curl -s -H 'X-Vysted-Region: IN' '127.0.0.1:52600/disclosures/announcements?symbol=FOCUS'`
- output (excerpt, `shard-0/focus-announcements.json`): count 50, 16 with `"exchange": "BSE"`, e.g.
  `{"symbol":"FOCUS","exchange":"BSE","headline":"Closure of Trading Window","category":"Insider Trading / SAST","ts":"2026-09-26T13:37:34.623000+05:30"}`,
  `{"headline":"Fixed Record Date For 19Th AGM Of The Company","category":"Corp. Action"}`.
- in-process: `is_nse_symbol('FOCUS')` True, `is_bse_symbol('FOCUS')` True, `bse_scrip_code('FOCUS')` '543312', `dual_listed_bse_code('FOCUS')` None; BSE master row ('Focus Business Solution Ltd','M','543312','INE0DXR01010').
- cause: `corporate_disclosures.get_announcements` builds lanes `(NSE, is_nse_symbol(bare)), (BSE, is_bse_symbol(bare))` and `_fetch_bse_announcements` calls `symbol_resolver.bse_scrip_code(bare)` — no dual-listing/ISIN guard (the deals lane has one). Results, corporate-actions and deals showed no BSE contamination.

### R15-RESEARCH-029 (not_certified)
- checkout: `633f844071d972b337f4c3526d86555c80df0568`
- command: `cd sidecar && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python verifier/shard-0/probe2.py`
- output (`shard-0/probe2.log`): `'## Citations': removed=0 survives=True` … `'Further reading:': removed=0 survives=True`; `'## References': removed=1`.
- cause: `_BIBLIOGRAPHY_HEADING_RE = ^(?:merged |cited )?(?:sources|references|bibliography|works cited)(?: used)?$` is a closed allowlist; iter.py has no min_web_domains brief.note.

### R15-CODE-DATA-005 (not_certified, strict — lead may adjudicate)
- checkout: `633f844071d972b337f4c3526d86555c80df0568`
- command: `grep -rn 'def _row_value' sidecar/services`
- output: `growth_check.py:94` and `earnings_quality.py:134` (docstring: "Mirrors services.growth_check._row_value … so the two Yahoo statement readers behave identically").
- The firing predicates the fix_shape names are fixed; only the title's "_row_value twins" remain. Low severity.

## Adjacent findings
- **medium, new_defect (near R15-AGENT-024):** `write_screener_filters` with only the documented OR/nested `group` tree is rejected by `_normalise_tool_args` — "invalid arguments for write_screener_filters: missing criteria — ask the user for it; do not guess". Schema `required: ['criteria']`; catalog text says the group "supersedes the flat list"; frontend host action accepts group-only. `criteria: []` + group passes. Evidence `shard-0/probe2.log`.
- **low (near R15-DATA-100):** BondPricerPanel `useState(() => regionConfig(region).currency)` (line 127) fixes the display currency at mount; region switch to IN while open still renders "$998.10" USD. Evidence `shard-0/vitest-fe.log`.
- **low (near R15-RESEARCH-034):** `_reflect_says_complete("Complete coverage is not yet achieved.")` -> True via the leading token; bounded by `coverage_floor_met`.

## Notes
- No live Ollama run was made (AGENT-018 verified in-process through `OllamaProvider.stream_chat` with a mocked stream), so the local-model lock was never taken.
- The candidate worktree shows `M docs/redesign/verification/r15/spend-ledger.jsonl`; this shard made no edit there.
