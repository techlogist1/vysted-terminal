"""Disposition-concurrence live runs on :52310 (worktree @014bb7f1), llama3.1:8b/ollama, agent mode, autonomy ask.
Usage: dv_live.py <SET> <runs> [tags...]; raw events to live/<tag>.r<n>.jsonl."""
import json, os, subprocess, sys
S = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad"
TREE = f"{S}/disp-verify"; HERE = os.path.dirname(os.path.abspath(__file__)); E = f"{HERE}/live"
sys.path.insert(0, HERE); import dv_prompts
PY = "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/.venv/bin/python"
VY = [PY, "scripts/r15/vy.py"]
def get(path):
    return subprocess.run(VY + ["get", path, "--port", "52310"], capture_output=True, text=True, cwd=TREE).stdout.strip()
def run(tag, prompt):
    cmd = VY + ["invoke", "copilot", prompt, "--port", "52310", "--provider", "ollama", "--model", "llama3.1:8b",
                "--mode", "agent", "--autonomy", "ask", "--no-key", "--tag", "dispv", "--out", f"{E}/{tag}.jsonl", "--timeout", "600"]
    with open(f"{E}/{tag}.txt", "w") as f: subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=TREE)
    evs = [json.loads(l) for l in open(f"{E}/{tag}.jsonl") if l.strip()]
    text = "".join(e.get("text") or "" for e in evs if e.get("kind") == "delta")
    calls = [(e["name"], e.get("input")) for e in evs if e.get("kind") == "tool_use"]
    res = [(e.get("name"), e.get("ok"), str(e.get("error") or "")[:120]) for e in evs if e.get("kind") == "tool_result"]
    other = sorted({e.get("kind") for e in evs} - {"delta", "tool_use", "tool_result", "heartbeat"})
    staged = [c[0] for c in calls if c[0].startswith("portfolio_") or c[0] in ("add_to_watchlist",)]
    print(f"== {tag}\nprompt={prompt!r}\ncalls={calls}\nresults={res}\nkinds={other}\nstaged_host_writes={staged}\npositions={get('/portfolio/positions')[:300]}\n---\n{text}\n", flush=True)
set_, runs, only = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
print(f"positions_before={get('/portfolio/positions')}\n", flush=True)
for r in range(1, runs + 1):
    for tag, q in getattr(dv_prompts, set_):
        if not only or tag in only: run(f"{tag}.r{r}", q)
print("ALLDONE", flush=True)
