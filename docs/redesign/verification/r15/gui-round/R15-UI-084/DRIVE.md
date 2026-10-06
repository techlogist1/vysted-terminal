# R15-UI-084 — GUI drive at ace7dd7 (rc2 candidate, session 3)

- entry: R15-UI-084 (medium) — agent dock hard-capped at 1200 px, no maximize mode (FR-001 "full cockpit")
- sha: ace7dd768c3b809b0e72b20b20cfc94eea2368bd (gui worktree scratchpad/gui-ace7dd7, HEAD verified)
- app: scratchpad/gui-ace7dd7/src-tauri/target/debug/bundle/macos/Vysted Terminal.app (packaged, tauri:// origin)
- isolated home: scratchpad/gui-round-home-R15-UI-084 (fresh copy of gui-round-seed; dev-keystore.json = {"secrets": {}, "migrated": true})
- real ~/Library/Application Support/com.vysted.terminal mtime before: 1790978102
- display: 3024x1964 Retina (1512x982 points); :5173 free; no Vysted app running at start (05:27Z, lsappinfo empty).
- CARRY_FORWARD_rc2.md: "carries" (agent-dock.ts / AgentDock.tsx have no diff in the lows merge); driven at ace7dd7 anyway as assigned.

## Code read at ace7dd7 (before driving)
- src/store/agent-dock.ts: MIN 280, MAX 1200, DEFAULT 310; `maximized` state; setWidth clamps; toggleMaximized flips maximized and leaves `width` untouched (the restore width).
- src/components/AgentDock.tsx: aside animates to width "100%" when maximized (maxWidth cap dropped), else `width` capped at 1200; the separator ("Resize agent column", w-3 = 12 px) has onDoubleClick=toggleMaximized, title "Drag to resize · double-click to maximize" / "Double-click to restore the cockpit"; maximized, the cockpit div is `invisible absolute`, aria-hidden + inert, kept mounted.
- src/lib/workspace.ts:105-110,424-440: agentDock {collapsed,width,maximized} rides the blob; older blobs restore un-maximized.
- Seed: R15-UI-009's raw/ace7dd7-seed-post.json carries agentDock {collapsed:false, width:458.47} (dock open), 7-symbol watchlist, 2 holdings, a note, a brief.

## Presence / steps
- 2026-10-03T05:27:34Z idle=205.0 (pre-launch-1) -> waited (detached idle watcher) until 05:39:33Z idle=924.1 sentinel=2026-10-03 21:43:50+00:00 front=Finder vysted=[] (pre-launch-1b). Real-data mtime before: 1790978102.
- Boot 1 (seeding, no GUI input): pid 13191 at 05:39:39Z; children 13203 vysted-sidecar --port 50608 --data-dir/--cache-dir <isolated home>/Library/Application Support/com.vysted.terminal (ps args), 13201 openbb-mcp 50609; logs/vysted.log under the isolated home. /health ok 0.9.0. GET /workspace/__autosave__ -> raw/ace7dd7-seed-before.json; POST raw/ace7dd7-seed-post.json (R15-UI-009's ace7dd7 seed) -> {"status":"saved"}; read back: 7 symbols (SPY QQQ BTC/USDT ETH/USDT NVDA AAPL MSFT), holdings AAPL 10 @ 180 + NVDA 5 @ 120, the seed note, agentDock {collapsed:false,width:458.47}. Killed 13191 then 13201/13203 by pid; none left; on-disk blob = 7 symbols. raw/app-stdout-boot1.log, raw/vysted-boot1.log.
- 2026-10-03T05:41:55Z idle=1066.1 sentinel=2026-10-03 21:43:50+00:00 front=Finder vysted=[] (pre-launch-2)
- Launch 2 (drive): pid 13998 at 05:41:56Z; children 14014 vysted-sidecar --port 51890 --data-dir/--cache-dir <isolated home>/Library/Application Support/com.vysted.terminal, 14011 openbb-mcp 51891, 14012 sec-edgar-mcp 51892; 14007 = system WebKit WebContent XPC (ppid 1). /health :51890 ok. Bounds [116,43,1280,832] at launch. Brought pid 13998 front via System Events (no input event).
- 2026-10-03T05:43:06Z idle=1136.6 front=Vysted Terminal vysted=[13998 14007] (pre-capture-01)
- ace7dd7-01-boot-passive.png (opened): dark theme, "Welcome to Vysted" terms modal over the seeded layout: agent dock (Chat 1, empty state + suggestions + composer) | Portfolio/Chart ^NSEI | Brief SETFNIF50 populated. Registry: byte-identical to R15-CODE-AGENT-001/ace7dd7-01-packaged-seeded-layout.png (sha 282de970…), so the rig returned that existing row (sha dedup). Used for coordinates: dock right edge ~459 pt, handle centre ~465 pt.
- 2026-10-03T05:43:31Z idle=1162.3 (pre-resize). `rig.py resize 2560 1440` EXIT=0; bounds after = [116,43,1396,862] -> the largest size the 1512x982-pt display allows from that origin: **1396x862 points** (captures 2792x1724). The resize did not reset the idle clock (idle 1166.3 right after).

## Batch A — raw/ace7dd7-batch-A.json (terms, onboarding skip, dock open capture, double-click handle, capture, double-click handle, capture)
- 2026-10-03T05:43:47Z idle=1177.5 sentinel=2026-10-03 21:43:50+00:00 front=Vysted Terminal vysted=[13998 14007] (pre-batch-A)
- Steps: click (768,598) terms; wait 4; click (502,728) onboarding skip; wait 5; capture 02; double-click (464,500) = handle centre (dock 458.47 + 6); wait 2; capture 03; double-click (1390,500) = handle centre when maximized (window 1396 - 6); wait 2; capture 04. EXIT=0, no abort (raw/ace7dd7-batch-A.log).
- ace7dd7-02-dock-open-1396w.png (opened): populated dark cockpit at 1396x862: agent dock (Chat 1, "Ask anything about what you're viewing", 4 suggestions, composer "Normal · GPT 5.6 Luna · no key"), Portfolio/Chart ^NSEI with MA 20/50/200, MACD, RSI, Volume, a Trend drawing, Brief SETFNIF50 (₹252.41, P/E 20.35, 52W 238-287, volume 870K). Header has the expand (↗) icon next to "Agent". Measured dock width: border-r at pixel 915-917 -> **458 pt** (= stored 458.47).
- ace7dd7-03-dock-maximized.png (opened): the header icon flipped to the collapse (↙) icon, so the store's `maximized` went true; the dock DID widen: its border at 916 px is gone, its composer box now runs to pixel 941 (= 470.5 pt = width 458.47 + 12 px handle, the cockpit's left edge) and continues under the cockpit, its "Normal" chip is drawn over the Brief panel's text at the right, and the dock's centred empty state/suggestions are no longer visible (re-centred under the Chart panel). BUT the cockpit is still painted on top: Portfolio/Chart (all panes, the Trend drawing) and Brief (metric cards, heading, Snapshot) are on screen at exactly their batch-02 positions. The panel host is NOT hidden; the user sees the cockpit, not a full-cockpit agent.
- ace7dd7-04-dock-restored.png (opened): back to the 02 layout: dock border at 915-917 px -> **458 pt** (the prior width returns), header icon back to ↗, empty state + suggestions back. The second double-click at x=1390 toggled maximize, so the handle sat at the window's right edge while maximized (the dock's flex box did go full width).
- Blob after A (raw/ace7dd7-blob-after-A.json): agentDock {collapsed:false, width:458.46875, maximized:false} — width preserved through the round trip, maximized persisted as a field.
- Built CSS check (out/assets/index-DfAhdGFk.css in the gui worktree): `.invisible{visibility:hidden}` and `.absolute{position:absolute}` are present, and dockview.css sets `visibility` only on tab-action buttons. Not root-caused further (driver role).

## Batch B — raw/ace7dd7-batch-B.json (rule out a transient; second entry point via the header button)
- 2026-10-03T05:59:32Z idle=933.5 sentinel=2026-10-03 21:43:50+00:00 front=Vysted Terminal vysted=[13998 14007] (pre-batch-B); bounds unchanged [116,43,1396,862].
- Steps: double-click (464,500) handle; wait 1; capture 05; wait 6; capture 06; double-click (1390,500); wait 3; capture 07; click (156,56) header maximize button (the ↗ next to "Agent"); wait 5; capture 08; click (156,56); wait 3; capture 09. EXIT=0, no abort (raw/ace7dd7-batch-B.log).
- ace7dd7-05-handle-max-1s.png (opened): same as 03 — header icon ↙, dock border gone, composer runs to 941 px and under the cockpit, "Normal" chip ghosted over the Brief text; Portfolio/Chart and Brief panels still fully painted at their un-maximized positions.
- ace7dd7-06-handle-max-7s.png (opened): 7 s after the double-click, pixel-identical to batch A's 03 (sha b47b4226…; the rig's sha dedup returned 03's row, so 06 has no row of its own — it is the same image). The state is settled and deterministic, not a mid-animation frame.
- ace7dd7-07-handle-restored.png (opened): back to the normal layout; dock border at 915-917 px = 458 pt; empty state, suggestions, full composer back.
- ace7dd7-08-header-max.png (opened): the header button path gives the identical result: icon ↙, dock widened under the cockpit, cockpit panels still visible on top.
- ace7dd7-09-header-restored.png (opened): normal layout, dock 458 pt, icon ↗.
- Blob after B (raw/ace7dd7-blob-after-B.json): agentDock {collapsed:false, width:458.46875, maximized:false}.

## Measured widths (window 1396x862 pt)
- Open: 458 pt (border pixel 915-917 / 2; stored 458.47).
- Maximized: the dock's flex box goes to the full window (its composer runs to 941 px and continues under the cockpit; the restore double-click landed on the handle at x=1390 = window width - 6), but the visible cockpit still covers x >= 470.5 pt, so the agent visibly occupies the same 458 pt plus the 12 pt handle gutter.
- Restored: 458 pt (prior width returns, both paths).

## Teardown
- kill 13998, then 14011/14012/14014 by pid; ps shows none; lsappinfo has no Vysted entry. No vite started. No Ollama call made, so no local-model lock taken.
- raw/vysted.log, raw/app-stdout.log, raw/app-stdout-boot1.log, raw/vysted-boot1.log: 0 keychain/SecurityAgent lines; no keychain or SecurityAgent dialog in any capture.
- Real ~/Library/Application Support/com.vysted.terminal mtime: before 1790978102, after 1790978102 (unchanged), 06:00:36Z.

## Stops
- None. No rig refusal, no abort, no foreign window, no human input. Waits for idle >= 900: 05:27-05:39Z and 05:44-05:59Z.
- Harness note: the Bash tool blocks a bare `sleep 100`; idle waits ran as a detached until-loop (run_in_background) polled with separate <=110 s calls.
- The display is 1512x982 pt, so "resize 2560 1440" got 1396x862; the 2560-wide check was driven at the largest size available (the defect does not depend on width).

## Checks
- Window resized to the largest size the display allows: SHOWN (1396x862 pt, bounds).
- Dock open, width recorded: SHOWN (02, 458 pt).
- Double-click handle -> dock spans the whole cockpit and the panel host is hidden: NOT SHOWN, the defect is on screen (03/05/06, and 08 via the header button): the maximize state flips (icon ↙, dock flex box widens to the window, handle moves to the right edge) but the dockview cockpit stays painted over it, so the user still sees Portfolio/Chart/Brief and the agent's content is hidden under them (only a stray "Normal" chip bleeds through the Brief).
- Double-click again -> prior width returns: SHOWN (04/07, and 09 via the header; 458 pt; blob width 458.47, maximized false).

## Verdict: REGRESSED — at ace7dd7 the agent dock cannot visibly take the full cockpit: maximizing (handle double-click or header button) widens the dock's box but the panel host is not hidden; it stays drawn on top at its old position (deterministic, identical at 1 s, 2 s and 7 s). Restore returns the prior 458 pt width. The store test passing does not cover what the WKWebView paints.
