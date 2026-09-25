"""Replay the live f-err-fenced stream with the LIVE layout: the deltas after a
tool_use stay in the same round (the round ends at the tool_result), and the
runtime context option is passed when CTX is set."""
import asyncio, json, os, sys
import pytest
sys.path.insert(0, ".")
from services import agent_runtime
from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMToolUseEvent, LLMUsage

DONE = LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
E = sys.argv[1]
evs = [json.loads(l) for l in open(E) if l.strip()]
rounds, cur, results = [], [], []
for e in evs:
    if e["kind"] == "delta":
        cur.append(LLMDeltaEvent(text=e["text"]))
    elif e["kind"] == "tool_use":
        cur.append(LLMToolUseEvent(tool_call_id=e["tool_call_id"], name=e["name"], input=e["input"]))
    elif e["kind"] == "tool_result":
        cur.append(DONE); rounds.append(cur); cur = []
        results.append({"ok": False, "error": e.get("error") or "missing or non-string symbol"} if not e["ok"] else {"ok": True, "symbol": "AAPL", "quote": {"symbol": "AAPL", "latest_price": 255.5}})
cur.append(DONE); rounds.append(cur)
print("rounds", [(len(r), [type(x).__name__ for x in r if not isinstance(x, LLMDeltaEvent)]) for r in rounds])
results = iter(results)

class P:
    def __init__(self, rounds): self.rounds, self.n = rounds, 0
    async def stream_chat(self, messages, model, api_key=None, **_):
        if self.n == 0:
            for m in messages:
                print("MSG", m.role, repr(m.content[:300]))
        r = self.rounds[self.n]; self.n += 1
        for e in r: yield e

async def main():
    mp = pytest.MonkeyPatch(); agent_runtime.reload()
    mp.setattr(agent_runtime, "get_provider", lambda *_a, **_k: P(rounds))
    async def _t(*a, **k): return json.dumps(next(results))
    mp.setattr(agent_runtime, "_dispatch_tool", _t)
    out = []
    kw = {}
    ctx = os.environ.get("CTX")
    if ctx:
        kw["context_snapshot"] = json.loads(ctx)
    async for e in agent_runtime.invoke_agent(agent_id="copilot", prompt=sys.argv[2], api_key="sk-test", autonomy="ask", **kw):
        if isinstance(e, LLMDeltaEvent): out.append(e.text)
        else: out.append(f"<<{type(e).__name__}>>")
    mp.undo()
    print("".join(out)[:1200])
asyncio.run(main())
