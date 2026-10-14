# Gate round 3 — fix round 1 integration (rc1-fix-r1-int)

- Base: `01d6920a300b016ab1ad8aa436ee4e4586f8e336`
- Branch: `worktree-agent-rc1-round-3-01d6920-fix-int` (pushed to origin)
- Head: `5ff9be041180c1c316ad48ceb120a23549a7575a`
- Worktree: `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-3-01d6920-fix-int` (left in place)

## Merges (PLAN.md order)

| # | writer branch | head | finding | result |
| --- | --- | --- | --- | --- |
| 1 | `worktree-agent-rc1-round-3-01d6920-fix-r1-W1-adapter-nokey-humanize` | `ac0d8617` | rc1-drive-composer-chat:1 | merged clean (`5ff9be04`), no conflicts |

Diff reviewed against the plan: `client = self._client(api_key)` moved inside the existing `try:` of
`stream_chat` in openai/groq/gemini/anthropic; one `_BODY_RULES` row (any provider/status) mapping
the four SDK no-key messages to `auth`; routers and `error_frame` untouched (AGENT-030 holds). No
later reference to `client` sits outside those `try` blocks. One parametrized test in
`sidecar/tests/test_errors.py` (4 cases). No integration fixes needed. Dropped commits: none.

rc1-drive-research-briefs:1 is deferred per PLAN.md (RESEARCH-043 class, DECISIONS 4.14) — no code.

## Verification (at `5ff9be04`)

| run | log | EXIT | counts |
| --- | --- | --- | --- |
| focused `pytest tests/test_errors.py` | — | 0 | 55 passed |
| ci-local run 1 (ensure step rebuilt all 3 sidecars clean in this worktree) | `ci-local.log` | 0 | vitest 153 files / 1849 tests passed; cargo test ok (19 + 0 + 0); pytest 3649 passed, 1 skipped |
| ci-local run 2 (final) | `ci-local.log` (appended) | 0 | vitest 1849 passed; cargo ok; pytest 3649 passed, 1 skipped |
| `node scripts/smoke-test-sidecars.mjs` | `smoke.log` | 0 | 3 sidecars booted + torn down; /agents 13; /mcp/status ready, 40 tools |

Chain: **pass** (final ci-local and smoke both EXIT 0 at head).

Not done here (verifier's job): the live `vy.py --no-key` recheck for openai/groq.
