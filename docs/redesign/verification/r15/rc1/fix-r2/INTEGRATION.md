# RC1 fix round 2 — integration

Integrator: rc1-fix-r2-int (Opus). Branch `worktree-agent-rc1-4097dac-fix-int`, base
`b0f2b256` (round 1 head), head `1d6511c89bb27f1785f7af4d2290983b2852d70a` (pushed to origin).
Worktree `scratchpad/rc1-4097dac-fix-int` (left in place).

## Merges (PLAN.md order, `--no-ff`, no conflicts)

| Merge | Writer branch head | Items |
|---|---|---|
| `fcbc38d9` | W1-statements-currency `d4741bc6` | rc1-scenarios:5 (`d4741bc6`) |
| `3fac7312` | W2-leaked-call-tail `54f28231` | rc1-drive-onboarding-stranger:1 (`54f28231`) |
| `1d6511c8` | W3-overlay-cache `d004d6fd` | rc1-battery-4:1, repeat-run half (`d004d6fd`) |

All three writer branches were based on `b0f2b256` and touched file-disjoint sets that match
PLAN.md. Each diff was read before merge. W2 changed `test_leaked_text_tool_call_is_rescued` to
the fixed behaviour (the rescued call text is now held, so the kinds are `tool_use, done`); its
commit logs why, and `test_leaked_json_for_a_tool_not_offered_stays_text` is unchanged.
Nothing was reverted, dropped or changed by the integrator. There were no integration fixes,
because the first ci-local run was green. Before the full run, the targeted writer suites
(`test_fundamentals_tool`, `test_agent_runtime`, `test_tool_call_rescue`, `test_llm_ollama`,
`test_llm_openai`, `test_b7_exchange_financials`) passed with 180 tests (`targeted.log`).

## Verification (all at `1d6511c8`)

| Gate | Result |
|---|---|
| `pnpm ci-local` run 1 (main sidecar rebuilt as STALE; the two MCP sidecars were current) | **EXIT=0** |
| `node scripts/smoke-test-sidecars.mjs` | **SMOKE_EXIT=0** (02:55:29Z). 3 sidecars booted, 13 agents, MCP ready with 40 tools, openbb + sec-edgar bound, all children torn down |
| `pnpm ci-local` run 2 (final) | **EXIT=0** (02:59:52Z) |

Counts from the final run: vitest has 152 files and 1825 tests passed. cargo test has 19 passed
across 3 suites. pytest has 3150 passed and 1 skipped (the pre-existing skip); round 1 had 3141,
and the 9 new tests are the writers' pins. lint, prettier, tsc, cargo fmt, clippy `-D warnings`
and ruff check/format all passed.

Logs: `ci-local.log` (both runs appended, each ending in an `EXIT=` line), `smoke.log`,
`install.log`, `targeted.log`.

## Carried issues (from PLAN.md, not in any diff)

- rc1-fix-r2-triage:1: the earnings estimate labels WIT's INR-sized revenue estimate as USD.
- The `nse_provider` `_lock` is held across `session.get` and the pacing waits.
- Model-capability limits: llama3.1:8b makes up a price in prose with no call written, and the
  SIFY ADR ratio is fabricated.
- The first-brief half of rc1-battery-4:1 is deferred (DECISIONS_FOR_OPERATOR §4.1).
- W1's commit does not record the sweep PLAN.md asked for, a check that no other `agent_tools`
  tool hands the model statement-size money without its currency. The next round should
  confirm it.
