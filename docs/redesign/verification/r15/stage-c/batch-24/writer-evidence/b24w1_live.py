"""batch-24 W1 live bar (R15-LEAD-035): source sidecar from the writer tree on :52350,
llama3.1:8b via ollama, keyless, agent mode, autonomy ask. Pattern reused from
batch-23 W1's b23w_live.py. Transcripts land in live/ beside this file as
<tag>.jsonl (events) + .txt (client log)."""

import json
import subprocess
import sys
from pathlib import Path

E = Path(__file__).resolve().parent / "live"
TREE = Path(__file__).resolve().parents[7]
PY = "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/.venv/bin/python"
VY = [PY, "scripts/r15/vy.py"]


def get(path):
    r = subprocess.run(
        VY + ["get", path, "--port", "52350"], capture_output=True, text=True, cwd=TREE
    )
    return r.stdout.strip()[:400]


def run(tag, prompt):
    E.mkdir(exist_ok=True)
    cmd = VY + [
        "invoke",
        "copilot",
        prompt,
        "--port",
        "52350",
        "--provider",
        "ollama",
        "--model",
        "llama3.1:8b",
        "--mode",
        "agent",
        "--autonomy",
        "ask",
        "--no-key",
        "--tag",
        "b24w1",
        "--out",
        f"{E}/{tag}.jsonl",
        "--timeout",
        "600",
    ]
    with open(f"{E}/{tag}.txt", "w") as f:
        subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=TREE)
    evs = [json.loads(l) for l in open(f"{E}/{tag}.jsonl") if l.strip()]
    text = "".join(e.get("text") or "" for e in evs if e.get("kind") == "delta")
    calls = [(e["name"], e.get("input")) for e in evs if e.get("kind") == "tool_use"]
    res = [
        (e.get("name"), e.get("ok"), str(e.get("error") or "")[:100])
        for e in evs
        if e.get("kind") == "tool_result"
    ]
    other = sorted({e.get("kind") for e in evs} - {"delta", "tool_use", "tool_result"})
    print(
        f"== {tag}\nprompt={prompt!r}\ncalls={calls}\nresults={res}\nkinds={other}\n"
        f"positions_after={get('/portfolio/positions')}\n---\n{text}\n",
        flush=True,
    )
    return text


# The 7 explicit data requests the shipping cue over-matched (batch-23
# verifier-evidence/disposition/dv_prompts.OVER) -- each x3, must call price_data and
# state the /quotes price.
OVER = [
    ("o-never-said", "I never said don't use tools — get RELIANCE.NS price."),
    ("o-other-than", "Don't use any tools other than price data: TCS.NS close?"),
    ("o-but-do-fetch", "Don't use tools for the math, but do fetch the TCS.NS price."),
    ("o-except", "No tools except price_data for TCS.NS"),
    ("o-dont-need", "Don't use tools you don't need; get the ITC.NS price."),
    ("o-twice", "Don't call tools twice — what is HDFCBANK.NS at?"),
    ("o-web", "Do not use tools from the web, only the quote: WIPRO.NS price?"),
]
# The literal register repro -- x2, must make no tool call and stage nothing.
REPRO = (
    "I sold 5 TCS shares at ₹3,100 each. Without calling any tool, restate my sale "
    "price and my total proceeds."
)

print(
    f"quotes RELIANCE.NS={get('/quotes/RELIANCE.NS')}\nquotes TCS.NS={get('/quotes/TCS.NS')}\n"
    f"quotes ITC.NS={get('/quotes/ITC.NS')}\nquotes HDFCBANK.NS={get('/quotes/HDFCBANK.NS')}\n"
    f"quotes WIPRO.NS={get('/quotes/WIPRO.NS')}\npositions_before={get('/portfolio/positions')}\n",
    flush=True,
)

only = sys.argv[1:]
for tag, q in OVER:
    for n in (1, 2, 3):
        full_tag = f"{tag}.r{n}"
        if not only or tag in only or full_tag in only:
            run(full_tag, q)
for n in (1, 2):
    full_tag = f"repro.r{n}"
    if not only or "repro" in only or full_tag in only:
        run(full_tag, REPRO)

print("ALLDONE", flush=True)
