import sys; sys.path.insert(0, ".")
from services import agent_runtime as ar
from services.agent_tools import catalog
ids = set(catalog.CAPABILITY_CATALOG)
s = '- fundamentals returned:\n{\n "trailing_12m_revenue": {"display": "$1320 m"}\n}\nDone.'
out, d = ar._guard_tool_citations(s, set(), ids, 0)
print(repr(out))
