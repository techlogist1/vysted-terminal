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

## Component 4 — deterministic symbol resolution (`services/symbol_resolver.py`)

- **No router/app wiring needed.** The change is internal to
  `symbol_resolver.py` (BSE master joins resolve/autocomplete; live-lookup
  `.BO`→BSE contradiction fixed) — the already-registered `/resolve` and
  `/history` routers pick it up with no signature/wire-shape change.
- **`types/data.ts` unchanged** — no sidecar model was added or modified
  (the `Instrument` dataclass gained no fields; the wire payload is identical,
  only the values are now consistent).
- **Wire-visible behaviour changes** the frontend may rely on:
  - `GET /resolve?q=ICONIKSPEV&region=IN` → `exchange:"BSE"`,
    `yahoo_symbol:"ICONIKSPEV.BO"`, `confidence:1.0` (was the NSE/.BO
    contradiction at 0.6 via live lookup).
  - A dual-listed bare ticker (e.g. RELIANCE) resolves best=NSE with the BSE
    row riding `candidates` — pickers that render candidates will now show
    both exchanges, NSE first.
  - An explicit `.BO` query pins the BSE identity (previously rewritten to
    the NSE row for dual-listed names).
  - `/resolve/autocomplete` now surfaces BSE-only micro-caps (exchange
    `"BSE"`); dual-listed names stay single-row (NSE canonical).
- **smoke-test**: `scripts/smoke-test-sidecars.mjs` gained a HARD ICONIKSPEV
  resolve check against the spawned binary (fails the run if the regenerated
  BSE master is not bundled or resolution regresses) and a no-SLA
  `/history/ICONIKSPEV` live-bars probe (warn-only). If the lead's track
  changes `ensure-sidecar.mjs` --add-data, this probe is the canary.

---

# R7 Track R — integration notes for the lead

App-shared touchpoints this track needs but did NOT change (per the brief's
ownership rules), plus wiring the frontend/lead must pick up.

## Component 3 (T3 hosted tier) — 2026-06-10

### Shared files deliberately left untouched

- **`sidecar/services/llm/native_search.py` `openrouter_web_search_tool()`**
  still emits the bare `{"type": "openrouter:web_search"}` with no
  `parameters`. The live docs (verified 2026-06-10,
  https://openrouter.ai/docs/guides/features/server-tools/web-search) support
  `parameters: {engine, max_results, max_total_results, search_context_size,
  allowed_domains, excluded_domains}` — the agent-loop injection could carry
  the user's engine choice via `config.get_hosted_search_engine()`. The t3
  search backend (`services/search/hosted.py:web_search_server_tool`) owns its
  own fully-parameterized builder, so this is an enhancement, not a defect.
  Left to the lead because `services/llm/` is shared with the LLM track.
- **`normalize_openai` excerpt fallbacks** read `snippet`/`text`; the server
  tool's `url_citation` carries the excerpt under **`content`** (live docs).
  Suggested one-line addition: `_get(src, "content")` first in the fallback
  chain. The hosted backend parses `content` itself; the sonar lane degrades
  to an empty excerpt through `normalize_openai` (sources still render — the
  brief's requirement holds), so again enhancement-only.

### Frontend wiring needed (settings round-trip)

New per-request headers read by the region middleware (`sidecar/app.py`
`_RegionMiddleware`), mirroring the existing `X-Vysted-Search-Tier` transport:

| Header | ContextVar | Values |
| --- | --- | --- |
| `X-Vysted-Research-Tier` | `config.get_research_search_tier()` | `t1_local` / `t2_searxng` / `t3_hosted` (absent → no explicit selection, floors to t1) |
| `X-Vysted-Openrouter-Key` | `config.get_openrouter_search_key()` | BYOK secret — keychain-sourced, never persisted/logged |
| `X-Vysted-Search-Engine` | `config.get_hosted_search_engine()` | `firecrawl` (default) / `exa` / `parallel` / `auto` / `native` |

The Settings panel should persist the tier + engine in the frontend store
(same pattern as the deep-research engine selection) and send them on every
sidecar request. The deep-research Settings picker may now also offer
`sonar` (the OpenRouter-routed Perplexity lane) alongside
`native`/`perplexity` — `run_deep_brief` dispatches it already.

### Verified-live facts the UI copy can rely on (2026-06-10)

- The `plugins: [{"id": "web"}]` array and the `:online` suffix are
  **deprecated**; the `openrouter:web_search` server tool is current.
- Engine pricing: Firecrawl = $0 OpenRouter-side (bills Firecrawl credits;
  10,000 free credits at signup, 3-month expiry). Exa/Parallel = $0.005 per
  search including 10 results, then $0.001 per additional result. Native =
  provider pass-through.
- `perplexity/sonar-deep-research` is routable via OpenRouter ($2/M in,
  $8/M out, $5/1000 searches pass-through).
- `alibaba/tongyi-deepresearch-30b-a3b` is **delisted** from OpenRouter —
  kept out of every picker; direct sources (Alibaba Bailian / WaveSpeed) only.

### NEEDS-MANUAL-CHECK (live key required)

- One live `t3_hosted` search with a real OpenRouter key per engine
  (firecrawl + exa) to confirm the annotation shape end-to-end.
- One live `backend="sonar"` run to confirm OpenRouter passes the top-level
  `citations[]` array through alongside annotations.

## Component 4 (depth router N/D/U + finance tuning) — 2026-06-10

### Shared files deliberately left untouched

- **`sidecar/services/agent_tools/catalog.py`** (owned by another track): the
  `research` capability's `depth` enum still reads `["quick", "deep", "heavy"]`.
  The handler accepts BOTH namings — `services/research/depth.py` is the one
  source of truth and maps `quick`→`normal`, `heavy`→`ultra` forever — so the
  current schema keeps working unchanged. Suggested catalog update when the
  lead touches it: enum `["normal", "deep", "ultra"]` (legacy spellings stay
  accepted by the handler), and the `rounds`/`wall_seconds` descriptions can
  note the new per-depth defaults (deep 3/120s, ultra 4/240s — an explicit arg
  still wins, clamped to [1,5]/[30,300]).
- **`sidecar/services/agent_runtime.py` auto-publish** maps the brief panel's
  `depth` from the result `mode` (`fast|deep|heavy` → `quick|deep|heavy`) —
  unchanged and still correct. The engine result now ALSO carries a top-level
  `depth: "normal"|"deep"|"ultra"` for the new surface naming; when the
  frontend renames its "Go deeper" tiers, read that field instead of `mode`.

### Frontend wiring needed

- Depth is per-query and orthogonal to the search tier: the agent passes
  `depth` on the `research` tool call (no new headers). If a UI depth picker
  ships, send `normal|deep|ultra` — the sidecar normalizes any spelling.
- ULTRA briefs may carry `structured.cross_check` (`{claims:[{claim, verdict:
  agree|disagree|unverified, detail, domains}], disagreements, min_domains}` or
  `{skipped, reason}`) plus a `## Cross-check` markdown section; a disagreement
  count is appended to `note`. The brief panel can badge disagreements from
  `structured.cross_check.disagreements` without parsing markdown.
- Web-only floor: when no structured price/fundamentals provider covers an
  instrument, a clean DEEP/ULTRA brief states it in markdown ("Coverage note:
  … web sources alone") — no new field; `web_available` semantics unchanged.