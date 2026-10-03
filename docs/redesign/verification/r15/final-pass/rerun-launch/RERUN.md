# Re-runs owed before r15-launch (CARRY_FORWARD_launch.md, "Re-runs owed before r15-launch")

- Runner: fresh re-proof runner, model `claude-opus-5-5` (Opus 5.5, medium effort). No advisor consulted.
- Release head: `1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056` (tag r15-rc2). Repo HEAD at run time `eaaa42c5` (docs-only on top).
- Binary: `<scratchpad>/bundle-rc2b/src-tauri/binaries/vysted-sidecar-aarch64-apple-darwin`, sha256 `90a8cf92ea6bd4bfff89d6753877e3cc507753df880e79048c571991a2c46447`, `/health` version 0.9.0.
- Port: 52310 (free per `lsof` before start). Data dir: `<scratchpad>/rerun-data`, fresh and empty at start. No key, no keystore, no GUI.
- Start: 2026-10-04 00:31:24 IST (third launch, healthy 00:32:06). End: 00:38:21 IST, pid tree 41500/41502 plus stdin-holder `sleep` 41499 killed by pid, `ps` and `lsof` confirm gone.
- Launch note: the first two launches died silently right after start-up. The sidecar exits when its stdin closes (`main.py` `_exit_when_parent_closes_stdin`), and a plain `nohup ... &` from a tool shell hands it a stdin that closes. The third launch held stdin open with a `sleep 86400` pipe, in its own session. Logs: `<scratchpad>/rerun-sidecar.attempt{1,2}.log`. Each failed launch used a wiped, empty data dir.
- Raw: `raw/` (`sidecar.log` = the healthy run's log, 0 secret-shaped strings, 0 tracebacks; the ERROR lines are yfinance library logs for the malformed symbols).

## 1. Route replay (malformed-symbol matrix and census)

Commands (repo root):

```
python3 docs/redesign/verification/r15/surface/failure-inducer/harness/malformed.py 52310 raw/10-malformed-symbols.jsonl
python3 raw/rerun_census.py 52310 docs/redesign/verification/r15/surface/panels-layouts/final/P-http-replay.jsonl raw/P-census-replay.jsonl
python3 raw/rerun_compare.py   # writes raw/replay-table.md
```

- Failure-inducer: the record's own harness (`malformed.py`), unchanged, 9 symbols x 9 routes = 81 GETs. Record: `surface/failure-inducer/final/10-malformed-symbols.jsonl` (57x200, 24x404).
- Census: every GET in the d38b5d1a `P-http-replay.jsonl` matching `/fundamentals/{s}`, `/fundamentals/{s}/{income,balance,cashflow}`, `/quotes?symbols=`, `/resolve/autocomplete`, `/news`, `/earnings/{s}/estimates`. That is 40 rows, re-issued with the recorded URL byte for byte. No region header, same as the record.
- Raw: `raw/10-malformed-symbols.jsonl`, `raw/10-malformed-run.log`, `raw/P-census-replay.jsonl`, `raw/P-census-run.log`, and the per-row table `raw/replay-table.md` (121 rows).

Pass line (judge): "no 5xx, every 404 carries a typed `detail`, and every status equals the d38b5d1a record. The only allowed difference is a known NSE/BSE listing that now answers 200 from the FINAL-005 filings fallback."

Observed:

- Malformed: 58x200 and 23x404. Census: 35x200, 3x404 and 2x422 (the `news` limit 500/0 validation rows, same as the record). Zero 5xx, zero transport errors.
- Status diffs: exactly one. `double_suffix/fundamentals` `/fundamentals/RELIANCE.NS.NS` was 404 typed and is now 200. The body is `provider` nse filings: `field_meta` `provider:"nse"`, label "consolidated, sum of 4 filed quarters to 2026-06-30", revenue_ttm 11,388,650,000,000, eps 55.22. `pe_ratio` and `market_cap` are null because the quote lane has no price for that spelling. This is the FINAL-005 path: `get_fundamentals_from_filings` gates on `_is_known_india_listing`, and the code treats the double-suffixed spelling as the known listing RELIANCE. The 39 other census statuses and the 80 other malformed statuses equal the record.
- 404 bodies: every handler-level 404 carries the typed `{"detail":..., "code":"not_found", "action":...}`. Five 404s are FastAPI router-level `{"detail":"Not Found"}` with no `code`: html/fundamentals, html/earnings_hist, path_trav/fundamentals, path_trav/earnings_hist and census `083 /fundamentals/BTC%2FUSDT`. All five are byte-identical to the d38b5d1a record. The cause is path routing for symbols with a slash (`%2F`), as the record already documents. They are not a change in the range.

Result: **holds**. The one status difference is the allowed class: the FINAL-005 filings fallback answers 200 for a spelling the code accepts as a known NSE listing. The lead may judge that the double-suffix spelling falls outside "known listing"; the exact observation is above. The five untyped router 404s are unchanged from the record.

## 2. Portfolio crypto through the batch path (P5b)

Command: `curl -sS -H 'X-Vysted-Region: US' 'http://127.0.0.1:52310/quotes?symbols=BTC%2FUSDT,ETH%2FUSDT&asset_class=crypto'`. Raw: `raw/P5b-crypto-batch.txt`.

Pass line (judge): "2 rows, `symbol` equals the requested spelling, currency USDT, freshness `live`."

Observed: HTTP 200 in 3.4 s. Two rows: `BTC/USDT` 84919.99 and `ETH/USDT` 2683.72. Both have `currency:"USDT"`, `freshness:"live"` and `provider:"ccxt:binance"`.

Result: **holds**.

## 3. LLM spot-check

Lock: `/tmp/vysted-r15-ollama.lock` acquired 00:36:29 on the first try and rmdir'd at 00:37:50. Ollama was up with `llama3.1:8b` present.

Command: `sidecar/.venv/bin/python3 scripts/r15/vy.py invoke copilot "What are BDL's P/E and market cap?" --provider ollama --model llama3.1:8b --region IN --port 52310 --tag rerun-launch-llm --timeout 600 --out raw/LLM-bdl-events.jsonl`

Raw: `raw/LLM-bdl-run.log`, `raw/LLM-bdl-events.jsonl`, `raw/LLM-bdl-fundamentals-route.json`.

Pass line (judge): "a fundamentals or price_data call parses under the schema that now carries `region`, and every figure in the reply equals that tool result."

Observed:

- One `tool_use` `fundamentals` with input `{"region":"IN","symbol":"BDL"}`, then `tool_result` `ok:true`. The catalog schema at 1fddb2b1 carries `region` (`catalog.py` fundamentals params). Status ok in 66.7 s, $0.
- Reply: "Bharat Dynamics Limited's (BDL.NS) current P/E ratio is 76.56 and its market capitalization is ₹39,878 crores."
- The SSE `tool_result` frame carries no payload. I compared against `GET /fundamentals/BDL` (`X-Vysted-Region: IN`) on the same sidecar right after the turn. That is the same provider path, warm cache.
  - Fundamentals: `pe_ratio` 76.5588 (derived, "1,088 / 14.21"), `market_cap` 398,783,348,736 INR.
  - Match: 76.56 equals 76.5588 rounded. 398,783,348,736 / 1e7 = ₹39,878.3 crore, which matches ₹39,878 crore.

Result: **holds**. The check against the tool result is indirect: it compares to the same route queried right after the turn, because the stream frame has no body.

## Adjacent notes (not verdicts)

- `fundamentals` answers 200 for `RELIANCE.NS.NS` with RELIANCE's filings while `/quotes/RELIANCE.NS.NS` answers 404 and `/history` returns empty bars. The double suffix is accepted as a known listing by `_is_known_india_listing` only.
- `vy.py` appended one ledger row to `docs/redesign/verification/r15/spend-ledger.jsonl` (tag `rerun-launch-llm`, $0). It is uncommitted, alongside this directory.
- Runner slip, contained: I ran the binary once with `--help` to read its usage. It was still in PyInstaller extraction after 8 s, and I killed it by pid within about 10 s. It left no listener, no `_MEI` dir and nothing in `~/Library/Application Support/com.vysted.terminal`.
