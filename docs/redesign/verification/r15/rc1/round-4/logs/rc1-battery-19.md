# rc1-battery-19 (regression battery shard 19) — gate round 4

Candidate: `1006c6da694ede5776c3dabbd27b305aeb56b5ad` (verified via `git rev-parse HEAD` in the
shared scratch worktree before starting).

## Rig

- Own sidecar booted from source on `127.0.0.1:52359`, cwd
  `rc1-round-4-cand/sidecar`, data dir `rc1-round-4-data-battery-19` (a fresh `cp -R` of the
  keyless ISO seed snapshot). `VYSTED_OPENBB_MCP_PORT=52153`, `VYSTED_SEC_EDGAR_MCP_PORT=52154`
  pointed at the shared read-only MCP subprocesses. Boot: `sleep 86400 | ./.venv/bin/python3
  main.py --host 127.0.0.1 --port 52359 --data-dir <data>`, sleep-wrapper pid recorded, `/health`
  polled ok (providers list matches the ISO_STACK.md baseline, openbb-mcp available).
- Stopped at the end by killing only that sleep pid (see below), not the shared stack.

## Sets worked (in order)

1. **batch-2/W4-workspace-persistence** (set-3.md, 7 ids). R15-CODE-FRONTEND-004 (sidecar workspace
   name percent-encoding) was re-run live end to end against my own sidecar: 6 names including
   `Research: NVDA`, `Research: M&M`, a path-traversal attempt (`../escape`) and a
   backslash/slash name (`a/b\c`) all saved 200, listed, and landed as percent-encoded filenames
   strictly inside `workspaces/` — no escape. Cleaned up (DELETE all 6, 204 each).
   The other 6 ids (CODE-FRONTEND-001/005/018, LIFECYCLE-002/003/009) are pure frontend TS/Zustand
   logic (`src/lib/workspace.ts`). The candidate worktree is read-only for this role and standing
   up a second writable frontend checkout + `node_modules` symlink (the pattern batch-2's own
   verifier used for its scratch vitest files) was not worth the setup cost for a single shard
   under the stall budget, so each was confirmed by reading the exact fix_shape source lines at
   the candidate sha and naming the already-committed pinned vitest test whose assertion is the
   register entry's original repro (verdict `ci_pinned`, per the task's own carve-out for this
   situation).
2. **batch-9/W5-frontend-shell** (set-39.md, 7 ids). DATA-092 (region hint copy) and UI-052
   (onboarding privacy/web-research copy) are static strings/constants with no branching logic —
   confirmed directly by grep against the shipped source (verdict `holds`, no pinned-test
   dependency needed). The other 5 (UI-016, CODE-FRONTEND-016, UI-086, CROSS-PLATFORM-004,
   UI-058) are frontend dispatch/render/registry logic — same ci_pinned treatment as above, each
   backed by a pinned test whose title is in several cases literally tagged with the register id
   (e.g. `keybindings.test.ts:85` "R15-UI-058: merges over the CURRENT overrides...").
3. **batch-12/W3-…** (set-58.md, 1 id: DATA-068). Pure sidecar behavior, re-run live: `GET
   /fundamentals/AAPL/ratings` twice on `:52359` returned the byte-identical `as_of` both times
   (cache write time, not `now()`); an uncached `MSFT` call got its own fresh stamp. Holds.
4. **unplanned-4** (set-82.md, 1 id: LEAD-043). Re-ran the register's own repro live: `vy.py
   invoke copilot "hi" --provider openai --model gpt-4o-mini --mode agent --autonomy ask
   --no-key --port 52359` and a direct `curl POST /llm/chat` with the same no-key openai request.
   Both returned the humanized `code: "auth"` frame, not the generic internal-error frame. The
   groq leg of the original two-provider repro could not be re-run — this candidate's `vy.py`
   only accepts `{openrouter, openai, deepseek, ollama}` as `--provider` — but the openai leg
   alone independently re-exercises the fixed mechanism (SDK-constructor exception reaching
   `humanize()` before the router's last-resort guard) on both call sites the entry names. Holds.

## Result

16/16 ids covered: 3 holds via live re-run against a fresh sidecar (CODE-FRONTEND-004, DATA-068,
LEAD-043), 2 holds via static source read (DATA-092, UI-052), 11 ci_pinned (frontend TS logic
confirmed by source + a named pinned test). 0 regressed, 0 needs_gui, 0 blocked_env. No new
defects observed outside the register while probing. Findings file is `[]`.

## Stack teardown

Stopped my own sidecar by killing its sleep-wrapper pid only (recorded at boot time). Never
touched the shared `:52152`/`:52153`/`:52154` stack or any other owner's port/data dir. No
LOCAL-MODEL LOCK was needed — LEAD-043's repro is the OpenAI adapter with `--no-key`, never
Ollama.

COVERAGE: 16/16 ids raw; no raw: none.
