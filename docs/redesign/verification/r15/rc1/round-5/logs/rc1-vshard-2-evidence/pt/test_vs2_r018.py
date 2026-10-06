import json, os
from services.research.target import ResearchTarget
from tests.test_b6_research_funnel import _researcher_tools

def T(sym, region, exch):
    return ResearchTarget(symbol=sym, name=f"{sym} Ltd", exchange=exch, asset_class="equity", confidence=1.0, region=region)

CASES = [
    ("in_bse_noregion_10k", "Form 10-K style annual filing review", T("KSE", None, "BSE"), False),
    ("in_region_only_sec_period", "Any disclosures to the SEC.", T("TCS.NS", "IN", None), False),
    ("in_lowercase_region_insider", "promoter insider trades (SAST)", T("PARAS.NS", "in", "NSE"), False),
    ("in_8k", "any 8-K equivalent material events", T("RELIANCE.NS", "IN", "NSE"), False),
    ("us_secular", "secular growth trends in AI demand", T("NVDA", "US", "NASDAQ"), False),
    ("us_secondary", "secondary offering dilution risk", T("RIVN", "US", "NASDAQ"), False),
    ("us_sectoral", "sectoral rotation into semis", T("AMD", "US", "NASDAQ"), False),
    ("us_secs_13f", "the SEC's 13F holdings data", T("MSFT", "US", "NASDAQ"), True),
    ("us_adr_infy", "latest 20-F filing", T("INFY", "US", "NYSE"), True),
]
out = {}
def test_r018_fresh():
    bad = []
    for name, q, t, want_sec in CASES:
        called = _researcher_tools(q, t)
        out[name] = called
        if ("sec_filings_list" in called) != want_sec:
            bad.append(name)
    json.dump(out, open(os.environ["R018_OUT"], "w"), indent=1)
    assert not bad, bad
