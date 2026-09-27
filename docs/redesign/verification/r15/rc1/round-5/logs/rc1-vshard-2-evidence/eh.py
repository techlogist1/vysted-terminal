import yfinance as yf
for s in ("INFY.NS","INFY","MSFT"):
    t=yf.Ticker(s)
    for a in ("earnings_history","earnings_dates"):
        try:
            v=getattr(t,a); print(s,a,"ok", None if v is None else getattr(v,"shape",v))
        except Exception as e: print(s,a,"RAISED",type(e).__name__, str(e)[:80])
