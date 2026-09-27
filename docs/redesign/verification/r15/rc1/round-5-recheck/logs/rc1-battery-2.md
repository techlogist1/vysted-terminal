# rc1-battery-2 — Regression Battery shard 2, gate round 5-recheck

Role: rc1-battery-2 (Sonnet). Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd` (confirmed
via `git -C .../rc1-round-5-recheck-cand rev-parse HEAD` before any work).

Sets: batch-7/W4-research-funnel (set-28, 11 ids), batch-10/W6-chart-notes-blueprint
(set-45, 4 ids), batch-16/W1-one-writer-set (set-64, 1 id). Total 16 ids.

## Setup

- Data dir: `cp -R rc1-round-5-recheck-seed-data -> rc1-round-5-recheck-data-battery-2`.
- Own sidecar booted on `:52342`, source boot from `rc1-round-5-recheck-cand/sidecar`,
  `VYSTED_OPENBB_MCP_PORT=52153`/`VYSTED_SEC_EDGAR_MCP_PORT=52154` pointing at the shared
  read-only stack, sleep pid 59265 (recorded in `logs/rc1-battery-2-sidecar.pid`). `/health`
  confirmed ok before use. Stopped cleanly at end of shard (`kill 59265`, `/health` now
  refused).

## Method

For each id: read the register entry's own `repro`/`evidence` fields directly from
`vysted-r15-register.json`, cross-checked against the original batch verifier's per-entry
evidence (`stage-c/batch-7,10,16/VERDICTS.md`), then re-ran that exact repro against the
candidate — an in-process python call against the candidate's own `sidecar/.venv` for
sidecar-side entries, a live curl against the shard's own sidecar for the one API-shaped
entry (LEAD-026), `git show HEAD:...` for the two pure-doc/token entries, and a grep-only
check (test name + mechanism, never executed) for the three frontend-only TS entries that
are `ci_pinned` (vitest is the heavy lane's job per the role rules).

A prior gate round (round-4) had verified this SAME battery-2 role's SAME id sets at an
earlier candidate (`1006c6da`) — its `battery/set-28.md`/`set-45.md`/`set-67.md` files were
read as a useful precedent/template (what repro shape and stub each entry needs) but never
copied as this round's evidence; every raw file and verdict in this round is a fresh run
against `949c3c9f`.

## Note on R15-LEAD-032

The first attempt at this repro accidentally reused a leftover `sec:ads-ratio:SIFY:miss`
cache row in the fresh data-dir copy (written by an earlier untimed sanity run of the same
script against the same data dir before the raw capture), which short-circuited the second
`lookup()` call before the timeout path ever ran, producing a false `0.00s` first-call
reading. Caught before finalizing: the stale row was deleted from `data_cache.db` and the
timed run redone, producing the correct `8.01s` / `0.00s` pair that matches the register's
and round-4's evidence. Recorded here as a working note, not a finding — no product defect,
a self-inflicted stale-cache artifact from re-running the same probe script twice against
one data dir.

## Result

All 16 ids: `holds` (10) or `ci_pinned` (3 frontend TS ids named to their exact pinned
test) — 16 raw files total (11+4+1), zero regressions, zero new defects. No findings filed.

COVERAGE: 16/16 ids raw; no raw: none.
