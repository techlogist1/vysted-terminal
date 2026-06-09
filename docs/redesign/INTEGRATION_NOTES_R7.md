# R7 Track D — integration notes for the lead

Append-only notes from the data track (worktree-agent-r7-data). Each entry
states what the lead must wire (or verify needs no wiring) when merging.

## Component 2 — NSE exchange-direct provider (`services/nse_provider.py`)

- **No router registration needed.** The provider self-registers through the
  `provider_registry._PROVIDERS` declaration table (`nse_direct`, rank 15, IN
  equity, quote + ohlcv). `/health` picks it up automatically via
  `active_providers()` — expect `quote`/`ohlcv` to now read
  `ccxt (nse_direct, nse, bse, yfinance fallback)`.
- **No `app.py` / `services/config.py` change.** Nothing in this component
  touches another track's files.
- **IN preference order is now** `nse_direct (15) → nse/jugaad (20) → bse (25)
→ yfinance (50)`. Any block/throttle/circuit-open on the direct lane falls
  through to jugaad transparently; yfinance stays the gated last resort for IN
  and the US spine.
- **`types/data.ts` unchanged** — the provider emits the existing
  `Quote`/`OHLCVSeries` models; no new model was added in this component.
- **Component 3 consumers:** `get_corporate_announcements` /
  `get_results_calendar` / `get_shareholding_master` return the RAW observed
  list shapes (fixtures under `sidecar/tests/fixtures/nse/`) for
  `services/corporate_disclosures.py` to model.
- **Deliberate deviation from the brief's `AsyncSession`:** the registry's
  quote/ohlcv seam is synchronous (every provider it drives is sync; callers
  wrap in `asyncio.to_thread`), so the cookie-dance session uses curl_cffi's
  sync `Session(impersonate="chrome")` guarded by a module lock — identical
  anti-bot surface, no event-loop friction in worker threads (Tier-2,
  spec-derivable from the registry contract).
- **Live caveat (observed 2026-06-10):** `api/quote-equity` is Akamai
  path-ACL'd from at least some vantages while every other API path serves on
  the same session. `get_quote` handles this: blocked → rotate → per-path
  breaker → EOD quote derived from `historicalOR` (worked live). Do not treat
  a quote-equity 403 in logs as a provider bug.
- `scripts/smoke-test-sidecars.mjs` gained `_probeNseDirectNoSla()` (warn-only,
  never fails the run) — it shells to the sidecar venv python because Node's
  fetch has the wrong TLS fingerprint for NSE's edge.

## Component 3 — corporate disclosures (`services/corporate_disclosures.py` + `routers/disclosures.py`)

- **ONE router registration needed** (the only `app.py` wiring this component
  asks of the lead). In `sidecar/app.py`, alongside the existing includes:

  ```python
  from routers import disclosures
  app.include_router(disclosures.router)
  ```

  The router is prefix-self-contained (`/disclosures`, tags `["disclosures"]`)
  and standalone-tested in `tests/test_disclosures_router.py` (TestClient over
  a local `FastAPI()` + `include_router`), so the suite is green before this
  wiring lands. Routes: `GET /disclosures/announcements?symbol=&exchange=&limit=`,
  `GET /disclosures/results?symbol=`, `GET /disclosures/shareholding?symbol=`.

- **No `services/config.py` change.** Caching rides the existing
  `services/data_cache` (announcements 15 min, results 6 h, shareholding 24 h).
- **Agent tools need NO extra wiring**: `corporate_announcements` and
  `shareholding_pattern` are registered through the existing
  `register_v0_6_0_tools()` aggregator (`agent_tools/registry_v0_6_0.py`) and
  declared as `read_handler` Capabilities in `catalog.py`, so TOOL_SCHEMAS, the
  custom-agent allow-list, and the external MCP surface all pick them up by
  projection. Copilot + AI Researcher allow-lists already include them
  (`agents/copilot.json` — roster now 36; `agents/researcher.json` — 19).
- **New models** `sidecar/models/announcements.py` (Announcement,
  AnnouncementsResponse, ResultsEvent, ResultsCalendarResponse,
  ShareholdingPattern, ShareholdingResponse) are mirrored in `types/data.ts`
  in the same commit and re-exported from `models/__init__`.
- **Honesty contract:** `ShareholdingPattern.fii_percent`/`dii_percent` are
  `null` — the NSE shareholding MASTER carries only promoter(+group)/public/
  employee-trust percentages; the FII/DII split lives in the per-quarter
  `xbrl_url` filing the model links. Do not "fix" the nulls by parsing-free
  guessing. One announcements lane failing serves a partial merge with the
  failure named in `errors`; both failing → 502 with the reason.
- **Live caveat (observed 2026-06-10):** the BSE `AnnSubCategoryGetData` API
  serves a Chrome-impersonated curl_cffi session (fixture
  `tests/fixtures/bse/ann_sub_category_get_data.json` is a verbatim trim);
  attachments resolve under
  `https://www.bseindia.com/xml-data/corpfiling/AttachLive/<ATTACHMENTNAME>`
  (verified 200 `application/pdf`; `AttachHis` 404s for current filings).
