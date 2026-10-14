import inspect
from fastapi.testclient import TestClient
from unittest.mock import patch
from app import create_app
from services import provider_registry as pr
from services.errors import ProviderError
c = TestClient(create_app())
names = ['get_income_statement','get_balance_sheet','get_analyst_rating','get_cash_flow','get_fundamentals','get_quote','get_history']
def boom(name, kind):
    msg = 'yfinance: Too Many Requests. Rate limited. Try after a while.'
    if inspect.iscoroutinefunction(getattr(pr, name)):
        async def f(*a, **k): raise ProviderError(msg, kind=kind)
    else:
        def f(*a, **k): raise ProviderError(msg, kind=kind)
    return f
for kind, exp in [('rate_limited',429),('not_found',404),('network',503),(None,502)]:
    out = []
    ps = [patch.object(pr, n, boom(n, kind)) for n in names]
    for p in ps: p.start()
    for path in ['/fundamentals/RELIANCE.NS','/fundamentals/TCS.NS/income','/fundamentals/TCS.NS/balance','/fundamentals/TCS.NS/cashflow','/fundamentals/TCS.NS/ratings','/quotes/AAPL','/history/AAPL']:
        r = c.get(path); j = r.json() if r.headers.get('content-type','').startswith('application/json') else {}
        out.append((path.split('/')[-1], r.status_code, j.get('code') if isinstance(j, dict) else None, 'RAW' if 'Too Many' in r.text else ''))
    for p in ps: p.stop()
    print(kind, 'expect', exp, out)
