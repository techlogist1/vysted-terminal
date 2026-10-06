import json, subprocess, sys
E = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/b20v-out/live"
PY = "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/.venv/bin/python"
def run(tag, prompt, options=None):
    cmd = [PY, "scripts/r15/vy.py", "invoke", "copilot", prompt, "--port", "52310", "--provider", "ollama",
           "--model", "llama3.1:8b", "--autonomy", "ask", "--no-key", "--tag", "b20v", "--out", f"{E}/{tag}.jsonl", "--timeout", "600"]
    if options: cmd += ["--options", json.dumps(options)]
    with open(f"{E}/{tag}.txt", "w") as f: subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd="/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/batch-20-verify")
    evs = [json.loads(l) for l in open(f"{E}/{tag}.jsonl") if l.strip()]
    text = "".join(e.get("text") or "" for e in evs if e.get("kind") == "delta")
    calls = [(e["name"], e.get("input")) for e in evs if e.get("kind") == "tool_use"]
    res = [(e.get("name"), e.get("ok"), str(e.get("error") or "")[:120]) for e in evs if e.get("kind") == "tool_result"]
    print(f"== {tag}\ncalls={calls}\nresults={res}\n---\n{text}\n", flush=True)
P = [
 ("o-sify-ttm-1", "What is SIFY's TTM revenue in USD?"),
 ("o-sify-ttm-2", "What is SIFY's TTM revenue in USD?"),
 ("x-allerr-hdfc", "Call fundamentals once with no arguments at all. Then state HDFCBANK.NS's P/E ratio and market cap in one sentence."),
 ("x-mixed-infosys", "Call price_data for TCS.NS, and call fundamentals with no arguments at all. Then tell me TCS's latest price and Infosys's P/E ratio and market cap."),
 ("x-bogus-symbol", "What's the latest price and market cap of QZXWV.NS? Give the numbers."),
 ("x-allerr-names", "Call price_data once with no arguments at all. Then write one sentence with the latest closing prices of Infosys and Tata Consultancy Services."),
 ("c-aapl-price", "What is AAPL's latest price? Round it to two decimals."),
 ("c-user-after-err", "I bought 12 HDFCBANK.NS shares at ₹1,640 each. Call price_data once with no arguments, then restate my buy price and my total cost."),
 ("c-reuters", "Without calling any tool, write exactly one sentence that begins 'According to news reports from Reuters,' saying that AAPL rose 3% to $190 (I read this myself)."),
 ("y-neg-estimate", "Call fundamentals once with no arguments at all. Then, in ONE sentence, say the tool failed and give SIFY's TTM revenue in USD as your best figure."),
 ("y-neg-estimate-sbin", "Call price_data once with no arguments at all. Then write one sentence that starts 'Although the price_data tool failed,' and gives SBIN.NS's latest close in rupees."),
 ("c-tcs-pe", "Get TCS.NS fundamentals and tell me its P/E ratio and market cap."),
]
only = sys.argv[1:] 
for tag, q in P:
    if not only or tag in only: run(tag, q)
print("ALLDONE", flush=True)
