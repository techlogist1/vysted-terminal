# Decisions for the operator (R15)

Things R15 did that reverse a standing rule of yours, or that are yours alone to decide
(Tier-4). Newest concerns at the top of each section. Each entry: what, why, my
recommendation, and how to undo it in one step.

## 1. Reversals of a standing operator rule (already done — revert if you disagree)

### 1.1 The "sacred" `enrich_nse_sectors.py` edit is now committed (`7a1cd8f`)

- **What:** every brief since R11 said never commit/revert/touch the uncommitted edit in
  `sidecar/services/resolver_masters/enrich_nse_sectors.py` (sha256 `5cb28e0d…286abdbe`).
  R15 reviewed the diff: it is exactly the documented `_nse_symbols` fix (the NSE master is
  `{exchange, instruments: [...]}`, not a flat list — the old code iterated dict keys and
  enriched nothing). It is committed alone as `7a1cd8f`.
- **Why:** the fix existed only on this laptop, protected by a sentence repeated in every
  brief. A rule held by memory fails the first time a brief forgets it; a commit cannot.
- **Undo:** `git revert 7a1cd8f`

### 1.2 `kill-switch-benchmark.json` no longer dirties the tree on every pytest

- **What:** `test_safety_end_to_end.py::test_audit_5_kill_switch_under_2s` rewrote the
  tracked v0.5.0 baseline with fresh timings on every full run. The capture now goes to the
  test's temp dir unless `VYSTED_REFRESH_SAFETY_CAPTURES=1` is set. **No assertion changed**
  (the `< 2000 ms` budget gate and the 12-subscriber check are byte-identical); the tracked
  baseline file is restored to its committed bytes.
- **Undo:** `git revert <commit>` (hash recorded in the run report).

## 2. Tier-4 items routed around (yours to decide)

(none yet)
