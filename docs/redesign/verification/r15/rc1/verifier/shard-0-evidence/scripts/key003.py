import asyncio, sys, inspect
sys.path.insert(0, '.')
from services.llm import get_provider
from services import errors
async def v(pid, key):
    p = get_provider(pid)
    try:
        r = p.validate_key(key)
        if inspect.isawaitable(r): r = await r
        print(f"{pid} validate_key({key[:14]}...) -> {r!r}")
    except Exception as e:
        print(f"{pid} validate_key RAISED {type(e).__name__}: {str(e)[:200]}")
        try:
            h = errors.humanize(pid, e); print("   humanize ->", h.code, "|", h.message[:160])
        except Exception as e2: print("   humanize failed", e2)
async def main():
    for pid, key in [("openrouter","not-a-real-key"), ("openrouter","sk-or-v1-" + "0"*64),
                     ("gemini","AIzaSyNOTAREALKEY000000000000000000000"), ("xai","xai-notarealkey000000000000"),
                     ("groq","gsk_notarealkey0000000000000000"), ("mistral","notarealkey0000000000000000"),
                     ("deepseek","sk-notarealkey00000000000000"), ("openai","sk-notarealkey0000000000000000"),
                     ("anthropic","sk-ant-notarealkey000000000")]:
        try: await v(pid, key)
        except Exception as e: print(pid, "outer", type(e).__name__, e)
asyncio.run(main())
