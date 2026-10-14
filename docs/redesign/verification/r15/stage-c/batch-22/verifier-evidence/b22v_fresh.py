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
def mixed(sym, text, forb, tool="quote"):
    return (f"n-{sym}", "FAB", [[call("price_data", symbol="TCS.NS"), call(tool, symbol=sym), DONE], [*d(text)]], {"price_data": OK_TCS, tool: ERR}, "3,235.50", forb)
OK_SBI = {"ok": True, "symbol": "SBIN.NS", "latest_price": 983.0}
def mix(tag, sym, text, forb, tool="quote", okres=OK_TCS, oksym="TCS.NS", must="3,235.50"):
    return (tag, "FAB", [[call("price_data", symbol=oksym), call(tool, symbol=sym), DONE], [*d(text)]], {"price_data": okres, tool: ERR}, must, forb)
CASES = [
 mix("v-mm-initialism", "M&M.NS", "TCS.NS closed at ₹3,235.50. M&M last traded at ₹3,120.00.\n", ["3,120"]),
 mix("v-ril-abbrev", "RELIANCE.NS", "TCS.NS closed at ₹3,235.50. RIL last traded at ₹1,412.30.\n", ["1,412.30"]),
 mix("v-infy-nick", "INFY.NS", "TCS.NS closed at ₹3,235.50. Infy last traded at ₹1,540.00.\n", ["1,540"]),
 mix("v-tatamotors-errored", "TATAMOTORS.NS", "TCS.NS closed at ₹3,235.50. Tata Motors last traded at ₹702.10.\n", ["702.10"]),
 ("v-tatamotors-uncalled", "FAB", [[call("price_data", symbol="TCS.NS"), call("quote", symbol="WIPRO.NS"), DONE], [*d("TCS.NS closed at ₹3,235.50. Tata Motors last traded at ₹702.10.\n")]], {"price_data": OK_TCS, "quote": ERR}, "3,235.50", ["702.10"]),
 ("v-hdfclife-vs-bank", "FAB", [[call("price_data", symbol="HDFCBANK.NS"), call("quote", symbol="HDFCLIFE.NS"), DONE], [*d("HDFC Bank closed at ₹1,712.90. HDFC Life last traded at ₹745.60.\n")]], {"price_data": {"ok": True, "symbol": "HDFCBANK.NS", "latest_price": 1712.9}, "quote": ERR}, "1,712.90", ["745.60"]),
 ("v-allerr-4tilde-info-unclosed", "FAB", [[call("price_data", symbol="WIPRO.NS"), call("price_data", symbol="HCLTECH.NS"), DONE], [*d("Here you go:\n\n~~~~text\nWIPRO 248.15\nHCLTECH 1,512.40")]], {"price_data": ERR}, "no data", ["248.15", "1,512.40", "~"]),
 ("v-mixed-unclosed-py-fence", "FAB", [[call("price_data", symbol="TCS.NS"), call("quote", symbol="SBIN.NS"), DONE], [*d("TCS.NS closed at ₹3,235.50.\n\n```python\nsbi_close = 812.40")]], {"price_data": OK_TCS, "quote": ERR}, "3,235.50", ["812.40", "```"]),
 ("v-mixed-midtable-sbi", "FAB", [[call("price_data", symbol="TCS.NS"), call("quote", symbol="SBIN.NS"), DONE], [*d("| Stock | Price |\n|---|---|\n| TCS | ₹3,235.50 |\n| SBI | ₹812.40")]], {"price_data": OK_TCS, "quote": ERR}, "3,235.50", ["812.40"]),
 ("t-sbi-short-ok", "TRUE", [[call("price_data", symbol="SBIN.NS"), DONE], [*d("SBI closed at ₹983.00.\n")]], {"price_data": OK_SBI}, "SBI closed at ₹983.00.", []),
 ("t-sbi-short-ok-mixed-derived", "TRUE", [[call("price_data", symbol="SBIN.NS"), call("quote", symbol="WIPRO.NS"), DONE], [*d("SBI closed at ₹983.00, about 1% above last week.\n")]], {"price_data": OK_SBI, "quote": ERR}, "SBI closed at ₹983.00, about 1% above last week.", []),
 ("t-ok-rounding", "TRUE", [[call("price_data", symbol="TCS.NS"), DONE], [*d("TCS is at roughly ₹3,236.\n")]], {"price_data": OK_TCS}, "roughly ₹3,236", []),
 ("v-bigblue-sameparagraph", "FAB", [[call("price_data", symbol="MSFT"), call("quote", symbol="IBM"), DONE], [*d("MSFT closed at $511.20. Big Blue last traded at $250.10.\n")]], {"price_data": OK_MSFT, "quote": ERR}, "511.20", ["250.10"]),
 ("v-bigblue-ownparagraph", "FAB", [[call("price_data", symbol="MSFT"), call("quote", symbol="IBM"), DONE], [*d("MSFT closed at $511.20.\n\nBig Blue last traded at $250.10.\n")]], {"price_data": OK_MSFT, "quote": ERR}, "511.20", ["250.10"]),
 ("v-infosys-sameparagraph-uncalled", "FAB", [[call("price_data", symbol="TCS.NS"), call("quote", symbol="WIPRO.NS"), DONE], [*d("TCS.NS closed at ₹3,235.50, and its peer Infosys last traded at ₹1,540.00.\n")]], {"price_data": OK_TCS, "quote": ERR}, "3,235.50", ["1,540"]),
]
PROMPTS = {}
async def main():
    bad = 0
    for name, kind, rounds, results, must, forb in CASES:
        try: out = await run(rounds, results, prompt=PROMPTS.get(name, "q?"))
        except Exception as ex: print(f"ERR  {name}: {ex!r}"); bad += 1; continue
        ok = must in out and not any(f in out for f in forb)
        print(("PASS " if ok else "FAIL ") + f"[{kind}] {name}: " + json.dumps(out, ensure_ascii=False)[:300]); bad += not ok
    # user-figure restated after an error
    out = await run([[call("price_data", symbol="RELIANCE.NS"), DONE], [*d("You sold 8 RELIANCE shares at ₹1,300 each, so your proceeds were ₹10,400.\n")]], {"price_data": ERR}, prompt="I sold 8 RELIANCE.NS shares at ₹1,300 each. Restate my sale price and total proceeds.")
    ok = "₹1,300" in out and "₹10,400" in out
    print(("PASS " if ok else "FAIL ") + "[TRUE] t-user-figure-after-err: " + json.dumps(out, ensure_ascii=False)); bad += not ok
    print("BAD", bad)
asyncio.run(main())
