# RC1 fix round 2: recheck

Rechecker: rc1-fix-r2-recheck (Opus 5.5). Candidate `1d6511c89bb27f1785f7af4d2290983b2852d70a`.
Everything was run from the running app on my own sidecar: source in `scratchpad/rc1-4097dac-fix-int`
(clean), port `:52337`, on a fresh keyless seed copy (`rc1-data-rc1-fix-r2-recheck`). The sidecar
was stopped when I finished (sleep pid 89074). I did not use the shared stack for writes. In-process
checks used the candidate venv with `PYTHONDONTWRITEBYTECODE=1` and wrote nothing to the worktree.
Evidence is in `fix-r2/recheck/`. Working log: `logs/rc1-fix-r2-recheck.md`. Findings:
`findings/rc1-fix-r2-recheck.json`.

**Result: 0 fixed and 2 still failing.** In both, the mechanism the writers fixed is closed, but a
model-capability half that the triage scoped out still reproduces the harm. The recheck also found
1 low new defect (a residue of the W2 fix) and 1 environment item.

| key | repro | observed | verdict |
|---|---|---|---|
| rc1-scenarios:5 | Exact prompt "How many ordinary shares does one SIFY ADR represent, and what is SIFY's TTM revenue in USD?". (a) OR `nvidia/nemotron-3-super-120b-a12b:free` ×3 (the finding's model). (b) llama3.1:8b ×2 (the finding's cross-model confirmation). (c) In-process `_model_facing_content('financial_statements', …)` for SIFY, plus fresh class variants WIT, INFY, INFY.NS and AAPL. (d) Live fresh variant: WIT income on llama. | (a) Runs 1 and 2 hit an upstream Nvidia 5xx (environment). Run 3: "One SIFY ADR represents **6 ordinary shares**" (web-sourced), revenue "₹4,651 cr", and no USD guess. The exact repro no longer reproduces. (b) Run 1: the ADR question was declined honestly, and revenue was given in INR, but a ₹13,444 cr cash-flow reading was called revenue. Run 2: "**SIFY ADR represents 1 ordinary share.** SIFY's TTM revenue is ₹4,651 cr." The ADR fabrication reproduces. (c) SIFY income comes back with `currency: INR`, and `total_revenue` 44877000000.0 becomes `₹4,488 cr`. WIT is INR, INFY is USD (its `financial_currency`) and AAPL is USD. EPS and share-count lines stay raw. (d) "₹92,624 crore … net income ₹13,197 crore … INR", which matches the served lines. A sweep of the `agent_tools` siblings found only the earnings estimate, already filed as rc1-fix-r2-triage:1. | **still failing.** The currency or USD mislabel is fixed, and the class fix holds on the WIT and INFY variants. The ADR-ratio fabrication still reproduces on llama3.1:8b (1 of 2 runs). That half was scoped out as model capability, so the operator decides (rc1-fix-r2-recheck:1). |
| rc1-drive-onboarding-stranger:1 | Keyless, llama3.1:8b, exact prompt "hi, I just installed this. what can you do, and how is Zomato stock doing today?" ×6. In-process `OllamaProvider` fed the original assistant text at chunk sizes 1, 3 and 7. Fresh variants: in-process JSON `news` leak and inline `fundamentals(...)` leak, each with fake results; live "hey, new here. how is Paytm stock doing today?" ×3. | In-process, the original text becomes one `price_data {symbol: ZOMATO.NS}`. None of `164.4`, the fake JSON or "As per the live data" is ever shown. The fresh leaks are rescued with their fake values dropped, and prose streams whole. Live, every leaked call in all 6 runs was held and rescued, and no hand-typed tool result streamed. Runs 2-5 were honest, and runs 3-4 quote ₹335.5, which is the served ETERNAL.NS price. Run 1 said "the last successful fetch showed a price of **₹149.30** … on 2023-12-01", but no such fetch happened. Run 6 said "Zomato (ETERNAL.NS) is currently trading at **₹128.05** … last price I have is ₹131.10"; it called ZEEL.NS, which was served at 78.17, and ETERNAL.NS is ₹335.5. Paytm ×3 gave no invented price. A dangling `{"name": "price_data` fragment shows in runs 1-4. | **still failing.** The leaked-call mechanism is fixed. In 2 of 6 exact runs an invented price is still presented as fetched, in prose with no call syntax. PLAN.md scoped that half out as model capability (rc1-fix-r2-recheck:2). New low defect: dangling marker fragment (rc1-fix-r2-recheck:3). |

Chain: `fix-r2/ci-local.log` ends `EXIT=0 2026-09-25T02:59:52Z`, and `fix-r2/smoke.log` has
`SMOKE_EXIT=0 2026-09-25T02:55:29Z`, both at `1d6511c8` according to INTEGRATION.md. Nothing
adjacent broke: prose without a call, and calls to tools that were not offered, stream unchanged.
The INFY/AAPL USD statements still render in USD.

Environment: the OR nemotron free lane returned an upstream "Service temporarily overloaded" 5xx on
2 of 3 runs (rc1-fix-r2-recheck:4).
