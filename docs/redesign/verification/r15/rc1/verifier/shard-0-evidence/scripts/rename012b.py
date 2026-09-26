import asyncio, sys, json
sys.path.insert(0,'.')
from services import nse_symbol_change as n, symbol_resolver as sr
m=asyncio.run(n.fetch_latest()); print('live map rows', len(m or {}), flush=True)
n.set_active_map_for_tests(m or {})
S=sys.argv[1]
bse=json.load(open(S+'/resolver_masters/bse_instruments.json'))['instruments']
nse=json.load(open(S+'/resolver_masters/nse_instruments.json'))['instruments']
nse_syms={ (r[0] if isinstance(r,list) else r.get('symbol')) for r in nse}
bse_by={r[1]:r for r in bse}
tot=0; bse_only=0
for old in sorted(m or {}):
    res=sr.resolve(old,'IN'); b=res.best
    if b is None or b.rename is None: continue
    tot+=1
    src=bse_by.get(old)
    flag=''
    if src and old not in nse_syms:
        bse_only+=1
        if src[4]!=b.isin: flag='ISIN-MISMATCH'
    if flag or tot<=5: print(flag or 'ok', old, '->', b.symbol, b.exchange, b.isin, 'bse_isin=', src[4] if src else None, b.name, flush=True)
print('renamed total', tot, 'bse-only renamed', bse_only, flush=True)
