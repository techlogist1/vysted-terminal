import copy, datetime, sys
from services import nse_provider as n, provider_registry as pr, bse_provider as b
from services.errors import ProviderError
today=datetime.date.today()
real=n._get_json(n._HISTORICAL_PATH, {"symbol":"TCS","series":'["EQ"]',"from":(today-datetime.timedelta(days=20)).strftime("%d-%m-%Y"),"to":today.strftime("%d-%m-%Y")}, n._quote_referer("TCS"))
print('real rows', len(real['data']))
orig=n._get_json
for key in ("CH_OPENING_PRICE","CH_TRADE_HIGH_PRICE","CH_TRADE_LOW_PRICE","CH_TOT_TRADED_QTY"):
    drift=copy.deepcopy(real)
    for r in drift['data']: r[key+"_V2"]=r.pop(key)
    n._get_json=lambda *a, _d=drift, **k: _d
    try:
        n.get_history("TCS.NS","1d","1mo"); print(key,'nse_direct SERVED (bad)')
    except ProviderError as e: print(key,'nse_direct ProviderError:',str(e)[:90])
    try:
        s=pr.get_history("TCS.NS","1d","1mo")
        s=s if not isinstance(s,tuple) else s[0]
        flat=sum(1 for x in s.bars if x.open==x.high==x.low==x.close); z=sum(1 for x in s.bars if not x.volume)
        print('   registry ->',s.provider,len(s.bars),'bars flat',flat,'zerovol',z)
    except Exception as e: print('   registry err',type(e).__name__,str(e)[:120])
n._get_json=orig
# BSE bhavcopy fresh: rename volume column
hdr="TradDt,FinInstrmId,TckrSymb,OpnPric,HghPric,LwPric,ClsPric,TtlTradgVolume\n2026-09-25,519421,KSE,140,145,139,142.5,1200\n"
try: print('bse renamed vol ->', b.parse_bhavcopy(hdr).to_dict('records'))
except ProviderError as e: print('bse renamed vol -> ProviderError', e)
