import json, sys, os
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import lows_spec as m
r = json.load(open(os.path.join(here, "lows-vt.json")))
root = os.path.abspath(os.path.join(here, *[".."] * 8))
byfile = {}
for f in r["testResults"]:
    byfile[os.path.relpath(f["name"], root)] = f
print("vitest totals:", r["numTotalTests"], "passed", r["numPassedTests"], "failed", r["numFailedTests"], "files", r["numTotalTestSuites"], "success", r["success"])
fails, ok = [], 0
for e, k, f, n in m.S:
    if k != "vt":
        continue
    fr = byfile.get(f)
    if fr is None:
        fails.append((e, f, n, "file not in run")); continue
    A = fr["assertionResults"]
    if n is None:
        sel = A
    elif n.startswith("D:*"):
        sel = [a for a in A if any(n[3:].lower() in t.lower() for t in a["ancestorTitles"])]
    elif n.startswith("D:"):
        sel = [a for a in A if n[2:] in a["ancestorTitles"]]
    elif n.startswith("P:"):
        p = n[2:]
        sel = [a for a in A if a["title"].startswith(p) or " > ".join(a["ancestorTitles"] + [a["title"]]).startswith(p)]
    else:
        sel = [a for a in A if a["title"] == n or " > ".join(a["ancestorTitles"] + [a["title"]]) == n]
    st = [a["status"] for a in sel]
    if not sel:
        fails.append((e, f, n, "no matching test")); continue
    if any(s != "passed" for s in st):
        fails.append((e, f, n, "status " + ",".join(st))); continue
    ok += 1
    print(f"PASS {e:24} {f}::{n or '(file)'} [{len(sel)} test(s)]")
print("vitest specs passed:", ok, "failed:", len(fails))
for x in fails: print("FAIL", x)
