# R15-LEAD-145 (gui-close-3) — on-screen 0.8.0 -> 0.9.0 upgrade with the LEAD-145 fix

- item: R15-LEAD-145 (close-drive-R15-LEAD-145, Opus 5.5)
- sha: f163d85856c427adeccd1a6919a70400cd3504f4 (fix commit 67531aef; fixround-wt HEAD verified equal)
- app: scratchpad/fixround-wt/src-tauri/target/debug/bundle/macos/Vysted Terminal.app (DEBUG build, 0.9.0, bundle id com.vysted.terminal). A debug build is used on purpose: a fresh release binary would raise a login-keychain prompt with nobody present, and the import (src/lib/workspace.ts, src/store/portfolios.ts) and notice (src/modules/portfolio/PortfolioPanel.tsx) code is frontend code identical in debug and release. Debug keychain calls go to `<data dir>/dev-keystore.json`, written as `{"secrets": {}, "migrated": true}` (0600) before launch.
- home: scratchpad/gui-close-home-R15-LEAD-145 (fresh, isolated); data dir: VYSTED_DATA_DIR=scratchpad/gui-close-3-upgrade-run, a fresh `cp -Rp` of the lead's pristine snapshot scratchpad/gui-close/upgrade-080-data (byte copy of the operator's 0.8.0-era audit-backup-20260529 profile).
- never opened by 0.9.0: `grep -l '"portfolios"' workspaces/*.vysted-workspace` -> no match (exit 1).
- launch 1: 2026-10-04T13:43:12Z, pid 39234 (raw/launch-1.txt). Sidecar pid 39262 `vysted-sidecar --port 65424 --data-dir .../scratchpad/gui-close-3-upgrade-run --cache-dir .../gui-close-3-upgrade-run` (raw/sidecar-args-1.txt).
- bounds: window id 7781, [116, 43, 1280, 832] points.
- real-data mtime before: ~/Library/Application Support/com.vysted.terminal 1790978102 (stat only); snapshot upgrade-080-data 1779906083 (raw/realdata-mtime-before.txt).

## Inventory before launch (raw/before.txt)
One named layout `phase9test` (keys chartDrawings/enabledModules/layout/name). custom_agents 0 rows, plugin_configs 0, workflows.db absent, portfolio.db positions 84 rows (no portfolio column -> all target the default portfolio). Flagged (3): id 2 AAPL 1e15 @ 1e-8 (qty > 1e12), id 3 AAPL -50 @ -10 (qty <= 0, cost < 0), id 4 AAPL 1e15 @ 1e-8 (qty > 1e12). Importable 81: id 1 AAPL 10 @ 150, T001..T080 with quantity n+1 and cost 10n (all 80 verified by SQL).

## Presence / timeline
- 13:43:07Z pre-launch: idle 3474.5, sentinel 15:40:56Z, frontmost loginwindow, no Vysted app.
- 13:43:53Z pre-capture-01: idle 3521.2, sentinel 15:40:56Z, frontmost **loginwindow**, only my app (pid 39234).
- 13:43:53Z passive capture `f163d85-01-first-screen.png` started detached (raw/rig-01.log). The rig printed `WAIT: screen locked, retrying` every 15 s from 0 s to 585 s, then `REFUSED: screen locked for 600s (limit 600s)`, `EXIT=3`. No image was written or registered (CAPTURES.jsonl has no gui-close-3 row). No input of any kind was posted; the rig never acted.
- Per the lane rule (exit 3 starting "screen locked" = the screen stayed locked for 10 min), the drive stopped here.

## Cross-check before quit (raw/after-http.txt; not on-screen evidence)
- /health 200, version 0.9.0, openbb-mcp available.
- GET /portfolio/positions: 84 rows; the 3 flagged rows (ids 2, 4 AAPL 1e15 @ 1e-8; id 3 AAPL -50 @ -10) are present, so the legacy ledger is intact.
- workspaces/ after ~10 min up: only phase9test, no `__autosave__` and no "portfolios" key. The frontend had not restored or imported (it was presumably held at the fresh-HOME terms screen, which nobody could see or accept). The run copy is therefore still un-imported, but a re-run should take a fresh copy anyway.

## Quit and real-data check
- 13:54Z SIGTERM to pid 39234 only; it and its children exited; no process from the debug bundle or the run copy remains; lsappinfo lists 0 "Vysted Terminal" apps.
- Real ~/Library/Application Support/com.vysted.terminal mtime 1790978102 before and after (stat only). Snapshot upgrade-080-data 1779906083 before and after (raw/realdata-mtime-after.txt).
- No SecurityAgent process seen, no chat turn, no research, Ollama never reached (no lock taken).

## Checks
| Check | Result | Capture |
|---|---|---|
| (1) Portfolio lists the 81 importable rows | not_driven (screen locked) | — |
| (2) Notice names the 3 flagged rows with reasons | not_driven | — |
| (3) Count/summary caveat before and after dismiss | not_driven | — |
| (4) Totals caveat text | not_driven | — |
| (5) Relaunch: no re-import, notice stays dismissed, caveat persists | not_driven | — |
| (6) Settings -> Advanced -> Layouts lists phase9test | not_driven | — |

## Findings
None (nothing was shown on screen).

## Stops
screen_locked — the rig waited 600 s on a locked screen (frontmost loginwindow) at the first, passive capture and refused with exit 3.

## Verdict
blocked_env — the screen was locked for the whole 10-minute rig wait, so no capture or input was possible. Re-run when the screen is unlocked inside an armed sentinel window (fresh copy of upgrade-080-data, same debug app at f163d858).
