import asyncio, json, subprocess
from services.llm import oneshot
from services.llm.openai import OpenAIProvider, INVALID_ARGS_SENTINEL
from services.agent_tools.schemas import TOOL_SCHEMAS
from models.llm import LLMUsage, LLMToolUseEvent

REPLY = {"v": ""}
async def fake(provider, model, key, messages, timeout=None):
    return REPLY["v"], LLMUsage(input_tokens=10, output_tokens=5)
oneshot.complete_with_usage = fake
p = OpenAIProvider()
print("HEAD", subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip())

def placeholder(schema, required_only=False):
    props = schema.get("properties") or {}
    keys = schema.get("required") or [] if required_only else list(props)
    out = {}
    for k in keys:
        t = props.get(k, {}).get("type")
        out[k] = t if isinstance(t, str) else "string"
    return out

async def repair(name, schema, reply):
    REPLY["v"] = reply
    return await p._repair_tool_args(tool_name=name, raw_args="{}", error="x", schema=schema, model="m", api_key=None, repairs=[])

async def main():
    # (A) ENTRY'S OWN REPRO: full schema echoed back (plain, fenced, prose-wrapped), every tool.
    total = 0; full_acc = []; noreq = []
    for name, spec in sorted(TOOL_SCHEMAS.items()):
        schema = spec.get("input_schema") or {}
        if not schema.get("properties"): continue
        total += 1
        if not schema.get("required"): noreq.append(name)
        for label, reply in (("plain", json.dumps(schema)),
                             ("fenced", "```json\n" + json.dumps(schema) + "\n```"),
                             ("prose", "Here are the args: " + json.dumps(schema)),
                             ("properties-only", json.dumps(schema["properties"]))):
            got = await repair(name, schema, reply)
            if got is not None: full_acc.append((name, label))
    print(f"(A) tools with properties: {total}; no-required tools: {len(noreq)} {noreq}")
    print(f"(A) full/fenced/prose/properties-only schema echo ACCEPTED: {len(full_acc)} {full_acc}")
    # (B) VERIFIER'S REFUTATION: placeholder echo {prop: '<type-name>'} (all props / required only)
    acc_all, acc_req = [], []
    for name, spec in sorted(TOOL_SCHEMAS.items()):
        schema = spec.get("input_schema") or {}
        if not schema.get("properties"): continue
        ph = placeholder(schema)
        got = await repair(name, schema, json.dumps(ph))
        if got is not None: acc_all.append((name, got))
        phr = placeholder(schema, required_only=True)
        if phr:
            got = await repair(name, schema, json.dumps(phr))
            if got is not None and (name, got) not in acc_all: acc_req.append((name, got))
    print(f"(B) placeholder echo (all props) ACCEPTED: {len(acc_all)}")
    for n, g in acc_all: print("    ", n, json.dumps(g))
    print(f"(B) placeholder echo (required props only, extra) ACCEPTED: {len(acc_req)}")
    for n, g in acc_req: print("    ", n, json.dumps(g))
    # (C) the verifier's `{}` for news: a legit zero-arg call, not an echo
    news = TOOL_SCHEMAS["news"]["input_schema"]
    print("(C) news required:", news.get("required"), "| repair reply '{}' ->", await repair("news", news, "{}"))
    # (D) legit args still pass
    for n, a in (("fundamentals", {"symbol": "AAPL"}), ("resolve_symbol", {"query": "Tata Steel"}), ("price_data", {"symbol": "SPY"})):
        print("(D) legit", n, "->", await repair(n, TOOL_SCHEMAS[n]["input_schema"], json.dumps(a)))
    # (E) end-to-end through _resolve_tool_events: an invalid first call + placeholder repair -> what reaches dispatch
    REPLY["v"] = json.dumps({"symbol": "string"})
    ev = LLMToolUseEvent(tool_call_id="c1", name="fundamentals", input={"symbol": 123})
    out = await p._resolve_tool_events([ev], [], model="m", api_key=None, repairs=[])
    print("(E) _resolve_tool_events(fundamentals {symbol:123}) + repair reply {symbol:'string'} ->", [(e.name, e.input) for e in out])
    REPLY["v"] = json.dumps(TOOL_SCHEMAS["news"]["input_schema"])
    ev = LLMToolUseEvent(tool_call_id="c2", name="news", input={"limit": "ten"})
    out = await p._resolve_tool_events([ev], [], model="m", api_key=None, repairs=[])
    print("(E) _resolve_tool_events(news {limit:'ten'}) + full schema echo reply ->", [(e.name, e.input) for e in out])
asyncio.run(main())
