# rc1 verdict: FAIL

**Candidate:** `1d6511c89bb27f1785f7af4d2290983b2852d70a`
**Verifier:** rc1-verifier (Opus 5.5), who never tags.
**Sheet:** `docs/redesign/verification/R15_GATE_RC1.md`
**Evidence:** `EV/` = `docs/redesign/verification/r15/rc1/verifier/rc1-verifier-evidence/`
**Findings:** `findings/rc1-verifier.json`

**Environment**
- Sidecar on `:52312`, booted from the read-only candidate worktree source.
- Data from a copy of rc1-seed-data (`scratchpad/rc1-data-rc1-verifier`).
- The shared stack (:52152) was used for GETs only.
- Models: llama3.1:8b (Ollama). OpenAI spend this session: $0.2011, under the guard.

Each item below gives its result, then the evidence excerpt it rests on.

---

## 1. Register criterion: FAIL

**Evidence:** `EV/register-census.txt`, the census of the working-tree register (631 entries, 410 c/h/m).

```
NONCONFORMING 11
   ('R15-AGENT-017', 'high', 'open', ...  'The shipped default chat model (DeepSeek V4 Flash via OpenRouter) returns content_filter w')
   ('R15-LEAD-010', 'high', 'fixed but not certified in stage-c', ... 'SEC filing viewer 404s a 10-K it just listed ...')
   ('R15-AGENT-049', 'medium', 'open', ... 'Native web search has no per-run cap off Anthropic ...')
   ('R15-LEAD-028', 'medium', 'open', ... 'BSE scrip-code addressing (e.g. 506597.BO, 544774.BO) 404s on data routes ...')
   ('R15-RELEASE-007', 'medium', 'open', ... 'The design-token audit ... runs in no script, gate or wo')
   ('R15-UI-088', 'medium', 'open', ... 'In-webview drag gestures ... have no aut')
   + 5 not_a_defect rows without rationale, all of which carry a stage-c concur:
     "not_a_defect c/h/m in 4 areas not in concur: []"
```

The register committed at the candidate sha itself has 29 nonconforming rows, including R15-AGENT-007 (high, open).

R15-LEAD-028 reproduces at the sha (`EV/lead028-open.txt`):

```
GET /quotes/506597.BO -> 404 {"detail": "The data provider has no data for this symbol or series — check the symbol.", "code": "not_found"}
GET /history/544774.BO?range=1mo&timeframe=1d -> 200 {"symbol": "544774.BO", "provider": "none", "bars": 0}
```

## 2. Gate 8, no trading path: PASS (not refuted)

`EV/openapi-paths.txt`: 111 routes. None of them concerns orders, brokers, the kill switch or the audit log. The only portfolio route is:

```
58	GET    /portfolio/positions
```

`EV/rg-summary.txt`:

```
place order: code-files=       0 ...
buy now: code-files=       0 ...
execute trade: code-files=       0 ...
paper trading: code-files=       0 ...
simulated account: code-files=       0 ...
```

None of the code hits in `EV/rg-code-hits-a.txt` (113 lines) is a trading path:
- `broker`, `margin` and `live mode` hits are negations, D81 removal notes, or false positives such as CSS margin.
- `leverage` hits are the idiom "highest-leverage" or a balance-sheet screen preset ("low leverage").
- `demat` hits are exchange fixture text.
- One residue is the keychain key name `broker:_meta:first-launch-tos`.
- The `types/plugin.ts` field is the locked-contract exemption.

`EV/tool-lists.json` holds 56 catalog tools and 40 MCP tools. None of them places an order or touches a broker.

One residue remains (finding `rc1-verifier:21`, low, inert), in `EV/gate8-plugins-list.json`:

```
{"plugin_id":"tradesa-v2","enabled":true,"installed":true,"settings":{},"granted_secret_ids":[]}
```

## 3. Gate 8, tracked portfolio: PASS

`EV/portfolio-roundtrip.json` records the real PortfolioPanel and stores, driven against my sidecar with only the Tauri IPC stubbed.

**Add, export and delete.**

```
01-store-after-add [{"symbol": "RELIANCE", "quantity": 10, "costBasis": 1100, ...}, {"symbol": "AAPL", "quantity": 5, "costBasis": 180, ...}]
05-export path .../scratchpad/rc1-data-rc1-verifier/exports/csv/vysted-portfolio-portfolio.csv
Symbol,Quantity,Cost basis,Asset class,Currency,Price,Market value,P&L,P&L %,Weight %,Note
RELIANCE,10,1100,equity,INR,1219.2,12192,1192,10.836363636363638,,
AAPL,5,180,equity,USD,335.9200134277344,1679.6000671386719,779.6000671386719,86.62222968207465,,
06-store-after-delete []
08-blob-after-delete {"list": [{"id": "default", "name": "Portfolio", "holdings": []}], "activeId": "default"}
```

**Agent write under ASK.** The proposal came from llama3.1:8b (`EV/agent-02-proposed-action.json`, `portfolio_add_position` TCS 5 @3500).

```
a2-pending-change {"status": "pending", "kind": "data-write", "title": "Add 5 TCS @ ₹3,500 to the portfolio", ...}
a4-blob-and-ledger-while-pending {"blobUnchanged": true, ..., "ledgerUnchanged": true, "ledger": []}
a8-blob-after-accept {... "holdings": [{"symbol": "TCS", "quantity": 5, "costBasis": 3500, ...}]}
a9-ledger-after-accept []
```

## 4. ci-local: PASS

`r15/rc1/fix-r2/ci-local.log`, at the sha:

```
769:=========== 3150 passed, 1 skipped, 4 warnings in 201.51s (0:03:21) ============
770:EXIT=0
834:      Tests  1825 passed (1825)
862:test result: ok. 19 passed; 0 failed; ...
1257:=========== 3150 passed, 1 skipped, 4 warnings in 195.81s (0:03:15) ============
1258:EXIT=0 2026-09-25T02:59:52Z
```

## 5. Smoke: PASS

`r15/rc1/fix-r2/smoke.log`:

```
17:[smoke] vysted-sidecar /agents roster OK (13 agents).
18:[smoke] vysted-sidecar /mcp/status OK (ready=true, toolCount=40).
30:SMOKE_EXIT=0 2026-09-25T02:55:29Z
```

## 6. Agent scenarios: FAIL

**The transcripts are incomplete.** From `r15/rc1/scenarios/*.jsonl`:
- 11 of 20 OpenRouter runs end in `Upstream error from Nvidia: Service temporarily ...`. The affected runs are rb1, rb2, sc2-b, sc2-thread, sc3-a/b/thread, sc4-a/b/thread and sk1.
- `ollama-sc1-tcs-pe-a.jsonl` is 0 bytes.
- sc3 and sc4 have no completed run on either lane.

**The transcripts predate the fix rounds.** File mtimes run from 05:26 to 05:42 IST. The first fix-round commit, 23f2ab34, landed at 07:11 IST and the candidate at 08:15 IST.

**rc1-scenarios:5 reproduces at the sha** (`EV/unclosed-sc5-sify-llama.stdout`, llama3.1:8b):

```
... ADR represents is 2, since the SIFY ADR has 1:2 ratio.
```

The true ratio is 1 ADS = 6 shares, and no tool field carries a ratio.

## 7. Owner-drives: FAIL

Raw evidence exists for all 8 groups (`surface/*/rc1/`). My spot-checks hold for:
- settings-plugins (`EV/drive-spot-settings-plugins.txt`: fake keys come back invalid or unauthorized, a `../evil-rc1v` name is saved encoded and then deleted with 204, and a long name gets 400);
- the screener's zero-evaluated case;
- the portfolio (item 3).

Replaying the screener drive on india-all exposes a defect the drive missed (`EV/drive-spot-screener-india-all.json`):

```
{'evaluated_count': 3951, 'result_count': 200, 'partial': True}
[('MANIKA.NS', None), ('RELIANCE.NS', 16551566639104.0), ('HDFCBANK.NS', 11237145039544.799)]   # sort_by market_cap desc
```

It reduces to a three-row repro (`EV/new-manika-sort-custom.json`; `EV/new-manika-fundamentals.json` shows `currency: None, provider: openbb-mcp`):

```
"rows":[{"symbol":"MANIKA.NS", ... "market_cap":null, ... "currency":"INR"}, {"symbol":"RELIANCE.NS", ...
```

The cause is at `screener.py:818-826` (`EV/code-excerpts.txt`). The sort key groups rows by `fundamentals.currency`, and that currency is re-stamped only after sorting. So the empty currency `''` sorts ahead of `INR`, and a null value ranks first. This is recorded as `rc1-verifier:15` (medium).

## 8. Fixed-name battery: FAIL

The census covers `r15/rc1/battery/raw/**` against the register's 376 fixed c/h/m ids:
- 160 of those ids have no raw output: 1 critical, 48 high, 109 medium and 2 low.
- `set-12/` and `set-46/` are empty.
- set-37, set-45, set-55 and set-57 are absent.

`r15/rc1/findings/` holds `rc1-battery-{0,1,2,4,6,7}.json` only. There is no file for workers 3 and 5.

## 9. Data packs: PASS

Recount of `r15/rc1/battery/collected/*.json`:

```
24 packs, 24 complete: True
283 calls  Counter({200: 263, 502: 16, 429: 4})   sidecar http://127.0.0.1:52313 (x24)
```

The 502s are environmental and reproduce at the sha (`EV/datapack-shareholding-probe.txt`):

```
GET /disclosures/shareholding?symbol=DAL&exchange=BSE -> 502 {"detail":"The data provider returned an unexpected response.", ...}
GET /disclosures/shareholding?symbol=RELIANCE -> 200 {"symbol":"RELIANCE","count":22, ...}
```

The sidecar log shows `bse shareholding: index HTTP 403`, which is logged as `rc1-verifier:22` (low).

The rc1-datapack:1 fix holds: `EV/datapack1-vertex-fundamentals.json` and `EV/fixloop-sify-fundamentals.json` both report pe unavailable with the reason "P/E not meaningful for a loss-making company".

## 10. Fix loop closed: FAIL

**Not closed:**
- **rc1-scenarios:5** (high). See item 6.
- **rc1-fix-r2-triage:1** (medium). It has no disposition in the fix loop and is live at the sha (`EV/fixr2-triage1-wit-estimates.json`):

  ```
  "revenue_estimate_mean": 244246846490.0, ... "revenue_analyst_count": 8, "currency": "USD", "provider": "yfinance"
  ```

  This is Wipro's INR revenue labelled USD.

**Concurred, rejected as not defects** (each re-checked at the sha):
- **rc1-scenarios:1 (SIFY).** `EV/fixloop-sify-fundamentals.json` shows `financial_currency: INR`, and price_to_sales is withheld with a reason.
- **rc1-scenarios:2 (ELCIDIN).** `EV/fixloop-elcidin-fundamentals.json` flags the 52-week range 102210 to 137000, with the reason citing the NSE+BSE range 87,003 to 144,500.
- **rc1-scenarios:3 and 4.** A staged notice was emitted, and 106,505 was never served.
- **rc1-drive-portfolio-notes:2.** This was harness drift.

**Not reproduced, open:** rc1-drive-onboarding-stranger:1 did not reproduce in 2 of 2 runs (`EV/unclosed-onb1-zomato-llama*.jsonl`). The model answered "not available at this time. We couldn't retrieve its price data." That fits the fix but does not prove closure.

**Tier-4 deferral accepted:** rc1-battery-4:1 (DECISIONS_FOR_OPERATOR.md §4.1).

## 11. GUI round: DEFERRED (allowed)

`r15/rc1/gui/presence.log` has a single line:

```
2026-09-25T03:18:04Z idle=6609 front="LSDisplayName"="Ghostty"
```

`docs/screenshots/vr15-rc1/` does not exist, so no GUI id is certified. The code fixes for the 9 ids are present, which I spot-checked. These stay needs_gui:

R15-CODE-AGENT-001, R15-LIFECYCLE-001, R15-LIFECYCLE-008, R15-UI-009, R15-UI-022, R15-UI-025, R15-UI-050, R15-UI-083, R15-UI-084

## 12. Adversarial sample: FAIL (14 of 14 refuted at the sha)

**R15-RESEARCH-002** (critical), `EV/inproc-refutations.txt`:

```
'Verdict: UNVERIFIED - no source confirms the 23% operating margin.' -> agree
'The claim is UNVERIFIED; nothing I found confirms the 23% margin.' -> agree
```

**R15-RESEARCH-007** (high), `EV/inproc-refutations.txt`:

```
https://ir.hotpennypicks.net/2024/xyz -> 1
https://investors.github.io/pump -> 1
https://www.investors.com/news/technology/nvidia-stock-buy-now/ -> 1
```

**R15-AGENT-019** (high), `EV/inproc-refutations.txt`:

```
'Can you log 10 TCS at 3400 in my portfolio?' -> read READ-ONLY
'Why not trim my INFY holding to 5 shares?' -> read READ-ONLY
```

**R15-AGENT-027** (medium), `EV/inproc-refutations.txt`:

```
openai 429 -> insufficient_credit | Your OpenAI account is out of credit or quota.
ollama ReadTimeout -> network | Could not reach Ollama — check your network.
```

**R15-AGENT-003** (high), `EV/agent003-rerun.txt`:

```
halt yielded [... 'price_data', 'fundamentals', 'write_note', 'price_data', 'fundamentals', 'write_note'] dispatched [3 ids]
1 failed, 1 passed
```

**R15-DATA-002** (high), `EV/data002.txt` and `EV/code-excerpts.txt`:

```
history AMAL (bare, region IN header) -> AMAL nse_direct ... close 687.65
CommandPalette.tsx:380-395  onSelect={() => { loadSymbolIntoChart(c.symbol); onClose(); }}
```

The US AMAL row is charted as Amal Limited (NSE).

**R15-DATA-043** (medium), `EV/data043.txt`:

```
limit=1 -> rows [('RELIANCE.NS', 'INR', 16551566639104.0)]  coverage "screened 2 of 2 — 0 unavailable"
```

The `spans INR, USD — ranked within each currency` note is dropped.

**R15-DATA-059** (medium), `EV/probes-059-068-090.txt`:

```
resolve q=SIFY -> {"symbol": "SIFY", ..., "isin": null, "former_name": null, ...}
```

**R15-DATA-068** (medium), `EV/probes-059-068-090.txt`:

```
GET /fundamentals/AAPL/ratings keys: [... 'target_mean']   # no as_of
```

**R15-UI-090** (high), `EV/probes-059-068-090.txt`, taken at 09:29 IST during NSE hours:

```
quote %5ENSEI: {'provider': 'yfinance', 'freshness': 'eod', 'market_state': None}
```

**R15-LEAD-010** (high), `EV/lead010-cold.txt`:

```
GET /sec/filings/0000950170-23-014423/sections?identifier=MSFT -> 404
GET /sec/filings/0000950170-24-048288/sections?identifier=MSFT&form_type=10-Q -> 404
```

The same filing returns 200 only on the non-sections route with a form hint.

**R15-DOCS-017** (medium), `EV/docs017-018.txt`:

```
'506': 1 ['`sp500` (full S&P 500 — 506 symbols ...']   sp500.json entries: 503   'india-all': 0
```

**R15-DOCS-018** (low), `EV/docs017-018.txt`:

```
'nse_direct': 0   'no-key default': 1 ['- **`yfinance_provider.py`** — no-key default for equities.']
```

**R15-CODE-PLATFORM-013** (low), `EV/code-excerpts.txt`. At `SettingsPanel.tsx:1936-1941`, the Modules toggle writes the module map only. At `marketplace.ts:150-175`, the Marketplace writes the runtime and `plugins.db`.

---

## Sha to tag

The only tree this gate evaluated is `1d6511c89bb27f1785f7af4d2290983b2852d70a`. The verdict is FAIL, so it is **not** to be tagged as rc1.

Running `git merge-base --is-ancestor 1d6511c8 004-r4-experience-rebuild` returns false. Branch 004 (29b9ae9b) lacks the fix-round code: 23 non-doc files differ, including `src/modules/portfolio/PortfolioPanel.tsx`.

Any rc1 tag must name exactly the sha that a passing gate verified. If it names any other tree, the gate re-runs.
