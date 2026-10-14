# rc1 round 4 — adversarial sample verifier, shard 4 (rc1-vshard-4)

Checkout: `68d5573aff9a579af084dcbb124843f2aecff6e8` (read-only worktree `scratchpad/rc1-round-4-1006c6d-fix-int`).
Own sidecar: :52604 from worktree source, data dir `scratchpad/rc1-round-4-data-rc1-vshard-4`. Scratch checks in `scratchpad/vshard4-r4` (in-process `PYTHONPATH=. sidecar/.venv/bin/python <script>`, scratch vitest `node_modules/.bin/vitest run --config $X/vitest.scratch.config.ts` from the worktree).
No Ollama, no OpenAI spend. Working log: `logs/rc1-vshard-4.md`.

## Tally

- 20 holds.
- 4 refuted / not certified: R15-LEAD-022, R15-RESEARCH-027, R15-UI-015, R15-UI-058.

## Verdicts

| id | verdict | entry repro | fresh variant |
|---|---|---|---|
| R15-UI-029 | holds | worktree vitest 19/19 | scratch vitest: an ECB series going 503 → TypeError → success shows error + Retry each time and never the skeleton |
| R15-AGENT-061 | holds | repro tickers → not_found | live NOSUCHCOXQ.NS and 999991.BO → not_found; financial_statements tool → not_found |
| R15-AGENT-030 | holds | router guards emit code `internal` | TestClient: TimeoutError on /llm/chat and sqlite OperationalError on /agents/{id}/invoke both → `internal` |
| R15-UI-039 | holds | GUJGASLTD → GUJENERGY with rename + isin | TISCO → TATASTEEL rename (see adjacent 6) |
| R15-CODE-DATA-002 | holds | repeat resolve infosys 291 ms → 0.1 ms | 'bharat heavy electricals' 762 ms → 0.1 ms (the memo is `_scan_names` lru_cache) |
| R15-CODE-DATA-003 | holds | tool dict == router payload for GUJGASLTD | TISCO: same, including the rename block |
| R15-LEAD-019 | holds | `:free` slugs rate 0.0 | 20 metered rounds → spend 0.0 |
| R15-CODE-AGENT-007 | holds | patched registry host reaches deepseek dispatch | xai and openrouter follow the patched host too (see adjacent 3) |
| R15-CODE-AGENT-016 | holds | openrouter/deepseek/xai load | a bogus defaultProvider is rejected and listed as degraded |
| R15-CODE-AGENT-008 | holds | brief attached at all 3 engine returns | stubbed web shapes (results+snippet, citations+excerpt) → non-empty sources, mode fast/quick |
| R15-RESEARCH-027 | **refuted (not certified)** | literal cold NORMAL now 6.0–8.9 s live (4 names) | keyless engines stalled (each hits ENGINE_DEADLINE_SECS 6 s): NORMAL 'Saksoft' 19.5 s, 'Tata Elxsi' 18.4 s > 15 s |
| R15-CODE-AGENT-005 | holds | only allow-listed keys reach the adapter | {depth, someNewKey, research_depth, modelWebSearch, temperature} → only temperature |
| R15-CROSS-PLATFORM-002 | holds | AST pin test exists | 183 passed under LC_ALL=en_US.ISO8859-1 PYTHONUTF8=0 |
| R15-LIFECYCLE-018 | holds | concurrent cold reads both get the URL | after warm_detect the hot path makes 0 docker calls |
| R15-DATA-094 | holds | fake key → x-news-sources newsapi=unauthorized | /news/sources/status → unauthorized; direct newsapi 401; vitest 78/78 (see adjacent 5) |
| R15-UI-015 | **refuted (not certified)** | 404 → 1 attempt; 503 retries | fix_shape "keep the reason in sec.searchCompanies" not done: sec.ts:257-258 |
| R15-DATA-052 | holds | ELCIDIN.BO / NAPEROL.BO → Financial Services / Investment Company, sector_source resolver | Yahoo '' → None; SAKSOFT.NS → Technology |
| R15-LEAD-022 | **refuted** | 'any non-US, non-IN foreign listing' reproduces | 2222.SR, SAP.F, GGAL.BA → 404 |
| R15-LIFECYCLE-021 | holds | fall-throughs surface on /system/provider-health | NSE refused and NSE 404-moved: count 4, /health "nse_direct failing" |
| R15-DATA-073 | holds | live NSE 2026 master == bundled list (20/20) | regenerator + pin test exist |
| R15-UI-053 | holds | all 10 IMF catalog series → 200, 40–1519 obs, 1.2–2.0 s | CPI/USA.CPI._T.IX.M (not catalogued) → 859 unique monthly obs, 0 duplicate dates |
| R15-CROSS-PLATFORM-004 | holds | the palette carries all 5 menu payloads | scratch vitest: invoking each calls applyLayoutMode ×4 plus resetToDefaultLayout ×1 (see adjacent 7) |
| R15-UI-058 | **refuted (not certified)** | {} and {theme:'dark'} → error | a recognised section key with only unrecognised content → green "Imported settings." |
| R15-DATA-092 | holds | the hint states what region controls; "Defaults to India" is derived | regionConfig('XX') falls back to India; the sidecar default is IN |

## Refutations — commands, checkout and output

### R15-LEAD-022 (high) — the foreign-listing dash rewrite still applies outside a 37-suffix allowlist

- **Checkout:** `68d5573aff9a579af084dcbb124843f2aecff6e8`.
- **Commands:**
  - In-process: `yfinance_provider._yahoo_symbol(s)`.
  - Live: `curl -s http://127.0.0.1:52604/quotes/2222.SR` (also SAP.F and GGAL.BA).
  - Direct: `curl 'https://query1.finance.yahoo.com/v8/finance/chart/2222.SR'` (also `2222-SR`).
- **Output:**
  - `_yahoo_symbol` gives 2222.SR→2222-SR, SAP.F→SAP-F and GGAL.BA→GGAL-BA. The same dash rewrite hits OPAP.AT, CEZ.PR, FALABELLA.SN, QNBK.QA, COMI.CA, WEED.CN, AAPL.NE and EMAAR.AE.
  - :52604 /quotes for 2222.SR, SAP.F and GGAL.BA → HTTP 404 not_found, "check the symbol".
  - Yahoo direct:
    - 2222.SR → 25.78 SAR; SAP.F → 185.2 EUR; GGAL.BA → 6290 ARS.
    - 2222-SR and SAP-F → "No data found, symbol may be delisted".
- **Why this fails:**
  - The fix is `_YAHOO_EXCHANGE_SUFFIXES`, a 37-entry allowlist. Every other real Yahoo suffix still gets the class-share dash rewrite.
  - The literal examples (BHP.AX, 0700.HK) are in the allowlist, so they hold. The entry's repro ("any non-US, non-IN foreign listing") does not.

### R15-RESEARCH-027 — NORMAL research is not bounded when the web round stalls

- **Command:** `cd <W>/sidecar; PYTHONPATH=. ./.venv/bin/python scratchpad/vshard4-r4/r027.py`. The keyless engines' `search()` is patched to `await asyncio.sleep(60)`; NORMAL depth, cold.
- **Output:**
  - `{"q":"Saksoft","wall_s":19.5,...,"web":{"available":false,"reason":"unreachable","note":"No web-search backend configured — structured data only"}}`
  - `{"q":"Tata Elxsi","wall_s":18.4,...}`
- **Unfixed claims:**
  - The web round is not time-boxed at the fast level. keyless allows 3 × 6 s, and the SearXNG lane has a 20 s timeout.
  - fast.py:694 runs `asyncio.gather(_structured(), _web())`.
  - The fix_shape step "publish the structured cockpit as soon as the gather returns (before web + prose)" is absent.
  - The literal cold repro no longer reproduces (6.0–8.9 s live).

### R15-UI-015 — `sec.searchCompanies` still discards the failure reason

- **Command:** `sed -n 250,262p src/store/sec.ts` at 68d5573a.
- **Output:** `catch { set({ searchResults: EMPTY_SEARCH, searchStatus: "error" }); }`. No SEC UI reads `searchStatus`, so a failed company search looks the same as "no match".
- **What holds:** the retry classification. A fresh scratch hook test gave SidecarError 404 → exactly 1 attempt over 60 s, and 503 → retries.

### R15-UI-058 — a recognised section key with unrecognised content still reports success

- **Command:** from the worktree, `node_modules/.bin/vitest run --config scratchpad/vshard4-r4/vitest.scratch.config.ts` with `ui058.test.tsx`. The test renders SettingsPanel and imports each bundle through the "Import settings file" input.
- **Output:**

  | imported bundle | status shown |
  |---|---|
  | `{keybindingOverrides:{"no.such.action":"Mod+X"}}` | "Imported settings. Secrets re-enter via the keychain." |
  | `{settings:{theme:"dark",fontSize:14}}` | same |
  | `{enabledModules:{"not-a-module":true}}` | same |
  | `{searchSettings:{colour:"blue"}}` | same |
  | `{version:2}` | "Could not read that file — expected a Vysted export." |

  Nothing is applied in the first four cases: region US is kept and the palette.open remap is kept.
- **Cause:** `ExportImportSection` sets `appliedAny = true` whenever a section key holds an object, not when a field inside it was applied.
- **What holds:** export v2 content, the full round-trip (GLOBAL / openai gpt-5.1-mini / a module toggle), merge-over-current and unknown-id rejection.

## Adjacent findings (different defects near sampled entries)

1. **Medium, near CODE-AGENT-008 / RESEARCH-027 (RESEARCH-022 class).**
   - A Mojeek challenge page counts as a healthy empty answer. Mojeek returns HTTP 200 with "Captcha … JavaScript is required to complete this challenge". `search/mojeek.py` parses that to 0 rows, and `keyless.py` records `any_engine_answered`, so `web_search` returns ok:true with results [].
   - Live NORMAL briefs (4/4: Kaveri Seed, Fusion Finance, Saksoft, Garware Hi-Tech) said web_available true, 0 sources, no note. Meanwhile DDG answered 202 and Brave 429.
2. **Low, near RESEARCH-027.** `research/fast.py` `_web_round` labels configured-but-unreachable keyless engines "No web-search backend configured — structured data only" (~line 526, r027.out).
3. **Low, near CODE-AGENT-007.** `services/research/sonar.py:42` `OPENROUTER_CHAT_URL` and `agent_tools/deep_research.py:795` hardcode `https://openrouter.ai/api/v1/chat/completions`, which bypasses `model_registry.default_base_url_for`.
4. **Low, near UI-015.** Same site as that refutation; recorded as part of the not-certified verdict above.
5. **Low, near DATA-094.** The NewsFeedPanel badge "NewsAPI key rejected" also shows for status `error` (429 / 5xx / network), at `NewsFeedPanel.tsx:282`.
6. **Low, near UI-039.** A prefix of a retired ticker ('GUJGAS') returns [] from both /resolve and autocomplete, while the full GUJGASLTD resolves with a rename.
7. **Low, near CROSS-PLATFORM-004 (test coverage).** No worktree test asserts that the palette corpus contains the layout payloads or that a palette item calls `applyLayoutMode`, which is the fix_shape's pin. Behaviour holds (scratch cp004.test.ts).

## Environment

- Yahoo getcrumb returns 429 throughout (shared IP, many lanes). Cold /quotes takes 6.7–6.9 s and cold /fundamentals 15.8–21.3 s, so cold research price/fundamentals legs time out at 6 s. They are honestly labelled.
- DDG html returns 202 and Brave 429.
- None of this is a product defect; it is noted because it colours the live research timings.
