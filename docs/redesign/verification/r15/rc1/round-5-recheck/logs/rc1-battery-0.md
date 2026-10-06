# rc1-battery-0 — regression battery shard 0 (gate round 5-recheck)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd` confirmed via
`git -C <scratch cand worktree> rev-parse HEAD`.

Sets: batch-7/W2-delegate-runs-runtime (`set-26.md`, 12 ids), batch-11/W8-frontend-visual
(`set-56.md`, 4 ids). All 16 ids in the register at this candidate are `status:"fixed"`
(checked before probing).

## Sidecar

One sidecar for the whole shard, `:52340`, from `rc1-round-5-recheck-cand/sidecar` source,
data dir `rc1-round-5-recheck-data-rc1-battery-0` (`cp -R` of the isolated seed). Started
detached (`nohup sh -c 'sleep 86400 | ./.venv/bin/python3 main.py ...' &`), sleep pid
**59150** (killed at the end of this shard). `GET /health` ok before any probe.

## Method — set-26 (delegate runs)

12/12 entries re-run in-process (no HTTP, no real LLM, no pytest) against the candidate's
own `sidecar/.venv`: `agent_runtime.get_provider` monkeypatched to a scripted `FakeAdapter`
whose `stream_chat` is a per-scenario async generator, driving `services.run_manager`
(`launch_run`/`cancel_run`/`resume_run`/`answer_run`/`start_run`) through each entry's own
repro scenario (token/step/spend ceilings, ask_user pause/resume, provider persistence
across resume, a simulated `kill -9` + sidecar-restart reconciliation, and a compound-prompt
planner pre-pass with `agent_runtime.decompose` patched). Script:
`battery0_set26.py` (scratchpad) + a small follow-up `battery0_set26_039only.py` for
AGENT-039 (a bug in my own harness — `RunPlan.steps` is `list[dict]`, not a dict, so
`planned.plan["steps"]` raised; fixed to `planned.plan.steps`, then AGENT-039 re-ran clean;
all other 11 entries passed on the first corrected run). Two throwaway-harness bugs were
found and fixed along the way, both in MY test script, not product code: (1) a no-tool
round is always the FINAL terminator regardless of budget breach, so AGENT-035/LIFECYCLE-013's
"force a breach" round needed a `tool_use` call, not a bare delta; (2) `FakeAdapter` builds a
FRESH generator per round (each `stream_chat` call re-invokes the stream function from
scratch), so LIFECYCLE-012's "round 2 hangs forever" needed the hang gated on the round
counter `n`, not reached by falling through a single generator instance.

`R15-UI-040` is frontend/client-store logic (`cancelDelegateRun`/`adoptSidecarRuns` in
`src/lib/delegate-runs.ts`) — not exercisable from an in-process sidecar script. Certified
via a source read cross-checked against a live `GET /runs` wire-shape probe on this shard's
own sidecar, verdict `ci_pinned` naming `src/lib/delegate-runs.test.ts` ("delegate-runs —
sidecar truth", both `R15-UI-040` cases) — vitest itself was not run (heavy lane's domain).

Result: 11 holds, 1 ci_pinned, 0 regressed.

## Method — set-56 (frontend visual / risk analytics)

`R15-UI-091`: live curl against `:52340` (`/indicators/suggested` for 3 timeframe/asset-class
combos + `/indicators/AAPL?indicators=ema:9,ema:21`) — all match the FR-092 sets, real
non-null EMA data past warmup. Verdict holds.

`R15-UI-085`: grep for `text-charcoal-600`/`700` outside tests (3 hits, all
`disabled:text-charcoal-600`) + a read of the pinned `src/lib/design-contrast.test.ts`.
Verdict ci_pinned (the numeric WCAG assertion itself needs vitest).

`R15-CODE-PLATFORM-023`: ran the entry's own literal sidecar greps verbatim — they are
BYTE-IDENTICAL to the original defect's own finding (0 hits for VaR/beta/correlation_matrix
outside `backtest_engine.py`; no risk fields in `portfolio_db.py`/`models/portfolio.py`) —
the sidecar was never where the fix landed. Followed up exactly as the batch-11 verifier and
the prior gate round's `rc1-battery-0`/`rc1-battery-2` certifications did: all 7 promised risk
functions (`sharpeRatio`, `sortinoRatio`, `calmarRatio`, `historicalVaR95`, `correlation`,
`beta`, `maxDrawdown`) exist client-side in `src/modules/portfolio/metrics.ts` and render at
`PortfolioPanel.tsx:1098-1160`. Verdict holds — the sidecar-only grep is an adjacent note
(gate rule change 1), not a regression, since the finding is about the promised UI feature
being unimplemented, which it now is not.

`R15-CODE-PLATFORM-025`: `tauri.conf.json` `app.windows` still exactly 1 entry; 0 hits for any
pop-out spawn code; `BLUEPRINT.md:249,322` correctly scope multi-window/pop-out as
v1.0-roadmap/deferred, citing the entry. Verdict holds.

Result: 3 holds, 1 ci_pinned, 0 regressed.

## Total

16/16 ids raw, 14 holds + 2 ci_pinned, **0 regressions**. No findings filed
(`findings/rc1-battery-0.json` is `[]`).

COVERAGE: 16/16 ids raw; no raw: none.

## Cleanup

Sidecar stopped: killed sleep pid 59150 first (per the ISO_STACK.md convention); the
`sleep 86400 | python3 main.py …` worker (pid 59153) did not exit on the pipe's stdin EOF
(uvicorn does not watch stdin), so its own worker pid was killed directly as a second step
— own port `:52340`, own process, no other owner's port touched. `GET /health` confirmed
connection-refused after.
