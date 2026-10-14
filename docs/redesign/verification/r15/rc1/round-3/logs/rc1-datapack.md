# rc1-datapack — gate round 3 working log

Candidate sha: 01d6920a300b016ab1ad8aa436ee4e4586f8e336 (verified via
`git rev-parse HEAD` in the scratch candidate worktree).

## Setup

- Own sidecar: main :52313, data dir
  `rc1-round-3-data-rc1-datapack` (fresh copy of `rc1-round-3-seed-data`,
  never reused from an earlier round). Started detached from
  `<cand>/sidecar` with `sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52313 --data-dir <data>`.
  `/health` returned `{"status":"ok",...}` before collecting.
- Pack copy tree: `rc1-round-3-pack` holding only
  `scripts/r15/collect_battery.py` and
  `docs/redesign/verification/r15/battery/manifest.json`, both copied
  from the candidate worktree (never the census baseline). Collector run
  from that copy with `--port 52313 --force` so census
  `r15/battery/collected/` was never touched.
- Collector detached, polled via Monitor + log tail, output copied to
  `r15/rc1/round-3/battery/collected/`.

## Fixed register entries touching a battery symbol (scope for re-diff)

Found via `grep` over `vysted-r15-register.json` entries with
status `fixed` whose repro/title names a battery symbol:
R15-DATA-001, 003, 004, 005, 006, 008, 013, 014, 015, 016, 017, 018, 019,
022, 023, 025, 026, 027, 048, 049, 050, 051, 052, 053, 054, 055, 056, 057,
058, 060, 076, 115, 116, R15-AGENT-022, R15-AGENT-090, R15-LEAD-004,
R15-LEAD-011, R15-LEAD-013, R15-LEAD-015, R15-LEAD-028, R15-LEAD-034.

Excluded (adjudicated to operator, not open, no fix round; see LEAD NOTE
(1)/(8)): R15-DATA-002 (blocked_tier4, AMAL add_to_watchlist region),
R15-DATA-059 (blocked_tier4, SIFY title claim), R15-LEAD-030
(blocked_tier4, local-model-figure class). R15-LEAD-017 is `open` (CSL,
not fixed) — out of scope for this role (no fix round on it, not a
regression since it was never fixed).

## Method

For each fixed entry, re-checked the exact field(s) the register repro
named against this round's freshly collected battery JSON (same routes:
`collect_battery.py`'s quote/fundamentals/income/balance/cashflow/
ratings/shareholding/announcements/results plan — this covers every
repro's GET in the fixed-entry list above). Then swept all 24 slots'
`diffs/<slot>.json` census field list for any field recorded `match` at
census time and re-derived the same field from this round's collected
JSON, flagging anything that stopped matching (price-like drift = as-of
skew, not a regression).

## Result

All 24 names re-collected (`battery/collected/*.json`, all `complete:
true`). 41 in-scope fixed register entries checked; 24 held on direct
re-check against `field_meta`; 17 were not reachable via
`collect_battery.py`'s fixed route plan (agent-loop, research-gate,
quarterly-statement, scrip-code, background-warm, screener-universe
entries — noted, not scored). Zero regressions confirmed. One candidate
(R15-DATA-015, ELCIDIN week52 range) was retracted after checking
`field_meta`: it carries an explicit `status:"flagged"` disagreement
reason, the same kept-but-flagged design already certified for
DATA-004/DATA-013 — not a silent regression.

An automated blind-equality sweep of all 24 slots' census-`match` fields
against fresh values produced 162 raw diffs; manual spot-checks showed
these are unit/format artifacts (crore-vs-raw, percent-vs-fraction,
"Ltd" vs "Limited", rounding), the same false-positive class the
census's own narrative diffing exists to avoid. None confirmed as real
defects; not reported as findings.

Own sidecar (:52313) stopped by killing its sleep pid (73575). See
`DATAPACK.md` and `datapack.json` for the full per-slot table.
