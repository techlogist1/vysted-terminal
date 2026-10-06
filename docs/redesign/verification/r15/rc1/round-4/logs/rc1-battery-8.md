# rc1-battery-8 — regression battery shard 8 (batch-4/W3-chat-runs-mcp + batch-6/W3-unattended-platform-chart + batch-25/W3-lead-028-data-064)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad` verified at start (matched).

## Stack

Own isolated sidecar on `:52348`, own openbb-mcp on `:52349`, own sec-edgar-mcp on `:52350`,
data dir `rc1-round-4-data-rc1-battery-8` (copy of the keyless seed profile). Never touched the
shared `:52152/52153/52154` stack or another owner's port.

Gotcha hit twice this shard, noted for future roles: killing the `sh -c "sleep 86400 | <binary>"`
wrapper's own PID does **not** kill the piped binary — it becomes an orphan and keeps serving.
Verified with `ps aux | grep <port>` after each "kill" and killed the real worker PID directly
both times (once for my own openbb-mcp during the LIFECYCLE-005 repro, once for my own main
sidecar during teardown). Stack fully down at end — confirmed `curl` on all three ports refused.

## Method per entry

For each id: read the register entry (repro + evidence), read how the batch verifier certified
it (`stage-c/batch-{4,6,25}/VERDICTS.md`, "Per-entry evidence"), then re-ran the ORIGINAL repro:

- Where the batch used a **permanent** vitest/pytest file (grep confirmed it still exists and
  still names the id or the exact behaviour) — ran only that file (never the full suite) →
  ci_pinned.
- Where the batch used a **scratch** file explicitly marked "not kept" (batch-6's
  `zz-b6v-verify.test.tsx` for AGENT-052/AGENT-051/CODE-FRONTEND-015/UI-021) — did not try to
  resurrect the scratch file; instead (a) read the current source at the exact lines the register
  and the batch verdict named, to confirm the class of fix is still in the code, and (b) located
  the closest **permanent** pinned test for the same behaviour (all four turned out to have one)
  and ran it.
- Where the batch used a live curl/API repro (LIFECYCLE-005, DATA-064, LEAD-028) — re-ran the
  same curl repro against my own live sidecar.

## Set-12 (batch-4/W3-chat-runs-mcp) — 9/9 hold

All ci_pinned or live-holds. See `battery/set-12.md`. Combined pytest (mcp_client +
openbb_mcp_provider + sec_filings_provider): 84 passed. Combined vitest (research-spaces +
agent-spaces + ChatSidebar, then delegate-runs + streaming): 57 + 33 = 90 passed.

LIFECYCLE-005 re-run live end to end: killed my openbb-mcp worker for real, `/openbb-mcp/status`
flipped to `available:false, lastToolCallOk:false, lastError` naming the ConnectError (was
`true/null` on base), and `/fundamentals/KPITTECH` returned 200 falling through to yfinance
(was a 500 on base). Both halves of the fix hold live.

## Set-22 (batch-6/W3-unattended-platform-chart) — 5/5 hold

LEAD-012 re-checked with the EXACT repro condition still present on this machine (`python3` on
PATH is 3.14.5, matching "Homebrew moved python3 to 3.14"); `resolveBuildPython()` still resolves
`python3.13` live. AGENT-052/AGENT-051/CODE-FRONTEND-015/UI-021: code read confirmed the fix
(dockview-id-keyed bus sources, one `focusedSymbolFromBus` derivation, `focused_chart` picked by
matching id not `charts[0]`) plus permanent pinned tests, all green (66 + 51 + 2 = 119 tests
across vitest/pytest). See `battery/set-22.md`.

## Set-72 (batch-25/W3-lead-028-data-064) — 2/2 hold

Live GETs against my own sidecar. DATA-064: RELIANCE.NS 30m/1y returns 767 bars with
`coverage_start:"2026-07-06"` — an exact match to the batch-25 cert numbers; `/indicators/SPY`
30m now 200 (was 502). LEAD-028 (a lead-note three-failure-list entry — holds cleanly here, no
regression to flag): 506597.BO/544774.BO scrip-code addressing resolves on fundamentals, income,
quotes, history, matching the batch-25 evidence verbatim. See `battery/set-72.md`.

## Result

16/16 entries hold. Zero regressions, zero new defects found in this shard.

COVERAGE: 16/16 ids raw; no raw: none.
