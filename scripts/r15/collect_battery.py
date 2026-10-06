#!/usr/bin/env python3
"""R15 battery collector — what the app SAYS about every hostile-battery name.

Re-runnable regression battery. Drives the sidecar exactly the way the
EquityOverview panel does (src/modules/equity-overview/api.ts:101 fans out to
quote + the five fundamentals routes; src/lib/sidecar-client.ts:263 holds the
paths) plus the resolve forms a user actually types and the India disclosure
feeds, and writes one JSON per name to battery/collected/<slot>_<SYMBOL>.json.

Polite by construction: >= --gap seconds between upstream-hitting calls, and it
parks while the Yahoo circuit breaker at /system/provider-health is open
(services/provider_health.py:140 — "open" means inside a cooldown window).

  python3 scripts/r15/collect_battery.py --port 52152
  python3 scripts/r15/collect_battery.py --port 52152 --only P9,P13 --force
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATTERY = ROOT / "docs/redesign/verification/r15/battery"
OUT_DIR = BATTERY / "collected"


def call(
    base: str, path: str, params: dict | None = None, timeout: float = 90.0
) -> dict:
    """One GET, recorded the way a defect reviewer needs it: status, latency, body."""
    url = base + path + (("?" + urllib.parse.urlencode(params)) if params else "")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        status = exc.code
    except Exception as exc:  # transport: timeout, connection refused
        return {
            "url": url,
            "status": None,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "transport_error": f"{type(exc).__name__}: {exc}",
        }
    rec = {
        "url": url,
        "status": status,
        "elapsed_ms": round((time.monotonic() - started) * 1000),
    }
    try:
        rec["body"] = json.loads(raw)
    except json.JSONDecodeError:
        rec["body_text"] = raw[:4000]
        rec["non_json_body"] = True
    return rec


def breaker(base: str) -> dict:
    rec = call(base, "/system/provider-health", timeout=10.0)
    body = rec.get("body")
    return body.get("yahoo", {}) if isinstance(body, dict) else {}


def wait_polite(base: str, gap: float, last: list[float], max_park: float) -> dict:
    """Space calls by `gap`, then park (bounded) while the Yahoo circuit is open."""
    delta = time.monotonic() - last[0]
    if delta < gap:
        time.sleep(gap - delta)
    health = breaker(base)
    parked = 0.0
    while health.get("open") and parked < max_park:
        nap = min(float(health.get("cooldown_remaining") or 5.0) + 1.0, 30.0)
        time.sleep(nap)
        parked += nap
        health = breaker(base)
    last[0] = time.monotonic()
    return {"yahoo_open": bool(health.get("open")), "parked_s": round(parked, 1)}


def collect_one(
    base: str, entry: dict, gap: float, max_park: float, last: list[float]
) -> dict:
    sym = entry["symbol"]
    plan: list[tuple[str, str, dict | None]] = [
        # resolve, the three forms a user types
        ("resolve_bare_symbol", "/resolve", {"q": sym}),
        ("resolve_company_name", "/resolve", {"q": entry["name"]}),
    ]
    if entry.get("bse_code"):
        plan.append(("resolve_bse_code", "/resolve", {"q": entry["bse_code"]}))
    plan += [
        # EquityOverview panel fan-out (api.ts:101)
        ("quote", f"/quotes/{urllib.parse.quote(sym)}", {"asset_class": "equity"}),
        ("fundamentals", f"/fundamentals/{urllib.parse.quote(sym)}", None),
        ("income", f"/fundamentals/{urllib.parse.quote(sym)}/income", None),
        ("balance", f"/fundamentals/{urllib.parse.quote(sym)}/balance", None),
        ("cashflow", f"/fundamentals/{urllib.parse.quote(sym)}/cashflow", None),
        ("ratings", f"/fundamentals/{urllib.parse.quote(sym)}/ratings", None),
        # India disclosure feeds (shareholding / announcements / results calendar)
        ("shareholding", "/disclosures/shareholding", {"symbol": sym}),
        ("announcements", "/disclosures/announcements", {"symbol": sym, "limit": 25}),
        ("results_calendar", "/disclosures/results", {"symbol": sym}),
    ]

    calls: dict[str, dict] = {}
    for key, path, params in plan:
        polite = wait_polite(base, gap, last, max_park)
        rec = call(base, path, params)
        rec["polite"] = polite
        calls[key] = rec
        status = rec.get("status")
        print(f"    {key:22s} {status} {rec['elapsed_ms']:>6}ms", flush=True)
    return {
        "slot": entry["slot"],
        "symbol": sym,
        "manifest_name": entry["name"],
        "exchange": entry["exchange"],
        "bse_code": entry.get("bse_code"),
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "sidecar": base,
        "complete": True,
        "calls": calls,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=52152)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--gap", type=float, default=2.0, help="min seconds between calls")
    ap.add_argument(
        "--max-park", type=float, default=120.0, help="max s to wait on the breaker"
    )
    ap.add_argument("--only", default="", help="comma-separated slots, e.g. P1,P9")
    ap.add_argument(
        "--force", action="store_true", help="re-collect names already on disk"
    )
    args = ap.parse_args()

    base = f"http://{args.host}:{args.port}"
    names = json.loads((BATTERY / "manifest.json").read_text())["names"]
    wanted = {s.strip() for s in args.only.split(",") if s.strip()}
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    last = [0.0]
    for entry in names:
        if wanted and entry["slot"] not in wanted:
            continue
        out = OUT_DIR / f"{entry['slot']}_{entry['symbol']}.json"
        if out.exists() and not args.force:
            try:
                if json.loads(out.read_text()).get("complete"):
                    print(f"[skip] {out.name}", flush=True)
                    continue
            except json.JSONDecodeError:
                pass  # half-written by a killed run — redo it
        print(f"[collect] {entry['slot']} {entry['symbol']}", flush=True)
        out.write_text(
            json.dumps(
                collect_one(base, entry, args.gap, args.max_park, last), indent=1
            )
            + "\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
