# rc1-vshard-1 log
- 2026-09-25 08:49:05 booted own sidecar :52601 from worktree 1d6511c (sh wrapper pid 97274, python 97277), data rc1-data-rc1-vshard-1
- 2026-09-25 09:05:59 vy.py refuses non-GET outside 52100-52399; used scratch inv.sh mirroring vy.py payload (ollama llama3.1:8b, no key, region IN, tier_a) against :52601.
- R007: original repro holds (medium/wordpress -> 3); variant investors.com (IBD news) + ir.<any host>/tumblr/github.io/blogspot.in -> TIER_PRIMARY, IBD owns [1] over Reuters.
- R008: keyless chain bounded (ddg rate-limited 0.2s, chain 3.9s; ddg-hang variant 7.0s; all-hang 12.0s); 2 llama runs returned results, no timeout.
- DATA-045: 12 redirect variants (loopback/metadata/nip.io/decimal/v6/v4-mapped/0.0.0.0/file/2-hop/pdf lane/curl_cffi lane) all blocked; canary never hit.
- R011: split BSE stamp survives into semantics basis + fundamentals gate flag.
- LEAD-002: warm 1.1-2.5s (5+3 symbols); cold ~15-17s but witness alone 1.1-1.8s.
- R013: RELIANCE nse+bse, TITANBIO/VALIANT bse, fake BSE-down nse.
- UI-090: AAPL@NSE hours eod; variant ^NSEI/^BSESN/VOD.L/bare IN ETF via yfinance -> US calendar -> 'live' after own exchange closed.
- DATA-026: quarterly route incl. DHANBANK 2026-06-30; financial_statements capability in default grants.
- 2026-09-25 09:17:42 AGENT-011: llama fumbled 3x (typo symbol / text call / stringified array); qwen2.5:7b local: run_custom_backtest -> synthetic open_panel(run_id) -> GET /backtest/runs/{id} 53 trades 752 equity pts; delegate run host_actions carries the auto open_panel.
- AGENT-020: llama called read_notes(RELIANCE) unprompted; variant non-focused DIXON note answered correctly. In-process: suffix scope mismatch -> false 'no note' (low finding 3).
- DATA-026: llama called financial_statements(DHANBANK.NS, income, quarterly) -> 6 quarters incl. 2026-06-30; net income matches screener.in (24.91 vs 25, 43.49 vs 43 ...).
- UI-090 live at 09:17 IST: AAPL eod (holds), ^NSEI live tick -> eod (variant).
- stopped own sidecar (killed sleep pid 97276; :52601 free) and canary http.server :52609.

# round 2 (gate round 2, candidate 81fbfe91)
- 2026-09-26 09:30:48 booted own sidecar :52601 from rc1-4c6dfe8-fix-int @81fbfe91 (sleep pid 89839, python 89840), data rc1-data-rc1-vshard-1-r2
- 2026-09-26 09:33:08 CODE-AGENT-018/020 reproduce (register status open, never certified); CODE-AGENT-016 holds (openrouter/xai/deepseek load, bogus rejected); RESEARCH-020 holds (3/1/12/25); RESEARCH-024 holds for web rows; adjacent: news-lane sources drop published_at + domain=feed label; web_search category never reaches SearXNG
- 2026-09-26 09:38:54 RESEARCH-016 holds: live run_heavy_research("Jonjua Overseas outlook") real tools -> 13 sources incl 5 bseindia floor rows. DATA-021 holds (no years-old split; SIL/DIXON splits all None) BUT adjacent: BSE SHP index 403 on plain httpx (curl_cffi 200) -> no FII/DII split for any name, BSE-only shareholding provider_error (ELCIDIN)
- 2026-09-26 09:41:03 DATA-024 holds (KOPRAN/SUZLON/YESBANK NSE, JONJUA/NAPEROL BSE-only). DATA-029 in-process mapping holds + news IN no Flanigan; live estimates Yahoo 429 (retry later). AGENT-010 loop lag 17ms w/ 1s stub, raising->ok:false; BUT yf.Search still has no explicit timeout (symbol_resolver.py:1574, default 30) -> fix_shape part unfixed
- 2026-09-26 09:44:10 LIFECYCLE-004 holds: live TCS historicalOR (fresh symbol) each O/H/L/V renamed -> nse_direct ProviderError, registry falls to nse (jugaad, real bars, 0 flat/0 zero-vol); BSE bhavcopy renamed vol col -> ProviderError. ollama lock busy (09:41/09:43)
- 2026-09-26 09:47:55 LIFECYCLE-006 holds: literal vy.py repro on :52152 (o3-deep-research) -> error research_step + named message; fresh perplexity/sonar-reasoning deep -> same; live catalog: all 6 static options present, 3 retired absent from options
- 2026-09-26 09:50:23 DATA-036 holds: /history 1y BSE-only JONJUA cold 0.45s warm 0.33s (244 bse bars); DAL 0.56s. DATA-016 holds: DAL 52w high/low withheld "no trades in 52 weeks (last trade 2025-03-12)", history 0 bars (no flat line); adjacent: DAL still ships 52w high/low dates 2025-09-25 status ok + 52w change 0.0 status ok
- 2026-09-26 09:51:42 UI-090: literal AAPL@NSE hrs IN -> eod (holds); ^NSEI/^NSEBANK/^CNXIT/^INDIAVIX live under IN+US; FRESH BHP.AX (ASX closed) and VOD.L (LSE closed) during US hours -> live (instrument_region defaults non-IN to US) -> not certified
- 2026-09-26 09:52:23 DATA-067 holds (/earnings/upcoming 60 events, 0 fiscal_period; no producer sets it). DATA-020 holds: live DIXON 36 NSE/4 BSE 0 residual pairs; TATASTEEL 2 residual pairs both the documented category-mismatch known limitation (Result vs Outcome of Board Meeting)
- 2026-09-26 09:54:48 AGENT-013 holds: live delegate run (copilot, llama3.1:8b, INFY research, under ollama lock) GET /runs/{id} answer 2784 chars untruncated + brief (sources/structured) persisted
- 2026-09-26 10:01:34 AGENT-016 fresh (researcher, provider=ollama) run ok on the local model in 47.7s; CODE-PLATFORM-014 holds (reloadPlugin plus tests); DATA-044 holds (criterion = formula, 853 matched, NULL rows itemized; price_to_book and dividend_yield also itemized); UI-006 holds (matched > result, monotonic sort before limit, header copy); UI-008 holds (2 fake keys -> invalid); UI-012 holds (streaming.ts extractSidecarDetail; adjacent: workflow.ts/screener.ts raw errors); DATA-029 estimates retry 200, INFY.NS INR EPS; adjacent: INR revenue labelled USD
- 2026-09-26 10:01:34 wrote findings/rc1-vshard-1.json (10) and verifier/shard-1.md (+ shard-1-evidence/); stopped own sidecar (killed sleep pid 89839; :52601 free, python 89840 gone); ollama lock absent
