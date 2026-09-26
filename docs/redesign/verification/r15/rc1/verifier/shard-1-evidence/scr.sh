# usage scr.sh <label> <json>
curl -s -m 590 -X POST http://127.0.0.1:52601/screener/run -H 'Content-Type: application/json' -H 'X-Vysted-Region: IN' --data "$2" > /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/vshard1r2/scr-$1.json
python3 - "$1" <<'PY'
import json,sys,collections
d=json.load(open(f'/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/vshard1r2/scr-{sys.argv[1]}.json'))
if 'rows' not in d: print(sys.argv[1], str(d)[:600]); sys.exit()
keep={k:v for k,v in d.items() if not isinstance(v,(list,dict))}
print(sys.argv[1], keep)
for k,v in d.items():
    if isinstance(v,dict): print('  ',k, str(v)[:400])
    elif k!='rows' and isinstance(v,list): print('  ',k, str(v)[:400])
print('   first rows', [(r.get('symbol'), r.get('pe_ratio'), r.get('market_cap')) for r in d['rows'][:5]])
PY
