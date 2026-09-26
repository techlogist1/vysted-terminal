# R15 gate: rc1 (gate round 2, fresh adversarial verifier)

- Candidate and tag sha: `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`.
- Verifier: `rc1-verifier`, Opus 5.5, 2026-09-26.
- Branch 004 has moved past the candidate to 8ca67fe6, with docs-only commits: `git diff --name-only 4c6dfe8c HEAD` lists nothing outside `docs/`. The tagged tree must be **4c6dfe8c**, not the branch head. The fix-round integration `81fbfe91` (fix-int) is not the candidate and is not certified here.
- Evidence root: `docs/redesign/verification/r15/rc1/verifier/g2/`. Every excerpt is in `r15/rc1/VERDICT.md`, findings are in `r15/rc1/findings/rc1-verifier.json`, and the log is in `r15/rc1/logs/rc1-verifier.md`.

**VERDICT: FAIL.** Do not tag rc1.

## Gate items

| # | Item | Result | Cause | Evidence |
|---|---|---|---|---|
| 1 | Register criterion (every critical/high/medium closed) | **FAIL** | product defect | At 4c6dfe8c the register shows 0 open critical/high/medium (205 open lows, 22 critical/high/medium blocked_tier4, 11 needs_gui). The claim does not hold at the candidate: 9 `fixed` entries are refuted by my re-runs (1 critical, 2 high, 6 medium, item 12), 2 new highs are open (rc1-verifier:1, :2), and rc1-drive-research-briefs:2 (medium) is unfixed. `vysted-r15-register.json` at 4c6dfe8c, `findings/rc1-verifier.json` |
| 2 | Gate 8: no trading path | **PASS** | none | My own openapi path list and tool lists: catalog 56, MCP 32 projected, 40 live, none trading. rg sweeps: 0 product-surface hits. Order paths return 404/405. An llama order attempt staged only a data write, not applied. Accepting place_order, submit_order or propose_order fails closed. audit_orders is absent. The safety surface vs r13-bedrock has 36 rows, all listed, and the candidate-to-HEAD surface diff is 0. `verifier/g2/{openapi-paths.txt,tools-lists.json,rg-*.txt,g8-order-paths.txt,g8-order-attempt.*,g8-portfolio-steps.json,datadir-tables-*.txt,safety-surface.tsv}` |
| 3 | Gate 8: tracked portfolio | **PASS** | none | Add with cost basis, then read back from the sidecar: 2 rows. P&L equals (price - cost) x qty on live quotes. The CSV export path works (non-Tauri fallback). Delete leaves 1 row on read-back. A gated llama write stages under ask, and accept applies it: 2 rows. `verifier/g2/g8-portfolio-steps.json`, `g8-portfolio-export.csv` |
| 4 | ci-local | **PASS** | none | My own run on a git-archive export of 4c6dfe8c: lint, format, typecheck, cargo fmt, clippy -D warnings, ruff check and format, vitest 152/1831, cargo test 19, pytest 3596 passed + 1 skipped. EXIT=0 at 12:13:39Z. The read-only rule forced two deviations: node_modules were linked, not a frozen-lockfile install, and the sidecar binaries came from rc1-cand, freshness-gated. The lane's own `logs/ci-local.log` (25 Sep) is from another sha and is not evidence. `verifier/g2/ci-local.log` |
| 5 | Smoke | **PASS** | none | SMOKE_EXIT=0 at 12:16:39Z. All 3 sidecars booted. Health 0.8.0, 13 agents, MCP ready with 40 tools. The binaries were built 06:08-06:10 IST, after the last sidecar commit (04:48) and after the candidate commit (06:01). `verifier/g2/smoke.log` |
| 6 | Agent scenarios | **FAIL** | harness/environment | The lane did not re-run at the candidate. All 20 OpenRouter transcripts and 7 of 13 llama transcripts are from 25 Sep, before the agent-runtime commits that landed before 4c6dfe8c. Only 6 llama runs are candidate-era, and property 3 (self-consistency b/thread) has no candidate-era run at all. `r15/rc1/scenarios/*.jsonl` (mtimes), rc1-verifier:14 |
| 7 | Owner-drives | **PASS** | none | All 8 groups have post-candidate raw evidence under `r15/surface/<group>/rc1/`. My 2 spot-checks on my own sidecar match. `verifier/g2/spot-screener-07.json`, `spot-panels-layouts.txt` |
| 8 | Fixed-name battery | **FAIL** | harness/environment | Of the 391 fixed ids, 76 have no raw file and 84 have raw output only from before the candidate. The ids are listed in `logs/rc1-verifier.md`. `r15/rc1/battery/raw/**`, rc1-verifier:13 |
| 9 | Data packs | **FAIL** | harness/environment | 14 of 24 packs were collected after the candidate. 10 (P15-P20, S1-S4) are from 25 Sep, before the data-route fixes. Shareholding returns 502 on 17 of 24 names, which is a product defect (rc1-verifier:1). `r15/rc1/battery/collected/*.json`, `verifier/g2/spot-shareholding.txt` |
| 10 | Fix loop closed | **FAIL** | product defect | rc1-drive-research-briefs:2 reproduces at 4c6dfe8c: MARKER_RE finds nothing in `[2, 3]`, and `[New findings]` ships as literal text. Both fix rounds live only on fix-int, and round-2's own recheck says 81fbfe91 does not certify it. I concur with all 5 triage rejections (rc1-verifier:26-30). `verifier/g2/fixloop-briefs2-citecheck.txt` |
| 11 | GUI round | **DEFERRED** | operator-attended | The round was skipped because the computer-use grant does not cover the built app. The 11 needs_gui ids are listed below. |
| 12 | Adversarial sample | **FAIL** | product defect | I re-ran the round-2 shard claims myself at 4c6dfe8c. 9 certified entries are refuted: AGENT-019, AGENT-093, DATA-002, DATA-113, LEAD-028, DATA-064, DATA-059, AGENT-053, RESEARCH-015. I also found 2 new high defects. `verifier/g2/adj-*.txt`, `spot-*.txt` |

## Blockers

These are why rc1 cannot be tagged at 4c6dfe8c:

1. **rc1-drive-research-briefs:2** (medium, research-search) is unfixed at the candidate: the citation net matches only a bare `[n]`, so `[2, 3]` and `[New findings]` ship unresolved. Files: `sidecar/services/research/citecheck.py:39`, `src/lib/brief-ingest.ts:396`.
2. **rc1-verifier:1** (high, data-smallcaps, new): BSE-only shareholding returns 502. `bse_provider._fetch_shp_index` uses plain httpx and BSE answers 403, while `_api_json` (curl_cffi) gets 200 for the same call. This also blocks the live repros of R15-DATA-022 and R15-DATA-056.
3. **rc1-verifier:2** (high, new): the MCP tools `list_workspaces` and `get_workspace` call `/workspaces`, but the route is `/workspace`, so every call 404s (`sidecar/services/mcp_server.py:252-265`).
4. **Refuted certifications at 4c6dfe8c** (rc1-verifier:4-12):
   - R15-DATA-002, critical. Code-level: the watchlist pick drops the region.
   - R15-AGENT-019, high. Fresh delete/update phrasings lose the write tools.
   - R15-AGENT-093, high. Nested numeric strings are not coerced.
   - R15-DATA-113, medium. INFY revenue estimate 491.65B is labelled USD.
   - R15-LEAD-028, medium. `/fundamentals/506597.BO` returns 404.
   - R15-DATA-064, medium. 30m with an explicit range returns in_eod_only.
   - R15-DATA-059, medium. The US master has no ISIN.
   - R15-AGENT-053, medium. News symbols are plain spans.
   - R15-RESEARCH-015, medium. Host-level independence counting.
5. **Chain coverage gaps** (harness): battery (76 ids with no raw, 84 stale), scenarios (hosted lane is all pre-candidate), data packs (10 of 24 pre-candidate).

## Operator-attended

| Id | Status | Severity | Reason |
|---|---|---|---|
| R15-CODE-AGENT-001 | needs_gui | high | GUI round skipped: the computer-use grant does not cover the built app |
| R15-LIFECYCLE-001 | needs_gui | high | same |
| R15-LIFECYCLE-008 | needs_gui | high | same |
| R15-UI-009 | needs_gui | high | same |
| R15-UI-022 | needs_gui | medium | same |
| R15-UI-025 | needs_gui | medium | same |
| R15-UI-050 | needs_gui | medium | same |
| R15-UI-083 | needs_gui | medium | same |
| R15-UI-084 | needs_gui | medium | same |
| R15-DOCS-024 | needs_gui | low | same |
| R15-LIFECYCLE-040 | needs_gui | low | same |
| R15-LEAD-030 / 035 / 037 / 038 | blocked_tier4 | high / medium / medium / medium | Known limitation of the local-model class ("figure for a subject with no ok tool call", value-only grounding). LEAD-035 is adjudicated to the operator (DECISIONS 4.9-4.12, `r15/stage-c/batch-24/LEAD-035-CONCURRENCE.md`). New local-lane instances are notes, not fix rounds. This gate adds one note: rc1-verifier:15 (ollama-sk4-sify-v2, ollama-sk3-elcidin-v2). |
| 18 other blocked_tier4 critical/high/medium entries | blocked_tier4 | 5 high, 13 medium | AGENT-017, RELEASE-001..004, AGENT-049, AGENT-064, CODE-FRONTEND-013, CODE-PLATFORM-010/015/071/073, CROSS-PLATFORM-001, DOCS-002/003/015, UI-044, UI-088. Tier-4, operator decision pending. |
| 5 not_a_defect and 14 removed_with_feature entries | as named | — | The four-area ones are concurred below. |

The bundle rehearsal passed at `64e9470e`, an ancestor of the candidate (`r15/stage-d/bundle-rehearsal/REHEARSAL.md`). I cite it and did not rebuild. Note that 202 files differ between 64e9470e and 4c6dfe8c.

## Fixed but uncertified

- **R15-CODE-DATA-023** (low) is `fixed` with no stage-c certificate. I checked it at 4c6dfe8c and it holds: the comments describe composition only, and `git grep` finds no stale counts (`battery/raw/set-71/CODE-DATA-023_probe.txt`).
- **Plausible, not proven, at code level:**
  - R15-CODE-PLATFORM-013: `resetToDefaultLayout` still calls `setEnabledMap({})`.
  - R15-AGENT-010: no explicit `yf.Search` timeout, although the fix_shape asks for one.
- **Round-2 shard claims I did not re-run** (open questions, not blockers here): CODE-FRONTEND-002, AGENT-045, DATA-112, DATA-066, UI-090, and the RESEARCH-024 news-lane adjacent.

## Adjacent findings

- rc1-verifier:1: BSE SHP 403, high.
- rc1-verifier:2: MCP /workspaces 404, high.
- rc1-verifier:15: local-lane figure note, low, known-limitation class.
- Known lows seen again: rc1-gate8:1/2/3. The CSV carries raw floats, and llama invented `cost_basis 0` on an order-shaped write, which was staged and not applied.

## needs_gui (exact ids)

R15-CODE-AGENT-001, R15-LIFECYCLE-001, R15-LIFECYCLE-008, R15-UI-009, R15-UI-022, R15-UI-025, R15-UI-050, R15-UI-083, R15-UI-084, R15-DOCS-024, R15-LIFECYCLE-040

## Four named areas

Counts are register statuses at 4c6dfe8c. An entry can sit in more than one area. All "open" entries are lows.

| Area | Before (census) | After (rc1) | Counts at 4c6dfe8c | Refuted at 4c6dfe8c by this verifier |
|---|---|---|---|---|
| ui-panels | `r15/surface/panels-layouts/`, `screener/`, `portfolio-notes/`, `settings-plugins/` (top-level census files) | `r15/surface/{panels-layouts,screener,portfolio-notes,settings-plugins}/rc1/*`, my `spot-panels-layouts.txt`, `spot-screener-07.json`, `spot-refutation-code.txt` | fixed 170, open 64, needs_gui 7, blocked_tier4 3, not_a_defect 3, removed_with_feature 3 | DATA-002, DATA-064, AGENT-053, AGENT-019 |
| agent-chat | `r15/surface/composer-chat/`, `failure-inducer/`, `onboarding-stranger/` | `.../rc1/*`, `rc1/scenarios/*.jsonl` (6 candidate-era), my `adj-agent019-intent-probe.txt`, `spot-agent093.txt`, `g8-agent-*` | fixed 164, open 54, blocked_tier4 9, needs_gui 2, not_a_defect 1 | AGENT-019, AGENT-093, AGENT-053 |
| research-search | `r15/surface/research-briefs/` | `r15/surface/research-briefs/rc1/*` (14 post-candidate), my `fixloop-briefs2-citecheck.txt`, `spot-research015.txt`, `spot-refutation-live.txt` | fixed 102, open 27, not_a_defect 2, blocked_tier4 1, needs_gui 1 | DATA-002, DATA-059, RESEARCH-015, plus rc1-drive-research-briefs:2 unfixed |
| data-smallcaps | `r15/battery/collected/`, `r15/BATTERY_DIFFS.md` census packs | `r15/rc1/battery/collected/*` (14 of 24 post-candidate), my `spot-shareholding.txt`, `spot-bse-shp.txt`, `spot-refutation-live.txt` | fixed 113, open 16, not_a_defect 2, blocked_tier4 1 | DATA-002, DATA-113, LEAD-028, plus new rc1-verifier:1 (BSE SHP 403) |

### Concurrence per not_a_defect / removed_with_feature id in the four areas

| Id | Status | Area | Verdict | Pointer |
|---|---|---|---|---|
| R15-CODE-PLATFORM-001 | removed_with_feature | ui-panels | concur | rc1-verifier:18, `verifier/g2/concur-killswitch-auditlog.txt` (D81: 3d037351, 5d45a0ae) |
| R15-UI-042 | removed_with_feature | ui-panels | concur | rc1-verifier:19, same file |
| R15-UI-043 | removed_with_feature | ui-panels | concur | rc1-verifier:20, same file |
| R15-AGENT-083 | not_a_defect | agent-chat | concur | rc1-verifier:21, `verifier/g2/tools-lists.json`; `r15/stage-c/batch-10/VERDICTS.json` concur_not_defect |
| R15-DATA-080 | not_a_defect | research-search, data-smallcaps | concur | rc1-verifier:22; `r15/stage-c/batch-11/VERDICTS.json` |
| R15-UI-041 | not_a_defect | ui-panels | concur | rc1-verifier:23, `verifier/g2/rg-src.txt` (DisclaimerFlow.test.tsx:58-66); `r15/stage-c/batch-6/VERDICTS.json` |
| R15-UI-047 | not_a_defect | ui-panels | concur | rc1-verifier:24; `r15/stage-c/batch-11/VERDICTS.json` |
| R15-UI-059 | not_a_defect | data-smallcaps, ui-panels, research-search | concur | rc1-verifier:25; `r15/stage-c/batch-11/VERDICTS.json` |

VERDICT: FAIL. There are 12 gate items: 5 PASS, 6 FAIL and 1 DEFERRED. rc1 is not tagged. The sha under test is 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2. Any rc1 tag must name that tree, not the head of 004, which has only docs-only commits on top of it. This gate does not certify that tree.
