import asyncio, time
from services.search.brave import BraveSearchBackend
async def main():
    t=time.monotonic()
    try:
        r=await BraveSearchBackend().search('Dixon Technologies')
        print('ok rows',len(r.results),'%.1fs'%(time.monotonic()-t))
    except Exception as e:
        print('ERR',type(e).__name__,str(e)[:200],'%.1fs'%(time.monotonic()-t))
asyncio.run(main())
