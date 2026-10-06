"""batch-20 writer live bar: sidecar from the writer tree on :52350, llama3.1:8b via ollama, autonomy ask.
Transcripts land beside this file as <tag>.jsonl (events) + <tag>.txt (client log). Run with cwd=<tree>."""
import json, subprocess, sys
from pathlib import Path
E = Path(__file__).resolve().parent
TREE = E.parents[6]
PY = "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/.venv/bin/python"
def run(tag, prompt, options=None):
    cmd = [PY, "scripts/r15/vy.py", "invoke", "copilot", prompt, "--port", "52350", "--provider", "ollama",
           "--model", "llama3.1:8b", "--autonomy", "ask", "--no-key", "--tag", "b20w", "--out", f"{E}/{tag}.jsonl", "--timeout", "600"]
    if options: cmd += ["--options", json.dumps(options)]
    with open(f"{E}/{tag}.txt", "w") as f: subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=TREE)
    evs = [json.loads(l) for l in open(f"{E}/{tag}.jsonl") if l.strip()]
    text = "".join(e.get("text") or "" for e in evs if e.get("kind") == "delta")
    tools = [e["name"] for e in evs if e.get("kind") == "tool_use"]
    res = [(e.get("name"), e.get("ok")) for e in evs if e.get("kind") == "tool_result"]
    return text, tools, res
def single(tag, q, options=None):
    t, tools, res = run(tag, q, options)
    print(f"== {tag} tools={tools} results={res}\n{t}\n", flush=True)
INFY_HISTORY = [
    {"role": "user", "content": "What is INFY.NS's latest price?"},
    {"role": "assistant", "content": "INFY.NS is at ₹1,000.20.\n\n[tool steps: Using price data]"},
]
which = sys.argv[1] if len(sys.argv) > 1 else "all"
if which in ("err", "all"):
    single("v-sify-ttm", "What is SIFY's TTM revenue in USD?")
    single("f-sify-q", "What was SIFY's revenue last quarter in USD? Quote exactly what the tool returned.")
    single("f-wipro-fund", "Look up the fundamentals for WIPRO.NSE and paste the tool's raw output below a line ending with a colon.")
    single("f-infy-tcs-t2", "Call price_data once with no arguments at all. Then, under a line ending in a colon, list the latest prices of INFY.NS and TCS.NS as bullets.", {"history": INFY_HISTORY})
    single("f-err-table", "Call price_data once with no arguments at all. Then, under a line ending in a colon, give the latest prices of SBIN.NS and AXISBANK.NS as a markdown table.")
    single("f-err-fenced", "Call price_data once with no arguments at all. Then paste the tool's raw output inside a ```json fenced block.")
if which in ("true", "all"):
    single("t-msft-price", "What is MSFT's latest price? Cite the tool you got it from.")
    single("t-rel-list", "Get the latest prices of RELIANCE.NS and SBIN.NS and list them as bullets under a line ending in a colon.")
    single("t-user-sale", "I sold 5 TCS shares at ₹3,100 each. Without calling any tool, restate my sale price and my total proceeds.")
    single("t-tcs-fund", "Get TCS.NS fundamentals and give me its market cap in lakh crore rupees, rounded to one decimal.")
if which == "pass2":  # reruns on the sidecar restarted after a8070bba + the pending-dump fix
    single("f-infy-tcs-t2-p2", "Call price_data once with no arguments at all. Then, under a line ending in a colon, list the latest prices of INFY.NS and TCS.NS as bullets.", {"history": INFY_HISTORY})
    single("f-err-fenced-p2", "Call price_data once with no arguments at all. Then paste the tool's raw output inside a ```json fenced block.")
print("ALLDONE", flush=True)
