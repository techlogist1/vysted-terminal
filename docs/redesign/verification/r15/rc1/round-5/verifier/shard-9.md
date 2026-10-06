# rc1 round 5 — adversarial sample verifier, shard 9 (rc1-vshard-9)

Model: claude-opus-5-5. Candidate checkout: `633f844071d972b337f4c3526d86555c80df0568`
(read-only worktree `scratchpad/rc1-round-5-9bc600e-fix-int`, `git rev-parse HEAD` verified).
Own sidecar on :52609 (stopped at end by killing its sleep pid only). Evidence: `shard-9-evidence/`.
`<wt>` = the worktree; `scratchpad/` = the session scratchpad. All Python ran with `PYTHONDONTWRITEBYTECODE=1`.

## Verdicts

| Entry | Verdict | Basis |
|---|---|---|
| R15-LEAD-039 | inconclusive | Live repro blocked by Yahoo 429 (every /earnings/*/estimates → 502). Fixture at the sha: RDY shape (Revenue, no Earnings fields) → partial detail, eps_* null; fresh TM (date only), SONY (NaN mean), UMC (ISO date string) all partial, no raise. |
| R15-AGENT-010 | holds | Stub 1 s resolver: tool 1.34 s, max loop lag 19 ms; raising resolver → `{ok:false, status:unresolved}`; `_canonicalize` swallows. Fresh: black-hole HTTPS proxy, live miss bounded (9.2 s cold incl. masters), 6 concurrent hung misses max lag 114 ms. (Standing at two failures — recorded only.) |
| R15-DATA-117 | holds | Live v7 (curl_cffi) rows: TSM P/B 92.1669 / book 4.889 withheld, HDB 9.32 withheld, fresh IBN/PDD/SIFY/BABA/WIT/NVO/UMC withheld, AAPL unchanged. .info path: pinned fixtures pass (Yahoo .info 429). trailing/forward P/E per-ADS USD-consistent in live rows. |
| R15-LEAD-040 | holds | Cold 12-way resolve_async (yf.Search instant): unrelated to_thread waits 13.5 ms; fresh mixed autocomplete+resolve: 11.1 ms. |
| R15-AGENT-092 | holds | Wall halt mid-round after tool_use: host_actions [], brief None; prior dispatched watchlist kept, halted round's write_note/publish_brief dropped; spend/token/step halts clean. |
| R15-AGENT-094 | holds | All custom panels forms coerced (stringified, mixed); `_coerce` never raises across all schemas. Live llama not run. |
| R15-AGENT-095 | **refuted** (not certified) | Acceptance date shapes kept, fabrications (5, 4) still replaced, but the title claim is unfixed for the DD-Mon-YYYY hyphen form: `Per the 20-F filed 26-Jun-2026, each SIFY ADS represents six equity shares.` and `26-JUN-2026 … 6 equity shares` are REPLACED against the depositary result (counts ['26','6']). |
| R15-DATA-113 | inconclusive | Live blocked (Yahoo 429). Fixture: WIT revenue_currency INR / EPS USD; fresh INFY (financialCurrency USD, INR-sized) → INR; TSM → TWD; NVO (Denmark unmapped) → null not guessed; AAPL USD. types/earnings.ts + EpsEstimateGrid label per field. |
| R15-RESEARCH-027 | **refuted** (not certified) | Register shape (resolved target, web stall 20 s) finishes 8.0 s; all-legs stall 8.0 s. Fresh: no instrument resolves → web-only branch `_web_round(tool_call, f"{query} news outlook")` is un-boxed → 20.0 s. Register records 2 prior failures (third-failure rule is the lead's call). |
| R15-RESEARCH-022 | **refuted** | Stub repro, Mojeek, fresh Brave → rate_limited + breaker failure. But the real `DdgSearchBackend` never calls `raise_if_challenge_page`: a 200 challenge on HTML+Lite → OK 0 results, ddg failures 0; all three engines blocked → OK 0 results ("found nothing"), not rate_limited. Caveat: live DDG today answers 202 on Lite (handled) and resets HTML. |
| R15-DATA-003 | holds | US AMAL/SAIL/TECH/CCL/IEX announcements/results/deals/shareholding/corp-actions → `not_applicable`; IN AMAL keeps promoter 71.35; ownership_check gates on the bound .NS/.BO listing. ABB is not in the US master (delisted) so IN is correct. |
| R15-DATA-024 | holds | Live: KOPRAN bulk 108 rows incl. 2026-09-07 UNITED SHIPPERS sell 700000 @234.3 BSE; block 3; RELIANCE/ADANIENT/YESBANK/SUZLON/IDEA bulk; YESBANK SAST 20; `exchange_deals` capability in catalog. |
| R15-LEAD-022 | holds | `_yahoo_symbol` keeps 2222.SR, SAP.F, GGAL.BA, BMW.BE, EQB.NE, CEZ.PR, QNBK.QA; BRK.B→BRK-B, BF.B→BF-B; direct Yahoo chart confirms SAR/EUR/ARS/CZK. Sidecar /quotes itself 429 at run time. |
| R15-DATA-008 | inconclusive | Live /fundamentals/SIFY 429. Pinned SIFY fixture: revenue kept + labelled INR, P/S/EV-EBITDA/P/B/book withheld with reason; frontend formats with `financial_currency ?? currency`. Live v7 confirms SIFY financialCurrency INR. |
| R15-DATA-055 | inconclusive | Live /fundamentals/NAVN, MDLN 429. Pinned tests (listing_date, first_trade_date, 52w leg dates, forward_pe_fiscal_year) pass; panel `listedUnderAYear` relabels "since listing" and drops 1Y change. |
| R15-DATA-114 | holds | Walk-back + probe cache: acceptance C and fresh D/E/F correct. Adjacent: truncated-zip BadZipFile (below). |
| R15-LEAD-044 | **refuted** (not certified, guard half) | Region threading holds: IN-session sp500 of HAL/CCL/IEX/ACGL/PTC → 5/5 US rows, store USD. But the fix_shape guard is absent: `_store_pair("PTC", PTC.NS/INR pair)` writes ('PTC India','INR') under bare key PTC. No live path reaching it was found (custom canonicalises to .NS keys). |
| R15-LEAD-045 | holds | Pinned crumb/v7 429 → rate_limited + throttled label pass; live `fetch_quotes_batch([AAPL,MSFT,RELIANCE.NS])` via curl_cffi → 3/3 ok, crumb minted, 1.4 s. |
| R15-CODE-FRONTEND-017 | holds | Vitest: filings P1, detail/insider acc1-4, fresh late-success-after-newer-error, fresh earnings 7/30-day success + reject. |
| R15-CODE-PLATFORM-017 | holds | Server /workflow/run: round(2.5)=3, 2^3=8, ternary=1, log(x,10) disallowed Call, x/0 division by zero; inspector preview and editor Run both hit the server. |
| R15-UI-015 | holds | Retry hook attempts: 502/404/422 → 1, 503/TypeError → 13; search keeps the 501 reason. |

## Adjacent (not refutations)

1. (low) `src/store/sec.ts` `clearSearch` does not bump `searchGeneration`: late 501 after clear paints "sec-edgar-mcp is not available" under an empty field (batch-29 residual, still open).
2. (low) `fetch_latest_fo`: 200 + truncated PK zip → `BadZipFile` escapes, no walk-back to the cached Monday.
3. (low) `/earnings/*/estimates` maps Yahoo 429 to 502 provider_error; `_fetch_calendar_sync` wraps untyped (fundamentals/quotes type it 429).
4. (low) Stale "client-side mathjs" comments in `node-registry.ts:185-190` and the `code-node-run.ts` header.

## Environment

- Yahoo quoteSummary/calendar 429 on this IP for the whole window (sidecar circuit OPEN, opens_total 8; in-process yfinance also 429). v7 via curl_cffi and chart still answered.
- Shared sec-edgar-mcp :52154 `get_recent_filings` timed out at 60 s → US shareholding 36–90 s.
- Live llama3.1:8b check for AGENT-094/095 not run (optional; in-process guard evidence is decisive).

## Refutation commands (checkout 633f844071d972b337f4c3526d86555c80df0568)

- AGENT-095: `cd <wt>/sidecar && PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scratchpad/v9_agent_inproc.py` → `agent094-095-inproc-output.txt`
- RESEARCH-022: `cd <wt>/sidecar && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scratchpad/v9_r022.py` → `research022-inproc-output.txt`
- RESEARCH-027: `cd <wt>/sidecar && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest scratchpad/v9-r027/test_v9_r027.py -q -s -p no:cacheprovider --rootdir=scratchpad/v9-r027 -c /dev/null` → `research027-pytest-output.txt`
- LEAD-044: `cd <wt>/sidecar && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest scratchpad/v9-l044/test_v9_l044.py -q -s -p no:cacheprovider --rootdir=scratchpad/v9-l044 -c /dev/null -o asyncio_mode=auto` → `lead044-pytest-output.txt`

Findings: `findings/rc1-vshard-9.json`. Log: `logs/rc1-vshard-9.md`.
