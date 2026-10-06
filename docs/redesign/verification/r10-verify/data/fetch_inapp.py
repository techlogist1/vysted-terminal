#!/usr/bin/env python3
"""Fetch in-app quote+fundamentals for the fresh-stock battery (read-only)."""
import json
import sys
import urllib.request

PORT = sys.argv[1] if len(sys.argv) > 1 else "59415"
NAMES = {
    "ASIANPAINT": "Asian Paints (large, NSE)",
    "TITAN": "Titan Company (large, NSE)",
    "SUNPHARMA": "Sun Pharmaceutical (large, NSE)",
    "NESTLEIND": "Nestle India (large, NSE)",
    "COFORGE": "Coforge (mid, IT, NSE)",
    "SUPREMEIND": "Supreme Industries (mid, NSE)",
    "ASTRAL": "Astral (mid, NSE)",
    "ABBOTINDIA": "Abbott India (mid, NSE)",
    "FINEORG": "Fine Organic Industries (small, NSE)",
    "CARTRADE": "CarTrade Tech (small, NSE)",
    "HOMEFIRST": "Home First Finance (small, NSE)",
    "KSCL": "Kaveri Seed (small/micro, NSE)",
}
FIELDS = [
    "sector", "industry", "market_cap", "pe_ratio", "forward_pe", "price_to_book",
    "dividend_yield", "dividend_per_share", "eps", "fifty_two_week_high",
    "fifty_two_week_low", "fifty_two_week_change", "roe", "revenue_growth",
    "earnings_growth", "profit_margin", "debt_to_equity", "book_value", "provider",
]


def get(path, timeout=60):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=timeout) as r:
        return json.load(r)


out = {}
for sym, desc in NAMES.items():
    rec = {"desc": desc}
    try:
        q = get(f"/quotes/{sym}")
        rec["price"] = q.get("price")
        rec["currency"] = q.get("currency")
        rec["quote_provider"] = q.get("provider")
        rec["quote_ts"] = q.get("timestamp")
    except Exception as e:  # noqa: BLE001
        rec["quote_error"] = str(e)[:60]
    try:
        f = get(f"/fundamentals/{sym}")
        for k in FIELDS:
            rec[k] = f.get(k)
        rec["mcap_cr"] = round(f["market_cap"] / 1e7, 1) if f.get("market_cap") else None
    except Exception as e:  # noqa: BLE001
        rec["fund_error"] = str(e)[:60]
    out[sym] = rec
    mc = rec.get("mcap_cr")
    print(
        f"{sym:<12} px={rec.get('price')!s:<9} mcap={mc!s:<10}cr "
        f"PE={rec.get('pe_ratio')!s:<10} ROE={rec.get('roe')!s:<10} "
        f"52w={rec.get('fifty_two_week_low')}-{rec.get('fifty_two_week_high')}"
    )

with open(sys.argv[0].rsplit("/", 1)[0] + "/inapp_fundamentals.json", "w") as fh:
    json.dump(out, fh, indent=1)
print("\nwrote inapp_fundamentals.json")
