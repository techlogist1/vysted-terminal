T=$1; OUT=$2; mkdir -p $OUT; cd $T/sidecar
PY=/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/.venv/bin/python
D=/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/batch-23-verify/docs/redesign/verification/r15/stage-c
for p in batch-17/verifier-evidence/b17v_probe batch-17/verifier-evidence/b17v_probe2 batch-17/verifier-evidence/b17v_probe3 batch-18/verifier-evidence/b18v_probe batch-18/verifier-evidence/b18v_probe_b batch-18/verifier-evidence/b18v_probe_c batch-18/verifier-evidence/b18v_probe_d batch-20/writer-evidence/b20w_probe batch-20/verifier-evidence/b20v_fresh batch-21/verifier-evidence/b21v_fresh batch-21/verifier-evidence/b21v_fresh2 batch-21/verifier-evidence/b21v_unclosed batch-22/verifier-evidence/b22v_fresh batch-22/verifier-evidence/b22v_crossround batch-22/verifier-evidence/b22v_notool_fab; do
  n=$(basename $p); $PY $D/$p.py > $OUT/$n.out 2>&1; echo "$n exit=$?"
done
for a in "" 2 3; do $PY $D/batch-19/verifier-evidence/b19v_probe.py $a > $OUT/b19v_probe$a.out 2>&1; echo b19-$a $?; done
echo ALLDONE
