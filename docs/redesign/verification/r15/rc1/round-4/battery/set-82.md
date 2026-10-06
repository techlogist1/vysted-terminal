# unplanned-4 (rc1-battery-19, set-82)

Candidate: `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Sidecar `:52359`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-LEAD-043 | Live `vy.py invoke copilot "hi" --provider openai --model gpt-4o-mini --mode agent --autonomy ask --no-key --port 52359`, plus a direct `curl POST /llm/chat` with the same no-key openai request | Both routes return the humanized `code: "auth"`, `"No OpenAI API key is set — add it in Settings."` frame, not the generic `code: "internal"` / "restart Vysted" frame. Groq is not a CLI provider choice in this candidate's `vy.py` (choices are openrouter/openai/deepseek/ollama), so only the openai leg of the original two-provider repro was re-run; it independently confirms the fixed mechanism (SDK-constructor exception now reaches `humanize()` before the router's last-resort guard) on both call sites named in the entry. | holds |

COVERAGE: 1/1 ids raw; no raw: none.
