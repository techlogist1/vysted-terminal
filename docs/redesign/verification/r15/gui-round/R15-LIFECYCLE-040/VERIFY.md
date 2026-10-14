# GUI verify — R15-LIFECYCLE-040 at ace7dd768c3b809b0e72b20b20cfc94eea2368bd

Verifier: Opus 5.5, fresh context. Inputs: register entry, this entry's DRIVE.md, captures + raw/ here, CAPTURES.jsonl, presence.log, code at ace7dd7.

Claim (title + fix_shape): a launched packaged app spawns the MCP children through the Tauri-Rust `app.shell().sidecar()` path on a cold boot, and `/openbb-mcp/status` and `/sec/status` bind — on each platform — recorded in DECISIONS.md and the release gate docs.

## Capture registration

| Capture | sha256 | Registry row | Ruling |
|---|---|---|---|
| ace7dd7-01-packaged-cold-boot-cockpit.png | 282de970… | only under R15-CODE-AGENT-001/ace7dd7-01, taken 2026-10-02T23:55:48Z | not attributable to this drive (row predates this entry's presence lines 82-88); ignored |
| ace7dd7-02-packaged-after-terms.png | 47725726… | only under R15-CODE-AGENT-001/ace7dd7-02, 2026-10-02T23:56:18Z | same; ignored |
| ace7dd7-03-packaged-cockpit-connected.png | 380d13fa… | only under R15-CODE-AGENT-001/ace7dd7-03, 2026-10-02T23:56:23Z | same; ignored |
| ace7dd7-04-packaged-plugin-manager.png | f078f7fe… | this path, rig.py capture, owner "Vysted Terminal", 2026-10-03T06:20:42Z; presence line 88 (06:20:21Z, idle 1232) precedes it | registered; used |

## Per part

1. **Spawn path at ace7dd7 (code).** `src-tauri/src/openbb_mcp.rs:92` spawns via `.sidecar("vysted-openbb-mcp-sidecar")` and waits with `wait_for_port_with_retries` (:152); `lib.rs:382-402` hands the MCP ports to the main sidecar via `.envs(mcp_port_env(...))`. Context only.

2. **MCP children spawned by the packaged app — raw/ps-tree.txt (boot 2).** openbb-mcp (24404, --port 54849), sec-edgar-mcp (24405, --port 54850) and the main sidecar (24406) all have ppid 24395, the `.app/Contents/MacOS/vysted-terminal` binary; their onefile workers LISTEN on 54849/54850/54848. **Holds for boot 2.**

3. **/openbb-mcp/status and /sec/status bind — raw/mcp-status.txt (boot 2, 06:19:17Z and 06:20:59Z).** Both 200 `available:true`, with endpoints at exactly the ports the Rust core handed out; /health `"openbb-mcp":"available"`. **Holds for boot 2.**

4. **The first, truly cold boot — raw/vysted-boot2.log lines 1-42 (boot 1, pid 23592, 06:14:59Z).** This part shows the defect, and DRIVE.md leaves it out. In order:
   - 06:15:44Z: openbb-mcp, the main sidecar and sec-edgar-mcp all missed attempt 1/2.
   - 06:16:29.747Z: `[vysted] Python sidecar did not come up on port 53562`.
   - 06:16:29.772Z: `[sec-edgar-mcp] subprocess did not bind to 127.0.0.1:53564 within 45s x 2 attempts; treating as unavailable. /sec routes will 501.`
   - Only openbb-mcp became healthy (06:16:03Z).
   On the boot that matches the entry's "packaged cold boot", the `/sec/status` bind check failed. Boot 2 came after boot 1 had already extracted and warmed the disk cache, so it was a warm relaunch. DRIVE.md's description of boot 1 says only that "53563 (openbb) and 53562 (main) listened", which matches this failure. **Defect shown.**

5. **GUI state — ace7dd7-04 (registered, opened).** Header chip shows a green CONNECTED. The Plugins panel reads "5 active of 5 loaded · 6 data sources", with vysted-yfinance ACTIVE and openbb-mcp (OpenBB Open Data Platform v0.1.0) ACTIVE. The Brief is populated. Nothing in it covers sec-edgar. **Holds for openbb only, on boot 2.**

6. **Windows packaged cold boot.** NOT_DRIVEN, so not shown.

7. **The record in DECISIONS.md and the release gate docs (fix_shape).** Not done. DRIVE.md defers it to the lead. Not shown.

## Ruling: not_certified

The first packaged cold boot (boot 1) shows sec-edgar-mcp failing the Rust 45 s x 2 bind budget and being declared unavailable (/sec routes 501). The main sidecar also missed its budget. The passing evidence all comes from the warm second launch. On top of that, the Windows half was not driven and fix_shape's DECISIONS.md / release-gate record does not exist. This matches the carried-forward MCP cold-bind latency (CLAUDE.md "Deferred": the real fix is `--onedir`).
