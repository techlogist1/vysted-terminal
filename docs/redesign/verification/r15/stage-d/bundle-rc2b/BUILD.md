PRODUCTION BUNDLE: PASS at 1fddb2b1

# 0.9.0 production bundle build — rc2 head 1fddb2b1 (lead, 23:20–23:31 IST 3 Oct)

- Worktree `<scratchpad>/bundle-rc2b`, detached at `1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056` (004 head after the 5.14 fail-safe merge; code == certified `b796f6a9`). Fresh worktree, so no prior target/ or binaries (clean profile).
- Recipe: `stage-d/bundle-rc2/BUILD.md` rows 1-5, unchanged. Script: one detached zsh chain stamping `date` at each step (`steps.txt`).
- Toolchain: pnpm 10.32.1, node v24.15.0, rustc 1.95.0, cargo 1.95.0. Version embedded: CFBundleShortVersionString **0.9.0**.
- `[dev-sign] signed` matches across all logs: 0 — `VYSTED_SKIP_DEV_SIGN=1` held. Unsigned, as intended (signing stays the operator's).

## Step table (measured)

| # | Step | Command | Exit | Duration |
|---|------|---------|------|----------|
| 1 | worktree | `git worktree add --detach <scratchpad>/bundle-rc2b 1fddb2b1…` | 0 | 3 s (23:20:06→23:20:09) |
| 2 | install | `pnpm install --frozen-lockfile` | 0 | 5 s (23:20:09→23:20:14) |
| 3 | sidecars | `VYSTED_SKIP_DEV_SIGN=1 node scripts/ensure-all-sidecars.mjs --force` | 0 | 324 s (23:20:14→23:25:38) |
| 4 | tauri build | `VYSTED_SKIP_DEV_SIGN=1 pnpm tauri build` | 0 | 178 s (23:25:38→23:28:36) |
| 5 | smoke | `node scripts/smoke-test-sidecars.mjs` | 0 | 149 s (23:28:36→23:31:05) |

Total 659 s (11.0 min) against the ~11 min estimate from the a9b954af build.

## Sizes (bytes)

| Artifact | Bytes | MB |
|---|---|---|
| `vysted-sidecar-aarch64-apple-darwin` | 87,426,304 | 83.4 (≤120 MB target) |
| `vysted-openbb-mcp-sidecar-aarch64-apple-darwin` | 54,434,448 | 51.9 |
| `vysted-sec-edgar-mcp-sidecar-aarch64-apple-darwin` | 82,788,512 | 79.0 |
| `Vysted Terminal.app` (du -k) | 233,611,264 | 222.8 |
| `Vysted Terminal_0.9.0_aarch64.dmg` | 228,480,607 | 217.9 |

## DMG checksum

```
shasum -a 256 "Vysted Terminal_0.9.0_aarch64.dmg"
9940d41b7ed6725aaabb6bb1709dc48b4f8ec51facd0696e376c68401139bc53
```

## Smoke tail

```
[smoke] skipping live-exchange probes (pass --require-network, or run `pnpm probe:exchanges`, to include them).

[smoke] all sidecars booted cleanly.
[smoke] ATTENDED-SAFE: this run spawned and fully tore down 3 child process(es) on freshly-picked ephemeral ports: vysted-sidecar-aarch64-apple-darwin(pid=24149), vysted-openbb-mcp-sidecar-aarch64-apple-darwin(pid=24325), vysted-sec-edgar-mcp-sidecar-aarch64-apple-darwin(pid=24377). Zero interaction with any pre-existing vysted-* process — safe to have run alongside the operator's live app.
```

Logs beside this file as `.txt` (`.log` is gitignored); `sidecars.log.txt` is the last 300 lines.
