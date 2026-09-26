import asyncio, time
from services import symbol_resolver
from services.agent_tools import resolve_symbol as rs, fundamentals as fu
orig=symbol_resolver.resolve
async def ticker(stop):
    worst=0; last=time.monotonic()
    while not stop.is_set():
        await asyncio.sleep(0.01); now=time.monotonic(); worst=max(worst,now-last-0.01); last=now
    return worst
async def measure(coro_fn):
    stop=asyncio.Event(); t=asyncio.create_task(ticker(stop)); await asyncio.sleep(0.05)
    out=await coro_fn(); stop.set(); return out, await t
def slow(*a,**k): time.sleep(1.0); return orig(*a,**k)
def boom(*a,**k): raise RuntimeError("resolver exploded")
async def main():
    symbol_resolver.resolve=slow
    out,w=await measure(lambda: rs._resolve_symbol({"query":"tata steel"})); print('resolve_symbol slow: status',out.get('status'),'max loop lag %.3fs'%w)
    out,w=await measure(lambda: fu._canonicalize("TATASTEEL")); print('fundamentals._canonicalize slow: max loop lag %.3fs'%w, type(out).__name__)
    symbol_resolver.resolve=boom
    out=await rs._resolve_symbol({"query":"infosys"}); print('resolve_symbol raising ->', {k:out.get(k) for k in ('ok','status','reason')})
    out=await fu._canonicalize("INFY"); print('canonicalize raising ->', out)
asyncio.run(main())
