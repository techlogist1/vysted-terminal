# RC1 PREFLIGHT log (rc1-preflight, Sonnet)

## 1. Git
- `git fetch origin`: up to date, no new refs.
- Candidate full sha: `4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a` (title: merge(r15): stage C batch 11 - 18 certified fixes at 9985b00e)
- `git merge-base --is-ancestor <cand> origin/004-r4-experience-rebuild` -> yes
- `git merge-base --is-ancestor <cand> 004-r4-experience-rebuild` (local) -> yes
- `origin/004-r4-experience-rebuild` == local `004-r4-experience-rebuild` == `a50c1152ad67fea3345a21699d6f64faf4684f5c`
- `worktree-agent-rc1-*` branches: none found (`git branch -a | grep worktree-agent-rc1`) — this is the first rc1 attempt.
- newest `r15-*` tag: none (`git tag | grep '^r15-'` empty).
- `git worktree list`: ~60 pre-existing agent worktrees from prior batches (unrelated); none for rc1.

## 2. Clean build
- `git worktree add --detach <scratchpad>/rc1-cand 4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a` — succeeded first try, HEAD at 4097dac4.
- `pnpm install --frozen-lockfile` (cwd rc1-cand, detached, log `logs/pnpm-install.log`) — succeeded, "Done in 4.2s" (pnpm store already warm). No errors.
- `node scripts/ensure-all-sidecars.mjs --force` (detached, log `logs/ensure-sidecars.log`) — in progress / see below.

## 3. Seed data
Seeded `<scratchpad>/rc1-seed-data` from `<scratchpad>/vysted-iso/data` (source, not the operator's live profile):
- `sqlite3 '.backup'` for: data_cache, fundamentals_cache, portfolio, plugins, custom_agents, delegate_runs, workflows (all present, all backed up).
- Copied non-sqlite dirs: notes/, workspaces/, searxng/, resolver_masters/.
- `audit_log.db` — NOT copied (per instruction, append-only §6.5 isolated profile starts at zero audit rows).
- Fresh `dev-keystore.json`: `{"secrets": {}, "migrated": true}`, chmod 600.

## 4. Shared stack
- `vysted-iso/pids.json` sleep pids (35151 main, 35093 openbb, 35094 sec-edgar) — all **dead** (checked individually with `ps -p`), ports 52152/52153/52154 free (`lsof -i` empty). Prior session's stack did not survive (machine sleep/restart, consistent with known "lid-close sleep kills the stack" gotcha).
- Action: after this role's own build/sidecar work is verified, boot the shared stack fresh per `r15/stage0/ISO_STACK.md` on `vysted-iso/data` (main sidecar from rc1-cand's `sidecar/`, MCPs from rc1-cand's `src-tauri/binaries/`), record new pids in `pids.json`. See below for status.

## 5. Env
- `ollama list | grep llama3.1` -> `llama3.1:8b  46e0c10c039e  4.9 GB  3 months ago` present.
- `df -h /` -> 133Gi avail / 460Gi total (8% used) — well above the 25GB warn / 10GB block thresholds.
- idle: `ioreg -c IOHIDSystem` HIDIdleTime -> 3s.
- frontmost: `lsappinfo info -only name $(lsappinfo front)` -> "Claude".
- `/search/status` + `/search/searxng/status` on :52152 — pending (stack was down; will probe once own/shared sidecar is confirmed up; NOT starting Docker).

## 6. Register
`python3 scripts/r15/register.py status`:
- raw findings: 887 in 99 files; refuter verdicts: 887 (0 pending)
- register entries: 631 total. counts: critical 16, high 112, medium 282, low 221 (rejections 76)
- status breakdown (from register JSON `entries[].status`): fixed 358, open 233, needs_gui 9, removed_with_feature 14, blocked_tier4 15, not_a_defect 2
- needs_gui ids: R15-CODE-AGENT-001, R15-LIFECYCLE-001, R15-LIFECYCLE-008, R15-UI-009, R15-UI-022, R15-UI-025, R15-UI-050, R15-UI-083, R15-UI-084
- blocked_tier4 ids: R15-AGENT-064, R15-CODE-FRONTEND-013, R15-CODE-PLATFORM-010, R15-CODE-PLATFORM-015, R15-CODE-PLATFORM-071, R15-CODE-PLATFORM-073, R15-CROSS-PLATFORM-001, R15-DOCS-002, R15-DOCS-003, R15-DOCS-015, R15-RELEASE-001, R15-RELEASE-002, R15-RELEASE-003, R15-RELEASE-004, R15-UI-044
- open critical/high/medium ids (26): R15-AGENT-007, R15-AGENT-017, R15-AGENT-049, R15-CODE-AGENT-009, R15-CODE-PLATFORM-023, R15-CODE-PLATFORM-025, R15-CODE-PLATFORM-026, R15-CODE-PLATFORM-027, R15-CODE-PLATFORM-028, R15-DATA-059, R15-DATA-071, R15-DATA-079, R15-DATA-080, R15-LEAD-013, R15-LEAD-028, R15-LIFECYCLE-024, R15-LIFECYCLE-026, R15-RELEASE-005, R15-RELEASE-006, R15-RELEASE-007, R15-UI-047, R15-UI-059, R15-UI-085, R15-UI-087, R15-UI-088, R15-UI-091

## 4 (cont.) Shared stack — booted fresh
Prior sleep pids (35151/35093/35094) all confirmed dead individually via `ps -p` (not `ps -p a -p b -p c`, which errors on macOS with multiple `-p`); ports 52152-52154 free via `lsof -i`. No unlisted process held any of the three ports, so nothing was force-killed.

Booted per `r15/stage0/ISO_STACK.md`, using rc1-cand's freshly-built binaries/source, on the existing (unmodified) `vysted-iso/data`:
- `sleep 86400 | rc1-cand/src-tauri/binaries/vysted-openbb-mcp-sidecar-aarch64-apple-darwin --port 52153` -> sleep pid 57726, worker 57727
- `sleep 86400 | rc1-cand/src-tauri/binaries/vysted-sec-edgar-mcp-sidecar-aarch64-apple-darwin --port 52154` -> sleep pid 57724, worker 57725
- `cd rc1-cand/sidecar; VYSTED_OPENBB_MCP_PORT=52153 VYSTED_SEC_EDGAR_MCP_PORT=52154 sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52152 --data-dir vysted-iso/data` -> sleep pid 57933, worker 57934

New pids recorded in `vysted-iso/pids.json` (sleep/wrapper/worker/ports/candidate_sha/restart_note).

`GET /health` on :52152 -> `{"status":"ok","service":"vysted-sidecar","version":"0.8.0",...,"openbb-mcp":"available","agents_degraded":[]}` — MCP env wiring confirmed working.
`GET /sec/filings/AAPL` -> `422` (validation error, not `501`) — confirms sec-edgar-mcp route is live, matching the stage0 baseline.
openbb/sec-edgar MCP servers have no `/health` route (404, expected — MCP-only surface); `POST /mcp` returns `200 OK` on both per their own logs.

## 5 (cont.) Search env
- `GET /search/status` (:52152) -> `tier: t1_keyless, available: true` (ddg/brave/mojeek all `state: closed`, i.e. not tripped).
- `GET /search/searxng/status` -> `state: degraded` ("SearXNG is running but its search engines are blocked" — brave suspended/too-many-requests, duckduckgo/startpage CAPTCHA), `container: running`, `docker.daemon_running: true`. This is an **upstream/environment** condition (rate-limited/CAPTCHA'd public search engines behind the existing SearXNG container), not touched — no Docker start/stop/restart performed, per the boundary rule. The keyless `t1_keyless` tier itself stays available via the direct-engine fallback.

## Status
**READY.** Clean worktree build (install + all 3 sidecars) succeeded first try, no retries needed. Seed data copied cleanly. Shared stack rebuilt and healthy. No Tier-4 blockers hit during preflight itself. The register's own blocked_tier4/needs_gui entries listed above are pre-existing register state, not preflight blockers.
