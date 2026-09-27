import asyncio, sys
sys.path.insert(0, '.')
from services import backtest_engine
from services.backtest_engine import Bar, BacktestStrategy, SimPortfolio, BacktestOrderIntent
from models.backtest import BacktestRequest
class EveryBar(BacktestStrategy):
    NAME="everybar"
    async def on_bar(self, bar, portfolio):
        q=self.params.get("q",{}).get(bar.timestamp, 10)
        return [BacktestOrderIntent(symbol=bar.symbol, quantity=q)]
async def run(closes, syms, q=None):
    async def loader(_s,_a,_b):
        out=[]
        for i,c in enumerate(closes):
            for s in syms: out.append(Bar(f"2025-01-{i+2:02d}", s, c,c,c,c,1))
        return out
    backtest_engine.register_strategy("everybar", EveryBar)
    r=BacktestRequest(strategyId="everybar", params={"q":q or {}}, symbols=syms, startDate="2025-01-01", endDate="2025-12-31", initialCapital=100000.0)
    return await backtest_engine.run_backtest(r, bar_loader=loader)
res=asyncio.run(run([100.0]*4,["AAA"]))
print("REPRO flat 4x+10: trades",len(res.trades),[ (t.quantity,round(t.entry_price,4),t.pnl) for t in res.trades],"final eq",res.equity_curve[-1].equity,"totalReturn",res.metrics.total_return,"tradeCount",res.metrics.trade_count)
# fresh: rising 100,110,120,130 buy 10 each of first 3 bars then sell 30 on bar 4, two symbols
q={"2025-01-02":10,"2025-01-03":10,"2025-01-04":10,"2025-01-05":-30}
res=asyncio.run(run([100.0,110.0,120.0,130.0],["AAA","BBB"],q))
f=0.001
avg=(100+110+120)/3*(1+f); exp_pnl=(130*(1-f)-avg)*30
print("FRESH 2-sym pyramid+exit: trades",[(t.symbol,t.quantity,round(t.entry_price,4),round(t.pnl,4) if t.pnl is not None else None) for t in res.trades],"expected pnl each",round(exp_pnl,4),"final eq",round(res.equity_curve[-1].equity,4),"expected eq",round(100000+2*exp_pnl,4),"tradeCount",res.metrics.trade_count,"winRate",res.metrics.win_rate, "curve pts", len(res.equity_curve))
