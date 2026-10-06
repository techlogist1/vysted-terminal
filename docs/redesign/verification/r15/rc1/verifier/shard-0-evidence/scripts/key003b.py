import asyncio, sys
sys.path.insert(0, '.')
from services.llm import get_provider
from models.llm import LLMMessage
async def main():
    for pid, key, model in [("gemini","AIzaSyNOTAREALKEY000000000000000000000","gemini-2.5-flash"), ("xai","xai-notarealkey000000000000","grok-3-mini"), ("openrouter","not-a-real-key","openai/gpt-4o-mini")]:
        p = get_provider(pid)
        async for ev in p.stream_chat([LLMMessage(role="user", content="hi")], model=model, api_key=key):
            if ev.kind in ("error","done"):
                print(pid, ev.kind, getattr(ev,"code",None), "|", getattr(ev,"message","")[:140]); break
asyncio.run(main())
