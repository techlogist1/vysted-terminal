import asyncio, httpx, sys
sys.path.insert(0,'.')
from services import news_provider as n
RSS=b"""<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>
<item><title>Old dated story</title><link>https://ex.com/a</link><pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate></item>
<item><title>Undated story about INFY</title><link>https://ex.com/b</link></item>
<item><title>Garbage-date story</title><link>https://ex.com/c</link><pubDate>yesterday-ish</pubDate></item>
<item><title>Recent dated story</title><link>https://ex.com/d</link><pubDate>Fri, 25 Sep 2026 10:00:00 GMT</pubDate></item>
</channel></rss>"""
API={"articles":[{"title":"NewsAPI no date","url":"https://ex.com/e"},{"title":"NewsAPI bad date","url":"https://ex.com/f","publishedAt":"2026-13-45"}]}
def h(req):
    if "newsapi" in str(req.url): return httpx.Response(200,json=API)
    return httpx.Response(200,content=RSS)
async def main():
    async with httpx.AsyncClient(transport=httpx.MockTransport(h)) as c:
        items=await n.fetch_news(c,["INFY"],50,newsapi_key="dummy")
        seen=[]
        for i in items:
            if i.title in seen: continue
            seen.append(i.title); print(repr(i.title), i.published_at)
        sc=n.enrich(items,["INFY"],{}) if True else None
        print("enrich ok", len(sc))
asyncio.run(main())
