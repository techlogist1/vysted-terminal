# Findings (round 6-rc2)

| key | kind | severity | register_id | title | evidence |
|---|---|---|---|---|---|
| rc1-battery-14:1 | new_defect | low | None | Bare 2-letter ticker absent from the company name (KO / Coca-Cola) still fails the non-IN relevance gate; _entity_signals credits ticker mentions only for len(s | docs/redesign/verification/r15/rc1/round-6-rc2/battery/raw/set-136/R15-LEAD-050.txt |
| rc1-battery-24:1 | new_defect | low | R15-UI-068 | R15-UI-068 is status fixed but half its repro still reproduces: 5 hand-rolled/skeleton tables still bypass DataTable (REMAINING.json records them as deferred_fe | docs/redesign/verification/r15/rc1/round-6-rc2/battery/raw/set-114/R15-UI-068.txt |
| rc1-battery-24:2 | new_defect | low | R15-DATA-098 | Yield curve with sample_count > span in days still emits curve[0]==curve[1] (identical first two points); extrapolation past the last tenor is fixed | docs/redesign/verification/r15/rc1/round-6-rc2/battery/raw/set-102/R15-DATA-098.txt |
| rc1-gate8:1 | new_defect | low | R15-AGENT-091 | llama3.1:8b get_portfolio answer prints USD holdings with the rupee sign although each holding carries currency:'USD' (IN default region) | docs/redesign/verification/r15/rc1/round-6-rc2/gate8/agent-get-portfolio.txt |
| rc1-heavy:1 | chain | medium | None | pnpm ci-local fails at format:check: docs/redesign/BACKLOG_0.9.1.md not prettier-formatted (added in 6f165d86, touched by ace7dd76) | docs/redesign/verification/r15/rc1/round-6-rc2/logs/ci-local.log |
| rc1-battery-8:1 | environment | low | R15-RESEARCH-008 | Keyless web_search engines are all blocked from this network today (Brave 429, Mojeek 403 automated-queries, DDG 202 challenge); the 'rotate to a live third eng | docs/redesign/verification/r15/rc1/round-6-rc2/battery/raw/set-8/R15-RESEARCH-008-direct-probe.txt |
