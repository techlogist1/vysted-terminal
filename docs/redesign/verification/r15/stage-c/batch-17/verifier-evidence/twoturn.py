import json, subprocess, sys
E="/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/stage-c/batch-17/verifier-evidence"
def run(tag, prompt, hist=None):
    cmd=["python3","scripts/r15/vy.py","invoke","copilot",prompt,"--port","52310","--provider","ollama","--model","llama3.1:8b","--autonomy","ask","--tag","b17v-lead030-2turn","--out",f"{E}/{tag}.jsonl","--timeout","600"]
    if hist: cmd += ["--options", json.dumps({"history": hist})]
    with open(f"{E}/{tag}.txt","w") as f: subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd="/Users/lokavyasingh/Documents/dev/vysted-terminal")
    evs=[json.loads(l) for l in open(f"{E}/{tag}.jsonl") if l.strip()]
    text="".join(e.get("delta") or e.get("text") or "" for e in evs if e.get("kind")=="delta")
    steps=[]
    for e in evs:
        if e.get("kind")=="tool_use":
            n=e["name"]; steps.append({"get_terminal_state":"Reading what you're looking at","get_portfolio":"Reading your portfolio"}.get(n, "Using "+n.replace("_"," ")))
    return text, steps
def twoturn(tag, q1, q2):
    t1, steps = run(tag+"-t1", q1)
    content = t1.strip() + ("\n\n[tool steps: " + "; ".join(steps) + "]" if steps else "")
    hist=[{"role":"user","content":q1},{"role":"assistant","content":content}]
    json.dump(hist, open(f"{E}/{tag}-history.json","w"), indent=1)
    run(tag+"-t2", q2, hist)
    print(tag, "done", steps, flush=True)
twoturn("followup-aapl", "What is AAPL's market cap?", "Which tool gave you that market cap figure? Show exactly what it returned.")
twoturn("followup-msft", "What is MSFT's latest price?", "Cite the tool that price came from and quote its result.")
twoturn("followup-aapl-2", "What is AAPL's market cap?", "Which tool gave you that market cap figure? Show exactly what it returned.")
print("ALLDONE")
