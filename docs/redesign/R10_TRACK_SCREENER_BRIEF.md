# R10 Track SCREENER — full NSE+BSE universe, never hangs

Branch: `worktree-agent-r10-screener`. Read first: `verification/R10_DEFECT_CATALOGUE.md`
(E4), DECISIONS D40, the contracts commit (models/screener.py + types/screener.ts:
nse-all/bse-all/india-all ids, partial/coverage/freshness fields, ScreenerProgressFrame).

## Files you own (exclusive)

`sidecar/services/screener.py`, `sidecar/services/screener_universe_india.py` (new),
`sidecar/services/fundamentals_store.py` (new), `sidecar/services/fundamentals_warm.py`
(new), `sidecar/services/yahoo_batch_provider.py`, `sidecar/routers/screener.py`,
`sidecar/services/resolver_masters/regenerate_india_sectors.py` (new) +
`india_sector_map.json` (new), `sidecar/app.py` (lifespan hook lines ONLY — Team
ERRORS deletes tradesa lines in the same file; keep your diff minimal so the lead
merges trivially), `sidecar/models/screener.py` (additive only if you need new
string/set fields like `exchange`), and tests (`test_screener_india.py` new,
`test_fundamentals_store.py` new, `test_fundamentals_warm.py` new, existing
`test_screener*.py` updates). Do NOT touch catalog.py (Team RUNTIME extends the
screener capability schemas), src/ (frontend teams), research files.

## 1. Universes — `screener_universe_india.py`

`load_india_universe(universe_id) -> ScreenerUniverse` from the bundled resolver
masters via importlib.resources (pattern: `_load_universe_snapshot`):

- nse-all: every NSE master row → `SYMBOL.NS` (~2,675).
- bse-all: BSE master rows with STATUS=="Active" → `SYMBOL.BO` (group retained).
- india-all: union, NSE listing preferred (skip BSE rows whose SYMBOL is in the NSE
  master).
  `india_symbol_meta(symbol)` → {exchange, scrip_code, isin, name, group}.
  `resolve_universe` in screener.py gains the three branches.

## 2. india_sector_map.json + regenerate script

`regenerate_india_sectors.py` (run by hand once tonight, like
regenerate_bse_master.py): one BSE `ListOfScripData` call → per record
{symbol, isin, industry_raw, sector, shares_outstanding} where `sector` maps BSE
industry strings to the Yahoo 11-sector vocabulary (hand table in the script;
"IT - Software"/"IT - Services"/"Computers - Software" → "Technology", banks/NBFC →
"Financial Services", pharma → "Healthcare", etc. — cover every distinct string the
live payload returns; unknown → null, never a guess) and shares_outstanding derives
from Mktcap/close at snapshot time. Join to NSE symbols via ISIN. RUN IT and bundle
the real JSON (~500KB OK). If bseindia is hostile tonight (it is intermittent —
LESSONS), fall back to building sector data from per-symbol yfinance `.info` for the
NSE master's top ~600 by presence in nifty/size and ship the map partial with an
honest `"coverage"` field in the JSON header object + a note in your report; the
warm crawler backfills sector for the rest at runtime (store sector_source).

## 3. fundamentals_store.py — the columnar cache

SQLite at `config.get_data_dir()/fundamentals_cache.db` (precedent portfolio*db.py),
sync sqlite3 under asyncio.Lock. Schema per D40 (symbol PK in quote form, identity
cols, sector/industry/sector_source, the full numeric vocabulary incl.
shares_outstanding/roe/margins/debt_to_equity/growth/52wk, quote*\* columns,
per-tier stamps quote_updated_at/v7_updated_at/info_updated_at, provider; indexes on
sector, market_cap DESC, info_updated_at). API: `seed_universe(rows)`,
`upsert_v7(symbol, fundamentals, quote)`, `upsert_info(symbol, fundamentals)`,
`query(symbols, require_fields, ttls)`, `prefilter(symbols, cheap_criteria)` (SQL
WHERE translation), `info_priority(symbols, limit)` (never-fetched first, mcap desc,
then stalest), `reset_for_tests(path)`. TTLs: quote 600s (full-universe) / existing
45s curated, v7 6h, info 7d.

## 4. Engine rewrite — `run_screener` phases (E4 dead)

Signature: `run_screener(req, *, wall_budget_s=120.0, on_progress=None)`.
Phases: U universe(5s) → P SQL prefilter (split criteria into cheap [sector/industry/
v7-tier numerics] vs enrichment-needing; top-level AND-ed cheap criteria prune via
the store; OR-trees mixing tiers skip pruning for that branch — pruning may only
WIDEN, never narrow, the candidate set; unit-test this soundness) → B budgeted v7
batch sweep, the WHOLE sweep inside `asyncio.wait_for(min(60, remaining))` — the
unbounded screener.py:687 call dies; chunk ≤50, Semaphore(8); only stale-or-missing
rows → upsert_v7 → re-apply cheap criteria → E targeted `.info` enrichment of
SURVIVORS ONLY (per-symbol timeout 15s, Semaphore(12), budget remaining−10s) →
F evaluate + formula + sort + limit (existing semantics).
On wall expiry / cancellation: finalize partials — unevaluated symbols itemized in
skip_details reason "budget_exhausted"; set `partial=True`,
`coverage="screened {evaluated} of {total} — {n} unavailable"`, `freshness` from the
serving tiers. `on_progress(phase, done, total, detail)` fires per chunk/phase.
Currency note in code comment: market_cap is listing-currency (INR for .NS/.BO).
The agent path bridges on_progress to `config.get_step_sink()` so chat renders live
"sweeping quotes 850/2,100" (the screener_run agent tool already routes through
run_screener — keep that seam working; catalog schema text is Team RUNTIME's).

## 5. SSE route — `routers/screener.py`

`POST /screener/run/stream` → StreamingResponse text/event-stream (precedent
routers/backtest.py): `{"event":"progress",phase,done,total,detail}` frames then
`{"event":"result", …ScreenerResult}`. Client disconnect → CancelledError → engine
finalizes partial and stops. Keep `POST /screener/run` unary, now budget-bounded.

## 6. fundamentals_warm.py — background warming

Started from the app.py lifespan beside start_warm_precompute; region-aware (India
loops only when get_region()=="IN"). Boot seed (<1s) from masters + sector map; v7
sweep of india-all every 15min (reuse/extract the backoff+jitter discipline from
screener.py `_warm_loop` — do not duplicate constants); `.info` crawler:
info_priority(20) per cycle, Semaphore(4), 1.5–3s jitter, PAUSES while a foreground
screen runs (module asyncio.Event the engine sets/clears); `stop_warm_fundamentals()`
in lifespan finally. yahoo_batch_provider: map `sharesOutstanding` into
fundamentals_from_v7.

## 7. Tests

Universe counts/suffixes/dedupe; store upsert/TTL/prefilter; prune soundness; budget
expiry → partial+ledger+`skipped_count==len(skip_details)`; cancellation; v7 mock via
existing `reset_for_tests(MockTransport)` seam; sharesOutstanding mapping; SSE frames
via httpx ASGI transport; warm loop start/stop clean. NO live network in tests.

## Gates before you push

ruff format/check; FULL pytest green; `node scripts/smoke-test-sidecars.mjs` must
still pass at integration (your new bundled JSON rides resolver_masters package data —
verify the PyInstaller spec needs no change; if it does, update ensure scripts and SAY
SO in your report). Granular commits, push at each green milestone.
