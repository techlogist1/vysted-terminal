#!/usr/bin/env python3
"""vy — key-safe headless client for a Vysted sidecar (R15 census + scenario drives).

Reads the BYOK key from the dev keystore IN-PROCESS and never prints it; logs every
LLM-backed call to a spend ledger and refuses once the run budget is reached.

  vy.py get /health [--port 52152]
  vy.py post /screener/run '{"json": "body"}' [--port 52152]
  vy.py invoke copilot "prompt" --provider openrouter [--model SLUG] [--mode agent]
        [--autonomy ask] [--tier tier_a] [--tag who-is-calling] [--out events.jsonl]
        [--options '{"json": 1}'] [--bad-key] [--no-key]

Stdlib only. Exit codes: 0 ok, 2 usage, 3 budget reached, 4 transport/HTTP error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEDGER = REPO / "docs/redesign/verification/r15/spend-ledger.jsonl"
KEYSTORE = (
    Path.home() / "Library/Application Support/com.vysted.terminal/dev-keystore.json"
)

FREE_DEFAULT = "inclusionai/ling-3.0-flash-vl:free"
#: Hard stops (R15 budget: $2.00 run total, OpenRouter paid lane unfunded).
FREE_CALLS_PER_DAY = 700
PAID_USD_CAP = 1.80
#: $/M tokens (input, output) for the OpenAI-direct lane; unknown models are priced high
#: on purpose so an unpriced model can only under-spend the cap.
PRICES = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-5-nano": (0.05, 0.40),
    "gpt-5.6-luna": (0.20, 1.20),
}
UNKNOWN_PRICE = (3.0, 12.0)


def _is_free(provider: str, model: str) -> bool:
    return provider == "openrouter" and (
        model.endswith(":free") or model == "openrouter/free"
    )


def _ledger_rows() -> list[dict]:
    if not LEDGER.exists():
        return []
    rows = []
    for line in LEDGER.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def _budget_check(provider: str, model: str) -> None:
    rows = _ledger_rows()
    today = time.strftime("%Y-%m-%d")
    if _is_free(provider, model):
        used = sum(1 for r in rows if r.get("free") and r.get("day") == today)
        if used >= FREE_CALLS_PER_DAY:
            sys.exit(
                f"vy: BUDGET — free-lane invokes today {used} >= {FREE_CALLS_PER_DAY}"
            )
        return
    if provider == "openrouter":
        sys.exit(
            "vy: BUDGET — OpenRouter paid lane is unfunded; use a :free slug or --provider openai"
        )
    spent = sum(float(r.get("est_usd") or 0) for r in rows if not r.get("free"))
    if spent >= PAID_USD_CAP:
        print(
            f"vy: BUDGET — paid spend ${spent:.4f} >= ${PAID_USD_CAP}", file=sys.stderr
        )
        sys.exit(3)


def _key(provider: str) -> str | None:
    try:
        return json.loads(KEYSTORE.read_text())["secrets"].get(
            f"llm-provider:{provider}"
        )
    except (OSError, ValueError, KeyError):
        return None


def _http(method: str, url: str, body: bytes | None, headers: dict, timeout: float):
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310 — loopback only


def cmd_plain(args) -> int:
    url = f"http://127.0.0.1:{args.port}{args.path}"
    body = args.body.encode() if getattr(args, "body", None) else None
    headers = {"Content-Type": "application/json"} if body else {}
    for kv in args.header or []:
        k, _, v = kv.partition("=")
        headers[k] = v
    try:
        with _http(args.method, url, body, headers, args.timeout) as resp:
            sys.stdout.write(f"HTTP {resp.status}\n")
            sys.stdout.write(
                resp.read().decode("utf-8", "replace")[: args.max_bytes] + "\n"
            )
            return 0
    except urllib.error.HTTPError as exc:
        sys.stdout.write(
            f"HTTP {exc.code}\n{exc.read().decode('utf-8', 'replace')[: args.max_bytes]}\n"
        )
        return 4
    except OSError as exc:
        sys.stdout.write(f"TRANSPORT {type(exc).__name__}: {exc}\n")
        return 4


def cmd_invoke(args) -> int:
    model = args.model or (
        FREE_DEFAULT if args.provider == "openrouter" else "gpt-4o-mini"
    )
    _budget_check(args.provider, model)
    key = (
        None
        if args.no_key
        else ("sk-invalid-r15-induced-401" if args.bad_key else _key(args.provider))
    )
    if key is None and not args.no_key:
        sys.exit(f"vy: no key for provider {args.provider!r} in the dev keystore")
    payload = {
        "prompt": args.prompt,
        "provider": args.provider,
        "model": model,
        "mode": args.mode,
    }
    if key:
        payload["api_key"] = key
    if args.autonomy:
        payload["autonomy"] = args.autonomy
    if args.options:
        payload["options"] = json.loads(args.options)
    if args.context:
        payload["context_snapshot"] = json.loads(Path(args.context).read_text())
    headers = {
        "Content-Type": "application/json",
        "X-Vysted-Region": args.region,
        "X-Vysted-Research-Tier": args.tier,
    }
    for kv in args.header or []:
        k, _, v = kv.partition("=")
        headers[k] = v
    url = f"http://127.0.0.1:{args.port}/agents/{args.agent}/invoke"
    started = time.time()
    text: list[str] = []
    thinking: list[str] = []
    usage: dict = {}
    kinds: dict[str, int] = {}
    status = "ok"
    out = open(args.out, "w") if args.out else None  # noqa: SIM115

    def scrub(s: str) -> str:
        return s.replace(key, "<KEY>") if key and len(key) > 8 else s

    try:
        with _http(
            "POST", url, json.dumps(payload).encode(), headers, args.timeout
        ) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                line = scrub(line[5:].strip())
                if out:
                    out.write(line + "\n")
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                kind = str(ev.get("kind") or ev.get("type") or "?")
                kinds[kind] = kinds.get(kind, 0) + 1
                if isinstance(ev.get("usage"), dict):
                    usage = ev["usage"]
                piece = ev.get("delta") or ev.get("content") or ev.get("text")
                if kind in ("delta", "text", "content", "token") and isinstance(
                    piece, str
                ):
                    text.append(piece)
                    continue
                if kind == "thinking":
                    thinking.append(str(piece or ""))
                    continue
                if not args.quiet:
                    print(
                        f"[{time.time() - started:6.1f}s] {kind}: {json.dumps(ev)[: args.max_event]}"
                    )
    except urllib.error.HTTPError as exc:
        status = f"http_{exc.code}"
        print(f"HTTP {exc.code}: {scrub(exc.read().decode('utf-8', 'replace')[:1500])}")
    except OSError as exc:
        status = f"transport_{type(exc).__name__}"
        print(f"TRANSPORT {type(exc).__name__}: {exc}")
    finally:
        if out:
            out.close()
    elapsed = time.time() - started
    tin = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
    tout = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
    free = _is_free(args.provider, model)
    pin, pout = PRICES.get(model, UNKNOWN_PRICE)
    est = (
        0.0 if free or args.bad_key or args.no_key else (tin * pin + tout * pout) / 1e6
    )
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as fh:
        fh.write(
            json.dumps(
                {
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "day": time.strftime("%Y-%m-%d"),
                    "tag": args.tag,
                    "port": args.port,
                    "agent": args.agent,
                    "provider": args.provider,
                    "model": model,
                    "free": free,
                    "prompt_sha": hashlib.sha256(args.prompt.encode()).hexdigest()[:12],
                    "status": status,
                    "secs": round(elapsed, 1),
                    "in": tin,
                    "out": tout,
                    "est_usd": round(est, 6),
                }
            )
            + "\n"
        )
    if thinking:
        print(
            "\n=== THINKING (streamed as kind=thinking) ===\n"
            + "".join(thinking)[-1500:]
        )
    print("\n=== ASSISTANT TEXT ===\n" + "".join(text))
    print(
        f"\n=== {status} · {elapsed:.1f}s · events {kinds} · usage in={tin} out={tout} · est ${est:.5f} · {model}"
    )
    return 0 if status == "ok" else 4


def main() -> int:
    ap = argparse.ArgumentParser(prog="vy")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, method in (("get", "GET"), ("post", "POST"), ("delete", "DELETE")):
        p = sub.add_parser(name)
        p.add_argument("path")
        if method != "GET":
            p.add_argument("body", nargs="?")
        p.set_defaults(fn=cmd_plain, method=method)
    inv = sub.add_parser("invoke")
    inv.add_argument("agent")
    inv.add_argument("prompt")
    inv.add_argument(
        "--provider",
        required=True,
        choices=["openrouter", "openai", "deepseek", "ollama"],
    )
    inv.add_argument("--model")
    inv.add_argument(
        "--mode", default="agent", choices=["agent", "ask", "edit", "build", "delegate"]
    )
    inv.add_argument("--autonomy", choices=["ask", "auto"])
    inv.add_argument("--tier", default="tier_a")
    inv.add_argument("--region", default="IN")
    inv.add_argument("--options")
    inv.add_argument("--context", help="path to a context_snapshot JSON file")
    inv.add_argument("--tag", default=os.environ.get("VY_TAG", "untagged"))
    inv.add_argument(
        "--out", help="write every raw SSE event (key-scrubbed) to this JSONL file"
    )
    inv.add_argument(
        "--bad-key", action="store_true", help="induce a 401 with a fake key"
    )
    inv.add_argument("--no-key", action="store_true", help="send no key at all")
    inv.add_argument("--quiet", action="store_true")
    inv.add_argument("--max-event", type=int, default=400)
    inv.set_defaults(fn=cmd_invoke)
    for p in sub.choices.values():
        p.add_argument("--port", type=int, default=52152)
        p.add_argument("--timeout", type=float, default=900)
        p.add_argument("--header", action="append")
        p.add_argument("--max-bytes", type=int, default=20000)
    args = ap.parse_args()
    if args.port == 5173 or args.cmd != "get" and args.port not in range(52100, 52400):
        sys.exit(
            "vy: refusing — non-GET calls are only allowed against R15 isolated sidecars (ports 52100-52399)"
        )
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
