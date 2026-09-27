# R15 gate sheet: rc1 (gate round 4)

**Verdict: FAIL.** Do not tag.

- Verifier: `rc1-verifier` (claude-opus-5-5[1m]), fresh adversarial gate verifier, 2026-09-27.
- Gate round: **4**. Evidence root: `docs/redesign/verification/r15/rc1/round-4/`.
  - The verifier's own evidence is in `round-4/verifier/own/`.
  - The evidence excerpt behind each line is in `round-4/VERDICT.md`.
  - Findings are in `round-4/findings/rc1-verifier.json`. The working log is `round-4/logs/rc1-verifier.md`.
- Candidate: the worktree `rc1-round-4-1006c6d-fix-int` at HEAD `68d5573aff9a579af084dcbb124843f2aecff6e8` (checked with `git rev-parse HEAD`). The own sidecar was booted from it on `:52312`.

## SHA to tag

`68d5573` is the head of `worktree-agent-rc1-round-4-1006c6d-fix-int`, a fast-forward of `1006c6da694ede5776c3dabbd27b305aeb56b5ad`.

- The lead fast-forwards 004 to it. If 004 has moved past it, the tagged tree must be this sha or the gate re-runs. The verifier never tags.
- Observed: 004 is at `aaad38ac`. It has moved past `1006c6da` (the merge-base) with `CHANGELOG.md`, `scripts/r15/hygiene_inventory.py` and verification evidence, so 004 cannot fast-forward to `68d5573` today.
- This verdict is FAIL, so nothing is tagged.

## Gate items

| # | Item | Result | Cause | Evidence |
|---|---|---|---|---|
| 1 | Register criterion (only `open` at critical/high/medium fails) | PASS | none | `verifier/own/register-at-68d5573.json`: 661 entries; 395 fixed; 207 open, **all low**; 29 blocked_tier4; 11 needs_gui; 5 not_a_defect; 14 removed_with_feature. The four-area exception holds (see below). Standing refutations are judged under item 12, not here. |
| 2 | Gate 8: no trading path | PASS | none | `verifier/own/openapi-paths-52312.txt` (111 routes, 0 order/trade/broker/kill/audit routes); `tools-lists.txt` (catalog, TOOL_SCHEMAS and KNOWN_TOOL_IDS 56, MCP 40, no order or broker tool); `rg-*.txt`; `g8-agent-order-attempt.*` (no tool call; the model refuses); `g8-failclosed.out` (execute_trade and market_order: accept=failed, holdings 0); `g8-audit-orders.txt` (no audit_orders table). gate8_refuted = false. |
| 3 | Gate 8: tracked portfolio | PASS | none | `verifier/own/g8-portfolio-roundtrip.out` (MSFT x10 @300 gives +$2,161.70 (+72.06%); CSV written; delete leaves []); `g8-exported.csv`; `g8-agent-gated-add.*` (portfolio_add_position staged, "proposed ... for review"); `g8-ledger-before/after.json` (legacy ledger [] before and after). |
| 4 | ci-local | PASS | none | `fix-r1/ci-local.log`: run 1 and run 2 at `68d5573`, both EXIT=0; vitest 1849 passed; cargo 19 passed; pytest 3671 passed, 1 skipped. |
| 5 | smoke | PASS | none | `fix-r1/smoke.log`: at `68d5573`, EXIT=0. The production-bundle rehearsal PASSED at 64e9470e (`r15/stage-d/bundle-rehearsal/REHEARSAL.md`); cited, not repeated. |
| 6 | Agent scenarios | FAIL | product_defect | `scenarios/*.jsonl` and `*.stdout.txt` (lane ran at 1006c6da). There are 4 complete hosted triples per property. Graded pass^3: **read-back 4/4, self-consistency 4/4, skepticism 1/4**. sk-smr passes. sk-amal and sk-dal fail on DATA-002; these are blocked_tier4 concurrence notes. **sk-sify fails** on `sk-sify-hosted-t2` ("... not available from this session's sources. 5 or The ADR-to-ordinary-share ratio ..."): the ratio guard releases a partial sentence mid-stream. This is a new medium defect, reproduced at 68d5573 in `verifier/own/adv-ratio-guard-sim.txt` (rc1-verifier:2). The local lane is single-trial and informational. |
| 7 | Owner drives | PASS | none | All 8 groups have raw files under `surface/*/rc1/round-4/`, so drive-raw-missing does not apply. Spot-checked 2 drives on `:52312` at 68d5573. Screener (`verifier/own/drive-spot.out`): custom-bare returns 5/5; the malformed formula gets an honest 422; zero-result reads "screened 49 of 50"; universe counts are 503/50/50/3506/5042/5891. Research-briefs: `/search/status` and `/search/searxng/status` have the same shape; the bad-key run (`drive-spot-badkey.*`) returns "The OpenAI API key was rejected — check it in Settings.". All match the drive raw. |
| 8 | Fixed-name battery | FAIL | harness_environment | battery-raw-missing is confirmed and **undercounted**. `verifier/own/battery-raw-check.txt`: 25 fixed ids have only NOT RUN raw (the collator claimed 3). The battery also ran at 1006c6da, not at 68d5573. |
| 9 | Data packs | PASS | none | `battery/collected/*`. I concur with the rc1-datapack:1 rejection (`verifier/own/rej-datapack1-sify.json`: SIFY `financial_currency` INR). |
| 10 | Fix loop closed | PASS | none | Unclosed []. Tier-4 deferred []. I concur with all four rejections: rc1-datapack:1, rc1-drive-screener:1, rc1-drive-panels-layouts:1 and rc1-battery-9:1 (`rej-*`). |
| 11 | GUI round | DEFERRED | operator_attended | SKIPPED because the computer-use grant does not cover the built app. The 11 needs_gui ids are listed below. |
| 12 | Adversarial sample (RUBRIC b) | FAIL | product_defect | Refutations that stand on their own repro at 68d5573: **DATA-003 (critical), LEAD-022 (high), LEAD-014, LEAD-004, AGENT-055, DATA-053 (medium)**, plus UI-015 on its secondary clause (low residual). Adjacent HIGH confirmed: arrange_layout `custom` TypeError (rc1-vshard-9:1 / rc1-verifier:1). The medium adjacents filed by shards are listed under Blockers. |

## Operator-attended

- **needs_gui**, all deferred because the computer-use grant does not cover the built app: R15-CODE-AGENT-001, R15-LIFECYCLE-001, R15-LIFECYCLE-008, R15-UI-009, R15-UI-022, R15-UI-025, R15-UI-050, R15-UI-083, R15-UI-084, R15-DOCS-024, R15-LIFECYCLE-040.
- **Known limitations (blocked_tier4):**
  - R15-LEAD-030, R15-LEAD-037 and R15-LEAD-038 (DECISIONS 4.9-4.12). New instances of "local model states a figure with no ok tool call" are filed under them, including `rb-brief-local-t1` (concurs with rc1-fix-r1-recheck:2).
  - R15-LEAD-035 (4.10).
- **Operator decision pending:** R15-DATA-002 (critical, 4.15), R15-DATA-059 (4.13) and R15-RESEARCH-043 (4.14). The reproductions are concurrence notes only: `sk-amal-hosted-t1..t3` and `sk-dal-hosted-t2` (rc1-verifier:14).
- **Other blocked_tier4, operator-attended:**
  - R15-AGENT-017 (funded lane), R15-AGENT-049 (native-search lane), R15-UI-088 (e2e runner).
  - R15-AGENT-064, R15-CODE-FRONTEND-013, R15-CODE-PLATFORM-010, -015, -063, -071, -073, R15-CROSS-PLATFORM-001.
  - R15-DOCS-002, -003, -008, -011, -015.
  - R15-RELEASE-001, -002, -003, -004, -012, R15-UI-044.
- **not_a_defect and removed_with_feature, concurred:** see "Four named areas". The removed_with_feature entries outside the areas are CODE-PLATFORM-006/007/008/009/031/032/033, DATA-091, DOCS-001, LIFECYCLE-016 and CROSS-PLATFORM-005 (kill-switch, audit and order surfaces removed by D81 `a122dbf6`). Their code is absent at 68d5573 (item 2 evidence).

## Fixed-uncertified

These have no battery raw (NOT RUN) and no verifier-shard raw, so they rest on ci-local tests only. This is a finding, not a failure.

R15-CODE-FRONTEND-001, R15-CODE-FRONTEND-016, R15-CODE-PLATFORM-053, R15-DATA-031, R15-DATA-042, R15-DATA-100, R15-LIFECYCLE-002, R15-LIFECYCLE-003, R15-LIFECYCLE-009, R15-RESEARCH-026, R15-UI-016, R15-UI-030, R15-UI-086, R15-UI-092.

The other 11 battery-missing ids have verifier-shard raw: AGENT-053, AGENT-057, CODE-FRONTEND-005, CODE-FRONTEND-018, CODE-PLATFORM-012, CODE-PLATFORM-013, CROSS-PLATFORM-004, LEAD-033, UI-029, UI-038 and UI-058.

**Three-failure list:** LEAD-028, AGENT-019, CODE-PLATFORM-013, AGENT-010 and LEAD-039. None is refuted by its own repro, so none is recorded as not certified.
- AGENT-019 has a fresh residual: a question-shaped write ask strips the write tool (rc1-verifier:12, medium).
- LEAD-039's partial estimates carry no stated reason (rc1-verifier:13, low).

## Adjacent findings

**Confirmed by me at 68d5573:**
- **rc1-verifier:1, high.** arrange_layout `custom` raises TypeError in `_coerce` (AGENT-093 fix 816f7cac).
- **rc1-verifier:2, medium.** The ratio guard's mid-sentence release leaks figures (`_seg_at` marks a whitespace-terminated fragment closed).
- **rc1-verifier:10, medium.** A flat AND screener group never runs (rc1-vshard-3:6).
- **rc1-verifier:16, low.** The nifty50 universe lists TATAMOTORS.NS, which is now unquotable. It is honestly skipped.

**Shard-filed, medium or higher, counted as new defects:**

| Shard key | Register tie | Finding |
|---|---|---|
| rc1-vshard-0:4, rc1-vshard-7:4 | DATA-007 / LEAD-010 | Every 10-Q has zero sections |
| rc1-vshard-0:5 | RESEARCH-001 | gate_news is IN-only |
| rc1-vshard-1:1 | DATA-024 | BSE bulk/block lane is never read |
| rc1-vshard-1:2 | DATA-030 | News alias over-matches |
| rc1-vshard-4:5 | RESEARCH-022 / CODE-AGENT-008 | A Mojeek captcha counts as a healthy empty answer |
| rc1-vshard-6:1 | LEAD-013 | S&P 500 PTC collision in an IN session |
| rc1-vshard-7:2 | AGENT-092 | A halted Delegate still delivers the brief |
| rc1-vshard-7:3 | DATA-114 | Option-chain walk-back |
| rc1-vshard-8:3 | AGENT-090 | The ratio guard replaces a true ratio when a date is present |
| rc1-vshard-9:5 | deduped into DATA-053 | BSE volume in lakh units |
| rc1-vshard-9:6 | DATA-113 | ADR EPS in reporting currency labelled with the trading currency |

**Shard regressions whose refutation does not stand** (the own repro no longer reproduces). Each residual is carried as an adjacent at the shard's severity:

| Shard key | Entry | Severity | Residual |
|---|---|---|---|
| rc1-vshard-0:2 | AGENT-001 | high | Unitless fractions reach the model |
| rc1-vshard-7:1 | UI-090 | high | Non-US/non-IN freshness uses the US calendar |
| rc1-vshard-8:1 | RESEARCH-007 | high | IR hosts on blog platforms rank as primary |
| rc1-vshard-9:2 | AGENT-019 | medium | Fresh '?' class; see rc1-verifier:12 |
| rc1-vshard-5:3 | CODE-PLATFORM-017 | medium | mathjs preview disagrees with the server |
| rc1-vshard-3:3 | AGENT-043 | medium | Dropped flat criterion has no note |
| rc1-vshard-3:4 | CODE-FRONTEND-017 | medium | SEC detail and insider slices have no generation guard |
| rc1-vshard-2:5 | CODE-FRONTEND-015 | medium | Bus key and panel id mismatch |
| rc1-vshard-2:6 | UI-021 | medium | Body-focus Backspace deletes drawings in every chart |
| rc1-vshard-2:2 | DATA-015 | medium | Since-listing range served as 52-week |
| rc1-vshard-5:2 | DATA-061 | medium | Unknown macro series or provider gives 502 Retry |
| rc1-vshard-9:3 | AGENT-053 | medium | News publish carries no headlines |
| rc1-vshard-4:2 | RESEARCH-027 | medium | Web stall goes unbounded under a patched engine |
| rc1-vshard-2:3 | LIFECYCLE-020 | medium | Warm-loop 429s share the user circuit |
| rc1-vshard-2:1 | DATA-063 | medium | No indicator freshness field |

**Low** (listed; not blockers): rc1-vshard-0:3, 0:6, 1:3-1:8, 2:7-2:9, 3:5, 3:7-3:9, 4:3, 4:4, 4:6-4:10, 5:4-5:11, 6:2, 7:5-7:7, 8:2, 8:4-8:6, 9:4, 10:1, rc1-fix-r1-triage:1, rc1-fix-r1-recheck:1 and rc1-fix-r1-recheck:2.

Environment: rc1-vshard-0:7 (the shared :52152 stack runs 1006c6da) and rc1-verifier:11 (battery raw missing).

## Blockers

1. **Standing refutations:**
   - R15-DATA-003 (critical): a US-bound AMAL still gets Amal Ltd's BSE shareholding and announcements.
   - R15-LEAD-022 (high): foreign suffixes outside the allowlist are dash-rewritten, so they 404.
   - R15-LEAD-014 (medium): a placeholder schema echo is accepted as tool args.
   - R15-LEAD-004 (medium): NDTV, a quarterly filer, is labelled half-yearly.
   - R15-AGENT-055 (medium): the agent and the menu build different panel sets for the same id.
   - R15-DATA-053 (medium): NSE-direct OHLC is null, and BSE volume is in lakh.
2. **New HIGH:** arrange_layout `custom` crashes the agent turn (rc1-verifier:1 / rc1-vshard-9:1).
3. **New medium:** the ratio guard's mid-sentence release leaks figures and fails the sk-sify scenario (rc1-verifier:2).
4. **Medium-or-higher adjacents** filed by shards: all rows of both tables under Adjacent findings.
5. **Harness:** battery-raw-missing (25 ids; the battery ran at 1006c6da). The fixed-name battery must re-run at the tag candidate.

## needs_gui ids

R15-CODE-AGENT-001, R15-LIFECYCLE-001, R15-LIFECYCLE-008, R15-UI-009, R15-UI-022, R15-UI-025, R15-UI-050, R15-UI-083, R15-UI-084, R15-DOCS-024, R15-LIFECYCLE-040. All are operator-attended because the computer-use grant does not cover the built app.

## Four named areas

**Before evidence:** the drives and battery raw at candidate 1006c6da: `surface/{composer-chat,research-briefs,screener,panels-layouts,portfolio-notes,settings-plugins,onboarding-stranger,failure-inducer}/rc1/round-4/`, `battery/raw/**` and `scenarios/*`.

**After evidence:**
- The own sidecar at 68d5573: `verifier/own/*`, including `register-at-68d5573.json`, `drive-spot.out`, `drive-spot-badkey.*`, `adv-*` and `adj-*`.
- `fix-r1/ci-local.log` and `fix-r1/smoke.log` at 68d5573.

**Counts by status at 68d5573** (areas from `operator_areas`; an entry can sit in more than one area):

| Area | Total | fixed | open (all low) | blocked_tier4 | needs_gui | not_a_defect | removed_with_feature |
|---|---|---|---|---|---|---|---|
| agent-chat | 233 | 166 | 55 | 9 | 2 | 1 | 0 |
| research-search | 134 | 100 | 27 | 4 | 1 | 2 | 0 |
| data-smallcaps | 137 | 116 | 17 | 2 | 0 | 2 | 0 |
| ui-panels | 252 | 170 | 65 | 4 | 7 | 3 | 3 |

**not_a_defect and removed_with_feature ids in the areas.** I concur with all eight. The pointers are in `docs/redesign/verification/r15/rc1/findings/rc1-verifier.json`.

| Id | Status | Area | Closure | Concurrence |
|---|---|---|---|---|
| R15-AGENT-083 | not_a_defect | agent-chat | batch-10 `f407107` | rc1-verifier:21 |
| R15-UI-047 | not_a_defect | ui-panels | batch-11 | rc1-verifier:24 |
| R15-UI-059 | not_a_defect | data-smallcaps, ui-panels, research-search | batch-11 | rc1-verifier:25 |
| R15-DATA-080 | not_a_defect | research-search, data-smallcaps | batch-11 | rc1-verifier:22 |
| R15-UI-041 | not_a_defect | ui-panels | batch-6 `5e14731` | rc1-verifier:23 |
| R15-CODE-PLATFORM-001 | removed_with_feature | ui-panels | D81 `a122dbf6` | rc1-verifier:18 |
| R15-UI-042 | removed_with_feature | ui-panels | D81 `a122dbf6` | rc1-verifier:19 |
| R15-UI-043 | removed_with_feature | ui-panels | D81 `a122dbf6` | rc1-verifier:20 |
