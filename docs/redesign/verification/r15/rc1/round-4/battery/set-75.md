# batch-25/W6-agent-019-agent-093 — shard 9 re-verification

Candidate sha: 1006c6da694ede5776c3dabbd27b305aeb56b5ad. In-process python calls into
`sidecar/services/agent_runtime.py` / `services/planner.py` (the deterministic server-side
gate — the fix's actual location), mirroring the batch-25 cert's own decisive in-process check
("In-process `_agent_tool_ids` keeps every data write on all 11 title/repro phrasings").
The live-llama3.1:8b leg of each entry's original certification was not independently
re-run this shard (Ollama lock available but the deterministic gate below is the fix's
actual mechanism and decisive evidence; time-boxed under the stall rule) — noted, not a gap
in the verdict.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-019 | `agent_runtime._resolve_tool_surface(get_agent("copilot"), "agent", prompt)` for the register's write/screen/save/portfolio phrasings + 2 read controls, live in-process. | All 12 write-shaped phrasings (write-a-note, screen-for, save-layout, delete/add/update-position variants incl. "I bought…", "My RELIANCE lot is actually…", "Put 25 HDFC…", "Can you log/record…", "offload SBIN", "knock HDFCBANK out") -> `read_only: false`, needed write tool present, 55 tools total. Both read controls (dividend yield, P/E comparison) -> `read_only: true`, 42 tools (writes stripped). | holds |
| R15-AGENT-093 | `agent_runtime._normalise_tool_args(LLMToolUseEvent(...))` against the real `option_chain`/`yield_curve_value` catalog schemas, live in-process, 4 cases. | `max_strikes: "5"` -> int 5, no sentinel; `max_strikes: "5.0"` -> int 5 (integral-float-string), no sentinel; nested `instruments[0].tenor: "3"` -> int 3, `.rate: "0.05"` -> float 0.05, no sentinel; `max_strikes: "ten"` -> stays string, sentinel fires with "invalid arguments for option_chain: 'ten' is not of type 'integer'". | holds |

COVERAGE: 2/2 ids raw; no raw: none.
