<!-- refreshed 26 Sep 2026 04:10 IST at fcac96bd by the run-report narrative pre-refresh; delta-refreshed 07:13 IST at ce0a7abd through the burst launch (batch-24 merged, gate round 2 launched, Stage D refreshed); every line marked "(at the rc1 tag: …)" still changes at the tag, so the at-tag refresh remains a delta -->

# R15 LAUNCH — run report

## Outcome so far

R15 has not tagged a release candidate yet. The newest tag is still `r13-bedrock` (`6a40f83`),
which remains the fallback release line. (at the rc1 tag: the newest tag becomes `r15-rc1` at the
round-2 sha, and `r13-bedrock` stops being the fallback.)

The census closed on 23 Sep (Gate 2) and Gate 1 (Truth) holds. Trading is out of the product
permanently (`D81`, the 23 Sep scope change): no broker connectivity, order placement or
live/paper switch survives anywhere in the product; the user's own tracked portfolio and
everything the agent does with it stays.

The first rc1 gate round failed at 09:57 IST 25 Sep and no tag was cut. It passed Gate 8 (no
trading path, tracked portfolio intact), ci-local, smoke and the data packs. It failed on open
register entries, agent scenarios, owner-drives, the fixed-name battery and the fix loop, and on
an adversarial sample in which all 14 re-tested certified entries failed. A refutation audit
upheld every refutation (`4f2aba93`): 13 entries were reopened and one adjacent defect was filed.
Round 2 launched at 06:05 IST Sat 26 Sep (`wf_4ed38558-4d0`, from head `4c6dfe8c`) once the
register showed zero open critical/high/medium entries and no lows writer was still running
tests; both gating conditions were met. It is in flight (15/19 agents landed at this refresh,
four battery shards still running); **its verdict is pending at the tag and is not guessed here.**

Stage C has since merged batches 12 through 22 into `004-r4-experience-rebuild` (22 batches
merged in total, `a122dbf6` through `c155e5ad`), almost all of that chasing one entry:
`R15-LEAD-030` (high, agent-chat). After a tool call errors, the local model can still write a
made-up figure as if a tool had returned it. Eight fix batches (15 through 22) each closed every
shape a fresh verifier had found in the one before, and each time the next fresh verifier found a
new escape; batch 20 replaced sentence-shape matching with figure grounding by provenance
(`sidecar/services/figure_grounding.py`); batch 21 closed the negative-clause exemption ordering
and the ticker-only subject match; batch 22 added short-name aliases, unclosed-fence handling and
a fail-safe rule before its eighth failure fired the stop rule: no ninth filter round. A fresh
verifier in batch 23
concurred with `blocked_tier4` for LEAD-030 — the operator decides at rc1 whether to ship with a
documented known limitation — on the condition that the briefing's wording be broadened; the
corrected wording is `DECISIONS_FOR_OPERATOR.md` item 4.9.

A second agent-chat entry surfaced alongside it: `R15-LEAD-035` (medium) — an explicit no-tool
instruction ("answer without calling any tool") is not always honoured by the no-tool cue in
`planner.py`. Three rounds (batches 21–23) each failed a fresh verifier: batch 21's closed phrase
list under-matched several real phrasings; batch 22's regex over-matched, stripping tools from
legitimate data requests and provoking fabricated prices, and was rejected as a regression; batch
23's per-clause matcher still lost the tool surface on seven qualified negations and was also a
regression, left unmerged. The stop rule fired on the third failure. The same fresh verifier that
concurred on LEAD-030 REFUSED to adjudicate LEAD-035 away: the shipping (batch-21) matcher
over-matches too, and it named a narrowing-only fix — a closed-tail lookahead plus a
reported-speech guard — that "should not be deferred." Batch 24 (`wf_e17e21c5-cb8`, merged
`6778f892`) built exactly that fix and nothing else: 0 new strips on 97 phrasings and every OVER
prompt keeps its tools, but 4 of 18 fresh qualified-negation requests still lose every tool and a
fresh verifier did **not certify LEAD-035 a fourth time**, REFUSING the `blocked_tier4`
concurrence and naming one further narrowing-only guard (`batch-24/LEAD-035-CONCURRENCE.md`
§3/§4). Under the operator's three-failure rule, the lead merged anyway: LEAD-035 is now
`blocked_tier4` with the refusal on record, not adjudicated away
(`DECISIONS_FOR_OPERATOR.md` 4.10 offers (a) accept the residual or (b) one bounded round on the
rc2 line; the lead recommends (b)). Open critical/high/medium entries in the register are now
**zero**.

Two more mediums were filed from the same batch-22/23 evidence: `R15-LEAD-037` (the figure guard
grounds a price by value only, so a stale bar from the same tool payload can pass as the current
price) and `R15-LEAD-038` (with tools withheld, the model can narrate a portfolio write that
never happened — no order row, no queued review, no position change). The fresh disposition
verifier concurred `blocked_tier4` on a corrected wording for both (`4fd3cbfd`);
`DECISIONS_FOR_OPERATOR.md` items 4.11 and 4.12 carry the operator-facing text.

The register (`vysted-r15-register.json`: 887 raw findings → 652 entries + 76 rejections; 16
critical / 116 high / 293 medium / 227 low) now has **zero** open critical/high/medium entries;
everything open is a low (205 of the 227). 26 entries are `blocked_tier4` (up from 25 — LEAD-035
joined LEAD-030, LEAD-037 and LEAD-038, the agent-chat known-limitation class named in
`DECISIONS_FOR_OPERATOR.md` §4.9–4.12), 11 `needs_gui`, 14 `removed_with_feature` (the trading
removal), 5 `not_a_defect`, and 391 fixed.

The three lows write waves finished at the batch-18 merge head (`ebc5ed41`): 184 fixed, 7
could_not, 3 not_a_defect_proposed, across 27 writer sets on their own branches — none of it
integrated yet. Gate round 2 launched at 06:05 IST Sat 26 Sep (`wf_4ed38558-4d0`, from head
`4c6dfe8c`) once the register showed zero open critical/high/medium entries; the lows-writer
condition was already satisfied.

**Stage D and the burst (pacing change 5, 06:45–07:10 IST Sat 26 Sep).** Off the machine's
heavy/live-app/GUI/local-model lanes — reserved for gate round 2 until it returns — the run
burst every remaining off-lane item to the concurrency ceiling. Stage D refreshed all five drafts
plus FACTS at head `4d893147` (`7c685b9f`, carrying the hand-added 'Known limitations at rc1'
block); a third-party notices draft was authored (`ccd542f0`: 1046 bundled packages across the
three sidecars, npm and Rust crates, 22 copyleft rows) alongside a GUI-round script
(`1dc9c325`, held on the operator's away-sentinel, which is not yet armed); a decisions
reconciliation pass filed `DECISIONS_FOR_OPERATOR.md` §5 (`3b90820e`) — headline **§5.1: eight
AGPL-3.0-only `openbb-*` packages, plus `sec-edgar-mcp` (AGPL-3.0) and `Unidecode` (GPLv2+), ship
unmodified inside two of the three sidecar binaries alongside the PolyForm Strict core; the
operator's licensing call, status awaiting operator**; a production-bundle rehearsal from a clean
profile came back **PASS-WITH-FINDINGS** at `64e9470e` (`c584f545`/`69f47e48`); the LEAD-035
disposition was folded into the Stage D drafts (`ed82d896`) and a new-lows draft filed 6 entries
(`e29ca6c7`) for the P1 adjudication. Three workflows launched in the same window, all still in
flight at this refresh: lows pre-integration for P1/P2/P3 (`wf_33fb46f9-580`), the remaining-lows
sweep — could_not retries, a fresh refuter and the new-lows/deferred writers (`wf_971af170-542`)
— and the judge-panel build specs plus the final-adversarial-pass authoring and the operator
handover draft (`wf_8388c01a-1e5`). None of this is integrated or tagged; it is off-lane and
marked "untested pending integration" until the gate returns.

(at the rc1 tag: replace this paragraph with the round-2 verdict, its time and the tag sha.)

## Gate table

| # | Gate | Status | Evidence | Time (IST) |
|---|---|---|---|---|
| 1 | Truth | **HOLDS** | run-state decisions R15-D1..D6 + `r15/stage0/`; commit `38ded25b` | 04:57 23 Sep |
| 2 | Census closed | **HOLDS** (after two BLOCKED passes) | `R15_GATE2.md` (three fresh-context Opus verifiers); commit `99e2ae38` | BLOCKED 13:28 and 14:17, HOLDS 15:00, all 23 Sep |
| 3–7 | not individually named | **not recorded** | The run brief is the only document that names gates 3–7, and this report does not read it. The run-state goes from Gate 2 to Stage C and then to the rc1 gate. | — |
| 8 | Safety (rewritten by the scope change): no order, broker or simulated-account path anywhere; tracked portfolio intact | **PASS in rc1 round 1** | `R15_GATE_RC1.md` items 2–3, `r15/rc1/GATE8.md`: 111 routes, none for orders, brokers, the kill switch or the audit log; 40 MCP tools, none for orders; the portfolio round-trip passed, including an agent write held for review | 09:57 25 Sep (at the rc1 tag: re-proved by round 2) |
| rc1 | Release-candidate gate | **round 1 FAILED 09:57 IST 25 Sep, no tag; round 2 LAUNCHED 06:05 IST 26 Sep (`wf_4ed38558-4d0`), in flight — verdict pending, not guessed here** | `R15_GATE_RC1.md` + `r15/rc1/` (commit `b2cfbb68`); the gate's own fix rounds merged as `57897778` | (at the rc1 tag: round-2 verdict, time and tag sha) |

rc1 round 1, item by item (run `wf_7c4b2e60-141`, 43 agents, 296 min; candidate `1d6511c8`):

| Item | Result | Item | Result |
|---|---|---|---|
| 1 Register criterion | FAIL — 5 c/h/m open + LEAD-010 fixed but uncertified | 7 Owner-drives | FAIL — a null market cap ranked first in a market_cap-desc sort |
| 2 Gate 8: no trading path | PASS | 8 Fixed-name battery | FAIL — 160 of 376 fixed ids had no raw output |
| 3 Gate 8: tracked portfolio | PASS | 9 Data packs | PASS — 24/24 complete |
| 4 ci-local | PASS — vitest 1825, cargo 19, pytest 3150 + 1 skipped | 10 Fix loop closed | FAIL — a fabricated SIFY ADR ratio unclosed after two rounds |
| 5 smoke | PASS — 3 sidecars, MCP toolCount 40 | 11 GUI round | DEFERRED — the computer-use grant does not cover the built app |
| 6 Agent scenarios | FAIL — 11/20 OpenRouter runs hit upstream 5xx; local-model runs contended | 12 Adversarial sample | FAIL — 14/14 certified entries refuted when re-run |

## Stages

**A — reconcile and relicense (closed 04:57 IST 23 Sep).** A worktree-salvage scout, the
relicense to PolyForm Strict 1.0.0 plus a commercial licence (`0c63d465`), an isolated stack
rebuilt from source on :52152-54, the Ollama local-lane proof (`r15/stage0/LOCAL_LANE_PROOF.md`)
and the num_ctx fix. Gate 1 holds. Loop log L9–L12.

**B — census (closed 15:00 IST 23 Sep).** Refute waves over every raw finding, Stage B items
1–6, and three Gate 2 attempts. Result: 887 raw findings became 603 register entries plus 76
rejections, all 23 intent chunks and 1,032/1,032 promises were assessed, and the coverage map
covers 101 surfaces in 288 cells. Loop log L12–L19.

**C — fix batches 1–24.** "Certified" means a fresh verifier re-proved the claim on the running
app, not that the writer said so. Tallies are each batch's own `r15/stage-c/batch-N/VERDICTS.json`.
Batch 1 has no VERDICTS file; its evidence is `r15/stage-c/REMOVAL_PLAN.md` and loop log L20.
Ids drop the `R15-` prefix. Batches 1–22 are merged into `004-r4-experience-rebuild`. Batch 23
built LEAD-035's third fix but a fresh verifier found it a regression on seven qualified
negations, so its int branch (`9aa9fb6c`) was never merged — base (batch-21's closed phrase list)
still ships. Batch 24 built the disposition verifier's narrowing-only fix instead of a new attempt
at the same shape; it merged (`6778f892`) but LEAD-035 was still not certified a fourth time, so
it now ships as `blocked_tier4` under the operator's three-failure rule.

| Batch | Scope | Merge | Merged (IST) | Certified | needs_gui | Not certified |
|---|---|---|---|---|---|---|
| 1 | trading removed from the product (D81) | `a122dbf6` | 23 Sep 16:33 | removal proved by the batch verifier (0 broker/order/kill/audit routes; all 22 former routes 404) | 0 | 0 |
| 2 | critical/high data, research, workspace | `806a90ca` | 23 Sep 18:47 | 37 | 0 | 3 (DATA-005, DATA-014, AGENT-001) |
| 3 | agent runtime, AUTO gate, LLM adapters, research depth | `c81d879b` | 23 Sep 21:07 | 38 | 0 | 2 (DATA-020, RESEARCH-005) |
| 4 | context admission, Gemini/xAI lanes, workflows, market-data gate | `dcbe7bae` | 24 Sep 00:01 | 45 | 2 | 3 (DATA-015, DATA-020, DATA-032) |
| 5 | India exchange lanes, resolver, runtime liveness | `1574ed8e` | 24 Sep 03:03 | 48 | 2 | 6 (LEAD-010, DATA-017, CODE-PLATFORM-018, AGENT-051, AGENT-052, CODE-FRONTEND-015) |
| 6 | India Emerge lanes, tool-call identity, research funnel (recovered after a harness stall; 22 delivered) | `5e147317` | 24 Sep 15:34 | 21 | 0 | 3 (CODE-PLATFORM-018, AGENT-046, RESEARCH-024); UI-041 concurred not a defect |
| 7 | India fundamentals, durable Delegate runs, chart integrity | `e81c9e7c` | 24 Sep 17:53 | 50 | 1 | 4 (AGENT-045, LEAD-005, AGENT-046, CODE-PLATFORM-021) |
| 8 | sidecar lifecycle, provider readiness, data-error honesty | `68bb7aa4` | 24 Sep 20:06 | 39 | 1 | 7 |
| 9 | tool-call identity, research brief contract, fundamentals truth | `6b702305` | 24 Sep 22:44 | 29 | 2 | 14 |
| 10 | runtime and backtest integrity, catalog and host actions, plugin lifecycle | `f407107f` | 25 Sep 01:43 | 50 | 1 | 4 (CODE-AGENT-009, UI-091, DATA-071, LEAD-013); AGENT-083 concurred not a defect |
| 11 | build recipe and gates, schema versions, agent eval, option chain | `4097dac4` | 25 Sep 04:55 | 18 | 0 | 2 (LEAD-028, RELEASE-007); UI-047, UI-059, DATA-080 concurred out of scope |
| 12 | rc1 refutation-audit reopenings and gate findings | `ef33c7f6` | 25 Sep 11:25 | 19 | 0 | 3 (RESEARCH-007, DOCS-017, AGENT-090) |
| 13 | source tiers via the Public Suffix List, live universe counts, ADR ratio guard | `a217a529` | 25 Sep 12:36 | 2 (RESEARCH-007, DOCS-017) | 0 | 2 (AGENT-090, CODE-AGENT-033) |
| 14 | tool_result stream event and grader; ADR ratio guard, second pass | `17301f54` | 25 Sep 13:29 | 1 (CODE-AGENT-033) | 0 | 1 (AGENT-090) |
| 15 | ADR ratio grounded from the SEC 20-F cover page (strongest-tier root cause) | `74ee3468` | 25 Sep 14:54 | 0 | 0 | 1 (AGENT-090) |
| 16 | ratio-guard class qualifier, tool-citation guard, bounded ADR lookup | `d64640d2` | 25 Sep 15:55 | 2 (AGENT-090, LEAD-032) | 0 | 1 (LEAD-030); LEAD-031 not attempted |
| 17 | citation guard across turns, partial tool-call marker hold | `292ba53a` | 25 Sep 16:50 | 1 (LEAD-031) | 0 | 1 (LEAD-030) |
| 18 | LEAD-030 strongest-tier root cause (step 1, branch `ecdd223e`) + LEAD-033 (tool-steps trailer echo) and LEAD-034 (Emerge `-SM` suffix gate), step 2 | `ebc5ed41` | 25 Sep 18:56 | 2 (LEAD-033, LEAD-034) | 0 | 1 (LEAD-030, fourth attempt) |
| 19 | LEAD-030 fifth attempt — colon-bound attribution + result-shaped all-errored blocks | `ec7f7cd6` | 25 Sep 20:15 | 0 | 0 | 1 (LEAD-030) |
| 20 | LEAD-030 sixth attempt — figure grounding by provenance (new `services/figure_grounding.py`, replaces shape matching); LEAD-036 fence unit holder | `1abef99b` | 25 Sep 22:09 | 0 | 0 | 2 (LEAD-030, LEAD-036) |
| 21 | LEAD-030 seventh attempt — negative-clause exemption ordering + ticker-only subject match closed; LEAD-035 first attempt | `86ae79c4` | 25 Sep 23:28 | 0 | 0 | 3 (LEAD-030, LEAD-035, LEAD-036) |
| 22 | LEAD-030 eighth attempt — short-name aliases, unclosed-fence handling and a fail-safe rule added, stop rule fires; LEAD-035 second attempt (a regression, excluded from the merge) | `c155e5ad` (W1 only) | 26 Sep 00:53 | 0 | 0 | 3 (LEAD-030 stop rule fired; LEAD-035 not merged; LEAD-036 not a regression, stays open) |
| 23 | LEAD-035 third and final attempt; LEAD-030 disposition concurrence sought; LEAD-037 + LEAD-038 filed from the batch-22 verifier's Issues | not merged (int `9aa9fb6c`) | — | 0 | 0 | 1 (LEAD-035, a regression) |
| 24 | LEAD-035 — the disposition verifier's narrowing-only fix (closed-tail lookahead + reported-speech guard) and nothing else | `6778f892` | 26 Sep 06:00 | 0 | 0 | 1 (LEAD-035, not certified a fourth time; concurrence refused; merged anyway under the three-failure rule, now `blocked_tier4`) |

(at the rc1 tag: add the rc1 gate round-2 verdict.)

**LEAD-030/035/037/038 disposition (04:03 IST Sat 26 Sep).** After batch 23's stop rule fired for
both entries, one Opus writer rewrote `DECISIONS_FOR_OPERATOR.md` §4.9 to the concurred, broader
wording and filed §4.10 (LEAD-035), §4.11 (LEAD-037) and §4.12 (LEAD-038) as one known-limitation
class (`535307c8`). A fresh Opus verifier then ran 141 live turns against a source sidecar at
`014bb7f1` and ruled per entry (`4fd3cbfd`): LEAD-038 **CONCUR**; LEAD-037 **CONCUR** on a
corrected wording (the guard never checks a figure for a subject whose call succeeded, striking
the LEAD-030 briefing clause that said otherwise); LEAD-035 **REFUSED** — the shipping matcher
over-matches seven explicit data requests too, and llama then invents a price presented as fetched
in 15 of 21 live runs — and named a narrowing-only fix the verifier said "should not be deferred."
Batch 24 built exactly that fix (`6778f892`); a fresh verifier still did not certify LEAD-035 a
fourth time and refused the `blocked_tier4` concurrence, naming one further narrowing-only guard.
Under the operator's three-failure rule the lead merged anyway: LEAD-035 joins LEAD-030, LEAD-037
and LEAD-038 as `blocked_tier4`, with the refusal on record rather than adjudicated away. Open
critical/high/medium entries in the register: **zero**.

**rc1 gate, round 1 (failed 09:57 IST 25 Sep).** See the gate table. The gate's two fix rounds
merged as `57897778`. The chain was green at `1d6511c8`, but the verifier failed the candidate on
the items above. The needs_gui set stays operator-attended because the rig's computer-use grant
does not cover the built app.

**Refutation audit (10:12 IST 25 Sep, `4f2aba93`).** Run `wf_90712d2d-cab` re-examined the 14
refuted certifications. It found 1 confirmed regression (DATA-059) and 12 partial fixes, where the
entry's own repro holds but the verifier's adjacent claim reproduces. It also filed 1 adjacent
finding as the new entry AGENT-092 and found 0 verifier errors. 13 entries were reopened, and the
gate verifier had got nothing wrong. Evidence:
`r15/rc1/refutation-audit/REFUTATION_AUDIT.md`. Round-2 preparation followed:
- Gate-script tuning `91dac548`: drive and battery limits, a local-model lock, and a battery
  indexer that covers every fixed id.
- The not-a-defect concurrence rubric restored in `3c51ac3c`.
- A verifier rule, "certify the claim, not only the repro", in `f1a2682d`.

**Filing-watcher model groundwork (measured; verdict: not worth fine-tuning; backlog candidate).**
Off the release line; no code in this release. The prep ran 05:07 IST and the measurement 11:41
IST on 25 Sep, committed as `52d6957e`. The backlog entry sits in `r15/invent/BACKLOG.md` for the
judge panel.

**Lows.**
- Pre-triage (`84418994`): 199 still reproduce, 5 were already fixed, 1 was proposed as not a
  defect and 1 was a duplicate.
- Partition (`9ec6bd17`, patched `dd7b98e9`): 194 entries in 27 writer sets (P1 63, P2 64, P3 67),
  4 verify-only, 1 proposed not-a-defect, 4 blocked on Tier-1 files, and 7 deferred.
- Bucket adjudication (`3483b699`): the 4 blocked lows went to blocked_tier4, with
  `DECISIONS_FOR_OPERATOR.md` rows 4.5–4.8. The 2 GUI-only deferrals went to needs_gui. The 5
  inseparable lows stay open for a serial set after the partitions merge.
- Write waves (pacing change 3; launched at the batch-18 merge head `ebc5ed41`): P1 (`06ce565f`,
  9 writer branches) 61 fixed, 2 could_not; P2 (`2ea83865`, 9 branches) 60 fixed, 3 could_not, 1
  not_a_defect_proposed; P3 (`c40bf690`, 9 branches) 63 fixed, 2 could_not, 2
  not_a_defect_proposed. Totals: **184 fixed, 7 could_not, 3 not_a_defect_proposed** across 27
  writer sets, each on its own branch — no lows writer is still running tests. None of it is
  integrated: integration is one partition at a time, rebased onto the rc1 head after the tag,
  each with a fresh verifier and a lead merge, then the serial set for the 5 inseparable lows.

**D — docs wave drafts (refreshed).** Run `wf_31f149cf-57d` wrote the first drafts at `f4444790`,
committed as `5f1ddaae` (24 Sep 23:17): 5 drafts, each revised after a critic, plus the secrets,
licence and dependency scans. Run `wf_acb50b5c-0d7` (26 Sep 04:19, 20 agents, 36 min) refreshed all
five against head `4d893147` and regenerated `FACTS.md` (`7c685b9f`), carrying forward the
hand-added 'Known limitations at rc1' block and the LEAD-030/035/037/038 disposition wording
verbatim into RELEASE_NOTES, OPERATOR_BRIEFING and CURRENT_STATE under the local-model lane. A
one-Sonnet-agent follow-up (`ed82d896`) then folded the LEAD-035 `blocked_tier4` escalation and
all 8 bundle-rehearsal runbook corrections into the same drafts. A third-party notices draft
(`ccd542f0`) and a GUI-round script (`1dc9c325`) were authored alongside. None of the drafts are
promoted yet; still due at the tag: final facts patched with the tag sha, gate verdict, and
0.9.0.

**Bundle rehearsal.** Run `wf_f3b7fd1a-361` (26 Sep 05:05, 1 Opus agent, 18 min) rehearsed a
production bundle from a clean profile at head `64e9470e`: offline install, all three sidecar
builds, an unsigned `tauri build`, the sidecar smoke test and a clean-profile app launch all
passed. Verdict **PASS-WITH-FINDINGS** (`c584f545`/`69f47e48`): the app rendered a working cockpit
and shut down cleanly, but a `HOME=`-isolated launch still wrote WKWebView housekeeping files into
the operator's real `~/Library` (recorded, not reverted) and the `.app`/`.dmg` are ad-hoc/unsealed
pending the operator's own signing. Eight runbook corrections and five new lows were filed from
the findings.

**DECISIONS §5 (new operator items, 26 Sep).** Run `wf_7370dec8-7cb` (05:26 IST, 1 Opus agent, 3.9
min) filed `DECISIONS_FOR_OPERATOR.md` §5.1–5.10 (`3b90820e`). Headline **§5.1: eight
AGPL-3.0-only `openbb-*` packages, plus `sec-edgar-mcp` (AGPL-3.0) and `Unidecode` (GPLv2+), ship
unmodified inside the openbb-mcp and sec-edgar-mcp sidecar binaries, alongside the same
`.app`/`.dmg` as the PolyForm Strict core** — recommendation: ship them as separate programs with
a third-party notices file for 0.9.0 and get a lawyer's read before the first commercial licence;
**status: awaiting operator**. The remaining items (5.2–5.10) cover the `frozendict` LGPL
dependency, resolved empty-metadata packages, the CLAUDE.md AGPL line, unverified Windows builds,
a clean secrets scan, the missing post-D81 rollback artefact, the groundwork folder's public
naming, and the two rehearsal findings.

**E — judge panel (done).** Run `wf_d855d73b-b6b` launched at 17:25 IST 25 Sep; 5 of 7 agents died
on API safeguard errors (all 4 Opus case-builders and Fable judge B), landing only judge A and a
synthesis over one judge's scores. A completion run, `wf_407df695-831` (launched 17:59 IST 25
Sep), added judge B independently (it never read the first run's output) and rewrote the
synthesis from both judges. `r15/invent/PANEL.md` + `PANEL.json` are on disk, committed
`52b47455`: 59 rows judged, 47 survivors, 12 killed, top survivor **BL-03 "Reasons about you"**
(the position half; S, 3 days), runners-up BL-18 then BL-11. The one small build waits for rc2.

**Pacing changes (operator).**
1. 21:45 IST 24 Sep: the agent ceiling rose from 8 to 16 and two workflows could run on
   different lanes. Waves were sized at about half a window, single lanes stayed single, and each
   merged batch got one fresh verifier.
2. about 01:45 IST 25 Sep: the ceiling rose to 32, with up to three workflows on different lanes
   and no workflow outliving two walls. `r15-rc1` is to be tagged the moment its gate passes,
   before the lows. A follow-up note at 03:35 split the lows into three concurrent partitioned
   workflows with serial integration.
3. 17:15 IST 25 Sep: the lows write runs launch at the batch-18 merge, not at the tag. Gate round
   2 waits until no writer is running tests. The judge panel starts now, off-machine. Up to four
   workflows can run on different lanes, and the panel and docs lanes do not count. At most 18
   test-running writers run on this Mac. Waves run full-size, and low-priority mode is allowed in
   a wall gap only if the tiers in flight are actually served.

## Register now

The snapshot is `vysted-r15-register.json` as last committed at `4c6dfe8c` (batch-24 merged as
`6778f892`; LEAD-035 flipped to `blocked_tier4` under the three-failure rule with the verifier's
refusal on record). Before that it was `1db862d0`, batch-24's adjudicator applying batch-23's
verdicts and the LEAD-030/037/038 disposition concurrence. Its own `counts` field: **887 raw
findings → 652 entries + 76 rejections** (16 critical / 116 high / 293 medium / 227 low);
`python3 scripts/r15/register.py status` reports the same raw (887) and rejections (76) but a
lower freshly-recomputed entries figure, because that command rebuilds entries straight from the
`r15/census/merge/` cluster files and new-finding files, and several Stage C adjudicators write
`vysted-r15-register.json` by hand rather than through `register.py build` — the table below is
derived from the register JSON's own entries, the more current of the two.

| Severity | fixed | open | needs_gui | blocked_tier4 | removed_with_feature | not_a_defect | total |
|---|---|---|---|---|---|---|---|
| critical | 16 | 0 | 0 | 0 | 0 | 0 | 16 |
| high | 105 | 0 | 4 | 6 | 1 | 0 | 116 |
| medium | 258 | 0 | 5 | 16 | 9 | 5 | 293 |
| low | 12 | 205 | 2 | 4 | 4 | 0 | 227 |
| **total** | **391** | **205** | **11** | **26** | **14** | **5** | **652** |

- **Open critical/high/medium: 0.** `R15-LEAD-035` (medium, agent-chat area) flipped to
  `blocked_tier4` at the batch-24 merge, under the operator's three-failure rule, with the fresh
  verifier's refusal on record rather than a CONCUR.
- **blocked_tier4 (26, up from 25):** the prior 22 (`DECISIONS_FOR_OPERATOR.md` §4.2–4.8) —
  RELEASE-001..004 and AGENT-017 (high); AGENT-049, AGENT-064, CODE-FRONTEND-013,
  CODE-PLATFORM-010/015/071/073, CROSS-PLATFORM-001, DOCS-002/003/015, UI-044, UI-088 (medium);
  CODE-PLATFORM-063, DOCS-008, DOCS-011, RELEASE-012 (low) — plus `R15-LEAD-030` (high, §4.9),
  `R15-LEAD-037` + `R15-LEAD-038` (medium, §4.11–4.12) and now `R15-LEAD-035` (medium, §4.10), the
  agent-chat known-limitation class from the batch-23/24 disposition round. The briefing draft §3
  groups the prior 22 by the decision each waits on.
- **needs_gui (11):** CODE-AGENT-001, LIFECYCLE-001, LIFECYCLE-008, UI-009 (high); UI-022,
  UI-025, UI-050, UI-083, UI-084 (medium); DOCS-024, LIFECYCLE-040 (low). Each needs a human
  click-through; `r15/stage-d/OPERATOR_BRIEFING.draft.md` §4 lists the check for each. A GUI-round
  script (`1dc9c325`) is authored and ready but held on the operator's away-sentinel.
- **Open lows (205 of 227):** the register's own count, not yet moved by the lows write waves —
  their 184 fixed / 7 could_not / 3 not_a_defect_proposed results sit on unmerged writer branches
  (see Stages) and only change these counts once each partition integrates after the rc1 tag. A
  burst launched lows pre-integration candidate branches for P1/P2/P3 and a remaining-lows sweep
  (could_not retries, a fresh refuter, the new-lows/deferred writers) in parallel with gate round
  2; none of it is merged.

(at the rc1 tag: re-derive this section from the register at the tag sha, and fold in whatever
the lows integration moves.)

## What is still ahead

The order comes from the run-state header's "Next action" line:

1. rc1 gate round 2 (in flight, run `wf_4ed38558-4d0`, launched 06:05 IST 26 Sep from head
   `4c6dfe8c`) — the register already shows 0 open critical/high/medium and no lows writer is
   running tests; verdict pending, not guessed here.
2. Tag `r15-rc1` the moment round 2 passes, then push, prune worktrees, merge the version branch
   (`c1e9164c`, `git restore CLAUDE.md` first) and refresh this handover.
3. Lows integrate P1, P2, P3 one at a time, rebased onto the rc1 head (ports
   :52320/:52330/:52340), each with a fresh verifier and a lead merge — pre-integration candidate
   branches are being assembled now by the burst (`wf_33fb46f9-580`). Then a serial set handles
   the 5 inseparable lows.
4. Stage D: promote the refreshed drafts (regenerated at `7c685b9f`; notices draft `ccd542f0`),
   write 0.9.0 into every version file, make the single CLAUDE.md commit, and build a production
   bundle from a clean profile (the rehearsal already passed with findings at `64e9470e`; a real
   bundle still runs on the integrated head).
5. The GUI round (`1dc9c325`, script authored and ready) once the operator arms the rig's
   away-sentinel.
6. Tag `r15-rc2`.
7. The one small build of the judge panel's top survivor (`BL-03`, "Reasons about you" — the
   position half); its spec and critic were authored in the burst (`wf_8388c01a-1e5`).
8. Tag `r15-rc3`.
9. Exactly one final adversarial pass (its script, scenarios and rubric were authored in the
   burst, `wf_8388c01a-1e5`).
10. Tag `r15-launch`.

The handover is refreshed at every tag.

## Where the evidence lives

- Header, in-flight ledger and loop log: `docs/redesign/verification/vysted-r15-run-state.md`
- Waves table and spend: `docs/redesign/verification/R15_RUN_LOG.md` (86 rows tabulated as of
  run-log backfill #6 part 1, 07:13 IST 26 Sep 2026; $0.21824 paid spend, all OpenAI-direct, up
  from $0.201076 at backfill #5); paid-call ledger
  `docs/redesign/verification/r15/spend-ledger.jsonl` (498 lines)
- Register: `docs/redesign/verification/vysted-r15-register.json` (+ `.md` view); new leads
  waiting to be filed: `r15/stage-c/LEAD_FOUND.json`
- Gate 2: `docs/redesign/verification/R15_GATE2.md`
- rc1 round 1: `docs/redesign/verification/R15_GATE_RC1.md`, `r15/rc1/` (`VERDICT.md`,
  `FINDINGS.md`, `GATE8.md`, `fix-r1/`, `fix-r2/`, `verifier/`), and the refutation audit
  `r15/rc1/refutation-audit/`
- Stage C: `docs/redesign/verification/r15/stage-c/batch-{2..17}/` (`PLAN.md`, `VERDICTS.json`,
  `VERDICTS.md`; batches 14–17 also `verifier-evidence/`); the trading removal
  `r15/stage-c/REMOVAL_PLAN.md`
- Lows: `r15/stage-c/lows-triage/LOWS_TRIAGE.md`, `r15/stage-c/lows/PARTITION.md`
- Filing-watcher model groundwork (the scope-change-2 measurement folder under `r15/`; its folder
  and script names are withheld here per the operator's naming ban): `VERDICT.md` +
  `measurements/`
- Ranked backlog and judge panel: `r15/invent/BACKLOG.md`; `r15/invent/PANEL.md` once the panel
  commits
- Stage D drafts and scans: `docs/redesign/verification/r15/stage-d/`
- Workflow scripts and exact relaunch arguments: `docs/redesign/verification/r15/tooling/`
- Decision logs: `docs/redesign/DECISIONS.md`, `docs/redesign/DECISIONS_FOR_OPERATOR.md` (§5,
  new 26 Sep: AGPL/GPL licensing, the CLAUDE.md AGPL line, Windows verification, the bundle
  rehearsal's findings — all awaiting operator except where noted)
- Batch summaries: `CHANGELOG.md` has sections for the trading removal, batches 2–17 and "R15
  rc1 gate — round 1" (`b1ee6aa5`). Batches 18–24 have no CHANGELOG section yet.
- Workflow journals: `…/3e7ae14d-d48a-4882-8a75-f7608754c23f/subagents/workflows/<runId>/journal.jsonl`
  (this session) and `…/5df12ac0-f23e-48c6-b614-80321cbbfb31/subagents/workflows/<runId>/journal.jsonl`
  (the 19 Sep session). Both folders are outside the repo, in the operator's local Claude Code project store.
