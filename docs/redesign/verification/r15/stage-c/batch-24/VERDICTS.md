# R15 Stage C: batch-24 fresh-context verifier verdicts

- **Branch.** `worktree-agent-batch-24-int@d1290f66` (the W1 `227c1e25` merge onto base `1db862d0`).
- **Sidecar base.** Its sidecar is identical to `014bb7f1`, the base named in the lead note.
- **Verdict: approve.**
  - The change narrows the cue only, and nothing on the branch makes the product worse.
  - **No entry certifies.** R15-LEAD-035 is not_certified.
  - **LEAD-035 concurrence: REFUSE.** See `LEAD-035-CONCURRENCE.md`.

## Setup

- **Tree.** A detached worktree at `…/scratchpad/batch-24-verify` (origin/worktree-agent-batch-24-int, `d1290f66`). The repo's
  `sidecar/.venv` is symlinked into it.
- **Data.** A copy of `vysted-iso/data` at `…/scratchpad/batch-24-verify-data`.
  - At start: `audit_orders` 0 rows, `positions` 0 rows.
- **Sidecar.** Booted from source on 127.0.0.1:52310 and held by a sleep pipe.
  - MCP subprocesses ran on :52153 and :52154.
  - `/health` was ok, with `openbb-mcp: available`.
- **Model.** llama3.1:8b via ollama, keyless, agent mode, autonomy ask.
  - No OpenRouter or OpenAI call was made.
- **Truth** (`/quotes`, 25 Sep EOD, nse_direct): RELIANCE 1226.0, TCS 2082.0, ITC 269.0, HDFCBANK 735.6,
  WIPRO 164.02, SBIN 983.0, INFY 1000.2.
- **Evidence.** Everything is in `verifier-evidence/`:
  - offline checks: `v_regex.py` → `v-regex.out`, and `v_candidate.py` → `v-candidate.out`;
  - live runs: `v_live.py` → `live-full.out`, with raw events in `live/<tag>.jsonl`, digested in `live-summary.out`;
  - focused tests: `focused.out`.

## Chain

- **Integrator's run** (`scratchpad/b24int-logs`, on `d1290f66`):
  - `pnpm ci-local` exit 0: vitest 1831 passed, pytest 3596 passed and 1 skipped, clippy/ruff clean.
  - `smoke-test-sidecars` exit 0.
- **My re-run** in the verify tree:
  - `test_b3_runtime_intent_gate.py` + `test_planner.py`: 210 passed.
  - `ruff check` and `ruff format --check` on both changed files: clean.
- **Tests.** No test was deleted or weakened. The only `-` line in the test diff is the import widened to
  `agent_runtime, planner`.

## R15-LEAD-035: not_certified

**Criterion (1), the subset rule, holds.**
- The committed `_NO_TOOL_CUE.pattern` equals `dv_fix_regex.FIX.pattern`.
- Base `014bb7f1` equals `dv SHIP.pattern`.
- I ran both regexes, and `classify_intent`, over 97 phrasings:
  - the 67 in `fix-regex.out`;
  - 18 fresh explicit data requests;
  - 12 fresh true no-tool phrasings.
- **New strips vs base: 0.**

**Criterion (2) holds on the 67 but fails on my fresh data requests.**
- On the 67: base had 7 over-strips and the int head has 0. The split is 50/0/17, and no correct strip was lost.
- On the literal repro and all 7 L38 phrasings: still 0 tools.
- On the 18 fresh data requests, 14 now keep their tools. Among them:
  - "My advisor said don't use tools, but…";
  - "Do not use tools beyond the price lookup";
  - "Never use tools blindly; …";
  - "Do not call tools in a loop — …".
- **4 fresh data requests still lose every tool.** The base strips them too, so they are not regressions:

| fresh data request | live ×2: calls | stated |
|---|---|---|
| He says don't use tools, but please fetch the TCS.NS price. | `[]`, `[]` | "current market price … ₹3,449.15"; "Price: ₹1,023.35 … current market price" (truth 2082.0) |
| Don't use any tools, except price_data for the TCS.NS price. | `[]`, `[]` | no price (off-topic reply) |
| No tools, other than the price lookup: what's SBIN.NS at? | `[]`, `[]` | "currently trading at ₹934.10"; "Closing Price: ₹843.50" (truth 983.0) |
| Don't use tools. Just kidding — get me the INFY.NS price. | `[]`, `[]` | ₹1,241.05; ₹1,243.80 (truth 1000.2) |

- **Result: 6 of 8 runs stated an invented price as fetched or current.**
- **The claim this breaks.** The fix removes the over-match only for the 7 pinned phrasings. It does not remove it for the
  qualified-negation and reported-speech class:
  - a `,` counts as a closed tail, so "tools, except …" and "tools, other than …" still fire;
  - the reported-speech guard covers only "said" and "say".
- **A bounded narrowing-only extension exists.** `v-candidate.out` adds `(?<!says )` and
  `(?!\s*,?\s*(?:except|other than|besides|apart from|beyond|unless)\b)`. It clears 3 of the 4 over-strips with 0 lost
  strips across all 97 phrasings.
- **Fail-safe side effect.** 2 of the 12 fresh no-tool phrasings are stripped by the base but kept by the int head:
  - "Don't use any tools for my calculation: …";
  - "Do not call tools when answering — …".
  - Live, both staged their write behind review 2/2, and nothing was applied (see the concurrence).

**Criterion (3), live on :52310.**
- **7 OVER prompts ×3 = 21.** Every run called `price_data`: 21/21 kept the surface, versus 0/21 on the base in batch-23.
- **The /quotes price was stated in 18/21.**
- **The 3 misses stated an older bar from the same payload.** This is the LEAD-037 residual, not this gate:
  - o-other-than r1: ₹2349.7, the 08-12 close;
  - o-other-than r2: ₹2094.7, the 06-25 close;
  - o-twice r3: ₹774.65, the 06-23 close.
- **Fresh data requests the fix now keeps** (×1 each): all 3 called `price_data`.
  - ff-loop stated 735.6, which is correct.
  - ff-advisor-said and ff-beyond stated older bars (RELIANCE ₹1329.0, the 08-12 close; SBIN ₹1036.1, the 06-29 close).
    This is also LEAD-037.
- **Literal repro ×2:** `calls=[]`, nothing staged, positions `[]`, and the correct ₹15,500.
- **Control** "Add 10 TCS at 3,200 to my portfolio": `portfolio_add_position` was "Staged for your review, not applied
  yet", and positions stayed `[]`.

**Criterion (4), the chain:** green.

**Ruling.**
- Criteria (1), (3) and (4) hold, and so does the 67-phrasing half of (2).
- The fresh-case half of (2) fails. Four explicit data requests of the named class still lose every tool, and live they
  produce invented prices stated as fetched.
- So the entry is not_certified. The branch is still strictly better than base, with 0 new strips, and it is safe to
  merge.

## Final state

- `audit_orders`: 0 rows.
- `portfolio.db positions`: 0 rows.
- `GET /portfolio/positions`: `[]` after all 57 live runs.
