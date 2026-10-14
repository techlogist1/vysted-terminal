# Set: lows-P2/lifecycle-upgrade (set-82.md) - rc1-battery-15 at ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-077 | temp data dir with 8 old backups/<build>, then data_cache._backup_data_dir('build-current') in-process | after: 5 dirs (build-current + 4 newest old), MAX_BACKUPS=5, oldest 4 pruned | holds |

COVERAGE: 1/1 ids raw; no raw: none
