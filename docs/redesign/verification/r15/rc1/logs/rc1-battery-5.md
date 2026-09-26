# rc1-battery-5 working log (RC1 gate round 2)

Role: REGRESSION BATTERY shard 5, lane `battery:shard-5`, candidate `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`.
Own sidecar: one boot for the whole shard, `127.0.0.1:52345`, data dir freshly copied from
`rc1-seed-data` into scratchpad `rc1-data-rc1-battery-5` (never the operator's real app dir).

## Setup

- Found stale round-1 battery files already on disk under the same filenames (set-25..29.md and
  their raw dirs), sourced from a different candidate sha (`4097dac4`) with a completely different
  W-group/entry mapping under the same filenames. Confirmed via `git rev-parse HEAD` in the
  candidate worktree that the current round's sha is `4c6dfe8c...`, distinct from the stale era.
  Discarded/overwrote rather than resuming, and discarded the stale seed-data copy in favor of a
  fresh one.
- Booted sidecar once (`sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52345
  --data-dir .../rc1-data-rc1-battery-5`), reused it for every set in this shard.

## Sets completed (in order)

1. **set-25** (`batch-7/W1-india-exchange-data`, R15-DATA-070..082, 7 ids) — all `holds`. One
   self-caught false alarm on R15-DATA-082: an isolated call to `ccxt_provider._ticker_to_quote`
   looked like a regression (returned 0.0 for a zero-price ticker) but that is not the registered
   repro path; re-tested through `provider_registry.get_quote()` (the actual call path) and the
   outer `correctness_gate.validate_quote` correctly raised `CorrectnessError` — holds. Both probe
   files kept for the record (labeled as such in set-25.md).
2. **set-26** (`batch-7/W2-delegate-runs-runtime`, 10 R15-AGENT-* ids + R15-CODE-AGENT-022) — 3
   `fixed`-status entries (AGENT-060, 062, 074) re-verified live/in-process, still hold; AGENT-064
   is `blocked_tier4` unchanged; the remaining 7 are `open`/`low`, re-confirmed present and
   unchanged (not silently fixed, not worse) — all `holds`.
3. **set-27** (`batch-7/W3-unattended-chart-workspace`, R15-UI-062..080, 10 ids) — all `open`/`low`,
   frontend-only, re-confirmed via source inspection (no vitest re-run, per the role's rules) —
   all `holds` unchanged.
4. **set-28** (`batch-7/W4-research-funnel`, R15-RESEARCH-044..066, 12 ids) — none of these 12 ids
   exist anywhere in the 652-entry register (series stops at -042); exhaustively verified via
   exact-id lookup over `entries[]`/`rejections[]` and a repo-wide grep. Genuine task/register data
   gap, not a product defect. All 12 given `blocked_env`, filed as ONE `environment`-kind finding.
5. **set-29** (`batch-7/W5-agent-writes-portfolio`, R15-UI-082/084/086/088 + 5x
   R15-CODE-PLATFORM-0{34,36,38,40,42}) — UI-086 is a genuine fix (CommandPalette now only shows a
   shortcut chip for a binding that actually fires) — `holds`. UI-084 `needs_gui` (dock-resize drag
   behavior needs a real display). UI-088 `blocked_tier4` (no Playwright/e2e coverage exists,
   unchanged). UI-082 came back BETTER than the register documents on both its sub-issues (clean
   200 for a Unicode workspace name, a readable 400 instead of a raw 500 for an over-long one) —
   flagged as "register status may be stale" rather than mis-labeled as a regression (nothing
   certified got worse). The 5 CODE-PLATFORM entries are `open`/`low`, unchanged, all `holds`.
6. **set-67** (`batch-16/W1`, R15-AGENT-090 + R15-LEAD-030) — see below; the long pole of this
   shard.

## set-67 detail

Live re-run of R15-AGENT-090's certified repro (SIFY ADR-ratio prompt) under the Ollama lock via
`scripts/r15/vy.py invoke copilot ... --provider ollama --model llama3.1:8b --port 52345
--autonomy ask --timeout 120`. Took ~42s model-side; wall-clock polling took much longer
(~3+ minutes of `sleep N`-then-check cycles) because the log file stayed empty until the run's
`done` event actually landed — no separate incident, just normal streaming latency for a
multi-round tool-use turn on a local 8b model.

Result: the model took a DIFFERENT tool path than all 5 of batch-16's certification runs (which
all called `fundamentals` and got a traced answer). Here it called `financial_statements`
(quarterly cashflow, ok), then two invalid-args retries, then stated "one SIFY ADR represents six
ordinary shares" attributed to "the tool call response" generically. The number is factually
correct (SIFY's 20-F: six equity shares) but untraced — the cashflow result has no ADR/depositary
term, so the ratio guard's source-count check should have been empty and the sentence should have
been replaced with `RATIO_UNAVAILABLE`. It was not. Read the guard source
(`_guard_ratio_claims`/`_ratio_claim_traced`/`_sourced_counts` in `agent_runtime.py`) to confirm
this should have fired on the code's own logic; could not inspect the actual raw tool-result JSON
content because `vy.py`'s jsonl/log format only records `ok`/`error`, not the payload, so the
exact mechanism of the miss (vs. e.g. some field in the cashflow JSON happening to satisfy the
source-term regex) is not provable further without deeper live debugging, which is out of scope
for a read-only verification shard.

Cross-checked R15-LEAD-030 (blocked_tier4, per the LEAD NOTE: no fix rounds on this class) by
reading the current tool-citation-guard machinery against batch-16's three documented failure
modes: mode 1 (humanised tool-name regex) looks fixed since batch-16 (`_tool_reference` now
handles "Price Data"/"price-data" style names); mode 3 (ok_tools scoped per-turn causing a
follow-up over-replacement) has a new `_TurnState.cited_tools` field whose docstring names
R15-LEAD-030 directly — looks like an attempted fix, not independently re-verified live this
round; mode 2 (dump-opens-on-next-line) not re-checked live. Used the AGENT-090 escape above as a
fresh, same-class instance (per the standing rule, no separate live LLM run was spent proving a
NEW LEAD-030 escape from scratch) and filed it as a register note under LEAD-030's existing entry.

Both entries verdicted `holds`: AGENT-090's certified fundamentals-calling path was not exercised
or shown broken this run (so `regressed` would be inaccurate and unearned); LEAD-030 remains
accurately `blocked_tier4`. No code changes made anywhere in this shard — pure verification role.

## Findings filed

- `set-28`: one `environment`-kind finding (register/task data gap, 12 non-existent ids).
- `set-67`: one `register_note`-kind finding (new same-class untraced-claim escape, filed under
  R15-LEAD-030 per standing operator policy — not a new defect, not a fix item).

## Cleanup

- Killed this shard's own sidecar (`sleep`-wrapper pid `9555`, sidecar pid `9558`, port `52345`)
  at the end of the run — never touched any other shard's process/port.
- Ollama lock (`/tmp/vysted-r15-ollama.lock`) confirmed released after the AGENT-090 run (the
  `trap ... EXIT` in the launch wrapper released it on the process's normal exit) — verified
  `mkdir`-able / absent before ending the shard, never held past this shard's own work, never
  removed a lock this shard did not hold.

## Coverage

52/52 ids across all 6 sets have raw evidence on disk (7 + 11 + 10 + 12 + 9 + 2 = 51... see note).
Actual count: set-25=7, set-26=10 R15-AGENT-* + 1 R15-CODE-AGENT-022 = 11, set-27=10, set-28=12,
set-29=9, set-67=2. Total = 7+11+10+12+9+2 = 51. Register list for set-26 in the original task text
enumerated R15-AGENT-060 through 078 (even numbers: 060,062,064,066,068,070,072,074,076,078 = 10
ids) plus R15-CODE-AGENT-022 = 11 ids, matching set-26.md's 11-row table. 7+11+10+12+9+2 = 51.
Rechecking the task's set-29 list: R15-UI-082,084,086,088 (4) + R15-CODE-PLATFORM-034,036,038,040,042
(5) = 9, matches. set-25: R15-DATA-070,072,074,076,078,080,082 = 7, matches. set-27: R15-UI-062
through 080 even = 10, matches. set-28: 12, matches. set-67: 2, matches. Total = 7+11+10+12+9+2 = 51.
The task text's own running total said 52 across all 6 sets; recount above yields 51 distinct
register ids — see `results` in the structured output for the exact per-id list this shard
verdicted (one row per id actually assigned, no id invented or dropped to force a round number).
