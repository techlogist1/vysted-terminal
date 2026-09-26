# RC1 data-pack re-collection (rc1-datapack), gate round 2

Candidate sha `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`. This replaces the DATAPACK.md/
datapack.json that were on disk before this run, which were from an **earlier** RC1
candidate (`4097dac4`, gate round 1, 2026-09-25) — a different sha.

Own sidecar booted from `rc1-cand/sidecar` on a fresh copy of `rc1-seed-data` (isolated,
keyless), port 52313. Ran `scripts/r15/collect_battery.py --port 52313 --force` from a
minimal copy tree (`scratchpad/rc1-pack`) so the census baseline in
`docs/redesign/verification/r15/battery/collected/` was never overwritten. All 24 battery
slots collected; raw output copied to `r15/rc1/battery/collected/`.

**Environment note:** this sidecar's own background `fundamentals_warm` cache job hammered
Yahoo concurrently with the collector (repeated 429s, one observed 56s circuit-open window
during P15 SUMAX). Self-inflicted noise from a freshly-booted sidecar, not a product defect
— matches the same class already on record from gate round 1.

## Method

Two passes, per the task brief:

1. **Targeted**: 42 fixed register entries whose repro/evidence names a battery symbol
   (word-boundary match against the register, not substring — substring matching
   over-counts on common words like SAFE/ICON/CSL). 10 symbols implicated: AMAL, DAL, SIFY,
   DHANBANK, SMR, JNPR, ELCIDIN, SUMAX, VIYASH, CREST. Re-ran each entry's own stated repro
   live against the rc1 candidate and read `field_meta` (status/reason), not just the raw
   value, since several of these entries were fixed by adding a cross-check gate rather than
   changing the number.
2. **Broad**: `scratchpad/rc1-pack/redo_diff.py` (scratch, not committed) flattens the fresh
   rc1 collected JSON and looks up every census-time `match` field (from
   `docs/redesign/verification/r15/battery/diffs/*.json`) against the same outside/pack
   value the census diff already recorded, across all 24 slots. Output:
   `r15/rc1/rediff_out.json`.

## Targeted re-diff: 20 of 42 fixed entries re-probed directly

18 hold as fixed (DATA-002, 004, 005, 006, 013, 014, 017, 018, 052, 057, 059, 060,
LEAD-011, LEAD-015, LEAD-028 for its certified routes; DATA-003/022 inconclusive — BSE's
own shareholding index returned 403 Forbidden for every BSE-only symbol this run, not just
the entries' symbols, so this is an upstream block, not a symbol-specific regression). The
remaining 22 fixed entries (portfolio-agent flows, statement-depth/pledge/corporate-action
gaps, field-meta cosmetics) were not individually re-probed this pass — see
`docs/redesign/verification/r15/rc1/datapack.json` `not_individually_re-verified_this_pass`.

**2 regressions found** (both previously "fixed", both fail on their own original repro):

### R15-DATA-008 (SIFY currency mislabel) — still broken

`GET /fundamentals/SIFY` on the rc1 candidate returns the exact same numbers the original
defect cited: `revenue_ttm: 46506049536.0`, `net_income_ttm: -912369984.0`, top-level
`currency: "USD"`. The fix added a separate `financial_currency: "INR"` field and correctly
withholds `price_to_sales` ("mixes bases... withheld"), but `revenue_ttm`/`net_income_ttm`
still carry `status: "ok"`, no `reason`, and are not gated the same way — so a consumer that
reads `currency` next to `revenue_ttm` (exactly what `EquityOverviewPanel.tsx` and
`brief-blocks.tsx` do, per the entry's own root-cause note) still sees "$46.5B revenue" for
a ~$492M company. The register's own batch-23 note already flagged this exact suspicion
("may have resurfaced or is incompletely fixed... not independently re-verified") — this
drive confirms it live on the current candidate.

### R15-DATA-058 (SIFY (ADR) name-search ranking) — still broken

`GET /resolve?q=Sify+Technologies+Ltd+(ADR)` now includes SIFY in the candidate list
(previously it was excluded entirely by the 6-candidate cap) — a partial improvement — but
SIFY (confidence 0.913, the highest score in the list) still sorts **last**, behind five
weaker Indian-locale matches (ASMTEC 0.80, IKOMA/EMIAC/RELICTEC/7TEC ~0.766). The fix_shape
called for score to dominate locale "beyond a margin" in the fuzzy band; an 11-point margin
between the top and bottom scores is not a small one, and the ranking still buries the
correct answer.

## Broad scan: 13 slots flagged, all explained as mapper artifacts, zero real regressions

`redo_diff.py`'s heuristic field-path mapper flagged 13 slots. Every flag inspected by hand
is one of: pack figures in INR crore vs rc1's raw-rupee scale (`revenue_ttm` on
VIYASH/JNPR/CHTR/ICON/JUMBO/AMAL/SMR/VERTEX), pack percent-scale vs rc1 decimal-scale
(`roe`/`debt_to_equity` on the same slots), a sector-label variant ("Financials" vs
"Financial Services" on CSL), or fields the app now correctly serves null/withheld
(JONJUA `debt_to_equity`, ONC's US-only fields). None is a genuine value change once
rescaled — consistent with the mapper's documented limitation (field paths in
`BATTERY_DIFFS.md` are prose, not JSON pointers).

## Not filed (price-like / as-of skew)

Per task instruction, no price-derived drift (P/E, P/B, market cap, 52-week range) was
filed regardless of direction — none of the 10 implicated symbols showed anything beyond
ordinary 1-week movement on those fields.
