#!/usr/bin/env python3
"""Agent-eval runner: the fixed scenario set, k trials per scenario, pass^k per lane.

  run.py --lane ollama|openrouter-free|openai --k 3 --port 52390 --out-dir DIR
         [--model SLUG] [--only id,id] [--max-minutes 18]

Every trial is driven through ``scripts/r15/vy.py invoke`` (key-safe, spend-
ledgered, budget-guarded; its port guard allows R15 isolated sidecars only) under
ASK autonomy, and graded by ``grader.grade`` over the recorded event stream plus
the scenario's end-state probe. Results append to ``DIR/<lane>.jsonl``, so a
re-run resumes: trials already recorded for that lane + model are not repeated.
The summary goes to ``DIR/<lane>.report.json``. Stdlib only; exit 3 = vy budget.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
VY = REPO / "scripts/r15/vy.py"
sys.path[:0] = [str(HERE), str(REPO / "sidecar")]

import grader  # noqa: E402

#: lane -> (vy provider, default model)
LANES = {
    "ollama": ("ollama", "llama3.1:8b"),
    "openrouter-free": ("openrouter", "qwen/qwen3.8-27b:free"),
    "openai": ("openai", "gpt-4o-mini"),
}
TRIAL_TIMEOUT_S = 600


def _probe(port: int, path: str) -> object:
    url = f"http://127.0.0.1:{port}{path}"
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 - loopback only
        return json.loads(resp.read())


def _read_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text().splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    return events


def run_trial(args, scenario: dict, provider: str, model: str, trial: int) -> dict | None:
    """One graded trial; ``None`` when vy refused on budget (stop the run)."""
    events_path = Path(args.out_dir) / args.lane / f"{scenario['id']}.{trial}.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    probe = scenario.get("state_probe")
    before = _probe(args.port, probe) if probe else None
    cmd = [
        sys.executable, str(VY), "invoke", scenario.get("agent", "copilot"), scenario["prompt"],
        "--provider", provider, "--model", model, "--mode", scenario.get("mode", "agent"),
        "--autonomy", "ask", "--region", scenario.get("region", "IN"),
        "--tag", f"agent-eval:{args.lane}:{scenario['id']}", "--out", str(events_path),
        "--port", str(args.port), "--timeout", str(TRIAL_TIMEOUT_S), "--quiet",
    ]  # fmt: skip
    started = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TRIAL_TIMEOUT_S + 30)
        code, tail = proc.returncode, (proc.stdout + proc.stderr)[-300:]
    except subprocess.TimeoutExpired:
        code, tail = -1, "trial timed out"
    if code == 3 or "BUDGET" in tail:
        print(f"vy budget guard refused: {tail.strip()}", file=sys.stderr)
        return None
    after = _probe(args.port, probe) if probe else None
    failures = grader.grade(scenario, _read_events(events_path), before, after)
    if code != 0:
        failures.insert(0, f"vy exit {code}: {tail.strip()[-160:]}")
    return {
        "lane": args.lane,
        "model": model,
        "scenario": scenario["id"],
        "trial": trial,
        "pass": not failures,
        "failures": failures,
        "secs": round(time.time() - started, 1),
        "events": str(events_path),
    }


def main() -> int:
    ap = argparse.ArgumentParser(prog="agent_eval")
    ap.add_argument("--lane", required=True, choices=sorted(LANES))
    ap.add_argument("--model")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--only", help="comma-separated scenario ids")
    ap.add_argument("--max-minutes", type=float, help="start no trial after this long")
    args = ap.parse_args()
    provider, default_model = LANES[args.lane]
    model = args.model or default_model
    scenarios = json.loads((HERE / "scenarios.json").read_text())
    if args.only:
        wanted = set(args.only.split(","))
        scenarios = [s for s in scenarios if s["id"] in wanted]
    results_path = Path(args.out_dir) / f"{args.lane}.jsonl"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    if results_path.exists():
        rows = [json.loads(line) for line in results_path.read_text().splitlines() if line]
    rows = [r for r in rows if r["model"] == model]
    started = time.time()
    budget_hit = False
    for scenario in scenarios:
        done = sum(1 for r in rows if r["scenario"] == scenario["id"])
        for trial in range(done, args.k):
            if args.max_minutes and time.time() - started > args.max_minutes * 60:
                break
            row = run_trial(args, scenario, provider, model, trial)
            if row is None:
                budget_hit = True
                break
            rows.append(row)
            with results_path.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            verdict = "PASS" if row["pass"] else "FAIL " + "; ".join(row["failures"])[:200]
            print(f"{scenario['id']} #{trial} {row['secs']}s {verdict}", flush=True)
        if budget_hit:
            break
    outcomes: dict[str, list[bool]] = {}
    for r in rows:
        outcomes.setdefault(r["scenario"], []).append(r["pass"])
    report = {"lane": args.lane, "model": model, **grader.pass_hat_k(outcomes, args.k)}
    report_path = Path(args.out_dir) / f"{args.lane}.report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "per_scenario"}))
    return 3 if budget_hit else 0


if __name__ == "__main__":
    sys.exit(main())
