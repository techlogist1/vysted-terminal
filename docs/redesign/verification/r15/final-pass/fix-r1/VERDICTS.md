# fix-r1 fresh verifier verdicts (R6)

Head `cac9d206759c2cd83d46778cc94a4dbd0b678429` (final-int worktree, read-only). Own sidecars: source :52887, :52888, :52890 and bundle binary :52889, each on its own scratch data dir; all stopped by recorded sleep pid.

Pins: frontend pin files 5/183 passed in scratch run (verify/frontend-pins.log); every pytest pin file present in fix-r1/ci-local.log run 2 EXIT=0 (pytest 3958 passed, vitest 2048 passed).

**Certified 26 / not certified 2 / adjudicated 0.**

## Not certified

### R15-FINAL-006
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- evidence: verify/f006-fe4-clean-replay.json, verify/f006-clean-52888-latency.txt, verify/f006-baseline-idle-52888.txt, verify/f006-single-latency-loaded.txt, verify/f006-fe3-replay.json
- verdict: NOT CERTIFIED (R7 count 1). The single-quote starvation half of the claim is not fixed. Fresh case: 100 cold NSE names (sym100b) mounted ALONE on an idle own sidecar :52888. Cold single quotes took 15.0-21.2 s while mounted (AXISBANK 21.2, MARUTI 19.9, SUNPHARMA 20.1, TITAN 20.4, ONGC 15.0). The same sidecar answered idle cold singles in 4.8-7.0 s (HDFCBANK, ICICIBANK, KOTAKBANK). Plan acceptance is under 5 s. On :52887 with a 120-name mount, HDFCBANK timed out at 40 s twice. The literal RELIANCE.NS answer under 5 s is a cache hit. Cause: nse_provider._Throttle is one global FIFO pacer at about 1.0-1.4 s per request. The 16-worker batch pool reserves its slots ahead of any single, so the new semaphore bounds the queue but does not isolate it. The batch also outlasts its own client budget: the 100-name batch aborted at 120 s with 0/100 priced, and the server finished at about 137 s. Parts that hold: one request in flight, backoff, no per-tick resend.

### R15-FINAL-005
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- evidence: verify/b.out (### /fundamentals/VOLERCAR), verify/a.out
- verdict: NOT CERTIFIED (R7 count 1). VOLERCAR, an SME listing named in the claim, still has no fundamentals and gives no reason. GET /fundamentals/VOLERCAR (IN) returns 200 with only ratio_price and revenue/earnings growth. revenue, net income, eps and pe_ratio are null with no field_meta reason, although NSE filed periods exist (growth is computed from them). YASHOPTICS is fixed: revenue 53.99 Cr, P/E 37.1, and statements carry the typed SME reason. SUMAX, QUALIANCE and GANESHIN give the typed not-covered reason.

## Certified

### R15-FINAL-001
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: jsdom harness fe.fr1v (real PortfolioPanel, own sidecar :52887): add INFY 20@1500 + fresh HAL under IN, switch region to US; fresh SAIL added under US, switch to IN; export CSV
- evidence: verify/fe-replay.json
- excerpt: INFY/HAL stay INR after the switch to US (quote requests carry X-Vysted-Region IN); SAIL stays US after the switch to IN; CSV currency column matches each listing

### R15-FINAL-007
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: fe2.fr1v: region IN, panel closed then open, holdings RELIANCE.NS TCS.NS AAPL MSFT BTC/USDT HAL SBIN.BO; captureTerminalState().portfolio
- evidence: verify/fe2-replay.json
- excerpt: closed: AAPL/MSFT currency null (never INR), BTC/USDT USDT, .NS/.BO INR; open: AAPL USD. Copilot tool-result turn not driven (vy.py refuses non-GET outside 52100-52399; F007-llama.stdout.txt)

### R15-FINAL-017
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: fe.fr1v: ZZZZNOTREAL beside resolved rows, fresh QQQQFAKE.NS and FAKECOINX/USDT
- evidence: verify/fe-replay.json
- excerpt: rows show 'no quote', no transport banner, unresolved symbols excluded from later 5 s ticks

### R15-FINAL-033
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: fe.fr1v through the add form: cost '   ', qty '0x10', '1e3', '0b11', '0o7', 'Infinity', '+5'; accept '0.5', ' 2500.5 '
- evidence: verify/fe-replay.json
- excerpt: all non-decimal inputs refused with a field error; plain decimals accepted

### R15-FINAL-016
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: fe2.fr1v: applyIntent(parseHostAction(arrange ...)) with unknown tokens, partial list, comma string, empty list
- evidence: verify/fe2-replay.json
- excerpt: failure names the unknown token(s); partial arrange notes the miss; comma string arranges; empty list fails

### R15-FINAL-030
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: fe2.fr1v: research/brief scope by company name: 'Cochin Shipyard', 'Tata Consultancy Services', 'infosys', unresolved name, ticker scopes
- evidence: verify/fe2-replay.json
- excerpt: COCHINSHIP / TCS / INFY resolved; unresolved keeps the literal with a note; ticker scopes unchanged

### R15-LEAD-077
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: fe2.fr1v: SEC filings panel focus MSFT, fresh NVDA, CIK 0000789019; captureTerminalState().focusedSymbol
- evidence: verify/fe2-replay.json
- excerpt: focusedSymbol MSFT / NVDA; a raw CIK passes through as-is (minor note, not part of the claim)

### R15-FINAL-003
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: curl -H 'X-Vysted-Region: IN' :52887/fundamentals/SUNRAJDI ; fresh /fundamentals/AMAL.BO
- evidence: verify/a.out
- excerpt: SUNRAJDI pe_ratio 54.09 derived on filed EPS with basis stated (no 141.1/155.5 left; screener.in 55.2); AMAL.BO P/E derived on filed EPS

### R15-FINAL-009
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: curl :52887/fundamentals/AMAL (IN); fresh in-process fill_market_cap_from_master on SUNRAJDI.BO, ZEAL.NS (other-company BSE row), ICON.NS with a served value
- evidence: verify/a.out, verify/f009-fresh.txt
- excerpt: AMAL market_cap 871.6 Cr derived 'ratio price x master share count (705 x 12,362,749 ...)' (screener.in 868 Cr); SUNRAJDI.BO derived with basis; ZEAL.NS refused (Zeal Aqua is another company); served value untouched

### R15-FINAL-024
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: curl :52887/fundamentals/AMAL, SUNRAJDI, ICON (IN); fresh in-process reconcile_ownership 0.00 vs 0.41 / 2.9 / 12.0, 10.0 vs 14.5
- evidence: verify/a.out, verify/b.out, verify/f024-fresh.txt
- excerpt: AMAL/SUNRAJDI/ICON institutions now status ok; 0 vs 0.41 and 0 vs 2.9 not flagged; 0 vs 12.0 and 10 vs 14.5 flagged with a true 'beyond 3pp' reason

### R15-FINAL-010
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: curl -H 'X-Vysted-Region: US' :52887/earnings/{SIFY,WIT,INFY,RDY,IBN,HDB,MMYT}/estimates
- evidence: verify/a.out, verify/b.out
- excerpt: SIFY revenue_currency null; WIT/INFY/RDY/IBN/HDB INR; MMYT USD

### R15-LEAD-071
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: in-process real earnings router + data_cache with a ticker stub raising YFRateLimitError on earnings_history / earnings_dates / info; GET history + surprises twice
- evidence: verify/lead071.txt
- excerpt: 429 rate_limited typed error, second call refetches upstream (2 raises), 0 cache rows, for every accessor and both routes

### R15-FINAL-002
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: curl :52887/resolve?q=GSTL, /disclosures/{results,corporate-actions,shareholding}?symbol=GSTL; fresh WSI, 21STCENMGM; master sweep of 2471 NSE/BSE pairs
- evidence: verify/a.out, verify/b.out, verify/f002-pairs.txt
- excerpt: GSTL needs disambiguation, NSE row carries no BSE ISIN, disclosures say 'BSE GSTL is a different company'; sweep flips only GSTL; true duals keep ISIN

### R15-FINAL-011
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: curl :52887/resolve/autocomplete?q= Zeal Aqua | Sanathnagar Enterprises | ZEAL.BO | SEL.BO; fresh Kalyani Cast | KALYANI.BO | Focus Business | FOCUS.BO
- evidence: verify/a.out, verify/b.out
- excerpt: each returns the right BSE company first; fresh names likewise

### R15-FINAL-004
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: in-process news relevance against real resolved targets: FOCUS, CLEAN, TRUST, TOTAL, BETA, OIL, IDEA; controls RELIANCE, ROUTE
- evidence: verify/f004-relevance.txt
- excerpt: common-word headlines dropped, company headlines kept; controls unchanged (live research run not driven: vy.py port range)

### R15-FINAL-027
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: curl :52887/news?limit=60 (IN)
- evidence: verify/a.out
- excerpt: 0 HTML entities in 60 items; 'F&O Talk', 'Bonus issues & stock split', fresh 'J&K' render correctly

### R15-LEAD-060
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: in-process services.research.verify._parse_verdict on 15 variants
- evidence: verify/lead060.txt
- excerpt: _UNVERIFIED_, __UNVERIFIED__, **_UNVERIFIED_**, ***UNVERIFIED***, `UNVERIFIED`, _Unverified_ -> unverified; __DISAGREE__, > _DISAGREE_ -> disagree; _AGREE_, __agree__ -> agree

### R15-FINAL-021
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: GET :52887/openapi.json vs docs/SIDECAR_API.md; Origin: http://evil.example probe; fresh /macro 422, /indicators 200
- evidence: verify/f021-check.txt, verify/openapi-52887.json
- excerpt: 0 of 111 live routes undocumented; documented origin rule matches the live 403

### R15-FINAL-022
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: grep -inE 'order|broker|paper|place' docs/redesign/R12_HAND_TESTING_GUIDE.md; fresh grep of current docs for order-placement walkthroughs
- evidence: verify/docs-checks.txt
- excerpt: 0 hits in the 9-line retired guide; fresh: the only current-doc hit is SAFETY_ARCHITECTURE.md section 10 History of what D81 removed

### R15-FINAL-023
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: read the release runbook; grep version in the five sources; git merge-base --is-ancestor 517da226 HEAD
- evidence: verify/docs-checks.txt
- excerpt: runbook states no merge step; all five sources 0.9.0; 517da226 not an ancestor

### R15-FINAL-037
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: step-by-step compare of the RELEASE_RUNBOOK section 3 verbatim block with package.json scripts.ci-local
- evidence: verify/docs-checks.txt
- excerpt: 15/15 &&-steps equal; no python -m pip or pnpm test left

### R15-FINAL-035
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: POST :52887/mcp/ tools/list (stateless JSON-RPC) vs docs/MCP_INTEGRATION.md; status sample
- evidence: verify/mcp-tools.raw, verify/f035-check.txt
- excerpt: all 39 live tools documented; sample reads 39 / 2025-11-25; the remaining 2025-06-18 matches lib.rs MCP_PROTOCOL_VERSION

### R15-FINAL-008
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: corrupt headers on all 7 stores, boot from source :52888; truncate all stores, boot the bundle binary :52889; hit every store route
- evidence: verify/f008-hdr-source.log, verify/f008-trunc-binary.log, verify/f008-trunc-routes.txt
- excerpt: every store quarantined byte-identical (.corrupt-<ts>, sha matches), boot healthy, every route 200

### R15-LIFECYCLE-024
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: boot.sh: v0.8.0-shape data_cache.db (user_version 0, cache table only, one stale row) beside user stores + workspaces, booted twice from source :52890; then meta build=0.8.9-prior (case b); plus no-data_cache dir (pm2) and clean profile (pm3)
- evidence: verify/l024-v080-shape-boots.txt, verify/l024-boots.txt
- excerpt: first boot: backups/unversioned-2026-10-03 (holds the stale row), cache cleared, meta build 0.9.0; second boot: no new backup; case b: backups/0.8.9-prior; pm2 backup once; pm3 no backup. Observation: a data_cache.db at user_version 1 with its meta table dropped (a shape no build writes) fails startup 'no such table: meta' (l024-artificial-shape-crash.txt), filed as a note, not this claim

### R15-FINAL-031
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: POST /workspace PLX twice, DELETE, POST C, corrupt file, GET; fresh desk_two 3 saves, DELETE, C1, C2, corrupt, GET
- evidence: verify/f031.txt
- excerpt: PLX: .bak gone after DELETE, GET 404 (never SECRET_B); desk_two: recovers FRESH_C1 from its own .bak, never the deleted content

### R15-FINAL-028
- sha: `cac9d206759c2cd83d46778cc94a4dbd0b678429`
- command: bundle binary --port 52887 (taken) and source main.py --port 52889 (taken), stdin held open by a pipe
- evidence: verify/f028-exit.txt, verify/f028-bin.log, verify/f028-src.log
- excerpt: Errno 48 address already in use; 'bin exit=1', 'src exit=1' (not 134, no SIGABRT)

## Observations (not verdicts)
- data_cache.db at user_version 1 with no meta table crashes startup ('no such table: meta', data_cache.py:146); no build writes that shape; low, for 0.9.1
- FINAL-007 copilot tool-result turn and FINAL-004 live research run not driven: scripts/r15/vy.py refuses non-GET outside ports 52100-52399; in-process and closed-panel snapshot evidence used
