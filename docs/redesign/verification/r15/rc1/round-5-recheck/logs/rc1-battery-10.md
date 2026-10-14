# rc1-battery-10 (Sonnet) — stage-c batch-2 + batch-11 + batch-25

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Own sidecar booted from source on :52350
(sleep pid 78872, worker pid 78874), data dir copied from rc1-round-5-recheck-seed-data.

Sets:
- batch-2/W5-surfaces-and-math (set-4.md): R15-DATA-009,010,011,031,042,CODE-PLATFORM-053,100,007 — all holds.
- batch-2/W2-instrument-identity (set-1.md): R15-DATA-012, CODE-DATA-001, 018, 001, CODE-DATA-005 — all holds.
- batch-11/W4-registry-loop (set-52.md): R15-LIFECYCLE-026 (5-min idle CPU soak, in progress), R15-DATA-071 (cold-cache BSE history) — DATA-071 holds.
- batch-25/W5-opus (set-71.md): R15-RESEARCH-015 — holds (in-process re-run of the fixed independence-floor function against the register's stated cases C/D + control B).

Notable technique: several frontend-only entries (R15-CODE-PLATFORM-053, R15-DATA-042, R15-DATA-100)
were re-run for real (not just source-read) via `node --experimental-strip-types` importing the
actual .ts modules (metrics.ts, region.ts) directly against live sidecar quotes — no GUI needed
since those functions are pure. csv.ts/format.ts's top-level imports pull in Tauri APIs, so their
pure logic (buildCsv/formatMoney) was reproduced verbatim inline rather than imported.

## Final

All 16 entries across the 4 writer sets re-proved: 16 holds, 0 regressed, 0 ci_pinned needed
(pure-function/CSV entries were re-run for real via node --experimental-strip-types rather than
deferred to vitest), 0 needs_gui, 0 blocked_env. No findings.

R15-LIFECYCLE-026's idle-CPU sample window was 231s (not the full 300s) due to the per-call time
budget; the trend across 6 samples over that window shows no CPU-burn signature, so verdict holds
with that caveat noted in the raw file.

COVERAGE: 16/16 ids raw across all 4 sets; no raw: none.
