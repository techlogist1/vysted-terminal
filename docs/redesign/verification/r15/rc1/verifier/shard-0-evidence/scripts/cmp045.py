import asyncio, json, sys
sys.path.insert(0, '.')
import config
from services.agent_tools.compare_symbols import _compare_symbols
async def main():
    for syms in (["COCHINSHIP","MAZAGONDOCK"], ["Cochin Shipyard","Mazagon Dock"], ["COCHINSHIP","GARDENREACH"], ["BHARATELECTRONICS","HINDAERO"], ["COCHINSHIP","ZZQXNOTREAL"]):
        r = await _compare_symbols({"symbols": syms})
        print("==", syms, "ok=", r.get("ok"))
        for s in r.get("symbols", []):
            print("   ", {k: s.get(k) for k in ("symbol","requested","note","error","provider")}, (s.get("quote") or {}).get("price"))
        if not r.get("ok"): print("   msg:", r.get("message","")[:300])
asyncio.run(main())
