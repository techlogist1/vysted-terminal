# seat-stranger transcript

Seat: a stranger, NO keys, NO Docker, CLEAN profile (empty data dir + seeded keystore guard). Own sidecar from source on :52215, data dir `/tmp/claude-501/r15-seat-stranger/data`. Model: claude-fable-5-1. Date 2026-09-19.

## Pass 1 — first-run state (clean profile)

### GET /system/ollama/status
status 200, 2.10s, 90 bytes
```
{"running":true,"endpoint":"http://127.0.0.1:11434","models":["qwen2.5:7b","llama3.1:8b"]}
```

### GET /search/status
status 200, 0.97s, 430 bytes
```
{"tier":"t1_keyless","available":true,"engines":[{"id":"ddg","label":"DuckDuckGo","state":"closed","cooldown_remaining_s":0.0,"min_interval_s":3.0,"detail":"DuckDuckGo available"},{"id":"brave","label":"Brave","state":"closed","cooldown_remaining_s":0.0,"min_interval_s":2.0,"detail":"Brave available"},{"id":"mojeek","label":"Mojeek","state":"closed","cooldown_remaining_s":0.0,"min_interval_s":2.0,"detail":"Mojeek available"}]}
```

### GET /search/searxng/status
status 200, 4.19s, 296 bytes
```
{"state":"not_installed_docker","detail":"docker CLI found but the daemon is not running — start Docker/OrbStack","reason":null,"port":null,"url":null,"container":null,"container_name":"vysted-searxng","image":"searxng/searxng","docker":{"cli_present":true,"daemon_running":false,"runtime":null}}
```

### GET /llm/providers
status 200, 1.65s, 1584 bytes
```
[{"id":"anthropic","label":"Anthropic","requires_key":true,"default_base_url":null,"default_model":"claude-opus-4-8","known_models":["claude-opus-4-8","claude-sonnet-4-6","claude-haiku-4-5"]},{"id":"openai","label":"OpenAI","requires_key":true,"default_base_url":null,"default_model":"gpt-4.1-mini","known_models":["gpt-4.1","gpt-4.1-mini","o4-mini"]},{"id":"gemini","label":"Google Gemini","requires_key":true,"default_base_url":null,"default_model":"gemini-2.5-pro","known_models":["gemini-2.5-pro","gemini-2.5-flash"]},{"id":"groq","label":"Groq","requires_key":true,"default_base_url":null,"default_model":"llama-3.3-70b-versatile","known_models":["llama-3.3-70b-versatile","llama-3.1-8b-instant"]},{"id":"ollama","label":"Ollama (local)","requires_key":false,"default_base_url":"http://127.0.0.1:11434","default_model":"qwen2.5:7b","known_models":["qwen2.5:7b","llama3.1:8b"]},{"id":"deepseek","label":"DeepSeek","requires_key":true,"default_base_url":"https://api.deepseek.com","default_model":"deepseek-chat","known_models":["deepseek-chat","deepseek-reasoner"]},{"id":"xai","label":"xAI","requires_key":true,"default_base_url":"https://api.x.ai/v1","default_model":"grok-4","known_models":["g…[trunc]
```

### GET /system/provider-health
status 200, 0.78s, 152 bytes
```
{"yahoo":{"open":true,"cooldown_remaining":12.814250730967615,"consecutive_throttles":0.0,"consecutive_opens":1,"opens_total":1,"throttles_total":19.0}}
```

### GET /mcp/status
status 200, 1.47s, 78 bytes
```
{"ready":true,"toolCount":36,"endpoint":"/mcp","protocolVersion":"2025-06-18"}
```

### GET /openbb-mcp/status
status 200, 0.51s, 98 bytes
```
{"available":false,"provider":"openbb-mcp","endpoint":null,"lastToolCallOk":null,"lastError":null}
```

### GET /sec/status
status 200, 0.71s, 101 bytes
```
{"available":false,"provider":"sec-edgar-mcp","endpoint":null,"lastToolCallOk":null,"lastError":null}
```

### GET /safety/disclaimer-status
status 200, 0.88s, 18 bytes
```
{"sessionAcks":[]}
```

### GET /workspace
status 200, 1.88s, 2 bytes
```
[]
```

### GET /brokers
status 200, 0.68s, 14 bytes
```
{"brokers":[]}
```

### GET /system/local-model-recommendation
status 200, 3.38s, 1466 bytes
```
{"device":{"ramBytes":17179869184,"ramGib":16.0,"gpuBudgetBytes":11338713661,"gpuBudgetGib":10.6,"totalCores":8,"perfCores":6,"isAppleSilicon":true,"arch":"arm64","chip":"Apple M1 Pro","osName":"macOS","osVersion":"26.3","reserveBytes":4294967296},"candidates":[{"name":"qwen3:8b","verdict":"green","gpuFitRatio":0.74,"ramFitRatio":0.739,"demandBytes":8392827537,"demandGib":7.8,"weightsBytes":4919999999,"kvBytes":2399085714,"ctxMax":12288,"reason":"fits with headroom (7.8 GiB of 10.6 GiB GPU budget) — enable locally.","throughputNote":"","signals":[]},{"name":"qwen2.5-coder:7b","verdict":"green","gpuFitRatio":0.693,"ramFitRatio":0.707,"demandBytes":7857284681,"demandGib":7.3,"weightsBytes":4560000000,"kvBytes":2223542857,"ctxMax":14336,"reason":"fits with headroom (7.3 GiB of 10.6 GiB GPU budget) — enable locally.","throughputNote":"","signals":[]},{"name":"llama3.1:8b","verdict":"green","gpuFitRatio":0.724,"ramFitRatio":0.728,"demandBytes":8214313252,"demandGib":7.7,"weightsBytes":4800000000,"kvBytes":2340571428,"ctxMax":12288,"reason":"fits with headroom (7.7 GiB of 10.6 GiB GPU budget) — enable locally.","throughputNote":"","signals":[]}],"recommended":{"name":"qwen3:8b","verdict"…[trunc]
```

## Pass 1 — resolve/autocomplete (what a stranger types)

### GET /resolve/autocomplete?q=zomato&region=IN&limit=6
status 200, 1.42s, 48 bytes
```
{"query":"zomato","region":"IN","candidates":[]}
```

### GET /resolve/autocomplete?q=tata%20power&region=IN&limit=6
status 200, 0.46s, 274 bytes
```
{"query":"tata power","region":"IN","candidates":[{"symbol":"TATAPOWER","name":"Tata Power Company Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"TATAPOWER.NS","confidence":0.9,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=irctc&region=IN&limit=6
status 200, 0.89s, 290 bytes
```
{"query":"irctc","region":"IN","candidates":[{"symbol":"IRCTC","name":"Indian Railway Catering And Tourism Corporation Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"IRCTC.NS","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=paytm&region=IN&limit=6
status 200, 0.86s, 264 bytes
```
{"query":"paytm","region":"IN","candidates":[{"symbol":"PAYTM","name":"One 97 Communications Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"PAYTM.NS","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=nykaa&region=IN&limit=6
status 200, 0.68s, 266 bytes
```
{"query":"nykaa","region":"IN","candidates":[{"symbol":"NYKAA","name":"FSN E-Commerce Ventures Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"NYKAA.NS","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=lic&region=IN&limit=6
status 200, 0.36s, 1344 bytes
```
{"query":"lic","region":"IN","candidates":[{"symbol":"LICHSGFIN","name":"LIC Housing Finance Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"LICHSGFIN.NS","confidence":0.95,"isin":null,"bse_code":null,"industry":null,"former_name":null},{"symbol":"LICI","name":"Life Insurance Corporation Of India","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"LICI.NS","confidence":0.95,"isin":null,"bse_code":null,"industry":null,"former_name":null},{"symbol":"LICMFGOLD","name":"LICMF LICGoldETF","exchange":"NSE","region":"IN","asset_class":"etf","yahoo_symbol":"LICMFGOLD.NS","confidence":0.95,"isin":null,"bse_code":null,"industry":null,"former_name":null},{"symbol":"LICNETFGSC","name":"LICNAMC-LICNMFET","exchange":"NSE","region":"IN","asset_class":"etf","yahoo_symbol":"LICNETFGSC.NS","confidence":0.95,"isin":null,"bse_code":null,"industry":null,"form…[trunc]
```

### GET /resolve/autocomplete?q=yes%20bank&region=IN&limit=6
status 200, 1.04s, 258 bytes
```
{"query":"yes bank","region":"IN","candidates":[{"symbol":"YESBANK","name":"Yes Bank Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"YESBANK.NS","confidence":0.9,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=suzl&region=IN&limit=6
status 200, 0.36s, 258 bytes
```
{"query":"suzl","region":"IN","candidates":[{"symbol":"SUZLON","name":"Suzlon Energy Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"SUZLON.NS","confidence":0.95,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=jio%20fin&region=IN&limit=6
status 200, 1.20s, 269 bytes
```
{"query":"jio fin","region":"IN","candidates":[{"symbol":"JIOFIN","name":"Jio Financial Services Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"JIOFIN.NS","confidence":0.9,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=adani%20green&region=IN&limit=6
status 200, 0.63s, 277 bytes
```
{"query":"adani green","region":"IN","candidates":[{"symbol":"ADANIGREEN","name":"Adani Green Energy Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"ADANIGREEN.NS","confidence":0.9,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=hal&region=IN&limit=6
status 200, 1.24s, 1313 bytes
```
{"query":"hal","region":"IN","candidates":[{"symbol":"HAL","name":"Hindustan Aeronautics Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"HAL.NS","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"former_name":null},{"symbol":"HAL","name":"HALLIBURTON CO","exchange":"US","region":"US","asset_class":"equity","yahoo_symbol":"HAL","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"former_name":null},{"symbol":"HALDER","name":"Halder Venture Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"HALDER.NS","confidence":0.95,"isin":null,"bse_code":null,"industry":null,"former_name":null},{"symbol":"HALDYNGL","name":"Haldyn Glass Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"HALDYNGL.NS","confidence":0.95,"isin":null,"bse_code":null,"industry":null,"former_name":null},{"symbol":"HALEOSL…[trunc]
```

### GET /resolve/autocomplete?q=vedanta&region=IN&limit=6
status 200, 0.73s, 468 bytes
```
{"query":"vedanta","region":"IN","candidates":[{"symbol":"VEDANTASSET","name":"Vedant Asset Ltd","exchange":"BSE","region":"IN","asset_class":"equity","yahoo_symbol":"VEDANTASSET.BO","confidence":0.95,"isin":null,"bse_code":null,"industry":null,"former_name":null},{"symbol":"VEDL","name":"Vedanta Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"VEDL.NS","confidence":0.9,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=eternal&region=IN&limit=6
status 200, 0.93s, 256 bytes
```
{"query":"eternal","region":"IN","candidates":[{"symbol":"ETERNAL","name":"ETERNAL LIMITED","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"ETERNAL.NS","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=bajaj%20finanse&region=IN&limit=6
status 200, 0.93s, 55 bytes
```
{"query":"bajaj finanse","region":"IN","candidates":[]}
```

### GET /resolve/autocomplete?q=indigo&region=IN&limit=6
status 200, 0.90s, 1111 bytes
```
{"query":"indigo","region":"IN","candidates":[{"symbol":"INDIGO","name":"InterGlobe Aviation Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"INDIGO.NS","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"former_name":null},{"symbol":"INDIGOPNTS","name":"Indigo Paints Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"INDIGOPNTS.NS","confidence":0.95…[trunc]
```

### GET /resolve/autocomplete?q=dmart&region=IN&limit=6
status 200, 0.80s, 260 bytes
```
{"query":"dmart","region":"IN","candidates":[{"symbol":"DMART","name":"Avenue Supermarts Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"DMART.NS","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=mamaearth&region=IN&limit=6
status 200, 0.70s, 51 bytes
```
{"query":"mamaearth","region":"IN","candidates":[]}
```

### GET /resolve/autocomplete?q=policybazaar&region=IN&limit=6
status 200, 0.56s, 54 bytes
```
{"query":"policybazaar","region":"IN","candidates":[]}
```

### GET /resolve/autocomplete?q=swiggy&region=IN&limit=6
status 200, 1.06s, 252 bytes
```
{"query":"swiggy","region":"IN","candidates":[{"symbol":"SWIGGY","name":"Swiggy Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"SWIGGY.NS","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=tata%20capital&region=IN&limit=6
status 200, 0.84s, 266 bytes
```
{"query":"tata capital","region":"IN","candidates":[{"symbol":"TATACAP","name":"Tata Capital Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"TATACAP.NS","confidence":0.9,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=lg%20electronics&region=IN&limit=6
status 200, 0.71s, 278 bytes
```
{"query":"lg electronics","region":"IN","candidates":[{"symbol":"LGEINDIA","name":"LG Electronics India Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"LGEINDIA.NS","confidence":0.9,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=groww&region=IN&limit=6
status 200, 1.99s, 1344 bytes
```
{"query":"groww","region":"IN","candidates":[{"symbol":"GROWW","name":"Billionbrains Garage Ventures Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"GROWW.NS","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"former_name":null},{"symbol":"GROWWCAPM","name":"GROWWAMC - GROWWCAPM","exchange":"NSE","region":"IN","asset_class":"etf","yahoo_symbol":"GROWWCAPM.NS","confidence":0.9…[trunc]
```

### GET /resolve/autocomplete?q=meesho&region=IN&limit=6
status 200, 1.42s, 252 bytes
```
{"query":"meesho","region":"IN","candidates":[{"symbol":"MEESHO","name":"Meesho Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"MEESHO.NS","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=lenskart&region=IN&limit=6
status 200, 0.87s, 270 bytes
```
{"query":"lenskart","region":"IN","candidates":[{"symbol":"LENSKART","name":"Lenskart Solutions Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"LENSKART.NS","confidence":1.0,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=hdb%20financial&region=IN&limit=6
status 200, 0.82s, 273 bytes
```
{"query":"hdb financial","region":"IN","candidates":[{"symbol":"HDBFS","name":"HDB Financial Services Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"HDBFS.NS","confidence":0.9,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

### GET /resolve/autocomplete?q=urban%20company&region=IN&limit=6
status 200, 0.76s, 268 bytes
```
{"query":"urban company","region":"IN","candidates":[{"symbol":"URBANCO","name":"Urban Company Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"URBANCO.NS","confidence":0.9,"isin":null,"bse_code":null,"industry":null,"former_name":null}]}
```

## Pass 1 (resumed after usage wall) — /resolve, what a stranger types

### GET /resolve?q=zomato&region=IN
status 200, 2.27s, 148 bytes
```
{"ok":false,"query":"zomato","region":"IN","message":"No instrument matched 'zomato'.","resolved":null,"needs_disambiguation":false,"candidates":[]}
```

### GET /resolve?q=Tata%20Power&region=IN
status 200, 2.44s, 1256 bytes
```
{"ok":true,"query":"Tata Power","region":"IN","resolved":{"symbol":"TATAPOWER","name":"Tata Power Company Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"TATAPOWER.NS","confidence":1.0,"isin":"INE245A01021","bse_code":"500400","industry":"Power / Integrated Power Utilities","former_name":null},"needs_disambiguation":false,"candidates":[{"symbol":"TATAPOWER","name":"Tata Power Company Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"TATAPOWER.NS","confidence":1.0,"isin":"INE245A01021","bse_code":"500400","industry":"Power / Integrated Power Utilities","former_name":null},{"symbol":"SPOWF","name":"Strata Power Corp","exchange":"US","…[trunc]
```

### GET /resolve?q=mamaearth&region=IN
status 200, 2.89s, 154 bytes
```
{"ok":false,"query":"mamaearth","region":"IN","message":"No instrument matched 'mamaearth'.","resolved":null,"needs_disambiguation":false,"candidates":[]}
```

### GET /resolve?q=policybazaar
status 200, 13.47s, 160 bytes
```
{"ok":false,"query":"policybazaar","region":"IN","message":"No instrument matched 'policybazaar'.","resolved":null,"needs_disambiguation":false,"candidates":[]}
```

### GET /resolve?q=bajaj%20finanse&region=IN
status 200, 0.77s, 1130 bytes
```
{"ok":true,"query":"bajaj finanse","region":"IN","resolved":null,"needs_disambiguation":true,"candidates":[{"symbol":"BAJFINANCE","name":"Bajaj Finance Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"BAJFINANCE.NS","confidence":0.7059,"isin":"INE296A01032","bse_code":"500034","industry":"Financial Services / Non Banking Financial Company (NBFC)","former_name":null},{"symbol":"BANASFN","name":"Banas Finance Ltd","exchange":"BSE","region":"IN","asset_class":"equity","yahoo_symbol":"BANASFN.BO","confidence":0.6667,"isin":"INE521L01030","bse_code":"509053","industry":null,"former_name":null},{"symbol":"BAJAJFINSV","name":"Bajaj Finserv Limited","exchange":"NSE","re…[trunc]
```

### GET /resolve?q=irctc
status 200, 0.51s, 1007 bytes
```
{"ok":true,"query":"irctc","region":"IN","resolved":{"symbol":"IRCTC","name":"Indian Railway Catering And Tourism Corporation Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"IRCTC.NS","confidence":1.0,"isin":"INE335Y01020","bse_code":"542830","industry":"Consumer Services / Tour, Travel Related Services","former_name":null},"needs_disambiguation":false,"candidates":[{"symbol":"IRCTC","name":"Indian Railway Catering And Tourism Corporation Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"IRCTC.NS","confidence":1.0,"isin":"INE335Y01020","bse_code":"542830","industry":"Consumer Services / Tour, Travel Related Services","former_name":n…[trunc]
```

### GET /resolve?q=apple
status 200, 1.53s, 1343 bytes
```
{"ok":true,"query":"apple","region":"IN","resolved":null,"needs_disambiguation":true,"candidates":[{"symbol":"AAPL","name":"Apple Inc.","exchange":"US","region":"US","asset_class":"equity","yahoo_symbol":"AAPL","confidence":0.97,"isin":null,"bse_code":null,"industry":null,"former_name":null},{"symbol":"APLE","name":"Apple Hospitality REIT, Inc.","exchange":"US","region":"US","asset_class":"equity","yahoo_symbol":"APLE","confidence":0.97,"isin":null,"bse_code":null,"industry":null,"former_name":null},{"symbol":"AAPI","name":"Apple iSports Group, Inc.","exchange":"US","region":"US","asset_class":"equity","yahoo_symbol":"AAPI","confidence":0.97,"isin":null,"bse_code":null,"industry":null,"forme…[trunc]
```

### GET /resolve?q=
status 200, 0.10s, 146 bytes
```
{"ok":false,"query":"","region":"IN","message":"Empty query — nothing to resolve.","resolved":null,"needs_disambiguation":false,"candidates":[]}
```

### GET /resolve?q=asdfqwerzz&region=IN
status 200, 2.81s, 156 bytes
```
{"ok":false,"query":"asdfqwerzz","region":"IN","message":"No instrument matched 'asdfqwerzz'.","resolved":null,"needs_disambiguation":false,"candidates":[]}
```
