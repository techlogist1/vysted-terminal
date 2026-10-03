# R15-LEAD-123 — fix

- writer: Opus 5.5 (claude-opus-5-5), judgement tier, medium; no advisor.
- base: 8d454e64; branch r15-lead123-fix; follows the fix shape in gui-round/R15-LEAD-123_ROOT_CAUSE.md §4.

## Diff summary

- `src-tauri/src/lib.rs`: new `MAIN_SIDECAR_WAIT_ATTEMPTS = 6` (45 s x 6 = 270 s, ponytail note: >270 s still latches, real fix is `--onedir`), used only by the main-sidecar wait in `start_main_sidecar`. Shared `MCP_PORT_WAIT_SECS`/`MCP_PORT_WAIT_ATTEMPTS` unchanged (MCP kill timing and the smoke test's `MCP_BIND_TIMEOUT_MS` untouched). New test `main_sidecar_budget_fits_inside_the_renderer_deadline` reads `READY_DEADLINE_MS` from `sidecar-client.ts` via `include_str!` and asserts core main budget + 15 s < deadline and core main budget >= 240 s. `the_boot_wait_keeps_an_earlier_exit_reason` unchanged. Two comments updated (120 s -> 300 s; the R8 wait comment).
- `src/lib/sidecar-client.ts`: renderer readiness deadline 120_000 -> `READY_DEADLINE_MS = 300_000` (> 270 s + 15 s health).
- `src/lib/sidecar-client.test.ts`: new fake-timer case — core answers `starting` and `/health` rejects until t=130 s, then both succeed; `getSidecarBaseUrl()` must resolve after 140 s.
- Not changed: no Failed->Ready flip on a late bind (workspace `restoreSettled` autosave hazard). `scripts/smoke-test-sidecars.mjs` asserts only its own `MAIN_BOOT_TIMEOUT_MS` and the MCP budget, not the core main budget, so it is untouched.

```
 src-tauri/src/lib.rs           | 45 +++++++++++++++++++++++++++++++++---------
 src/lib/sidecar-client.test.ts | 26 +++++++++++++++++++++++-
 src/lib/sidecar-client.ts      |  9 +++++++--
 3 files changed, 68 insertions(+), 12 deletions(-)
```

## Fail-before / pass-after (new vitest)

Base `sidecar-client.ts` (HEAD copy swapped in, then restored):
```
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/lib/sidecar-client.test.ts > getSidecarBaseUrl readiness gate > R15-LEAD-123: an engine that binds at +130 s still resolves (the deadline outlasts the core's budget)
  "message": "The data engine did not become ready in time.",
      Tests  1 failed | 18 skipped (19)
EXIT=1
```
With the fix:
```
 Test Files  1 passed (1)
      Tests  1 passed | 18 skipped (19)
   Start at  12:16:40
   Duration  568ms (transform 73ms, setup 47ms, import 30ms, tests 52ms, environment 348ms)

EXIT=0
```

## Check tails

Setup note: the fresh worktree had no externalBin sidecars, so `cargo clippy` first failed on the tauri build script (`resource path binaries/vysted-sidecar-aarch64-apple-darwin doesn't exist`); the three already-built binaries were copied (git-ignored) from the main worktree. The Rust checks run in a debug build and never execute them.

### install.log
```
│   to run scripts.                                                            │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
Done in 3.9s using pnpm v10.32.1
EXIT=0
```

### vitest.log
```
      Tests  19 passed (19)
   Start at  12:16:39
   Duration  621ms (transform 93ms, setup 51ms, import 30ms, tests 115ms, environment 338ms)

EXIT=0
```

### pnpm-typecheck.log
```

> vysted-terminal@0.9.0 typecheck /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/lead123-fix
> tsc --noEmit

EXIT=0
```

### pnpm-lint.log
```
> vysted-terminal@0.9.0 lint /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/lead123-fix
> eslint . && node scripts/audit-design-tokens.mjs

design-token audit clean (392 files)
EXIT=0
```

### pnpm-format:check.log
```
> prettier --check .

Checking formatting...
All matched files use Prettier code style!
EXIT=0
```

### rust-fmt.log
```
EXIT=0
```

### rust-clippy.log
```
   Compiling vysted-terminal v0.9.0 (/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/lead123-fix/src-tauri)
    Checking tauri-plugin-updater v2.10.1
    Checking tauri-plugin-shell v2.3.5
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 2.00s
EXIT=0
```

### rust-test.log
```
test tests::main_sidecar_budget_fits_inside_the_renderer_deadline ... ok
test tests::smoke_bind_budget_matches_supervisor ... ok
test tests::the_boot_wait_keeps_an_earlier_exit_reason ... ok
test result: ok. 32 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.02s
test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
EXIT=0
```
