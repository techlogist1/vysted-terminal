"""LEAD-037 offline (cwd=<tree>/sidecar @014bb7f1): does the guard ever check a figure for the subject a call
returned ok for? Payload: the current quote 983.0 plus two older bars (1082.0, 1035.1), as price_data returns."""
exec(open("/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/stage-c/batch-22/verifier-evidence/b22v_fresh.py").read().split("OK_SBI =")[0])
OK_SBIN = {"ok": True, "symbol": "SBIN.NS", "quote": {"price": 983.0, "change": 4.5}, "bars": [
    {"timestamp": "2026-06-19T00:00:00Z", "close": 1035.1}, {"timestamp": "2026-08-12T00:00:00Z", "close": 1082.0},
    {"timestamp": "2026-09-25T00:00:00Z", "close": 983.0}]}
def ok(tag, text, forb, must=""):
    return (tag, [[call("price_data", symbol="SBIN.NS"), DONE], [*d(text)]], {"price_data": OK_SBIN}, must, forb)
def err(tag, text, forb, must=""):
    return (tag, [[call("price_data", symbol="SBIN.NS"), call("quote", symbol="WIPRO.NS"), DONE], [*d(text)]], {"price_data": OK_SBIN, "quote": ERR}, must, forb)
CASES = [
 ok("s-stale-bar-as-current", "The latest price of SBI is ₹1082.0.\n", ["1082.0"]),          # LEAD-037 as filed (in payload)
 ok("s-stale-bar-2", "SBIN.NS is trading at ₹1,035.10 right now.\n", ["1,035.10"]),
 ok("s-invented-10x-allok", "The current price of SBIN.NS is ₹9,830.\n", ["9,830"]),          # not in payload
 ok("s-invented-allok", "SBIN.NS last traded at ₹1,210.40.\n", ["1,210.40"]),                   # not in payload
 err("s-invented-errturn", "SBIN.NS last traded at ₹1,210.40.\n", ["1,210.40"]),               # same, a call errored
 ok("t-true-current", "SBIN.NS last traded at ₹983.00.\n", [], "983.00"),                       # control
]
async def main():
    for name, rounds, results, must, forb in CASES:
        try: out = await run(rounds, results)
        except Exception as ex: print(f"ERR  {name}: {ex!r}"); continue
        leak = any(f in out for f in forb)
        print(("STREAMS " if leak else ("MISSING " if must and must not in out else "HELD    ")) + f"{name}: " + json.dumps(out, ensure_ascii=False)[:220])
asyncio.run(main())
