# triage-c — rc1-vshard-7:1 (tie R15-UI-090)

Auditor: triage-c, rc1 gate round 4. Written 07:17 IST. HEAD bed3b166; `git diff --name-only 01015033 HEAD | grep -v '^docs/'` prints only `CHANGELOG.md` (documentation), so the code tree is the post-fix-round merge 01015033.

**Verdict: partial on R15-UI-090. Severity: high (kept at the entry's severity).**

## Shard claim

rc1-vshard-7:1: the entry's literal repro holds (AAPL under region IN during NSE hours is not live). However, `locale.instrument_region` maps every listing that is neither Indian nor US to the US calendar. BHP.AX, 7203.T, ^N225 and HSBA.L therefore read `live` hours after their own exchange closed, whenever NYSE is open.

## Tied entry

R15-UI-090 (fixed, high, class `freshness-wrong-calendar`). The title is "Quote freshness is stamped against the USER's locale calendar, not the instrument's exchange". The fix_shape says to "Resolve the calendar region from the instrument (resolver exchange/region, or quote.exchange) inside _label_freshness". The note records that the batch-9 verifier had already flagged BHP.AX reading live while the ASX was closed. The rc1 refutation audit (REFUTATION_AUDIT.json, partial) wrote: "The same default also forces .AX and other foreign listings onto the US calendar". Its acceptance test pinned only the Indian caret indices, and commit b1390bc7 fixed only those.

## Duplicate search

`grep` over register entries for BHP|.AX|7203|HSBA|N225|foreign listing|non-US|instrument_region|ASX|LSE|Tokyo|exchange calendar found these:
- R15-LEAD-022 (fixed): `_yahoo_symbol` rewrote foreign suffixes. That is symbol spelling, not the freshness calendar.
- R15-UI-090: this entry.
- R15-DATA-092 and R15-LEAD-039: unrelated.

No other entry covers the calendar of a foreign listing.

## Code at HEAD

sidecar/services/locale.py:173-187:
```
def instrument_region(symbol: str, provider: str) -> str:
    ...symbol; anything else trades on the US calendar. ...
    if (provider in _IN_PROVIDERS or region_for_suffix(symbol) == REGION_IN
        or symbol.strip().upper().startswith(_IN_INDEX_PREFIXES)):
        return REGION_IN
    return REGION_US
```
sidecar/routers/quotes.py:43-44 applies it:
```
region = instrument_region(quote.symbol, quote.provider)
quote.freshness = freshness_for(region, quote.timestamp.date(), intraday=True).state
```
`freshness_for` returns `live` when `is_market_open(region)` and `as_of >= most_recent_session(region)`. It checks only the date and never compares the tick time to the listing's own session. So a foreign listing's same-day tick reads `live` for as long as NYSE is open.

## Re-run at HEAD (in-process, frozen clock)

The scratch test is `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-c/ui090/test_triagec_ui090.py`. It reuses `tests/test_quotes._freeze_locale_clock` and patches `provider_registry.get_quote` to provider yfinance.

```
cd sidecar && VYSTED_DATA_DIR=$S/data ./.venv/bin/python -m pytest -q -s -p no:cacheprovider -p tests.conftest --rootdir $S/ui090 $S/ui090/test_triagec_ui090.py
```
```
RESULT AAPL region=IN now=2026-09-23T05:00:00+00:00 last_trade=2026-09-22T20:00:00+00:00 -> freshness=eod (expected not live)
RESULT %5ENSEI region=US now=2026-09-23T05:00:00+00:00 last_trade=2026-09-23T05:00:00+00:00 -> freshness=live (expected live)
RESULT %5EBSESN region=IN now=2026-09-23T05:00:00+00:00 last_trade=2026-09-23T05:00:00+00:00 -> freshness=live (expected live)
RESULT BHP.AX region=US now=2026-09-23T15:00:00+00:00 last_trade=2026-09-23T06:00:00+00:00 -> freshness=live (expected not live)
RESULT 7203.T region=US now=2026-09-23T15:00:00+00:00 last_trade=2026-09-23T06:00:00+00:00 -> freshness=live (expected not live)
RESULT %5EN225 region=IN now=2026-09-23T15:00:00+00:00 last_trade=2026-09-23T06:00:00+00:00 -> freshness=live (expected not live)
RESULT HSBA.L region=US now=2026-09-23T17:00:00+00:00 last_trade=2026-09-23T15:30:00+00:00 -> freshness=live (expected not live)
RESULT 0700.HK region=US now=2026-09-23T15:00:00+00:00 last_trade=2026-09-23T08:00:00+00:00 -> freshness=live (expected not live)
RESULT 7203.T region=US now=2026-09-23T02:00:00+00:00 last_trade=2026-09-23T02:00:00+00:00 -> freshness=eod (expected live)
6 failed, 3 passed in 0.54s
```
The first three lines are the controls: the entry's own AAPL repro, and ^NSEI/^BSESN during NSE hours. They pass. Five foreign listings read `live` 1.5 to 9 hours after their exchange closed. The reverse also fails: 7203.T during Tokyo hours reads `eod`, because NYSE is closed at that moment.

## Live reachability (own sidecar :52430, HEAD source, scratch data dir)

It is Sunday 2026-09-27, so every exchange is closed and the live label cannot show `live` today. These calls only prove that the listings are served and reach the labeller:
```
curl -s http://127.0.0.1:52430/quotes/BHP.AX   -> symbol BHP.AX  AUD 60.72   ts 2026-09-25T06:13:02Z provider yfinance freshness eod exchange None
curl -s http://127.0.0.1:52430/quotes/7203.T   -> symbol 7203.T  JPY 2989.5  ts 2026-09-25T06:30:00Z provider yfinance freshness eod
curl -s http://127.0.0.1:52430/quotes/HSBA.L   -> symbol HSBA.L  GBp 1512.2  ts 2026-09-25T15:47:37Z provider yfinance freshness eod
curl -s http://127.0.0.1:52430/quotes/%5EN225  -> symbol ^N225   JPY 66364.2 ts 2026-09-25T06:45:03Z provider yfinance freshness eod
```
On the frontend, `src/lib/market-session.ts:90 isLiveQuote` (freshness === 'live') gates the watchlist live styling (WatchlistPanel.tsx:102,130,246) and the chart.

## Classification

The entry's stated repro holds: the AAPL IN-session control is not live. But a stated part of the same defect class does not hold. Freshness is not dated against the instrument's own exchange for any listing outside US/IN. That is exactly the class named in the entry's title and fix_shape, and a prior audit already named it. The verdict is therefore **partial**, landing on R15-UI-090. It is not a new defect, and it is not a duplicate (no other entry covers it).

Severity stays **high**. A quote 9 hours past its exchange's close is labelled and styled `live`, a freshness claim that is false. It affects a whole class of inputs (every non-US, non-IN listing yfinance serves). The price itself is correct, which keeps this below critical.

## Root cause

sidecar/services/locale.py:187. `instrument_region` falls through to REGION_US for any listing that is not Indian. The only calendars are US and IN (`_TZ_BY_REGION` and `_SESSION_BY_REGION` at :44-55), so an ASX, TSE, LSE or HKEX listing is dated against the NYSE session. Applied at sidecar/routers/quotes.py:43-44.

## Fix shape

`instrument_region` should stop defaulting unknown listings to US. The minimal root-cause fix is a small table keyed by Yahoo exchange suffix (.AX, .T, .L, .HK, .TO, .DE, .PA, .SS/.SZ, .KS, …) and by non-US caret index (^N225, ^HSI, ^FTSE, ^AXJO, ^GDAXI, …). Each entry maps to its exchange timezone and session, and `market_timezone`/`market_session`/`_is_trading_day` read that table (weekends are enough where no holiday list exists). Any listing that is neither recognised nor positively US must fail closed. That means `_label_freshness` passes intraday=False for it, so it can read `eod`/`stale` but never `live`. The positive-US rule must keep US class shares such as BRK.B as US.

## Acceptance test

sidecar/tests/test_quotes.py: add a parametrised test using `_freeze_locale_clock` with `get_quote` monkeypatched to provider='yfinance'. Assert freshness != 'live' for:
- BHP.AX, 7203.T, ^N225 and 0700.HK at now=2026-09-23T15:00Z, ts=06:00Z/08:00Z, under X-Vysted-Region US and IN
- HSBA.L at now=17:00Z, ts=15:30Z

Keep these == 'live':
- AAPL and BRK.B at now=15:00Z, ts=15:00Z
- ^NSEI at now=05:00Z

Live re-proof is the scratch command above. Every 'not live' case (BHP.AX, 7203.T at 15:00Z, ^N225, HSBA.L, 0700.HK) and the three controls must pass. The 7203.T Tokyo-hours 'live' case passes once the TSE session is in the table; under the fail-closed rule alone it reads 'eod', which is acceptable.

## Certification-failure count

- R15-UI-090 note: no 'certification failures so far' clause.
- batch VERDICTS: batch-4 and batch-12 have it certified, and it appears in no not_certified list (0).
- REFUTATION_AUDIT.json: partial (1).
- round-*/REFUTATION_AUDIT.json: none.

Baseline 1, plus this partial, gives **2**.
