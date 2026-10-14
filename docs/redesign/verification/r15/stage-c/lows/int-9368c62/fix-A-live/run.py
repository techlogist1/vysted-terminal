import json, subprocess, sys
base="http://127.0.0.1:52391/disclosures/"
lanes=["announcements","results","shareholding","corporate-actions","deals"]
syms=["FOCUS.BO","543312","FOCUS","AMAL.BO","INFY.NS","HDFCBANK"]
def get(l,s):
    out=subprocess.run(["curl","-s","-m","90","-H","X-Vysted-Region: IN",f"{base}{l}?symbol={s}"],capture_output=True,text=True).stdout
    return json.loads(out)
def rows(d):
    for k in ("items","rows","announcements","results","quarters","actions","deals","data"):
        if isinstance(d.get(k),list): return d[k]
    return [v for v in d.values() if isinstance(v,list)][0] if any(isinstance(v,list) for v in d.values()) else []
for l in lanes:
    res={s:get(l,s) for s in syms}
    for s,d in res.items():
        json.dump(d,open(f"live-A/{l}-{s}.json","w"),indent=1)
        r=rows(d)
        print(f"{l:18} {s:9} count={len(r)} sources={d.get('sources')} sym={d.get('symbol')} note={str(d.get('note') or d.get('notes') or '')[:60]!r}")
    print(f"  FOCUS.BO rows == 543312 rows: {rows(res['FOCUS.BO'])==rows(res['543312'])}")
