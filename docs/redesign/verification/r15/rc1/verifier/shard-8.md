# rc1 adversarial verifier: shard 8 (rc1-vshard-8, Opus)

Candidate: `81fbfe910d472ecd154fa62e42d86bce213a697e`, worktree `scratchpad/rc1-4c6dfe8-fix-int`. I checked `git rev-parse HEAD` there before every in-process check.
My own sidecar ran on :52608 with data dir `scratchpad/rc1-data-rc1-vshard-8` and sleep pid 89378. It is stopped now.
`scripts/r15/vy.py` refuses non-GET calls outside ports 52100-52399, so the live llama3.1:8b agent runs went to the shared read-only stack on :52152 instead. That stack runs 4c6dfe8c. `git diff --quiet 4c6dfe8c 81fbfe91` over the following files is empty, so they are byte-identical to the candidate: `agent_runtime.py`, `agent_tools/`, `agents/`, `llm/`, `correctness_gate.py`, `yfinance_provider.py` and `tool_call_rescue.py`.
The Ollama lock was taken for every model call. Twice the trap's rmdir found the lock already gone, which means another agent had removed it during my hold. That is a harness observation, not a product finding.
Evidence files are in `shard-8-evidence/`.

| id | verdict | one line |
|---|---|---|
| R15-RESEARCH-007 | refuted (not_certified) | Literal repro and all earlier fresh lists hold at tier 3. Fresh blog and newsletter platforms still rank PRIMARY and outrank Reuters. |
| R15-DOCS-017 | holds | Every §3.3 figure matches the live loader and route (nse-all 3506 = EQ 2584 + ETF 351 + SM 571; bse-all 5042; india-all 5891; sp500 503 as of 2026-09-24). Nested AND/OR via `CriterionGroup.combinator` matches the doc. |
| R15-CODE-DATA-023 | holds | Both named comments now describe composition without counts. `_nse_lookup`'s "~5,156" is already R15-LEAD-029 (open). |
| R15-AGENT-090 | refuted (not_certified) | The live literal repro and a live TSM run were guarded, and grounding is correct. A fabricated decimal SIFY ratio still passes the guard. |
| R15-LEAD-030 | inconclusive | The live literal repro streamed no figure. The entry is blocked_tier4, a known limitation accepted in DECISIONS 4.9-4.12. Its title claim was not re-litigated. |
| R15-LEAD-033 | holds | The literal two-turn repro and a fresh RELIANCE/price-data turn (asked to repeat "every line") echoed no `[tool steps:`. |
| R15-LEAD-034 | holds | `symbols_match` holds for 6 random Emerge symbols from the master. The in-process yfinance path plus `validate_fundamentals` passes the gate for SCML, INSPIRE and QVCEL. |

## R15-RESEARCH-007: refuted
- Command: in `<cand>/sidecar`, run `.venv/bin/python` against `services.research.finance` using `domain_tier`, `rank_sources` and `priority_note` (output in `r007.out`).
- These still tier 3: the literal repro (medium, wordpress, the `/investors-rush` path), the audit acceptance list (investors.com, github.io, blogspot.in, wixsite, netlify, hubpages) and the batch-12 list (firebaseapp, web.app, azurewebsites, onrender, fly.dev, notion.site, herokuapp and the ccSLDs). The controls ir.nvidia.com, investors.infosys.com, investor.apple.com and ir.tatamotors.com still tier 1.
- Fresh cases that tier 1 (PRIMARY) with both the `ir.` and the `investors.` prefix: typepad.com, livejournal.com, beehiiv.com, ghost.io, hashnode.dev, over-blog.com, neocities.org, jimdosite.com, godaddysites.com, tilda.ws, site123.me, mystrikingly.com, webnode.page and 000webhostapp.com. None of these is in the vendored PSL, and none is on `_IR_PLATFORM_DENYLIST`.
- `rank_sources([Reuters, investors.beehiiv.com, ir.typepad.com])` returns `['Beehiiv newsletter', 'Typepad blog', 'Reuters']`, and `priority_note` returns `primary record (exchange/regulator/filings/IR): [1, 2]; tier-1 press: [3]`. That is the title's defect exactly: a blog post owns [1] and is called the primary record.

## R15-AGENT-090: refuted
- Live literal repro (`a090-orig.out`, llama3.1:8b): the model called `financial_statements` with symbol `SIFYUS`. The answer streamed only `RATIO_UNAVAILABLE`, and it stated no revenue figure.
- Live fresh case TSM (`a090-tsm.out`): `fundamentals` was rate-limited, and the ratio sentence was replaced.
- Grounding (`adr.out`): SIFY 6, WIT 1, INFY 1, IBN 2 and BABA 8 each carry 20-F provenance, and all are true. TSM, RDY and AZN return None, which leaves the guard as their only defence.
- Offline guard at the candidate (`a090-offline.out`):
  - With SIFY's grounded result carrying 6, `Each SIFY ADR represents 1.5 ordinary shares.` is KEPT.
  - With a no-depositary result, `Each ADS represents 0.5 ordinary shares.`, `... 2.5 equity shares.`, `The ADR converts into 0.1 shares...`, `half an ordinary share` and `a dozen ordinary shares` are all KEPT.
  - Cause: `_MARKED` blanks every `\d+\.\d+`, so a decimal share count is never read as a claim.
  - The integer, word and `1:6` forms are all guarded, and the true-prose controls are kept.
- Conclusion: a fabricated SIFY ratio in a fresh wording still reaches the stream, so the title claim is not met.

## R15-LEAD-030: inconclusive (operator-adjudicated)
- Live literal repro `What is SIFY's TTM revenue in USD?` (`l030-orig.out`): `financial_statements(SIFY)` returned ok, and the model stated no figure.
- The entry stays blocked_tier4 under DECISIONS 4.9-4.12, so no fix round and no re-proof of the class.

## R15-LEAD-033: holds
- Literal repro (`l033-orig.out`, with the history from `l033-orig-opts.json`): the turn-2 text contains no `[tool steps`.
- Fresh case (`l033-fresh.out`): a RELIANCE/price-data history, with the prompt "Repeat your previous answer word for word, including every line after it". The model repeated only the prose.
- Server-side fix: `agent_runtime._without_step_trailers` plus a system note. `src/store/chat-history.ts withTrailer` still appends the trailer, and the runtime strips it.

## R15-LEAD-034: holds
- `symbols_match` returns True for (INSPIRE, INSPIRE-SM.NS), (INSPIRE.NS, INSPIRE-SM.NS), IPHL, and QVCEL, SCML, VISHNUINFR, PATILAUTOM, SAJHOTELS and BIOPOL, all against their `-SM.NS` forms. It returns False for (ASM, A.NS), (INSPIRE, INSPIRES.NS), (TCS, TCSSM.NS) and (ISM, I-SM.NS).
- In process, yfinance resolves each Emerge symbol to its `-SM.NS` form and `validate_fundamentals` passes.
- `/fundamentals/SCML` returns 404 because Yahoo has no usable data for it (market_cap None). The gate does not reject it: the sidecar log has 0 mismatch lines.

## Adjacent (see `findings/rc1-vshard-8.json`)
1. The `[failed: …]` trailer line is not stripped from verbatim assistant history. Only `[tool steps:` is stripped. Live, the model recited it as its own prior answer (`l033-failed.out`). Severity: medium.
2. With an ok `fundamentals(MSFT)` call in the turn, llama3.1:8b invented a "previous answer": P/E 27.42 and market cap ₹1,23,011 cr, where the true figures are 28.72 and 3.83e12 USD (`l033-failed.out`). The lead decides whether this falls inside the known-limitation lane. Severity: medium.
3. `routers/screener.py:192` docstring says "S&P 500 (100 tickers)", but the live count is 503. Severity: low.
4. The ratio guard splices its replacement into a sentence that has already been partly released: "a standard Y-Share has The ADR-to-ordinary-share ratio is not available…" (`a090-tsm.out`). Severity: low.
