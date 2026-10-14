from services.research.citecheck import strip_model_bibliography
from services.agent_runtime import _normalise_tool_args
from models.llm import LLMToolUseEvent
body = "NVDA grew revenue 94% [1]. Margins expanded [2].\n\n"
for head in ["## Citations", "**Sources cited:**", "## Source List", "## Key sources", "Further reading:", "## References"]:
    md = body + head + "\n1. Reuters - NVDA Q2\n2. SEC 10-Q\n3. Blog post\n4. Extra source\n"
    out, n = strip_model_bibliography(md)
    print(f"{head!r}: removed={n} survives={'Extra source' in out}")
print("--- write_screener_filters group-only")
for args in [{"group": {"op": "or", "children": [{"field": "pe", "op": "<", "value": 20}, {"field": "roe", "op": ">", "value": 15}]}},
             {"criteria": [], "group": {"op": "or", "children": [{"field": "pe", "op": "<", "value": 20}]}}]:
    ev = LLMToolUseEvent(tool_call_id="t1", name="write_screener_filters", input=args)
    _normalise_tool_args(ev)
    print(list(args), "->", ev.input)
