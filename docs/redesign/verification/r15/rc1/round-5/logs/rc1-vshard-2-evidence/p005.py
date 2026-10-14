import json, urllib.request, concurrent.futures as cf
def req(vd, method="black-scholes", steps=None):
    b={"exercise":"european" if method!="binomial" else "american","payoff":"call","spot":100,"strike":95,"risk_free_rate":0.05,"dividend_yield":0.0,"volatility":0.2,
       "valuation_date":vd,"expiry_date":"2030-06-30","method":method}
    if steps: b["binomial_steps"]=steps
    r=urllib.request.Request("http://127.0.0.1:52602/quant/option/price",data=json.dumps(b).encode(),headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(r,timeout=90).read())
A,B="2026-05-16","2030-01-02"
refA=req(A); refB=req(B); print("ref A", refA.get("price"), "ref B", refB.get("price"))
jobs=[]
with cf.ThreadPoolExecutor(16) as ex:
    for i in range(200):
        vd=A if i%2==0 else B
        jobs.append((vd, ex.submit(req, vd)))
    bad=[(vd, f.result().get("price")) for vd,f in jobs if abs(f.result().get("price") - (refA if vd==A else refB)["price"])>1e-9]
print("concurrent BS pricings", len(jobs), "mismatched", len(bad), bad[:3])
# fresh: american binomial at two dates concurrently
bA=req(A,"binomial",800); bB=req(B,"binomial",800)
with cf.ThreadPoolExecutor(8) as ex:
    fs=[(vd, ex.submit(req, vd, "binomial", 800)) for vd in [A,B]*20]
    bad2=[(vd,f.result().get("price")) for vd,f in fs if abs(f.result()["price"]-(bA if vd==A else bB)["price"])>1e-9]
print("binomial ref", bA["price"], bB["price"], "concurrent", len(fs), "mismatched", len(bad2))
