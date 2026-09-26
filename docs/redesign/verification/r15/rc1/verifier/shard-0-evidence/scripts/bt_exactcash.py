import asyncio, sys, random, math, statistics
from datetime import date, timedelta
sys.path.insert(0,'.')
from services import backtest_engine as be
from services.backtest_engine import _compute_metrics, EquityCurvePoint, Bar, BacktestOrderIntent, BacktestStrategy
from models.backtest import BacktestRequest, BacktestFeeModel
class BuyHold(BacktestStrategy):
    def __init__(self, params):
        super().__init__(params); self.done=set()
    async def on_bar(self, bar, portfolio):
        if bar.symbol in self.done: return []
        self.done.add(bar.symbol)
        return [BacktestOrderIntent(symbol=bar.symbol, quantity=self.params['q'][bar.symbol], reason='entry')]
be.register_strategy('vs0_bh', BuyHold)
def walk(n, days, seed):
    rng=random.Random(seed); d0=date(2024,1,1); bars=[]; paths={}
    for i in range(n):
        p=100.0; path=[]
        for k in range(days):
            p*=1+rng.gauss(0.0005,0.015); path.append(p)
        paths[f'S{i}']=path
    dates=[]; d=d0
    while len(dates)<days:
        if d.weekday()<5: dates.append(d.isoformat())
        d+=timedelta(days=1)
    for s,path in paths.items():
        for ds,p in zip(dates,path): bars.append(Bar(timestamp=ds,symbol=s,open=p,high=p,low=p,close=p,volume=1000))
    return bars, paths, dates
async def run(n, days, seed, slices=1):
    bars,paths,dates=walk(n,days,seed)
    async def loader(a,b,c): return bars
    q={s:(100000.0/n)/paths[s][0] for s in paths}
    req=BacktestRequest(strategyId='vs0_bh',params={'q':q},symbols=list(paths),startDate=dates[0],endDate=dates[-1],initialCapital=100000.0,feeModel=BacktestFeeModel(feeBps=0,slippageBps=0),walkForwardSlices=slices)
    r=await be.run_backtest(req, bar_loader=loader)
    # date-sampled reference
    eq=[10.0+sum(q[s]*paths[s][k] for s in paths) for k in range(days)]
    rets=[(eq[k]-eq[k-1])/eq[k-1] for k in range(1,days)]
    ref=statistics.fmean(rets)/statistics.pstdev(rets)*math.sqrt(252)
    ddev=math.sqrt(sum(min(x,0)**2 for x in rets)/len(rets)); ref_sort=statistics.fmean(rets)/ddev*math.sqrt(252)
    print(f'N={n} seed={seed} slices={slices}: curve={len(r.equity_curve)} dates={days} sharpe={r.metrics.sharpe:.4f} ref={ref:.4f} ratio={r.metrics.sharpe/ref:.3f} sortino={r.metrics.sortino:.4f} ref_sortino={ref_sort:.4f} annRet={r.metrics.annualized_return if hasattr(r.metrics,"annualized_return") else r.metrics.annualizedReturn:.5f}')
    if r.walk_forward_slices:
        for sl in r.walk_forward_slices[:2]: print('   slice', getattr(sl,'metrics',sl).sharpe if hasattr(getattr(sl,'metrics',sl),'sharpe') else sl)
async def main():
    for n in (1,2,4): await run(n,200,7)            # literal shape
    await run(3,150,20260926)                        # fresh N/seed
    await run(5,120,99,slices=3)                     # fresh: walk-forward slices
asyncio.run(main())
def curve(rs):
    e=100000.0; c=[EquityCurvePoint(timestamp='2025-01-01',equity=e,drawdownPct=0.0)]; pk=e
    for i,r in enumerate(rs):
        e*=1+r; pk=max(pk,e); c.append(EquityCurvePoint(timestamp=f'2025-02-{i+1:02d}',equity=e,drawdownPct=(e-pk)/pk))
    return c
def textbook(rs):
    m=statistics.fmean(rs); d=math.sqrt(sum(min(x,0)**2 for x in rs)/len(rs)); return m/d*math.sqrt(252) if d>0 else 0.0
for label,rs in [('010 literal',[0.02]*10+[-0.05,-0.051]),('010 identical losses',[0.02]*10+[-0.03,-0.03]),('010 fresh single loss',[0.01,0.015,-0.02,0.012,0.008]),('010 fresh all-negative',[-0.01,-0.02,-0.005])]:
    m=_compute_metrics(curve(rs),[],100000.0); print(label,'sortino',round(m.sortino,4),'textbook',round(textbook(rs),4))
