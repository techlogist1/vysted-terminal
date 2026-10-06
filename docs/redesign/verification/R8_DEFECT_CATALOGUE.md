# R8 Defect Catalogue — root-caused from code + live drive (2026-06-10, pre-build)

Method: 12-reader recon workflow over the codebase (file:line anchors), lead deep-reads of the
research loop, live sidecar API probes, and a live drive of the rebuilt app via the
tauri-plugin-mcp rig (captures in `verification/r8/`). Items marked LIVE were reproduced on the
running app; CODE means confirmed at the cited lines.

## A. Research engine truth (WS1)

| ID | Defect | Root cause (file:line) | Evidence |
|----|--------|------------------------|----------|
| A1 | ULTRA explorers research a contaminated query; structured tools get the whole focus sentence as "symbol" (SAKSOFT bug) | `iter.py:580` seeds explorers with `f"{query} — focus: {angle}"`; `iter.py:243` `symbol = instrument.get("symbol") or query` falls back to the raw string when resolve fails | LIVE: `/resolve?q=<contaminated>` → ok:False; persisted brief shows the class |
| A2 | Wrong instrument binds to a run (CMTL-for-Reliance) | per-explorer re-resolution on contaminated text falls through to the resolver's guarded yfinance fuzzy search; heavy brief takes `good[0].symbol` (`iter.py:662`) | LIVE: operator's autosave blob: query "Reliance Industries Limited", symbol "CMTL", 92 sources (saved at `r8/regression-brief-cmtl.json`) |
| A3 | Results-filing PDFs in hand are never read ("no quarterly results announced" while holding the outcome PDF) | `extract.py:225-227` rejects every non-HTML content type; no PDF library exists in the sidecar; `visit` reads only the TOP web result (`deep.py:422`), capped at 1800 chars (`extract.py:250`) | CODE + R7 evidence pack (ROUTE) |
| A4 | Junk sources count as coverage (crypto Router Protocol, Nestle/Zomato filings, SEO explainers → "69 sources") | `_record_web` (`deep.py:321-354`) folds in every row with zero entity-match; researcher web query is bare `f"{symbol} {sub_question}"` (`deep.py:410`); `finance.domain_tier` ranks authority but never relevance | CODE |
| A5 | Citations point at wrong documents ([47] TMB Bank PDF as Route's transcript) | synthesis prompt receives the full unfiltered [1..N] list; no claim→source verification exists post-synthesis (`deep.py:497-554`, `iter.py:160-202`) | CODE |
| A6 | Debug internals render in user briefs ("per-round wall-clock guard: round exceeded 22s", "heavy:3 angles") | abort reason / panel note stamped on `brief.note` (`iter.py:432,656`) which `BriefPanel.tsx:479-482` renders | LIVE: boot screenshot 01 shows "HEAVY:3 ANGLES" banner |
| A7 | Deep runs guard-abort at 16-22s on thin names instead of degrading | `_round_wall_limit` (`deep.py:75-86`) = min(90s, remaining); a slow round 1 leaves round 2 a ~20s ceiling → TimeoutError → whole-run abort (`iter.py:428-433`) | CODE |
| A8 | Research ignores the in-house disclosures/announcements the app already ingests | `_run_researcher` dim rotation (`deep.py:397-407`) knows only fundamentals/sec_filings/price/news; disclosure tools registered but never consulted | LIVE: `/disclosures/results?symbol=ROUTE` carries the 2026-05-07 results meeting; `/disclosures/announcements` carries attachment PDFs incl. transcripts |
| A9 | FAST banner contradicts body (ICONIKSPEV "0 SOURCES" vs inline Screener.in citations) | FAST prose is model-written from the bundle; nothing stops uncited/memory web claims; banner counts only bundle citations (`fast.py:264-302`, auto-publish `agent_runtime.py:586-616`) | R7 evidence pack |
| A10 | Brief P/E "not available" while the panel shows 13.9× from the same backend | research leg swallows provider errors (`agent_tools/fundamentals.py:39-42` + `_safe_call`), no retry; symbol-format divergence (bare vs .NS) can route different providers | CODE |
| A11 | Cost renders as "$0.0000" and the brief header meta row overlaps/clips at panel widths | brief MetaHeader layout + cost formatting | LIVE: capture 01 |

## B. Search tier routing / settings truth (WS4)

| ID | Defect | Root cause | Evidence |
|----|--------|------------|----------|
| B1 | Live managed SearXNG (READY at 8888) bypassed → "no web backend / rate-limited" runs | legacy default tier "native" never calls `detect_searxng()` (`web_search.py:132-135`); only the R7 header path autodetects; requests without the R7 header floor to keyless | CODE (confirmed flow trace) |
| B2 | Two conflicting settings surfaces | legacy "Web search" section (`SettingsPanel.tsx:738-964`, manual docker-run snippet on 8080) coexists with R7 "Research" tiers (`:1405-1470`); both write distinct store keys (`search-settings.ts`); sidecar honors legacy when R7 header missing | LIVE: captures 17/18 |
| B3 | Workspace blobs can desync legacy tier vs R7 tier (hand-edited/old blobs restore to t1) | no legacy→R7 migration in `workspace.ts` deserialize | CODE |

## C. Agent seams (WS5)

| ID | Defect | Root cause | Evidence |
|----|--------|------------|----------|
| C1 | Personas can't drive panels ("I don't have the ability to open panels") | only copilot.json carries the 11 host actions; graham.json has 3 read tools; no parity mechanism or test | CODE: agents/*.json |
| C2 | Agent-opened equity overview can arrive without the requested symbol | `open_panel` host action carries no symbol arg (only `open_company_overview` does); panel command consumption unverified | CODE + operator evidence |
| C3 | Narration claims unmatched by panel state (SMA/RSI claim; 52wk ₹655 vs panel ₹1,158) | prose claims are never reconciled with actual panel/host-action state; brief numbers can come from junk web sources instead of the structured feed the panel uses | evidence pack |

## D. Proportion / UI (WS2+WS3) — LIVE captures at 1396px and 850-1000px

| ID | Defect | Evidence |
|----|--------|----------|
| D1 | Composer send button tiny (24px, bottom-right inside field); no plus/attach affordance; meta-row chips give zero clickability affordance | capture 01/16; `ChatSidebar.tsx:1498-1556`, `ComposerMetaRow.tsx:330-503` |
| D2 | Depth slider/lens chip overlap risk at narrow dock (<650px); meta row has no responsive collapse | `ComposerMetaRow.tsx` flex map (recon) |
| D3 | Watchlist at narrow width: price/change columns collide ("61,446.08-1.35%"); chips truncate ("YFINAN", "Add symb", "Portfol") | capture 22 |
| D4 | Settings: SET DEFAULT labels wrap to two lines; provider rows cramped; section chips clip at narrow panel | capture 02 |
| D5 | Chart: symbol input comically small; 3-row toolbar; timeframe row descender clipping (operator) | capture 04 |
| D6 | Notes toolbar icon sizes mixed (pencil vs micro icons) | capture 03 |
| D7 | Brief panel: prose size vs narrow panel column → 2-3 words/line; header meta overlap; "→HEAVY" clip | capture 01 |
| D8 | User chat messages render larger than everything around them; bullets can overflow the dock (operator) | capture 16 + operator screenshots |
| D9 | Header model label area shows "+1" overflow chip and truncates model names ("DEEPSEEK-V4-FLA…") | captures 21/22 |
| D10 | Equity overview: ₹ symbol on AAPL (US instrument) market cap; autocomplete dropdown left stuck open over content | capture 19 |
| D11 | Chart SPY "Failed to load price history" while `/history/SPY` API serves 64 bars (panel param/transient issue) | capture 04 + API probe |

## E. Engine/infra

| ID | Item |
|----|------|
| E1 | tauri-plugin-mcp `evaluate_script` rejects `const` at statement start (expression context) — rig scripts must use IIFEs (rig note, not app defect) |
| E2 | dockview tabs require pointerdown dispatch (click alone doesn't switch) — rig note |
