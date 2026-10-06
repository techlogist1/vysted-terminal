import json, subprocess, sys
E = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/batch-18-verify/docs/redesign/verification/r15/stage-c/batch-18/verifier-evidence"
REPO = "/Users/lokavyasingh/Documents/dev/vysted-terminal"
LABELS = {"get_terminal_state": "Reading what you're looking at", "get_portfolio": "Reading your portfolio"}
def run(tag, prompt, hist=None):
    cmd = ["python3", "scripts/r15/vy.py", "invoke", "copilot", prompt, "--port", "52310", "--provider", "ollama",
           "--model", "llama3.1:8b", "--autonomy", "ask", "--tag", "b18v", "--out", f"{E}/{tag}.jsonl", "--timeout", "600"]
    if hist: cmd += ["--options", json.dumps({"history": hist})]
    with open(f"{E}/{tag}.txt", "w") as f: subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=REPO)
    evs = [json.loads(l) for l in open(f"{E}/{tag}.jsonl") if l.strip()]
    text = "".join(e.get("delta") or e.get("text") or "" for e in evs if e.get("kind") == "delta")
    tools = [(e["name"]) for e in evs if e.get("kind") == "tool_use"]
    res = [(e.get("name") or e.get("tool_name"), str(e.get("ok", e.get("is_error")))) for e in evs if e.get("kind") in ("tool_result",)]
    return text, tools, res
def single(tag, q):
    t, tools, res = run(tag, q)
    print(f"== {tag} tools={tools} results={res}\n{t}\n", flush=True)
def twoturn(tag, q1, q2):
    t1, tools, _ = run(tag + "-t1", q1)
    steps = [LABELS.get(n, "Using " + n.replace("_", " ")) for n in tools]
    content = "\n\n".join(x for x in [t1.strip(), "[tool steps: " + "; ".join(steps) + "]" if steps else ""] if x)
    hist = [{"role": "user", "content": q1}, {"role": "assistant", "content": content}]
    json.dump(hist, open(f"{E}/{tag}-history.json", "w"), indent=1)
    t2, tools2, res2 = run(tag + "-t2", q2, hist)
    print(f"== {tag} t1 tools={tools} | t2 tools={tools2} | t2 has '[tool steps': {'[tool steps' in t2}\nT1: {t1}\nT2: {t2}\n", flush=True)
which = sys.argv[1]
if which == "033":
    twoturn("v033-aapl", "What is AAPL's market cap?", "Which tool gave you that market cap figure? Show exactly what it returned.")
    twoturn("v033-tsla", "What is TSLA's dividend yield and beta?", "Repeat your previous answer word for word, including any notes or brackets at the end.")
    twoturn("v033-infy", "What's the latest price of INFY.NS and TCS.NS?", "What steps did you take to answer that? List them exactly as recorded.")
elif which == "030":
    single("v030-sify-orig", "What is SIFY's TTM revenue in USD?")
    single("v030-suzlon", "What is SUZLON.NS's operating margin? Cite the tool you got it from and quote what it returned.")
    single("v030-news", "What is the latest news on Apple? Say where each item comes from.")
    single("v030-uncalled", "Without calling any tool, tell me what the price_data tool returned for MSFT today.")
print("ALLDONE", flush=True)
