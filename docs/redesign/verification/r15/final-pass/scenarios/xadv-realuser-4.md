# xadv-realuser-4 — renamed companies: old name typed, new name typed

Lens: a screener.in user still calls Sammaan Capital "Indiabulls Housing", Angel One "Angel Broking", Zydus Lifesciences "Cadila",
Patanjali Foods "Ruchi Soya". None is in r15/battery/manifest.json (ZOMATO/SEQUENT/GUJGAS/TATAMOTORS, already in the register, avoided).
Own stack :52910, region IN. Raw: `xadv-realuser-raw/` s4-resolve-renames.txt, s-autocomplete.txt, f-SAMMAANCAP.json, r-ibh.json.

## Outside truth

https://www.screener.in/company/SAMMAANCAP/consolidated/ — "Sammaan Capital Ltd (formerly Indiabulls Housing Finance)", "BSE: 535789 | NSE: SAMMAANCAP",
"Current Price: ₹132 (-2.97%)", "Market Cap: ₹15,388 Cr", "Book Value: ₹164", "52-week Range: ₹193 / ₹129"; P&L "TTM ... Revenue: 7,418,
Net Profit: -7,236, EPS in Rs: -60.32"; quarters Sep 2025 EPS 3.72, Dec 2025 3.79, Mar 2026 -69.92 (Net Profit -8,101), Jun 2026 2.09.

## /resolve (pass)

| typed | bound | former |
|---|---|---|
| `Indiabulls Housing Finance` | SAMMAANCAP 0.99 | IBULHSGFIN |
| `indiabulls housing` | SAMMAANCAP 0.91 | IBULHSGFIN |
| `IBULHSGFIN` | SAMMAANCAP 1.0 | IBULHSGFIN |
| `Sammaan Capital` | SAMMAANCAP 1.0 | |
| `Angel Broking` | ANGELONE 0.99 | ANGELBRKG |
| `Cadila Healthcare` | ZYDUSLIFE 0.99 | CADILAHC |
| `Ruchi Soya` | PATANJALI 0.91 | Ruchi Soya Industries Limited |
| `Kirloskar Oil Engines` (trap: former name of Kirloskar Industries) | KIRLOSENG 1.0 (the current KOEL), KIRLOSIND second with former "Kirloskar Oil Engines Limited" | |

The KOEL trap resolves to the right company (current name beats former name). Good.

## Autocomplete — the search box (FAIL)

`GET /resolve/autocomplete?q=...` (what CommandPalette.tsx:162 `useSymbolAutocomplete` and WatchlistPanel.tsx:190 call on every keystroke):

```
indiabulls housing -> n=0      angel broking -> n=0      cadila -> n=0      ruchi soya -> n=0
IBULHSG -> n=0                 513353 -> n=0             zomato -> ETERNAL (former ZOMATO)  [retired-ticker lane, exact ticker only]
kirloskar oil -> KIRLOSENG
```

`symbol_resolver.autocomplete` (symbol_resolver.py:1637-1708) matches ticker-prefix, name-prefix and name-substring over the three masters, plus
`_retired_symbol_instrument` for an EXACT old ticker. It never reads `former_names.json` (1,996 IN rows, 4,827 US rows, loaded by resolve()'s
former-name fallback) or the BSE scrip-code index. So the user who types the name they remember gets an empty instrument list in the palette and
the watchlist add box, while the same string through /resolve binds at 0.91-0.99. -> realuser:1 (with the scrip-code half from xadv-realuser-1).

R3: R15-DATA-018 (fixed) fixed resolve() for an old TICKER and its note records "autocomplete is still exact-only for a renamed symbol's old
ticker"; R15-UI-039 (fixed) added rename/enrichment stages to autocomplete rows already matched. Neither covers the former-NAME lane nor scrip codes
in autocomplete; their own repros (ZOMATO, GUJGAS) hold. New entry.

## Figures belong to the right entity (pass)

`/quotes/SAMMAANCAP` -> 132.48 INR (screener ₹132). `/fundamentals/SAMMAANCAP` (second call; the first was a Yahoo-429 fallback, see
xadv-realuser-5) -> name "Sammaan Capital Limited", revenue_ttm 7,417.73 cr (7,418), net_income_ttm -7,235.56 cr (-7,236), label "consolidated, sum of 4
filed quarters to 2026-06-30", 52w 192.95/129.0 (193/129), book_value 232.31 **flagged** with reason "disagrees by 28.6% with ... 165.77" (screener
164 — the flag points at the right number). EPS -89.32 vs screener -60.32: the product sums the four filed basic EPS (pre-IHC weighted share
count in Mar-26), screener recomputes on current shares; both are defensible, not filed.

VERDICT xadv-realuser-4: finding realuser:1
