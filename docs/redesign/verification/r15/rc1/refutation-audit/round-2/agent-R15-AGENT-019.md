# R15-AGENT-019 refutation audit, round 2 (group agent)

Tree: HEAD a3275f64; `git diff --name-only 4c6dfe8c HEAD | grep -v '^docs/'` printed nothing (code tree = candidate 4c6dfe8c).
Own sidecar: `cd sidecar && VYSTED_DATA_DIR=$SCRATCH/refaudit2-agent/data VYSTED_OPENBB_MCP_PORT=0 VYSTED_SEC_EDGAR_MCP_PORT=0 nohup ./.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 52370` (pid 5451, /health ok, killed at 18:23 IST). Ollama llama3.1:8b behind /tmp/vysted-r15-ollama.lock. Audit window 18:15-18:23 IST.

## Entry and certification history
- Entry: the intent gate read question/statement-shaped write asks (note, /screener, save, "Delete TCS from my portfolio", "I bought 10 INFY at 1500") as `read` and stripped the write tools; llama3.1:8b then typed the call as JSON text. fix_shape: stop stripping on an inferred read (strip only on a positive read signal) or add cues; class `intent-gate-false-read`.
- batch-3 certified (VERDICTS.md:65). Round-1 refutation audit: **partial** (question-shaped asks: trailing `?` is a positive read cue + verb outside `_EDIT_SIGNALS`). batch-12 re-certified (VERDICTS.md:33) after adding `log`, `record` and a `<qty> <sym> at <price>` cue; its fresh cases were all add-shaped.

## Verifier refutation (rc1-verifier:4, verifier/g2/adj-agent019-intent-probe.txt)
Literal register phrasings pass; "Could you drop WIPRO from my portfolio?", "I exited my ITC position, can you take it out of my portfolio?", "Can you bump my INFY quantity to 30?" -> intent read, writes [].

## 1. Entry's own repro + round-1 acceptance, and 2. verifier's phrasings + 8 auditor-fresh phrasings (in-process, the runtime's own `_resolve_tool_surface(spec, "agent", prompt)`, the function invoke calls at agent_runtime.py:2628)
`cd sidecar && VYSTED_DATA_DIR=$SCRATCH/refaudit2-agent/data ./.venv/bin/python $SCRATCH/refaudit2-agent/agent019.py`
```
## ENTRY + ROUND-1 ACCEPTANCE
PASS edit     signals=['\\bnotes?\\b', '\\bwrite\\b'] read_only=False tools=55 need=write_note writes_kept=7 | Write a note on Cochin Shipyard: valuation looks stretched at ~54x trailing P/E; revisit after Q2 results.
PASS edit     signals=['\\bscreen\\b'] read_only=False tools=55 need=write_screener_filters writes_kept=7 | screen for defence stocks P/E < 40
PASS research signals=['\\bresearch\\b'] read_only=False tools=55 need=save_layout writes_kept=7 | Save my layout as research desk
PASS edit     signals=['\\bdelete\\b'] read_only=False tools=55 need=portfolio_delete_position writes_kept=7 | Delete TCS from my portfolio
PASS edit     signals=['\\bupdate\\b'] read_only=False tools=55 need=portfolio_update_position writes_kept=7 | Update my RELIANCE cost basis to 1180
PASS read     signals=[] read_only=False tools=55 need=portfolio_update_position writes_kept=7 | My RELIANCE lot is actually 12 shares
PASS edit     signals=['\\bbought\\b', '\\btrack\\b'] read_only=False tools=55 need=portfolio_add_position writes_kept=7 | I bought 10 shares of INFY at 1500, track it in my portfolio
PASS edit     signals=['\\bput\\b.*\\b(on|in|into)\\b'] read_only=False tools=55 need=portfolio_add_position writes_kept=7 | Put 25 HDFC Bank at 1600 in my paper portfolio
PASS edit     signals=['\\blog\\b', '\\b\\d[\\d,.]*\\s+[a-z][\\w.&-]*\\s+at\\s+\\S*\\d'] read_only=False tools=55 need=portfolio_add_position writes_kept=7 | Can you log 10 TCS at 3400 in my portfolio?
PASS edit     signals=['\\brecord\\b(?! (highs?|lows?)\\b)', '\\b\\d[\\d,.]*\\s+[a-z][\\w.&-]*\\s+at\\s+\\S*\\d'] read_only=False tools=55 need=portfolio_add_position writes_kept=7 | Can you record that I hold 20 ITC at 410?
## VERIFIER (rc1-verifier:4)
FAIL read     signals=['\\?\\s*$'] read_only=True tools=42 need=portfolio_delete_position writes_kept=0 | Could you drop WIPRO from my portfolio?
FAIL read     signals=['\\?\\s*$'] read_only=True tools=42 need=portfolio_delete_position writes_kept=0 | I exited my ITC position, can you take it out of my portfolio?
FAIL read     signals=['\\?\\s*$'] read_only=True tools=42 need=portfolio_update_position writes_kept=0 | Can you bump my INFY quantity to 30?
## AUDITOR FRESH (round 2)
FAIL read     signals=['\\?\\s*$'] read_only=True tools=42 need=portfolio_delete_position writes_kept=0 | Could you take INFY off my portfolio?
FAIL read     signals=['\\?\\s*$'] read_only=True tools=42 need=portfolio_update_position writes_kept=0 | Can you knock my TCS holding down to 5 shares?
FAIL read     signals=['\\?\\s*$'] read_only=True tools=42 need=portfolio_delete_position writes_kept=0 | Would you scrap my ITC position?
FAIL read     signals=['\\?\\s*$'] read_only=True tools=42 need=portfolio_update_position writes_kept=0 | Can you set my RELIANCE quantity to 15?
FAIL read     signals=['\\?\\s*$'] read_only=True tools=42 need=portfolio_delete_position writes_kept=0 | Can you clear WIPRO out of my holdings?
FAIL read     signals=['\\?\\s*$'] read_only=True tools=42 need=portfolio_update_position writes_kept=0 | Can you trim INFY to 5 shares?
FAIL read     signals=['\\?\\s*$'] read_only=True tools=42 need=portfolio_delete_position writes_kept=0 | Could you get rid of my HDFC Bank holding?
FAIL read     signals=['\\?\\s*$'] read_only=True tools=42 need=portfolio_update_position writes_kept=0 | Can you fix my RELIANCE cost basis, it should be 1180?
## CONTROLS (must stay read_only True)
read     signals=['\\?\\s*$'] read_only=True tools=42 need=None writes_kept=0 | How is my portfolio doing?
read     signals=["\\bwhat('?s| is| are| was)\\b", '\\?\\s*$'] read_only=True tools=42 need=None writes_kept=0 | what is P/E?
read     signals=['\\?\\s*$'] read_only=True tools=42 need=None writes_kept=0 | Is RELIANCE up today?
read     signals=['\\bexplain\\b', '\\?\\s*$'] read_only=True tools=42 need=None writes_kept=0 | Can you explain what a P/E ratio is?
```
`./.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_b3_runtime_tool_args.py tests/test_b3_runtime_intent_gate.py` -> `192 passed in 0.48s` (the shipped tests pin only add-shaped question asks).

Entry's own repro: all literal phrasings keep their write tool (55 tools, read_only False). The verifier's 3 phrasings reproduce (read, signal `\?\s*$` only, read_only True, 42 tools, no write). All 8 auditor-fresh phrasings (drop/take off/knock down/scrap/set quantity/clear out/trim/get rid of/fix cost basis, each question-shaped) fail the same way. Controls strip as intended.

## Live, llama3.1:8b, mode agent, autonomy auto (tool_use read from the SSE transcript, not the prose)
`python3 scripts/r15/vy.py invoke copilot "<prompt>" --port 52370 --provider ollama --model llama3.1:8b --mode agent --autonomy auto --out live019-<n>.jsonl` via $SCRATCH/refaudit2-agent/live019.sh (each under the lock)
```
lock acquired 18:17:28 IST  PROMPT[1]: Could you drop WIPRO from my portfolio?
=== ASSISTANT TEXT ===
{"name": "portfolio_delete_position", "parameters": {"asset_class": "equity", "symbol": "WIPRO"}}

=== ok · 44.1s · events {'heartbeat': 4, 'delta': 1, 'done': 1} · usage in=6023 out=28 · est $0.00000 · llama3.1:8b
lock acquired 18:18:13 IST  PROMPT[2]: Can you bump my INFY quantity to 30?
=== ASSISTANT TEXT ===
{"name": "portfolio_update_position", "parameters": {"asset_class": "equity", "quantity": 30, "symbol": "INFY"}}

=== ok · 2.7s · events {'delta': 1, 'done': 1} · usage in=6024 out=33 · est $0.00000 · llama3.1:8b
lock acquired 18:18:16 IST  PROMPT[3]: Would you scrap my ITC position?
=== ASSISTANT TEXT ===
{"name": "portfolio_update_position", "parameters": {"asset_class": "equity", "symbol": "ITC.NS", "direction": "OUT"}}

=== ok · 2.7s · events {'delta': 1, 'done': 1} · usage in=6021 out=35 · est $0.00000 · llama3.1:8b
lock acquired 18:18:18 IST  PROMPT[4]: Can you trim INFY to 5 shares?
=== ASSISTANT TEXT ===
{"name": "portfolio_update_position", "parameters": {"asset_class": "equity", "symbol": "INFY", "quantity": -5, "action": "sell"}}

=== ok · 3.0s · events {'delta': 1, 'done': 1} · usage in=6023 out=39 · est $0.00000 · llama3.1:8b
lock acquired 18:18:21 IST  PROMPT[5]: Please drop WIPRO from my portfolio

Note: The status is "dispatched_unconfirmed" because we are currently in auto-apply mode, but you can verify the panel state with `get_terminal_state` before confirming.

=== ok · 27.0s · events {'heartbeat': 2, 'tool_use': 1, 'tool_result': 1, 'delta': 64, 'done': 1} · usage in=2859 out=64 · est $0.00000 · llama3.1:8b
ALLDONE
--- non-delta events per transcript
[1]
{"kind": "done", "usage": {"input_tokens": 6023, "output_tokens": 28, "cache_read_input_tokens": null, "cache_creation_input_tokens": null, "web_search_requests": null}, "finish_reason": "stop", "context_window": 16384, "spend_usd": 0.0}
{"kind": "delta", "text": "{\"name\": \"portfolio_delete_position\", \"parameters\": {\"asset_class\": \"equity\", \"symbol\": \"WIPRO\"}}"}
[2]
{"kind": "done", "usage": {"input_tokens": 6024, "output_tokens": 33, "cache_read_input_tokens": null, "cache_creation_input_tokens": null, "web_search_requests": null}, "finish_reason": "stop", "context_window": 16384, "spend_usd": 0.0}
{"kind": "delta", "text": "{\"name\": \"portfolio_update_position\", \"parameters\": {\"asset_class\": \"equity\", \"quantity\": 30, \"symbol\": \"INFY\"}}"}
[3]
{"kind": "done", "usage": {"input_tokens": 6021, "output_tokens": 35, "cache_read_input_tokens": null, "cache_creation_input_tokens": null, "web_search_requests": null}, "finish_reason": "stop", "context_window": 16384, "spend_usd": 0.0}
{"kind": "delta", "text": "{\"name\": \"portfolio_update_position\", \"parameters\": {\"asset_class\": \"equity\", \"symbol\": \"ITC.NS\", \"direction\": \"OUT\"}}"}
[4]
{"kind": "done", "usage": {"input_tokens": 6023, "output_tokens": 39, "cache_read_input_tokens": null, "cache_creation_input_tokens": null, "web_search_requests": null}, "finish_reason": "stop", "context_window": 16384, "spend_usd": 0.0}
{"kind": "delta", "text": "{\"name\": \"portfolio_update_position\", \"parameters\": {\"asset_class\": \"equity\", \"symbol\": \"INFY\", \"quantity\": -5, \"action\": \"sell\"}}"}
[5]
{"kind": "tool_use", "tool_call_id": "call_76d18b19138e4c5cb36ee9284f835e5a", "name": "portfolio_delete_position", "input": {"position_id": "get_portfolio"}}
{"kind": "tool_result", "tool_call_id": "call_76d18b19138e4c5cb36ee9284f835e5a", "name": "portfolio_delete_position", "ok": true, "error": null}
{"kind": "done", "usage": {"input_tokens": 2859, "output_tokens": 64, "cache_read_input_tokens": null, "cache_creation_input_tokens": null, "web_search_requests": null}, "finish_reason": "stop", "context_window": 16384, "spend_usd": 0.0}
{"kind": "delta", "text": "I"}
```
Prompts 1-4 (verifier x2, auditor-fresh x2): zero `tool_use` events; the only delta is the call typed as JSON chat text, turn ends (the entry's A1 symptom, 4/4). Prompt 5 is the controlled twin of prompt 1 without the `?` ("Please drop WIPRO from my portfolio"): real `tool_use portfolio_delete_position` + `tool_result`. The only difference is the gate.

## Classification: partial
The entry's stated repro holds (every captured phrasing keeps its write tools; the round-1 acceptance cases pass). The defect class the entry names (everyday portfolio write asks read as `read`, write tools stripped) still reproduces for every polite question-shaped write whose verb is not in the cue table: 11/11 in-process, 4/4 live with the identical symptom. This is the second time the class has been patched by adding verbs (batch-3, batch-12); each round new synonyms fail. Not a verifier error: the verifier ran the same runtime function the invoke path uses and the live path confirms it.

Root cause: sidecar/services/planner.py:127 `r"\?\s*$"` makes any trailing "?" a positive read cue, including a request addressed to the agent ("Can/Could/Would you ...?"); with no listed edit verb the result is `read` with signals, so sidecar/services/agent_runtime.py:1772 (`read_only = inferred_intent == "read" and bool(intent.signals)`) strips every data write at :1788-1794.

Fix shape (checked by simulation, $SCRATCH/refaudit2-agent/sim019.py, not applied): in classify_intent, do not count the bare trailing-"?" cue when the text is a request to the agent (`\b(can|could|would|will) you\b` or `\bplease\b`). Such a turn then has no read signal and keeps the full set (D-B3-3: writes still stage for review). Real read words still strip: "Can you explain what a P/E ratio is?" keeps `explain`; "How is my portfolio doing?", "what is P/E?", "Is RELIANCE up today?", "Why did TCS fall today?" still strip. Simulation output:
```
keep  read [] | Could you drop WIPRO from my portfolio?
keep  read [] | I exited my ITC position, can you take it out of my portfolio?
keep  read [] | Can you bump my INFY quantity to 30?
keep  read [] | Could you take INFY off my portfolio?
keep  read [] | Can you knock my TCS holding down to 5 shares?
keep  read [] | Would you scrap my ITC position?
keep  read [] | Can you set my RELIANCE quantity to 15?
keep  read [] | Can you clear WIPRO out of my holdings?
keep  read [] | Can you trim INFY to 5 shares?
keep  read [] | Could you get rid of my HDFC Bank holding?
keep  read [] | Can you fix my RELIANCE cost basis, it should be 1180?
-- controls
strip read ['\\?\\s*$'] | How is my portfolio doing?
strip read ["\\bwhat('?s| is| are| was)\\b", '\\?\\s*$'] | what is P/E?
strip read ['\\?\\s*$'] | Is RELIANCE up today?
strip read ['\\bexplain\\b'] | Can you explain what a P/E ratio is?
strip read ['\\bwhy\\b', '\\?\\s*$'] | Why did TCS fall today?
```

Acceptance test: sidecar/tests/test_b3_runtime_intent_gate.py, a parametrized test using `_agent_tool_ids` over "Could you drop WIPRO from my portfolio?", "Can you bump my INFY quantity to 30?", "Would you scrap my ITC position?", "Can you trim INFY to 5 shares?", "Could you get rid of my HDFC Bank holding?" asserting the needed portfolio_delete_position / portfolio_update_position is in tool_ids; plus a strip test that "Can you explain what a P/E ratio is?", "Is RELIANCE up today?" and "How is my portfolio doing?" stay disjoint from `_DATA_WRITES`. Live re-proof: `python3 scripts/r15/vy.py invoke copilot "Would you scrap my ITC position?" --port <p> --provider ollama --model llama3.1:8b --mode agent --autonomy auto --out x.jsonl` must show a `tool_use` event named portfolio_delete_position.

## Certification-failure count
batch not_certified lists: 0 (grep over every stage-c/batch-*/VERDICTS.json not_certified). Round-1 REFUTATION_AUDIT.json: partial (1). This gate (rc1-verifier:4): partial (1). Total 2.
