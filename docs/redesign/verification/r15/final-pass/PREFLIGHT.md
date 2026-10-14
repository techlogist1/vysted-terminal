# R15 final pass — preflight (final-preflight, Opus 5.5 high)

Started 2026-10-03 (clock: see `date` stamps in logs). Head under test d38b5d1a2487bd52fe8a7e741a3a5266e3206611.
S = /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad

## (1) Git
- `git fetch origin` (ssh key form) ok.
- `git rev-parse d38b5d1a...^{commit}` = d38b5d1a2487bd52fe8a7e741a3a5266e3206611.
- `git merge-base --is-ancestor <sha> 004-r4-experience-rebuild` true; also ancestor of origin/004.
- `git tag --points-at <sha>`: none (burst window: rc2 not yet tagged; note, not blocker). Existing r15 tags: r15-rc1 -> 949c3c9f.
- authoring head 6bc6d378 is an ancestor of the sha: authored_head_is_ancestor = true.
- `git rev-parse r13-bedrock^{commit}` = 6a40f835ed7dd590de0b92c5177aa926c2264e58.
- local 004 = 2a256646, origin/004 = 4da7fc91; `rev-list --left-right --count 004...origin/004` = 2 0 (local 2 docs commits ahead, unpushed).
- `git branch -a --list '*worktree-agent-final-*'`: none (no previous attempt of this workflow).
- Main checkout HEAD 2a256646 on 004-r4-experience-rebuild; `git status --short` 28 lines (GUI-redrive evidence for R15-LIFECYCLE-008 + final-pass.js tooling edits, all uncommitted, untouched).
- `git worktree list`: ~45 worktrees; one other at this sha: $S/gui-d38b5d1 (GUI redrive, debug build only).

## (4) Seed $S/final-seed-data
Source $S/vysted-iso/data (never the operator's real dir). `sqlite3 "file:<db>?mode=ro" ".backup '<dst>'"` for custom_agents, data_cache, delegate_runs, fundamentals_cache, plugins, portfolio, workflows (all `pragma integrity_check` = ok); cp workspaces/__autosave__.vysted-workspace, searxng/settings.yml, notes/; fresh dev-keystore.json = `{"secrets": {}, "migrated": true}` chmod 600; no audit_log.db. Not copied (as ISO_STACK.md): backups/, resolver_masters/ (regenerated cache).

## (7) Register snapshot
`git show <sha>:docs/redesign/verification/vysted-r15-register.json > final-pass/register-at-d38b5d1.json`: 745 entries; fixed 595, open 90, blocked_tier4 35, removed_with_feature 14, not_a_defect 6, needs_gui 5. Open by severity: high 1, medium 31, low 58.
Note: R15-LEAD-123 (high) is `open` in the snapshot at the sha because its closure was recorded in the register after the merge (12d60f39); at 004 head it is `fixed`.

## (6) Env
- `ollama list`: llama3.1:8b present (also qwen3:8b, qwen2.5:7b); `curl :11434/api/tags` lists it; nothing loaded (`ollama ps` empty).
- `df -h /System/Volumes/Data`: 83 GiB free (no warn).

## (2) Candidate worktree
- `git worktree add --detach $S/final-cand d38b5d1a...` (fresh; path did not exist).
- Driver $S/final-build.sh (detached, pid 16919, started 14:35:20 IST): `pnpm install --frozen-lockfile` -> logs/preflight-install.log EXIT=0; `node scripts/ensure-all-sidecars.mjs --force` -> logs/preflight-sidecars.log; `VYSTED_SKIP_DEV_SIGN=1 pnpm tauri build` -> logs/preflight-tauri-build.log.

## (3) Bundle
- Search for an existing production bundle at this sha: $S/gui-d38b5d1 is a `pnpm tauri build --debug --bundles app` (gui-d38b5d1-build.sh) and has no release bundle; no other worktree at the sha. Not acceptable -> building.
- Correction 14:37:40 IST: attempt 0 of the sidecar step ran without VYSTED_SKIP_DEV_SIGN and dev-signed the main sidecar (`[dev-sign] signed ...vysted-sidecar...`, logs/preflight-sidecars-attempt0-devsigned.log). The production recipe (stage-d/bundle-rc2/BUILD.md) skips dev signing for the sidecar step too, so I stopped my own driver (pids 16919/16947/18740, by pid) and restarted it (pid 18892, 14:37:59 IST) with `export VYSTED_SKIP_DEV_SIGN=1` for every step: `node scripts/ensure-all-sidecars.mjs --force` then `pnpm tauri build`.
- Sidecar step (attempt 1, dev-sign skipped): logs/preflight-sidecars.log EXIT=0 at 14:41:57 IST, 0 `dev-sign` lines; `codesign -dv` on the main sidecar = `Signature=adhoc`. Binaries: vysted-sidecar 86,665,968 B; openbb-mcp and sec-edgar-mcp built.

## (5) Shared final-pass stack (from $S/final-cand/src-tauri/binaries, data $S/final-shared-data = cp -R of the seed)
Launcher $S/final-stack.sh: `mkfifo`; worker `< fifo` detached; `sleep 86400 > fifo` detached (exact sleep pid, no pgrep). Ports 52800-52802 were free (`lsof -iTCP:<p> -sTCP:LISTEN` empty) before start.
- openbb-mcp :52801 `--port 52801`, sleep 20806 / worker 20805, bound 14:41:03 (~40 s).
- sec-edgar-mcp :52802 `--port 52802`, sleep 22413 / worker 22412, bound by 14:44:11.
- main :52800 `env VYSTED_OPENBB_MCP_PORT=52801 VYSTED_SEC_EDGAR_MCP_PORT=52802 vysted-sidecar --host 127.0.0.1 --port 52800 --data-dir $S/final-shared-data`, sleep 22800 / worker 22799, bound by 14:44:11 (~2 min cold: XProtect scanning the freshly extracted .so files while cargo compiled; `sample` showed pandas imports progressing).
- `curl :52800/health` -> status ok, version 0.9.0, `"openbb-mcp":"available"`, agents_degraded [] (logs/shared-health.json). `/mcp/status` ready, toolCount 39. `/agents` 13. `/sec/filings/AAPL` 422 (route live, not 501). `Origin: http://evil.example` -> 403 (origin guard live).
- pids.json written. Stop = kill the sleep pid only.

## (3) Bundle result
- `pnpm tauri build` (VYSTED_SKIP_DEV_SIGN=1 exported) in $S/final-cand: logs/preflight-tauri-build.log 14:41:56 -> 14:44:58 IST, EXIT=0, 0 `dev-sign` lines, 0 sidecar rebuilds (beforeBuildCommand ensure was a no-op). "Finished 2 bundles". Static frontend written to $S/final-cand/out (index.html + assets).
- bundle_path: $S/final-cand/src-tauri/target/release/bundle/macos/Vysted Terminal.app (227,392 KiB du). Info.plist CFBundleShortVersionString 0.9.0 = CFBundleVersion 0.9.0 = package.json 0.9.0 at the sha; CFBundleIdentifier com.vysted.terminal.
- `shasum -a 256 Contents/MacOS/vysted-terminal` = 87df4f2e8f92145e04770e2c20a8783fe1769cf6bd85e52c7d61d7709d489eb8.
  Bundled sidecars (identical to src-tauri/binaries, i.e. the same binaries the shared stack runs): vysted-sidecar 2b5bfd595d676256f57918ff3ea19082caadc18a23b077f788af9fa4f08760a3; openbb-mcp 326d8d26cffa85c821b9ebfd2f077aa8cd89f71d6e54d836f318d66750ae81d9; sec-edgar-mcp aa91bee70224ba1555b68439a4ffa93cac63364c8c2e415712fe5e2c8bac63b4.
- DMG: .../bundle/dmg/Vysted Terminal_0.9.0_aarch64.dmg, 227,708,098 B, sha256 c0ddc38579fe76b9d80f089a994ece8d3aae1f778bf29859f00ef91a647288b3.
- Unsigned, not notarized (operator-only). Never opened. Install-and-launch check waits for the rig.
- Note: the default `tauri build` target set includes the DMG, whose bundle_dmg.sh mounts an image and lays it out via Finder AppleScript (as in the rc2 build); no app window was opened.
- `git -C $S/final-cand status --short` empty after the build (no tracked changes).
