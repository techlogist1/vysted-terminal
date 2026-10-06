# Agent Tool-Use Plan — Build Run Telemetry

Branch: 004-r4-experience-rebuild
Build start HEAD: 2f0bbcdc22690b061e82ad53daed26e5cb7b8a80
Baseline: test_safety_end_to_end 9/9, combined WS1-area suite 54/54 green, venv py3.13.13.

| WS | agents | wall-clock | tool calls | files changed | lines (+/-) | commit |
|----|--------|-----------|-----------|---------------|-------------|--------|
| WS1 | 3 (impl+spec+quality, clean first pass) + lead narration fix | 21.7 min | 142 | 12 | +432/-24 | 64a6524 |
| WS2 | 5 (impl+spec+quality+fix+re-review) + lead 3 polish fixes | 18.1 min | 126 | 5 | +466/-30 | 724d31d |
| WS3 | 3 (impl+spec+quality, clean first pass) + lead 3 fixes (badge honesty, iter coverage, stale WS1 test) | 23.2 min | 178 | 18 (+1 WS1 test) | +492/-39 | 4c5435c, 59cb9d6 |

| WS4 | 3 (impl+spec+quality, clean first pass) + lead 3 polish fixes (DRY, JSDoc honesty, stale comment) | 15.7 min | 130 | 11 | +473/-123 | aee0457 |
| WS5 | 3 (impl+spec+quality, clean first pass) + lead 3 fixes (docstring, nativeSearchStatus simplify+matrix test, plugin truthiness+test) | 25.6 min | 186 | 15 | +595/-35 | faba3b0 |
| WS6 | 5 (impl+spec+quality+fix+re-review) + lead Step-1 solo + lead prefer-EQ hardening+test | 29.3 min | 197 | 17 (2 commits) | +1276/-43 | 1284c19, a811581 |
| WS7 | 3 (impl+spec+quality, clean first pass) + lead 1 fix (inline _consume_one) | 10.2 min | 58 | 2 | +209/-1 | b251a20 |
| WS8 | 5 (impl+spec+quality+fix+re-review) + lead 1 fix (HTTP-date Retry-After + test) | 32.0 min | 183 | 4 | +1195/-24 | 9ed5001 |

**Integration-pass note (WS3):** the full sidecar pytest (1409 passed) caught a stale WS1 test (`test_tool_loop_e2e::test_agent_mode_infers_read_intent_and_gates_to_read_only`) that WS1's targeted run missed — it asserted the pre-Decision-4 strict gate. Fixed in 59cb9d6. Lesson: run the full suite per workstream, not just per-file (the plan warned this).
