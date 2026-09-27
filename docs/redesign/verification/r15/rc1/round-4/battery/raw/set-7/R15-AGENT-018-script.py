import sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-4-cand/sidecar")
from services.llm.tool_call_rescue import rescue_leaked_tool_call

# original evidence text, verbatim, from
# docs/redesign/verification/r15/surface/composer-chat/13-multiturn-t4-note.jsonl
leaked_note = '{"name": "write_note", "parameters": {"note": "Cochin Shipyard: valuation looks stretched at ~54x trailing P/E; revisit after Q2 results."}}'

offered = {"write_note", "screener_run", "price_data", "news"}
event = rescue_leaked_tool_call(leaked_note, offered)
print("rescue result:", event)
assert event is not None, "FAIL: leaked write_note JSON was not rescued"
assert event.name == "write_note"
assert event.input.get("note", "").startswith("Cochin Shipyard")
print("PASS AGENT-018: leaked write_note JSON is rescued into a real tool_use")

# fresh case: a name NOT offered stays text (must not fire on unrelated JSON)
not_offered_case = '{"name": "delete_everything", "parameters": {}}'
event2 = rescue_leaked_tool_call(not_offered_case, offered)
print("not-offered case result:", event2)
assert event2 is None, "FAIL: rescued a tool name that was never offered this round"
print("PASS AGENT-018b: a name not offered this round stays text")

# confirm the Ollama adapter actually calls the shared rescue (not the OpenAI-only path)
import inspect
from services.llm import ollama as ollama_mod
src = inspect.getsource(ollama_mod)
assert "rescue_leaked_tool_call" in src, "FAIL: ollama.py no longer calls the shared rescue"
print("PASS AGENT-018c: ollama.py calls the shared rescue_leaked_tool_call")
