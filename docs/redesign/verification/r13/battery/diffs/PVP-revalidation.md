# PVP — PVP Ventures Ltd (NSE PVP / BSE 517556; SPARE, multi-segment loss-maker) — RE-VALIDATION diff vs reference pack

Collected 2026-07-10T14:44Z (ref pack 2026-07-10T10:07:46Z). Battery **SPARE** — not in the original fix-target set.

## Resolve

| Probe                        | Result                                                                     | Verdict                              |
| ---------------------------- | -------------------------------------------------------------------------- | ------------------------------------ |
| Bare "PVP"                   | Binds PVP Ventures Limited NSE conf 1.0                                    | MATCH                                |
| Full name "PVP Ventures Ltd" | **Binds at 1.0, no disambiguation**                                        | **FIX CONFIRMED** (Ltd/Limited seam) |
| Enriched fields              | isin INE362A01016 = pack; bse_code 517556 = pack; industry "Conglomerates" | MATCH                                |

## Field table

| Field                   | Reference (as-of)                                          | Collected (as-of)                                                                                            | Verdict                                                                                                                                                                                                                                                                                             |
| ----------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Mcap                    | ₹721 Cr                                                    | ₹718.7 Cr                                                                                                    | MATCH (~0.3%)                                                                                                                                                                                                                                                                                       |
| PE                      | null (loss-making, honest)                                 | null (eps negative)                                                                                          | MATCH — both sides honestly null                                                                                                                                                                                                                                                                    |
| PB                      | 3.30                                                       | 4.00                                                                                                         | **MISMATCH (~21%)** — app book_value 6.90 implies pack's basis (~8.39) differs; a real app-vs-world basis divergence but not one of the fixes under test (same shape as the original battery's GEE PB 2x mismatch)                                                                                  |
| 52w high/low            | 39.9 / 18.3                                                | 39.41 / 18.49                                                                                                | MATCH (~1%)                                                                                                                                                                                                                                                                                         |
| Div yield               | 0.00% (affirmed)                                           | **0.0 — affirmed_zero, `dividend_per_share_ttm: 0.0`, field_meta reason "no dividends paid (trailing 12m)"** | **FIX CONFIRMED — the null-vs-affirmed-zero mechanism correctly renders a stateable 0.0**, not a bare null, because yfinance's dividend series for PVP has real depth (10 historical dividend events, most recent 2004 — old but present, giving the ≥12-month-depth anchor the mechanism requires) |
| Shareholding (Mar 2026) | promoter 61.30, FII 0.50, DII 0.00, public(non-inst) 38.20 | promoter 61.3, FII 0.5, DII 0.0, public(non-inst) 38.2, `split_source: BSE`, `split_as_of: 2026-03-31`       | **MATCH (exact)** — FII/DII split fix HOLDS                                                                                                                                                                                                                                                         |

## field_meta (null-reason stamping fix)

36 total fields; 7 null (`pe_ratio`, `forward_pe`, `peg_ratio`, `dividend_yield`, `dividend_per_share`, `earnings_growth`, `identity_note`), all stamped with an honest reason. **FIX CONFIRMED.** Note `dividend_yield`/`dividend_per_share` are stamped unavailable at the RAW yfinance-info level even though the DERIVED `dividend_per_share_ttm` leg (a separate, later-computed field) correctly resolves to the affirmed 0.0 above — two different fields, both honestly provenance-tagged, no conflict.

## Income statement

`/fundamentals/PVP/income` — 200, 5 periods (2022–2026), 51 line items populated.

## Research bundle (gather_fast, 27.9s)

- **News leg**: honest decline, note: _"No on-entity news found for PVP — 135 item(s)... off-entity/off-topic and dropped."_ **FIX CONFIRMED.**
- **Filings leg**: `ok: true`, provider `nse+bse`, 20 announcements (NCD amendment, Regulation 30 disclosures, trading-window closure — matches the live corporate-action texture the reference pack itself flagged). **FIX CONFIRMED.**
- **Range/mcap-witness legs**: `range_52w_exchange` attached, `market_cap_witness` attached — no divergence conflicts fired (agreement).
- Web backend: searxng, 0 citations this round (see summary).

## New finding — historical shareholding split: CLEAN

Unlike TCI/ADOR/APEX, PVP's 86 quarterly patterns show **zero corrupted (>100%) rows** — the historical-split defect does NOT reproduce here. Bounds the defect: it is name-specific (likely tied to a particular BSE XBRL filer/format quirk), not a universal regression in the nearest-quarter fallback.

## Verdict

**CLEAN, with the battery's clearest affirmed-zero win.** PVP is the strongest evidence the D56 dividend-TTM fix generalizes correctly: real (if old) dividend history gives the series enough depth to affirm a true zero rather than decline to null — contrast with DEN (below), whose dividend series is completely empty and therefore cannot clear the same depth bar. Ltd/Limited seam, field_meta, FII/DII split, and filings wiring all hold. One real PB basis mismatch noted (pre-existing app-vs-world divergence class, not part of this fix wave).
