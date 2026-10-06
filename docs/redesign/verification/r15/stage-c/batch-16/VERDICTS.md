# R15 Stage C batch 16: verifier verdicts

Merge target: `worktree-agent-batch-16-int@7b65b217b358b76579158d9cc9af4e77252b217b`.
Verifier: fresh-context Opus. The checks ran in a scratch worktree at that sha, now removed. Its main sidecar was booted from
source on 127.0.0.1:52310 against a copy of the iso data dir, now stopped, with MCP on :52153/:52154. The local model was
llama3.1:8b through ollama. No paid or OpenRouter call was made. All evidence is in `verifier-evidence/`.

- **Verdict: approve.** Two entries certify and neither is a regression. R15-LEAD-030 does not certify. It has two escapes and
  one new over-replacement, all named below. The over-replacement is a regression inside an uncertified entry, and the next
  pass on LEAD-030 must fix it first.
- **Chain: green.** The integrator ran `pnpm ci-local` at 7b65b217 (worktree clean) with CI_EXIT=0 (3271 passed, 1 skipped),
  and the smoke test with SMOKE_EXIT=0 (`b16int-ci1.log`, `b16int-smoke.log`). At the same sha the verifier re-ran the focused
  `test_agent_runtime`, `test_adr_ratio`, `test_fundamentals_tool` and `test_tool_call_rescue`: 186 passed (`b16v-focused.log`).

| id | verdict |
|---|---|
| R15-AGENT-090 | certified |
| R15-LEAD-032 | certified |
| R15-LEAD-030 | not_certified |
| R15-LEAD-031 | not attempted (no writer commit) |

## R15-AGENT-090: certified

- **Outside-world truth.** The verifier fetched each company's newest 20-F cover from sec.gov:
  - SIFY: "American Depositary Shares, each represented by Six Equity Shares" (filed 2026-06-26).
  - WIT: "each represented by one Equity Share".
  - BABA: "each representing eight Ordinary Shares".
- **Original repro, 5 runs** (`orig-1..5`, prompt verbatim): 0 untraced ratio claims. Every run called `fundamentals` SIFY
  (ok) and answered the true "six equity/ordinary shares". orig-2 first hit an errored `SIFY.A`, and its no-number refusal
  sentence was replaced with RATIO_UNAVAILABLE, which is harmless.
- **Fresh phrasings, live:**
  - fresh-1, the class-qualifier wording "how many class A shares back each ADS": fundamentals errored on SIFY.NS, and the
    model stated no ratio.
  - fresh-2, WIT: "1:1". This is true and traced.
  - fresh-3, BABA: the model called only `price_data`, then wrote "One ADS of Alibaba (BABA) equals 8 ordinary shares."
    That claim is untraced (no fundamentals result carried it), and the guard replaced it (`sidecar-guard-lines.log`).
- **Fresh class cases the fix was not written against** (`probe.out`). Against a fundamentals result with no depositary term,
  12 of 12 are replaced:
  - "One ADS equals 3 series B preferred shares."
  - "Each ADS represents 6 underlying class A shares."
  - "8 restricted voting shares"
  - "2 class A common shares"
  - "4 new equity shares"
  - "6 fully paid class A shares"
  - "5 Series A shares"
  - "2 A shares"
  - "10 non-voting shares"
  - "Each ADR corresponds to 6 class A ordinary shares."
  - "One SIFY ADS = 6 class A shares."
  - "12 ordinary shares of class A"
- **Kept, 5 of 5:** "SIFY's ADSs each gained 3 points in 2024.", "3 analyst ratings", "fell 4 percent over 2 sessions",
  "₹4,651 cr", and "Each ADR closed at 5.20 USD".
- **Traced:** a lower-case source "each representing ten class A ordinary shares" keeps "10 class A ordinary shares" and
  still replaces "8 class A ordinary shares".
- **Grounding holds cold** (`b16v-cold.log`, fresh data dir, real EDGAR): SIFY 6, WIT 1, INFY 1, IBN 2, HDB 3 and BABA 8 are
  all true, and TSM gets no ratio (the safe direction). Each fetch took 1.0 to 2.1 s, well under the new 8 s bound.

## R15-LEAD-032: certified

- **Fresh case with a real network stall.** A black-hole HTTPS proxy accepts connections and never answers. The real httpx
  path ran through it (`b16v_stall.py` / `b16v-stall.log`):
  - `lookup("TSM")` returned None in 8.01 s (TimeoutError).
  - A second `lookup("TSM")` took 0.00 s and made 0 extra `_fetch` calls (the miss is cached).
  - BABA was independently bounded at 8.01 s.
- **Through the tool** (`b16v_stall2.py`: only SEC goes through the black hole, yahoo stays direct).
  `_fundamentals({"symbol": "TSM"})` returned ok with no `ads_ratio` in 11.61 s, then in 0.42 s on the second call. Before
  the fix this was up to about 150 s on every call.
- **The ceiling holds.** Real cold fetches take 1 to 2 s, so the 8 s bound does not cost grounding.

## R15-LEAD-030: not certified

What holds:
- The live-1 shape "- fundamentals returned: {" with an errored tool (the unit test).
- "According to `news`, revenue was $5 bn." and "The financial_statements output shows revenue of ₹4,411 cr." for uncalled
  tools are replaced.
- An ok tool's citation streams (okcite-1: "The tool that returned these figures was fundamentals", kept).
- lead030-2 (INFY) raised no false positive.

What fails:
1. **Escape, live** (`lead030-1`). The model called only `financial_statements`, then streamed a fabricated
   `Price Data: {"ok": true, "symbol": "SIFY.US", ..., "latest_price": 2.11, ..., "volume": 1234567, ...}` for `price_data`,
   which was never called. The real price is 13.41 USD (`/quotes/SIFY` on the running sidecar). The guard's reference regex
   needs the literal id, so a humanised name (`Price Data`, `price data`, `price-data`) never matches. Offline,
   "Price data returned a close of $2.11." is also kept (`b16v_probe2.py`).
2. **Escape: the dump on the next line** (`b16v_probe3.py`, and live in followup-1). When the citation ends in "returned:"
   and the `{` opens on the next line, depth stays 0. With fundamentals errored, the stream is "The fundamentals tool returned
   no data for this in this session." followed by the fabricated `"trailing_12m_revenue": {"display": "$1320 m"}` dump.
3. **Over-replacement: a new regression in agent-chat** (`followup-1`). `ok_tools` is per turn. In a follow-up whose history
   shows fundamentals returned AAPL's market cap, the true "The tool that provided the market cap figure was `fundamentals`,
   which returned:" became the false "The fundamentals tool returned no data for this in this session.", and the dump still
   followed. Offline, pre-call narrations are also replaced before any call runs: "Let me look up the fundamentals data for
   SIFY." and "Next I'll check the news data for any sentiment." (`probe.out`). llama did not narrate that way in
   precall-1/2.

Fix shape for the next pass:
- Match humanised tool names.
- Carry the dump-drop across the newline after a replaced citation that ends in `:`/`=`.
- Seed `ok_tools` from the history's `[tool steps: …]` trailer, or scope the replacement text to "this turn".
- Do not replace a figure-less sentence for a tool not yet dispatched.

Pin each with a test on a case the fix was not written against.

## R15-LEAD-031: not attempted

W1 made no commit for item D. The defect is still live: orig-2 streamed
`{"name": "fundamentalsSIFY's American Depositary Share (ADS) represents six equity shares.`

## Issues found (outside the entries)

- **The currency label still slips.** The model answers "SIFY's TTM revenue in USD is ₹4,651 cr" without converting (orig-1,
  orig-3, orig-5). orig-1 converted on its own and got the arithmetic wrong ("approximately $64.69 million"). This is
  model-side prose, and no guard covers it.
- **The citation guard's single-word tool ids** (`news`, `research`, `fundamentals`) followed by "data"/"results" also match
  ordinary prose ("research results show …"). Watch the next pass's over-replacement.
