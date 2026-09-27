# rc1-battery-4 — regression battery shard 4 (stage-c batch-5/10/11/18)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Own sidecar on `:52344`, data dir
`rc1-round-5-recheck-data-battery-4` (copied from `rc1-round-5-recheck-seed-data`).

## Boot note

Port 52344 was squatting an orphaned Python process (pid 47225, `PPID 1`, started 2:48pm,
data dir `rc1-round-5-data-rc1-battery-4` — no `-recheck`, so a leftover from an earlier
gate round, not this round's evidence). Killed it (orphaned, not a live concurrent owner)
before booting my own sidecar cleanly on the same port. Stopped my own sidecar (sleep pid
65380, worker pid 65385) at the end of the shard.

## Sets covered

- `battery/set-20.md` — batch-5/W5-screener-earnings-sec (10 ids): all holds. R15-DATA-110
  live cold sp500 screen: 502/503 evaluated, 164ms, 0 rate-limited skips (Yahoo currently
  not throttled from this host). R15-CODE-DATA-004 and R15-DATA-028/032/067 confirmed live
  via curl against the sidecar. R15-UI-055/056/045, R15-CODE-DATA-006, R15-LIFECYCLE-017 are
  UI/vitest- or pytest-pinned per their own certification (batch-5 VERDICTS.md) — source-read
  confirms the fix logic is still present; verdict ci_pinned naming the test (never ran
  vitest/pytest myself, per the role's instruction).
- `battery/set-41.md` — batch-10/W2-catalog-hostactions (4 ids): all holds, all via live
  in-process candidate-venv calls or curl (catalog projections, earnings_call_transcript for
  KPITTECH/INFY, a live llama3.1:8b `add_chart_drawing` agent turn, portfolio route 405/404/404/200).
- `battery/set-53.md` — batch-11/W5-data-reference (1 id): R15-LEAD-013 holds — sp500.json
  503 symbols, 0 of 14 named delisted tickers present, BXP/NVR/UDR all present, confirmed
  both statically (candidate worktree file) and live (`GET /screener/universe?id=sp500`).
- `battery/set-66.md` — batch-18/W1-opus (1 id): R15-LEAD-033 holds — live two-turn
  llama3.1:8b run reproducing the entry's own literal repro (AAPL market cap, then "show
  exactly what it returned" with the client-built history trailer). Turn 2's answer contains
  zero `[tool steps` occurrences; the model called tools itself instead of echoing.

## Ollama lock

Three llama3.1:8b calls this shard (R15-AGENT-084 draw, R15-LEAD-033 turn 1, R15-LEAD-033
turn 2), each under its own `mkdir`/trap-`rmdir` lock hold, released before the next
acquisition. One shell-quoting failure on the first turn-2 attempt (options JSON broke on
an apostrophe inside nested single-quotes) — never reached the model, lock released via the
trap on the process's argparse-error exit; retried via a Python-driven subprocess (argv list,
no shell re-quoting) and it succeeded. Noted transient contention with another shard's
concurrent ollama call (rc1-battery-7, port 52347) during the retry — turn 2 took 198s
(vs turn 1's 50s) but completed correctly.

## Result

0 regressions, 0 new defects, 0 chain failures, 0 gate8-relevant findings. 16/16 ids have
raw evidence from this round at this candidate sha.

COVERAGE: 16/16 ids raw; no raw: none.
