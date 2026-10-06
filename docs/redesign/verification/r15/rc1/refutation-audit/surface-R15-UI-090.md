# Refutation audit: R15-UI-090 (group surface) at HEAD 6741387b

Verdict: **partial**

## Certification
batch-4 VERDICTS.md:113 certified both halves: AAPL under IN is not live while the US is closed; Portfolio renders an EOD / Market closed cue.

## Gate verifier refutation (rc1-verifier:6)
probes-059-068-090.txt: at 09:29 IST, GET /quotes/%5ENSEI returned provider yfinance, timestamp 2026-09-25T03:59:04Z, freshness 'eod'; ^BSESN the same.

## Re-run at HEAD
Sidecar: sidecar/.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 52375, VYSTED_DATA_DIR=<scratch>/data.
Clock: 2026-09-25T04:31:00Z = 10:01 IST (NSE open) = 00:31 ET (US closed). This is exactly the entry's repro window.

```
## run at 2026-09-25T04:31:00Z = 10:01 IST = 00:31 ET
region=IN AAPL: {'symbol': 'AAPL', 'provider': 'yfinance', 'timestamp': '2026-09-24T20:00:01Z', 'freshness': 'eod', 'market_state': None}
region=IN %5ENSEI: {'symbol': '^NSEI', 'provider': 'yfinance', 'timestamp': '2026-09-25T04:30:59Z', 'freshness': 'eod', 'market_state': None}
region=IN %5EBSESN: {'symbol': '^BSESN', 'provider': 'yfinance', 'timestamp': '2026-09-25T04:16:00Z', 'freshness': 'eod', 'market_state': None}
region=IN RELIANCE.NS: {'symbol': 'RELIANCE', 'provider': 'nse_direct', 'timestamp': '2026-09-24T00:00:00Z', 'freshness': 'eod', 'market_state': 'REGULAR'}
region=IN %5ENSEBANK: {'symbol': '^NSEBANK', 'provider': 'yfinance', 'timestamp': '2026-09-25T04:31:07Z', 'freshness': 'eod', 'market_state': None}
region=US AAPL: {'symbol': 'AAPL', 'provider': 'yfinance', 'timestamp': '2026-09-24T20:00:01Z', 'freshness': 'eod', 'market_state': None}
region=US %5ENSEI: {'symbol': '^NSEI', 'provider': 'yfinance', 'timestamp': '2026-09-25T04:31:08Z', 'freshness': 'eod', 'market_state': None}
region=US %5EBSESN: {'symbol': '^BSESN', 'provider': 'yfinance', 'timestamp': '2026-09-25T04:16:00Z', 'freshness': 'eod', 'market_state': None}
region=US RELIANCE.NS: {'symbol': 'RELIANCE', 'provider': 'nse_direct', 'timestamp': '2026-09-24T00:00:00Z', 'freshness': 'eod', 'market_state': 'REGULAR'}
region=US %5ENSEBANK: {'symbol': '^NSEBANK', 'provider': 'yfinance', 'timestamp': '2026-09-25T04:31:07Z', 'freshness': 'eod', 'market_state': None}
```

The entry's own repro, AAPL with region IN during NSE hours, reads 'eod', not 'live'. That part is fixed.
The verifier's probe reproduces: ^NSEI has a timestamp 1 second old during NSE hours and reads 'eod'. ^BSESN and ^NSEBANK behave the same way, under both IN and US session regions.

In-process check at a frozen 09:30 IST (services.locale.instrument_region and freshness_for):
```
AAPL         prov=yfinance   instrument_region=US resolver.region_hint=US freshness@09:30IST=eod
^NSEI        prov=yfinance   instrument_region=US resolver.region_hint=None freshness@09:30IST=eod
^BSESN       prov=yfinance   instrument_region=US resolver.region_hint=None freshness@09:30IST=eod
^NSEBANK     prov=yfinance   instrument_region=US resolver.region_hint=None freshness@09:30IST=eod
RELIANCE.NS  prov=yfinance   instrument_region=IN resolver.region_hint=IN freshness@09:30IST=live
RELIANCE     prov=nse_direct instrument_region=IN resolver.region_hint=IN freshness@09:30IST=live
BHP.AX       prov=yfinance   instrument_region=US resolver.region_hint=None freshness@09:30IST=eod
```

Certified tests still pass at HEAD:
- `pytest tests/test_quotes.py -k us_quote_in_an_in_session`: 1 passed, 9 deselected in 0.08s
- `vitest run src/modules/portfolio/PortfolioPanel.test.tsx -t "UI-090|..."`: 1 passed.

## Reasoning
The entry's defect class is freshness-wrong-calendar. Its fix_shape says to resolve the calendar region from the instrument (resolver exchange/region, or quote.exchange). The fix, sidecar/services/locale.py:168-178 `instrument_region`, uses a narrower rule: IN only when the provider is nse_direct/nse/bse or the symbol ends in .NS/.BO, and US for everything else. Indian indices served by yfinance (^NSEI, ^BSESN, ^NSEBANK) have neither signal, so they are dated against the US calendar. The US market is closed during NSE hours, so a live Indian index tick reads 'eod'. This is the same defect with the direction flipped. The batch-9 residual (BHP.AX read 'live' while the ASX was closed) comes from the same default-to-US branch.
The verifier's claim holds, but it tests a sibling symbol class rather than the entry's own repro. The entry's AAPL/IN repro and the Portfolio cue both hold. That makes this 'partial', not a full regression.

Separate observation, not this entry's defect: at 10:01 IST, nse_direct served RELIANCE with timestamp 2026-09-24T00:00:00Z and market_state REGULAR. Its date-only prior-day stamp makes a live NSE quote read 'eod'. This should be triaged on its own as a DATA item if it is not already registered.

## Root cause
sidecar/services/locale.py:176-178: `instrument_region` falls back to REGION_US for any symbol that has no IN provider and no .NS/.BO suffix. Caret-prefixed Indian index tickers (^NSEI, ^BSESN, ^NSEBANK, and others) are not mapped to IN. Non-US and non-IN listings (for example .AX) are also forced onto the US calendar.

## Acceptance test
sidecar/tests/test_quotes.py: add a test next to test_us_quote_in_an_in_session_reads_the_us_calendar. Freeze the clock at _NSE_HOURS and monkeypatch get_quote to return provider 'yfinance' with timestamp=_NSE_HOURS for '^NSEI' and '^BSESN'. With either X-Vysted-Region IN or US, assert `client.get('/quotes/%5ENSEI').json()['freshness'] == 'live'`, and the same for ^BSESN. Also add a unit test asserting `locale.instrument_region('^NSEI','yfinance') == 'IN'`.
