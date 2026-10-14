# ADOR — Ador Welding Ltd (NSE ADOR / BSE 517041; SPARE, small/mid boundary; former Advani-Oerlikon) — RE-VALIDATION diff vs reference pack

Collected 2026-07-10T14:43Z (ref pack 2026-07-10T10:07:46Z). Battery **SPARE** — not in the original fix-target set.

## Resolve

| Probe                                 | Result                                                                                      | Verdict                              |
| ------------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------ |
| Bare "ADOR"                           | Binds Ador Welding Limited NSE conf 1.0                                                     | MATCH                                |
| Full name "Ador Welding Ltd"          | **Binds at 1.0, no disambiguation**                                                         | **FIX CONFIRMED** (Ltd/Limited seam) |
| Former name "Advani-Oerlikon Limited" | Not probed this round (out of AFFECTED-FIELD scope)                                         | n/a                                  |
| Enriched fields                       | isin INE045A01017 = pack; bse_code 517041 = pack; industry "Specialty Industrial Machinery" | MATCH                                |

## Field table

| Field                   | Reference (as-of)                                           | Collected (as-of)                                                                                           | Verdict                                                                                                                                                                                                                           |
| ----------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Mcap                    | ₹2,309 Cr                                                   | ₹2,305.5 Cr                                                                                                 | MATCH (~0.2%)                                                                                                                                                                                                                     |
| PE                      | 27.5                                                        | 28.17                                                                                                       | MATCH (~2.4%)                                                                                                                                                                                                                     |
| PB                      | 4.16                                                        | 4.16                                                                                                        | MATCH (exact)                                                                                                                                                                                                                     |
| 52w high/low            | 1360 / 848                                                  | 1360.0 / 848.0                                                                                              | MATCH (exact)                                                                                                                                                                                                                     |
| Div yield               | 1.75%                                                       | 2.24%                                                                                                       | MISMATCH (~28% relative; basis/timing difference — ADOR has a live FY26 final dividend of ₹23/share with record date 16-Jul-2026, still in the future as of collection — worth a closer look but not one of the fixes under test) |
| Shareholding (Mar 2026) | promoter 53.76, FII 0.37, DII 12.63, public(non-inst) 33.26 | promoter 53.76, FII 0.37, DII 12.63, public(non-inst) 33.24, `split_source: BSE`, `split_as_of: 2026-03-31` | **MATCH (near-exact)** — FII/DII split fix HOLDS                                                                                                                                                                                  |

## field_meta (null-reason stamping fix)

36 total fields; 7 null (`peg_ratio`, `roe`, `roa`, `current_ratio`, `quick_ratio`, `free_cash_flow`, `identity_note`), all stamped `status: unavailable, reason: "provider did not publish this field"`. **FIX CONFIRMED.** Note: `roe` null here vs pack's 15.8% is a genuine provider-coverage gap (app doesn't have the figure at all) — but it is now honestly labeled rather than a bare unexplained null.

## Income statement

`/fundamentals/ADOR/income` — 200, 4 periods (2023–2026), 54 line items populated.

## Research bundle (gather_fast, 31.6s)

- **News leg**: `ok: true`, `data: []`, note: _"No on-entity news found for ADOR — 135 item(s) returned by the news feed were off-entity/off-topic and dropped."_ Honest decline. **FIX CONFIRMED.**
- **Filings leg**: `ok: true`, provider `nse+bse`, 20 exchange announcements. **FIX CONFIRMED.**
- **Range/mcap-witness legs**: `range_52w_exchange` = {1360.0, 848.0} — exact agreement with provider, no conflict. `market_cap_witness` attached, no divergence flagged.
- Web backend: searxng, 0 citations this round (see summary).

## New finding — historical shareholding split corruption

82 of 85 quarterly patterns (all pre-2026-03-31, plus a corrupted stretch back to 2005) carry the same nonsensical FII/DII/institutions values (hundreds to ~1500%) seen on TCI. Current quarter is correct. Same pre-existing, out-of-scope defect — see TCI-revalidation.md and the summary for detail.

## Verdict

**CLEAN.** Ltd/Limited seam, field_meta null-reason stamping, FII/DII split merge, filings wiring, and honest news decline all hold on ADOR. One real but modest dividend-yield divergence (unrelated to the fixes under test, live corporate-action timing) and the same historical-shareholding-split defect as TCI.
