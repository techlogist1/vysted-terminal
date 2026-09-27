# batch-29/W4-sonnet (rc1-battery-13, shard 13)

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-048 | `node_modules/.bin/vitest run src/lib/host-actions.test.ts -t "R15-LEAD-048"` (single targeted test file, not the full suite) against the real `applyIntent`/`describeIntent`/`applyHostAction` | 5/5 passed: "a recognised Layout-menu mode id (e.g. 'fundamental') applies that mode, never resetLayout"; "an unrecognised pattern (banana) fails, names it, and does not reset"; "an unrecognised pattern (constructor) fails, names it, and does not reset"; "'default' still resets"; "class case: 'compare-desk' routes to the mode, 'compare' still takes the template path". Code trace confirms: `host-actions.ts` `arrange_layout` case now checks `MENU_PAYLOAD_TO_MODE` (comment cites R15-LEAD-048 by id) and calls `applyLayoutMode` before ever reaching `ws.resetLayout()` | holds |

COVERAGE: 1/1 ids raw; no raw: none.
