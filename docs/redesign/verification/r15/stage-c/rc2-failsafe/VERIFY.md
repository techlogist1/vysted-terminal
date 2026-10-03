# rc2 fail-safe landing: fresh verification (5.14)

- Verifier: Opus 5.5 (claude-opus-5-5), judgement tier, fresh context. I wrote no product code. I did not consult the advisor.
- Candidate: `r15-rc2-int` @ `b796f6a9acc7fcd38ef0bcbc1c3b0c1c83fb4374`. Base for scope: `b7d37fd99336251624f15881d09a2944eec45b34`.
- Worktree: `scratchpad/fs-verify` (detached at the candidate; clean afterwards, and `vitest.config.ts` was restored after the ratchet rewrote it).
- Finished: 2026-10-03 23:15 IST.
- Gate rule: DECISIONS 6.1. Each entry is certified on its stated repro, which for both entries here is the CLASS. Anything found beyond the stated repro is listed as a candidate entry.

## Verdict

| Entry | Verdict |
|---|---|
| R15-LEAD-137 (high, attempt 2) | **CERTIFIED** |
| R15-LEAD-141 (high, attempt 1) | **CERTIFIED** |
| Overall | **CERTIFIED**: steps (1) to (4) hold, and (5a) and (5b) hold |

## (1) Scope and safety

```
$ git log --oneline b7d37fd9..b796f6a9
b796f6a9 merge: R15-LEAD-141 fail-safe fix
06e775d2 merge: R15-LEAD-137 fail-safe fix
469110d0 fix(research): 3-letter NSE word tickers need an anchor (R15-LEAD-141)
70150817 fix(fundamentals): SME P/E stays on the current share count through the gate's second overlay pass (R15-LEAD-137)

$ git diff --stat b7d37fd9 b796f6a9 -- . ':(exclude)docs'
 sidecar/services/correctness_gate.py               |   8 +-
 sidecar/services/research/relevance.py             |  18 ++--
 .../services/resolver_masters/english_words.txt.gz | Bin 731652 -> 734081 bytes
 sidecar/tests/test_final_data_fundamentals.py      |  82 +++++++++++++++++
 sidecar/tests/test_research_relevance.py           |  98 +++++++++++++++++++++
 5 files changed, 199 insertions(+), 7 deletions(-)

$ git diff --name-only b7d37fd9 b796f6a9 -- src types sidecar/services/agent_runtime.py sidecar/services/planner.py \
    sidecar/services/action_ledger.py sidecar/tests/test_no_trading_surface.py docs/SAFETY_ARCHITECTURE.md src-tauri \
    .github LICENSE COMMERCIAL_LICENSE.md CLAUDE.md
(empty)
```

Every changed file is in an entry's owned set:
- LEAD-137: `correctness_gate.py` and `test_final_data_fundamentals.py`. `provider_registry.py` was not touched.
- LEAD-141: `relevance.py`, the bundled word list (`english_words.txt.gz`, at the existing PyInstaller-shipped path) and `test_research_relevance.py`.

The safety surface is empty, so the result is **PASS**.

### LEAD-137 fix shape

At `correctness_gate.py:791`, `filings_only = f.provider == filed.venue or all(<provider sizes> is None)`. When the gate's second overlay pass meets the filings shell (`provider_registry._fundamentals_from_filings` builds it with `provider=filed.venue`), it stays on the filings-only path. `_rebase_pe_on_filed_eps` therefore never overwrites the current-count P/E.

I checked that no main-board path can pick up the venue branch. The only `Fundamentals(...)` constructors are yahoo_batch, fundamentals_store, openbb_mcp, yfinance and the filings shell, and only the shell uses the venue as its provider.

## (2) Chain (in the verify worktree)

```
VENV_EXIT=0        (python3.13 venv + requirements + requirements-dev)
INSTALL_EXIT=0     (pnpm install --frozen-lockfile)
ENSURE_EXIT=0      (node scripts/ensure-all-sidecars.mjs)
CI_EXIT=0          (PATH=<wt>/sidecar/.venv/bin:$PATH pnpm ci-local)
   ruff: All checks passed!
   vitest: Test Files 170 passed (170) / Tests 2048 passed (2048)
   cargo test: ok. 32 passed; 0 failed
   pytest: 4013 passed, 1 skipped, 4 warnings in 229.29s
 M vitest.config.ts -> git restore vitest.config.ts (done)
SMOKE_EXIT=1   (first run, in the chain)
SMOKE_EXIT=0   (attended re-run, alone)
```

The first smoke run failed with `vysted-sidecar HUNG — bound the port but /health did not respond within 120000ms`. I caused that: at 23:09:05 I cold-started my own live stack (two `--onefile` MCP binaries plus the source sidecar) at the same moment the smoke test started its cold `_MEI` extraction. That is the documented boot-contention trap (CLAUDE.md "Deferred / carry-forward").

I stopped my stack by pid and re-ran `node scripts/smoke-test-sidecars.mjs` alone. The re-run passed:

```
[smoke] vysted-sidecar version OK (0.9.0).
[smoke] vysted-sidecar screener universe OK.
[smoke] vysted-sidecar ICONIKSPEV resolution OK (deterministic BSE identity).
[smoke] vysted-sidecar /agents roster OK (13 agents).
[smoke] vysted-sidecar /mcp/status OK (ready=true, toolCount=39).
[smoke] vysted-openbb-mcp-sidecar OK (bound :62845, survived settle window).
[smoke] vysted-sec-edgar-mcp-sidecar OK (bound :62869, survived settle window).
[smoke] all sidecars booted cleanly.
SMOKE_EXIT=0
```

Logs: `scratchpad/fsv-chain.log` and `scratchpad/fsv-smoke2.log`.

## (3) Gate 8

```
$ cd sidecar && .venv/bin/python -m pytest tests/test_no_trading_surface.py -q
8 passed, 1 warning in 0.85s
EXIT=0
```

## (4) Own repro of fixed entries on the touched files

**Selection.** I took every register entry with `status: fixed` whose `files` intersect the changed files, plus R15-FINAL-005, FINAL-006, FINAL-003, LEAD-136 and LEAD-127. Each entry's pinned test files come from its register evidence, merged with the earlier verifiers' maps (`scratchpad/fsv-map.json`).

**Run.** All 20 test files ran in one batch at the candidate, together with `test_no_trading_surface.py`:

```
579 passed, 3 warnings in 26.32s
EXIT=0
```

| Id | Pinned tests | Verdict |
|---|---|---|
| R15-DATA-001 | test_openbb_mcp_provider, test_provider_registry_region | holds |
| R15-DATA-004 | test_company_narrative, test_fundamentals | holds |
| R15-DATA-005 | test_correctness_gate, test_fundamentals | holds |
| R15-DATA-006 | test_bse_provider, test_yfinance_provider | holds |
| R15-RESEARCH-001 | test_research_deep, test_research_relevance | holds |
| R15-DATA-013 | test_correctness_gate | holds |
| R15-DATA-014 | test_b7_exchange_financials, test_company_narrative, test_fundamentals | holds |
| R15-DATA-033 | test_correctness_gate, test_india_provider | holds |
| R15-DATA-034 | test_b4_v7_gate | holds |
| R15-DATA-117 | test_yahoo_batch_provider, test_yfinance_provider | holds |
| R15-LIFECYCLE-004 | test_bse_provider, test_correctness_gate, test_nse_provider | holds |
| R15-CODE-DATA-005 | test_witness | holds |
| R15-LEAD-034 | test_correctness_gate | holds |
| R15-LEAD-050 | test_research_relevance | holds |
| R15-RESEARCH-018 | test_b6_research_funnel | holds |
| R15-RESEARCH-021 | test_research_relevance | holds |
| R15-CODE-RESEARCH-012 | test_research_relevance | holds |
| R15-LEAD-127 | test_lead127_listing_region | holds |
| R15-FINAL-003 | test_final_data_fundamentals (incl. `test_a_provider_sized_listing_keeps_its_pe_on_the_filed_eps`, `..._filed_eps_pe_on_a_second_pass`) | holds |
| R15-FINAL-004 | test_research_relevance | holds |
| R15-FINAL-005 | test_final_data_fundamentals | holds |
| R15-FINAL-006 | test_nse_throttle, test_quotes | holds |
| R15-FINAL-024 | test_final_data_fundamentals, test_fundamentals | holds |
| R15-LEAD-136 | test_research_relevance | holds |

No entry regressed.

### Fail-before / pass-after for the new pinned tests

I ran the candidate's two test files against the base code, in a detached worktree at `b7d37fd9` with only the test files swapped in (`scratchpad/fsv-failbefore.txt`):

```
FAILED test_curis_route_pe_survives_the_gates_second_overlay_pass
   E  assert 12.151215121512152 == 15.780093257955844 ± 1.6e-05     <- price / filed EPS (135 / 11.11), the 18.59-style figure
FAILED test_no_current_count_route_pe_stays_a_typed_null_through_the_gate
   E  assert 12.151215121512152 is None                             <- the 2nd pass filled the typed null with price/EPS
FAILED test_every_nse_word_symbol_needs_an_anchor_in_title_case
   E  {'ACE','CUB','DEN','KEN','PAR'} <= set()   (NSE symbols in the word list: 234, 0 three-letter)
FAILED test_three_letter_word_ticker_needs_an_anchor[ACE|DEN|CUB|PAR|KEN]
   E  'Ace shuttler PV Sindhu storms into final'  assert 0.6 <= 0.25   (same 0.6 short-tier keep for DEN/CUB/PAR/KEN)
PASSED test_a_provider_sized_listing_keeps_its_filed_eps_pe_on_a_second_pass   (main-board rebase unchanged at base too)
PASSED test_three_letter_words_leave_brand_list_headlines_unchanged            (pins b7d37fd9 values)
8 failed, 2 passed
```

At the candidate, all of them pass (`scratchpad/fsv-passafter.txt`):

```
NSE symbols in the word list: 251 (17 three-letter: ['ABB', 'ACE', 'AWL', 'AYE', 'BEL', 'CUB', 'DEN', 'HAL', 'KEN', 'MAL', 'OIL', 'PAR', 'SAB', 'SIL', 'SIS', 'TIL', 'UDS'])
18 passed (relevance anchor + three-letter tests); 4 passed (LEAD-137 route tests + FINAL-003 provider-sized tests)
```

The LEAD-137 test meets the attempt-2 requirement. `_route_through_the_gate` drives `GET /fundamentals/CURIS` through `TestClient(create_app())` with the real correctness gate, so the filings shell (pass 1) and then `apply_witnesses` (pass 2) both run. Only identity, basis and witness network reads are stubbed. It fails on base with the price/EPS figure and passes at the candidate. It is not a single overlay call.

## (5) Live

All live runs used my own source sidecars from the candidate worktree, with fresh keyless data copies seeded from `final-seed-data` and `dev-keystore.json` set to exactly `{"secrets": {}, "migrated": true}`:
- **52940** (`fsv-137-data`): LEAD-137.
- **52950** (`fsv-141-data`): LEAD-141.
- **52970**, with openbb-mcp on 52971 and sec-edgar-mcp on 52972 from the worktree's built binaries (`fs-verify-data`): the full stack.

Region was IN throughout. I used fresh `fsv-*` copies rather than the writers' `fs-137-data` and `fs-141-data`, so that no writer-warmed cache could serve a value.

After each run I stopped every one of my processes by pid (sidecar python, MCP bootloaders and workers, and the `sleep 86400` stdin holders). No process of mine is left.

### (5a) LEAD-127: holds

Research FAST via the `/mcp` `research` tool (`depth: quick`):

```
== Halliburton | resolved HAL US US HALLIBURTON CO
   price ok True 31.85 USD
   fund ok True {'symbol': 'HAL', 'currency': 'USD', 'market_cap': 26535202816.0, 'pe_ratio': 16.675394, 'revenue_ttm': 22372999168.0, 'net_income_ttm': 1602000000.0, 'name': 'Halliburton Company'}
== Hindustan Aeronautics | resolved HAL NSE IN Hindustan Aeronautics Limited
   price ok True 4601.0 INR
```

- **Halliburton.** Grounded against https://stockanalysis.com/stocks/hal/: $31.85, market cap $26.54B, P/E 16.70, revenue TTM $22.37B, net income TTM $1.60B. Every figure matches.
- **Control, Hindustan Aeronautics.** The research fundamentals leg hit the FAST 6 s leg cap in all three tries. The route `GET /fundamentals/HAL.NS` (IN) returned `INR price 4601 mcap 3,077,033,689,088 pe 33.01`, basis "price / exchange-filed TTM EPS (4,601 / 139.38)". That is the main-board R15-FINAL-003 rebase, unchanged. Grounded against https://www.screener.in/company/HAL/consolidated/: market cap ₹3,07,703 Cr, price ₹4,601, P/E 33.0. It matches.

### (5b) FINAL-005: holds

```
VOLERCAR VOLERCAR-SM.NS INR price 216.3 mcap 2410344890.1 pe 73.14 eps 2.952 rev 547,027,000 ni 32,956,000
```

Revenue, net income and EPS all carry values.

### (5c) LEAD-137 stated repro via the route: holds

`curl -H 'X-Vysted-Region: IN' 127.0.0.1:52940/fundamentals/<SYM>` (`scratchpad/fsv-137-live.txt`):

| Symbol | Ours: P/E, market cap | Basis note | screener.in (URL, value) | Δ |
|---|---|---|---|---|
| CURIS | 24.14, ₹166.9 Cr | market cap on the current share count / exchange-filed TTM net income (206.5 x 8,084,434 / 69,163,000, shares from the NSE quote issued size) | https://www.screener.in/company/CURIS/ P/E 24.1, ₹167 Cr | 0.2% / 0.0% |
| SHETHJI | 20.91, ₹416.5 Cr | current count (183 x 22,760,000 / 199,182,000) | https://www.screener.in/company/SHETHJI/ P/E 21.0, ₹419 Cr | 0.4% / 0.6% |
| FINBUD | 20.43, ₹234.3 Cr | current count (123 x 19,049,480 / 114,662,000) | https://www.screener.in/company/FINBUD/ P/E 20.7, ₹241 Cr (price ₹126 vs our 123) | 1.3% / 2.8% |
| VOLERCAR | 73.14, ₹241.0 Cr | current count (216.3 x 11,143,527 / 32,956,000) | https://www.screener.in/company/VOLERCAR/ P/E 73.0, ₹241 Cr | 0.2% / 0.0% |
| GANESHIN | 5.10, ₹388.7 Cr | current count (88.8 x 43,770,997 / 761,727,000) | https://www.screener.in/company/GANESHIN/ P/E 5.15, ₹379 Cr (price ₹86.6 vs our 88.8) | 1.0% / 2.5% |
| JAYESH (claim) | 9.95 | current count | claim's screener 9.94 | 0.1% |
| GREENLEAF (claim) | 9.35 | current count | claim's screener 9.35 | 0.0% |

Every figure is within about 5%. None is price / filed EPS any more (the claim's earlier values were CURIS 18.59, SHETHJI 17.00, FINBUD 16.53, JAYESH 7.79 and GREENLEAF 7.28). The same route on the 52970 full stack returned identical CURIS, VOLERCAR and ACCPL values.

Fresh in-class names the writer did not use:
- **ACCPL** (Accretion Pharmaceuticals, NSE-SME). Ours: P/E 23.38, market cap ₹226.0 Cr, current-count basis (203.3 x 11,116,000 / 96,675,000). Against https://www.screener.in/company/ACCPL/ (P/E 23.4, ₹226 Cr) the difference is 0.1% / 0.0%. **Holds.**
- **ATCENERGY** (NSE-SME, loss-making). Ours: P/E is a typed null, "the trailing net income -14,759,000 is not positive — no trailing P/E". https://www.screener.in/company/ATCENERGY/ shows P/E blank and TTM net profit ₹-1.48 Cr. **Holds** (typed null).
- **PRIMECAB** (Prime Cable, NSE-SME). Ours: P/E 30.88, market cap ₹377.9 Cr, current-count basis (206.25 x 18,324,060 / 122,386,000). https://www.screener.in/company/PRIMECAB/ shows market cap ₹378 Cr (a match) but P/E 26.5.
  - Our net income (₹12.24 Cr, the sum of the filed half-years Sep-25 and Mar-26) agrees with screener's own FY2026 net profit (₹12 Cr). The half-year EPS also agree (2.99 + 3.69).
  - So the gap is screener's P/E basis, not our share count or net income. It is not the LEAD-137 defect, which is price / weighted EPS: that would give 206.25 / 6.68 = 30.9 here, the same number, because the count did not change.
  - I record this as an observation, not a candidate entry.
- **SRIGEE**. Out of class: it resolved to BSE `SRIGEE.BO`, a yfinance-published, provider-sized listing (P/E 6.70 = market cap / net income). Recorded for completeness only.

### (5c) LEAD-141 stated repro: holds

**Research FAST on 52950** (`scratchpad/fsv-141-live.txt`):

```
== Action Construction Equipment | resolved ACE NSE IN Action Construction Equipment Limited
   fund ok True {'symbol': 'ACE.NS', 'currency': 'INR', 'market_cap': 144333209600.0, 'pe_ratio': 33.03, ...}
   news note: No on-entity news found for ACE — 1 item(s) returned by the news feed were off-entity/off-topic and dropped.
     (raw feed item: "9 large-cap stocks that surged over 50% in the first half of FY27", a list item, correctly off-entity)
== Ace Software Exports | resolved ACESOFT BSE IN ACE Software Exports Ltd   (BSE-only, a different ticker)
== City Union Bank | resolved CUB NSE IN City Union Bank Limited
   NEWS: Wizz Financial collaborates with City Union Bank to Unveil 'Wizz Voyager', the Ultimate Smart Travel Card   (on-entity)
```

No unrelated word-use headline appears in either brief's news.

**Fresh 3-letter word tickers from the NSE intersection.** The writer used ACE, DEN, CUB, PAR and KEN. Live research:
- OIL: 5 feed items dropped. All are generic market wraps or Petronet stories.
- BEL: 1 dropped. "3 India Deep Tech Stocks…", a list item.
- SIS: no news.

**Scorer probe, base vs candidate** (`scratchpad/fsv-probe.txt`; economictimes host):

```
                                                         base        candidate
OIL  Oil India Q2 net profit jumps 20%                   1.00 keep   1.00 keep
OIL  OIL shares hit 52-week high                         0.60 keep   0.60 keep
HAL  HAL bags Rs 62,000 crore order for LCA              0.60 keep   0.60 keep
HAL  Hal Foster wins award                               0.60 KEEP   0.00 drop
BEL  BEL shares rise on defence orders                   0.60 keep   0.60 keep
BEL  Bel Air hotel sold                                  0.60 KEEP   0.00 drop
ACE  Ace of spades: a poker night guide                  0.60 KEEP   0.00 drop
ACE  Ace investor Vijay Kedia adds stake in smallcap     0.60 KEEP   0.00 drop
ACE  ACE shares jump on order win                        0.60 keep   0.60 keep
CUB  Cub Scouts celebrate 100 years                      0.60 KEEP   0.00 drop
CUB  City Union Bank Q2 profit rises / CUB shares rally  keep        keep
SIS  Sis act: sisters open bakery in Pune                0.60 KEEP   0.25 drop
MAL  Mal de mer: a seasick sailor tale                   0.60 KEEP   0.25 drop
TIL  Til ladoo recipe for Makar Sankranti                0.60 KEEP   0.25 drop
TITAN Titan, Trent lead Nifty gains ...                  0.25 drop   0.25 drop   (LEAD-142 behaviour unchanged)
TITAN Titan Q2 jewellery sales rise 20%                  1.00 keep   1.00 keep
```

The fresh in-class words HAL, BEL, SIS, MAL and TIL are now dropped when used as prose. Anchored all-caps and company-name uses stay kept.

"Ace Q2 results: profit up 30%" is kept at 0.60 in both base and candidate (a financial-context keep). That is outside this class and not a regression.

### LEAD-136: holds

Titan brief on 52970: `resolved TITAN NSE IN Titan Company Limited`, news "Titan Company deepens focus on mechanical horology as category grows almost 5-fold" (thehindu.com), which is on-entity. The pinned brand/list scores are unchanged (table above).

## Candidate new entries

None. Two things I saw are covered elsewhere:
- **Already tracked as R15-LEAD-135 (open).** The Halliburton (HAL/US) brief's news leg carries "India's Hindustan Aeronautics posts strong quarterly results…", sourced from "Yahoo! Finance: HAL.NS News" with `via_symbol_feed` trusted for a non-IN target. `gate_news` keeps it at both base and candidate, so this is not a regression. It is not a new entry.
- **Observation, no entry.** PRIMECAB's screener.in P/E (26.5) differs from ours (30.9), while market cap and FY26 net income agree. The cause is screener's P/E basis, not ours (see 5c).

## Evidence files (scratchpad)

`fsv-chain.log`, `fsv-smoke2.log`, `fsv-gate8.txt`, `fsv-pins.log`, `fsv-map.json`, `fsv-failbefore.txt`, `fsv-passafter.txt`, `fsv-probe.txt`, `fsv-137-live.txt`, `fsv-137-<SYM>.json`, `fsv-141-live.txt`, `fsv-res-52950-*.json`, `fsv-res-52970-*.json`, `fsv-stack-research.txt`, `fsv-stack-fund.txt`, `fsv-news-{OIL,BEL,ACE}.json`.
