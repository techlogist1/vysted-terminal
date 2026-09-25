"""batch-18 verifier offline probe: full invoke_agent relay, scripted provider. Run with cwd=<tree>/sidecar."""
import asyncio, json, sys
import pytest
sys.path.insert(0, ".")
from services import agent_runtime
from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMToolUseEvent, LLMUsage
DONE = LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
class P:
    def __init__(self, rounds): self.rounds, self.n = rounds, 0
    async def stream_chat(self, messages, model, api_key=None, **_):
        r = self.rounds[self.n]; self.n += 1
        for e in r: yield e
async def run(rounds, results, history=None, opts=None):
    mp = pytest.MonkeyPatch(); agent_runtime.reload()
    mp.setattr(agent_runtime, "get_provider", lambda *_a, **_k: P(rounds))
    async def _t(*a, **k):
        for x in list(a) + list(k.values()):
            if isinstance(x, str) and x in results: return json.dumps(results[x])
            n = getattr(x, "name", None)
            if n in results: return json.dumps(results[n])
        raise RuntimeError(f"no stub for {a} {k}")
    mp.setattr(agent_runtime, "_dispatch_tool", _t)
    o = dict(opts or {})
    if history: o["history"] = history
    try:
        out = [e.text async for e in agent_runtime.invoke_agent(agent_id="copilot", prompt="q?", api_key="sk-test", autonomy="ask", options=o or None) if isinstance(e, LLMDeltaEvent)]
    finally: mp.undo()
    return "".join(out)
def call(n, **inp): return LLMToolUseEvent(tool_call_id=n, name=n, input=inp or {"symbol": "AAPL"})
def d(*xs): return [LLMDeltaEvent(text=x) for x in xs]
OK_WS = {"ok": True, "results": [{"title": "Apple rises", "snippet": "AAPL rose 3% to $190 (Reuters)"}]}
OK_F = {"ok": True, "symbol": "AAPL", "pe_ratio": 30, "market_cap": 4.9e12}
OK_PX = {"ok": True, "symbol": "AAPL", "latest_price": 190}
OK_FS = {"ok": True, "statements": {"revenue": 44110000000, "currency": "INR"}}
ERR = {"ok": False, "error": "no data"}
# (name, kind TRUE=must keep / FAB=must replace, rounds, results, must_keep_substr)
CASES_OLD = [
 # reviewer's three
 ("rev-according-news-reports", "TRUE", [[call("web_search", query="AAPL"), DONE], [*d("According to news reports from Reuters, AAPL rose 3% to $190.\n"), DONE]], {"web_search": OK_WS}, "AAPL rose 3% to $190"),
 ("rev-based-on-research", "TRUE", [[call("web_search", query="AAPL target"), DONE], [*d("Based on research from Morgan Stanley, the target is $250.\n"), DONE]], {"web_search": OK_WS}, "the target is $250"),
 ("rev-based-on-price-data", "TRUE", [[call("fundamentals"), DONE], [*d("The P/E is 30, based on the price data and earnings.\n"), DONE]], {"fundamentals": OK_F}, "The P/E is 30"),
 # fresh same class (common words that are tool ids: news, research, fundamentals, price data, screener? macro?)
 ("fresh-per-news", "TRUE", [[call("web_search", query="MSFT"), DONE], [*d("Per news from Bloomberg, MSFT closed at $512.\n"), DONE]], {"web_search": OK_WS}, "MSFT closed at $512"),
 ("fresh-as-per-fundamentals-word", "TRUE", [[call("price_data"), DONE], [*d("As per fundamentals of the business and today's quote, AAPL trades at $190.\n"), DONE]], {"price_data": OK_PX}, "AAPL trades at $190"),
 ("fresh-fetched-from-research", "TRUE", [[call("web_search", query="NVDA"), DONE], [*d("I fetched this from research published by Goldman: NVDA's target is $200.\n"), DONE]], {"web_search": OK_WS}, "target is $200"),
 # fabrications the lead-in form was added for (must still be replaced)
 ("fab-according-to-backtick", "FAB", [[call("web_search", query="x"), DONE], [*d("According to `price_data`, AAPL closed at $2.11.\n"), DONE]], {"web_search": OK_WS}, "price_data tool returned no data"),
 ("fab-according-to-snake", "FAB", [[call("web_search", query="x"), DONE], [*d("According to price_data, AAPL closed at $2.11.\n"), DONE]], {"web_search": OK_WS}, "price_data tool returned no data"),
 ("fab-according-to-the-tool-noun", "FAB", [[call("web_search", query="x"), DONE], [*d("According to the Price Data tool, AAPL closed at $2.11.\n"), DONE]], {"web_search": OK_WS}, "price_data tool returned no data"),
 # original entry repro shape
 ("fab-live1-dump", "FAB", [[call("fundamentals", symbol="SIFY.NS"), DONE], [*d("- fundamentals returned: {\"trailing_12m_revenue\": \"$1320 m\"}\n", "Done."), DONE]], {"fundamentals": ERR}, "fundamentals tool returned no data"),
 ("true-err-plus-ok-figure", "TRUE", [[call("fundamentals"), call("financial_statements"), DONE], [*d("The fundamentals tool returned an error, so I used financial statements, which shows revenue of ₹4,411 cr.\n"), DONE]], {"fundamentals": ERR, "financial_statements": OK_FS}, "4,411 cr"),
 ("fab-camel", "FAB", [[call("financial_statements"), DONE], [*d("PriceData returned a close of $2.11.\n"), DONE]], {"financial_statements": OK_FS}, "price_data tool returned no data"),
]
CASES = [
 ("x-news-data-shows", "TRUE", [[call("web_search", query="AAPL"), DONE], [*d("The news data shows AAPL rose 3% to $190.\n"), DONE]], {"web_search": OK_WS}, "AAPL rose 3% to $190"),
 ("x-research-shows", "TRUE", [[call("web_search", query="AAPL"), DONE], [*d("Research shows Apple's services margin is 70%, per Reuters.\n"), DONE]], {"web_search": OK_WS}, "services margin is 70%"),
 ("x-news-outlets-report", "TRUE", [[call("web_search", query="AAPL"), DONE], [*d("News outlets report AAPL rose 3% to $190.\n"), DONE]], {"web_search": OK_WS}, "AAPL rose 3% to $190"),
 ("x-according-to-fundamentals-analysis", "TRUE", [[call("price_data"), DONE], [*d("According to fundamentals analysts, fair value is $210; the price is $190.\n"), DONE]], {"price_data": OK_PX}, "fair value is $210"),
 ("x-fab-according-news-tool", "FAB", [[call("web_search", query="x"), DONE], [*d("According to the news tool, AAPL rose to $2.11.\n"), DONE]], {"web_search": OK_WS}, "news tool returned no data"),
 ("x-fab-per-backtick-news", "FAB", [[call("price_data"), DONE], [*d("Per `news`, AAPL fell to $2.11.\n"), DONE]], {"price_data": OK_PX}, "news tool returned no data"),
]
async def main():
    bad = 0
    for name, kind, rounds, results, must in CASES:
        try: out = await run(rounds, results)
        except Exception as ex: print(f"ERR  {name}: {ex!r}"); bad += 1; continue
        ok = must in out
        if kind == "FAB": ok = ok and "2.11" not in out and "1320" not in out
        print(("PASS " if ok else "FAIL ") + f"[{kind}] {name}: " + json.dumps(out)[:300]); bad += not ok
    print("BAD", bad)
asyncio.run(main())
