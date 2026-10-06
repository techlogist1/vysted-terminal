# Gate round 3 — fix round 1 recheck (rc1-fix-r1-recheck)

Opus, fresh. Certified from the running app: own sidecar from source at the candidate worktree
(`git rev-parse HEAD` = `5ff9be041180c1c316ad48ceb120a23549a7575a`), port 52336, data dir
`rc1-round-3-data-rc1-fix-r1-recheck` (copy of the seed), sleep pid 3561 (killed at the end).
Evidence: `fix-r1/recheck/`. Written 2026-09-26 22:44 IST.

| key | repro | observed | verdict |
| --- | --- | --- | --- |
| rc1-drive-composer-chat:1 | Literal: `vy.py invoke copilot "hi" --port 52336 --provider openai --model gpt-4o-mini --mode agent --autonomy ask --no-key` (`recheck/invoke-nokey-openai.jsonl`). Groq: vy.py has no groq lane, so direct POST `/agents/copilot/invoke` and `/llm/chat` with no `api_key`. Fresh cases: the same two routes for all 7 key-taking providers (anthropic, openai, gemini, groq, deepseek, xai, openrouter) on their default models (`recheck/{invoke,llmchat}-nokey-<id>.sse`); an empty-string key `""` on openai and anthropic (`llmchat-emptykey-*.sse`); a third route, a durable run `POST /agents/copilot/runs` on groq with no key (`run-nokey-groq*.json`). Adjacent checks: `--bad-key` on openai (`invoke-badkey-openai.jsonl`) and a happy-path call on the openai-shaped adapter via an OpenRouter free slug (`invoke-happy-openrouter-2.*`). | All 14 no-key frames (7 providers x 2 routes) are `code:"auth"`, "No <Provider> API key is set — add it in Settings." / "Add your <Provider> API key in Settings.". None is `code:"internal"`. The literal openai repro gives the same result. The empty key gives `auth` too. The durable run ends `status:"error"` with detail "No Groq API key is set — add it in Settings.". The invalid key still humanizes to `auth` ("The OpenAI API key was rejected — check it in Settings."). The happy path on nemotron-3-super:free returns a normal answer (thinking 31, delta 9, done). All `_client(api_key)` calls in openai/groq/gemini/anthropic (stream_chat, validate_key, list_models) now run inside a `try`. The chain is green at 5ff9be04: ci-local run 2 EXIT=0 (vitest 1849, cargo ok, pytest 3649 passed / 1 skipped) and smoke EXIT=0 (`fix-r1/INTEGRATION.md`). | **fixed** |

Side note (not a product defect): vy.py's default free slug `inclusionai/ling-3.0-flash-vl:free` is now
404 "unavailable for free" upstream. The sidecar correctly humanized it as `model_not_found`
(`invoke-happy-openrouter.*`), so the happy path was rerun on `nvidia/nemotron-3-super-120b-a12b:free`.
