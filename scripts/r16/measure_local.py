#!/usr/bin/env python3
"""Which on-computer model to recommend per RAM tier (R16): measure, don't guess.

  measure_local.py [MODEL_ID ...] [--k 1] [--probe-repeats 2] [--skip-probes]
                   [--only scenario,ids] [--scratch DIR] [--summary-only]

For each catalog model id (default: all of ``sidecar/services/local_models/catalog.json``):

  1. start an isolated sidecar from source (``sidecar_tap.py``, port 52300-52399, its
     own data dir, models dir = <data>/models) - reusing a verified model file when
     one is already there, otherwise downloading it through the sidecar's own
     ``POST /local-models/{id}/download`` and polling ``GET /local-models/downloads``;
  2. run llama-server from a temp dir holding the bundled binary and its dylibs
     (rpath is @loader_path) with the contract args, wait for /health, then
     ``PUT /local-models/engine``;
  3. run the 16-scenario agent-eval battery (``scripts/agent_eval``, lane ``local``)
     and the R15-LEAD-030 probes (``probes.json``, each twice), every trial graded
     for tool use AND for invented figures (``grounding.py`` against the tapped
     tool results), with wall time and generation tokens/s from llama-server's
     /metrics deltas;
  4. tear everything down and check nothing is left (pgrep, ports).

One ``<id>.json`` per model plus ``summary.md`` land in ``<scratch>/results``.
Run it detached (``nohup ... &``) and poll the log: one model takes a while.
Stdlib only; run with the sidecar venv's python (the grader reads the catalog).
"""

from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from argparse import Namespace
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(REPO / "scripts/agent_eval"), str(REPO / "sidecar")]

import run as agent_eval  # noqa: E402  (scripts/agent_eval/run.py)

MAIN_REPO = Path("/Users/lokavyasingh/Documents/dev/vysted-terminal")
DEFAULT_SCRATCH = Path(
    "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/"
    "9500707c-bdb2-4a31-adb3-975aa91d7edf/scratchpad/measure"
)
LLAMA_BIN = MAIN_REPO / "src-tauri/binaries/llama-server-aarch64-apple-darwin"
LLAMA_LIBS = MAIN_REPO / "src-tauri/llama-libs/aarch64-apple-darwin"
CATALOG = REPO / "sidecar/services/local_models/catalog.json"
PORTS = range(52300, 52400)
CTX = 8192
HEALTH_WAIT_S = 300

_children: list[subprocess.Popen] = []


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def http(method: str, port: int, path: str, body: dict | None = None, timeout: float = 30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - loopback
            raw = resp.read().decode("utf-8", "replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read().decode("utf-8", "replace"), exc.code
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, raw


def port_free(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def pick_port(rng: range) -> int:
    for p in rng:
        if port_free(p):
            return p
    raise RuntimeError(f"no free port in {rng.start}-{rng.stop - 1}")


def free_ephemeral() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pgrep(pattern: str) -> list[int]:
    out = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
    return [int(p) for p in out.stdout.split() if int(p) != os.getpid()]


def kill_tree(proc: subprocess.Popen, sig: int = signal.SIGTERM, wait: float = 10) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        return
    try:
        proc.wait(wait)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(10)


def _cleanup() -> None:
    for proc in _children:
        kill_tree(proc, wait=5)


atexit.register(_cleanup)
signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))


# --------------------------------------------------------------------------- sidecar


class Sidecar:
    def __init__(self, port: int, data_dir: Path, tap: Path, logfile: Path) -> None:
        self.port = port
        env = {**os.environ, "VYSTED_TAP_FILE": str(tap)}
        self.log = logfile.open("w")
        self.proc = subprocess.Popen(  # noqa: S603
            [sys.executable, str(HERE / "sidecar_tap.py"), "--host", "127.0.0.1",
             "--port", str(port), "--data-dir", str(data_dir)],
            stdin=subprocess.PIPE, stdout=self.log, stderr=subprocess.STDOUT,
            env=env, start_new_session=True,
        )  # fmt: skip
        _children.append(self.proc)

    def wait_ready(self, secs: float = 180) -> float:
        t0 = time.time()
        while time.time() - t0 < secs:
            if self.proc.poll() is not None:
                raise RuntimeError(f"sidecar exited early ({self.proc.returncode})")
            try:
                if http("GET", self.port, "/health", timeout=3)[0] == 200:
                    return time.time() - t0
            except OSError:
                pass
            time.sleep(1)
        raise RuntimeError("sidecar never answered /health")

    def stop(self) -> None:
        try:
            self.proc.stdin.close()  # the sidecar exits when its stdin closes
            self.proc.wait(8)
        except (subprocess.TimeoutExpired, OSError):
            pass
        kill_tree(self.proc)
        self.log.close()


# --------------------------------------------------------------------------- download


def ensure_model(port: int, model: dict, models_dir: Path) -> dict:
    """A verified file already in the models dir is reused; else download it through
    the sidecar (the real downloader, resume included) and poll to done."""
    target = models_dir / model["file"]
    if target.exists():
        if target.stat().st_size == model["sizeBytes"] and sha256_of(target) == model["sha256"]:
            log(f"download: reusing verified {target.name}")
            return {"reused": True, "secs": 0.0, "events": []}
        log(f"download: {target.name} fails size/sha256, removing")
        target.unlink()
    t0, events, last_log, starts = time.time(), [], 0.0, 0
    while True:
        status, body = http("POST", port, f"/local-models/{model['id']}/download")
        starts += 1
        events.append({"t": round(time.time() - t0, 1), "post": status, "body": body})
        if status != 200:
            return {"reused": False, "secs": time.time() - t0, "events": events, "error": body}
        while time.time() - t0 < 4 * 3600:
            _, dl = http("GET", port, "/local-models/downloads")
            mine = next((d for d in dl["downloads"] if d["id"] == model["id"]), None)
            if mine is None:
                time.sleep(2)
                continue
            if time.time() - last_log > 10 or mine["state"] in ("done", "failed", "paused"):
                last_log = time.time()
                pct = 100 * mine["receivedBytes"] / max(mine["totalBytes"], 1)
                rate = (mine["bytesPerSec"] or 0) / 1e6
                log(f"download: {mine['state']} {pct:5.1f}% {rate:.1f} MB/s {mine['error'] or ''}")
                events.append({"t": round(time.time() - t0, 1), **mine})
            if mine["state"] in ("done", "failed", "cancelled", "paused"):
                break
            time.sleep(3)
        if mine and mine["state"] == "done":
            return {"reused": False, "secs": time.time() - t0, "events": events, "posts": starts}
        if mine and mine["state"] == "paused" and mine["retryable"] and starts < 4:
            log("download: paused (retryable), resuming through POST again")
            continue
        return {"reused": False, "secs": time.time() - t0, "events": events, "error": mine}


# --------------------------------------------------------------------------- llama-server


class Engine:
    def __init__(self, model_path: Path, workdir: Path, errfile: Path, ctx: int) -> None:
        workdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LLAMA_BIN, workdir / "llama-server")
        for lib in LLAMA_LIBS.iterdir():
            shutil.copy2(lib, workdir / lib.name)
        self.workdir, self.port = workdir, free_ephemeral()
        self.args = ["--host", "127.0.0.1", "--port", str(self.port), "-m", str(model_path),
                     "--jinja", "-c", str(ctx), "-ngl", "999", "--no-webui"]  # fmt: skip
        self.cmd = [str(workdir / "llama-server"), *self.args, "--metrics"]
        self.errfile = errfile.open("w")
        # /usr/bin/time -l reports the child's peak RSS + footprint on exit.
        self.proc = subprocess.Popen(  # noqa: S603
            ["/usr/bin/time", "-l", *self.cmd], cwd=workdir, stdin=subprocess.DEVNULL,
            stdout=self.errfile, stderr=self.errfile, start_new_session=True,
        )  # fmt: skip
        _children.append(self.proc)
        self.errpath, self.peak_rss, self._stop = errfile, 0, threading.Event()
        self.pid: int | None = None
        threading.Thread(target=self._sample_rss, daemon=True).start()

    def _child_pid(self) -> int | None:
        out = subprocess.run(["pgrep", "-P", str(self.proc.pid)], capture_output=True, text=True)
        return int(out.stdout.split()[0]) if out.stdout.split() else None

    def _sample_rss(self) -> None:
        while not self._stop.wait(1.0):
            self.pid = self.pid or self._child_pid()
            if not self.pid:
                continue
            out = subprocess.run(["ps", "-o", "rss=", "-p", str(self.pid)], capture_output=True, text=True)
            if out.stdout.strip().isdigit():
                self.peak_rss = max(self.peak_rss, int(out.stdout) * 1024)

    def wait_ready(self) -> float:
        t0 = time.time()
        while time.time() - t0 < HEALTH_WAIT_S:
            if self.proc.poll() is not None:
                raise RuntimeError(f"llama-server exited ({self.proc.returncode}) before /health")
            try:
                if http("GET", self.port, "/health", timeout=3)[0] == 200:
                    return time.time() - t0
            except OSError:
                pass
            time.sleep(1)
        raise RuntimeError(f"llama-server not healthy after {HEALTH_WAIT_S}s")

    def stop(self) -> dict:
        self._stop.set()
        child = self._child_pid() or self.pid
        if child:
            try:
                os.kill(child, signal.SIGTERM)  # the child only: `time` then prints its rusage
            except ProcessLookupError:
                pass
        try:
            self.proc.wait(20)
        except subprocess.TimeoutExpired:
            kill_tree(self.proc, signal.SIGKILL)
        self.errfile.close()
        return self.time_stats()

    def time_stats(self) -> dict:
        text = self.errpath.read_text(errors="replace")
        stats = {}
        for key, label in (("max_rss_bytes", "maximum resident set size"),
                           ("peak_footprint_bytes", "peak memory footprint")):  # fmt: skip
            m = re.search(rf"^\s*(\d+)\s+{label}", text, re.M)
            if m:
                stats[key] = int(m.group(1))
        return stats

    def stderr_tail(self, n: int = 12) -> list[str]:
        lines = [x for x in self.errpath.read_text(errors="replace").splitlines() if x.strip()]
        return lines[-n:]

    def stderr_grep(self, pattern: str) -> list[str]:
        return [x for x in self.errpath.read_text(errors="replace").splitlines() if re.search(pattern, x)][:6]


def metrics(port: int) -> dict[str, float] | None:
    try:
        raw = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=10).read().decode()  # noqa: S310
    except OSError:
        return None
    return {k: float(v) for k, v in re.findall(r"^(llamacpp:\w+)\s+(\S+)$", raw, re.M)}


# --------------------------------------------------------------------------- trials


def timed_trial(ns: Namespace, scenario: dict, model_id: str, trial: int, llama_port: int, kind: str) -> dict:
    before = metrics(llama_port)
    try:
        row = agent_eval.run_trial(ns, scenario, "local", model_id, trial)
    except Exception as exc:  # noqa: BLE001 - a dead sidecar must not end the other trials' record
        row = {"scenario": scenario["id"], "trial": trial, "pass": False, "failures": [f"harness: {exc!r}"],
               "secs": 0.0, "tool_calls": [], "ungrounded": None, "answer": ""}  # fmt: skip
    after = metrics(llama_port)
    row["kind"] = kind
    if before and after:
        d = {k: after.get(k, 0) - before.get(k, 0) for k in after}
        gt, gs = d.get("llamacpp:tokens_predicted_total", 0), d.get("llamacpp:tokens_predicted_seconds_total", 0)
        pt, ps = d.get("llamacpp:prompt_tokens_total", 0), d.get("llamacpp:prompt_seconds_total", 0)
        row.update(gen_tokens=int(gt), gen_secs=round(gs, 2), gen_tok_s=round(gt / gs, 2) if gs else None,
                   prompt_tokens=int(pt), prompt_secs=round(ps, 2), prompt_tok_s=round(pt / ps, 2) if ps else None)  # fmt: skip
    base = [f for f in row["failures"] if not f.startswith("ungrounded figures")]
    row["pass_base"] = not base
    if kind == "probe":
        hard = ("error event", "stream ended", "empty answer", "vy exit", "harness")
        row["clean"] = not row["ungrounded"] and not any(f.startswith(hard) for f in row["failures"])
    else:
        row["clean"] = row["pass_base"] and not row["ungrounded"]
    verdict = "clean" if row["clean"] else "NOT clean"
    log(f"{kind} {scenario['id']} #{trial}: {verdict} {row['secs']}s tools={[c['name'] for c in row['tool_calls']]} "
        f"ungrounded={row['ungrounded']} tok/s={row.get('gen_tok_s')} {'; '.join(base)[:160]}")  # fmt: skip
    return row


def aggregate(trials: list[dict]) -> dict:
    sc = [t for t in trials if t["kind"] == "scenario"]
    pr = [t for t in trials if t["kind"] == "probe"]
    gen_t = sum(t.get("gen_tokens") or 0 for t in trials)
    gen_s = sum(t.get("gen_secs") or 0 for t in trials)
    pt = sum(t.get("prompt_tokens") or 0 for t in trials)
    ps = sum(t.get("prompt_secs") or 0 for t in trials)
    fails = [f for t in trials for f in t["failures"]]
    figs = [x for t in trials for x in t["ungrounded"] or []]
    return {
        "scenario_trials": len(sc),
        "scenario_pass_base": sum(t["pass_base"] for t in sc),
        "scenario_clean": sum(t["clean"] for t in sc),
        "probe_trials": len(pr),
        "probe_clean": sum(t["clean"] for t in pr),
        "trials_with_invented_figures": sum(bool(t["ungrounded"]) for t in trials),
        "invented_figures_total": len(figs),
        "tool_calls_total": sum(len(t["tool_calls"]) for t in trials),
        "malformed_tool_calls": sum(("invalid args" in f or "without required" in f) for f in fails),
        "leaked_call_syntax": sum(f.startswith("answer matches forbidden") for f in fails),
        "missing_expected_tool": sum(bool(re.match(r"no \S+ call with input", f)) for f in fails),
        "gen_tokens": gen_t,
        "gen_tok_s": round(gen_t / gen_s, 2) if gen_s else None,
        "prompt_tok_s": round(pt / ps, 2) if ps else None,
        "mean_trial_secs": round(statistics.mean(t["secs"] for t in trials), 1) if trials else None,
        "median_trial_secs": round(statistics.median(t["secs"] for t in trials), 1) if trials else None,
        "clean_rate": round(sum(t["clean"] for t in trials) / len(trials), 3) if trials else None,
    }


def measure(model: dict, args, scratch: Path) -> dict:
    results = scratch / "results"
    out = results / model["id"]
    out.mkdir(parents=True, exist_ok=True)
    data_dir = scratch / "data"
    models_dir = data_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    tap = out / "tool-tap.jsonl"
    tap.write_text("")
    rec: dict = {"model": {k: v for k, v in model.items() if k != "licence"}, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
                 "findings": [], "trials": []}  # fmt: skip
    t_start = time.time()
    side = eng = None
    try:
        port = pick_port(PORTS)
        log(f"== {model['id']}: sidecar on :{port}, data dir {data_dir}")
        side = Sidecar(port, data_dir, tap, out / "sidecar.log")
        rec["sidecar_boot_secs"] = round(side.wait_ready(), 1)
        rec["hardware"] = http("GET", port, "/local-models/hardware")[1]
        cat = http("GET", port, "/local-models/catalog")[1]
        rec["catalog_view"] = {"tier": cat.get("tier"), "recommendedId": cat.get("recommendedId"),
                               "fits": next((m.get("fits") for m in cat["models"] if m["id"] == model["id"]), None)}  # fmt: skip
        rec["download"] = ensure_model(port, model, models_dir)
        path = models_dir / model["file"]
        if not path.exists() or sha256_of(path) != model["sha256"]:
            rec["findings"].append(f"model file missing or failing sha256 after download: {rec['download'].get('error')}")
            return rec
        inst = http("GET", port, "/local-models/installed")[1]
        rec["installed_view"] = next((m for m in inst["models"] if m["id"] == model["id"]), None)

        eng = Engine(path, scratch / "engine" / model["id"], out / "llama-server.stderr.log", args.ctx)
        rec["engine"] = {"cmd": eng.cmd}
        try:
            rec["engine"]["load_secs"] = round(eng.wait_ready(), 1)
        except RuntimeError as exc:
            rec["engine"]["stderr_tail"] = eng.stderr_tail(20)
            rec["findings"].append(f"engine failed to load: {exc}; last stderr: {eng.stderr_tail(1)}")
            log(f"FINDING: {rec['findings'][-1]}")
            return rec
        rec["engine"]["ctx_lines"] = eng.stderr_grep(r"n_ctx|n_slots|kv_unified|tool|chat template|jinja")
        status, body = http("PUT", port, "/local-models/engine", {"port": eng.port, "modelId": model["id"]})
        rec["engine"]["put_engine"] = [status, body]
        if status != 200:
            rec["findings"].append(f"PUT /local-models/engine returned {status}: {body}")
            return rec
        log(f"engine ready on :{eng.port} in {rec['engine']['load_secs']}s")

        ns = Namespace(lane="local", port=port, out_dir=str(out), tap=str(tap))
        scenarios = json.loads((REPO / "scripts/agent_eval/scenarios.json").read_text())
        if args.only:
            scenarios = [s for s in scenarios if s["id"] in set(args.only.split(","))]
        probes = [] if args.skip_probes else json.loads((HERE / "probes.json").read_text())
        for scenario in scenarios:
            for trial in range(args.k):
                rec["trials"].append(timed_trial(ns, scenario, model["id"], trial, eng.port, "scenario"))
                _save(rec, results, model["id"])
        for probe in probes:
            for trial in range(args.probe_repeats):
                rec["trials"].append(timed_trial(ns, probe, model["id"], trial, eng.port, "probe"))
                _save(rec, results, model["id"])
        rec["aggregate"] = aggregate(rec["trials"])
        if rec["aggregate"]["tool_calls_total"] == 0:
            rec["findings"].append("no tool call was ever made across all trials")
        if not any(t.get("gen_tok_s") for t in rec["trials"]):
            rec["findings"].append("no generation timings recorded from llama-server /metrics")
        return rec
    finally:
        if eng:
            rec.setdefault("engine", {}).update(eng.stop())
            rec["engine"]["peak_rss_polled_bytes"] = eng.peak_rss
            rec["engine"]["stderr_tail"] = rec["engine"].get("stderr_tail") or eng.stderr_tail()
        if side:
            side.stop()
        time.sleep(1)
        orphans = pgrep(str(scratch / "engine" / model["id"])) + pgrep("sidecar_tap.py")
        rec["teardown"] = {
            "orphans": orphans,
            "sidecar_port_free": port_free(port) if side else None,
            "engine_port_free": port_free(eng.port) if eng else None,
        }
        log(f"teardown: {rec['teardown']}")
        rec["run_secs"] = round(time.time() - t_start, 1)
        rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _save(rec, results, model["id"])


def _save(rec: dict, results: Path, model_id: str) -> None:
    if rec["trials"] and "aggregate" not in rec:
        rec["aggregate_partial"] = aggregate(rec["trials"])
    (results / f"{model_id}.json").write_text(json.dumps(rec, indent=2, default=str) + "\n")


# --------------------------------------------------------------------------- summary


def write_summary(results: Path) -> Path:
    recs = [json.loads(p.read_text()) for p in sorted(results.glob("*.json"))]
    recs = [r for r in recs if "model" in r]
    scored = [r for r in recs if r.get("aggregate")]
    scored.sort(key=lambda r: (-(r["aggregate"]["clean_rate"] or 0), -(r["aggregate"]["gen_tok_s"] or 0)))
    gb = lambda b: f"{b / 1e9:.2f}" if b else "n/a"  # noqa: E731
    lines = [
        "# On-computer model measurement (R16)",
        "",
        "Ranked by clean-trial rate first (correct tool use AND no invented figure), generation speed second.",
        "A battery trial is clean when the existing grader passes and no answer figure is missing from an ok tool result.",
        "A probe trial is clean when the stream is error-free with a non-empty answer and no figure is invented.",
        "",
        "| rank | model | file GB | battery pass (grader) | battery clean | probes clean | trials with invented figs | invented figs | tool calls (malformed) | gen tok/s | prompt tok/s | mean trial s | peak RSS GB (rusage / polled) | load s |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(scored, 1):
        a, e = r["aggregate"], r.get("engine", {})
        lines.append(
            f"| {i} | {r['model']['id']} | {r['model']['sizeBytes'] / 1e9:.2f} | {a['scenario_pass_base']}/{a['scenario_trials']} "
            f"| {a['scenario_clean']}/{a['scenario_trials']} | {a['probe_clean']}/{a['probe_trials']} "
            f"| {a['trials_with_invented_figures']} | {a['invented_figures_total']} "
            f"| {a['tool_calls_total']} ({a['malformed_tool_calls']}) | {a['gen_tok_s']} | {a['prompt_tok_s']} "
            f"| {a['mean_trial_secs']} | {gb(e.get('max_rss_bytes'))} / {gb(e.get('peak_rss_polled_bytes'))} | {e.get('load_secs')} |"
        )
    for r in recs:
        if not r.get("aggregate"):
            lines.append(f"| - | {r['model']['id']} | {r['model']['sizeBytes'] / 1e9:.2f} | not measured | | | | | | | | | | |")
    ids = [r["model"]["id"] for r in scored]
    if scored:
        sids = []
        for r in scored:
            for t in r["trials"]:
                if t["scenario"] not in sids:
                    sids.append(t["scenario"])
        lines += ["", "## Per scenario (clean trials / trials; INV = an invented figure appeared)", "",
                  "| scenario | " + " | ".join(ids) + " |", "|---|" + "---|" * len(ids)]  # fmt: skip
        for sid in sids:
            cells = []
            for r in scored:
                ts = [t for t in r["trials"] if t["scenario"] == sid]
                inv = " INV" if any(t["ungrounded"] for t in ts) else ""
                cells.append(f"{sum(t['clean'] for t in ts)}/{len(ts)}{inv}" if ts else "-")
            lines.append(f"| {sid} | " + " | ".join(cells) + " |")
    notes = [(r["model"]["id"], f) for r in recs for f in r.get("findings", [])]
    for r in recs:
        td = r.get("teardown") or {}
        if td.get("orphans"):
            notes.append((r["model"]["id"], f"orphan processes after teardown: {td['orphans']}"))
    if notes:
        lines += ["", "## Findings", ""] + [f"- {m}: {f}" for m, f in notes]
    path = results / "summary.md"
    path.write_text("\n".join(lines) + "\n")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(prog="measure_local")
    ap.add_argument("models", nargs="*", help="catalog ids (default: all)")
    ap.add_argument("--k", type=int, default=1, help="trials per battery scenario")
    ap.add_argument("--probe-repeats", type=int, default=2)
    ap.add_argument("--skip-probes", action="store_true")
    ap.add_argument("--only", help="comma-separated battery scenario ids")
    ap.add_argument("--ctx", type=int, default=CTX)
    ap.add_argument("--scratch", default=str(DEFAULT_SCRATCH))
    ap.add_argument("--summary-only", action="store_true")
    args = ap.parse_args()
    scratch = Path(args.scratch)
    (scratch / "results").mkdir(parents=True, exist_ok=True)
    if args.summary_only:
        print(write_summary(scratch / "results"))
        return 0
    catalog = {m["id"]: m for m in json.loads(CATALOG.read_text())["models"]}
    ids = args.models or list(catalog)
    unknown = [i for i in ids if i not in catalog]
    if unknown:
        ap.error(f"not in the catalog: {unknown}")
    for model_id in ids:
        measure(catalog[model_id], args, scratch)
        log(f"summary: {write_summary(scratch / 'results')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
