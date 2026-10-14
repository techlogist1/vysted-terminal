# GUI drive — R15-LIFECYCLE-040 at ace7dd7

- Entry: R15-LIFECYCLE-040 (low) — packaged-app cold boot never exercised the Tauri-Rust MCP spawn.
- SHA: ace7dd768c3b809b0e72b20b20cfc94eea2368bd (gui worktree HEAD confirmed)
- App: scratchpad/gui-ace7dd7/src-tauri/target/debug/bundle/macos/Vysted Terminal.app (Contents/MacOS: vysted-terminal + vysted-sidecar + vysted-openbb-mcp-sidecar + vysted-sec-edgar-mcp-sidecar, built 3 Oct 05:16-05:19)
- Isolated home: scratchpad/gui-round-home-R15-LIFECYCLE-040 (fresh copy of gui-round-seed; dev-keystore.json = {"secrets": {}, "migrated": true})
- CARRY_FORWARD_rc2: redrive (port handoff via Command::envs, Python status via mcp_client.LocalMcpSubprocess rewritten).
- Code read: sidecar/routers/mcp.py GET /openbb-mcp/status -> openbb_mcp_provider.status(); sidecar/routers/sec_filings.py GET /sec/status; src-tauri/src/openbb_mcp.rs header (spawn via tauri-plugin-shell, port handed to the main sidecar env).
- Real data dir mtime before (stat -f %m): 1790978102

## Log
- 06:02:08Z presence: idle=139.3 (below 900) — waiting before launch.
- 06:14:53Z presence: idle=904.8 sentinel=2026-10-03 21:43:50+00:00 front=Finder vysted=[] — launch allowed.

## Boot 1 (cold boot + seeding) — 06:14:59Z, pid 23592
- Launch: HOME=<isolated home> nohup ".../Vysted Terminal.app/Contents/MacOS/vysted-terminal" > raw/app-stdout-boot1.log.
- Children of 23592 (ps, t+52 s): 23606 vysted-openbb-mcp-sidecar --port 53563; 23607 vysted-sec-edgar-mcp-sidecar --port 53564; 23608 vysted-sidecar --port 53562 --data-dir <isolated home>/Library/Application Support/com.vysted.terminal. PyInstaller onefile workers 23617/23619/23618 under them.
- At t+57 s nothing listened yet (cold onefile extraction); at t+~100 s 53563 (openbb) and 53562 (main) listened; /health 200 version 0.9.0, providers "openbb-mcp":"available". vysted.log under the isolated home shows the main sidecar's httpx POST /mcp to 127.0.0.1:53563 200 (port handoff working).
- Seed (my sidecar :53562 only): GET /workspace/__autosave__ -> raw/seed-before.json; POST /workspace with raw/seed-post.json (copy of R15-CODE-AGENT-001's ace7dd7 seed: watchlist SPY QQQ BTC/USDT ETH/USDT NVDA AAPL MSFT, holdings AAPL 10 @180 + NVDA 5 @120, general note) -> {"status":"saved"}. Killed 23592; all children gone (ps). Blob on disk: 7 symbols, note present. Log raw/vysted-boot1.log (73 lines). Real data dir mtime still 1790978102.

## Boot 2 (the proof cold boot) — 06:17:35Z, pid 24395
- Presence before launch: 2026-10-03T06:17:33Z idle=1065.0 sentinel=2026-10-03 21:43:50+00:00 front=Finder vysted=[].
- Launch: same command, stdout raw/app-stdout.log. Window bounds (rig bounds): owner "Vysted Terminal", [116, 43, 1280, 832] -> launched size 1280x832 points (captures 2560x1664 px).

### Check 1 — MCP children are processes spawned by the app (raw/ps-tree.txt)
- ps at t+~100 s: 24404 vysted-openbb-mcp-sidecar --port 54849, 24405 vysted-sec-edgar-mcp-sidecar --port 54850, 24406 vysted-sidecar --port 54848 --data-dir <isolated home>/Library/Application Support/com.vysted.terminal — all ppid 24395 (the packaged app binary inside the .app bundle, Contents/MacOS). Their onefile workers 24421 / 24425 / 24424 hold LISTEN on 127.0.0.1:54849 / 54850 / 54848.
- vysted.log (isolated home, raw/vysted-boot2.log): sec-edgar-mcp "not bound on 127.0.0.1:54850 after attempt 1/2 (45s); cold PyInstaller extraction may be slow — retrying" at 06:18:19Z, then "Uvicorn running ... subprocess healthy on 127.0.0.1:54850" at 06:18:30Z — the Rust wait_for_port_with_retries 45 s x 2 budget doing its job on a cold boot. Isolation: logs, data dir and --data-dir all under the isolated home.
- Result: SHOWN (ps + lsof read back).

### Check 2 — GET /openbb-mcp/status and /sec/status on the app's sidecar port report bound/ready (raw/mcp-status.txt)
- 06:19:17Z, port 54848 (mine): /openbb-mcp/status 200 {"available":true,"provider":"openbb-mcp","endpoint":"http://127.0.0.1:54849/mcp","lastToolCallOk":true,"lastError":null}; /sec/status 200 {"available":true,"provider":"sec-edgar-mcp","endpoint":"http://127.0.0.1:54850/mcp","lastToolCallOk":null,"lastError":null}; /mcp/status ready:true toolCount 39; /health ok 0.9.0, "openbb-mcp":"available". The endpoints are exactly the ports the Rust core handed the children (Command::envs handoff works). Re-read after the GUI shots (appended): identical.
- Result: SHOWN.

### Check 3 — cockpit with the status chip (captures)
- First `rig.py capture` refused exit 4 (RIG_ABORTS.log `2026-10-03T06:19:27.468489+00:00 ABORT capture: frontmost app is 'Finder', not Vysted`) — precondition: my app launched unactivated, no human input, idle kept climbing (1177 -> 1191). Brought MY pid front via System Events `set frontmost of (first process whose unix id is 24395)` (LIFECYCLE-001/008, UI-050 precedent).
- Presence 2026-10-03T06:19:40Z idle=1191.4 front=Vysted Terminal vysted=[24395 mine + 24403 its helper]. `rig.py capture` -> ace7dd7-01-packaged-cold-boot-cockpit.png (opened): dark theme; "Welcome to Vysted" terms modal over the seeded layout; header status chip green "CONNECTED"; Chat 1 dock, Portfolio|Chart (^NSEI) group, Brief SETFNIF50 ₹252.41 -0.08%, P/E 20.35, 52W 238-287, volume 870K. Note: byte-identical (sha256 282de970…) to R15-CODE-AGENT-001's ace7dd7-01 (same seed, same build, weekend market data unchanged); the registry dedupes by sha, so it is registered under that row.
- batch raw/batch-01-terms-cockpit-plugins.json, presence 2026-10-03T06:20:21Z idle=1232.4 sentinel=2026-10-03 21:43:50+00:00 front=Vysted Terminal vysted=[24395 24403]. Steps: accept terms (768,598), capture 02; Skip onboarding (502,728), capture 03; Open panel (243,56), type "Open Plugin Manager", down, return, wait 8, capture 04. All 14 steps ok, EXIT=0.
  - ace7dd7-02-packaged-after-terms.png: not opened (intermediate; sha-identical to CODE-AGENT-001's 02).
  - ace7dd7-03-packaged-cockpit-connected.png (opened): populated cockpit, header chip "CONNECTED" (green dot) next to "OPENAI · NO API KEY"; ^NSEI 1d chart MA(200/50/20) 24355.76/23870.10/23268.93, last 22421.95, MACD/RSI(14)/Volume panes, Trend drawing; Brief SETFNIF50 ₹252.41 metrics + snapshot prose. (sha-identical to CODE-AGENT-001's 03 for the same reason.)
  - ace7dd7-04-packaged-plugin-manager.png (opened, new sha f078f7fe…): CONNECTED chip; Plugins panel "5 active of 5 loaded · 6 data sources · 1 agents · 0 nodes"; vysted-yfinance ACTIVE, openbb-mcp (OpenBB Open Data Platform, v0.1.0) ACTIVE; Brief populated alongside.
- Result: SHOWN.

### Check 4 — Windows packaged cold boot
- Out of reach on this Mac: NOT_DRIVEN.

## Quit and real-data check
- kill 24395 at ~06:21Z; all children (24404/24405/24406) and workers (24421/24424/24425) gone (ps empty; pgrep on the bundle path empty; lsappinfo shows no Vysted). No vite started.
- Real ~/Library/Application Support/com.vysted.terminal mtime: before 1790978102, after boot 1 1790978102, after boot 2 1790978102 — unchanged. No keychain / SecurityAgent dialog.

## Stops
- none from presence or a human. One rig precondition refusal (exit 4, frontmost Finder, unactivated launch, 06:19:27Z), recorded above.

## Note for the lead
- fix_shape asks for a DECISIONS.md record; DECISIONS.md is lead-owned, not edited here. This DRIVE.md is the macOS packaged cold-boot record.

## Verdict: HOLDS (macOS half) — packaged .app cold boot at ace7dd7 spawns openbb-mcp and sec-edgar-mcp as children of the app pid (onefile workers bound 54849/54850), /openbb-mcp/status and /sec/status on the app's sidecar report available with those endpoints, cockpit CONNECTED chip and Plugin Manager openbb-mcp ACTIVE captured. Windows half not_driven.
