import json, subprocess, sys
S = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad"
E = f"{S}/b22v/live"
PY = "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/.venv/bin/python"
def run(tag, prompt, options=None):
    cmd = [PY, "scripts/r15/vy.py", "invoke", "copilot", prompt, "--port", "52310", "--provider", "ollama",
           "--model", "llama3.1:8b", "--autonomy", "ask", "--no-key", "--tag", "b22v", "--out", f"{E}/{tag}.jsonl", "--timeout", "600"]
    if options: cmd += ["--options", json.dumps(options)]
    with open(f"{E}/{tag}.txt", "w") as f: subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=f"{S}/batch-22-verify")
    evs = [json.loads(l) for l in open(f"{E}/{tag}.jsonl") if l.strip()]
    text = "".join(e.get("text") or "" for e in evs if e.get("kind") == "delta")
    calls = [(e["name"], e.get("input")) for e in evs if e.get("kind") == "tool_use"]
    res = [(e.get("name"), e.get("ok"), str(e.get("error") or "")[:120]) for e in evs if e.get("kind") == "tool_result"]
    other = sorted({e.get("kind") for e in evs} - {"delta", "tool_use", "tool_result"})
    print(f"== {tag}\nprompt={prompt!r}\ncalls={calls}\nresults={res}\nkinds={other}\n---\n{text}\n", flush=True)
P = [
 ("o-sify-ttm", "What is SIFY's TTM revenue in USD?"),
 ("l-mixed-mm", "Call price_data for TCS.NS, and call price_data for MM.ZZ. Then tell me the latest prices of TCS and M&M, one sentence each."),
 ("l-unclosed-json", "Call fundamentals once with no arguments at all. Then reply with only a ```json code block holding Infosys's P/E and market cap, and do not write the closing fence."),
 ("l-allerr-bullets", "Call price_data once with no arguments at all. Then list the latest closes of Axis Bank, Kotak Mahindra Bank and ICICI Bank as bullet points."),
 ("l-peer-uncalled", "Get TCS.NS's latest price with price_data, and in the same sentence also tell me Infosys's latest price from what you remember."),
 ("c-user-figure", "I bought 12 HDFCBANK.NS shares at ₹1,650 each. Call price_data once with no arguments, then restate my buy price and my total cost."),
 ("c-ok-rounding", "What is ITC.NS's latest price? Round it to the nearest rupee."),
 ("c-short-ok", "Get the latest price of SBIN.NS and state it in one sentence that calls the company SBI."),
 ("n-answer-without", "Answer without any tools: I sold 5 TCS shares at ₹3,100 each. Restate my total proceeds."),
 ("n-do-not-call-a-tool", "Do not call a tool. I sold 5 TCS shares at ₹3,100 each; restate my proceeds."),
 ("n-curly-dont", "Don’t use any tools. I sold 5 TCS shares at ₹3,100 each; restate my proceeds."),
 ("n-avoid-functions", "Avoid calling any functions. I bought 40 ITC shares at ₹415, add them to my holdings and tell me what I spent."),
 ("n-zero-tool-calls", "Zero tool calls please: I want to add 7 INFY at ₹1,500 to my portfolio — just tell me the total cost."),
 ("n-control-add", "Add 10 TCS at 3,200 to my portfolio"),
 ("n-named-exclusion", "Don't use web search, get TCS.NS price"),
 ("fp-dont-forget", "Don't forget to use the tools to get the latest TCS.NS price."),
 ("l2-json-dump", "Call fundamentals once with no arguments at all. Then give Infosys's P/E and market cap as raw JSON inside a ```json code block, nothing else."),
 ("l2-tata-paragraph", "Call price_data for TCS.NS and price_data for TATAMOTORS.ZZ. Then give both latest prices in a single paragraph, one sentence each, TCS first."),
 ("fp-just-from-market", "Just get the latest price from the market for the stocks in this message: INFY.NS"),
]
only = sys.argv[1:]
for tag, q in P:
    if not only or tag in only: run(tag, q)
print("ALLDONE", flush=True)
