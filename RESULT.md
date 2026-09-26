# R15-AGENT-077 second attempt (CN, base 4c6dfe8c)

- Entry: R15-AGENT-077 (tool-arg repair round and native-search oneshot rebuilt the adapter without the configured base_url)
- Outcome: fixed_untested
- Stamped: 06:50 IST

## Commits
- e7c9adc0: cherry-pick -x of 0e5e72e5 (prior W2 branch): base_url kwarg on oneshot.complete / complete_with_usage and native_search_oneshot, threaded into get_provider; openai.py repair round passes self._base_url; acceptance test test_llm_openai.py::test_repair_round_keeps_configured_base_url.
- ef9e04cd: the two get_provider fakes that pinned a narrower signature than the real get_provider now accept **_k (tests/test_research_metering.py:114 `lambda _p`, tests/test_b5_runtime_synthesis.py:55 `lambda *_a`), assertions unchanged; new test_native_search.py::test_native_search_oneshot_keeps_the_callers_base_url.

## Files
sidecar/services/llm/oneshot.py, sidecar/services/llm/native_search.py, sidecar/services/llm/openai.py, sidecar/tests/test_llm_openai.py, sidecar/tests/test_research_metering.py, sidecar/tests/test_b5_runtime_synthesis.py, sidecar/tests/test_native_search.py

## Verification done
py_compile, ruff format --check, ruff check on all touched files: clean. Sequential merge simulation (base + origin/worktree-agent-lows-P3-W2-llm-chat, then this branch) via git merge-tree: clean.

## Untested pending integration
No test was run (off-lane rule). Audit of every get_provider fake patched on the oneshot module or services.llm package: all others already take **kwargs or base_url=None. complete_with_usage fakes in test_llm_openai.py take **_k or base_url; the one in test_research_metering.py:89 is reached only from deep_research, which passes no base_url.

## Risks
Latent-only per the refuter: no shipped surface sets a custom base_url on the agent path (agent_runtime and deep_research call without one), so behaviour is unchanged today. The native_search_oneshot base_url has no production caller yet.
