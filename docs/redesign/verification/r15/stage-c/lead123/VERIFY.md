# R15-LEAD-123 — fresh verification

- Verifier: Opus 5.5 (claude-opus-5-5), judgement tier, medium effort, fresh context. No product code was written and no advisor was consulted.
- Candidate: `r15-lead123-fix` at `45e3da32eab9b3445b2d1a02850ab42fe6aad3a6`. Base: `8d454e64e1e2afbc464a1e62f5333757160a8cc1`.
- Worktree: `<scratch>/lead123-verify` (detached at the candidate).
- Date: 2026-10-03, 12:20–12:44 IST.

## Verdict: CERTIFIED

| Check | Result |
|---|---|
| (1) Diff scope + safety surface | PASS. 4 files, all on the boot-wait path or its tests or docs; safety `git diff --quiet` exit 0 |
| (2) `pnpm ci-local` | EXIT=0 |
| (2) `node scripts/smoke-test-sidecars.mjs` | EXIT=0 |
| (3) Gate 8 `test_no_trading_surface.py` | 8 passed |
| (4) Fixed entries on the touched path | all hold (table below) |
| (5) Release bundle, first exec | main sidecar bound late, at **+92 to +102 s** (after core attempt 2/6). No "did not come up". The chip went CONNECTING… then CONNECTED, and panels populated |

## (1) Diff scope

```
$ git diff --stat 8d454e64 45e3da32
 .../verification/r15/stage-c/lead123/FIX.md        | 112 +++++++++++++++++++++
 src-tauri/src/lib.rs                               |  45 +++++++--
 src/lib/sidecar-client.test.ts                     |  26 ++++-
 src/lib/sidecar-client.ts                          |   9 +-
 4 files changed, 180 insertions(+), 12 deletions(-)
$ git diff --quiet 8d454e64 45e3da32 -- src/store/proposed-changes.ts types/proposed-change.ts sidecar/tests/test_no_trading_surface.py docs/SAFETY_ARCHITECTURE.md types/plugin.ts src-tauri/tauri.conf.json .github LICENSE COMMERCIAL_LICENSE.md CLAUDE.md
SAFETY_EXIT=0
```

### Conformance to the root cause's fix shape

- `MAIN_SIDECAR_WAIT_ATTEMPTS = 6` was added, with a `ponytail:` note naming `--onedir`. It is used only in the `start_main_sidecar` wait.
  - `MCP_PORT_WAIT_SECS` and `MCP_PORT_WAIT_ATTEMPTS` are unchanged.
  - `smoke_bind_budget_matches_supervisor` still passes.
- The renderer deadline moved from 120_000 to `READY_DEADLINE_MS = 300_000`. That exceeds the core's 270 s budget plus the 15 s `/health` confirm.
- There is no Failed→Ready flip; `settle_boot` is untouched.
- `the_boot_wait_keeps_an_earlier_exit_reason` is unchanged and passes.
- The stale "120 s probe" comment strings were updated.
- The remaining "90 s" mentions in `lib.rs` and the smoke script describe the MCP pair, which is correct.
- The smoke script's `MAIN_BOOT_TIMEOUT_MS = 120_000` is a smoke-test budget, not an assertion of the core budget, so it was correctly left alone.

### Test (1): fails at the base deadline, passes at the candidate

I temporarily set `READY_DEADLINE_MS = 120_000`, then restored it with `git restore`:

```
VITEST_EXIT=1
 × R15-LEAD-123: an engine that binds at +130 s still resolves (the deadline outlasts the core's budget)
AssertionError: expected SidecarError: The data engine did not bec… { status: … } to be 'http://127.0.0.1:54321'
      Tests  1 failed | 18 passed (19)
```

At the candidate: `Tests  19 passed (19)`.

### Test (2): Rust budget pin

At the base budget (45 × 2 = 90 s), the assertion `main_secs >= 240` fails. That is by inspection; I did not run a mutation for it.

## (2) Chain

`PATH=<wt>/sidecar/.venv/bin:$PATH pnpm ci-local`, with log at `<scratch>/ci-local.log`:

```
eslint/audit, prettier --check, tsc, cargo fmt --check, clippy -D warnings: clean
ruff: All checks passed!
 Test Files  169 passed (169)
      Tests  2032 passed (2032)
test tests::main_sidecar_budget_fits_inside_the_renderer_deadline ... ok
test tests::smoke_bind_budget_matches_supervisor ... ok
test tests::the_boot_wait_keeps_an_earlier_exit_reason ... ok
test result: ok. 32 passed; 0 failed
=========== 3921 passed, 1 skipped, 4 warnings in 224.85s (0:03:44) ============
EXIT=0
```

The coverage ratchet rewrote `vitest.config.ts` (1 line), and I ran `git restore` on it.

`node scripts/smoke-test-sidecars.mjs`:

```
[smoke] vysted-sidecar version OK (0.9.0).
[smoke] vysted-sidecar /agents roster OK (13 agents).
[smoke] vysted-sidecar /mcp/status OK (ready=true, toolCount=39).
[smoke] vysted-openbb-mcp-sidecar OK (bound :57849, survived settle window).
[smoke] all sidecars booted cleanly.
EXIT=0
```

## (3) Gate 8

```
$ cd sidecar && pytest tests/test_no_trading_surface.py -q
8 passed, 1 warning in 1.25s
```

## (4) Fixed register entries whose `files` include a changed file

These all hold. Each entry's pinned test lives in a suite that ran green in ci-local above (vitest, cargo test or pytest). Where an entry has no test, its design repro was re-checked at the candidate.

| ID | Pin / repro | Verdict |
|---|---|---|
| R15-LIFECYCLE-010 | `sidecar-client.test.ts` "a failed sidecar boot" + `lib.rs` tests | holds |
| R15-LIFECYCLE-011 | `src/store/app.test.ts` | holds |
| R15-LIFECYCLE-027 | `sidecar-client.test.ts`, `plugin-bootstrap.test.ts` | holds |
| R15-LIFECYCLE-037 | `lib.rs` tests | holds |
| R15-LIFECYCLE-038 | `lib.rs` tests | holds |
| R15-LIFECYCLE-007 | `test_searxng_manager.py` | holds |
| R15-AGENT-029 | `streaming.test.ts` | holds |
| R15-UI-012 | `streaming.test.ts` | holds |
| R15-UI-013 | `KeyEntryDialog`/`ChatSidebar` tests, `test_llm_*` | holds |
| R15-UI-014 | `sidecar-client.test.ts`, `streaming.test.ts` | holds |
| R15-RELEASE-009 | `lib.rs::smoke_bind_budget_matches_supervisor` (the MCP constants are untouched) | holds |
| R15-CODE-PLATFORM-011 | `delegate-runs.test.ts`, `sidecar-client.test.ts` | holds |
| R15-CODE-PLATFORM-039 | `sidecar-client.test.ts`, `search-headers.test.ts` | holds |
| R15-CODE-PLATFORM-054 | `lib.rs` tests | holds |
| R15-CODE-PLATFORM-055 | `lib.rs` tests | holds |
| R15-CODE-PLATFORM-074 | `lib.rs::clear_mcp_endpoint_file_removes_existing`; `clear_mcp_endpoint_file` is still called at `lib.rs:394/440/789` | holds |
| R15-CODE-PLATFORM-059 | design: all three kill sites still hoist `let child = state.0.lock().unwrap().take();` (`lib.rs:780`, `openbb_mcp.rs:190`, `sec_edgar_mcp.rs:185`) | holds |
| R15-CODE-PLATFORM-058, -060, -025 | closed as untestable / doc-only; the diff does not touch those regions | holds |
| R15-CODE-FRONTEND-027 | `sidecar-client.test.ts` + quant, node-editor and store tests | holds |
| R15-CODE-AGENT-021 | `test_llm_router.py` | holds |
| R15-CROSS-PLATFORM-004 | `command-palette.test.ts` | holds |
| R15-CROSS-PLATFORM-007 | `lib.rs` tests, `test_workspace.py` | holds |
| R15-CROSS-PLATFORM-008 | `lib.rs` tests | holds |
| R15-CROSS-PLATFORM-012 | `lib.rs` tests, `test_data_cache.py`, `test_cache_dir.py` | holds |
| R15-DATA-081 | chart, portfolio and watchlist tests, `test_quotes`/`test_history` | holds |
| R15-DATA-109 | `sidecar-client.test.ts` | holds |
| R15-RESEARCH-032 | `SettingsPanel.test.tsx` | holds |

## (5) The finding's own repro on the real release bundle

### Build

`VYSTED_SKIP_DEV_SIGN=1 pnpm tauri build` returned EXIT=0. It produced `Vysted Terminal.app` and `Vysted Terminal_0.9.0_aarch64.dmg`.

### Presence

At 12:38 IST:

- `rig.py idle` returned 2852.0, which meets the ≥ 900 requirement.
- `~/.vysted-rig-away` reads `2026-10-03T21:43:50+00:00`, which is in the future.
- `lsappinfo list | grep -i vysted` matched nothing (exit 1).
- Load average was 4.02 / 3.71 / 3.45.

### Launch

This was the first exec of the freshly built binary:

- app pid 54088
- `VYSTED_DATA_DIR=<scratch>/lead123-launch-data`
- T0 = 12:38:27 IST
- log at `<scratch>/lead123-launch.log`

### Listener poll

Abridged from `<scratch>/poll.log`:

```
+1s .. +51s   listeners=[]                                         load ~3.0-3.4
+61s          listeners=[vysted-op:127.0.0.1:57941]                (openbb-mcp)
+92s          listeners=[vysted-op:127.0.0.1:57941]  did_not_come_up=0
+102s         listeners=[vysted-op:127.0.0.1:57941 vysted-si:127.0.0.1:57940]  did_not_come_up=0
```

The main sidecar (port 57940) bound between **+92 s and +102 s**, which is past the old 90 s latch. So this launch exercised the late-bind path on the real bundle, not only in test (1).

### Core log

```
[vysted] Python sidecar not up yet on port 57940 after attempt 1/6 (45s); ...
[vysted] Python sidecar not up yet on port 57940 after attempt 2/6 (45s); ...
[vysted] Python sidecar healthy on 127.0.0.1:57940
[vysted] wrote MCP endpoint discovery file ".../lead123-launch-data/mcp-endpoint.json"
```

`grep -c "did not come up"` on the launch log returned 0 at +117 s, +238 s and +304 s. At +117 s, `curl /health` returned `{"status":"ok","service":"vysted-sidecar","version":"0.9.0",...}`.

### Captures

Each capture was taken with `screencapture -x -o -l 6695`, where window 6695 has owner pid 54088 and is named "Vysted Terminal". Each was registered with `register_capture.py`.

- `verify-1.png` (~+61 s): the status bar reads **CONNECTING…**, with the first-run terms dialog shown. This is before the bind and is the honest state.
- `verify-2.png` (+117 s, after the bind): the status bar reads **CONNECTED**. The Equity Overview, Watchlist and Portfolio panels are mounted, the watchlist rows are loading, and the news panel is populated (a TCS/Infosys item, "POSITIVE +0.77").
- `verify-3.png` (+304 s): still **CONNECTED**. The watchlist is populated with live rows (^NSEI 22,421.95 −0.88%; a second row 1,167.70 −1.63%). Nothing shows "DID NOT COME UP".

On a fresh data dir the first-run terms dialog stays over the cockpit throughout. The verifier did not interact with it. The status bar and the panels behind it are legible.

### Quit

I sent SIGTERM to 54088. The tree was 54088, 54128, 54139, 54131 and 54144, and none of those pids was alive 8 s later.

### Adjacent, out of scope

The sec-edgar MCP child again missed its unchanged 45 s × 2 budget and was treated as unavailable:

```
[sec-edgar-mcp] subprocess did not bind ... within 45s x 2 attempts; treating as unavailable. /sec routes will 501.
```

This is the separately registered medium split out in the root cause. It does not affect this finding.

### Limits

- This was a single launch at load ~3.5–4. The bind landed about 2–12 s past the old latch, so it proves the latch is gone for a modestly late bind.
- Binds near the new 270 s ceiling are covered only by test (1) and the Rust budget pin.
- The root cause's autosave read-back and kill negative control were not in this brief and were not run. With no Failed→Ready flip in the diff, the autosave overwrite path is unreachable by construction.
