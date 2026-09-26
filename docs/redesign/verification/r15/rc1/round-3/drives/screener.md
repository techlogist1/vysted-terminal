# Owner-drive: screener — gate round 3 (candidate 01d6920a)

Worker: rc1-drive-screener (Sonnet). Candidate sha `01d6920a300b016ab1ad8aa436ee4e4586f8e336`
(verified `git rev-parse HEAD` before driving). Own sidecar `127.0.0.1:52322`, source run from
`rc1-round-3-cand/sidecar`, data dir `rc1-round-3-data-screener` (cp -R of the seed data),
sleep pid 72201 (stopped at end of drive). Reads against the shared read-only stack
`127.0.0.1:52152`; the one host-action write (agent screener authoring) against my own sidecar
under the shared Ollama lock.

Frontend/sidecar screener source (`src/store/screener.ts`, `src/modules/screener/*`,
`sidecar/routers/screener.py`, `sidecar/services/screener*.py`) is **byte-identical** between
the candidate worktree and the main worktree HEAD (`69b6eda1`) — only `.pyc` mtimes differ — so
code citations below are file:line accurate against the candidate.

## Census → RC1 deltas

| # | Census (2026-09-23) | RC1 round-3 result | Score | Register id |
|---|---|---|---|---|
| 1 | Panel-default sp500 screen: 0/506 evaluated, all `rate_limited`, `partial:false` | `01-run-default-sp500.json`: 497/503 evaluated, 3 rows, real skip reasons (`not_found`/`missing_field`), `partial:false` correctly means "nothing unevaluated", `throttled:true` still surfaced honestly | **ok — regression fix holds** | R15-DATA-110, R15-UI-055 |
| 2 | Preset click over a stale nested-group+formula ran the OLD tree, presented as the preset | Code-read: `ScreenerPresets.tsx:126-140` `apply()` omits `group`; `screener.ts:349-364 applyFilters` then resets `group:null, advanced:false` for any omitted group — old tree can no longer survive a preset click | **ok — fix holds** | R15-UI-007 |
| 3 | SSE `error` frame discarded; panel showed "Stream ended without a result frame" | Code-read: `screener.ts:551-554` `processFrame` on `event==="error"` sets `serverError = frame.message` and the finish path (`600-604`) surfaces it directly — the discard path no longer reachable when the server actually sends an error frame | **ok — fix holds** | R15-UI-056 |
| 4 | `result_count` (200 vs 1000) silently WAS the match count, not the page | `04a/04b-india-wide-limit*.json`: `matched_count:2799` identical at both limits; `result_count` is honestly the page (200 / 1000) | **ok — fix holds** | R15-UI-006 |
| 5/6 | Agent `write_screener_filters` sent `criteria` as a JSON **string**; host action applied nothing, model claimed success | Code-read: `sidecar/services/agent_runtime.py:946-983 _normalise_tool_args` runs on EVERY tool_use before the frontend ever sees it, JSON-parses an `array`/`object`-typed arg sent as a string (`_coerce`, docstring names `write_screener_filters.criteria` explicitly), at every schema depth. Live re-drive (`python3 scripts/r15/vy.py invoke copilot 'Set up a screener on the NSE full market: P/E below 20, ROE above 15% and debt to equity under 0.5, then run it.' --port 52322 --provider ollama --model llama3.1:8b`, 228.5s, under the Ollama lock): model emitted `write_screener_filters` with `criteria` as a well-formed 3-item array (all 3 leaves present, ROE not dropped) and the host action returned `ok:true`, staged for review with an honest "Staged for your review, not applied yet" notice (no false "already applied" claim) | **ok — fix holds (code-confirmed for the string-arg path; live run additionally confirms the array path + no silent-drop + honest staging copy)** | R15-AGENT-024, R15-AGENT-043 |
| formula grammar | 39-formula parity, zero drift | `02`/`03`-formula-validate: caret position (col 21 on `%`) and the 29-field unknown-field list both match census exactly | **ok — unchanged** | — |
| bonus | `min(pe < 5, roe) > 0.5` boolean-coercion validated OK and ran a meaningless screen (COD-screener-6-adjacent, "known, not re-filed" in census) | `/screener/formula/validate` now returns `ok:false`, `"min() needs a numeric argument, not a boolean expression — wrap the comparison on its own, or combine with 'and'/'or'"` | **newly fixed** (not tracked as its own register id; consistent with R15-RESEARCH-025 "fixed") | R15-RESEARCH-025 |
| unchanged known limitation | `pe_ratio / 0 > 1` silently 0 matches, no skip | `09-formula-div-zero.json`: still 0 matches; the 1 skip present is unrelated (`TATAMOTORS.NS rate_limited`), not a div-zero skip | not re-driven as a defect (census logged this "known, not re-filed") | — |
| region default | sp500-only default, India region ignored | `GET /screener/default-universe` → `{"universe":"nifty50"}` on both the shared and my own sidecar | **ok — fix holds** | R15-CODE-DATA-004 |
| bare Indian tickers vs `.NS` store | all 5 skipped `rate_limited` while circuit open (census finding 7) | `12-custom-bare.json`: 5/5 evaluated live, 0 skipped, circuit was closed at drive time (shared stack `open:false`) — could not re-force the open-circuit leg without tripping the shared stack's breaker, which is out of scope for an owner-drive read lane; code path (`screener_universes` `.NS` custom-symbol resolution) unchanged from census | **ok (best-effort; circuit state not reproducible read-only)** | R15-DATA-093 |
| saved screens session-only | never rode the workspace blob | `src/lib/workspace.ts:170-171,553-563` — `savedScreens` is now a workspace field with a read/restore/subscribe wiring identical to every other persisted slice | **ok — fix holds** | R15-CODE-FRONTEND-018 |
| existing unit suite | 4 files / 41 tests | `pnpm vitest run src/modules/screener src/store/screener.test.ts` on the candidate worktree: **6 files / 87 tests, all passed** (`screener-vitest2.log`) | **ok — grew, no regression** | chain check |

Universe picker (`sp500`/`nifty50`/`crypto-top50`/`nse-all`/`bse-all`/`india-all`, `custom`→400,
bogus→422), limit validation (1001→422), zero-result screen, OR-group run, and a real nse-all
sector+mcap screen were all re-driven and match census behaviour — no deltas, no findings.

## Not re-driven this round (unchanged from census, no regression signal)

Row-click drill, CSV download, column-resize (all `NEEDS-GUI`, per Stage B / this gate's GUI
skip); mid-run cancel (SSE-cancel semantics unchanged in code, not re-timed this round).

## Findings

**None.** Every census-scored `broken`/`partial` interaction in this group maps to a register
entry with status `fixed`, and every one re-verified live or by exact code citation on the
candidate sha still holds. One formerly-accepted quirk (boolean-coercion in `min`/`max`) is now
also rejected at validate time, a strict improvement not attributable to a single tracked id.
No regression, no new defect, no chain failure (vitest green), no gate-8-relevant surface here
(screener never touches order/broker paths).
