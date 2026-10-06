import sys, math
from datetime import datetime, UTC, timedelta
sys.path.insert(0,'.')
from models.market import Quote, OHLCVSeries, OHLCVBar
from services import correctness_gate as g, provider_registry as pr
from services.errors import ProviderError
now=datetime.now(UTC)
def q(p,prov): return Quote(symbol='TEST',price=p,change=0.0,change_percent=0.0,currency='USD',market_state='CLOSED',timestamp=now,provider=prov)
bars=[OHLCVBar(timestamp=now-timedelta(days=2-i),open=1,high=1,low=1,close=c,volume=10) for i,c in enumerate([1.0,1.1,float('nan')])]
s=OHLCVSeries(symbol='TEST',timeframe='1d',bars=bars,provider='x')
for label,fn in [('literal quote nan',lambda: g.validate_quote(q(float('nan'),'yfinance'),'TEST','US')),
                 ('literal series nan',lambda: g.validate_series(s,'TEST','US')),
                 ('fresh quote +inf',lambda: g.validate_quote(q(float('inf'),'ccxt'),'BTC/USDT','US',check_staleness=False))]:
    try: fn(); print(label,'ACCEPTED (defect)')
    except Exception as e: print(label,'REJECTED:',type(e).__name__, str(e)[:90])
# fresh: registry walk falls through a NaN lane to the healthy next lane (crypto)
class P:
    def __init__(s,id,rank,f): s.id=id; s.rank=rank; s.serves={'quote':f}
cands=[P('laneA',0,lambda sym: Quote(symbol='ETH/USDT',price=float('nan'),change=0.0,change_percent=0.0,currency='USD',market_state='REGULAR',timestamp=now,provider='laneA')),
       P('laneB',1,lambda sym: Quote(symbol='ETH/USDT',price=2500.0,change=0.0,change_percent=0.0,currency='USD',market_state='REGULAR',timestamp=now,provider='laneB'))]
pr._candidates=lambda *a,**k: cands
r=pr.get_quote('ETH/USDT','crypto','US'); print('fresh walk served by', r.provider, r.price)
