| lane | key | url | d38b5d1a | 1fddb2b1 | flags | body excerpt |
|---|---|---|---|---|---|---|
| malformed | spaces/quote | `/quotes/%20%20%20` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | spaces/quotes_batch | `/quotes?symbols=%20%20%20` | 200 | 200 | same | `[]` |
| malformed | spaces/history | `/history/%20%20%20?timeframe=1d&range=1mo` | 200 | 200 | same | `{"symbol":"   ","timeframe":"1d","bars":[],"provider":"none","freshness":null,"reason":"un` |
| malformed | spaces/fundamentals | `/fundamentals/%20%20%20` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | spaces/indicators | `/indicators/%20%20%20?indicators=rsi` | 200 | 200 | same | `{"symbol":"   ","timeframe":"1d","provider":"none","indicators":[],"volume_profile":null,"` |
| malformed | spaces/resolve | `/resolve?q=%20%20%20` | 200 | 200 | same | `{"ok":false,"query":"   ","region":"IN","message":"Empty query — nothing to resolve.","res` |
| malformed | spaces/autocomplete | `/resolve/autocomplete?q=%20%20%20` | 200 | 200 | same | `{"query":"   ","region":"IN","candidates":[]}` |
| malformed | spaces/earnings_hist | `/earnings/%20%20%20/history` | 200 | 200 | same | `{"symbol":".NS","history":[],"as_of":"2026-10-03T19:02:21.607589Z"}` |
| malformed | spaces/news | `/news?symbols=%20%20%20&limit=3` | 200 | 200 | same | `[{"id":"f649df1df85232ff","title":"India Summons Pakistan Diplomat Over 'Continued' Cross-` |
| malformed | dollars/quote | `/quotes/%24%24%24` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | dollars/quotes_batch | `/quotes?symbols=%24%24%24` | 200 | 200 | same | `[]` |
| malformed | dollars/history | `/history/%24%24%24?timeframe=1d&range=1mo` | 200 | 200 | same | `{"symbol":"$$$","timeframe":"1d","bars":[],"provider":"none","freshness":null,"reason":"un` |
| malformed | dollars/fundamentals | `/fundamentals/%24%24%24` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | dollars/indicators | `/indicators/%24%24%24?indicators=rsi` | 200 | 200 | same | `{"symbol":"$$$","timeframe":"1d","provider":"none","indicators":[],"volume_profile":null,"` |
| malformed | dollars/resolve | `/resolve?q=%24%24%24` | 200 | 200 | same | `{"ok":false,"query":"$$$","region":"IN","message":"No instrument matched '$$$'.","resolved` |
| malformed | dollars/autocomplete | `/resolve/autocomplete?q=%24%24%24` | 200 | 200 | same | `{"query":"$$$","region":"IN","candidates":[]}` |
| malformed | dollars/earnings_hist | `/earnings/%24%24%24/history` | 200 | 200 | same | `{"symbol":"$$$.NS","history":[],"as_of":"2026-10-03T19:02:30.746545Z"}` |
| malformed | dollars/news | `/news?symbols=%24%24%24&limit=3` | 200 | 200 | same | `[]` |
| malformed | len300/quote | `/quotes/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | len300/quotes_batch | `/quotes?symbols=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` | 200 | 200 | same | `[]` |
| malformed | len300/history | `/history/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` | 200 | 200 | same | `{"symbol":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` |
| malformed | len300/fundamentals | `/fundamentals/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | len300/indicators | `/indicators/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` | 200 | 200 | same | `{"symbol":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` |
| malformed | len300/resolve | `/resolve?q=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` | 200 | 200 | same | `{"ok":false,"query":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` |
| malformed | len300/autocomplete | `/resolve/autocomplete?q=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` | 200 | 200 | same | `{"query":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` |
| malformed | len300/earnings_hist | `/earnings/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` | 200 | 200 | same | `{"symbol":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` |
| malformed | len300/news | `/news?symbols=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` | 200 | 200 | same | `[]` |
| malformed | sql/quote | `/quotes/RELIANCE%27%3B%20DROP%20TABLE%20positions%3B--` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | sql/quotes_batch | `/quotes?symbols=RELIANCE%27%3B%20DROP%20TABLE%20positions%3B--` | 200 | 200 | same | `[]` |
| malformed | sql/history | `/history/RELIANCE%27%3B%20DROP%20TABLE%20positions%3B--?timeframe=1d&r` | 200 | 200 | same | `{"symbol":"RELIANCE'; DROP TABLE positions;--","timeframe":"1d","bars":[],"provider":"none` |
| malformed | sql/fundamentals | `/fundamentals/RELIANCE%27%3B%20DROP%20TABLE%20positions%3B--` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | sql/indicators | `/indicators/RELIANCE%27%3B%20DROP%20TABLE%20positions%3B--?indicators=` | 200 | 200 | same | `{"symbol":"RELIANCE'; DROP TABLE positions;--","timeframe":"1d","provider":"none","indicat` |
| malformed | sql/resolve | `/resolve?q=RELIANCE%27%3B%20DROP%20TABLE%20positions%3B--` | 200 | 200 | same | `{"ok":false,"query":"RELIANCE'; DROP TABLE positions;--","region":"IN","message":"No instr` |
| malformed | sql/autocomplete | `/resolve/autocomplete?q=RELIANCE%27%3B%20DROP%20TABLE%20positions%3B--` | 200 | 200 | same | `{"query":"RELIANCE'; DROP TABLE positions;--","region":"IN","candidates":[]}` |
| malformed | sql/earnings_hist | `/earnings/RELIANCE%27%3B%20DROP%20TABLE%20positions%3B--/history` | 200 | 200 | same | `{"symbol":"RELIANCE'; DROP TABLE POSITIONS;--.NS","history":[],"as_of":"2026-10-03T19:02:5` |
| malformed | sql/news | `/news?symbols=RELIANCE%27%3B%20DROP%20TABLE%20positions%3B--&limit=3` | 200 | 200 | same | `[]` |
| malformed | html/quote | `/quotes/%3Cscript%3Ealert%281%29%3C%2Fscript%3E` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | html/quotes_batch | `/quotes?symbols=%3Cscript%3Ealert%281%29%3C/script%3E` | 200 | 200 | same | `[]` |
| malformed | html/history | `/history/%3Cscript%3Ealert%281%29%3C%2Fscript%3E?timeframe=1d&range=1m` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | html/fundamentals | `/fundamentals/%3Cscript%3Ealert%281%29%3C%2Fscript%3E` | 404 | 404 | untyped-404 | `{"detail":"Not Found"}` |
| malformed | html/indicators | `/indicators/%3Cscript%3Ealert%281%29%3C%2Fscript%3E?indicators=rsi` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | html/resolve | `/resolve?q=%3Cscript%3Ealert%281%29%3C/script%3E` | 200 | 200 | same | `{"ok":false,"query":"<script>alert(1)</script>","region":"IN","message":"No instrument mat` |
| malformed | html/autocomplete | `/resolve/autocomplete?q=%3Cscript%3Ealert%281%29%3C/script%3E` | 200 | 200 | same | `{"query":"<script>alert(1)</script>","region":"IN","candidates":[]}` |
| malformed | html/earnings_hist | `/earnings/%3Cscript%3Ealert%281%29%3C%2Fscript%3E/history` | 404 | 404 | untyped-404 | `{"detail":"Not Found"}` |
| malformed | html/news | `/news?symbols=%3Cscript%3Ealert%281%29%3C/script%3E&limit=3` | 200 | 200 | same | `[]` |
| malformed | unicode_hi/quote | `/quotes/%E0%A4%B0%E0%A4%BF%E0%A4%B2%E0%A4%BE%E0%A4%AF%E0%A4%82%E0%A4%B` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | unicode_hi/quotes_batch | `/quotes?symbols=%E0%A4%B0%E0%A4%BF%E0%A4%B2%E0%A4%BE%E0%A4%AF%E0%A4%82` | 200 | 200 | same | `[]` |
| malformed | unicode_hi/history | `/history/%E0%A4%B0%E0%A4%BF%E0%A4%B2%E0%A4%BE%E0%A4%AF%E0%A4%82%E0%A4%` | 200 | 200 | same | `{"symbol":"रिलायंस","timeframe":"1d","bars":[],"provider":"none","freshness":null,"reason"` |
| malformed | unicode_hi/fundamentals | `/fundamentals/%E0%A4%B0%E0%A4%BF%E0%A4%B2%E0%A4%BE%E0%A4%AF%E0%A4%82%E` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | unicode_hi/indicators | `/indicators/%E0%A4%B0%E0%A4%BF%E0%A4%B2%E0%A4%BE%E0%A4%AF%E0%A4%82%E0%` | 200 | 200 | same | `{"symbol":"रिलायंस","timeframe":"1d","provider":"none","indicators":[],"volume_profile":nu` |
| malformed | unicode_hi/resolve | `/resolve?q=%E0%A4%B0%E0%A4%BF%E0%A4%B2%E0%A4%BE%E0%A4%AF%E0%A4%82%E0%A` | 200 | 200 | same | `{"ok":false,"query":"रिलायंस","region":"IN","message":"No instrument matched 'रिलायंस'.","` |
| malformed | unicode_hi/autocomplete | `/resolve/autocomplete?q=%E0%A4%B0%E0%A4%BF%E0%A4%B2%E0%A4%BE%E0%A4%AF%` | 200 | 200 | same | `{"query":"रिलायंस","region":"IN","candidates":[]}` |
| malformed | unicode_hi/earnings_hist | `/earnings/%E0%A4%B0%E0%A4%BF%E0%A4%B2%E0%A4%BE%E0%A4%AF%E0%A4%82%E0%A4` | 200 | 200 | same | `{"symbol":"रिलायंस.NS","history":[],"as_of":"2026-10-03T19:03:10.200832Z"}` |
| malformed | unicode_hi/news | `/news?symbols=%E0%A4%B0%E0%A4%BF%E0%A4%B2%E0%A4%BE%E0%A4%AF%E0%A4%82%E` | 200 | 200 | same | `[]` |
| malformed | emoji/quote | `/quotes/%F0%9F%9A%80MOON` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | emoji/quotes_batch | `/quotes?symbols=%F0%9F%9A%80MOON` | 200 | 200 | same | `[]` |
| malformed | emoji/history | `/history/%F0%9F%9A%80MOON?timeframe=1d&range=1mo` | 200 | 200 | same | `{"symbol":"🚀MOON","timeframe":"1d","bars":[],"provider":"none","freshness":null,"reason":"` |
| malformed | emoji/fundamentals | `/fundamentals/%F0%9F%9A%80MOON` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | emoji/indicators | `/indicators/%F0%9F%9A%80MOON?indicators=rsi` | 200 | 200 | same | `{"symbol":"🚀MOON","timeframe":"1d","provider":"none","indicators":[],"volume_profile":null` |
| malformed | emoji/resolve | `/resolve?q=%F0%9F%9A%80MOON` | 200 | 200 | same | `{"ok":true,"query":"🚀MOON","region":"IN","resolved":null,"needs_disambiguation":true,"cand` |
| malformed | emoji/autocomplete | `/resolve/autocomplete?q=%F0%9F%9A%80MOON` | 200 | 200 | same | `{"query":"🚀MOON","region":"IN","candidates":[]}` |
| malformed | emoji/earnings_hist | `/earnings/%F0%9F%9A%80MOON/history` | 200 | 200 | same | `{"symbol":"🚀MOON.NS","history":[],"as_of":"2026-10-03T19:03:20.977243Z"}` |
| malformed | emoji/news | `/news?symbols=%F0%9F%9A%80MOON&limit=3` | 200 | 200 | same | `[]` |
| malformed | double_suffix/quote | `/quotes/RELIANCE.NS.NS` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | double_suffix/quotes_batch | `/quotes?symbols=RELIANCE.NS.NS` | 200 | 200 | same | `[]` |
| malformed | double_suffix/history | `/history/RELIANCE.NS.NS?timeframe=1d&range=1mo` | 200 | 200 | same | `{"symbol":"RELIANCE.NS.NS","timeframe":"1d","bars":[],"provider":"none","freshness":null,"` |
| malformed | double_suffix/fundamentals | `/fundamentals/RELIANCE.NS.NS` | 404 | 200 | status-diff | `{"symbol":"RELIANCE.NS.NS","name":null,"sector":null,"industry":null,"sector_source":null,` |
| malformed | double_suffix/indicators | `/indicators/RELIANCE.NS.NS?indicators=rsi` | 200 | 200 | same | `{"symbol":"RELIANCE.NS.NS","timeframe":"1d","provider":"none","indicators":[],"volume_prof` |
| malformed | double_suffix/resolve | `/resolve?q=RELIANCE.NS.NS` | 200 | 200 | same | `{"ok":true,"query":"RELIANCE.NS.NS","region":"IN","resolved":null,"needs_disambiguation":t` |
| malformed | double_suffix/autocomplete | `/resolve/autocomplete?q=RELIANCE.NS.NS` | 200 | 200 | same | `{"query":"RELIANCE.NS.NS","region":"IN","candidates":[]}` |
| malformed | double_suffix/earnings_hist | `/earnings/RELIANCE.NS.NS/history` | 200 | 200 | same | `{"symbol":"RELIANCE.NS.NS","history":[],"as_of":"2026-10-03T19:04:13.593386Z"}` |
| malformed | double_suffix/news | `/news?symbols=RELIANCE.NS.NS&limit=3` | 200 | 200 | same | `[]` |
| malformed | path_trav/quote | `/quotes/..%2F..%2Fetc%2Fpasswd` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | path_trav/quotes_batch | `/quotes?symbols=../../etc/passwd` | 200 | 200 | same | `[]` |
| malformed | path_trav/history | `/history/..%2F..%2Fetc%2Fpasswd?timeframe=1d&range=1mo` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | path_trav/fundamentals | `/fundamentals/..%2F..%2Fetc%2Fpasswd` | 404 | 404 | untyped-404 | `{"detail":"Not Found"}` |
| malformed | path_trav/indicators | `/indicators/..%2F..%2Fetc%2Fpasswd?indicators=rsi` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| malformed | path_trav/resolve | `/resolve?q=../../etc/passwd` | 200 | 200 | same | `{"ok":false,"query":"../../etc/passwd","region":"IN","message":"No instrument matched '../` |
| malformed | path_trav/autocomplete | `/resolve/autocomplete?q=../../etc/passwd` | 200 | 200 | same | `{"query":"../../etc/passwd","region":"IN","candidates":[]}` |
| malformed | path_trav/earnings_hist | `/earnings/..%2F..%2Fetc%2Fpasswd/history` | 404 | 404 | untyped-404 | `{"detail":"Not Found"}` |
| malformed | path_trav/news | `/news?symbols=../../etc/passwd&limit=3` | 200 | 200 | same | `[]` |
| census | 037:watchlist-default-equities | `/quotes?symbols=SPY%2CQQQ%2CNVDA%2CAAPL&asset_class=equity` | 200 | 200 | same | `[{"symbol":"SPY","price":769.6400146484375,"change":4.910014648437482,"change_percent":0.6` |
| census | 040:watchlist-25-mixed | `/quotes?symbols=RELIANCE.NS%2CTCS.NS%2CINFY.NS%2CHDFCBANK.NS%2CICICIBA` | 200 | 200 | same | `[{"symbol":"RELIANCE.NS","price":1167.7,"change":-19.299999999999955,"change_percent":-1.6` |
| census | 041:autocomplete-reliance | `/resolve/autocomplete?q=reliance` | 200 | 200 | same | `{"query":"reliance","region":"IN","candidates":[{"symbol":"RELIANCE","name":"Reliance Indu` |
| census | 042:autocomplete-kaynes | `/resolve/autocomplete?q=kaynes` | 200 | 200 | same | `{"query":"kaynes","region":"IN","candidates":[{"symbol":"KAYNES","name":"Kaynes Technology` |
| census | 043:autocomplete-tata motors | `/resolve/autocomplete?q=tata+motors` | 200 | 200 | same | `{"query":"tata motors","region":"IN","candidates":[{"symbol":"TMCV","name":"Tata Motors Li` |
| census | 044:autocomplete-hdfc | `/resolve/autocomplete?q=hdfc` | 200 | 200 | same | `{"query":"hdfc","region":"IN","candidates":[{"symbol":"HDFCBANK","name":"HDFC Bank Limited` |
| census | 045:watchlist-3-NS-warm | `/quotes?symbols=RELIANCE.NS%2CTCS.NS%2CINFY.NS&asset_class=equity` | 200 | 200 | same | `[{"symbol":"RELIANCE.NS","price":1167.7,"change":-19.299999999999955,"change_percent":-1.6` |
| census | 046:watchlist-3-bare-warm | `/quotes?symbols=RELIANCE%2CTCS%2CINFY&asset_class=equity` | 200 | 200 | same | `[{"symbol":"RELIANCE","price":1167.7,"change":-19.299999999999955,"change_percent":-1.6259` |
| census | 047:watchlist-1-BO | `/quotes?symbols=RELIANCE.BO&asset_class=equity` | 200 | 200 | same | `[{"symbol":"RELIANCE.BO","price":1166.0,"change":-21.5,"change_percent":-1.810526315789473` |
| census | 048:autocomplete-reliance.ns | `/resolve/autocomplete?q=reliance.ns` | 200 | 200 | same | `{"query":"reliance.ns","region":"IN","candidates":[{"symbol":"RELIANCE","name":"Reliance I` |
| census | 049:autocomplete-RELIANCE.NS-upper | `/resolve/autocomplete?q=RELIANCE.NS` | 200 | 200 | same | `{"query":"RELIANCE.NS","region":"IN","candidates":[{"symbol":"RELIANCE","name":"Reliance I` |
| census | 050:watchlist-20-good-warm | `/quotes?symbols=RELIANCE%2CTCS%2CINFY%2CHDFCBANK%2CICICIBANK%2CSBIN%2C` | 200 | 200 | same | `[{"symbol":"RELIANCE","price":1167.7,"change":-19.299999999999955,"change_percent":-1.6259` |
| census | 051:watchlist-junk-only-NOTAREALSYM | `/quotes?symbols=NOTAREALSYM&asset_class=equity` | 200 | 200 | same | `[]` |
| census | 052:watchlist-junk-only-532540 | `/quotes?symbols=532540&asset_class=equity` | 200 | 200 | same | `[{"symbol":"532540","price":2079.3,"change":29.300000000000182,"change_percent":1.42926829` |
| census | 053:watchlist-3good+junk | `/quotes?symbols=RELIANCE%2CTCS%2CINFY%2CNOTAREALSYM2&asset_class=equit` | 200 | 200 | same | `[{"symbol":"RELIANCE","price":1167.7,"change":-19.299999999999955,"change_percent":-1.6259` |
| census | 060:contended-watchlist-20 | `/quotes?symbols=RELIANCE%2CTCS%2CINFY%2CHDFCBANK%2CICICIBANK%2CSBIN%2C` | 200 | 200 | same | `[{"symbol":"RELIANCE","price":1167.7,"change":-19.299999999999955,"change_percent":-1.6259` |
| census | 061:news-default-watchlist | `/news?symbols=SPY%2CQQQ%2CBTC%2FUSDT%2CETH%2FUSDT%2CNVDA%2CAAPL&limit=` | 200 | 200 | same | `[{"id":"0dc86d85e9263af9","title":"Michael Saylor Says Strategy's STRC Is Now Steadier Tha` |
| census | 062:news-IN-watchlist | `/news?symbols=RELIANCE%2CTCS%2CKAYNES%2CBDL&limit=50` | 200 | 200 | same | `[{"id":"44b155ef4690f268","title":"‘Pashu seva bhi prabhu seva hai’: Reliance Executive Di` |
| census | 063:news-empty-symbols | `/news?limit=20` | 200 | 200 | same | `[{"id":"f649df1df85232ff","title":"India Summons Pakistan Diplomat Over 'Continued' Cross-` |
| census | 064:news-limit-500 | `/news?symbols=AAPL&limit=500` | 422 | 422 | same | `{"detail":[{"type":"less_than_equal","loc":["query","limit"],"msg":"Input should be less t` |
| census | 065:news-limit-0 | `/news?symbols=AAPL&limit=0` | 422 | 422 | same | `{"detail":[{"type":"greater_than_equal","loc":["query","limit"],"msg":"Input should be gre` |
| census | 066:eo-fund-RELIANCE | `/fundamentals/RELIANCE` | 200 | 200 | same | `{"symbol":"RELIANCE.NS","name":"Reliance Industries Limited","sector":"Energy","industry":` |
| census | 067:eo-income-RELIANCE | `/fundamentals/RELIANCE/income` | 200 | 200 | same | `{"symbol":"RELIANCE.NS","periods":["2026-03-31","2025-03-31","2024-03-31","2023-03-31","20` |
| census | 068:eo-balance-RELIANCE | `/fundamentals/RELIANCE/balance` | 200 | 200 | same | `{"symbol":"RELIANCE.NS","periods":["2026-03-31","2025-03-31","2024-03-31","2023-03-31","20` |
| census | 069:eo-cashflow-RELIANCE | `/fundamentals/RELIANCE/cashflow` | 200 | 200 | same | `{"symbol":"RELIANCE.NS","periods":["2026-03-31","2025-03-31","2024-03-31","2023-03-31","20` |
| census | 071:eo-fund-KAYNES | `/fundamentals/KAYNES` | 200 | 200 | same | `{"symbol":"KAYNES.NS","name":"Kaynes Technology India Limited","sector":"Industrials","ind` |
| census | 072:eo-income-KAYNES | `/fundamentals/KAYNES/income` | 200 | 200 | same | `{"symbol":"KAYNES.NS","periods":["2026-03-31","2025-03-31","2024-03-31","2023-03-31","2022` |
| census | 073:eo-balance-KAYNES | `/fundamentals/KAYNES/balance` | 200 | 200 | same | `{"symbol":"KAYNES.NS","periods":["2026-03-31","2025-03-31","2024-03-31","2023-03-31","2022` |
| census | 074:eo-cashflow-KAYNES | `/fundamentals/KAYNES/cashflow` | 200 | 200 | same | `{"symbol":"KAYNES.NS","periods":["2026-03-31","2025-03-31","2024-03-31","2023-03-31","2022` |
| census | 076:eo-fund-AAPL | `/fundamentals/AAPL` | 200 | 200 | same | `{"symbol":"AAPL","name":"Apple Inc.","sector":"Technology","industry":"Consumer Electronic` |
| census | 077:eo-income-AAPL | `/fundamentals/AAPL/income` | 200 | 200 | same | `{"symbol":"AAPL","periods":["2025-09-30","2024-09-30","2023-09-30","2022-09-30"],"lines":[` |
| census | 078:eo-balance-AAPL | `/fundamentals/AAPL/balance` | 200 | 200 | same | `{"symbol":"AAPL","periods":["2025-09-30","2024-09-30","2023-09-30","2022-09-30"],"lines":[` |
| census | 079:eo-cashflow-AAPL | `/fundamentals/AAPL/cashflow` | 200 | 200 | same | `{"symbol":"AAPL","periods":["2025-09-30","2024-09-30","2023-09-30","2022-09-30"],"lines":[` |
| census | 083:eo-crypto-BTC-fund | `/fundamentals/BTC%2FUSDT` | 404 | 404 | untyped-404 | `{"detail":"Not Found"}` |
| census | 085:eo-junk-fund | `/fundamentals/NOTAREALSYM` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| census | 086:eo-junk-income | `/fundamentals/NOTAREALSYM/income` | 404 | 404 | same | `{"detail":"The data provider has no data for this symbol or series — check the symbol.","c` |
| census | 104:earn-estimates-RELIANCE | `/earnings/RELIANCE/estimates` | 200 | 200 | same | `{"symbol":"RELIANCE.NS","fiscal_period":null,"eps_estimate_mean":16.275,"eps_estimate_medi` |
| census | 107:earn-estimates-AAPL | `/earnings/AAPL/estimates` | 200 | 200 | same | `{"symbol":"AAPL","fiscal_period":null,"eps_estimate_mean":1.98236,"eps_estimate_median":nu` |
| census | 109:earn-estimates-INFY.NS | `/earnings/INFY.NS/estimates` | 200 | 200 | same | `{"symbol":"INFY.NS","fiscal_period":null,"eps_estimate_mean":19.63622,"eps_estimate_median` |
| census | 110:earn-estimates-INFY | `/earnings/INFY/estimates` | 200 | 200 | same | `{"symbol":"INFY.NS","fiscal_period":null,"eps_estimate_mean":19.63622,"eps_estimate_median` |

rows=121 flagged=6
