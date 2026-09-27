# rc1-scenarios — gate round 4 working log

Role: AGENT SCENARIO HARNESS. Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`
(verified via `git -C <candidate-worktree> rev-parse HEAD` at start and again at end).
No prior round-4 files existed for this label at start (checked
`docs/redesign/verification/r15/rc1/round-4/{logs,findings,scenarios}` — only `gate8*`
artifacts from another role were present); this is a from-scratch run, nothing to resume.

## Setup

- Copied `rc1-round-4-seed-data` → `rc1-round-4-data-rc1-scenarios` (private copy).
- Booted the main sidecar from the candidate's `sidecar/` source on `127.0.0.1:52311`
  (`VYSTED_OPENBB_MCP_PORT=52153`, `VYSTED_SEC_EDGAR_MCP_PORT=52154`, pointed at the shared
  read-only MCP subprocesses), sleep pid 55499 / worker pid 55502, per
  `docs/redesign/verification/r15/stage0/ISO_STACK.md`'s boot recipe. `/health` ok immediately
  (source boot, no PyInstaller extraction).
- Read `sidecar/services/agent_runtime.py` (host-action ack/read-back pipeline, `options.history`
  coercion for multi-turn), `sidecar/services/agent_tools/{catalog,schemas}.py` (host_action tool
  ids), `sidecar/routers/agents.py` (the ack endpoint this headless harness never calls), and
  cross-referenced `docs/redesign/verification/vysted-r15-register.json` for the named tickers
  (AMAL/SMR/DAL/SIFY/BGNE) before writing a single pass rule.
- Wrote `SCENARIOS.md` pass rules for all 12 scenarios (4/property) BEFORE the first graded run.

## Hosted lane resolution

Key check: both `openrouter` and `openai` resolve in the dev keystore (booleans only, per the
sanctioned in-process `vy._key()` call — never opened/printed the file myself). Probed
`openrouter` on vy.py's default free slug `inclusionai/ling-3.0-flash-vl:free` first: **0 tokens**,
`model_not_found` (OpenRouter 404: "unavailable for free... use this slug instead:
inclusionai/ling-3.0-flash-vl" — note: no `:free` suffix, i.e. the vy.py default itself is stale
against OpenRouter's current catalog). Fell to `openai --model gpt-4o-mini` per the precedence
rule: 28.2s, tool calls worked, tokens returned. **Hosted = openai gpt-4o-mini.**

## Execution

Two Python drivers (`run_hosted.py`, `run_local.py` — both in the scratchpad, not published)
launched detached, polled via `until … ; do sleep …; done` background loops (never a foreground
sleep, never a single tool call blocking past the ~120s guidance) rather than one long call:

- Hosted: 12 scenarios × 3 fresh trials (self-consistency scenarios instead run fresh+fresh+
  in-thread, the in-thread leg building `options.history` from a filler exchange) = 36 calls, all
  `ran`, ~3-30s each. Tag `rc1-round-4-scenarios`, real spend $0.0779 (well under the $0.90 cap;
  checked the tag's ledger spend before every call per the driver's own budget guard).
- Local: 12 scenarios × 1 trial, serialized under the shared Ollama lock (`mkdir
  /tmp/vysted-r15-ollama.lock`, stale check at 20 min, retry every 5s up to 15 min/scenario). Hit
  real contention once (another role's deep-research CG Power drive on port 52321 held the lock
  ~several minutes); all 12 still completed within their own windows — no `lock_timeout` outcome
  was needed this run.

## Own harness bug found and fixed mid-run (not a product defect)

Both drivers initially invoked `scripts/r15/vy.py` **from inside the read-only candidate scratch
worktree** (`rc1-round-4-cand/scripts/r15/vy.py`, `cwd` = that worktree's `sidecar/`'s parent). Since
`vy.py`'s `REPO` constant is computed from its own `__file__`, every ledger write landed on
`rc1-round-4-cand/docs/redesign/verification/r15/spend-ledger.jsonl` — a stray modification to a
worktree I was told to treat read-only — instead of the canonical
`docs/redesign/verification/r15/spend-ledger.jsonl` other roles read for shared budget
coordination. Caught it via `git -C <candidate> status --short` mid-run (unexpected `M` on the
ledger file). Fixed:

1. `git -C <candidate> checkout -- docs/redesign/verification/r15/spend-ledger.jsonl` — reverted
   the candidate worktree back to a clean `git status` (done twice: once after the hosted lane, a
   second time after the still-running local driver re-dirtied it before I'd swapped its `VY`
   path; confirmed `git rev-parse HEAD` unchanged, `1006c6da…`, after each revert).
2. Reconstructed the 36 real hosted (openai) rows from each trial's own `*.stdout.txt` summary
   line (real observed secs/tokens/est — nothing fabricated, all from calls that had already
   actually run and spent real money against the real key) and appended them to the **real**
   ledger with a `note` field explaining the backfill, so the shared $7.50 global / $0.90
   lane-tag caps stay accurate for every other role. The 12 free/ollama local rows were not
   backfilled — `est_usd` is always 0 for `provider=ollama`, so there is no cap impact, and
   reverting the stray copy was sufficient.
3. Confirmed no other file in the candidate worktree was left modified (`git status --short`
   clean; `HEAD` still `1006c6da694ede5776c3dabbd27b305aeb56b5ad`).

All *future* calls after the fix used the real repo's `scripts/r15/vy.py` (byte-identical to the
candidate's copy — diffed to confirm) so this could not recur.

## Grading

Read every trial's raw JSONL (assistant `delta` text reassembled, `tool_use`/`tool_result`
names, and `research_step` `notice` events — the ground-truth "staged/applied/etc" signal) via a
small local summarizer script, plus direct `curl` ground-truth checks against my own sidecar
(e.g. `GET /fundamentals/DAL` to confirm the bare ticker really does resolve to `DAL.BO` /
"Dynamic Archistructures Limited" server-side, before concluding an agent transcript's DAL mix-up
traced to that root cause and not a one-off model error). Full grading tables and pass rules are
in `SCENARIOS.md`. One regression filed (`findings/rc1-scenarios.json`); several skepticism
failures traced to the two register classes the lead note names as adjudicated
(R15-DATA-002, R15-LEAD-030) and recorded as concurrence notes in `SCENARIOS.md` rather than as
fresh findings, per that instruction.

## Teardown

Killed the sidecar's sleep pid (55499); worker (55502) exited on its own shortly after (stdin
close → its own watchdog). Left the candidate worktree exactly as found.
