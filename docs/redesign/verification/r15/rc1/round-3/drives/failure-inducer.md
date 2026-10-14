# rc1-drive-failure-inducer — gate round 3

Candidate `01d6920a300b016ab1ad8aa436ee4e4586f8e336`. Own sidecar `:52327` (sleep pid 89938),
data dir a fresh `cp -R` of `rc1-round-3-seed-data`. Full method/evidence in
`docs/redesign/verification/r15/surface/failure-inducer/rc1/round-3/EVIDENCE.md`; this file
is the scored table + census→rc1 delta the harness asks for.

Census baseline: `docs/redesign/verification/r15/surface/failure-inducer/EVIDENCE.md` — 5 raw
findings, `SURF-FAILURE-INDUCER-1..5`, all merged into register entries marked `fixed`
(R15-AGENT-026, R15-RESEARCH-008, R15-AGENT-025, R15-DATA-061, R15-AGENT-027). None of the
five are on this round's three-failure or adjudicated (blocked_tier4) lists.

## Scored table

| # | inducer class | census score | fixing entry | rc1 round-3 score | evidence |
|---|---|---|---|---|---|
| 1 | silent truncated/empty/max_tokens stream shown as complete | broken/silent | R15-AGENT-026 | **ok** | `openai.py:780-784` no fabricated done; `streaming.ts:373-383` `STREAM_ENDED_EARLY`; `isLengthFinish`/`LENGTH_NOTICE` both paths |
| 2 | keyless web_search timeout (DDG-first burns the 25s budget before Brave) | broken/silent | R15-RESEARCH-008 | **ok** | live: DDG 202→202 in 3.3s, Mojeek 200 immediately, tool `ok:true` in ~7s (`research008-vy-transcript.txt`) |
| 3 | provider accepts, never streams — silent spinner, no watchdog | broken/silent | R15-AGENT-025 | **ok** | `oneshot.py` `timeout=`/`asyncio.wait_for`; `streaming.ts` stall watchdog, 45s/330s budgets, `STREAM_STALLED` |
| 4 | data-route raw library text, kind dropped | misleading | R15-DATA-061 | **ok** | live: `/quotes/%20%20%20` on shared `:52152` AND own `:52327` both return clean `{"code":"not_found",...}`, no `AttributeError`; single global `app.py` exception handler, not per-route |
| 5 | nonsense/retired slug → generic "try again" (retry can't help) | misleading | R15-AGENT-027 | **ok** | `errors.py` `_BODY_RULES` `model_not_found` branch ahead of the status-only fallback |
| — | Docker absent / SearXNG down (Settings honesty) | honest | (no fix claimed) | NOT TESTED | unchanged code path this candidate's diff doesn't touch; not re-probed to avoid a second shared-env Docker read this round |
| — | malformed-symbol 81-row sweep / typo-history | mixed, already registered | (DATA-061 covers the AttributeError half) | NOT TESTED (beyond the one repro above) | no register entry claims a fix outside DATA-061's kind-aware handler, already live-confirmed |

## Census → rc1 deltas

All 5 census-broken/misleading states that had a fixing register entry now score **ok**,
confirmed live or by direct code read against the candidate's actual source (not the register
status field alone). Zero regressions found: nothing that was `ok`/honest in the census came
back `broken`/`partial` on this candidate. One phrasing observation (not filed): on a genuine
zero-result web_search, the local llama3.1:8b model's own final answer said "web search is
degraded" rather than "found nothing for this query" — the tool itself returned `ok:true`
with an empty result set (a valid outcome per `keyless.py`'s `any_engine_answered` logic), so
this is model narration, not a silent/misleading app defect, and not filed as a finding.

Sidecar stopped: `kill 89938` (own sleep pid only). Ollama lock released via the `trap …
EXIT` wrapper on the vy.py call, confirmed absent after.
