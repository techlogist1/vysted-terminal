import asyncio, json, sys
sys.path.insert(0, "../scripts/agent_eval")
import ollama
from services import agent_runtime
from grader import grade
from services import agent_tools
agent_tools.register_v0_5_0_tools(); agent_tools.register_v0_6_0_tools()

NAME, ARGS = sys.argv[1], json.loads(sys.argv[2])
ROUNDS = [
    [{"message": {"content": "", "tool_calls": [{"function": {"name": NAME, "arguments": ARGS}}]}, "done": False}, {"message": {"content": ""}, "done": True, "done_reason": "stop"}],
    [{"message": {"content": "Here is what I found."}, "done": False}, {"message": {"content": ""}, "done": True, "done_reason": "stop"}],
]
async def _iter(items):
    for i in items:
        yield i
class Fake:
    n = 0
    async def chat(self, **kw):
        r = ROUNDS[min(Fake.n, len(ROUNDS) - 1)]; Fake.n += 1
        return _iter(r)
ollama.AsyncClient = lambda **_: Fake()

async def main():
    events = []
    async for ev in agent_runtime.invoke_agent(agent_id="copilot", prompt="x", context_snapshot=None, api_key=None, provider="ollama", model="llama3.1:8b", options=None, mode="agent", autonomy="ask"):
        if ev.kind != "heartbeat":
            events.append(json.loads(ev.model_dump_json()))
    print("events:", [(e["kind"], e.get("name"), e.get("ok"), e.get("error")) for e in events if e["kind"] in ("tool_use", "tool_result", "done", "error")])
    print("grade:", grade({"expect": {"tools": [{"tool": NAME}]}}, events))

asyncio.run(main())
