#!/usr/bin/env python3
"""Render the R15 register's readable md view from its JSON (stdlib only, read-only).

The JSON is the record; the md is a regenerated view. After any edit to the JSON:

    python3 scripts/r15/render_register_md.py > docs/redesign/verification/vysted-r15-register.md

An optional first argument points at another register JSON (e.g. a `git show <sha>:...`
copy); output always goes to stdout. The output must stay byte-identical to the committed
md for an unchanged JSON -- check with `... | cmp - docs/redesign/verification/vysted-r15-register.md`.
"""

import json
import sys
from collections import Counter
from pathlib import Path

R = Path(__file__).resolve().parents[2] / "docs/redesign/verification"
d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else R / "vysted-r15-register.json"))
E = d["entries"]; c = d["counts"]
SEV = ["critical", "high", "medium", "low"]
AREAS = {"ui": "UI / panels / layout", "agent": "Agent / chat", "research": "Research / web search", "data": "Data on small or obscure stocks"}
by = {s: sum(1 for e in E if e.get("severity") == s) for s in SEV}
st = Counter(e.get("status") for e in E)
md = ["# R15 register (readable view)", "",
      f"{c['raw']} raw findings -> {len(E)} entries + {len(d['rejections'])} rejections. " + " . ".join(f"{s}: {by[s]}" for s in SEV), "",
      "Status: " + " . ".join(f"{k}: {st[k]}" for k in sorted(st)), "",
      "## The operator's four areas", ""]
for a, label in AREAS.items():
    rows = [e for e in E if e.get("area") == a]
    md += [f"### {label} ({len(rows)})", ""] + [f"- **{e['id']}** [{e.get('severity')}] {e.get('title')} — _{e.get('status')}_" for e in rows] + [""]
md += ["## All entries by severity", "", "| id | sev | area | subsystem | title | status | raw ids |", "|---|---|---|---|---|---|---|"]
for e in E:
    md.append(f"| {e['id']} | {e.get('severity')} | {e.get('area')} | {e.get('subsystem')} | {str(e.get('title')).replace('|', '/')} | {e.get('status')} | {', '.join(e.get('raw_ids') or [])} |")
sys.stdout.write("\n".join(md) + "\n")
