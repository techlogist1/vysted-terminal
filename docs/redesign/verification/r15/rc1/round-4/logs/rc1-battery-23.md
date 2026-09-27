# rc1-battery-23 — round 4 log

Shard 23: batch-8/W1-sidecar-lifecycle-transport (set-30, 7 ids), batch-2/W2-instrument-identity
(set-1, 6 ids), batch-11/W4-registry-loop (set-51, 2 ids). Candidate
`1006c6da694ede5776c3dabbd27b305aeb56b5ad`.

Own sidecar: source-booted from the candidate worktree's `sidecar/`, `127.0.0.1:52363`, data
dir `rc1-round-4-data-rc1-battery-23` (copy of the seed keyless profile). Sleep pid 10073
(kill target), worker pid 10076. Health confirmed ok before any probe; stopped at end of shard.

Method: for every id, read the register entry's repro/evidence and the batch's own
`VERDICTS.md` "Per-entry evidence" (`stage-c/batch-8`, `stage-c/batch-2`, `stage-c/batch-11` —
not the old `rc1/battery/set-*.md` files, which belong to an earlier round and were only read
for context, never cited as evidence). Where the repro is HTTP-observable, re-ran it live
against the own sidecar (curl) or in-process via the candidate's `.venv` python (resolver/
ownership-gate checks). Where the fix is purely Rust/frontend source with a pinned unit test as
the only certification evidence, re-ran that exact test directly (`cargo test --lib --
<name(s)>`, 0.00s, 2/2 passed for R15-LIFECYCLE-010) rather than citing ci_pinned without
trying, since a single named test is well under the 120s budget. Where no test exists and no
runtime repro is reachable headless, read the certified fix's exact file:line source and
confirmed byte-for-byte it still matches the certified shape (React error-boundary wiring,
sidecar-client transport wrapping, SettingsPanel listeners) — this mirrors the project's own
established battery precedent (grep-only "holds" verdicts) rather than reading a historical
diff.

One near-miss: R15-DATA-003's own register repro cites `/disclosures/shareholding?symbol=AMAL`
directly, but that raw REST route is documented India-only by design (no region param) and was
never the object of the fix — the actual applicability gate lives in
`ownership_check.is_applicable`/`get_exchange_ownership`, gated on the *resolved listing*
(`AMAL.BO` vs bare `AMAL`), consumed by the research snapshot pipeline. Re-ran the gate
directly in-process instead of the raw disclosures route and confirmed it holds; noted the raw
route's unchanged India-only behavior in the set-1 evidence column so it isn't mistaken for a
regression by a later reader.

Result: 15/15 holds, 0 regressed, 0 ci_pinned, 0 needs_gui, 0 blocked_env.

COVERAGE: 15/15 ids raw (set-30 7/7, set-1 6/6, set-51 2/2).
