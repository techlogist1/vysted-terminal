#!/bin/bash
# boot.sh <profile> — (re)start MY main sidecar on :52224 with an induced-failure env profile.
# profiles: base | netdown | nodocker | junk  (junk stub must already run on :52294)
set -u
REPO=/Users/lokavyasingh/Documents/dev/vysted-terminal
ISO=/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/vysted-iso
SEAT=$ISO/seat-failure-inducer
PIDS=$SEAT/pids.json
PORT=52224
prof=$1
# stop my previous main (only the sleep I recorded)
if [ -f $SEAT/main.sleep.pid ]; then kill $(cat $SEAT/main.sleep.pid) 2>/dev/null; sleep 3; fi
for i in $(seq 1 20); do lsof -nP -iTCP:$PORT -sTCP:LISTEN -t >/dev/null || break; sleep 0.5; done
cd $REPO/sidecar
ENVV=(VYSTED_OPENBB_MCP_PORT=53224 VYSTED_SEC_EDGAR_MCP_PORT=53234)
case $prof in
  base) ;;
  netdown) ENVV+=(HTTPS_PROXY=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9 ALL_PROXY=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9 http_proxy=http://127.0.0.1:9 all_proxy=http://127.0.0.1:9 NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost) ;;
  nodocker) ENVV+=(PATH=/usr/bin:/bin:/usr/sbin:/sbin) ;;
  junk) ENVV+=(OPENAI_BASE_URL=http://127.0.0.1:52294/v1 OLLAMA_HOST=http://127.0.0.1:52294) ;;
  *) echo "bad profile"; exit 2;;
esac
LOG=$SEAT/sidecar-$prof.log
( exec env "${ENVV[@]}" bash -c "sleep 86400 | exec ./.venv/bin/python3 main.py --host 127.0.0.1 --port $PORT --data-dir '$SEAT/data'" > $LOG 2>&1 & )
for i in $(seq 1 60); do curl -s -m 2 127.0.0.1:$PORT/health >/dev/null && break; sleep 0.5; done
SPID=$(pgrep -f "^sleep 86400$" -n)
WPID=$(lsof -nP -iTCP:$PORT -sTCP:LISTEN -t | head -1)
# find the sleep feeding this worker: same parent bash
PPIDW=$(ps -o ppid= -p $WPID | tr -d ' ')
SPID=$(pgrep -P $PPIDW sleep | head -1)
echo $SPID > $SEAT/main.sleep.pid
echo "{\"profile\":\"$prof\",\"main_sleep\":$SPID,\"main_worker\":$WPID,\"port\":$PORT,\"log\":\"$LOG\"}"
curl -s 127.0.0.1:$PORT/health | head -c 600; echo
