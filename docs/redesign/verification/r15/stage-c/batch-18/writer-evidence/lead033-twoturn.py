import json, subprocess

W = "/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_ea0144f4-04a-3"
E = f"{W}/docs/redesign/verification/r15/stage-c/batch-18/writer-evidence"
LABELS = {"get_terminal_state": "Reading what you're looking at", "get_portfolio": "Reading your portfolio"}


def run(tag, prompt, hist=None):
    cmd = ["python3", "scripts/r15/vy.py", "invoke", "copilot", prompt, "--port", "52377",
           "--provider", "ollama", "--model", "llama3.1:8b", "--autonomy", "ask",
           "--tag", "b18w1-lead033", "--out", f"{E}/{tag}.jsonl", "--timeout", "600"]
    if hist:
        cmd += ["--options", json.dumps({"history": hist})]
    with open(f"{E}/{tag}.txt", "w") as f:
        subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=W)
    evs = [json.loads(l) for l in open(f"{E}/{tag}.jsonl") if l.strip()]
    text = "".join(e.get("delta") or e.get("text") or "" for e in evs if e.get("kind") == "delta")
    steps = [LABELS.get(e["name"], "Using " + e["name"].replace("_", " "))
             for e in evs if e.get("kind") == "tool_use"]
    return text, steps


def twoturn(tag, q1, q2):
    t1, steps = run(tag + "-t1", q1)
    # historyForSend/withTrailer: trimmed content, then "\n\n[tool steps: a; b]"
    content = "\n\n".join(x for x in [t1.strip(), "[tool steps: " + "; ".join(steps) + "]" if steps else ""] if x)
    hist = [{"role": "user", "content": q1}, {"role": "assistant", "content": content}]
    json.dump(hist, open(f"{E}/{tag}-history.json", "w"), indent=1)
    t2, steps2 = run(tag + "-t2", q2, hist)
    print(tag, "t1 steps", steps, "| t2 steps", steps2, "| t2 has '[tool steps':", "[tool steps" in t2, flush=True)
    print("T1:", t1[:400].replace("\n", " "), flush=True)
    print("T2:", t2[:600].replace("\n", " "), flush=True)


twoturn("lead033-1", "What is AAPL's market cap?", "Which tool gave you that market cap figure? Show exactly what it returned.")
twoturn("lead033-2", "What is MSFT's latest price?", "Cite the tool that price came from and quote its result.")
twoturn("lead033-3", "What is NVDA's P/E ratio?", "Which tool did you use for that figure? Answer from this chat, without calling a tool.")
print("ALLDONE", flush=True)
