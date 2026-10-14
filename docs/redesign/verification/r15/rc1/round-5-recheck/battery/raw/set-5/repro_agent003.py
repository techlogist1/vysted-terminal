import asyncio, sys
sys.path.insert(0, ".")
from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMMessage, LLMToolUseEvent, LLMUsage
from services import agent_runtime


class ToolForeverProvider:
    def __init__(self, final_round_tool="price_data"):
        self._final_round_tool = final_round_tool
        self.round_messages = []

    async def stream_chat(self, messages, model, api_key=None, **_):
        self.round_messages.append(list(messages))
        n = len(self.round_messages)
        name = self._final_round_tool if n > agent_runtime._MAX_TOOL_ROUNDS else "price_data"
        yield LLMToolUseEvent(tool_call_id=f"tc{n}", name=name, input={"symbol": "TCS.NS"})
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))


async def run(provider, autonomy):
    orig_get_provider = agent_runtime.get_provider
    orig_ack = agent_runtime._ACK_GRACE_SECONDS
    orig_dispatch = agent_runtime._dispatch_tool_with_progress
    dispatched = []

    async def fake_dispatch(call, _local=None):
        dispatched.append(call.tool_call_id)
        yield agent_runtime._ToolDone('{"ok": true}')

    agent_runtime.reload()
    agent_runtime.get_provider = lambda *_a, **_k: provider
    agent_runtime._ACK_GRACE_SECONDS = 0.0
    agent_runtime._dispatch_tool_with_progress = fake_dispatch
    try:
        events = [
            e async for e in agent_runtime.invoke_agent(
                agent_id="copilot", prompt="x", api_key="k", mode="edit", autonomy=autonomy
            )
        ]
    finally:
        agent_runtime.get_provider = orig_get_provider
        agent_runtime._ACK_GRACE_SECONDS = orig_ack
        agent_runtime._dispatch_tool_with_progress = orig_dispatch
    return events, dispatched


async def main():
    # Case 1: no autonomy, expect yielded==dispatched, capped round ends in text
    provider = ToolForeverProvider()
    events, dispatched = await run(provider, autonomy=None)
    yielded = [e.tool_call_id for e in events if isinstance(e, LLMToolUseEvent)]
    print("case1 yielded:", yielded)
    print("case1 dispatched:", dispatched)
    print("case1 yielded==dispatched:", yielded == dispatched)
    print("case1 len(dispatched)==MAX_TOOL_ROUNDS:", len(dispatched) == agent_runtime._MAX_TOOL_ROUNDS, agent_runtime._MAX_TOOL_ROUNDS)
    print("case1 last event is LLMDoneEvent:", isinstance(events[-1], LLMDoneEvent))
    print("case1 second-last is LLMDeltaEvent w/ text:", isinstance(events[-2], LLMDeltaEvent), repr(getattr(events[-2], "text", None)))
    capped_messages = provider.round_messages[-1]
    print("case1 capped last msg role:", capped_messages[-1].role)
    print("case1 'do not call any more tools' in content:", "do not call any more tools" in capped_messages[-1].content)

    # Case 2: AUTO autonomy, final round tool is write_note -> must not be yielded
    provider2 = ToolForeverProvider(final_round_tool="write_note")
    events2, dispatched2 = await run(provider2, autonomy="auto")
    names2 = [e.name for e in events2 if isinstance(e, LLMToolUseEvent)]
    print("case2 names:", names2)
    print("case2 'write_note' not in names:", "write_note" not in names2)
    print("case2 len match MAX_TOOL_ROUNDS:", len(names2) == len(dispatched2) == agent_runtime._MAX_TOOL_ROUNDS)

asyncio.run(main())
