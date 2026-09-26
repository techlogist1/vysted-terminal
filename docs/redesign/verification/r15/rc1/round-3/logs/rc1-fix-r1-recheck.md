# rc1-fix-r1-recheck — working log (2026-09-26 22:44 IST)

- The candidate worktree HEAD is 5ff9be041180c1c316ad48ceb120a23549a7575a (OK).
- Seed copied to rc1-round-3-data-rc1-fix-r1-recheck. Sidecar booted from source on :52336 (sleep pid 3561, worker 3562); /health ok, openbb-mcp available.
- The literal openai --no-key repro gives an auth frame. vy.py refuses --provider groq (choices openrouter/openai/deepseek/ollama), so groq was driven with a direct curl.
- Sweep of 7 key-taking providers on /agents/copilot/invoke and /llm/chat: all 14 are auth.
- Empty-string key on openai and anthropic: auth. Durable run on groq with no key: status error, humanized detail.
- --bad-key on openai: auth "rejected". Happy path on the OpenRouter free slug nemotron: ok (the default ling slug is 404 upstream and was humanized as model_not_found).
- Chain: INTEGRATION.md, ci-local run 2 EXIT=0 and smoke EXIT=0 at 5ff9be04.
- Local model not used, so the Ollama lock was not taken. No OpenAI spend: the no-key and bad-key calls were logged at $0.
- Sidecar stopped (killed sleep pid 3561; worker gone; :52336 closed).
- Verdict: rc1-drive-composer-chat:1 fixed.
