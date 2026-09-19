# R15 worker rules (read fully, obey exactly)

**Context.** You are a worker in the R15 "LAUNCH" autonomous run on the Vysted Terminal repo
(`/Users/lokavyasingh/Documents/dev/vysted-terminal`, branch `004-r4-experience-rebuild`): an
open-source, BYOK, local-first, agent-native desktop finance terminal for Indian markets —
"Jarvis, if Tony Stark built a finance app". Benchmarks: Perplexity Finance for research,
screener.in for data (any listed stock, however obscure, returns complete, accurate, dense
data). The moat is data trust, research quality and a finance-tuned agent — not the model.
Stage 1 is the CENSUS: find everything wrong, missing, rotten or merely mediocre. A lead
orchestrates; you do one bounded job and return.

**Hard rules.**

- The operator is AT the machine. NO GUI interaction of any kind: no clicks, keystrokes,
  screenshots, `screencapture`, `osascript` UI events, no opening apps or visible browser
  windows. Headless only.
- Do not start, stop or kill any process you did not start yourself. The operator's live app
  (vite `:5173` and the sidecars it spawned) is HIS session: never POST to it, never restart it.
- An ISOLATED headless sidecar for this run is at `http://127.0.0.1:52152` (a copy of his data
  dir; safe to drive with GET/POST). If your task says you may start your OWN sidecar, run it
  from source exactly like this, on the port you were given, and stop it (kill the `sleep`)
  when done:
  `cd sidecar && (sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port <PORT> --data-dir <YOUR_DIR> > <LOG> 2>&1 &)`
  (stdin must stay open or the sidecar exits instantly). Always pass `--data-dir`.
- LLM-backed drives go ONLY through `scripts/r15/vy.py` (it reads the key in-process, never
  prints it, logs every call to the spend ledger and enforces the budget cap). Never read,
  print or copy `dev-keystore.json` yourself. Default model = the free lane. Always pass
  `--provider` explicitly (a provider-less invoke cold-loads a 4 GB local model).
- No full pytest / cargo / PyInstaller / production builds (single heavy lane, lead-owned). One
  targeted test file is fine when it settles a claim
  (`sidecar/.venv/bin/python -m pytest <file> -q`, `pnpm exec vitest run <file>`).
- Never print, log or write a secret. Never touch the operator's other products on this Mac.
- Never speculate about code you have not opened: `file:line` for every code claim, URL +
  quote for every world claim.
- WRITE YOUR OUTPUT FILE(S) AS YOU GO. If one already exists, a previous attempt died when the
  machine lost power — continue from it, do not restart.
- Shell: `cat` is aliased to `bat` and `ls` to `eza` and both can hang — use `/bin/cat`,
  `/bin/ls`, or your Read tool. Never pipe a long command through `head`/`tee` in the foreground.
- Return value: compact. Verbose detail lives in your file. Report the exact model id you run
  as (from your system prompt) in the `model` field.
- If you find yourself without a lead (errors, no way to report): write state to your file and
  stop. Never take over the run.

**Out of scope by decision (never report as missing or propose):** live broker order
execution (1.0 roadmap; the agent never places, confirms or auto-applies an order); Tradesa;
reopening two-tier research, the R9 design system, the dev keystore, or the plugin system's
existence. UI findings are FUNCTIONAL defects (dead controls, broken empty/error/overflow
states, clipped/unreadable text), never visual taste.

**Raw finding shape** (every census sweep uses it so the lead can merge):

```json
{
  "raw_id": "<PREFIX>-<n>",
  "title": "...",
  "severity": "critical|high|medium|low",
  "area": "ui|agent|research|data|code|lifecycle|release|docs",
  "subsystem": "...",
  "repro": "input/state -> wrong output (exact command or steps), or 'design'",
  "evidence": "file:line[, file:line] / URL / evidence file path",
  "notes": "principle violated or mechanism + concrete consequence + smallest fix shape"
}
```

Severity: **critical** = wrong money-relevant data shown as true, data loss, safety boundary;
**high** = a core flow breaks or silently degrades, or a promise central to the product is
missing; **medium** = a real defect or gap a demanding owner hits in normal use (or that bites
the next maintainer); **low** = polish / edge. Do not pad: a finding that would not change a
decision is not a finding.
