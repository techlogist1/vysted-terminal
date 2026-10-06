# RC1 gate round 4: fix round 1 recheck

Label `rc1-fix-r1-recheck` (Opus, fresh). Certified from the running app, not the diff. Own sidecar :52336 started from
the candidate worktree source at `68d5573aff9a579af084dcbb124843f2aecff6e8` (HEAD checked), on a copy of the round-4
seed data (region IN). Raw evidence: `fix-r1/recheck/`. Working log: `logs/rc1-fix-r1-recheck.md`.
Chain context: `fix-r1/INTEGRATION.md` + `ci-local.log` show ci-local EXIT=0 twice and smoke EXIT=0 at 68d5573a.

| key | repro | observed | verdict |
|---|---|---|---|
| rc1-scenarios:1 (R15-AGENT-046 regression, high) | Exact: `vy.py invoke copilot "Publish a research brief for MSFT." --provider ollama --model llama3.1:8b --mode agent`, default (ask) autonomy. Trial 1 the model called publish_brief itself (did not exercise the path); trial 2 called only `research`, so the runtime injected `<id>__autobrief`. Fresh: `"Research Infosys for me."` on hosted gpt-4o-mini (the model never called publish_brief; only the autobrief ran), and `"research Kirloskar Oil Engines"` (same shape). Control: `"Research TCS for me." --autonomy auto`. | Trial 2 (`scen1-msft-ask-local-t2.jsonl`): the notice `Staged for your review, not applied yet: publish_brief MSFT. Accept it below to apply.` fires; the model says "which I've proposed for your review". INFY fresh (`scen1-infy-ask-hosted.jsonl`): notice names `publish_brief INFY; arrange_layout INFY`; the model says "proposed a brief for your review". Kirloskar: "proposed a brief for your review". AUTO control (`scen1-tcs-auto-hosted.jsonl`): no staged notice; the unacked auto-brief gets `The brief panel did not confirm the publish` (the AUTO read-back is unchanged). Every tool_call_id is non-empty and unique (the `__autobrief` id carries the per-call uuid). | **fixed** |
| rc1-drive-failure-inducer:1 (R15-DATA-061 class, medium) | Exact: `/quotes/<script>…`, `/quotes/$$%^`, `/history/XYZ%2FABC`. Fresh (not in the fix's tests): `/fundamentals/%3Cb%3E/income`, `/fundamentals/@@!/ratings`, `/quotes/FOO;BAR`, `/history/A|B`. Controls: `BRK-B`, `^NSEI`, `M&M`, `RELIANCE` history, `TCS`/`AAPL`/`MSFT` statements. Original DATA-061 repro `/quotes/ZZZZNOTREAL`. | All exact and fresh cases: 404 `not_found` "check the symbol", no "Retry" (`/history/A|B` gives a 200 with `reason: unknown_symbol`, the honest history shape). Controls are 200 with data. `/quotes/ZZZZNOTREAL` is 404 `not_found`, with no raw library text. (`failure-inducer-live.txt`, `-fresh.txt`, `-controls.txt`, `data-061-original.txt`) | **fixed** |
| rc1-drive-failure-inducer:2 (R15-DATA-061 class, medium) | Exact: `/fundamentals/ZZZZNOTREAL/{income,balance,cashflow,ratings}`. Fresh: an unknown US-shaped `QZXQVW` on all four sub-routes, and an unknown BSE `ZZZNOPE.BO` on income and ratings. Adjacent: real no-coverage names `GOKUL`, `KRITINUT` on ratings. | All exact and fresh cases: 404 `not_found`, where there used to be a 200 of empty data. The real no-coverage names still return 200 with a null consensus and zero counts, so the empty-frame probe does not misfire on real tickers. `INFY` ratings are 200 with data. | **fixed** |
| rc1-battery-14:1 (new, medium) | Exact: `vy.py invoke copilot 'research KPIT Technologies' --provider ollama --model llama3.1:8b`, plus `/resolve?q=KPIT Technologies` and `…Limited`. Fresh cases were found by scanning `former_names.json` for every former name that equals another listed company's current name: `Bajaj Auto`, `Gujarat Fluorochemicals`, `Kirloskar Oil Engines`, `Max India`, `Sundaram Clayton`, `Tata Motors` on `/resolve`, and a live hosted `research Kirloskar Oil Engines`. Adjacent: former-name-only queries `Iifl Wealth Management`, `Birla 3M`. | The live research step reads `resolved → KPITTECH`, the brief and autobrief are for KPITTECH, and Birlasoft is mentioned nowhere (`b14-kpit-local.jsonl`). `/resolve` returns KPITTECH at 1.0 with no disambiguation (BSOFT drops to 0.99). All six fresh collisions resolve to the current-name holder (BAJAJ-AUTO, FLUOROCHEM, KIRLOSENG, MAXIND, SUNCLAY, TMCV), with the former-name holder at 0.99. The live Kirloskar research reads `resolved → KIRLOSENG`. Former-name-only queries still resolve (360ONE, 3MINDIA at 0.99). (`battery-14-resolve.txt`, `b14-kirloskar-hosted.jsonl`) | **fixed** |

## Residuals observed (not verdict-changing, recorded for the lead)

- **Local-model narration of the auto-brief under ask autonomy.** In the live KPIT run (research only, then the
  autobrief, default ask autonomy), llama3.1:8b still wrote "Built you a brief on KPIT Technologies — it's at the top
  of the cockpit…". It ended that reply with "Do you want to accept the current brief and proceed?". The runtime now
  fires the deterministic `Staged for your review, not applied yet: publish_brief KPITTECH` notice in that same
  transcript, and it has told the model the brief is staged.
  - Tally: the local model narrated "proposed" in 1 of the 2 local research-only runs (MSFT trial 2 did, KPIT did
    not). The hosted model narrated "proposed" in 2 of 2 (INFY, Kirloskar).
  - Why the verdict holds: the runtime notice is this product's standing guarantee for the class. R15-AGENT-033 set
    it up because "under ASK the model may still narrate…". The regression was that the autobrief was the ONE host
    action with no notice and no model signal. Both now hold.
  - Product-side contributor: `sidecar/agents/copilot.json`'s after-research template ("Built you a brief on NVDA —
    it's at the top of the cockpit…") does not depend on review mode. Filed as `rc1-fix-r1-recheck:2` (low).
- **EURUSD=X under the IN session.** It gets `.NS` appended and returns 404, on both this candidate and the shared
  :52152. This predates fix-r1 and falls outside these entries. Filed as `rc1-fix-r1-recheck:1` (low).
- **Environment.** Yahoo was answering 429 intermittently during the recheck: the v7 batch quote returned 429, and
  the research price/fundamentals legs timed out after 6 s on KPIT. Every verdict above rests on classification and
  resolution, which the 429s did not affect.

## Result

4 of 4 fixed: rc1-scenarios:1, rc1-drive-failure-inducer:1, rc1-drive-failure-inducer:2, rc1-battery-14:1. None is
still failing. The own sidecar :52336 was stopped by its sleep pid (30720).
