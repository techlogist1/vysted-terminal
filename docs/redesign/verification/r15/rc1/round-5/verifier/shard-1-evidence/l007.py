import asyncio, os, json
from pathlib import Path
from services import searxng_manager as m
print("PATH=", os.environ.get("PATH"))
print("resolved:", m._resolve_docker_binary())
async def main():
    mgr = m.SearxngManager(config_dir=Path(os.environ["VYSTED_DATA_DIR"])/"searxng-cfg")
    p = await mgr.detect(); print("detect:", p)
    r = await mgr.refresh(); print("refresh:", json.dumps(r, default=str)[:600])
    print("pull-nonexistent:", await m._run_docker("pull", "searxng/searxng:vshard1-nonexistent-tag", timeout=40))
asyncio.run(main())
