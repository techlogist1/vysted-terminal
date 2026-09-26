import json,sys
sys.path.insert(0,'.')
from services import bse_provider as b
S=sys.argv[1]
d=json.load(open(S+'/resolver_masters/bse_instruments.json'))['instruments']
rows=[r for r in d if r[3] in ('Z','XT','X') and r[1]!='DAL'][-25:]
for code,sym,name,grp,isin,st in rows:
    try:
        q=b._fetch_scrip_header(sym,code)
        print(sym,code,grp,q.timestamp if q else None, q.change_percent if q else None, flush=True)
    except Exception as e:
        print(sym,code,'ERR',e, flush=True)
