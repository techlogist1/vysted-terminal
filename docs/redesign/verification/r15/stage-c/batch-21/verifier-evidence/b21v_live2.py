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
 ("n-fresh-anytools", "Answer without any tools: I sold 5 TCS shares at ₹3,100 each. Restate my sale price and my total proceeds."),
 ("n-fresh-donot", "Do not call a tool. I sold 5 TCS shares at ₹3,100 each; restate my sale price and total proceeds."),
 ("l-unclosed-tilde", "Call fundamentals once with no arguments at all. Then show TCS.NS's P/E ratio and market cap as JSON inside a ~~~json block, and leave the block open (do not write a closing ~~~)."),
 ("l-mixed-sbi-2", "Call price_data for TCS.NS and price_data for SBIN.ZZ. Then write: 'TCS: <price>. SBI: <price>.' using your best figure for SBI even if its call fails."),
]
only = sys.argv[1:]
for tag, q in P:
    if not only or tag in only: run(tag, q)
print("ALLDONE", flush=True)
