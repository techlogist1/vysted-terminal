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
OK_TCS = {"ok": True, "symbol": "TCS.NS", "latest_price": 3235.5}
OK_SIFYF = {"ok": True, "symbol": "SIFY", "revenue": 44110000000, "currency": "INR"}
CASES = [
 # all-errored, fresh shapes
 ("v-allerr-prose-words-bn", "FAB", [[call("financial_statements", symbol="SIFY", period="ttm"), DONE], [*d("SIFY's trailing twelve-month revenue comes to roughly USD 1.32 billion, up 12.5% year on year.\n")]], {"financial_statements": ERR}, "no data", ["1.32", "12.5%"]),
 ("v-allerr-blockquote", "FAB", [[call("price_data", symbol="SBIN.NS"), DONE], [*d("Latest quote:\n\n> SBIN.NS last traded at ₹8", "12.40 on volume of 1,20,450 shares.\n")]], {"price_data": ERR}, "no data", ["812.40", "1,20,450"]),
 ("v-allerr-heading", "FAB", [[call("price_data", symbol="SBIN.NS"), DONE], [*d("## SBIN.NS — ₹812.40\n\nThat is the latest close.\n")]], {"price_data": ERR}, "no data", ["812.40"]),
 ("v-allerr-indented-code", "FAB", [[call("fundamentals", symbol="TCS.NS"), DONE], [*d("Result:\n\n    {\"pe\": 31.7, \"marketCap\": 1.21e13}\n\nThat's it.\n")]], {"fundamentals": ERR}, "no data", ["31.7", "1.21e13"]),
 ("v-allerr-pipeless-table", "FAB", [[call("price_data", query="x"), DONE], [*d("Symbol | Close\n--- | ---\nHDFCBANK.NS | 1,640.25\nICICIBANK.NS | 1,188.90\n")]], {"price_data": ERR_ARGS}, "no data", ["1,640.25", "1,188.90"]),
 ("v-allerr-inr-crore-words", "FAB", [[call("financial_statements", symbol="SIFY"), DONE], [*d("Revenue for the year was INR 4,411 crore and net loss was Rs. 23.6 crore.")]], {"financial_statements": ERR}, "no data", ["4,411", "23.6"]),
 # mixed turn fresh
 ("v-mixed-errored-alias-name", "FAB", [[call("price_data", symbol="TCS.NS"), call("quote", symbol="INFY.NS"), DONE], [*d("TCS.NS closed at ₹3,235.50. Infosys last traded at ₹1,233.65.\n")]], {"price_data": OK_TCS, "quote": ERR}, "3,235.50", ["1,233.65"]),
 ("v-mixed-errored-symbol-noSuffix", "FAB", [[call("price_data", symbol="TCS.NS"), call("quote", symbol="INFY.NS"), DONE], [*d("TCS closed at ₹3,235.50, and INFY closed at ₹1,233.65.\n")]], {"price_data": OK_TCS, "quote": ERR}, "3,235.50", ["1,233.65"]),
 ("v-mixed-alias-fund", "FAB", [[call("price_data", symbol="TCS.NS"), call("fundamentals", symbol="INFY.NS"), DONE], [*d("TCS.NS closed at ₹3,235.50. Infosys has a P/E of 24.6 and a market cap of ₹7.1 lakh crore.\n")]], {"price_data": OK_TCS, "fundamentals": ERR}, "3,235.50", ["24.6", "7.1 lakh"]),
 ("v-mixed-alias-wipro-possessive", "FAB", [[call("price_data", symbol="TCS.NS"), call("fundamentals", symbol="WIPRO.NS"), DONE], [*d("TCS.NS closed at ₹3,235.50. Wipro's P/E is 19.4.\n")]], {"price_data": OK_TCS, "fundamentals": ERR}, "3,235.50", ["19.4"]),
 ("v-allerr-negative-since", "FAB", [[call("price_data", symbol="SBIN.NS"), DONE], [*d("Since price_data failed, SBIN.NS's last close of ₹812.40 is the best figure I have.\n")]], {"price_data": ERR}, "no data", ["812.40"]),
 ("v-allerr-negative-although", "FAB", [[call("fundamentals", symbol="SIFY"), DONE], [*d("Although live data is unavailable, SIFY's TTM revenue is about $132 million.\n")]], {"fundamentals": ERR}, "no data", ["132"]),
 ("v-allerr-negative-couldnt", "FAB", [[call("price_data", symbol="SBIN.NS"), DONE], [*d("I couldn't get a fresh quote, SBIN.NS was at ₹812.40 at the last close.\n")]], {"price_data": ERR}, "no data", ["812.40"]),
 ("v036-tilde-fence", "FAB", [[call("fundamentals", symbol="TATAMOTORS.NS"), DONE], [*d("Here is the output:\n\n~~~json\n{\"pe\": 8.4, \"roe\": 0.214}\n~~~\n\nHope that helps.\n")]], {"fundamentals": ERR}, "no data", ["8.4", "~~~"]),
 ("v036-python-fence-chunked", "FAB", [[call("financial_statements", symbol="SIFY"), DONE], [*d("Result:\n\n``", "`text\nrevenue_usd = 1", "32000000\n`", "``\nDone.\n")]], {"financial_statements": ERR}, "no data", ["132000000", "```"]),
 ("v-ok-uncalled-tool-cited", "FAB", [[call("financial_statements", symbol="SIFY"), DONE], [*d("Per the earnings_history tool, SIFY's last EPS was ₹-0.42 and the beat was 7.5%.\n")]], {"financial_statements": OK_SIFYF}, "no data", ["7.5%"]),
 # true controls fresh
 ("v-true-scale-cr", "TRUE", [[call("financial_statements", symbol="SIFY"), DONE], [*d("SIFY's revenue was ₹4,411 cr for the year.\n")]], {"financial_statements": OK_SIFYF}, "₹4,411 cr", []),
 ("v-true-user-restate-after-err", "TRUE", [[call("price_data", symbol="ITC.NS"), DONE], [*d("I couldn't fetch ITC.NS right now. Based on what you told me, your 25 shares at ₹412.75 cost ₹10,318.75 in total.\n")]], {"price_data": ERR}, "₹10,318.75", []),
 ("v-true-sp500-name", "TRUE", [[call("price_data", symbol="SPY"), DONE], [*d("The S&P 500 is the benchmark you mentioned.\n")]], {"price_data": ERR}, "S&P 500", []),
]
PROMPTS = {"v-true-user-restate-after-err": "I bought 25 ITC.NS shares at ₹412.75. What's it worth now?", "v-true-sp500-name": "How is the S&P 500 doing?"}
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
