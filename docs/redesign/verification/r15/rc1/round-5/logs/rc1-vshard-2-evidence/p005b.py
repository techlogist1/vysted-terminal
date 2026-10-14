import json, urllib.request, threading, time
b={"exercise":"american","payoff":"put","spot":100,"strike":105,"risk_free_rate":0.05,"dividend_yield":0.0,"volatility":0.3,"valuation_date":"2026-09-27","expiry_date":"2031-06-30","method":"binomial","binomial_steps":20000}
out={}
def price():
    t=time.monotonic(); r=urllib.request.Request("http://127.0.0.1:52602/quant/option/price",data=json.dumps(b).encode(),headers={"Content-Type":"application/json"})
    out["p"]=json.loads(urllib.request.urlopen(r,timeout=100).read()).get("price"); out["dt"]=time.monotonic()-t
th=threading.Thread(target=price); th.start(); time.sleep(0.3)
lat=[]
while th.is_alive():
    t=time.monotonic(); urllib.request.urlopen("http://127.0.0.1:52602/health",timeout=30).read(); lat.append(time.monotonic()-t); time.sleep(0.2)
print("pricing", out, "health calls during", len(lat), "max latency s", round(max(lat) if lat else -1,3))
