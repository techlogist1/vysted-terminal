"""LEAD-037: for each live run that called price_data, rebuild its payload (the /history slice for the same
args, last 90 bars, + /quotes) from the running :52310 app and classify every currency figure in the reply:
QUOTE (= /quotes price), LASTBAR (= latest bar field), OLDBAR (a value of an older bar: stale-as-current if
the sentence calls it current/latest), PAYLOAD-OTHER, or INVENTED (in no payload value)."""
import glob, json, re, sys, urllib.request
from decimal import Decimal
BASE = "http://127.0.0.1:52310"
def j(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r: return json.load(r)
FIG = re.compile(r"(?:₹|Rs\.?\s?|INR\s?)\s*(\d[\d,]*(?:\.\d+)?)")
cache = {}
def payload(sym, args):
    tf = args.get("timeframe", "1d"); rng = args.get("range") or args.get("range_") or "6mo"
    k = (sym, tf, rng)
    if k not in cache:
        h = j(f"/history/{sym}?timeframe={tf}&range={rng}")["bars"][-90:]
        q = j(f"/quotes/{sym}")
        cache[k] = (h, q)
    return cache[k]
def match(v, x, dec):
    return x is not None and round(Decimal(str(x)), dec) == v
rows = []
for f in sorted(glob.glob(sys.argv[1] + "/*.jsonl")):
    evs = [json.loads(l) for l in open(f) if l.strip()]
    calls = [e for e in evs if e.get("kind") == "tool_use" and e.get("name") == "price_data"]
    oks = {e["tool_call_id"] for e in evs if e.get("kind") == "tool_result" and e.get("ok")}
    calls = [c for c in calls if c["tool_call_id"] in oks and isinstance((c.get("input") or {}).get("symbol"), str)]
    if not calls: continue
    text = "".join(e.get("text") or "" for e in evs if e.get("kind") == "delta")
    tag = f.split("/")[-1][:-6]
    for c in calls:
        sym = c["input"]["symbol"]; bars, q = payload(sym, c["input"]); qp = q.get("price")
        for m in FIG.finditer(text):
            raw = m.group(1).replace(",", ""); dec = len(raw.split(".")[1]) if "." in raw else 0
            v = Decimal(raw)
            if match(v, qp, dec): cls = "QUOTE"
            elif any(match(v, bars[-1].get(k), dec) for k in ("open", "high", "low", "close")): cls = "LASTBAR"
            else:
                hit = [(b["timestamp"][:10], k) for b in bars[:-1] for k in ("open", "high", "low", "close") if match(v, b.get(k), dec)]
                if hit: cls = f"OLDBAR{hit[-1]}"
                elif any(match(v, abs(x), dec) for x in q.values() if isinstance(x, (int, float))): cls = "PAYLOAD-OTHER(quote field)"
                else: cls = "INVENTED"
            off = f"{(float(v) - qp) / qp * 100:+.1f}%" if qp else "?"
            s = text.rfind(".", 0, m.start()) + 1
            rows.append((tag, sym, str(c["input"]), str(v), qp, cls, off, text[s:m.end() + 40].strip().replace("\n", " ")[:160]))
for r in rows: print(" | ".join(map(str, r)))
