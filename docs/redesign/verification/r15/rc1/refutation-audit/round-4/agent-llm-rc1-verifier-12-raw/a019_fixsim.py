import asyncio, re, sys
sys.path.insert(0, "tests")
import test_b3_runtime_intent_gate as T
from services import agent_runtime, planner
async def tools(prompt):
    agent_runtime.reload()
    p = T._CaptureProvider()
    agent_runtime.get_provider = lambda *_a, **_k: p
    async for _ in agent_runtime.invoke_agent(agent_id="copilot", prompt=prompt, api_key="k", provider="ollama", mode="agent"):
        pass
    return set(p.tool_ids)
# Candidate fix: the bare trailing '?' is a read cue ONLY on an interrogative opener
# (closed set) that is not itself a request frame; the existing agent-request alternatives stay.
_OPENERS = r"(?:is|are|am|was|were|do|does|did|has|have|had|how|what|which|who|whom|whose|when|where|why)"
_NOT_A_READ_QUESTION = re.compile(
    rf"^(?!\s*{_OPENERS}\b(?!\s+(?:you\b|you'd\b|if\b|it\s+(?:be\s+)?(?:ok|okay|alright|all right|possible|fine)\b)))"
    r"|\b(?:can|could|would|will) you\b|\bplease\b"
)
KEEP = list(T._PHRASINGS) + list(T._AGENT_REQUEST_KEEP_PHRASINGS) + [
  ("Can you log 10 TCS at 3400 in my portfolio?", "portfolio_add_position"),
  ("Can you record that I hold 20 ITC at 410?", "portfolio_add_position"),
  ("Could you enter 5 HDFCBANK at 1600 into my portfolio?", "portfolio_add_position"),
  ("Could you ditch my ITC shares?", "portfolio_delete_position"),
  ("Could you jot down that HDFC looks cheap?", "write_note"),
  ("Any chance you could get rid of my TCS position?", "portfolio_delete_position"),
  ("Mind noting that INFY cut its guidance?", "write_note"),
  ("What if you noted that BEL order book is 75k cr?", "write_note"),
  ("Think you could scrap my WIPRO lot?", "portfolio_delete_position"),
  ("Do you mind dropping ITC from my holdings?", "portfolio_delete_position"),
  ("Would it be okay to bump my TCS quantity to 40?", "portfolio_update_position"),
  ("Mind jotting down that HAL's order book crossed 1 lakh cr?", "write_note"),
  ("Is it alright if you get rid of my SBIN position?", "portfolio_delete_position"),
  ("You'd be able to trim my LT holding to 5 shares?", "portfolio_update_position"),
]
STRIP = ["what is P/E?", "Can you explain what a P/E ratio is?", "Is RELIANCE up today?", "How is my portfolio doing?",
         "Is TCS cheaper than INFY?", "Are markets open today?", "Did RELIANCE beat estimates?", "Has HDFC Bank raised its dividend?",
         "Which sector led today?", "Where is NIFTY at right now?", "Do I hold any TCS?", "Does ITC pay a dividend?", "Who runs Infosys?"]
async def run(label):
    bad_keep = [(p, n) for p, n in KEEP if n not in await tools(p)]
    bad_strip = [p for p in STRIP if not (await tools(p)).isdisjoint(T._DATA_WRITES)]
    print(f"[{label}] keep-cases {len(KEEP)}: stripped {len(bad_keep)} -> {[p for p, _ in bad_keep]}")
    print(f"[{label}] strip-controls {len(STRIP)}: kept writes {len(bad_strip)} -> {bad_strip}")
async def main():
    await run("HEAD")
    planner._AGENT_REQUEST_CUE = _NOT_A_READ_QUESTION
    await run("SIM interrogative-opener rule")
asyncio.run(main())
