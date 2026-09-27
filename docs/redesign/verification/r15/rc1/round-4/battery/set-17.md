# Battery shard 17 — set-17 (batch-5/W3-agent-runtime-chat)

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad, sidecar :52357 (own data dir, isolated,
keyless). All entries re-run live against candidate code (in-process python calls into the real
services.agent_runtime / services.llm.openai / services.research.deep modules, one live SSE
curl against the sidecar, and one node re-run of the frontend matcher) — never judged from the
diff alone.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-040 | live SSE: 12-turn history via /agents/copilot/invoke (ollama llama3.1:8b) | folded-history notice: "the 4 earliest messages... folded" (8 kept verbatim, matches _HISTORY_VERBATIM_MESSAGES=8) | holds |
| R15-AGENT-026 | in-process: agent_runtime._finish_turn(LLMDoneEvent(finish_reason="length"), ...) | typed notice "The answer hit the model's output limit and was cut off..." + done frame | holds |
| R15-RESEARCH-014 | in-process: research.deep._synthesis_llm with stub adapter emitting finish_reason="length" | truncated=True | holds |
| R15-AGENT-025 | in-process: agent_runtime._relay_provider(never-emitting stream, idle=25.0) | 2 heartbeats @10s cadence then error frame at t=30s ("provider_idle") | holds |
| R15-AGENT-048 | in-process: OpenAIProvider._resolve_tool_events with 5 schema-invalid tool calls, stubbed oneshot.complete_with_usage | exactly 2 repair calls made (timed+metered), 3 sentinel'd with no call | holds |
| R15-AGENT-033 | in-process: agent_runtime._staged_actions_notice([set_chart_symbol BDL staged]) | "Staged for your review, not applied yet: set_chart_symbol BDL. Accept it below to apply." | holds |
| R15-AGENT-031 | node: re-ran isRuntimeNotice(stepKind) against the 3 register notice copies | all 3 match (old regex missed 2/3) | holds |
| R15-UI-054 | node: same as AGENT-031 (live instance, same fix) | all 3 match | holds |

COVERAGE: 8/8 ids raw; no raw: none.
