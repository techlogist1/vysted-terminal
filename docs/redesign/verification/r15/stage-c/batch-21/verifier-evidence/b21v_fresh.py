"""batch-21 verifier fresh cases (not in any writer test). Run with cwd=<tree>/sidecar."""
import asyncio, json, sys
import pytest
sys.path.insert(0, ".")
from services import agent_runtime
from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMToolUseEvent, LLMUsage
DONE = LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
class P:
    def __init__(self, rounds): self.rounds, self.n = rounds, 0
    async def stream_chat(self, messages, model, api_key=None, **_):
        r = self.rounds[self.n]; self.n += 1
        for e in r: yield e
async def run(rounds, results, history=None, opts=None, prompt="q?"):
    mp = pytest.MonkeyPatch(); agent_runtime.reload()
    mp.setattr(agent_runtime, "get_provider", lambda *_a, **_k: P(rounds))
    async def _t(*a, **k):
        for x in list(a) + list(k.values()):
            if isinstance(x, str) and x in results: return json.dumps(results[x])
            n = getattr(x, "name", None)
            if n in results: return json.dumps(results[n])
        raise RuntimeError(f"no stub for {a} {k}")
    mp.setattr(agent_runtime, "_dispatch_tool", _t)
    o = dict(opts or {})
    if history: o["history"] = history
    try:
        out = [e.text async for e in agent_runtime.invoke_agent(agent_id="copilot", prompt=prompt, api_key="sk-test", autonomy="ask", options=o or None) if isinstance(e, LLMDeltaEvent)]
    finally: mp.undo()
    return "".join(out)
def call(n, **inp): return LLMToolUseEvent(tool_call_id=n, name=n, input=inp or {"symbol": "AAPL"})
def d(*xs): return [LLMDeltaEvent(text=x) for x in xs]
ERR = {"ok": False, "error": "no data"}
ERR_ARGS = {"ok": False, "error": "invalid arguments for price_data: 'symbol' is a required property"}
OK_F = {"ok": True, "symbol": "TCS.NS", "pe_ratio": 29.8}
OK_PX = {"ok": True, "symbol": "RELIANCE.NS", "latest_price": 1412.3}
# (name, kind, rounds, results, must_substr, forbidden_substrs)
OK_TCS = {"ok": True, "symbol": "TCS.NS", "latest_price": 3235.5}
OK_SIFYF = {"ok": True, "symbol": "SIFY", "revenue": 44110000000, "currency": "INR"}
OK_MSFT = {"ok": True, "symbol": "MSFT", "latest_price": 511.2}
CASES = [
 # mixed turns: errored subject by a name form
 ("w-mixed-sbi-abbrev", "FAB", [[call("price_data", symbol="TCS.NS"), call("quote", symbol="SBIN.NS"), DONE], [*d("TCS.NS closed at ₹3,235.50. SBI last traded at ₹812.40.\n")]], {"price_data": OK_TCS, "quote": ERR}, "3,235.50", ["812.40"]),
 ("w-mixed-reliance-first", "FAB", [[call("price_data", symbol="TCS.NS"), call("fundamentals", symbol="RELIANCE.NS"), DONE], [*d("TCS.NS closed at ₹3,235.50. Reliance trades at a P/E of 27.3.\n")]], {"price_data": OK_TCS, "fundamentals": ERR}, "3,235.50", ["27.3"]),
 ("w-mixed-hdfc-bank", "FAB", [[call("price_data", symbol="TCS.NS"), call("quote", symbol="HDFCBANK.NS"), DONE], [*d("TCS.NS closed at ₹3,235.50, while HDFC Bank closed at ₹1,712.90.\n")]], {"price_data": OK_TCS, "quote": ERR}, "3,235.50", ["1,712.90"]),
 ("w-mixed-apple-us", "FAB", [[call("price_data", symbol="MSFT"), call("fundamentals", symbol="AAPL"), DONE], [*d("MSFT is at $511.20. Apple's market cap is about $3.4 trillion.\n")]], {"price_data": OK_MSFT, "fundamentals": ERR}, "511.20", ["3.4 trillion"]),
 ("w-mixed-inherit-its-newline", "FAB", [[call("price_data", symbol="TCS.NS"), call("quote", symbol="WIPRO.NS"), DONE], [*d("TCS.NS closed at ₹3,235.50.\nWipro (WIPRO.NS) could not be refreshed.\nIts last close was ₹248.15.\n")]], {"price_data": OK_TCS, "quote": ERR}, "3,235.50", ["248.15"]),
 ("w-mixed-inherit-chunked", "FAB", [[call("price_data", symbol="TCS.NS"), call("quote", symbol="INFY.NS"), DONE], [*d("Infosys could not be ref", "reshed. The last print ", "was ₹1,233.65.\n")]], {"price_data": OK_TCS, "quote": ERR}, "no data", ["1,233.65"]),
 ("w-mixed-although-name", "FAB", [[call("price_data", symbol="TCS.NS"), call("quote", symbol="INFY.NS"), DONE], [*d("Although I couldn't refresh Infosys, it was around ₹1,500 last week.\n")]], {"price_data": OK_TCS, "quote": ERR}, "no data", ["1,500"]),
 # all-errored: acknowledgement shapes
 ("w-allerr-however", "FAB", [[call("price_data", symbol="ICICIBANK.NS"), DONE], [*d("The tool failed; however, my estimate for ICICIBANK.NS is ₹1,190.\n")]], {"price_data": ERR}, "no data", ["1,190"]),
 ("w-allerr-unable-but", "FAB", [[call("price_data", symbol="HCLTECH.NS"), DONE], [*d("Unable to retrieve live data, but HCLTECH.NS is trading near ₹1,650 as of today.\n")]], {"price_data": ERR}, "no data", ["1,650"]),
 ("w-allerr-despite", "FAB", [[call("fundamentals", symbol="SIFY"), DONE], [*d("Despite the error, SIFY's TTM revenue is roughly USD 128.5 million.\n")]], {"fundamentals": ERR}, "no data", ["128.5"]),
 ("w-allerr-multi-names", "FAB", [[call("price_data", query="x"), DONE], [*d("Latest closes: Wipro ₹248, HCL Technologies ₹1,650 and Tech Mahindra ₹1,420.\n")]], {"price_data": ERR_ARGS}, "no data", ["248", "1,650", "1,420"]),
 # fences
 ("w036-tilde4-chunked", "FAB", [[call("fundamentals", symbol="TCS.NS"), DONE], [*d("Output:\n\n~~", "~~ text\n{\"close\": 812.4}\n~~", "~~\n\nThanks.\n")]], {"fundamentals": ERR}, "Thanks.", ["812.4", "~"]),
 ("w036-backtick4-nested", "FAB", [[call("fundamentals", symbol="TCS.NS"), DONE], [*d("Raw:\n\n````md\n```json\n{\"pe\": 31.7}\n```\n````\n\nDone.\n")]], {"fundamentals": ERR}, "Done.", ["31.7", "`"]),
 ("w036-tilde-closer-longer", "FAB", [[call("price_data", symbol="SBIN.NS"), DONE], [*d("Here:\n\n~~~\nclose: 812.40\n~~~~~\n\nEnd.\n")]], {"price_data": ERR}, "End.", ["812.40", "~"]),
 # true controls
 ("t-mixed-ok-fullname", "TRUE", [[call("price_data", symbol="TCS.NS"), call("quote", symbol="INFY.NS"), DONE], [*d("Tata Consultancy Services closed at ₹3,235.50.\n")]], {"price_data": OK_TCS, "quote": ERR}, "₹3,235.50", []),
 ("t-mixed-ok-row-beside-err", "TRUE", [[call("price_data", symbol="TCS.NS"), call("quote", symbol="WIPRO.NS"), DONE], [*d("Closes:\n- Tata Consultancy: ₹3,235.50\n- Wipro: ₹248.15\n")]], {"price_data": OK_TCS, "quote": ERR}, "₹3,235.50", ["248.15"]),
 ("t-inherit-reset-blank", "TRUE", [[call("price_data", symbol="TCS.NS"), call("quote", symbol="INFY.NS"), DONE], [*d("Infosys could not be refreshed.\n\nThe index rose 0.8% today.\n")]], {"price_data": OK_TCS, "quote": ERR}, "0.8%", []),
 ("t-neg-no-figure", "TRUE", [[call("price_data", symbol="SBIN.NS"), DONE], [*d("The price_data tool failed for SBIN.NS, so I can't give you a price right now.\n")]], {"price_data": ERR}, "can't give you a price", []),
 ("t-user-figure-name-after-err", "TRUE", [[call("price_data", symbol="TCS.NS"), call("quote", symbol="INFY.NS"), DONE], [*d("I couldn't refresh Infosys. Your 40 Infosys shares at ₹1,450 cost ₹58,000 in total.\n")]], {"price_data": OK_TCS, "quote": ERR}, "₹58,000", []),
 ("t-ok-rounding-msft", "TRUE", [[call("price_data", symbol="MSFT"), DONE], [*d("Microsoft last traded at about $511.\n")]], {"price_data": OK_MSFT}, "$511", []),
]
PROMPTS = {"t-user-figure-name-after-err": "I hold 40 Infosys shares at ₹1,450 each. Also, how is TCS doing?"}
async def main():
    bad = 0
    for name, kind, rounds, results, must, forb in CASES:
        rounds = [r if r and r[-1] is DONE else [*r, DONE] for r in rounds]
        try: out = await run(rounds, results, prompt=PROMPTS.get(name, "q?"))
        except Exception as ex: print(f"ERR  {name}: {ex!r}"); bad += 1; continue
        ok = must in out and not any(f in out for f in forb)
        print(("PASS " if ok else "FAIL ") + f"[{kind}] {name}: " + json.dumps(out, ensure_ascii=False)[:400]); bad += not ok
    print("BAD", bad)
asyncio.run(main())
