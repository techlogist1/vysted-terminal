# Refutation audit round 4, group surface: rc1-vshard-3:3 (tie R15-AGENT-043)

Auditor: Opus, 06:45-07:14 IST. HEAD 33586c21, code tree equals 01015033. Same scratch harness, sidecar and
artifacts as `surface-rc1-verifier-10.md` (scratchpad `refaudit4-surface/evidence/`).

## Tied entry

R15-AGENT-043 (fixed; batch-7 certified; fix 98311dfb). Repro: flat criteria [pe_ratio lt 20, roe gt
{min:15,max:15}, debt_to_equity lt 0.5] -> label "Wrote 2 screener criteria", ROE silently gone.
fix_shape: report rejected leaves in the label and the tool result so the model can retry.

## Shard claim

"write_screener_filters silently drops a malformed flat criterion whenever a group is also sent": input
`{criteria:[{roe gt "15"},{market_cap gt 1000}], group:{and:[pe_ratio lt 20]}}` -> "Wrote 1 screener
criterion", no drop note, roe gone. Code: `dropped: group ? groupDropped : [...flatDropped, ...groupDropped]`.

## Entry's own repro at HEAD: holds (fixed)

Scratch vitest case A (real host-actions + stores, fetch captured):

```
review: Screener: 2 criteria; dropped roe: value must be a number — review then Run
label : Wrote 2 of 3 screener criteria; dropped roe: value must be a number — running
ack dropped: ['roe: value must be a number']
run body criteria: [pe_ratio lt 20, debt_to_equity lt 0.5]
```

A malformed leaf inside the group is also reported (case H: "Wrote 1 of 2 screener criteria; dropped roe:
value must be a number"). Repo test `src/lib/host-actions.test.ts` (AGENT-043 pins) passes: 7 files / 200
tests green in the run listed in `surface-R15-UI-015.md`.

## Shard's command re-run at HEAD: the observation is real

Case B (the shard's input, real `{combinator:"and", criteria:[...]}` shape):

```
review: Screener: 1 criterion — review then Run
label : Wrote 1 screener criterion — running
ack dropped: []
store : criteria [market_cap gt 1000], group and[pe_ratio lt 20], advanced false, combinator and
run body: criteria [market_cap gt 1000], no group
```

## Why this is not AGENT-043's defect

1. The silence is deliberate and follows the contract: with a group present the flat list is superseded
   (`catalog.py:1529-1531` "which supersedes the flat list"; `sidecar/services/screener.py:373` "When
   ``group`` is given it supersedes the flat ``criteria``"; `host-actions.ts:922` "A surviving group is
   what applies (and is counted); else the flat list"; commit 98311dfb). The label counts the group, and
   the group's own malformed leaves ARE reported (case H).
2. The only harm in the shard's repro, the flat list (minus roe) running as a looser screen, exists
   because the store runs the flat list instead of a flat group: that is rc1-verifier:10's defect, not a
   reporting gap. Nested case E (`criteria:[{roe gt "15"}]` + a nested or-group): the group runs exactly as
   labelled ("Wrote 3 screener criteria (nested AND/OR)"; body group = the nested tree); the malformed flat
   leaf is superseded like any well-formed flat leaf, so nothing the user asked for runs looser than
   stated.
3. With rc1-verifier:10's one-line fix applied in scratch (`fixcheck.scratch.test.ts`), the shard's input
   runs body [pe_ratio lt 20], matching "Wrote 1 screener criterion". Adding flatDropped to the note as the
   shard implies would report "dropped roe" while the equally superseded, well-formed market_cap goes
   unmentioned: a misleading fix.

## Verdict: verifier_error

The shard tested a real defect but attributed it to the wrong entry: its repro exercises the store's
flat-group collapse (rc1-verifier:10, new_defect_confirmed in this audit), not AGENT-043's rejected-leaf
reporting, which holds at HEAD for flat lists and for group leaves and is silent only for a flat list the
contract supersedes. The shard's exact input is in rc1-verifier:10's acceptance test, so the harm is pinned
there. Severity of the observed harm: medium, and it belongs to rc1-verifier:10.

Certification-failure count: 0, n/a (no register entry reopened). AGENT-043 baseline stays 0 (batch-7
certified; no not_certified rows; no refutation-audit partial/regression).
