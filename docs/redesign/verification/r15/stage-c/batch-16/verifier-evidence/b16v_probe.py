import json, sys
sys.path.insert(0, ".")
from services import agent_runtime as ar
from services.agent_tools import catalog
SIFY = {"ok": True, "fundamentals": {"symbol": "SIFY", "trailing_12m_revenue": {"display": "$1320 m"}}}
res = [json.dumps(SIFY)]
print("== AGENT-090 fresh guarded (expect REPLACED)")
for s in ["One ADS equals 3 series B preferred shares. ", "Each ADS represents 6 underlying class A shares. ",
          "Each ADR represents 8 restricted voting shares. ", "Each ADS is equivalent to 2 class A common shares. ",
          "Each ADR represents 4 new equity shares. ", "Each ADS represents 6 fully paid class A shares. ",
          "Each ADS represents 5 Series A shares. ", "Each ADS represents 2 A shares. ",
          "Each ADS represents 10 non-voting shares. ", "Each ADR corresponds to 6 class A ordinary shares. ",
          "One SIFY ADS = 6 class A shares. ", "Each ADS represents 12 ordinary shares of class A. "]:
    out = ar._guard_ratio_claims(s, res)
    print("REPLACED" if out.strip()==ar.RATIO_UNAVAILABLE else "KEPT    ", repr(s))
print("== AGENT-090 kept (expect KEPT)")
for s in ["SIFY's ADSs each gained 3 points in 2024. ", "There are 3 analyst ratings on the ADS. ",
          "The ADS fell 4 percent over 2 sessions. ", "Revenue was ₹4,651 cr. ", "Each ADR closed at 5.20 USD on Friday. "]:
    out = ar._guard_ratio_claims(s, res)
    print("REPLACED" if out.strip()==ar.RATIO_UNAVAILABLE else "KEPT    ", repr(s))
print("== AGENT-090 traced lower-case source (expect KEPT)")
st = {"ok": True, "ads_ratio": {"statement": "American Depositary Shares, each representing ten class A ordinary shares"}}
s = "Each ADS represents 10 class A ordinary shares. "
print("KEPT" if ar._guard_ratio_claims(s,[json.dumps(st)])==s else "REPLACED", repr(s))
s = "Each ADS represents 8 class A ordinary shares. "
print("KEPT(bad)" if ar._guard_ratio_claims(s,[json.dumps(st)])==s else "REPLACED(good)", repr(s))
ids = set(catalog.CAPABILITY_CATALOG)
print("== LEAD-030 citation guard; ok_tools={'fundamentals'}")
for s in ["- price_data returned: [{\"close\": 12.3}]\nNext line. ", "According to `news`, revenue was $5 bn. ",
          "The financial_statements output shows revenue of ₹4,411 cr. ", "fundamentals returned revenue of $1.3 bn. ",
          "The quote tool shows the price at $12.30. ", "Per the tool output, revenue was $1.3 bn. ",
          "I'll call `price_data` next. ", "Let me look up the fundamentals data for SIFY. ",
          "Let me fetch the `financial_statements` data for SIFY. ", "I will use the price_data tool to get the latest price. ",
          "Next I'll check the news data for any sentiment. ", "The fundamentals tool shows revenue of $1320 m. "]:
    for ok in ({"fundamentals"}, set()):
        out, d = ar._guard_tool_citations(s, ok, ids, 0)
        print(("REPLACED" if out!=s else "KEPT    "), sorted(ok), repr(s), "->", repr(out[:80]))
