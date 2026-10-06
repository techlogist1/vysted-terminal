#!/usr/bin/env python3
"""Malformed-symbol inducer: every symbol-taking GET route a panel calls, on MY sidecar (:52224)."""
import json, sys, time, urllib.error, urllib.parse, urllib.request
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 52224
OUT = sys.argv[2]
SYMS = {
    "spaces": "   ",
    "dollars": "$$$",
    "len300": "A" * 300,
    "sql": "RELIANCE'; DROP TABLE positions;--",
    "html": "<script>alert(1)</script>",
    "unicode_hi": "रिलायंस",
    "emoji": "\U0001F680MOON",
    "double_suffix": "RELIANCE.NS.NS",
    "path_trav": "../../etc/passwd",
}
def routes(s):
    e = urllib.parse.quote(s, safe="")
    q = urllib.parse.quote(s)
    return {
        "quote": f"/quotes/{e}",
        "quotes_batch": f"/quotes?symbols={q}",
        "history": f"/history/{e}?timeframe=1d&range=1mo",
        "fundamentals": f"/fundamentals/{e}",
        "indicators": f"/indicators/{e}?indicators=rsi",
        "resolve": f"/resolve?q={q}",
        "autocomplete": f"/resolve/autocomplete?q={q}",
        "earnings_hist": f"/earnings/{e}/history",
        "news": f"/news?symbols={q}&limit=3",
    }
rows = []
with open(OUT, "w") as fh:
    for tag, s in SYMS.items():
        for rname, path in routes(s).items():
            t0 = time.time()
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=60) as r:
                    code, body = r.status, r.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as ex:
                code, body = ex.code, ex.read().decode("utf-8", "replace")
            except Exception as ex:  # noqa: BLE001
                code, body = -1, f"{type(ex).__name__}: {ex}"
            row = {"sym": tag, "route": rname, "path": path[:120], "status": code,
                   "secs": round(time.time() - t0, 2), "body": body[:400]}
            fh.write(json.dumps(row, ensure_ascii=False) + "\n"); fh.flush()
            print(f"{tag:14} {rname:14} {code:4} {row['secs']:6}s {body[:110]!r}")
