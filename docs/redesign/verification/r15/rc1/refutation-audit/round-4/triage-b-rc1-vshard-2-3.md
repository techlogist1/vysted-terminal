# triage-b — rc1-vshard-2:3 (tie R15-LIFECYCLE-020)

Audited 07:35 IST at HEAD bed3b166. The code tree equals 01015033, and the fix round did not touch screener.py, yahoo_batch_provider.py or provider_health.py.

## Claim (shard 2)
The warm loop is now lazy and follows the region, but its 429s still record into the same YAHOO circuit that user requests read. There is no separate budget and no lower-priority weight.

## Code at HEAD
- `sidecar/services/screener.py:1327-1346` `_warm_once` → `yahoo_batch_provider.fetch_quotes_batch(symbols)` (:1338). `fundamentals_warm.py:178` does the same. The user's screener batch path calls the identical function (`screener.py:957`).
- `sidecar/services/yahoo_batch_provider.py:306-325`: after its retries, a chunk 429 calls `provider_health.record_rate_limited(provider_health.YAHOO)` at the default weight 1.0 (:322) whoever the caller is. `fetch_quotes_batch` has no parameter to mark background traffic.
- `sidecar/services/provider_health.py:97-121`: `record_rate_limited(family, *, weight=1.0)` already supports a weight, and `_OPEN_THRESHOLD = 3` (:52). No warm caller passes a weight.
- The user paths gated by that circuit are `screener.py:550` (`_fetch_pair` → "rate_limited" with no spend), `screener.py:1070` (enrichment), `yahoo_batch_provider.py:276` (every batch chunk) and `earnings_quality.py:243`.
- The fix commit 4c2e78fb touched only the lazy, region-following start. The batch-5 PLAN (`stage-c/batch-5/PLAN.md:434-439`) dropped the fix_shape's third clause, "keep background warming from opening the circuit user requests share (a separate budget or a lower-priority weight)", without comment.

## Repro at HEAD (in-process, deterministic; only HTTP is faked)
`/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/l020/warm429.py` fakes the batch client to return 429 and sets `_warm_universe = "nifty50"` (50 symbols). It runs three background warm cycles with no user traffic at all, then makes one user screener fetch.
Command: `cd sidecar && ./.venv/bin/python /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/l020/warm429.py /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/data-l020`
```
provider health: yahoo circuit OPEN for 68s (consecutive opens=1) — callers serve stale/seed basis until it half-opens
before: {'open': False, 'cooldown_remaining': 0.0, 'consecutive_throttles': 0.0, 'consecutive_opens': 0, 'opens_total': 0, 'throttles_total': 0.0}
warm cycle 1: throttled=True http_calls=3 is_open=False consecutive_throttles=1.0 opens_total=0 cooldown=0s
warm cycle 2: throttled=True http_calls=6 is_open=False consecutive_throttles=2.0 opens_total=0 cooldown=0s
warm cycle 3: throttled=True http_calls=9 is_open=True consecutive_throttles=0.0 opens_total=1 cooldown=68s
user _fetch_pair(RELIANCE.NS): None rate_limited | http calls spent: 0
user fetch_quotes_batch: {} {'RELIANCE.NS': 'rate_limited', 'TCS.NS': 'rate_limited'} | http calls spent: 0
```
Background warming alone opens the shared YAHOO circuit for 68 s. The user's next screener fetch (`_fetch_pair`) and batch quote are then refused as `rate_limited` without a single request. The shard's live evidence at 68d5573a (yahoo `throttles_total` 236 → 238 from a warm cycle after one nifty50 run) is consistent with this mechanism.

## Duplicate search
I scanned the register for warm + circuit/provider_health/429 and for fundamentals_warm. DATA-110 (throttled-IP screen coverage), DATA-072 (circuit cannot close on success) and LEAD-025/LIFECYCLE-030/031/032 (warm worker boot issues) are different defects. Only LIFECYCLE-020's fix_shape names this one.

## Classification: partial on R15-LIFECYCLE-020
Its stated repro (a US-only S&P 500 loop at boot whatever the region) is fixed. The entry's root_cause ("... on the same circuit user requests use") and the third clause of its fix_shape are unfixed and reproduce. That is a stated part of the same defect, so the tie reopens.

## Severity: medium (unchanged)
A stated feature is degraded: background activity can make a user's screener run serve stale or skipped rows for a cooldown that grows with each re-open. It is honestly labelled `rate_limited`, and the workaround is to wait.

## Certification failures
The baseline for R15-LIFECYCLE-020 is 0. It is certified in stage-c batch-5, its note has no clause, and no refutation-audit verdicts exist for it. This partial adds 1, for a total of 1.
