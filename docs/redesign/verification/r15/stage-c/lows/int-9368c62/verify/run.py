import json, subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor
base = "http://127.0.0.1:52395/disclosures/"
lanes = ["announcements", "results", "shareholding", "corporate-actions", "deals"]
pairs = {"FOCUS": "543312", "KALYANI": "544023", "RAJPUTANA": "539090", "MAL": "531613", "SEL": "509423", "ZEAL": "539963"}
syms = []
for n, c in pairs.items():
    syms += [n + ".BO", c, n]
syms += ["AMAL.BO", "AMAL", "INFY.NS", "HDFCBANK"]
out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "json")
def get(ls):
    l, s = ls
    o = subprocess.run(["curl", "-s", "-m", "110", "-H", "X-Vysted-Region: IN", f"{base}{l}?symbol={s}"], capture_output=True, text=True).stdout
    try:
        d = json.loads(o)
    except Exception:
        d = {"_raw": o[:500]}
    json.dump(d, open(f"{out_dir}/{l}-{s}.json", "w"), indent=1)
    return ls, d
def rows(d):
    for k in ("items", "rows", "announcements", "results", "quarters", "actions", "deals", "data"):
        if isinstance(d.get(k), list):
            return d[k]
    ls = [v for v in d.values() if isinstance(v, list) and k not in ("sources", "errors")]
    return ls[0] if ls else []
with ThreadPoolExecutor(6) as ex:
    res = dict(ex.map(get, [(l, s) for l in lanes for s in syms]))
def src(d):
    return d.get("sources")
for l in lanes:
    for s in syms:
        d = res[(l, s)]
        print(f"{l:18} {s:10} n={len(rows(d)):4} cov={d.get('coverage')} sym={d.get('symbol')} sources={src(d)} note={str(d.get('note') or '')[:90]!r} err={str(d.get('errors') or d.get('detail') or '')[:80]!r}")
    for n, c in pairs.items():
        a, b = rows(res[(l, n + '.BO')]), rows(res[(l, c)])
        print(f"  CHECK {l} {n}.BO == {c}: {a == b} (n={len(a)})")
    print(f"  CHECK {l} AMAL.BO == AMAL: {rows(res[(l,'AMAL.BO')]) == rows(res[(l,'AMAL')])}")
