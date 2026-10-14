# R15-FINAL-006, round 2: single-quote starvation under a portfolio batch

- Base: `d0744711b4be7cf22af3712a0b5c6ab193dfb98a`. Branch: `r15-r2-final006`.
- Writer: claude-opus-5-5 (judgement tier, effort high). 3 Oct 2026.
- Scope: the server half. Round 1 fixed the client half (one batch request, an in-flight guard, backoff) and is not touched here.

## Root cause

A cold NSE quote is paced by `nse_provider._Throttle`. This is one process-wide pacer, about 1 request per 1.0-1.4 s. Every caller reserved the next slot in FIFO order at call time. The batch `/quotes` route runs 16 members at once on its pool. Each member reserves a slot as soon as it starts, so 16 slots (about 16-20 s) are always booked ahead of any single `/quotes/{symbol}`. An interactive cold quote lands behind all of them. Measured on the base code: 19.2-20.5 s under load, against 1.1-1.5 s idle in the same circuit state.

The first live run of the fix found a second shared resource. `_get_json` sends each GET while holding the one module `_lock`, because a curl_cffi session is not thread-safe. During that run the NSE edge reset connections, and each reset hung for about 10 s. A batch member's hung GET held the one session lock, so a single quote waited out several of them. TITAN took 36.9 s and ONGC 33.7 s, in `r2-006-live-fix1`. The fix therefore covers both the pacer and the session.

## Fix (server side; the pacing rate is unchanged)

- `sidecar/services/nse_provider.py`
  - New `bulk_lane` ContextVar, default `False`.
  - `_Throttle` keeps a slot reservation for every caller. A bulk-lane caller's reservation is a `_BulkTicket`. An interactive caller takes the earliest bulk slot that is still in the future. The bulk member it displaced is re-queued at the tail with a fresh `_reserve_tail` slot. The set of slots, and so the upstream request rate, stays the same; only who rides each slot changes. An interactive caller now waits at most for the slot in progress, never for the 16 booked ones. Sleeping still happens outside the throttle lock (R15-DATA-066 holds).
  - Each lane has its own session and lock: `_holder`/`_lock` for interactive callers and `_bulk_holder`/`_bulk_lock` for batch members, picked by `_lane_session()`. A hung or slow bulk GET never holds the session an interactive call needs. The circuit breakers are still per path and shared by both lanes. Their map has its own short `_breakers_lock`, so a GET in progress never blocks the breaker lookup. `get_archive_text` uses the same lane selection.
- `sidecar/routers/quotes.py`: each batch member runs `_batch_member_quote`, which sets `nse_provider.bulk_lane` inside that member's copied context. `GET /quotes` (batch) takes the bulk lane. `GET /quotes/{symbol}` (single) and every other caller (copilot tools, research, charts) stay interactive.
- `src/modules/portfolio/api.ts` is not changed. The route marks its own members, so the client sends no hint.
- Also considered: serving batch members from the one-request NSE bhavcopy, which is already applied at boot by `fundamentals_warm`. It only covers EOD (off-hours) quotes and changes where quotes come from, so it is not part of this fix. It would make the cold 100-name batch near-instant off-hours, which bears on the residual below.

## Tests (new)

- `tests/test_nse_throttle.py::test_an_interactive_call_is_admitted_ahead_of_a_queued_bulk_batch`
  - This is the deterministic scheduler test: fake clock, threads parked in the injected sleep, no real timing.
  - 16 batch members hold slots 0..15. An interactive call is admitted at slot 1.0, not 16.0.
  - After release, the last slots of all 16 waiters are exactly 1..16, one interval apart. The bump re-queued a member; it did not add rate.
- `tests/test_nse_throttle.py::test_a_hung_batch_get_never_holds_the_interactive_session`: a batch member's GET hangs inside the fake edge. An interactive `_get_json` still completes, because it uses its own session.
- `tests/test_quotes.py::test_batch_members_take_the_nse_bulk_lane_and_a_single_does_not`: batch members see `bulk_lane` True and the single route sees False.

### Fail before (base source restored via `git stash push -- sidecar/routers/quotes.py sidecar/services/nse_provider.py`, new tests kept)

```
E           assert False
E            +  where False = acquire(timeout=5)
E            +    where acquire = <threading.Semaphore at 0x113c8f820: value=0>.acquire
E           assert False
E            +  where False = wait(5)
E            +    where wait = <threading.Event at 0x114ac43c0: unset>.wait
E           RuntimeError: cannot join thread before it is started
E       AttributeError: module 'services.nse_provider' has no attribute 'bulk_lane'
FAILED tests/test_nse_throttle.py::test_an_interactive_call_is_admitted_ahead_of_a_queued_bulk_batch
FAILED tests/test_nse_throttle.py::test_a_hung_batch_get_never_holds_the_interactive_session
FAILED tests/test_quotes.py::test_batch_members_take_the_nse_bulk_lane_and_a_single_does_not
3 failed, 32 deselected in 10.44s
```

The `RuntimeError` came from the hung test's teardown. The teardown now joins only threads that started; the test still fails on the base code at `entered.wait(5)`.

The same scheduling question was also run as a behaviour script with no lane API. It parks 16 batch waiters on the pacer, then makes one interactive call:

```
base:  bulk lane present: False | interactive call admitted at slot 16.0 s (min_interval 1.0 s)
fixed: bulk lane present: True  | interactive call admitted at slot 1.0 s (min_interval 1.0 s)
both:  distinct final slots: [1.0, 2.0, ..., 16.0]
```

A real-time pacing check used 16 bulk workers × 8 waits plus an interactive caller every 0.13 s, with min_interval 50 ms. The mean gap between grants was 59.6-60.1 ms with the bulk lane, against the 60 ms expected (min + jitter/2). The minimum gap of 42-44 ms is thread-wake jitter and matches the pure-FIFO control (42.5-43.6 ms). The rate is unchanged. Interactive wait: mean 40 ms, max 63 ms, against about 960 ms FIFO.

### Pass after

```
3 passed, 32 deselected in 0.09s
```

## Live (own sidecar from source, :52950, keyless data copy seeded from final-seed-data, dev-keystore `{"secrets": {}, "migrated": true}`)

The replay follows the round-1 verifier's load. A fresh sidecar process means a cold in-memory EOD cache.

1. 3 idle cold singles.
2. The 100 cold NSE names from `fr1v/vt/sym100b.json`, sent as one batch `GET /quotes` with `X-Vysted-Region: IN`, the way the portfolio now sends them.
3. 5 cold singles timed while the batch is in flight.
4. 3 cold singles after the batch, while the quote-equity circuit is still open. This is the same circuit state the loaded singles see.

| run | idle (fresh, circuit closed) | loaded singles (batch in flight) | idle after (circuit open) | batch |
|---|---|---|---|---|
| base `d0744711` | 6.48 / 5.99 / 5.71 s | 19.24 / 20.49 / 19.40 / 19.19 / 20.17 s | 1.11 / 1.45 / 1.13 s | 100/100 in 124.9 s |
| fix (final run) | 7.12 / 6.51 / 7.07 s | **0.73 / 0.92 / 1.56 / 1.42 / 0.40 s** | 0.97 / 1.07 / 1.18 s (median 1.07) | **100/100** in 128.0 s |

Target check: a loaded single must return within 2× its idle latency.
- Same circuit state: the loaded singles have a median of 0.92 s and a maximum of 1.56 s. Idle-after has a median of 1.07 s, so 2× is 2.14 s. All 5 loaded singles pass.
- Against the fresh idle median (7.07 s) they are faster still. The fresh idle figure includes the quote-equity 403 rotation dance, about 5 throttle slots.
- On base, the loaded singles were 17-18× the same-state idle.
- Every quote was served by `nse_direct`, and the final run saw 0 connection resets.

### Earlier runs of the fix

These are kept for honesty. Both ran within 15 minutes of other heavy NSE load from this machine.

- `fix1`, before the per-lane session:
  - Loaded singles: 0.68 / 1.22 / 1.55 s, then 36.87 / 33.72 s.
  - Cause of the slow two: 9 edge connection resets (`curl: (35) Recv failure: Connection reset by peer`, about 10 s each), sent on batch members' GETs that held the one shared session lock. This finding led to the per-lane session.
  - Batch: 100/100 in 157.9 s.
- `fix2`, per-lane session, edge still resetting:
  - Loaded singles: 1.13 / 1.44 / 0.22 s, then TITAN 22.89 s (served by `bse`) and ONGC 10.28 s (served by `nse`).
  - The sidecar log shows both slow singles' OWN requests reset at the edge: their historicalOR GET, their warm-up, then jugaad. That is an upstream failure on their own requests, not queueing behind the batch.
  - Batch: 100/100 in 139.1 s.
- base runs: base1 had 1 reset, on the resolver's master download; base2 had 0.

## Residual (not in this entry's owned scope)

The cold 100-name batch takes 124.9 s on base and 128.0 s with the fix. The client budget `QUOTES_BATCH_TIMEOUT_MS` is 120 s (`src/modules/portfolio/api.ts`). So a fully cold 100-NSE-name portfolio's first refresh can still abort client-side just before the server finishes. The next refresh, after the round-1 backoff, is served from the EOD cache, as round 1's FE replay showed with 100/100 priced. It takes about 1 slot per name, because the quote-equity circuit is open. Two fixes, either of which would close it:
- Size the budget to the pacer, for example 1.4 s × names + margin.
- Serve EOD batch members from the bhavcopy, as described in the Fix section.

Both are outside this entry's owned files and the "do not raise the rate" constraint, so they are left for the lead.

## Checks (worktree)

- New tests: fail on the base source, pass after (tails above).
- Touched area: `.venv/bin/python -m pytest tests/test_nse_throttle.py tests/test_quotes.py tests/test_nse_provider.py -q` → `68 passed in 3.94s`, EXIT=0.
- Full suite: `cd sidecar && .venv/bin/python -m pytest tests -q` (detached, polled) → `3975 passed, 1 skipped, 4 warnings in 218.38s (0:03:38)`, EXIT=0.
- `ruff format <changed files>` → `4 files left unchanged`, EXIT=0. `ruff format --check .` → `455 files already formatted`, EXIT=0. `ruff check .` → `All checks passed!`, EXIT=0.
- No TS change, so pnpm was not run.
