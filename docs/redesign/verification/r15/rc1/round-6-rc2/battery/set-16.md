# batch-5/W2-resolver-market-data (set-16), shard rc1-battery-11, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-097 | in-process _live_lookup, yf.Search stubbed, monotonic time-travel | empty result re-queried after 301 s (calls 1->2, finds NEWLISTCO); non-empty stays cached | holds |
| R15-DATA-057 | GET /resolve?q=Dhanalakshmi+Bank | DHANBANK first (0.792, former_name "The Dhanalakshmi Bank Limited"); no DHAN-RE | holds |
| R15-LEAD-011 | GET /history/%5ENSEI, %5EBSESN (region IN); _yahoo_symbol | 246 bars each, provider yfinance; _yahoo_symbol('^NSEI')='^NSEI' (first attempt 429 from Yahoo throttle, retry ok) | holds |
| R15-DATA-064 | GET /history/{SPY,AAPL,RELIANCE.NS}?timeframe=30m; indicators SPY 30m | 273/273/260 bars, reason None; indicators 200 (was 502) | holds |
| R15-DATA-063 | GET /history/DAL and /indicators/DAL?indicators=rsi (empty series) | both 200 empty (indicators payload empty, no 502) | holds |
| R15-DATA-015 | GET /fundamentals/ELCIDIN field_meta | 52w high 137,000 and low 101,110 both status flagged vs exchange range 87,003-144,500 | holds |
| R15-DATA-037 | GET /history/BTC/USDT?range=1mo/1y/5y&asset_class=crypto; ETH/USDT 1h 1mo | 30 / 365 / 1826 bars (ccxt:binance); ETH 1h 720 | holds |
| R15-LEAD-009 | GET /earnings/INFY/estimates and /fundamentals/INFY/ratings, region IN/US/IN | INFY.NS INR eps 19.67 vs INFY USD eps 0.205; ratings buy vs hold; code keys use resolved listing | holds |
| R15-DATA-072 | grep record_success + in-process trip then get_history (yf.Ticker stubbed; Yahoo throttling live) | breaker open=True after trip, open=False after one successful get_history; record_success present in history/income/balance/cashflow/analyst | holds |

COVERAGE: 9/9 ids raw; no raw: none
