import asyncio
from types import SimpleNamespace as N
from services.llm import gemini as g
from services import budget_guard
from models.llm import LLMMessage
cls=[v for k,v in vars(g).items() if isinstance(v,type) and hasattr(v,'_client') and k.lower().startswith('gemini')][0]
async def gen():
    yield N(candidates=[N(finish_reason='STOP', grounding_metadata=None, content=N(parts=[N(text='hi', function_call=None)]))],
            usage_metadata=N(prompt_token_count=1000, tool_use_prompt_token_count=None, candidates_token_count=800, thoughts_token_count=6000))
class FakeModels:
    async def generate_content_stream(self, **kw): return gen()
fake=N(aio=N(models=FakeModels()))
a=cls(); a._client=lambda key: fake
async def main():
    evs=[e async for e in a.stream_chat([LLMMessage(role="user",content="x")], model="gemini-2.5-pro", api_key="k")]
    print(evs[-1])
asyncio.run(main())
