import asyncio, httpx
from services import news_provider as n
RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>
<item><title>Old dated</title><link>https://x/1</link><pubDate>Mon, 21 Sep 2026 10:00:00 GMT</pubDate></item>
<item><title>Undated headline</title><link>https://x/2</link></item>
<item><title>Garbage date</title><link>https://x/3</link><pubDate>not a date at all</pubDate></item>
<item><title>Newest dated</title><link>https://x/4</link><pubDate>Fri, 25 Sep 2026 10:00:00 GMT</pubDate></item>
</channel></rss>"""
async def main():
    t = httpx.MockTransport(lambda req: httpx.Response(200, text=RSS, headers={"content-type":"application/rss+xml"}))
    async with httpx.AsyncClient(transport=t) as c:
        items = await n.fetch_rss(c, "https://feed.example/rss", fallback_source="ex")
    for i in items: print(i.title, i.published_at)
asyncio.run(main())
