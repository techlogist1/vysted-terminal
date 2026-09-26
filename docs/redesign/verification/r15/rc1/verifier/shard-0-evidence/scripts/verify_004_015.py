import asyncio, sys, inspect
sys.path.insert(0,'.')
from services.research import verify as v
from services.research.models import ResearchBrief
from services.budget_guard import BudgetGuard
print('ResearchBrief sig', str(inspect.signature(ResearchBrief))[:300])
def brief():
    return ResearchBrief(query='q',symbol='KAYNES',mode='ultra',markdown='body') if 'steps' in inspect.signature(ResearchBrief).parameters else ResearchBrief(symbol='KAYNES', markdown='body')
async def run(claim_lines, search_urls, native, label):
    async def llm(msgs, *a, **k):
        sysmsg=msgs[0]['content']
        if 'numeric claim' in sysmsg and 'verify ONE' not in sysmsg: return claim_lines
        return 'AGREE - sources support it'
    async def tool(name,args):
        return {'ok':True,'results':[{'url':u,'title':'t','snippet':'s'} for u in search_urls]}
    async def nat(prompt): return native
    b=brief(); g=BudgetGuard(max_wall_seconds=120) if 'max_wall_seconds' in inspect.signature(BudgetGuard).parameters else BudgetGuard()
    try: g.start()
    except Exception: pass
    out=await v.cross_check(b, tool_call=tool, llm_call=llm, budget=g, native_search=(nat if native is not None else None))
    print('=== ',label)
    print([c['claim'] for c in out.structured['cross_check']['claims']])
    print(out.markdown.split('## Cross-check')[1].strip()[:900])
    print('STEP:', out.steps[-1].__dict__ if hasattr(out.steps[-1],'__dict__') else out.steps[-1])
async def main():
    # 004 literal: model lists claims starting with figures
    await run("40.5% revenue growth\n-0.4% earnings growth\n67.13953 P/E\n", ['https://a.com/x'], None, '004 literal (1 domain -> unverified)')
    # 004 fresh: ordered/bulleted markers + signed/decimal heads not in the pin
    await run("1. 12.75x EV/EBITDA\n- -3.2% operating margin\n2) .85 beta\n* 1,234.5 crore revenue\n3.5% dividend yield\n", ['https://a.com/x','https://b.org/y'], None, '004 fresh (2 domains, agree)')
    # 015 literal: one domain via both lanes (native cites same domain)
    await run("40.5% revenue growth\n", ['https://www.moneycontrol.com/a'], {'ok':True,'text':'40.5% per moneycontrol','citations':[{'url':'https://moneycontrol.com/b'}]}, '015 literal one domain both lanes')
    # 015 fresh: one registrable domain via two subdomains + native citing a third subdomain
    await run("-0.4% earnings growth\n", ['https://www.nseindia.com/a','https://nsearchives.nseindia.com/b'], {'ok':True,'text':'x','citations':[{'url':'https://archives.nseindia.com/c'}]}, '015 fresh subdomains of one registrable domain')
asyncio.run(main())
