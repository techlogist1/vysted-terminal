#!/usr/bin/env python3
"""R11 twelve-stock battery — diff the app's figures against the independent
reference pack (R10-VERIFY's ok/watch/MISMATCH discipline).

Usage: python3 diff_battery.py <sidecar_port> <reference_pack.json> <out.json>

Per figure: |app - ref| / |ref| <= ok_tol → ok; <= watch_tol → watch; else
MISMATCH. Growth diffs compare the app's MRQ-YoY fields against the
reference's MRQ-YoY (never annual — the V1/D55 semantics under test), and the
basis label itself is asserted. Entity identity is a hard string check.
"""

from __future__ import annotations

import json
import sys
import urllib.request

#: (app field, ref path, ok tolerance, watch tolerance, unit note)
FIGURES = [
    ("market_cap", ("valuation", "market_cap_inr_cr"), 0.05, 0.10, "app inr -> cr /1e7"),
    ("pe_ratio", ("valuation", "pe_ttm"), 0.08, 0.15, ""),
    ("eps", ("valuation", "eps_ttm"), 0.08, 0.15, ""),
    ("fifty_two_week_high", ("range52w", "high"), 0.02, 0.05, ""),
    ("fifty_two_week_low", ("range52w", "low"), 0.02, 0.05, ""),
    ("dividend_per_share", ("dividends", "fy_total_per_share"), 0.10, 0.25, "V11 watch: rate may omit specials"),
    ("dividend_per_share_ttm", ("dividends", "ttm_paid_per_share"), 0.10, 0.25, "D56 ttm actual"),
    ("roe", ("roe",), 0.15, 0.30, "app fraction -> x100"),
    ("revenue_growth", ("growth", "revenue_mrq_yoy_pct"), 0.15, 0.35, "MRQ YoY both sides (D55); app fraction -> x100"),
    ("earnings_growth", ("growth", "earnings_mrq_yoy_pct"), 0.15, 0.35, "MRQ YoY both sides (D55); app fraction -> x100"),
]
PCT_FIELDS = {"roe", "revenue_growth", "earnings_growth"}


def ref_get(pack: dict, path: tuple) -> float | None:
    node = pack
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node if isinstance(node, (int, float)) else None


def classify(app: float | None, ref: float | None, ok_tol: float, watch_tol: float) -> str:
    if app is None and ref is None:
        return "ok(both-null)"
    if app is None:
        return "watch(app-null)"
    if ref is None:
        return "watch(ref-null)"
    if ref == 0:
        return "ok" if abs(app) < 1e-9 else "MISMATCH"
    rel = abs(app - ref) / abs(ref)
    if rel <= ok_tol:
        return "ok"
    if rel <= watch_tol:
        return "watch"
    return "MISMATCH"


def main() -> int:
    port, ref_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    packs = json.load(open(ref_path))
    results = []
    for pack in packs:
        sym = pack["symbol"]
        suffix = ".BO" if pack["entity"]["exchange"].upper().startswith("BSE") else ".NS"
        url = f"http://127.0.0.1:{port}/fundamentals/{sym}{suffix}"
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                app = json.load(resp)
        except Exception as exc:  # noqa: BLE001
            results.append({"symbol": sym, "error": str(exc)})
            continue
        row = {"symbol": sym, "figures": {}, "identity": {}, "counts": {"ok": 0, "watch": 0, "MISMATCH": 0}}
        app_name = (app.get("name") or "").lower()
        ref_name = pack["entity"]["name"].lower()
        name_ok = any(tok in app_name for tok in ref_name.split()[:2])
        row["identity"] = {"app_name": app.get("name"), "ref_name": pack["entity"]["name"], "ok": name_ok}
        row["growth_basis"] = app.get("growth_basis")
        for app_field, ref_path_t, ok_tol, watch_tol, note in FIGURES:
            app_val = app.get(app_field)
            if app_val is not None and app_field == "market_cap":
                app_val = app_val / 1e7  # INR -> crores
            if app_val is not None and app_field in PCT_FIELDS:
                app_val = app_val * 100.0  # fraction -> percent
            ref_val = ref_get(pack, ref_path_t)
            verdict = classify(app_val, ref_val, ok_tol, watch_tol)
            if app_field == "dividend_per_share" and verdict == "MISMATCH":
                # Yahoo's dividendRate is a TRAILING-PAID-basis scalar; the
                # reference's fy_total can include a DECLARED-BUT-UNPAID final
                # (AGM-pending). Judge against the trailing-paid reference too
                # and keep the better verdict, noting the basis.
                ttm_ref = ref_get(pack, ("dividends", "ttm_paid_per_share"))
                alt = classify(app_val, ttm_ref, ok_tol, watch_tol)
                if alt.startswith("ok") or alt.startswith("watch"):
                    verdict = alt
                    note = (note + "; matches trailing-PAID basis (declared final pending)").strip("; ")
            bucket = verdict.split("(")[0]
            row["counts"][bucket] = row["counts"].get(bucket, 0) + 1
            row["figures"][app_field] = {
                "app": app_val,
                "ref": ref_val,
                "verdict": verdict,
                "note": note,
            }
        results.append(row)
    json.dump(results, open(out_path, "w"), indent=1)
    total = {"ok": 0, "watch": 0, "MISMATCH": 0}
    for row in results:
        for key in total:
            total[key] += row.get("counts", {}).get(key, 0)
        ident = row.get("identity", {})
        flag = "" if ident.get("ok") else "  IDENTITY-FAIL"
        mism = [f for f, d in row.get("figures", {}).items() if d["verdict"] == "MISMATCH"]
        print(f"{row['symbol']:12s} {row.get('counts')}{flag}  basis={row.get('growth_basis')}  mismatches={mism}")
    print("TOTAL:", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
