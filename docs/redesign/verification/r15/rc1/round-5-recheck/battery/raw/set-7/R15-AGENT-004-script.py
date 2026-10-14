import asyncio, json, sys
sys.path.insert(0, ".")
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
        {"type":"content_block_start","index":0,"content_block":{"type":"thinking","thinking":"","signature":""}},
        {"type":"content_block_delta","index":0,"delta":{"type":"thinking_delta","thinking":"Let me consider..."}},
        {"type":"content_block_stop","index":0},
        *tool_block(1, "toolu_01", "get_quote", ['{"symbol": "RELI', 'ANCE.NS"}']),
        *MESSAGE_END,
    )
    def _handler(request):
        assert request.url.path == "/v1/messages"
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)

    real_client = anthropic.AsyncAnthropic
    orig_init = real_client
    # monkeypatch by subclassing behavior: just construct with mock transport directly
    provider = AnthropicProvider()
    def fake_ctor(**kw):
        return orig_init(**kw, http_client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)))
    anthropic.AsyncAnthropic = fake_ctor
    try:
        out = [e async for e in provider.stream_chat(
            messages=[LLMMessage(role="user", content="quote RELIANCE")],
            model="claude-opus-4-8",
            api_key="sk-test",
        )]
    finally:
        anthropic.AsyncAnthropic = orig_init

    kinds = [e.kind for e in out]
    print("kinds:", kinds)
    tu = out[1]
    print("tool_call_id:", tu.tool_call_id, "name:", tu.name, "input:", tu.input)
    assert kinds == ["thinking", "tool_use", "done"], kinds
    assert tu.tool_call_id == "toolu_01"
    assert tu.name == "get_quote"
    assert tu.input == {"symbol": "RELIANCE.NS"}, tu.input
    print("PASS: tool_use carries streamed+accumulated input, not {}")

asyncio.run(main())
