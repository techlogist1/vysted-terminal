"""Per-run digest of a live-<SET>.out: tag, calls, staged host writes, positions, and the reply."""
import re, sys
for blk in open(sys.argv[1]).read().split("\n== ")[1:]:
    head, _, body = blk.partition("\n---\n")
    L = head.splitlines(); tag = L[0]
    g = lambda k: next((l[len(k)+1:] for l in L if l.startswith(k + "=")), "")
    pos = head.split("positions=")[-1].replace("HTTP 200", "").strip()
    body = body.replace("ALLDONE", "").strip()
    print(f"### {tag} | calls={g('calls')[:200]} | results={g('results')[:160]} | staged={g('staged_host_writes')} | pos={pos}\n{body}\n")
