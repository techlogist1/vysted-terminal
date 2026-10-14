# rc1 gate round 4: adversarial sample verifier, shard 7 (rc1-vshard-7)

- Candidate: `68d5573aff9a579af084dcbb124843f2aecff6e8`. `git rev-parse HEAD` in the scratch worktree `rc1-round-4-1006c6d-fix-int` printed this sha before every run.
- Own sidecar: :52607, started from worktree source with data dir `scratchpad/rc1-round-4-data-rc1-vshard-7` (a fresh copy of the seed). Its sleep pid was 34158. It was stopped by killing that pid, and :52607 now refuses connections.
- `vy.py` refuses non-GET calls on :52607 because the port is outside its 52100-52399 allow-range. The one live agent call was a zero-cost read-only invoke with a nonsense slug, run on the shared :52152, which runs candidate source.
- No local model (Ollama) call was needed. The Ollama lock was never taken.
- Inputs were the register entries, the running app, the worktree code and the outside world (SEC EDGAR through sec-edgar-mcp). Nothing under `r15/rc1/` was read.
- Raw outputs are in `verifier/shard-7-evidence/`. Scratch tests were run from the scratchpad and never committed.

## Verdicts

| id | verdict | one line |
|---|---|---|
| R15-DATA-115 | holds | `/history/AMAL.BO?range=1y` returns provider `bse` with 255 bars, where NSE has 29. Fresh cases RELIANCE.BO, INFY.BO and 500325.BO (quote and history) also return `bse`. |
| R15-DATA-043 | holds | Custom [AAPL, RELIANCE.NS, MSFT, TCS.NS] with limit 2 serves one INR row and one USD row, and coverage reads "spans INR, USD — ranked within each currency". Criterion labels carry USD, INR or "listing currency". The header still reads a bare "Market cap", but every cell carries its row currency (D57). The fix disclosed the currency rather than FX-normalising, citing no FX layer (D-B2-4). |
| R15-DOCS-018 | holds | §3.3 now describes model-key preference-rank resolution and lists nse_direct 15, nse 20 and bse 25 for region IN. The yfinance bullet is region-qualified. This matches `provider_registry.py`. One adjacent low is recorded below. |
| R15-DATA-112 | holds | Live: MANIKA.NS (null market_cap) sorts last in both desc and asc. In-process: rows with currency None or ' ' sort last in both directions, for both market_cap and pe_ratio. |
| R15-DATA-068 | holds | `as_of` is present on ratings, ratings/history, price-target-history, individual, earnings history/surprises/estimates/upcoming. A second GET within the TTL returns the same `as_of` (AAPL, INFY.NS). The stores keep `fetchedAt` with a 15-minute TTL and a refresh. The panels render "As of" and a Refresh button. |
| R15-RESEARCH-002 | holds | All 3 repro strings and all 8 acceptance strings parse correctly. 18 fresh variants also parse correctly, including backticks, `>`, `Status =`, `(UNVERIFIED)` and a mid-line uppercase word. The labelled cases in `deep._reflect_says_complete` also hold. One adjacent low is recorded below. |
| R15-AGENT-092 | holds | Fresh two-round case: round 1's note is dispatched, then round 2's note arrives with a token-ceiling halt. `host_actions` contains only round 1's note. One adjacent medium is recorded below. |
| R15-AGENT-027 | holds | `humanize()` was run over 24 provider bodies: the repro, the acceptance cases, and fresh Anthropic credit/context, Mistral context, DeepSeek 402, OpenAI 404, Gemini 404/429 and Ollama 404. Each returns a workable code and next step. A live invoke with a nonsense OpenRouter slug returns `model_not_found` with `user_id` redacted. |
| R15-DATA-114 | holds | In-process `fetch_latest_fo`: when today's probe fails or 404s and yesterday is cached, the cached day is served, with one network call across 3 requests. One adjacent medium is recorded below. |
| R15-UI-090 | **refuted (not certified)** | The literal repro holds: AAPL under region IN during NSE hours is not live, and ^NSEI/^BSESN during NSE hours are live. But `locale.instrument_region` maps every non-IN instrument to the US calendar. So BHP.AX, 7203.T, ^N225 and HSBA.L read `live` hours after their own exchange closed, whenever the US is open. The title claim ("stamped against … not the instrument's exchange; a closed quote reads 'live'") still holds for every listing that is neither US nor IN. |
| R15-LEAD-010 | holds | Without a hint, AAPL 10-Ks 25-000079, 24-000123, 21-000105 and 17-000070 all return 200. `/sections` forwards `form_type`. The viewer (`src/store/sec.ts`) passes the listed row's `form_type`. Two adjacents are recorded below. |
| R15-RELEASE-007 | holds | `package.json` `lint` is now `eslint . && node scripts/audit-design-tokens.mjs`, which `ci-local` and `lint.yml` run. The audit exits 0 on the tree (373 files). Fresh off-grid classes `mt-[3px]`, `h-[37px]` and `py-2.5` make it exit 1. ROOT uses `import.meta.dirname`. |

## R15-UI-090: refutation detail

The command ran in the worktree at 68d5573a. `cd sidecar && ./.venv/bin/python3 -m pytest -q -s scratch test_vshard7_ui090.py` reuses `tests/test_quotes._freeze_locale_clock` and patches `provider_registry.get_quote` to provider yfinance.

```
RESULT RELIANCE.NS region=US now=2026-09-23T15:00Z last_trade=10:00Z -> eod     (correct)
RESULT ^NSEBANK   region=US now=2026-09-23T15:00Z last_trade=10:00Z -> eod     (correct)
RESULT ^CNXIT     region=US now=2026-09-23T05:00Z (NSE open)       -> live    (correct)
RESULT MSFT       region=IN now=2026-09-23T05:00Z last_trade=09-22 20:00Z -> eod (correct)
RESULT BHP.AX     region=US now=2026-09-23T15:00Z last_trade=06:00Z -> live   (ASX closed 9h)
RESULT 7203.T     region=US now=2026-09-23T15:00Z last_trade=06:00Z -> live   (TSE closed)
RESULT ^N225      region=IN now=2026-09-23T15:00Z last_trade=06:00Z -> live   (TSE closed)
RESULT HSBA.L     region=US now=2026-09-23T17:00Z last_trade=15:30Z -> live   (LSE closed 16:30Z)
```

The code path is `sidecar/services/locale.py` `instrument_region`, which is documented as "anything else trades on the US calendar". `routers/quotes.py _label_freshness` then calls `freshness_for(region, …, intraday=True)`.

These listings are reachable. The live `/quotes/BHP.AX`, `/quotes/7203.T`, `/quotes/HSBA.L` and `/quotes/^N225` on :52607 all return 200 from yfinance, with currency AUD, JPY, GBp and JPY respectively. The watchlist and chart gate the live-tick flash on `isLiveQuote(freshness === "live")`.

This is the same residual the batch-9 verifier flagged for BHP.AX. The refutation audit named it too (".AX and other foreign listings onto the US calendar"), but its acceptance test pinned only the Indian indices.

## Adjacent findings

1. **Near AGENT-092 (medium): a halted round's `publish_brief` is still delivered.** In the scratch run, round 2 emits `publish_brief` together with the token-ceiling halt. Dispatch records only round 1's `write_note`, yet `row.brief` is still `{symbol: MSFT, title: 'halted brief'}`. `run_manager.py` stores `brief` on `tool_use` (the `name == "publish_brief"` branch), not on dispatch. `delegate-runs.ts:282-286` then enqueues it as a `publish_brief` proposed change. This is the same announced-but-undispatched class as AGENT-092, on the brief field instead of `host_actions`.
2. **Near DATA-114 (medium): a transport failure on the walk-back day still returns 502 while an older good day is cached, and that day is re-probed on every request.** Scenario: today (Tue) is 404, which is normal before the close. Monday's request raises a transport error. Friday is cached. The result is `[None, None, None]`, with Monday probed on each of the 3 requests. The cause is `option_chain.fetch_latest_fo`: `if status == "failed": return None`. Only today's probe is negative-cached. Evidence: `oc114.out`.
3. **Near LEAD-010 (medium): every 10-Q opens blank with no stated reason.** For AAPL 0000320193-26-000020 and MSFT 0001193125-26-191507, `/sec/filings/{acc}?form_type=10-Q` returns 200 with `sections: []`. The raw sec-edgar-mcp `get_filing_sections` payload for the 10-Q is `{"sections": {"has_financials": true}}`, with no text. `FilingViewer.tsx` then renders an empty nav and "No section selected.", with no explanation beyond the EDGAR link. 10-Ks, by contrast, return 2 sections (Business and Risk Factors, 10,000 characters each).
4. **Near LEAD-010 (low): an unhinted lookup of an older 10-Q returns 404.** `/sec/filings/0001193125-10-090116?identifier=MSFT` with no `form_type` returns 404 `not_found`. With `form_type=10-Q` it returns 200 after 23 seconds. The filing is row 50 of MSFT's 10-Q list, and the unhinted periodic pass only covers 40 rows. Agent `sec_filing_content` calls without a hint take this path.
5. **Near RESEARCH-002 (low): the marker fallback reads a negated reason as agree.** `_parse_verdict('Not verified - no source confirms')` and `'I cannot verify this; no source confirms it'` both return `agree`. With no verdict word present, the `_AGREE_MARKERS` substring scan matches "confirms" inside a negation.
6. **Near DOCS-018 (low): a factual slip in the rewritten §3.3 yfinance bullet.** The bullet (CURRENT_STATE.md:340, commit 190b380e) says "(fundamentals and any other region still hit it first)". In code, `openbb-mcp` is rank 10 for fundamentals, statements and analyst_rating with no region gate. `/health` reports "fundamentals: openbb-mcp (yfinance fallback)", and `/fundamentals/MANIKA.NS` is served by openbb-mcp.
