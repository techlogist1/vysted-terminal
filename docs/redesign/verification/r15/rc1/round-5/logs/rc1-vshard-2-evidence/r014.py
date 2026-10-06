import sys, asyncio; sys.path.insert(0, sys.argv[1])
from services import agent_runtime as ar
from services.llm.ollama import OllamaProvider
real = OllamaProvider()
class Capped:
    async def stream_chat(self, messages, model, api_key=None, **kw):
        kw.pop("tool_ids", None); kw.pop("web_search", None); kw.pop("web_search_max_uses", None)
        async for e in real.stream_chat(messages, model, api_key, options={"num_predict": 24}, **kw):
            if e.kind == "done": print("adapter done finish_reason:", e.finish_reason)
            yield e
async def main():
    ar.reload()
    ar.get_provider = lambda *a, **k: Capped()
    text = []
    async for e in ar.invoke_agent(agent_id="copilot", prompt="Explain in five detailed paragraphs what a price-to-earnings ratio is. Do not call tools.", provider="ollama", model="llama3.1:8b", mode="ask"):
        if e.kind == "delta": text.append(e.text)
        elif e.kind == "research_step" and getattr(e, "step_kind", "") == "notice": print("NOTICE:", e.detail)
        elif e.kind in ("error", "done"): print(e.kind, getattr(e, "code", None), getattr(e, "finish_reason", None))
    print("TEXT:", "".join(text)[-160:])
asyncio.run(main())
