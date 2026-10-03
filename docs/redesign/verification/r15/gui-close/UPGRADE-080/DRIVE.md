# UPGRADE-080 — app half of the 0.8.0 -> 0.9.0 upgrade from real 0.8.0 data

- item: UPGRADE-080 (close-drive-UPGRADE-080, Opus 5.5)
- sha: 1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056 (r15-launch)
- app: scratchpad/gui-close/Applications/Vysted Terminal.app (0.9.0 release bundle from the draft release dmg)
- home: real HOME; data dir: VYSTED_DATA_DIR=scratchpad/gui-close-upgrade-run (fresh cp -Rp of the lead's snapshot scratchpad/gui-close/upgrade-080-data, itself a byte copy of ~/Library/Application Support/com.vysted.terminal.audit-backup-20260529, last written 22-27 May 2026)
- real-data mtime before: com.vysted.terminal 1790978102 (Oct 3 03:25:02 2026); audit-backup-20260529 1779906083 (May 27 23:51:23 2026)

## Inventory before launch
raw/before.txt: 1 named layout `phase9test` (keys name/layout/enabledModules/chartDrawings; no watchlist/holdings key; 9 layout panels), no `__autosave__`, no notes/, no workflows.db; custom_agents 0 rows; plugin_configs 0 rows; portfolio.db positions 84 rows (81 distinct symbols; schema has no portfolio column); data_cache 5; audit_log.db audit_orders 3 (legacy pre-D81 table).

## Presence / timeline
- 20:37:46Z pre-launch presence: idle 219 s (below 900) -> waited (polled idle).
- 20:49:14Z pre-launch presence: idle 906.6, sentinel 2026-10-03 23:25:36+00:00, frontmost Zed, no Vysted app -> launched 20:49:19Z, app pid 68876 (raw/launch-time.txt, raw/app-stdout.log).
- No SecurityAgent process appeared at launch (pgrep empty through boot) — the 01:48 IST 'Always Allow' held.
- Data dir proven: sidecar child pid 68893 args `--port 53675 --data-dir .../scratchpad/gui-close-upgrade-run --cache-dir .../scratchpad/gui-close-upgrade-run` (raw/sidecar-args.txt). /health 200 version 0.9.0 on :53675. sec-edgar-mcp did not bind within 45 s x 2 (/sec routes 501; known cold-bind carry-forward, BLOCKERS.md).
- bounds: Vysted Terminal window id 7325, [116, 43, 1280, 832] points.
- 20:51:35Z presence: idle 6.7 s (human input), frontmost Zed -> no guarded action; re-checking for up to 30 min.
- 20:51-21:06Z: idle re-polled every ~100 s (99.8 -> 908.5); no human input after 20:51.
- 21:06:37Z presence (pre-capture-01): idle 908.5, sentinel 2026-10-03 23:25:36+00:00, frontmost Zed, only my Vysted app running -> first guarded call, a single passive `rig.py capture 1fddb2b-01-cockpit-boot.png`.
- **STOP — exit 4.** RIG_ABORTS.log line: `2026-10-03T21:06:37.801344+00:00 ABORT capture: frontmost app is 'Zed', not Vysted`. The rig tried to bring the window forward (`real_activate`, `activateWithOptions_(NSApplicationActivateIgnoringOtherApps)`, scripts/rig/rig.py:104-108) and Zed was still frontmost after 0.6 s. Idle was 908.5 s, so this was not human input. macOS 26 (Darwin 25.3) ignores that activation option when a background process asks (cooperative activation). This is the same class as the two earlier `frontmost app is 'Finder'` aborts on 2026-10-03 04:31Z and 06:19Z. No capture file was written; nothing was registered in CAPTURES.jsonl. Per the presence rules exit 4 is a hard stop: app pid 68876 quit with SIGTERM at 21:07Z, and all its children are gone (pgrep empty).

## Checks
| check | result | evidence |
|---|---|---|
| Boots on the copied 0.8.0 data, no new keychain prompt, data dir proven | shown (process/HTTP) | raw/sidecar-args.txt, raw/app-stdout.log, /health 0.9.0 |
| Cockpit capture after CONNECTED | not_driven | rig exit 4 before the first capture |
| Portfolio: 84 positions, same symbols, quantities and cost bases (HTTP) | shown | raw/after-http.txt GET /portfolio/positions: 84 rows; raw/compare.txt: 0 differing rows across all 7 columns vs the lead's snapshot (incl. row 4's injection-string note, kept byte-exact) |
| Portfolio panel lists them (GUI + scroll) | not_driven | exit 4 |
| Layout `phase9test` listed (HTTP) | shown | GET /workspace -> ["phase9test"]; GET /workspace/phase9test keys and 9 panels match before.txt |
| Settings -> Advanced -> Layouts lists it and loading restores it (GUI) | not_driven | exit 4 |
| Notes | n/a | 0.8.0 profile has no notes/ |
| Settings -> AI Providers key-configured state (GUI) | not_driven | exit 4 |
| Custom agents / workflows read back (HTTP) | shown | GET /custom-agents -> [] (before: 0 rows); GET /workflow/saved -> {"workflows":[],"unreadable":[]} (before: no workflows.db) |
| Upgrade side effects | shown | raw/after-quit.txt: the app wrote a pre-upgrade backup `backups/unversioned-2026-10-04/` (all 0.8.0 files), app-meta.json, workflows.db, __autosave__; portfolio still 84 rows; phase9test byte-size unchanged (3932) |
| Real dir mtime unchanged after quit | shown | com.vysted.terminal 1790978102 before and after; audit-backup-20260529 1779906083 before and after; lead snapshot upgrade-080-data 1779906083 unchanged |

## Stops
- 21:06:37Z rig exit 4 (could not bring the window forward: frontmost Zed, `activateWithOptions_` ignored). Hard stop, app quit.

## Verdict
blocked_env. The data half reads back intact over the release app's own sidecar: 84/84 positions identical, the layout, and zero agents and zero workflows, as before. The app wrote a pre-upgrade backup, and the real dirs were not touched. The GUI half (cockpit, Portfolio panel with scroll, Settings Layouts load, AI Providers) was not driven. The rig cannot bring the Vysted window forward over another app on this macOS. That needs an activation path that works on macOS 26 (e.g. `open -a`/LaunchServices activation inside the rig), or the operator leaving Vysted frontmost.
