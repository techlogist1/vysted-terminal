# xadv-realuser-2 — collision tickers NSE vs US: HAL, IEX, SAIL

Lens: one symbol, two companies. HAL = Hindustan Aeronautics (NSE) / Halliburton (NYSE); IEX = Indian Energy Exchange (NSE) / IDEX Corp (NYSE);
SAIL = Steel Authority of India (NSE) / SailPoint (NASDAQ). None is in r15/battery/manifest.json. Own stack :52910, session region IN (default).
Raw: `xadv-realuser-raw/` s2-collisions.txt, s3-names.txt, s-autocomplete.txt, t-fund-HAL.json, t-price-HAL.json, r-hal.json, r-sail.json.

## Outside truth

https://www.screener.in/company/HAL/consolidated/ — "Hindustan Aeronautics Ltd", "BSE: 541154 | NSE: HAL", "Current Price: ₹4,601 (-1.44%)",
"Market Cap: ₹3,07,703 Crores", "Stock P/E: 33.0", "Book Value: ₹614", "52-Week Range: ₹5,150 / ₹3,479", "EPS (TTM): ₹139.38".
Halliburton/IDEX/SailPoint figures below come from the product's US lane (yfinance) and are used only to show which entity a payload belongs to
(currency USD, names "Halliburton Company", "IDEX Corporation", "SailPoint, Inc.").

## Search + routes (pass)

- `/resolve?q=HAL` -> bound Hindustan Aeronautics (NSE), candidates also list HAL BSE and HALLIBURTON CO US at 1.0. `q=halliburton` -> HAL US 0.97.
  `q=Hindustan Aeronautics` -> HAL NSE 1.0. Autocomplete `HAL` lists both "Hindustan Aeronautics Limited · NSE" and "HALLIBURTON CO · US";
  same for IEX and SAIL.
- `/quotes/HAL` (IN) -> 4601.0 INR nse_direct; with `X-Vysted-Region: US` -> 31.85 USD Halliburton. IEX: 105.98 INR / 232.99 USD. SAIL: 174.5 INR / 20.43 USD.
- `/fundamentals/HAL` (IN) -> HAL.NS "Hindustan Aeronautics Limited", P/E 33.00, EPS 139.38, BV 613.68, 52w 5149.9/3479.1, mcap ₹3.077 lakh cr —
  every figure matches screener. With US header -> "Halliburton Company", USD, P/E 16.68. Region pinning works at the route level.
- The palette's chart path now carries the picked listing's region (`CommandPalette.tsx:355 loadSymbolIntoChart(c.symbol, undefined, c.region)`).

## Research brief: the bound US instrument, the Indian company's numbers (FAIL)

MCP tool `research` {"query":"Halliburton","depth":"quick"} on :52910 (r-hal.json):
- `resolved.resolved` = `{symbol: HAL, name: HALLIBURTON CO, exchange: US, region: US, yahoo_symbol: HAL}` — the research run itself bound Halliburton.
- `structured.price` = ok, provider **nse_direct**, `price 4601.0, currency INR` — Hindustan Aeronautics' close.
- `structured.fundamentals` = ok, provider openbb-mcp, `symbol HAL.NS, market_cap 3,077,033,689,088, pe_ratio 33.003, eps 139.38, revenue_ttm 337,849,800,000`
  — Hindustan Aeronautics' figures.
- `structured.derived.conflicts` = `[]` — no identity conflict, because the openbb-mcp leg carried no company name (`identity_conflict` returns None
  when either name is blank, identity_crosscheck.py:105-106).

`deriveMetrics` (src/modules/research/brief-blocks.tsx) builds the metric cards from exactly these legs, so the "Halliburton" brief shows
Price ₹4,601, P/E 33.0, EPS 139.38, Market cap ₹3.08T as the company's figures, with no warning.

Fresh case of the same class: research {"query":"SailPoint"} (r-sail.json) binds `SAIL / SailPoint, Inc. / US`; price leg = nse_direct 174.5 INR
(Steel Authority), fundamentals leg = yfinance `SAIL.NS "Steel Authority of India Limited"`, mcap ₹72,078 cr, P/E 16.86. Here a conflict line
(similarity 0.0) is raised, but the cards still render SAIL India's price, P/E and market cap under the SailPoint brief.

Root cause (source at the sha): `sidecar/services/research/fast.py:624 symbol = target.symbol` then `snapshot_structured(tool_call, symbol, ...)`
calls `price_data`/`fundamentals` with the bare `{"symbol": "HAL"}` (fast.py:354-361); the tools resolve a bare ticker by the session region
(IN), and neither `target.region` nor a request-region override is passed. The research run has the bound listing in hand and drops it.

The agent's own tools have the same blindness: `fundamentals` takes only `{"symbol"}` (catalog.py `_cap("fundamentals" ...)`), and
MCP `fundamentals {"symbol":"HAL"}` / `price_data {"symbol":"HAL"}` return Hindustan Aeronautics (t-fund-HAL.json, t-price-HAL.json), so an agent
asked about Halliburton in an IN session has no way to fetch Halliburton's data.

## R1-R3

R1: reproducible on the running sidecar at the sha (commands above, outputs saved); world claim carries the screener URL + quote. R2: wrong
money-relevant data shown as true under the user's chosen company -> critical. R3:
- R15-DATA-002 (blocked_tier4, critical) is the frontend-panel half of the bare-ticker-binds-session-region mechanism (files: sidecar-client.ts,
  equity-overview, quotes/fundamentals routers, resolution_policy). The agent-tool half above (tool schema has no region) is that mechanism ->
  ATTACHED to R15-DATA-002 as realuser:5.
- R15-DATA-003 (fixed) fixed only the ownership gate inside research (its certification: "HAL under US not_applicable"); its repro (AMAL
  shareholding) still holds. The research price/fundamentals legs re-querying the bare symbol is a different root cause in fast.py with the
  bound instrument already resolved -> new entry realuser:3 (note: same class as R15-DATA-002/003, distinct file and root cause; triage may merge).

VERDICT xadv-realuser-2: finding realuser:3, realuser:5
