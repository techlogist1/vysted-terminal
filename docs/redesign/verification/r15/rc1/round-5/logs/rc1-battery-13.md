# rc1-battery-13 — gate round 5

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sets: batch-4/W3-chat-runs-mcp
(set-12), batch-2/W3-research-integrity (set-2), batch-11/W4-registry-loop (set-50),
batch-25/W1-opus (set-67).

No prior round-5 files existed for this shard/label (checked
`battery/raw/set-{12,2,50,67}` and `battery/set-{12,2,50,67}.md` — none present; other
labels' set files existed under different set numbers, none of them mine). Started fresh.

## Environment

- Own sidecar :52353, data dir `rc1-round-5-data-rc1-battery-13` (fresh copy of the
  isolated seed data).
- For set-12's LIFECYCLE-005 repro (needs to kill an openbb-mcp child), booted my OWN
  openbb-mcp on :52360 rather than touching the shared :52153 stack, restarted the main
  sidecar pointed at it, ran the kill/probe, then continued using the shared sec-edgar-mcp
  :52154 (read-only, untouched) for the rest of the shard.
- No local-model (Ollama) or hosted-key calls were needed for this shard — every
  R15-AGENT-090-adjacent live-model repro is out of scope for my assigned entries.

## Set-by-set

- **set-12** (9 ids): 5-file vitest run (90/90 passed) covers CODE-FRONTEND-002,
  AGENT-013, AGENT-029, CODE-PLATFORM-037. Combined pytest run (86 passed) covers
  CODE-AGENT-002, DATA-083, DATA-038, DATA-039. LIFECYCLE-005 re-proved live by killing my
  own openbb-mcp child and observing `/openbb-mcp/status` flip to
  `available:false/lastToolCallOk:false/lastError:<populated>` and `/fundamentals` still
  200 (yfinance fall-through), not 500. All hold.
- **set-2** (6 ids): in-process python probe script (`probe_set2.py`) against
  `services/research/{relevance,deep,verify,citecheck,finance}` — no network, no LLM.
  All 6 outputs match the round's certified evidence strings exactly. All hold.
- **set-50** (2 ids): DATA-071 — confirmed cold cache for KARNAVATI.BO in my own
  data_cache.db, then a live `/history/KARNAVATI.BO?range=1y` call: 255 bars, `partial:false`
  (the pre-fix shape was <=8 bars with no partial field at all). LIFECYCLE-026 — ran the
  pinned `test_loop_idle.py` (2/2 passed) plus a live idle-CPU spot sample on my own sidecar
  (~23s window, +0.02s CPU, well under 1%). Both hold.
- **set-67** (1 id): CODE-PLATFORM-013 — this entry stands at two prior certification
  failures per the lead note's three-failure rule; a regression here would be recorded
  not-certified and NOT opened as a fix round. Ran the 5-file vitest set naming this id
  explicitly in each test title (157/157 passed, including all 5 R15-CODE-PLATFORM-013
  tests by name). Holds — the three-failure rule is not triggered this round.

## Findings

None. 0 regressions, 0 new defects, 0 chain failures, 0 gate8, 0 environment across all
18 entries in this shard.

COVERAGE: 18/18 ids raw; no raw: none.
