# xadv-realuser-5 — demerged companies: ITC Hotels, Siemens Energy India, Raymond Lifestyle

Lens: the new demerged entity typed by name; do the figures belong to the new entity, not the parent? Not in r15/battery/manifest.json
(TMPV/TATAMOTORS avoided). Own stack :52910, region IN. Raw: `xadv-realuser-raw/` s5-demerged.txt, f-ENRIN.json, f-SIEMENS.json,
r-itch.json, r-rlsl.json, r-sricc.json.

## Outside truth

https://www.screener.in/company/ITCHOTELS/consolidated/ — "Current Price: ₹159 (down 3.42%)", "Market Cap: ₹33,019 Crore", "Stock P/E: 35.8",
"Book Value: ₹56.0", "52-week Range: ₹227 / ₹137", "Sales: ₹4,260 Crores", "Net Profit: ₹869 Crores", "listed on the stock exchanges on 29 Jan'25".
https://www.screener.in/company/ENRIN/consolidated/ — "Siemens Energy India Ltd", "BSE: 544390 | NSE: ENRIN", "Incorporation: 2024" (the page
rendered no live figures to the fetcher, so ENRIN figures are checked for entity only).

## Resolution (pass) — see xadv-realuser-3: `ITC Hotel` -> ITCHOTELS, `Siemens Energy` -> ENRIN, `Raymond Lifestyle` -> RAYMONDLSL; parents bind on their own names.

## Figures (pass)

- `/quotes/ITCHOTELS` 158.51 INR -3.42% (screener ₹159, -3.42%). `/fundamentals/ITCHOTELS`: name "ITC Hotels Limited", mcap 33,069 cr (33,019),
  BV 55.97 (56.0), 52w 226.63/137.3 (227/137), revenue_ttm 4,259.9 cr (4,260), net_income_ttm 864.0 cr (869), first_trade_date 2025-01-29 (listing
  29 Jan'25), shares 208.3 cr. These are ITC Hotels', not ITC Ltd's. P/E 38.25 vs 35.8 is the R15-DATA-013 trailing-EPS class (not re-filed).
- `/fundamentals/ENRIN` (2nd call): "Siemens Energy India Limited", listing_date 2025-06-19, revenue_ttm 9,436 cr, net_income_ttm 1,488 cr (NSE filed,
  4 quarters to 2026-06-30), shares 35.6 cr — the demerged energy entity, not Siemens Ltd (`/fundamentals/SIEMENS`: "Siemens Limited", separate figures).
- `/quotes/RAYMONDLSL` 200 in 0.71 s.

## Observation, not filed: first call serves a sparse fallback, research drops legs on cold names

The FIRST `/fundamentals/SIEMENS` / `ENRIN` / `SAMMAANCAP` call returned provider `openbb-mcp` with name/book value/EPS/52w null and an empty
`field_meta`; the immediate second call returned the full yfinance payload. Sidecar log at those seconds:
`WARNING services.provider_registry: provider yfinance failed for fundamentals, falling through: yfinance fundamentals rate-limited for 'SIEMENS': Too Many Requests`
(48 such lines in logs/xadv-realuser-main.log during this run, with the final pass and another adversary sharing the same egress IP).
Research `quick` on cold names (ITC Hotels and Indiabulls Housing run concurrently; Raymond Lifestyle and Sri Chakra Cement run alone) dropped the
price and/or fundamentals leg at the 6 s box (`"fundamentals timed out after 6s — dropped"`, research/fast.py:177, the R15-RESEARCH-027 time box).
Direct probe of the upstream: `curl https://query1.finance.yahoo.com/v8/finance/chart/KEMP.BO` -> 200, `quoteSummary` without crumb -> 401; the
throttle shows in the app's own yfinance calls, which a single direct call cannot reproduce. Under R1(b) this is an upstream-throttle condition
plus a deliberate time box, so it is recorded here and not admitted. (The empty `field_meta` on the throttled fallback may deserve a look: the
panel then cannot say why book value/EPS are blank.)

VERDICT xadv-realuser-5: pass
