"""batch-23 W1 live bar (R15-LEAD-035): source sidecar from the writer tree on :52350, llama3.1:8b via ollama,
autonomy ask. Transcripts land in live/ beside this file as <tag>.jsonl (events) + <tag>.txt (client log).
Run with cwd=<tree>; optional args pick tags."""
import json, os, subprocess, sys
from pathlib import Path
E = Path(__file__).resolve().parent / "live"
TREE = Path(__file__).resolve().parents[7]
PY = "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/.venv/bin/python"
VY = [PY, "scripts/r15/vy.py"]
def get(path):
    r = subprocess.run(VY + ["get", path, "--port", "52350"], capture_output=True, text=True, cwd=TREE)
    return r.stdout.strip()[:400]
def run(tag, prompt, history=None):
    tag += os.environ.get("B23_RUN", "")  # B23_RUN=-r2 keeps a re-run beside run 1
    E.mkdir(exist_ok=True)
    cmd = VY + ["invoke", "copilot", prompt, "--port", "52350", "--provider", "ollama", "--model", "llama3.1:8b",
                "--autonomy", "ask", "--no-key", "--tag", "b23w", "--out", f"{E}/{tag}.jsonl", "--timeout", "600"]
    if history: cmd += ["--options", json.dumps({"history": history})]
    with open(f"{E}/{tag}.txt", "w") as f: subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=TREE)
    evs = [json.loads(l) for l in open(f"{E}/{tag}.jsonl") if l.strip()]
    text = "".join(e.get("text") or "" for e in evs if e.get("kind") == "delta")
    calls = [(e["name"], e.get("input")) for e in evs if e.get("kind") == "tool_use"]
    res = [(e.get("name"), e.get("ok"), str(e.get("error") or "")[:100]) for e in evs if e.get("kind") == "tool_result"]
    other = sorted({e.get("kind") for e in evs} - {"delta", "tool_use", "tool_result"})
    print(f"== {tag}\nprompt={prompt!r}\nhistory_turns={len(history or [])}\ncalls={calls}\nresults={res}\n"
          f"kinds={other}\npositions_after={get('/portfolio/positions')}\n---\n{text}\n", flush=True)
    return text
P = [
 ("k-dont-forget", "Don't forget to use the tools to get the latest TCS.NS price."),
 ("k-do-not-answer-without", "Do not answer without using the tools: what is TCS.NS trading at?"),
 ("k-why-not-q", "Why did you not use the tools? Get the TCS.NS price now."),
 ("k-just-from-market", "Just get the latest price from the market for the stocks in this message: TCS.NS, INFY.NS"),
 ("k-only-price-data", "Only use data from price_data for the above symbols: TCS.NS"),
 ("n-dont-use-add-infy", "Don't use any tools, add 7 INFY to my holdings"),
 ("c-add-tcs", "Add 10 TCS at 3,200 to my portfolio"),
 ("x-named-exclusion", "Don't use web search, get TCS.NS price"),
]
only = sys.argv[1:]
print(f"quotes TCS.NS={get('/quotes/TCS.NS')}\nquotes INFY.NS={get('/quotes/INFY.NS')}\n"
      f"positions_before={get('/portfolio/positions')}\n", flush=True)
for tag, q in P:
    if not only or tag in only: run(tag, q)
if not only or "k-why-not-bare" in only:
    t1 = "What is TCS.NS trading at?"
    a1 = run("k-why-not-bare-t1", t1)
    run("k-why-not-bare", "Why did you not use the tools",
        [{"role": "user", "content": t1}, {"role": "assistant", "content": a1}])
print("ALLDONE", flush=True)
