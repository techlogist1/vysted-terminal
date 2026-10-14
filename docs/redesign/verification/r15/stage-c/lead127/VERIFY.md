# R15-LEAD-127 — fresh verification

- **Verifier:** fresh context, judgement tier, model `claude-opus-5-5` (Opus 5.5). No advisor was consulted. No product code was written.
- **Candidate:** `r15-lead127-fix` @ `39b9bfcf8b0272b41be6d1fb06240bcfb2b8f73d`. Base `341bc72dfc06704d92ba296c632128f9570dfc83`.
- **Verify worktree:** `scratchpad/lead127-verify` (detached at the candidate). It was clean after the run: `git status --short` was empty and `vitest.config.ts` was restored after the coverage ratchet rewrote it.
- **Verdict: CERTIFIED.** Checks (1) to (5) all hold. One residual sibling of the same class is out of the claim's scope. It is described at the end.

## (1) Diff scope + safety surface

```
 .../verification/r15/stage-c/lead127/FIX.md        |  67 ++++++++
 sidecar/services/agent_tools/catalog.py            |  18 +-
 sidecar/services/agent_tools/deep_research.py      |   1 +
 sidecar/services/agent_tools/fundamentals.py       |  13 ++
 sidecar/services/agent_tools/price_data.py         |  43 ++++-
 sidecar/services/research/fast.py                  |  52 +++++-
 sidecar/services/research/iter.py                  |   2 +
 sidecar/tests/test_lead127_listing_region.py       | 191 +++++++++++++++++++++
 8 files changed, 384 insertions(+), 3 deletions(-)
SAFETY_EXIT=0   (git diff --quiet base cand -- src agent_runtime.py planner.py proposed-changes.ts types test_no_trading_surface.py SAFETY_ARCHITECTURE.md src-tauri .github LICENSE COMMERCIAL_LICENSE.md CLAUDE.md)
```

- Every changed file is in the owned set or under `stage-c/lead127/`.
- The fix matches the triage shape:
  - `snapshot_structured(listing_region=)` sets the region ContextVar before the `_snapshot_legs` fan-out and resets it in a `finally`.
  - All callers pass `target.region`: `gather_fast`, `iter.py` (x2) and `deep_research.py`.
  - `price_data` and `fundamentals` take an optional `region`, enum `US/IN/GLOBAL`. It is declared once in `catalog.py`, and an unknown value is ignored.
- No existing test was deleted, skipped or weakened. The only test change is the new file.

**Fail-before.** I ran the new test file against base code (`git archive 341bc72d sidecar`) with the candidate venv: `11 failed, 3 passed`. The 3 that pass at base are the IN control and the two "no region keeps the session" controls. At the candidate, all 14 pass (they run inside ci-local and the pinned run below).

## (2) Chain

Log: `scratchpad/l127v-chain.log`.

```
INSTALL_EXIT=0                 pnpm install --frozen-lockfile
ENSURE_EXIT=0                  node scripts/ensure-all-sidecars.mjs (3 binaries)
  All checks passed!           (ruff)
  Test Files  169 passed (169) / Tests  2032 passed (2032)   (vitest)
  test result: ok. 32 passed   (cargo test)
  3935 passed, 1 skipped, 4 warnings in 246.86s              (pytest)
CI_EXIT=0                      PATH=<wt>/sidecar/.venv/bin:$PATH pnpm ci-local
 M vitest.config.ts  -> git restore vitest.config.ts
  [smoke] vysted-sidecar version OK (0.9.0) / /agents roster OK (13 agents) / /mcp/status OK (ready=true, toolCount=39)
  [smoke] vysted-openbb-mcp-sidecar OK / vysted-sec-edgar-mcp-sidecar OK
SMOKE_EXIT=0                   node scripts/smoke-test-sidecars.mjs
```

## (3) Gate 8

`cd sidecar && .venv/bin/python -m pytest tests/test_no_trading_surface.py -q`. Result: `8 passed, 1 warning in 1.62s`. Exit 0.

## (4) Own repro of fixed entries on the touched path

**Method.**
- I selected the register entries (`vysted-r15-register.json` @ candidate) with `status == fixed` whose `files` include any of the 6 changed sidecar files. That gives 57 entries.
- For each entry, its pinned tests are the test files named in the entry's text, plus the test files that cite its id.
- All of those 49 sidecar test files, plus the new file, ran together at the candidate. Result: **`1230 passed, 1 warning in 123.30s`, exit 0** (`scratchpad/l127v-pinned.log`).
- The frontend-pinned ids are covered by vitest in ci-local: 2032 passed, and `src` is byte-identical.

**All 57 hold.**

| id(s) | pinned tests (all green at candidate) |
|---|---|
| DATA-003 | test_disclosure_tools, test_disclosures_router. Live: the Halliburton/SailPoint/Transcontinental briefs below carry no promoter/shareholding data (`promoter` count 0) |
| RESEARCH-001 | test_research_deep |
| AGENT-008 | test_research_tools, test_b4_runtime_context_admission |
| AGENT-010 | test_resolve_symbol_tool, test_symbol_resolver |
| AGENT-011 | test_agent_runtime, test_run_manager (+ host-actions/agent-runs vitest) |
| AGENT-012, RESEARCH-009 | test_research_metering, test_research_tools, test_ddg_backend (+ BriefPanel vitest) |
| AGENT-020 | test_llm_lows, test_b5_runtime_notes, test_capability_catalog (+ ChatSidebar/context-provider vitest) |
| AGENT-022, AGENT-054, AGENT-094 | test_mcp_server, test_b3_runtime_tool_args |
| DATA-024 | test_b5_india_deals |
| DATA-026 | test_fundamentals_tool, test_fundamentals |
| DATA-028 | test_earnings_provider |
| LIFECYCLE-006, RESEARCH-010 | test_sonar_lane, test_research_model_lane, test_llm_openai (+ SettingsPanel/search-settings vitest) |
| RESEARCH-003, CODE-RESEARCH-003 | test_research_iter, test_research_tools, test_b6_research_funnel, test_research_deep |
| RESEARCH-005 | test_research_module_boundary, test_research_execution_record, test_research_tools, test_research_synthesis_timeout |
| RESEARCH-006 | test_research_verify, test_research_depth |
| RESEARCH-008 | test_web_search, test_keyless_backend, test_ddg_backend, test_research_hosted_lanes, test_capability_catalog |
| UI-003, CODE-AGENT-013, LIFECYCLE-025, AGENT-055 | test_capability_catalog, test_custom_agents_router (+ layout-templates vitest) |
| AGENT-044, AGENT-056, CODE-FRONTEND-014 | frontend-pinned (host-actions/workspace vitest, green). The catalog diff touches only the price_data/fundamentals schemas |
| AGENT-060, RESEARCH-030 | test_corporate_disclosures, test_disclosure_tools, test_research_disclosures |
| AGENT-061 | test_fundamentals_tool |
| AGENT-062 | test_price_data |
| AGENT-066, AGENT-067, CODE-AGENT-026 | test_mcp_catalog_parity, test_no_trading_surface |
| AGENT-070, AGENT-084, CODE-AGENT-008 | test_agent_runtime |
| CODE-DATA-005 | test_witness |
| CODE-RESEARCH-001 | test_deep_research_wall |
| CODE-RESEARCH-002, RESEARCH-013, RESEARCH-042, UI-091 | test_research_fast, test_indicators (+ chart vitest) |
| CODE-RESEARCH-005 | test_research_module_boundary |
| CODE-RESEARCH-006, RESEARCH-027 | test_research_depth, test_research_fast |
| DATA-049 | test_dividend_history |
| DATA-079 | test_option_chain |
| LEAD-032 | test_adr_ratio |
| RESEARCH-016, RESEARCH-035, RESEARCH-041 | test_research_iter |
| RESEARCH-017 | test_b6_research_funnel |
| RESEARCH-029 | test_research_citecheck |
| RESEARCH-033 | test_b7_research_visits |
| RESEARCH-040 | frontend-pinned (DepthControl/search-settings vitest, green) |

`test_capability_catalog.py` and `test_mcp_catalog_parity.py` are green, and neither file changed.

## (5) Live: the finder's repro, a fresh case, the copilot path, and a control

**Stack.** I booted the candidate's main sidecar from source on :52930. The worktree's built openbb-mcp ran on :52931 and sec-edgar-mcp on :52932.
- Data dir: `scratchpad/lead127-verify-data`, seeded from `final-seed-data`.
- `dev-keystore.json` read exactly `{"secrets": {}, "migrated": true}`.
- Session region was the default IN. Every brief echoes `"region": "IN"`.
- Health: `version 0.9.0`, `openbb-mcp: available`.
- I used the finder's exact command: `mcpcall.py research {"query":...,"depth":"quick"}`, with the port changed to 52930. Raw files are in `scratchpad/l127v-live/`.

**Ollama lock.** Every research call ran inside `mkdir /tmp/vysted-r15-ollama.lock`.
- On the 3rd acquisition, the final `rmdir` found the lock dir already gone, so another holder had removed it.
- No research run touched Ollama, because FAST makes no LLM call.

**Research FAST, session IN** (`structured.price.data` / `structured.fundamentals.data`):

| query | resolved | structured price | structured fundamentals | outside world (stockanalysis.com, close 2 Oct 2026) |
|---|---|---|---|---|
| Halliburton (finder) | HAL / HALLIBURTON CO / US | **31.85 USD** (yfinance) | **Halliburton Company**, USD, P/E 16.68, mcap 26.61B | https://stockanalysis.com/stocks/hal/: "Halliburton Company … $31.85 USD on October 2, 2026 … Market Cap $26.54 billion … PE Ratio 16.70" |
| SailPoint (finder) | SAIL / SailPoint, Inc. / US | **20.43 USD** | **SailPoint, Inc.**, USD, P/E null, mcap 11.66B | https://stockanalysis.com/stocks/sail/: "SailPoint, Inc. … $20.43 USD on October 2, 2026 … Market Cap $11.66 billion … PE n/a" |
| Transcontinental Realty (fresh; the writer used Halliburton/Ferrari/Carnival/PTC/RACE/HAL) | TCI / TRANSCONTINENTAL REALTY INVESTORS INC / US | **44.40 USD** | **Transcontinental Realty Investors, Inc.**, USD, P/E 47.23, mcap 389.56M | https://stockanalysis.com/stocks/tci/: "Transcontinental Realty Investors, Inc. (TCI) … $44.40 USD on October 2, 2026 … Market Cap $389.56 million … PE 47.61" |

**Why TCI is a real collision.** On this sidecar, `/quotes/TCI` returns 877.1 INR (Transport Corporation of India) under `X-Vysted-Region: IN`, and 44.40 USD under `US`.

**Before the fix.** At d38b5d1a the finder recorded nse_direct 4601.0 INR and HAL.NS fundamentals for Halliburton, and 174.5 INR for SailPoint. None of the three briefs above contains any INR value or Indian-namesake fundamentals.

**Control: Hindustan Aeronautics under IN.**
- Resolves HAL / Hindustan Aeronautics Limited / NSE / IN.
- Fundamentals: **HAL.NS, Hindustan Aeronautics Limited, INR, P/E 33.00, mcap 3.077T**, which is still the IN listing.
- The structured price leg timed out at the 6 s box on both runs ("price timed out after 6s — dropped"). The same box timed fundamentals out on the cold first run. This is the separately filed R15-LEAD-128 (history fetched before the quote; out of scope).
- The IN quote itself is served by the copilot call below (4601.0 INR, nse_direct).

**Copilot path** (MCP `price_data` / `fundamentals` on the candidate, session IN):

| call | result |
|---|---|
| `fundamentals {symbol:'HAL', region:'US'}` | ok, **HAL, Halliburton Company, USD, P/E 16.68, mcap 26.54B** |
| `fundamentals {symbol:'HAL'}` | ok, **HAL.NS, Hindustan Aeronautics Limited, INR, P/E 33.00, mcap 3.077T** (today's behaviour kept) |
| `price_data {symbol:'HAL', region:'US', period:'1mo'}` | ok, quote **HAL 31.85 USD** (yfinance) |
| `price_data {symbol:'HAL', period:'1mo'}` | ok, quote **HAL 4601.0 INR** (nse_direct) |

**Teardown.** I stopped my processes by pid: sleeps 71013/71015/71019, sh 71017, python 71020, openbb 71014/71033, edgar 71016/71039. None remain, and nothing listens on 52930-52932.

## Residual (not part of this claim; recommend filing)

The **news** leg in `gather_fast._structured` (`fast.py` ~689-694, `_safe_call(tool_call, "news", {"symbols": [symbol]})`) runs outside `snapshot_structured`. It therefore still resolves the bare ticker under the session region.
- **Observed live:** the Halliburton brief's `structured.news.data[0]` (and `brief.structured.news`) is "India's Hindustan Aeronautics posts strong quarterly results…" (Reuters, 12 Aug).
- This is the same wrong-entity-ticker-collision class, on a non-money leg.
- The behaviour is unchanged from base, so it is not a regression.
- It falls outside this claim's acceptance, which covers price and fundamentals, and outside its fix shape, which is the `snapshot_structured` fan-out.
- Suggested fix: scope the news leg (or the whole `_structured` gather) to `target.region` in the same way. Severity medium.
