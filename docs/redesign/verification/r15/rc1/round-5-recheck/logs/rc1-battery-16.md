# rc1-battery-16 — shard 16 log

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd, own sidecar :52356, data dir
rc1-round-5-recheck-data-rc1-battery-16 (copy of rc1-round-5-recheck-seed-data), sleep pid 89284.

Sets: batch-8/W2-provider-readiness-host-actions (set-31.md, 8 ids), batch-11/W1-scripts-build
(set-49.md, 5 ids), batch-28/W2-sonnet (set-76.md, 2 ids), unplanned-1 (set-87.md, 1 id).

## Results

All 16 ids: holds (11), ci_pinned (5: R15-UI-019, R15-UI-049, R15-CODE-PLATFORM-028,
R15-AGENT-056, R15-AGENT-081 — frontend store/React logic that needs vitest or a GUI to
exercise directly; this role never runs vitest, so these are verified by source-read
confirming the certified fix shape is unchanged plus citing the pinned test file/describe
block). No regressions, no chain failures, no gate8-relevant findings. findings/rc1-battery-16.json
is [] (empty).

One incidental note: the R15-RELEASE-005 live probe (in-process `isStale()` call) touched
`sidecar/services/screener_universes/us_fundamentals_seed.json.gz`'s mtime in the read-only
candidate worktree to observe the staleness flip; its mtime was restored immediately via
`touch -t` to match the pre-probe value (confirmed by a follow-up `stat`), and no file content
was ever changed.

COVERAGE: 16/16 ids raw; no raw: none.
