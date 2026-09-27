import asyncio, sys, subprocess
sys.path.insert(0, "tests")
from test_b3_runtime_intent_gate import _CaptureProvider, _DATA_WRITES
from services import agent_runtime, planner
print("HEAD", subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip())
async def tools(prompt):
    agent_runtime.reload()
    p = _CaptureProvider()
    agent_runtime.get_provider = lambda *_a, **_k: p
    async for _ in agent_runtime.invoke_agent(agent_id="copilot", prompt=prompt, api_key="k", provider="ollama", mode="agent"):
        pass
    return set(p.tool_ids)
GROUPS = {
 "ENTRY OWN REPRO (register repro + round-1/round-2 acceptance phrasings)": [
  ("Write a note on Cochin Shipyard: valuation looks stretched at ~54x trailing P/E; revisit after Q2 results.", "write_note"),
  ("screen for defence stocks P/E < 40", "write_screener_filters"),
  ("Save my layout as research desk", "save_layout"),
  ("Delete TCS from my portfolio", "portfolio_delete_position"),
  ("Update my RELIANCE cost basis to 1180", "portfolio_update_position"),
  ("My RELIANCE lot is actually 12 shares", "portfolio_update_position"),
  ("I bought 10 shares of INFY at 1500, track it in my portfolio", "portfolio_add_position"),
  ("Put 25 HDFC Bank at 1600 in my paper portfolio", "portfolio_add_position"),
  ("Can you log 10 TCS at 3400 in my portfolio?", "portfolio_add_position"),
  ("Can you record that I hold 20 ITC at 410?", "portfolio_add_position"),
  ("Could you drop WIPRO from my portfolio?", "portfolio_delete_position"),
  ("Can you bump my INFY quantity to 30?", "portfolio_update_position"),
  ("Would you scrap my ITC position?", "portfolio_delete_position"),
  ("Can you trim INFY to 5 shares?", "portfolio_update_position"),
  ("Could you get rid of my HDFC Bank holding?", "portfolio_delete_position"),
 ],
 "VERIFIER / SHARD-9 REFUTATION PHRASINGS": [
  ("Any chance you could get rid of my TCS position?", "portfolio_delete_position"),
  ("Mind noting that INFY cut its guidance?", "write_note"),
  ("What if you noted that BEL order book is 75k cr?", "write_note"),
 ],
 "AUDITOR FRESH PHRASINGS (not in any test, not in any verifier file)": [
  ("Think you could scrap my WIPRO lot?", "portfolio_delete_position"),
  ("Do you mind dropping ITC from my holdings?", "portfolio_delete_position"),
  ("Would it be okay to bump my TCS quantity to 40?", "portfolio_update_position"),
  ("Mind jotting down that HAL's order book crossed 1 lakh cr?", "write_note"),
  ("Is it alright if you get rid of my SBIN position?", "portfolio_delete_position"),
  ("You'd be able to trim my LT holding to 5 shares?", "portfolio_update_position"),
 ],
 "SAME FRESH PHRASINGS WITHOUT THE TRAILING '?' (isolates the cue)": [
  ("Any chance you could get rid of my TCS position", "portfolio_delete_position"),
  ("Mind noting that INFY cut its guidance", "write_note"),
  ("Think you could scrap my WIPRO lot", "portfolio_delete_position"),
  ("Do you mind dropping ITC from my holdings", "portfolio_delete_position"),
 ],
}
CONTROLS = ["Is RELIANCE up today?", "How is my portfolio doing?", "what is P/E?", "Can you explain what a P/E ratio is?", "Any chance RELIANCE is up today?"]
async def main():
    for g, cases in GROUPS.items():
        print("\n##", g)
        for pr, need in cases:
            t = await tools(pr)
            ic = planner.classify_intent(pr)
            print("KEEP " if need in t else "STRIP", "|", pr, "| need", need, "| intent", ic.intent, ic.signals, "| n_tools", len(t))
    print("\n## CONTROLS (real reads must strip data writes)")
    for pr in CONTROLS:
        t = await tools(pr)
        print("control", "STRIPS" if not (t & _DATA_WRITES) else "KEEPS " + str(sorted(t & _DATA_WRITES)), "|", pr, "| n_tools", len(t))
asyncio.run(main())
