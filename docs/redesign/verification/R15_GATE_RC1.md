# R15 gate sheet: rc1 (gate round 5)

**Verdict: FAIL.** Do not tag.

- Verifier: `rc1-verifier` (claude-opus-5-5[1m]), fresh adversarial gate verifier, 2026-09-27.
- Gate round: **5**. Evidence root: `docs/redesign/verification/r15/rc1/round-5/`.
  - The verifier's own evidence: `round-5/verifier/gate8/`, `round-5/verifier/refutations/`, `round-5/verifier/adjacent/`, `round-5/verifier/register-at-633f844.json`, and the sample shards `round-5/verifier/shard-*.md` (+ `shard-*-raw/`, `shard-*-evidence/`).
  - The evidence excerpt behind each line: `round-5/VERDICT.md`.
  - Findings: `round-5/findings/rc1-verifier.json` (40 entries). Working log: `round-5/logs/rc1-verifier.md`.
  - The round-4 sheet is preserved in git at `150041b4`.
- Candidate: the worktree `rc1-round-5-9bc600e-fix-int` at HEAD `633f844071d972b337f4c3526d86555c80df0568` (checked with `git rev-parse HEAD` before every probe). Own sidecars were booted from its source (read-only, `PYTHONDONTWRITEBYTECODE=1`): `:52312` (default profile) and `:52313` (clean data dir, `VYSTED_REGION=IN`, for the LIFECYCLE-020 own repro). Both are stopped.

## SHA to tag

`633f844071d972b337f4c3526d86555c80df0568`, the head of `worktree-agent-rc1-round-5-9bc600e-fix-int`, a fast-forward of `9bc600ece2ce6343a6aa48f130d7620b1466bb98` (adds the fix-r1 insider-table commit `38a64fda`).

- Observed: 004 is at `ec9d0d5e`, 7 commits past `9bc600ec` (`CHANGELOG.md`, `docs/redesign/DECISIONS_FOR_OPERATOR.md`, run-state and verification evidence only; no product file). 004 cannot fast-forward to `633f844` as-is. If a later round passes, the tagged tree must be this sha or the gate re-runs.
- This verdict is FAIL, so nothing is tagged. The verifier never tags.

## Gate items

| # | Item | Result | Cause | Evidence |
|---|---|---|---|---|
| 1 | Register criterion (only `open` at critical/high/medium fails) | PASS | none | `verifier/register-at-633f844.json` (byte-identical to `vysted-r15-register.json` at `9bc600ec` and in the candidate): 679 entries; 398 fixed; 215 open, **all low**; 35 blocked_tier4; 11 needs_gui; 6 not_a_defect; 14 removed_with_feature. Standing refutations are judged under item 12. |
| 2 | Gate 8: no trading path | PASS | none | `verifier/gate8/openapi-paths.txt` (101 routes, 0 matching safety/audit/order/trade/broker/kill); `tool-lists.txt` (catalog = TOOL_SCHEMAS = KNOWN_TOOL_IDS = 56, MCP 40, no order/broker tool); `rg-summary.json` + `rg-code-hits-classified.tsv`; `agent-order-attempt.*` (llama3.1:8b, no tool call: "I cannot fulfill your request to buy or sell securities."); `accept-and-order-shaped-actions.json` (place_order/submit_order: "Unknown action — can't apply", holdings 0); `datadir-and-ack.txt` (no audit_orders table; the name survives only in `test_no_trading_surface.py`). gate8_refuted = false. |
| 3 | Gate 8: tracked portfolio | PASS | none | `verifier/gate8/portfolio-roundtrip.json` + `portfolio-roundtrip-vitest.log` (1 passed): MSFT x7 @312.5 added, persisted in `__autosave__`, read back; CSV price 516.17 = live quote, P&L 1425.69 recomputes (delta 0); delete persists `[]`. `positions-before/after.json` (legacy ledger `[]` both sides); `agent-add-position-ask.*` (portfolio_add_position staged, "awaiting your review"). |
| 4 | ci-local | PASS | none | `fix-r1/ci-local.log`: run 1 and run 2 (final) at `633f844`, EXIT=0; vitest 153 files / 1881 passed; cargo 19 passed; pytest 3780 passed, 1 skipped. |
| 5 | smoke | PASS | none | `fix-r1/smoke.log` at `633f844`: EXIT=0, `/agents` roster 13, `/mcp/status` ready toolCount 40. The production-bundle rehearsal PASSED at 64e9470e (`r15/stage-d/bundle-rehearsal/REHEARSAL.md`); cited, not repeated. |
| 6 | Agent scenarios | DEFERRED | operator_attended | `scenarios/*-hosted-t{1,2,3}.jsonl` (12 hosted triples, 12 local singles). Graded pass^3: **read-back** rb1 pass (all three "proposed ... for review"); **self-consistency** sc1 pass (P/E 15.13 x3), sc4 consistent but on DAL.BO data narrated as Delta Air Lines; **skepticism** 1/4: sk3 pass (BGNE unresolvable, says so); sk1 (Amalgamated -> ₹674.40) and sk4 (DAL -> ₹ figures) are the DATA-002 class (operator decision 4.15, blocked_tier4); sk2 (t1 "not on an ADR basis" vs t2 "on an ADR basis") is the AGENT-090 class (4.17). Every failure sits in an operator-pending class, so the item defers to the operator. The scenarios-lane harness failure is not observed (all 48 files present). The local lane is single-trial and informational (rb1/rb4 overclaim; low adjacent rc1-verifier:40). |
| 7 | Owner drives | PASS | none | All 8 groups have non-md raw under `surface/*/rc1/round-5/`; drive-raw-missing is refuted on disk. Spot-checked 2 on `:52312` at 633f844 (`verifier/adjacent/drive-spotcheck.out.txt`): screener formula validate `%` gives the same error shape as the drive raw; workspace save "Research: NVDA" round-trips and a missing workspace 404s. Both match. |
| 8 | Fixed-name battery | PASS | none | 394/398 fixed ids have raw by filename under `battery/`; the other 4 are in combined files (set-28 `UI-034_035_036_037`, set-47 `CODE-PLATFORM-026-and-RELEASE-006`). battery-raw-missing is refuted on disk. The battery ran at 9bc600e; fix-r1 touched only `InsiderTradingTable` (re-proven by ci-local at 633f844). |
| 9 | Data packs | PASS | none | `battery/collected/*`: 24/24 packs complete=True, 0 5xx. |
| 10 | Fix loop closed | PASS | none | Rejections [], unclosed [], tier-4 deferred [] (as stated for this round; nothing to concur with). |
| 11 | GUI round | DEFERRED | operator_attended | SKIPPED: the computer-use grant does not cover the built app. The 11 needs_gui ids are listed below. |
| 12 | Adversarial sample | FAIL | product_defect | Each of the 24 refuted entries' own repro was re-run at 633f844 (`verifier/refutations/*`). **Standing (own repro reproduces): CODE-PLATFORM-072, LIFECYCLE-024, RESEARCH-022, AGENT-027** (all medium). Not standing: LIFECYCLE-020 (clean IN profile, T+11: sp500 503/503 evaluated, 0 skipped, nifty50 6 ms, circuit never opened) and 19 others; LEAD-023 and DATA-073 are covered by decisions D-B9-2 / D-B9-4. Adjacent blockers: **1 high** (FOCUS announcements merge BSE 543312, a different company) and **12 medium confirmed by the verifier** plus **12 medium from the verifier's own sample shards** (see Blockers). |

## Operator-attended

- **needs_gui**, deferred because the computer-use grant does not cover the built app: R15-CODE-AGENT-001, R15-LIFECYCLE-001, R15-LIFECYCLE-008, R15-UI-009, R15-UI-022, R15-UI-025, R15-UI-050, R15-UI-083, R15-UI-084, R15-DOCS-024, R15-LIFECYCLE-040.
- **Operator decision pending** (reproductions are concurrence notes, not refutations): DATA-059 (4.13), RESEARCH-043 (4.14), DATA-002 (4.15; reproduced by sk1, sk4, sc4), AGENT-019 (4.16), AGENT-090 (4.17; reproduced by sk2), RESEARCH-007 (4.18), DATA-061 (4.19), UI-090 (4.20), DATA-030 (4.21).
- **Known limitation, blocked_tier4** (35): the local-model class LEAD-030/035/037/038 (DECISIONS 4.9-4.12) plus DATA-002, AGENT-017, AGENT-019, AGENT-090, DATA-030, RELEASE-001..004, RESEARCH-007, UI-090, AGENT-049, AGENT-064, CODE-FRONTEND-013, CODE-PLATFORM-010/015/063/071/073, CROSS-PLATFORM-001, DATA-059, DATA-061, DOCS-002/003/008/011/015, RESEARCH-043, UI-044, UI-088, RELEASE-012. No new "local model states a figure with no ok tool call" instance was filed this round.
- **Scenarios** (item 6) defer to the operator for the reason above.

## Fixed-uncertified

None. 396/398 fixed ids appear in a batch certified list; the other two have holding raw at the candidate (LEAD-043 in battery set-86, auth humanized; CODE-DATA-023 in set-87).

## Adjacent findings

Low (not blockers; keys in `findings/rc1-verifier.json`):

- DATA-073: NSE holiday table ends 2026-12-25; 2027-01-26 counts as an IN trading day (D-B9-4 covers the test horizon, not the data) - rc1-verifier:30.
- LEAD-026: suffixed unknown symbols (QQZZFAKE.NS/.BO, RELIANC.NS) return 0 bars with reason null; the bare one says unknown_symbol - :31.
- LEAD-033: the `[failed: ...]` trailer still rides history to the provider - :32.
- AGENT-095: 26-Jun-2026 / Jun-26-2026 date forms still trip the ratio guard - :33.
- AGENT-044: resolver suggestions for MAZAGONDOCK / RELIANCEIND - :34.
- UI-058: `{settings:{fontSize}}` import toast - :35. RESEARCH-006: slow extract before the wall - :36. LEAD-031: type-first JSON tool-call text leaks - :37. CODE-DATA-005: `_row_value` twin (growth_check.py:94, earnings_quality.py:134) - :38. DOCS-016: one doc line still says 18 host actions (19 in the catalog) - :39. copilot.json example reply in the applied tense conflicts with review mode - :40.
- Shard lows (in `verifier/shard-*.md`, not re-keyed): BondPricer currency, `_reflect_says_complete`, `_us_isin` cache, CONTRIBUTING, SEC clearSearch, BadZipFile, stale comments, OpenRouter literal URL, search_companies, parseChartDrawing, BLUEPRINT "12 agents".
- Environment (:41): the candidate worktree carries 3 uncommitted `spend-ledger.jsonl` lines (free ollama calls from vy.py runs invoked from that checkout). HEAD is unchanged at 633f844, so the tagged tree is unaffected; the lead should fold the lines into the main ledger.

## Blockers

Standing refutations (regression, medium): rc1-verifier:1 CODE-PLATFORM-072 (ccxt has no marketplace row), :2 LIFECYCLE-024 (no backup when the data dir has no meta build row - every shipped build incl. v0.8.0), :3 RESEARCH-022 (DDG 200 block page reads as healthy empty and resets the breaker), :4 AGENT-027 (body-less 413 humanizes to unknown).

Adjacent new defects confirmed by the verifier at 633f844:

- **High** :5 FOCUS announcements merge BSE scrip 543312 (a different company) into Focus Lighting's NSE feed (near CODE-DATA-001).
- Medium :6 `_UNVERIFIED_` / `__UNVERIFIED__` parse as AGREE (RESEARCH-002); :7 bibliography heading variants survive (RESEARCH-029); :8 Gemini free-tier per-minute 429 read as out of credit (AGENT-027); :9 historyForSend silently drops turns past 60k chars (AGENT-040); :10 IBN/HDB 20-F ownership not_applicable with 0 holders (DATA-060); :11 web-only FAST branch not time-boxed (RESEARCH-027); :12 group-only write_screener_filters rejected (AGENT-024); :13 macro search swallows the 502 as "No matching series" (UI-029); :14 Settings privacy copy over-promises (UI-052); :15 boolean-operand formulas validate ok (RESEARCH-025); :16 ratings swallow a Yahoo 429 (DATA-069); :17 earnings history swallows a 429 and caches it 24 h (LEAD-009).

Adjacent medium from the verifier's own sample shards (not re-run by the lead verifier): :18 RESEARCH-009, :19 AGENT-008, :20 CODE-FRONTEND-006, :21 UI-003 (partly code-confirmed: `src/store/agents.ts:128` sets `defaultModel: null`), :22 UI-055, :23 CODE-FRONTEND-015, :24 CROSS-PLATFORM-002 (chain: flaky test), :25 LEAD-018 (provisional), :26 UI-028, :27 LEAD-013 (poisoned PTC India row in a pre-LEAD-044 store), :28 DATA-112, :29 DATA-068.

Three-failure rule: LIFECYCLE-020 did not reproduce, so nothing is recorded against it. LEAD-028, CODE-PLATFORM-013, AGENT-010, RESEARCH-001, DATA-063 and LEAD-004 were not in this round's refuted list.

## needs_gui ids

R15-CODE-AGENT-001, R15-LIFECYCLE-001, R15-LIFECYCLE-008, R15-UI-009, R15-UI-022, R15-UI-025, R15-UI-050, R15-UI-083, R15-UI-084, R15-DOCS-024, R15-LIFECYCLE-040. All are operator-attended because the computer-use grant does not cover the built app.

## Four named areas

**Before evidence:** the register entries' `repro`/`evidence` fields and the drives, battery and scenarios raw at 9bc600e: `surface/{composer-chat,research-briefs,screener,panels-layouts,portfolio-notes,settings-plugins,onboarding-stranger,failure-inducer}/rc1/round-5/`, `round-5/battery/**`, `round-5/scenarios/*`.

**After evidence:** own sidecars at 633f844: `verifier/refutations/*`, `verifier/adjacent/*`, `verifier/gate8/*`; `fix-r1/ci-local.log` and `fix-r1/smoke.log` at 633f844.

**Counts by status at 633f844** (from `operator_areas`; an entry can sit in more than one area):

| Area | Total | fixed | open (all low) | blocked_tier4 | needs_gui | not_a_defect | removed_with_feature | Standing refutations | Adjacent blockers |
|---|---|---|---|---|---|---|---|---|---|
| agent-chat | 237 | 167 | 55 | 12 | 2 | 1 | 0 | AGENT-027 | :8 :9 :12 :18 :19 :21 :23 :25 |
| research-search | 138 | 100 | 29 | 6 | 1 | 2 | 0 | RESEARCH-022, AGENT-027 | :5 :6 :7 :10 :11 :24 |
| data-smallcaps | 147 | 118 | 22 | 4 | 0 | 3 | 0 | CODE-PLATFORM-072 | :5 :15 :17 :27 :28 |
| ui-panels | 255 | 168 | 66 | 8 | 7 | 3 | 3 | - | :13 :14 :16 :20 :22 :26 :29 |

LIFECYCLE-024 has no operator area.

**not_a_defect and removed_with_feature concurrences.**

| Id | Status | Area | Closure | Concurrence |
|---|---|---|---|---|
| R15-AGENT-083 | not_a_defect | agent-chat | batch-10 `f407107` | `r15/rc1/findings/rc1-verifier.json` :21 |
| R15-UI-047 | not_a_defect | ui-panels | batch-11 | same file :24 |
| R15-UI-059 | not_a_defect | data-smallcaps, ui-panels, research-search | batch-11 | same file :25 |
| R15-DATA-080 | not_a_defect | research-search, data-smallcaps | batch-11 | same file :22 |
| R15-UI-041 | not_a_defect | ui-panels | batch-6 `5e14731` | same file :23 |
| R15-LEAD-046 | not_a_defect | data-smallcaps | batch-28 fresh verifier | batch-28 `VERDICTS.json` |
| R15-CODE-PLATFORM-001, R15-UI-042, R15-UI-043 | removed_with_feature | ui-panels | D81 `a122dbf6` | same file :18-20 |
| R15-DATA-091 | removed_with_feature | - | D81 `a122dbf6` | **fresh, this round**: at 633f844 `sidecar/models/audit_log.py`, `services/kill_switch.py` and `src-tauri/src/kill_switch.rs` do not exist, no non-test file names `audit_orders`/`AUDIT_LOG_DDL`, and no `/safety/*` route is served (`verifier/gate8/openapi-paths.txt`). The unreadable-audit-log defect has no surface left. Concur. |
| other 10 removed_with_feature (CODE-PLATFORM-006..009/031..033, DOCS-001, LIFECYCLE-016, CROSS-PLATFORM-005) | removed_with_feature | - | D81 `a122dbf6` | stage-c batch `VERDICTS.json`; Gate 8 evidence shows the trading surface absent |

## Round 5-recheck (lead reading under gate rule change 1, 27 Sep 2026)

Run `wf_da354223-f11` on candidate `949c3c9f` (round-5 adjudication + the bounded fix round for R15-LEAD-059 merged at `794bc68f`): chain green (ci-local EXIT=0: vitest 1881, cargo 19, pytest 3784/1 skipped; smoke EXIT=0), Gate 8 PASS with 0 findings, battery 395 fixed ids = 316 holds + 79 ci_pinned, 0 regressed, raw for all 395. Open critical 0, open high 1 (R15-LEAD-116, DECISIONS 4.22, operator-pending). The tag waits on that answer. Full reading: `r15/rc1/round-5-recheck/RECHECK_READING.md`. Measured 167 min, 30 agents, hosted spend USD 0.00.
