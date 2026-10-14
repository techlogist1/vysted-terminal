# Set batch-3/W4-research-depth (set-8)

Candidate ace7dd768c3b809b0e72b20b20cfc94eea2368bd, sidecar :52348, in-process python with the candidate venv, Ollama calls under /tmp/vysted-r15-ollama.lock. Raw: battery/raw/set-8/<id>.txt

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-009 | real `_research(depth=deep)` on ollama llama3.1:8b; PROFILES; BudgetGuard | brief.cost {tokens 10655, spend 0.0 (local), steps 4, estimate true} (was zero); PROFILES deep 600k tok / $3, ultra 1.8M / $9 | holds |
| R15-AGENT-012 | BudgetGuard.record with a metered openai LLMUsage + `oneshot.complete_with_usage` presence | cost() {tokens 43000, spend_usd 0.0258}; token ceiling breach trips ("token ceiling 1000 reached (2000 used)"); paid-model live spend not run (no funded lane; local run above shows tokens flow end to end) | holds |
| R15-RESEARCH-006 | real `cross_check` with 5 claims, 3 s verdict turns, 0.5 s wall | returns at 0.50 s (not 15 s), 1 verdict call started, all 5 claims unverified "ran out of its time budget" | holds |
| R15-RESEARCH-008 | in-process `_web_search` keyless tier + per-engine probes + direct curl_cffi probes | UPSTREAM BLOCK from this network: Brave HTTP 429 (curl_cffi chrome), Mojeek "403 automated queries" wall / challenge, DDG HTTP 202 challenge; product answers in ~9-10 s with an honest "no engine available ... rate-limiting" message (no 40 s timeout). Cannot show rows; the rotation-to-third-engine half is not provable today | blocked_env |
| R15-DATA-045 | in-process `fetch_page` / `visit_for_research` through httpbin.org/redirect-to -> loopback canary | fetch_page ok:false "blocked redirect to a non-public or non-http(s) URL"; visit_for_research text None + same reason; canary server hits [] ; control public->public (example.com) fetches ok | holds |
| R15-LIFECYCLE-006 | vy.py invoke researcher, openrouter free nemotron, tier_b, X-Vysted-Research-Models=...=openai/o3-deep-research | research_step status "error": "The research model openai/o3-deep-research is no longer available on OpenRouter; pick another in Settings > Research." (7 occurrences); the model's answer reports the research tool unavailable (no blank turn) | holds |

COVERAGE: 6/6 ids raw; no raw: none
