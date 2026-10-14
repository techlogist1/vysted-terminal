# rc1-battery-1 working log (REGRESSION BATTERY shard 1, stage-c batch-3 + batch-11)

Candidate: 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2
Own sidecar: booted from `rc1-cand` scratch worktree on 127.0.0.1:52341, data dir a fresh
copy of `rc1-seed-data`, sleep wrapper pid 61273, python pid 61275. Reused for every set.
Shared read-only stack (:52152/53/54) touched only via GET / read-only agent runs.

## Method
For each id: looked up `closure_evidence` in `vysted-r15-register.json` to find the entry's
true certifying batch (several ids' task-assigned "batch-N/W-label" set name does not match
the batch that actually closed them per the register — noted per-set in each battery/set-N.md
header). Read that batch's VERDICTS.md "Per-entry evidence"/"Certified" section, then re-ran
the repro live where feasible (curl against the own sidecar or the shared read-only stack,
or an in-process python call against the candidate's actual gating/computation function —
never just the surface-level classifier), falling back to grep/ast/static confirmation +
citing the committed test (`ci_pinned`) for entries whose live repro needs either a live
DEEP-research run, a multi-minute wait, secrets/funded keys, or the full ~45-min agent-eval
harness, consistent with the task's own allowance and the 52-entry shard's time/stall-
watchdog budget.

## Methodological note (AGENT-019 near-miss)
Testing `classify_intent()` alone on the register's own tricky phrasing ("My RELIANCE lot is
actually 12 shares") returns `intent='read', signals=[]`, which looks like a regression
against the certified "keeps write tools" behaviour. Investigating further: the actual gate
is `agent_runtime._resolve_tool_surface`, whose `read_only = inferred_intent == "read" and
bool(intent.signals)` requires a POSITIVE signal, not just the "read" label — with
`signals=[]`, `read_only` is False, so write tools are KEPT. Confirmed directly against the
real function for 5 phrasings. `git log`/`git show` on the two `_EDIT_SIGNALS`-touching
commits (`cac929d8`, `c65c4c1f`) confirm purely additive changes. No regression. Lesson: trace
to the actual consuming/gating function, never the surface classifier alone, before calling
a regression.

## Environment conditions confirmed live this shard (not product defects)
- BSE `api.bseindia.com` SHP/scrip-header endpoints: 403 Akamai "Access Denied" from this
  IP/session (affects DATA-021's live-rows-with-real-content half; the merge fail-safe
  itself — never fabricating BSE data on failure — was confirmed instead).
- Shared SearXNG (`vysted-searxng:8888`): `state: degraded`, `reason: "brave: Suspended: too
  many requests; duckduckgo: CAPTCHA; startpage: Suspended: CAPTCHA"` (RESEARCH-020,
  `blocked_env`).
- Yahoo circuit breaker: one transient 502 on `/earnings/*/estimates` traced to a nonzero
  `cooldown_remaining` via `/system/provider-health`; retry after cooldown cleared succeeded
  (DATA-029, not a regression).

## Sets completed
set-5 (batch-3/W1, 8 ids), set-6 (batch-3/W2, 7 ids incl. AGENT-007 dedup'd to set-50),
set-7 (batch-3/W3, 5 ids), set-8 (batch-3/W4, 7 ids), set-9 (batch-3/W5, 8 ids),
set-48 (batch-11/W1, 5 ids), set-49 (batch-11/W2, 2 ids), set-50 (batch-11/W3, 1 id),
set-51 (batch-11/W4, 2 ids), set-52 (batch-11/W5, 1 id), set-53 (batch-11/W6, 1 id),
set-54 (batch-11/W7, 1 id), set-55 (batch-11/W8, 4 ids).

51 unique entries (52 listed rows, AGENT-007 appears in both set-6 and set-50 for the same
id — one row in the top-level `results`). 0 regressions found.

Tally: holds 37, ci_pinned 13, blocked_env 1, regressed 0, needs_gui 0.

## Teardown
Own sidecar (:52341, sleep pid 61273 / python pid 61275) stopped at shard end. Ollama lock
released via the `trap ... EXIT` wrapper on every call that took it; verified free.

COVERAGE: 51/51 unique ids raw (52/52 listed rows; AGENT-007's raw lives under set-50, cross-
referenced from set-6); no raw: none.
