import asyncio, time, sys
import config
from models.fundamentals import Fundamentals
from services import provider_registry, correctness_gate, ownership_check, yfinance_provider, exchange_financials
from services.correctness_gate import range_check as _rc
from routers import fundamentals as R
calls = {}
def wrap(mod, name):
    fn = getattr(mod, name)
    if asyncio.iscoroutinefunction(fn):
        async def w(*a, **k):
            calls[name] = calls.get(name, 0) + 1; return await fn(*a, **k)
    else:
        def w(*a, **k):
            calls[name] = calls.get(name, 0) + 1; return fn(*a, **k)
    setattr(mod, name, w)
wrap(ownership_check, "get_exchange_ownership")
wrap(yfinance_provider, "get_income_statement")
wrap(yfinance_provider, "get_quarterly_period_ends")
wrap(yfinance_provider, "get_newest_equity")
wrap(_rc, "get_venue_history")
def canned(sym):
    return Fundamentals(symbol=sym, name=sym, provider="yfinance", currency="INR", held_percent_insiders=0.72, held_percent_institutions=0.20,
        revenue_ttm=2.5e12, book_value=300.0, price_to_book=5.0, fifty_two_week_high=4000.0, fifty_two_week_low=3000.0, market_cap=1.2e13)
async def fake_get(symbol, region=None):
    return canned(symbol if symbol.endswith(".NS") else symbol + ".NS")
provider_registry.get_fundamentals = fake_get
async def main():
    tok = config.set_request_region("IN") if hasattr(config, "set_request_region") else None
    for rnd in (1, 2):
        for s in sys.argv[1:]:
            before = dict(calls); t = time.monotonic()
            f = await R.get_fundamentals(s)
            delta = {k: calls.get(k, 0) - before.get(k, 0) for k in calls if calls.get(k, 0) - before.get(k, 0)}
            print(f"r{rnd} {s} {time.monotonic()-t:.2f}s witness_fetches={delta}")
asyncio.run(main())
