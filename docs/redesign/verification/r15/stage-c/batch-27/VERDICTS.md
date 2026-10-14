# R15 Stage C — batch-27 verifier verdicts

Merge target: `worktree-agent-batch-27-int@0338a7bf9bf02c0cacc82a3f76da590d97b3fcca`. The only change from the
ci-local run's tip (`9bb60037`) is a 2-line docstring edit in `symbol_resolver.py`.

Setup: a scratch worktree of the merge target. The sidecar was booted from source on `127.0.0.1:52310` with a fresh
copy of `vysted-iso/data`, and the MCPs were on :52153/:52154. For the A/B comparison, a base sidecar at `e4b9554d`
ran on :52311 with its own data copy.

Chain: the integrator's `pnpm ci-local` passed. It showed lint, format, typecheck, clippy and ruff clean, vitest at
1849/1849, cargo test ok and pytest at 3657 passed with 1 skipped. The smoke test booted all 3 sidecars cleanly. On
the merge target itself, I re-ran the focused tests (`test_symbol_resolver`, `test_yfinance_provider`,
`test_yahoo_batch_provider`, `test_resolve_router`, `test_resolve_symbol_tool` and `test_fundamentals_tool`), and
216 passed.

**Verdict: approve.** Both entries are certified, and nothing I found is a regression.

## R15-DATA-117 — certified

**Original repro (live, `GET /fundamentals/<sym>`):**

| symbol | ccy/fin | price_to_book | book_value | P/S | pe_ratio |
|---|---|---|---|---|---|
| TSM | USD/TWD | None **withheld** | None **withheld** | withheld | 33.55 ok |
| HDB | USD/INR | None **withheld** | None **withheld** | withheld | 16.09 ok |
| AAPL | USD/— | 46.341 ok (unchanged) | 7.36 ok | 10.66 ok | 39.07 ok |

The TSM reason reads: "Yahoo's price/book (listing price over book value per share) divides or states a USD listing
value against TWD statements; its basis cannot be verified without FX, so it is withheld". Both currency codes are
present, and the provider is stamped.

**Fresh cases the fix was not written against:**

- On the primary path, IBN (USD/INR) and SONY (USD/JPY) have P/B and book value withheld, and their P/E stays `ok`.
- On the v7 batch path, I fetched real v7 rows from Yahoo through the yfinance session, because the sidecar's own
  crumb path gets a 429 from this network (see issues). I then ran them through `fundamentals_from_v7`. RDY, TM, UMC
  and SAP, plus TSM, all came back `withheld` with `provider=yahoo-v7-batch`. AAPL (USD/USD) and INFY (reports in USD)
  are served unchanged, at 46.34 and 8.84.
- On the derived-EPS path, I used real `.info` with `trailingEps` and `trailingPE` removed. UMC (TWD) and RDY (INR)
  gave eps and pe `unavailable`, so nothing was derived. MSFT still derives eps 18.01 and P/E 28.66.

**Agent path:** I ran `vy.py invoke copilot` against llama3.1:8b on :52310, asking for TSM's P/B and book value. It
made one `fundamentals` call (`ok`), and the answer states that both are withheld by the provider. No 92.17 was
served.

**fix_shape audit, checked against home listings:**

- The P/E basis is consistent. TSM's P/E is 33.55 against 28.98 for 2330.TW, which is the ADR premium, and its
  forward P/E is 20.55 against 17.31. SONY's is 20.13 against 20.00 for 6758.T. Serving P/E is correct.
- On EV ratios, `ev_to_ebitda` was already withheld. There is no price_to_cash_flow field in `Fundamentals`.
- Book value itself is now withheld.
- The outside-world truth matches the entry: 2330.TW shows P/B 9.98 and book 248.05 TWD, and HDFCBANK.NS shows P/B
  1.87.

## R15-LEAD-040 — certified

**Original repro:** the batch-26 script `b26v/sat-timed.py stub` runs 12 concurrent cold first resolves through the
`resolve_symbol` agent tool, with `yf.Search` stubbed so it answers instantly.

- Base `e4b9554d`: the unrelated `to_thread` waited **7.06 s**.
- Merge target: it waited **0.00 s**.

**Fresh case over HTTP:** the running sidecar took 16 concurrent cold requests, 8 to `/resolve/autocomplete` and 8 to
`/resolve`, all with unique queries. `autocomplete` was not named in the entry. While they ran, I timed an unrelated
`/quotes/AAPL`:

- Base :52311: the first quote under the storm took **5.02 s**, against 0.44 s idle.
- Fix :52310: it took **1.19 s**, against 0.15 s idle.

The remainder is GIL contention from the CPU-bound fuzzy scan. The pool no longer queues the quote. A grep of routers
and services finds no `to_thread(symbol_resolver.resolve|autocomplete)` left. All 5 call sites use
`resolve_async`/`autocomplete_async` on `_RESOLVE_POOL`, which has 4 workers.

The title's "cold masters load" framing was corrected by the planner. The cost is the resolve scan plus the ISIN
lookup, not the masters load. The claim that concurrent first resolves starve unrelated `to_thread` work no longer
reproduces.

## Issues noticed (outside the entries, not in the diff)

1. The sidecar's own v7 crumb flow fails live. `fc.yahoo.com` returns 404, and `getcrumb` and `v7/quote` both return
   429, so every v7 chunk comes back `rate_limited` from this network. yfinance's session fetches the same v7 URL fine.
   Screener and warm-store fundamentals therefore fall back to their stale basis.
2. HDB's `forward_pe` is 16.54, against 11.66 at home for HDFCBANK.NS, while the trailing figures match (16.09 vs
   16.08). Yahoo's ADR forward EPS looks stale, which is a different mechanism from the mixed-currency basis.
3. A derived eps is stamped `status: ok`, with no reason text, on MSFT. This is pre-existing and cosmetic.
