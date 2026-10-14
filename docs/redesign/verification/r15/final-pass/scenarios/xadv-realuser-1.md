# xadv-realuser-1 — thin BSE-only name: Cochin Minerals & Rutile (BSE 513353)

Lens: a screener.in user searching a BSE-only micro-cap by partial name, by BSE scrip code and by a misspelling.
Head d38b5d1a2487bd52fe8a7e741a3a5266e3206611, own stack :52910 (main) / :52911 (openbb-mcp) / :52912 (sec-edgar-mcp) from
`$SCRATCH/final-cand/src-tauri/binaries`, data dir `$SCRATCH/final-xadv-realuser-data` (seed copy, keystore `{"secrets": {}, "migrated": true}`).
Not in r15/battery/manifest.json. Raw outputs: `xadv-realuser-raw/` (s1-resolve.txt, s1-quote.txt, s1-fund.json, s-autocomplete.txt, r-cochin.json).

## Outside truth

https://www.screener.in/company/513353/ — "Cochin Minerals & Rutile Ltd", "BSE Code: 513353" (no NSE code), "Current Price: ₹293 (as of Oct 1)",
"Market Cap: ₹230 Cr", "Stock P/E: 9.36", "Book Value: ₹220", "52-Week Range: ₹330 / ₹197", "Sales: ₹344 Crores / Net Profit: ₹22 Crores" (TTM).
(BSE api.bseindia.com ComHeadernew/getScripHeaderData answered Akamai "Access Denied" to curl — saved s1-bse-*.json; screener is the reference.)

## Search resolution (GET /resolve, region IN)

| typed | result |
|---|---|
| `cochin minerals` | bound COCHINM, BSE, conf 0.92, bse_code 513353, ISIN INE105D01013 |
| `513353` (scrip code) | bound COCHINM conf 1.0 |
| `COCHINM` | bound conf 1.0 |
| `cochin minerals and rutile` | disambiguation, COCHINM first (0.807) |
| `cochin minrals` (misspelling) | disambiguation, COCHINM first (0.62; US Namib Minerals 0.64 sorted below) |
| `cochin` | disambiguation: Cochin Shipyard / Cochin Minerals / Cochin Malabar (all 0.97) — correct |

`/resolve` is good. The **name shown everywhere is the BSE master row `Cochin Minerals & Rutiles Ltd-$`** (the company is "Cochin Minerals & Rutile Ltd").
310 of 5,042 rows in `sidecar/services/resolver_masters/bse_instruments.json` end in `-$`; no code at the sha strips it
(grep of sidecar/services and src/lib for the suffix: 0 hits). It renders verbatim in the palette (`src/components/CommandPalette.tsx:364 {c.name}`)
and the watchlist picker (`src/modules/watchlist/WatchlistPanel.tsx:453 {c.name}`).

## Autocomplete (the search box the palette and watchlist actually use)

`GET /resolve/autocomplete?q=513353` -> `{"query":"513353","region":"IN","candidates":[]}` (also `q=5133` -> []), while `/resolve?q=513353` binds at 1.0.
`symbol_resolver.autocomplete` (sidecar/services/symbol_resolver.py:1637-1708) scores only ticker-prefix / name-prefix / name-substring; it has no
scrip-code lane (and no former-name lane, see xadv-realuser-4). The palette's symbol rows come only from `useSymbolAutocomplete`
(CommandPalette.tsx:162), so a scrip code typed into the palette lists no instrument. -> finding realuser:1.

## Quote (GET /quotes/{COCHINM | COCHINM.BO | 513353.BO | 513353})

All four: `price 293.4, change -5.4 (-1.81%), volume 3677, O/H/L 295/303/293, prev_close 298.8, INR, provider bse, freshness eod, 2026-10-01`.
Matches screener's ₹293 (Oct 1; Oct 2 was a holiday). Pass.

## Fundamentals (GET /fundamentals/COCHINM)

name "Cochin Minerals and Rutile Limited" (yfinance), market_cap 232.5 cr (screener 230), book_value 219.49 (220), 52w 330.0/197.1 (330/197),
revenue_ttm 343.67 cr (344), net_income_ttm 21.62 cr (22), dividend_yield 2.73% (2.73%). P/E 10.76 vs screener 9.36 is the trailing-EPS class
of R15-DATA-013 (not re-filed); ROE/ROCE differ by basis (TTM vs last FY) — not a defect.

**But the same response carries**
`identity_note: "The fundamentals provider (openbb-mcp) reports the company name 'Cochin Minerals and Rutile Limited' for COCHINM, which materially
disagrees with the resolver's canonical name 'Cochin Minerals & Rutiles Ltd-$' (token-set similarity 40% < 50%). This can indicate a symbol rename
or a mis-resolution; the identities are NOT reconciled automatically."`

## Research brief (MCP tool `research`, depth quick, query "Cochin Minerals and Rutile")

Bound COCHINM; price leg ok (bse 293.4); fundamentals leg ok (openbb-mcp: market cap, EPS 27.61, revenue, growth). `structured.derived.conflicts`
carries the same `identity_conflict` (similarity 0.4, sources "Cochin Minerals & Rutiles Ltd-$ (resolver (canonical master))" vs
"Cochin Minerals and Rutile Limited (openbb-mcp)"). `src/modules/research/brief-blocks.tsx:266 conflictLines` renders every conflict into the
brief, so the brief tells the user its own (correct) figures may belong to another company.

Root cause (sidecar/services/identity_crosscheck.py:46-87): tokens = `[a-z0-9]+` minus corporate suffixes; `&` yields no token but the word `and`
is a token, and the BSE master's own spelling variant ("Rutiles") costs a second token: {cochin, minerals, rutiles} vs {cochin, minerals, and, rutile}
= 2/5 = 0.40 < 0.50. The resolver already canonicalizes `&`⟺`and` for exactly this seam (symbol_resolver.py `_NAME_CANON_MAP`), the cross-check
does not. -> finding realuser:2 (false identity conflict + the raw `-$` name shown as the company name).

Checked as a control (6 more BSE-only `&` names via /fundamentals, amp.out): CIANAGRO, BHATIA, SERA, LUDLOWJUT, INDGELA -> identity_note null
(the `and` token alone does not trip a long name; it trips when one more token differs, as here).

## R3 duplicate check

- realuser:1 — R15-UI-039 (fixed: autocomplete skipped rename+enrichment stages) and R15-DATA-018 (fixed: renamed stock by old ticker) are
  different lanes; R15-LEAD-028 (fixed) covers scrip-code addressing on data routes (holds: /quotes/513353.BO works). No entry names
  autocomplete + scrip code. New.
- realuser:2 — register search for `-$`, `identity_conflict` false positives, `identity_crosscheck`: none. New.

VERDICT xadv-realuser-1: finding realuser:1, realuser:2
