import asyncio, json, sys, time
import config
from services.agent_tools import screener_tools
async def main(universe):
    tok = config.set_request_region("IN" if "india" in universe or "nifty" in universe else "US")
    t = time.monotonic()
    r = await screener_tools._screener_run({"universe": universe, "criteria": [{"field": "pe_ratio", "operator": "lt", "value": 15}]})
    body = r.get("result", {})
    print(f"{universe}: ok={r.get('ok')} {time.monotonic()-t:.0f}s bytes={len(json.dumps(r))} partial={body.get('partial')} evaluated={body.get('evaluated_count')} skip_summary={body.get('skip_summary')} examples={len(body.get('skip_examples') or [])} has_skip_details={'skip_details' in body} err={r.get('error','')[:200]}")
asyncio.run(main(sys.argv[1]))
