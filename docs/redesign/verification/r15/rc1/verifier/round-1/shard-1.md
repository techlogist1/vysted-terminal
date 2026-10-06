# RC1 adversarial sample verifier: shard 1 (rc1-vshard-1)

Candidate `1d6511c89bb27f1785f7af4d2290983b2852d70a`. I ran my own sidecar from the read-only scratch worktree on :52601, with a copy of the seed data (`rc1-data-rc1-vshard-1`). It has been stopped; its sleep pid was 97276.

Models: local Ollama llama3.1:8b first. Where llama3.1:8b could not produce a valid tool call (AGENT-011, three attempts), I used local qwen2.5:7b. No OpenRouter or OpenAI calls were made, so nothing was spent.

`scripts/r15/vy.py` refuses non-GET calls outside ports 52100-52399. For :52601 I used a scratch `inv.sh` that sends the same payload vy.py builds: provider ollama, no key, `X-Vysted-Region: IN`, `X-Vysted-Research-Tier: tier_a`, mode agent.

Raw evidence is in `shard-1-evidence/`.

| id | verdict | one line |
|---|---|---|
| R15-RESEARCH-007 | **refuted** | Original holds, but the host-prefix rule ranks `investors.com` (IBD news) and any `ir.`/`investors.` subdomain outside a 7-entry denylist as PRIMARY. IBD then takes [1] over Reuters. |
| R15-RESEARCH-008 | holds | The keyless chain is bounded by a 6 s deadline per engine. With DDG hung, Brave answers in 7.0 s. Both llama runs returned results with no timeout. |
| R15-DATA-045 | holds | 12 redirect variants were all blocked on every lane, and the loopback canary was never fetched by sidecar code. |
| R15-LEAD-002 | holds | Warm /fundamentals takes 1.1–2.5 s across 8 IN names. The ownership witness is cached and costs 1.1–1.8 s cold. |
| R15-RESEARCH-011 | holds | A split merged from BSE keeps its `BSE shareholding filing, <BSE quarter>` basis in the semantics fact, the conflict and the /fundamentals gate flag. |
| R15-RESEARCH-013 | holds | The provider badge follows the exchanges that served the data: nse+bse, bse (BSE-only listings), nse (BSE lane down). |
| R15-AGENT-011 | holds | run_custom_backtest fires a synthetic `open_panel(run_id)`, and GET /backtest/runs/{id} returns the full result. The delegate run carries the same host action. |
| R15-UI-090 | **refuted** | Original holds (AAPL reads eod during NSE hours), but ^NSEI/^BSESN/VOD.L/bare-symbol IN ETFs served by yfinance are dated on the US calendar. They read 'live' after their own exchange closes, and the ^NSEI live tick reads 'eod' during NSE hours. |
| R15-AGENT-020 | holds | read_notes plus the preamble excerpt work: llama called read_notes(RELIANCE) and answered a question on a non-focused DIXON note. There is a low-severity scope-suffix edge case (finding 3). |
| R15-DATA-026 | holds | The financial_statements capability returns quarterly data. DHANBANK's 6 quarters include 2026-06-30, and net income matches screener.in. |

## R15-RESEARCH-007: refuted

**Original repro holds.** `domain_tier(medium.com/investor-diary/...)` returns 3 and `domain_tier(someblog.wordpress.com/ir/...)` returns 3. `rank_sources([Reuters, Blog])` returns `['Reuters','Blog']`, and the priority note is `tier-1 press: [1]`.

**The variant still breaks it.** `finance._looks_like_ir` treats any host that *starts with* `ir.`, `investor.` or `investors.` as a company IR site, with only a 7-entry platform denylist as the exception:

```
https://www.investors.com/news/technology/nvidia-stock-buy-now/ 1   <- Investor's Business Daily (news; title confirmed live)
https://ir.hotpennypicks.net/2024/xyz-to-the-moon 1
https://investors.github.io/pump 1
https://ir.blogspot.in/post 1          (denylist has blogspot.com only)
https://ir.tumblr.com/post/1 1
https://investors.wixsite.com/tips 1
rank_sources([Reuters, IBD]) -> ['IBD', 'Reuters']
priority_note -> 'primary record (exchange/regulator/filings/IR): [1]; tier-1 press: [2].'
```

This is the defect the entry's title describes: a non-primary page outranks Reuters, takes [1], and the synthesis prompt calls it the primary record. The fix only closed the path-marker route and a named list of platforms. Finding `rc1-vshard-1:1`.

## R15-RESEARCH-008: holds

- Direct engine timing: DDG FAIL (rate-limiting) in 0.2 s, Brave ok with 8 results in 1.2 s, Mojeek ok with 0 results in 1.0 s. The full chain answered from `keyless:brave` in 3.9 s.
- Variant, DDG hung (never returns): the chain answered from Brave in 7.0 s. With all three engines hung it gave an honest SearchError after 12.0 s. Both are under the 25 s tool cap.
- Original prompt on llama (Dixon news): the `web_search` tool_use was answered, and the model listed 5 sourced URLs with no timeout message.
- Variant prompt (Kaynes order wins): 3 headlines with sources.
- Search relevance was mediocre (price pages), but that is outside this entry.

## R15-DATA-045: holds

A public redirector (`https://httpbin.org/redirect-to?url=`) pointed at a loopback canary on `127.0.0.1:52609`. Every case returned `blocked redirect to a non-public or non-http(s) URL`:

- 127.0.0.1
- 169.254.169.254
- localtest.me
- 127.0.0.1.nip.io
- decimal 2130706433
- [::1]
- [::ffff:127.0.0.1]
- 0.0.0.0
- file://
- a 2-hop public→public→loopback chain
- the PDF byte lane called directly
- the curl_cffi impersonation lane (`RedirectBlocked`)

`visit_for_research` returned `reason='blocked redirect…'`. The canary's access log shows only my own curl.

## R15-LEAD-002: holds

GET /fundamentals with `X-Vysted-Region: IN`, two rounds:

- Round 2 (warm): TCS 2.46 s, INFY 2.45 s, ITC 2.46 s, HDFCBANK 1.46 s, SBIN 1.50 s.
- Variant symbols the fix was not written against, round 2: DIXON 1.29 s, KAYNES 1.10 s, POLYCAB 1.57 s, ASIANPAINT 2.06 s.
- Round 1 (cold) was 15–17 s, but `get_exchange_ownership('ASIANPAINT.NS')` alone took 1.82 s cold and 1.10 s on the repeat. The witness is not what makes the cold path slow; the log shows yfinance getcrumb 429s and the openbb-mcp fallthrough.
- `correctness_gate._cached_witness` caches per listing for `_WITNESS_TTL_SECONDS`.
- No A/B against a base sidecar was run, so the cold-path comparison is not a verdict input.

## R15-RESEARCH-011: holds

In-process, `corporate_disclosures.get_shareholding` was stubbed with an NSE pattern for 2026-06-30 carrying `split_source='BSE'` and `split_as_of=2026-03-31`. That is the nearest-quarter branch.

- `_fetch_latest` wire: `institutions_source: 'BSE', institutions_as_of: '2026-03-31'`.
- semantics fact: `institutions_percent_exchange.basis = 'BSE shareholding filing, 2026-03-31'`. The promoter fact correctly stays `'NSE …, 2026-06-30'`.
- The conflict source is `BSE shareholding filing … as of 2026-03-31`.
- Variant (the /fundamentals route's `correctness_gate.reconcile_ownership`): the flag reads `disagrees with the BSE shareholding filing for the quarter ended 2026-03-31`.
- Live `/disclosures/shareholding?symbol=SIL` currently has no split (`split_source None`), so no live nearest-quarter case was available.

## R15-RESEARCH-013: holds

`fast._filings_leg` was run in-process with the real `corporate_announcements` tool:

- RELIANCE: sources `['NSE','BSE']`, provider `nse+bse`.
- BSE-only listings from the master ISIN diff: TITANBIO 524717 and VALIANT 526775 both have sources `['BSE']`, provider `bse`.
- Fake with the BSE lane down (sources `['NSE']`, errors set): provider `nse`.
- Edge case: an `ok` result with no sources gives provider `''`. No live path produces that was found, so it is not filed.

## R15-AGENT-011: holds

- `grep backtest/runs src/`: `src/store/backtest.ts:332 loadRun` is reached from `host-actions.applyIntentAsync` for `open_panel` with a runId. The proposed-changes store applies through `applyIntentAsync`.
- llama3.1:8b fumbled the tool call three times: a typo'd symbol `RELAINF.NS` (the run failed and correctly emitted no open_panel), a text-only call, and a stringified array.
- qwen2.5:7b (local): `run_custom_backtest(SPY…)` was followed at 58 s by a synthetic `tool_use open_panel {"panel":"backtest","run_id":"fe6cad40-…"}`. `GET /backtest/runs/fe6cad40-…` returned keys equityCurve (752 pts), trades (53), walkForwardSlices, metrics and request.
- Variant, a durable Delegate run (`POST /agents/copilot/runs`, QQQ ema(10)/ema(30)): status done, and `host_actions` contains the auto `open_panel` with `run_id f9e2a0a5-…`.

## R15-UI-090: refuted

**Original holds.** Live at 09:17 IST (NSE open, US closed), `GET /quotes/AAPL` returns eod (timestamp 2026-09-24T20:00Z). MSFT also returns eod. The PortfolioPanel now renders a StalenessBadge from `useMarketSession`.

**The variant still breaks it.** `locale.instrument_region` maps a quote to IN only when the provider is nse_direct/nse/bse or the symbol has a `.NS`/`.BO` suffix. Everything else goes on the US calendar. yfinance serves the caret Indian indices unsuffixed.

Live, 09:17 IST (NSE open):

```
{'symbol': '^NSEI', 'provider': 'yfinance', 'timestamp': '2026-09-25T03:47:07Z', 'freshness': 'eod'}
```

That is a current-session NIFTY tick labelled not live.

In-process, same code path, with `now` fixed:

```
^NSEI  yfinance  as_of 2026-09-24 @20:30 IST (NSE closed, US open) -> ('US', 'live')
^BSESN yfinance  @20:30 IST -> ('US', 'live')
VOD.L  yfinance  @22:00 IST (LSE closed) -> ('US', 'live')
NIFTYBEES yfinance (bare) @20:30 IST -> ('US', 'live')
```

A closed Indian index therefore reads 'live' on every surface that keys on freshness (chart and watchlist `isLiveQuote`) for the whole US session. `market_overview` uses `^NSEI`/`^BSESN` for IN, and the portfolio benchmark is `^NSEI`. This is the entry's defect class: the calendar is not the instrument's exchange. Finding `rc1-vshard-1:2`.

## R15-AGENT-020: holds

- Code: `read_notes` is a local handler over the snapshot's `__notes__`. `captureAgentContext` sends `__notes__`, and the preamble names the note scopes and quotes the focused symbol's note.
- In-process preamble: `User notes exist for: RELIANCE (read them with read_notes). Their note on RELIANCE: "My thesis: … EXIT if promoter pledge goes above 20% …"`.
- Original (llama, new chat, RELIANCE thesis note): the model called `read_notes {"scope":"RELIANCE"}`, then fumbled the next tool as text. The read path worked; the failure afterwards was the model's.
- Variant (llama, focused TCS, note on the non-focused DIXON, prompt using `DIXON.NS`): the model called `read_notes(DIXON)` and answered "Buy price: Below ₹12,000 – Target: ₹18,000", which is correct.
- Edge case (finding `rc1-vshard-1:3`, low): `_note_for(notes,'DIXON.NS')` returns empty, giving "The user has no DIXON.NS note", while a DIXON note exists. `write_note` scope is only uppercased, so a suffixed scope splits notes across two keys.

## R15-DATA-026: holds

- Route: `/fundamentals/DHANBANK/{income,balance}?period=quarterly` returns periods 2026-06-30 … 2025-03-31, so Q1 FY27 is present. The annual route returns 4–5 fiscal years.
- Variants: NVDA quarterly (5 periods), TITANBIO (BSE-only) quarterly (5), DIXON income quarterly (6, gap 2025-09-30 reported).
- Agent (llama, "DHANBANK revenue for each of the last 6 quarters"): called `financial_statements {"symbol":"DHANBANK.NS","statement":"income","period":"quarterly"}` and listed Jun-26 ₹212.51 cr … Mar-25 ₹177.32 cr, with Sep-25 marked not available.
- Checked against screener.in:
  - Net profit: 25/43/24/12/29 vs route 24.91/43.49/23.88/12.18/28.98.
  - Revenue: the route's bank `total_revenue` (212.51) equals screener's NII (449−272=177) plus other income (35). That is a definitional difference, not wrong data.
- DHANBANK quarterly cash flow is empty with no note. Indian filers report cash flow half-yearly, and DIXON quarterly cash flow returns 2 half-year periods, so this is not filed.

## Findings

`docs/redesign/verification/r15/rc1/findings/rc1-vshard-1.json` has three findings:

- `rc1-vshard-1:1`: regression, R15-RESEARCH-007, high.
- `rc1-vshard-1:2`: regression, R15-UI-090, high.
- `rc1-vshard-1:3`: new_defect, low.
