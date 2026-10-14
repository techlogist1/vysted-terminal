import asyncio, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-4-cand/sidecar")
import config
from services.agent_tools.deep_research import run_research_model_brief

FAKE_KEY = "sk-or-v1-R15CANARY-battery13-not-a-real-key"

steps = []
config.set_step_sink(lambda step: steps.append(step))

async def main():
    result = await run_research_model_brief("research Bharat Electronics", depth="normal", api_key=FAKE_KEY)
    print("result:", result)
    print("steps:", steps)
    assert result.get("ok") is False, f"FAIL: expected ok:false, got {result}"
    error_steps = [s for s in steps if getattr(s, "status", None) == "error" or (isinstance(s, dict) and s.get("status") == "error")]
    print("error_steps:", error_steps)
    assert error_steps, "FAIL: no error step reached the trace"
    print("PASS RESEARCH-010: a rejected OpenRouter key surfaces as an error step + ok:false, not a silent fabricated-source answer")

asyncio.run(main())
