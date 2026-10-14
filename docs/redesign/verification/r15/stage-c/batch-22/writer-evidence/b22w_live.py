"""batch-22 W1 live bar (l2-* tags: the second run, live2.out): sidecar from the writer tree on :52350, llama3.1:8b via ollama, autonomy ask.
Transcripts land in live/ beside this file as <tag>.jsonl (events) + <tag>.txt (client log).
Run with cwd=<tree>; optional args pick tags."""
import json, subprocess, sys
from pathlib import Path
E = Path(__file__).resolve().parent / "live"
TREE = Path(__file__).resolve().parents[7]
PY = "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/.venv/bin/python"
def run(tag, prompt):
    E.mkdir(exist_ok=True)
    cmd = [PY, "scripts/r15/vy.py", "invoke", "copilot", prompt, "--port", "52350", "--provider", "ollama",
           "--model", "llama3.1:8b", "--autonomy", "ask", "--no-key", "--tag", "b22w", "--out", f"{E}/{tag}.jsonl", "--timeout", "600"]
    with open(f"{E}/{tag}.txt", "w") as f: subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=TREE)
    evs = [json.loads(l) for l in open(f"{E}/{tag}.jsonl") if l.strip()]
    text = "".join(e.get("text") or "" for e in evs if e.get("kind") == "delta")
    calls = [(e["name"], e.get("input")) for e in evs if e.get("kind") == "tool_use"]
    res = [(e.get("name"), e.get("ok"), str(e.get("error") or "")[:100]) for e in evs if e.get("kind") == "tool_result"]
    print(f"== {tag}\nprompt={prompt!r}\ncalls={calls}\nresults={res}\n---\n{text}\n", flush=True)
P = [
 ("o-sify-ttm", "What is SIFY's TTM revenue in USD?"),
 ("l-mixed-sbi-airtel", "Call price_data for SBIN.ZZ and price_data for BHARTIARTL.NS. Then give the latest price of SBI and of Airtel, one sentence each."),
 ("l-mixed-lt", "Call price_data for TCS.NS and price_data for LT.ZZ. Then tell me the latest price of TCS and of L&T, one sentence each."),
 ("l-allerr-codeblock", "Call price_data once with no arguments at all. Then give the latest closes of SBI, Airtel and L&T in a JSON code block."),
 ("l-raw-json", "Call fundamentals once with no arguments at all. Then reply with raw JSON only: an object with TCS's pe_ratio and market_cap."),
 ("l-nifty-2c", "Call price_data for XYZ.ZZ. Then tell me in one sentence how much the Nifty 50 moved today, as a percentage."),
 ("c-ok-rounding", "What is NVDA's latest price? Round it to the nearest dollar."),
 ("c-short-ok", "Get the latest price of SBIN.NS and state it in one sentence that calls the company SBI."),
 ("c-short-ok-mixed", "Call price_data for BHARTIARTL.NS and price_data for INFY.ZZ. Then give Airtel's latest price in one sentence."),
 ("c-user-after-err", "I sold 8 RELIANCE.NS shares at ₹1,300 each. Call price_data once with no arguments, then restate my sale price and my total proceeds."),
 ("l2-nifty-2c-mixed", "Call price_data for TCS.NS and price_data for XYZ.ZZ. Do not call any other tool. Give TCS's latest price in one sentence. Then, in a separate paragraph, state from memory how much the Nifty 50 moved today as a percentage."),
 ("l2-short-hul", "Call price_data for TCS.NS and price_data for HINDUNILVR.ZZ. Then give the latest price of TCS and of HUL, one sentence each."),
 ("l2-user-after-err", "I sold 8 RELIANCE.NS shares at ₹1,300 each, so my proceeds were ₹10,400. Call price_data for XYZ.ZZ, then repeat back my sale price and my total proceeds in one sentence."),
 ("l2-short-ril", "Call price_data for TCS.NS and price_data for RELIANCE.ZZ. Do not call any other tool. Then give the latest price of TCS and of RIL, one sentence each."),
]
only = sys.argv[1:]
for tag, q in P:
    if not only or tag in only: run(tag, q)
print("ALLDONE", flush=True)
