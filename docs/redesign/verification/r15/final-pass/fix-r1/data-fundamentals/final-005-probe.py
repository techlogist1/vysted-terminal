import asyncio
import json

from services import exchange_financials, symbol_resolver


async def main():
    out = {}
    for sym in ["YASHOPTICS.NS", "YASHOPTICS-SM.NS", "SUMAX.NS"]:
        bare = sym.split(".")[0].removesuffix("-SM")
        try:
            print("emerge", sym, symbol_resolver.is_nse_emerge(bare), flush=True)
        except Exception as e:
            print("emerge err", e)
        fp = await exchange_financials.get_filed_periods(sym)
        if fp is None:
            out[sym] = None
        else:
            out[sym] = {
                "venue": fp.venue,
                "basis": fp.basis,
                "cadence": fp.cadence(),
                "trailing": [str(p.end) for p in (fp.trailing() or [])],
                "periods": [
                    {"start": str(p.start), "end": str(p.end), "revenue": p.revenue,
                     "net_profit": p.net_profit, "eps": p.eps, "url": p.url}
                    for p in fp.periods
                ],
            }
        print(sym, json.dumps(out[sym], indent=1), flush=True)
    try:
        from services import nse_provider
        rows = nse_provider.get_financial_filings("YASHOPTICS")
        print("raw filings rows", len(rows), json.dumps(rows[:3], indent=1, default=str))
    except Exception as e:
        print("raw filings err", type(e).__name__, e)


asyncio.run(main())
