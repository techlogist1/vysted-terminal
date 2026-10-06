# final-drive-screener — attachments (head d38b5d1a)

## R15-LEAD-069 (open) — boolean operand in a comparison still validates

Command: `curl -X POST http://127.0.0.1:52800/screener/formula/validate -H "Origin: http://localhost:5173" -d {"formula": ...}` (full table: 09-formula-validate.txt)
```
min(pe<5,roe)>0.5	{"ok":false,"error":"min() needs a numeric argument, not a boolean expression — wrap the comparison on its own, or combine with 'and'/'or'","position":3,"fields":[]}
pe_ratio + (roe > 0.1) > 5	{"ok":false,"error":"a boolean expression can't be used in arithmetic — wrap the comparison on its own, or combine with 'and'/'or'","position":9,"fields":[]}
roe > (pe_ratio < 15)	{"ok":true,"error":null,"position":null,"fields":["pe_ratio","roe"]}
```
Arithmetic/min() coercion is rejected (R15-RESEARCH-025 holds) but a comparison with a boolean operand is still ok:true — same mechanism as LEAD-069's repro.

## R15-LEAD-076 (open) — partially throttled 0-match run blames the filters

Command: `python3 surface/screener/harness/scr.py 23-partial-throttle-zero '{"universe":"bse-all","criteria":[{"field":"pe_ratio","operator":"between","value":{"min":0,"max":0.01}}],"limit":200,"sort_by":"market_cap","sort_dir":"desc"}' --port 52842 --out runs.jsonl` (runs.jsonl line 19)
```
{'evaluated_count': 1676, 'skipped_count': 3366, 'result_count': 0, 'partial': True, 'throttled': True, 'coverage': 'screened 1,676 of 5,042 — 3,366 unavailable'} {'rate_limited': 2579, 'missing_field:pe_ratio': 787}
```
Render branch (evaluated_count>0, rows==0) at /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/final-cand/src/modules/screener/ScreenerResultsTable.tsx:547-552:
```
        ) : rows.length === 0 ? (
          <EmptyState
            icon={FilterX}
            headline="No rows matched the criteria"
            hint="No stocks in this universe passed every filter. Loosen a threshold or reset to the defaults."
            cta={{ label: "Reset filters", onClick: () => resetCriteria() }}
```
2,579 of 5,042 symbols were rate-limited, yet the empty state says no stock passed every filter and offers Reset filters. Same mechanism as LEAD-076.
