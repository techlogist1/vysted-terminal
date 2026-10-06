"""batch-22 verifier: a fence opened in the round before an errored call encloses the next round's dump. cwd=<tree>/sidecar."""
exec(open(__file__.replace("b22v_crossround.py", "b22v_fresh.py")).read().split("OK_SBI =")[0])
async def main():
    for tag, fence in (("backtick", "```"), ("tilde", "~~~")):
        out = await run([[*d(f"Let me fetch that.\n\n{fence}\n"), call("price_data", symbol="WIPRO.NS"), DONE], [*d("* The latest close of Wipro is ₹248.15.\n* The latest close of HCL Technologies is ₹1,512.40.\n")]], {"price_data": ERR}, prompt="Latest closes of Wipro and HCL Technologies as bullets.")
        leak = any(x in out for x in ("248.15", "1,512.40"))
        print(f"{tag}: leak={leak} orphan_fence={fence in out} -> {out!r}")
asyncio.run(main())
