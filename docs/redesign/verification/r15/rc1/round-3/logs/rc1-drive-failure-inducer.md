# rc1-drive-failure-inducer log

Candidate HEAD verified: `01d6920a300b016ab1ad8aa436ee4e4586f8e336` (matches RC1 GATE FACTS).

1. Checked `docs/redesign/verification/r15/rc1/round-3/` for prior work under this label:
   none found — first attempt this round.
2. Read `PROMPT_surface_s2.md` OWNER-DRIVE / failure-inducer section, `COMMON.md` (via the
   scope facts embedded in `PROMPT_surface_s2.md`).
3. Read census evidence `docs/redesign/verification/r15/surface/failure-inducer/EVIDENCE.md`
   + `COVERAGE.json` + `_CLAIM.txt` — 5 raw findings (`SURF-FAILURE-INDUCER-1..5`), continued
   past 5 pre-existing induced files (401/no-key/402/network + the 20/21/22/40-44/50-53
   session-2 additions).
4. Cross-referenced the register (`vysted-r15-register.json`) for every entry whose
   `raw_ids` names a `SURF-FAILURE-INDUCER-*` id: all 5 map to entries marked `fixed`
   (R15-AGENT-026, R15-RESEARCH-008, R15-AGENT-025, R15-DATA-061, R15-AGENT-027). None on
   the round's three-failure/adjudicated lists — ordinary fix-round verification applies.
5. Copied `rc1-round-3-seed-data` to `rc1-round-3-data-failure-inducer`, booted own sidecar
   on `127.0.0.1:52327` from the candidate worktree's `sidecar/` (source), sleep pid 89938,
   worker pid 89939. `/health` confirmed ok.
6. Read the candidate's own current code for each fixing entry (`streaming.ts`,
   `openai.py`, `agent_runtime.py`, `oneshot.py`, `errors.py`, `app.py`, `keyless.py`,
   `breaker.py`, `catalog.py`) to confirm each fix's mechanism, not just its register status.
7. Held the Ollama lock (`mkdir /tmp/vysted-r15-ollama.lock`, acquired first try), ran the
   census's exact web_search repro (`vy.py invoke copilot "Use your web_search tool to find
   recent news about Dixon Technologies and cite the sources" --port 52327 --provider ollama
   --model llama3.1:8b`) detached under a `trap … EXIT INT TERM HUP; rmdir` wrapper, polled
   the log in separate short calls. Result: `ok:true`, 62.0s total, DDG's two attempts took
   3.3s (was ~41s), tool_result inside 7s (was a 25s timeout). Lock released on exit,
   confirmed absent afterward.
8. Live-probed `GET /quotes/%20%20%20` (census's own malformed-symbol repro) against BOTH
   the shared read-only `:52152` and my own `:52327` — identical clean `not_found` response
   on both, no raw library text, confirming the DATA-061 global-handler fix.
9. Wrote `surface/failure-inducer/rc1/round-3/EVIDENCE.md` (full method + evidence per
   finding), `rc1/round-3/drives/failure-inducer.md` (scored table + deltas),
   `findings/rc1-drive-failure-inducer.json` (empty — no regression, no new defect), and
   this log.
10. Stopped my sidecar: `kill 89938` (own sleep pid only). Never touched `:52152-54` or any
    other port.

## Outcome

All 5 census raw findings for this group's fixing register entries reproduce as fixed on the
candidate, verified live (web_search timing, malformed-symbol error shape) or by direct code
read of the fix mechanism (stall watchdog, ProviderError global handler, body-aware error
rules, missing-terminator handling) — not by register status alone. No regression. No new
defect. Docker-absent/SearXNG-down honesty and the full 81-row malformed-symbol sweep were
not re-driven this round (no register entry claims a fix there beyond what was already
confirmed) — recorded `NOT TESTED` in the drive summary, not silently skipped.
