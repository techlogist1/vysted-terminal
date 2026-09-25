# rc1-battery-4 — working log

Shard: REGRESSION BATTERY shard 4 (Sonnet), lane `battery:shard-4`, batch-6 writer sets
W1-W5. RC1 candidate `4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a`, worktree `rc1-cand` (read-only).

## Sidecar

- Own copy of seed data: `rc1-data-rc1-battery-4` (copied from `rc1-seed-data`).
- Boot: `sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52344 --data-dir
  <own copy>` — port `:52344`, one sidecar reused across all 5 sets.
- Sleep-wrapper pid 9571 (worker pid 9574, restarted twice mid-shard for R15-CODE-PLATFORM-018
  and R15-LIFECYCLE-012's hard-kill reproductions; final live pids 9571/9574).
- No writes to the shared stack (`:52152`/`:52153`/`:52154`), no writes to `rc1-cand`, no writes
  to the operator's live app-support data dir.

## Sets, in write order (each file written before the next set started)

1. `battery/set-18.md` (W1 india-exchange-data, 8 entries) — all `holds`. Live curl reproductions
   against `:52344` for disclosures (QUALIANCE announcements/shareholding/results), fundamentals
   revenue_ttm provenance (DAL, FUSION — screener.in cross-check), half-yearly-filer labelling
   (JONJUA vs DHANBANK), statements gap reporting (DHANBANK), BSE-only results feeds
   (JONJUA/DAL/ELCIDIN), and the ADR SEC 20-F ownership lane (SIFY) vs the not-applicable case
   (AAPL). One early false alarm: 3 concurrent/racy curl calls returned a generic provider_error
   body; a clean sequential re-run (`curl -s -i -o file`) got real 200s — not reported as a finding.

2. `battery/set-19.md` (W2 delegate-runs-runtime, 13 entries) — 10 `holds`, 3 `ci_pinned`
   (R15-AGENT-036 checkpoint-order, R15-CODE-AGENT-011 ask_user pause/resume,
   R15-UI-040 frontend rail — no live ask_user round or browser harness driven this shard).
   Live: budget-ceiling floor/reject (422 on `max_steps:0`), an ollama breach→resume cycle keeping
   provider/model + checkpoint, a hard-kill-mid-round→restart reconciliation
   (`LIFECYCLE-012`, `detail="interrupted by sidecar restart"`), cancel/resume state-machine edges
   (`CODE-AGENT-010`, corrected an initial wrong assumption that `resume` on `cancelled` should 409
   — `runs_store.py`'s TRANSITIONS table makes it resumable by design), a compound-task ollama run
   showing the typed `activity[]` list live (`AGENT-039`), the `_PLANNER_PROVIDERS` gate confirmed
   at source (ollama excluded by design; 3 OpenRouter free-slug attempts all hit real 429 rate
   limiting — environment, not product), and a 2-host-action run showing distinct fresh
   `call_<uuid>` ids (`AGENT-046`) — source shows the id-minting is now unconditional
   (`agent_runtime.py:1987`), closing the cross-run Gemini-id-reuse leg VERDICTS.md had left open.
   `b6v_repair.py` reused verbatim for `LEAD-014` (needed `PYTHONPATH=sidecar` to fix a
   `ModuleNotFoundError`).

3. `battery/set-20.md` (W3 unattended-platform-chart, 10 entries) — 9 `holds`, 1 `needs_gui`
   (R15-UI-022 — the register itself flags this entry `needs_gui`; source is consistent with the
   fix but the click-to-place/off-bar visual behavior needs a live chart interaction this
   environment cannot exercise). Live: a 20k-step binomial price while polling `/health`
   (stayed ~1.3ms) then a hard `kill -9` of the worker confirming no orphaned quant/resource_tracker
   process (`CODE-PLATFORM-018`); direct `node -e` calls into `build-python.mjs`'s exported
   functions forcing a stale-venv recreate (`LEAD-012`); full live CRUD against
   `/workflow/{save,schedules,webhooks}` — interval/announcement schedule create, a `<5min`
   interval correctly 422's, patch/delete round-trip, and a webhook secret registered by header
   that never appears in the `GET /webhooks` response (`AGENT-023` — the actual interval/
   announcement firing + no-overlap + 10s-timeout behavior is `ci_pinned` to
   `test_workflow_scheduler.py`, needing a fake clock not run this shard). Source-confirmed:
   the panel-context-bus dockview-id keying (`AGENT-052`+`051`+`CODE-FRONTEND-015`), the drawing
   symbol/timeframe persistence (`UI-020`), the delete-key target/lock guard (`UI-021`), and the
   indicator-series clear-on-load+catch with a committed-candles-key gate (`UI-023`).

4. `battery/set-21.md` (W4 research-funnel, 15 entries) — all `holds`. Live: reused `b6v_bucket.py`
   (India filings sub-question routing, region-aware + word-bounded "sec" match — `RESEARCH-018`)
   and `b6v_floor.py` (results-first disclosure floor ranking across 3 Indian symbols —
   `RESEARCH-012`) verbatim in-process against the candidate venv, matching VERDICTS.md exactly.
   Reused `b6v_snap.py` for `CODE-RESEARCH-002`'s isolate-cross-check-legs monkeypatch: the
   injected fault never fired this run because a separate concurrency issue (nse_direct throttle
   contention — logged as a finding, see below) kept the fundamentals leg from completing inside
   the shared 6s witness timeout, so the `if isinstance(fund_data, dict):` guard skipped the whole
   cross-check block before reaching the patched functions. Root-caused via two follow-up scripts
   (`b4v_snap_debug.py`, `b4v_concurrent_check.py`): price_data + fundamentals for RELIANCE each
   succeed in a few seconds ALONE, but concurrently (as `snapshot_structured` runs them) they take
   ~18.3s, serializing behind `nse_provider.py`'s module-level throttle+lock. This is NOT a
   regression of `CODE-RESEARCH-002` itself — source shows the try/except+timeout isolation intact,
   and the live run is itself evidence of graceful degradation (no exception propagated despite
   two real leg timeouts) — filed separately as a new_defect. The remaining 12 entries (heavy-loop
   fallback parity, ULTRA floor citation, VisitResult reason propagation + AttachHis fallback, the
   shared `result_limit()`, the index-tail regex fix, the interstitial-marker/breaker-order split,
   the `BriefSource.publishedAt`/`provider` contract + `hostOf` URL-host preference, the
   broken-citation inert-marker + count, and the `lib/format.ts`-routed money/percent formatters)
   were all confirmed at the source level against PLAN.md's stated mechanism (no live vitest/
   browser this shard).

5. `battery/set-22.md` (W5 host-actions-portfolio, 13 entries) — all `holds`. Live: full
   GET/POST/PUT/DELETE probe of `/portfolio/positions[/1]` against `:52344` confirming the
   GET-only surface (`405`/`404` on the write verbs) — the write-only-ledger class
   (`CODE-FRONTEND-012`+`DATA-089`+`CODE-PLATFORM-021`+`022`). The remaining 9 entries (bound
   `HostIntent` parse-once for describe/apply parity + stale-target refusal, `save_screen`/
   `write_screener_filters` cast removal, screener-criterion drop reasons, published holding ids +
   ambiguous-lot refusal, typed pre-image + `undoPreImage`, the `ChangeOutcome`-gated transcript
   line, and `normalizeHolding`'s non-finite/non-positive rejection) were confirmed at the source
   level (no live browser this shard).

## Findings

One new_defect filed (not a regression of any specific certified entry): the `nse_direct` provider's
module-level anti-bot throttle (`nse_provider.py` `_Throttle`/`_lock`, min_interval ~1s+jitter,
tagged "R15-DATA-066") serializes ALL nse_direct HTTP calls process-wide, but
`services/research/fast.py`'s `_WITNESS_LEG_TIMEOUT_S = 6.0` time-boxes price+fundamentals AND all
7 cross-check witness legs independently. Under India-region `snapshot_structured` calls (the core
of every FAST/DEEP/ULTRA research path), up to 9 concurrent legs can contend for the same
serialized resource, and later-queued legs routinely exceed the shared 6s window and get dropped —
observed live and reproducibly (RELIANCE: ~18.3s combined vs 6s budget) rather than as a one-off
network blip. See `findings/rc1-battery-4.json` for the full writeup.

## Sidecar stop

Final action: `kill 9571` (the sleep-wrapper pid; leaves no orphaned worker per the
`CODE-PLATFORM-018` fix already confirmed live). No shared-stack or other-owner process touched.
