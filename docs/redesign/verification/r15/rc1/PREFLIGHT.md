# RC1 PREFLIGHT log (rc1-preflight, this run — candidate 4c6dfe8c)

Note: a prior rc1-preflight attempt exists in this file's earlier form for a **stale**
candidate (`4097dac4`, 297 commits behind). Its worktree (`<scratchpad>/rc1-cand`) and shared
stack pids were confirmed gone (machine slept; pids dead, ports free). This is a clean rebuild
at the current gate-round candidate. `rc1-seed-data` (the keyless isolated-profile snapshot)
was reused as-is — already correctly shaped (no `audit_log.db`, keyless `dev-keystore.json`,
all required `.db` backups + non-sqlite dirs present) — no need to recreate it.

## 1. Git
- `git fetch origin`: no error; local `004-r4-experience-rebuild` == `4c6dfe8c...` (HEAD).
- Candidate full sha: `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2` (docs(r15): batch-24 merged...).
- `git merge-base --is-ancestor <cand> origin/004-r4-experience-rebuild` -> yes (candidate IS
  `origin/004`'s tip, and local tip too).
- `worktree-agent-rc1-*` branches: 8 found, all named `worktree-agent-rc1-4097dac-fix-*` (from
  the prior candidate's fix rounds — stale, unrelated to this build).
- newest `r15-*` tag: none (`git tag -l 'r15-*'` empty).
- `git worktree list`: pre-existing agent worktrees from prior batches (version-0.9.0, palette);
  none for rc1 before this run.

## 2. Clean build
- `git worktree add --detach <scratchpad>/rc1-cand 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2` —
  succeeded first try, HEAD at 4c6dfe8c.
- `pnpm install --frozen-lockfile` (cwd rc1-cand, detached, log `logs/pnpm-install.log`) —
  succeeded, "Done in 4s" (pnpm store warm, lockfile unchanged from the prior candidate — no
  errors, one pre-existing ignored-build-script warning for `core-js`, harmless).
- `node scripts/ensure-all-sidecars.mjs --force` (detached, log `logs/ensure-sidecars.log`) —
  in progress at time of writing; see Status below for final result.

## 3. Seed data
`<scratchpad>/rc1-seed-data` already present and correctly shaped from a prior attempt (same
source `vysted-iso/data`, same recipe as `ISO_STACK.md`):
- `.db` backups present: `custom_agents.db`, `data_cache.db`, `delegate_runs.db`,
  `fundamentals_cache.db`, `plugins.db`, `portfolio.db`, `workflows.db`.
- Non-sqlite dirs: `notes/`, `resolver_masters/`, `searxng/`, `workspaces/`.
- `audit_log.db` — absent (correct, append-only §6.5, isolated profile starts at zero rows).
- `dev-keystore.json` — `{"secrets": {}, "migrated": true}`, present and readable (permissions
  not re-verified byte-for-byte here since the file's content was inspected directly and
  matches the required exact literal).
Reused as-is; not recopied (no reason to touch source-of-truth data unnecessarily).

## 4. Shared stack
Prior pids (57933/57726/57724, from the stale-candidate attempt) all confirmed **dead**
individually via `ps -p`; ports 52152/52153/52154 confirmed **free** via `lsof -i`. Nothing to
force-kill; no unlisted process held any port.

Booted fresh per `r15/stage0/ISO_STACK.md`, using rc1-cand's freshly-built binaries/source, on
`vysted-iso/data` (unmodified): see Status below for pids/ports and `/health` result.

## 5. Env
- `ollama list` -> `llama3.1:8b  46e0c10c039e  4.9 GB  3 months ago` present.
- `df -h /` -> 137Gi avail / 460Gi total (8% used) — well above 25GB warn / 10GB block.
- idle: `ioreg -c IOHIDSystem` HIDIdleTime -> ~4772s (~79 min idle).
- frontmost: `lsappinfo info -only name $(lsappinfo front)` -> "Finder".
- `/search/status` + `/search/searxng/status` on :52152 — pending own sidecar boot; not
  starting Docker regardless of result.

## 6. Register (read directly from JSON, not register.py status)
`docs/redesign/verification/vysted-r15-register.json` at candidate `4c6dfe8c`:
- `counts` field: `{"raw": 887, "entries": 652, "rejections": 76, "critical": 16, "high": 116,
  "medium": 293, "low": 227}`.
- `entries[].status` breakdown: fixed 391, open 205, blocked_tier4 26, removed_with_feature 14,
  needs_gui 11, not_a_defect 5 (total 652).
- **Open critical/high/medium: 0** (matches gate expectation).
- needs_gui ids (11): R15-CODE-AGENT-001, R15-LIFECYCLE-001, R15-LIFECYCLE-008, R15-UI-009,
  R15-UI-022, R15-UI-025, R15-UI-050, R15-UI-083, R15-UI-084, R15-DOCS-024, R15-LIFECYCLE-040.
- blocked_tier4 ids (26): R15-AGENT-017, R15-RELEASE-001, R15-RELEASE-002, R15-RELEASE-003,
  R15-RELEASE-004, R15-AGENT-049, R15-AGENT-064, R15-CODE-FRONTEND-013, R15-CODE-PLATFORM-010,
  R15-CODE-PLATFORM-015, R15-CODE-PLATFORM-071, R15-CODE-PLATFORM-073, R15-CROSS-PLATFORM-001,
  R15-DOCS-002, R15-DOCS-003, R15-DOCS-015, R15-UI-044, R15-UI-088, R15-CODE-PLATFORM-063,
  R15-DOCS-008, R15-DOCS-011, R15-RELEASE-012, R15-LEAD-030, R15-LEAD-035, R15-LEAD-037,
  R15-LEAD-038.
  (Per the lead note: LEAD-030/037/038 are accepted known limitations per DECISIONS 4.9-4.12;
  LEAD-035 is adjudicated to the operator per the three-failure rule, not open, no fix round.)

## 4 (cont.) Shared stack — booted fresh
`node scripts/ensure-all-sidecars.mjs --force` completed clean (all 3 binaries): main sidecar
87M, openbb-mcp 54M, sec-edgar-mcp 83M (all well under the 120MB per-binary footprint target,
and PyInstaller reported "Build complete" / "all sidecars present" for each with no errors —
only benign warnings, e.g. an unused optional `openai` extra for fastmcp sampling handlers, a
missing win32-only ctypes lib on macOS, both expected/harmless).

Booted per `r15/stage0/ISO_STACK.md`, using rc1-cand's freshly-built binaries/source, on the
existing (unmodified) `vysted-iso/data`:
- `sleep 86400 | rc1-cand/src-tauri/binaries/vysted-openbb-mcp-sidecar-aarch64-apple-darwin
  --port 52153` -> sleep/bootloader pid 50588, wrapper pid 50603
- `sleep 86400 | rc1-cand/src-tauri/binaries/vysted-sec-edgar-mcp-sidecar-aarch64-apple-darwin
  --port 52154` -> sleep/bootloader pid 50590, wrapper pid 50602
- `cd rc1-cand/sidecar; VYSTED_OPENBB_MCP_PORT=52153 VYSTED_SEC_EDGAR_MCP_PORT=52154 sleep 86400
  | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52152 --data-dir vysted-iso/data` ->
  sleep/worker pid 50612 (source run — no PyInstaller `_MEI` extraction, up in ~1s per the log
  timestamps: process start 06:11:09, "Uvicorn running" 06:11:27, mostly fundamentals-warm-seed
  work, not cold-boot).

New pids recorded in `vysted-iso/pids.json`.

`GET /health` on :52152 ->
`{"status":"ok","service":"vysted-sidecar","version":"0.8.0",...,"openbb-mcp":"available","agents_degraded":[]}`
— MCP env wiring confirmed working.
`GET /sec/filings/AAPL` -> `422` (validation error, not `501`) — confirms sec-edgar-mcp route
is live, matching the stage0 baseline.

## 5 (cont.) Search env
- `GET /search/status` (:52152) -> `tier: t1_keyless, available: true` (ddg/brave/mojeek all
  `state: closed`, i.e. not tripped).
- `GET /search/searxng/status` -> `state: degraded` ("SearXNG is running but its search engines
  are blocked" — brave suspended/too-many-requests, duckduckgo/startpage CAPTCHA), `container:
  running`, `docker.daemon_running: true`. Pre-existing upstream/environment condition (rate-
  limited/CAPTCHA'd public search engines behind the shared SearXNG container), not touched —
  no Docker start/stop/restart performed. The keyless `t1_keyless` tier stays available via the
  direct-engine fallback.

## Status
**READY.** Clean worktree build (install + all 3 sidecars) succeeded first try, no retries
needed. Seed data (`rc1-seed-data`) reused as-is from a prior correctly-shaped snapshot. Shared
stack rebuilt fresh at the current candidate and healthy. No Tier-4 blockers hit during
preflight itself. The register's own blocked_tier4/needs_gui entries are pre-existing register
state (see §6), not preflight blockers; open critical/high/medium = 0, matching the gate
expectation from the lead note.
