import asyncio, json, sys
import ollama
from services import agent_runtime

LEAK = sys.argv[1]
ROUNDS = [
    [{"message": {"content": c}, "done": False} for c in json.loads(LEAK)] + [{"message": {"content": ""}, "done": True, "done_reason": "stop"}],
    [{"message": {"content": "Each SIFY ADR represents 2 ordinary shares."}, "done": False}, {"message": {"content": ""}, "done": True, "done_reason": "stop"}],
]

async def _iter(items):
    for i in items:
        yield i

class Fake:
    n = 0
    async def chat(self, **kw):
        r = ROUNDS[min(Fake.n, len(ROUNDS) - 1)]; Fake.n += 1
        return _iter(r)
    async def list(self):
        return {"models": [{"model": "llama3.1:8b"}]}

ollama.AsyncClient = lambda **_: Fake()

async def main():
    text, kinds = "", []
    async for ev in agent_runtime.invoke_agent(agent_id="copilot", prompt="How many ordinary shares does one SIFY ADR represent?", context_snapshot=None, api_key=None, provider="ollama", model="llama3.1:8b", options=None, mode="agent", autonomy="ask"):
        kinds.append(ev.kind)
        if ev.kind == "delta":
            text += ev.text
        if ev.kind == "tool_use":
            kinds[-1] += f"({ev.name})"
    print("kinds:", [k for k in kinds if k != "heartbeat"])
    print("text:", repr(text))

asyncio.run(main())
