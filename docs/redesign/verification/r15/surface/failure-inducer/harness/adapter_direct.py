"""Drive the OpenAI-compatible adapter directly against the loopback junk stub (no sidecar)."""
import asyncio, sys
sys.path.insert(0, ".")
from services.llm import get_provider
from services.llm.base import LLMMessage  # noqa: E402

async def run(provider_id, model):
    p = get_provider(provider_id, base_url="http://127.0.0.1:52294/v1")
    evs = []
    try:
        async for ev in p.stream_chat([LLMMessage(role="user", content="price of RELIANCE?")], model=model, api_key="sk-fake-stub"):
            evs.append(f"{type(ev).__name__}:{getattr(ev,'text',None) or getattr(ev,'message',None) or getattr(ev,'finish_reason',None)}")
    except Exception as e:  # noqa: BLE001
        evs.append(f"RAISED {type(e).__name__}: {e}")
    print(provider_id, model, "->", evs)

async def main():
    for prov in ("openai", "openrouter"):
        for m in ("junk-chunkdrop", "junk-orerror", "junk-truncated"):
            await run(prov, m)
asyncio.run(main())
