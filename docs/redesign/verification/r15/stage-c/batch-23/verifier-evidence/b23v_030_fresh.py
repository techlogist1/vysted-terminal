"""batch-23 verifier: fresh LEAD-030 mixed-turn, unmapped-name, uncalled and no-call cases. cwd=<tree>/sidecar."""
exec(open("/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/batch-23-verify/docs/redesign/verification/r15/stage-c/batch-22/verifier-evidence/b22v_fresh.py").read().split("OK_SBI =")[0])
def two(tag, errsym, text, forb, must="3,235.50", tool="quote"):
    return (tag, [[call("price_data", symbol="TCS.NS"), call(tool, symbol=errsym), DONE], [*d(text)]], {"price_data": OK_TCS, tool: ERR}, must, forb)
def okonly(tag, text, forb, must="3,235.50"):
    return (tag, [[call("price_data", symbol="TCS.NS"), DONE], [*d(text)]], {"price_data": OK_TCS}, must, forb)
def nocall(tag, text, forb):
    return (tag, [[*d(text)]], {}, "", forb)
CASES = [
 # (1) in-class per 4.9: errored subject named in a form the guard cannot map
 two("e-hul-initialism", "HINDUNILVR.NS", "TCS.NS closed at ₹3,235.50. HUL last traded at ₹2,410.00.\n", ["2,410"]),
 two("e-adani-flagship", "ADANIENT.NS", "TCS.NS closed at ₹3,235.50. The Adani flagship last traded at ₹2,310.40.\n", ["2,310.40"]),
 two("e-bajaj-finance-comma", "BAJFINANCE.NS", "TCS.NS closed at ₹3,235.50, while Bajaj Finance sat at ₹6,905.00.\n", ["6,905"]),
 two("e-wipro-named-failed", "WIPRO.NS", "TCS.NS closed at ₹3,235.50. Its rival Wipro, whose call failed, traded at ₹248.15.\n", ["248.15"]),
 two("e-errored-pronoun", "INFY.NS", "TCS.NS closed at ₹3,235.50. INFY.NS could not be fetched, but it last traded near ₹1,540.\n", ["1,540"]),
 two("u-uncalled-ownpara-errturn", "WIPRO.NS", "TCS.NS closed at ₹3,235.50.\n\nKotak Bank last traded at ₹1,844.60.\n", ["1,844.60"]),
 two("u-uncalled-sameparagraph-errturn", "WIPRO.NS", "TCS.NS closed at ₹3,235.50. Kotak Bank last traded at ₹1,844.60.\n", ["1,844.60"]),
 # figure-less fabricated dump
 ("d-allerr-figureless-json", [[call("fundamentals", symbol="INFY.NS"), DONE], [*d('Here is the result:\n\n```json\n{"ok": true, "result": {"name": "Infosys Ltd.", "isin": "INE009A01027"}}\n```\n')]], {"fundamentals": ERR}, "", ['"isin"']),
 ("d-mixed-figureless-json", [[call("price_data", symbol="TCS.NS"), call("fundamentals", symbol="INFY.NS"), DONE], [*d('TCS.NS closed at ₹3,235.50.\n\nfundamentals returned:\n```json\n{"ok": true, "result": {"name": "Infosys Ltd.", "isin": "INE009A01027"}}\n```\n')]], {"price_data": OK_TCS, "fundamentals": ERR}, "3,235.50", ['"isin"']),
 # beyond 4.9's framing: no errored call in the turn
 okonly("a-allok-uncalled-ownpara", "TCS.NS closed at ₹3,235.50.\n\nInfosys last traded at ₹1,540.00.\n", ["1,540"]),
 okonly("a-allok-uncalled-sameparagraph", "TCS.NS closed at ₹3,235.50. Infosys last traded at ₹1,540.00.\n", ["1,540"]),
 okonly("a-allok-uncalled-cited-oktool", "TCS.NS closed at ₹3,235.50. price_data also shows Infosys at ₹1,540.00.\n", ["1,540"]),
 okonly("a-allok-uncalled-fundamentals-cited", "TCS.NS closed at ₹3,235.50. The fundamentals tool returned a P/E of 31.4 for TCS.\n", ["31.4"]),
 nocall("z-nocall-named-prev-sentence", "I'll use the `price_data` tool to fetch the latest price for SBIN.NS.\n\nThe latest price for SBIN.NS is ₹949.50.\n", ["949.50"]),
 nocall("z-nocall-fetched-after", "INFY.NS is currently trading at ₹443.85 per share. This is based on the latest data fetched with price_data.\n", ["443.85"]),
 nocall("z-nocall-same-clause", "According to price_data, SBIN.NS last traded at ₹949.50.\n", ["949.50"]),
 nocall("z-nocall-tool-returned-dump", "price_data returned: {\"symbol\": \"SBIN.NS\", \"close\": 949.5}\n", ["949.5"]),
 # true controls
 two("t-ok-subject-derived-errturn", "INFY.NS", "TCS.NS closed at ₹3,235.50, about 0.4% above last week.\n", []),
 two("t-errored-honest", "INFY.NS", "TCS.NS closed at ₹3,235.50. I could not fetch INFY.NS this time.\n", []),
]
async def main():
    for name, rounds, results, must, forb in CASES:
        try: out = await run(rounds, results)
        except Exception as ex: print(f"ERR  {name}: {ex!r}"); continue
        leak = any(f in out for f in forb)
        print(("LEAK    " if leak else ("MISSING " if must not in out else "HELD    ")) + f"{name}: " + json.dumps(out, ensure_ascii=False)[:260])
asyncio.run(main())
