# R15 Stage 0 — World-Drift Report

**Date:** 2026-09-19 · **Worker model:** `claude-opus-5[1m]` · **Mode:** read-only, no GUI, no process control
**Repo:** `/Users/lokavyasingh/Documents/dev/vysted-terminal` @ `004-r4-experience-rebuild`
**Method:** every code claim carries a `file:line` anchor. Network probes are single GETs, ≤1 req/s per host.
**Catalog snapshot:** `GET https://openrouter.ai/api/v1/models` → HTTP 200, 738,444 bytes, **446 models**, fetched 2026-09-19.

---

## Section 1 — Pinned model slugs vs. the live OpenRouter catalog

### 1a. Every pinned slug in the repo

Model pins live in three mirrored places (the repo's own drift-guard: `src/store/model-selection.ts:16-24`
says the JSON, `llm-providers.ts` and `model-selection.ts` must be edited together):

| # | Role | Slug | Source file:line |
|---|---|---|---|
| 1 | OpenRouter **chat default** | `deepseek/deepseek-v4-flash` | `sidecar/config/model_registry.json:61`, `src/store/llm-providers.ts:99`, `src/store/model-selection.ts:39` |
| 2 | OpenRouter known-model #1 (ex-keyless-research default) | `minimax/minimax-m3` | `sidecar/config/model_registry.json:63`, `src/store/model-selection.ts:51`, `src/store/llm-providers.ts:102` |
| 3 | OpenRouter known-model | `moonshotai/kimi-k2.6` | `sidecar/config/model_registry.json:65`, `src/store/model-selection.ts:53` |
| 4 | OpenRouter known-model | `deepseek/deepseek-v4-pro` | `sidecar/config/model_registry.json:66`, `src/store/model-selection.ts:54` |
| 5 | OpenRouter known-model | `qwen/qwen3.7-max` | `sidecar/config/model_registry.json:67`, `src/store/model-selection.ts:55` |
| 6 | OpenRouter known-model | `qwen/qwen3.7-plus` | `sidecar/config/model_registry.json:68`, `src/store/model-selection.ts:56` |
| 7 | OpenRouter known-model | `z-ai/glm-5.1` | `sidecar/config/model_registry.json:69`, `src/store/model-selection.ts:57` |
| 8 | OpenRouter known-model | `qwen/qwen3.6-flash` | `sidecar/config/model_registry.json:70`, `src/store/model-selection.ts:58` |
| 9 | OpenRouter known-model (router sentinel) | `openrouter/auto` | `sidecar/config/model_registry.json:71`, `src/store/model-selection.ts:59` |
| 10 | Research-depth pin **normal** | `perplexity/sonar` | `sidecar/config.py:447` (`DEFAULT_RESEARCH_MODELS`) |
| 11 | Research-depth pin **deep** | `perplexity/sonar-reasoning-pro` | `sidecar/config.py:448` |
| 12 | Research-depth pin **ultra** | `perplexity/sonar-deep-research` | `sidecar/config.py:449` |
| 13 | Sonar lane — routable family | `perplexity/sonar` | `sidecar/services/research/sonar.py:50` |
| 14 | Sonar lane — routable family | `perplexity/sonar-pro` | `sidecar/services/research/sonar.py:51` |
| 15 | Sonar lane — routable family | `perplexity/sonar-reasoning` | `sidecar/services/research/sonar.py:52` |
| 16 | Sonar lane — routable family | `perplexity/sonar-reasoning-pro` | `sidecar/services/research/sonar.py:53` |
| 17 | Sonar lane — `SONAR_DEEP_MODEL` (the catch-all resolve target) | `perplexity/sonar-deep-research` | `sidecar/services/research/sonar.py:46` |
| 18 | Perplexity-direct DEEP backend (vendor API, not OR) | `sonar-deep-research` | `sidecar/services/research/perplexity.py:51` |
| 19 | Deep-research **Tongyi slug** (delisted; kept only as a resolve *input*) | `alibaba/tongyi-deepresearch-30b-a3b` | `sidecar/services/research/sonar.py:19-21`, asserted delisted in `sidecar/tests/test_sonar_lane.py:61-65` |
| 20 | Operator's cheap model (test battery) | `openai/gpt-5.6-luna` | named in `docs/redesign/verification/R15_BRIEF.md:44`; used in tests `sidecar/tests/test_agent_runtime.py:545,793`, `test_native_search.py:389,629`, `test_llm_openai.py:745` |

**Direct-provider (non-OpenRouter) defaults** — these hit vendor APIs, so the OpenRouter catalog is only a
cross-check, not authority. All from `sidecar/config/model_registry.json:8-54` mirrored at
`src/store/model-selection.ts:36-43` / `:46-53`:

`anthropic` → `claude-opus-4-8` (known: `claude-sonnet-4-6`, `claude-haiku-4-5`) ·
`openai` → `gpt-4.1-mini` (known: `gpt-4.1`, `o4-mini`) ·
`gemini` → `gemini-2.5-pro` (known: `gemini-2.5-flash`) ·
`groq` → `llama-3.3-70b-versatile` (known: `llama-3.1-8b-instant`) ·
`ollama` → `qwen2.5:7b` (known: `llama3.1:8b`) ·
`deepseek` → `deepseek-chat` (known: `deepseek-reasoner`) ·
`xai` → `grok-4` (known: `grok-3`).

Ollama hardware-fit candidates: `qwen3:8b`, `qwen2.5-coder:7b` (`sidecar/routers/system.py:35-36`).

### 1b. Live verification against the OpenRouter catalog

| Slug | Status today | Price in $/M | Price out $/M | Context | Tools? |
|---|---|---|---|---|---|
| `deepseek/deepseek-v4-flash` | **exists** | 0.0484 | 0.0969 | 1,048,576 | yes |
| `minimax/minimax-m3` | **exists** | 0.30 | 1.20 | 1,048,576 | yes |
| `moonshotai/kimi-k2.6` | **exists** | 0.95 | 4.00 | 262,144 | yes |
| `deepseek/deepseek-v4-pro` | **exists** | 0.6758 | 1.3516 | 1,048,576 | yes |
| `qwen/qwen3.7-max` | **exists** | 1.475 | 4.425 | 1,000,000 | yes |
| `qwen/qwen3.7-plus` | **exists** | 0.32 | 1.28 | 1,000,000 | yes |
| `z-ai/glm-5.1` | **exists** | 0.966 | 3.036 | 204,800 | yes |
| `qwen/qwen3.6-flash` | **exists** | 0.1875 | 1.125 | 1,000,000 | yes |
| `openrouter/auto` | **exists** | −1 sentinel (routed price) | −1 sentinel | 2,000,000 | yes |
| `perplexity/sonar` | **exists** | 1.00 | 1.00 | 127,072 | **no** |
| `perplexity/sonar-pro` | **exists** | 3.00 | 15.00 | 200,000 | **no** |
| `perplexity/sonar-reasoning` | **RETIRED — not in catalog** | — | — | — | — |
| `perplexity/sonar-reasoning-pro` | **exists** | 2.00 | 8.00 | 128,000 | **no** |
| `perplexity/sonar-deep-research` | **exists** | 2.00 | 8.00 | 128,000 | **no** |
| `alibaba/tongyi-deepresearch-30b-a3b` | **still absent** (delisted; code already knows) | — | — | — | — |
| `openai/gpt-5.6-luna` | **exists** | **0.20** | **1.20** | 1,050,000 | **yes** |
| `x-ai/grok-4.3` (test-only header example) | exists | 1.25 | 2.50 | 1,000,000 | yes |
| `openai/o4-mini-deep-research` (test-only header example) | **not in catalog** | — | — | — | — |
| `anthropic/claude-opus-4-8` (as an OR slug) | **not in catalog** — OR spells it `anthropic/claude-opus-4.8` (dot, not dash) | — | — | — | — |

Perplexity family actually listed on OpenRouter today: `perplexity/sonar`, `perplexity/sonar-pro`,
`perplexity/sonar-pro-search`, `perplexity/sonar-reasoning-pro`, `perplexity/sonar-deep-research`.
Note the **new** member `perplexity/sonar-pro-search`, which the repo does not know about.

**Operator's cheap model — CONFIRMED exactly as believed.** `openai/gpt-5.6-luna` is real, priced
**$0.20 in / $1.20 out per M tokens**, 1.05M context, and `supported_parameters` **includes `tools`**.
It is safe as the battery's default tool-capable model. (For reference it ranks 124th of 354 *paid*
tool-capable models by in+out price — cheap-tier but far from the floor; the floor is much cheaper and
much weaker.)

### 1c. Five cheapest tool-capable models on OpenRouter today

375 of 446 models declare `tools`. 21 of those are `$0` `:free` variants; the rest are paid.

**Cheapest paid tool-capable (by in + out $/M):**

| Rank | Slug | In $/M | Out $/M | Context |
|---|---|---|---|---|
| 1 | `mistralai/mistral-nemo` | 0.0190 | 0.0300 | 131,072 |
| 2 | `inclusionai/ling-3.0-flash` | 0.0210 | 0.0630 | 262,144 |
| 3 | `meta-llama/llama-3.1-8b-instruct` | 0.0500 | 0.0800 | 131,072 |
| 4 | `deepseek/deepseek-v4-flash` | 0.0484 | 0.0969 | 1,048,576 |
| 5 | `mistralai/ministral-8b-2512:batch` | 0.0750 | 0.0750 | 262,144 |

(next: `openai/gpt-oss-20b` and `qwen/qwen3.7-flash`, both 0.0300 / 0.1300)

**Free ($0) tool-capable**, if the battery wants a zero-cost lane: `cohere/north-mini-code:free`,
`deepseek/deepseek-v4-flash-0731:free`, `dots-studio/dots-3-note-preview:free`, `google/gemma-4-26b-a4b-it:free`,
`google/gemma-4-31b-it:free`, `inclusionai/ling-3.0-flash-{fin,sante,vl}:free`, `liquid/lfm-2.5-2.6b:free`,
`nex-agi/nex-n2.5-{mini,pro}:free`, `nvidia/nemotron-3-*:free` (+ 9 more, 21 total).
**Note:** rank 4, `deepseek/deepseek-v4-flash`, is *already the app's OpenRouter default* — the repo's own
default is in the global top-5 cheapest tool-capable models. That pin has not rotted.

---

## Section 3 — SearXNG image pin and container-absent behaviour

### What the repo pins

| Item | Value | file:line |
|---|---|---|
| Image | `searxng/searxng` — **no tag**, so Docker resolves `:latest` | `sidecar/services/searxng_manager.py:65` |
| Container name | `vysted-searxng` | `sidecar/services/searxng_manager.py:66` |
| Host port | `8888` preferred, probes 20 consecutive ports; container-internal `8080` | `sidecar/services/searxng_manager.py:70-74` |

There is **no docker-compose file and no pinned digest anywhere in the repo** — the only image reference is
that one string constant, pulled via `docker pull searxng/searxng` (`searxng_manager.py:21`).

### Is the tag current upstream?

Docker Hub public tag listing (`GET https://hub.docker.com/v2/repositories/searxng/searxng/tags`, HTTP 200):
**1,018 tags**; `latest` was last pushed **2026-09-18T15:29:40Z — yesterday**. Upstream publishes several
date-stamped tags per day (`2026.9.18-c0042add3`, `2026.9.18-c0ec29fdc`, …).

**Verdict: the reference is current but unpinned.** `searxng/searxng:latest` still resolves and is
actively maintained (daily pushes), so nothing has rotted. The *risk* is the opposite of rot: a floating
`:latest` against a project that ships 1,018 tags and multiple builds per day means the user's local
SearXNG can change under the app between two `docker pull`s, with no digest to reproduce. That is a
supply-chain and reproducibility concern, not a drift failure.

### What the app does when the container is absent

The absent container is a **first-class, silent degrade — not an error path.**
Resolution order in `sidecar/services/agent_tools/web_search.py:78-98`:

1. `:78-83` — an explicit custom SearXNG URL (`X-Vysted-Searxng-Url` → `config.get_searxng_url()`) is used as-is.
2. `:86-92` — else a **ready managed** SearXNG via `searxng_manager.manager.ready_base_url_detected()`.
3. `:94-98` — else the **keyless rotation floor** (DDG → Brave → Mojeek, `services/search/keyless.py:131`),
   which "ALWAYS resolves", with `registry.resolve("ddg", …)` as the defensive fallback if the keyless
   module fails to import.

The result is stamped with the honest backend id `keyless-fallback`
(`KEYLESS_FALLBACK_BACKEND_ID`, `web_search.py:55`) so the UI can render a nudge and no banner can
falsely claim SearXNG served the run. A SearXNG instance that is present-but-broken at search time
(stopped container, dead custom URL) degrades the same way — one retry on the keyless floor,
`web_search.py:137-149`. A SearXNG that is up but returns **zero results** is cross-checked against
the keyless floor once before the empty answer is accepted (`web_search.py:151-165`).
Telemetry separates the two lanes: `searxng_searches` vs `keyless_fallback_searches`
(`web_search.py:172`, `:181-183`).

`searxng_manager.py:13-21` also models the docker-absent states explicitly
(`not_installed_docker`, `docker_present_not_setup`, `pulling`), so "no docker at all" is a reported
state driving an install CTA, never a crash.

---

## Section 2 — Exchange / Yahoo / SEC endpoint probes

Each row probed **once** with the client + headers the code itself uses, ≥1.2 s apart per host.
Scripts: `<scratchpad>/probe.py`, `yahoo_retest.py`, `yahoo_tls.py`, `confirm.py`; raw JSON in
`<scratchpad>/probe_results.json`.

### 2a. NSE — `sidecar/services/nse_provider.py` (curl_cffi `impersonate="chrome"`, `:240-242`)

| Endpoint | file:line | HTTP | Payload shape vs. parser | Verdict |
|---|---|---|---|---|
| `GET https://www.nseindia.com/` (cookie warm-up) | `nse_provider.py:88`, `:253-258` | **200** | 4 cookies set | healthy |
| `/api/historicalOR/cm/equity` | `nse_provider.py:89`, parser `:374-386` + `:391-411` | **200** | `data[]` n=21, **all six `CH_*` keys present** (`CH_CLOSING_PRICE`, `CH_TIMESTAMP`, `CH_OPENING_PRICE`, `CH_TRADE_HIGH_PRICE`, `CH_TRADE_LOW_PRICE`, `CH_TOT_TRADED_QTY`) | healthy |
| `/api/corporate-announcements` | `nse_provider.py:91`, parser `:/_fetch_corporate_list` | **200** | bare JSON list, n=3354 — matches `isinstance(payload, list)` | healthy |
| `/api/quote-equity` | `nse_provider.py:90`, parser `:502-520` | **403** Akamai "Access Denied" | n/a | **known + handled** — `nse_provider.py:484-487` documents this path as edge-blocked from the probe vantage and falls back to the EOD quote from the last two `historicalOR` rows. Not new rot. |
| `/api/event-calendar`, `/api/corporate-share-holdings-master`, `/api/corporates-corporateActions` | `nse_provider.py:92-94` | not probed | same `_fetch_corporate_list` bare-list contract as `/api/corporate-announcements`, which passed | assumed healthy (one probe per host budget) |

### 2b. NSE archives — httpx + desktop UA + `nseindia.com` Referer

| Endpoint | file:line | HTTP | Shape | Verdict |
|---|---|---|---|---|
| `nsearchives.nseindia.com/content/equities/symbolchange.csv` | `nse_symbol_change.py:84`, headers `:104-108` | **200** | CSV, 1060 lines, 4 columns — matches the `01-JUL-2026` month-token parse | healthy |
| `nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{ymd}_F_0000.csv.zip` | `nse_bhavcopy.py:93`, headers `:109-116` | **200** | valid ZIP (`PK` magic), 203,981 bytes for 2026-09-17 | healthy |
| `archives.nseindia.com/products/content/sec_bhavdata_full_{dmy}.csv` | `nse_bhavcopy.py:95` | **200** | CSV, 15 columns, header `SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, …` as expected | healthy |

### 2c. BSE — `bse_provider.py`, `corporate_disclosures.py`, `resolver_masters/*`

| Endpoint | file:line | HTTP | Shape vs. parser | Verdict |
|---|---|---|---|---|
| `api.bseindia.com/.../getScripHeaderData/w` | `bse_provider.py:95`, parser `:506-537` | **200** | `Header[]` present; **close key = `LTP`**, **prev key = `PrevClose`** — both in the parser's defensive tuple | healthy |
| `api.bseindia.com/.../AnnSubCategoryGetData/w` | `corporate_disclosures.py:83`, params `:137-145`, parser `:148-165` | **200** | `Table[]` n=13, **no missing keys** (`NEWSID`, `SCRIP_CD`, `NEWSSUB`, `HEADLINE`, `CATEGORYNAME` all present) | healthy |
| `api.bseindia.com/.../ListOfScripData/w` (resolver master refresh) | `resolver_masters/regenerate_bse_master.py:55`, also `regenerate_india_sectors.py:65` | **200** | JSON list n=**5037**, keys `SCRIP_CD, Scrip_Name, Status, GROUP, FACE_VALUE, ISIN_NUMBER, INDUSTRY, Mktcap…` | healthy |
| `api.bseindia.com/.../ComHeadernew/w` (sector master) | `resolver_masters/regenerate_india_sectors.py:69` | **200** | dict with `SecurityId, SecurityCode, ISIN, Grp_Index, Industry…` | healthy |
| `www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_..._F_0000.CSV` | `bse_provider.py:90-92`, decoder `:262-271` | **200** | **plain CSV, not a ZIP** (`TradDt,BizDt,Sgmt,Src,Fi…`, 850,429 bytes) | **healthy — but the comment is stale.** `bse_provider.py:88-91` says "Served as a ZIP wrapping the CSV"; today it is served plain. No functional break: `_decode_bhavcopy_body` (`:262-271`) already branches on the `PK` magic and falls through to a plain decode. Comment-only drift. |
| `www.bseindia.com/XBRLFILES/SHPXBRLDataXML/`, `.../SHPQNewFormat/w`, `.../AttachLive/` | `bse_provider.py:587-589`, `corporate_disclosures.py:84` | not probed | per-document paths needing a live doc id | untested this run |

### 2d. Yahoo — **the one real rot**

Probed three times with plain `httpx` (the client the code uses), across a >20 s cooldown, then once with
`curl_cffi` Chrome impersonation:

| Endpoint | file:line | httpx | curl_cffi (chrome) | Shape when 200 |
|---|---|---|---|---|
| `fc.yahoo.com` (cookie seed) | `yahoo_batch_provider.py:103` | 404, **0 cookies** | 404, 1 cookie | code tolerates 404 (`:156-163`) and falls through |
| `finance.yahoo.com` (cookie fallback) | `yahoo_batch_provider.py:104` | 200, **0 cookies** | — | serves HTML but sets no cookie for httpx |
| `query2.finance.yahoo.com/v1/test/getcrumb` | `yahoo_batch_provider.py:102` | **429** `Too Many Requests` | **200**, valid 11-char crumb | — |
| `query1.finance.yahoo.com/v7/finance/quote` | `yahoo_batch_provider.py:101` | **429** | **200** | `quoteResponse.result[]` intact — parser contract unchanged |
| `query1.finance.yahoo.com/v8/finance/chart/{sym}` (the yfinance lane) | via `yfinance==1.3.0`, `requirements.txt:4` | **429** | **200** | `chart.result[0].timestamp` intact |
| `feeds.finance.yahoo.com/rss/2.0/headline` | `news_provider.py:97-99` | **429** | **200**, 19 `<item>`s | — |
| `finance.yahoo.com/news/rssindex` | `news_provider.py:70` | **200**, 50 `<item>`s | — | healthy on httpx |
| `yfinance` library end-to-end (`Ticker.history` + `fast_info`) | `yfinance_provider.py:19` | — | **works** — 5 rows, OHLCV columns, live `lastPrice` | healthy |

**Root cause (evidence-backed, not inferred):** Yahoo's API edge hosts —
`query1.finance.yahoo.com`, `query2.finance.yahoo.com`, `feeds.finance.yahoo.com` — now return a blanket
HTTP **429 `Too Many Requests`** (19-byte `text/html` body) to **plain-httpx TLS fingerprints**, while
serving **200** to a Chrome-impersonated TLS handshake from the same IP, seconds apart. The www host
(`finance.yahoo.com`) is unaffected. The payload **shapes are unchanged** — every parser contract still
matches once the request gets through. This is a TLS-fingerprint gate, not a quota and not an API redesign.

**Blast radius.** `yahoo_batch_provider` is explicitly "the screener's fast path (FR-126 / SC-034)"
(`yahoo_batch_provider.py:1`) and uses **pure httpx by deliberate choice** (`:38-40`: *"Pure `httpx` — no new
dependency"*, client built at `:122-137`). Its consumers are `screener.py:861` and `:1216` (universe scan +
enrichment) and `fundamentals_warm.py:174` (the warm-cache refresh). All of those are dead from this
vantage today. `news_provider.py` (httpx, `:52`) loses the **per-symbol** Yahoo headline feed (`:97-99`)
but keeps the market-wide `rssindex` (`:70`). `yfinance_provider.py` is **unaffected** — the `yfinance`
1.3.0 library brings its own impersonating session.

**The fix is one seam, zero new dependencies:** `curl_cffi==0.15.0` is already pinned
(`sidecar/requirements.txt:12`) and already wired through PyInstaller (`--collect-all=curl_cffi`), and the
codebase already has the exact pattern in `nse_provider.py:240-242` (`_new_session` →
`curl_requests.Session(impersonate="chrome")`) and `corporate_disclosures.py:108-112`. The premise of the
`:38-40` comment ("no new dependency") is simply out of date — curl_cffi shipped after it was written.

*Caveat stated honestly:* this was measured from one egress IP. The httpx-vs-curl_cffi split within the
same minute rules out a plain per-IP quota (a quota would block both), but a second vantage (the ROG or the
Oracle VPS) would confirm it is global before the code change is committed.

### 2e. SEC / EDGAR

| Endpoint | file:line | HTTP | Shape | Verdict |
|---|---|---|---|---|
| `data.sec.gov/submissions/CIK{10}.json` | via `sec-edgar-mcp`; UA default `sec_edgar_mcp_subprocess/main.py:84-87` | **200** | `cik` / `name` / `filings` present | healthy |
| `data.sec.gov/api/xbrl/companyconcept/...` | same subprocess | **200** | `units` present | healthy |
| `www.sec.gov/cgi-bin/browse-edgar` | `sec_filings_provider.py:242` — **docstring only** | 1st try ReadTimeout, retry **200** (16,615 B) | HTML | healthy; transient. Grep confirms no app code fetches it — only `tests/test_research_finance.py:34` references it. |
| `www.sec.gov/Archives/edgar/data/{cik}/{acc}/` | `sec_filings_provider.py:248` | link-builder only, never fetched by the sidecar | n/a | n/a |

The `SEC_EDGAR_USER_AGENT` default (`main.py:84-87`) still satisfies SEC fair-access; no 403 seen.

### 2f. Screener seeds

`sidecar/services/screener_universes/` and `screener_universe_india.py` contain **no outbound URLs** (grep
clean). Universes are static seed files enriched through `yahoo_batch_provider` — i.e. their only world
dependency is the Yahoo lane in 2d, and it is the broken one.

---

## Ranked verdict

### ROTTED — breaks today, needs a code change

1. **Yahoo API edge blocks plain httpx (HTTP 429).** `yahoo_batch_provider.py:101-104` + client `:122-137`
   (pure httpx by design, `:38-40`). Kills the screener fast path (`screener.py:861`, `:1216`) and the
   fundamentals warm cache (`fundamentals_warm.py:174`). Also kills the per-symbol Yahoo news feed
   (`news_provider.py:97-99`). **Fix:** route these through the already-pinned
   `curl_cffi==0.15.0` (`requirements.txt:12`) using the existing `nse_provider.py:240-242` pattern.
   Confirmed by A/B: 429 on httpx ×3, 200 on curl_cffi ×1, same IP, same minute, shapes unchanged.
2. **`perplexity/sonar-reasoning` is retired from OpenRouter.** Listed as routable at
   `sidecar/services/research/sonar.py:52`. A caller hinting that slug routes to a 404 model.
   *Mitigation already in place:* `resolve_model` (`sonar.py:89-107`) falls through to `SONAR_DEEP_MODEL`
   for unknowns, and the retired slug is not a **default** anywhere — so the failure mode is "an explicit
   hint 404s", not a broken default. **Fix:** delete line 52; optionally add the new
   `perplexity/sonar-pro-search`.

### AT RISK — works today, will bite

3. **SearXNG image is unpinned (`searxng/searxng` → implicit `:latest`).** `searxng_manager.py:65`. Upstream
   pushed `latest` yesterday and ships 1,018 tags with multiple builds per day, so the user's local
   container can change under the app between pulls with no digest to reproduce. Not broken — unreproducible.
4. **Sonar research pins are not tool-capable.** All three depth pins (`config.py:447-449`) and the whole
   sonar family have `supported_parameters` **without `tools`**. If any lane ever sends `tools=` to them it
   will 400. Fine today (the sonar lane is a one-call research model, not the agent loop) but it is a live
   trap for anyone wiring them into the tool loop.
5. **`perplexity/sonar-pro` costs $3 / $15 per M.** `sonar.py:51`. The single most expensive pin in the repo
   — 5× the `sonar-deep-research` output rate. Worth a deliberate look before any battery run selects it.
6. **`openrouter/auto` carries a −1 price sentinel.** `model_registry.json:71`, `model-selection.ts:59`.
   Any cost estimator reading OpenRouter pricing arithmetically for this slug gets a nonsense negative
   number. `BudgetGuard` uses its own static `PRICE_TABLE` (`model_registry.json:99-118`) so it is safe
   today, but that table's OpenRouter block has only family substrings (`deepseek`, `qwen`, `llama`,
   `gemini`, `gpt`, `claude`) plus a `""` catch-all of $2.00/M, and it is materially out of step with
   today's real rates: `deepseek/deepseek-v4-flash` meters at $0.90/M against a real ~$0.05/$0.10
   (≈13× **over**), `minimax/minimax-m3` falls to the $2.00 catch-all against $0.30/$1.20 (**over**), while
   `qwen/qwen3.7-max` meters at $1.00/M against $1.48/$4.43 and `moonshotai/kimi-k2.6` at $2.00 against
   $0.95/$4.00 (both **under**). The budget ceiling therefore errs in *both* directions depending on the
   slug — it is not conservatively-safe.
7. **BSE bhavcopy comment is stale** — `bse_provider.py:88-91` claims a ZIP; the endpoint now serves plain
   CSV. Code already handles both (`:262-271`). Comment-only.
8. **CLAUDE.md is stale on the deep-research backend.** It describes a `GET /system/deepresearch/probe`
   route and a live `tongyi.resolve_model` fallback to `minimax/minimax-m3`. Neither exists any more:
   no `probe` route in `sidecar/routers/` (grep clean), and the frontend enum is now
   `"native" | "perplexity"` with legacy `"tongyi"` blobs coerced to native (`src/store/settings.ts:45`,
   `:172-175`). Documentation drift, not code drift.

### HEALTHY — verified live, no action

- All nine OpenRouter chat/known-model pins exist and are tool-capable; the default
  `deepseek/deepseek-v4-flash` is in the **global top-5 cheapest tool-capable models**.
- `openai/gpt-5.6-luna` confirmed at exactly the believed **$0.20 / $1.20 per M**, tools supported,
  1.05M context — safe as the battery default.
- Four of the five research/sonar pins still exist at unchanged prices.
- NSE direct (`historicalOR`, corporates), NSE archives (symbolchange, both bhavcopy lanes), all four BSE
  API endpoints and the BSE bhavcopy — all 200, all payload shapes matching the parsers.
- NSE `/api/quote-equity` 403 is pre-existing and explicitly handled (`nse_provider.py:484-487`).
- SEC `data.sec.gov` submissions + XBRL companyconcept — 200, shapes intact, UA accepted.
- `yfinance==1.3.0` end-to-end works (its own impersonating session).
- `searxng/searxng:latest` still published and actively maintained; the container-absent path is a
  deliberate silent degrade to the keyless floor stamped `keyless-fallback`
  (`web_search.py:78-98`, `:55`) — no crash, no false banner.
- `alibaba/tongyi-deepresearch-30b-a3b` is still delisted, exactly as the code already asserts
  (`sonar.py:19-21`, `test_sonar_lane.py:61-65`). No new drift.
