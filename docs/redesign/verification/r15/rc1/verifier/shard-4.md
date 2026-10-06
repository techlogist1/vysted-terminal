# rc1 adversarial sample verifier, shard 4

Candidate sha 81fbfe910d472ecd154fa62e42d86bce213a697e (worktree rc1-4c6dfe8-fix-int, read-only). Own sidecar on :52604 (data dir copied from rc1-seed-data). The shared MCPs were on :52153/:52154. I did not restart the shared stack. The sidecar is now stopped. Evidence is in `verifier/shard-4-evidence/` and findings are in `findings/rc1-vshard-4.json`.

## Picks audit

14 of the 24 picked ids do not exist in the register at the candidate (652 entries). The highest ids are DATA-115, AGENT-093, RESEARCH-042 and UI-094. Those 14 are recorded as inconclusive (id absent).

The 10 picks that do exist are not members of their named sets. I verified each of them on its own claim:
- DATA-104, DATA-106, AGENT-087 and AGENT-089 are status `open` at the candidate, so they are not certified claims. They are recorded as inconclusive, with their current state noted.
- For each missing id, I substituted the first fixed entry of the named set that was not already picked, in PLAN table order.

## Verdicts

| id | verdict | how checked | evidence |
|---|---|---|---|
| R15-DATA-114 | holds | in-process `d114.py` against `services/option_chain.fetch_latest_fo` | today fails, 09-24 cached: returns 2026-09-24 after one probe. A burst re-probe makes no upstream call. |
| R15-DATA-032 | holds | `curl :52604/earnings/{INFY.NS,AAPL}/estimates` | median and stddev are null. INFY eps analysts 8, revenue analysts 16. |
| R15-DATA-034 | holds | in-process `fundamentals_from_v7` with 1.5 / 30% / 26% yield rows | yield withheld, field_meta reason set, provider yahoo-v7-batch |
| R15-DATA-037 | holds | `curl ':52604/history/BTC%2FUSDT?asset_class=crypto&range=1mo|1y|5y'` plus SOL and ETH 5d/1h | 30 / 365 / 1826 bars from ccxt:binance. ETH 5d 1h gives 120 bars. |
| R15-DATA-104 | inconclusive | status open at candidate | earnings get_upcoming still gathers with no semaphore |
| R15-DATA-106 | inconclusive | status open | enrich_nse_sectors still writes rec["industry"] |
| R15-AGENT-087 | inconclusive | status open | agent-mode.ts docblock still says four modes |
| R15-AGENT-089 | inconclusive | status open | PLAN_ACTIONS lacks close_panel and focus_panel |
| R15-AGENT-046 | holds | llama3.1:8b live invoke through vy.py (`a046-run1.jsonl`) plus agent_runtime code read | 3 host actions got distinct `call_<uuid>` ids. The ledger uses take(). |
| R15-DATA-070 | holds | in-process `d070.py` (RSS with undated and garbage dates) plus live `/news` | undated items get published_at None and sort last. Live /news had 40 items, none null. |
| R15-CODE-AGENT-004 (sub b8W5) | holds | `ca004.py`, a fake Gemini chunk | 1000 prompt, 800 candidates and 6000 thoughts give output usage 6800 |
| R15-CODE-AGENT-008 (sub b9W1) | holds | live research invoke (`research-run1.jsonl`) | 6 sources, mode fast, depth quick, unique `__autobrief` id |
| R15-RESEARCH-027 (sub b9W1) | holds | same run plus sidecar log | the gather took about 6.5 s. The price and fundamentals legs were cut at 6 s while Yahoo was throttled. |
| **R15-RESEARCH-028 (sub b9W2)** | **refuted** | `/search/searxng/status` shows degraded. Live research brief plus in-process `r028.py`. | The web_search tool returns reason `searxng_degraded`, but `research/fast.py _web_round` copies `reason` only when `not web_ok`. The brief ends up with backend keyless-fallback and web_reason None, so the "set up Unlimited local research" nudge still shows. |
| R15-LIFECYCLE-018 (sub b9W2) | holds | code read (app.py:144 warm_detect; searxng_manager flag after refresh under _detect_lock) | Minor: the web_search.py:84 comment is stale ("instant in-process read"). |
| R15-DATA-048 (sub b9W3) | holds | `curl :52604/fundamentals/KPITTECH.NS` | roce 0.2127 is labelled derived and has a basis_note |
| R15-DATA-054 (sub b9W3) | holds | fundamentals TATAELXSI.NS and KPITTECH.NS | TATAELXSI is standalone (screener consolidated ends Mar 2015). KPITTECH is consolidated, provider exchange-filings. |
| **R15-DATA-055 (sub b9W3)** | **refuted** | live MPIMANIPAL.NS quote and fundamentals (listed 2026-09-17) run through `derive_semantics` | fifty_two_week_change is labelled '52-week price change (Yahoo)', basis 'trailing 52 weeks', display 4.29%. drawdown_from_high is labelled 'Below 52-week high'. brief-blocks.tsx has no since-listing logic; only EquityOverviewPanel has it. |
| **R15-DATA-061 (sub b9W4)** | **refuted** | curl during the Yahoo throttle window (`d061-evidence.txt`) | /earnings/{HDFCBANK,TCS}.NS/estimates return 502 provider_error. /fundamentals/HDFCBANK.NS/income returns 200 with empty periods (record_success). /fundamentals/HDFCBANK.NS returns 429 rate_limited. A direct probe showed income_stmt (0,0) and calendar YFRateLimitError. |
| **R15-DATA-066 (sub b9W4)** | **refuted** | cold 20-name /quotes batch with concurrent single-quote and /history calls (`d066-evidence.txt`) | The warm EOD cache holds (0.002 s). During the cold batch, a cached RELIANCE.NS single quote took 5.5 s (one 30 s timeout) and /history took 14.3 s. `_Throttle.wait` still sleeps inside the to_thread worker, so the fix_shape step "throttle wait off the executor" was not delivered. |
| R15-DATA-062 (sub b9W4) | holds | `/quotes?symbols=RELIANCE.NS,...,BOGUS.NS` | the requested spelling is echoed. A failed symbol is absent and the watchlist marks it unavailable. |
| R15-UI-016 (sub b9W5) | holds | code read (page.tsx single keydown dispatcher, resolveKeyboardAction, registerAction users) | every default id has a handler |
| R15-CODE-FRONTEND-016 (sub b9W5) | holds | code read | no hardcoded metaKey remains in CommandPalette, ChatSidebar or AgentDock. Letter keys are shift-strict. |
| R15-UI-027 (sub b9W5) | holds | code read | comboFromEvent emits `mod` and conflicts() compares resolved chords |
| 14 missing ids (RESEARCH-068, AGENT-096, AGENT-098, RESEARCH-074, RESEARCH-076, DATA-124, DATA-126, DATA-116, DATA-134, DATA-136, DATA-138, UI-098, UI-100, UI-102) | inconclusive | `jq` over vysted-r15-register.json | the id is absent from the register at the candidate |

## Adjacent (fresh-variant) defects

- medium, near DATA-032: the INFY.NS revenue_estimate_mean is 491,180,745,790, which is INR-sized, but it is labelled revenue_currency USD (taken from financialCurrency). Annual totalRevenue is 20.3B USD. This also fails the R15-DATA-113 claim.
- medium, near DATA-048: derived ROCE and ROE diverge from screener.in (KPITTECH ROCE 21.3% vs 26.3%, ROE 16.5% vs 20.9%). The formula uses period-end capital with no average and no witness.
- low, near DATA-114: when an older day fails, the walk stops. With today 404, D-1 failed and D-2 cached, the result is None (script B gives `(None, ['2026-10-01','2026-09-30'])`).
- low, near DATA-054: the listing_date field_meta provider is `yfinance`, but the value comes from the NSE master (symbol_resolver.nse_listing_date).
- low, near UI-027: on macOS the recorder records Option+1 as `alt+¡` (it uses event.key). conflicts() misses the clash with alt+1 (agent.mode.agent), which wins through the event.code fallback, so the remap never fires.
- low, near DATA-061: `/macro/GDP?provider=bogus` returns 502 provider_error "Retry" instead of a 4xx.

## Harness notes

- vy.py refused port 52604, so I ran a scratch copy with the port check relaxed. The spend guard was untouched and only local Ollama was used.
- The local-model lock dir `/tmp/vysted-r15-ollama.lock` disappeared during my second hold; another process removed it. My run finished, and no lock_timeout occurred.
- Yahoo throttled the shared egress IP for about 09:35 to 09:50 IST. That window produced the DATA-061 evidence and also truncated the RESEARCH-027 price and fundamentals legs, which was the intended timeout behaviour.
