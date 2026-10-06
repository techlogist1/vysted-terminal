# rc1 tag-window header draft

Proposed replacement text for four lines of the run-state HEADER block
(`docs/redesign/verification/vysted-r15-run-state.md`). Each block below is
paste-ready as the named line. Facts only, shas cited, under ~900 characters
each. Not applied to the run-state by this branch — the lead splices these
in at the tag; the run-state stays lead-only.

## `- Current stage:`

```
rc1 GATE ROUND 5 read under GATE RULE CHANGE 1 (DECISIONS §6.1): round 5 (`wf_7ded8293-3fe`, 279 min, 56 agents) sheet verdict FAIL under the old all-or-nothing rubric (`R15_GATE_RC1.md` @313676e9) but PASSES the fixed bar — chain green, Gate 8 PASS, register criterion PASS. Adjudicated `510e936d`→`872382b7`: 4 regressions reopened for 0.9.1, 57 new entries filed (1 high + 24 medium + 32 low). The one bounded fix round merged `794bc68f` (R15-LEAD-059 certified), but its own fresh verifier filed a new high, R15-LEAD-116 (an explicit FOCUS.BO pin still serves the NSE company's disclosure feed), plus R15-LEAD-117 low — open c/h = 1. Recheck launched on `949c3c9f` (`wf_da354223-f11`): chain green + Gate 8 PASS on disk (`round-5-recheck/{PREFLIGHT,GATE8,REGRESSION}.md`), battery lane (25 shards) still running — it did not gate the tag. Tagged: `r15-rc1` (annotated tag object `0e0852e9`) on `949c3c9f`, pushed 03:13:57 IST Sat 3 Oct 2026. Operator took DECISIONS §4.22 option (d): LEAD-116 is an OPEN HIGH at 0.9.0-rc1; its bounded fix runs first in the lows integration (in flight), certified by that candidate's fresh verifier. rc2 requires open critical/high = 0 including it; if certification fails once, it is filed for 0.9.1 with its fail-safe described.
```

## `- Gates that hold:`

```
Gate 1 (Truth) ✓ 04:58 23 Sep; Gate 2 (Census closed) ✓ 15:00 IST 23 Sep (`R15_GATE2.md`). Gate 8 (no trading path) re-proved at round 5 (`633f8440`: 101 routes, 0 trading-surface hits; catalog=schemas=allow-list 56, MCP 40; fail-closed order attempt; no audit_orders table) and again at recheck candidate `949c3c9f` (`GATE8.md`: PASS, 0 findings) — chain green both times (round-5 ci-local EXIT=0: pytest 3780+1 skipped/vitest 1881/cargo 19; recheck ci-local EXIT=0: pytest 3784+1 skipped/vitest 1881/cargo 19; smoke EXIT=0 both). Register criterion held both times (round-5 sheet: 679 entries, 398 fixed, 215 open all-low; recheck candidate: 738 entries, 395 fixed, 277 open = 1 high (LEAD-116) + 28 medium + 248 low, 35 blocked_tier4, 11 needs_gui). Scenarios + GUI stay operator-attended/deferred, as every round this release.
```

## `- Newest tag:`

```
`r15-rc1` (annotated tag object `0e0852e9`) on `949c3c9f`, pushed 03:13:57 IST Sat 3 Oct 2026, under DECISIONS §4.22 option (d) (R15-LEAD-116 open high at rc1, fixed first in the lows integration). Previous tag `r13-bedrock`. 004 now carries 0.9.0 (`06879089`) and the 0.9.1 backlog draft (`6f165d86`).
```

## `- Next action:`

```
Post-tag order (DECISIONS §6.2, verbatim); done so far: push, hygiene prune (record `9368c626`), version merge (`06879089`), handover refresh (this commit). Remaining: LEAD-116 fix first inside the lows integration as ONE candidate (`worktree-agent-lows-P1-int-4c6dfe8@dbe5fe4f`+`-P2-int-4c6dfe8@78220d0c`+`-P3-int-4c6dfe8@f9da207a`, rebased onto the TAG off-lane, conflicts resolved, one chain run + one fresh verifier) + GUI round on the rig (re-arm `~/.vysted-rig-away`) + docs promotion as results land → clean-profile bundle → r15-rc2 → ONE final adversarial pass under the same bar (c/h closed one round, m/l filed for 0.9.1) → r15-launch. Held, never auto-merged: `worktree-agent-backlog-0.9.1@a3c7a384` (merges AT the tag), `feature/bl-03-reasons-about-you@4ea397d1` (NEVER merged). Operator briefing + 0.9.1 backlog written BEFORE the launch tag.
```
