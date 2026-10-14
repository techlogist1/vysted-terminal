import sys
sys.path.insert(0, ".")
from services.llm.groq import _parse_tool_args
from services.llm.ollama import _parse_tool_input
from services.llm.base import INVALID_ARGS_SENTINEL

truncated = '{"symbol": "RELI'

g = _parse_tool_args(truncated)
print("groq truncated ->", g)
assert INVALID_ARGS_SENTINEL in g, "FAIL groq truncated silently became something else"

o = _parse_tool_input(truncated)
print("ollama truncated (str) ->", o)
assert INVALID_ARGS_SENTINEL in o, "FAIL ollama truncated silently became something else"

o_empty = _parse_tool_input("")
print("ollama empty string ->", o_empty)
assert o_empty == {}, "FAIL empty ollama args should stay {}"

g_empty = _parse_tool_args("")
print("groq empty string ->", g_empty)
assert g_empty == {}, "FAIL empty groq args should stay {}"

print("PASS: no silent coercion of malformed JSON to {}; empty stays {}")
