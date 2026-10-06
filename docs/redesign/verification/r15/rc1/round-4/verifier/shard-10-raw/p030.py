import asyncio, os, sys, tempfile
os.environ["VYSTED_DATA_DIR"] = tempfile.mkdtemp()
from services import backtest_engine as be
from services.backtest_engine import Bar, BacktestOrderIntent, BacktestStrategy
from models.backtest import BacktestRequest

def scripted(script, closes, sym="X"):
    class S(BacktestStrategy):
        NAME = "s"
        def __init__(self, p): super().__init__(p); self.n = 0
        async def on_bar(self, bar, pf):
            self.n += 1
            q = script.get(self.n)
            return [BacktestOrderIntent(symbol=bar.symbol, quantity=q)] if q else []
    be.reset_registry_for_tests(); be.register_strategy("s", S)
    bars = [Bar(timestamp=f"2025-01-{i+2:02d}", symbol=sym, open=c, high=c, low=c, close=c, volume=1) for i, c in enumerate(closes)]
    async def loader(*_): return bars
    req = BacktestRequest(strategyId="s", symbols=[sym], startDate="2025-01-01", endDate="2025-02-01", initialCapital=100000)
    return asyncio.run(be.run_backtest(req, bar_loader=loader))

def show(label, r):
    print(label, "final_equity=%.4f" % r.equity_curve[-1].equity, "trades=", [(t.quantity, t.pnl, t.exited_at) for t in r.trades], "trade_count=", r.metrics.trade_count)

show("ENTRY_REPRO buy10@bar2 sell100@bar5 flat100:", scripted({2: 10, 5: -100}, [100.0]*6))
show("FRESH pyramid 7+5, partial -4, oversell -50, then oversell -50 again, flat 250:", scripted({1: 7, 2: 5, 3: -4, 4: -50, 5: -50}, [250.0]*6))
show("FRESH rising market oversell 3 held, sell 30 at 200:", scripted({1: 3, 3: -30}, [100.0, 150.0, 200.0, 200.0]))
show("FRESH fractional 0.1+0.2 then sell 0.3:", scripted({1: 0.1, 2: 0.2, 3: -0.3}, [100.0]*4))
