# RC1 data-pack re-collection (rc1-datapack)

Candidate sha `4097dac4`. Own sidecar booted from `rc1-cand/sidecar` on a fresh copy of
`rc1-seed-data` (isolated, keyless), port 52313. Ran
`scripts/r15/collect_battery.py --port 52313 --force` from a minimal copy tree
(`scratchpad/rc1-pack`) so the census baseline in
`docs/redesign/verification/r15/battery/collected/` was never overwritten. All 24 battery
slots collected; raw output copied to `r15/rc1/battery/collected/`. Full field-by-field
re-diff: `r15/rc1/datapack.json` (script: `scratchpad/rc1-pack/redo_diff.py`, not committed —
scratch tool).

**Environment note (read first):** this sidecar's own background `fundamentals_warm` cache
job hammered Yahoo concurrently with the collector, opening the Yahoo circuit breaker
repeatedly (`opens_total` 26→28, `throttles_total` up to 287, "backing off 543s" in
`sidecar.log`). P6 ICON and P18 ONC's `/fundamentals` calls landed while `yahoo_open:false`,
fell through to `openbb-mcp`, and got an all-null payload — self-inflicted noise, not
evidence of a code regression. Those two slots' blank numeric fields are excluded from
findings below.

## 38 fixed register entries touching battery symbols (re-diff target)

21 symbols implicated: AMAL(8) DAL(11) SMR(8) DHANBANK(5) ELCIDIN(8) CREST(4) JNPR(5)
ICON(5) CHTR(3) JONJUA(5) NAPEROL(4) DHOOTTRANS(4) SIFY(4) TTC(4) VERTEX(3) JUMBO(3)
SUMAX(3) ONC(2) CSL(2) FUSION(2) SAFE(1) VIYASH(2) — see mapping in
`scratchpad/rc1-pack` session log; full id list was cross-checked against
`vysted-r15-register.json`.

## What re-diffed clean (no regression)

- All "app blank" / "no source truth" / "definitional difference" / "mismatch" statuses
  from the census are unaffected by this drive (out of scope — we only re-diffed prior
  `match` cells for drift, plus the shareholding/announcements/results_calendar call
  status).
- The great majority (~340 of ~367) prior `match` cells still match once unit
  ambiguity (bare pack numbers that are implicitly INR crore), percentage-vs-decimal
  scale, and multi-source pack dicts are normalized. Several apparent mismatches were
  tool artifacts of the automated re-diff (compound outside_value strings, custom field
  names not in the generic mapper) and are not filed as findings.
- `results_calendar` flipped 502→200 for **every** slot that had it 502 at census time
  (P14, P15, P17, P18, P19, P1, P20, P2–P9, S1–S4) — a broad, consistent improvement,
  not attributable to a single register id in this drive's scope; noted, not filed as
  a finding (no register regression to pin it against).

## Findings filed

1. **rc1-datapack:1 (new_defect, high)** — the derived P/E fallback (`basis_note:
   "price / EPS"`, `provider: "derived"`) does not guard negative EPS: SIFY (P17,
   eps -0.13) and VERTEX (S3, eps -0.25) both got a negative P/E served as `status: ok`
   with no reason/flag (-103.15 and -12.2 respectively), while the census pack recorded
   both as correctly "loss-making, PE n/a" at fetch time. Same defect class in 2 of 2
   loss-making names checked → a computation-path bug (missing `eps <= 0` guard before
   `price / eps`), not a one-off. `sidecar/services/fundamentals*` derived-ratio path is
   the suspected location (not opened this drive — re-diff only, no code read/fix per
   role scope).
2. **rc1-datapack:2 (environment, medium)** — `/disclosures/shareholding` status flipped
   between census and rc1 for the same BSE-only symbols in **both** directions (200→502
   for 15 slots: P13 P14 P19 P20 P2 P3 P4 P5 P6 P7 P8 P9 S2 S3 S4; 502→200 for 6 slots:
   P15 P17 P18 P1 S1). This bidirectional flip, concurrent with this sidecar's own
   Yahoo-driven circuit-breaker churn, reads as endpoint/rate-limit flakiness rather than
   a deterministic code regression — flagged as environment, but the register's
   shareholding-derived entries (R15-DATA-004, R15-DATA-056, R15-DATA-057) may be
   reproducibility-sensitive and worth a dedicated flake-rate check outside this drive.
3. **rc1-datapack:3 (environment, low)** — P6 ICON and P18 ONC fundamentals came back
   fully null because this sidecar's own concurrent warm-cache job had the Yahoo circuit
   open at collection time (`yahoo_open:false`, `openbb-mcp` fallback returned all-null
   for both). Not usable as regression evidence; would need a re-collect with the warm
   job paused to test cleanly. Secondary observation: `openbb-mcp`'s fallback for a US
   ADR (ONC) when Yahoo is unavailable is a wall of nulls rather than a clear
   degraded-provider signal — worth a look if this reproduces cleanly outside this
   drive's noisy environment.

## Low-confidence, not filed

Small (5–12%) numeric drift on VIYASH debt_to_equity/revenue_ttm, JONJUA pe_ttm/pb, and
CSL pe_ttm plausibly reflects ordinary 2–6 day as-of movement on price-derived ratios
(P/E, P/B move with daily price) or a TTM-window quarter rollover; per task instruction
("price-like drift is as-of skew, not a regression") these are not filed.
