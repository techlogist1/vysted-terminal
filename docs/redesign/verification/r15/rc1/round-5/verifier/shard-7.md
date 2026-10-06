# RC1 gate round 5 — adversarial sample verifier, shard 7 (rc1-vshard-7, Opus)

Candidate `633f844071d972b337f4c3526d86555c80df0568`. All commands ran in the read-only scratch worktree
`rc1-round-5-9bc600e-fix-int` (`git rev-parse HEAD` = the candidate). Own sidecar on :52607 from that
worktree's source, data dir `rc1-round-5-data-rc1-vshard-7` (a copy of the seed data), sleep pid 87668.
In-process runs used the worktree `sidecar/.venv` with `VYSTED_DATA_DIR` in scratch. Raw output is in
`verifier/shard-7-raw/`. Log: `logs/rc1-vshard-7.md`. Findings: `findings/rc1-vshard-7.json`.

"NOT CERTIFIED" means the entry's literal repro holds but a fresh case of the same claim fails. The
return schema has no not_certified value, so these are returned as `refuted` and labelled NOT CERTIFIED.

| id | verdict | one line |
|---|---|---|
| R15-DOCS-018 | holds | §3.3 now matches provider_registry.py (model key + preference rank; nse_direct 15 / nse 20 / bse 25 ahead of yfinance 50) and the live /health; RELIANCE.NS quote is served by nse_direct |
| R15-DATA-043 | holds | live custom [AAPL, RELIANCE.NS] and a 4-symbol mixed list: grouped by currency, coverage "spans INR, USD — ranked within each currency" shown in ScreenerPanel, criterion labels "(USD/INR/listing currency)", top-K cut round-robin per currency (limit 2 -> RELIANCE, NVDA) |
| R15-DATA-112 | holds | live repro (MANIKA/RELIANCE/TCS) puts MANIKA last in both directions; an in-process currency-less null-cap row also sorts last at limit 200. Adjacent: the top-K round-robin gives the '' group its own slot (finding 4) |
| R15-DATA-068 | holds | every earnings/analyst envelope (AAPL plus a fresh case, INFY.NS) carries as_of; a second call returns the ORIGINAL fetch stamp; stores have a 15-min TTL + refresh; the analyst panel shows the server as_of + Refresh. Adjacent: the earnings chip uses the client clock (finding 6) |
| R15-RESEARCH-002 | NOT CERTIFIED | the 3 literal strings -> unverified; `_UNVERIFIED_ - no source confirms the 23% operating margin.` and `__UNVERIFIED__ - evidence does not support the figure` -> **agree** |
| R15-AGENT-027 | refuted (literal leg) | credit-429, context-400, Gemini/xAI bad-key 400, invalid model 400, shared-pool 429 (user_id scrubbed) and Ollama (live adapter against a dead port) all fixed; the entry's own leg `humanize('groq', exc(status_code=413))` still returns code=unknown "Something went wrong… Try again" |
| R15-RELEASE-007 | holds | `lint` = `eslint . && node scripts/audit-design-tokens.mjs` (ci-local + lint.yml run `pnpm lint`); on a scratch copy the entry's classes -> exit 1, and a fresh case (sm:space-y-9, min-h-[22px] inside a template literal, md:-mt-11) -> exit 1; the fixture test is in the vitest include |
| R15-LEAD-010 | holds | AAPL 10-Ks -25-000079 and -24-000123 open 200 with and without the form hint. Fresh cases: GS's oldest listed 10-K (2000, row 28) opens 200; MSFT's 1994 DEF 14A opens 200 with and without the hint; JPM's oldest listed 10-K (row 37, 1994) resolves its metadata with no 404, but sectioning 502s (adjacent, finding 8). Earlier JPM list 503s were transient sec-edgar-mcp 60 s timeouts (data.sec.gov answered directly in 0.5 s; a later retry returned 200) |
| R15-DOCS-017 | holds | live universe sizes sp500 503 / nifty50 50 / crypto 50 / nse-all 3,506 (EQ 2,584 + SM 571 + ETF 351) / bse-all 5,042 / india-all 5,891 all equal the doc; nested AND/OR CriterionGroup exists |
| R15-CODE-AGENT-033 | NOT CERTIFIED | the real option_chain handler with expiry 'nearest' -> tool_result ok=false -> the grader fails the trial (literal repro holds). Fresh case: an errored option_chain(AAPL) followed by an ok option_chain(MSFT) -> grader [] PASS (last_result is keyed by tool name) |
| R15-LEAD-032 | holds | raising _fetch -> the second lookup makes no re-fetch; fresh case with the REAL _fetch against a blackholed EDGAR (WIT): 8.00 s, then 0.00 s; a _fetch that hangs forever (SIFY) is bounded at 8 s, then a cached miss |

## Details

### R15-RESEARCH-002 (NOT CERTIFIED)
`cd <wt>/sidecar && ./.venv/bin/python -c "from services.research.verify import _parse_verdict; print(_parse_verdict('_UNVERIFIED_ - no source confirms the 23% operating margin.'))"`
-> `('agree', ...)`. `deep.leading_token` strips `*:-#>[]` but not `_`, so the head is not a verdict token.
The standalone `\bUNVERIFIED\b` check then fails because `_` is a word character, and the marker scan
matches "confirm". Result: the entry's own reason text, with markdown underscore emphasis on the verdict
word, renders `- **AGREE** — claim` with the detail suppressed (verify.py:398). Raw: shard-7-raw/RESEARCH-002.txt.

### R15-AGENT-027 (literal leg refuted)
`humanize('groq', Exc(413))` (status_code=413, empty message) -> `unknown`, "Something went wrong with Groq." /
"Try again or switch provider in Settings." The same happens for openai and for `humanize('groq', status=413)`.
The marker-less 413 context_overflow row is only consulted `if raw:` (errors.py:415-418), and the status
branches have no 413. The real-world reach is narrow: an SDK error string always carries a body, and with
any body the call reads context_overflow. Raw: shard-7-raw/AGENT-027.txt.

### R15-CODE-AGENT-033 (NOT CERTIFIED)
grader.py:95-104 records the LAST tool_result per tool NAME. A trial where option_chain(AAPL, expiry
'nearest') errored and a later option_chain(MSFT) succeeded grades as a pass. That later call is a different
subject, not a retry. Raw: shard-7-raw/CODE-AGENT-033-grader.txt.
Live trial: `python3 scripts/r15/vy.py invoke copilot 'Pull the AAPL option chain for the nearest expiry …'
--provider ollama --model llama3.1:8b --port 52152 --autonomy ask --out …`. It ran on the shared read-only
stack because vy.py refuses :52607, which is outside 52100-52399, and it ran under the Ollama lock. The stream
carries tool_result frames: call 1 option_chain(AAPL) was ok=false (yfinance 429); call 2, for the same
subject, was ok=true. As recorded, the grader returns [], a legitimate retry recovery. With call 2 removed, the
grader fails the trial with "option_chain errored: provider error …". Raw: CODE-AGENT-033.events.jsonl,
CODE-AGENT-033.vy.txt, CODE-AGENT-033-live-grade.txt.

### SEC / R15-LEAD-010
The literal repro holds, and the fresh cases above are in shard-7-raw/LEAD-010.txt. Two of my own script bugs
are recorded there and were rerun by hand: the 'DEF 14A' word-split, and an empty form_type that returned 422.

## Adjacent (findings file)
4. Screener top-K round-robin gives currency-less rows a slot (medium).
5. A Gemini free-tier per-minute 429 is read as "out of credit" (medium).
6. The earnings drill-down as-of chip uses the client clock, not the server as_of (medium).
7. /earnings/{sym}/estimates types a yfinance 429 as a 502 "unexpected response" (low).
8. A listed 1994 JPM 10-K opens as 502 (sec-edgar-mcp sectioning NoneType) instead of a raw-text fallback (low).

Not filed: the llama3.1:8b trial answer stated ATM premiums "as of December 2023" for a nearest-expiry request. That is the local-model known limitation (DECISIONS 4.9-4.12), not a fix-round item.
