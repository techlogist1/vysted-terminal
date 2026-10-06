"""Offline check of the named narrowing-only fix to planner._NO_TOOL_CUE (not applied to code).
Every prompt the verifiers classified (batches 21-23 + this run) with its intended outcome; compares the
shipping cue (014bb7f1, copied verbatim) with the narrowed cue."""
import re, sys
sys.path.insert(0, "."); import dv_prompts as P
SHIP = re.compile(
    r"\bwithout (?:calling|using|running|invoking)(?: any)? tools?\b"
    r"|\b(?:don'?t|do not|never) (?:call|use)(?: any)? tools?\b"
    r"|\bno tool(?:s\b|\s*calls?\b)"
    r"|\b(?:just|only) answer from what (?:i )?(?:gave|told) you\b")
# Narrowing only: same four alternatives, each must be followed by a clause end or a closed tail, and a
# reported instruction ("never said don't use tools") never fires. It can only turn a strip into a keep.
TAIL = (r"(?=\s*(?:$|[.,;:!?)—–]|-\s|please\b|at all\b|whatsoever\b|here\b|now\b|this time\b|today\b"
        r"|and\b|just\b|for (?:this|that)(?: one| question| turn)?\s*(?:$|[.,;:!?—–])))")
FIX = re.compile(
    r"(?<!said )(?<!say )(?:\bwithout (?:calling|using|running|invoking)(?: any)? tools?\b"
    r"|\b(?:don'?t|do not|never) (?:call|use)(?: any)? tools?\b"
    r"|\bno tool(?:s\b|\s*calls?\b)"
    r"|\b(?:just|only) answer from what (?:i )?(?:gave|told) you\b)" + TAIL)
# (want_strip, prompt): True = an explicit no-tool instruction, False = a data request that must keep tools
CASES = [(True, p) for _, p in P.L38] + [(True, p) for _, p in P.MISS] + [(False, p) for _, p in P.KEEP + P.OVER + P.L37]
CASES += [
 (True, "I sold 5 TCS shares at ₹3,100 each. Without calling any tool, restate my sale price and my total proceeds."),
 (True, "Please answer without using any tools: I own 30 ITC shares at ₹410 and will add 10 more at ₹420. What's my new average cost?"),
 (True, "No tools please. I bought 15 WIPRO shares at ₹250 and sold them at ₹262. What was my profit?"),
 (True, "Don't use any tools, add 7 INFY to my holdings"),
 (True, "no tool calls — I sold 4 TCS at ₹3,200, what did I get?"),
 (True, "DON'T USE TOOLS. Sell 5 ITC at ₹420 from my portfolio."),
 (True, "Never use tools for this: add 5 TCS at ₹3,000 to my holdings."),
 (True, "I hold 40 HDFCBANK at ₹1,640; just answer from what I gave you: what is my cost basis?"),
 (False, "Just get the latest price from the market for the stocks in this message: TCS.NS, INFY.NS"),
 (False, "Only use data from price_data for the above symbols: TCS.NS"),
 (False, "Why did you not use the tools? Get the TCS.NS price now."),
 (False, "Don't forget to use the tools to get the latest TCS.NS price."),
 (False, "Do not answer without using the tools: what is TCS.NS trading at?"),
 (False, "Never guess, always call the tools: what is INFY.NS trading at"),
 (False, "Don't use web search, get TCS.NS price"),
 (False, "Add 10 TCS at 3,200 to my portfolio"),
 (False, "What tools do you have?"),
 (False, "I don't trust your memory, use the tools to fetch INFY.NS fundamentals"),
 (False, "Could you use the tools to get HDFCBANK.NS price?"),
 (False, "Don't rely on memory; get TCS.NS price with the tools."),
 (False, "No need to avoid the tools this time: what is SBIN.NS at?"),
 (False, "What is TCS.NS at? Don't call the news tool."),
 (False, "Without calling the fundamentals tool, use price_data for TCS.NS."),
]
tot = {"ship": [0, 0, 0], "fix": [0, 0, 0]}  # [correct, over-strip, miss]
for want, p in CASES:
    s, f = bool(SHIP.search(p.lower())), bool(FIX.search(p.lower()))
    for k, got in (("ship", s), ("fix", f)):
        tot[k][0 if got == want else (1 if got else 2)] += 1
    flag = "" if f == want else ("  <- FIX OVER-STRIP" if f else "  <- fix miss (fails safe)")
    new = "  ** NEW DIVERGENCE vs ship on a strip" if (s and want and not f) else ""
    print(f"want_strip={want!s:5} ship={s!s:5} fix={f!s:5}{flag}{new} | {p}")
    assert not (f and not s), "fix must only narrow"
print(f"\nN={len(CASES)}  ship correct/over-strip/miss={tot['ship']}  fix correct/over-strip/miss={tot['fix']}")
