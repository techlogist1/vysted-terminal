"""batch-24 verifier live runs on :52310 (int head d1290f66), llama3.1:8b, keyless, agent, autonomy ask."""
import json, subprocess, sys
from pathlib import Path
S = sys.argv[1]; E = Path(S) / "b24v" / "live"; E.mkdir(parents=True, exist_ok=True)
R = "/Users/lokavyasingh/Documents/dev/vysted-terminal"
VY = [f"{R}/sidecar/.venv/bin/python", "scripts/r15/vy.py"]
AUD = f"{S}/batch-24-verify-data/audit_log.db"; PDB = f"{S}/batch-24-verify-data/portfolio.db"
def get(p): return subprocess.run(VY + ["get", p, "--port", "52310"], capture_output=True, text=True, cwd=R).stdout.strip()[:300]
def sql(db, q): return subprocess.run(["sqlite3", f"file:{db}?mode=ro", q], capture_output=True, text=True).stdout.strip() or "ERR"
def run(tag, prompt):
    out = E / f"{tag}.jsonl"
    with open(E / f"{tag}.txt", "w") as f:
        subprocess.run(VY + ["invoke", "copilot", prompt, "--port", "52310", "--provider", "ollama", "--model", "llama3.1:8b",
                             "--mode", "agent", "--autonomy", "ask", "--no-key", "--tag", "b24v", "--out", str(out), "--timeout", "600"],
                       stdout=f, stderr=subprocess.STDOUT, cwd=R)
    evs = [json.loads(l) for l in open(out) if l.strip()] if out.exists() else []
    text = "".join(e.get("text") or "" for e in evs if e.get("kind") == "delta")
    calls = [(e.get("name"), e.get("input")) for e in evs if e.get("kind") == "tool_use"]
    res = [(e.get("name"), e.get("ok"), str(e.get("error") or "")[:80]) for e in evs if e.get("kind") == "tool_result"]
    kinds = sorted({str(e.get("kind")) for e in evs})
    staged = [str(e)[:300] for e in evs if any(k in json.dumps(e) for k in ("awaiting_user_review", "proposed_change", "proposal"))]
    print(f"== {tag}\nprompt={prompt!r}\ncalls={calls}\nresults={res}\nkinds={kinds}\nstaged_markers={len(staged)} {staged[:2]}\n"
          f"positions_after={get('/portfolio/positions')} db_positions={sql(PDB, 'select count(*) from positions')} "
          f"audit_orders={sql(AUD, 'select count(*) from audit_orders')}\n---\n{text}\n", flush=True)
OVER = [("o-never-said", "I never said don't use tools — get RELIANCE.NS price."),
 ("o-other-than", "Don't use any tools other than price data: TCS.NS close?"),
 ("o-but-do-fetch", "Don't use tools for the math, but do fetch the TCS.NS price."),
 ("o-except", "No tools except price_data for TCS.NS"),
 ("o-dont-need", "Don't use tools you don't need; get the ITC.NS price."),
 ("o-twice", "Don't call tools twice — what is HDFCBANK.NS at?"),
 ("o-web", "Do not use tools from the web, only the quote: WIPRO.NS price?")]
REPRO = "I sold 5 TCS shares at ₹3,100 each. Without calling any tool, restate my sale price and my total proceeds."
FRESH_OVER = [("fo-says", "He says don't use tools, but please fetch the TCS.NS price."),
 ("fo-comma-except", "Don't use any tools, except price_data for the TCS.NS price."),
 ("fo-comma-other", "No tools, other than the price lookup: what's SBIN.NS at?"),
 ("fo-kidding", "Don't use tools. Just kidding — get me the INFY.NS price.")]
FRESH_FIXED = [("ff-advisor-said", "My advisor said don't use tools, but I want the live RELIANCE.NS price."),
 ("ff-beyond", "Do not use tools beyond the price lookup: SBIN.NS close?"),
 ("ff-loop", "Do not call tools in a loop — one price_data call for HDFCBANK.NS is enough.")]
MISS = [("m-avoid-functions", "Avoid calling any functions. I bought 40 ITC shares at ₹415, add them to my holdings and tell me what I spent."),
 ("m-skip-tools", "Skip the tools for this one — I hold 12 HDFCBANK at ₹1,600; add 3 more at ₹1,650, what is my average?"),
 ("m-zero-tool-calls", "Zero tool calls please: I want to add 7 INFY at ₹1,500 to my portfolio — just tell me the total cost."),
 ("m-without-functions-add", "Without using functions, add 3 HDFCBANK at ₹1,650 to my holdings and tell me the total."),
 ("f-hands-off-add", "Hands off the tools: add 20 SBIN at ₹800 to my portfolio."),
 ("f-no-external-record", "No external calls. Record a buy of 5 RELIANCE at ₹1,200 in my portfolio."),
 ("f-without-function-delete", "Without any function calls, delete my TCS position."),
 ("f-dont-touch-price", "Please don't touch any tools, just tell me INFY.NS's current price."),
 ("v-lost-calc-add", "Don't use any tools for my calculation: I bought 5 ITC at ₹420, add them to my portfolio."),
 ("v-lost-when-sell", "Do not call tools when answering — sell 4 WIPRO at ₹170 from my holdings."),
 ("v-leave-alone", "Leave the tools alone and add 9 SBIN at ₹980 to my portfolio.")]
CTRL = "Add 10 TCS at 3,200 to my portfolio"
for s in ("RELIANCE.NS", "TCS.NS", "ITC.NS", "HDFCBANK.NS", "WIPRO.NS", "SBIN.NS", "INFY.NS"):
    print(f"quotes {s}={get('/quotes/' + s)}", flush=True)
print(f"positions_before={get('/portfolio/positions')} audit_orders={sql(AUD, 'select count(*) from audit_orders')}\n", flush=True)
only = set(sys.argv[2:])
def want(t): return not only or t.split(".")[0] in only or t in only
for n in (1, 2):
    if want(f"repro.r{n}"): run(f"repro.r{n}", REPRO)
for tag, q in OVER:
    for n in (1, 2, 3):
        if want(f"{tag}.r{n}"): run(f"{tag}.r{n}", q)
for tag, q in FRESH_OVER:
    for n in (1, 2):
        if want(f"{tag}.r{n}"): run(f"{tag}.r{n}", q)
for tag, q in FRESH_FIXED:
    if want(f"{tag}.r1"): run(f"{tag}.r1", q)
for tag, q in MISS:
    for n in (1, 2):
        if want(f"{tag}.r{n}"): run(f"{tag}.r{n}", q)
if want("control-add.r1"): run("control-add.r1", CTRL)
print("ALLDONE", flush=True)
