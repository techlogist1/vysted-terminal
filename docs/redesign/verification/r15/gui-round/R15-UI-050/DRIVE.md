# R15-UI-050 GUI drive at ace7dd7

- entry: R15-UI-050 (Notes slash-menu two-line rows clip/overlap in a fixed 32px row)
- sha: ace7dd768c3b809b0e72b20b20cfc94eea2368bd (rc2 candidate); CARRY_FORWARD_rc2.md: carries (slash-menu markup unchanged since d3509715)
- app: scratchpad/gui-ace7dd7/src-tauri/target/debug/bundle/macos/Vysted Terminal.app (Contents/MacOS/vysted-terminal)
- isolated home: scratchpad/gui-round-home-R15-UI-050 (fresh copy of gui-round-seed; dev-keystore.json = {"secrets": {}, "migrated": true})
- real data dir mtime before (stat -f %m): 1790978102
- code read at ace7dd7: src/modules/notes/NotesPanel.tsx slash popup rows `flex min-h-8 w-full flex-col ... px-3 py-1`, two `text-caption` spans (title, description); active row `bg-charcoal-800`. Original defect: fixed `h-8`.
- seed body: raw/ace7dd7-seed-post.json (copy of R15-UI-025's ace7dd7 seed: 7 watchlist symbols, AAPL/NVDA holdings with cost basis, a general note, Notes panel active).

## Log
- Boot 1 (seeding): pid 91077 at 2026-10-03T04:27:27Z (presence 04:27:21Z idle=910.0 sentinel 2026-10-03 21:43:50+00:00, Finder front, no Vysted app). Children 91089 vysted-sidecar --port 60923 --data-dir <isolated home>/Library/Application Support/com.vysted.terminal (--cache-dir same), 91087 openbb-mcp 60924, 91088 sec-edgar-mcp 60925; logs/vysted.log under the isolated home. GET /workspace/__autosave__ on :60923 -> raw/ace7dd7-seed-before.json; POST /workspace raw/ace7dd7-seed-post.json -> {"status":"saved"}. Killed 91077 then 91087/91088/91089 by pid; none left. On-disk blob carries 7 watchlist symbols (SPY QQQ BTC/USDT ETH/USDT NVDA AAPL MSFT), the general note, Notes active in leaf 1. raw/app-stdout-boot1.log, raw/vysted-boot1.log (0 keychain/SecurityAgent lines). Real mtime after boot 1: 1790978102 (unchanged).
- Boot 2 (drive): pid 91879 at 2026-10-03T04:30:00Z (presence pre-launch-2 04:30:00Z idle=1068.9). Children: vysted-sidecar --port 62242 --data-dir <isolated home>/... (ps args), openbb-mcp 62243, sec-edgar-mcp 62244; 91888 = system WebKit WebContent XPC (ppid 1) lsappinfo lists with it. /health on :62242 -> ok, version 0.9.0. Bounds [116,43,1280,832] -> launched size 1280x832 points (captures 2560x1664).
- First passive capture refused by the foreground gate (RIG_ABORTS.log: `2026-10-03T04:31:23.165199+00:00 ABORT capture: frontmost app is 'Finder', not Vysted`; app launched unactivated, no capture file written, no human input involved). Brought MY pid 91879 front via System Events `set frontmost of (first process whose unix id is 91879)` (R15-UI-009/022/025 precedent, no input event).
- presence 04:31:38Z idle=1166.8 front=Vysted Terminal vysted=[91879 91888] (pre-capture-01b). ace7dd7-01-boot-passive.png (opened): dark theme; "Welcome to Vysted" terms modal over the seeded layout: Portfolio | Chart | Notes tabs (Notes active), General scope, toolbar H1 H2 H3 B I code lists quote, seed note "R15 GUI round seed note: watch SPY breadth and ..."; Brief SETFNIF50 on the right; CONNECTED pill.

## Batch A — raw/ace7dd7-batch-A.json (terms, then slash menu)

- presence 2026-10-03T04:32:03Z idle=1191.9 sentinel=2026-10-03 21:43:50+00:00 front=Vysted Terminal vysted=[91879 91888] (pre-batch-A)
- Steps: terms button (768,598) -> capture 02; click editor (192,448); cmd+down; return; type "/"; capture 03; down; down; capture 04. All 16 steps exit 0 (raw/ace7dd7-batch-A.log), no abort.
- ace7dd7-03-slash-menu-open.png and ace7dd7-04-slash-menu-down2-active.png (both opened): terms gone, but a second onboarding modal ("WELCOME / An agent-native finance terminal", Connect a model / Run it locally cards, "Skip — I'll explore first") covers the app; it swallowed the editor steps. No slash menu on screen; note on disk unchanged (seed line). Not evidence for the check; 02 intermediate not opened. Batch B dismisses onboarding first.

## Batch B — raw/ace7dd7-batch-B.json (onboarding skip, then slash menu)

- presence 2026-10-03T04:47:29Z idle=920.1 (pre-capture-05). ace7dd7-05-pre-batch-B-passive.png (opened): onboarding modal still up, unchanged.
- presence 2026-10-03T04:47:44Z idle=934.9 sentinel=2026-10-03 21:43:50+00:00 front=Vysted Terminal vysted=[91879 91888] (pre-batch-B)
- Steps: Skip (502.4,727.7) -> capture 06; click editor empty area (192,448); cmd+down; return; type "/"; capture 07; down; down; capture 08. All 16 steps exit 0 (raw/ace7dd7-batch-B.log), no abort.
- ace7dd7-07-slash-menu-open.png and ace7dd7-08-slash-menu-down2-active.png (both opened): onboarding gone; populated cockpit (Notes: General, full toolbar incl. link + [ ] wikilink, note "R15 GUI round seed note: watch SPY breadth and NVDA earnings."; Brief SETFNIF50 ₹252.41, P/E 20.35, 52W 238-287, volume 870K). No new line and no slash menu: the click below the one-line note landed outside the ProseMirror content element (it is only as tall as its content), so the editor never got focus. Not evidence for the check; 06 intermediate not opened. Batch C clicks at the end of the note text instead.

## Batch C — raw/ace7dd7-batch-C.json (slash menu at the start of an empty line)

- presence 2026-10-03T05:03:12Z idle=922.3 sentinel=2026-10-03 21:43:50+00:00 front=Vysted Terminal vysted=[91879 91888] (pre-batch-C)
- Steps: click just right of "earnings." on the note line (520,306); cmd+down; return; type "/"; wait 1.2 s; capture 09; down; down; wait 1 s; capture 10. All 13 steps exit 0 (raw/ace7dd7-batch-C.log), no abort.
- ace7dd7-09-slash-menu-open.png (opened, full window, crop-free): caret on a new empty line under the note, "/" typed, the slash menu open directly below it, populated cockpit (Notes + Brief SETFNIF50 ₹252.41) behind. Rows, each title over a grey description: Heading 1 / Large section heading (active, first row highlighted), Heading 2 / Medium section heading, Heading 3 / Small section heading, Bullet List / Unordered list, Numbered List / Ordered list, Task List / Checklist with checkboxes (description wraps to two lines and the row grows to three lines), Blockquote (title at the menu's lower edge; the menu is the 320px-max scroll container, scrollbar visible at right, so the rest of the list scrolls). Every description sits fully inside its own row with clear space before the next title; no text overlaps the next item.
- ace7dd7-10-slash-menu-down2-active.png (opened, full window, crop-free): after down x2 the active highlight moved from Heading 1 to Heading 3 (third row). The active background covers both "Heading 3" and "Small section heading" and ends above "Bullet List"; it does not cut the next row's text. Task List's three-line row still shows its whole description without clipping or overlap.
- Read-back vs the defect: the original repro (fixed h-8 row holding two 13px lines, text overrunning, the active background cutting the next item) is not on screen; rows size to content (min-h-8 + py-1 at ace7dd7 NotesPanel.tsx slash popup).

## Teardown

- Quit: kill 91879, then children 91889/91890/91891 by pid; ps shows none of them; no Vysted process or lsappinfo entry left. No vite started.
- raw/vysted.log, raw/app-stdout.log: 0 keychain/SecurityAgent lines; no keychain or SecurityAgent dialog appeared in any capture.
- Real ~/Library/Application Support/com.vysted.terminal mtime: before 1790978102, after 1790978102 (unchanged).

## Stops

- 04:31:23Z rig foreground-gate refusal on the first passive capture (app launched unactivated; no capture written; not a human input). Resolved by bringing my pid front via System Events.
- Batches A and B produced no slash menu (onboarding modal swallowed A's editor steps; B's click missed the content element). Neither was an abort or a presence event.

## Verdict

holds — the Notes slash menu opens at the start of an empty line, and after down x2 the active row (Heading 3) is highlighted; no two-line (or three-line) row clips its description or overlaps the next item, and the active background does not cut the next row (ace7dd7-09, ace7dd7-10).
