# UI-2 — portfolio P&L vs raw /quotes, no fabricated zero, mixed currency, CSV (final-adv-maintainer, d38b5d1a)

Harness: scratch vitest jsdom (never committed), real `PortfolioPanel` + real `fetchPositionQuotes` against own sidecar :52825; only `downloadCsv` stubbed to capture the CSV text. Holdings AAPL 10@180, INFY 20@1500, TCS 5@3500, ZZZNOTREAL 1@10 (bare symbols — what both the add form and the agent's portfolio_add_position store). Evidence: UI-2/harness-portfolio.json (raw quotes, rendered rows, panel text, CSV) per region.

## Region IN — pass on every criterion
- INFY: raw /quotes INR 1035 → row ₹1,035.00 / ₹20,700.00 / -₹9,300.00 (-31.00%) = (1035−1500)×20 ✓. TCS (2075−3500)×5 = -₹7,125.00 ✓.
- AAPL (upstream 429 in that window) and ZZZNOTREAL (404): "—" in every money cell, header "2 without a live quote", banner "Couldn't refresh live quotes"; totals cover only resolved rows (₹31,075.00). No fabricated zero.
- CSV equals the table (Currency column present, unresolved rows blank).

## Region US — mixed currency handled, but one lot is re-priced against another listing
- Mixed USD+INR: Wt column dropped, totals per currency with the reason "mixed currencies — totals per currency", CSV Weight % blank ✓.
- **maintainer:2 (high):** the same INFY lot (entered at ₹1,500 under IN) is now quoted against the NYSE ADR (raw /quotes/INFY with X-Vysted-Region US → USD 11.04) and its cost is relabelled `$1,500.00`: row `-$29,779.20 (-99.26%)`, header `Total P&L: -$28,242.30 (-88.81%)`, CSV the same. The holding stores no listing/currency (`Holding` in src/store/portfolios.ts) and `fetchPositionQuote` (src/modules/portfolio/api.ts) prices it under the session region, so a region switch (Settings, or the agent's set_region) silently turns a ₹ lot into a fabricated USD loss — the portfolio analogue of R15-DATA-001's colliding-ticker class.

Writes reading back from the blob are covered under UI-1.

- **R3 re-check (post-LS-3):** class sibling of R15-DATA-002 (blocked_tier4, DECISIONS 4.15) — bare tickers bind to the session region; 4.15's scope and option (a) cover the watchlist pick and the agent add_to_watchlist leg only, not the portfolio Holding. Kept as its own site (register_id R15-DATA-002 recorded on maintainer:2); the sidecar side shows the same binding (/fundamentals/META under IN = META.BO 'String Metaverse Limited', LS-3/kill-probes.txt).
VERDICT UI-2: finding maintainer:2
