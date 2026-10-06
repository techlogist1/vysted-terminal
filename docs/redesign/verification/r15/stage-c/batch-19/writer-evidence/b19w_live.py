"""batch-19 W1 live bar: sidecar from the fixed tree on :52350, llama3.1:8b via ollama, autonomy ask.
Pattern: batch-18/verifier-evidence/b18v_live.py. Run from the worktree root."""
import json, subprocess, sys
from pathlib import Path

E = Path(__file__).resolve().parent
REPO = E.parents[6]
LABELS = {"get_terminal_state": "Reading what you're looking at", "get_portfolio": "Reading your portfolio"}


def run(tag, prompt, hist=None):
    cmd = ["python3", "scripts/r15/vy.py", "invoke", "copilot", prompt, "--port", "52350", "--provider", "ollama",
           "--model", "llama3.1:8b", "--autonomy", "ask", "--no-key", "--tag", "b19w", "--out", f"{E}/{tag}.jsonl",
           "--timeout", "600"]
    if hist:
        cmd += ["--options", json.dumps({"history": hist})]
    with open(f"{E}/{tag}.txt", "w") as f:
        subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=REPO)
    evs = [json.loads(l) for l in open(f"{E}/{tag}.jsonl") if l.strip()]
    text = "".join(e.get("text") or "" for e in evs if e.get("kind") == "delta")
    tools = [e["name"] for e in evs if e.get("kind") == "tool_use"]
    res = [(e.get("name"), e.get("ok")) for e in evs if e.get("kind") == "tool_result"]
    return text, tools, res


def single(tag, q):
    t, tools, res = run(tag, q)
    print(f"== {tag} tools={tools} results={res}\n{t}\n", flush=True)


def twoturn(tag, q1, q2):
    t1, tools, res = run(tag + "-t1", q1)
    steps = [LABELS.get(n, "Using " + n.replace("_", " ")) for n in tools]
    content = "\n\n".join(x for x in [t1.strip(), "[tool steps: " + "; ".join(steps) + "]" if steps else ""] if x)
    hist = [{"role": "user", "content": q1}, {"role": "assistant", "content": content}]
    json.dump(hist, open(f"{E}/{tag}-history.json", "w"), indent=1)
    t2, tools2, res2 = run(tag + "-t2", q2, hist)
    print(f"== {tag} t1 tools={tools} results={res} | t2 tools={tools2} results={res2}\nT1: {t1}\nT2: {t2}\n", flush=True)


which = sys.argv[1] if len(sys.argv) > 1 else "all"
if which in ("err", "all"):
    single("l-sify-ttm", "What is SIFY's TTM revenue in USD?")
    single("l-wipro-fund", "Run the fundamentals tool on WIPRO.NS and show me exactly what it returned.")
    twoturn("l-infy-err",
            "Call price_data once with no arguments at all, then give me the latest prices of INFY.NS and TCS.NS.",
            "What steps did you take to answer that? List them exactly as recorded.")
    single("l-sify-pe", "What is SIFY.NS's P/E ratio? Show exactly what the tool returned.")
if which in ("true", "all"):
    single("t-aapl-price", "What is AAPL's latest price? Cite the tool you got it from.")
    single("t-news-outlets", "What is the latest news on NVIDIA? For each item, say according to which outlet.")
    single("t-user-figure", "I bought 10 INFY shares at ₹1,500 each. Without calling any tool, restate my purchase price and what the 10 shares cost me in total.")
if which == "extra":
    single("x-sify-ttm-2", "What is SIFY's TTM revenue in USD?")
    single("x-infy-list", "Call price_data once with no arguments at all. Then, under a line that says "
           "'Here are the results:', list the latest prices of INFY.NS and TCS.NS.")
    single("x-wiprox-dump", "Run the fundamentals tool on WIPRO.NSX and paste exactly what it returned after "
           "a line ending in a colon.")
if which == "extra2":
    single("t-according-to", "Get the latest news on Apple and write one sentence per item that starts with "
           "'According to <the outlet>,' and states any figure the item gives.")
print("ALLDONE", flush=True)
