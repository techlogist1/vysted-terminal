# rc1-battery-11 — regression battery shard 11

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98` (worktree
`/private/tmp/claude-501/.../scratchpad/rc1-round-5-cand`, HEAD verified before starting).
Own sidecar booted from candidate source on `127.0.0.1:52351`, data dir
`rc1-round-5-data-rc1-battery-11` (fresh copy of the seed profile). No vitest/pytest suites
run — only targeted `pytest -k` for the two backend-math entries, grep for the frontend-only
`ci_pinned` entries, live curl and in-process python for everything else.

## Sets worked

1. `batch-2/W5-surfaces-and-math` (set-4.md) — 8 entries, 2 holds (live), 6 ci_pinned.
2. `batch-2/W1-fundamentals-seam` (set-0.md) — 6 entries, 6 holds.
3. `batch-28/W4-sonnet` (set-77.md) — 3 entries, re-run against batch-28's own fresh-case
   repro (not the pre-batch-28 register repro), 3 holds.

## Notable investigation

R15-DATA-055's fresh case (`SAIL`) is a resolver-ambiguous bare ticker: under the default/IN
region it resolves to Steel Authority of India (first_trade_date 1996-01-01, listing_date
1995-07-06); under `X-Vysted-Region: US` it resolves to SailPoint, Inc. (first_trade_date
2025-02-13, listing_date null) — the company batch-28's certification actually used. First
probe (no region header) looked like a regression; confirmed via `GET /resolve?q=SAIL`
(lists both candidates) that it was my own header omission, not a product defect. Re-ran with
the correct header and it matches batch-28's certification exactly. No finding filed.

## Result

16/16 assigned ids re-run live/in-process/grep this round, all holds (with 6 of the 8
set-4 entries being frontend-only and staying `ci_pinned` against their committed vitest
test per the "never run vitest suites" rule for this role). Zero regressions, zero new
defects. Findings file is `[]`.

Sidecar stopped at end of shard (sleep pid recorded, killed only that pid).

COVERAGE: 16/16 ids raw; no raw: none.
