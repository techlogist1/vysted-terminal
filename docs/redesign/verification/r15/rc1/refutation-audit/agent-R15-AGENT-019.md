# R15-AGENT-019 refutation audit (group agent)

HEAD: `6741387b`. Own sidecar on 127.0.0.1:52370 (repo venv, uvicorn app:app, VYSTED_DATA_DIR=$SCRATCH/refaudit-agent/data/live, MCP left unbound); ollama llama3.1:8b behind /tmp/vysted-r15-ollama.lock.

## Entry and certification
- Entry: the intent gate classified write/note/screen/save asks and everyday portfolio phrasings ("Delete TCS from my portfolio", "I bought 10 INFY at 1500") as read and stripped the write tools; llama3.1:8b then typed the call as JSON text. Fix shape: strip only on a positive read signal, or add cues.
- Certified stage-c/batch-3/VERDICTS.md:65 (9 captured phrasings keep their write tools; live note + delete emitted real tool_use).
- The fix (D-B3-3): `sidecar/services/agent_runtime.py:1666` `read_only = inferred_intent == "read" and bool(intent.signals)` plus new edit cues in `sidecar/services/planner.py:76-108`.

## Verifier refutation (rc1-verifier:3, evidence inproc-refutations.txt)
Question-shaped portfolio writes: "Can you log 10 TCS at 3400 in my portfolio?", "Can you record that I hold 20 ITC at 410?", "What if you drop TCS from my holdings?", "Why not trim my INFY holding to 5 shares?" -> read with a positive read cue -> data writes stripped.

## 1. Entry's own repro at HEAD (in-process; runtime tool surface, mode "agent")
`cd sidecar && VYSTED_DATA_DIR=$SCRATCH/refaudit-agent/data .venv/bin/python $SCRATCH/refaudit-agent/agent019.py`
```
## ENTRY PHRASINGS
edit     signals=['\\bnotes?\\b', '\\bwrite\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Write a note on Cochin Shipyard: valuation looks stretched at ~54x trailing P/E; revisit after Q2 results.
edit     signals=['\\bscreen\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | screen for Indian defence and shipbuilding stocks with P/E below 60 and market cap above 10000 crore
edit     signals=['\\bscreen\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | screen for defence stocks P/E < 40
edit     signals=['\\bscreen\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Screen for cheap profitable tech
read     signals=[] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | find me low-P/E high-ROE names
edit     signals=['\\bsave\\b', '\\bscreen\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Save this screen as Defence value
research signals=['\\bresearch\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Save my layout as research desk
edit     signals=['\\bnotes?\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Note: BDL order inflow looks lumpy
edit     signals=['\\bjot\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Jot down that HAL results are on 12 Nov
edit     signals=['\\badd\\b', '\\bnotes?\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Add a note to COCHINSHIP
edit     signals=['\\bbought\\b', '\\btrack\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | I bought 10 shares of INFY at 1500, track it in my portfolio
edit     signals=['\\badd\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Add 10 INFY.NS at 1500 to my portfolio
edit     signals=['\\bput\\b.*\\b(on|in|into)\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Put 25 HDFC Bank at 1600 in my paper portfolio
edit     signals=['\\bbuy(ing)?\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Log a buy: 5 TCS @ 2500
edit     signals=['\\bsold\\b', '\\bremove\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | I sold my TCS, remove it from my portfolio
edit     signals=['\\bdelete\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Delete TCS from my portfolio
edit     signals=['\\bchange\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Change my TCS position to 25 shares
edit     signals=['\\bupdate\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Update my RELIANCE cost basis to 1180
read     signals=[] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | My RELIANCE lot is actually 12 shares not 10
edit     signals=['\\bnotes?\\b', '\\bsave\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Save a note on RELIANCE: capex guidance raised
edit     signals=['\\bnotes?\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Append to my RELIANCE note that Jio IPO is H1
read     signals=[] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Remember that HAL results are on 12 Nov
edit     signals=['\\bnotes?\\b', '\\bwrite\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Write this to my general notes: rates on hold
edit     signals=['\\bnotes?\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Replace my TCS note with: exit below 2000
## CONTROLS
read     signals=['\\?\\s*$'] read_only=True tools=42 writes_kept=[] | How is my portfolio doing?
read     signals=["\\bwhat('?s| is| are| was)\\b", '\\?\\s*$'] read_only=True tools=42 writes_kept=[] | what is P/E?
## VERIFIER PHRASINGS
read     signals=['\\?\\s*$'] read_only=True tools=42 writes_kept=[] | Can you log 10 TCS at 3400 in my portfolio?
read     signals=['\\?\\s*$'] read_only=True tools=42 writes_kept=[] | Can you record that I hold 20 ITC at 410?
read     signals=['\\?\\s*$'] read_only=True tools=42 writes_kept=[] | What if you drop TCS from my holdings?
read     signals=['\\bwhy\\b', '\\?\\s*$'] read_only=True tools=42 writes_kept=[] | Why not trim my INFY holding to 5 shares?
## AUDITOR EXTRA (same class)
edit     signals=['\\badd\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Could you add 10 TCS at 3400 to my portfolio?
edit     signals=['\\bnotes?\\b', '\\bwrite\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Can you write a note on TCS: margins improving?
build    signals=['\\blay ?out\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Can you save my layout as desk?
edit     signals=['\\bnotes?\\b'] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Can you log a note that HAL results are on 12 Nov?
read     signals=[] read_only=False tools=55 writes_kept=['write_note', 'write_screener_filters', 'save_screen', 'save_layout', 'portfolio_add_position', 'portfolio_update_position', 'portfolio_delete_position'] | Please log 10 TCS at 3400 in my portfolio
```
`cd sidecar && .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_b3_runtime_intent_gate.py`
```
26 passed in 0.11s
```
All 24 phrasings the entry captured (composer-chat/52-intent-gate-probe.txt + portfolio-notes/30-intent-gate-portfolio-notes.txt) keep every write tool (55 tools, read_only False). Controls "How is my portfolio doing?" / "what is P/E?" still strip to 42.

Live, entry's own prompts (POST /agents/copilot/invoke, ollama llama3.1:8b, mode agent, autonomy auto; script `$SCRATCH/refaudit-agent/live.py` driven by `live.sh`):
```
PROMPT: Delete TCS from my portfolio
  elapsed=58.8s kinds={'heartbeat': 5, 'tool_use': 1, 'delta': 45, 'done': 1}
  tool_use=[('portfolio_delete_position', {'position_id': "the id of the TCS position in the user's portfolio"})]
  text="I've deleted TCS from your portfolio. Please note that this action has been dispatched to the panel, but its status is still unconfirmed. You can verify the result by checking the terminal state using `get_terminal_state`."
lock acquired Fri Sep 25 10:03:03 IST 2026
PROMPT: Write a note on Cochin Shipyard: valuation looks stretched at ~54x trailing P/E; revisit after Q2 results.
  elapsed=40.7s kinds={'heartbeat': 3, 'tool_use': 1, 'delta': 25, 'done': 1}
  tool_use=[('write_note', {'text': 'valuation looks stretched at ~54x trailing P/E; revisit after Q2 results.', 'mode': 'append', 'scope': 'COCHIND.NS'})]
```
Both now emit a real tool_use (the original run emitted none). The entry's stated repro does not reproduce.

## 2. Verifier's refutation at HEAD
In-process: the "VERIFIER PHRASINGS" block above - all four -> read, signals ['\?\s*$'] (plus '\bwhy\b'), read_only True, 42 tools, no write tool kept. Reproduces.

Live, same lane:
```
  text='The note has been dispatched to the panel, and its status is awaiting confirmation. Please check the panel state for further updates.'
lock acquired Fri Sep 25 10:03:44 IST 2026
PROMPT: Can you log 10 TCS at 3400 in my portfolio?
  elapsed=25.6s kinds={'heartbeat': 2, 'delta': 1, 'done': 1}
  tool_use=[]
  text='{"name": "portfolio_update_position", "parameters": {"quantity": 10, "price": 3400.0, "asset_class": "equity", "symbol": "TCS"}}'
lock acquired Fri Sep 25 10:04:10 IST 2026
PROMPT: Can you record that I hold 20 ITC at 410?
  elapsed=3.2s kinds={'delta': 1, 'done': 1}
```
This is the entry's exact live symptom (A1): no tool_use; llama3.1:8b types the portfolio write as JSON chat text and the turn ends. The ollama adapter's leaked-call rescue (services/llm/ollama.py ~:265-270) cannot recover it because the tool was not offered.

Auditor's bounding cases (same block "AUDITOR EXTRA"): a question with a known edit verb keeps the writes ("Could you add 10 TCS…?", "Can you write a note…?"), and "Please log 10 TCS at 3400 in my portfolio" (no "?") keeps them (cue-less -> not stripped). The failure needs BOTH a positive read cue ("?" / "why" / "what if") AND a write verb missing from `_EDIT_SIGNALS` (log, record, hold, drop, trim).

## Classification: partial
The fix holds for every phrasing the entry captured and for its live repro. But the entry's stated class ("everyday portfolio phrasings … classified as read, stripping the exact write tools they need") still reproduces for polite question-shaped asks, with the identical live failure. Root cause: `sidecar/services/planner.py:76-108` `_EDIT_SIGNALS` lacks log/record/hold/drop/trim cues, and `planner.py:120` `r"\?\s*$"` counts a trailing "?" as a positive read cue, so `agent_runtime.py:1666` strips (`read_only = inferred_intent == "read" and bool(intent.signals)`) and :1669-1688 remove every data write.

Acceptance test (sidecar/tests/test_b3_runtime_intent_gate.py, reusing `_agent_tool_ids`): parametrize over "Can you log 10 TCS at 3400 in my portfolio?" and "Can you record that I hold 20 ITC at 410?" -> assert "portfolio_add_position" in tool_ids; keep `test_positive_read_cue_still_strips_data_writes` ("what is P/E?") and "How is my portfolio doing?" stripping green. The verifier's two hypotheticals ("What if you drop TCS…?", "Why not trim…?") are genuinely ambiguous (a what-if can be a read); keeping the write tools there is desirable (writes still stage for review) but is a judgment call, not required for this entry.
