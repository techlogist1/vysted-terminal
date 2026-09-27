import asyncio, json, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-4-cand/sidecar")
import anthropic, httpx
from models.llm import LLMMessage
from services.llm.anthropic import AnthropicProvider

def _sse(*frames):
    return "".join("event: " + f["type"] + "\ndata: " + json.dumps(f) + "\n\n" for f in frames).encode()

MESSAGE_START = {"type":"message_start","message":{"id":"msg_01","type":"message","role":"assistant","model":"claude-opus-4-8","content":[],"stop_reason":None,"stop_sequence":None,"usage":{"input_tokens":42,"output_tokens":1}}}
MESSAGE_END = [{"type":"message_delta","delta":{"stop_reason":"tool_use","stop_sequence":None},"usage":{"output_tokens":30}},{"type":"message_stop"}]

def tool_block(index, tool_id, name, fragments):
    return [
        {"type":"content_block_start","index":index,"content_block":{"type":"tool_use","id":tool_id,"name":name,"input":{}}},
        *({"type":"content_block_delta","index":index,"delta":{"type":"input_json_delta","partial_json":f}} for f in fragments),
        {"type":"content_block_stop","index":index},
    ]

async def main():
    body = _sse(
        MESSAGE_START,
        *tool_block(0, "toolu_01", "get_quote", ['{"symbol": "RELI', 'ANCE.NS"}']),
        *MESSAGE_END,
    )
    real_client = anthropic.AsyncAnthropic
    def handler(request):
        assert request.url.path == "/v1/messages"
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)
    anthropic.AsyncAnthropic = lambda **kw: real_client(**kw, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    provider = AnthropicProvider()
    out = [e async for e in provider.stream_chat(messages=[LLMMessage(role="user", content="quote RELIANCE")], model="claude-opus-4-8", api_key="sk-test")]
    kinds = [e.kind for e in out]
    print("kinds:", kinds)
    tool_events = [e for e in out if e.kind == "tool_use"]
    for e in tool_events:
        print(f"tool_use name={e.name!r} input={e.input!r}")
    assert tool_events, "FAIL: no tool_use event emitted"
    assert tool_events[0].input == {"symbol": "RELIANCE.NS"}, f"FAIL: input was {tool_events[0].input!r}, expected the streamed symbol, not {{}}"
    print("PASS AGENT-004: tool_use carries the accumulated streamed input, not {}")

asyncio.run(main())
