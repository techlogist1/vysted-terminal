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
 ("err-mention-plus-true-figure", [[call("fundamentals"), call("financial_statements"), DONE], [*d("The fundamentals tool returned an error, so I used financial statements, which shows revenue of ₹4,411 cr.\n", "Done."), DONE]], {"fundamentals": ERR, "financial_statements": OK_FS}, None, [], ["4,411 cr"]),
 ("err-mention-plus-true-figure-2", [[call("fundamentals"), call("financial_statements"), DONE], [*d("fundamentals failed for SIFY.NS, but `financial_statements` shows revenue of ₹4,411 cr.\n", "Done."), DONE]], {"fundamentals": ERR, "financial_statements": OK_FS}, None, [], ["4,411 cr"]),
 ("err-mention-separate-sentence", [[call("fundamentals"), call("financial_statements"), DONE], [*d("The fundamentals tool returned an error. ", "Financial statements show revenue of ₹4,411 cr.\n", "Done."), DONE]], {"fundamentals": ERR, "financial_statements": OK_FS}, None, [], ["4,411 cr"]),
 # (name, rounds, results, history, must_not, must)
 ("fab-humanised-titlecase-sameline", [[call("financial_statements"), DONE], [*d("Here is what I found.\n\n", "Earnings History: {\"ok\": true, \"eps\": \"$0.42\"}\n\n", "Revenue is above.") , DONE]], {"financial_statements": OK_FS}, None, ["0.42", "\"eps\""], ["earnings_history tool returned no data for this in this turn", "Revenue is above."]),
 ("fab-humanised-nextline-dump", [[call("financial_statements"), DONE], [*d("The Analyst History output:\n", "{\n", " \"target\": \"$25.00\"\n", "}\n", "Consensus is buy."), DONE]], {"financial_statements": OK_FS}, None, ["25.00", "\"target\""], ["analyst_history tool returned no data", "Consensus is buy."]),
 ("fab-hyphen-errored", [[call("price_data"), DONE], [*d("Per price-data results, the close was $2.11.\n", "Done."), DONE]], {"price_data": ERR}, None, ["2.11"], ["price_data tool returned no data", "Done."]),
 ("fab-bracket-array-humanised", [[call("financial_statements"), DONE], [*d("Corporate Actions = [\n", " {\"split\": \"2:1\", \"dividend\": \"₹5\"}\n", "]\n", "No more."), DONE]], {"financial_statements": OK_FS}, None, ["₹5", "split"], ["corporate_actions tool returned no data", "No more."]),
 ("true-humanised-ok", [[call("financial_statements"), DONE], [*d("Financial Statements returned revenue of ₹4,411 cr.\n", "That is TTM."), DONE]], {"financial_statements": OK_FS}, None, ["returned no data"], ["Financial Statements returned revenue of ₹4,411 cr.", "That is TTM."]),
 ("true-backtick-dump-ok", [[call("price_data"), DONE], [*d("`price_data` returned:\n", "{\n \"latest_price\": 13.41\n}\n", "So it closed at $13.41."), DONE]], {"price_data": OK_PX}, None, ["returned no data"], ["\"latest_price\": 13.41", "So it closed at $13.41."]),
 ("precall-narration-fresh", [[*d("I'm about to check the earnings history data for SIFY. "), call("earnings_history"), DONE], [*d("Done."), DONE]], {"earnings_history": {"ok": True, "rows": []}}, None, ["returned no data"], ["I'm about to check the earnings history data for SIFY."]),
 ("precall-narration-with-other-ok", [[call("price_data"), DONE], [*d("Next I'll pull the financial statements data for SIFY. "), call("financial_statements"), DONE], [*d("Done."), DONE]], {"price_data": OK_PX, "financial_statements": OK_FS}, None, ["returned no data"], ["Next I'll pull the financial statements data for SIFY."]),
 ("precall-with-figure-fabricated", [[*d("Let me check: `news` data shows revenue of $5 bn. "), DONE]], {}, None, ["$5 bn"], ["news tool returned no data"]),
 ("history-seed-fixed-label", [[*d("The get_portfolio tool returned 10 AAPL shares worth $2,300.\n", "OK."), DONE]], {}, [{"role": "user", "content": "What do I hold?"}, {"role": "assistant", "content": "You hold 10 AAPL.\n\n[tool steps: Reading your portfolio]"}], ["returned no data"], ["The get_portfolio tool returned 10 AAPL shares worth $2,300."]),
 ("history-seed-multi-step", [[*d("The Price Data tool returned a close of $13.41.\n", "OK."), DONE]], {}, [{"role": "user", "content": "SIFY?"}, {"role": "assistant", "content": "SIFY is at $13.41.\n\n[tool steps: Using resolve symbol; Using price data]"}], ["returned no data"], ["The Price Data tool returned a close of $13.41."]),
 ("history-seed-negative", [[*d("The price_data tool returned a close of $2.11.\n", "OK."), DONE]], {}, [{"role": "user", "content": "SIFY?"}, {"role": "assistant", "content": "Revenue ₹4,411 cr.\n\n[tool steps: Using financial statements]"}], ["2.11"], ["price_data tool returned no data for this in this turn"]),
 ("prose-price-data-kept", [[call("financial_statements"), DONE], [*d("I don't have price data for SIFY yet, but revenue grew."), DONE]], {"financial_statements": OK_FS}, None, ["returned no data"], ["I don't have price data for SIFY yet"]),
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
