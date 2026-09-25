# rc1-scenarios working log

- Start (see file mtimes below). Candidate 4097dac4 (rc1-cand worktree, read-only). Data dir
  scratchpad/rc1-data-rc1-scenarios (cp -R of rc1-seed-data).
- Own sidecar :52311 booted from rc1-cand/sidecar, env VYSTED_OPENBB_MCP_PORT=52153
  VYSTED_SEC_EDGAR_MCP_PORT=52154. sleep wrapper pid 67595 (python worker 67598). Log
  scratchpad/rc1-scenarios-sidecar.log. /health ok.
- Read sidecar/services/agent_runtime.py: the read-back/ack contract is real and fairly
  mature — `_await_host_action_acks` grace-polls the ack ledger per round,
  `_grounded_host_action_result` rewrites the tool's own result before the model narrates:
  `dispatched_unconfirmed` ("verify with get_terminal_state before claiming success"),
  `applied` ("you may state it as done"), `kept_previous` ("do NOT claim this rendered"),
  `staged` ("do NOT claim it is done"), `failed` ("say plainly it did not happen"). This is
  exactly the mechanism the register's fixed AGENT-032/033/046 and CODE-FRONTEND-011 entries
  point at — so those four are my primary regression-check targets on the candidate.
- Register scan for the 3 properties: all of R15-AGENT-001 (money-figure hallucination),
  R15-AGENT-021/022/080 (unfenced auto-apply / fabricated cost basis), R15-AGENT-032/033/046,
  R15-AGENT-054, R15-CODE-FRONTEND-011, R15-RESEARCH-002 (ULTRA cross-check hides UNVERIFIED)
  are status=fixed — regression targets.
- Reused a prior composer-chat trace (12-multiturn-t3-watchlist.jsonl,
  13b-multiturn-t4-note-retry.jsonl) to confirm vy.py/harness conventions: empty
  Ollama tool_call_id skips the ack (`_ack_skipped`), and the OLD fixed behaviour already
  showed the model correctly hedging ("pending confirmation") rather than claiming success —
  reused as the read-back baseline to diff against.
- Designed 12 scenarios (4/property): RB1-4 (watchlist add/auto, portfolio add/ask, note
  write/ask, arrange layout/ask), SK1-4 (AMAL, SMR, ELCIDIN 52w-low, SIFY ADR+revenue —
  all direct register traps), SC1-4 (TCS P/E, AMAL identity, portfolio total, SMR revenue),
  each SC scenario run twice fresh + once inside a synthetic 2-turn thread (via
  `--options '{"history":[...]}'`) = 20 calls/model.
- Ran the full 20-call set via scratchpad/rc1-scenarios/run_ollama.sh (llama3.1:8b,
  sequential, one nohup'd shell to respect the single-Ollama-slot constraint) then
  run_openrouter.sh (inclusionai/ling-3.0-flash-vl:free, FREE_DEFAULT). Raw SSE saved to
  docs/redesign/verification/r15/rc1/scenarios/{ollama,or}-<id>.jsonl.
- Wrap-up (05:42 IST): completed 8/8 Property 1+2 Ollama calls and 20/20 OpenRouter calls
  (nemotron:free — roughly half hit an intermittent live Nvidia provider_5xx outage
  mid-stream, half completed cleanly and are used as evidence). The 12 Property 3 (SC)
  Ollama calls remained queued behind sustained multi-agent contention on the shared local
  Ollama slot (confirmed via `ps -ef`: 3-4 concurrent sibling vy.py processes throughout,
  including 900s-budget deep-research calls on other ports) and were not completed inside
  the time budget — documented honestly as a gap rather than waited out further or
  fabricated.
- 5 findings filed to findings/rc1-scenarios.json:
  1. R15-DATA-008 regression — SIFY revenue/net_income served as INR under currency "USD"
     (direct backend probe + reproduces through the agent path on OpenRouter/nemotron).
  2. R15-DATA-015 regression — ELCIDIN 52w-low still the truncated single-venue 102,210
     (direct backend probe).
  3. R15-AGENT-033 regression — arrange_layout claims "done" against its own staged/
     not-applied notice, while portfolio_add_position and write_note in the same session
     correctly hedge on an identical notice.
  4. R15-DATA-015 regression, agent-level angle — price_data-path 52w-low for ELCIDIN is
     self-contradictory (current price stated below the "low"); model states it as fact,
     no impossibility flag.
  5. NEW defect — agent (both llama3.1:8b and nemotron, independently) fabricates SIFY's
     ADR ratio as 1:1 against a documented 1:6 ground truth trap; nemotron additionally
     invents a false "fundamentals data" citation for the fabricated number.
  R15-DATA-002 (AMAL/SMR cross-region tie) was investigated and explicitly NOT filed: the
  backend `/resolve`/`/quotes` behavior matches `resolution_policy._residual_tie`'s
  documented D58b/R11 design (cross-region is non-residual by design), and the real fix is
  a frontend-only `EquityOverviewPanel` chooser (confirmed via its own dedicated
  `R15-DATA-002`-labeled test) that a headless API/agent-tool harness cannot reach — a
  false positive avoided, not a finding.
- SCENARIOS.md and findings/rc1-scenarios.json both updated to final state before closing.
  Stopping own sidecar (:52311, wrapper pid 67595) and background monitors next; the
  shared stack and other agents' processes on other ports are left untouched.
