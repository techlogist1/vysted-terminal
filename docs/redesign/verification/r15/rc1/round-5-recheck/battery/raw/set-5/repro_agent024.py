import sys, json
sys.path.insert(0, ".")
from services.agent_runtime import _normalise_tool_args
from models.llm import LLMToolUseEvent

criteria_str = json.dumps([
    {"field": "pe_ratio", "operator": "lt", "value": 20},
    {"field": "roe", "operator": "gt", "value": 0.15},
    {"field": "debt_to_equity", "operator": "lt", "value": 0.5},
])
event = LLMToolUseEvent(
    tool_call_id="tc1",
    name="write_screener_filters",
    input={"criteria": criteria_str, "universe": "nse-all"},
)
print("before: criteria type =", type(event.input["criteria"]).__name__, "value =", event.input["criteria"])
_normalise_tool_args(event)
print("after: criteria type =", type(event.input.get("criteria")).__name__ if "criteria" in event.input else None)
print("after: full input =", event.input)
assert isinstance(event.input.get("criteria"), list), "FAIL: criteria not converted to list"
assert len(event.input["criteria"]) == 3, "FAIL: expected 3 elements"
print("PASS: stringified criteria coerced to 3-element list")
