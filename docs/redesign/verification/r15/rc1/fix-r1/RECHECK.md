# RC1 fix round 1 (gate round 2): recheck

The rechecker was rc1-fix-r1-recheck (Opus, fresh). The candidate was
`ca6ec990d226bb8a3ba2eb2cc89b5af056a6e19c`, from worktree `scratchpad/rc1-4c6dfe8-fix-int`,
which was used read-only. I ran my own sidecar from that source on `:52336`, with a fresh seed
copy in `scratchpad/rc1-data-rc1-fix-r1-recheck`. The evidence is in `fix-r1/recheck/gr2-*`,
the working log is `../logs/rc1-fix-r1-recheck.md` (gate round 2 section), and the new findings
are in `../findings/rc1-fix-r1-recheck.json`. This file replaces the 25 Sep recheck for
`b0f2b256`, which is in git at `b2cfbb68`.

There was no GUI, so the frontend net was checked by running the candidate's own
`src/lib/brief-ingest.ts` under node type-stripping in a scratch directory. The backend net ran
in-process with the candidate venv.

**Chain status at ca6ec990.** `ci-local.log` shows `CI_EXIT=0` twice (02:51:38Z and
02:58:25Z). `smoke.log` shows `SMOKE_EXIT=0` (02:54:04Z).

| key | repro | observed | verdict |
|---|---|---|---|
| rc1-drive-research-briefs:2 | **Literal repro, in-process.** Ran the finding's tokens through both nets: `[New findings]` (BDL) and `[2, 3]` / `[2, 4]` (Kaynes), plus the triage string. **Literal repro, live on :52336** (gpt-4o-mini, auto, acked through `harness/turn.py`). The exact BDL deep prompt did not call `research`. It was re-run as "Run a deep research brief: Bharat Dynamics — …" (`gr2-1b`). Kaynes ran at ultra, and with "Run an ultra (heavy) research brief: …" (`gr2-3b`). **Fresh live variant:** HAL deep (`gr2-4`). **Fresh class cases, in-process:** range groups `[2-4]`, `[2–4]` and `[7-9]` (5 sources); `[New findings][2]`; `[Web evidence][9]`; ULTRA `_remap_markers` on `[1-2]`. **Adjacent:** the finding's own BDL brief markdown was pushed through the candidate nets (`gr2-original-bdl-brief-through-candidate.txt`), plus `[NSE: BDL]` and `[Note: consolidated]`. | **Literal holds.** In the backend, `[New findings]` is stripped. `[2, 3]` becomes `[2][3]`, and `[6][New findings]` becomes `[6]`. In the frontend, `[New findings]` becomes `[?]` and is counted broken, and `[2, 3]` becomes two chips. **Live:** BDL (31 sources, markers 1/2/18/27), Kaynes ULTRA (25 sources, markers 1-3) and HAL (9 sources) all published cleanly. Citecheck stripped 0 out-of-range markers. No pseudo or group token appeared, so the live runs did not exercise the new rules. **Class NOT fixed:** `[2-4]`, `[2–4]` and out-of-range `[7-9]` ship verbatim in both nets. They are never range-checked, and countBroken is 0. In ULTRA, `[1-2]` keeps the angle-local numbering, while `[1, 2]` remaps to `[3][1]`. `[New findings][2]` ships verbatim, because the `(?![(\[:])` lookahead spares it. `[Web evidence][9]` leaves `[Web evidence]` in the backend and `[Web evidence][?]` in the frontend. **Adjacent breakage:** the pseudo rule matches any bracket token that starts with a letter. On the finding's own BDL brief, the backend deletes `[basis: fraction of price]` and `[basis: trailing 52 weeks]`, which carry the basis disclosure fed by `semantics.py:1290`. The frontend renders both as `[?]` and counts 9 broken citations, 2 of them false. `[NSE: BDL]` and `[Note: consolidated]` are deleted or flagged the same way. | **not certified.** The multi-numeric half is fixed only for `,` and `;`, so range groups still ship unresolved. The pseudo half misses a label that is followed by a marker. The rule also over-matches: it strips basis qualifiers and bracketed prose and flags them as broken citations. Filed as rc1-fix-r1-recheck:1 and rc1-fix-r1-recheck:2. |

## Result

0 fixed, 1 still failing (rc1-drive-research-briefs:2).

The literal tokens `[New findings]` and `[2, 3]` are handled. The title claim does not hold for
the same class written another way:

- A range group such as `[2-4]` still ships as dead text, and in ULTRA it is mis-numbered.
- A pseudo-label followed by a marker still ships as dead text.

The fix also breaks something next to it. Metric basis qualifiers and ordinary bracketed text
are now deleted, or shown as broken citations.

I spent about $0.02 on OpenAI-direct across 5 gpt-4o-mini runs, under the vy.py guard. The
Kaynes client was stopped after its first publish, while it was starting its known second
research round. Own sidecar `:52336` was stopped by killing only its own sleep pid, 68130. The
shared `:52152`-`:52154` stack was not touched.
