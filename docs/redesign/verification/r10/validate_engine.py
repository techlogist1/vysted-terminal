#!/usr/bin/env python3
"""R10 engine validation — app-vs-reference diffs against the live sidecar API.

Usage: validate_engine.py <sidecar_base_url>
Drives /resolve, /fundamentals, /history against the running sidecar and diffs
the bound entity + key figures against the independently-sourced reference pack
(docs/redesign/verification/r10/reference-pack.json). Resolver gate (1) is the
hard one: every fresh name must bind its correct NSE entity, never a foreign
ticker; marquee families must disambiguate.
"""

import json
import sys
import urllib.request
from pathlib import Path

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8799"
HERE = Path(__file__).resolve().parent
PACK = json.load(open(HERE / "reference-pack.json"))


def get(path: str) -> dict:
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=20) as r:
            return json.load(r)
    except Exception as e:  # noqa: BLE001
        return {"_error": str(e)}


def pct_diff(a, b) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return abs(a - b) / abs(b) * 100.0


print(f"=== R10 engine validation against {BASE} ===\n")

# --- Gate 1: resolver binds the right NSE entity for every fresh name ---------
print("## RESOLVER (gate 1) — fresh names bind correct NSE entity")
resolver_fail = 0
for stock in PACK["stocks"]:
    sym = stock["symbol"]
    want = stock["entity"]["nse_symbol"]
    r = get(f"/resolve?q={urllib.parse.quote(sym)}&region=IN")
    best = r.get("best") or r.get("resolved") or {}
    got = best.get("symbol")
    ok = got == want
    if not ok:
        resolver_fail += 1
    print(f"  {sym:12} want {want:12} got {str(got):12} {'OK' if ok else 'MISMATCH'}")
print(f"  -> {len(PACK['stocks']) - resolver_fail}/{len(PACK['stocks'])} bound correctly\n")

# --- Marquee disambiguation ---------------------------------------------------
print("## MARQUEE (gate 1) — families disambiguate, never guess")
for name in ["Tata", "Bajaj", "Adani"]:
    r = get(f"/resolve?q={name}&region=IN")
    needs = r.get("needs_disambiguation")
    cands = [c.get("symbol") for c in (r.get("candidates") or [])][:4]
    print(f"  {name:10} needs_disambiguation={needs} candidates={cands}")
print()

# --- Gate 11: fundamentals diffs ----------------------------------------------
print("## FUNDAMENTALS (gate 11) — app vs independent reference (>10% flagged)")
for stock in PACK["stocks"][:8]:
    want = stock["entity"]["nse_symbol"]
    fig = stock["figures"]
    f = get(f"/fundamentals/{want}.NS")
    data = f.get("data") or f
    print(f"  {want}:")
    for app_key, ref_key, label in [
        ("pe_ratio", "pe_ttm", "P/E"),
        ("market_cap", "market_cap_inr_crore", "mcap(cr)"),
    ]:
        av = data.get(app_key)
        rv = fig.get(ref_key)
        if app_key == "market_cap" and av:
            av = av / 1e7  # rupees -> crore
        d = pct_diff(av, rv)
        flag = "" if d is None else (" <<DIFF" if d > 10 else " ok")
        print(f"    {label:10} app={av} ref={rv} diff={d}{flag}")
print("\n=== done ===")
