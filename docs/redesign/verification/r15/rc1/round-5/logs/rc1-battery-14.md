# rc1-battery-14 — regression battery shard 14

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sidecar booted from candidate source
(`sidecar/main.py`), port 52354, data dir `rc1-round-5-data-rc1-battery-14` (copied from the
isolated seed). Sleep pid 56839 (killed at teardown). openbb-mcp :52153 / sec-edgar-mcp :52154
shared read-only per the round's ISO_STACK.

Sets worked, in order (each set file written to `battery/set-<n>.md` before moving to the next):

1. **batch-4/W4-market-data-gate** (`battery/set-13.md`): DATA-016, DATA-034, DATA-035,
   DATA-036, DATA-047, DATA-049, DATA-082, LIFECYCLE-004 — all 8 **holds**. Highlights:
   DATA-034 confirmed the single 25%-yield bound in-process (1.5/0.9 withheld, 0.03 passes,
   no local 2.0 bound reachable via `fundamentals_from_v7`). DATA-082 reproduced both the
   `ProviderError` (no price field) and the `CorrectnessError: non-positive price 0.0`
   (stubbed zero-price ticker) through `provider_registry.get_quote`, plus live BTC/USDT
   ETH/USDT quotes at `freshness: live`. LIFECYCLE-004 repointed the census harness
   `parser_drift.py` at the candidate sidecar (its hardcoded `SIDECAR` path pointed at the
   real repo, not the worktree — patched in a scratch copy only) and got the exact cert
   wording (`ProviderError: … lacks CH_OPENING_PRICE, … (payload shape changed)`), then
   drove `provider_registry.get_history` through the same drift to confirm the fall-through
   to `nse`, 26 real bars, 0 flat, 0 zero-volume.
2. **batch-3/W3-llm-adapters-and-errors** (`battery/set-7.md`): AGENT-004, AGENT-005,
   AGENT-018, CODE-AGENT-003, UI-008 — all **holds**. AGENT-004 via the pinned
   `test_stream_chat_tool_use_carries_streamed_input` (the register's own MockTransport
   repro, now a permanent test). AGENT-018 via the two pinned Ollama leak-rescue tests.
   UI-008/CODE-AGENT-003: live `/llm/keys/validate` negative control only (fake keys for
   openrouter/gemini/xai all return `invalid`, Gemini no longer "transport error"); no
   positive-control re-check with real keys this shard (no safe in-scope path to a real key
   without risking printing it).
3. **batch-12/W8-design-token** (`battery/set-60.md`): LEAD-010, RELEASE-007 — both
   **holds**. LEAD-010 live against the shared candidate stack (AAPL 10-K, MSFT 10-Q,
   unhinted). RELEASE-007: ran `audit-design-tokens.mjs` against the real `src/` (373 files,
   clean) and reran the entry's own negative case (`gap-1.5 px-[7px] text-[12px]`) — but
   injected into a **scratch copy** of `brief-blocks.tsx`, never the read-only candidate
   worktree, and scanned that scratch tree instead of the candidate. Exactly 3 violations,
   same three tokens.
4. **batch-25/W5-opus** (`battery/set-70.md`): RESEARCH-015 — **holds**. `r015.py` (the
   register's own script) was not present anywhere in the tree (a batch-25 scratch artifact,
   never committed), so the underlying mechanism (`verify._row_domains` /
   `finance.registrable_domain`, PSL-backed, and `deep.distinct_web_domains`) was exercised
   directly with the cert's exact URL sets. All five cases and the fresh RBI/BSE pair
   reproduced byte-for-byte the cert's registrable-domain counts.

No regressions found. 0 findings.

COVERAGE: 16/16 ids raw; no raw: none.
