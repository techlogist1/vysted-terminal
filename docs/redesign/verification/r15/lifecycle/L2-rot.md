# L2-rot: six months on, a model slug is retired or an exchange endpoint moves. Does the user see it?

Worker: claude-opus-5-5[1m], 23 Sep 2026, 09:56 to 10:25 IST. Status: DONE. Sidecar and MCP
pair stopped.

Method: code-read of the adapter, registry and frontend paths, plus induced tests on my OWN
sidecar only. That sidecar ran from source on `:52226` with its own MCP pair (`:53226` openbb,
`:53236` sec-edgar). Its data dir is a `sqlite3 .backup` copy of `$ISO/data` at
`<scratchpad>/vysted-iso/seat-l2-rot/data`. I booted it under three env profiles
(`L2-rot/harness/boot.sh`):

| profile | how induced (my process only) |
|---|---|
| `base` | normal env |
| `deadhost` | `HTTPS_PROXY`/`https_proxy` point at `harness/deadhost_proxy.py`, a loopback CONNECT proxy on `:52286`. It tunnels every host except `*.nseindia.com`, and answers CONNECT for those with a 502. That is what a client sees when the upstream host is gone. `NO_PROXY` keeps loopback direct |
| `moved` | `harness/rot_main.py` runs the unmodified `main.main()` after renaming NSE's endpoint paths in-process: historicalOR, quote-equity, the UDiFF and legacy bhavcopy archives, and symbolchange.csv. The host still resolves and the old path 404s, which is what a released binary sees after NSE moves an endpoint. No source file was edited |

The in-process probes (`harness/parser_drift.py`, own scratch data dir, no sidecar) call the
real provider functions. Only the upstream answer changes: one real historicalOR window with
renamed keys, a renamed CSV header, or a moved archive URL. All LLM calls went through
`scripts/r15/vy.py` on the free lane. The spend-ledger tags start with `life-l2-rot-`, and $0
was spent. Evidence lives in `lifecycle/L2-rot/`: `http-log.jsonl` has 33 rows across 3
profiles, plus `20-…` to `24-…` and `30-parser-drift.txt`.

No endpoint is configurable. Every exchange host and path is a module constant:
`nse_provider.py:88-95`, `nse_bhavcopy.py:92-95`, `nse_symbol_change.py:84`,
`bse_provider.py:92-96,588-590` and `corporate_disclosures.py:83-84`. `grep os.environ` over
`services/` and `routers/` finds only MCP ports, NewsAPI/FRED keys, the region and the data dir.
When NSE moves an endpoint, recovery needs a code release. Until then, whatever the failure
path does is what the user lives with.

## 1. Retired chat-model slug: honest

| induced | what the app SAID (SSE) | honest? | evidence |
|---|---|---|---|
| `z-ai/glm-4.5-air:free` (OpenRouter dropped the free variant) | 0.9 s: `error` `code=model_not_found`, "The requested model is not available on OpenRouter — pick another model." / "Choose a different model in Settings." `detail` quotes OpenRouter's "use this slug instead: z-ai/glm-4.5-air" | **honest** | `L2-rot/20-retired-slug.*` |
| tool-less free model `z-ai/glm-5.2:free` on a tool agent | 0.2 s: the same `model_not_found` text. The upstream said "No endpoints found that support tool use" | partial: the model exists and only its tool endpoints are gone. The "pick another" action still fixes it | `L2-rot/21-retired-research-model.*` |
| nonsense slug | already filed as SURF-FAILURE-INDUCER-5 (400 shown as "Something went wrong… Try again") | not re-run | `surface/failure-inducer/21-*` |

Mechanism: `errors.py:173-180` maps any 404 on an LLM path to `model_not_found`. The chat's
`ErrorRow` shows the message, the action and "Details" (`ChatSidebar.tsx:1239-1250` via
`streaming.ts:344-356`, per `surface/failure-inducer/EVIDENCE.md`). The stale pick survives a
relaunch by design (`model-selection.ts:69-75`, `isKnownModel` is always true for OpenRouter).
Nothing checks it against the live catalog before a send. The live catalog *is* fetched
(`model-catalog.ts:96`), but `ChatSidebar.tsx:818` reads it only for the `webSearch` hint. The
first send after a retirement is the detection point, and that detection is clear. No finding.

Side note for L3: the `detail` string carries OpenRouter's account `user_id` (`user_2tEz…`)
verbatim into the chat's "Details" disclosure and the SSE stream.

## 2. Pinned slugs measured against today's catalog: rot has already landed

`L2-rot/24-pinned-slug-catalog-check.txt` checks every pinned slug against
`GET https://openrouter.ai/api/v1/models` (public, 454 models, fetched 23 Sep).

| pin | where | today |
|---|---|---|
| chat default + 8 known OpenRouter models | `model-selection.ts:34,51-59` | all LIVE |
| research defaults `sonar` / `sonar-reasoning-pro` / `sonar-deep-research` | `search-settings.ts:85-89` | all LIVE |
| **`openai/o4-mini-deep-research`**, **`openai/o3-deep-research`** | `search-settings.ts:144-153`, offered in Settings with `priceVerified: true` ("verified live 2026-06-11") | **GONE** |
| **`perplexity/sonar-reasoning`** | `sonar.py:49-55` `SONAR_MODELS` (a "routable" allow-list) | **GONE** |

Three of 18 pinned slugs (17%) retired within 3.5 months of being "verified live". OpenRouter
also publishes an `expiration_date` per model; 21 models carry one today, some as soon as 25
Sep. `grep -rn expiration_date src sidecar/services sidecar/routers` finds no consumer. The
catalog adapter `openrouter_catalog.py` reads `supported_parameters` but not expiry. The
Settings research picker is a static constant (`SettingsPanel.tsx:1003-1007`) and never
consults the live catalog.

### What a retired research model does to a research turn (induced)

`L2-rot/23-retired-research-model.*`. The `researcher` agent ran on
`nvidia/nemotron-3-super-120b-a12b:free`, tier_b, with every stop set to
`openai/o3-deep-research`. This is what a user gets after picking "OpenAI o3 Deep Research" in
Settings.

- The model called `research` **5 times**. Each call emitted two `research_step` frames, both
  `"status":"ok"`: `research:begin …` and `research-model:openai/o3-deep-research — hosted
  research model (normal stop, via OpenRouter)`.
- Every call's tool result was `{"ok": false, "message": "The hosted research model request
  failed with HTTP 404."}` (`deep_research.py:723-724` → `_research_model_http_error`
  `:505-523`, which has no 404 branch). The result goes only to the model. Its reasoning
  stream shows it looping: "We already tried several variations and got HTTP 404".
- The stream ended `done` with `finish_reason: "tool_calls"` and **zero assistant text**. There
  was no `error` frame. Per `chat-history.ts:213-219`, a text-less `done` renders as a finished
  empty turn with no Retry (the mechanism is SURF-FAILURE-INDUCER-1).
- An earlier attempt (`22-…`, `qwen/qwen3.8-27b:free`) showed the same "ok" steps, then the
  free chat model hit a 429.

The user's view: the research steps tick "ok", then nothing. Nothing names the model, says it is
retired, or points at Settings → Research. The chat lane's own 404 handling (section 1) would
have said exactly that. The research lane has its own error table without it. → **LIFE-L2-ROT-1**

## 3. A dead exchange host (`deadhost`): the lanes fall through, and only a provider label changes

Measured on `http-log.jsonl` rows `deadhost:*`, against `base:*` for the same requests.
`proxy.jsonl` counted `www.nseindia.com` blocked ×26, `nsearchives`/`archives` blocked ×2, and
`bseindia`/`yahoo` tunnelled.

| route | base | deadhost | user-visible difference |
|---|---|---|---|
| `/quotes/RELIANCE.NS` | 200, `nse_direct`, EOD 22 Sep, 1240.4 | 200, **`bse`**, `freshness:"live"`, 1243.2, `volume:null` | watchlist `ProvenanceBadge` (`WatchlistPanel.tsx:74`) |
| `/history/RELIANCE.NS` 3mo | 200, `nse_direct`, last-bar volume 10,684,376 | 200, **`bse`**, last-bar volume **560,999** (5%) | chart status reads "via bse" (`ChartPanel.tsx:1420-1421`). The volume pane is a different exchange's |
| `/quotes?symbols=TCS,INFY,SUZLON` | all `nse_direct` | `nse` (jugaad, disk-cached) ×2 + `bse` ×1 | badges only |
| `/disclosures/*` RELIANCE | 200 | 200 in 0.0 s from `data_cache` | none, the cache masks it |
| `/health` | `ohlcv/quote: "ccxt (nse_direct, nse, bse, yfinance fallback)"` | **identical** | none |
| `/system/provider-health` | `yahoo` only | `yahoo` only | none |

The sidecar log is the only place the death shows up: one `provider nse_direct failed for …,
falling through: … CONNECT tunnel failed, response 502` WARNING **per request**
(`provider_registry.py:362-364`). `/health` is derived from `ProviderDeclaration.available()`
(`provider_registry.py:552-570`), which for nse_direct means "curl_cffi imports"
(`nse_provider.py:139-146`). `/system/provider-health` knows only the Yahoo breaker
(`provider_health.py:49`). The `moved` profile behaved the same way: `nse_direct: HTTP 404 for
/api/historicalOR-v0-retired/cm/equity` once per request, and jugaad (`nse`) served. nse_direct's
per-path breaker counts only 401/403 (`nse_provider.py:323-341`), so a 404 path is retried with
a fresh throttle slot on every quote and history call, forever. → **LIFE-L2-ROT-2**

The fallback chain itself works as designed. Nothing on screen goes blank. The problem is that
the product's own "first-party exchange data" lane can be dead for months, and neither the user
nor a maintainer reading `/health` would know.

## 4. Changed payload shape: a partial drift is served as fabricated candles

`L2-rot/30-parser-drift.txt`. One real historicalOR window (RELIANCE, 8 to 22 Sep, 10 rows) was
fetched live. Then the four OHLV keys (`CH_OPENING_PRICE`, `CH_TRADE_HIGH_PRICE`,
`CH_TRADE_LOW_PRICE`, `CH_TOT_TRADED_QTY`) were renamed, the way an upstream API revision
renames fields.

| probe | result |
|---|---|
| A1 `_rows_to_bars` | every bar `open = high = low = close`, `volume = 0.0` |
| A2 `provider_registry.get_history("RELIANCE.NS","1d","1mo")` | **served**: `provider:"nse_direct"`, 10/10 bars flat, 10/10 zero-volume. The correctness gate passed it |
| A3 `_quote_from_history` | price and change correct, `volume:null` (honest null) |
| A4 close key also renamed | `ProviderError: no EOD data`, then honest fall-through |
| B1/B2 bhavcopy header drift (`TckrSymb`→`TckrSym`, `ClsPric`→`ClsgPric`) | `parse_bhavcopy` → `{}`, then "parsed to zero equity rows" WARNING and degrade (honest) |

The mechanism is `nse_provider.py:405-409`: `open=_num(...) or close`, `high=… or close`,
`low=… or close`, `volume=… or 0.0`. The BSE lane does the same (`bse_provider.py:240-244`).
`correctness_gate.validate_series` (`correctness_gate.py:118-140`) checks only non-empty bars,
last close > 0 and symbol match. A renamed close fails honestly. A renamed high, low or volume
is papered over with invented values under the exchange's own label, and ATR, VWAP, volume
indicators and the candle bodies are all computed from them. → **LIFE-L2-ROT-3**

## 5. A moved archive path: a 404 is read as a holiday

`30-parser-drift.txt` C1 to C3. The run used a fresh scratch cache, IST 23 Sep ~10:15, with
today's file not yet published.

| step | requests | result | cache after |
|---|---|---|---|
| C1 archive path moved | 6 × 404 (23, 22, 21, 18, 17, 16 Sep) | `None`. The only log line is "no bhavcopy found within 7 days" | **`{"empty": true}` holiday markers written for 22, 21, 18, 17, 16 Sep** |
| C2 path fixed (the "hotfix release"), same cache | 1 × 404 (today, unpublished) | **`None`**. The five poisoned days are skipped without a request | unchanged |
| C3 control: path fixed, clean cache | 404 (today) + 200 (22 Sep) | `2026-09-22`, 2,921 rows | normal |

The mechanism is `nse_bhavcopy.py:345-348`, where any 404 returns `"missing"` (the comment
says "a holiday, or today's not yet published"). `:388-394` then caches a past-date `missing`
as `_EMPTY_MARKER` for `_CACHE_TTL_SECONDS` = 7 days (`:101`). No 404 is ever logged. On the
live `moved` sidecar with a warm cache, the lane produced **zero** log lines, because 22 Sep was
already cached.

The consequence: `fundamentals_warm.bhavcopy_refresh_once` (`fundamentals_warm.py:263-265`)
returns 0 and the exchange-direct EOD lane (the one that "keeps prices one-trading-day fresh
on a Yahoo-blocked IP", `:254-258`) stops. Screener freshness headers exist
(`ScreenerPanel.tsx:117`), so the staleness may surface as an old "quotes as of" date. I did
not induce that far: NEEDS-GUI / not driven. Even after the fix ships, the poisoned week stays
lost until the markers expire. → **LIFE-L2-ROT-4**

The symbol-change master behaves the same way (`D1`): the moved path gives
`HTTP 404 … symbolchange-v0-retired.csv`, then "no file and no recent cache — rename lane is a
no-op", and `lookup_current("ZOMATO")` returns `None`. With a warm cache it serves the cached
map for up to 30 days, logged as "network down — serving cached" (`nse_symbol_change.py:418-423`,
the wrong label for a 404), then goes silently inert. That folds into LIFE-L2-ROT-4's notes. The
rename lane's user impact is already filed as SURF-ONBOARDING-STRANGER-5.

## Measured facts

| # | induced at my edge | visible to the user? | explained? |
|---|---|---|---|
| 1 | retired chat slug | yes, error row | yes, names the fix |
| 2 | tool-less model | yes, error row | partly ("not available") |
| 3 | retired **research** model (pinned in Settings today) | a blank turn after "ok" steps | **no** |
| 4 | NSE host dead | only as "via bse" / a badge | **no**. `/health` is unchanged |
| 5 | NSE API path moved (404) | only as "via nse" / a badge | **no** |
| 6 | historicalOR OHLV fields renamed | flat candles, zero volume, labelled nse_direct | **no**, fabricated |
| 7 | historicalOR close renamed | falls through, badge | no, but the data is honest |
| 8 | bhavcopy path moved | nothing (warm cache), then stale screener prices | **no**. Logged as "no bhavcopy within 7 days", with holidays poisoned |
| 9 | bhavcopy header drift | nothing on screen | log WARNING only |
| 10 | symbolchange path moved | renames stop resolving | **no** ("network down" in log) |

## Root cause read-back (recorded, nothing fixed)

- **No liveness signal for exchange lanes.** `/health` reports importability, and
  provider-health tracks one vendor (Yahoo). Registry fall-through logs a WARNING per request
  and keeps no counter. The smallest fix shape is a per-provider fall-through counter in
  `_resolve_sync`/`_resolve_async`, exposed on `/system/provider-health`, with a quiet
  "NSE lane degraded, serving BSE" chrome notice once it crosses a threshold.
- **404 is overloaded.** It means "holiday / not yet published" in `nse_bhavcopy`, "not a
  block" in `nse_provider`'s breaker and "network down" in `nse_symbol_change`. A calendar
  check (a weekday that is not an NSE holiday) or "404 on N consecutive past trading days"
  would separate an endpoint move from a holiday.
- **Defaulting missing fields to `close`/`0.0`** fabricates data. Missing OHLV should be
  `None`, or the gate should reject a series where every bar is flat or zero-volume.
- **Pinned slugs are never reconciled with the live catalog.** The catalog is already fetched
  (`model-catalog.ts`, `openrouter_catalog.py`) and carries `expiration_date`. The research
  lane's HTTP-error table (`deep_research.py:505-523`) lacks the chat lane's 404 case, and its
  failures never become a stream-visible error step.

## Not tested

- The Settings and HUD pickers' rendering of a stale selected slug: NEEDS-GUI (code-read
  above).
- The screener's "quotes as of" header during a long bhavcopy outage: NEEDS-GUI. It would also
  need a multi-day clock skew. Not induced.
- A paid-lane retired slug (OpenAI direct): the chat 404 path is provider-agnostic
  (`errors.py:173-180`), so it was not worth the money ($0.00, since a 404 bills nothing, but
  it was out of this item's need).

## Continuation (refute-stage re-check, 10:11 IST): the bhavcopy fallback is never tried on a 404

Method: induced test, in-process, real network, fresh scratch cache
(`<scratchpad>/vysted-iso/seat-l2-rot/probe-e-data`), source untouched. Only `_UDIFF_URL` was
moved; the legacy `sec_bhavdata_full` fallback was left live (`L2-rot/harness/fallback_skip.py`,
output `L2-rot/31-fallback-skip.txt`).

| Probe | Observed |
|---|---|
| `_fetch_day(2026-09-22)`, primary moved | `('missing', None)` after ONE request (primary 404); fallback not requested |
| direct GET of the fallback URL for the same day | 200, 397,662 B, 2,921 equity rows parsed |
| `fetch_latest()` | `None`; 6 primary requests, 0 fallback requests; empty markers written for 22, 21, 18, 17, 16 Sep |

Root cause read-back: `_fetch_day` returns `"missing"` on any 404 before it reaches the
fallback (`nse_bhavcopy.py:345-348`, "the fallback host would 404 identically"). The fallback
only helps against blocks and 5xx, not against the path move this item is about. So a move of the
UDiFF path alone kills the lane even though a working source is one request away. This sharpens
LIFE-L2-ROT-4. It is recorded in that finding's refute verdict and was not filed separately.
