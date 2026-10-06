import asyncio, sys, json
sys.path.insert(0, ".")
import pytest
from tests.test_llm_ollama import _patch
from services.llm.ollama import OllamaProvider
from models.llm import LLMMessage

async def drive(pieces, tools):
    mp = pytest.MonkeyPatch()
    chunks = [{"message": {"content": p}, "done": False} for p in pieces] + [{"message": {"content": ""}, "done": True, "done_reason": "stop"}]
    _patch(mp, chunks=chunks)
    try:
        return [e async for e in OllamaProvider().stream_chat(messages=[LLMMessage(role="user", content="x")], model="llama3.1:8b", tool_ids=tools)]
    finally:
        mp.undo()

CASES = [
 ("orig2-reshape", [" Let", " me", " try", " another", " way", ".\n\n", '{"', 'name', '":', ' "', 'fund', 'amentals', '", "', 'parameters', '": {"', 'symbol', '": "', 'SIFY', '"}}'], ["fundamentals", "price_data"], ['{"', 'fund', 'name']),
 ("fresh-nospace-price", ["Checking", ".\n", '{', '"na', 'me":"', 'pri', 'ce_d', 'ata","arg', 'uments":{"symbol":"SIFY"}}'], ["fundamentals", "price_data"], ['{', 'pri', 'name']),
 ("fresh-callsyntax", ["Checking. ", "price", "_da", "ta(symbol", '="SIFY")'], ["price_data"], ['price']),
 ("fresh-abandoned-prefix", ["The ", "price", " moved; ", '{"', "note", '": 1}'], ["price_data"], []),
]
async def main():
    bad = 0
    for name, pieces, tools, forbidden in CASES:
        out = await drive(pieces, tools)
        deltas = [e.text for e in out if e.kind == "delta"]
        calls = [(e.name, e.input) for e in out if e.kind == "tool_use"]
        shown = "".join(deltas)
        fails = [f"SHOWN {f!r}" for f in forbidden if f in shown]
        if name == "fresh-abandoned-prefix" and shown != "".join(pieces): fails.append("LOST")
        print(("FAIL " if fails else "PASS ") + name + f": deltas={deltas} calls={calls}" + (" | " + "; ".join(fails) if fails else ""))
        bad += bool(fails)
    print("BAD", bad)
asyncio.run(main())
