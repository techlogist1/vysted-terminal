from datetime import UTC, datetime
from fastapi.testclient import TestClient
from app import create_app
from models.market import Quote
from services import locale, provider_registry
def freeze(now):
    class F(datetime):
        @classmethod
        def now(cls, tz=None): return now.astimezone(tz) if tz else now
    locale.datetime=F
TS={}
def quote(symbol, asset_class="equity"):
    return Quote(symbol=symbol, price=100.0, change=0.0, change_percent=0.0, timestamp=TS[symbol], provider=TS.get(symbol+'#p','yfinance'))
provider_registry.get_quote=quote
c=TestClient(create_app())
def run(label, now, sym, ts, region):
    freeze(now); TS[sym]=ts
    r=c.get('/quotes/'+sym.replace('^','%5E'), headers={'X-Vysted-Region':region}).json()
    print(f"{label:55s} region={region} -> {r.get('freshness')}")
NSE=datetime(2026,9,23,5,0,tzinfo=UTC)          # 10:30 IST Wed, US closed
run('LITERAL AAPL@NSE hours (US closed)', NSE, 'AAPL', NSE, 'IN')
for s in ('^NSEI','^NSEBANK','^CNXIT','^INDIAVIX'):
    for reg in ('IN','US'): run(f'{s} @NSE hours', NSE, s, NSE, reg)
USH=datetime(2026,9,23,15,0,tzinfo=UTC)         # 11:00 ET Wed; ASX closed (01:00 AEST Thu); LSE closed 15:30? (16:00 BST open until 15:30 UTC)
ASX_CLOSE=datetime(2026,9,23,6,10,tzinfo=UTC)   # 16:10 AEST Wed close
run('FRESH BHP.AX @US hours, ASX closed since 06:10Z', USH, 'BHP.AX', ASX_CLOSE, 'IN')
run('FRESH BHP.AX @US hours, ASX closed since 06:10Z', USH, 'BHP.AX', ASX_CLOSE, 'US')
USH2=datetime(2026,9,23,18,0,tzinfo=UTC)        # 14:00 ET; LSE closed at 15:30Z
LSE_CLOSE=datetime(2026,9,23,15,30,tzinfo=UTC)
run('FRESH VOD.L @US hours, LSE closed since 15:30Z', USH2, 'VOD.L', LSE_CLOSE, 'US')
ASXH=datetime(2026,9,24,2,0,tzinfo=UTC)         # 12:00 AEST Thu, ASX open; US closed
run('FRESH BHP.AX @ASX open (US closed)', ASXH, 'BHP.AX', ASXH, 'US')
