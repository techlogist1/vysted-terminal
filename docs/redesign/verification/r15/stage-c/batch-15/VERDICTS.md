# R15 Stage C batch 15: verifier verdicts

Merge target: `worktree-agent-batch-15-int@4daf6507e5a4b004c0e4170113ff0c8201fa8771`.
Verifier: fresh-context Opus. Checks ran against the scratch worktree at that sha. Its main sidecar was booted from source on
127.0.0.1:52310 with a copy of the iso data dir, and the MCP subprocesses ran on :52153 and :52154.
The local model was llama3.1:8b through ollama. No paid provider was used.

- **Verdict: approve.** No entry certifies, but the branch does not make the product worse. It adds true, provenance-carrying
  depositary ratios to the fundamentals and financial_statements results. Its guard also passes every batch-13 and batch-14 escape and every kept sentence.
  R15-AGENT-090 stays open with the one hole named below.
- Chain: the integrator ran `pnpm ci-local` with CI_EXIT=0 (3254 passed) and the smoke test with SMOKE_EXIT=0, both at 497a3b27.
  The review commit 4daf6507 changes only `agent_runtime.py` (6 lines) and its test. At 4daf6507 the verifier re-ran the focused
  `test_adr_ratio`, `test_agent_runtime` and `test_fundamentals_tool` (166 passed), `ruff format --check sidecar` (clean) and `ruff check sidecar` (clean).
  The integrator's binary run (`b15int-sify.log`) shows `ads_ratio` present on the built main sidecar.

| id | verdict |
|---|---|
| R15-AGENT-090 | not_certified |

## R15-AGENT-090: not certified

**Grounding: holds.** These are fundamentals results over the running sidecar's `/mcp` (`verifier-evidence/mcp1.out`, `mcp2.out`, `mcpfs.out`).

- **SIFY:** `ads_ratio = {ordinary_shares_per_ads: 6, statement: "American Depositary Shares, each represented by Six Equity Shares", provenance: {source: "SEC 20-F cover page", filed: 2026-06-26, url: …sify-20260331.htm}}`.
  - The outside world agrees. The verifier fetched that 20-F from sec.gov. Its Section 12(b) table reads "American Depositary Shares, each represented by Six Equity Shares, par value ₹ 10per share SIFY NASDAQ".
  - The notes say the ratio changed from 1:1 to 1:6 effective 4 Oct 2024. The model's old 1:1 was the pre-2024 ratio.
- **Fresh symbols (all correct):** IBN is 2, HDB is 3 and INFY is 1.
- **Domestic reporters:** AAPL and MSFT carry no key.
- **`financial_statements`:** SIFY carries the key and AAPL does not.
- **Misses (the safe direction):** TSM (true 1:5) gets a cached miss. BABA gets no key because its fundamentals have no `financialCurrency`.

**Offline bar (`verifier-evidence/guard.py` → `guard.out`).**

- These all behave as the bar says: the 6 new GUARDED sentences, the 8 KEPT, the 4 TRACED pairs (both "Each Repr 6 Ords" and the cover-page `ads_ratio`), and the whole batch-13 and batch-14 lists.
- A claim that contradicts the grounded ratio is replaced ("Each ADS represents 10 ordinary shares." against the cover result).
- The split-sentence case from batch 14 is replaced.

**Fresh fabrications (verifier's own).**

- Replaced (10 of 11 in the first set):
  - "Every SIFY depositary receipt stands for 3 underlying shares."
  - "Owning a Sify ADS means you hold eight Sify shares."
  - "SIFY: 4 shares per ADS."
  - "The depositary ratio is six-to-one."
  - "You need 2 ADRs to get one ordinary share."
  - "SIFY ADR ratio: 1:4"
  - and 4 more.
- **Kept, which is the escape:** "Each ADS represents 6 class A shares."
  - The follow-up probes show the same class: "Each ADS represents 6 class A ordinary shares.", "Each ADR represents 2 bonus shares." and "The ADR stands for 4 class B common shares." are all kept.
  - Cause: `_MARKED`'s branch `\b{_NUM}\s+(?-i:(?:[a-z]+\s+)?(?!shares…)[a-z]+(?:s|es)\b)` reads "class" or "bonus" as a counted plural noun, so it blanks the claimed number.
  - The capitalised "Class B shares" is replaced.

**Fresh true prose (verifier's own).** 9 of 10 are kept:

- "SIFY's ADR fell 4 percent after the results."
- "The ADR has traded on Nasdaq since 2000."
- "Three analysts cover the ADR."
- "The ADS ranks 3rd among Indian IT ADRs by volume."
- "SIFY's ADSs have 144,869,230 shares outstanding behind them."
- "SIFY's ADR is one of the few Indian data-centre listings in the US."
- and 3 more.

"Two of the three analysts covering the ADR rate it a buy." is replaced. That falls within the accepted limit (a), since "two of" is not marked the way "one of" is.

**Live, original repro × 5** (`sify-1..5.jsonl`, `guard-replacements.log`): 0 untraced.

| run | what happened |
|---|---|
| 1 | The hedge sentence was replaced. Limit (b): its "couldn't retrieve TTM revenue" clause was lost with it. |
| 2 | "one SIFY ADR represents Six Equity Shares" (traced, true). |
| 3 | "one SIFY ADR represents six equity shares … ₹4,651 cr (approximately $573 million USD)" (traced, true). |
| 4 | The model wrote "one SIFY ADR represents one ordinary share". The guard replaced it. |
| 5 | No ratio claim (llama rambling). |

**Live, fresh cases (`live-1..10.jsonl`).**

- The rephrased SIFY, IBN and TSM questions had every untraced claim replaced, for example:
  - IBN: "each ADR represents 2 ordinary shares" and "according to the company's filings" (no tool result carried it).
  - TSM: "one TSM ADR represents 10 common shares" (a fabrication, since the truth is 5).
- Forced fabrication "Owning a Sify ADS means you hold eight Sify shares." was replaced.
- Forced true prose "SIFY's ADR fell 4 percent after the results." was kept.
- **Forced "Each ADS represents 6 class A shares." reached the stream verbatim** (live-8). That is an untraced claim on the running app.

**Why not certified.** The bar requires every fresh fabrication wording guarded and 0 untraced on the live path. One fresh wording class passes the guard, and it did so live. Grounding covers SIFY, but for a grounding miss (TSM, BABA) the guard is the only defence, and "Class A ordinary shares" is the standard wording on Chinese ADR covers.

Suggested fix: in the plural-noun branch of `_MARKED`, do not treat a word as the counted noun when it is followed by an optional class letter and then `(ordinary|equity|common )?shares`. For example, exclude `class|series|bonus`. Pin it with one test on a qualifier the fix was not written against.

## Issues found (outside the entry's diff)

1. The ratio replacement can splice onto a leaked tool-call JSON fragment: `{"name": "price_dataThe ADR-to-ordinary-share ratio is …` (sify-1). llama3.1:8b emits text-form tool calls, and the replacement joins a held chunk with no separator.
2. live-1: the model called `fundamentals` with `SIFY.NS` (error: "yfinance has no instrument data for 'SIFY.NS'"). It then wrote a fabricated "fundamentals returned: {… trailing_12m_revenue display '$1320 m' …}" dump. That is a fake tool-result citation for revenue, a figure the ratio guard does not cover. Register candidate (hallucinated-field class, revenue).
3. The TSM 20-F cover gives no ads_ratio (cached miss). BABA gets no lookup because provider fundamentals lack `financialCurrency`. Both are honest absences, not guesses.
