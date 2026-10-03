# Windows manual check (NEEDS-MANUAL-CHECK) - ROG test

Nobody has built or run this branch on Windows, and CI has never run on `004-r4-experience-rebuild` (R15-RELEASE-004, R15-CROSS-PLATFORM-001). Source: `docs/RELEASE_RUNBOOK.md` section 10, the register at `4da7fc91`, `CLAUDE.md` gotchas. Build target is the NSIS installer (`bundle.targets` includes `nsis`); the installer is unsigned, so SmartScreen will warn (R15-RELEASE-001).

## 0. Setup

Prerequisites: pnpm, node, Rust (MSVC toolchain), Python 3.13. Then `pnpm install --frozen-lockfile`, `node scripts/ensure-all-sidecars.mjs --force`, `pnpm tauri build`. <<CHECK: Windows prerequisites and exact build recipe are not recorded beyond the runbook; confirm against docs/RELEASE_RUNBOOK.md section 4 to 6>> Expected: three sidecars build (`vysted-sidecar`, `vysted-openbb-mcp-sidecar`, `vysted-sec-edgar-mcp-sidecar`) and an NSIS installer is produced.

## 1. R15-CODE-AGENT-001 (high, needs_gui) - Origin allow-list - do this first

- What: the sidecar answers only allow-listed Origins (`tauri://localhost`, `http://tauri.localhost`, `https://tauri.localhost`, `http://localhost:5173`) and returns 403 to an unlisted or null Origin. Windows WebView2 sends `http://tauri.localhost`.
- Steps: install and launch the packaged app; open every panel (watchlist, chart, research, chat, portfolio, notes, settings). Then run `pnpm tauri:dev` and repeat. Read the app log (`logs/vysted.log` under the app data directory) for any `403`.
- Expected: every panel loads and no 403 appears for the webview's own origin. From a PowerShell prompt, `curl.exe -i -H "Origin: https://evil.example" http://127.0.0.1:<sidecar-port>/health` returns 403 and with `-H "Origin: http://tauri.localhost"` returns 200 (the port is chosen at launch; read it from the log).
- Register note: Batch-5 (1574ed8) needs_gui. Sidecar side verified live on both /health and /mcp/, including preflight: an evil Origin and the null Origin get 403; tauri://localhost, http(s)://tauri.localhost and localhost:5173 get 200 with ACAO; no Origin gets 200. GUI check: launch the packaged app (macOS and Windows) and pnpm tauri:dev -- confirm every panel loads and the sidecar log shows no 403 for the webview's origin. \|\| gui-round@ace7dd7: stays needs_gui: still_needs_gui: macOS packaged and dev both hold: every panel loads and no webview 403 appears (65 and 96 preflights, all 200). Remaining: launch the Windows packaged app (origin http(s)://tauri.localhost), tour every panel and grep the sidecar log for 403., evidence docs/redesign/verification/r15/gui-round/R15-CODE-AGENT-001/DRIVE.md, verifier docs/redesign/verification/r15/gui-round/R15-CODE-AGENT-001/VERIFY.md

## 2. Sidecar tree-kill on Windows

- Why: PyInstaller `--onefile` workers orphan and hold the temp extraction directory unless the whole process tree is killed (`taskkill /F /T`); the Rust core spawns sidecars through `app.shell().sidecar(...)` because Python `subprocess.Popen` deadlocks on Windows handle inheritance.
- Steps: launch the app, wait for connected, note the `vysted-*` processes in Task Manager (details view), quit the app, wait 10 seconds.
- Expected: no `vysted-*` process remains, and relaunch works without an extraction-lock error. Then kill the main sidecar from Task Manager while the app runs: the status chip flips to an error and panels say the data engine stopped, with an exit code.

## 3. Keychain on Windows

- Why: the `keyring` crate needs the `windows-native` feature (confirmed in `src-tauri/Cargo.toml`); without it `set_password` silently no-ops.
- Steps: in Settings, save a provider key, quit, relaunch, open the same provider.
- Expected: the key is still there after relaunch (Credential Manager shows an entry for the app), and no key text appears in `logs/vysted.log` or in Copy diagnostics. A debug build uses `dev-keystore.json` instead and is not a valid test of this item.

## 4. First-boot timing on Windows

- Why: the core waits 45 s x 6 = 270 s for the main data engine and the interface waits 300 s (R15-LEAD-123, merged at `d38b5d1a`); the MCP sidecars keep 45 s x 2.
- Steps: with the machine idle, launch the installed app cold; time launch to connected. Repeat once under load and once on relaunch. Antivirus scanning of the extraction can slow this.
- Expected: window paints and takes input within seconds (R15-LIFECYCLE-001 check 1), the engine answers health before the MCP binds finish (check 2), and the chip reaches connected inside the budget. Record all three timings. A bind later than 270 s still latches failed; the real fix is a `--onedir` build (deferred).

## 5. Needs-gui items that are not Windows-specific but should be run here too

- **R15-LIFECYCLE-001** (high): Every launch freezes the app's main event loop for the whole MCP bind window (about 25 s warm, 34 s+ cold, up to 90 s), and the data sidecar is not even spawned until both MCP binds return
- **R15-LIFECYCLE-008** (high): No diagnostics exist and a shipped build persists no log at all: every Rust, sidecar and MCP line goes to process stdout (no console at all on a Windows release build), so a user with a problem has...
- **R15-UI-022** (medium): Chart drawing tools cannot place what the user clicks: anchors snap to the bar close, clicks past the last bar commit invisible drawings, Text always reads 'label', and Lock is a dead control
- **R15-DOCS-024** (low): MCP_INTEGRATION.md's Claude Desktop (mcp-remote) setup has never been demonstrated end to end, and its claim that tools appear in Claude Desktop's slash picker as /vysted__price_data is unverified

Steps and expected results for each are in the register notes (`needs_gui` entries) and summarised here:

- R15-LIFECYCLE-001: cold launch after a reboot paints and accepts input while the MCP children bind (no beachball for 25 to 90 s); rename the bundled `vysted-sidecar` binary and launch: the chip goes red at once and panels name "The data engine could not start"; kill the sidecar: "Sidecar error" and "The data engine stopped (exit code ...)".
- R15-LIFECYCLE-008: `vysted.log` gets timestamped `[sidecar]`, `[vysted]` and MCP lines and rotates to `vysted.log.1`; a Windows release build has no console, so this log is the only record. Settings, Copy diagnostics previews then copies.
- R15-UI-022: chart drawings need native event injection; check a trendline at mid-candle, a click right of the last bar, the Text label, and a locked drawing's delete control.
- R15-DOCS-024: a real Claude Desktop session over `mcp-remote` against the sidecar's MCP endpoint (see `docs/MCP_INTEGRATION.md`); invoke a Vysted tool and record what the slash picker shows. Expected: tools appear; the documented `/vysted__price_data` form is unverified.
- R15-LIFECYCLE-040 (open low): the Rust MCP spawn (the Windows deadlock fix) has never been exercised inside a launched packaged app on any platform; check both MCP sidecars bind and `/mcp/status` reports them.

## 6. Installer

Run the NSIS installer: SmartScreen shows a warning (expected, unsigned); install, launch from the Start menu, uninstall. Expected: installs per-user without error and leaves the data directory alone on uninstall. <<CHECK: uninstall data-retention behaviour not recorded>>
