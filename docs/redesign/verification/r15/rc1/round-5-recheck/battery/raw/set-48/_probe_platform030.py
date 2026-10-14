import sys, os, asyncio
sys.path.insert(0, "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-5-recheck-cand/sidecar")
os.environ["VYSTED_DATA_DIR"] = "/tmp/battery15work/bt030data"
os.makedirs("/tmp/battery15work/bt030data", exist_ok=True)

from models.backtest import BacktestRequest
from services import backtest_engine, backtest_store
from services.backtest_engine import BacktestOrderIntent, BacktestStrategy, Bar, SimPortfolio

_CAPITAL = 100_000.0
_FEE_RATE = 0.001

class _Scripted(BacktestStrategy):
    NAME = "scripted030"
    def __init__(self, params):
        super().__init__(params)
        self._n = 0
    async def on_bar(self, bar, portfolio):
        self._n += 1
        qty = self.params["script"].get(self._n)
        return [BacktestOrderIntent(symbol=bar.symbol, quantity=qty)] if qty else []

async def main():
    backtest_engine.reset_registry_for_tests()
    backtest_store.reset_for_tests()
    backtest_engine.register_strategy("scripted030", _Scripted)

    async def loader(_s, _a, _b):
        closes = [100.0] * 5
        return [Bar(f"2025-01-{i+2:02d}", "AAA", c, c, c, c, 1) for i, c in enumerate(closes)]

    # register's literal repro: buy 10 on bar 2, sell -100 (oversell) on bar 5
    request = BacktestRequest(
        strategyId="scripted030", params={"script": {2: 10, 5: -100}},
        symbols=["AAA"], startDate="2025-01-01", endDate="2025-12-31",
        initialCapital=_CAPITAL,
    )
    result = await backtest_engine.run_backtest(request, bar_loader=loader)
    final_equity = result.equity_curve[-1].equity
    fees = 2 * 10 * 100.0 * _FEE_RATE
    print(f"final equity: {final_equity:.2f} (expected ~{_CAPITAL - fees:.2f}, fees only)")
    print(f"trades: {[(t.side, t.quantity, t.pnl) for t in result.trades]}")
    print(f"positions remaining: {result.portfolio_positions if hasattr(result,'portfolio_positions') else 'n/a'}")
    phantom_cash = final_equity - (_CAPITAL - fees)
    print(f"phantom cash from the oversold 90 shares (should be ~0): {phantom_cash:.2f}")
    assert abs(phantom_cash) < 1.0, f"oversell minted phantom cash: {phantom_cash}"
    assert len(result.trades) == 1
    assert result.trades[0].quantity == 10, f"sold more than held: {result.trades[0].quantity}"
    print("PASS: sell larger than held position is clamped to the held quantity; no phantom cash")

asyncio.run(main())
