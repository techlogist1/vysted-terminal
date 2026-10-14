import asyncio, sys, os, time, inspect
sys.path.insert(0,'.')
from services import backtest_engine, backtest_store, agent_tools
from services.backtest_engine import Bar
from models.backtest import BacktestRequest
import services.agent_tools.backtest_summary as bs
async def loader(_s,_a,_b):
    return [Bar(f"2025-01-{i+2:02d}","AAA",100+i,100+i,100+i,100+i,1) for i in range(5)]
async def main():
    from services.backtest_strategies import register_all; register_all()
    ids=[]
    for n in range(34):
        r=BacktestRequest(strategyId="trend_following",params={},symbols=["AAA"],startDate="2025-01-01",endDate="2025-12-31",initialCapital=100000.0)
        res=await backtest_engine.run_backtest(r,bar_loader=loader)
        backtest_store.put(res); ids.append(res.run_id)
    print("in-memory has first?", backtest_store._cache.get(ids[0]) is not None)
    backtest_store.get(ids[5])  # LRU touch
    lst=[x.run_id for x in backtest_store.list_runs()]
    print("list newest-first:", lst[0]==ids[-1], "last==first run:", lst[-1]==ids[0], "len", len(lst))
    backtest_store.reset_for_tests()  # simulate restart (memory gone)
    fn=[f for n,f in inspect.getmembers(bs, inspect.iscoroutinefunction)]
    print("summary fns", [f.__name__ for f in fn])
    out=await fn[0]({"run_id":ids[0]}) if fn else None
    print("backtest_summary(first run after restart):", str(out)[:300])
asyncio.run(main())
