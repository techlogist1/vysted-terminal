# battery shard 5 — set-54 (batch-11/W6-options-chain)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-079 | `grep -rniE 'open_interest|openInterest' sidecar/models/ types/` at candidate 949c3c9f (register's own repro command, minus the now-nonexistent `sidecar/services/quotes.py` path). Then live `curl http://127.0.0.1:52345/quant/option/chain/NIFTY` against my own booted sidecar (source: candidate). | grep now hits `sidecar/models/market.py:102` (`open_interest: float | None`) and `types/data.ts:92`; `catalog.py:1059` registers an `option_chain` capability with a description naming exchange-published OI, NSE F&O bhavcopy sourcing. Live GET returned a full NIFTY chain (18 expiries, `underlying_price:23140.5`) with real per-strike `open_interest`/`change_in_oi`/`volume`/`last_price`/`settle_price` values (not all-zero, not a stub) via `routers/quant.py GET /option/chain/{symbol}` → `services/option_chain.get_option_chain`. This is new feature work, not a copy fix — the register's "zero hits, no capability exists" claim no longer holds. | holds |

COVERAGE: 1/1 ids raw; no raw: none.
