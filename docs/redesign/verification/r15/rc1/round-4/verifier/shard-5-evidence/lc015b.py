import asyncio, sys
sys.path.insert(0,'.')
from services import backtest_engine, backtest_store
from services.backtest_strategies import register_all
from services.backtest_engine import Bar
from models.backtest import BacktestRequest
async def loader(_s,_a,_b):
    await asyncio.sleep(0.01)
    return [Bar(f"2025-01-{i+2:02d}","AAA",100+i,100+i,100+i,100+i,1) for i in range(5)]
async def main():
    register_all(); ids=[]
    for n in range(3):
        r=BacktestRequest(strategyId="trend_following",params={},symbols=["AAA"],startDate="2025-01-01",endDate="2025-12-31",initialCapital=100000.0)
        res=await backtest_engine.run_backtest(r,bar_loader=loader); backtest_store.put(res); ids.append((res.run_id,res.started_at))
    backtest_store.get(ids[0][0])
    lst=[(x.run_id,x.started_at) for x in backtest_store.list_runs()]
    print("put order started_at:", [s for _,s in ids]); print("list order started_at:", [s for _,s in lst]); print("newest-first after get():", [i for i,_ in lst]==[i for i,_ in reversed(ids)])
asyncio.run(main())
