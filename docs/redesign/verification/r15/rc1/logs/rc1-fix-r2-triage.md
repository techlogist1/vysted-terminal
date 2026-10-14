# rc1-fix-r2-triage log
2026-09-25 07:58 own sidecar :52332 from rc1-cand source (b0f2b256), data rc1-data-rc1-fix-r2-triage, sleep pid 72433.
08:08 Read the three r1 records and rc1-fix-r1-recheck:1-3 (the residuals). Base b0f2b256 code read in the rc1-cand worktree.
- scenarios:5 residual: agent_tools/fundamentals.py _financial_statements returns no currency; agent_runtime._FUNDAMENTALS_TOOLS omits financial_statements. Real.
- onboarding-stranger:1 residual: ollama.py yields each delta before rescue_leaked_tool_call runs (openai.py:760 same shape), so a rescued call's leaked text and hand-typed result stay visible. Real. The prose-only fabrication (recheck run 6, Tata Motors) has no call to rescue. That is a model-capability limit (issue).
- battery-4:1 FAST: profiled in-process (evidence fix-r2/evidence/battery4-leg-profile.jsonl). Cold quote alone takes 7-8 s (quote-equity is Akamai-blocked: 2 extra warm-ups). Fundamentals for an uncached Indian name takes about 10.7 s: openbb 0.8 s, yfinance 2.3 s, then the exchange-filed overlay 7.0 s (6 paced NSE requests). Warm process (breaker open): price ok in about 5 s, fundamentals still dropped at 6 s.
- New finding rc1-fix-r2-triage:1: earnings estimate revenue for WIT is INR-sized but labelled USD.
- DECISIONS_FOR_OPERATOR 4.1 added (FAST first-brief budget), prettier-formatted.
08:09 PLAN.md written (3 writer sets W1 opus, W2 opus, W3 sonnet; battery-4:1 first-brief half deferred). Own sidecar stopped by killing sleep pid 72433.

## Gate round 2, fix round 2 (base ca6ec990)
2026-09-26 08:42 IST read rc1-drive-research-briefs:2, fix-r1 PLAN/RECHECK and rc1-fix-r1-recheck:1-2; read citecheck.py, iter.py (_remap_markers, merge prompt), brief-ingest.ts at ca6ec990 in the rc1-cand worktree (read-only).
- Record conclusive; re-proved in-process with the candidate venv (no own sidecar started — none needed for a regex grammar; nothing to stop). Evidence fix-r2/triage/r2-citecheck-repro.txt. Extra over-match case: '[the Company]' editorial insertion deleted.
- Real. Root cause: range separators missing from MARKER_GROUP_RE; pseudo rule is a shape rule (over- and under-matches) instead of the prompt-block-label family. Proposed regexes validated in python3 and node.
- PLAN.md written: 1 writer set W1 (opus), 0 rejected, 0 deferred. No new findings.
