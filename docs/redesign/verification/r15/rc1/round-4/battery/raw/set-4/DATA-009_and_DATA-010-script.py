import asyncio, math, random, statistics, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-4-cand/sidecar")
from services.backtest_engine import _run_single_slice, _compute_metrics, BacktestStrategy, Bar
from models.backtest import BacktestFeeModel

class NoOp(BacktestStrategy):
    async def on_bar(self, bar, portfolio):
        return []

async def make_curve(n_symbols, n_dates=200, seed=42):
    rnd = random.Random(seed)
    bars = []
    price = {f"S{i}": 100.0 for i in range(n_symbols)}
    for d in range(n_dates):
        ts = f"2024-01-{(d%28)+1:02d}T{d:04d}"
        for i in range(n_symbols):
            sym = f"S{i}"
            price[sym] *= (1 + rnd.gauss(0, 0.01))
            bars.append(Bar(symbol=sym, timestamp=ts, open=price[sym], high=price[sym], low=price[sym], close=price[sym], volume=1000))
    fees = BacktestFeeModel(fee_bps=0, slippage_bps=0)
    trades, curve, skipped, worst = await _run_single_slice(NoOp({}), bars, 100000.0, fees)
    return curve

def date_sampled_sharpe(returns):
    mean = statistics.fmean(returns)
    stdev = statistics.pstdev(returns) if len(returns) > 1 else 0.0
    return (mean / stdev) * math.sqrt(252) if stdev > 0 else 0.0

async def main():
    results = {}
    for n in (1, 2, 4):
        curve = await make_curve(n)
        results[n] = len(curve)
        print(f"N={n}: curve points = {len(curve)}")
    assert results[1] == results[2] == results[4] == 200, f"FAIL: curve points differ by N: {results}"
    print("PASS DATA-009: curve points independent of symbol count (one point per date)")

    # DATA-010: Sortino textbook check
    returns = [0.02]*10 + [-0.05, -0.051]
    from models.backtest import EquityCurvePoint
    curve = [EquityCurvePoint(timestamp="0", equity=100000.0, drawdownPct=0.0)]
    eq = 100000.0
    for r in returns:
        eq = eq * (1 + r)
        curve.append(EquityCurvePoint(timestamp=str(len(curve)), equity=eq, drawdownPct=0.0))
    metrics = _compute_metrics(curve, [], 100000.0)
    # textbook downside deviation: sqrt(mean(min(r,0)^2)) over ALL periods
    downside = math.sqrt(sum(min(r,0.0)**2 for r in returns)/len(returns))
    mean_r = statistics.fmean(returns)
    textbook_sortino = (mean_r/downside)*math.sqrt(252)
    print(f"engine sortino={metrics.sortino:.4f} textbook={textbook_sortino:.4f}")
    assert abs(metrics.sortino - textbook_sortino) < 0.01, f"FAIL sortino mismatch: {metrics.sortino} vs {textbook_sortino}"
    print("PASS DATA-010: sortino matches textbook downside-deviation formula")

    # degenerate: two identical losses (not zero)
    returns2 = [0.02]*10 + [-0.05, -0.05]
    curve2 = [EquityCurvePoint(timestamp="0", equity=100000.0, drawdownPct=0.0)]
    eq = 100000.0
    for r in returns2:
        eq = eq*(1+r)
        curve2.append(EquityCurvePoint(timestamp=str(len(curve2)), equity=eq, drawdownPct=0.0))
    m2 = _compute_metrics(curve2, [], 100000.0)
    print(f"degenerate identical-losses sortino={m2.sortino:.4f}")
    assert m2.sortino != 0.0, "FAIL: identical losses should not give sortino=0 anymore"
    print("PASS DATA-010b: identical-loss case no longer reads 0.00")

asyncio.run(main())
