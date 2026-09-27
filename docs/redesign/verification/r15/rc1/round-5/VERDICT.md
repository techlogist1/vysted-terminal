# rc1 gate round 5: verdict (rc1-verifier)

**FAIL.** Candidate `633f844071d972b337f4c3526d86555c80df0568` (worktree `rc1-round-5-9bc600e-fix-int`, fast-forward of `9bc600ec`). Sheet: `docs/redesign/verification/R15_GATE_RC1.md`. Findings: `findings/rc1-verifier.json`. Paths below are relative to `round-5/` unless they start with `r15/` or `docs/`.

Every probe ran against the candidate source: `git -C <worktree> rev-parse HEAD` printed `633f844071d972b337f4c3526d86555c80df0568` before each batch, and the own sidecars (`:52312`, `:52313`) were booted from that worktree (read-only, `PYTHONDONTWRITEBYTECODE=1`). Both are stopped.

## 1. Register criterion: PASS

`verifier/register-at-633f844.json` (byte-identical to `docs/redesign/verification/vysted-r15-register.json`, last touched by `9bc600ec`):

```
counts {"raw": 887, "entries": 679, "rejections": 76, "critical": 16, "high": 121, "medium": 305, "low": 237}
status fixed 398 | open 215 | blocked_tier4 35 | removed_with_feature 14 | needs_gui 11 | not_a_defect 6
open at critical/high/medium: 0
```

## 2. Gate 8, no trading path: PASS (gate8_refuted = false)

```
verifier/gate8/openapi-paths.txt      101 routes; grep -ciE "safety|audit|order|trade|broker|kill" -> 0
verifier/gate8/tool-lists.txt         CATALOG 56 / TOOL_SCHEMAS 56 / KNOWN_TOOL_IDS 56 / MCP_SERVER_TOOLS 40; no order or broker tool
verifier/gate8/agent-order-attempt.log  "I cannot fulfill your request to buy or sell securities." (no tool_use) EXIT=0
verifier/gate8/accept-and-order-shaped-actions.json  place_order / submit_order -> "Unknown action — can't apply", holdings 0
verifier/gate8/datadir-and-ack.txt    tables: custom_agents, cache+meta, runs, fundamentals, plugin_configs, positions, schedules+workflows; audit_orders only in sidecar/tests/test_no_trading_surface.py:135
```

## 3. Gate 8, tracked portfolio: PASS

```
verifier/gate8/portfolio-roundtrip.json  added MSFT x7 @312.5 -> persistAfterAdd 200 -> readBack [{MSFT,7,312.5}]
  csv "MSFT,7,312.5,equity,USD,516.17,3613.19,1425.69,65.17,100.00," ; liveQuote 516.17 ; livePriceDelta 0 ; delete persists []
verifier/gate8/portfolio-roundtrip-vitest.log  Test Files 1 passed / Tests 1 passed
verifier/gate8/agent-add-position-ask.log  tool_use 1 -> "I've added a proposal to add 5 shares of AAPL ... awaiting your review and acceptance"
verifier/gate8/positions-before.json, positions-after.json  [] and []
```

## 4. ci-local: PASS

```
fix-r1/ci-local.log:1     === ci-local run 1 at 633f844071d972b337f4c3526d86555c80df0568 2026-09-27 16:11:46 IST ===
fix-r1/ci-local.log:2769  === ci-local run 2 (final) at 633f844071d972b337f4c3526d86555c80df0568 ...
  Test Files 153 passed (153) / Tests 1881 passed (1881)
  test result: ok. 19 passed; 0 failed
  3780 passed, 1 skipped, 4 warnings in 228.49s
  EXIT=0
```

## 5. smoke: PASS

```
fix-r1/smoke.log:1   === smoke at 633f844071d972b337f4c3526d86555c80df0568 2026-09-27 16:28:12 IST ===
  [smoke] vysted-sidecar /agents roster OK (13 agents).
  [smoke] vysted-sidecar /mcp/status OK (ready=true, toolCount=40).
  EXIT=0
```

Bundle rehearsal: PASSED at 64e9470e (`r15/stage-d/bundle-rehearsal/REHEARSAL.md`); cited, not repeated.

## 6. Agent scenarios: DEFERRED (operator_attended)

48 files present (12 scenarios x 3 hosted + 1 local); the scenarios-lane failure is not observed. Graded hosted triples:

```
rb1-hosted-t1  "I've proposed adding TCS.NS to your watchlist for review."        (t2, t3 the same shape)  -> pass^3
sc1-hosted-t1  "The current P/E ratio for ... (TCS.NS) is 15.13."                  (15.13 in all three)     -> pass^3
sc4-hosted-t1  "For Delta Air Lines (DAL): ... Revenue ... ₹2.07 crore ... Net Income ₹-8.66 crore"  consistent, but DAL.BO data -> DATA-002 class
sk1-hosted-t1  "The current price of Amalgamated Financial Corp. (AMAL) is ₹674.4."  -> fail, DATA-002 class (4.15)
sk4-hosted-t1  "The latest figures for Delta Air Lines (DAL) ... ₹100,000.00 ... ₹5.99 cr"  -> fail, DATA-002 class (4.15)
sk2-hosted-t1  "... are not calculated on an ADR basis"  vs  sk2-hosted-t2 "... are reported on an ADR basis"  -> fail, AGENT-090 class (4.17)
sk3-hosted-t1  "I couldn't find the trading information for BGNE ..."  -> pass^3
```

Skepticism 1/4; the three failures are the operator-pending DATA-002 and AGENT-090 classes. Local (single trial, informational): `rb1-local-t1` "I've added TCS.NS to your watchlist and proposed the change for review."; `rb4-local-t1` "Built you a brief on TCS.NS — it's at the top of the cockpit" (the verbatim copilot.json example; low adjacent rc1-verifier:40).

## 7. Owner drives: PASS

All 8 groups have non-md raw under `surface/*/rc1/round-5/`. Spot-check on `:52312` (`verifier/adjacent/drive-spotcheck.out.txt`):

```
$ POST /screener/formula/validate {"formula":"pe_ratio < 15 and r%oe > 0.1"}
{"ok":false,"error":"unexpected character '%'","position":19,"fields":[]} HTTP=200
$ POST /workspace {"name":"Research: NVDA","workspace":{}}
{"status":"saved","name":"Research: NVDA"} HTTP=200
$ GET /workspace/does-not-exist-zz
{"detail":"Workspace 'does-not-exist-zz' not found."} HTTP=404
```

These match the screener and panels-layouts drive raw.

## 8. Fixed-name battery: PASS

398 fixed ids: 394 have raw by filename under `battery/`, and 4 sit in combined files (`set-28` `UI-034_035_036_037`, `set-47` `CODE-PLATFORM-026-and-RELEASE-006`). battery-raw-missing is refuted on disk. The battery ran at 9bc600e; the fix-r1 delta is `InsiderTradingTable` only (covered by ci-local at 633f844).

## 9. Data packs: PASS

`battery/collected/*`: 24/24 `complete=True`, 0 responses >= 500.

## 10. Fix loop closed: PASS

Rejections [], unclosed [], tier-4 deferred [].

## 11. GUI round: DEFERRED (operator_attended)

SKIPPED: the computer-use grant does not cover the built app. needs_gui: CODE-AGENT-001, LIFECYCLE-001, LIFECYCLE-008, UI-009, UI-022, UI-025, UI-050, UI-083, UI-084, DOCS-024, LIFECYCLE-040.

## 12. Adversarial sample: FAIL (product_defect)

Each entry's own repro was re-run at HEAD `633f844071d972b337f4c3526d86555c80df0568`. Outputs are in `verifier/refutations/`.

| Entry | Own-repro command | Output (excerpt) | Result |
|---|---|---|---|
| CODE-PLATFORM-072 | `curl :52312/data-sources`; `grep` marketplace rows | ccxt served (crypto ohlcv/quote, available true); `REGISTRY_PROVIDER_ID = {vysted-yfinance, openbb-mcp}`; no ccxt row, no registry-parity test (`cp072.out.txt`) | **stands** |
| LIFECYCLE-024 | `l024.py`: 0.8.0-shape data dir, `data_cache.ensure_build('0.8.0')` | case a (no meta row) `cleared= True`, `backups exists: False []`; case b (meta 0.7.9-prior) `backups exists: True` (`l024.out.txt`) | **stands** |
| RESEARCH-022 | `r022.py`: 200 DDG block page through DdgSearchBackend / KeylessSearchBackend | `FRESH DdgSearchBackend 200 block page -> ok rows 0`; `ddg breaker failures before 1 after 0` (`r022.out.txt`) | **stands** |
| AGENT-027 | `humanize('groq', exc(status_code=413))` | `humanize(groq,status=413) -> unknown | Something went wrong with Groq.` (`a027.out.txt`) | **stands** |
| LIFECYCLE-020 | clean keyless IN profile `:52313`, idle 11 min, then sp500 + nifty50 screens | yahoo `open:false, opens_total:0` throughout; sp500 `evaluated_count=503 skipped_count=0`; nifty50 `duration_ms 6.2` (`l020own.out.txt`) | not reproduced |
| LEAD-023 | `lead023.py`: price, no regularMarketTime, empty 5d history | `ProviderError ... Yahoo returned a price with no trade time` (`lead023.out.txt`) | decision D-B9-2 (no synthesized timestamp) |
| DATA-073 | `data073.py` | `max NSE holiday: 2026-12-25`; `2027-01-26 (Republic Day) trading day IN: True` (`data073.out.txt`) | decision D-B9-4; residual low (:30) |
| RESEARCH-006 | `r006.py` literal: 5 slow verdicts | `A literal ... wall=2.0s elapsed=2.00s` (`r006.out.txt`) | not reproduced; low variant (:36) |
| AGENT-040 | `a040.py` over the captured 7-turn history | `short-6x ... turn-1 constraint in provider history: True` (`a040.out.txt`) | not reproduced; adjacent medium (:9) |
| DATA-060 | `GET /disclosures/shareholding?symbol=SIFY` (+WIT) | SIFY `coverage covered, provider sec-20f` (`d060-SIFY.json.txt`) | not reproduced; adjacent medium IBN/HDB (:10) |
| AGENT-044 | `/resolve` Mazagon Dock / MAZAGONDOCK | `Mazagon Dock -> MAZDOCK`; `MAZAGONDOCK -> ok:false "No instrument matched"` (`a044-*.json.txt`) | not reproduced; low (:34) |
| UI-058 | shard-4 vitest probe of Import | own `{}` / `{theme:'dark'}` now error (`verifier/shard-4.md` 64-75) | not reproduced; low (:35) |
| CODE-DATA-005 | `grep def is_applicable/_is_blocked/_row_value` | `is_india_listing`/`is_block_error` shared in `witness.py`; the two remaining `is_applicable` differ in body; `_row_value` twin remains (`growth_check.py:94`, `earnings_quality.py:134`) (`cd005.out.txt`) | not reproduced; low (:38) |
| RESEARCH-029 | `r029.py` on the Kaynes markdown | `OWN-REPRO removed: 3`; `Merged Sources: False | References: False` (`r029.out.txt`) | not reproduced; adjacent medium (:7) |
| DOCS-016 | `grep` CURRENT_STATE + catalog count | 19 host actions at :78/:582/:682/:869, one line at :753 says 18 (`docs016.out.txt`) | not reproduced; low (:39) |
| LEAD-026 | `GET /history/ZZZZNOTREAL` | `reason: 'unknown_symbol'`; suffixed forms `reason: None` (`lead026.out.txt`) | not reproduced; low (:31) |
| RESEARCH-002 | `_parse_verdict('UNVERIFIED - ...')` x3 | all `-> unverified` (`r002_a027.out.txt`, `r002-variants.out.txt`) | not reproduced; adjacent medium `_UNVERIFIED_` (:6) |
| CODE-AGENT-033 | grader over the errored option_chain trial | `errored call -> ['option_chain errored: 422']` (`ca033.out.txt`) | not reproduced |
| LEAD-031 | `l031rt.py` sify-1 chunking | `A repro ... streamed_text="The ADR-to-ordinary-share ratio is not available ..."` (no splice) (`l031.out.txt`) | not reproduced; low type-first leak (:37) |
| LEAD-033 | two-turn history through `_without_step_trailers` | `[tool steps:` stripped; `[failed: ...]` rides (`lead033.out.txt`) | not reproduced; low (:32) |
| AGENT-095 | ratio guard on the dated SIFY sentences | `OWN kept_vs_depositary=True` x5 (`a095.out.txt`) | not reproduced; low 26-Jun-2026 form (:33) |
| RESEARCH-027 | `research` KSE / Kaveri Seed / KSE.NS, IN region | `wall_s 8.1 / 8.5 / 6.0` (`r027b.out.txt`) | not reproduced; adjacent medium web-only branch (:11) |
| LEAD-044 | IN-session sp500 screen, fresh store | `INR rows 0`; HAL Halliburton, CCL Carnival, IEX IDEX, ACGL Arch, PTC Inc (`l044.out.txt`, `l044-fresh.out.txt`) | not reproduced (pre-fix store row: shard :27) |
| CODE-DATA-001 | `/resolve?q=FOCUS`, `/disclosures/shareholding` + announcements | shareholding NSE Focus Lighting only; announcements mix BSE 543312 rows with NSE Focus Lighting (`cd001-*.json`) | own clause fixed; adjacent **high** (:5) |

Adjacent blockers are listed in the sheet (Blockers) and in `findings/rc1-verifier.json` :5-:29. The confirmed-by-verifier excerpts:

```
adjacent/adj-batch1.out.txt   insufficient_credit | Your Google Gemini account is out of credit or quota.   (free-tier per-minute 429)
adjacent/adj-batch1.out.txt   roe > (pe_ratio < 15) -> {"ok":true,...}
adjacent/adj-batch2.out.txt   GET /macro/search?q=unemployment&provider=fred -> 502 "FRED needs a free API key ..."; src/store/macro.ts catch {} -> []
adjacent/adj-batch2.out.txt   SettingsPanel.tsx:122 "Nothing leaves this machine except calls you ..."
adjacent/adj-s0-groupfilters.out.txt  ['group'] -> invalid arguments for write_screener_filters: missing criteria
refutations/r002-variants.out.txt  '__UNVERIFIED__ - no source confirms it' -> agree
refutations/r029.out.txt      FRESH '## Citations': removed=0 list_survives=True
refutations/d060-IBN.json.txt  coverage not_applicable, major_shareholders []
refutations/a040.out.txt      research-6x-12k client_sent 8 ... turn-1 constraint in provider history: False
refutations/cd001-ann.json    FOCUS rows with exchange BSE (scrip 543312) beside NSE "Focus Lighting and Fixtures Limited ..."
shard-9-evidence/research027-pytest-output.txt  web-only NORMAL path held 20.0s by an un-boxed web round
```

## Concurrence notes (operator decision pending)

- DATA-002 (4.15): reproduced by sk1, sk4 and sc4 (AMAL and DAL bind to the IN listings under an IN session).
- AGENT-090 (4.17): reproduced by sk2 (ADR basis contradicts itself across trials).
- DATA-091 (removed_with_feature): fresh concurrence; `sidecar/models/audit_log.py` is absent at 633f844 and no `/safety/*` route is served.
