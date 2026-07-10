# R13 DATA BEDROCK — run report

Autonomous overnight run. Lead: Fable 5 (advisor-orchestrator, no mechanical work, no Fable teammates).
Mission: any-symbol data bedrock — profile contract, foreign witness, entity-anchored retrieval, filings floor, cross-source sanity, depth integrity; Jarvis verification reflex; ≥12-name hostile battery; 8 gates.

## Telemetry
| # | Task | Routed to | Actual model | Result |
|---|---|---|---|---|
| T1 | Phase A doc reads + arch scouts (wf_82ecafab-11c, 8 agents) | sonnet x7, haiku x1 | sonnet/haiku | 4/8 good; 2 schema-cap failures (r12-close, design), 2 placeholder-junk "test" returns (disposition, scout:retrieval) — all 4 re-run |
| T2 | Re-reads: r12-close, disposition, retrieval scout (sonnet), design (haiku) | sonnet x3, haiku x1 | sonnet x3, haiku x1 | all landed, high quality |
| T3 | Subtle-wrong triad live prober | sonnet | sonnet | all 3 cases REPRODUCED w/ mechanisms (126k tokens, 52 tools) |
| T4 | SPINE implementer (worktree-agent-spine) | opus | opus 4.8 | dispatched 15:20 |
| T5 | WITNESS implementer (worktree-agent-witness) | opus | opus 4.8 | dispatched 15:20 |
| T6 | RETRIEVAL implementer (worktree-agent-retrieval) | opus | opus 4.8 | dispatched 15:20 |
| T7 | Battery curator (≥16 names + reference packs) | sonnet | sonnet | done — 17 packs + manifest, 6 BSE-only, 10 collision-class, all masters-verified (124k tokens, 72 tools) |
| T8 | Agent-runtime scout (Jarvis design input) | sonnet | sonnet | done — full ack/narration map; found the kept_previous false-notice mechanism (160k tokens) |
| T9 | SPINE fresh-context adversarial verifier | opus | opus 4.8 | dispatched ~15:50 |

## Phase B progress
- SPINE landed (worktree-agent-spine @ cf83b5e, pushed): _yahoo_symbol BSE-only→.BO; husk honesty; registry fallback_ok never serves all-null shell; correctness_gate withhold/flag bounds; FieldMeta contract + types/data.ts mirror. Suite 2311→2335/1skip. Live smoke: get_fundamentals('KSE') → PE 6.913, ROE 0.260, provider yfinance, field_meta 32 entries. Lead diff review: APPROVED (is_bse_symbol pre-exists at base — no partition violation; PE×EPS price-proxy design accepted: intra-snapshot consistency check, non-circular). Awaiting adversarial verifier before merge.

## Phase A — KSE repro (lead's own hands, r13/kse-repro/)
- NORMAL (15:07, 33s, 12 steps): resolve 0ms → 4/4 structured legs (fundamentals died to junk-guard live in logs) → 8 web sources for "KSE Ltd" — sources 1-2 verified ON-ENTITY (Moneycontrol, Economic Times KSE Ltd pages). Brief panel: price card + SOURCES(8), zero metric cards (all-null fundamentals → honest no-card), prose in chat only. Chat note "The panel kept the previous, richer brief." contradicted the panel showing the new FAST brief — Phase C self-consistency evidence.
- DEEP (15:09, engine): round-1 LLM planning 60,003ms vs 90s slice → "round overran its 90s slice — win[ding down]" → brief: "No findings were gathered before the run ended", 2 sources — byte-match of the operator's 12:57 failure artifact (01-boot-state.png). Model's recovery pass then pulled BSE feeds + filings manually and produced a real price/action brief (4 sources) — but narrated the fundamentals gap as world-absence ("our data feeds simply don't carry fundamentals") when the lane is app-broken: Gate-8b baseline evidence (10-deep-followup.png).
- ULTRA: model initially DECLINED to re-run ("deep already hit a data wall") and pulled BSE filings directly (30 Jun window closure, 17 Jun board outcome, 3 Jul SEBI cert — the filings floor works); forced via tool-arg escalation 15:19:40.
- Root causes: D72 triad. Subtle-wrong: D73 (all three reproduced).

## Phase A — truth and repro
- Caffeinate: armed run-scoped (`caffeinate -dims`, PID 3695).
- Tree adjudication: HEAD `7a7f7fd` = origin/004-r4-experience-rebuild; tag `r12-finisher` @ `14d05b6` + two docs-only commits after (`247d35b`, `7a7f7fd`) — the established pattern, no drift. Branch 004, version 0.8.0.
- Sacred files: `enrich_nse_sectors.py` working sha256 `5cb28e0d…abbe` — byte-identical to R11_RUN_REPORT record, VERIFIED. `kill-switch-benchmark.json` M-uncommitted as designed.
- Baseline vitest: **1481 passed / 134 files, 0 skips** (matches R12 close exactly).
- Baseline pytest: **2311 passed / 1 skipped (live-key conditional), 172s** (matches R12 close exactly).
- Sidecar rebuild x3: (running)
- KSE repro: (pending)

## Evidence index
- Screenshots: docs/redesign/verification/r13/<surface>/
- Run state: vysted-r13-run-state.md
