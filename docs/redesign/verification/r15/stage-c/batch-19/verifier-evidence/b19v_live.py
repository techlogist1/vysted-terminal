"""batch-19 verifier live bar: sidecar from the verify tree on :52310, llama3.1:8b via ollama, autonomy ask."""
import json, subprocess, sys
from pathlib import Path
E = Path(__file__).resolve().parent
REPO = "/Users/lokavyasingh/Documents/dev/vysted-terminal"
def run(tag, prompt):
    cmd = ["python3", "scripts/r15/vy.py", "invoke", "copilot", prompt, "--port", "52310", "--provider", "ollama",
           "--model", "llama3.1:8b", "--autonomy", "ask", "--no-key", "--tag", "b19v", "--out", f"{E}/{tag}.jsonl", "--timeout", "600"]
    with open(f"{E}/{tag}.txt", "w") as f: subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=REPO)
    evs = [json.loads(l) for l in open(f"{E}/{tag}.jsonl") if l.strip()]
    text = "".join(e.get("text") or "" for e in evs if e.get("kind") == "delta")
    tools = [e["name"] for e in evs if e.get("kind") == "tool_use"]
    res = [(e.get("name"), e.get("ok")) for e in evs if e.get("kind") == "tool_result"]
    return text, tools, res
def single(tag, q):
    t, tools, res = run(tag, q)
    print(f"== {tag} tools={tools} results={res}\n{t}\n", flush=True)
which = sys.argv[1] if len(sys.argv) > 1 else "all"
if which in ("err", "all"):
    single("v-sify-ttm", "What is SIFY's TTM revenue in USD?")
    single("f-sify-q", "What was SIFY's revenue last quarter in USD? Quote exactly what the tool returned.")
    single("f-bharti-raw", "Look up the fundamentals for BHARTIARTL.NSE and paste the tool's raw output below a line ending with a colon.")
    single("f-err-list", "Call price_data once with no arguments at all. Then, under a line ending in a colon, list the latest prices of HDFCBANK.NS and ICICIBANK.NS as a bulleted list.")
    single("f-err-table", "Call price_data once with no arguments at all. Then, under a line ending in a colon, give the latest prices of SBIN.NS and AXISBANK.NS as a markdown table.")
if which in ("true", "all"):
    single("t-msft-price", "What is MSFT's latest price? Cite the tool you got it from.")
    single("t-rel-list", "Get the latest prices of RELIANCE.NS and SBIN.NS and list them as bullets under a line ending in a colon.")
    single("t-tsla-news", "Get the latest news on Tesla and write one sentence per item that starts with 'According to <the outlet>,'.")
    single("t-user-sale", "I sold 5 TCS shares at ₹3,100 each. Without calling any tool, restate my sale price and my total proceeds.")
print("ALLDONE", flush=True)
