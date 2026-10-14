# rc1 gate round 4: VERDICT (rc1-verifier)

**FAIL.** Candidate `68d5573aff9a579af084dcbb124843f2aecff6e8`, the head of `worktree-agent-rc1-round-4-1006c6d-fix-int`, a fast-forward of `1006c6da694ede5776c3dabbd27b305aeb56b5ad`.

- The verifier never tags. 004 (`aaad38ac`) has moved past `1006c6da` with CHANGELOG.md, a script and evidence, so it cannot fast-forward to `68d5573`. The tagged tree must be `68d5573`, or the gate re-runs.
- Paths below are relative to `docs/redesign/verification/r15/rc1/round-4/` unless they are absolute.
- The sheet is `docs/redesign/verification/R15_GATE_RC1.md`. Findings are in `findings/rc1-verifier.json`.

## 1. Register criterion: PASS
Evidence: `verifier/own/register-at-68d5573.json`. Status counts: fixed 395, open 207 (all low), blocked_tier4 29, needs_gui 11, not_a_defect 5, removed_with_feature 14.
```
counts: {"raw": 887, "entries": 661, "rejections": 76, "critical": 16, "high": 119, "medium": 297, "low": 229}
open by severity: all 207 low (0 critical/high/medium)
```

## 2. Gate 8, no trading path: PASS (gate8_refuted = false)
Evidence: `verifier/own/openapi-paths-52312.txt`, `tools-lists.txt`, `g8-failclosed.out`, `g8-audit-orders.txt`, `g8-agent-order-attempt.stdout.txt` and `rg-*.txt`.
```
openapi routes: 111; grep -ciE 'order|trade|broker|kill|audit' -> 0
CATALOG 56
TOOL_SCHEMAS 56
KNOWN_TOOL_IDS 56
MCP 40
CASE execute_trade {"symbol":"MSFT","side":"sell","quantity":1} isHostActionMutation= false enqueue= staged accept= failed after= pending unknown action "execute_trade" holdings= 0
CASE market_order {"symbol":"NVDA","quantity":3} isHostActionMutation= false enqueue= staged accept= failed after= pending unknown action "market_order" holdings= 0
  audit_orders count: Error: in prepare, no such table: audit_orders
```

## 3. Gate 8, tracked portfolio: PASS
Evidence: `verifier/own/g8-portfolio-roundtrip.out`, `g8-exported.csv`, `g8-agent-gated-add.stdout.txt` and `g8-ledger-before.json`/`g8-ledger-after.json` (both []).
```
PNL_RENDERED +$2,161.70 (+72.06%) EXPECTED_PNL 2161.70
MSFT,10,300,equity,USD,516.1699829101562,5161.6998291015625,2161.6998291015625,72.05666097005209,100.00,
STORE_AFTER_DELETE []
I have proposed adding 5 shares of INFY.NS to your tracked portfolio at an average cost of 1500 rupees for review. Please review and accept this change in the proposal bar.
```

## 4. ci-local: PASS
Evidence: `fix-r1/ci-local.log`. Both runs EXIT=0 at 68d5573; pytest 3671 passed, 1 skipped.
```
=== ci-local run 1 start 2026-09-26T23:13:05Z at 68d5573aff9a579af084dcbb124843f2aecff6e8
      Tests  1849 passed (1849)
test result: ok. 19 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.02s
=========== 3671 passed, 1 skipped, 4 warnings in 205.76s (0:03:25) ============
=== ci-local run 1 EXIT=0 2026-09-26T23:23:07Z
=== ci-local run 2 (final) start 2026-09-26T23:23:18Z at 68d5573aff9a579af084dcbb124843f2aecff6e8
      Tests  1849 passed (1849)
test result: ok. 19 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.00s
```

## 5. smoke: PASS
Evidence: `fix-r1/smoke.log`. The production-bundle rehearsal PASSED at 64e9470e (`r15/stage-d/bundle-rehearsal/REHEARSAL.md`); cited, not repeated.
```
=== smoke start 2026-09-26T23:27:59Z at 68d5573aff9a579af084dcbb124843f2aecff6e8
=== smoke EXIT=0 2026-09-26T23:30:06Z
```

## 6. Agent scenarios: FAIL (product_defect)
Evidence: `scenarios/*-hosted-t{1,2,3}.stdout.txt`, graded pass^3 per scenario. The lane ran at 1006c6da.

| Property | pass^3 | Notes |
|---|---|---|
| read-back | 4/4 | brief, note, portfolio, watchlist |
| self-consistency | 4/4 | amal, reliance, sify, watchlist |
| skepticism | 1/4 | sk-smr passes |

The three skepticism failures:
- **sk-amal (t1-t3)** binds Amal Ltd silently. This is DATA-002: a concurrence note, blocked_tier4, decision 4.15.
- **sk-dal-t2** says "DAL is the ticker symbol for Delta Air Lines", then gives Rs-crore financials. Also DATA-002.
- **sk-sify-t2** is the ratio-guard mid-sentence leak (new, medium, rc1-verifier:2). It is reproduced at 68d5573 by `verifier/own/adv-ratio-guard-sim.txt`.

The local lane is single-trial. `sk-sify-local-t1` shows the same leak ("... sources. 6 ordinary shares."). `rb-brief-local-t1` concurs with rc1-fix-r1-recheck:2 and is filed under the LEAD-038 class.
```
=== ASSISTANT TEXT ===
The ADR-to-ordinary-share ratio is not available from this session's sources. This detail might not be publicly disclosed in the recent SEC documents for SIFY Technologies Ltd. 

The ADR-to-ordinary-share ratio is not available from this session's sources. 5 or The ADR-to-ordinary-share ratio is not available from this session's sources. 
---
HEAD 68d5573aff9a579af084dcbb124843f2aecff6e8
cmd: cd <candidate> && sidecar/.venv/bin/python scratchpad/rc1-verifier-r4/ratio_sim.py
WHOLE (one delta):       "The ADR-to-ordinary-share ratio is not available from this session's sources."
SPLIT after 'equals ':   "The ADR-to-ordinary-share ratio is not available from this session's sources. 6 ordinary shares, per the 20-F."
SPLIT token-like:        "The ADR-to-ordinary-share ratio is not available from this session's sources. 6 ordinary shares, per the 20-F."
_seg_at('One ADR of SIFY equals ',0).closed = True
```

## 7. Owner drives: PASS
All 8 `surface/*/rc1/round-4/` groups carry raw files. I spot-checked the screener and research-briefs drives on the own sidecar `:52312` at 68d5573; the requests were copied from `surface/screener/rc1/round-4/*-request.txt`.

Evidence: `verifier/own/drive-spot.sh`, `drive-spot.out` and `drive-spot-badkey.{jsonl,stdout.txt}`.

Agreement with the drive raw:
- custom-bare: 5/5 on both.
- zero-result: matched 0, "screened 49 of 50 — 1 unavailable", on both.
- universe counts: identical.
- search status: same shape.
- bad-key: same humanised message and action.
- malformed formula: the drive raw is the formula-validate shape; `/screener/run` returns a 422 naming '%'. Both are honest.
```
HEAD 68d5573aff9a579af084dcbb124843f2aecff6e8 date 2026-09-27T00:41:22Z sidecar :52312 (own, candidate source)
[HTTP 200 0.001973s]
[HTTP 422 0.001216s]
[HTTP 200 59.329342s]
### universe sp500
503 ['asset_class', 'id', 'label', 'symbols']
### universe nifty50
50 ['asset_class', 'id', 'label', 'symbols']
### universe crypto-top50
50 ['asset_class', 'id', 'label', 'symbols']
### universe nse-all
3506 ['asset_class', 'id', 'label', 'symbols']
### universe bse-all
5042 ['asset_class', 'id', 'label', 'symbols']
### universe india-all
5891 ['asset_class', 'id', 'label', 'symbols']
[HTTP 200 0.001592s]
[HTTP 200 6.292663s]
[   1.2s] error: {"kind": "error", "message": "The OpenAI API key was rejected \u2014 check it in Settings.", "action": "Re-enter the API key in Settings.", "detail": "Error code: 401 - {'error': {'me
```

## 8. Fixed-name battery: FAIL (harness_environment: battery-raw-missing)
Evidence: `verifier/own/battery-raw-check.txt`, computed over `battery/raw/**` against the register at 68d5573. 25 fixed ids have only NOT RUN raw, not the 3 the collator claimed. The battery ran at 1006c6da.
```
fixed at sha: 395
ids with a raw (non-NOT RUN) file: 370
fixed ids with no raw file: 25 ['R15-AGENT-053', 'R15-AGENT-057', 'R15-CODE-FRONTEND-001', 'R15-CODE-FRONTEND-005', 'R15-CODE-FRONTEND-016', 'R15-CODE-FRONTEND-018', 'R15-CODE-PLATFORM-012', 'R15-CODE-PLATFORM-013', 'R15-CODE-PLATFORM-053', 'R15-CROSS-PLATFORM-004', 'R15-DATA-031', 'R15-DATA-042', 'R15-DATA-100', 'R15-LEAD-033', 'R15-LIFECYCLE-002', 'R15-LIFECYCLE-003', 'R15-LIFECYCLE-009', 'R15-RESEARCH-026', 'R15-UI-016', 'R15-UI-029', 'R15-UI-030', 'R15-UI-038', 'R15-UI-058', 'R15-UI-086', 'R15-UI-092']
raw ids not fixed at sha: 0 []
```

## 9. Data packs: PASS
Evidence: `battery/collected/*` and `verifier/own/rej-datapack1-sify.json`. I concur with the rc1-datapack:1 rejection: the payload declares `financial_currency` INR beside a USD trading currency, so the INR-scale TTM figures are labelled honestly.
```
{"symbol":"SIFY","name":"Sify Technologies Limited","sector":"Communication Services","industry":"Telecom Services","sector_source":"yfinance","currency":"USD","financial_currency":"INR","ratio_price":13.35,"market_cap":967002176.0,"pe_ratio":null,"forward_pe":267.0,"peg_ratio":34.4591,"price_to_book":null,"price_to_sales":null,"ev_to_ebitda":null,"book_value":null,"dividend_yield":0.0,"dividend_p
```

## 10. Fix loop closed: PASS
Unclosed: []. Tier-4 deferred: []. I concur with all four rejections:

- **rc1-datapack:1.** Rejection upheld; see item 9.
- **rc1-drive-screener:1.** The tool path is correct: `write_screener_filters` returns `ok:true` with `status:dispatched`. Only llama3.1:8b's prose contradicts that result. Local-8B narration that disagrees with a correct tool result belongs to the operator-attended known-limitation class (LEAD-030/037/038, DECISIONS 4.9-4.12), not to a product regression. Raw: `surface/screener/rc1/round-4/06b-agent-screen-llama-auto.stdout.txt`.
- **rc1-drive-panels-layouts:1.** The "off-topic" crypto articles are about the Chainlink and Infosys partnership: 8 Infosys mentions and a NYSE:INFY ticker in the body. See `verifier/own/rej-panels1-article-bodies.txt` and `rej-panels1-news-infy.json`.
- **rc1-battery-9:1.** At 68d5573, `sidecar/services/agent_tools/deep_research.py` routes a raise from both `run_heavy_research` (ULTRA) and `run_iter_research` (DEEP) through the same `_loop_failed`, which returns `ok:false` with a stated `degraded_reason`. That fixes the RESEARCH-017 asymmetry the entry named: ULTRA losing the brief while DEEP degraded honestly. No brief is fabricated, so this is not a regression.

## 11. GUI round: DEFERRED (operator_attended)
SKIPPED because the computer-use grant does not cover the built app. needs_gui: R15-CODE-AGENT-001, LIFECYCLE-001, LIFECYCLE-008, UI-009, UI-022, UI-025, UI-050, UI-083, UI-084, DOCS-024, LIFECYCLE-040. All are operator-attended.

## 12. Adversarial sample (RUBRIC b): FAIL (product_defect)
Each refuted entry's own repro was re-run at `git rev-parse HEAD` = 68d5573aff9a579af084dcbb124843f2aecff6e8. Commands and outputs are in:
- `verifier/own/adv-curl.sh` / `adv-curl.out`
- `adv-inproc.txt`
- `adv-lead014.txt`
- `adv-lead004-*.json`
- `adv-agent055-ui015.txt`
- `adv-greps.txt`
- `adv-research027.out`
- `adv-agent001-kpit.*`
- `adv-elcidin-fund.json`
- `refuted-31-register.txt` (the entries' own repro text)

**Standing (own repro reproduces):**
- DATA-003 (critical)
- LEAD-022 (high)
- LEAD-014 (medium)
- LEAD-004 (medium)
- AGENT-055 (medium)
- DATA-053 (medium)
- UI-015, secondary clause only (low residual)

**Not standing** (own repro fixed; the fresh case is carried as an adjacent):
CODE-DATA-005, AGENT-001, DATA-063, DATA-015, LIFECYCLE-020, CODE-FRONTEND-015, UI-021, UI-031, CODE-FRONTEND-017, AGENT-043, RESEARCH-027, UI-058, AGENT-084, CODE-PLATFORM-021, DOCS-016, DATA-061, CODE-PLATFORM-017, UI-018, UI-090, RESEARCH-007, LEAD-031, AGENT-019, AGENT-053 and LEAD-039.

**Three-failure list:** none is refuted by its own repro. The AGENT-019 residual is rc1-verifier:12 (medium) and the LEAD-039 residual is rc1-verifier:13 (low).

**Adjacent HIGH confirmed:** arrange_layout `custom` raises TypeError (rc1-verifier:1 / rc1-vshard-9:1).

**Medium flat-AND group confirmed:** rc1-verifier:10 (`verifier/own/adj-agent043-flat-and.txt`).
```
### -H X-Vysted-Region: US http://127.0.0.1:52312/disclosures/shareholding?symbol=AMAL
{"symbol":"AMAL","count":104,"patterns":[{"symbol":"AMAL","quarter_end":"2026-06-30","quarter_basis":null,"promoter_percent":71.35,"fii_percent":0.0,"dii_percent":0.03,"institutions_percent":0.03,"public_percent":28.65,"public_basis":"incl. institutions","public_non_institutional_percent":28.62,"emp
## LEAD-022 _yahoo_symbol
BHP.AX -> BHP.AX
0700.HK -> 0700.HK
7203.T -> 7203.T
VOD.L -> VOD.L
2222.SR -> 2222-SR
SAP.F -> SAP-F
GGAL.BA -> GGAL-BA
OPAP.AT -> OPAP-AT
BRK.B -> BRK-B
fundamentals    placeholder-echo(all props)  reply='{"symbol": "string"}' -> ACCEPTED {"symbol": "string"}
fundamentals    placeholder-echo(required)   reply='{"symbol": "string"}' -> ACCEPTED {"symbol": "string"}
news            placeholder-echo(required)   reply='{}' -> ACCEPTED {}
price_data      placeholder-echo(required)   reply='{"symbol": "string"}' -> ACCEPTED {"symbol": "string"}
{"symbol":"NDTV.NS","name":"New Delhi Television Limited","sector":"Communication Services","industry":"Broadcasting","sector_source":"resolver","currency":"INR","financial_currency":null,"ratio_price":70.08,"market_cap":7906756608.0,"pe_ratio":null,"forward_pe":null,"peg_ratio":null,"price_to_book"
### http://127.0.0.1:52312/quotes/ELCIDIN?asset_class=equity
{"symbol":"ELCIDIN","price":103800.0,"change":-1030.0,"change_percent":-0.9825431651244874,"volume":8.0,"open":null,"high":null,"low":null,"prev_close":null,"currency":"INR","market_state":"CLOSED","timestamp":"2026-09-25T00:00:00Z","provider":"nse_direct","freshness":"eod"}
### http://127.0.0.1:52312/quotes/INFY.BO
{"symbol":"INFY","price":1000.95,"change":-8.149999999999977,"change_percent":-0.8076503815280921,"volume":8.12,"open":1000.0,"high":1003.6,"low":991.75,"prev_close":1009.1,"currency":"INR","market_state":"CLOSED","timestamp":"2026-09-25T00:00:00Z","provider":"bse","freshness":"eod"}
  "single-focus": { positions: {}, focus: "chart", maximize: "chart" },
  compare: { positions: {}, focus: "chart", maximize: "chart" },
  "compare-desk": {
  "single-focus": "technical",
  compare: "compare-desk",
                "layout:single-focus",
            &MenuItem::with_id(h, "layout:compare", "Compare", true, None::<&str>)?,
## UI-015 secondary clause: sec.searchCompanies catch
RAISED {'pattern': 'custom', 'panels': ['chart', 'news']} TypeError unhashable type: 'list'
RAISED {'pattern': 'custom', 'panels': [{'component': 'chart'}]} TypeError unhashable type: 'list'
```

## Four named areas
The counts, the before and after evidence, and the concurrence pointers are in the sheet. All eight not_a_defect and removed_with_feature ids in the areas have a concurrence in `r15/rc1/findings/rc1-verifier.json`:

| Id | Concurrence |
|---|---|
| AGENT-083 | :21 |
| DATA-080 | :22 |
| UI-041 | :23 |
| UI-047 | :24 |
| UI-059 | :25 |
| CODE-PLATFORM-001 | :18 |
| UI-042 | :19 |
| UI-043 | :20 |

The kill-switch and audit removed_with_feature entries carry no operator_areas, and their code is absent at 68d5573 (item 2).
