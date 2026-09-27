import sys; sys.path.insert(0, sys.argv[1])
import pandas as pd
from services import provider_health as ph, yfinance_provider as yp
def trip():
    ph.reset_for_tests()
    for _ in range(3): ph.record_rate_limited(ph.YAHOO)
    return ph.is_open(ph.YAHOO)
b=trip()
try:
    s=yp.get_history("KO","1d"); print("live KO history bars", len(s.bars), "open_before", b, "open_after", ph.is_open(ph.YAHOO))
except Exception as e: print("live KO raised", e, "open_after", ph.is_open(ph.YAHOO))
class T:
    def __init__(self,*a,**k): pass
    def history(self, period=None, interval=None):
        idx=pd.date_range("2026-09-01",periods=3,freq="D",tz="UTC")
        return pd.DataFrame({"Open":[1,2,3],"High":[1,2,3],"Low":[1,2,3],"Close":[1,2,3],"Volume":[10,10,10]},index=idx)
    recommendations = pd.DataFrame({"period":["0m"],"strongBuy":[1],"buy":[2],"hold":[0],"sell":[0],"strongSell":[0]})
    analyst_price_targets = {"current":1,"low":1,"high":2,"mean":1.5,"median":1.5}
yp.yf.Ticker = T
b=trip(); s=yp.get_history("ZZZ","1d"); print("stub history", len(s.bars), "open_before", b, "open_after", ph.is_open(ph.YAHOO))
b=trip()
try:
    yp.get_analyst_rating("ZZZ"); print("stub analyst open_before", b, "open_after", ph.is_open(ph.YAHOO))
except Exception as e: print("stub analyst raised", e, ph.is_open(ph.YAHOO))
