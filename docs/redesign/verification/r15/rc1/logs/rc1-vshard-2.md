# rc1-vshard-2 working log

- 2026-09-25 08:49:14 start. candidate 1d6511c8, worktree rc1-4097dac-fix-int (read-only). own sidecar :52602, data dir scratchpad/rc1-data-rc1-vshard-2, sleep pid 97364 (worker 97365, sh 97362).
- 2026-09-25 08:50:58 vy.py refuses POST to :52602 (guard allows 52100-52399 only). Decision: agent runs (read-only, context-snapshot only, autonomy ask) go through vy.py against the shared candidate stack :52152; curl/data probes use my own :52602. vy.py not modified.
- 2026-09-25 08:55:49 PLATFORM-030 holds (in-process: orig oversell final equity 99998.00 = fees only; variant pyramid+partial+oversell+no-position sell 99995.60 = sum of trade pnl).
- AGENT-020 holds: orig read_notes(RELIANCE) + thesis quoted verbatim; variant non-focused BDL note, canary ZEPHYR-41 quoted after read_notes(BDL).
- UI-091 holds: suggested (5m eq) ema:9,ema:21,vwap,rsi; (1d crypto) ema:50,ema:200,vwap:week,rsi; variant BTC/USDT 1h vwap:week recomputed independently max rel diff 9.8e-8, Monday-00 bars reset to typical price.
- UI-085 holds: only disabled:text-charcoal-600 remains; variant contrast sweep over all raised surfaces, no sub-floor text token pair found in use.
- DATA-068: GET /fundamentals/AAPL/ratings (consensus, 6h _cached, consumed by Equity Overview) has NO as_of; route discards it (rating, _ = await _cached(...)). Other 7 routes carry as_of.
- 2026-09-25 08:58:33 UI-087 holds (code: orderedProviders + nextFallbackAttempt + startLayout/applyStartLayout + palette consumers; live: bad-key OpenRouter and DeepSeek emit code=auth (a fallback code), missing Ollama model emits model_not_pulled (not a fallback code)).
- DOCS-005 holds: vystedModules has 20 entries, BLUEPRINT :20/:238 say 20 shipped, D-B10-4 recorded; no other doc repeats ~38.
- CODE-AGENT-009 holds: invoke_agent 95 lines (ast); variant drove _consume_round (error mid-round, unterminated stream) and _prepare_run (real copilot spec + notes snapshot) with no provider.
- RESEARCH-010 validate half holds: 3 fake OR keys -> ok:false reason invalid; KeyEntryDialog blocks save on !ok. Tier B stream run pending.
- 2026-09-25 09:02:18 RESEARCH-010 holds: live tier_b fake key -> each research call emits status=error step 'OpenRouter rejected the request...'; in-process variant (ultra no-instrument; bogus model slug) -> ok:false + error step. New defect: model answered 'Built you a brief on Infosys' with no brief published (finding :2).
- AGENT-007: Anthropic real-SDK variant (2 tool blocks, split fragments with escapes, no-arg tool) -> correct inputs; grader fails json-text call, wrong symbol, missing leg, no-done; live compare-tcs-infy scenario run pending.
- 2026-09-25 09:06:00 AGENT-007 live compare-tcs-infy graded [] (pass). Report at verifier/shard-2.md. Sidecar stopped (kill 97364).
