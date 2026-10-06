# Windows manual check (NEEDS-MANUAL-CHECK) - ROG test

Nobody has built or run this branch on Windows, and CI has never run on `004-r4-experience-rebuild` (R15-RELEASE-004, R15-CROSS-PLATFORM-001). Source: `docs/RELEASE_RUNBOOK.md` sections 0, 4, 6 and 10, the register at `4b460027`, `CLAUDE.md` gotchas. Build target is the NSIS installer (`bundle.targets` includes `nsis`); the installer is unsigned, so SmartScreen will warn (R15-RELEASE-001).

## 0. Setup

Prerequisites per the runbook (§0, §4, §6), none of them confirmed on an actual Windows run: pnpm `10.32.1` exactly (pinned in all three CI workflows), Node, Rust with `rustc -vV` on `PATH` (MSVC toolchain), Python 3.13.13 in a `sidecar/.venv` (created by `ensureBuildVenv` the first time §3 or §4 runs; activate with `sidecar\.venv\Scripts\activate` in PowerShell, the Windows equivalent of the runbook's macOS `source sidecar/.venv/bin/activate`).

Build recipe (the same commands the runbook's §4/§6 give for macOS; nothing Windows-specific is recorded beyond the NSIS target itself):

```
pnpm install --frozen-lockfile
VYSTED_SKIP_DEV_SIGN=1 node scripts/ensure-all-sidecars.mjs --force
VYSTED_SKIP_DEV_SIGN=1 pnpm tauri build
```

Expected: three sidecars build (`vysted-sidecar.exe`, `vysted-openbb-mcp-sidecar.exe`, `vysted-sec-edgar-mcp-sidecar.exe`) and an NSIS installer is produced. This recipe is written from the runbook and the `tauri.conf.json`/`sidecar-specs.mjs` config, not verified against a real Windows build — if any step fails or needs a Windows-specific flag, that is itself worth recording as the first real Windows evidence this branch has ever had.

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

R15-LIFECYCLE-001 (the boot-freeze item previously listed here) is now **fixed**, not `needs_gui`; it is dropped from this list. The four items that remain `needs_gui` are R15-CODE-AGENT-001 (§1 above, Windows-specific), and these three, which are platform-agnostic but worth a Windows pass too:

- **R15-LIFECYCLE-008** (high): No diagnostics exist and a shipped build persists no log at all: every Rust, sidecar and MCP line goes to process stdout (no console at all on a Windows release build), so a user with a problem has no record. Packaged click-through on "Copy diagnostics" still needed on both platforms.
- **R15-UI-022** (medium): Chart drawing tools cannot place what the user clicks: anchors snap to the bar close, clicks past the last bar commit invisible drawings, Text always reads 'label', and Lock is a dead control.
- **R15-DOCS-024** (low): MCP_INTEGRATION.md's Claude Desktop (mcp-remote) setup has never been demonstrated end to end, and its claim that tools appear in Claude Desktop's slash picker as /vysted\_\_price_data is unverified.

Steps and expected results for each are in the register notes (`needs_gui` entries) and summarised here:

- R15-LIFECYCLE-008: `vysted.log` gets timestamped `[sidecar]`, `[vysted]` and MCP lines and rotates to `vysted.log.1`; a Windows release build has no console, so this log is the only record. Settings, Copy diagnostics previews then copies.
- R15-UI-022: chart drawings need native event injection; check a trendline at mid-candle, a click right of the last bar, the Text label, and a locked drawing's delete control.
- R15-DOCS-024: a real Claude Desktop session over `mcp-remote` against the sidecar's MCP endpoint (see `docs/MCP_INTEGRATION.md`); invoke a Vysted tool and record what the slash picker shows. Expected: tools appear; the documented `/vysted__price_data` form is unverified.
- R15-LIFECYCLE-040 (open low): the Rust MCP spawn (the Windows deadlock fix) has never been exercised inside a launched packaged app on any platform; check both MCP sidecars bind and `/mcp/status` reports them.

## 6. Installer

Run the NSIS installer: SmartScreen shows a warning (expected, unsigned); install, launch from the Start menu, uninstall. **Operator to confirm:** whether uninstall is expected to leave the data directory and keychain/Credential Manager entries in place or remove them — this is not recorded anywhere in the runbook or the register, and the NSIS config at this sha has no explicit data-retention setting one way or the other, so note what you actually observe rather than assuming either behaviour is "expected."
