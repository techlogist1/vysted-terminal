from datetime import datetime, UTC
from services import locale
from routers.quotes import _label_freshness
from models.market import Quote
import inspect
def freeze(t):
    class F(datetime):
        @classmethod
        def now(cls, tz=None): return t if tz is None else t.astimezone(tz)
    locale.datetime=F
NSE_HOURS=datetime(2026,9,23,5,0,tzinfo=UTC)   # Wed 10:30 IST, US closed
US_HOURS=datetime(2026,9,23,15,0,tzinfo=UTC)   # Wed 11:00 ET, NSE + ASX + TSE + HKEX closed
flds=Quote.model_fields
def q(sym,prov,ts,cur="USD"):
    kw=dict(symbol=sym,price=1.0,provider=prov,timestamp=ts)
    for k in ('currency','change','change_percent','volume'):
        if k in flds: kw.setdefault(k, cur if k=='currency' else 0.0)
    return Quote(**{k:v for k,v in kw.items() if k in flds})
cases=[
 ("AAPL","yfinance",NSE_HOURS,NSE_HOURS,"expect not live (US closed)"),
 ("^NSEI","yfinance",NSE_HOURS,NSE_HOURS,"expect live"),
 ("^BSESN","yfinance",NSE_HOURS,NSE_HOURS,"expect live"),
 ("^NSEBANK","yfinance",NSE_HOURS,NSE_HOURS,"expect live"),
 ("BHP.AX","yfinance",datetime(2026,9,23,6,0,tzinfo=UTC),US_HOURS,"ASX closed -> expect not live"),
 ("7203.T","yfinance",datetime(2026,9,23,6,0,tzinfo=UTC),US_HOURS,"TSE closed -> expect not live"),
 ("0700.HK","yfinance",datetime(2026,9,23,8,0,tzinfo=UTC),US_HOURS,"HKEX closed -> expect not live"),
 ("VOD.L","yfinance",datetime(2026,9,23,15,0,tzinfo=UTC),US_HOURS,"LSE open 15:00 UTC -> live ok"),
 ("VOD.L","yfinance",datetime(2026,9,23,16,30,tzinfo=UTC),datetime(2026,9,23,18,0,tzinfo=UTC),"LSE closed 18:00 UTC -> expect not live"),
 ("^N225","yfinance",datetime(2026,9,23,6,0,tzinfo=UTC),US_HOURS,"TSE index closed -> expect not live"),
 ("BHP.AX","yfinance",datetime(2026,9,23,2,0,tzinfo=UTC),datetime(2026,9,23,2,30,tzinfo=UTC),"ASX OPEN -> expect live"),
]
for sym,prov,ts,now,note in cases:
    freeze(now); r=_label_freshness(q(sym,prov,ts),"equity")
    print(sym.ljust(9), "now",now.isoformat()[11:16],"UTC ->", r.freshness, "|", note, "| region", locale.instrument_region(sym,prov))
