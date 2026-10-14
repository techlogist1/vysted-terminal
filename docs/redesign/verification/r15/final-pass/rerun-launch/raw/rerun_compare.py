#!/usr/bin/env python3
"""Compare the 1fddb2b1 replay against the d38b5d1a record; write a markdown table."""
import json, sys
V = "docs/redesign/verification/r15/"
REC_M, REC_C = V + "surface/failure-inducer/final/10-malformed-symbols.jsonl", V + "surface/panels-layouts/final/P-http-replay.jsonl"
RAW = V + "final-pass/rerun-launch/raw/"
def load(p): return [json.loads(l) for l in open(p) if l.strip()]
def typed404(body):
    try: d = json.loads(body)
    except ValueError: return False
    return isinstance(d, dict) and isinstance(d.get("detail"), str) and d["detail"] != "Not Found" and "code" in d
out, bad = [], 0
def emit(lane, key, url, rec, new, body):
    global bad
    flags = []
    if new >= 500 or new < 0: flags.append("5xx/err")
    if new == 404 and not typed404(body): flags.append("untyped-404")
    if new != rec: flags.append("status-diff")
    bad += bool(flags)
    out.append(f"| {lane} | {key} | `{url[:70]}` | {rec} | {new} | {', '.join(flags) or 'same'} | `{body[:90].replace('|', '/')}` |")
rec = {(r["sym"], r["route"]): r for r in load(REC_M)}
for r in load(RAW + "10-malformed-symbols.jsonl"):
    emit("malformed", f"{r['sym']}/{r['route']}", r["path"], rec[(r["sym"], r["route"])]["status"], r["status"], r["body"])
recc = {r["label"]: r for r in load(REC_C)}
for r in load(RAW + "P-census-replay.jsonl"):
    emit("census", r["label"], r["url"], recc[r["label"]]["status"], r["status"], r["body"])
hdr = ["| lane | key | url | d38b5d1a | 1fddb2b1 | flags | body excerpt |", "|---|---|---|---|---|---|---|"]
open(RAW + "replay-table.md", "w").write("\n".join(hdr + out) + f"\n\nrows={len(out)} flagged={bad}\n")
print(f"rows={len(out)} flagged={bad}")
for l in out:
    if "| same |" not in l: print(l)
