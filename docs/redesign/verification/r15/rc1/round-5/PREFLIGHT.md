# RC1 gate round 5 — PREFLIGHT

Role: rc1-preflight (Sonnet, mechanical). Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`.

## (1) Git

```
git fetch origin   # no new refs
git rev-parse 9bc600ece2ce6343a6aa48f130d7620b1466bb98  # OK, resolves, is a commit
git merge-base --is-ancestor 9bc600ec 004-r4-experience-rebuild        -> yes
git merge-base --is-ancestor 9bc600ec origin/004-r4-experience-rebuild -> yes
```

- Local `004-r4-experience-rebuild` HEAD == `origin/004-r4-experience-rebuild` HEAD ==
  `f71b0a12` ("docs(r15): ledger — batch-30 merged, rc1 bar met (0 open c/h/m); gate round 5
  in flight, launch args recorded"). No local/origin divergence.
- Candidate `9bc600ec` is 2 commits behind `004-r4-experience-rebuild`:
  `9bc600ec..004-r4-experience-rebuild` = `f71b0a12`, `c9e34b5c` (both `docs(r15): ledger`
  commits, launch bookkeeping only). Confirmed no diff on the register file between the
  candidate and current branch tip:
  `git diff --stat 9bc600ec 004-r4-experience-rebuild -- docs/redesign/verification/vysted-r15-register.json`
  produced no output (byte-identical).
- `git worktree list`: no pre-existing `rc1-round-5-cand` worktree before this run (created
  fresh below). Found an unrelated worktree `rc1-gate-r5` (branch `worktree-agent-rc1-gate-r5`,
  HEAD `8704a491`, a docs-only commit hardening the round-5 gate script) — not the candidate
  worktree, not this role's, left untouched.
- `worktree-agent-rc1-*` branches present (local + `origin/*`): a long tail from rounds 3/4 —
  `worktree-agent-rc1-4097dac-fix-*` (round-2-era), `worktree-agent-rc1-4c6dfe8-fix-*`,
  `worktree-agent-rc1-gate-r3`, `worktree-agent-rc1-gate-r4`, `worktree-agent-rc1-gate-r5`,
  `worktree-agent-rc1-round-3-01d6920-fix-*`, `worktree-agent-rc1-round-4-1006c6d-fix-*`. None
  named for this round's candidate sha (`9bc600ec`) or this preflight role — nothing to resume
  from for this role.
- Newest `r15-*` tag: **none exists** (`git tag -l "r15-*"` empty). Newest tags overall are
  pre-R15 (`r13-bedrock`, `r12-finisher`, ...) — expected, since no rc1 round has passed yet
  (round 4 FAILed, no tag cut).

## (2) Clean build

```
git worktree add --detach <ISO_SCRATCH>/rc1-round-5-cand 9bc600ece2ce6343a6aa48f130d7620b1466bb98
```
-> `HEAD is now at 9bc600ec`. Fresh worktree, no prior `src-tauri/binaries/` or `sidecar/.venv`
(confirmed empty before build — nothing from a previous attempt of this role in this round).

```
cd <worktree>; nohup sh -c 'pnpm install --frozen-lockfile; echo EXIT=$?' > logs/preflight-install.log 2>&1 &
```
-> `EXIT=0` in ~4s (content-addressed store mostly warm; one ignored build script notice for
`core-js`, non-fatal).

```
nohup sh -c 'node scripts/ensure-all-sidecars.mjs; echo EXIT=$?' > logs/preflight-sidecars-1.log 2>&1 &
```
No competing `ensure-all-sidecars` process was found running in this worktree before starting
(`pgrep -fl ensure-all-sidecars` empty), so this is the only build attempt. Polled via Monitor in
15s-line increments, never in a single >120s call. Final EXIT status recorded below.

**Result: EXIT=0.** All three binaries present at `src-tauri/binaries/`:
`vysted-sidecar-aarch64-apple-darwin` (87M), `vysted-openbb-mcp-sidecar-aarch64-apple-darwin`
(55M), `vysted-sec-edgar-mcp-sidecar-aarch64-apple-darwin` (83M) — main sidecar footprint (87M)
under the ≤120MB target. `sidecar/.venv/bin/python3` present. One benign `WARNING: Hidden
import "jinja2" not found!` during the openbb-mcp build (pre-existing pattern in this build,
not a new fault — jinja2 is present as a runtime dep of a sub-package, PyInstaller's hidden-
import scan just doesn't see it at that hook stage; the binary built and boots clean). Full log:
`logs/preflight-sidecars-1.log`. Total wall time ≈9 minutes (13:12→13:21 IST) — no stale/partial
build reused, this was the only attempt.

## (3) Seed data

Seeded `<ISO_SCRATCH>/rc1-round-5-seed-data` from `<ISO_SCRATCH>/vysted-iso/data` (the already
keyless, already-isolated round-4 profile — never touched the operator's live
`~/Library/Application Support/com.vysted.terminal`):

```
for db in data_cache fundamentals_cache portfolio plugins custom_agents delegate_runs workflows; do
  sqlite3 "file:$SRC/$db.db?mode=ro" ".backup '$DST/$db.db'"
done
cp -R notes resolver_masters searxng workspaces  # into DST
printf '{\n  "secrets": {},\n  "migrated": true\n}\n' > $DST/dev-keystore.json; chmod 600 $DST/dev-keystore.json
```

All 7 `.db` files backed up via `sqlite3 .backup` (WAL-safe read), none dropped. `audit_log.db`
deliberately **not** copied (§6.5: isolated profile starts at zero audit rows). Fresh keyless
`dev-keystore.json` written exactly `{"secrets": {}, "migrated": true}`, mode 600. Verified no
`audit_log*` file present in the destination.

## (4) Shared stack

Found the shared stack still running from the **round-4** candidate (stale — `pids.json`
recorded `candidate_sha: 1006c6da...`, `source_worktree: rc1-round-4-cand`). All 3 listed sleep
pids (48626 main, 48260 openbb-mcp, 48261 sec-edgar-mcp) and their listed worker pids (48629,
48277, 48274) were confirmed running by `ps`/`lsof` before touching anything — matched the
`pids.json` record exactly (no unlisted process on those ports).

Killed the 3 sleep pids first (`kill 48626 48260 48261`); after 15s the worker pids had **not**
self-exited (same pattern the round-4 preflight noted), so they were SIGTERM'd directly
(48629, 48277, 48274) — all three are explicitly listed `worker_pids` in the existing
`pids.json`, never an unlisted or guessed pid. Confirmed ports 52152/52153/52154 fully free via
`lsof` before reboot.

Rebooted from `rc1-round-5-cand` per `ISO_STACK.md`'s exact command pattern, on the existing
`vysted-iso/data` dir (reused as-is, per the task's instruction — this is distinct from
`rc1-round-5-seed-data`, which is the fresh copy handed to owner sidecars):

```
sleep 86400 | src-tauri/binaries/vysted-openbb-mcp-sidecar-...  --port 52153   -> sleep pid 9909
sleep 86400 | src-tauri/binaries/vysted-sec-edgar-mcp-sidecar-... --port 52154 -> sleep pid 9910
(cd sidecar; VYSTED_OPENBB_MCP_PORT=52153 VYSTED_SEC_EDGAR_MCP_PORT=52154
 sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52152 --data-dir $ISO/data) -> sleep pid 9911
```

`GET /health` returned `ok` within ~10s (cold PyInstaller `_MEI` extraction for the two MCP
binaries): `openbb-mcp: available`, `agents_degraded: []`. New pids written to
`vysted-iso/pids.json` (sleep: 9911/9909/9910, worker: 9918/9926/9925, `candidate_sha:
9bc600ec...`, `source_worktree: rc1-round-5-cand`). Noted in passing, not touched: two unrelated
leftover processes on ports 52353/52354 (`rc1-round-4-data-battery-13` /
`rc1-round-4-data-rc1-battery-14`) belong to another role's round-4 battery work, out of scope
for this round and left exactly as found.

## (5) Env

- `ollama list`: `llama3.1:8b` present (`46e0c10c039e`, 4.9GB) — `ollama_llama31: true`. Also
  present: `qwen3:8b`, `qwen2.5:7b` (unused by this round's lane spec).
- `/search/status`: `{"tier":"t1_keyless","available":true,...}` (ddg/brave/mojeek all
  `state: closed`, i.e. not in cooldown).
- `/search/searxng/status`: `{"state":"degraded","detail":"SearXNG is running but its search
  engines are blocked","reason":"brave: Suspended: too many requests; duckduckgo: CAPTCHA;
  startpage: Suspended: CAPTCHA", "container":"running", "docker":{"daemon_running":true}}` —
  the container itself is up and was **not** touched/restarted by this role (never started
  Docker); its upstream engines are currently rate-limited/CAPTCHA'd, an environment condition
  a scenario-lane role should record as `environment`, not a product defect, if it depends on
  live SearXNG results this round.
- `df -h /`: 54Gi available (18% used) — above both the <10GB block and <25GB warn thresholds.
  `disk_free_gb: 54`.
- Idle time: `ioreg -c IOHIDSystem` -> HIDIdleTime ≈ 105109s (~29h) — consistent with "operator
  away", no GUI interaction in progress.
- Frontmost app: `loginwindow` (screen locked/no user session frontmost) — no GUI in play,
  consistent with the no-GUI instruction.

## (6) Register

Read `docs/redesign/verification/vysted-r15-register.json` **directly** (never
`register.py status`) from the candidate worktree. `counts` field: `{"raw": 887, "entries": 679,
"rejections": 76, "critical": 16, "high": 121, "medium": 305, "low": 237}` (severity totals
across all entries, not a status breakdown).

Status breakdown computed from the `entries` list (679 total):

| status | count |
|---|---|
| fixed | 398 |
| open | 215 |
| blocked_tier4 | 35 |
| needs_gui | 11 |
| removed_with_feature | 14 |
| not_a_defect | 6 |

**Open critical/high/medium ids: 0** (empty list) — the rc1 bar (0 open c/h/m) holds at this
candidate, matching the ledger's claim (`f71b0a12`).

**needs_gui (11)**: R15-CODE-AGENT-001, R15-DOCS-024, R15-LIFECYCLE-001, R15-LIFECYCLE-008,
R15-LIFECYCLE-040, R15-UI-009, R15-UI-022, R15-UI-025, R15-UI-050, R15-UI-083, R15-UI-084.

**blocked_tier4 (35)**: R15-AGENT-017, R15-AGENT-019, R15-AGENT-049, R15-AGENT-064,
R15-AGENT-090, R15-CODE-FRONTEND-013, R15-CODE-PLATFORM-010, R15-CODE-PLATFORM-015,
R15-CODE-PLATFORM-063, R15-CODE-PLATFORM-071, R15-CODE-PLATFORM-073, R15-CROSS-PLATFORM-001,
R15-DATA-002, R15-DATA-030, R15-DATA-059, R15-DATA-061, R15-DOCS-002, R15-DOCS-003,
R15-DOCS-008, R15-DOCS-011, R15-DOCS-015, R15-LEAD-030, R15-LEAD-035, R15-LEAD-037,
R15-LEAD-038, R15-RELEASE-001, R15-RELEASE-002, R15-RELEASE-003, R15-RELEASE-004,
R15-RELEASE-012, R15-RESEARCH-007, R15-RESEARCH-043, R15-UI-044, R15-UI-088, R15-UI-090.

This set is consistent with the lead note's DECISIONS-adjudicated ids (4.9-4.21: LEAD-030/035/
037/038, DATA-059, RESEARCH-043, DATA-002, AGENT-019, AGENT-090, RESEARCH-007, DATA-061,
UI-090, DATA-030 all appear here as `blocked_tier4`), plus a further tail of RELEASE-*/DOCS-*/
CODE-PLATFORM-*/CROSS-PLATFORM-* entries not covered by this round's lead note — those are
pre-existing blocked_tier4 classifications from earlier rounds, out of scope for this note.
