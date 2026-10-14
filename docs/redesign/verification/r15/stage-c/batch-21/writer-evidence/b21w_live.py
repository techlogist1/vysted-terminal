"""batch-21 W1 live bar: sidecar from the writer tree on :52350, llama3.1:8b via ollama, autonomy ask.
Transcripts land beside this file as <tag>.jsonl (events) + <tag>.txt (client log). Run with cwd=<tree>."""
import json, subprocess, sys
from pathlib import Path
E = Path(__file__).resolve().parent
TREE = E.parents[6]
PY = "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/.venv/bin/python"
def run(tag, prompt, options=None):
    cmd = [PY, "scripts/r15/vy.py", "invoke", "copilot", prompt, "--port", "52350", "--provider", "ollama",
           "--model", "llama3.1:8b", "--autonomy", "ask", "--no-key", "--tag", "b21w", "--out", f"{E}/{tag}.jsonl", "--timeout", "600"]
    if options: cmd += ["--options", json.dumps(options)]
    with open(f"{E}/{tag}.txt", "w") as f: subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=TREE)
    evs = [json.loads(l) for l in open(f"{E}/{tag}.jsonl") if l.strip()]
    text = "".join(e.get("text") or "" for e in evs if e.get("kind") == "delta")
    calls = [(e["name"], e.get("input")) for e in evs if e.get("kind") == "tool_use"]
    res = [(e.get("name"), e.get("ok"), str(e.get("error") or "")[:100]) for e in evs if e.get("kind") == "tool_result"]
    print(f"== {tag}\ncalls={calls}\nresults={res}\n---\n{text}\n", flush=True)
    return text
INFY_T1 = "What are the latest prices of Infosys and TCS? Call price_data for INFY.ZZ and for TCS.NS."
P = [
 ("v-sify-ttm", "What is SIFY's TTM revenue in USD?"),
 ("y-ack-sbin", "Call price_data once with no arguments. Even if the tool fails, tell me what you know about SBIN.NS's latest close."),
 ("y-neg-estimate-sbin", "Call price_data once with no arguments at all. Then write one sentence that starts 'Although the price_data tool failed,' and gives SBIN.NS's latest close in rupees."),
 ("x-infy-tcs-t1", INFY_T1),
 ("x-tilde-fence", "Show the raw fundamentals for TATAMOTORS.NS in a ~~~ fenced block."),
 ("t-msft-price", "What is MSFT's latest price? Round it to two decimals."),
 ("t-tcs-name", "Get the latest price of TCS.NS and state it in one sentence that names the company as Tata Consultancy Services."),
 ("x-tilde-fence-err", "Call fundamentals once with no arguments at all. Then show TATAMOTORS.NS's P/E and market cap as JSON in a ~~~ fenced block, then say 'Hope that helps.'"),
 ("x-allerr-names", "Call price_data once with no arguments at all. Then write one sentence with the latest closing prices of Infosys and State Bank of India."),
 ("t-user-after-err","I bought 12 HDFCBANK.NS shares at ₹1,640 each. Call price_data once with no arguments, then restate my buy price and my total cost."),
]
only = sys.argv[1:]
for tag, q in P:
    if only and tag not in only: continue
    text = run(tag, q)
    if tag == "x-infy-tcs-t1":
        history = [{"role": "user", "content": INFY_T1}, {"role": "assistant", "content": text}]
        run("x-infy-tcs-t2", "Infosys matters most to me. Call price_data for INFY.ZZ and TCS.NS again and give me both latest prices.", {"history": history})
print("ALLDONE", flush=True)
