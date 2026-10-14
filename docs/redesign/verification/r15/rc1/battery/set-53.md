# batch-11/W6-options-chain (rc1-battery-1, candidate 4c6dfe8c)

Note: closed in batch-11 per `closure_evidence` (matches the task's own set label).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-079 | live `GET /quant/option/chain/NIFTY` on own sidecar (:52341); full JSON saved | 200 OK, expiry 2026-09-29, underlying_price 23140.5, contracts populated with real `open_interest`/`change_in_oi` on multiple strikes (e.g. 15000 PE: OI 121680, chg 12480; 16500 PE: OI 154700, chg 8190) — matches batch-11's certified shape (provider `nse-fo-bhavcopy`, independently cross-checked against the NSE UDiFF bhavcopy directly by that verifier). Batch-11 also logged a pre-existing, not-a-regression issue (today's-file re-probe on every request can surface a transient 502 even with a good cached prior day) — not newly observed this shard, just noted for completeness | holds |

COVERAGE: 1/1 ids raw; no raw: none.
