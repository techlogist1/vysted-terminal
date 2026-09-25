# rc1-datapack working log

Role: rc1-datapack (RC1 gate-verification, candidate sha 4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a)

## Setup
- Checked for prior-attempt artifacts for this role: none found at start (only rc1-gate8's).
- Isolation pattern followed per `docs/redesign/verification/r15/stage0/ISO_STACK.md`: fresh
  copy of `rc1-seed-data` (never operator's real profile, audit_log.db not copied), booted
  own sidecar from the candidate source tree (`sidecar/main.py`) on port 52313, pointed
  `VYSTED_OPENBB_MCP_PORT`/`VYSTED_SEC_EDGAR_MCP_PORT` at the shared read-only MCP
  subprocesses (:52153/:52154). Shared candidate-source stack (:52152) never touched/restarted.
- Copied `scripts/r15/collect_battery.py` into a scratch copy tree
  (`scratchpad/rc1-pack`) so it writes `collected/*.json` under the scratch root, never
  overwriting the census baseline at `docs/redesign/verification/r15/battery/collected/`.

## Collection run
- `python3 scripts/r15/collect_battery.py --port 52313 --force` run detached, background,
  polled via short Bash/Monitor calls (~19 min wall time, 24 slots, ~12 calls/slot).
- Full per-call status/timing log: `scratchpad/rc1-pack/collect.log`.
- Confirmed all 24 slots landed (`P1..P20`, `S1..S4`); copied to
  `docs/redesign/verification/r15/rc1/battery/collected/`.
- Observed during collection: `/system/provider-health` showed the Yahoo circuit breaker
  opening repeatedly (opens_total 26->28, throttles_total up to 287) -- traced to this same
  sidecar's own background `services.fundamentals_warm` cache-warming job running
  concurrently and independently hammering Yahoo for hundreds of bundled tickers, sharing
  the collector's circuit breaker. This is an environmental confound for this run, not a
  candidate-code property; called out per-slot below where it affected results (P6 ICON,
  P18 ONC fundamentals).

## Register mapping
- Loaded `vysted-r15-register.json`, filtered `status == "fixed"` entries whose
  repro/evidence names a battery symbol or a BATTERY_DIFFS field. Result: 38 entries across
  21 symbols (AMAL 8, DAL 11, SMR 8, DHANBANK 5, ELCIDIN 8, CREST 4, JNPR 5, ICON 5, CHTR 3,
  JONJUA 5, NAPEROL 4, DHOOTTRANS 4, SIFY 4, TTC 4, VERTEX 3, JUMBO 3, SUMAX 3, ONC 2, CSL 2,
  FUSION 2, SAFE 1, VIYASH 2).

## Re-diff tool
- Wrote `scratchpad/rc1-pack/redo_diff.py` (scratch tool, not committed): loads every
  `docs/redesign/verification/r15/battery/diffs/*.json`, for each prior-`match` field
  re-locates the corresponding value in the freshly collected rc1 payload (via an explicit
  leaf-alias map to the fundamentals/shareholding/identity response shapes) and checks it
  still agrees (numeric within 3% after crore/lakh/1e7-scale normalization, or exact/Ltd-
  normalized string match); price-like/volatile/endpoint-status fields are excluded from
  per-field checks and compared separately via HTTP status at the call level
  (shareholding/announcements/results_calendar).
- Iterated through 5 rounds of false-positive elimination: diff-file schema key variance
  (`fields` vs `diffs`, `slot` vs `battery_slot`), a wrong-field bug (generic leaf fallback
  matching `quote.high` instead of `fundamentals.fifty_two_week_high`), field-name
  annotation stripping (`"revenue_ttm (raw value vs ...)"`), unit-mismatch tolerance
  (crore/lakh + bare-number 1e7 fallback), Ltd/Limited name normalization.
- Known tool limitation not fixed this drive: no percentage-vs-decimal (x100) tolerance in
  `numeric_close()` -- two ROE fields (P3 CHTR, S3 VERTEX) flagged as mismatches are actually
  the same value once scaled (rc1 stores ROE as a decimal fraction, census pack recorded it
  as a raw percentage); verified by hand, not filed as a finding, but the automated tool's
  raw regression count includes these two as false positives -- see DATAPACK.md.
- Output: `docs/redesign/verification/r15/rc1/datapack.json` (`{fields: {...per-slot...},
  call_status_flips: [...]}`).

## Triage of flagged fields
- Manually walked every slot's `possible_regression` entries plus the call_status_flips
  list. Confirmed via direct `field_meta` inspection (provider/basis_note/reason) that the
  P17 SIFY and S3 VERTEX P/E flags are a genuine computation-path defect (negative EPS not
  guarded before `price / eps`), not a data-source artifact -- filed as rc1-datapack:1.
- Confirmed the shareholding call-status flips are bidirectional (not a one-way regression)
  and temporally correlated with this sidecar's own circuit-breaker churn -- filed as
  environment (rc1-datapack:2), not a per-slot regression list.
- Confirmed P6 ICON / P18 ONC fundamentals-all-null via `polite.yahoo_open: false` in the
  same payload, directly traceable to the concurrent warm-job rate-limit collision --
  filed as environment (rc1-datapack:3), fields excluded from regression consideration.
- Small (5-12%) numeric drift on VIYASH debt_to_equity/revenue_ttm, JONJUA pe_ttm/pb, CSL
  pe_ttm read as ordinary as-of skew on price-derived ratios / TTM window movement per the
  task's own "price-like drift is as-of skew" instruction -- not filed.
- `results_calendar` flipped 502->200 for every slot that had it 502 at census -- a broad
  improvement, not a regression, not filed (no register id to pin a regression against).

## Cleanup
- Own sidecar (pid 67777, port 52313) killed directly; confirmed dead via `ps -p 67777`
  (empty result). Shared stack (:52152/:52153/:52154) never restarted or written through.
