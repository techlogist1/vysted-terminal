#!/usr/bin/env python3
"""route_fuzz — walk /openapi.json on a Vysted sidecar and fuzz every read route.

Stdlib only. Sends, per route: a valid call, missing required params, wrong types,
unknown entity ids, huge limits, negative numbers, unicode, injection strings.
Records status / elapsed / content-type / body prefix for every request and flags
500s, >10 s responses, non-JSON error bodies, stack traces and sibling inconsistency.

    python3 scripts/r15/route_fuzz.py --port 52242 --out <dir>
    python3 scripts/r15/route_fuzz.py --port 52242 --out <dir> --graduated   # unbounded-input probes

NEVER calls order / kill-switch / docker-setup / ollama-pull / teardown / any write route:
the deny list below is a hard gate, plus only GET and an explicit pure-read POST allow list
are ever dispatched.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TIMEOUT = 30.0
SLOW_S = 10.0

# Hard gate: substrings that must never be requested (side effects / safety boundary).
DENY = (
    "/orders",
    "/confirm",
    "/cancel",
    "/kill-switch",
    "/searxng/setup",
    "/searxng/teardown",
    "/ollama/pull",
    "/provider-health/trip",
    "/provider-health/reset",
    "/connect",
    "/disconnect",
    "/mode",
    "/read-only",
    "/disclaimer-ack",
    "/session",
    "/resume",
    "/answer",
)

# POST routes judged pure reads (compute or validate only; no persistence, no upstream write).
POST_READS = {
    "/screener/formula/validate",
    "/backtest/strategies/custom/validate",
    "/quant/option/price",
    "/quant/option/greeks",
    "/quant/bond/price",
    "/quant/yield-curve",
    "/screener/run",
}

# Fresh symbols: none appear in r15/stage0/BATTERY_EXCLUSIONS.txt.
SYM = "TRENT"
VALID = {
    "symbol": SYM,
    "symbols": f"{SYM},CAMS",
    "q": "Trent",
    "limit": "10",
    "days": "7",
    "timeframe": "1d",
    "range": "1y",
    "asset_class": "equity",
    "indicators": "sma,rsi",
    "exchange": "NSE",
    "series_id": "GDP",
    "provider": "fred",
    "cik": "0000320193",
    "identifier": "ORCL",
    "accession": "0000320193-23-000106",
    "form_type": "10-K",
    "form": "4",
    "id": "nifty50",
    "configured": "1.2.3.4",
    "watchlist": f"{SYM},CAMS",
    "agent_id": "copilot",
    "name": "__autosave__",
    "start_ms": "0",
    "end_ms": "9999999999999",
    "region": "IN",
    "base_url": "",
    "model": "",
    "plugin_id": "example",
    "broker_id": "paper",
    "run_id": "nonexistent-run",
    "workflow_id": "nonexistent-workflow",
    "position_id": "1",
}
PATH_VALID = {
    "/crypto/ticker": {"exchange": "binance", "symbol": "SOL/USDT"},
    "/crypto/history": {"exchange": "binance", "symbol": "SOL/USDT", "timeframe": "1d"},
    "/llm/models": {"provider": "ollama"},
    "/macro/catalog": {"provider": "fred"},
    "/macro/search": {"provider": "fred", "q": "gdp"},
    "/sec/filings": {"symbol": "ORCL"},
    "/sec/filings/search": {"q": "Oracle"},
    "/sec/insider/{identifier}": {"identifier": "ORCL"},
}

# Params that name an entity (symbol, id, free-text query) — the string mutations target these.
ENTITY = (
    "symbol",
    "symbols",
    "q",
    "identifier",
    "cik",
    "series_id",
    "accession",
    "run_id",
    "agent_id",
    "plugin_id",
    "broker_id",
    "workflow_id",
    "id",
    "name",
    "watchlist",
)
STR_MUT = [
    ("unknown", "ZZQQXXNOTREAL9"),
    ("blank", "   "),
    ("empty", ""),
    ("special", "$$$"),
    ("long300", "A" * 300),
    ("sqli", "'; DROP TABLE quotes;--"),
    ("html", "<script>alert(1)</script>"),
    ("unicode", "\U0001f9e8日本語Ωπ"),
    ("double_suffix", f"{SYM}.NS.NS"),
]
NUM_MUT = [
    ("huge", "999999999"),
    ("negative", "-1"),
    ("zero", "0"),
    ("wrongtype", "abc"),
    ("float", "1.5"),
]
NUMERIC = ("limit", "days", "start_ms", "end_ms", "position_id")

TRACE_MARKERS = ('Traceback (most recent call last)', 'File "/', "  File ")

TODAY = time.strftime("%Y-%m-%d")
NEXT_YR = time.strftime("%Y-%m-%d", time.localtime(time.time() + 365 * 86400))


def _opt(body: dict) -> dict:
    base = {
        "exercise": "european",
        "payoff": "call",
        "spot": 100.0,
        "strike": 100.0,
        "risk_free_rate": 0.05,
        "dividend_yield": 0.0,
        "volatility": 0.2,
        "valuation_date": TODAY,
        "expiry_date": NEXT_YR,
        "method": "black-scholes",
    }
    base.update(body)
    return base


def _bond(body: dict) -> dict:
    base = {
        "face_value": 1000.0,
        "coupon_rate": 0.07,
        "coupons_per_year": 2,
        "issue_date": "2020-01-01",
        "maturity_date": "2030-01-01",
        "settlement_date": TODAY,
        "yield_to_maturity": 0.06,
    }
    base.update(body)
    return base


def _screen(body: dict) -> dict:
    base = {
        "universe": "nifty50",
        "criteria": [{"field": "pe_ratio", "operator": "lt", "value": 20}],
        "limit": 10,
    }
    base.update(body)
    return base


POST_BODIES: dict[str, list[tuple[str, object]]] = {
    "/screener/formula/validate": [
        ("valid", {"formula": "pe_ratio < 20 and roe > 15"}),
        ("missing_required", {}),
        ("wrongtype", {"formula": 12345}),
        ("empty", {"formula": ""}),
        ("blank", {"formula": "   "}),
        ("unicode", {"formula": "\U0001f9e8 日本語 > 1"}),
        ("sqli", {"formula": "'; DROP TABLE quotes;--"}),
        ("long", {"formula": "pe_ratio < 20 and " * 500 + "roe > 1"}),
        ("unknown_field", {"formula": "zzz_not_a_field > 1"}),
        ("div_zero", {"formula": "pe_ratio / 0 > 1"}),
        ("deep_nest", {"formula": "(" * 200 + "pe_ratio > 1" + ")" * 200}),
        ("extra_field", {"formula": "roe > 1", "unexpected": 1}),
    ],
    "/backtest/strategies/custom/validate": [
        ("valid", {"entry": "close > sma(close, 20)", "exit": "close < sma(close, 20)"}),
        ("missing_required", {}),
        ("wrongtype", {"entry": 5, "exit": []}),
        ("blank", {"entry": "   ", "exit": "   "}),
        ("unicode", {"entry": "日本語 > 1", "exit": ""}),
        ("negative_size", {"entry": "close > 1", "exit": "close < 1", "positionSize": -100}),
        ("huge_size", {"entry": "close > 1", "exit": "close < 1", "positionSize": 1e308}),
        ("deep_nest", {"entry": "(" * 200 + "close > 1" + ")" * 200, "exit": ""}),
    ],
    "/quant/option/price": [
        ("valid", _opt({})),
        ("missing_required", {"payoff": "call"}),
        ("wrongtype", _opt({"spot": "abc"})),
        ("negative_spot", _opt({"spot": -100.0})),
        ("zero_vol", _opt({"volatility": 0.0})),
        ("negative_vol", _opt({"volatility": -0.2})),
        ("zero_strike", _opt({"strike": 0.0})),
        ("expiry_before_valuation", _opt({"expiry_date": "2000-01-01"})),
        ("expiry_equals_valuation", _opt({"expiry_date": TODAY})),
        ("huge_spot", _opt({"spot": 1e308})),
        ("bad_enum", _opt({"method": "quantum"})),
        ("bad_date", _opt({"valuation_date": "not-a-date"})),
        ("unicode_enum", _opt({"payoff": "\U0001f9e8"})),
        ("negative_steps", _opt({"method": "binomial", "binomial_steps": -5})),
        ("zero_steps", _opt({"method": "binomial", "binomial_steps": 0})),
        ("negative_paths", _opt({"method": "monte-carlo", "monte_carlo_paths": -5})),
    ],
    "/quant/option/greeks": [
        ("valid", {k: v for k, v in _opt({}).items() if k not in ("exercise", "method")}),
        ("missing_required", {"payoff": "put"}),
        ("zero_vol", {k: v for k, v in _opt({"volatility": 0.0}).items() if k not in ("exercise", "method")}),
        ("negative_spot", {k: v for k, v in _opt({"spot": -1.0}).items() if k not in ("exercise", "method")}),
        ("expiry_before_valuation", {k: v for k, v in _opt({"expiry_date": "2000-01-01"}).items() if k not in ("exercise", "method")}),
    ],
    "/quant/bond/price": [
        ("valid", _bond({})),
        ("missing_required", {"coupon_rate": 0.07}),
        ("wrongtype", _bond({"coupon_rate": "abc"})),
        ("negative_ytm", _bond({"yield_to_maturity": -0.05})),
        ("zero_ytm", _bond({"yield_to_maturity": 0.0})),
        ("maturity_before_settlement", _bond({"maturity_date": "2000-01-01"})),
        ("bad_frequency", _bond({"coupons_per_year": 3})),
        ("huge_face", _bond({"face_value": 1e308})),
        ("negative_face", _bond({"face_value": -1000.0})),
    ],
    "/quant/yield-curve": [
        (
            "valid",
            {
                "valuation_date": TODAY,
                "instruments": [
                    {"type": "deposit", "tenor": 3, "tenor_unit": "months", "rate": 0.06},
                    {"type": "swap", "tenor": 2, "tenor_unit": "years", "rate": 0.065},
                ],
                "sample_count": 10,
            },
        ),
        ("missing_required", {"valuation_date": TODAY}),
        ("empty_instruments", {"valuation_date": TODAY, "instruments": [], "sample_count": 10}),
        (
            "zero_samples",
            {
                "valuation_date": TODAY,
                "instruments": [{"type": "deposit", "tenor": 3, "tenor_unit": "months", "rate": 0.06}],
                "sample_count": 0,
            },
        ),
        (
            "negative_samples",
            {
                "valuation_date": TODAY,
                "instruments": [{"type": "deposit", "tenor": 3, "tenor_unit": "months", "rate": 0.06}],
                "sample_count": -5,
            },
        ),
        (
            "negative_tenor",
            {
                "valuation_date": TODAY,
                "instruments": [{"type": "deposit", "tenor": -3, "tenor_unit": "months", "rate": 0.06}],
                "sample_count": 10,
            },
        ),
        (
            "bad_enum",
            {
                "valuation_date": TODAY,
                "instruments": [{"type": "futures", "tenor": 3, "tenor_unit": "months", "rate": 0.06}],
                "sample_count": 10,
            },
        ),
    ],
    "/screener/run": [
        ("valid", _screen({})),
        ("missing_required", {"limit": 5}),
        ("bad_universe", _screen({"universe": "not-a-universe"})),
        ("custom_no_symbols", _screen({"universe": "custom", "custom_symbols": []})),
        ("custom_unknown_symbols", _screen({"universe": "custom", "custom_symbols": ["ZZQQXXNOTREAL9"]})),
        ("custom_unicode_symbols", _screen({"universe": "custom", "custom_symbols": ["\U0001f9e8日本"]})),
        ("empty_criteria", _screen({"criteria": []})),
        ("limit_over_max", _screen({"limit": 1001})),
        ("limit_zero", _screen({"limit": 0})),
        ("limit_negative", _screen({"limit": -1})),
        ("bad_field", _screen({"criteria": [{"field": "zzz", "operator": "lt", "value": 1}]})),
        ("bad_operator", _screen({"criteria": [{"field": "pe_ratio", "operator": "===", "value": 1}]})),
        ("wrongtype_value", _screen({"criteria": [{"field": "pe_ratio", "operator": "lt", "value": "abc"}]})),
        ("nan_value", _screen({"criteria": [{"field": "pe_ratio", "operator": "lt", "value": 1e308}]})),
        ("formula_injection", _screen({"formula": "__import__('os').system('true')"})),
    ],
}


def request(method: str, url: str, body: object | None) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read(20000)
            return _record(t0, r.status, r.headers.get("Content-Type", ""), raw)
    except urllib.error.HTTPError as e:
        raw = e.read(20000)
        return _record(t0, e.code, e.headers.get("Content-Type", ""), raw)
    except Exception as e:  # timeout / connection reset / malformed response
        return {
            "status": 0,
            "elapsed": round(time.monotonic() - t0, 2),
            "ctype": "",
            "json_ok": False,
            "body": f"{type(e).__name__}: {e}"[:400],
            "trace": False,
        }


def _record(t0: float, status: int, ctype: str, raw: bytes) -> dict:
    text = raw.decode("utf-8", "replace")
    try:
        json.loads(text)
        json_ok = True
    except ValueError:
        json_ok = False
    return {
        "status": status,
        "elapsed": round(time.monotonic() - t0, 2),
        "ctype": ctype,
        "json_ok": json_ok,
        "body": text[:400],
        "trace": any(m in text for m in TRACE_MARKERS),
    }


def cases_for(path: str, op: dict) -> list[dict]:
    """Build the fuzz cases for one GET operation."""
    params = op.get("parameters", [])
    over = PATH_VALID.get(path, {})
    qp = [p for p in params if p["in"] == "query"]
    pp = [p for p in params if p["in"] == "path"]

    def val(p):
        n = p["name"]
        return over.get(n, VALID.get(n, "test"))

    def build(qmut=None, drop_required=False, pmut=None):
        q = {}
        for p in qp:
            n = p["name"]
            if qmut and n == qmut[0]:
                q[n] = qmut[1]
                continue
            if drop_required and p.get("required"):
                continue
            if p.get("required") or n in over:
                q[n] = val(p)
        url = path
        for p in pp:
            n = p["name"]
            v = pmut[1] if pmut and n == pmut[0] else val(p)
            url = url.replace("{%s}" % n, urllib.parse.quote(str(v), safe=""))
        if q:
            url += "?" + urllib.parse.urlencode(q)
        return url

    out = [{"case": "valid", "url": build(), "param": None}]
    # string mutations on the first entity-ish param (path param wins — it is the identity)
    ent_p = next((p["name"] for p in pp if p["name"] in ENTITY), None)
    ent_q = None if ent_p else next((p["name"] for p in qp if p["name"] in ENTITY), None)
    target = ent_p or ent_q
    if target:
        for label, v in STR_MUT:
            url = build(pmut=(target, v)) if ent_p else build(qmut=(target, v))
            out.append({"case": f"str:{label}", "url": url, "param": target})
    num = next((p["name"] for p in qp if p["name"] in NUMERIC), None)
    if num:
        for label, v in NUM_MUT:
            out.append({"case": f"num:{label}", "url": build(qmut=(num, v)), "param": num})
    if any(p.get("required") for p in qp):
        out.append({"case": "missing_required", "url": build(drop_required=True), "param": None})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--graduated", action="store_true", help="only the unbounded-input probes")
    args = ap.parse_args()
    base = f"http://127.0.0.1:{args.port}"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.graduated:
        graduated(base, out)
        return

    spec = json.loads(request("GET", base + "/openapi.json", None)["body"] or "{}")
    if not spec:
        with urllib.request.urlopen(base + "/openapi.json", timeout=TIMEOUT) as r:
            spec = json.loads(r.read())

    jobs = []
    skipped = []
    for path, ops in sorted(spec["paths"].items()):
        if any(d in path for d in DENY):
            skipped.append((path, "deny"))
            continue
        if "get" in ops:
            for c in cases_for(path, ops["get"]):
                jobs.append({"path": path, "method": "GET", "body": None, **c})
        for m in ("post", "put", "delete", "patch"):
            if m not in ops:
                continue
            if m != "post" or path not in POST_READS:
                skipped.append((f"{m.upper()} {path}", "write-or-side-effect"))
                continue
            for label, body in POST_BODIES.get(path, []):
                jobs.append(
                    {"path": path, "method": "POST", "body": body, "case": label, "url": path, "param": None}
                )

    print(f"{len(jobs)} requests over {len({j['path'] for j in jobs})} routes; {len(skipped)} ops skipped")
    results = []
    lines = out / "results.jsonl"
    with lines.open("w") as fh, ThreadPoolExecutor(args.workers) as pool:
        for job, res in zip(jobs, pool.map(lambda j: request(j["method"], base + j["url"], j["body"]), jobs)):
            row = {**job, **res}
            row.pop("body_sent", None)
            if job["body"] is not None:
                row["body"] = json.dumps(job["body"])[:200]
                row["resp"] = res["body"]
            else:
                row["resp"] = res["body"]
            row.pop("body", None) if job["body"] is None else None
            fh.write(json.dumps(row, default=str) + "\n")
            results.append(row)
    (out / "skipped.json").write_text(json.dumps(skipped, indent=2))
    report(results, out)


def report(results: list[dict], out: Path) -> None:
    flags = {
        "http_500": [r for r in results if r["status"] >= 500],
        "transport_fail": [r for r in results if r["status"] == 0],
        "slow": [r for r in results if r["elapsed"] > SLOW_S],
        "non_json_error": [r for r in results if r["status"] >= 400 and not r["json_ok"]],
        "stack_trace": [r for r in results if r["trace"]],
    }
    # sibling consistency: what each route does with an unknown entity id
    unknown = {}
    for r in results:
        if r["case"] == "str:unknown":
            unknown.setdefault(r["status"], []).append(f"{r['method']} {r['path']}")
    blank = {}
    for r in results:
        if r["case"] == "str:blank":
            blank.setdefault(r["status"], []).append(f"{r['method']} {r['path']}")
    summary = {
        "total": len(results),
        "by_status": {},
        "flags": {k: len(v) for k, v in flags.items()},
        "unknown_entity_by_status": {str(k): sorted(v) for k, v in sorted(unknown.items())},
        "blank_entity_by_status": {str(k): sorted(v) for k, v in sorted(blank.items())},
    }
    for r in results:
        summary["by_status"][str(r["status"])] = summary["by_status"].get(str(r["status"]), 0) + 1
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    (out / "flags.json").write_text(json.dumps(flags, indent=2, default=str))
    print(json.dumps(summary["by_status"], indent=2))
    print(json.dumps(summary["flags"], indent=2))


def graduated(base: str, out: Path) -> None:
    """Unbounded numeric inputs, escalated one step at a time and stopped at the first
    response over SLOW_S — proves the ceiling without wedging the sidecar."""
    probes = []
    for steps in (1000, 5000, 20000, 100000):
        body = _opt({"method": "binomial", "binomial_steps": steps})
        r = request("POST", base + "/quant/option/price", body)
        probes.append({"probe": "binomial_steps", "n": steps, **r})
        print("binomial_steps", steps, r["status"], r["elapsed"])
        if r["elapsed"] > SLOW_S or r["status"] != 200:
            break
    for paths in (10000, 200000, 2000000):
        body = _opt({"method": "monte-carlo", "monte_carlo_paths": paths, "monte_carlo_seed": 7})
        r = request("POST", base + "/quant/option/price", body)
        probes.append({"probe": "monte_carlo_paths", "n": paths, **r})
        print("monte_carlo_paths", paths, r["status"], r["elapsed"])
        if r["elapsed"] > SLOW_S or r["status"] != 200:
            break
    for n in (100, 10000, 1000000):
        body = {
            "valuation_date": TODAY,
            "instruments": [{"type": "deposit", "tenor": 3, "tenor_unit": "months", "rate": 0.06}],
            "sample_count": n,
        }
        r = request("POST", base + "/quant/yield-curve", body)
        probes.append({"probe": "sample_count", "n": n, **r})
        print("sample_count", n, r["status"], r["elapsed"], len(r["body"]))
        if r["elapsed"] > SLOW_S or r["status"] != 200:
            break
    (out / "graduated.json").write_text(json.dumps(probes, indent=2))


if __name__ == "__main__":
    main()
