# triage-a: rc1-vshard-6:1, the S&P 500 screen serves Indian namesakes after an IN-session run

Auditor: Opus, group `triage-a`. Written 07:45 IST.

- HEAD: bed3b166. The code tree equals 01015033.
- Own sidecar on :52420 with a **fresh** scratch data dir (`<scratch>/data`): `main.py --data-dir`, MCP subprocesses unbound except my own sec-edgar-mcp.
- Scratch: `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-a/`.

## Verdict

**new_defect_confirmed.**

- Severity: **high**, raised from the shard's medium.
- It does not land on a register entry, so the certification-failure count is 0 (n/a).

## Live at HEAD

The bare ticker resolves by session region:

```
curl -s -H "X-Vysted-Region: IN" http://127.0.0.1:52420/fundamentals/PTC -> {'symbol': 'PTC.NS', 'name': 'PTC India Limited', 'currency': 'INR', ...}
curl -s -H "X-Vysted-Region: US" http://127.0.0.1:52420/fundamentals/PTC -> {'symbol': 'PTC', 'name': 'PTC Inc.', 'currency': 'USD', ...}
```

Run 1: one S&P 500 screen in an IN session, on the fresh store:

```
curl -s -X POST -H "Content-Type: application/json" -H "X-Vysted-Region: IN" \
  -d '{"universe":"sp500","criteria":[],"limit":600}' http://127.0.0.1:52420/screener/run
-> coverage: 'screened 498 of 503 — 5 unavailable · spans INR, USD — ranked within each currency · ...'  throttled: True
   HAL  Hindustan Aeronautics Limited        INR 4800.0 live
   CCL  CCL Products (India) Limited         INR 1044.4 live
   IEX  Indian Energy Exchange Limited       INR 112.7  live
   ACGL Automobile Corporation of Goa Limited INR 1737.8 live
   PTC/PNC/PPL/TECH/IT/MOS: correct US names (snapshot basis, not refetched this run)
```

The store is now poisoned under the S&P 500 keys (sqlite, read-only, on my scratch `fundamentals_cache.db`):

```
HAL|Hindustan Aeronautics Limited|INR|3210120003584.0|... info/v7 stamped 2026-09-27 01:59:25 UTC
HAL.NS|Hindustan Aeronautics Limited|INR|...        (the legitimate IN key, separate row)
CCL|CCL Products (India) Limited|INR|...  IEX|Indian Energy Exchange Limited|INR|...  ACGL|Automobile Corporation of Goa Limited|INR|...
PTC|PTC Inc.|USD|...                     (not refetched this run)
```

Run 2: the S&P 500 screen in a **US** session straight afterwards:

```
-> coverage: '... spans INR, USD ...'
   HAL  Hindustan Aeronautics Limited INR 4800.0 live
   CCL  CCL Products (India) Limited  INR 1044.4 mixed
   IEX  Indian Energy Exchange Limited INR 112.7 live
   ACGL Automobile Corporation of Goa Limited INR 1737.8 snapshot
```

The shard saw PTC, and I saw HAL, CCL, IEX and ACGL. Which of the 10 colliding tickers gets swapped depends on which ones fall to the per-symbol path in a given run; the colliding set is ACGL, CCL, HAL, IEX, IT, MOS, PNC, PPL, PTC and TECH.

The bundled seed packs are not the cause:

- `india_fundamentals_seed.json.gz` keys every row with a suffix (`PTC.NS`, `HAL.NS`, `ACGL.BO`).
- `us_fundamentals_seed.json.gz` keys the bare US rows (`PTC` PTC Inc., `HAL` Halliburton).

## Root cause

- `sidecar/services/screener.py:555`: `_fetch_pair` calls `provider_registry.get_fundamentals(symbol)` without a region.
- `:574`: it calls `get_quote(symbol, asset_class)` without a region.
- `:1078`: `_enrich_survivors` calls `get_fundamentals(key)` without a region.
- `provider_registry._effective_region` (`provider_registry.py:312-326`) defers an ambiguous bare ticker to the session region. `symbol_resolver.region_hint` returns nothing when a ticker is in both masters.
- So in an IN session a bare S&P 500 ticker resolves to the NSE company.
- `_store_pair` (`:585-591`) and `upsert_info(key, rich)` (`:1094`) then write that company under the bare universe key.
- The written row is stamped `live`, so every later session, US included, serves it until the tier goes stale.
- These paths run when the v7 batch sweep misses (Yahoo 429, `throttled: True`) and for survivor enrichment, including the warm loop at `:1285-1291`.
- The universe is intrinsically US: `resolve_universe` loads `sp500.json` as bare US tickers. Its region is dropped before the per-symbol fetch.

## Why new, not partial or duplicate

**R15-LEAD-013** (the shard's tie) is class `stale-static-reference-data` and is about sp500 pack membership drift. It is not this defect.

- The pack is correct: PTC and HAL are current members. Batch-11 diffed it against Wikipedia and found 0 missing and 0 extra.

**R15-DATA-002** (blocked_tier4, critical, same `wrong-entity-ticker-collision` family) is related but does not cover this.

- Its root cause and fix_shape concern the frontend dropping the **picked** /resolve candidate's region on panel fan-out, and a cross-region tie chooser.
- The screener has no picked instrument, because the universe itself carries the region. Its fix, carrying the picked instrument through the Equity Overview and chart, cannot reach `screener._fetch_pair` or `_enrich_survivors`.
- The store-key poisoning across sessions is not in DATA-002 either.

**R15-DATA-001** (fixed) covers openbb statements for IN tickers colliding with US ones, the reverse direction on a different surface.

A register grep for Halliburton, Hindustan Aeronautics, PTC India, collision, region_hint and `_effective_region` finds nothing on the screener.

## Severity

High: a core flow, the S&P 500 screen and the agent's screener tool that runs it, is broken for a class of inputs.

- Non-member Indian companies are served as live S&P 500 rows, and Halliburton, Carnival, IDEX and Arch Capital drop out.
- The poisoned store row persists into US sessions.
- It is not critical because each wrong row carries its own Indian name and INR currency, so the swap is visible on the row. No numbers are silently corrupted under the right name.

## Fix shape

Thread the universe's intrinsic region into the screener's per-symbol fetches:

- `sp500` maps to "US"; the India universes (`screener_universe_india.is_india_universe`) and `nifty50` map to "IN"; a custom list keeps `None` and so defers to the locale.
- `_fetch_pair(symbol, asset_class, region)` passes it to `provider_registry.get_fundamentals(symbol, region=region)` and to `get_quote(symbol, asset_class, region)`.
- `_enrich_survivors` passes the same region.

As a guard, `_store_pair` and `upsert_info` should refuse to write a result whose resolved listing differs from the key: a `Fundamentals.symbol` of `PTC.NS` under key `PTC` is logged and skipped. That guard also stops an already poisoned store being refreshed with the wrong entity.

## Acceptance test

In `sidecar/tests/test_screener.py`, set `config.set_request_region('IN')`. Monkeypatch `provider_registry.get_fundamentals(symbol, region=None)` to record `region`: it returns Halliburton/USD when `region == 'US'` and Hindustan Aeronautics/INR otherwise. Make the v7 batch return no row for HAL, so the fallback runs, and run an sp500 screen restricted to HAL. Assert:

- the recorded region is 'US';
- the HAL row name is 'Halliburton Company' with currency 'USD';
- the coverage string contains no 'INR'.

Add a second case for `_enrich_survivors` with the same assertion.

Live re-proof, on a fresh data dir:

```
curl -s -X POST -H 'Content-Type: application/json' -H 'X-Vysted-Region: IN' -d '{"universe":"sp500","criteria":[],"limit":600}' http://127.0.0.1:<port>/screener/run | jq '[.rows[] | select(.currency=="INR")] | length'
```

This must print 0, including after a throttled run.
