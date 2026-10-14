import json, subprocess, os, sys
base = "http://127.0.0.1:52395/disclosures/shareholding?symbol="
d0 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "json-seq")
pairs = [("KALYANI.BO", "544023"), ("RAJPUTANA.BO", "539090"), ("ZEAL.BO", "539963")]
def get(s):
    return json.loads(subprocess.run(["curl", "-s", "-m", "110", "-H", "X-Vysted-Region: IN", base + s], capture_output=True, text=True).stdout)
for a, b in pairs:
    for attempt in (1, 2):
        da, db = get(a), get(b)
        json.dump(da, open(f"{d0}/shareholding-{a}-{attempt}.json", "w"), indent=1)
        json.dump(db, open(f"{d0}/shareholding-{b}-{attempt}.json", "w"), indent=1)
        ra, rb = da.get("patterns") or [], db.get("patterns") or []
        nulls = lambda r: sum(1 for q in r if q.get("promoter_percent") is None)
        print(f"attempt {attempt} {a} vs {b}: equal={ra == rb} n={len(ra)}/{len(rb)} sym={da.get('symbol')}/{db.get('symbol')} null-promoter-rows={nulls(ra)}/{nulls(rb)} keys={[k for k in da if isinstance(da[k], list)]}", flush=True)
