# DS-4 — renames, near-namesakes and same-ticker collisions (investor lens)

Stack: own clean-profile sidecar :52810 built from final-cand (d38b5d1a), region IN, Origin http://localhost:5173.
Raw: `raw/investor/ds4.json` (36 calls), `raw/investor/gstl.json` (GSTL disclosure lanes).
Outside witness: NSE Emerge equity list https://nsearchives.nseindia.com/emerge/corporates/content/SME_EQUITY_L.csv (captured 3 Oct 2026).

## Renames — pass
- `zomato`, `ZOMATO`, `Zomato Ltd` resolve to ETERNAL with former_name ZOMATO; autocomplete lists ETERNAL first, annotated.
- `SEQUENT` and `Sequent Scientific` resolve to VIYASH with former_name SEQUENT.

## Collisions via /resolve — pass
- `ZEAL` and `SEL` return needs_disambiguation true with both companies (NSE SME vs BSE).
- `ZEAL.BO` binds BSE Zeal Aqua Ltd (INE819S01025, 539963); `SEL.BO` binds BSE Sanathnagar Enterprises. Their announcements and shareholding come back BSE-only (no NSE namesake rows).

## GSTL — finding investor:5 (regression of R15-CODE-DATA-001; class R15-LEAD-059)
- NSE `GSTL` is Globesecure Technologies (NSE Emerge, ISIN INE00WS01056 per the NSE list). BSE `GSTL` (540654) is Globalspace Technologies, ISIN INE632W01016 — a different company.
- `/resolve?q=GSTL` binds NSE Globesecure at confidence 1.0, needs_disambiguation false, stamped isin INE632W01016 and bse_code 540654 (the other company's).
- Consequences in the same sidecar:
  - `/disclosures/results?symbol=GSTL`: 10 events, every one `company: "GlobalSpace Technologies Limited"`, exchange BSE.
  - `/disclosures/announcements?symbol=GSTL`: BSE Globalspace rows merged with NSE Globesecure rows under one symbol.
  - `/disclosures/corporate-actions?symbol=GSTL`: a BSE rights issue (2023-11-03) and a BSE final dividend of 0.2 merged beside NSE Globesecure's rights 3:4.
  - `/disclosures/shareholding?symbol=GSTL`: NSE pattern with `split_source: "BSE"` (FII 0.15% derived from the BSE filing).
- Mechanism (read in final-cand): `symbol_resolver._bse_row_is_same_company` (:1493-1511) accepts the BSE row when `SequenceMatcher` over `_company_name_key` is >= `_SAME_COMPANY_NAME_RATIO` = 0.75 (:1480). "globesecuretechnologies" vs "globalspacetechnologies" scores 0.826 (computed with stdlib difflib), so `dual_listed_bse_code` (:768) returns 540654 and `_enrich_instrument` stamps the ISIN. The shared "technologies" suffix carries the ratio. FOCUS (the LEAD-059 verifier name) still disambiguates correctly.

## Autocomplete — finding investor:6 (new defect)
- `/resolve/autocomplete?q=Zeal Aqua` -> []; `q=Sanathnagar Enterprises` -> [].
- `q=ZEAL.BO` -> only NSE ZEAL (Zeal Global Services, ZEAL-SM.NS); `q=SEL.BO` -> NSE Sungarner first, no Sanathnagar.
- `symbol_resolver.autocomplete` (:1637) skips every BSE row whose ticker is in the NSE master, on the assumption that same ticker = same company; the .BO pin is lost because matching runs on the stripped ticker. In the picker, the BSE company of a collision cannot be found by its ticker or its name.

## Attached
- Bare AMAL binding NSE under IN with no chooser (DS-1 observation) attached to R15-DATA-002 (blocked_tier4), in ATTACHED.json.

VERDICT DS-4: finding investor:5 investor:6
