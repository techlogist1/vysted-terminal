# xadv-keyless-8 — the default first-launch cockpit and error messages, keyless (API level)

Default layout (src/config/default-layout.ts:33-54): chart, equity-overview, watchlist, news, portfolio — all keyless-capable panels. Region default IN (src/lib/region.ts:39).

## Default panels' data, own keyless stack :52900
```
chart default ^NSEI (chart-drawings.ts:53-54)      GET /history/%5ENSEI?timeframe=1d -> 246 bars, last 2026-10-01 C 22421.95, yfinance, eod
IN watchlist seeds (symbols.ts:49-54) GET /quotes?symbols=RELIANCE.NS,TCS.NS,HDFCBANK.NS,INFY.NS,NIFTYBEES.NS,%5ENSEI
   -> RELIANCE 1167.7, TCS 2075.0, HDFCBANK 721.2, INFY 1035.0, NIFTYBEES 256.5 (nse_direct), ^NSEI 22421.95 (yfinance)
   outside: NSE UDiFF bhavcopy 2026-10-01 ClsPric HDFCBANK 721.20, INFY 1035.00, NIFTYBEES 256.50, TCS 2075.00 — exact match
portfolio  GET /portfolio/positions -> [] (empty profile, honest empty)
news       see xadv-keyless-2 (RSS keyless; NewsAPI absent)
equity overview on an index: GET /fundamentals/%5ENSEI -> {"code":"rate_limited","detail":"The data provider is throttled right now — try again shortly.","action":"Wait a minute, then retry."} (yfinance 429s on this shared IP, main.log "Too Many Requests"; environment, honest message)
```
Off the default layout: Macro opens on FRED/DGS10 (MacroPanel.tsx:15-16), which needs a key: `GET /macro/series/CPIAUCSL?provider=fred` -> 502 "FRED needs a free API key ... or switch the series provider to ECB, IMF, or World Bank, which need no key." — honest and actionable; the retry storm on it is fixed (R15-UI-015) and the search-side flattening is R15-LEAD-067 (open). Not re-filed.

## Error messages at the edge
```
GET /quotes/NOTAREALTICKER123 -> {"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found","action":"Check the symbol or series id."}
GET /resolve?q=kitex&region=IN -> resolved KITEX, Kitex Garments Limited, NSE, KITEX.NS, ISIN INE602G01020, bse_code 521248
GET /resolve/autocomplete?q=shaily -> SHAILY, Shaily Engineering Plastics Limited, SHAILY.NS, bse 501423
POST /agents/copilot/invoke (truncated JSON) -> 422 json_invalid
POST /agents/nosuchagent/invoke -> {"detail":"unknown agent: 'nosuchagent'"}
GET /health with Origin http://evil.example -> 403 {"detail":"origin not allowed"}
POST /llm/keys/validate {"provider":"openrouter"} with no key -> {"ok":false,"reason":"not_configured","detail":"No API key is set for OpenRouter."}
```
All honest, actionable, no stack traces, no key echoes.

VERDICT xadv-keyless-8: pass
