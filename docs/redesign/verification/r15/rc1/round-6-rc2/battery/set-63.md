# Battery shard 1 (lows-P1/host-actions-proposed-changes) at ace7dd76 [set-63]

 | id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-FRONTEND-034 | git grep pinned tests at candidate (host-actions.test.ts:1126, proposed-changes.test.ts:192/205) | ack status taken from apply result; 'a reworded Kept label still acks kept_previous' exists. Lead ruling (2) applies to src/store/proposed-changes.ts:146; not a finding | ci_pinned |
| R15-CODE-FRONTEND-035 | entry's repro is a grep: git grep for the dead seams | addPosition/updatePosition/deletePosition: 0 hits (seams removed); write_note uses notes.appendSymbolNote (host-actions.ts:1854); pin host-actions.test.ts:1357 | holds |
| R15-RESEARCH-041 | git grep pinned test at candidate | host-actions.test.ts:589 'briefFromInput with only vysted:// + nsearchives rows -> webAvailable false' exists; source comments at host-actions.ts:191-295 | ci_pinned |

COVERAGE: 3/3 ids raw; no raw: none
