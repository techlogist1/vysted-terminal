"""Verifier offline check: base 014bb7f1 cue vs int-head cue over the 67 + fresh phrasings."""
import importlib.util, re, sys
S = sys.argv[1]
sys.path.insert(0, f"{S}/batch-24-verify/sidecar")
from services import planner as INT  # int head d1290f66
spec = importlib.util.spec_from_file_location("planner_base", f"{S}/b24v/planner_014bb7f1.py")
BASE = importlib.util.module_from_spec(spec); sys.modules["planner_base"] = BASE; spec.loader.exec_module(BASE)
FIX_SRC = open("/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/stage-c/batch-23/verifier-evidence/disposition/dv_fix_regex.py").read()
ns = {}; exec(FIX_SRC.split("# (want_strip")[0].replace("sys.path.insert(0, \".\"); import dv_prompts as P", ""), ns)
print("int pattern == dv_fix_regex.FIX.pattern:", INT._NO_TOOL_CUE.pattern == ns["FIX"].pattern)
print("base pattern == dv SHIP.pattern:", BASE._NO_TOOL_CUE.pattern == ns["SHIP"].pattern)
rows = []
for line in open("/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/stage-c/batch-23/verifier-evidence/disposition/fix-regex.out"):
    m = re.match(r"want_strip=(True|False)\s+ship=\S+\s+fix=\S+.*? \| (.*)$", line.rstrip("\n"))
    if m: rows.append(("67", m.group(1) == "True", m.group(2)))
FRESH_DATA = [
 "Don't use tools other than the quote lookup — what's INFY.NS trading at?",
 "Don't call tools you can skip; just fetch the SBIN.NS quote.",
 "Don't call tools twice. Fetch the WIPRO.NS price once.",
 "Don't use tools for the maths, but do look up the ITC.NS quote.",
 "I never said don't use tools. Get me the HDFCBANK.NS price.",
 "My advisor said don't use tools, but I want the live RELIANCE.NS price.",
 "You said no tools earlier — ignore that and fetch the TCS.NS price.",
 "Do not use tools beyond the price lookup: SBIN.NS close?",
 "No tools except the quote tool, please: WIPRO.NS price?",
 "Without using tools like web search, give me the ITC.NS price from price_data.",
 "Don't use any tools except price_data for RELIANCE.NS.",
 "Never use tools blindly; check the INFY.NS price with price_data.",
 "Don't use tools unnecessarily, but I do need the live TCS.NS price.",
 "Do not call tools in a loop — one price_data call for HDFCBANK.NS is enough.",
 "He says don't use tools, but please fetch the TCS.NS price.",
 "Don't use any tools, except price_data for the TCS.NS price.",
 "No tools, other than the price lookup: what's SBIN.NS at?",
 "Don't use tools. Just kidding — get me the INFY.NS price.",
]
FRESH_NOTOOL = [
 "Don't use any tools; I bought 12 ITC at ₹270, what did I spend?",
 "No tools at all please. 8 WIPRO at ₹160 — total cost?",
 "Without calling any tools, tell me 20 × ₹983.",
 "Do not use tools! Add up 3 SBIN at ₹980 and 2 SBIN at ₹990.",
 "never call tools here: what's my average if I bought 10 at 100 and 10 at 120?",
 "Please answer without using tools. I hold 6 TCS at ₹2,000; value at ₹2,100?",
 "Don't call any tools, just compute 15% of ₹40,000.",
 "Just answer from what I gave you. I sold 3 INFY at ₹1,010; proceeds?",
 "no tool calls. restate: I own 50 HDFCBANK at ₹735.",
 "Don't use tools for this one. 4 RELIANCE at ₹1,226 — total?",
 "Don't use any tools for my calculation: I bought 5 ITC at ₹420, total?",
 "Do not call tools when answering: 7 × ₹269?",
]
rows += [("fresh-data", False, p) for p in FRESH_DATA] + [("fresh-notool", True, p) for p in FRESH_NOTOOL]
tally = {}
for src, want, p in rows:
    low = p.strip().lower()
    b, f = bool(BASE._NO_TOOL_CUE.search(low)), bool(INT._NO_TOOL_CUE.search(low))
    bi = "no-tool" in BASE.classify_intent(p).signals; fi = "no-tool" in INT.classify_intent(p).signals
    assert (b, f) == (bi, fi)
    newstrip = f and not b
    k = tally.setdefault(src, {"n": 0, "base_over": 0, "int_over": 0, "base_miss": 0, "int_miss": 0, "NEW_STRIP": 0, "lost_strip": 0})
    k["n"] += 1; k["NEW_STRIP"] += newstrip
    k["base_over"] += (b and not want); k["int_over"] += (f and not want)
    k["base_miss"] += (want and not b); k["int_miss"] += (want and not f); k["lost_strip"] += (want and b and not f)
    tag = ("  ** NEW STRIP" if newstrip else "") + ("  <- INT OVER-STRIP" if f and not want else "") + ("  <- lost strip (fails safe)" if want and b and not f else "")
    print(f"[{src:12}] want_strip={want!s:5} base={b!s:5} int={f!s:5}{tag} | {p}")
print()
for k, v in tally.items(): print(k, v)
