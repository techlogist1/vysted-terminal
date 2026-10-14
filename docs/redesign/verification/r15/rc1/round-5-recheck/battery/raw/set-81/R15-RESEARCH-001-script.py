import json, sys
sys.path.insert(0, ".")
from services.research.target import ResearchTarget
from services.research.relevance import gate_news

target = ResearchTarget(
    symbol="AI", name="C3.ai, Inc.", exchange="US", asset_class="equity",
    confidence=1.0, region="US", isin="US12468P1049", bse_code=None,
    industry=None, former_name="C3 IoT, Inc.",
)

items = json.load(open("/tmp/news_AI.json"))
print("raw count:", len(items))
kept, note = gate_news(items, target=target)
print("kept count:", len(kept))
print("note:", note)
dropped = [it.get("title") for it in items if it not in kept]
print("dropped examples:")
for t in dropped[:8]:
    print(" -", (t or "")[:80])
