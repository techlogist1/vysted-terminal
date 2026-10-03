# GUI drive — R15-LIFECYCLE-001 (boot no longer blocks on the MCP binds; sidecar failure named at once)

- entry: R15-LIFECYCLE-001 (high), sha 9368c62 (9368c626b76f4a4aa6a319e30b2841d0cd2a4d9b)
- app: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-9368c62/src-tauri/target/debug/bundle/macos/Vysted Terminal.app (Contents/MacOS: vysted-terminal, vysted-sidecar, vysted-openbb-mcp-sidecar, vysted-sec-edgar-mcp-sidecar)
- isolated home: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-round-home-R15-LIFECYCLE-001 (fresh copy of gui-round-seed; dev-keystore.json = {"secrets": {}, "migrated": true}, verified)
- code read at 9368c62: src-tauri/src/lib.rs — spawn_boot(start_a, start_b, start_main) on one thread (l.350, called from setup l.558); start_main_sidecar fails status with "The data engine could not start (<err>)." (l.272-286); termination reason "The data engine stopped (exit code N)." (l.87-89) emitted as vysted://sidecar-terminated (l.307). src/lib/sidecar-client.ts:99-110 throws status.reason when state == "failed"; src/components/StatusChrome.tsx:232 chip label "Sidecar error" on status error.
- launch is WARM: no reboot is possible in this run; PyInstaller _MEI extraction is per-launch for --onefile, but OS file cache is warm. The verifier rules whether a warm launch carries the claim.
- real data dir mtime before: 1790978102
- timeline poller: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/lc001/poller.py (stdlib; every 0.5 s: monotonic t, app children, their LISTEN ports, GET /health, /openbb-mcp/status, /sec/status on the main sidecar port)

## Plan
launch 1 = seed via my sidecar HTTP (no GUI input) -> launch 2 = populated capture + check 4 (kill main sidecar child, captures only) -> check 3 broken copy (captures only) -> launch 3 = check 1 batch (captures + clicks); check 2 read from the launch-2/3 timelines.

Revised order (so the welcome/terms + onboarding modals are dismissed by check 1's clicks and later proof shots are unobstructed): launch 1 seed (no GUI input) -> launch 2 check 1 batch -> wait idle >= 900 -> launch 3 check 4 (captures only) -> check 3 broken copy (captures only). Check 2 from every launch timeline.
Coordinates (points) from R15-CODE-AGENT-001 captures of the same build at the same 1280x832 window: terms "I understand — continue" (768,598), onboarding "Skip" (502,728), toolbar "Open panel" (243,56).

## Presence waits
- 2026-10-02T23:2xZ idle 261 -> 341 -> 451 -> 469 s (input by someone else); waiting for idle >= 900 with a Monitor that prints idle every 60 s.
- 2026-10-02T23:26:15Z idle=909.1 sentinel=2026-10-03 21:43:50+00:00 front=Finder vysted=[0 Vysted apps] (pre-launch-1)

Order actually used: launch 1 = check 1 (fresh layout, unseeded) + seeding afterwards via HTTP; launch 2 = check 4 on the seeded layout; then check 3.

## Launch 1 — check 1 (window paints and takes input while the MCP children are still binding)
- presence before: 2026-10-02T23:26:15Z idle=909.1 sentinel=2026-10-03 21:43:50+00:00 front=Finder vysted=[0 Vysted apps]
- runner: lc001/run_check1.sh (launch.sh starts the poller, then `HOME=<isolated> nohup .../Contents/MacOS/vysted-terminal`, waits for the window via `rig.py bounds`, pid-scoped System Events frontmost for MY pid only, then `rig.py batch raw/batch-check1.json`, every rig stderr line epoch-stamped). Log raw/check1-run.log; batch exit 0, no abort.
- launch epoch 1790983582.231 (2026-10-02T23:26:22Z), app pid 37345, window present at +1.7 s: owner "Vysted Terminal", bounds [116, 43, 1280, 832] -> 1280x832 points (captures 2560x1664, 2x).
- children (raw/boot-timeline-check1.txt, t=1.0 s): 37364 vysted-openbb-mcp-sidecar, 37366 vysted-sec-edgar-mcp-sidecar, 37367 vysted-sidecar --port 64578 — ALL THREE spawned within ~1 s of launch: the data sidecar no longer waits for the MCP binds (the original repro: sidecar spawned only after both joins return).
- Bind times (raw/vysted-launch1.log, timestamps from the Rust core): openbb-mcp "subprocess healthy on 127.0.0.1:64579" 23:27:23.864Z (+61.6 s); sec-edgar-mcp never bound, killed at 23:27:53.668Z (+91.4 s, "did not bind ... within 45s x 2 attempts; treating as unavailable"); main sidecar uvicorn "running on 127.0.0.1:64578" 23:28:05.462Z (+103.2 s; the core's own wait logged "did not come up" at +91.3 s, the frontend's retries connected after). This warm launch ran under heavy CPU contention (load average 3.6; the parallel ci-local lane), so every PyInstaller --onefile child was slow.
- note: the launch-1 poller looked for LISTEN sockets only on the direct children; a --onefile binary's listener is its grandchild (bootloader -> python), so `listen=-` in that file is not evidence of "not bound". Bind times above come from the core's log; the poller was fixed (grandchildren included) for later launches (raw/poller.py).
- captures (each opened):
  - 9368c62-01-boot-early.png (+2.65 s): window fully painted, dark theme: toolbar (Agent, Open panel ⌘K, Save layout), status chip amber "CONNECTING…", "OLLAMA (LOCAL) · QWEN2.5 7B", Chat 1 dock with "Ask anything" + Try-this prompts, and the first-run "Welcome to Vysted" terms modal. Nothing bound at this time.
  - click (768,598) "I understand — continue" at +2.72 s; click (502,728) at +4.29 s (onboarding Skip position; no onboarding modal had appeared, so it hit empty canvas).
  - 9368c62-02-boot-after-clicks.png (+5.87 s): terms modal GONE (the click was handled at once); chip still "CONNECTING…"; dock and toolbar painted; panel area empty (workspace restore waits on the sidecar).
  - click toolbar "Open panel" (243,56) at +5.92 s.
  - 9368c62-03-boot-toolbar-palette.png (+8.99 s): command palette open — "Ask anything, search agents, panels, symbols…", SUGGESTED Open Notes / New Research Space / Open Chart / Search a Ticker, ACTIONS Open Chart ⌘1, Open Watchlist ⌘2, Open News Feed ⌘3. Chip still "CONNECTING…".
  - key escape at +9.18 s.
  - 9368c62-04-boot-later.png (+13.26 s): palette closed (escape handled), chip "CONNECTING…", window responsive.
- All four captures and three inputs landed while NO child had bound (first bind +61.6 s). No beachball, no frozen main loop.
- Check 1: SHOWN (warm launch).

## Launch 1 — check 2 (/health ok before the MCP binds finish)
- On launch 1 the order was openbb-mcp bound +61.6 s, main /health ok +103.2 s (timeline line 206, t=102.75: health=200, openbb available, sec "available":true endpoint 64580 though the sec child had been killed at +91.4 s). So on THIS contended launch /health did NOT precede the openbb bind; it did precede nothing. The fix does not order the binds, it only removes the serial wait: the sidecar was spawned at +1 s instead of after the joins (original: after both joins, up to 90 s). Re-measured on launch 2.

## Seeding (after check 1, my sidecar :64578 only)
- GET /workspace/__autosave__ -> raw/seed-before.json (6 symbols, 0 holdings, empty note). Added MSFT, holdings AAPL 10 @ 180 and NVDA 5 @ 120, notes.general; POST /workspace (raw/seed-post.json) -> {"status":"saved"}. kill 37345: all children (37364, 37367, grandchildren 37431, 37440) gone (ps empty). Blob on disk: 7 symbols, 2 holdings, note, layout portfolio/chart/brief.
- isolation (launch 1): HOME=<isolated>; app log at <isolated home>/Library/Application Support/com.vysted.terminal/logs/vysted.log; the workspace POST landed in the isolated workspaces/ file; real data dir mtime after launch 1 = 1790978102 (unchanged). (The --data-dir arg is proven explicitly on launch 2.)

---

# Round 2 — rc2 candidate ace7dd7 (ace7dd768c3b809b0e72b20b20cfc94eea2368bd)

The 9368c62 section above is kept as committed evidence; everything below is this round (files prefixed `ace7dd7`).

- entry: R15-LIFECYCLE-001 (high); CARRY_FORWARD_rc2.md: full **redrive** (boot thread order changed: MCP ports ride the main sidecar command env; Ready only after up to 15 s of `/health`; spawn-failure arm clears the endpoint file; Terminated arm clears it; renderer probe gets a 5 s timeout).
- app: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-ace7dd7/src-tauri/target/debug/bundle/macos/Vysted Terminal.app (worktree HEAD verified = ace7dd768c3b809b0e72b20b20cfc94eea2368bd; Contents/MacOS: vysted-terminal, vysted-sidecar, vysted-openbb-mcp-sidecar, vysted-sec-edgar-mcp-sidecar)
- isolated home: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gui-round-home-R15-LIFECYCLE-001 (rebuilt fresh from gui-round-seed at 00:3xZ; dev-keystore.json = {"secrets": {}, "migrated": true}, verified)
- code read at ace7dd7 (git show): src-tauri/src/lib.rs — `spawn_boot` (l.487) runs start_a, start_b (each returns its port + bind-wait step), then `start_main(port_a, port_b)`, THEN both bind waits concurrently, all on one background thread; `start_main_sidecar` (l.382) fails status with "The data engine could not start (<err>)." on sidecar()/spawn() error (l.404/411), passes MCP ports via `.envs(mcp_port_env(..))`; Terminated arm (l.430) -> `terminated_reason` "The data engine stopped (exit code N)." (l.87) + emits vysted://sidecar-terminated; Ready only after bind + `wait_for_sidecar_health(port, 15)` (l.463). src/lib/sidecar-client.ts:98-100 throws `status.reason` when state == failed; src/components/StatusChrome.tsx:232-240 chip "Sidecar error — <reason>" (R15-LEAD-021).
- launch is WARM: no reboot possible in this run (OS file cache warm; --onefile _MEI extraction is still per-launch). The verifier rules whether a warm launch carries the claim.
- real ~/Library/Application Support/com.vysted.terminal mtime before (stat only): 1790978102
- runners: scratchpad/lcace/{launch.sh, run_check1.sh, presence.sh, poller.py} (poller = raw/poller.py, grandchildren-aware: every 0.5 s monotonic t, app children, their LISTEN ports incl. --onefile grandchildren, GET /health, /openbb-mcp/status, /sec/status on the main sidecar port)
- concurrent load: the rc2 gate lane is running (battery sidecars :52346-52349, shared stack :52152-54) — the machine is contended; not mine, untouched.

## Plan (ace7dd7)
launch A = check 1 batch at boot (fresh home) + check 2 from its timeline, then seed via my own sidecar HTTP; wait idle >= 900; launch B (seeded) = populated proof + check 4 (kill only its main sidecar child; captures only); check 3 on a renamed-sidecar copy (captures only).

## Presence waits
- 2026-10-03T00:28Z idle=485 (needs 900) — waiting with separate sleep calls.
- 2026-10-03T00:36:15Z idle=908 READY (Monitor). Note: Bash foreground `sleep` is blocked in this harness; waits are a Monitor/`until` loop (each call < 120 s).

## Launch A — check 1 (window paints and takes input while both MCP children are still binding)
- presence before: 2026-10-03T00:36:26Z idle=918.4 sentinel=2026-10-03 21:43:50+00:00 front="Finder" vysted=[0 Vysted apps]; :5173 free; real mtime 1790978102.
- batch: raw/ace7dd7-batch-check1.json via scratchpad/lcace/run_check1.sh (launch.sh starts the poller then `HOME=<isolated> nohup .../Contents/MacOS/vysted-terminal`, waits for `rig.py bounds`, pid-scoped frontmost for MY pid, then the batch; every rig line epoch-stamped). Log raw/ace7dd7-check1-run.log; batch exit 0, 12/12 steps ok, no abort.
- launch epoch 1790987786.801 (2026-10-03T00:36:26.8Z), app pid 86910; window at +2.36 s: owner "Vysted Terminal", id 6319, bounds [116, 43, 1280, 832] -> **1280x832 points** (captures 2560x1664, 2x).
- children (raw/ace7dd7-boot-timeline-check1.txt line 5, t=1.51 s): 86936 vysted-openbb-mcp-sidecar --port 64620, 86939 vysted-sec-edgar-mcp-sidecar --port 64621, 86940 vysted-sidecar --port 64619 — all three spawned within 1.5 s of launch (the main sidecar no longer waits for the MCP joins).
- isolation (raw/ace7dd7-launchA-ps.txt): 86940 args `--data-dir <isolated home>/Library/Application Support/com.vysted.terminal --cache-dir <same>`; the isolated data dir gained logs/, app-meta.json, data_cache.db-wal (the app's own writes); real data dir mtime still 1790978102.
- captures (each opened; times from launch epoch):
  - ace7dd7-01-boot-2s.png (+3.67 s): window fully painted, dark theme — toolbar (Agent, Open panel ⌘K, Save layout), chip amber "CONNECTING…", "OLLAMA (LOCAL) · QWEN2.5 7B", Chat 1 dock (Ask anything…, Try-this chips), and the first-run "Welcome to Vysted" terms modal with "I understand — continue". No child bound.
  - click (768,598) "I understand — continue" +3.76 s; click (502,728) +5.33 s (onboarding Skip position; no onboarding modal appeared — empty canvas).
  - ace7dd7-02-boot-6s-after-clicks.png (+6.41 s): terms modal GONE (click handled at once); chip still "CONNECTING…"; dock fully interactive-looking (chips now full contrast); panel area empty (workspace restore waits on the sidecar).
  - click toolbar "Open panel" (243,56) +6.47 s.
  - ace7dd7-03-boot-toolbar-palette.png (+9.55 s): command palette open — "Ask anything, search agents, panels, symbols…", ACTIONS Open Chart ⌘1, Open Watchlist ⌘2, Open News Feed ⌘3, Open Portfolio ⌘4, Open Equity Overview, Open Research Brief, Open Settings ⌘,, Save Workspace ⌘S. Chip "CONNECTING…".
  - key escape +9.77 s.
  - ace7dd7-04-boot-12s.png (+11.84 s): palette closed (escape handled); chip "CONNECTING…"; window responsive.
- All four captures and three inputs landed while NO child had bound (first bind, openbb-mcp, at t=66.1 s). No beachball, no frozen loop.
- **Check 1: SHOWN (warm launch).**

## Launch A — check 2 (/health ok before the MCP binds finish)
- timeline (raw/ace7dd7-boot-timeline-check1.txt): openbb-mcp LISTEN 64620 at t=66.10 s; sec-edgar-mcp never bound, gone at t=91.31 s; main /health=200 first at t=107.43 s (line 215; openbb available endpoint 64620, sec "available":true endpoint 64621 although that child had been killed).
- app stdout (raw/ace7dd7-app-stdout-check1.log): "[vysted] Python sidecar not up yet on port 64619 after attempt 1/2 (45s)"; "[openbb-mcp] subprocess healthy on 127.0.0.1:64620"; "[vysted] Python sidecar did not come up on port 64619" (+~90 s, so `settle_boot(false)` recorded state Failed "The data engine did not come up on port 64619."); "[sec-edgar-mcp] subprocess did not bind ... within 45s x 2 attempts"; sidecar uvicorn "running on 127.0.0.1:64619" at 06:08:14 IST (=00:38:14Z, +107 s).
- load average at +100 s: 4.61 / 3.14 / 3.46 (the rc2 gate battery lane runs concurrently); three PyInstaller --onefile children extract at once.
- So on THIS contended warm launch /health did NOT come before the openbb bind; the main sidecar was simply the slowest of the three. The fix removes the serial wait (main spawned at +1.5 s, not after both joins) but does not order the binds. **Check 2: NOT SHOWN on launch A** (re-measured on launch B).
- Adjacent observation (launch A, code-backed): after the core's 45 s x 2 wait expires at ~+90 s, `settle_boot(false)` sets state Failed ("The data engine did not come up on port 64619.", lib.rs:67-80, sticky: `settle_boot` only moves from Starting). `resolvePortToBaseUrl` (sidecar-client.ts at ace7dd7) throws `status.reason` whenever state == failed, so the sidecar that answered /health at +107 s was never used: the app stdout shows NO webview request to :64619 after it came up (only my poller's /health, /openbb-mcp/status, /sec/status). A main sidecar slower than 90 s under load is lost for the session. Passive capture of launch A's settled state follows once idle >= 900 again.
- passive capture (presence 2026-10-03T00:51:43Z idle=906.9 sentinel=2026-10-03 21:43:50+00:00 front="Vysted Terminal" vysted=[pid 86910 mine + its WebKit helpers]): **ace7dd7-05-launchA-settled-after-late-sidecar.png** (opened, +15 min): chip red "SIDECAR ERROR — THE DATA ENGINE DID NOT COME UP ON PORT 64619." while :64619 answered /health 200 at that moment (curl); seeded layout NOT restored (default Equity Overview / Watchlist "Could not refresh quotes" skeleton / News error icon / empty Portfolio); provider banner; Ollama "NOT RUNNING". This confirms the adjacent observation on screen: a main sidecar slower than the core's 90 s wait is permanently declared failed for the session.

## Seeding (after the launch-A capture; my sidecar :64619 only)
- GET /workspace/__autosave__ -> raw/ace7dd7-seed-before.json (6 symbols, 0 holdings, empty note, seeded layout). Added MSFT, holdings AAPL 10 @ 180 and NVDA 5 @ 120, notes.general; POST /workspace (raw/ace7dd7-seed-post.json) -> {"status":"saved","name":"__autosave__"}. Blob on disk after quit: 7 symbols, 2 holdings, note.
- quit launch A: kill 86910; children 86936/86940 gone with it (ps empty; no listener on 64619/64620; no _MEI orphan). lsappinfo: 0 Vysted apps. Real data dir mtime 1790978102 (unchanged).

## Launch B — seeded relaunch; check 2 re-measured; check 4 (kill only the main sidecar child)
- presence before launch: 2026-10-03T00:52:38Z idle=961.5 sentinel=2026-10-03 21:43:50+00:00 front="Finder" vysted=[0 Vysted apps]. Load 2.97/3.21/3.32.
- launch.sh launchB: app pid 4182 at 00:52:44Z; children 4208 openbb-mcp :54121, 4210 vysted-sidecar :54120 (+ sec-edgar :54122). Timeline raw/ace7dd7-boot-timeline-launchB.txt, stdout raw/ace7dd7-app-stdout-launchB.log.
- check 2 again: openbb-mcp LISTEN t=64.40 s; core "Python sidecar did not come up on port 54120" (~+90 s); sec-edgar never bound, gone t=91.29 s; main /health=200 first at t=106.99 s (line 213); sidecar uvicorn "running on 127.0.0.1:54120" 06:24:31 IST. Same order as launch A: /health came LAST. **Check 2: NOT SHOWN (2/2 warm launches, both under the concurrent rc2 gate load).**
- presence before the capture: 2026-10-03T00:55:01Z idle=1104.7 sentinel=2026-10-03 21:43:50+00:00 front="Finder" vysted=[pid 4182 mine + helpers]. First `rig.py capture` refused: exit 4, RIG_ABORTS.log `2026-10-03T00:55:02.242856+00:00 ABORT capture: frontmost app is 'Finder', not Vysted` — a precondition refusal (Finder was already frontmost in the presence line before launch; my app had launched unactivated, no human input, idle kept climbing to 1119.6), not a mid-batch surprise. Brought MY pid front (`System Events ... unix id is 4182`), idle 1119.6, captured.
- **ace7dd7-10-launchB-before-kill.png** (opened, 00:55:16Z, +152 s): chip red "SIDECAR ERROR — THE DATA ENGINE DID NOT COME UP ON PORT 54120." although :54120 answered /health 200; the seeded layout (portfolio/chart/brief, 7-symbol watchlist, 2 holdings) was NOT restored — default Equity Overview / Watchlist "Could not refresh quotes" skeleton / News error / "This portfolio is empty". So this instance is not a healthy one: populated proof shots were unreachable because the app never used its own late sidecar.
- `kill 4210` (SIGTERM, the main sidecar child only; its --onefile grandchild 4283 exited with it) at 00:55:28Z; app stdout: "[vysted] The data engine stopped (signal 15)."
- **ace7dd7-11-launchB-after-sidecar-kill.png** (opened, +4 s after the kill): chip now red "SIDECAR ERROR — THE DATA ENGINE STOPPED (SIGNAL 15)." (the Terminated arm overwrote the boot failure and the chip shows the reason, R15-LEAD-021). Panels unchanged (they were already in their error states and make no new request without input; no chat turn sent — captures only). SIGTERM yields the "(signal N)" arm of `terminated_reason`, not "(exit code N)".
- **Check 4: chip half SHOWN on an instance that was already failed; panels/chat half NOT DRIVEN (no healthy instance and no input).**
- quit: kill 4182; ps empty for its tree and ports 54120-54122; lsappinfo 0 Vysted apps; real mtime 1790978102.

## Check 3 — renamed vysted-sidecar copy
- cp -R the built .app to scratchpad/gui-round-broken.app; renamed Contents/MacOS/vysted-sidecar -> vysted-sidecar.renamed-r15 (original bundle untouched: its MacOS dir still lists vysted-sidecar).
- presence before: 2026-10-03T00:56:08Z idle=1171.9 sentinel=2026-10-03 21:43:50+00:00 front="Finder" vysted=[0 Vysted apps].
- runner scratchpad/lcace/run_broken.sh (launch with isolated HOME, wait window, pid-scoped frontmost, batch raw/ace7dd7-batch-check3.json: wait 1, capture, wait 11, capture). Log raw/ace7dd7-check3-run.log: batch exit 0. App pid 11087, launch epoch 1790988969.261, window +2.6 s (bounds [116,43,1280,832]). stdout raw/ace7dd7-app-stdout-broken.log: "[vysted] The data engine could not start (No such file or directory (os error 2))."
- **ace7dd7-20-broken-3s.png** (opened, +4.34 s): chip red "SIDECAR ERROR — THE DATA ENGINE COULD NOT START (NO SUCH FILE OR DIRECTORY (OS ERROR 2))."; Watchlist "Could not refresh quotes", News "Could not load the news feed" (its sub-line, where the reason renders, is clipped behind the Portfolio group header at this layout size), Portfolio empty. Named at once, not after 120 s.
- **ace7dd7-21-broken-15s.png** (opened, +15.42 s): identical — chip still names "could not start (...)", no spinner.
- **Check 3: SHOWN** (chip names the reason at +4 s; panels show their error states at once; the panel-body reason text itself is clipped in the News panel and not legible in the shot).
- quit: kill 11087; its MCP children 11146/11150 gone; `rm -rf scratchpad/gui-round-broken.app` done; real mtime 1790978102.

## Launch C — a healthy instance for check 4 (and check 2 a third time)
- presence before: 2026-10-03T00:57:24Z idle=1247.6 sentinel=2026-10-03 21:43:50+00:00 front="Finder" vysted=[0 Vysted apps]. Load at 00:57: 6.61/4.91/4.01.
- app pid 12804 at 00:57:24Z; children 12822 openbb-mcp :57652, 12823 sec-edgar-mcp :57653, 12824 vysted-sidecar :57651. Timeline raw/ace7dd7-boot-timeline-launchC.txt, stdout raw/ace7dd7-app-stdout-launchC.log ("Python sidecar not up yet ... attempt 1/2", then "Python sidecar healthy on 127.0.0.1:57651", endpoint discovery file written under the isolated data dir).
- check 2 again: openbb-mcp LISTEN t=43.13 s; sec-edgar-mcp LISTEN t=83.75 s (line 167); main /health=200 t=84.77 s (line 169). /health came after both MCP binds, by ~1 s. **Check 2: NOT SHOWN (0/3 launches).** The original defect is absent in every timeline (main sidecar spawned at ~+1.5 s with the MCP children, not after their joins); what is not established is the stronger claim that the data engine answers before the binds finish — on this loaded machine the main --onefile sidecar is the slowest of the three.
- presence before the capture: 2026-10-03T00:59:28Z idle=1371.8 front="Vysted Terminal" (pid-scoped frontmost for 12804) vysted=[pid 12804 mine + helpers].
- **ace7dd7-30-launchC-healthy-populated.png** (opened, +124 s): chip green "CONNECTED"; seeded layout restored — Chat 1 (CONTEXT: CHART (^NSEI, 1D)), Portfolio|Chart group on the ^NSEI 1d chart (MA 24355.76/23870.10/23268.93, last 22421.95, MACD, RSI(14), Volume, Trend drawing), Brief SETFNIF50 ₹252.41 -₹0.20 (-0.08%), P/E 20.35, 52W 238-287, volume 870K; model chip "OPENAI · NO API KEY". Dark theme, populated.
- `kill 12824` (SIGTERM, main sidecar child only) at 00:59:42Z; stdout "[vysted] The data engine stopped (signal 15)."
- **ace7dd7-31-launchC-after-sidecar-kill.png** (opened, +4 s): chip red "SIDECAR ERROR — THE DATA ENGINE IS NOT RESPONDING — IT MAY HAVE STOPPED. RESTART VYSTED." (the renderer's generic SIDECAR_UNREACHABLE from a failed request won the race against the terminated event at this instant). Panels keep their last data.
- **ace7dd7-32-launchC-after-kill-20s.png** (opened, +25 s): chip settled to red "SIDECAR ERROR — THE DATA ENGINE STOPPED (SIGNAL 15)." Panels unchanged (no new request without input).
- batch raw/ace7dd7-batch-check4-chat.json (presence 2026-10-03T01:00:21Z idle=1424.9 sentinel=2026-10-03 21:43:50+00:00 front="Vysted Terminal" vysted=[pid 12804 mine]): click chat input (230,768), type "What moved NVDA today?", return, wait 5, capture; click Portfolio tab (515,148), wait 4, capture. 9/9 ok, exit 0 (raw/ace7dd7-check4-chat-run.log).
  - **ace7dd7-33-launchC-chat-after-kill.png** (opened): chat send was refused before it reached the engine: "No API key for OpenAI. Add one in Settings → AI Providers (or /key set openai)." (the seed's default provider has no key, and keys are out of bounds for this drive). The chat half of check 4 cannot be shown here.
  - **ace7dd7-34-launchC-portfolio-after-kill.png** (opened): Portfolio "Portfolio · 2" with AAPL and NVDA rows (the seed), "Market value: — (no live quotes) · Total P&L: —", amber "Couldn't refresh live quotes — values shown without market data." + Retry. The panel shows its own quote-refresh copy, NOT "The data engine stopped (...)"; chip still "SIDECAR ERROR — THE DATA ENGINE STOPPED (SIGNAL 15)."
- **Check 4: chip half SHOWN on a healthy instance (settles to "Sidecar error — The data engine stopped (signal 15)." within 25 s; a generic "not responding" chip shows for the first seconds). Panel half: the one panel re-driven (Portfolio) shows a generic quote-refresh warning, not the termination reason. Chat half NOT DRIVEN (no provider key).** SIGTERM gives "(signal 15)"; an "(exit code N)" exit was not produced.
- quit: kill 12804; nothing of its tree or ports 57651-57653 left; poller stopped; lsappinfo 0 Vysted apps; :5173 untouched (no vite started).

## Real-data check and stops
- real ~/Library/Application Support/com.vysted.terminal mtime: before 1790978102, after every launch 1790978102, final 1790978102 (unchanged). No keychain or SecurityAgent dialog appeared in any capture.
- stops: none from presence or a human. One rig refusal (exit 4, frontmost Finder before my unactivated window was brought front, 00:55:02Z), a precondition, not a surprise; recorded above.
- warm launches only (no reboot); load 3-6.6 from the concurrent rc2 gate lane throughout.

## Verdict (ace7dd7)
- check 1 SHOWN (01-04); check 2 NOT SHOWN 0/3 (main spawned at +1.5 s every time, the original serial wait is gone, but /health was last each time under load); check 3 SHOWN (20-21; chip names "could not start (No such file or directory (os error 2))" at +4 s); check 4 chip SHOWN (32), panel shows generic copy (34), chat not driven (33, no key).
- Adjacent, high-impact (launches A and B, 2/3 boots): a main sidecar that answers /health after the core's 45 s x 2 wait is declared failed for the whole session — chip "SIDECAR ERROR — THE DATA ENGINE DID NOT COME UP ON PORT N.", seeded layout and data never restored, while the sidecar is healthy on that port (05, 10). `settle_boot(false)` is sticky and `resolvePortToBaseUrl` throws on state == failed (lib.rs:67-80, sidecar-client.ts at ace7dd7). Same logic at 9368c626.
- verdict: **blocked_env** — the contended warm environment (rc2 gate load, no reboot) kept the main sidecar the slowest boot every time, so check 2 could not be established, and the chat half of check 4 needs a provider key that is out of bounds. Nothing showed the original defect (frozen loop or a sidecar spawned only after the MCP joins). The verifier rules on the warm launch and on the panel copy in 34.
- tracked excerpts of the git-ignored *.log files: raw/ace7dd7-app-stdout-excerpts.txt (bind/health/failure lines of every launch), raw/ace7dd7-run-logs.txt (the three rig run logs).
