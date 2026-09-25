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
 ("u-tilde-unclosed", [[call("fundamentals", symbol="TCS.NS"), DONE], [*d("Output:\n\n~~~json\n{\"pe\": 31.7}\n")]], {"fundamentals": ERR}),
 ("u-backtick-unclosed", [[call("fundamentals", symbol="TCS.NS"), DONE], [*d("Output:\n\n```json\n{\"pe\": 31.7}\n")]], {"fundamentals": ERR}),
 ("u-backtick-unclosed-prose", [[call("price_data", symbol="SBIN.NS"), DONE], [*d("Here:\n\n```\nSBIN.NS last close ₹812.40\n")]], {"price_data": ERR}),
 ("u-backtick-closed-prose", [[call("price_data", symbol="SBIN.NS"), DONE], [*d("Here:\n\n```\nSBIN.NS last close ₹812.40\n```\n")]], {"price_data": ERR}),
]
async def main():
    for name, rounds, results in CASES:
        out = await run(rounds, results, prompt="q?")
        print(name, json.dumps(out, ensure_ascii=False))
asyncio.run(main())
