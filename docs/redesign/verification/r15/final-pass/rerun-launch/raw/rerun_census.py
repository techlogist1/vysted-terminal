#!/usr/bin/env python3
"""Replay the in-scope census GETs (from the d38b5d1a P-http-replay.jsonl) on PORT; same shape as the record."""
import json, re, sys, time, urllib.error, urllib.request
PORT, SRC, OUT = int(sys.argv[1]), sys.argv[2], sys.argv[3]
PAT = re.compile(r'^/(fundamentals/[^/?]+(/(income|balance|cashflow))?(\?|$)|quotes\?symbols=|resolve/autocomplete|news(\?|$)|earnings/[^/?]+/estimates)')
rows = [json.loads(l) for l in open(SRC)]
sel = [r for r in rows if r["method"] == "GET" and PAT.match(r["url"])]
with open(OUT, "w") as fh:
    for r in sel:
        t0 = time.time()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{r['url']}", timeout=240) as resp:
                code, body = resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as ex:
            code, body = ex.code, ex.read().decode("utf-8", "replace")
        except Exception as ex:  # noqa: BLE001
            code, body = -1, f"{type(ex).__name__}: {ex}"
        row = {"label": r["label"], "url": r["url"], "status": code, "ms": int((time.time() - t0) * 1000),
               "bytes": len(body.encode()), "body": body[:600]}
        fh.write(json.dumps(row, ensure_ascii=False) + "\n"); fh.flush()
        print(f"{r['label']:40} {code:4} {row['ms']:6}ms {body[:100]!r}", flush=True)
