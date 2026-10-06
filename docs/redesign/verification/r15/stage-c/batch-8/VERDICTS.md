# R15 Stage C: Batch 8 Verdicts (fresh-context verifier)

- **Merge target:** `worktree-agent-batch-8-int@04eb5e16092eb8643a93270a82c9bb28ac7922f0` (base `b47ed2d`).
- **Verifier:** Opus, fresh context. Every verdict comes from one of three sources: the running sidecar, the vitest-executed frontend path against that sidecar (or a throwaway Node engine that really dies), or the outside world. The outside-world checks used Binance, Coinbase, Yahoo chart meta, the World Bank API, api.imf.org, live NSE archives, and BSE ComHeader truth recorded in the battery packs. No verdict comes from reading the diff.
- **Tally:** 47 planned. Result: **39 certified, 1 needs GUI (LIFECYCLE-001), 7 not certified.** The 7 break down as 3 real residuals (DATA-061, UI-053, RESEARCH-027), 1 partial landing the integrator did not claim (UI-015), and 3 not delivered (AGENT-046, CODE-AGENT-008, CODE-PLATFORM-021). No not-a-defect proposals.
- **Verdict:** approve. The chain is green and nothing certified is a regression. The three residuals are narrower than their base defects: none makes the product worse than base.

## Rig

- Scratch worktree `batch-8-verify` at `origin/worktree-agent-batch-8-int` (detached, `04eb5e1`). `sidecar/.venv`, `node_modules` and `src-tauri/binaries` are symlinked from the integrator's `batch-8-int` worktree, which uses the same lockfiles.
- Data dir: `batch-8-verify-data`, copied from `vysted-iso/data` (the keyless ISO profile).
- Sidecars, each started from source with stdin held by a sleep pipe; the MCP env vars point at the ISO `:52153`/`:52154`:
  - **Main sidecar** on `127.0.0.1:52310`.
  - **Network-down sidecar** on `:52311`: every proxy env var points at a dead port and loopback is exempt. It gave a real transport failure for yfinance, requests and httpx. The NSE/BSE clients ignore proxies, so their legs still answered.
  - **Throwaway sidecar** on `:52312` with a bad and an `openrouter` agent JSON dropped into the scratch `agents/`. Both files were removed afterwards.
- Models:
  - Local `llama3.1:8b` via Ollama for the agent research run.
  - One OpenRouter free-slug delegate run (`nvidia/nemotron-3-super-120b-a12b:free`, key read in-process), logged to the spend ledger as `free: true`.
  - OpenAI-direct: not used.
- Scratch vitest files `src/zz-b8v-*.test.ts(x)` live in the scratch worktree only and were never committed. They drive the real stores, components and `sidecar-client` against `:52310` through the `?sidecar-port=` path, or against a Node `http` engine that is closed mid-test.
- Yahoo throttled the session IP (429 on `getcrumb`) for most of the window, which affects RESEARCH-027 timing and forced the LEAD-005 probe onto US ADRs.

## Chain observed at the target (`04eb5e1`, verifier re-run)

| Gate | Result |
| ---- | ------ |
| `pnpm exec vitest run` (full) | 136 files, 1616 tests passed, EXIT 0 |
| `pnpm typecheck` / `pnpm lint` / `pnpm format:check` | EXIT 0 / 0 / 0 |
| `pytest` (sidecar, full) | 2872 passed, 1 skipped, EXIT 0 |
| `ruff check` / `ruff format --check` | "All checks passed!" / "414 files already formatted" |
| `cargo fmt --check` / `cargo test` / `cargo clippy --all-targets -D warnings` | EXIT 0 / 19 passed / EXIT 0 |
| `pnpm ci-local` (integrator, `b8int-ci-1.log`) | `CI_EXIT=0` (2872 passed) |
| `node scripts/smoke-test-sidecars.mjs` (integrator) | all three sidecars booted and torn down cleanly |

## Per-entry evidence

### W1: sidecar lifecycle and transport

- **R15-LIFECYCLE-001: needs GUI.**
  - Headless evidence: the Rust pin `boot_returns_at_once_and_spawns_the_sidecar_before_any_mcp_bind_wait_ends` passes. `setup()` now hands `spawn_boot(start_openbb, start_sec, start_main)` to one thread. The env vars are set in `start`, before the main spawn, and the bind waits run after it.
  - A GUI round must check four things on a packaged cold launch (after a reboot):
    1. The window paints and accepts input while both MCP children are still binding. No beachball for 25-90 s.
    2. The data engine answers `/health` before the MCP binds finish.
    3. Rename the bundled `vysted-sidecar` binary and launch: the status chip goes red and panels name "The data engine could not start (...)" at once, not after 120 s.
    4. Kill the running sidecar: the chip flips to "Sidecar error", and panels and chat say "The data engine stopped (exit code ...)".
- **R15-LIFECYCLE-010: certified.**
  - Rust: `a_spawn_failure_reaches_the_renderer_as_failed_with_its_reason` and `the_boot_wait_keeps_an_earlier_exit_reason` pass.
  - Renderer (vitest, real `sidecar-client`; only the Tauri boundary is mocked): `get_sidecar_port` returned `{state:"failed", reason:"The data engine could not start (No such file or directory (os error 2))."}`. `getSidecarBaseUrl` rejected with that reason in 0 ms, as status 0, with **0 fetches**, so there is no 120 s probe.
  - The packaged renamed-binary launch is on the LIFECYCLE-001 GUI list.
- **R15-UI-014: certified.**
  - Real fetch against a Node engine that answered and was then closed. `sidecarGet("/quotes/AAPL")` threw `SidecarError` status 0: "The data engine is not responding — it may have stopped. Restart Vysted." It never threw `fetch failed` or `Load failed`.
  - `lib.rs` now handles `CommandEvent::Terminated`: it sets Failed and emits `vysted://sidecar-terminated`. `store/app.ts` listens for it. The live kill is on the GUI list.
  - Residual, see Issues 1: outside the Tauri status the next call after a death waits the full 120 s probe.
- **R15-LIFECYCLE-011: certified.** Real store and client against the dying engine. The status went `connected -> error ("The data engine is not responding…") -> connected` after the engine came back on the same port. The 20 s re-probe runs while in `error`.
- **R15-UI-012: certified.** The real `streamAgentInvocation` against `:52310`:
  - `POST /agents/nope/invoke` reached `onError` as `unknown agent: 'nope'`.
  - A 422 array from `mode:"bogus-mode"` arrived as `mode: Input should be 'agent', 'ask', 'edit', 'build' or 'delegate'`.
  - No JSON body reached the transcript.
- **R15-CODE-PLATFORM-011: certified.** The real `launchDelegateRun` against `:52310`, using the register's exact 422 (`budget.max_tokens:"abc"`). The rail run ended with the detail `Could not start: max_tokens: Input should be a valid integer, unable to parse string as an integer`. `[object Object]` never appeared. The class case: `cancelDelegateRun` on an unknown run returned `Cancel failed (unknown run: 'run-does-not-exist-b8v') — retry.`
- **R15-RESEARCH-032: certified.** The real `SettingsPanel`:
  - Against `:52310` the chip reads **Ready**, from the real Docker SearXNG.
  - Against a Node engine, the chip followed a status flip from Ready to **Error** on a window `focus`. The writers pinned `visibilitychange`, so `focus` is the case the fix was not written against.
  - A hardware 500 rendered "Hardware detection unavailable: sysctl hw.memsize failed".
  - A failed Set up POST rendered "That did not go through: docker pull failed: no space left on device" instead of "sidecar not connected".
- **R15-LIFECYCLE-023: certified.** A fresh case: a panel that throws on a later state update, not on its first render. It showed "This panel crashed. series.setData on a disposed chart" with Reload panel and Copy error, and the sibling "Portfolio holdings" kept rendering. React 19's root `onCaughtError` received the error; `main.tsx` forwards it to `diag_log_line`. `PanelHost` passes the wrapped map to `DockviewReact`.

### W2: provider readiness and host actions

- **R15-UI-013: certified.** The real `validateProvider` against `:52310`:

  | Provider / condition | Result |
  | --- | --- |
  | `openrouter` with no key | `not_configured` "No API key is set for OpenRouter." |
  | `openai` with a fake key | `invalid` "OpenAI rejected this key." |
  | `ollama` / `gemma3:4b` | `model_not_pulled` |
  | `ollama` / `llama3.1:8b` | `ok` |
  | Network-down sidecar, `openai` | `unreachable` "Could not reach OpenAI (APIConnectionError: Connection error.)." |
  | Engine that hangs on validate | `unreachable` in 15,001 ms ("No answer within 15 s") |
  | Caller's Cancel | Rejected with AbortError in 303 ms |

  `ChatSidebar` opens onboarding only on `not_configured` (and on `model_not_pulled`, onboarding opens at the download step). An unreachable engine keeps the prompt and names the cause.
- **R15-AGENT-028: certified.**
  - `POST /llm/keys/validate {ollama, gemma3:4b}` returned `{"ok":false,"reason":"model_not_pulled","detail":"gemma3:4b is not downloaded in Ollama (local) yet."}`. The pulled `qwen3:8b` returned ok.
  - The live chat on the unpulled model sent an error frame: `code:"model_not_pulled"`, "The model gemma3:4b is not downloaded in Ollama.", action "Run `ollama pull gemma3:4b`…". Before the fix this was "pick another model".
- **R15-UI-057: certified.** Keys with trailing space or newline for openai, anthropic, groq, deepseek and gemini all come back `invalid` ("<Provider> rejected this key."). Before the fix they came back as "transport error: Connection error.". `KeyEntryDialog` saves `key.trim()`.
- **R15-UI-049: certified.** The real `promoteKeyedProvider` with live readiness:
  - Default `ollama` with the unpulled `gemma3:4b`: saving an OpenRouter key promoted it (`true`, default became `openrouter`).
  - Default `ollama` with the working `llama3.1:8b`: `false`, default stayed `ollama`. A working local lane is never displaced.
- **R15-UI-019: certified.** The real `OnboardingBanner` with live probes:
  - Ollama default with a working `llama3.1:8b`: renders nothing.
  - Ollama default with the unpulled `gemma3:4b`: renders the setup copy.
  - Dismissal is persisted as keychain `app-meta:onboarding-banner-dismissed = "dismissed"`, beside the seen marker.
- **R15-CODE-AGENT-006: certified.**
  - The TS `DEFAULT_MODEL_BY_PROVIDER`/`KNOWN_MODELS_BY_PROVIDER` equal the live `GET /llm/providers` for all 8 providers (0 diffs).
  - Editing the registry JSON's ollama default reached both TS tables: `b8v-new-default:1b`.
  - A restored JSON-only model (`b8v-json-only:2b`) is not pruned.
- **R15-AGENT-055: certified.**
  - For each template, `planLayout` places exactly the JSON's roles: single-focus = chart (maximised); research-cockpit = chart, equity-overview, brief, news; compare = chart; macro-scan = macro, chart, screener.
  - The `arrange_layout` description is generated from the same `layout_templates.json`. It no longer promises "dual charts", "heatmap" or "stats".
  - The menu now speaks modes (fundamental, technical, macro, compare-desk). Its historical payload ids are mapped once in `MENU_PAYLOAD_TO_MODE`.
- **R15-AGENT-056: certified.** The real `applyHostAction("arrange_layout", {})`, plus a fresh case with `{pattern:"zzz-not-a-pattern"}`:
  - Both kept the chart drawing and `{news:false, screener:false}`.
  - The only dockview effect was `clear` plus the default arrangement.
  - The gate reads "Reset the panel arrangement (drawings and modules kept)".
- **R15-AGENT-081: certified.** The real `EquityOverviewPanel` on live TATASTEEL data, using a metric the writers did not pin:
  - `open_company_overview {highlight:"roe"}` returned "Opened TATASTEEL's overview — spotlighting ROE", and exactly 1 row (ROE) carried `data-highlighted`.
  - `highlight:"moat_score"` returned "…"moat_score" is not a metric on that panel, so nothing is spotlit", with 0 rows highlighted.

### W3: data-error honesty

- **R15-DATA-061: not certified.**
  - What holds live:
    - `/quotes/ZZZZNOTREAL` → 404 `not_found` with the sentence. It was a 502 with `'PriceHistory' … '_dividends'` before.
    - `/fundamentals/ZZZZNOTREAL` → 404.
    - On the network-down sidecar, `/history/AAPL` and `/macro/search?provider=world-bank` → 503 `network` "Could not reach the data provider".
    - Throttling surfaces as 429 `rate_limited`.
  - What still reproduces: the entry's own `curl /macro/GDP` → 502 `provider_error` with raw library text: `World Bank upstream error for 'GDP'/'IND': APIError: JSON decoding error (https://api.worldbank.org/v2/en/sources/2/series/GDP/…)`, action "Retry, or try again later.".
  - Other raw text on the same path:
    - The US-region legacy path returns the nested openbb-mcp error dict (`Missing credential 'fred_api_key'`).
    - A fresh class case, `/history/XYZ%2FABC`, returns `yfinance history failed for 'XYZ/ABC': 'Response' object has no attribute 'get'`.
    - IMF upstream 404s are classified `provider_error`/502.
  - The mapper keeps `str(exc)` as `detail` for `kind=None` (`errors.py:83`), against C5.
- **R15-AGENT-061: certified.**
  - Over MCP, `fundamentals {symbol:"ZZZZNOTREAL"}` returned `{"ok":false,"reason":"not_found"}`.
  - The register's two exact messages, raised as `ProviderError(kind="not_found")` through `_fetch_once`, both classify `not_found`.
  - A `network` kind classifies as `provider_error` (our feed's gap).
  - KSE.NS and 509470.BO now return real Yahoo records.
- **R15-AGENT-030: certified.** The exact guard `error_frame` that both SSE routers call:
  - Given `RuntimeError('runs_store: database connection is closed')`, `ValueError("could not parse depth 'ultra2'")`, the `TypeError` for `research_depth`, and `KeyError('connect_args')`, it yields `code:"internal"`, "The terminal hit an internal error.", with `type: message` in detail. Before the fix these were network, parse_error or provider blame.
  - A real `httpx.ConnectError` still humanizes to `network`.
  - The live guard could not be triggered headlessly: bad options are absorbed upstream.
- **R15-LEAD-005: certified.** Live `/quotes` for US ADRs mid-session at 14:32:42Z:
  - NSRGY stamped `2026-09-24T14:15:12Z` and TKOMY stamped `14:12:55Z`. Both equal Yahoo's chart `regularMarketTime` exactly, not now().
  - Closed-market probes (Tokyo, HK, ASX) were blocked by a pre-existing symbol-mapping bug (Issues 4). An in-process run with Yahoo's real 7203.T trade time (06:30Z) stamped 06:30Z at 14:31Z.
- **R15-UI-053: not certified.** Routing is fixed: IMF ids reach the provider. The outcome still stands from the outside world: all 8 IMF catalog ids return 502 `IMF upstream error … 404 Client Error: Not Found for url: https://api.imf.org/external/sdmx/2.1/data/IFS/…`. `api.imf.org` answers 204 for the SDMX 2.1 `IFS` dataflow, and 200 for SDMX 3.0 dataflows such as `CPI`. The Macro panel's IMF provider is still 100% dead, the India series included.
- **R15-DATA-081: certified.**
  - Live `GET /quotes/BTC%2FUSDT?asset_class=crypto` returned 84,240.01 USDT from `ccxt:binance`; Binance said 84,229.03 in the same second.
  - The real portfolio `fetchPositionQuotes` priced BTC/USDT at 84,896.72 USDT and ETH/USDT at 2,695.53 USDT (Binance: 2,695.47), with 0 failures.
  - The chart's real `sidecarApi.history("ETH/USDT", "1d", undefined, "crypto")` returned 365 bars via `ccxt:binance`.
  - A watchlist crypto row opens the chart, not the overview (writer vitest, passes in the full run).
- **R15-UI-030: certified.** The real `MacroPanel` and `sidecar-client` against `:52310`:
  - Mount made one `/macro/DGS10?provider=fred` call (a deterministic keyless 502 showing the FRED-key sentence) and no retry.
  - Clicking the ECB tab made exactly one call, for ECB's own default `FM.D.U2.EUR.4F.KR.MRR_FR.LEV`, which loaded (MRO).
- **R15-UI-029: certified.** The real `MacroSeriesPicker` against a Node engine whose `/macro/catalog` answered 503. It showed "Could not load featured series." with Retry and no skeleton. After the engine recovered, Retry rendered the catalog row.
- **R15-UI-015: not certified (not claimed, partial).** The integrator recorded that earnings and screener still flatten the error. The macro leg holds live: see UI-030, one attempt on a deterministic 502.

### W4: resolver and exchange lanes

- **R15-DATA-058: certified.** Live `/resolve?q=Sify Technologies Ltd (ADR)` now lists `SIFY US 0.913` in the last slot. Before, it listed 6 Indian rows only.
  - Fresh cases: "MakeMyTrip Limited (ADR)" lists `MMYT US 0.7778`, and "Wipro ADR" keeps WIPRO (NSE) first with WIT (US) listed.
  - "Infosys Ltd ADR" still leads with INFY (NSE).
- **R15-LIFECYCLE-019: certified.** The live NSE master (HTTP 200, 68,974 bytes) was served through a MockTransport that raised `ConnectTimeout` first.
  - After the failed attempt: `attempts 1`, lane off, `_refreshed_on None`. The log named the exception type.
  - After the backoff: `attempts 2`, lane on, `_refreshed_on 2026-09-24`, and GUJGASLTD → GUJENERGY (effective 2026-07-01).
  - Live `/resolve?q=GUJGASLTD` carries `rename` and `rename_lane: available`.
- **R15-LIFECYCLE-022: certified.**
  - Primary UDiFF forced to 404, legacy served live from NSE: `fetch_latest` returned 2026-09-24 with 2,927 rows, and no holiday markers were written.
  - Both hosts 404: `None`, 0 empty markers on trading days, and a WARNING "2 past trading days 404 on both hosts (latest https://nsearchives…20260922…) — has the archive path moved?".
- **R15-UI-039: certified.** Live `/resolve/autocomplete`:
  - `GUJGASLTD` → GUJENERGY, `former_name: GUJGASLTD`, ISIN INE844O01030, BSE 539336, FV 2 (Gujarat Gas's real ISIN and code).
  - Fresh case: `ZOMATO` → ETERNAL with the rename block, INE758T01015, 543320.
  - `INFY` rows carry ISIN INE009A01021, BSE 500209 and industry, where these fields were always null before.
- **R15-CODE-DATA-002: certified.**
  - In-process with the live lookup stubbed: 'infosys' took 205.7 ms and 16,255 `SequenceMatcher.ratio` calls, then 0.1 ms and 3 calls on repeat.
  - 'hdfc bank limited results' took 421.7 ms, then 0.1 ms.
  - A rename map injected after the memo still applied: TMPV → NEWSYM with `former_name` TMPV, so the rename stays outside the memo.
  - Live repeat `/resolve` calls: 0.70 s → 0.003 s.
- **R15-CODE-DATA-003: certified.**
  - The MCP `resolve_symbol` tool returns the same dict as `/resolve` for GUJGASLTD, including the `rename` block with `effective_date` and `note`.
  - Confidences match to 4 places on a fuzzy query (`MMYT 0.7778`, `EMAMILTD 0.6857`).
- **R15-DATA-051: certified.** Live `/resolve` and the agent tool carry the fields, and they match BSE truth from the battery packs:

  | Symbol | board | group | face value |
  | --- | --- | --- | --- |
  | SMR | SME | M (BSE now reports M; the old master said MT) | 10 |
  | ELCIDIN | mainboard | B | 10 |
  | CREST | mainboard | B | 10 |
  | RELIANCE | mainboard | A | 10 |

  `/fundamentals` does not echo these fields; the plan scoped identity to the resolve payload (Issues 7).
- **R15-AGENT-045: certified.** MCP `compare_symbols`:
  - `["COCHINSHIP","MAZAGONDOCK"]` now returns the per-symbol reason "unresolved name: 'MAZAGONDOCK' is not a known ticker and matched no listing — retry with the company name or the exact exchange ticker", in both `symbols[]` and `message`. Before, it was a bare "fewer than two symbols resolved".
  - Fresh case: `["Cochin Shipyard","Mazagon Dock"]` → ok, COCHINSHIP ₹1,370 and MAZDOCK ₹2,202, resolved from names.
- **R15-DATA-084: certified.**
  - The register's stub payload now yields `[('2021-01-04', 0.0), ('2021-01-05', 0.07)]`. Before, it was `None`.
  - Class mate: a quote with `volume: 0` stays `0.0`.
- **R15-DATA-085: certified.** Live `/macro/NY.GDP.MKTP.CD?provider=world-bank` is titled "GDP (current US$) — IND". The 2025 value, 3,956,067,115,771.63, equals `api.worldbank.org`'s IND 2025 figure and indicator name. Fresh cases: SL.UEM.TOTL.ZS and FP.CPI.TOTL.ZG are also titled.
- **R15-DATA-086: certified.**
  - Real `requests` transport forced down: `macro_router.search('unemployment','world-bank')` raised `ProviderError kind=network`, and the cache key stayed empty.
  - Network restored: 25 real World Bank hits.
  - On the network-down sidecar, `/macro/search?provider=world-bank` → 503 `network`.

### W5: agent runtime and research

- **R15-CODE-AGENT-004: certified.** Real `google.genai` `GenerateContentResponse` objects were passed through `GeminiProvider.stream_chat`:
  - Input: prompt 1000, tool-use 200, candidates 800, thoughts 6000.
  - Usage came out as input 1200, output 6800.
  - `BudgetGuard(max_tokens=7000)` then breached: "token ceiling 7000 reached (8000 used)".
- **R15-LEAD-019: certified.**
  - A live delegate run on `nvidia/nemotron-3-super-120b-a12b:free` (the register's slug) finished `done` with `cost {tokens: 15438, spend_usd: 0.0}`. Batch 7 recorded 0.12979 for 64,895 tokens on the same slug.
  - Paid slugs still meter: `deepseek/deepseek-v4-flash` $0.05841 and an unlisted paid slug $0.12979 for 64,895 tokens.
- **R15-CODE-AGENT-007: certified.** Dispatch hosts equal the registry for deepseek, xai and openrouter. After editing the registry rows in-process, `get_provider("deepseek"/"xai")` dispatched to `https://edited.deepseek.example/v9` and `https://edited.x.example/v2`.
- **R15-CODE-AGENT-016: certified.** On the `:52312` sidecar, an agent JSON with `defaultProvider:"openrouter"` loaded: roster 14, where `:52310` had 13. The schema enum now lists all 8 registry ids.
- **R15-LIFECYCLE-014: certified.**
  - On `:52312`, `/health` returned `agents_degraded: [{"file":"zz-b8v-bad.json","reason":"schema violation: ['defaultProvider']: 'notaprovider' is not one of [...]"}]`. `:52310` shows `[]`.
  - A missing agents dir logs `ERROR agents directory not found at … no agents will load` and reports itself in `agents_degraded`.
  - The smoke test asserts the roster and `agents_degraded`.
- **R15-CODE-RESEARCH-003: certified.** `run_deep_research` is gone. With `run_iter_research` and `run_heavy_research` forced to raise, `_run_loop` returns `{ok: false, message: "Deep research could not finish — the iter research loop failed: RuntimeError: …", execution_loop: "iter"}` (and "heavy" likewise). No second, drifted loop runs.
- **R15-RESEARCH-027: not certified.**
  - Live NORMAL wall over MCP: KSE 7.7 s, Tata Steel 9.2 s, Crest Ventures 11.3 s, Fusion Finance 19.7 s.
  - Through the agent (llama3.1:8b), research began and finished in 16.1 s. The step log carries latency_ms: resolve 726 ms, web 5,695 ms (runs concurrently), witnesses 0 to 4,833 ms, and "52-week range cross-check timed out after 6s — dropped" (6,003 ms). But "pulled 4/4 data sources" took 15,401 ms.
  - Two of five cold runs miss the ≤15 s target. The price/fundamentals legs are not time-boxed, and Yahoo throttling was active during the window.
- **R15-AGENT-046, R15-CODE-AGENT-008, R15-CODE-PLATFORM-021: not certified (not delivered).** For CODE-AGENT-008, the live research tool result still has no `brief` key.

## Issues (outside the entries; not in any diff)

1. **120 s wait after a transport failure outside the Tauri status.** `sidecarFetch` nulls `readyPromise`, so the next call re-runs the 120 s `/health` probe, then fails with "The data engine did not become ready in time." (503). That message overwrites the precise reason. Live: call 1 took 3 ms, call 2 took 120,238 ms. Inside Tauri, a crash sets Failed through `Terminated` and short-circuits. A hung but unexited engine would still hit this.
2. **The status chip never shows the reason.** `StatusChrome` never renders `sidecarError`, so a terminated engine reads "Sidecar error" with no reason in the chip or its tooltip. Panels do show the reason.
3. **Raw text for unclassified provider errors (DATA-061 residual).** `ProviderError(kind=None)` keeps raw library text in `detail`, with a "Retry" action even for a missing credential or an unknown series.
4. **Pre-existing: foreign suffixes are mangled.** `_yahoo_symbol` rewrites every non-Indian foreign suffix with a dash: BHP.AX → BHP-AX, 0700.HK → 0700-HK, 7203.T → 7203-T, VOD.L → VOD-L. Yahoo then says "possibly delisted", which the new classifier maps to 404 "check the symbol". Every non-US, non-IN listing is unquotable.
5. **IMF catalog is dead upstream.** It needs the SDMX 3.0 dataflows (UI-053 residual).
6. **Empty web search reports success.** `web_search` returns `ok:true` with 0 results and no reason when every SearXNG engine is suspended (brave, duckduckgo and startpage returned CAPTCHA or "too many requests" this session). Research then reports the web as available with 0 sources.
7. **`/fundamentals` does not echo `board`/`exchange_group`/`face_value`.** These live on the resolve identity only. The register's DATA-051 fix shape named fundamentals identity too.
8. **Adapter humanize blames the provider for our own errors.** A pydantic validation error from a bad `options.tools` reads "Something went wrong with Ollama".
9. **`std::env::set_var` now runs while the main loop is live.** `openbb_mcp::start`/`sec_edgar_mcp::start` call it on the boot thread while the main event loop runs; before, the main thread was blocked in `join`. `setenv` and `getenv` are not thread-safe on macOS. The chance is low; setting the vars before the boot thread spawns would remove it.
10. **Retired-symbol autocomplete is exact-only.** "ZOMA" and "GUJGAS" list nothing, while the full old ticker works.
11. **`arrange_layout` default claims success before layout mount.** It reports "Reset the panel arrangement…" even when `dockviewApi` is null and `resetLayout` does nothing.
12. **`_quote_time` has no no-time fallback.** It falls back to `history(period="5d").index[-1]`, which raises on an empty frame. A quote whose metadata has no `regularMarketTime` and whose history comes back empty now fails outright instead of pricing with an unknown as-of.
