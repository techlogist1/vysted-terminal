import asyncio, json
from services.llm import oneshot
from services.llm.openai import OpenAIProvider
from services.agent_tools.schemas import TOOL_SCHEMAS
from models.llm import LLMUsage

REPLY = {"v": ""}
async def fake(provider, model, key, messages, timeout=None):
    return REPLY["v"], LLMUsage(input_tokens=10, output_tokens=5)
oneshot.complete_with_usage = fake
p = OpenAIProvider()

def placeholder(schema):
    out = {}
    for k, v in (schema.get("properties") or {}).items():
        t = v.get("type")
        out[k] = t if isinstance(t, str) else "string"
    return out

async def main():
    full_acc, ph_acc, props_acc, total = [], [], [], 0
    for name, spec in sorted(TOOL_SCHEMAS.items()):
        schema = spec.get("input_schema") or {}
        if not schema.get("properties"):
            continue
        total += 1
        for label, reply, bucket in (
            ("full", json.dumps(schema), full_acc),
            ("fenced-full", "```json\n" + json.dumps(schema) + "\n```", full_acc),
            ("placeholder", json.dumps(placeholder(schema)), ph_acc),
            ("properties-only", json.dumps(schema["properties"]), props_acc),
        ):
            REPLY["v"] = reply
            got = await p._repair_tool_args(tool_name=name, raw_args="{}", error="x", schema=schema, model="m", api_key=None, repairs=[])
            if got is not None:
                bucket.append((name, label, got))
    print("tools with properties:", total)
    print("full/fenced schema echo accepted:", len(full_acc), full_acc[:3])
    print("placeholder echo {prop: <type-name>} accepted:", len(ph_acc))
    for n, l, g in ph_acc[:12]: print("   ", n, json.dumps(g)[:120])
    print("properties-only echo accepted:", len(props_acc))
    for n, l, g in props_acc[:6]: print("   ", n, json.dumps(g)[:160])
asyncio.run(main())
