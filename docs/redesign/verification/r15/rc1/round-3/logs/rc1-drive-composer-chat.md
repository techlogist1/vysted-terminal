# rc1-drive-composer-chat — working log

Candidate HEAD confirmed `01d6920a300b016ab1ad8aa436ee4e4586f8e336` at
`/private/tmp/claude-501/.../scratchpad/rc1-round-3-cand`.

1. Data dir: `cp -R rc1-round-3-seed-data -> rc1-round-3-data-composer-chat`.
2. Booted own sidecar on `:52320` from candidate source (`sidecar/main.py`), MCP env pointed
   at the shared read-only `:52153`/`:52154`. Sleep pid 73681, worker 73682. `/health` ok.
3. Read `PROMPT_surface_s2.md` (OWNER-DRIVE, composer-chat group: composer 16 rows + chat-agent
   8 rows) and the census `EVIDENCE.md` for this group (agent B, Opus, 2026-09-23).
4. Cross-referenced every census-found defect in this group against
   `vysted-r15-register.json` — all mapped to entries already `fixed`: R15-AGENT-002 (stop),
   R15-AGENT-019 (intent gate), R15-AGENT-046 (tool-call id), R15-AGENT-093 (schema coercion),
   R15-AGENT-034 (budget floor), R15-CODE-AGENT-010/011 (delegate lifecycle guard + ask_user
   pause plane), R15-LIFECYCLE-013/AGENT-035 (resume model), R15-AGENT-092 (halted-run
   host_actions), R15-CODE-FRONTEND-002 (tab-switch stream drop).
5. Acquired the Ollama lock (`mkdir /tmp/vysted-r15-ollama.lock` — got it on the first try),
   ran the 6-turn multi-turn drive detached (`cc-drive/multiturn.py`, wrapped in a
   `trap rmdir ... EXIT` release), threading history exactly like the composer
   (`options.history`, last-10 turns). Total wall time ~13 min across 6 turns, contended with
   other roles' concurrent Ollama calls observed via `ps aux` (other roles' vy.py invocations
   for research-briefs/screener/scenarios were running in the same window — contention noted,
   not a product defect).
6. Read back every turn's `.jsonl` before scoring (never claimed a result from memory).
7. For the delegate-lifecycle / stop-mid-stream / budget-floor census findings, ran the repo's
   own dedicated regression tests instead of a second paid/local LLM re-drive:
   `test_b3_runtime_cancel.py` (1/1), `test_run_manager.py` (27/27),
   `test_b3_runtime_tool_args.py` (8/8), `test_tool_call_identity.py` (3/3), `test_planner.py`
   (25/25) — all green on the candidate, plus code-read confirmation of each fix's cited lines.
8. Ran the 19-file/190-test vitest batch covering every composer/chat-agent frontend unit
   (`ComposerPlusMenu`, `AgentsRail`, `BudgetConfig`, `streaming`, `message-notices`,
   `composer-collapse`, `mentions`, `slash-commands`, `context-provider`, `chat-markdown`,
   `agent-mode`, `research-depth`, `agent-runs`, `agent-dock`, `chat-pending`, `agent-command`,
   `markdown-stream`, `model-options`, `SuggestionChips`) plus `agent-spaces.test.ts` /
   `research-spaces.test.ts` for R15-CODE-FRONTEND-002 — 21 files, 205 tests, all pass.
9. Probed the no-key error frame directly (matching census's own `20-err-nokey-openai.*`
   repro exactly via `vy.py --no-key`) and found it regressed: the router's last-resort guard
   (hardened by the now-fixed R15-AGENT-030) unconditionally emits a generic "internal error"
   frame for ANY exception reaching it, including a legitimate missing-API-key exception from
   the OpenAI/Groq SDK clients that construct (and can raise) OUTSIDE the adapter's own
   try/except. Confirmed the gap is provider-SDK-specific (OpenAI, Groq eagerly validate;
   Anthropic does not) via an A/B on the identical `/llm/chat` route. Filed as a new_defect.
10. Wrote `COVERAGE.json` (all 24 rows in this group resolved to ok/partial/NEEDS-GUI/NOT
    TESTED, none left bare), `findings/rc1-drive-composer-chat.json` (1 finding),
    `drives/composer-chat.md` (scored table + deltas).
11. Stopped own sidecar (`kill 73681`) and released the data-dir copy in place (left under
    scratch for any later re-check).

No GUI lane used. No trading/broker surface touched (out of scope, D81). No shared port other
than the read-only MCP pair was touched. Did not read `R15_BRIEF*.md` or `r15/local/`.
