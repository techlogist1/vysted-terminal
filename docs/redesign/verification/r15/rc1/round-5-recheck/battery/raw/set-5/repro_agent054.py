import sys
sys.path.insert(0, ".")
from services.agent_runtime import _normalise_tool_args
from models.llm import LLMToolUseEvent
from services.agent_tools.catalog import SUPPORTED_INDICATORS

event = LLMToolUseEvent(tool_call_id="tc1", name="set_chart_indicators", input={"indicators": ["rsi", "bollinger_bands"]})
_normalise_tool_args(event)
print("input after normalise:", event.input)
print("SUPPORTED_INDICATORS count:", len(SUPPORTED_INDICATORS))
print("full sorted list:", ",".join(sorted(SUPPORTED_INDICATORS)))
