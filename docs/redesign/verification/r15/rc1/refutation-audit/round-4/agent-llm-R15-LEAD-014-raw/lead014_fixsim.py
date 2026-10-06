import json
from services.agent_tools.schemas import TOOL_SCHEMAS
_TYPES = {"string","number","integer","boolean","array","object","null"}
def is_placeholder(parsed, schema):
    props = schema.get("properties") or {}
    return any(isinstance(v, str) and v in _TYPES and v == (props.get(k) or {}).get("type", v) for k, v in parsed.items())
caught = missed = 0
for name, spec in TOOL_SCHEMAS.items():
    s = spec.get("input_schema") or {}
    props = s.get("properties") or {}
    if not props: continue
    for keys in (list(props), s.get("required") or []):
        if not keys: continue
        ph = {k: (props[k].get("type") if isinstance(props[k].get("type"), str) else "string") for k in keys}
        if is_placeholder(ph, s): caught += 1
        else: missed += 1
legit = [("fundamentals", {"symbol": "AAPL"}), ("resolve_symbol", {"query": "Tata Steel"}), ("write_note", {"scope": "RELIANCE", "text": "capex raised"}), ("news", {}), ("news", {"symbols": ["AAPL"], "limit": 5}), ("price_data", {"symbol": "SPY", "timeframe": "1d"})]
print("placeholder echoes caught:", caught, "missed:", missed)
print("legit false positives:", [(n, a) for n, a in legit if is_placeholder(a, TOOL_SCHEMAS[n]["input_schema"])])
