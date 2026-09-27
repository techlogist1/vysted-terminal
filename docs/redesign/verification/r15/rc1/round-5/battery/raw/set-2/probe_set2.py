import sys, json
sys.path.insert(0, ".")

from services.research import relevance, deep, verify, citecheck, finance
from services.research.models import ResearchSource
from services.research.target import target_from_payload

out = {}

# --- R15-RESEARCH-001: gate_news drops off-entity, keeps on-entity, for a resolved target ---
bdl = target_from_payload({"ok": True, "resolved": {
    "symbol": "BDL", "name": "Bharat Dynamics Limited", "exchange": "NSE",
    "region": "IN", "asset_class": "equity", "confidence": 0.95,
}})
items = [
    {"url": "https://x.example/1", "title": "Sterling and Wilson bags Rs 985 cr order", "snippet": ""},
    {"url": "https://x.example/2", "title": "Bharat Dynamics wins Rs 500 cr defence order", "snippet": ""},
]
kept, note = relevance.gate_news(items, target=bdl)
out["RESEARCH-001"] = {
    "kept_urls": [i["url"] for i in kept],
    "note": note,
}

# --- R15-RESEARCH-034: _reflect_says_complete on the three register strings ---
out["RESEARCH-034"] = {
    "not_covered_yet": deep._reflect_says_complete("Price action is not covered yet"),
    "COMPLETE": deep._reflect_says_complete("COMPLETE"),
    "no_gaps": deep._reflect_says_complete("No gaps remain"),
}

# --- R15-RESEARCH-004: _split_claims keeps figures intact ---
claims1 = verify._split_claims(
    "revenue growth +40.5%\nP/E 67.13953\n-0.4% YoY margin\n40.5% growth again",
    limit=10,
)
claims2 = verify._split_claims("P/E 34.42\nGross Margin 51.70%", limit=10)
out["RESEARCH-004"] = {"claims1": claims1, "claims2": claims2}

# --- R15-RESEARCH-003: all_sources append-only across rounds ---
f = deep._Findings()
f.web_sources = [
    ResearchSource(url="vysted://price/BDL", title="price", excerpt="", source_type="web"),
    ResearchSource(url="vysted://fundamentals/BDL", title="fundamentals", excerpt="", source_type="web"),
]
round1 = f.all_sources()
round1_urls = [s.url for s in round1]
# round 2 appends higher-tier filings sources
f.web_sources.extend([
    ResearchSource(url="https://nsearchives.nseindia.com/f1.pdf", title="filing1", excerpt="", source_type="filing"),
    ResearchSource(url="https://nsearchives.nseindia.com/f2.pdf", title="filing2", excerpt="", source_type="filing"),
])
round2 = f.all_sources()
round2_urls = [s.url for s in round2]
out["RESEARCH-003"] = {
    "round1_urls": round1_urls,
    "round2_urls": round2_urls,
    "round1_prefix_stable": round2_urls[: len(round1_urls)] == round1_urls,
}

# --- R15-RESEARCH-029: strip_model_bibliography ---
md = (
    "Earnings growth: -0.4% ([n] 1)\n\n"
    "**Merged Sources**\n"
    "1. Foo\n2. Bar\n3. Baz\n4. Qux\n5. Quux\n6. Corge\n7. Grault\n\n"
    "References:\n"
    "[n] 1. Foo (https://a.example)\n"
    "[n] 2. Bar (https://b.example)\n"
)
cleaned, removed = citecheck.strip_model_bibliography(md)
out["RESEARCH-029"] = {
    "removed": removed,
    "has_n_marker": "[n]" in cleaned,
    "has_merged_sources": "Merged Sources" in cleaned,
    "has_references": "References:" in cleaned,
    "cleaned": cleaned,
}

# --- R15-RESEARCH-037: priority_note on an UNRANKED list ---
general = ResearchSource(url="https://blog.example/x", title="general", excerpt="", source_type="web")
primary = ResearchSource(url="https://www.sec.gov/x", title="primary", excerpt="", source_type="filing")
press = ResearchSource(url="https://www.reuters.com/x", title="press", excerpt="", source_type="news")
note = finance.priority_note([general, primary, press])
out["RESEARCH-037"] = {"note": note}

print(json.dumps(out, indent=2))
