import asyncio, json, httpx
from services import news_provider
from services.agent_tools import market_overview as mo
from services.provider_registry import ProviderError
from services import provider_registry as pr
from models.market import Quote
async def fake_quote(*a, **k): raise ProviderError("stub offline")
async def run(label, exc):
    async def boom(client, symbols, limit): raise exc
    news_provider.fetch_news = boom
    r = await mo._market_overview({"region": "US"})
    print(label, "ok=", r.get("ok"), "headlines=", r.get("headlines"), "headlines_error=", r.get("headlines_error"), "indices=", len(r.get("indices", [])), "error=", r.get("error"))
asyncio.run(run("literal ProviderError('all news sources failed'):", ProviderError("all news sources failed")))
asyncio.run(run("fresh httpx.ReadTimeout:", httpx.ReadTimeout("t")))
