import asyncio, sys, json
sys.path.insert(0, ".")
import services.agent_tools.compare_symbols as cs

async def main():
    result = await cs._compare_symbols({"symbols": ["Cochin Shipyard", "Mazagon Dock"]})
    print(json.dumps(result, indent=2, default=str)[:2500])

asyncio.run(main())
