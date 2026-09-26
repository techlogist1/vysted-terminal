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

---

# R15-DATA-102 second attempt (CN) - RESULT

- entry: R15-DATA-102 (partition P3, prior set W3, prior outcome could_not)
- outcome: fixed_untested
- branch: worktree-agent-lows-CN-r15-data-102-4c6dfe8 (base 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2)
- stamped: 06:57 IST

## Commits
- a84cb868 cherry-pick -x of 858ed56e (prior W3 store part: growth_basis column,
  per-tier field_meta in row_to_pair, yfinance states mrq_yoy). Carried WITHOUT its
  sidecar/tests/test_fundamentals_store.py hunk: that hunk is textually entangled with
  the R15-DATA-103 test from 22d4a619 and conflicts when this branch merges after the
  prior branch. The test reaches the candidate verbatim via the prior branch.
- 94185b4d model default flip + consumers + the tests that pinned the inherited default.
- 975cc181 legacy-row store test (appended at file end; merges clean).

## Files
- sidecar/models/fundamentals.py: growth_basis default "mrq_yoy" -> None; producer states it.
- sidecar/services/correctness_gate.py: overlay_filed_periods serves filed MRQ-YoY growth
  over a stated mrq_yoy OR an unstated basis (was: only the inherited default), and states
  growth_basis="mrq_yoy" when it serves. Without this the flip would silently drop filed
  growth on an Indian listing Yahoo served none for. annual_yoy is still never overlaid.
- sidecar/services/growth_check.py: should_cross_check requires a STATED mrq_yoy.
- types/data.ts: growth_basis doc (no shape change).
- (cherry-picked) sidecar/services/fundamentals_store.py, sidecar/services/yfinance_provider.py.

## Tests written (source only, none run: off-lane rule)
- test_b7_exchange_financials.py::test_filed_growth_states_mrq_yoy_and_never_overrides_an_annual_basis (acceptance, new)
- test_fundamentals.py::test_served_growth_states_its_mrq_yoy_basis (new)
- test_fundamentals.py::test_get_fundamentals: fixed; asserted "mrq_yoy" on a fake that serves
  no growth (the inherited claim); now asserts no basis stated.
- test_fundamentals_tool.py::test_tool_result_carries_growth_basis: fixed; fake producer states the basis.
- test_growth_check.py: two gate tests fixed; the absent-basis case flips True -> False.
- test_fundamentals_store.py::test_row_to_pair_growth_without_a_recorded_basis_states_none (new)
- via prior branch: test_fundamentals_store.py::test_row_to_pair_null_growth_row_states_no_basis_and_derives_field_meta

## Untested pending integration
All of the above. Only py_compile + ruff format/check (touched Python) and prettier --check
(types/data.ts) were run. Simulated candidate merge (base + prior W3 branch, then this branch)
is conflict-free (git merge-tree exit 0) and the merged Python files compile.

## Risks
- Any unseen fixture that builds Fundamentals with growth and relies on the default basis
  now gets None (grep of sidecar/tests found only the three fixed above).
- Legacy store rows (growth, NULL basis column) now state no basis until the next .info refresh.
- Adjacent, not changed here: research/semantics.py and company_narrative.py label growth
  "quarterly YoY (MRQ)" unconditionally and never read growth_basis, so a yfinance
  annual_yoy fallback figure is labelled MRQ there. Unfiled; independent of the default.
- field_meta stays Optional on the contract (openbb-mcp / v7 rows still emit none of their own);
  the entry's fix_shape scopes field_meta to row_to_pair only.
