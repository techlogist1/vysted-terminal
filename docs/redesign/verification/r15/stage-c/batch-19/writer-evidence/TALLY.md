# batch-19 W1 writer evidence — R15-LEAD-030

Fix: `abbb8644` on `worktree-agent-batch-19-W1` (base `c5a6ade8`; `sidecar/` is identical to `ebc5ed41`).

## Pinned tests (sidecar/tests/test_agent_runtime.py)

| test | base (runtime from ebc5ed41) | fixed |
|---|---|---|
| `test_a_result_after_a_colon_intro_is_judged_with_the_intro` (v030-sify-orig + class a, c) | 3 FAIL | 3 pass |
| `test_a_result_list_when_every_call_errored_is_replaced` (v033-infy-t1 + class b) | 2 FAIL | 2 pass |
| `test_a_result_list_with_a_source_or_no_result_shape_streams` (5 controls) | 5 pass | 5 pass |

Focused files (test_agent_runtime, test_b5_runtime_history, test_tool_call_rescue, test_llm_ollama): 231 passed.
No existing expectation changed.

## Offline probes (cwd `sidecar`, fixed tree)

| probe | BAD |
|---|---|
| b17v_probe / b17v_probe2 / b17v_probe3 | 0 / 0 / 0 |
| b18v_probe | 0 |
| b18v_probe_b | 1 (`x-news-data-shows`; same FAIL on base 08908883 and 24bff097, pre-existing) |
| b18v_probe_c (was BAD 2) | 0 |
| b18v_probe_d (was BAD 2) | 0 |

## Live bar (:52350, sidecar from the fixed tree, llama3.1:8b via ollama, autonomy ask)

Script `b19w_live.py`; transcripts `<tag>.txt/.jsonl`; outputs `live.out`, `live-extra.out`, `live-extra2.out`.
The sidecar log recorded 0 guard replacements over the whole bar.

| tag | kind | tools (ok) | result |
|---|---|---|---|
| l-sify-ttm | entry prompt | financial_statements (ok) | honest "couldn't find"; no fabricated block |
| x-sify-ttm-2 | entry prompt, rerun | financial_statements (ok) | honest; no fabricated block |
| l-sify-pe | error-shaped | fundamentals (error) | honest "No data"; no fabricated block |
| l-infy-err-t1 | two-turn, price_data forced to error | price_data x3 error, then ok | true ₹1000.2 (ok-sourced) streamed unchanged |
| l-infy-err-t2 | follow-up turn | price_data ok x2 | true 1000.2 / 2082.0 streamed unchanged |
| x-infy-list | forced error + "Here are the results:" list | price_data error, ok, ok | true list (1000.20 / 2082.00) after colon streamed unchanged |
| x-wiprox-dump | error-shaped (WIPRO.NSX) | fundamentals (ok) | true colon + list streamed unchanged |
| l-wipro-fund | WIPRO.NS fundamentals | fundamentals (ok) | true colon + list streamed unchanged |
| t-aapl-price | true control: ok tool figure | price_data (ok) | streamed unchanged |
| t-news-outlets | true control: numbered list after colon | news (ok) | streamed unchanged |
| t-according-to | true control: "According to Yahoo! Finance, ..." | news (ok) | streamed unchanged |
| t-user-figure | true control: user's ₹1,500 restated | portfolio_add_position (staged) | streamed unchanged |

Tally: 0 fabricated result blocks streamed; 0 true answers replaced (9 true/ok-sourced outputs unchanged).
This run of llama3.1:8b did not write the fabricated shapes live, so the pinned tests and probes c/d are the
evidence for the two shapes. They replay the batch-18 live streams through the full `invoke_agent` relay.
