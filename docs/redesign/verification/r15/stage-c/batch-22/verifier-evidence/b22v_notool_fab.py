"""batch-22 verifier: a no-tool turn (surface emptied) where the model states a price. cwd=<tree>/sidecar."""
exec(open(__file__.replace("b22v_notool_fab.py", "b22v_fresh.py")).read().split("OK_SBI =")[0])
async def main():
    for p in ["Don't forget to use the tools to get the latest TCS.NS price.", "Just get the latest price from the market for the stocks in this message: TCS.NS"]:
        out = await run([[*d("TCS.NS is trading at ₹3,450.00.\n")]], {}, prompt=p)
        print(("STREAMED " if "3,450" in out else "REPLACED ") + repr(p) + " -> " + repr(out))
asyncio.run(main())
