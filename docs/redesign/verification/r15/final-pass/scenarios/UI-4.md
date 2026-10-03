# UI-4 — screener panel: count, missing values last, empty and error states (final-adv-maintainer, d38b5d1a)

Harness: scratch vitest jsdom, real `<ScreenerPanel/>` + real store against own sidecar :52825 (region IN), custom universe INFY.NS, TCS.NS, NIFTYBEES.NS (ETF, no market cap / sector), PAYTM.NS, ZZZNOTREAL, RELIANCE.NS. Evidence: UI-4/harness-screener.json, harness-formula.json, server-sort.txt.

- Count: "5 matched · showing top 5 by market cap (5 evaluated, 1 skipped, 509 ms)" plus the coverage line "PARTIAL screened 5 of 6 — 1 unavailable … 1 rate-limited" (upstream 429 in that window; "1 not found" on the next run). ✓
- Missing values last: server `sort_by=market_cap` asc and desc both end with NIFTYBEES (null) (server-sort.txt); in the panel, clicking Market cap (asc, then desc) and the client-only Sector column (both directions) keeps NIFTYBEES ("—") last every time. ✓
- Empty: a no-match threshold renders "No rows matched the criteria — No stocks in this universe passed every filter. Loosen a threshold or reset to the defaults." with a Reset filters action. ✓
- Error: a malformed formula typed in the panel is caught client-side ("Formula: unexpected end of formula (col 11)" + Retry), never sent. ✓ (A criterion the server rejects with a 422 list detail renders "Screener failed: [object Object],…" via src/store/screener.ts:493-501 — only reachable with a criterion the builder cannot produce, so not filed; noted as a class sibling of the fixed R15-CODE-PLATFORM-011.)
- **maintainer:3 (low):** the freshness line prints raw float seconds on every fresh run — "quotes 41.64699196815491s ago · valuation 41.64699912071228s ago · deep fields 46.1444091796875s ago". `fmtAgo` (src/modules/screener/ScreenerPanel.tsx:29-31) subtracts the float epoch from a floored `now` and prints the difference unrounded under 60 s.

VERDICT UI-4: finding maintainer:3
