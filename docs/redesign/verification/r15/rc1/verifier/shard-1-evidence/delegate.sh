#!/bin/sh
# usage: delegate.sh <agent> <prompt> <out>
OUT=$3
python3 -c "import json,sys; print(json.dumps({'prompt':sys.argv[1],'provider':'ollama','model':'llama3.1:8b','budget':{}}))" "$2" > $OUT.req.json
R=$(curl -s -m 30 -X POST "http://127.0.0.1:52601/agents/$1/runs" -H 'Content-Type: application/json' -H 'X-Vysted-Region: IN' --data @$OUT.req.json)
echo "LAUNCH $R" > $OUT
ID=$(echo "$R" | python3 -c "import json,sys; print(json.load(sys.stdin).get('runId',''))")
i=0
while [ $i -lt 180 ]; do
  sleep 5; i=$((i+1))
  curl -s -m 20 "http://127.0.0.1:52601/runs/$ID" > $OUT.run.json
  st=$(python3 -c "import json; d=json.load(open('$OUT.run.json')); print(d.get('status'))")
  echo "[$((i*5))s] $st" >> $OUT
  case "$st" in done|error|paused|cancelled|aborted|planned) break;; esac
done
echo DONE >> $OUT
