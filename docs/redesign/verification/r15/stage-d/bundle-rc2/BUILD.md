PRODUCTION BUNDLE: PASS at a9b954af

# 0.9.0 production bundle build — rc2 candidate a9b954af

- Worktree: `<scratchpad>/bundle-rc2`, detached. `git rev-parse a9b954af` resolved to
  `a9b954af1fbafb51ce20a9a750a10c83af21cb69`. Left in place for the lead's launch check.
- Recipe followed: `stage-d/bundle-rehearsal/REHEARSAL.md` step table rows 1-4 (worktree,
  install, sidecars, tauri build) + `docs/RELEASE_RUNBOOK.md`, with the rehearsal's runbook
  corrections applied (no `source sidecar/.venv/bin/activate` before the sidecar build; sizes
  reported as observed, not the stale `<!-- VERIFY -->` placeholder).
- Did NOT launch the app — a GUI round was driving the screen during this run. The lead
  launches from this worktree separately.
- Toolchain: pnpm 10.32.1, node v24.15.0, rustc 1.95.0 (aarch64-apple-darwin), cargo 1.95.0,
  python3 3.14.5 (system; the sidecar build venvs pin their own Python 3.13 per
  `sidecar_*/.venv`, confirmed in the PyInstaller log: `.venv/lib/python3.13/site-packages/...`).
- Version at this sha: **0.9.0** (the 0.9.0 bump is merged at this sha, unlike the 0.8.0
  rehearsal sha).
- Run window: step timestamps below are each step's own `date` start/end. There is a large
  wall-clock gap between step 3 (sidecars, ended 07:02:14 IST) and step 4 (tauri build,
  started 12:02:37 IST) — the harness session was idle for several hours between those two
  calls; this is a scheduling gap, not a build issue (no process ran during the gap).
- Logs sit beside this file as `.txt` tails (not `.log`, which is gitignored).

## Step table

| # | Step | Command | Exit | Duration | Log |
|---|------|---------|------|----------|-----|
| 1 | worktree | `git worktree add --detach <scratchpad>/bundle-rc2 a9b954af1fbafb51ce20a9a750a10c83af21cb69` | 0 | ~3 s (06:56:51→06:56:54 IST) | — |
| 2 | install | `pnpm install --frozen-lockfile` | 0 | 5 s (06:57:00→06:57:05 IST) | `install.log.txt` |
| 3 | sidecars | `VYSTED_SKIP_DEV_SIGN=1 node scripts/ensure-all-sidecars.mjs --force` | 0 | 287 s / 4m47s (06:57:27→07:02:14 IST) | `sidecars.log.txt` (tail of ~1800 lines) |
| 4 | tauri build | `VYSTED_SKIP_DEV_SIGN=1 pnpm tauri build` | 0 | 174 s / 2m54s, cargo release "Finished in 2m 13s" on a cold target (12:02:37→12:05:31 IST) | `tauri-build.log.txt` |
| 5 | smoke | `node scripts/smoke-test-sidecars.mjs` | 0 | 156 s / 2m36s (12:06:34→12:09:10 IST) | `smoke.log.txt` |

## Sizes (bytes)

| Artifact | Bytes | MB |
|---|---|---|
| `src-tauri/binaries/vysted-sidecar-aarch64-apple-darwin` | 86,664,576 | 82.6, within the ≤120 MB target |
| `src-tauri/binaries/vysted-openbb-mcp-sidecar-aarch64-apple-darwin` | 54,434,144 | 51.9 |
| `src-tauri/binaries/vysted-sec-edgar-mcp-sidecar-aarch64-apple-darwin` | 82,786,368 | 79.0 |
| `src-tauri/target/release/bundle/macos/Vysted Terminal.app` (du) | 232,845,312 | 222.1 |
| `src-tauri/target/release/bundle/dmg/Vysted Terminal_0.9.0_aarch64.dmg` | 227,712,662 | 217.2 |

Paths (inside the worktree, under `<scratchpad>/bundle-rc2/`):
- `src-tauri/target/release/bundle/macos/Vysted Terminal.app`
- `src-tauri/target/release/bundle/dmg/Vysted Terminal_0.9.0_aarch64.dmg`

The tauri-build log contains no `[dev-sign] signed` line (0 matches in `tauri-build.log.txt`
and 0 matches in the full sidecars log), confirming `VYSTED_SKIP_DEV_SIGN=1` held for both
steps 3 and 4.

## DMG checksum

```
shasum -a 256 "Vysted Terminal_0.9.0_aarch64.dmg"
36c755c49cdd4870df26daa52ae5f9c44d4383f9e3571ee0fee0ec1630d53a35
```

## Version embedded

```
defaults read ".../Vysted Terminal.app/Contents/Info.plist" CFBundleShortVersionString
0.9.0
```

## Signing state

Same as the 0.8.0 rehearsal (unchanged, expected under `VYSTED_SKIP_DEV_SIGN=1`, operator
signs/notarizes separately):

- `codesign -dv --verbose=2` on the .app: `Signature=adhoc`, `TeamIdentifier=not set`,
  `Identifier=vysted_terminal-47df5a6d55d6127f` (the linker's ad-hoc signature, not
  `com.vysted.terminal`), `Sealed Resources=none`.
- `codesign --verify --deep --strict`: exits 1, "code has no resources but signature
  indicates they must be present".
- `spctl -a -t exec`: exits 1, same reason.
- Nothing was signed or notarized by this run.

## Smoke result (step 5)

- `/health` OK — version check passed at **0.9.0**.
- `/agents` roster OK with **13 agents**.
- `/mcp/status` returned `ready=true, toolCount=39`.
- `/history/ICONIKSPEV` returned 26 EOD bars, provider=bse.
- Screener universe and ICONIKSPEV resolution probes passed.
- openbb-mcp and sec-edgar-mcp both bound their ports and survived the settle window.
- Live-exchange probes were skipped (not passed `--require-network`), per the script's
  default — same as the rehearsal did not require them for a PASS.
- Final line: `[smoke] all sidecars booted cleanly.`
- ATTENDED-SAFE teardown: the script tree-killed its own 3 children (vysted-sidecar
  pid=34237, openbb-mcp pid=35326, sec-edgar-mcp pid=35536) via its own PID ledger only; it
  never touched any pre-existing `vysted-*` process, including any live operator app.

## Confirmation

- No `[dev-sign] signed` line appears anywhere in the step 3 or step 4 logs.
- Worktree and build artifacts are left in place at `<scratchpad>/bundle-rc2` for the lead's
  launch check.
- The app was never launched by this run.
