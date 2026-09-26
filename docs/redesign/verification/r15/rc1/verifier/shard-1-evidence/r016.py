import asyncio, sys, time
sys.path.insert(0,'tests')
from app import create_app
create_app()
from services import agent_tools
from services.research.iter import run_heavy_research
from services.budget_guard import BudgetGuard
from test_research_iter import FakeLLM
q=sys.argv[1]
t=time.time()
brief=asyncio.run(run_heavy_research(q, angles=2, region="IN", tool_call=agent_tools.invoke_tool, llm_call=FakeLLM(reflect="complete"), budget=BudgetGuard(max_steps=6)))
print('elapsed',round(time.time()-t,1))
if isinstance(brief,dict): print("DICT",str(brief)[:1500]); sys.exit()
src=getattr(brief,'sources',[])
print('n sources',len(src))
for s in src: print(' ', s.domain, s.url[:110], s.published_at)
print('floor-shaped (bse/nse attachments):', sum(1 for s in src if 'bseindia' in s.url or 'nsearchives' in s.url or 'nseindia' in s.url))
print('DICT', str(brief)[:1500]) if isinstance(brief,dict) else None
