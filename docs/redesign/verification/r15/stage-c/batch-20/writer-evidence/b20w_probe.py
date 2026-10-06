"""batch-20 writer copy of the batch-19 verifier probe (b19v_probe.py): every case list in one run, and a
per-case PROMPT so the two user-figure controls carry the figure the user is said to have given (under the
batch-19 prompt "q?" their premise is false: nothing in the turn carries the figure). Run with cwd=<tree>/sidecar."""
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
CASES = [
 # entry-class shapes the writer pinned, re-phrased / re-chunked (fresh)
 ("f-named-colon-dump-nextpara", "FAB", [[call("fundamentals", symbol="TATAMOTORS.NS"), DONE], [*d("Checking the `fundamentals` tool on TATAMOTORS.NS, here's wh", "at came back:\n", "\n{\"marketCap\": 2300000000000, \"pe\": 8.4}\n\nLet me know if you need more.")], ], {"fundamentals": ERR}, "no data", ["2300000000000", "8.4"]),
 ("f-named-colon-fenced-json", "FAB", [[call("fundamentals", symbol="TATAMOTORS.NS"), DONE], [*d("After calling `fundamentals` for TATAMOTORS.NS, I got:\n\n", "```json\n{\"marketCap\": 2300000000000, \"pe\": 8.4}\n```\n")]], {"fundamentals": ERR}, "no data", ["2300000000000"]),
 ("f-uncalled-colon-fenced", "FAB", [[call("fundamentals"), DONE], [*d("Running the `price_data` tool, I got back:\n\n```\n{\"close\": 2.11}\n```\n")]], {"fundamentals": OK_F}, "no data", ["2.11"]),
 ("f-allerr-bullets-bold", "FAB", [[call("price_data", query="x"), DONE], [*d("Here's what I found:\n\n", "- **SBIN.NS**: ₹8", "12.40\n- **AXISBANK.NS**: ₹1,102.55\n")]], {"price_data": ERR_ARGS}, "no data", ["812.40", "1,102.55"]),
 ("f-allerr-numbered-eq", "FAB", [[call("price_data", query="x"), DONE], [*d("Latest closing prices:\n1. LT.NS = 3,610.20\n2. ITC.NS = 412.75\n")]], {"price_data": ERR_ARGS}, "no data", ["3,610.20", "412.75"]),
 ("f-allerr-table", "FAB", [[call("price_data", query="x"), DONE], [*d("Here are the latest prices:\n\n| Symbol | Price |\n|---|---|\n| SBIN.NS | ₹812.40 |\n| AXISBANK.NS | ₹1,102.55 |\n")]], {"price_data": ERR_ARGS}, "no data", ["812.40", "1,102.55"]),
 ("f-allerr-bullets-annotated", "FAB", [[call("price_data", query="x"), DONE], [*d("Here are the results:\n\n* INFY.NS: ₹1,233.65 (up 1.2%)\n* TCS.NS: ₹3,235.50 (down 0.4%)\n")]], {"price_data": ERR_ARGS}, "no data", ["1,233.65", "3,235.50"]),
 ("f-allerr-inline-json-dump", "FAB", [[call("financial_statements", symbol="SIFY", period="ttm"), DONE], [*d("I get: {\"ttmRevenueUsd\": 98700000}\n")]], {"financial_statements": ERR}, "no data", ["98700000"]),
 # true controls, fresh
 ("t-ok-list-after-colon", "TRUE", [[call("price_data", symbol="RELIANCE.NS"), DONE], [*d("Here are the latest prices:\n\n- RELIANCE.NS: ₹1,412.30\n- SBIN.NS: ₹812.40\n")]], {"price_data": OK_PX}, "1,412.30", []),
 ("t-ok-named-colon-dump", "TRUE", [[call("fundamentals", symbol="TCS.NS"), DONE], [*d("The `fundamentals` tool returned:\n\n{\"pe_ratio\": 29.8}\n")]], {"fundamentals": OK_F}, "29.8", []),
 ("t-err-plan-list", "TRUE", [[call("price_data", query="x"), DONE], [*d("Next steps:\n- retry price_data with a symbol\n- compare the two closes\n")]], {"price_data": ERR_ARGS}, "compare the two closes", []),
 ("t-err-user-figures-list", "TRUE", [[call("price_data", query="x"), DONE], [*d("You told me:\n- Buy price: ₹1,500\n- Quantity: 10\n\nThat is ₹15,000 in total.\n")]], {"price_data": ERR_ARGS}, "Buy price: ₹1,500", []),
 ("t-err-markdown-link", "TRUE", [[call("price_data", query="x"), DONE], [*d("The price_data call failed. You can check [NSE](https://nseindia.com) directly.\n")]], {"price_data": ERR_ARGS}, "[NSE](https://nseindia.com)", []),
 ("t-nocall-list", "TRUE", [[*d("From memory, rough levels:\n- NIFTY: 24,000\n- SENSEX: 79,000\n"), DONE]], {}, "NIFTY: 24,000", []),
]

CASES2 = [
 ("c-plan-case-c-unfenced", "FAB", [[call("fundamentals"), DONE], [*d('Running the `price_data` tool, I got back:\n\n{"close": 2.11}\n')]], {"fundamentals": OK_F}, "no data", ["2.11"]),
 ("t-err-user-position-summary", "TRUE", [[call("fundamentals", symbol="HDFCBANK.NS"), DONE], [*d("I could not load HDFCBANK.NS data. Your position as you gave it:\n\n- Shares: 40\n- Average cost: \u20b91,640\n")]], {"fundamentals": ERR}, "Average cost: \u20b91,640", []),
 ("f-mixed-errored-named-fenced", "FAB", [[call("fundamentals"), call("price_data", symbol="WIPRO.NS"), DONE], [*d('After calling `price_data` for WIPRO.NS, I got:\n\n```json\n{"close": 248.15}\n```\n')]], {"fundamentals": OK_F, "price_data": ERR}, "no data", ["248.15"]),
]
import sys as _s

J1 = '[{"name": "price_data", "parameters": {"symbol": "RELIANCE.NS", "range": "1mo", "timeframe": "1d"}},\n{"name": "price_data", "parameters": {"symbol": "SBIN.NS", "range": "1mo", "timeframe": "1d"}}]'
CASES3 = [
 ("t-live-rel-list-replay", "TRUE", [[*d("To format the response as per your request, I will provide a JSON array of function calls:\n\n", J1[:60], J1[60:], "\n"), call("price_data", symbol="RELIANCE.NS"), DONE], [*d("\u2022 RELIANCE.NS: \u20b91226.4\n\u2022 SBIN.NS: \u20b9983.0")]], {"price_data": OK_PX}, "RELIANCE.NS: \u20b91226.4", ["returned no data"]),
]
CASES = CASES + CASES2 + CASES3
PROMPTS = {
 "t-err-user-figures-list": "I bought 10 shares at a buy price of \u20b91,500. What is the current price?",
 "t-err-user-position-summary": "I hold 40 shares of HDFCBANK.NS at an average cost of \u20b91,640. Fundamentals?",
}
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
