import asyncio, sys
from types import SimpleNamespace as NS
from services.llm.ollama import OllamaProvider
from models.llm import LLMMessage

def mk(chunks):
    async def gen():
        for i,c in enumerate(chunks):
            yield {"message":{"content":c,"tool_calls":None},"done":i==len(chunks)-1,"done_reason":"stop" if i==len(chunks)-1 else None}
    class C:
        async def chat(self, **kw):
            return gen()
    return C()

async def run(label, chunks, tools=("write_note","screener_run","price_data")):
    p = OllamaProvider()
    p._client = lambda: mk(chunks)
    evs=[]
    async for e in p.stream_chat(messages=[LLMMessage(role="user",content="x")], model="llama3.1:8b", tool_ids=list(tools)):
        evs.append(e)
    print("==",label)
    for e in evs: print("  ",type(e).__name__, getattr(e,"text",None) or getattr(e,"name",None), getattr(e,"input",None), getattr(e,"tool_call_id",None))

async def main():
    await run("repro single chunk", ['{"name": "write_note", "parameters": {"scope": "NVDA", "content": "hello"}}'])
    await run("fresh: split across chunks after prose", ['Sure, I will save it.\n', '{"na', 'me": "write_note", "param', 'eters": {"scope": "AAPL", "content": "a {brace} b"}}', '\nDone! The note was saved.'])
    await run("fresh: fenced + stringified args", ['```json\n{"name": "screener_run", "arguments": "{\\"criteria\\": [{\\"field\\": \\"pe\\", \\"op\\": \\"<\\", \\"value\\": 20}]}"}\n```'])
    await run("fresh: non-offered name stays prose", ['{"name": "delete_everything", "parameters": {}}'])
    await run("fresh: call syntax", ['price_data(symbol="ZOMATO.NS")'])
asyncio.run(main())
