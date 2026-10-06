"""batch-23 verifier live runs on :52310, llama3.1:8b/ollama, autonomy ask. Args pick tags; env B23V_SET picks a set."""
import json, os, subprocess, sys
S = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad"
E = f"{S}/b23v/live"; TREE = f"{S}/batch-23-verify"
PY = "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/.venv/bin/python"
VY = [PY, "scripts/r15/vy.py"]
def get(path):
    return subprocess.run(VY + ["get", path, "--port", "52310"], capture_output=True, text=True, cwd=TREE).stdout.strip()[:300]
def run(tag, prompt, history=None):
    cmd = VY + ["invoke", "copilot", prompt, "--port", "52310", "--provider", "ollama", "--model", "llama3.1:8b",
                "--autonomy", "ask", "--no-key", "--tag", "b23v", "--out", f"{E}/{tag}.jsonl", "--timeout", "600"]
    if history: cmd += ["--options", json.dumps({"history": history})]
    with open(f"{E}/{tag}.txt", "w") as f: subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=TREE)
    evs = [json.loads(l) for l in open(f"{E}/{tag}.jsonl") if l.strip()]
    text = "".join(e.get("text") or "" for e in evs if e.get("kind") == "delta")
    calls = [(e["name"], e.get("input")) for e in evs if e.get("kind") == "tool_use"]
    res = [(e.get("name"), e.get("ok"), str(e.get("error") or "")[:120]) for e in evs if e.get("kind") == "tool_result"]
    other = sorted({e.get("kind") for e in evs} - {"delta", "tool_use", "tool_result"})
    print(f"== {tag}\nprompt={prompt!r}\ncalls={calls}\nresults={res}\nkinds={other}\npositions={get('/portfolio/positions')}\n---\n{text}\n", flush=True)
    return text
SETS = {
"a": [  # LEAD-035 batch-22 keep-surface six + no-tool b21/b22 + literal repro + controls
 ("k-dont-forget", "Don't forget to use the tools to get the latest TCS.NS price."),
 ("k-do-not-answer-without", "Do not answer without using the tools: what is TCS.NS trading at?"),
 ("k-why-not-q", "Why did you not use the tools? Get the TCS.NS price now."),
 ("k-just-from-market", "Just get the latest price from the market for the stocks in this message: TCS.NS, INFY.NS"),
 ("k-only-price-data", "Only use data from price_data for the above symbols: TCS.NS"),
 ("t-user-sale", "I sold 5 TCS shares at ₹3,100 each. Without calling any tool, restate my sale price and my total proceeds."),
 ("n-answer-without", "Answer without any tools: I sold 5 TCS shares at ₹3,100 each. Restate my total proceeds."),
 ("n-do-not-call-a-tool", "Do not call a tool. I sold 5 TCS shares at ₹3,100 each; restate my proceeds."),
 ("n-curly-dont", "Don’t use any tools. I sold 5 TCS shares at ₹3,100 each; restate my proceeds."),
 ("n-avoid-functions", "Avoid calling any functions. I bought 40 ITC shares at ₹415, add them to my holdings and tell me what I spent."),
 ("n-zero-tool-calls", "Zero tool calls please: I want to add 7 INFY at ₹1,500 to my portfolio — just tell me the total cost."),
 ("n-skip-tools", "Skip the tools for this one — I hold 12 HDFCBANK at ₹1,600; add 3 more at ₹1,650, what is my average?"),
 ("n-fresh-add", "Please answer without using any tools: I own 30 ITC shares at ₹410 and will add 10 more at ₹420. What's my new average cost?"),
 ("n-fresh-notools", "No tools please. I bought 15 WIPRO shares at ₹250 and sold them at ₹262. What was my profit?"),
 ("n-from-given", "I hold 40 HDFCBANK at ₹1,640; answer only from what I gave you: what is my cost basis?"),
 ("n-from-memory", "From memory only: what did TCS close at last year?"),
 ("n-dont-use-add-infy", "Don't use any tools, add 7 INFY to my holdings"),
 ("c-add-tcs", "Add 10 TCS at 3,200 to my portfolio"),
 ("x-named-exclusion", "Don't use web search, get TCS.NS price"),
],
"b": [  # fresh verifier phrasings
 ("fk-blindly", "Don't just use the tools blindly — check the TCS.NS price and explain the move."),
 ("fk-twice", "Never call the tools twice for one symbol; get the INFY.NS price."),
 ("fk-dont-need", "Don't call functions you don't need, just get me SBIN.NS's latest price."),
 ("fk-no-lookups-tcs", "No lookups needed for TCS, I know it; what is ITC.NS trading at?"),
 ("fk-search-tools", "Never use the search tools, only the quote: INFY.NS price?"),
 ("fk-arith", "Don't use the tools for arithmetic; get the TCS.NS price."),
 ("fk-again", "Do not call the tools again for TCS, just get INFY.NS price."),
 ("fk-could-you", "Could you use the tools to get HDFCBANK.NS price?"),
 ("fk-please-use", "Please use your tools and fetch WIPRO.NS's close."),
 ("fk-never-said", "I never said don't use tools — get RELIANCE.NS price."),
 ("fn-memory", "Please answer from memory only: what's 12% of ₹5,000?"),
 ("fn-no-function-calls", "No function calls. I bought 15 WIPRO at ₹250; total cost?"),
 ("fn-never-use-add", "Never use tools for this: add 5 TCS at ₹3,000 to my holdings."),
 ("fn-refrain", "Refrain from calling any tools and restate my 5 TCS at ₹3,100."),
 ("fn-passive", "The tools must not be used here. I hold 10 INFY at ₹1,500; cost?"),
 ("fn-caps-sell", "DON'T USE TOOLS. Sell 5 ITC at ₹420 from my portfolio."),
 ("fn-without-functions-add", "Without using functions, add 3 HDFCBANK at ₹1,650 to my holdings and tell me the total."),
],
"c": [  # LEAD-030 literal repro + fresh mixed turns
 ("o-sify-ttm", "What is SIFY's TTM revenue in USD?"),
 ("o-sify-ttm-2", "What is SIFY's TTM revenue in USD?"),
 ("c1-adani-errored", "Call price_data for TCS.NS and price_data for ADANIENT.ZZ. Then give both latest prices in one paragraph, TCS first, calling the second one the Adani flagship."),
 ("c2-kotak-uncalled", "Get SBIN.NS's latest price with price_data, and in the same paragraph tell me Kotak Bank's latest price from memory."),
 ("c3-hul-errored", "Call price_data for INFY.NS and price_data for HINDUNILVR.ZZ, then write one paragraph with the latest price of Infosys and of HUL."),
 ("c4-allerr-bajaj-maruti", "Call price_data once with no arguments at all. Then tell me the latest close of Bajaj Finance and Maruti Suzuki."),
 ("c5-allerr-reliance-fund", "Call fundamentals for RELIANCE.ZZ, then give Reliance's P/E and market cap."),
 ("c6-hul-peer-uncalled", "Get ITC.NS's latest price with price_data. Then, without calling anything else, tell me the latest price of its peer Hindustan Unilever in the same paragraph."),
 ("c8-l2-json-dump", "Call fundamentals once with no arguments at all. Then give Infosys's P/E and market cap as raw JSON inside a ```json code block, nothing else."),
 ("c7-ibm-memory", "Call price_data for WIPRO.NS and for BIGBLUE.ZZ. Report both, then add IBM's latest price from memory."),
],
}
only = sys.argv[1:]
s = os.environ.get("B23V_SET", "a")
print(f"quotes={[get('/quotes/'+x) for x in ('TCS.NS','INFY.NS','SBIN.NS','ITC.NS','HDFCBANK.NS','WIPRO.NS','RELIANCE.NS')]}\npositions_before={get('/portfolio/positions')}\n", flush=True)
for tag, q in SETS[s]:
    if not only or tag in only: run(tag, q)
if s == "a" and (not only or "k-why-not-bare" in only):
    t1 = "What is TCS.NS trading at?"; a1 = run("k-why-not-bare-t1", t1)
    run("k-why-not-bare", "Why did you not use the tools", [{"role": "user", "content": t1}, {"role": "assistant", "content": a1}])
print("ALLDONE", flush=True)
