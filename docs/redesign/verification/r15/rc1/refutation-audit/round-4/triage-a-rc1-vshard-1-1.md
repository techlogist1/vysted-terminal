# triage-a: rc1-vshard-1:1, the BSE bulk/block lane is never read for dual-listed names

Auditor: Opus, group `triage-a`. Written 07:38 IST.

- HEAD: bed3b166. The code tree equals 01015033.
- Own sidecar on :52420, with scratch data dir `<scratch>/data`.
- Scratch: `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-a/`.

## Verdict

**partial on R15-DATA-024.**

- Severity: **medium**, the same as the shard.
- Certification failures: 1 (baseline 0, plus 1 for this verdict).

## Live at HEAD

```
curl -s -H "X-Vysted-Region: IN" "http://127.0.0.1:52420/disclosures/deals?symbol=KOPRAN"
-> count 62 sources ['NSE bulk', 'NSE block', 'NSE sast'] errors {} coverage covered note None
   Counter({('NSE','bulk'): 48, ('NSE','sast'): 14})
   ... 2026-09-07 NSE bulk UNITED SHIPPERS LTD sell 500000.0      (item3-kopran-deals.json)
```

The same symbol's BSE lane, run in-process with `bse_deals.py`. `_bse_deals` is the function the route uses for BSE-only scrips.

```
KOPRAN is_nse True dual_listed_bse_code 524280
  BSE bulk: 60 rows; 2026 rows: 3 [('2026-09-07', 'UNITED SHIPPERS LTD', 'sell', 700000.0), ('2026-05-25', 'YUGA STOCKS AND COMMODITIES PRIVATE LIMITED', 'sell', 409820.0), ('2026-05-25', 'YUGA ...', 'buy', 26700.0)]
  BSE block: 3 rows; 2026 rows: 0 []
ADANIENT is_nse True dual_listed_bse_code 512599
  BSE bulk: 13 rows; 2026 rows: 0 []
  BSE block: 30 rows; 2026 rows: 0 []
```

What this shows:

- On 2026-09-07 UNITED SHIPPERS LTD sold 700,000 KOPRAN shares on BSE. That is a separate trade from its 500,000-share sale on NSE, because bulk deals are reported per venue.
- The BSE sale and the two May BSE rows are absent from `/disclosures/deals`.
- The response still says `coverage: covered` with no note.

I also checked that no file was written under `~/Library/Caches/bse-bhavcopy`.

## Root cause

`sidecar/services/corporate_disclosures.py:1035-1036`:

```python
if symbol_resolver.is_nse_symbol(bare):
    lanes = [(f"{EXCHANGE_NSE} {k}", lambda k=k: _nse_deals(bare, k)) for k in kinds]
elif code := symbol_resolver.bse_scrip_code(bare):
```

- An NSE listing is served from NSE only. The BSE lane (`:954-975`) is reached only by BSE-only scrips.
- The same file's corporate-actions path already resolves `symbol_resolver.dual_listed_bse_code(bare)` (`:881-885`) and merges the NSE and BSE lanes. The deals path does not.
- The capability text (`agent_tools/catalog.py:869-876`) says "NSE listings get all three". It never tells the model that BSE-venue deals are excluded.

## Why partial on DATA-024

R15-DATA-024 is fixed. Its class is `missing-india-signal`.

- Repro: "Ask who bought or sold a block of an Indian name last week".
- fix_shape: "Add a bulk/block-deal + SAST lane from the public exchange feeds".
- Its stated repro holds: the lane exists and KOPRAN returns NSE rows. Batch-5 certified it on KOPRAN, ADANIENT and CCDL, but tested NSE rows for the NSE names only.
- For a dual-listed name, the BSE exchange feed is implemented but never read. That feed is part of "the public exchange feeds" in the fix_shape, so the entry's own question gets an incomplete answer labelled as covered: the largest KOPRAN seller of the week is short 700,000 shares.
- This is the same missing-India-signal class, not a new mechanism.
- I found no other register entry for deals coverage; a register grep for bulk/block/get_deals/exchange_deals returns only DATA-024.

## Severity

Medium.

- The feature works, and `sources` and each row's `exchange` label the NSE venue.
- The BSE-venue rows are silently missing while coverage reads "covered".
- Workaround: none in-app for a dual-listed name. The BSE site shows the rows.

## Certification failures

R15-DATA-024 baseline is 0:

- no note;
- not in any `not_certified` list;
- no audit partial or regression verdict.

Adding this partial gives **1**.

## Fix shape

In `get_deals`, when `is_nse_symbol(bare)` is true and `symbol_resolver.dual_listed_bse_code(bare)` returns a code, append the BSE bulk and block lanes (`_bse_deals(bare, code, k)` for `k` in `_BSE_DEAL_TYPE`) to the NSE lanes.

- Do not dedup across venues, because each venue's bulk deal is its own trade. Sort by date as today.
- A failing BSE lane lands in `errors` while the NSE rows are still served, as the lane loop already does.
- Update the catalog description to say "dual-listed names get NSE bulk/block/SAST plus BSE bulk/block".

## Acceptance test

In `sidecar/tests/test_b5_india_deals.py`, add a dual-listed case:

- monkeypatch `is_nse_symbol` to True and `dual_listed_bse_code` to '524280';
- `_nse_deals` bulk returns the 500000 NSE row;
- `_bse_get_json` for type 1 returns a Table with the 700000 BSE row.

Assert that `get_deals('KOPRAN', 'bulk')` returns both rows, with exchanges `{'NSE', 'BSE'}` and 'BSE bulk' in `sources`.

Live re-proof:

```
curl -s -H 'X-Vysted-Region: IN' 'http://127.0.0.1:<port>/disclosures/deals?symbol=KOPRAN&kind=bulk' | jq '[.deals[] | select(.exchange=="BSE")] | length'
```

This must print a value greater than 0 and include the 2026-09-07 700000 UNITED SHIPPERS LTD row.
