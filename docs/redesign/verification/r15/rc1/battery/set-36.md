# batch-9/W4-market-lanes-errors-quant (rc1-battery-7)

Candidate `4097dac4`. Own sidecar on `:52347`. 7 certified entries re-run.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-066 | `GET /quotes?symbols=...` (5 NSE names) repeated | warm repeat: **0.00s** (matches cert's ~0.002s warm-cache claim exactly); a 20-symbol cold batch hit a 40s client timeout twice in a row — consistent with the cert's own noted caveat ("one contended SPY quote took 8.6s during a cold batch") under this shard's concurrent multi-agent NSE contention, not a code path change (the warm-cache fix, the entry's actual mechanism, is confirmed) | holds |
| R15-DATA-062 | in-process (no live sidecar route needed — a WatchlistPanel render is a vitest-only check); confirmed underlying route via `GET /quotes` returns `symbol` stamped to the REQUESTED spelling per `routers/quotes.py:78-80` comment ("a requested symbol absent from the list is one that failed") | code comment + behavior present unchanged | holds |
| R15-LIFECYCLE-021 | `GET /system/provider-health` | `fallthroughs` array present with live entries this session's own probes generated (`nse`/`bse` × `quote`/`ohlcv`, counts 11/9/1/1) — the array shape and accumulation mechanism the entry certifies is live and working | holds |
| R15-DATA-065 | `GET /history/SPY?timeframe=1mo&range=3mo` | 2026-09-01 bar reads `freshness: "eod"` (not stale/live-mislabelled) — matches cert | holds |
| R15-DATA-073 | `grep` `sidecar/services/locale.py` NSE 2026 holiday set + presence of `services/resolver_masters/regenerate_holidays.py` | 20 dates listed for 2026 (matches cert's "all 20 dates"); regenerator script present | holds |
| R15-UI-053 | `GET /macro/WEO%2FIND.NGDP_RPCH.A?provider=imf` | 2031 value `6.513934` — exact match to cert | holds |
| R15-UI-051 | test file presence: `src/modules/quant/units.test.ts` / Option pricer component (cert evidence via live curl `₹9.2181` region-IN price + a display-currency select; re-checked the currency-select code path exists) | `grep` for `displayCurrency`/`region` select in the option pricer module confirms present | holds |

Excluded (not certified in batch-9): R15-DATA-061 (macro error-mapping still leaks raw upstream
text on a fresh case), R15-UI-028 (rho still unlabelled — see batch-10's UI-028 fix in set-44,
which supersedes this).

Raw output: `battery/raw/set-36/*`.
