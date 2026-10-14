# unplanned-1 (set-87, rc1-battery-16)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`, own sidecar `:52356`. Raw: `battery/raw/set-87/`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-043 | `python3 scripts/r15/vy.py invoke copilot "hi" --provider openai --model gpt-4o-mini --mode agent --autonomy ask --no-key --port 52356` (the register's own literal repro) | `{"kind":"error","message":"No OpenAI API key is set — add it in Settings.","action":"Add your OpenAI API key in Settings.","code":"auth", ...}` — the humanized `auth` frame, not the pre-fix generic "internal error, restart Vysted." Identical to round-5's re-verification on this exact repro. | holds |

COVERAGE: 1/1 ids raw; no raw: none.
