# rc1-battery-17 — regression battery shard 17 (rc1 round-5-recheck)

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd.
Own sidecar booted from candidate source on :52357, data dir
`rc1-round-5-recheck-data-battery-17` (copy of `rc1-round-5-recheck-seed-data`).
Sleep pid: 94047 (main sidecar sh -c wrapper pid: 94045). Log:
`logs/rc1-battery-17-sidecar.log`.

Sets covered: batch-2/W4-workspace-persistence (set-3.md, 7 ids),
batch-28/W6-sonnet (set-80.md, 7 ids), batch-11/W7-preferences (set-55.md, 1 id),
unplanned-2 (set-88.md, R15-LEAD-059).

## Method

For every id: read the register entry's own repro + how the originating batch verifier
(`stage-c/batch-2/VERDICTS.md`, `stage-c/batch-28/VERDICTS.md`, `stage-c/batch-11/VERDICTS.md`,
round-5 `fix-r2/VERIFY.md`) certified it, then re-ran that repro against the candidate:

- Where the register repro is a live sidecar endpoint, curled it against :52357
  (workspace save/load round-trip, portfolio positions, macro FRED 502, FOCUS announcements)
  or called the underlying Python function in-process via the candidate's `sidecar/.venv`
  (the `transform.code` evaluator for CODE-PLATFORM-017).
- Where the register repro is pure frontend logic with no sidecar endpoint (workspace
  rollback/autosave gating, panel-context-bus fan-out, layout-template/menu-mode mapping,
  screener group-vs-flat-criteria, stale-response ordering, chart-drawing keyboard scope,
  settings preference depth), grepped the candidate source for the id-labelled pinned vitest
  case(s), confirmed each is present at HEAD, unmodified, and read the assertion body to
  confirm it is a real check (not skipped/weakened) — verdict `ci_pinned` naming the test(s),
  per the role's instruction not to run vitest/pytest suites myself.

## Results

All 16 ids: **holds** (3: R15-CODE-FRONTEND-004, R15-LEAD-059, plus the R15-LIFECYCLE-009
supplementary live probe) or **ci_pinned** (13). No regressions, no chain failures, no gate8
findings, no new defects. Full detail in `battery/set-3.md`, `battery/set-80.md`,
`battery/set-55.md`, `battery/set-88.md`; raw per-id output in
`battery/raw/set-3/`, `battery/raw/set-80/`, `battery/raw/set-55/`, `battery/raw/set-88/`.

R15-LEAD-059 (the unplanned-2 fixed-entry re-proof): own repro
`GET /disclosures/announcements?symbol=FOCUS` with `X-Vysted-Region: IN` returns 44 rows,
all `exchange:NSE`, 0 rows carrying scrip 543312, `sources:["NSE"]`, note naming the other
BSE company (Focus Business Solution) — exactly the stated fixed behaviour. Holds.

findings/rc1-battery-17.json: `[]` (no regressions/new_defect/chain/gate8 findings this shard).

Sidecar stopped at end of shard (`kill 94047`).

COVERAGE: 16/16 ids raw; no raw: none.
