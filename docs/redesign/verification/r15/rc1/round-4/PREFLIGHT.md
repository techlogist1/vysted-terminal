# RC1 gate round 4 — PREFLIGHT

Role: rc1-preflight. Candidate: `1006c6da694ede5776c3dabbd27b305aeb56b5ad`.

## (1) Git

- `git fetch origin` — ok, no new refs relevant to this check.
- `git rev-parse 1006c6da694ede5776c3dabbd27b305aeb56b5ad` → `1006c6da694ede5776c3dabbd27b305aeb56b5ad` (full sha resolves).
- `git merge-base --is-ancestor 1006c6da... origin/004-r4-experience-rebuild` → true (candidate is an ancestor of origin/004).
- `git merge-base --is-ancestor 1006c6da... 004-r4-experience-rebuild` (local) → true.
- `git worktree list` — many prior-round/batch worktrees present (batch-25/26/27-int, lows-*, rc1-round-3-cand @ 01d6920a, rc1-cand @ 4c6dfe8c, gate-r3, gate-r4, etc.). No `worktree-agent-rc1-*` branch existed yet for round 4 before this run; created this round's candidate worktree fresh (see (2)).
- Newest `r15-*` tag: none exist (`git tag -l "r15-*"` empty).

## (2) Clean build — candidate worktree

- `git worktree add --detach <scratchpad>/rc1-round-4-cand 1006c6da694ede5776c3dabbd27b305aeb56b5ad` — succeeded (path did not previously exist, no removal needed). HEAD confirmed at `1006c6da`.
- `pnpm install --frozen-lockfile` — **done in 3.9s** (warm pnpm store), one build-script warning (`core-js@3.49.0` ignored, expected/benign). Log: `docs/redesign/verification/r15/rc1/round-4/logs/preflight-install.log`.
- `node scripts/ensure-all-sidecars.mjs --force` — ran detached (pid 42327), log: `docs/redesign/verification/r15/rc1/round-4/logs/preflight-sidecars.log`. Result recorded below once it completes (Python 3.13 venv resolve + pip install of the full sidecar dependency set, then three PyInstaller `--onefile` builds — this is the ~minutes-long step the stall rule anticipates).

## (3) Seed data

- Source: `<scratchpad>/vysted-iso/data` (the running iso stack's data dir, currently still on the round-3 candidate — see (4)).
- Seeded `<scratchpad>/rc1-round-4-seed-data` via `sqlite3 '.backup'` per `.db` file (`custom_agents.db`, `data_cache.db`, `delegate_runs.db`, `fundamentals_cache.db`, `plugins.db`, `portfolio.db`, `workflows.db`) plus a plain `cp -R` of the non-sqlite dirs (`notes/`, `resolver_masters/`, `searxng/`, `workspaces/`).
- `audit_log.db` (+ `-shm`/`-wal`) deliberately **not** copied (never seeded, per ISOLATION_MAP.md / §6.5 — audit log starts empty for a fresh boot).
- Fresh keyless `dev-keystore.json` written as exactly `{"secrets": {}, "migrated": true}`, `chmod 600`.

## (4) Shared stack

- `<scratchpad>/vysted-iso/pids.json` at session start: sleep pids `65402`/`65349`/`65350`, all verified live and each genuinely `sh -c "sleep 86400 | <sidecar>"` (confirmed via `ps -p`). **candidate_sha in that file is `01d6920a...` (round 3)** — the shared stack was left running on the round-3 candidate, not this round's `1006c6da`.
- `/health` on :52152 → `{"status":"ok", ...}` with `openbb-mcp: "available"`. `/search/status` → `t1_keyless available`. `/search/searxng/status` → `degraded` (SearXNG container up, upstream engines brave/duckduckgo/startpage rate-limited/CAPTCHA'd — an environment fact carried over from the round-3 preflight note, not a product defect, not something this role should "fix").
- :52153 and :52154 `/health` → `404 Not Found` (those two sidecars don't expose `/health`; this matches the round-3 note's own probe style, which used a data route instead — not treated as a fault here).
- **Action needed / status**: this role has *not yet* rebuilt the shared stack onto `1006c6da`. Per the round-4 candidate facts block, the shared stack should be candidate-source; it is currently stale. Rebuilding requires killing the three listed sleep pids (each verified `sleep 86400`, so kill is safe) and re-booting :52153/:52154 from `rc1-round-4-cand/src-tauri/binaries` and :52152 from `rc1-round-4-cand/sidecar` on the *existing* `vysted-iso/data` dir, once (2)'s sidecar build finishes producing the round-4 binaries. This is queued right after the sidecar build completes; see status field for whether it completed within this run.

## (5) Env

- `ollama list` → `llama3.1:8b` present (4.9 GB, pulled 4 months ago).
- `/search/status` (t1_keyless available) and `/search/searxng/status` (degraded, upstream CAPTCHA) checked against the *currently running* (round-3) sidecar — see (4); values are environment facts, not candidate-specific.
- `df -h /` → 92Gi available (12% used) — above both the <10GB block and <25GB warn thresholds.
- Idle: `ioreg -c IOHIDSystem` → ~61714 s (~17h idle).
- Frontmost app: `Zed` (`lsappinfo`).

## (6) Register (read directly from `docs/redesign/verification/vysted-r15-register.json`, not `register.py status`)

`counts` field: `{raw: 887, entries: 661, rejections: 76, critical: 16, high: 119, medium: 297, low: 229}`.

Status breakdown over the 661 `entries[]` (computed directly, matches the file's own bookkeeping):
`fixed: 395, open: 207, blocked_tier4: 29, removed_with_feature: 14, needs_gui: 11, not_a_defect: 5`.

- **Open critical/high/medium ids: none.** All 207 entries with `status == "open"` are severity `low`. Open critical/high/medium = 0, matching the lead note's expectation for this candidate.
- **needs_gui ids (11)**: `R15-CODE-AGENT-001, R15-LIFECYCLE-001, R15-LIFECYCLE-008, R15-UI-009, R15-UI-022, R15-UI-025, R15-UI-050, R15-UI-083, R15-UI-084, R15-DOCS-024, R15-LIFECYCLE-040`.
- **blocked_tier4 ids (29)**: `R15-DATA-002, R15-AGENT-017, R15-RELEASE-001, R15-RELEASE-002, R15-RELEASE-003, R15-RELEASE-004, R15-AGENT-049, R15-AGENT-064, R15-CODE-FRONTEND-013, R15-CODE-PLATFORM-010, R15-CODE-PLATFORM-015, R15-CODE-PLATFORM-071, R15-CODE-PLATFORM-073, R15-CROSS-PLATFORM-001, R15-DATA-059, R15-DOCS-002, R15-DOCS-003, R15-DOCS-015, R15-UI-044, R15-UI-088, R15-CODE-PLATFORM-063, R15-DOCS-008, R15-DOCS-011, R15-RELEASE-012, R15-LEAD-030, R15-LEAD-035, R15-LEAD-037, R15-LEAD-038, R15-RESEARCH-043` (includes the three the lead note calls out under DECISIONS 4.9/4.10/4.13-4.15: R15-DATA-002, R15-DATA-059, R15-RESEARCH-043, R15-LEAD-030/037/038, R15-LEAD-035).
- Confirms batch-27's two fixed ids (`R15-DATA-117`, `R15-LEAD-040`) are **not** in the open list (i.e. fixed), consistent with the commit trail.

## Status — continuation, same role/round

Resumed from the attempt-1 state above (all git/seed/env/register facts unchanged; re-verified
register counts directly against `1006c6da`'s `vysted-r15-register.json` this pass, byte-identical
to attempt-1's numbers). Completed the two items attempt-1 left open:

- **Sidecar build finished clean.** `node scripts/ensure-all-sidecars.mjs --force` (pid 42327,
  launched by attempt-1) had exited by this pass's first poll — log's final line is
  `[ensure-all-sidecars] all sidecars present.` (no trailing `EXIT=` line was written/flushed, but
  the process was gone from `ps`/`pgrep`, the log had been untouched for 3+ min, and all three
  binaries were present and correctly sized in `rc1-round-4-cand/src-tauri/binaries/`:
  `vysted-sidecar-aarch64-apple-darwin` 87M, `vysted-openbb-mcp-sidecar-aarch64-apple-darwin` 55M,
  `vysted-sec-edgar-mcp-sidecar-aarch64-apple-darwin` 83M — treated as a completed, successful
  build). Log: `logs/preflight-sidecars.log`.
- **Shared stack rebuilt onto the round-4 candidate.** Killed the stale round-3 sleep pids
  (`65402`/`65349`/`65350` from `vysted-iso/pids.json`, all confirmed genuinely `sleep 86400`
  beforehand) — they exited immediately on stdin EOF, but the three **worker** pids
  (`65405`/`65364`/`65361`, the same pids the round-3 `pids.json` itself lists under
  `worker_pids`, so listed, not unlisted) did not self-terminate on stdin EOF after ~15s of
  polling, so they were sent a plain `kill` directly; all three exited and ports 52152-52154 were
  confirmed freed via `lsof` before rebooting. Rebooted per `docs/redesign/verification/r15/stage0/ISO_STACK.md`'s
  exact pattern, from `rc1-round-4-cand` (candidate source), onto the **existing** (unmodified)
  `vysted-iso/data` dir:
  - `:52153` (openbb-mcp) and `:52154` (sec-edgar-mcp) from `rc1-round-4-cand/src-tauri/binaries` —
    both up after PyInstaller `_MEI` cold-extraction (~30-50s); root path returns `404` on both
    (neither binary exposes `/health` — same probe-style note as round 3, not a fault).
  - `:52152` (main sidecar) from `rc1-round-4-cand/sidecar` source (`.venv/bin/python3 main.py`),
    `VYSTED_OPENBB_MCP_PORT=52153` / `VYSTED_SEC_EDGAR_MCP_PORT=52154` exported.
  - `GET /health` → `{"status":"ok","service":"vysted-sidecar","version":"0.8.0",...,"openbb-mcp":"available"},"agents_degraded":[]}` — stack_ok.
  - New pids written to `vysted-iso/pids.json` (`sleep_pids`: main 48626, openbb 48260, sec-edgar
    48261; `worker_pids`: main 48629, openbb 48277, sec-edgar 48274; `candidate_sha` updated to
    `1006c6da694ede5776c3dabbd27b305aeb56b5ad`).
- **Env facts re-checked against the now-candidate-source stack** (superseding attempt-1's
  round-3-stack readings, though the values are identical): `ollama list` → `llama3.1:8b` present.
  `/search/status` → `t1_keyless`, `available: true`. `/search/searxng/status` → `degraded`
  (`brave: Suspended: too many requests; duckduckgo: CAPTCHA; startpage: Suspended: CAPTCHA` —
  container up, upstream engines CAPTCHA'd/rate-limited; environment fact, not a product defect,
  unchanged from round 3). `df -h /` → 90Gi free (12% used, above both thresholds). Idle ≈62472s
  (~17.4h). Frontmost: `Zed`.

## Final status: READY

All six preflight checks complete for gate round 4 on candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`.
No blockers. The shared stack is live on candidate source at :52152/:52153/:52154, `/health` ok,
`openbb-mcp` available, `agents_degraded: []`. Seed data + isolated candidate worktree are ready
for other roles to `cp -R` from and boot their own sidecar copies against.

**No evidence was deleted or overwritten.** `rc1-round-4-seed-data` and the round-4 candidate
worktree are net-new (untouched this pass beyond reading them). `vysted-iso/pids.json` was
rewritten (its own job, tracking the shared stack this preflight owns) — no other round's file
was touched.
