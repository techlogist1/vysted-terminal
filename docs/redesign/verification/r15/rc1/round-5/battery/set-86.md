# set-86 — unplanned-1 (rc1-battery-20)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. No pinned test names R15-LEAD-043
directly, so this was re-run live against the candidate's own sidecar (own boot on :52360, data
dir `rc1-round-5-data-rc1-battery-20`).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-043 | `python3 scripts/r15/vy.py invoke copilot "hi" --provider openai --model gpt-4o-mini --mode agent --autonomy ask --no-key --port 52360` (the register's own literal repro). | `{"kind":"error","message":"No OpenAI API key is set — add it in Settings.","action":"Add your OpenAI API key in Settings.","code":"auth", ...}` — humanized `auth` error, not the generic "internal error, restart Vysted" frame the entry names. Raw: `battery/raw/set-86/R15-LEAD-043-openai.txt`. A parallel `--provider groq` run was attempted but `vy.py`'s `--provider` choices are only `{openrouter,openai,deepseek,ollama}` (groq is not a selectable lane in this harness script) — recorded as an environment note, not a defect; the register's own repro used exactly the openai path reproduced above, and that one both reproduced (pre-fix framing) and re-verifies fixed here. | holds |

COVERAGE: 1/1 ids raw; no raw: none.
