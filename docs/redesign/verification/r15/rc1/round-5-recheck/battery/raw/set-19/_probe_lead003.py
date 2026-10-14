import sys, os, asyncio, sqlite3
sys.path.insert(0, "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-5-recheck-cand/sidecar")
os.environ["VYSTED_DATA_DIR"] = "/tmp/battery15work/lead003data"
from services import data_cache

async def main():
    from pathlib import Path
    data_cache.reset_for_tests(Path("/tmp/battery15work/lead003data") / "data_cache.db")
    # simulate a pre-fix build writing a row
    await data_cache.ensure_build("0.7.9")
    await data_cache.set("PREFIX-SYM:quote", {"stale": "pre-fix-row"})
    size_before = await data_cache.size()
    print(f"after pre-fix write: cache size={size_before}")
    row = data_cache._get_conn().execute("SELECT value FROM meta WHERE key='build'").fetchone()
    print(f"meta.build before upgrade: {row[0]}")

    # now "upgrade" to 0.8.0 (real app.version) and boot
    cleared = await data_cache.ensure_build("0.8.0")
    print(f"ensure_build('0.8.0') cleared={cleared}")
    size_after = await data_cache.size()
    print(f"after upgrade boot: cache size={size_after}")
    row2 = data_cache._get_conn().execute("SELECT value FROM meta WHERE key='build'").fetchone()
    print(f"meta.build after upgrade: {row2[0]}")

    # a boot at the same version should NOT clear
    await data_cache.set("KEEPME:quote", {"fresh": "post-fix-row"})
    cleared2 = await data_cache.ensure_build("0.8.0")
    size3 = await data_cache.size()
    print(f"ensure_build('0.8.0') again (same version) cleared={cleared2}, size={size3}")

    assert size_before == 1
    assert cleared is True
    assert size_after == 0, "cache must be cleared on a build change"
    assert cleared2 is False
    assert size3 == 1, "same-version boot must keep rows"
    print("PASS: cache cleared on build change, retained on same-version boot")

asyncio.run(main())
