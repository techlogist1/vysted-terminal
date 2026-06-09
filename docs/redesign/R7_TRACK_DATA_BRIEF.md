# R7 Track D — India Data Brief (worktree: worktree-agent-r7-data)

You are building screener.in-grade, exchange-direct Indian market data for Vysted
Terminal, inside THIS worktree only:
`~/Documents/dev/vysted-terminal/.claude/worktrees/r7-data`.
Branch: `worktree-agent-r7-data`. NEVER write to the main repo path. Use the main venv's
binaries (all deps incl. curl_cffi present):
`~/Documents/dev/vysted-terminal/sidecar/.venv/bin/{python,ruff,pytest}` with cwd in THIS worktree.

## Ground rules

- Conventional commits per deliverable; push to `origin worktree-agent-r7-data` after each.
- Before each Python commit: `ruff format <changed> && ruff format --check sidecar && ruff check sidecar` + targeted pytest (offline; mock network in tests; live probes belong in scripts/smoke, not pytest).
- NEVER touch: `types/plugin.ts`, `.github/`, `src-tauri/tauri.conf.json`, `LICENSE*`, `CLAUDE.md`, §6.5 safety files, broker code, `sidecar/app.py` (owned by another track), `sidecar/services/config.py` (owned by another track), `sidecar/services/search/**`, `sidecar/services/research/**` (another track). Register new routers by appending instructions to `docs/redesign/INTEGRATION_NOTES_R7.md` (create it); test routers standalone (TestClient over a local FastAPI() + include_router).
- You OWN: `sidecar/services/{bse_provider,india_provider,yfinance_provider,symbol_resolver,provider_registry}.py`, new `sidecar/services/nse_provider.py`, `sidecar/services/resolver_masters/**`, `sidecar/scripts or sidecar tools for master regeneration`, new announcements service/models/router, `sidecar/services/agent_tools/` additions + `catalog.py` (you are the catalog owner this run), their tests.
- `types/data.ts` mirrors `sidecar/models/` BY HAND — when you add/change a model, ALSO update `types/data.ts` in the same commit (TS edits to that one file are in-scope for you).
- No GPL imports (BseIndiaApi is GPL — idea-level reimplementation only). jugaad-data already vendored is fine.
- Keyless-first; honest errors; never fabricate bars.

## Current defects you are fixing (verified live, 2026-06-10)

- `GET /resolve?q=ICONIKSPEV&region=IN` → exchange "NSE" but yahoo_symbol "ICONIKSPEV.BO" (contradiction), confidence 0.6. Master data is sloppy.
- `GET /history/ICONIKSPEV` → `bars:[], provider:"none", reason:null` — the seeded BSE master has 2 placeholder rows (regenerate_bse_master.py never run), so scrip-code routing + region_hint + the `in_eod_only` honest reason ALL misfire.
- No corporate announcements/results/shareholding ingestion exists anywhere.

## Component 1 — BSE completed (bhavcopy + scrip-code routing + real master)

- Regenerate the REAL BSE master: extend/replace `resolver_masters` BSE data by downloading
  BSE's scrip master (the public ListOfScrips/scrip-master CSV from bseindia.com — the
  existing regenerate_bse_master.py has the URL shape; harden it with curl_cffi
  impersonation + retries) covering ALL equity groups (A/B/T/X/XT/Z/M/MT incl. SME) with
  scrip code, ticker, name, ISIN, group, status. Ship the regenerated master FILE in the
  repo (it's static-ish data; note the regeneration date in a header). Target: ICONIKSPEV
  resolves deterministically to its BSE scrip code.
- Complete `bse_provider.py`: route get_history/get_quote by SCRIP CODE looked up from the
  master (ticker→code), not just ticker string matching. Bhavcopy cache stays per-day;
  bound cold-download as it does today. Quote via getScripHeaderData with bhavcopy
  fallback. EQ-series/group preference retained.
- History for thin listings must return real EOD bars for BSE-only names (ICONIKSPEV class).

## Component 2 — NSE exchange-direct (anti-bot)

New `services/nse_provider.py` (jugaad-data stays as one source; this is the direct lane):

- curl_cffi `AsyncSession(impersonate="chrome")` with the NSE cookie dance (hit
  https://www.nseindia.com first for cookies, then API endpoints with proper headers;
  rotate session on 401/403; throttle ~1 req/s with jitter; circuit breaker on repeated
  blocks).
- Endpoints: quote (api/quote-equity?symbol=), historical candles (api/historicalOR
  chart data), corporate announcements (api/corporate-announcements?index=equities&symbol=),
  results calendar (api/event-calendar), shareholding pattern (api/corporate-share-holdings-master or the corporates page APIs — verify the current endpoint shapes by fetching them
  with curl_cffi in a scratch script FIRST and modeling the REAL response, then write the
  provider + tests from observed shapes; record observed JSON samples in test fixtures).
- Register in provider_registry: nse_direct above jugaad above yfinance for IN; yfinance
  demoted to one provider among several for IN (keep it the US spine).
- All network access mocked in pytest; add a live probe to `scripts/smoke-test-sidecars.mjs`
  style (note in INTEGRATION_NOTES if you can't edit that script — actually you MAY edit
  `scripts/smoke-test-sidecars.mjs`, you own it this run).

## Component 3 — Corporate disclosures into the product

- New models (`sidecar/models/announcements.py`: Announcement {symbol, exchange, headline,
  category, attachment_url, ts}, ResultsEvent, ShareholdingPattern with promoter/FII/DII/
  public percentages + quarter) — mirror in `types/data.ts` same commit.
- New service `services/corporate_disclosures.py`: BSE + NSE announcement fetchers
  (merged, deduped by (symbol, headline-hash, date)), results calendar, shareholding.
- New router `routers/disclosures.py` (standalone-tested; registration via INTEGRATION_NOTES):
  GET /disclosures/announcements?symbol=&exchange=&limit=, /disclosures/results?symbol=,
  /disclosures/shareholding?symbol=.
- New agent tools in catalog.py (you own it): `corporate_announcements` and
  `shareholding_pattern` as read_handler Capabilities (auto-projects to TOOL_SCHEMAS/
  allow-list/MCP). Update roster-count asserts (`test_capability_catalog`,
  `test_mcp_catalog_parity`, `test_agent_runtime` roster, `test_agents_router`,
  `test_mcp_server`) — the counts bump.
- Add the tools to the copilot + AI Researcher agents' allow-lists (sidecar/agents/\*.json)
  so research runs can pull filings.

## Component 4 — Deterministic symbol resolution

- Master hygiene: one canonical row per instrument; exchange field must agree with the
  yahoo_symbol suffix; dual-listed names carry BOTH exchanges with NSE preferred for
  trading data but BSE retained for BSE-only fundamentals; confidence model documented.
- region_hint covers the full regenerated BSE+NSE masters (bare BSE-only ticker → IN).
- Fix the `in_eod_only` honest reason for IN symbols with no bars (region_hint must hit).
- The ICONIKSPEV acceptance: resolve → consistent BSE identity; /history/ICONIKSPEV →
  real EOD bars from bhavcopy via scrip code (write an offline test with a fixture
  bhavcopy row + a live smoke probe).
- Autocomplete stays fast and masters-only; verify "Route Mobile" still → ROUTE.

## Definition of done

No stubs/TODOs. Offline tests green (your suites + FULL sidecar pytest still green), ruff
clean, committed + pushed per component. Final `docs/redesign/R7_TRACK_DATA_REPORT.md` in
the worktree: what shipped (file:line), verification evidence (test output), live-probe
results for BSE/NSE endpoints (run them once from a scratch script and paste observed
shapes), NEEDS-MANUAL-CHECK items, integration notes for the lead.
