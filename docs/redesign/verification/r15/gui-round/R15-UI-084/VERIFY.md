# R15-UI-084 — GUI verify at ace7dd7 (fresh verifier, Opus)

- sha: ace7dd768c3b809b0e72b20b20cfc94eea2368bd
- claim (title + fix_shape): the agent dock can take the full cockpit — a maximized state (command + handle double-click) renders the dock at 100% width and HIDES PanelHost; un-maximize restores the prior width.
- GUI check (note): open dock, maximize, confirm it spans the cockpit, un-maximize, confirm prior width returns.
- inputs: register entry, DRIVE.md, captures + raw/ under this folder, CAPTURES.jsonl, presence.log, code at ace7dd7 (AgentDock.tsx: `full && "invisible absolute inset-y-0 right-0"` on the cockpit div, aside animates to width "100%").

## Registration / presence
- 02 (7036bbfc…, 05:43:56Z), 03 (b47b4226…, 05:43:59Z), 04 (4946fe70…, 05:44:01Z): registered, rig.py capture, owner Vysted Terminal; presence line 05:43:47Z idle=1177.5 before them.
- 05 (a5385e0c…, 05:59:34Z), 07 (e82e5a0f…), 08 (6243ebcc…), 09 (db96651f…): registered, rig.py capture, owner Vysted Terminal; presence line 05:59:32Z idle=933.5 before them.
- 01: sha 282de970… is registered only under R15-CODE-AGENT-001's path (taken 2026-10-02T23:55Z, before this entry's presence lines) — not this drive's capture; ignored (coordinates only in DRIVE).
- 06: byte-identical to 03 (sha b47b4226…); its only row is 03's path/time — ignored as a separate capture; adds nothing beyond 03.

## Per part
| Part | Evidence | What it shows | Ruling |
|---|---|---|---|
| Dock open, width recorded | 02 | Populated dark cockpit; dock (Chat 1, empty state, 4 suggestions, composer) ~458 pt wide; header expand icon; Portfolio/Chart ^NSEI + Brief SETFNIF50 to the right. | holds |
| Maximize (handle double-click) spans cockpit, panel host hidden | 03, 05 | Header icon flips to collapse (state maximized); dock's empty state/suggestions disappear and its composer box extends under the Chart panel; a ghost "Normal" chip bleeds over the Brief text (~x 1600, y 1190 display). The Chart (all panes, Trend drawing) and Brief panels remain fully painted at their unmaximized positions. The cockpit is NOT hidden; the agent does not visibly take the cockpit. | DEFECT SHOWN |
| Maximize via header button | 08 | Identical to 03/05: cockpit panels still on top of the widened dock. | DEFECT SHOWN |
| Un-maximize restores prior width | 04, 07, 09; raw/ace7dd7-blob-after-A.json, -B.json | Layout returns to 02; dock ~458 pt, icon back to expand, empty state back. Blob agentDock {collapsed:false, width:458.46875, maximized:false}. | holds |
| 2560-wide window | DRIVE bounds | Display is 1512x982 pt; drove at 1396x862 pt. Defect is width-independent (cockpit painted on top). | n/a for the ruling |

## Ruling: NOT CERTIFIED
The fix_shape's core — the maximized dock renders at full width with PanelHost hidden — is contradicted on screen at ace7dd7: in 03/05 (handle) and 08 (header button) the dock's box widens but the dockview cockpit stays visibly painted over it, so the user sees Chart/Brief, not a full-cockpit agent. Restore of the prior width holds (04/07/09 + blob). The store test passing does not cover what WKWebView paints.
