# rc1-battery-0 working log

Role: REGRESSION BATTERY shard 0 (Sonnet, label `rc1-battery-0`), stage-c batch-2 + batch-10.
Candidate under test: `4c6dfe8c` (rc1-cand worktree). Note: an earlier partial attempt in
this evidence tree had been built against a stale candidate (`4097dac4`) and a mismatched
W-to-set mapping (leftover `set-40`..`set-47`/`set-47` "unplanned-2" content from a
different shard's numbering) — that stale material was not reused; every entry below was
re-run fresh against the correct `4c6dfe8c` candidate and written into the set files that
match THIS shard's exact assigned mapping.

## Setup
- Own sidecar booted from the `rc1-cand` worktree source (candidate `4c6dfe8c`) against a
  copy of `rc1-seed-data` at `rc1-data-rc1-battery-0`, port **52340**, started detached
  (`nohup sh -c 'sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52340
  --data-dir <data-dir>' > <log> 2>&1 &`, sleep-wrapper pid **62288**, python pid **62291**).
  `/health` polled ok throughout. Shared `openbb-mcp :52153` / `sec-edgar-mcp :52154` used
  read-only for MCP-backed routes.
- Reused for all 13 assigned writer sets across both batches; one sidecar for the whole
  shard per role instructions.
- Stopped at the end of the run by killing only the shard's own sleep-wrapper pid (62288/
  62290); confirmed the python process (62291) exited and `/health` now refuses the
  connection.

## Sets completed (13/13)
- `battery/set-0.md` — batch-2/W1-fundamentals-seam: 6/6 holds.
- `battery/set-1.md` — batch-2/W2-instrument-identity: 6/6 holds.
- `battery/set-2.md` — batch-2/W3-research-integrity: 7/7 holds (3 live model calls:
  RESEARCH-001/003 on OpenAI `gpt-4o-mini`, RESEARCH-004 on local `llama3.1:8b` via the
  ollama single-lane lock; 4 in-process code-level checks).
- `battery/set-3.md` — batch-2/W4-workspace-persistence: 1/7 holds (live curl,
  CODE-FRONTEND-004), 6/7 ci_pinned (workspace.ts entries whose original certification
  drove code in-process against a live sidecar — not curl-able; named against the
  committed vitest test per the never-run-vitest-suites rule).
- `battery/set-4.md` — batch-2/W5-surfaces-and-math: 2/8 holds (live/pytest -k backend),
  6/8 ci_pinned (frontend-currency-rendering entries with a named committed vitest pin,
  no HTTP repro). Two backend entries (DATA-009/010/011... DATA-010/011 ultimately
  ci_pinned because their only feasible repro is the pinned pytest itself even though I
  ran it directly — named the exact test, not counted as an independent live repro).
- `battery/set-40.md` — batch-10/W1-runtime-backtest: 7/7 holds (design/code-level, read
  current source + docstrings citing the register id directly for each).
- `battery/set-41.md` — batch-10/W2-catalog-hostactions: 3/4 holds (UI-010 live 422
  validation, LEAD-018 live OpenRouter free-tier no-leaked-thinking check, CODE-PLATFORM-021
  code read), 1/4 ci_pinned (UI-011 BacktestPanel Stop button).
- `battery/set-42.md` — batch-10/W3-fundamentals-bse-cache: 6/6 holds, plus DATA-096 (its
  assigned set is W6/set-45) verified live here and cross-referenced from set-45.
- `battery/set-43.md` — batch-10/W4-screener-routes-statedocs: 6/6 holds.
- `battery/set-44.md` — batch-10/W5-chat-search-workflow: 5/7 holds (live), 2/7 ci_pinned
  (AGENT-082/088 chat-footer/slash-command frontend tests).
- `battery/set-45.md` — batch-10/W6-chart-notes-blueprint: 6/7 holds (5 grep/code-read +
  1 cross-ref to set-42's live DATA-096 run), 1/7 ci_pinned (UI-048 ChartPanel default).
- `battery/set-46.md` — batch-10/W7-panels-marketplace: 6/6 holds (DATA-004 cross-referenced
  to its full live re-run in set-0, same candidate/sidecar, not repeated).
- `battery/set-47.md` — batch-10/W8-plugins-dock: 2/3 holds (CODE-PLATFORM-017 in-process
  asyncio evaluate_code run over the full cert expression set; AGENT-063 in-process
  build_aliases + _tag_symbols over the cert's 4 headlines, no substring false-positive),
  1/3 ci_pinned (CODE-PLATFORM-013 workspace plugin-flag persistence test).

## Totals
80 assigned register-id slots across 13 sets; 1 true duplicate assignment
(R15-DATA-004 appears in both W1 and W7) collapses to 79 unique register ids verified.
62 holds, 17 ci_pinned, 0 regressed, 0 needs_gui, 0 blocked_env.

## Method notes
- Repro method per entry followed the register's own `repro` field: live curl for
  HTTP-shaped repros, in-process python (candidate `.venv`, modules imported directly, no
  pytest runner — except a small number of explicitly targeted `pytest -k` invocations for
  backtest/options math, never the full suite) for code-level repros, grep + source read
  for design-level entries, `vy.py invoke copilot` against my own sidecar for the handful
  of live-model entries (RESEARCH-001/003/004, LEAD-018) under the ollama single-lane lock
  where applicable.
- Never ran a full vitest/pytest suite. An entry whose only original certification method
  was driving frontend TS modules (requiring a jsdom/vitest harness to replicate) is
  `ci_pinned`, naming the exact committed test/describe block + line that now asserts the
  behavior, grepped for presence at the candidate sha, not executed.
- Zero regressions found across all 79 unique entries. No `needs_gui` or `blocked_env`
  outcomes in this shard's assignment.
- Two apparent discrepancies investigated and resolved as non-regressions: R15-DOCS-017's
  sp500 snapshot numbers changed (503/2026-09-24 vs an older cert's 506/2026-06-04) —
  expected, a downstream consequence of R15-LEAD-013's own fix regenerating the universe
  pack, and DOCS-017's own latest certification round already re-pins to the new numbers;
  R15-LEAD-013's screener run appearing to omit BXP/NVR/UDR was a `/screener/run` 200-row
  pagination artifact, not a data-pack defect — confirmed present by reading the raw
  universe JSON directly.
- Coverage: raw probe/output files saved under `battery/raw/set-<n>/<id>.*` for every
  live/in-process entry before judging; grep/code-read-only entries (ci_pinned test-name
  citations, pure source inspections) are recorded inline in the set `.md` table itself
  and not separately duplicated as a raw file where the grep output IS the evidence line.
