# rc1-vshard-5 working log (gate round 5)
- candidate worktree HEAD = 633f844071d972b337f4c3526d86555c80df0568 (checked)
- own sidecar :52605, data dir scratchpad/rc1-round-5-data-rc1-vshard-5 (copy of seed), sleep pid 87786; /health ok v0.8.0
- vy.py refuses non-GET on :52605 (outside 52100-52399): the Ollama agent runs were direct curl POSTs with vy.py's payload shape, no key, each under the Ollama lock; no hosted lane used, $0 spend.
- Ollama runs: transcript INFY (earnings_call_transcript called, ok), draw RELIANCE 1,450 (bad args x2), draw TCS 2,900 (staged), greeks default call (unlabelled units stated).
- vitest (22 files, 222 tests) on the relevant existing files: all pass.
- Yahoo 429 throughout (direct yfinance YFRateLimitError): DATA-048 inconclusive, offline derivation holds.
- Verdicts: 20 holds, 3 refuted (DOCS-016, CODE-PLATFORM-072, LEAD-026), 1 inconclusive (DATA-048). 5 adjacent. Report: verifier/shard-5.md, raw: verifier/shard-5-raw/.
- Sidecar sleep pid 87786 killed; :52605 refuses.
