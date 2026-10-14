#!/bin/sh
S=/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/vshard1-r5
RID=$(curl -s -m20 -X POST localhost:52601/agents/copilot/runs -H 'content-type: application/json' -d '{"prompt":"Research INFY: give me a detailed multi-paragraph summary of its valuation, recent news, and risks.","provider":"ollama","model":"llama3.1:8b"}' | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("runId") or d)')
echo "RID=$RID"
i=0
while [ $i -lt 120 ]; do
  st=$(curl -s -m10 localhost:52601/runs/$RID | python3 -c 'import sys,json;print(json.load(sys.stdin).get("status"))')
  echo "$(date +%T) $st"
  case "$st" in ok|done|completed|error|cancelled|failed|succeeded) break;; esac
  i=$((i+1)); sleep 10
done
curl -s -m10 localhost:52601/runs/$RID > $S/a013-run.json
echo END
