# RC1 gate round 3 — adversarial sample verifier, shard 0 (rc1-vshard-0)

Candidate `5ff9be041180c1c316ad48ceb120a23549a7575a` (worktree `rc1-round-3-01d6920-fix-int`, `git rev-parse HEAD` checked before every in-process run). Own sidecar from that source on :52600, data dir = copy of `rc1-round-3-seed-data`, shared MCPs :52153/:52154 read-only. Model: Opus. No LLM call was needed (no Ollama lock taken).

Sample: battery `INDEX.json` sets whose index % 9 == 0 (0, 9, 18, 27, 36, 45, 54, 63, 72; ids only), then a risk-weighted pick (every critical, most highs, the live-reproducible mediums): 17 entries.

## Verdicts

| id | verdict | literal repro | fresh case |
|---|---|---|---|
| R15-DATA-004 | holds | DHANBANK insiders 51.18% `flagged` vs NSE promoter group 0.00% | ITC 29.49%, ICICIBANK 3.53%, LT 18.09% all `flagged`; screener field labelled "Insider holding (Yahoo)" |
| R15-DATA-005 | **refuted (not certified)** | VERTEX / JNPR / JUMBO book_value + P/B `flagged` | **TSM P/B 92.17 and HDB P/B 9.32 served `ok`**: Yahoo book value per ORDINARY share against an ADR price (TSM ADR = 5 sh, HDB ADR = 3 sh). TSM market cap 2.337T USD / filed equity 5.355T TWD (~170B USD) = ~13.7; HDB ~3.1. `correctness_gate.reconcile_book_value` returns early for any `financial_currency` (line 770), so the title's "P/B served from a wrong share count" still ships ok for foreign-reporter ADRs |
| R15-DATA-006 | holds | /quotes/DAL timestamp 2025-03-12, freshness `stale`, change 0; fundamentals as_of 2025-03-12 | in-process `_quote_from_header` with Ason '21 Sep 26' and '2 Jan 24': change 0, dated to Ason |
| R15-DATA-008 | holds | SIFY `financial_currency: INR`, P/S `withheld`; panel + brief format sizes in `financial_currency ?? currency` | TSM (TWD) and IBN (INR): P/S withheld with the mixed-bases reason |
| R15-DATA-033 | holds | NaN / inf last close and NaN / ±inf quote price rejected | yfinance / india / nse / bse OHLC go through `_num` and drop NaN rows |
| R15-DATA-022 | holds | SMR count 1 (2026-06-04, BSE, promoter 65.74) | '4 Jun 2026', '17 Sep 2026' parse; an unparsed qtr falls back to the submission date (corporate_disclosures.py:1178-1183) |
| R15-DATA-021 | holds | SIL 2024-06 and earlier: split None; 2024-09 takes 2024-12 (92 d, within bound) | Jun-2026 FII 38.86 checked against NSE XBRL SHP_1697865 (InstitutionsForeign 0.3886); screener.in's 0.00% is its own reclassification |
| R15-DATA-019 | holds | JUMBO count 18, BSE window 2026-03-30..2026-09-26 stated | AMAL 21 (NSE+BSE), TTC 16, windows stated |
| R15-DATA-070 | holds | undated RSS item -> published_at None, sorted last | malformed pubDate also None; NewsFeedPanel renders "date unknown" |
| R15-DATA-090 | holds | truncated `__autosave__` moved to `.corrupt-<ts>`; next save leaves it intact | named workspace with non-dict `[1,2,3]` and binary junk: `.bak` served, corrupt copy quarantined |
| R15-AGENT-010 | holds | resolver runs on `asyncio.to_thread`, yf.Search timeout 5 s | live miss 4.69 s, never-answering HTTPS proxy 6.04 s, max event-loop gap 27 ms in all runs |
| R15-CODE-PLATFORM-004 | holds | live `/workflow/run`: value ' FALSE ', 'Off', 0 -> true-port node and its downstream `skipped` | 'yes' -> false-port node `skipped` |
| R15-CODE-PLATFORM-005 | holds | every eval-date setter under `holds_ql_lock` | 200 concurrent /quant/option/price (2 valuation dates x BS/binomial, 32 threads): 0 mismatches vs sequential |
| R15-CODE-PLATFORM-020 | holds | extra-key row listed under `unreadable`, good row still listed | v2 row and non-JSON row also listed as unreadable |
| R15-LEAD-026 | **refuted (not certified)** | ZZZZNOTREAL -> `unknown_symbol` | **QQZZFAKE.NS and QQZZFAKE.BO -> 200, 0 bars, `reason: null`**: `_is_unknown_symbol` returns False for any .NS/.BO suffix although the NSE/BSE masters are bundled and checked for bare tickers (history.py:43). The documented batch-10 residual is still there, so the title's "unknown symbol answers reason null" holds for suffixed Indian symbols |
| R15-LEAD-039 | holds | RDY / TM / SONY -> 200, null EPS triple, revenue kept | HMC 200 null triple; NVS full triple |
| R15-UI-046 | holds (code read) | `listWorkspaces` filters reserved names; save/delete reject `__` names | — |

Commands: listed with each verdict in the returned object. Every sidecar result came from :52600 booted from the candidate source; in-process runs used `<worktree>/sidecar/.venv/bin/python3` with `PYTHONDONTWRITEBYTECODE=1`.

## Adjacent findings (new, not refutations)

1. **medium — near R15-DATA-005.** A foreign-reporter ADR's P/B (and book_value) is served `ok` on an ordinary-share basis: TSM 92.17 (true ~13.7-18), HDB 9.32 (~3.1). This is the same unfixed claim that makes DATA-005 not certified. Recorded here too so it is tracked if the lead scopes it separately.
2. **low — near R15-LEAD-039.** TM `estimate_analyst_count` = 1 comes from yfinance `earnings_estimate` (row 0q: avg 2.735, low/high 2.735), yet the EPS triple is served null because only the calendar is read. The grid shows "1 analyst" next to a blank EPS.
3. **low — near R15-CODE-PLATFORM-020.** `GET /workflow/saved/{id}` for an extra-key or non-JSON row returns a bare 500 (the v2 row gets a typed 409). `POST /workflow/schedules` on such an id reaches the same `get_workflow`. A CORS-masked 500 in the webview.
4. **low — near R15-DATA-090.** A corrupt workspace with no `.bak` is quarantined but answered as `404 not found`, so the app boots the default layout without telling the user that their portfolio/notes file was moved to `.corrupt-<ts>`.
