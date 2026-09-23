#!/usr/bin/env python3
"""S2B screener driver: POST /screener/run/stream with EXACTLY the body src/store/screener.ts:320-333
builds, parse SSE frames like processFrame (:436-455), append one record per run to a .jsonl.
  scr.py <label> '<json request>' --out FILE [--port 52219] [--cancel-after S] [--unary]
"""
import argparse, json, time, http.client, socket
ap = argparse.ArgumentParser()
ap.add_argument("label"); ap.add_argument("body")
ap.add_argument("--port", type=int, default=52219)
ap.add_argument("--out", required=True)
ap.add_argument("--cancel-after", type=float)
ap.add_argument("--unary", action="store_true")
ap.add_argument("--rows", type=int, default=12, help="rows to keep in the record")
a = ap.parse_args()
req = json.loads(a.body)
conn = http.client.HTTPConnection("127.0.0.1", a.port, timeout=600)
t0 = time.time()
path = "/screener/run" if a.unary else "/screener/run/stream"
conn.request("POST", path, json.dumps(req), {"Content-Type": "application/json"})
resp = conn.getresponse()
rec = {"label": a.label, "path": path, "request": req, "status": resp.status, "t0": t0}
frames = []; result = None; err = None; buf = b""; cancelled = False
if resp.status != 200:
    rec["body"] = resp.read().decode()[:3000]
elif a.unary:
    result = json.loads(resp.read())
else:
    while True:
        if a.cancel_after and time.time() - t0 > a.cancel_after:
            cancelled = True
            conn.sock.shutdown(socket.SHUT_RDWR); conn.close(); break
        chunk = resp.read1(65536) if hasattr(resp, "read1") else resp.read(65536)
        if not chunk: break
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            s = line.decode().strip()
            if not s or s.startswith(":"): continue
            js = s[5:].strip() if s.startswith("data:") else s
            try: f = json.loads(js)
            except ValueError: frames.append({"_unparsed": js[:200]}); continue
            f["_t"] = round(time.time() - t0, 2)
            if f.get("event") == "result": result = f
            elif f.get("event") == "error": err = f
            else: frames.append(f)
rec["elapsed_s"] = round(time.time() - t0, 2)
rec["cancelled"] = cancelled
rec["progress_frames"] = len(frames)
rec["progress_sample"] = frames[:3] + (frames[-3:] if len(frames) > 6 else frames[3:])
rec["error_frame"] = err
if result:
    rows = result.pop("rows", [])
    sd = result.pop("skip_details", [])
    from collections import Counter
    rec["result"] = result
    rec["rows_len"] = len(rows)
    rec["skip_reasons"] = dict(Counter(d["reason"] for d in sd).most_common(12))
    rec["skip_details_len"] = len(sd)
    rec["rows"] = rows[: a.rows]
    rec["rows_tail"] = rows[-2:] if len(rows) > a.rows else []
    rec["all_symbols"] = [r["symbol"] for r in rows]
open(a.out, "a").write(json.dumps(rec) + "\n")
r = rec.get("result") or {}
print(json.dumps({"label": a.label, "status": resp.status, "elapsed_s": rec["elapsed_s"], "frames": len(frames),
  "evaluated": r.get("evaluated_count"), "result_count": r.get("result_count"), "rows": rec.get("rows_len"),
  "skipped": r.get("skipped_count"), "partial": r.get("partial"), "coverage": r.get("coverage"),
  "throttled": r.get("throttled"), "basis": r.get("basis_counts"), "skip_reasons": rec.get("skip_reasons"),
  "error_frame": err, "body": rec.get("body", "")[:400], "top": [(x["symbol"], x.get("pe_ratio"), x.get("market_cap"), x.get("currency")) for x in rec.get("rows", [])[:5]]}, default=str))
