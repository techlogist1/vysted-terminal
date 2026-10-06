# xadv-keyless-2 — keyless data a stranger hits first: quotes, chart history, screener, news

Stack: own keyless stack :52900 (see xadv-keyless-1). All requests carry `Origin: http://localhost:5173` (the app's dev origin, accepted by the origin guard). No key of any kind in any header.

## Quotes (`GET /quotes/<sym>`; watchlist crypto uses `/crypto/ticker?exchange=binance`, src/modules/watchlist/api.ts:15)
```
AAPL        -> price 333.69, chg% 0.87, provider yfinance, freshness eod, ts 2026-10-02T20:00:01Z (open/high/low/prev_close null)
RELIANCE.NS -> 1167.7, -1.63%, O 1180.1 H 1183.9 L 1160.8 PC 1187.0, provider nse_direct, eod, ts 2026-10-01
SHAILY.NS   -> 3009.1, -1.76%, nse_direct, eod, ts 2026-10-01
KITEX.NS    -> 116.68, -2.40%, O 118.77 H 119.89 L 114.68 PC 119.55, nse_direct, eod, ts 2026-10-01
/crypto/ticker?exchange=binance&symbol=BTC/USDT -> 84588.01, -2.05%, ccxt:binance, ts 2026-10-03T09:42:05Z
/quotes/BTC/USDT -> 404-shape {"code":"not_found","detail":"The data provider has no data for this symbol or series — check the symbol."} (equity route; the app routes crypto to /crypto/ticker, so not a user path)
```
Outside check (NSE archive, direct): https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20261001_F_0000.csv.zip ->
`2026-10-01,...,KITEX,EQ,...,KITEX GARMENTS LTD,118.77,119.89,114.68,116.68,116.75,119.55,...,245777` and
`2026-10-01,...,RELIANCE,EQ,...,1180.10,1183.90,1160.80,1167.70,1167.70,1187.00,...,16771221` — app values match exactly. 2 Oct 2026 is an NSE holiday (Gandhi Jayanti; sidecar/services/locale.py:98), so 1 Oct is the correct last close.

## Chart history (`GET /history/<sym>?timeframe=1d`)
```
KITEX.NS -> 257 bars, last 2026-10-01 O118.77 H119.89 L114.68 C116.68 V245777, provider nse_direct, freshness eod
SPY      -> 251 bars, last 2026-10-02 C769.64, yfinance, eod
BTC/USDT&asset_class=crypto -> 365 bars, last 2026-10-03 C84588.01
BTC-USD (equity default) -> 200 empty series, reason "unknown_symbol" (the app's crypto form is BASE/QUOTE; honest empty state, not filed)
```

## Screener (`POST /screener/run`)
```
{"universe":"custom","custom_symbols":["KITEX.NS","SHAILY.NS","RELIANCE.NS"],"criteria":[]}
-> evaluated 3, skipped 0, coverage "screened 3 of 3 — 0 unavailable"; RELIANCE 1167.7 mcap 1.58e13 PE 21.14; SHAILY 3009.1 PE 79.02; KITEX 116.68 PE null (honest null)
{"universe":"nifty50","criteria":[]} -> 50 of 50, 0 skipped, 467 ms
```

## News (`GET /news?symbols=...`; X-News-Sources newsapi=absent, RSS keyless)
```
symbols=KITEX.NS   -> [] (honest empty)
symbols=SHAILY.NS  -> 1: "Shaily Engineering Plastics Ltd (BOM:501423) (Q1 2027) Earnings Call Highlights..." (Yahoo Finance SHAILY.NS feed)
symbols=RELIANCE.NS-> 2: "RIL Q2 Results: Nuvama sees 17% EBITDA growth..." + a "Wall Street Week Ahead" item tagged RELIANCE (tagging heuristic; not filed — no figure rendered as data)
no symbols         -> general market RSS (mint, ET Markets, Zerodha Pulse) with sentiment scores
/news/sources/status -> {"newsapi":"absent"}
```

Result: the README/onboarding promise "live quotes, charts, news and screeners run right now" with no key holds at the API level, including NSE small caps. Rendering = operator-attended (no window here). One data-labeling defect found in the background EOD warm path is filed separately as xadv-keyless-3.

VERDICT xadv-keyless-2: pass
