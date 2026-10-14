import asyncio, hashlib, json, sys, time
sys.path.insert(0, "/Users/lokavyasingh/Documents/dev/vysted-terminal/scripts/r15")
import vy
from services.llm import get_provider
from models.llm import LLMMessage
MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
PROMPT = sys.argv[1]
vy._budget_check("openrouter", MODEL)
key = vy._key("openrouter")
assert key, "no key"
async def main():
    p = get_provider("openrouter")
    thinking, text, kinds, other = [], [], {}, []
    t0 = time.time(); status = "ok"
    try:
        import os; tids = [t for t in os.environ.get("TOOLS","").split(",") if t] or None
        async for ev in p.stream_chat([LLMMessage(role="user", content=PROMPT)], MODEL, api_key=key, tool_ids=tids):
            k = type(ev).__name__; kinds[k] = kinds.get(k, 0) + 1
            if k == "LLMThinkingEvent": thinking.append(ev.text)
            elif k == "LLMDeltaEvent": text.append(ev.text)
            else: other.append(repr(ev)[:300])
    except Exception as e:
        status = f"err_{type(e).__name__}"; print("ERR", type(e).__name__, str(e)[:300].replace(key, "***"))
    el = time.time() - t0
    with vy.LEDGER.open("a") as fh:
        fh.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "day": time.strftime("%Y-%m-%d"), "tag": "rc1-vshard-5", "port": 0, "agent": "adapter-direct", "provider": "openrouter", "model": MODEL, "free": True, "prompt_sha": hashlib.sha256(PROMPT.encode()).hexdigest()[:12], "status": status, "secs": round(el, 1), "in": 0, "out": 0, "est_usd": 0.0}) + "\n")
    print("KINDS", kinds, "secs", round(el,1)); print("OTHER", other[-3:])
    print("=== THINKING len", len("".join(thinking)), "\n", "".join(thinking)[:800])
    print("=== VISIBLE TEXT len", len("".join(text)), "\n", "".join(text)[:2000])
asyncio.run(main())
