# RC1 Gate Round 5-Recheck — PREFLIGHT

Role: rc1-preflight (Sonnet). Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`.

## 1. Git

- `git fetch origin` — no new refs (already current).
- `git cat-file -t 949c3c9fd49d61ecadc9813a8321bcdfd81178bd` → `commit`; committed 2026-09-27 18:31:58 +0530.
- `git merge-base --is-ancestor 949c3c9f... 004-r4-experience-rebuild` → **yes**, both local and `origin/004-r4-experience-rebuild`.
- `origin/004-r4-experience-rebuild` == local `004-r4-experience-rebuild` HEAD == `d96e7d8f6997680a42eaced9c396ab398331135d` (identical, no divergence).
- `git worktree list` — no pre-existing `round-5-recheck` worktree before this run (checked before creating one). No `worktree-agent-rc1-*` branch carrying `round-5-recheck` in its name yet.
- `git tag -l 'r15-*'` → empty, no r15-* tags exist.

## 2. Clean build

- `git worktree add --detach <scratchpad>/rc1-round-5-recheck-cand 949c3c9fd49d61ecadc9813a8321bcdfd81178bd` — succeeded, HEAD confirmed at candidate sha.
- `pnpm install --frozen-lockfile` — log `logs/preflight-install.log` — **EXIT=0** (~5s, lockfile already satisfied by pnpm store; only warning was the standard `core-js` ignored-build-script notice, not a failure).
- `node scripts/ensure-all-sidecars.mjs` (no `--force`) — fresh worktree, `src-tauri/binaries/` did not exist beforehand (no stale binaries to reuse, no prior in-progress build found via `pgrep -fl ensure-all-sidecars`) — started detached, log `logs/preflight-sidecars-1.log`. Status recorded below once the log's `EXIT=` line lands (no time budget; polled in separate short calls per the stall rule).

## 3. Seed data

- Source: `<scratchpad>/vysted-iso/data` (the running round-5 shared-stack data dir).
- Seeded to `<scratchpad>/rc1-round-5-recheck-seed-data` via `sqlite3 '.backup'` per `.db` file: `custom_agents.db`, `data_cache.db`, `delegate_runs.db`, `fundamentals_cache.db`, `plugins.db`, `portfolio.db`, `workflows.db` — all backed up OK.
- `audit_log.db` deliberately **not** seeded (append-only audit log; a fresh isolated profile starts clean per ISOLATION_MAP.md §2.4 / no-audit-log-in-seed instruction).
- Non-sqlite dirs copied: `notes/`, `resolver_masters/`, `searxng/`, `workspaces/`.
- `dev-keystore.json` written fresh as `{"secrets": {}, "migrated": true}`, `chmod 600`.

## 4. Shared stack

Sidecar build (`ensure-all-sidecars.mjs`, no `--force`) — log `logs/preflight-sidecars-1.log` — **EXIT=0**, ~7 min (18:32→18:39; faster than the stated 15-30 min ceiling, pip wheel cache was warm from the same-day round-5 build). All three binaries landed in `src-tauri/binaries/`: `vysted-sidecar-aarch64-apple-darwin` (87M), `vysted-openbb-mcp-sidecar-aarch64-apple-darwin` (55M), `vysted-sec-edgar-mcp-sidecar-aarch64-apple-darwin` (83M) — main sidecar under the 120 MB footprint target.

**Restart anomaly (verified, then resolved):** `pids.json`'s recorded `sleep_pids` (9911/9909/9910) did not exist at all, and ports `52152-52154` were held by a *different*, unlisted set of orphaned processes (PPID 1). Before touching anything, verified via `lsof -p <pid>` that the port-52152 holder's `cwd` was exactly `rc1-round-5-cand/sidecar` — i.e. this was round-5's own shared stack, restarted mid-round (process start time 14:48 IST) by some other round-5 role without ever updating `pids.json`, not an unrelated/foreign process. Round-5's `VERDICT.md`/`ADJUDICATION.md` confirm that gate round closed (adjudication finished 18:18 IST, ~15 min before this restart). This matches the established cross-round pattern already recorded in this same `pids.json`'s own round-4→round-5 `restart_note` (this preflight role tears down the prior round's stack each round). Killed the three confirmed port-holding PIDs directly (SIGTERM; no `-9` needed, all exited cleanly, no live `sleep 86400` was piping into them any more to close instead) and confirmed ports free via `lsof` before rebooting. Unrelated round-5 battery-lane sidecars on other ports (`52344/52346/52347`) were left untouched — out of scope.

Booted fresh from `rc1-round-5-recheck-cand` (candidate `949c3c9f`) per `ISO_STACK.md`'s exact boot commands, on the existing `vysted-iso/data` dir (matches the "Shared stack ... shared READ-ONLY" instruction — this dir is not this role's own seed-data copy, which lives separately at `rc1-round-5-recheck-seed-data`).

- `GET /health` (`:52152`) → `{"status":"ok","service":"vysted-sidecar","version":"0.8.0",...,"openbb-mcp":"available","agents_degraded":[]}`.
- `GET /sec/filings/AAPL` (`:52152`, proxied to `:52154`) → `422` (validation error on params, not `501`) — confirms the sec-edgar-mcp route is live, matching `ISO_STACK.md`'s own precedent for this exact check.
- `GET /search/status` → `{"tier":"t1_keyless","available":true,...}`.
- `GET /search/searxng/status` → `{"state":"degraded","detail":"SearXNG is running but its search engines are blocked","reason":"brave: Suspended...; duckduckgo: CAPTCHA; startpage: Suspended: CAPTCHA",...,"container":"running",...}` — container itself untouched/not restarted, matches the no-Docker-start instruction.
- `pids.json` rewritten with the new sleep/worker pids (42793/42794 main, 42556/42566 openbb, 42558/42573 sec-edgar), new `candidate_sha`, `source_worktree`, and a full `restart_note` recording the anomaly and resolution above.
- `git -C rc1-round-5-recheck-cand rev-parse HEAD` → `949c3c9fd49d61ecadc9813a8321bcdfd81178bd` — confirmed at candidate.

## 5. Env

- `ollama list` → `llama3.1:8b` present (4.9 GB, pulled 4 months ago).
- Disk free: `df -h /` → **11Gi free** (WARN: below the 25 GB warn threshold, above the 10 GB block threshold — not a blocker, noted).
- Idle: `HIDIdleTime` → 0s.
- Frontmost app: Spotify.
- `/search/status` + `/search/searxng/status` on `:52152`: probed post-restart against the recheck candidate's own stack — see §4.

## 6. Register (read directly, not via register.py status)

`docs/redesign/verification/vysted-r15-register.json` at candidate `949c3c9f`, `entries` array (738 total) + `counts` field.

- `counts`: raw 887, entries 738, rejections 76, critical 16, high 123, medium 329, low 270.
- Status breakdown (from `entries[].status`): `fixed` 395, `open` 277, `blocked_tier4` 35, `needs_gui` 11, `removed_with_feature` 14, `not_a_defect` 6. Matches the lead note's stated "fixed 395, open 277" and "35 blocked_tier4".
- Open + severity in {critical, high, medium} (29 ids): R15-AGENT-027, R15-CODE-PLATFORM-072, R15-LEAD-060..083 (block), R15-LIFECYCLE-024, R15-RESEARCH-022, R15-LEAD-116. **R15-LEAD-116 confirmed present** (the known high the lead note names, filed under DECISIONS 4.22 — not a blocker for these lanes, per the lead note).
- `needs_gui` ids (11): R15-CODE-AGENT-001, R15-LIFECYCLE-001, R15-LIFECYCLE-008, R15-UI-009, R15-UI-022, R15-UI-025, R15-UI-050, R15-UI-083, R15-UI-084, R15-DOCS-024, R15-LIFECYCLE-040.
- `blocked_tier4` ids (35): R15-DATA-002, R15-AGENT-017, R15-AGENT-019, R15-AGENT-090, R15-DATA-030, R15-LEAD-030, R15-RELEASE-001..004, R15-RESEARCH-007, R15-UI-090, R15-AGENT-049, R15-AGENT-064, R15-CODE-FRONTEND-013, R15-CODE-PLATFORM-010/015/071/073, R15-CROSS-PLATFORM-001, R15-DATA-059, R15-DATA-061, R15-DOCS-002/003/015, R15-LEAD-035/037/038, R15-RESEARCH-043, R15-UI-044, R15-UI-088, R15-CODE-PLATFORM-063, R15-DOCS-008, R15-DOCS-011, R15-RELEASE-012. Count matches lead note (35, DECISIONS 4.9-4.21 adjudicated).

## Summary

All preflight steps complete: candidate confirmed on `004-r4-experience-rebuild`; clean `pnpm install` + full sidecar build (EXIT=0, all 3 binaries present); seed data backed up; shared stack torn down (round-5 leftover, verified before touching) and rebooted on the recheck candidate with `/health` ok, `openbb-mcp` available, sec-edgar route live, `pids.json` updated; env facts collected (ollama model present, disk 11Gi free — warn band, not block; idle 0s; frontmost Spotify); register read directly and cross-checked against the lead note's stated counts (all matched). **status: ready.** No blockers.
