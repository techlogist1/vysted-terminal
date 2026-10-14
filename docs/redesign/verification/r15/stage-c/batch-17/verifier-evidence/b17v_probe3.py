"""batch-17 verifier offline probe: full invoke_agent relay with a scripted provider."""
import asyncio, json, sys
from typing import Any
import pytest
sys.path.insert(0, ".")
from services import agent_runtime
from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMToolUseEvent, LLMUsage
from services.llm.tool_call_rescue import LeakHold

DONE = LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))

class P:
    def __init__(self, rounds): self.rounds, self.n = rounds, 0
    async def stream_chat(self, messages, model, api_key=None, **_):
        r = self.rounds[self.n]; self.n += 1
        for e in r: yield e

async def run(rounds, results, history=None):
    mp = pytest.MonkeyPatch()
    agent_runtime.reload()
    mp.setattr(agent_runtime, "get_provider", lambda *_a, **_k: P(rounds))
    async def tool(name, *a, **k):
        return json.dumps(results[name])
    async def _t(*a, **k):
        # name is the first positional str arg matching a key
        for x in list(a) + list(k.values()):
            if isinstance(x, str) and x in results: return json.dumps(results[x])
            n = getattr(x, "name", None)
            if n in results: return json.dumps(results[n])
        raise RuntimeError(f"no stub for {a} {k}")
    mp.setattr(agent_runtime, "_dispatch_tool", _t)
    try:
        out = [e.text async for e in agent_runtime.invoke_agent(agent_id="copilot", prompt="SIFY revenue?", api_key="sk-test", autonomy="ask", options={"history": history} if history else None) if isinstance(e, LLMDeltaEvent)]
    finally:
        mp.undo()
    return "".join(out)

def call(name): return LLMToolUseEvent(tool_call_id=name, name=name, input={"symbol": "SIFY"})
def d(*xs): return [LLMDeltaEvent(text=x) for x in xs]
OK_FS = {"ok": True, "statements": {"revenue": 44110000000, "currency": "INR"}}
ERR = {"ok": False, "error": "yfinance has no instrument data for 'SIFY.NS'"}
OK_PX = {"ok": True, "symbol": "SIFY", "latest_price": 13.41}
OK_PF = {"ok": True, "positions": [{"symbol": "AAPL", "qty": 10}]}

CASES = [
 ("fab-according-to-errored", [[call("fundamentals"), DONE], [*d("According to the fundamentals tool, TTM revenue is $1320 m.\n", "Done."), DONE]], {"fundamentals": ERR}, None, ["1320"], ["fundamentals tool returned no data", "Done."]),
 ("fab-camelcase", [[call("financial_statements"), DONE], [*d("PriceData returned a close of $2.11.\n", "Done."), DONE]], {"financial_statements": OK_FS}, None, ["2.11"], ["Done."]),
 ("fab-news-uncalled-humanised-sameline-figure", [[call("price_data"), DONE], [*d("The News results say SIFY raised $40 m.\n", "Done."), DONE]], {"price_data": OK_PX}, None, ["$40 m"], ["news tool returned no data"]),
 ("true-fundamentals-same-turn-dump", [[call("fundamentals"), DONE], [*d("The tool that provided the market cap figure was `fundamentals`, which returned:\n\n", "{\n", ' "market_cap": 3440000000000\n', "}"), DONE]], {"fundamentals": {"ok": True, "market_cap": 3440000000000}}, None, ["returned no data"], ['"market_cap": 3440000000000']),
]

async def main():
    bad = 0
    for name, rounds, results, hist, must_not, must in CASES:
        try:
            out = await run(rounds, results, hist)
        except Exception as ex:
            print(f"ERR  {name}: {ex!r}"); bad += 1; continue
        fails = [f"LEAK {x!r}" for x in must_not if x in out] + [f"MISSING {x!r}" for x in must if x not in out]
        print(("FAIL " if fails else "PASS ") + name + ": " + json.dumps(out)[:400] + (" | " + "; ".join(fails) if fails else ""))
        bad += bool(fails)
    # LEAD-031: LeakHold chunk replay
    offered = {"price_data", "fundamentals", "financial_statements", "write_note", "news"}
    L = [
      ("orig2-json-fundamentals", ['Sure. ', '{"', 'name', '":', ' "', 'fund', 'amentals', '", "', 'arguments', '": {"symbol": "SIFY"}}', ], ['{"name', 'fund'], None),
      ("nospace-json-charwise", list('Ok {"name":"financial_statements","arguments":{}}'), ['{"', 'financial'], None),
      ("call-syntax-news", ['See ', 'ne', 'ws', '(symbol=', '"SIFY")'], ['news('], None),
      ("benign-prefix-replay", ['The ', 'pri', 'ce', ' is up.'], [], 'The price is up.'),
      ("unoffered-json-replay", ['x; {"', 'name', '": "', 'scre', 'ener_run"} y'], [], 'x; {"name": "screener_run"} y'),
    ]
    for name, chunks, forbidden, whole in L:
        h = LeakHold(offered); shown = []
        for c in chunks: shown += h.feed(c)
        s = "".join(shown); rest = h.held()
        fails = [f"SHOWN {f!r}" for f in forbidden if f in s]
        if whole is not None and s + rest != whole: fails.append(f"LOST {s+rest!r}")
        if whole is not None and s != whole: fails.append(f"NOT-RELEASED shown={s!r} held={rest!r}")
        print(("FAIL " if fails else "PASS ") + "031/" + name + f": shown={shown!r} held={rest!r}" + (" | " + "; ".join(fails) if fails else ""))
        bad += bool(fails)
    print("BAD", bad)

asyncio.run(main())
