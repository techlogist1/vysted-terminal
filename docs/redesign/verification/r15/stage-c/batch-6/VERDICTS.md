# R15 Stage C: Batch 6 Verdicts (fresh-context verifier) — RECONSTRUCTED

**Reconstructed after a harness kill — not written live by the verifier.** The
batch-6 fresh-context verifier (Opus) was killed by a harness watchdog at
08:25:18Z, ~15 min after it wrote `VERDICTS.json` (08:09:32Z) but before writing
this evidence file. `VERDICTS.json` is the verifier's own file, authoritative
for the verdict lists. This file is rebuilt from its transcript
(`agent-a412b7dfbfd173653.jsonl`, the first attempt, ~2 MB, the one that wrote
the JSON; under `.../subagents/workflows/wf_94ccf2b8-e97/`). Five restarts of
the same role exist alongside it (a9fbe09556e858e49, a7c19fcbd988843ab,
a057ffe55e98095d2, ab1397ac5d505d791, a138667eacad31330); all five were
interrupted within 15–40 min during re-orientation (re-fetching the branch,
re-reading `VERDICTS.json`/`PLAN.md`) and reached no new gate runs or entry
tests, so nothing from them is used here. Where the transcript has no
observation for a certified id, that is stated plainly rather than invented.

- **Merge target:** `worktree-agent-batch-6-int@4c9f75168bc2bec141ca1d7e3c74710bf7070dc7`
  (base `bc03be5`, batch 5 merged).
- **Verifier:** Opus, fresh context, from the running app and the outside world.

## Rig

- Scratch worktree `batch-6-verify` at `origin/worktree-agent-batch-6-int`
  (`git worktree add ... origin/worktree-agent-batch-6-int`, detached HEAD at
  `4c9f751`). `node_modules` was **symlinked** from the main repo checkout, not
  freshly installed (`ln -s .../vysted-terminal/node_modules $W/node_modules`).
- Data dir `batch-6-verify-data`, copied from the session's `vysted-iso/data` ISO
  stack (never the operator's live data dir or keychain).
- Primary sidecar: built from source, `127.0.0.1:52310`, stdin held by a sleep pipe.
- Second sidecar: the **frozen `--onefile` binary**, `127.0.0.1:52311`, from a
  clean `node scripts/ensure-sidecar.mjs --force` build kicked off deliberately
  with bare `python3` on PATH resolving to 3.14.5 (Homebrew's default at the time)
  — the exact R15-LEAD-012 repro condition.
- Models: local `llama3.1:8b` via Ollama for agent-side/live-deixis entries;
  `nvidia`/OpenRouter free-tier lanes (`inclusionai/ling-3.0-flash-vl:free`,
  `meta-llama/llama-3.3-70b-instruct:free`) tried as a cross-check for AGENT-051
  and were inconclusive (one errored with empty output, the other honestly
  refused to fabricate a ticker from a malformed test context) — llama3.1:8b with
  a corrected context shape is the entry's real evidence.

## Chain observed at the target

The verifier never reached a full green chain confirmation before being killed.
What it actually ran and saw:

| Gate | Result |
| ---- | ------ |
| `pnpm exec vitest run` (full suite) | **125 files, 1517 tests passed, EXIT 0** |
| `tsc` (typecheck) | EXIT 0 |
| `eslint .` (lint) | EXIT 0 |
| `prettier --check` (format:check) | "All matched files use Prettier code style!", EXIT 0 |
| `ruff check sidecar` | "All checks passed!" |
| `ruff format --check sidecar` | "403 files already formatted" |
| `pytest` (sidecar, full suite) | **Started twice; never observed to completion.** First attempt used `-n auto` and errored (`pytest-xdist` not installed, EXIT 4 — not a real result). Rerun without `-n` was launched as a background job; the only progress check (07:21:32Z) showed it at 68% with no failures printed up to that point. No later check-in exists in the transcript, so no final pass/fail count was ever recorded by this verifier. |
| `cargo fmt` / `cargo clippy` / `cargo test` | **Never run** in this transcript. |
| LEAD-001-style clean-venv build of all three sidecars (`openbb-mcp`, `sec-edgar-mcp`) | **Not run.** Only the **main** sidecar binary was clean-built (see LEAD-012 below); `openbb-mcp`/`sec-edgar-mcp` binaries were never built or smoke-tested in this attempt. |
| `node scripts/smoke-test-sidecars.mjs` | **Never run.** |

This is materially incomplete relative to prior batches' chain sign-off. The
per-entry live evidence below stands on its own regardless.

---

## Certified (21)

### R15-DATA-017 — NSE Emerge (SME) corporate disclosures
Fix: `sidecar/services/nse_provider.py` adds `_corporate_index(bare)`, routing
Emerge/SME symbols to `index=sme` (was hard-coded `index=equities`, which NSE
answers with an empty list for SME names) and historicalOR to series `["SM"]`.
Live against the target sidecar (`:52310`):
- `QUALIANCE announcements -> 200`, 4 rows (real headlines: "Resignation of Mrs
  KRUPA RAJESH BADANI...", etc.), `shareholding -> 200` (promoter 63.66%),
  `results -> 200 events 0`.
- `SHANTIINOR announcements -> 200`, 2 rows; `shareholding -> 200` (promoter
  56.05%); `results -> 200 events 0`.
- Cross-checked QUALIANCE's app rows directly against NSE's own `index=sme` feed
  via a raw `curl_cffi` probe (Chrome impersonation): dates/categories/headlines
  match exactly for the first 4 of NSE's 7 SME announcements.
- Direct NSE probe (`index=sme` vs `index=equities`) confirmed the mechanism for
  all three names: SUMAX sme=7/equities=0, QUALIANCE sme=7/equities=0,
  SHANTIINOR sme=2/equities=0.
- SUMAX itself 502'd at the exact test moment (`nse_direct: cookie warm-up
  failed ... Recv failure: Connection reset by peer`) — a live NSE transport
  flake at that instant, not the SME-index bug (the direct probe run seconds
  later against the same NSE endpoint succeeded and returned SUMAX's 7 rows).

### R15-LEAD-012 — pin sidecar build venvs to Python 3.13
Fix: `scripts/build-python.mjs` `resolveBuildPython()`/`ensureBuildVenv()` force
the build venv onto 3.13 regardless of what bare `python3` resolves to.
Live: the verifier's own Mac had `python3 -> 3.14.5` (Homebrew moved it — the
exact repro condition) and `python3.13 -> 3.13.13`.
- A stale test venv created on 3.14 was fed through `ensureBuildVenv`:
  `[build-python] .../b6v-venvtest/v is Python 3.14, recreating on 3.13.` →
  `after: Python 3.13.13`.
- A full clean `node scripts/ensure-sidecar.mjs --force` build was run with that
  same PATH (bare `python3`=3.14.5): the build log shows
  `[ensure-sidecar] $ python3.13 -m venv ".../batch-6-verify/sidecar/.venv"`
  and PyInstaller's own banner `49 INFO: Python: 3.13.13`, ending
  `Build complete!`. The resulting frozen binary was then run live on `:52311`
  and used as the frozen-binary leg of the CODE-PLATFORM-018 probe below.

### R15-CODE-RESEARCH-002 — isolate the snapshot cross-check legs
Fix (mechanism inferred from live behavior; diff not separately captured in the
transcript): `services/research/fast.snapshot_structured`'s `asyncio.gather` over
the cross-check legs (`growth_check`, `ownership_check`, `earnings_quality`,
`range_check`, `market_cap_witness`) now isolates failures instead of letting
one leg's exception crash the whole snapshot.
Live: monkeypatched `growth_check.should_cross_check` to raise synchronously and
`dividend_history.get_dividend_ttm` / `market_cap_witness.get_market_cap_witness`
to raise `RuntimeError` asynchronously, then called `snapshot_structured(...,
"RELIANCE", region="IN")` against the real sidecar. Confirmed hits:
`injected hits: ['async', 'sync', 'async']` (all 3 injected faults fired). Result
shape was unchanged from the baseline call: `ok keys: ['derived', 'fundamentals',
'price'] | price ok: True` in both the baseline and the injected run — no crash,
no escaped exception.

### R15-RESEARCH-017 — ULTRA's heavy loop falls back like DEEP
Fix: `services/agent_tools/deep_research.py` `_run_loop` now wraps
`iter_research.run_heavy_research(...)` in `try/except Exception` and falls back
to `_single_pass_fallback(deep, query, common, loop="heavy")`, matching DEEP's
existing fallback.
Live: `b6v_ultra.py fault` mode monkeypatched `disclosures.gather_floor` to raise
`RuntimeError("b6v injected: heavy prologue gather_floor failed")` on its first
call, then ran a real ULTRA `run_deep_brief("Research Kaynes Technology...",
depth="ultra", wall_seconds=300)` against `:52310` with local llama3.1:8b.
Result: `{"mode": "fault", "secs": 194, "ok": true, "loop": "heavy", "note":
"heavy loop raised; the single-pass deep fallback ran", "n_sources": 14,
"n_filing_sources": 5}` — the injected exception was caught and the run degraded
honestly to the single-pass fallback with a typed note, exactly as the fix
intends.

### R15-RESEARCH-018 — India filings sub-questions never query EDGAR
Fix: bucket routing in `services/research/deep._run_researcher` is now
region-aware and the "SEC" filings match is word-bounded.
Live (`b6v_bucket.py`, real `resolve_target` + `deep._run_researcher` calls):
- `KAYNES IN | "What do recent SEC filings and insider trades show?" -> tools
  ['corporate_announcements', 'web_search']` (not `sec_filings_list`).
- `KAYNES IN | "What is the sector outlook for electronics manufacturing?" ->
  tools ['news', 'web_search']` ("sector" no longer false-matches the bare "sec"
  substring).
- `KAYNES IN | "Is there a second-quarter guidance change?" -> tools
  ['corporate_announcements', 'news', 'web_search']` ("second" doesn't
  false-match either).
- Control case: `AAPL US | "What do recent SEC filings..." -> tools
  ['sec_filings_list', 'web_search']` — US targets are unaffected.

### R15-RESEARCH-012 — disclosures floor ranks the results filing first
Fix: `services/research/disclosures.gather_floor`'s citable `rows` are now
results-ranked, not raw-newest-first.
Live (`b6v_floor.py`, real `resolve_target` + `disclosures.gather_floor` against
`:52310`):
- Kaynes Technology (KAYNES): 50 announcements, results-shaped headlines sit at
  raw positions `[15, 21, 22, 26, 32]`, yet the floor's top-3 citable `rows` are
  the corrigendum-to-results and "Financial Results For The Quarter Ended 30
  June 2026" items — pulled to the front.
- CG Power (CGPOWER): results-shaped headlines at raw positions `[34, 38]`; the
  top rows returned are the board-meeting/results items, not the newest
  attachment.
- Jonjua Overseas (JONJUA): 47 announcements, results-shaped at `[0, 9, 10, 12,
  18]`; floor rows lead with "Outcome Of Board Meeting Dated 18-09-2026" and
  "Unaudited Financial Results For Quarter Ended 30-06-2026" (raw position 9).

### R15-RESEARCH-016 — ULTRA explorers cite the pre-seeded filings floor
Fix: the guard in `services/research/iter.py` that gated pulling the floor no
longer also gates recording it as a citation.
Live: `b6v_ultra.py floor` mode ran a real ULTRA `run_deep_brief("Research
Jonjua Overseas (BSE-listed micro-cap)...", depth="ultra", wall_seconds=300)`.
Result: `{"mode": "floor", "secs": 377, "ok": true, "loop": "heavy", "n_sources":
15, "n_filing_sources": 5, "filing_sources": ["Outcome Of Board Meeting Dated
18-09-2026.", "Unaudited Financial Results For Quarter Ended 30-06-2026.",
"Board Meeting Outcome for Unaudited Financial Results...", "Board Meeting
Intimation for 30 June 2026 Unaudited Financial Results...", "Board Meeting
Outcome for Outcome Of Board Meeting For Bonus, AGM..."]}` — 5 floor rows
recorded as `[n]` sources, where the pre-fix behavior recorded 0.

### R15-LEAD-014 — reject a schema echo in the tool-arg repair round
Fix: `services/llm/openai.py` `OpenAIProvider._repair_tool_args` /
`_validate_tool_args` now reject a repair reply that is the JSON Schema itself
echoed back.
Live (`b6v_repair.py` against the real `TOOL_SCHEMAS` + `OpenAIProvider`):
- `tools with no required keys: 8 | full echo validates as args (pre-fix hole):
  8` — all 8 such tools were vulnerable to the schema-echo hole before the fix.
- `echo accepted after fix: []` — none leak through post-fix.
- `fenced echo -> None`, `prose echo -> None` (a ```json-fenced echo and a
  prose-wrapped echo are both rejected too).
- Legit args still pass: `legit news args -> {'symbols': ['AAPL']}`.
- This closes the exact hole batch-5's verifier flagged as issue #9
  ("Tool-arg repair accepted a JSON-schema echo from the model as args").

### R15-CODE-FRONTEND-012 — stop syncing agent writes to the write-only sidecar ledger
Commit `f37543d`: `host-actions.ts` no longer POST/PUT/DELETEs
`/portfolio/positions` on an agent write (holding ids are `h-<uuid>`, so
PUT/DELETE hit the bare collection route and silently 405'd, while POSTs
accumulated in a ledger no surface ever read). Portfolio writes now land in the
store only; the workspace blob is the documented authority. Diff:
`sidecar/routers/portfolio.py` (14 lines), `src/lib/host-actions.ts` (83 lines,
mostly deletions), `src/store/portfolios.ts` (76 lines). Test:
`portfolios.test.ts` / `host-actions.test.ts` updated to assert add/update/
delete make **no** network call (previously asserted the deleted sync).

### R15-DATA-089 — sidecar-write client removed (dead positions-ledger path)
Same commit `f37543d` ("Covers R15-DATA-089" in the commit body): the
importer-less `addPosition`/`updatePosition`/`deletePosition`/`refresh` client
in `portfolios.ts` is deleted along with the sync call, closing the same
write-only-ledger class as CODE-FRONTEND-012/CODE-PLATFORM-022.

### R15-CODE-PLATFORM-022 — dead positions-ledger client removed
Same commit `f37543d`; this is the client-removal half of the shared
write-only-ledger class (`CODE-FRONTEND-012` + `DATA-089` + `CODE-PLATFORM-022`
+ `CODE-PLATFORM-021`, per the batch plan's class rule). `CODE-PLATFORM-021` was
**not** taken in this batch (stays open).

### R15-DATA-088 — normalizeHolding rejects non-positive quantity/negative cost
Commit `b69800c`: `normalizeHolding` no longer coerces a non-finite quantity or
cost to `0`; it now drops a non-finite/`<=0` quantity and a non-finite/`<0` cost
basis for every caller (restore, form, agent), and `addHolding`/`updateHolding`
report the refusal (`id|null`, boolean) so the agent apply path returns an
honest `null` instead of narrating a write that never landed. Diff:
`src/store/portfolios.ts` (74 lines), `src/lib/host-actions.ts` (+10),
`portfolios.test.ts` (+27), `host-actions.test.ts` (+11).

### R15-CODE-FRONTEND-011 — one bound intent shared by describe and apply
Commit `124b316`: `describeHostAction`/`applyHostAction` used to parse the
agent's args independently (risking drift between the described action and the
one actually applied). `parseHostAction(name, input) -> HostIntent` now runs
once at enqueue and rides the `ProposedChange`; portfolio intents bind
`{portfolioId, holding}` at parse time and apply acts on exactly that pair,
failing honestly ("no longer in the portfolio") if it's gone by accept time.
Large diff: `host-actions.ts` (1162 lines), `host-actions.test.ts` (+215 lines,
a describe/apply parity table over every `HOST_ACTION_NAMES` entry).

### R15-CODE-FRONTEND-007 — stale-target-at-accept-time closed
Same commit `124b316` ("Also covers R15-CODE-FRONTEND-007" in the commit body)
— the bound-intent mechanism above is the direct fix for the entry's
re-resolve-against-whatever-portfolio-is-active-at-accept-time defect.

### R15-AGENT-042 — publish holding ids; refuse an ambiguous lot
Commit `7f8c452`: with the Portfolio panel open, `get_portfolio`'s holdings now
carry each row's id (`PortfolioPanel` publishes `holdings[i].id` per row —
previously only the closed-panel store fallback carried ids).
`resolveHolding` now refuses a same-symbol ambiguous match (2+ lots, no id)
instead of silently picking the first, naming each lot's id/size/price so the
model can retry by `position_id`; the review diff now names the lot ("TCS (lot
2 of 2): x20 @ ...").

### R15-CODE-FRONTEND-009 — save_screen saves the agent's recipe; run:true runs it
Commit `e6ea8bb`: `save_screen` duck-typed `saveScreen(name, payload)`, but the
real store method `saveScreen(name)` only snapshots the on-screen draft — the
agent's criteria were silently ignored and a same-name screen silently
replaced. Both casts are gone: `save_screen` now writes the agent's recipe into
the draft before saving, and the diff/label say "replaced" on a name collision.

### R15-CODE-FRONTEND-010 — write_screener_filters run:true actually runs
Same commit `e6ea8bb` ("Also covers R15-CODE-FRONTEND-010"): `run` was forwarded
through a cast into `applyFilters`, which ignored it, so `run:true` narrated
"running" without ever calling `runScreener()`. `write_screener_filters` now
chains `runScreener()` explicitly on `run:true`.

### R15-AGENT-052 / R15-AGENT-051 / R15-CODE-FRONTEND-015 — panel bus keyed by dockview id
Commit `b6741b5` fixes all three together (shared root cause: bus keys were not
the dockview panel ids `PanelHost` focuses). `BacktestResultView` now publishes
under `BUS_SOURCE = "backtest"` (the dockview id) instead of the literal
`"backtest-panel"`; `EquityOverviewPanel`/`ChartPanel` similarly publish under
their real panel ids.
Live evidence (scratch vitest `zz-b6v-verify.test.tsx` against the real
`default-layout`/publishers/`ChatSidebar` context provider, **3 passed (3)**,
then **4 passed (4)** after a fixture fix):
- `_render_terminal_preamble` rendered from real captured snapshots: snap2
  → "Focused chart: INFY (1d, no indicators)."; snap1 → "Chart: TSLA (1d, no
  indicators). Focused panel: equity-overview."
- Live agent deixis check (llama3.1:8b, real `/agents/copilot/invoke` against
  `:52310`) with the CORRECTLY-shaped `AgentContextSnapshot`
  (`focused_source`/`by_source`/`captured_at`, snake_case per `models/agent.py`):
  asked "Which symbol am I looking at right now?" against snap2 → answered
  **"INFY"** (matches the preamble's stated focused chart) — an earlier run with
  a malformed camelCase context (`focusedSource`/`bySource`) had answered the
  wrong symbol ("NVDA"), which is what motivated re-checking the context shape.
  Asked the same question against snap1 (equity-overview focused) → also
  answered "INFY" consistent with that snapshot's stated focus.

### R15-UI-021 — drawing delete key scoped to the chart; locked drawings refuse
Commits `d2e0e78` + a follow-up review fix `4c9f751` ("a drawing delete key with
nothing focused still deletes"). Live: a fresh scratch vitest case appended to
`zz-b6v-verify.test.tsx` — "contentEditable note + another panel's button +
locked-from-body never delete" — covering a locked drawing (`locked: true`) plus
delete-key presses from a contentEditable note and from another panel's button.
Result: **4 passed (4)**.

---

## Not certified (3)

- **R15-CODE-PLATFORM-018.** The freeze is fixed (20k-step binomial: `/health`
  max 33 ms over 82 polls, was 6.4 s; 60k steps: 54 s pricing, `/health` max 33
  ms over 496 polls; the workflow node path 26 ms; the frozen `--onefile`
  binary prices through `freeze_support`). But the fix adds a new defect: the
  pool's worker and `resource_tracker` processes are orphaned on every sidecar
  exit. The stdin-EOF watchdog (`main.py:61-77`) calls `os._exit(0)`, and
  Tauri's `RunEvent::Exit` kills the child, so the lifespan `finally` that
  calls `quant_pool.shutdown()` never runs. Reproduced twice: on the frozen
  binary built from the target (workers 27453/27454 reparented to PID 1, still
  alive a minute later) and on the source sidecar (25653/25654, PPID 1). Two
  workers from the W3 writer's worktree at 03:42 were still alive 9h40m later
  (PIDs 98721/98722, confirmed via `ps -o pid,ppid,lstart,etime,rss`: `ELAPSED
  09:40:54`). Every app session that prices anything leaks two processes. Fix:
  the watchdog shuts the pool down before `os._exit`, and each worker exits
  when its parent dies (for example, a pool initializer that watches
  `os.getppid()`).
  - Extra detail: live probes behind these numbers — workflow-node 20k-step:
    `job_s=6.15 health_n=57 max_s=0.026`; monte-carlo variant: `job_s=0.82
    health_n=8 max_s=0.014`; route 60k-step: `job_s=53.94 health_n=496
    max_s=0.033`; frozen-binary (`:52311`) route 20k-step: `job_s=6.24
    health_n=58 max_s=0.018`. Health-poll maxima all stayed under ~35 ms
    regardless of pricing duration — the event loop is no longer blocked; the
    remaining defect is process cleanup, not the freeze.

- **R15-AGENT-046.** The Ollama leg is fixed live: on llama3.1:8b, host actions
  carried distinct `call_<uuid>` ids (e.g. `call_d8599a16e1f641f3a026795be20f6aea`,
  `call_dabc61df9aea4fd48cf45367c101ed9f`), each `POST /agents/actions/ack`
  returned 200, and the model confirmed. The cross-run leg still reproduces: a
  scratch pytest case (`test_cross_turn_gemini_id_with_late_ack`, in
  `sidecar/tests/test_zz_b6v_scratch.py`, not kept) simulated Gemini-style
  per-stream ids (`set_chart_symbol_0`) reused across two `invoke_agent` turns,
  with turn 1's ack arriving late (after the 0.8 s grace). Result: `B6V turn1
  set_chart_symbol_0 dispatched_unconfirmed | turn2 set_chart_symbol_0
  applied`; pinned assertion failed: `AssertionError: turn 2 falsely confirmed
  by turn 1's late ack`. The runtime mints an id only when the provider's own
  id is empty or already seen in THIS invocation (`seen_call_ids` starts empty
  per call), so Gemini's per-stream `set_chart_symbol_0` repeats across runs
  and a late ack from run 1 falsely grounds run 2's action as "applied." Fix
  needed: mint ids whose uniqueness holds across runs, not just per turn.

- **R15-RESEARCH-024.** Not fully delivered. Only the runtime half landed
  (commit `26ea55c`): `_auto_publish_event` now forwards a host domain and
  `published_at` for FAST web rows, pinned by a new test
  (`test_auto_publish_fast_source_keeps_its_date_and_a_host_domain` in
  `sidecar/tests/test_agent_runtime.py`) asserting a Reuters URL yields
  `domain: "www.reuters.com"` with its `published_at` preserved, and a
  domain-only row keeps its domain. The other half (C4: `Citation`/web rows
  themselves carrying `domain` and `published_at` at the contract level, so
  FAST rows reach the mapping already dated) was not delivered by this batch's
  writers — it stays open per the batch's own CHANGELOG note ("RESEARCH-024
  waits on C4's row fields").

## Proposed not-a-defect — concurred (1)

- **R15-UI-041.** The register's removed-trading half is moot (D81 merged
  trading out of the product entirely). The open question was whether the
  rewritten first-launch terms disclose licence terms, data-accuracy caveats
  and AI-output caveats. Verifier read `src/modules/safety/DisclaimerFlow.tsx`
  live (component `FirstLaunchTosDialog`, keychain-backed, no
  localStorage/sessionStorage): the `TOS_BODY` text states, verbatim — "does
  not provide investment advice and is not a registered broker-dealer or
  investment adviser"; "Vysted has no brokerage connection. It cannot place,
  route or simulate orders"; "Market data may be delayed, incomplete or
  wrong... Check anything you rely on against the source"; "AI-generated
  analysis can be wrong. You remain solely responsible for your own
  decisions"; and the PolyForm Strict 1.0.0 / commercial-license line. Cross-
  checked against `LICENSE` (PolyForm Strict License 1.0.0) and
  `LICENSING.md` ("source-available, not open-source... noncommercial
  purpose... Anything beyond that noncommercial grant needs a commercial
  license") — the disclaimer's claims match the actual licensing files. A grep
  for stray kill-switch/order-routing UI residue found only the unrelated
  Tauri sidecar-process kill code (`src-tauri/src/lib.rs`, `child.kill()` on
  app exit) — not a trading kill-switch, no residue found. Nothing remains to
  fix in code; the copy itself is the operator's Tier-4 review item
  (`DECISIONS_FOR_OPERATOR` 3.2), not a defect. Concur.

## Issues found outside the entries

1. **NSE transport flake (cookie warm-up):** `sidecar/services/nse_provider.py`
   (`_get_json`/cookie warm-up path) 502'd once for SUMAX mid-test with `nse_direct:
   cookie warm-up failed: ... Recv failure: Connection reset by peer` — a
   transient live-NSE connectivity issue, not a code defect (a direct probe
   against the same NSE endpoint seconds later succeeded). Worth noting since it
   can intermittently mask the DATA-017 fix in a future run.
2. **Yahoo Finance RSS feed instability:** observed incidentally during the
   RESEARCH-018 bucket-routing test — `https://feeds.finance.yahoo.com/rss/2.0/
   headline?s=KAYNES.NS...` failed after retries with `Server error '500
   Internal Server Error'`. Pre-existing upstream feed flakiness, unrelated to
   any batch-6 change; the researcher correctly degraded (still routed to
   `['news', 'web_search']`, no crash).

The verifier made no code changes. Scratch scripts (`b6v_*.py`,
`zz-b6v-*.test.tsx`, `test_zz_b6v_scratch.py`), the second data dir, and the
scratch worktree were set up as tooling for verification; per the harness
kill, the transcript does not record whether the sidecars/worktree were torn
down (the task's own instructions required it, but no teardown commands were
observed after the last live test at 08:09).
