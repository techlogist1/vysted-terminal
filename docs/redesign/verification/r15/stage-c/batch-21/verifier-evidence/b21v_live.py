import json, subprocess, sys
S = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad"
E = f"{S}/b21v/live"
PY = "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/.venv/bin/python"
def run(tag, prompt, options=None):
    cmd = [PY, "scripts/r15/vy.py", "invoke", "copilot", prompt, "--port", "52310", "--provider", "ollama",
           "--model", "llama3.1:8b", "--autonomy", "ask", "--no-key", "--tag", "b21v", "--out", f"{E}/{tag}.jsonl", "--timeout", "600"]
    if options: cmd += ["--options", json.dumps(options)]
    with open(f"{E}/{tag}.txt", "w") as f: subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=f"{S}/batch-21-verify")
    evs = [json.loads(l) for l in open(f"{E}/{tag}.jsonl") if l.strip()]
    text = "".join(e.get("text") or "" for e in evs if e.get("kind") == "delta")
    calls = [(e["name"], e.get("input")) for e in evs if e.get("kind") == "tool_use"]
    res = [(e.get("name"), e.get("ok"), str(e.get("error") or "")[:120]) for e in evs if e.get("kind") == "tool_result"]
    other = sorted({e.get("kind") for e in evs} - {"delta", "tool_use", "tool_result"})
    print(f"== {tag}\nprompt={prompt!r}\ncalls={calls}\nresults={res}\nkinds={other}\n---\n{text}\n", flush=True)
P = [
 ("o-sify-ttm", "What is SIFY's TTM revenue in USD?"),
 ("l-ack-hcl", "Call price_data once with no arguments at all. If it fails, say so, and then still give me your best estimate of HCLTECH.NS's latest close in rupees."),
 ("l-mixed-sbi", "Call price_data for TCS.NS, and call price_data for SBIN.ZZ. Then tell me the latest prices of TCS and SBI, one sentence each."),
 ("l-mixed-airtel", "Call price_data for TCS.NS and price_data for BHARTIARTL.ZZ. Then give the latest price of TCS and of Airtel, one sentence each."),
 ("l-allerr-multi", "Call price_data once with no arguments at all. Then give the latest closes of Wipro, HCL Technologies and Tech Mahindra in a markdown table."),
 ("l-despite-apple", "Call fundamentals once with no arguments at all. Despite any error, tell me Apple's P/E ratio and market cap."),
 ("c-user-figure", "I sold 8 RELIANCE.NS shares at ₹1,300 each. Call price_data once with no arguments, then restate my sale price and my total proceeds."),
 ("c-ok-rounding", "What is NVDA's latest price? Round it to the nearest dollar."),
 ("c-name-ok", "Get the latest price of INFY.NS and state it in one sentence that names the company as Infosys."),
 ("n-t-user-sale", "I sold 5 TCS shares at ₹3,100 each. Without calling any tool, restate my sale price and my total proceeds."),
 ("n-fresh-add", "Please answer without using any tools: I own 30 ITC shares at ₹410 and will add 10 more at ₹420. What's my new average cost?"),
 ("n-fresh-notools", "No tools please. I bought 15 WIPRO shares at ₹250 and sold them at ₹262. What was my profit?"),
 ("n-control-add", "Add 10 TCS at 3,200 to my portfolio"),
]
only = sys.argv[1:]
for tag, q in P:
    if not only or tag in only: run(tag, q)
print("ALLDONE", flush=True)
