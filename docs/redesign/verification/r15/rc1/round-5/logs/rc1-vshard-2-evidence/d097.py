import sys; sys.path.insert(0, sys.argv[1])
import yfinance as yf
from services import symbol_resolver as sr
clock=[1000.0]
sr.time.monotonic = lambda: clock[0]
listed=[False]
class S:
    def __init__(self, q, **k):
        self.quotes = [{"symbol":"NEWCO-SM.NS","shortname":"Newco Freshlisted Ltd","exchange":"NSI"}] if listed[0] else []
yf.Search = S
sr._reset_live_lookup_for_tests()
for region in ("IN","US"):
    listed[0]=False; sr._reset_live_lookup_for_tests(); clock[0]=1000.0
    q="Zqxwvortle Qlorticbex"
    r1=sr.resolve(q, region); listed[0]=True
    r2=sr.resolve(q, region)  # within TTL -> negative still cached
    clock[0]+=sr._LIVE_EMPTY_TTL_SECONDS+1
    r3=sr.resolve(q, region)
    print(region, "t0", [c.symbol for c in r1.candidates], "| listed within TTL", [c.symbol for c in r2.candidates], "| after TTL+1", [c.symbol for c in r3.candidates])
print("TTL s", sr._LIVE_EMPTY_TTL_SECONDS)
