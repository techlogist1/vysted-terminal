# RC1 Gate Round 3 — PREFLIGHT

## (1) Git

```
git fetch origin
git cat-file -t 01d6920a300b016ab1ad8aa436ee4e4586f8e336   # commit
git merge-base --is-ancestor 01d6920a300b016ab1ad8aa436ee4e4586f8e336 origin/004-r4-experience-rebuild
  -> IS ANCESTOR of origin/004-r4-experience-rebuild
git log --oneline -1 004-r4-experience-rebuild
  -> 01d6920a ... (candidate IS the current tip of local 004-r4-experience-rebuild)
```

Candidate `01d6920a300b016ab1ad8aa436ee4e4586f8e336` is the current HEAD of
`004-r4-experience-rebuild` (both local and origin), confirmed a full 40-char sha via
`git rev-parse`.

`git worktree list` at start showed many pre-existing worktrees from prior batches/gate rounds
(batch-25-int, batch-26-int, gate-r3 @ 6553c92d, rc1-cand @ 4c6dfe8c detached, rc1-4c6dfe8-fix-*,
version-0.9.0*, several `.claude/worktrees/wf_*` from earlier workflow runs) — none of these
were touched; they belong to other rounds/roles.

`worktree-agent-rc1-*` branches present: the round-2 family (`rc1-4097dac-fix-*`, 8 branches)
and the round-(pre-3, candidate 4c6dfe8c) family (`rc1-4c6dfe8-fix-int`,
`rc1-4c6dfe8-fix-r1-W1-citation-marker-grammar`, `rc1-4c6dfe8-fix-r1-W1-citation-pseudo-class`,
`rc1-4c6dfe8-fix-r2-W1-citation-grammar-r2`, `rc1-gate-r3`). None carry a `round-3` label per
this round's harness convention (that convention lives in the evidence-file paths, not branch
names) — left untouched, not this round's to reuse.

No `r15-*` tags exist (`git tag -l "r15-*"` empty).

## (2) Clean build

Built a **new** worktree at the round-3 evidence root (the RC1 GATE FACTS' named path
`rc1-round-3-cand` did not exist yet — this preflight created it):

```
git worktree add --detach <scratch>/rc1-round-3-cand 01d6920a300b016ab1ad8aa436ee4e4586f8e336
git -C <scratch>/rc1-round-3-cand rev-parse HEAD
  -> 01d6920a300b016ab1ad8aa436ee4e4586f8e336   (confirmed)
```

`pnpm install --frozen-lockfile` (detached, `logs/pnpm-install.log`): **PASS**, warm store,
664 packages, `Done in 4.1s`. Only benign notice: `Ignored build scripts: core-js@3.49.0`
(pnpm's default posture, not an error).

`node scripts/ensure-all-sidecars.mjs --force` (detached, `logs/ensure-sidecars.log`, 1600+
lines): **PASS** — `[ensure-all-sidecars] all sidecars present.` All 3 binaries built clean
from empty per-subprocess venvs/caches (Python 3.13.13, PyInstaller 6.20.0):
`sidecar/dist/vysted-sidecar` → `src-tauri/binaries/vysted-sidecar-aarch64-apple-darwin`
(87M), `vysted-openbb-mcp-sidecar-aarch64-apple-darwin` (55M),
`vysted-sec-edgar-mcp-sidecar-aarch64-apple-darwin` (83M) — all under the 120MB main-sidecar
footprint target. Each was dev-signed (`[dev-sign] signed ... as com.vysted.<name>`). No
`FastMCPDeprecationWarning`/`AuthlibDeprecationWarning` or the one benign
"Failed to collect submodules for 'fastmcp.experimental.sampling.handlers'" (optional
`openai` extra) rose to an actual build failure.

## (3) Seed data

Seeded `<scratch>/rc1-round-3-seed-data` from `<scratch>/vysted-iso/data` (this gate round's
existing isolated-profile snapshot, per the RC1 GATE FACTS pointer — not the operator's live
profile):

- `sqlite3 "file:$SRC/$db.db?mode=ro" ".backup ..."` for `data_cache`, `fundamentals_cache`,
  `portfolio`, `plugins`, `custom_agents`, `delegate_runs`, `workflows` — all 7 backed up clean.
- `audit_log.db` — **not copied** (by design, §6.5, isolated profile starts at zero audit rows).
- Non-sqlite files per `ISO_STACK.md`: `workspaces/__autosave__.vysted-workspace`,
  `searxng/settings.yml`, `notes/` (recursive) — copied.
- `dev-keystore.json` seeded fresh: `{"secrets": {}, "migrated": true}`, `chmod 600`.
- `resolver_masters/` (present in the source dir, not in `ISO_STACK.md`'s copy list) —
  deliberately left out, matching the source doc's explicit list.

## (4) Shared stack

Found the **old** shared stack running at `<scratch>/vysted-iso` on candidate `4c6dfe8c`
(the round-3 GATE FACTS's `pids.json` — stale, from an earlier round's boot), listening on
:52152/:52153/:52154. Per rule (4), the sleep pids listed in `pids.json` were killed:
`kill 50612 50588 50590` — all three exited clean, ports freed (`lsof` confirmed empty).

Booted the fresh stack on candidate `01d6920a...` per `ISO_STACK.md`'s exact recipe, reusing
the existing `vysted-iso/data` dir as-is (not recopied — this session's `rc1-round-3-seed-data`
copy for per-role use is separate):

```
cd <rc1-round-3-cand>
sleep 86400 | src-tauri/binaries/vysted-openbb-mcp-sidecar-aarch64-apple-darwin --port 52153 > $ISO/openbb-mcp.log 2>&1 &
sleep 86400 | src-tauri/binaries/vysted-sec-edgar-mcp-sidecar-aarch64-apple-darwin --port 52154 > $ISO/sec-edgar-mcp.log 2>&1 &
cd sidecar
VYSTED_OPENBB_MCP_PORT=52153 VYSTED_SEC_EDGAR_MCP_PORT=52154 \
  sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52152 --data-dir "$DATA" > $ISO/sidecar.log 2>&1 &
```

**stack_ok = true.** All 3 ports bound (main sidecar was near-instant, source boot; the two
onefile MCP binaries took their usual `_MEI` cold-extract, both up within ~25s):

```
GET /health
{"status":"ok","service":"vysted-sidecar","version":"0.8.0",
 "providers":{...,"macro_series":"openbb-mcp","openbb-mcp":"available"},"agents_degraded":[]}

GET /sec/filings/AAPL -> 422   (not 501 -- sec-edgar-mcp wiring confirmed)
```

New pids recorded to `vysted-iso/pids.json` (sleep pids `65402`/`65349`/`65350`, candidate
`01d6920a...`, `restart_note` documenting this preflight's rebuild). Stop with
`kill 65402 65349 65350`.

## (5) Env

- `ollama list`: `qwen3:8b`, `qwen2.5:7b`, **`llama3.1:8b`** present. `ollama_llama31 = true`.
- SearXNG: `docker ps` shows `vysted-searxng` (searxng/searxng) already **Up 3 days** on
  `127.0.0.1:8888` — pre-existing, not started by this session (rule: never start Docker).
  Probed against the fresh candidate sidecar:
  `GET /search/status` → `{"tier":"t1_keyless","available":true,"engines":[ddg,brave,mojeek all "closed"/available]}`.
  `GET /search/searxng/status` → `{"state":"degraded","detail":"SearXNG is running but its
  search engines are blocked","reason":"brave: Suspended: too many requests; duckduckgo:
  CAPTCHA; startpage: Suspended: CAPTCHA", "container":"running", "docker":{"daemon_running":true}}`.
  The container itself is healthy; its upstream engines are currently rate-limited/CAPTCHA'd —
  an **environment** fact (nothing this preflight did), not a product defect. `searxng = "degraded (engines rate-limited/CAPTCHA'd; container healthy)"`.
- `df -h /`: 460Gi total, 108Gi available (10% used) — **well above** the 25GB warn / 10GB
  block thresholds. `disk_free_gb ≈ 108`.
- Idle: `ioreg -c IOHIDSystem` → `HIDIdleTime` ≈ **46886 s** (~13h idle).
- Frontmost app: `lsappinfo` → **Zed**.

## (6) Register

Read `docs/redesign/verification/vysted-r15-register.json` directly at the candidate worktree
(never `register.py status`). Its own `counts` field:

```
{"raw": 887, "entries": 656, "rejections": 76, "critical": 16, "high": 118, "medium": 295, "low": 227}
```

Recomputed status breakdown over the 656 `entries` (`status` field, exact match):

| status | count |
|---|---|
| fixed | 392 |
| open | 205 |
| blocked_tier4 | 29 |
| needs_gui | 11 |
| removed_with_feature | 14 |
| not_a_defect | 5 |

- **Open critical/high/medium** (status exactly `open`, severity in critical/high/medium): **0**
  — all 205 `open` entries are severity `low`. Matches the lead note's expectation.
- **needs_gui** (status exactly `needs_gui`, 11 ids): `R15-CODE-AGENT-001`, `R15-LIFECYCLE-001`,
  `R15-LIFECYCLE-008`, `R15-UI-009`, `R15-UI-022`, `R15-UI-025`, `R15-UI-050`, `R15-UI-083`,
  `R15-UI-084`, `R15-DOCS-024`, `R15-LIFECYCLE-040` — matches the lead note's "11 needs_gui
  entries are operator-attended," not gated on here.
- **blocked_tier4** (29 ids): `R15-DATA-002, R15-AGENT-017, R15-RELEASE-001..004, R15-AGENT-049,
  R15-AGENT-064, R15-CODE-FRONTEND-013, R15-CODE-PLATFORM-010/015/071/073, R15-CROSS-PLATFORM-001,
  R15-DATA-059, R15-DOCS-002/003/015, R15-UI-044, R15-UI-088, R15-CODE-PLATFORM-063,
  R15-DOCS-008/011, R15-RELEASE-012, R15-LEAD-030, R15-LEAD-035, R15-LEAD-037, R15-LEAD-038,
  R15-RESEARCH-043`. Includes the three named in the lead note as adjudicated-to-operator
  (`R15-DATA-002`/DECISIONS 4.15, `R15-DATA-059`/DECISIONS 4.13, `R15-RESEARCH-043`/DECISIONS
  4.14) and the local-model-lane class (`R15-LEAD-030/037/038`/DECISIONS 4.9-4.12) plus
  `R15-LEAD-035` (three-failure stop, DECISIONS 4.10).
