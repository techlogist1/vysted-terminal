import re, sys
txt = open(sys.argv[1]).read()
blocks = txt.split("\n== ")[1:]
for b in blocks:
    lines = b.split("\n"); tag = lines[0]
    calls = next(l for l in lines if l.startswith("calls="))
    names = re.findall(r"\('(\w+)', \{", calls)
    res = next(l for l in lines if l.startswith("results="))
    import os; jf=os.path.join(os.path.dirname(sys.argv[1]),"live",tag+".jsonl"); st="STAGED" if os.path.exists(jf) and "Staged for your review" in open(jf).read() else "-"
    pos = re.search(r"db_positions=(\S+) audit_orders=(\S+)", b)
    body = b.split("\n---\n", 1)[1] if "\n---\n" in b else ""
    prices = re.findall(r"₹\s?[\d,]+(?:\.\d+)?", body)[:4]
    print(f"{tag:28} calls={names} ok={re.findall(r', (True|False),', res)} {st} dbpos={pos.group(1) if pos else '?'} audit={pos.group(2) if pos else '?'} prices={prices}")
