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
