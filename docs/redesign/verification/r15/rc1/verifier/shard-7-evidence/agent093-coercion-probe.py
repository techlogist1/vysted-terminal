from services import agent_runtime as ar
from models.llm import LLMToolUseEvent
cases=[
 ("option_chain",{"symbol":"NIFTY","max_strikes":"10"}),
 ("option_chain",{"symbol":"NIFTY","max_strikes":" 5 "}),
 ("option_chain",{"symbol":"NIFTY","max_strikes":"5.0"}),
 ("add_chart_drawing",{"kind":"horizontal-line","points":[{"price":"185.5"}]}),
 ("yield_curve_value",{"valuation_date":"2026-09-25","sample_count":"5","instruments":[{"type":"deposit","tenor":"3","tenor_unit":"months","rate":"0.05"},{"type":"swap","tenor":2,"tenor_unit":"years","rate":0.055}]}),
]
for n,a in cases:
    e=LLMToolUseEvent(tool_call_id="x",name=n,input=dict(a)); ar._normalise_tool_args(e)
    print(n, a, "->", e.input)
