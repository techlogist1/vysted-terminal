#!/bin/bash
# usage: boot.sh mcp | boot.sh <base|deadhost|moved>   (main sidecar on :52226, MCP pair :53226/:53236)
set -u
REPO=/Users/lokavyasingh/Documents/dev/vysted-terminal
S=/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/vysted-iso/seat-l2-rot
H=$REPO/docs/redesign/verification/r15/lifecycle/L2-rot/harness
P=$1
if [ "$P" = mcp ]; then
  cd $REPO
  (sleep 86400 | src-tauri/binaries/vysted-openbb-mcp-sidecar-aarch64-apple-darwin --port 53226 > $S/openbb-mcp.log 2>&1 &)
  (sleep 86400 | src-tauri/binaries/vysted-sec-edgar-mcp-sidecar-aarch64-apple-darwin --port 53236 > $S/sec-edgar-mcp.log 2>&1 &)
  exit 0
fi
export VYSTED_OPENBB_MCP_PORT=53226 VYSTED_SEC_EDGAR_MCP_PORT=53236
cd $REPO/sidecar
case "$P" in
  base)
    (sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52226 --data-dir $S/data > $S/sidecar-base.log 2>&1 &) ;;
  deadhost)
    (sleep 86400 | ./.venv/bin/python3 $H/deadhost_proxy.py 52286 $S/proxy.jsonl nseindia.com > $S/proxy.log 2>&1 &)
    sleep 1
    export HTTPS_PROXY=http://127.0.0.1:52286 https_proxy=http://127.0.0.1:52286 NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost
    (sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52226 --data-dir $S/data > $S/sidecar-deadhost.log 2>&1 &) ;;
  moved)
    (sleep 86400 | env ROT_MOVED=1 ./.venv/bin/python3 $H/rot_main.py --host 127.0.0.1 --port 52226 --data-dir $S/data > $S/sidecar-moved.log 2>&1 &) ;;
esac
