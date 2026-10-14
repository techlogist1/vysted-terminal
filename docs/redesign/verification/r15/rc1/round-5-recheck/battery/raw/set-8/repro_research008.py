import asyncio, sys, time
sys.path.insert(0, ".")
from services.search.ddg import DdgSearchBackend
from services.search.brave import BraveSearchBackend
from services.search.mojeek import MojeekSearchBackend
from services.search.keyless import KeylessSearchBackend

async def main():
    for name, cls in [("ddg", DdgSearchBackend), ("brave", BraveSearchBackend), ("mojeek", MojeekSearchBackend)]:
        eng = cls()
        t0 = time.monotonic()
        try:
            resp = await eng.search("Dixon Technologies recent news")
            dt = time.monotonic() - t0
            print(f"{name}: OK in {dt:.1f}s, results={len(resp.results) if resp and resp.results else 0}")
        except Exception as e:
            dt = time.monotonic() - t0
            print(f"{name}: FAIL in {dt:.1f}s ({type(e).__name__}: {e})")

    rot = KeylessSearchBackend()
    t0 = time.monotonic()
    try:
        resp = await asyncio.wait_for(rot.search("Dixon Technologies recent news"), timeout=25.0)
        dt = time.monotonic() - t0
        print(f"rotation: OK in {dt:.1f}s (< 25s cap), results={len(resp.results) if resp and resp.results else 0}")
    except asyncio.TimeoutError:
        dt = time.monotonic() - t0
        print(f"rotation: TIMED OUT at {dt:.1f}s (>= 25s cap)")
    except Exception as e:
        dt = time.monotonic() - t0
        print(f"rotation: FAIL in {dt:.1f}s ({type(e).__name__}: {e})")

asyncio.run(main())
