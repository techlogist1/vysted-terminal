import sys; sys.path.insert(0, ".")
from services import agent_runtime as ar
from services.agent_tools import catalog
ids = set(catalog.CAPABILITY_CATALOG)
live = 'Price Data: {"ok": true, "symbol": "SIFY.US", "latest_price": 2.11, "volume": 1234567}\n\nUnfortunately, I am unable.'
for s in [live, 'Financial Statements returned: {"revenue": "$410 m"}\n', 'Price data returned a close of $2.11.\n',
          'The Fundamentals Tool shows revenue of $1320 m.\n', 'price-data: {"close": 2.11}\n', 'Per `price data`, the close was $2.11.\n']:
    out, d = ar._guard_tool_citations(s, {"financial_statements"}, ids, 0)
    print("REPLACED" if out != s else "KEPT    ", repr(s[:70]), "->", repr(out[:70]))
