import sys; sys.path.insert(0, sys.argv[1])
from services import provider_health as ph, yfinance_provider as yp
def trip():
    ph.reset_for_tests()
    for _ in range(3): ph.record_rate_limited(ph.YAHOO)
    return ph.is_open(ph.YAHOO)
for name, fn in [("get_history MSFT 1d", lambda: yp.get_history("MSFT","1d")),
                 ("get_cash_flow NVDA", lambda: yp.get_cash_flow("NVDA")),
                 ("get_balance_sheet INFY.NS", lambda: yp.get_balance_sheet("INFY.NS")),
                 ("get_income_statement ASML quarterly", lambda: yp.get_income_statement("ASML","quarterly")),
                 ("get_analyst_rating TSM", lambda: yp.get_analyst_rating("TSM"))]:
    before = trip()
    try:
        r = fn(); ok = "ok"
    except Exception as e:
        ok = f"raised {type(e).__name__}: {str(e)[:100]}"
    print(f"{name}: open_before={before} call={ok} open_after={ph.is_open(ph.YAHOO)} status={ph.status(ph.YAHOO)}")
