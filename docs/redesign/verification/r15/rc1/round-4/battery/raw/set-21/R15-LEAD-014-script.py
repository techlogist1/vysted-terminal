import asyncio, json, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-4-cand/sidecar")
from unittest.mock import AsyncMock, patch
from services.agent_tools.schemas import TOOL_SCHEMAS
from services.llm.openai import OpenAIProvider
from models.llm import LLMUsage

provider = OpenAIProvider(provider_id="openai")

def schema_for(name):
    return TOOL_SCHEMAS.get(name, {}).get("input_schema")

async def repair_with_reply(tool_name, reply_text):
    schema = schema_for(tool_name)
    with patch("services.llm.oneshot.complete_with_usage", new=AsyncMock(return_value=(reply_text, LLMUsage(input_tokens=1, output_tokens=1)))):
        return await provider._repair_tool_args(
            tool_name=tool_name, raw_args="{bad json", error="malformed",
            schema=schema, model="gpt-4o-mini", api_key="sk-test", repairs=[],
        )

async def main():
    no_required = [name for name, s in TOOL_SCHEMAS.items() if not (s.get("input_schema") or {}).get("required")]
    print(f"tools with no required keys: {len(no_required)}")
    leaked = 0
    for name in no_required:
        schema = schema_for(name)
        echo = json.dumps(schema)
        result = await repair_with_reply(name, echo)
        if result is not None:
            leaked += 1
    print(f"full echo accepted after fix: {leaked} of {len(no_required)}")
    assert leaked == 0, f"FAIL: {leaked} tools still accept a schema echo as valid args"

    # fenced + prose-wrapped echo, using the first no-required tool
    sample = no_required[0]
    schema = schema_for(sample)
    fenced = "```json\n" + json.dumps(schema) + "\n```"
    prose = "Sure, here you go:\n" + json.dumps(schema) + "\nHope that helps!"
    r_fenced = await repair_with_reply(sample, fenced)
    r_prose = await repair_with_reply(sample, prose)
    print(f"fenced echo -> {r_fenced}")
    print(f"prose echo -> {r_prose}")
    assert r_fenced is None, "FAIL: fenced schema echo accepted"
    assert r_prose is None, "FAIL: prose-wrapped schema echo accepted"

    # legit args still pass
    legit = await repair_with_reply("news", json.dumps({"symbols": ["AAPL"]}))
    print(f"legit news args -> {legit}")
    assert legit == {"symbols": ["AAPL"]}, f"FAIL: legit args rejected: {legit}"

    print("PASS LEAD-014: schema-echo repair replies are rejected; legit args still pass")

asyncio.run(main())
