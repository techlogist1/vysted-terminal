# R15 Stage C: Batch 9 Verdicts (fresh-context verifier)

- **Merge target:** `worktree-agent-batch-9-int@a3b82180b26c0b143ba2c11663e9c15061264933` (base `c1f0fea`).
- **Verifier:** Opus, fresh context. Every verdict comes from one of three sources:
  - the running sidecar on `:52310`;
  - a vitest-executed frontend path against that sidecar, or against a Node `http` engine;
  - the outside world: Yahoo chart meta, raw yfinance upgrades_downgrades, the NSE holiday master, api.imf.org, the SearXNG container, sec-edgar-mcp, SEC company_tickers.json, and the BSE filings in the battery packs.

  No verdict comes from reading the diff.
- **Tally:** 45 planned. **29 certified, 2 need GUI (UI-083, UI-050), 14 not certified.**
  - 3 are integrator-declared partials: AGENT-082, DATA-068, and RESEARCH-028, whose sidecar leg also fails live.
  - 4 have undelivered or false panel/derivation legs: DATA-048/054/055, UI-032.
  - 6 fail a fresh case of their class: DATA-061, UI-028, AGENT-063, UI-027, AGENT-088, UI-018.
  - 1 could not be exercised live: AGENT-049.
  - No not-a-defect proposals.
- **Verdict: approve.** The chain is green, and nothing certified is a regression. Every residual is narrower than its base defect. The one new mislabel is DATA-054's hard-coded "consolidated" basis on standalone filers. It is wire-only (no panel chip renders it) and is recorded as not certified, not as a block.

## Rig

- **Scratch worktree:** `scratchpad/batch-9-verify`, detached at `a3b8218`. `sidecar/.venv` and `node_modules` are symlinked from the integrator's `batch-9-int` worktree, which uses the same lockfiles.
- **Data:** `scratchpad/batch-9-verify-data`, copied from the ISO profile. One `custom:macro-hawk` row was inserted for LIFECYCLE-025.
- **Sidecar:** started from source on `127.0.0.1:52310`. The MCP env vars point at the ISO `:52153` (openbb) and `:52154` (sec-edgar).
- **In-process probes:** used where a live repro needs a dead upstream, with `VYSTED_DATA_DIR` set to a throwaway dir:
  - LEAD-023 (empty frames);
  - LIFECYCLE-021 (dead nseindia session);
  - RESEARCH-027 (stalled leg).
- **Models:**
  - Local `llama3.1:8b` via Ollama, for three agent runs through `vy.py`.
  - OpenAI-direct: only the AGENT-049 probe, which returned 404 (deprecated model), so no spend.
  - OpenRouter free slugs: not needed.
- **Scratch vitest files:** `src/zz-b9v-*.test.ts(x)`, in the scratch worktree only, never committed. They drive the real stores, components and `sidecar-client` against `:52310` via `?sidecar-port=`.

## Chain observed at the target (`a3b8218`, verifier re-run)

| Gate | Result |
| ---- | ------ |
| `pnpm exec vitest run` (full) | 141 files, 1683 tests passed, EXIT 0 |
| `pnpm typecheck` / `pnpm lint` / `pnpm format:check` | EXIT 0 / 0 / 0 |
| `pytest` (sidecar, full) | 2962 passed, 1 skipped, EXIT 0 |
| `ruff check` / `ruff format --check` | "All checks passed!" / "419 files already formatted" |
| cargo | no `src-tauri/` diff in the batch, so unchanged from base |

## Per-entry evidence

### W1: agent runtime

- **AGENT-046: certified.**
  - Live Ollama runs got minted ids: `call_65e94a88c0b243359dbef741fc638794` in run 1 and `call_807b74bc…` in run 2. Before the fix they were `''`.
  - The auto-brief id is `call_224f…__autobrief`, unique per run.
- **CODE-AGENT-008: certified.**
  - Research run 3 ("Research NVDA briefly.") auto-published the tool's brief verbatim, with:
    - backend and web_reason;
    - 6 sources;
    - structured `{derived, filings, fundamentals, news, price}`.
- **RESEARCH-027: certified.**
  - Live run 3: the engine took 13.9 s. The news leg was dropped with "news timed out after 6s — dropped", and "pulled 3/4 data sources".
  - Fresh case, run in-process through the real `snapshot_structured`: a fundamentals leg sleeping 30 s. The call returned in **6.84 s**, with `price` ok, `fundamentals` dropped with the step "fundamentals timed out after 6s — dropped 6002 ms", and `derived` intact.
- **CODE-AGENT-005: certified.** POST `/llm/chat` to openrouter with a fake key and the options `{depth, brandNewComposerControl}`. The result was a 401 auth frame, with no TypeError from an unknown kwarg.
- **LIFECYCLE-025: certified.**
  - A DB-inserted agent had tools `['price_data','macro','news']`. PUT returned 200, with `macro` resolved to `macro_series`.
  - `schemas.openai_tools` gave `['price_data','macro_series','news']`.
- **AGENT-049: not certified.**
  - No live native-search lane was reachable under the guard:
    - the OpenAI `gpt-4o(-mini)-search-preview` models return 404 model_not_found ("deprecated");
    - the OpenRouter paid lane is unfunded;
    - there is no Gemini or Anthropic key.
  - Only the focused tests ran, and 58 passed.
- **AGENT-082: not certified (integrator-partial).**
  - The done frame carries `spend_usd` (0.0 on the local run).
  - `ChatSidebar.tsx` still sets `spendUsd: 0`, and `streaming.ts` does not parse the field.

### W2: search, news, SEC, brief

- **RESEARCH-028: not certified.**
  - `/search/searxng/status` reads `ready` while the container answers 0 results for three real queries. `unresponsive_engines` lists brave, duckduckgo and startpage.
  - The probe query "test" hits wikipedia once, and `_apply_quality` tests `has_results` before `unresponsive_engines`.
  - The research brief reported keyless-fallback with `web_reason: null`.
  - The Settings leg is also missing (integrator).
- **LIFECYCLE-018: certified.**
  - `warm_detect()` runs from the lifespan at boot.
  - The hot-path flag flips only after `refresh()` completes, under a lock.
- **AGENT-063: not certified.**
  - AAPL returns 18 items, all scored and tagged, on the tool path.
  - `symbols=BTC/USDT` returns 0, although the feed carries a Bitcoin options-expiry story; the aliases lack "Bitcoin".
- **DATA-094: certified.**
  - With a fake key in `X-Vysted-Newsapi-Key`:
    - `/news/sources/status` returns `{"newsapi":"unauthorized"}`;
    - `/news` returns the header `x-news-sources: rss=ok;newsapi=unauthorized`;
    - the key appears 0 times in the body and 0 times in `sidecar.log`.
  - A scratch vitest drove the real store against `:52310`. `configure("vysted-news", {newsapi_key: fake})` threw "NewsAPI rejected this key", with 0 `setSecret` calls and grants `[]`.
- **UI-033: certified.** A scratch render of the real `MarketplacePanel` against `:52310`: Configure, paste the fake key, then Save. The form shows "NewsAPI rejected this key", and nothing is written to the keychain.
- **CROSS-PLATFORM-002: certified.**
  - Fresh case: a new scratch test file with `open(p,"w")`, `Path.read_text()` and `p.open()`, none passing `encoding=`.
  - `test_tests_encoding.py` failed and named all three call sites: `:6 open()`, `:9 open()`, `:8 read_text()`.
  - Once the file was removed, the check passed again (3 passed).
- **UI-032: not certified.**
  - Live `/sec/filings/search?q=Apple` (and Tesla, Palantir, AAPL, Microsoft) returns `{"results":[]}`.
  - The installed sec-edgar-mcp 1.0.8 `search_companies` returns `{success: true, companies: [], count: 0}` for every query. Its client swallows `edgar.search()` failures to `[]`, and on a hit the tool layer would read `.cik` off dict rows.
  - `get_cik_by_ticker(AAPL)` → `0000320193` works, and SEC `company_tickers.json` is reachable, so a working local path exists.
- **UI-083: needs GUI.**
  - Headless evidence: the Save .md / Save PDF / Save PNG buttons exist, gated on `bodySettled`, and route through `saveTextArtifact` / `savePdfArtifact` / `savePngArtifact`; the chain vitest passes.
  - The PDF/PNG raster of a settled brief needs the WKWebView.
- **UI-050: needs GUI.**
  - Headless evidence: the slash rows are now `min-h-8 … py-1` (`NotesPanel.tsx:390`).
  - Whether a two-line row still clips is visual.

### W3: fundamentals, identity, earnings

- **LEAD-022: certified.**
  - These all price and match Yahoo chart meta: BHP.AX 61.02 AUD, 0700.HK 438.4 HKD, 7203.T, VOD.L, SAP.DE.
  - Fresh case: BRK.B → BRK-B 507.59.
- **LEAD-023: certified.** In-process, empty metadata plus an empty history gives a clean `ProviderError("… no trade time")`, not an IndexError, and falls through.
- **LEAD-016: certified.**
  - AAPL reported 2025-10-30 and 2026-01-29; MSFT 2025-10-29 and 2026-01-28; `period_end` is the quarter end.
  - Fresh case: RELIANCE.NS reported 2025-10-17 and 2026-07-17.
- **DATA-052: certified.**
  - NAPEROL and ELCIDIN now read Financial Services / Investment Company (the BSE truth), with `sector_source: resolver`.
  - Minor: `field_meta.sector.provider` still says yfinance.
- **DATA-048 / DATA-054 / DATA-055: not certified.** See `VERDICTS.json` for the live values:
  - DATA-048: the ROCE panel leg was undelivered, and ELCIDIN is still unavailable.
  - DATA-054: basis is a hard-coded "consolidated", which is false for SMR (standalone) and ICON.
  - DATA-055: NAPEROL listing_date is Yahoo's data start, and the since-listing panel leg was undelivered.
- **DATA-068: not certified (integrator-partial).** The earnings routes carry `as_of`; the analyst routes do not.
- **DATA-069: certified.** The price-target history and individual targets match raw yfinance upgrades_downgrades:
  - Evercore 365→380 on 09-18;
  - BofA 370 on 09-23.
  - The timeline is titled "Mean of targets revised that day".
- **UI-015: certified.** A scratch vitest against a Node engine returning a deterministic 502, over 9 s:
  - the target makes 1 fetch each for earnings and screener;
  - the base files make 4 each (control run).

### W4: market lanes, errors, quant

- **DATA-061: not certified.**
  - The entry repros are fixed.
  - Fresh case: `/macro/GDP?provider=worldbank` returns 502 with the raw openbb-mcp 422 dict text as detail.
- **DATA-066: certified.**
  - A warm 20-name batch takes 0.002 s (it took 23 s before). Cold batches take 23.4 s and 21.2 s. The watchlist refreshes on a 60 s EOD cadence.
  - Caveat: one contended SPY quote took 8.6 s during a cold batch.
- **DATA-062: certified.**
  - A scratch vitest `WatchlistPanel` against `:52310` shows "RELIANCE.NS … 1,219.20" (matches Yahoo), "ZZZNOTREAL.NS unavailable" and "BHP.AX 61.02".
  - The requested spellings are stamped.
- **LIFECYCLE-021: certified.**
  - A dead nseindia session gives 4 quotes served by `nse`.
  - `fallthroughs` records `('nse_direct','quote',4)`, which is at or above the chrome threshold of 3.
  - The live `/system/provider-health` carries the array.
- **DATA-065: certified.**
  - SPY's 1mo bar dated 2026-09-01 now reads eod (it read stale).
  - RELIANCE.NS's 1wk bar is dated 2026-09-21 (it was a future date).
  - Fresh cases: TCS.NS 1mo and AAPL 1wk.
- **DATA-073: certified.** The app's 2026 NSE holidays equal the live NSE holiday-master CM list, all 20 dates. A regenerator is present.
- **UI-053: certified.**
  - All 10 IMF catalog ids return data.
  - `WEO/IND.NGDP_RPCH.A` 2031 = 6.513934 matches api.imf.org.
- **UI-028: not certified.**
  - Vega and theta are correct and labelled.
  - Rho 13.5565 is unlabelled, in per-unit-rate units (the market convention is 0.1356 per 1%).
- **UI-051: certified.** The Option pricer shows ₹9.2181 for region IN, with a display-currency select.

### W5: frontend shell

These were checked by a scratch vitest on a macOS navigator through the real `resolveKeyboardAction`, `buildPaletteCorpus`, `CommandPalette` (with the real `vystedModules` registered) and `parseSlashCommand`.

- **UI-016: certified.**
  - Cmd+K → `palette.open`, and Ctrl+K on mac → nothing.
  - After remapping to `mod+p`: Cmd+K → nothing, and Cmd+P → `palette.open`.
  - Cmd+1 while typing is skipped. The global Option digits still fire in an input.
- **CODE-FRONTEND-016: certified.** Each of the 13 default ids resolves to a handler in the `page.tsx` dispatcher:
  - `palette.open`, `agent.*` and `changes.*` register via `registerAction`;
  - `platform.*` and `*.open` route through `executeCommand`.
- **UI-086: certified.**
  - Palette rows render "Open Chart ⌘1", "Open Watchlist ⌘2", "Open Portfolio ⌘4", "Open Settings ⌘,", "Save Workspace ⌘S" and "Load Workspace ⌘O".
  - After a remap, "Open News Feed ⇧⌘N" is shown.
  - Option+1 on mac (key `¡`, code `Digit1`) resolves to `agent.mode.agent`.
- **UI-027: not certified.** `conflicts()` still groups raw strings:
  - remapping chart.open to `shift+mod+p` beside `palette.open=mod+p` gives `conflicts() = []`;
  - Cmd+Shift+P then resolves to `palette.open`, so the remap is silently dead.
- **CROSS-PLATFORM-004: certified.**
  - The corpus holds `action:layout:{research-cockpit,single-focus,macro-scan,compare,default}`. This covers every `MENU_PAYLOAD_TO_MODE` key plus reset.
  - The palette renders the five "Layout: …" rows.
- **UI-018: not certified.** Every site the register names confirms. The fresh case fails: the saved-screen delete and Marketplace Remove are still one click.
- **UI-058: certified.**
  - v2 export carries settings, searchSettings, the default provider/model, enabledModules and overrides.
  - `setAll` and `setOverrides` merge over the current state and drop unknown ids; `{}` reports an error.
  - Minor: a file whose only content is unknown action ids still reports "Imported settings."
- **DATA-092: certified.**
  - The hint is derived: "Defaults to India." The section hint names the resolver, calendar, macro/news providers and screener universe.
  - `regionConfig` falls back to `DEFAULT_REGION`.
- **AGENT-088: not certified.**
  - `BARE_TICKER_SHAPE` caps a symbol at 10 characters.
  - RELIANCE.NS, HDFCBANK.NS and BAJFINANCE.NS on the watchlist stay raw, and pay an LLM round-trip.
- **UI-052: certified.**
  - The keyless claims no longer promise web research.
  - The privacy lines now say that market data and web searches go to public providers (onboarding flow, banner, and the local-AI card).

## Issues seen outside the entries (not blocking)

- **Freshness labels:** BHP.AX reads `live` while the ASX is closed, and AAPL's daily bar reads `eod` intraday.
- **OpenAI native search:** the gate targets `*-search-preview` models that OpenAI now 404s as deprecated.
- **IMF WEO:** projections through 2031 are unlabelled as projections.
- **DATA-052 provenance:** `field_meta.sector.provider` says yfinance while the value came from the resolver.
- **Cold NSE batches:** they still hold `to_thread` workers. One contended SPY quote took 8.6 s, which will matter during market hours.
- **Fundamentals warmer:** it hits openbb-mcp hard at boot.
- **/history/ZZZZNOTREAL:** returns 200, empty, with `reason: null`.
- **Keybindings hint:** the Settings copy says "two actions on one combo both fire", but the dispatcher fires only the first match.
- **Palette:** the starter "Open Chart" row duplicates the command row and shows no chord.
