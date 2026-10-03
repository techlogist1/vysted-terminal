# AC-3 — read turns offer no data-write tool; no-tool behaviour (final-adv-maintainer, d38b5d1a)

Lane: llama3.1:8b on own source sidecar :52825 (data dir own scratch), one Ollama lock hold per call.

## Server-side tool surface (in-process, cand sidecar, copilot spec, mode=agent) — AC-3/tool-surface.jsonl
- Positive read cue (`?`, what/explain): read_only=true, 42 tools, **0 data-write tools** (portfolio_*, write_note, save_*, write_screener_filters all stripped).
- Explicit no-tool cue ("Do not call any tools", "Do not use any tools. Also add 5 TCS…"): **0 tools sent** (signal `no-tool`), matching DECISIONS 4.10's shipped `_NO_TOOL_CUE` behaviour.
- Cue-less read ("Show me NVDA's latest earnings") keeps the full 55-tool set: this is the documented D-B3-3 rule (agent_runtime.py:1800-1804), writes still stage. Not a finding.
- Mixed read+write prompts keep writes (edit/build intent) — by design, writes stage.

## Live (llama3.1:8b)
- AC-3/read: tool_use get_portfolio + price_data only, both ok; reply grounded (AAPL 10@180, INFY 20@1500).
- AC-3/notool: 0 tool_use, prose answer.
- AC-3/notool-plus-write (auto): 0 tool_use, nothing staged; model declined (misframed the tracking write as a trade — model prose, no write, no claim of a write). Matches 4.12's §6.5 fact "no write happened" and did not even narrate one.
- GET /portfolio/positions on :52825 after the runs: `[]` (AC-3/positions-after.json).

Nothing written without a tool call; no-tool behaviour equals 4.10/4.12 exactly.

VERDICT AC-3: pass
