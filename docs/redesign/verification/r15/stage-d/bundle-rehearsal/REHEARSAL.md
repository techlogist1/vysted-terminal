BUNDLE REHEARSAL: PASS-WITH-FINDINGS at 64e9470e

# Production-bundle rehearsal at 64e9470e

- Worktree: `<scratchpad>/rehearsal-64e9470e`, detached. `git rev-parse HEAD` returned `64e9470e9b677ada4338e5c7a9a2aa2fa297b4a2`. It is left in place for the lead to remove.
- Runbook followed: `stage-d/RELEASE_RUNBOOK.draft.md` (draft at 4d893147), §0, §2, §4, §5, §6 and §7.
- Toolchain: pnpm 10.32.1, node v24.15.0, rustc host `aarch64-apple-darwin`. `python3` is Homebrew 3.13. `python` and `pytest` are not on PATH, and a fresh worktree has no `sidecar/.venv`.
- Version at this sha: `0.8.0`. The 0.9.0 bump branch is still unmerged, so every artifact is named 0.8.0.
- Run window: 05:05–05:22 IST, 26 Sep 2026. Stamps come from `date`.
- Logs sit beside this file. Long logs are tailed and paths are sanitized to `<scratchpad>`, `~` and `<tmp>`.

## Step table

| # | Step | Command | Exit | Duration | Log |
|---|------|---------|------|----------|-----|
| 1 | worktree | `git worktree add --detach <scratchpad>/rehearsal-64e9470e 64e9470e` | 0 | ~5 s | — |
| 2a | install | `pnpm install --frozen-lockfile --offline` (the offline attempt worked, so no online fallback was needed) | 0 | 7 s (05:05:52) | `install-offline.log.txt` |
| 2b | sidecars | `VYSTED_SKIP_DEV_SIGN=1 node scripts/ensure-all-sidecars.mjs --force` | 0 | 316 s, pip wheel cache warm (05:06:04) | `sidecars.log.tail` (last 400 of 1730 lines) |
| 3 | tauri build | `VYSTED_SKIP_DEV_SIGN=1 pnpm tauri build` | 0 | 196 s, cargo release 2m29s on a cold target (05:11:33) | `tauri-build.log.tail` |
| 4 | smoke | `node scripts/smoke-test-sidecars.mjs` | 0 | 138 s (05:15:17) | `smoke.log.txt` |
| 5 | clean-profile launch | `HOME=<scratchpad>/rehearsal-home "<app>/Contents/MacOS/vysted-terminal"` | quit by SIGTERM | 05:18:21 to 05:20:47 | `app-launch.log.tail`, `first-run-1x.png` |

## Sizes

| Artifact | Bytes | MB |
|---|---|---|
| `src-tauri/binaries/vysted-sidecar-aarch64-apple-darwin` | 87,435,968 | 87.4 (83.4 MiB), within the ≤120 MB target |
| `src-tauri/binaries/vysted-openbb-mcp-sidecar-aarch64-apple-darwin` | 54,492,496 | 54.5 |
| `src-tauri/binaries/vysted-sec-edgar-mcp-sidecar-aarch64-apple-darwin` | 82,806,624 | 82.8 |
| `src-tauri/target/release/bundle/macos/Vysted Terminal.app` (du) | 233,676,800 | 233.7 (the host binary alone is 8.65 MB) |
| `src-tauri/target/release/bundle/dmg/Vysted Terminal_0.8.0_aarch64.dmg` | 228,589,409 | 228.6 |

The build log contains no `[dev-sign] signed` line (0 matches), so `VYSTED_SKIP_DEV_SIGN=1` worked in both step 2b and step 3. In step 3, `beforeBuildCommand` re-ran ensure-all-sidecars and logged "present and fresh — skipping build" for all three sidecars.

## Signing state

- `codesign -dv --verbose=2` on the .app printed `Signature=adhoc` and `TeamIdentifier=not set`. The identifier is `vysted_terminal-da7ff30dcca9f983`, which is the linker's ad-hoc signature on the host binary, not `com.vysted.terminal`.
- All three sidecars inside `Contents/MacOS` are also `Signature=adhoc`.
- `codesign --verify --deep --strict` on the .app exits 1 with "code has no resources but signature indicates they must be present". `spctl -a -t exec` exits 1. The bundle is not sealed.
- Nothing was signed or notarized. That step is operator-only (§8).

## Smoke test (step 4)

- `/health` OK. The version check passed at `0.8.0`.
- `/agents` roster OK with 13 agents.
- `/mcp/status` returned `ready=true, toolCount=40`.
- The screener universe and ICONIKSPEV probes passed. `/history/ICONIKSPEV` returned 27 EOD bars from bse.
- openbb-mcp and sec-edgar-mcp both bound their ports and survived the settle window.
- The BSE bhavcopy and NSE direct no-SLA probes passed.
- The run ended with `[smoke] all sidecars booted cleanly.`
- The script tore down its three children itself (pids 28065, 28416, 28534). A `ps` check afterwards found none of them alive.
- Also found were a pre-existing pair of relative-path MCP sidecars with ppid 1 on :52153/:52154 (pids 20465/20469 and their children). They predate this run (lower pids, started before 05:05) and are not mine, so I left them alone.

## Clean-profile launch (step 5, runbook §7)

**Presence rule.** HID idle was 1837 s and the frontmost app was Finder, so the machine was idle. It was still 1953 s idle at capture time. The operator's installed `/Applications/Vysted.app` was not running. It has a different bundle id (`com.vysted.desk`, 0.8.0) and was never touched.

**Isolation mechanism.** §7 names no mechanism for a fresh app-data directory. There is no env var for it. `src-tauri/src/lib.rs:186-203` (`resolve_data_dir`) uses Tauri's `app.path().app_data_dir()`, which on macOS is `$HOME/Library/Application Support/com.vysted.terminal`. The core passes that path to the sidecar as `--data-dir` (`lib.rs:277`). So I used a `HOME=` override and exec'd the bundle's binary directly. I did not use `open`, because `open` does not forward the environment and LaunchServices can re-activate an existing instance.

**Sidecar warm-up.** Timings from launch:

- 0–30 s: no listener (cold `_MEI` extraction).
- 40 s: the main sidecar was listening.
- 60 s: all three were listening: main on :51693, openbb-mcp on :51694, sec-edgar-mcp on :51695.

`curl /health` returned `{"status":"ok","service":"vysted-sidecar","version":"0.8.0",…,"agents_degraded":[]}`.

**Window.** The window rendered and was not white: the full cockpit with the agent dock, Equity Overview, a populated Watchlist, News with sentiment, and Portfolio (`first-run-1x.png`, 1280×832). The status bar read `CONNECTED · OLLAMA (LOCAL)`.

- The System Events process name of the release bundle is `vysted-terminal`, but its CGWindow owner name is `Vysted Terminal`.
- `/tmp/rigcap.py` does not exist on this machine.
- A Quartz `CGWindowListCreateImage` call from the sidecar venv's python returned no image (that interpreter has no screen-recording grant). `screencapture -x -o -l <windowid>` with the window id found by owner PID worked.

**First-run terms (DisclaimerFlow).** The terms did **not** appear, and the app was fully usable without an ack. Before launch I checked the keychain read-only, with no value printed:

- `security find-generic-password -s vysted-terminal -a app-meta:first-launch-terms` exited **44**, so there is no ack item.
- The same check for `app-meta:onboarding-complete` exited **0**, so that item is present.

The dialog was missing for this reason: the unified log for my app's pid shows `SecKeychainCopyDomainDefault` followed by `MacOS error: -25307` (errSecNoDefaultKeychain), 30 times from 05:18:26. With `HOME` redirected, the Security framework finds no default keychain, every `keychain_get` fails, and `FirstLaunchTosDialog` awaits `refreshFirstLaunchAck()` with no catch (`src/modules/safety/DisclaimerFlow.tsx:44-49`). `hydrated` therefore stays false and the dialog returns null (`:68`). This is the R15-UI-044 failure mode, triggered here by the isolation method rather than by a Deny click. The terms check is **inconclusive** under `HOME=` isolation. It is not a pass.

- **Keychain dialog:** none appeared. No SecurityAgent process ran and no dialog window showed. With no default keychain, nothing reaches the login keychain, so the operator's keychain items were neither read nor written.

**Isolation leak.** WKWebView did not honour `HOME`. After launch, 10 files were modified under the real `~/Library/WebKit/com.vysted.terminal/WebsiteData/ResourceLoadStatistics/` (`pcm.db*`, `observations.db*`) and `~/Library/Caches/com.vysted.terminal/WebKit/` (`CacheStorage/salt`, `AlternativeServices/*`). No LocalStorage or IndexedDB files changed. This is the store shared with dev/rig builds of `com.vysted.terminal`, not the installed `com.vysted.desk` copy. I did not revert these files, because they are the operator's.

**Quit.** `kill -TERM 29178` (the app). All seven processes of my tree exited within 5 s: the app, three sidecar bootloaders and three python children, pids 29178/29197/29198/29199/29215/29220/29221. No kill -9 was needed. The stdin-EOF watchdog covers the case where `RunEvent::Exit` does not run on a signal. Ports 51693–51695 were free afterwards. The fresh HOME was 4.3 MB and has been deleted (`rm -rf` exit 0, path gone).

## Runbook corrections

1. **§0** says `source sidecar/.venv/bin/activate`. In a fresh checkout or worktree that venv does not exist until §4 creates it (`sidecar-specs.mjs:258-266` `ensureBuildVenv`). Replace with: "Run §4 first (it creates `sidecar/.venv` on Python 3.13 from `requirements-dev.txt`), then `source sidecar/.venv/bin/activate` before §3." Also move the checklist so §4 comes before §3, or note that §3's own `ensure-all-sidecars` builds the venvs.
2. **§6** gives `src-tauri/target/release/bundle/dmg/Vysted Terminal_0.9.0_<arch>.dmg` plus the `<!-- VERIFY … -->` note. Replace with the observed pattern `Vysted Terminal_<version>_aarch64.dmg` (at this sha, `Vysted Terminal_0.8.0_aarch64.dmg`, 228.6 MB), and the .app at `bundle/macos/Vysted Terminal.app` (~234 MB). Drop the VERIFY comment.
3. **§6** should state the signing state. Add: "Without §8 the bundle is ad-hoc only and unsealed. `codesign --verify --deep --strict` fails ('code has no resources but signature indicates they must be present') and `spctl` rejects it. The dmg is not distributable until §8 runs."
4. **§7** says "launch the just-built `.app` against a fresh app-data directory" and names no mechanism. Replace with: "There is no env var. The app-data dir is `$HOME/Library/Application Support/com.vysted.terminal` (`lib.rs:186` `app_data_dir()`). Launch `HOME=<fresh> "<bundle>/Contents/MacOS/vysted-terminal"` directly, not with `open`."
5. **§7** says "check (read-only…) `security find-generic-password …` … If present, either delete it … or run the check as a separate macOS user." This is incomplete. A `HOME=` launch has no default keychain (errSecNoDefaultKeychain -25307), so the terms dialog never renders whether the item exists or not, and the delete is irrelevant. Replace with: "`HOME=` isolation proves data-dir and sidecar warm-up only. The terms/onboarding check needs a separate macOS user account (its own login keychain and its own `~/Library/WebKit`). Never delete the operator's items as part of a rehearsal."
6. **§7** implies a fresh app-data dir isolates the run. It does not isolate WKWebView. Add: "WKWebView website data and caches still go to the real `~/Library/WebKit/com.vysted.terminal` and `~/Library/Caches/com.vysted.terminal` under a `HOME=` override."
7. **§4/§5** leave a `<!-- fill at rc2 -->` placeholder for expected output. It can be filled from `sidecars.log.tail` and `smoke.log.txt` here: three `[ensure-*] done.` lines and no `[dev-sign]` line; smoke shows 13 agents, MCP toolCount 40, and `[smoke] all sidecars booted cleanly.`
8. **§7** should add the observed warm-up so the reader knows what to expect: the main sidecar needs ~40 s and all three need ~60 s to listen on a cold first launch.

## Findings for the register

1. **HOME-isolated release launch silently skips the first-launch terms.**
   - Repro: `HOME=$(mktemp -d) "<bundle>/Contents/MacOS/vysted-terminal"` with no terms ack item in the login keychain. The cockpit renders with no terms dialog. The log shows `-25307` from `SecKeychainCopyDomainDefault`.
   - Severity: medium (same root cause as R15-UI-044; attach it there as a second trigger).
   - Location: `src/modules/safety/DisclaimerFlow.tsx:44-49,68`.
2. **Release bundle is unsealed and rejected by Gatekeeper before §8.**
   - Repro: `codesign --verify --deep --strict "Vysted Terminal.app"` exits 1; `spctl -a -t exec` exits 1.
   - Severity: medium. It blocks release only if §8 is skipped, but no unsigned dmg can be shared.
   - Location: `src-tauri/tauri.conf.json:30` (the `bundle` block has no macOS signing config).
3. **`HOME=` isolation leaks WKWebView data into the real user Library.**
   - Repro: launch as in 1, then `find ~/Library/WebKit/com.vysted.terminal ~/Library/Caches/com.vysted.terminal -newer <launch-marker>`. 10 files show up.
   - Severity: low (process/runbook; only WebKit housekeeping DBs were touched).
   - Location: `RELEASE_RUNBOOK.draft.md:447`.
4. **CLAUDE.md capture path points at a missing helper.**
   - Repro: `ls /tmp/rigcap.py` finds no such file. The release window owner is `Vysted Terminal`, not `vysted-terminal`. `screencapture -l <windowid>` works where venv Quartz capture is denied.
   - Severity: low.
   - Location: `CLAUDE.md:316`.
5. **§0 runbook step references a venv that does not exist yet.**
   - Repro: in a fresh worktree, `source sidecar/.venv/bin/activate` fails with "no such file".
   - Severity: low.
   - Location: `RELEASE_RUNBOOK.draft.md:44`.
6. **Main sidecar build venv installs dev requirements.**
   - Repro: `sidecars.log` shows `pip install -r sidecar/requirements-dev.txt` for `vysted-sidecar`.
   - Severity: low. PyInstaller bundles only imported modules and the binary is 87.4 MB, but test tooling sits in the build env.
   - Location: `scripts/sidecar-specs.mjs:86`.
7. **Frontend main chunk is 2.93 MB and one dynamic import is ineffective.**
   - Repro: the `pnpm tauri build` log prints `index-*.js 2,933.93 kB` and `[INEFFECTIVE_DYNAMIC_IMPORT] src/lib/sidecar-client.ts`.
   - Severity: low.
   - Location: `src/lib/export-artifact.ts` (the dynamic import of `sidecar-client`).

Benign PyInstaller warnings, recorded but not filed: `Hidden import "jinja2" not found` (main and openbb), `pycparser.lextab/yacctab` (sec-edgar), and `fastmcp.experimental.sampling.handlers` needing `openai` (openbb). The smoke test is green despite them.

## Processes

Every process I started has exited:

- the pnpm install
- the ensure-all-sidecars build
- `pnpm tauri build`
- the smoke test and its three children
- the app tree (29178 plus six children), ended with SIGTERM, no kill -9

No process of anyone else was touched.
