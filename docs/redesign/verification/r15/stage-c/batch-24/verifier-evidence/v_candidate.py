"""Scratch only: does a further narrowing-only qualifier guard clear the residual comma/'says' over-strips
without losing a correct strip? Not committed, not a fix."""
import re, subprocess, sys
S = sys.argv[1]
sys.path.insert(0, f"{S}/batch-24-verify/sidecar")
from services import planner as INT
p = INT._NO_TOOL_CUE.pattern
cand = re.compile(p.replace("(?<!said )(?<!say )", "(?<!said )(?<!say )(?<!says )", 1)
                  .replace(")(?=\\s*(?:$", r")(?!\s*,?\s*(?:except|other than|besides|apart from|beyond|unless)\b)(?=\s*(?:$", 1))
rows = [l for l in open(f"{S}/b24v/v-regex.out") if l.startswith("[")]
bad = 0
for l in rows:
    m = re.match(r"\[(\S+)\s*\] want_strip=(\S+)\s+base=(\S+)\s+int=(\S+).*? \| (.*)$", l.rstrip("\n"))
    src, want, b, i, q = m.group(1), m.group(2) == "True", m.group(3) == "True", m.group(4) == "True", m.group(5)
    c = bool(cand.search(q.strip().lower()))
    assert not (c and not i), q
    if c != i: print(f"changed vs int: want={want} int={i} cand={c} | {q}")
    if c != want and (want and i): bad += 1; print("LOST", q)
print("lost correct strips vs int:", bad)
