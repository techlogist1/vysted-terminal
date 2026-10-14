# xadv-realuser-6 — agent chat on a collision name and a renamed name, plus the old ticker typed straight into the data routes

Lens: the same screener.in user asks the copilot in plain English instead of searching. Own stack :52910, direct POST
`/agents/copilot/invoke` (provider ollama, model llama3.1:8b, mode agent, autonomy ask, `X-Vysted-Region: IN`), each run under the
`/tmp/vysted-r15-ollama.lock` (one call per hold, the trap released it). The OpenRouter lane was not run: `vy.py` refuses non-GET calls
outside ports 52100-52399, and the keystore is empty by design. Raw: `xadv-realuser-raw/` a-hal-llama.jsonl, a-ibh-llama.jsonl,
t-fund-HAL.json, t-price-HAL.json, t-price-IBH.json, t-resolve-IBH.json.

## Outside truth

https://www.screener.in/company/HAL/consolidated/ — "Hindustan Aeronautics Ltd", "Current Price: ₹4,601", "Stock P/E: 33.0".
Halliburton (NYSE: HAL) is a US oilfield-services company quoted in USD, roughly $20-30 a share, so ₹4,601 is not its price.
https://www.screener.in/company/SAMMAANCAP/consolidated/ — "Sammaan Capital Ltd (formerly Indiabulls Housing Finance)".

## Run A — "What are Halliburton's current share price, P/E and market cap?"

The model's one tool call was `fundamentals {"symbol":"HAL.NS"}`, which returned ok. Its answer:
"Halliburton's current share price is ₹4601.0, its P/E ratio is 33.003372, and its market cap is ₹307,703 cr."
All three figures are Hindustan Aeronautics' (screener ₹4,601 / P/E 33.0), presented as Halliburton's. An ok tool call stands behind every
figure, so this is NOT the R4 keyless-figure limitation. The tool and the data are correct for HAL.NS. What fails is that nothing tells the user
(or the model) that in an IN session the bare "HAL" belongs to a different company from the one named. The MCP tool path shows the same bind:
`fundamentals {"symbol":"HAL"}` -> "Hindustan Aeronautics Limited" (t-fund-HAL.json), `price_data {"symbol":"HAL"}` -> INR series (t-price-HAL.json).
R3: R15-DATA-002 (critical, blocked_tier4): "A bare ticker that exists in both the US and Indian masters binds silently to the session region".
This is the same root behaviour, reached through the agent tools -> attach as realuser:5. The research-tool variant that binds HAL/US and then
fills the brief with HAL.NS data has its own root cause in research/fast.py and is filed as realuser:3 (xadv-realuser-2).

## Run B — "How is Indiabulls Housing Finance doing?"

The model called `market_overview {"region":"IN"}` (ok) and `market_overview {"symbol":"IBULHSGFIN.NS"}` (error "no index data resolved for
this region"). Its answer gave market headlines and ended "Let me check the current price of Indiabulls Housing Finance (IBULHSGFIN.NS)." It
stated no figure. It used the wrong tool and the retired ticker, which is a local-model tool-choice weakness, not a product defect. Not filed.
The catalog's `resolve_symbol` does the right thing for the same words (t-resolve-IBH.json: bound SAMMAANCAP 0.99, bse_code 535789).

## Old ticker typed into the data routes (attach)

```
GET /quotes/IBULHSGFIN.NS                 -> 404 {"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found"}
GET /quotes/IBULHSGFIN?asset_class=equity -> 404 same
GET /quotes/ANGELBRKG.NS                  -> 404 same
MCP price_data {"symbol":"IBULHSGFIN.NS"} -> "tool 'price_data' raised: correctness gate: empty series for 'IBULHSGFIN.NS' from 'yfinance'"
```

Meanwhile `/resolve?q=IBULHSGFIN` binds SAMMAANCAP and records the former ticker (xadv-realuser-4). No hint from the data route that the
ticker was renamed. R3: R15-LEAD-053 (open, low): "Direct GET /quotes/TATAMOTORS.NS and .BO still 404 with no rename hint to TMPV, even
though /resolve already lists TMPV first". Same mechanism, new instances -> attach as realuser:6.

VERDICT xadv-realuser-6: finding realuser:5, realuser:6
