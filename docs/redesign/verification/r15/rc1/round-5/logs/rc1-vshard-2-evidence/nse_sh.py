from curl_cffi import requests
s=requests.Session(impersonate="chrome")
s.get("https://www.nseindia.com/", timeout=20)
for sym in ("AXIOMGAS","SUMAX"):
    for idx in ("sme","equities"):
        r=s.get(f"https://www.nseindia.com/api/corporate-share-holdings-master?index={idx}&symbol={sym}", timeout=20, headers={"Referer":"https://www.nseindia.com/"})
        try: j=r.json(); n=len(j) if isinstance(j,list) else j
        except Exception: n=r.text[:80]
        print(sym, idx, r.status_code, n, (j[0] if isinstance(j,list) and j else "")) 
