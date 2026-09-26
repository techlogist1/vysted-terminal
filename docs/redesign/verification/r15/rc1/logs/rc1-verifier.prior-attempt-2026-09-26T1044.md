# rc1-verifier working log (gate round 2)

- Candidate 81fbfe910d472ecd154fa62e42d86bce213a697e (worktree rc1-4c6dfe8-fix-int, clean, FF of 4c6dfe8c). 004 head 3ec2d531 has moved past 4c6dfe8 with docs commits; candidate is not an ancestor of 004.
- Round-1 log/sheet (candidate 1d6511c8) superseded; old data dir moved to rc1-data-rc1-verifier.round1-old.
- Own sidecar: source run from the candidate worktree, port 52312, data dir scratchpad/rc1-data-rc1-verifier (fresh cp -R of rc1-seed-data at 10:06 IST). Sleep pid 13475 (python 13477). Log scratchpad/rc1-verifier-r2/sidecar.log.
- 10:36 restart: reusing own sidecar (sleep pid 13475, :52312, healthy) and gate8 raw lists in verifier/r2 (openapi, rg sweeps, tool lists, in-process order dispatch).
- Register at candidate: 652 entries, open = 205 low only (0 open c/h/m). Four-area closed entries lacking recorded concurrence: CODE-PLATFORM-001, UI-042, UI-043 (all removed_with_feature) -> own concurrence due.
- Battery on disk: 79 fixed ids have no raw file (by name or content) under battery/raw; all 79 are in a stage-c certified list.
