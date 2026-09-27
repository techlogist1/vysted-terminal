import asyncio, dataclasses, sys
sys.path.insert(0, "tests")
import config
from models.llm import LLMUsage
from services import agent_tools
from services.agent_tools import deep_research
from services.llm import oneshot
from services.research import iter as iter_research
from services.research.depth import PROFILES
from services.search import extract
import test_research_metering as T
async def _no_visit(url, **_): return extract.VisitResult(None)
async def _snap(tool_call, symbol, **_): return {"price": {"ok": True, "provider": "test", "data": {"price": 181.2}}}
agent_tools.invoke_tool = T._fake_tool
iter_research.snapshot_structured = _snap
extract.visit_for_research = _no_visit
config.get_step_sink = lambda: None
def run(profile, provider, model, usage, rounds=2, wall=120):
    calls = []
    async def fake(p, m, k, messages, *, timeout=None):
        calls.append(str(messages[0].get("content",""))[:40]); return T._route(messages), usage
    oneshot.complete_with_usage = fake
    tok = config.set_request_llm_creds(provider, model, "sk-test")
    try:
        out = asyncio.run(deep_research._run_native("research NVDA", profile, rounds, wall))
    finally:
        config.reset_request_llm_creds(tok)
    xc = sum(1 for c in calls if c.startswith("List the most important NUMERIC"))
    print(f"{profile.depth} {provider}/{model}: ok={out.get('ok')} mode={out.get('mode')} calls={len(calls)} crosscheck_calls={xc} cost={out.get('cost')} note={out.get('note')!r}")
    return out
run(PROFILES["ultra"], "openrouter", "anthropic/claude-sonnet-4", LLMUsage(input_tokens=1500, output_tokens=400))
run(dataclasses.replace(PROFILES["ultra"], max_spend_usd=0.0001), "openrouter", "anthropic/claude-sonnet-4", LLMUsage(input_tokens=1500, output_tokens=400))
o = run(dataclasses.replace(PROFILES["ultra"], max_spend_usd=0.0001), "openrouter", "anthropic/claude-sonnet-4", LLMUsage(input_tokens=1500, output_tokens=400))
for s in o["steps"]: print("STEP", s.get("kind"), s.get("status"), s.get("detail")[:140])
print("MD", o["markdown"][:300].replace("\n"," | "))
