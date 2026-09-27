#!/bin/sh
B=http://127.0.0.1:52312
echo "HEAD $(git -C "$1" rev-parse HEAD) date $(date -u +%FT%TZ) sidecar :52312 (own, candidate source)"
p() { echo; echo "### POST /screener/run $1"; curl -s -m 90 -w '\n[HTTP %{http_code} %{time_total}s]\n' -X POST -H 'Content-Type: application/json' -d "$1" $B/screener/run | head -c 1800; echo; }
g() { echo; echo "### GET $1"; curl -s -m 30 -w '\n[HTTP %{http_code} %{time_total}s]\n' "$B$1" | head -c 1500; echo; }
g /screener/default-universe
p '{"universe":"custom","custom_symbols":["RELIANCE","TCS","INFY","HDFCBANK","COCHINSHIP"],"criteria":[],"limit":200,"sort_by":"market_cap","sort_dir":"desc"}'
p '{"universe":"nifty50","criteria":[],"formula":"pe < 20 and roe > 15%","limit":50,"sort_by":"market_cap","sort_dir":"desc"}'
p '{"universe":"nifty50","criteria":[{"field":"pe_ratio","operator":"gt","value":0},{"field":"pe_ratio","operator":"lt","value":0.5}],"limit":200,"sort_by":"market_cap","sort_dir":"desc"}'
for u in sp500 nifty50 crypto-top50 nse-all bse-all india-all; do echo "### universe $u"; curl -s -m 30 "$B/screener/universe?id=$u" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(len(d.get("symbols",[])), sorted(d.keys()))'; done
g /search/status
g /search/searxng/status
