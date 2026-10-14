# batch-29/W4-sonnet (shard rc1-battery-17)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-048 | batch-29 certified this via a scratch vitest (deleted, never committed per `batch-29/VERDICTS.md`). At candidate sha it is now a PERMANENT pinned test: `host-actions.test.ts:1858 describe("arrange_layout routes Layout-menu mode ids instead of resetting (R15-LEAD-048)")`, incl. `"a recognised Layout-menu mode id ('fundamental') applies that mode, never resetLayout"` and an `it.each(["banana","constructor"])` unrecognised-pattern case. Live GUI exercise not possible (arrange_layout requires a mounted `dockviewApi`, out of scope this round). Live source read of `src/lib/host-actions.ts:1680-1710` confirms: `MENU_PAYLOAD_TO_MODE` pattern match -> `applyLayoutMode(api, mode)` (never `resetLayout`); a genuinely unrecognised pattern now `fail()`s instead of silently resetting. | Pinned test present, unmodified, matches the register repro exactly (fundamental/technical/macro/compare-desk route to the same layout the native menu produces; unknown patterns fail loudly, not silently reset). | ci_pinned |

Raw: `battery/raw/set-83/R15-LEAD-048.txt`.

COVERAGE: 1/1 ids raw; no raw: none.
