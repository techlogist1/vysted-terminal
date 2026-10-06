#!/usr/bin/env python3
"""R10-VERIFY resolver ambiguity battery (read-only). Hits the LIVE sidecar
/resolve for the full marquee/ambiguity list and records the verdict + a doctrine
check (an Indian-name query must never bind a foreign/OTC ticker; specific names
must bind their correct entity; family names must disambiguate, not guess)."""
import json
import sys
import urllib.parse
import urllib.request

PORT = sys.argv[1] if len(sys.argv) > 1 else "59415"
BASE = f"http://127.0.0.1:{PORT}/resolve"

# (query, expectation)  exp: ("bind", SYMBOL) | ("disambig", first_candidate_or_None) | ("either",)
BATTERY = [
    # E1 regression repros — must never bind REFR/FRLCY/LNKS/RECX/RPOWER
    ("research Reliance", ("bind", "RELIANCE")),
    ("Reliance Q4 results", ("bind", "RELIANCE")),
    ("Reliance Industries Q4 FY26 results", ("bind", "RELIANCE")),
    ("RELIANCE.NS", ("bind", "RELIANCE")),
    # Tata family
    ("Tata", ("disambig", None)),
    ("Tata Motors", ("either",)),
    ("Tata Steel", ("bind", "TATASTEEL")),
    ("TCS", ("bind", "TCS")),
    ("Tata Consultancy Services", ("bind", "TCS")),
    # Bajaj family
    ("Bajaj", ("disambig", None)),
    ("Bajaj Finance", ("either",)),
    ("Bajaj Auto", ("either",)),
    # Adani family
    ("Adani", ("disambig", None)),
    ("Adani Enterprises", ("either",)),
    ("Adani Ports", ("either",)),
    # Other marquee families (bare)
    ("Birla", ("either",)),
    ("Mahindra", ("either",)),
    ("Jindal", ("either",)),
    ("Godrej", ("either",)),
    # HDFC family
    ("HDFC", ("either",)),
    ("HDFC Bank", ("either",)),
    ("HDFCBANK", ("bind", "HDFCBANK")),
    ("HDFCLIFE", ("bind", "HDFCLIFE")),
    ("HDFCAMC", ("bind", "HDFCAMC")),
    # L&T spellings
    ("L&T", ("either",)),
    ("LT", ("either",)),
    ("Larsen & Toubro", ("either",)),
    ("Larsen and Toubro", ("either",)),
]


def resolve(q):
    url = f"{BASE}?q={urllib.parse.quote(q)}&region=IN"
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def is_foreign(inst):
    return inst and inst.get("region") not in ("IN", None) and inst.get("exchange") not in (
        "NSE",
        "BSE",
    )


rows = []
raw = {}
for q, exp in BATTERY:
    try:
        d = resolve(q)
    except Exception as e:  # noqa: BLE001
        rows.append((q, "ERROR", str(e)[:40], "FAIL"))
        continue
    raw[q] = d
    resolved = d.get("resolved")
    disambig = d.get("needs_disambiguation")
    cands = d.get("candidates") or []
    top = [c["symbol"] for c in cands[:4]]
    # doctrine: any foreign bind for an Indian query is a hard fail
    foreign_bind = is_foreign(resolved)
    foreign_cand = any(is_foreign(c) for c in cands)
    if resolved:
        verdict = f"BIND {resolved['symbol']} ({resolved['exchange']})"
    elif disambig:
        verdict = f"DISAMBIG {top}"
    else:
        verdict = f"UNRESOLVED {top}"
    # check expectation
    status = "ok"
    kind = exp[0]
    if kind == "bind":
        status = "ok" if (resolved and resolved["symbol"] == exp[1]) else "MISMATCH"
    elif kind == "disambig":
        status = "ok" if disambig else "MISMATCH"
    elif kind == "either":
        status = "ok" if (resolved or disambig) else "MISMATCH"
    flags = []
    if foreign_bind:
        flags.append("FOREIGN_BIND")
    if foreign_cand:
        flags.append("foreign_cand")
    rows.append((q, verdict, " ".join(flags) or "-", status))

print(f"{'QUERY':<38} {'VERDICT':<34} {'FLAGS':<18} STATUS")
print("-" * 100)
nfail = 0
for q, v, f, s in rows:
    if s != "ok" or "FOREIGN_BIND" in f:
        nfail += 1
    print(f"{q:<38} {v:<34} {f:<18} {s}")
print("-" * 100)
print(f"queries: {len(rows)}  failures/foreign-binds: {nfail}")

with open(sys.argv[0].rsplit("/", 1)[0] + "/resolver_battery_raw.json", "w") as fh:
    json.dump(raw, fh, indent=1)
