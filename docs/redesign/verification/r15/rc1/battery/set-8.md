# batch-3/W4-research-depth (rc1-battery-1, candidate 4c6dfe8c)

Note: RESEARCH-007 actually closed in batch-13, RESEARCH-016 in batch-6, RESEARCH-020/024 in
batch-7, RESEARCH-005 in batch-4 per the register's `closure_evidence` (batch-3's own
VERDICTS.md left RESEARCH-005 NOT certified and doesn't mention the others at all) —
evidence below cites the entry's real closing batch.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-005 | grep committed test file | `test_research_synthesis_timeout.py:109` `test_synthesis_timeout_with_web_sources_is_stated_not_called_thin`, `:123` `test_synthesis_timeout_reaches_the_execution_record` present at HEAD unchanged — the entry's own certification says this half is "pinned by the committed stub test", not live (the live half needs the LLM call timeout force-reduced to 3s, a code change, not a black-box repro) | ci_pinned |
| R15-RESEARCH-007 | in-process `domain_tier(url)` over the original 4 + 10 fresh URLs | `medium.com`/`wordpress.com`/`investors.com` → 3, `reuters.com` → 2 (unchanged); `ir.tata.co.in`/`investors.xero.co.nz`/`ir.sony.co.jp`/`investor.vale.com.br`/`ir.nvidia.com`/`investors.infosys.com`/`ir.tesla.com` → 1; `ir.repl.co`/`investors.co.nz`/`ir.vercel.app` → 3 — all match the certified table exactly | holds |
| R15-RESEARCH-011 | `GET /disclosures/shareholding?symbol=SIL` live | 20 quarterly patterns, source NSE, `split_source: null` on every row (BSE lane is a no-op under the still-live BSE 403 block — exactly the fail-safe "never fabricated" behaviour the merge function documents) | holds |
| R15-RESEARCH-016 | grep `services/research/iter.py:378-391` | The fix's guard is unconditional: `if floor_rows: _record_web(...)` fires whenever floor rows exist, regardless of whether they were pre-seeded or pulled in this call — comment "ALWAYS cite the floor rows, pre-seeded or pulled here" — byte-identical to the certified shape. The full live 300+s ULTRA re-run (`b6v_ultra.py floor` mode) was not repeated this shard given the stall-watchdog/cost budget; static confirmation only | holds |
| R15-RESEARCH-020 | in-process `_web_search({'query':..,'num_results':3})`; `GET /search/searxng/status`; grep `num_results` threading in `web_search.py:137-226` | `num_results`/`numResults` threads unchanged through every dispatch path (grep). Live calls returned 0 rows both at n=3 and n=6 — `/search/searxng/status` confirms `state: degraded`, `reason: "brave: Suspended...; duckduckgo: CAPTCHA; startpage: Suspended: CAPTCHA"`, the SAME upstream block prior batches (10, and the earlier battery shard-1 run) already recorded from this IP/session. Mechanism confirmed by grep; live row-count comparison blocked by this recorded outage | blocked_env |
| R15-RESEARCH-024 | in-process `searxng._map_results({'results':[{...,'publishedDate':'2026-07-17T10:05:00'}]})` | `SearchResult(published_at='2026-07-17T10:05:00', ...)` — publishedDate → published_at mapping intact | holds |
| R15-RESEARCH-031 | node one-liner from the register's own repro: single-line `research:begin` regex against a multi-line query | `false` (unmatched) — same as the register's own repro; entry is `status: open`, never fixed, so this is the expected still-open state, not a regression | holds |

COVERAGE: 7/7 ids raw; no raw: none.
