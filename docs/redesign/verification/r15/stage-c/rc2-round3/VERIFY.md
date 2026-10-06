# rc2 round-3 fresh verifier: r15-rc2-int at a5abb7ec

Verifier: claude-opus-5-5 (judgement tier, medium, fresh context). I wrote no product code and consulted no advisor.

- Worktree: `scratchpad/rc3-verify`, detached at `a5abb7ecae00e47bf21800257fe455d6114fd97d`.
- Scope base: `ae6ffff0ab02c3e5b696a5fe76905ea8d0b7e692`.
- Raw evidence is under `scratchpad/`: `rc3-chain.log`, `rc3v-gate8.txt`, `rc3v-pins-py.log`, `rc3v-map.json`, and `rc3v-live/` (all live JSON, probes and screener HTML).

## Verdicts

| entry | verdict | failed stated-repro step |
|---|---|---|
| R15-LEAD-137 | **NOT CERTIFIED** | Stated instance CURIS. `GET /fundamentals/CURIS` (IN) still serves **pe_ratio 18.59**, with basis "price / exchange-filed TTM EPS (206.5 / 11.11)". screener.in shows 24.1, so the figure is 23% low, the same as before the fix. market_cap is now correct (166.9 Cr against 167 Cr). The same P/E fault appears on every fresh in-class name I checked. |
| R15-LEAD-136 | **CERTIFIED** | none (class repro holds; see residuals) |
| Overall rc2 candidate gate ((1)-(4) and (5a)-(5b)) | **CERTIFIED** | (1), (2), (3), (4), (5a) and (5b) all hold. LEAD-137 is refused only on its own row. |

## (1) Scope and safety

```
$ git diff --stat ae6ffff0 a5abb7ec -- . ':(exclude)docs'
 sidecar/services/correctness_gate.py               |  99 +++++++---
 sidecar/services/exchange_financials.py            |  52 +++++-
 sidecar/services/nse_provider.py                   |  33 ++++
 sidecar/services/research/relevance.py             | 118 ++++++++----
 .../services/resolver_masters/english_words.txt.gz | Bin 659150 -> 731652 bytes
 sidecar/tests/test_final_data_fundamentals.py      | 206 ++++++++++++++++++++-
 sidecar/tests/test_research_relevance.py           | 139 ++++++++++++++
 7 files changed, 572 insertions(+), 75 deletions(-)
```

Every changed file is in an owned set:
- LEAD-137 owns `correctness_gate.py`, `exchange_financials.py`, `nse_provider.py` and `test_final_data_fundamentals.py`.
  - The `nse_provider.py` change only adds a read-only `get_issued_size` on the existing `_get_json` lane. The throttle and lane code are untouched.
- LEAD-136 owns `relevance.py`, `english_words.txt.gz` and `test_research_relevance.py`.

Safety surface: `git diff --name-only ae6ffff0 a5abb7ec -- src types sidecar/services/agent_runtime.py sidecar/services/planner.py sidecar/services/action_ledger.py sidecar/tests/test_no_trading_surface.py docs/SAFETY_ARCHITECTURE.md src-tauri .github LICENSE COMMERCIAL_LICENSE.md CLAUDE.md` returns **EMPTY**.

Test edits:
- The existing YASHOPTICS and VOLERCAR assertions in `test_final_data_fundamentals.py` changed from the weighted-count P/E and market cap to the current-count figures. The precision is unchanged, and they now also assert market_cap and the basis note.
- I judge this an intended re-pin to the fixed behaviour, not a weakening. No test was deleted or skipped.

## (2) Chain (verify worktree)

- `pnpm install --frozen-lockfile`: INSTALL_EXIT=0.
- `node scripts/ensure-all-sidecars.mjs`: ENSURE_EXIT=0. All 3 binaries were built from a5abb7ec.
- `PATH=<wt>/sidecar/.venv/bin:$PATH pnpm ci-local`: **CI_EXIT=0**.
  - ruff: "All checks passed!"
  - vitest: `Test Files 170 passed (170)`, `Tests 2048 passed (2048)`
  - cargo test: `32 passed; 0 failed`
  - pytest: `4003 passed, 1 skipped, 4 warnings in 229.57s`
- The coverage ratchet rewrote `vitest.config.ts`. I ran `git restore vitest.config.ts`, and the tree is clean.
- `node scripts/smoke-test-sidecars.mjs`: **SMOKE_EXIT=0**.
  - "vysted-sidecar version OK (0.9.0)", "/agents roster OK (13 agents)", "/mcp/status OK (ready=true, toolCount=39)"
  - openbb-mcp and sec-edgar-mcp bound
  - "all sidecars booted cleanly"

## (3) Gate 8

`cd sidecar && .venv/bin/python -m pytest tests/test_no_trading_surface.py -q` gives `8 passed, 1 warning in 1.23s`.

## (4) Fixed entries on touched files: pinned tests at the candidate

I selected every `fixed` register entry whose `files` intersect the code diff, plus FINAL-005, FINAL-006 and LEAD-127. That gives **31 entries**:

> DATA-001/004/005/006/013/014/017/025/033/034/050/066/079/117, RESEARCH-001/018/021, CODE-DATA-005, CODE-RESEARCH-012, LIFECYCLE-004/021, LEAD-020/034/050/051/127, FINAL-003/004/005/006/024

Pins are the test files that name the id, plus the test files cited in the entry's closure_evidence, note or evidence. The map is in `rc3v-map.json`. 29 files ran in one batch:

`773 passed, 3 warnings in 47.93s`, **PY_EXIT=0**. **Holds for all 31, regressed 0**, including R15-FINAL-005, R15-FINAL-006 and R15-LEAD-127. The full pytest run in (2) is also green.

## (5) Live: own stack from the candidate's built binaries

Stack setup:
- Ports: main `:52970`, openbb-mcp `:52971`, sec-edgar-mcp `:52972`, all from the worktree's `src-tauri/binaries/*` built at a5abb7ec. That exercises the onefile bundling of the new word list and the new NSE read.
- Data dir: `scratchpad/rc3-verify-data`, a `.backup` copy of `final-seed-data`.
- `dev-keystore.json` is exactly `{"secrets": {}, "migrated": true}`.
- Region IN. `/health` returned version 0.9.0 and `openbb-mcp: available`.
- Every research call ran inside `mkdir /tmp/vysted-r15-ollama.lock` and released it with `rmdir`.

I ran both entries' live checks on this one stack, not on separate source sidecars at 52940/52950. The binaries are the candidate's source, built.

Teardown: I killed sleep pids 99707, 99710 and 99713, and bootloaders 99708, 99711 and 99714 had exited. Workers 99719, 99726 and 99729 exited, and nothing listens on 52970-52972.

Some first-pass research legs timed out at the 6 s box (price/news, known R15-LEAD-128) while ci-local pytest was running. The figures below are from re-runs on an idle stack (`r2-*`, `r3-*`).

### (5a) R15-LEAD-127: HOLDS

| query (IN) | resolved | price | fundamentals |
|---|---|---|---|
| Halliburton | HAL / HALLIBURTON CO / US | 31.85 USD (yfinance) | Halliburton Company, USD, P/E 16.68, mcap 26.54B |
| Hindustan Aeronautics (control) | HAL / Hindustan Aeronautics Limited / IN | 4601.0 INR | HAL.NS, INR, P/E 33.01, mcap 3.077T |

Grounding:
- Halliburton: these values are identical to the 2 Oct close grounded at https://stockanalysis.com/stocks/hal/ in round 2 ($31.85, mcap $26.54B, PE 16.70). 3 Oct is a Saturday.
- The control: https://www.screener.in/company/HAL/consolidated/ shows "Market Cap ₹ 3,07,703 Cr | Current Price ₹ 4,601 | Stock P/E 33.0".

The control's first run hit the 6 s box. The re-run is `r3-Hindustan_Aeronautics.json`.

### (5b) R15-FINAL-005: HOLDS

`f137-VOLERCAR.json` serves revenue_ttm 54.70 Cr, net_income_ttm 3.30 Cr and EPS 2.95, with as_of 2026-06-30. These are the same values round 2 certified.

### (5c) R15-LEAD-137: NOT CERTIFIED

`GET /fundamentals/<sym>` (IN). Raw responses are in `rc3v-live/f137-*.json`. screener.in figures were fetched on 3 Oct 2026 (`rc3v-live/screener-*.html`).

| name | ours: market cap | ours: P/E (basis) | screener.in | verdict |
|---|---|---|---|---|
| **CURIS** (stated) | 166.9 Cr (206.5 x 8,084,434, NSE quote issued size) | **18.59** ("price / exchange-filed TTM EPS (206.5 / 11.11)") | 167 Cr / **24.1** (https://www.screener.in/company/CURIS/) | mcap ok; **P/E 23% low** |
| VOLERCAR | 241.0 Cr (216.3 x 11,143,527) | 73.14 (mcap / TTM NI) | 241 Cr / 73.0 | ok |
| GANESHIN | 379.3 Cr (86.65 x 43,770,997) | 4.98 (mcap / TTM NI) | 379 Cr / 5.15 | ok (P/E 3.3%; NI includes minority share, as in round 2) |
| YASHOPTICS | 335.3 Cr | 37.10 (price / EPS) | 335 Cr / 37.0 | ok (no share change) |
| **SHETHJI** (fresh, listed 2025-11-12) | 419.1 Cr | **17.00** (price / EPS) | 419 Cr / **21.0** | **P/E 19% low** |
| **FINBUD** (fresh, 2025-11-13) | 240.6 Cr | **16.53** (price / EPS) | 241 Cr / **20.7** | **P/E 20% low** |
| **JAYESH** (fresh, 2025-11-03) | 100.2 Cr | **7.79** (price / EPS) | 100 Cr / **9.94** | **P/E 22% low** |
| **GREENLEAF** (fresh, 2025-10-09) | 67.6 Cr | **7.28** (price / EPS) | 67.6 Cr / **9.35** | **P/E 22% low** |
| NEOCHEM (fresh, 2025-12-09) | 172.9 Cr | null, typed "no trailing EPS … insufficient filed periods" | 173 Cr / 13.8 | ok (typed null) |
| SPEB (fresh, 2025-12-08) | 193.2 Cr | null, typed (same) | not fetched | typed null |

Market cap is fixed everywhere. The issued size from NSE matches screener within 0.5% on all eight names.

The P/E is not fixed. On CURIS and every fresh name with a strict trailing year, the served P/E is price / summed filed EPS, which is the weighted-count figure the fix shape says must never be served.

**Root cause:** the overlay runs twice on the SME path.
1. `provider_registry.py:641` serves the filings shell through `overlay_filed_periods`. That pass is filings-only, so `_size_on_current_count` sets P/E = cap / NI = 24.14.
2. The correctness gate's verify step runs `overlay_filed_periods` again (`correctness_gate.py:1314`). Revenue and NI are now non-null, so `filings_only` is False. The strict `trailing()` succeeds, and `_rebase_pe_on_filed_eps` (`correctness_gate.py:826-827`) overwrites the P/E with price / filed EPS.

VOLERCAR and GANESHIN escape only because their strict `trailing()` is None, so the second pass changes nothing. The writer's unit tests call the overlay once. In-process reproduction with the writer's own CURIS fixture (`rc3v-live/l137-twice.py`):

```
once  mcap 1669435621.0 pe 24.13769820568801 | market cap on the current share count / exchange-filed TTM net income (206.5 x 8,084,434 / 69,163,000, shares from the NSE quote issued size)
twice mcap 1669435621.0 pe 18.586858685868588 | price / exchange-filed TTM EPS (206.5 / 11.11, price from the ratio price)
```

A fix would make the second pass recognise an already-filings-sized payload, for example by keying `filings_only` on the provider tag or field_meta provenance rather than on null sizes. It also needs a test that runs the full `/fundamentals` route, or overlay twice, for a CURIS-shaped fixture.

### (5c) R15-LEAD-136: CERTIFIED

**Class enumeration (writer's test, re-run in (2) and (4)):**
- `test_every_nse_word_symbol_needs_an_anchor` loads the bundled NSE master (`resolver_masters/nse_instruments.json`, 3,506 instruments) and intersects it case-folded with the word list. That gives **234 symbols**.
- TITAN, CUPID, TRENT and APOLLO fall out of the enumeration and are not hand-listed.
- Green.

**My in-process probes at the candidate** (`rc3v-live/l136-probe.txt`, economictimes URL):

```
TITAN      0.25 keep=False  Tech titan Elon Musk unveils new rocket
TITAN      0.25 keep=False  Tech Titan Elon Musk Unveils New Rocket
TITAN      0.25 keep=False  Media Titan Murdoch Steps Down
TITAN      0.25 keep=False  Titan submersible inquiry report released
TITAN      1.00 keep=True   Titan Company shares rise
TITAN      1.00 keep=True   Titan Q2 profit jumps 20%
TRENT      0.25 keep=False  River Trent floods as storm lashes England
TRENT      0.25 keep=False  Trent Bridge Test: England bat first
TRENT      1.00 keep=True   Trent Q2 profit jumps as Zudio expands
CUPID      0.25 keep=False  Cupid's arrow: Valentine's Day spending hits record
APOLLO     0.25 keep=False  Apollo Global Management raises $5bn fund
APOLLO     1.00 keep=True   Apollo Micro Systems bags defence order
FOCUS/CAMPUS/SAFARI/ETERNAL/RAIN: prose 0.25 dropped, company headlines 1.00 kept
RELIANCE / INFY / ROUTE controls: unchanged ("Best route to the airport" 0.25 dropped)
fresh in-class (from the enumeration, not used by the writer): MAZDA, LINCOLN, NILE, CROWN
  "the <w> of the matter", "Why the <W> Debate Is Back", "<W> rises as markets rally" -> 0.25 dropped
  "<W> Ltd shares jump 5%", "<SYM> shares hit upper circuit on NSE" -> 1.00 kept
Title-case prose sweep over all 234 ("Why the <W> Debate Is Back", "Tech <W> Unveils New Rocket"):
  kept 3 = RELIANCE x2 (marquee-family exemption, a control) + DEEM ("Tech Deem…": its name token "Tech" corroborates; an artefact of my synthetic headline)
```

**Live, research quick on IN** (`r2-Titan_Company.json`, `r2-Trent.json`, `r3-Mazda_Limited.json`):
- **Titan Company**:
  - Resolves to TITAN.
  - News has one item, the company's own: "Titan Company deepens focus on mechanical horology as category grows almost 5-fold" (thehindu).
  - No unrelated common-word headline.
- **Trent**:
  - Resolves to TRENT. News is empty.
  - The raw feed (`l136-feed.txt`, `news_provider.fetch_news(["TRENT"])`) gave 140 items with zero mentions of "trent" in title or summary. So there was no own headline to keep, and the filter dropped none.
  - No unrelated headline.
- **Mazda Limited** (fresh): resolves to MAZDA. News is empty, and no unrelated headline appeared.
- Web search was rate-limited or unreachable in these runs, so the news leg is the only headline surface exercised live.

**Why certified:** the stated class repro holds.
- TITAN, CUPID, TRENT and APOLLO, plus the fresh MAZDA, LINCOLN, NILE and CROWN, all drop an unrelated common-word headline (lowercase, mid-sentence title case and full Title-Case) and keep the anchored one.
- The prior instances and the controls hold.
- The required corroborated-company headlines are kept.

## Candidate new entries (beyond the stated repros; none refuses an entry)

| id | proposed severity | finding |
|---|---|---|
| N1 | high | **The LEAD-137 P/E residual, if the lead tracks it separately from the refused row.** The SME P/E is still price / summed filed EPS whenever the strict trailing year exists, on CURIS, SHETHJI, FINBUD, JAYESH and GREENLEAF (19-23% low). Cause: the double overlay above. |
| N2 | high | **3-letter NSE word tickers bypass the word rule** (pre-existing, unchanged from base). The bundled list is 4+ letters, and the occurrence rule only fires on lowercase. With an India host, a sentence-initial or Title-Case use scores short-only 0.60 keep=True. Examples: ACE "Ace shuttler PV Sindhu storms into final", DEN "Den of thieves: police bust Mumbai cyber fraud ring", CUB "Cub reporter's scoop rattles Delhi", PAR "Par for the course: markets shrug off Fed", KEN "Ken Griffin's Citadel posts record gains". `rc3v-live/l136-real.py` and `l136-short.txt` list all 17 three-letter word symbols (HAL, BEL, ABB, OIL, AWL, CUB, ACE, SIS, AYE, TIL, UDS, DEN, SAB, SIL, PAR, KEN, MAL); OIL is handled. The base gives identical scores. I did not refuse LEAD-136 on this because the claim is a *distinctive* match and these score on the separate short-symbol tier. If the lead reads the class as any keep, this folds into LEAD-136. |
| N3 | medium | **Recall regression: brand-only and list headlines for word tickers now drop.** Live raw-feed item for Titan: "Stocks to buy: Titan, Lenskart, Dabur among Nomura's 17 consumer picks" was 1.00 kept at base and is now 0.25 dropped. Also "Titan, Trent lead Nifty gains as consumer stocks rally" (both targets) and "Trent rallies 5% as Zudio store count crosses 800" (no snippet) were kept at base and now drop. The writer's `ponytail:` comment names a brand table as the upgrade. This affects all 234 word-ticker names. |
| N4 | low | The LEAD-127 news leg is still not region-scoped (known). The Halliburton brief's news is "India's Hindustan Aeronautics posts strong quarterly results…". |
