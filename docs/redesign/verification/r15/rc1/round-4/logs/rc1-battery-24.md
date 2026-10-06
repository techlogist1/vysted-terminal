# rc1-battery-24 — regression battery, shard 24 (batch-9/W4 + batch-2/W3 + batch-12/W6)

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Own sidecar :52364 (sleep pid 10487),
data dir rc1-round-4-data-rc1-battery-24 (fresh copy of rc1-round-4-seed-data).

## Sets

- set-38 (batch-9/W4-market-lanes-errors-quant): DATA-065, DATA-062, DATA-066,
  LIFECYCLE-021, DATA-073, UI-053, UI-051 — all live GET/curl repros against :52364, plus
  greps for DATA-073 (holiday table extent + regenerator script) and UI-051 (formatMoney /
  displayCurrency usage). 7/7 hold.
- set-2 (batch-2/W3-research-integrity): RESEARCH-001, RESEARCH-034, RESEARCH-004,
  RESEARCH-003, RESEARCH-029, RESEARCH-037 — all six are pure-function fixes in
  services/research/*, re-run as in-process python calls against the sidecar's .venv
  using the register's exact repro strings/shapes (no live LLM spend needed; these modules
  are documented "no network, no LLM — fully unit-testable"). 6/6 hold.
- set-61 (batch-12/W6-error-copy-markers-option-chain-negative-probe): AGENT-027
  (errors.humanize() in-process on the register rows + batch-12's fresh cases, including a
  real httpx.ConnectError), DATA-114 (live 3x GET /quant/option/chain/NIFTY). 2/2 hold.

No regressions, no new defects, no chain/gate8 findings. findings/rc1-battery-24.json is [].

Notable observation (not a regression): DATA-066's cold 10-name NSE batch took 66.5s
(6.65s/symbol) vs batch-9's certified ~1s/symbol for 20-25 names; warm re-run of the same
batch was 0.01s and a contended cross-provider quote (AAPL) + a sync history route stayed
fast (0.59s/0.55s) while the NSE batch was in flight — the certified fix (other to_thread
routes no longer starve behind nse_direct's lock) holds; the absolute cold-batch latency
looks like live-NSE/network variance, not a code regression, since warm-cache and
cross-provider behavior match the certified numbers exactly.

Sidecar stopped at end of shard (sleep pid 10487 killed).

COVERAGE: 15/15 ids raw; no raw: none.
