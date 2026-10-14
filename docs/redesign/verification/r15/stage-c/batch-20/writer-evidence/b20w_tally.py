"""batch-20 writer live tally: for every <tag>.jsonl beside this file, the tools called, their outcomes, the
figures the answer streamed and which of them the prompt does not carry. The event log carries no tool
payloads, so a figure of an ok turn is read against the tool's data by hand (see live-tally.md); after an
errored call with no ok result, any figure not in the prompt is a leak. Run with cwd=<tree>/sidecar."""
import json, sys
from pathlib import Path
sys.path.insert(0, ".")
from services import figure_grounding as fg
E = Path(__file__).resolve().parent
PROMPTS = {}
for line in (E / "b20w_live.py").read_text().splitlines():
    if line.strip().startswith('single("'):
        parts = line.strip()[len('single("'):].split('", "', 1)
        PROMPTS[parts[0]] = parts[1].split('"')[0] if len(parts) > 1 else ""
rows = []
for f in sorted(E.glob("*.jsonl")):
    tag = f.stem
    evs = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    text = "".join(e.get("text") or "" for e in evs if e.get("kind") == "delta")
    calls = [(e.get("name"), e.get("input")) for e in evs if e.get("kind") == "tool_use"]
    results = [(e.get("name"), e.get("ok"), e) for e in evs if e.get("kind") == "tool_result"]
    g = fg.Grounding()
    g.seed(PROMPTS.get(tag, ""))
    for _, _, e in results:
        payload = e.get("result") if e.get("result") is not None else e.get("content", e.get("data", ""))
        g.add_result(payload if isinstance(payload, str) else json.dumps(payload))
    figs = fg.figures(text)
    ungrounded = [x.text for x in figs if not g.grounded(x)]
    notes = text.count("returned no data for this in this turn") + text.count("no tool returned data")
    rows.append((tag, calls, [(n, ok) for n, ok, _ in results], len(figs), ungrounded, notes, "```" in text))
print("| tag | calls | results | figures | figures not in the prompt | notes | fence in answer |")
print("|---|---|---|---|---|---|---|")
for tag, calls, res, nfig, ungrounded, notes, fence in rows:
    print(f"| {tag} | {[c for c, _ in calls]} | {res} | {nfig} | {ungrounded} | {notes} | {fence} |")
