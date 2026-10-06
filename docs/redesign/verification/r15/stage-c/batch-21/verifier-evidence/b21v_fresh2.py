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
CASES = [
 mixed("BHARTIARTL.NS", "TCS.NS closed at ₹3,235.50. Airtel last traded at ₹1,874.20.\n", ["1,874.20"]),
 mixed("BHARTIARTL.NS", "TCS.NS closed at ₹3,235.50. Bharti Airtel last traded at ₹1,874.20.\n", ["1,874.20"]),
 mixed("LT.NS", "TCS.NS closed at ₹3,235.50. Larsen & Toubro last traded at ₹3,512.00.\n", ["3,512"]),
 mixed("LT.NS", "TCS.NS closed at ₹3,235.50. L&T last traded at ₹3,512.00.\n", ["3,512"]),
 mixed("HINDUNILVR.NS", "TCS.NS closed at ₹3,235.50. Hindustan Unilever last traded at ₹2,410.00.\n", ["2,410"]),
 mixed("ICICIBANK.NS", "TCS.NS closed at ₹3,235.50. ICICI Bank last traded at ₹1,190.40.\n", ["1,190.40"]),
 mixed("KOTAKBANK.NS", "TCS.NS closed at ₹3,235.50. Kotak last traded at ₹1,788.10.\n", ["1,788.10"]),
 mixed("MARUTI.NS", "TCS.NS closed at ₹3,235.50. Maruti Suzuki last traded at ₹12,450.00.\n", ["12,450"]),
 mixed("SBIN.NS", "TCS.NS closed at ₹3,235.50. State Bank of India last traded at ₹812.40.\n", ["812.40"]),
 ("f036-mixed-tilde", "FAB", [[call("price_data", symbol="TCS.NS"), call("quote", symbol="WIPRO.NS"), DONE], [*d("Wipro data:\n\n~~~\nWIPRO.NS close: 248.15\n~~~\n\nTCS closed at ₹3,235.50.\n")]], {"price_data": OK_TCS, "quote": ERR}, "3,235.50", ["248.15", "~"]),
 ("f036-unclosed-tilde", "FAB", [[call("fundamentals", symbol="TCS.NS"), DONE], [*d("Output:\n\n~~~json\n{\"pe\": 31.7}\n")]], {"fundamentals": ERR}, "no data", ["31.7", "~"]),
 ("f036-list-indented-tilde", "FAB", [[call("fundamentals", symbol="TCS.NS"), DONE], [*d("Result:\n\n  ~~~\n  pe: 31.7\n  ~~~\n\nOk.\n")]], {"fundamentals": ERR}, "Ok.", ["31.7", "~"]),
 ("t036-ok-tilde-kept", "TRUE", [[call("price_data", symbol="TCS.NS"), DONE], [*d("~~~\nTCS.NS 3235.5\n~~~\n")]], {"price_data": OK_TCS}, "~~~\nTCS.NS 3235.5\n~~~", []),
]
async def main():
    bad = 0
    for name, kind, rounds, results, must, forb in CASES:
        try: out = await run(rounds, results, prompt="q?")
        except Exception as ex: print(f"ERR  {name}: {ex!r}"); bad += 1; continue
        ok = must in out and not any(f in out for f in forb)
        print(("PASS " if ok else "FAIL ") + f"[{kind}] {name}: " + json.dumps(out, ensure_ascii=False)[:300]); bad += not ok
    print("BAD", bad)
asyncio.run(main())
