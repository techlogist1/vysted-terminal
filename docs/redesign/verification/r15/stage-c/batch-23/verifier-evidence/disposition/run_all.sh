#!/bin/sh
P=/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/.venv/bin/python
cd "$(dirname "$0")"
for s in L38 OVER MISS KEEP L37; do $P dv_live.py $s 3 > live-$s.out 2>&1; echo "$s exit=$?"; done
echo RUNALL_DONE
