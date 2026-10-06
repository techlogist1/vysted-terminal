### 3.3 Market-data & analytics services

All under `sidecar/services/`. `provider_registry.py` resolves by **standard
model key** (`quote`, `ohlcv`, `fundamentals`, `income_statement`, …), walking
installed providers in **preference order** until one succeeds — `asset_class`
is a resolution _hint_ layered on top, not the dispatch switch (FR-035/053; a
`ProviderDeclaration` table — id, model-keys served, preference rank,
credential/availability gate — is the single source of truth, and
`active_providers()` at `/health` derives from it rather than being
hand-maintained). `get_quote`/`get_history` stay **synchronous** (ccxt/yfinance
providers, wrapped in `asyncio.to_thread`); openbb-backed methods stay `async`
— two resolvers (sync/async) share one declaration table and the same
preference-order fallthrough.

- **`yfinance_provider.py`** — no-key default for equities. Load-bearing
  details: `BRK.B`→`BRK-B` rewrite; **dividend-yield divided by 100** (yfinance
  1.3.0 returns a percentage, the contract wants a fraction — a silent corruption
  risk if upstream changes); aggregate rating reads only the single most-recent
  recommendation row.
- **`ccxt_provider.py`** — ccxt (sync REST) + ccxt.pro (async WS). Exchanges:
  bybit, binance, kraken, coinbase. Backs `/crypto/*`.
- **`openbb_mcp_provider.py`** (conditional) — richer fundamentals/macro via the
  openbb-mcp subprocess over Streamable-HTTP. Port 0/unset → `is_available()`
  False → registry falls back. **Whether the binary ships in a given build is
  unverified from service code alone.**
- **`news_provider.py`** — RSS (Yahoo, MarketWatch, per-symbol Yahoo; always on)
  - NewsAPI (BYOK `NEWSAPI_KEY` only). Shared pooled `httpx.AsyncClient` (the
    cold-start TLS-cascade fix). No caching — re-fetches live every request.
- **`sentiment.py`** — VADER lexicon (a deliberate Tier-3 choice: FinBERT would
  drag `torch` into the bundle). Coarse, "at a glance," **not finance-grade** —
  flagged honestly in the docstring.
- **`earnings_provider.py`** — yfinance calendar/estimates/surprises. Fiscal
  period **inferred from calendar month** (best-effort, UI-only); EPS stddev is
  an approximation `(high−low)/4`. Router-side caching.
- **`analyst_ratings_extended.py`** — yfinance has **no individual-analyst
  names** (firm used as label), **no real price-target timeline** (often a single
  synthetic "Consensus" anchor row). Honest degeneracy baked in.
- **`sec_filings_provider.py`** (conditional) — sec-edgar-mcp subprocess. Narrow
  form coverage (10-K/10-Q/8-K/DEF 14A/3/4/5); extractors heavily defensive
  against upstream shape drift. Caches via `data_cache`.
- **`screener.py` + `screener_universes/`** — fan-out filter engine. Universes:
  `sp500` (full S&P 500 — 506 symbols, a static snapshot dated 2026-06-04 that
  has drifted from current membership, R15-LEAD-013 open),
  `nifty50` (50), `crypto-top50` (50, reseeded from the bundled snapshot on
  cache expiry — a live "refresh from ccxt" worker still does **not exist**),
  `custom`. Criteria support **nested AND/OR** via `CriterionGroup`
  (`models/screener.py`, `combinator: "and"|"or"`) — OR-grouping is no longer
  reserved/unimplemented.
- **`services/macro/`** — four in-process providers (FRED requires
