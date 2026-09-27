# rc1-drive-screener — working log (gate round 5)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98` confirmed via
`git -C rc1-round-5-cand rev-parse HEAD` before starting.

## Rig

- Own sidecar `127.0.0.1:52322`, source run from `rc1-round-5-cand/sidecar`
  (`VYSTED_OPENBB_MCP_PORT=53322`, `VYSTED_SEC_EDGAR_MCP_PORT=53323`), data dir
  `rc1-round-5-data-rc1-drive-screener` (`cp -R` of `rc1-round-5-seed-data`). `/health` ok,
  `openbb-mcp: available`.
- MCP subprocesses booted detached first (sleep pids 19685 openbb, 19686 sec-edgar), main
  sidecar detached after (sleep pid 20018).
- No pre-existing round-5-labelled screener files were found under
  `docs/redesign/verification/r15/rc1/round-5/`; found `rc1-round-3-data-screener`,
  `rc1-round-4-data-screener`, `rc1-data-rc1-drive-screener`, `pids-screener.json` in the
  scratch dir but none carry `round-5` in the name, so per the harness rule they were left
  untouched and not reused as this round's evidence.
- No Ollama lock was needed — every check in this drive resolved via direct sidecar reads
  (shared `:52152`, GET-only/read-only screener endpoints) or the repo's existing pytest/
  vitest suites; no local-model call was made.

## What I did

1. Read `PROMPT_surface_s2.md`'s screener section, `surface/screener/EVIDENCE.md`,
   `COVERAGE.json`, and `census/refute/surf-screener.json` (the 7 verdicts:
   SURF-SCREENER-1..7, all `admitted`/`admitted_with_correction`).
2. Cross-referenced each raw_id against `vysted-r15-register.json` — all 7 map to entries at
   `fixed` status (R15-UI-055, R15-UI-007, R15-UI-056, R15-UI-006, R15-AGENT-024,
   R15-AGENT-043, R15-DATA-093). None are in the three-failure/blocked_tier4/operator-
   adjudicated classes for this gate round, so this was a pure regression check, not a fix
   round regardless of outcome.
3. For each of the 7, read the current candidate source at the cited file:line, then either:
   - drove it live against the shared read-only stack (`:52152`) when the behaviour is
     server-observable (zero-eval disclosure, matched_count vs result_count cap, custom
     universe bare-ticker resolution), or
   - ran the repo's own pinned regression test (pytest/vitest) when the behaviour is
     client-state-only (preset reset, SSE error-frame handling, dropped-criterion ack, agent
     JSON-string coercion) — every one of these fixes carries an explicit `R15-<ID>` comment
     or docstring citation at the fix site, and a test file/name that pins it by the same id.
4. Ran the full targeted sidecar screener test suite (`test_screener*.py` + `test_b5_screener.py`,
   150 tests) as a broader regression sweep — all passed.
5. Tripped the Yahoo circuit myself (via the india-all limit-cap probe) and immediately re-ran
   the sp500 default screen to catch the "circuit open" condition live; sp500 is warm-cached
   on this candidate so it didn't reproduce a true zero-evaluated run, but the honest-disclosure
   code path and its pinned unit test cover that case directly.
6. Wrote 14 raw evidence files (curl output + vitest/pytest logs) to
   `surface/screener/rc1/round-5/`, the scored table to `rc1/round-5/drives/screener.md`, and
   an empty findings array (nothing regressed, nothing new) to
   `rc1/round-5/findings/rc1-drive-screener.json`.
7. Stopped my own sidecar + MCP subprocesses by killing their sleep pids.

## Outcome

All 7 mapped census findings for this group hold fixed at the candidate. No regression, no
new defect. Full detail and evidence citations in `drives/screener.md`.
