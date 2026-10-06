# Owner-drive: screener — RC1 gate round 4

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar `127.0.0.1:52322`, source
run from the round-4 candidate worktree, data dir copied from `rc1-round-4-seed-data`
(keyless), MCP env pointed at the shared read-only `openbb-mcp:52153`/`sec-edgar-mcp:52154`.
Reads for the universe/screener endpoints went to my own sidecar (writes-capable, isolated
data); no writes touched the shared `:52152` stack. Yahoo circuit was **open** on this IP for
the whole drive (`00-provider-health.txt`) — same standing condition the census documented.

Method: re-drove the census's `EVIDENCE.md`/`COVERAGE.json` findings 1, 2, 4, 5/6, 7 plus the
region-default-universe and workspace-persistence fixes, cross-checked against the register's
`fixed` entries for `screener`. Read `src/store/screener.ts`, `src/modules/screener/*.tsx`,
`src/lib/host-actions.ts`, `sidecar/routers/screener.py`, `sidecar/services/agent_runtime.py`
before driving, per the task's "read the panel code and api.ts first" instruction.

## Scored table

| # | Drive | Result | Score | Raw file |
|---|---|---|---|---|
| 1 | Universe picker, all 6 catalogued universes | 200 for all 6, sp500 503 / nifty50 50 / crypto-top50 50 / nse-all 3,506 / bse-all 5,042 / india-all 5,891 (minor drift from census's 506/2,675/4,873/5,156 — consistent with LEAD-013's constituent-list refresh, not itself re-checked) | ok | `08-universe-list.txt` |
| 2 | Default screen (region-aware default now **nifty50**, not sp500) | `GET /screener/default-universe` → `{"universe":"nifty50"}` (region=IN seed); `ScreenerPanel.tsx:134` wires `adoptRegionDefaultUniverse` via `useRetryOnSidecarReady` | ok — **R15-CODE-DATA-004 fixed, confirmed live + code** | `01-default-universe.txt` |
| 3 | Same default criteria (P/E<20, mcap>1e11, sector=Technology) run on nifty50, circuit open | 4 rows, 49/50 evaluated, `partial:true`, `throttled:true`, honest coverage `"screened 49 of 50 — 1 unavailable · 1 rows on stale/snapshot basis"` | **ok — census finding 1 (0-of-506, `partial:false`) FIXED**; census's own default (sp500) no longer even reached — regional default routes around it | `02-default-screen-stream.txt` |
| 4 | Genuinely empty result (nifty50, 0<P/E<0.5) | 0 rows, 49 evaluated, `partial:false`, "No rows matched" true-when-true | ok (unchanged from census) | `07-zero-result-response.json` |
| 5 | Malformed formula (`pe < 20 and roe > 15%`) | `{"ok":false,"error":"unexpected character '%'","position":20}` | ok (byte-identical to census S3) | `04-malformed-formula-response.json` |
| 6 | Custom universe, 5 bare Indian tickers, no `.NS`, circuit open | evaluated_count 5, skipped 0, all resolved to `*.NS`, all live | **ok — census finding 7 / R15-DATA-093 FIXED**, and better than the census's own fix (didn't need the circuit closed) | `03-custom-bare-request.txt` / `03-custom-bare-response.json` |
| 7 | india-all, 0<P/E<40, limit 200 vs limit 1000 | Both return a **separate** `matched_count:2799`; `result_count` is 200/1000 respectively (the true page size, not silently presented as the match count); `ScreenerResultsTable.tsx:489-513` renders both with a truncation note | **ok — census finding 4 / R15-UI-006 FIXED**, confirmed API + render code | `05-out-limit-200.json` / `05-out-limit-1000.json` |
| 8 | Stream error frame → panel message (R15-UI-056) | Not re-induced live (would need a forced engine crash); code-read confirms `screener.ts:551-553` now threads `frame.message` into `serverError`, a path distinct from the `"Stream ended without a result frame"` fallback, with a comment citing R15-UI-056 | ok (code-read only) | n/a — code citation in COVERAGE.json |
| 9 | Preset applied over a nested-group + formula draft (R15-UI-007) | Not re-driven through jsdom; code-read confirms `ScreenerPresets.tsx` `apply()` now explicitly resets `group: null, formula: ""` before applying, with a comment citing R15-UI-007 and describing the exact old bug | ok (code-read only, pure sync state assignment — low regression risk) | n/a — code citation |
| 10 | Saved screens persistence (COD-workspace-layout-6 / R15-CODE-FRONTEND-018) | `src/lib/workspace.ts:553-563` now has a `savedScreens` field wired into `serializeWorkspace`/`deserializeWorkspace`/`onChange` subscribe — was session-only before | ok (code-read) | n/a — code citation |
| 11 | Agent-authored screen, local llama3.1:8b, `--autonomy ask` (default), exact census prompt | Model called `write_screener_filters` with a proper **array** criteria (not the census JSON-string bug); `roe` as `{min:15,max:100}` (odd shape but schema-coerced, `ok:true`); narrated correctly as "proposed... for review" | **ok — census finding 5/6 / R15-AGENT-024/043/CODE-FRONTEND-009/010 FIXED**; root-caused to `agent_runtime.py:945-965 _normalise_tool_args`, which now runs before every adapter (Ollama included) and coerces a stringified array/object arg when its parsed type matches the schema | `06-agent-screen-llama.jsonl` |
| 12 | Same prompt, `--autonomy auto` | Tool call again well-formed (`roe: 0.15, value_type: "fraction"` — a clean leaf this time), `ok:true`. Model's narration: "sent to the panel for review. I will wait for your confirmation or rejection... before proceeding" | **broken — new_defect rc1-drive-screener:1**: AUTO dispatches (agent_runtime's own stub says `status:"dispatched"`, note says verify-don't-claim-done) but the model tells the user it needs their manual accept — the exact framing `copilot.json`'s system prompt forbids | `06b-agent-screen-llama-auto.jsonl` |
| 13 | Existing screener unit tests | Not re-run this round (out of drive scope — `pnpm ci-local`/vitest is the chain-gate lane's job, not owner-drive's); census's `23-existing-screener-tests.log` (41/41 pass) not re-verified | NOT TESTED | n/a |

NEEDS-GUI (unchanged from census, not re-driven): row-click drill-down (`openCompanyOverview`/
`loadSymbolIntoChart` need a mounted dockview), CSV download (`WLD-T-2`), column-resize/overflow
at narrow width.

## Census → RC1 deltas

- Finding 1 (zero-evaluated default screen, `partial:false`, no throttle badge) — **FIXED**,
  and the region-aware default (nifty50) means the sp500-throttle collapse census hit by
  default is no longer even the first thing a fresh IN-region user sees.
- Finding 2 (preset rides old nested group + formula) — **FIXED** (code-read).
- Finding 3 (stream error frame discarded) — **FIXED** (code-read).
- Finding 4 (200-row page cap presented as the match count) — **FIXED**, confirmed live with a
  distinct `matched_count` field and a render-side truncation note.
- Finding 5/6 (agent-authored screen: JSON-string criteria dropped, ROE leaf silently vanishes,
  `run:true` narrated but never runs, `save_screen` files the wrong filters) — **FIXED**, root
  cause traced to a shared runtime coercion function used by every LLM adapter.
- Finding 7 (bare Indian tickers on a throttled IP) — **FIXED**, and stronger than the original
  fix (works with the circuit still open).
- COD-workspace-layout-6 (saved screens never in the workspace blob) — **FIXED**.
- **New**: rc1-drive-screener:1 — AUTO-autonomy narration/mode mismatch on `write_screener_filters`
  (see findings file). Not a regression of anything census/register scored — new surface (the
  AUTO-mode agent-authoring path) census's transcripts didn't drive for this group.
- No regressions found: every census-`ok`/`partial` row re-driven this round held.

## Scope notes

- `TATAMOTORS.NS` intermittently comes back `not_found`/`rate_limited`/`timeout` across
  different screener runs this round — consistent with the shared Yahoo-throttle condition
  documented in the census (`EVIDENCE.md`'s "this IS the owner's normal condition on this
  machine"); itemized honestly every time (never a silent drop), not filed as a new defect.
- Formula-grammar parity (39-formula matrix), agent-context/panel publish rows, and the
  full existing-test suite were not re-driven this round (unchanged surface, no register
  entry pointed at a regression there, and re-deriving them was explicitly out of scope
  per the task's "cross-check ... before re-deriving").

## Evidence files

All under `docs/redesign/verification/r15/surface/screener/rc1/round-4/`:
`00-provider-health.txt`, `01-default-universe.txt`, `01b-settings.txt`,
`02-default-screen-request.txt`, `02-default-screen-stream.txt`,
`03-custom-bare-request.txt`, `03-custom-bare-response.json`,
`04-malformed-formula-request.txt`, `04-malformed-formula-response.json`,
`05-limit-200-request.txt`, `05-limit-1000-request.txt`, `05-out-limit-200.json`,
`05-out-limit-1000.json`, `06-agent-screen-llama.jsonl`, `06-agent-screen-llama.stdout.txt`,
`06b-agent-screen-llama-auto.jsonl`, `06b-agent-screen-llama-auto.stdout.txt`,
`07-zero-result-request.txt`, `07-zero-result-response.json`, `08-universe-list.json`,
`08-universe-list.txt`, and `COVERAGE.json` in the same directory.
