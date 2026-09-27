import asyncio
from datetime import datetime, timedelta, UTC, date
from pathlib import Path
import pandas as pd
from services import yfinance_provider, correctness_gate, dividend_history
from services.research import range_check
from models.fundamentals import FieldMeta
from models.market import OHLCVBar
import tests.test_correctness_gate as T

fx = Path("tests/fixtures/bse/dal_bo_yahoo_history_20260923.csv")
frame = pd.read_csv(fx, index_col="Date"); frame.index = pd.to_datetime(frame.index, utc=True)
class _T:
    def __init__(self, s): pass
    def history(self, period, interval): return frame
yfinance_provider.yf.Ticker = _T
s = yfinance_provider.get_history("DAL.BO", "1d", "5y")
print("literal history bars", len(frame), "->", len(s.bars), "zero-vol", sum(1 for b in s.bars if not b.volume), "min low", min(b.low for b in s.bars[-5:]))

async def nodiv(sym): return None
dividend_history.get_dividend_ttm = nodiv
def run(label, hist, asof):
    async def vh(sym): return hist
    range_check.get_venue_history = vh
    correctness_gate.reset_witness_cache_for_tests()
    f = T._fund(symbol="DAL.BO", fifty_two_week_high=49.88, fifty_two_week_low=46.58, ratio_price=49.88,
        field_meta={"ratio_price": FieldMeta(status="ok", provider="yfinance", as_of=asof)})
    out = asyncio.run(correctness_gate.apply_witnesses(f))
    print(label, out.fifty_two_week_high, out.fifty_two_week_low, {k:(out.field_meta[k].status, out.field_meta[k].reason) for k in ("fifty_two_week_high","fifty_two_week_low") if k in out.field_meta})
run("literal DAL (last trade 2025-03-12, no bars)", None, "2025-03-12T03:58:51+00:00")
d = datetime.now(UTC) - timedelta(days=200)
bar = OHLCVBar(timestamp=d, open=49.88, high=49.88, low=49.88, close=49.88, volume=10)
run("fresh: one BSE trade 200d ago @49.88, provider low 46.58", ([bar], ["BSE"]), d.isoformat())
run("fresh: no venue bars, ratio as_of 200d ago", None, d.isoformat())
