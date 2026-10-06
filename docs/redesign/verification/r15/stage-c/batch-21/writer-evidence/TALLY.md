# batch-21 W1 evidence — R15-LEAD-030 (GAP 1, GAP 2), R15-LEAD-036 (GAP 3), LEAD-035 runtime hunk

Commits on `worktree-agent-batch-21-W1` (base `4d9a7324`): `26dc3aab` LEAD-030, `1841b22e` LEAD-036,
`4ee83499` LEAD-035 hunk (inert until W2's planner cue; `test_b3_runtime_intent_gate` green).

## Pinned tests (before / after)

`pinned-base-4d9a7324.out`: the new tests run against the base services: 23 failed, 7 passed. The 7 that pass
on base are the 6 controls and the "but"-split class case (its figure clause already stood alone).
`pinned-fix.out`: 30 passed. Every fresh.out FAIL line, the live 742.35 replay (token chunking from
batch-20 `live/y-neg-estimate-sbin.jsonl`), the Infosys mixed turn, both tilde fences and the
four-backtick nested fence fail on base.

Focused: `test_agent_runtime test_figure_grounding test_b5_runtime_history test_tool_call_rescue
test_llm_ollama test_b3_runtime_intent_gate`: 348 passed. Full sidecar pytest: 3416 passed, 1 skipped.
`ruff format --check sidecar && ruff check sidecar`: clean.

## Offline probes (cwd `<tree>/sidecar`, fix sha)

| probe | result |
|---|---|
| b17v_probe / 2 / 3 | BAD 0 |
| b18v_probe / _b / _c / _d | BAD 0 |
| b19v_probe 3 | BAD 0 |
| b19v_probe (no arg), b19v_probe 2 | BAD 1 each: the two false-premise "q?" lines, unchanged from batch-20; PASS in their premise-true form in b20w_probe |
| b20w_probe | 18/18, BAD 0 |
| b20v_fresh | 19/19, BAD 0 (was 6 FAIL) |

## Live bar (:52350, sidecar from this tree, llama3.1:8b via ollama, autonomy ask)

`live.out`, `live2.out`, per-tag `<tag>.jsonl`/`.txt`; `guard-log.txt` holds the sidecar's own
"guard replaced" lines (the model's pre-guard text for every replaced clause).

| tag | calls / results | verdict |
|---|---|---|
| v-sify-ttm | financial_statements ok | no figure stated, honest "unavailable" |
| y-ack-sbin | price_data errored (no args) | acknowledgement with no figure, streams (negative, figure-free) |
| y-neg-estimate-sbin (batch-20's escape prompt) | price_data errored | REPLACED: model wrote "Although the price_data tool failed ..., SBIN.NS's latest close was ₹740.60 per share." (guard-log) -> the note. /quotes/SBIN.NS = 983.0 |
| x-infy-tcs-t1 | price_data INFY.ZZ errored, TCS.NS ok | TCS ₹2082.0 kept (/quotes/TCS.NS = 2082.0); Infosys acknowledged with no figure |
| x-infy-tcs-t2 (history, user writes "Infosys") | same | TCS kept; model's "So, the latest price of Infosys (INFY.ZZ) is ₹1203.5" REPLACED (guard-log; /quotes/INFY.NS = 1000.2); a second unit after it was replaced too; a stray ", " the model wrote between them streams (cosmetic) |
| x-tilde-fence | fundamentals ok | ~~~ fenced table of the ok result streams whole, closer kept |
| x-tilde-fence-err | fundamentals errored (no args) then ok | round-1 text dump replaced by "No tool returned data ..."; round-2 the model opened a ``` it never closed around a figure-free ~~~ block (model's own text) |
| x-allerr-names | price_data errored | REPLACED: "- Infosys (INFY): ₹1,323.45" and "- State Bank of India (SBIN): ₹590.10" -> one note |
| t-msft-price (true) | price_data ok | "$517.04" streams; /quotes/MSFT read 517.385 and 516.875 around it (live market) |
| t-tcs-name (true, company name on ok subject) | price_data ok | "Tata Consultancy Services (TCS.NS) is ₹2082.0" streams; /quotes/TCS.NS 2082.0 |
| t-user-after-err (true) | portfolio_add_position staged (model did not call price_data) | user figures ₹1,640 x 12 = ₹19,680 kept. Residual: the model also calls ₹1,640 "the current price" after claiming it called the price data tool; the figure is the user's own, so provenance grounds it (outside this guard's figure remit; /quotes/HDFCBANK.NS 735.6) |

Fabricated figures streamed: 0 of 4 attempted (740.60, 1203.5, 1,323.45, 590.10 all replaced).
True controls unchanged: 3 of 3.
