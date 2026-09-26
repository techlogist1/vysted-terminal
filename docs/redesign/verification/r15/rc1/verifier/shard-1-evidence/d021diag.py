import logging; logging.basicConfig(level=logging.DEBUG)
for n in ('httpx','httpcore','urllib3','asyncio','filelock','peewee','charset_normalizer'): logging.getLogger(n).setLevel(logging.WARNING)
from services import symbol_resolver as sr, corporate_disclosures as cd
for s in ('SIL','DIXON'):
    print(s,'dual',sr.dual_listed_bse_code(s))
    try:
        ps=cd._bse_shareholding(s); print(s,'bse patterns',[(str(p.quarter_end),p.fii_percent,p.institutions_percent) for p in ps])
    except Exception as e: print(s,'bse err',type(e).__name__,e)
