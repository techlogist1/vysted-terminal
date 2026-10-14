from services.research import verify as v
def ev(s_urls, n_urls, text="native says yes"):
    res={"ok":True,"citations":[{"url":u} for u in s_urls]}
    nat={"ok":True,"text":text,"citations":[{"url":u} for u in n_urls]}
    e=v._claim_evidence(res,nat)
    row=v._check_row("claim","agree","d",e,dual=True)
    return sorted(e["domains"]), e["independence"], e["distinct_lanes"], row["corroborated"]
cases={
 "entry literal: one domain both lanes": (["https://www.moneycontrol.com/a"],["https://moneycontrol.com/b"]),
 "fresh: m.moneycontrol vs www": (["https://m.moneycontrol.com/a"],["https://www.moneycontrol.com/b"]),
 "fresh: yahoo regional subdomains": (["https://in.finance.yahoo.com/q"],["https://uk.finance.yahoo.com/q"]),
 "fresh: bbc.co.uk hosts": (["https://www.bbc.co.uk/news/x"],["https://news.bbc.co.uk/y"]),
 "fresh: uppercase+port": (["https://WWW.BSEINDIA.COM:443/x"],["https://api.bseindia.com/y"]),
 "fresh: searxng two hosts one domain, uncited native": (["https://economictimes.indiatimes.com/a","https://m.economictimes.indiatimes.com/b"],[]),
 "control: two domains": (["https://blog.example/a"],["https://other.example/b"]),
}
for k,(s,n) in cases.items():
    print(k, ev(s,n))
print("searxng-only 2 hosts same domain (no native):", v._claim_evidence({"ok":True,"citations":[{"url":"https://www.livemint.com/a"},{"url":"https://epaper.livemint.com/b"}]},{})["independence"])
