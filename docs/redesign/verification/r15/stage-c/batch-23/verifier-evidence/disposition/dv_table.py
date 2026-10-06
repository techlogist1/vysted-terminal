"""Compact per-run table from a live-<SET>.out: tag, tools called (ok/err), staged host writes, raw call-JSON text."""
import ast, sys
for blk in open(sys.argv[1]).read().split("\n== ")[1:]:
    head, _, body = blk.partition("\n---\n"); L = head.splitlines()
    g = lambda k: next((l[len(k)+1:] for l in L if l.startswith(k + "=")), "[]")
    res = ast.literal_eval(g("results")); st = ast.literal_eval(g("staged_host_writes"))
    calls = ",".join(f"{n}:{'ok' if ok else 'ERR'}" for n, ok, _ in res) or "-"
    raw = "RAW-CALL-JSON" if body.strip().startswith('{"name"') else ""
    print(f"{L[0]:32} calls={calls:60} staged={','.join(st) or '-':28} {raw}")
