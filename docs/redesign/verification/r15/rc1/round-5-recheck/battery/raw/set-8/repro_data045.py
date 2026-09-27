import asyncio, sys
sys.path.insert(0, ".")
from services.search.extract import fetch_page

CANARY_URL = "http://127.0.0.1:18765/latest/meta-data/"
REDIRECTOR = f"https://httpbin.org/redirect-to?url={CANARY_URL}"
CONTROL = "https://httpbin.org/redirect-to?url=https://example.com"

async def main():
    print("--- SSRF case: public -> loopback redirect ---")
    try:
        result = await fetch_page(REDIRECTOR)
        print("fetch_page result:", result)
    except Exception as e:
        print(f"fetch_page raised {type(e).__name__}: {e}")

    print("--- control case: public -> public redirect ---")
    try:
        result = await fetch_page(CONTROL)
        ok = result is not None and "content" in result
        print("control fetch ok:", ok, "keys:", list(result.keys()) if isinstance(result, dict) else type(result))
    except Exception as e:
        print(f"control raised {type(e).__name__}: {e}")

asyncio.run(main())
