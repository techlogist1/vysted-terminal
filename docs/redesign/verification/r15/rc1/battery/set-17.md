# batch-5/W3-agent-runtime-chat

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-020 | Same live invoke as set-15 (agent-runtime mechanics are W3-owned: `agent_runtime.py` `_notes_of`/`_note_for`/`_render_notes_line`/`_read_notes` and preamble assembly). `vy.py invoke copilot` (llama3.1:8b), `--context` with `by_source.__notes__.bySymbol.BDL` set, candidate own sidecar :52343. | `_read_notes` handler (`agent_runtime.py:1545`) reads `snapshot.by_source["__notes__"]` and answers `read_notes(scope="BDL")` with the note text; the preamble helper `_render_notes_line` (agent_runtime.py:495-517) is present and would surface "User notes exist for: BDL" + a 300-char excerpt when a symbol is focused. Live run: model called `read_notes(scope="BDL")`, then `shareholding_pattern`, then `read_notes` again, and the final answer referenced the note's 20%-pledge threshold alongside the live 74.93% pledge figure — the note round-trips through the tool loop as certified. | holds |

Evidence: `raw/set-17/R15-AGENT-020.stdout.txt`, `raw/set-17/R15-AGENT-020.events.jsonl` (same run as set-15, copied — the underlying repro is identical; W3 owns the mechanism exercised).
