# RC1 Gate Round 3 — Battery Index

Candidate sha `01d6920a300b016ab1ad8aa436ee4e4586f8e336`. Collated mechanically from
`battery/INDEX.json`, `battery/set-*.md`, `battery/raw/set-*/` and `battery/collected/*.json`
already on disk — no re-runs, no new judgement.

Fixed-status entries at sha (per `battery/INDEX.json`): **392**, packed into **75** writer/
unplanned sets, intended to be sharded 25-wide. On disk this round: **only shard 0 ran**,
producing `battery/raw/set-0`, `battery/raw/set-1`, `battery/raw/set-2` (per
`logs/rc1-battery-0.md`'s own shard-assignment note: "no explicit shard→set mapping file
exists ... took the first contiguous block of 3 sets by list order ... plus `batch-2/
W4-workspace-persistence` once the first three cleared quickly — 4 sets / 27 entries"). This
corrects the harness's shorthand shard→set fact (`{"shard":0,"sets":["raw/set-0"]}`), which
names only the first of the three raw directories shard 0 actually produced on disk; sets 1
and 2 exist and are shard 0's output too, confirmed by `battery/set-1.md`/`set-2.md` headers
(both signed "— rc1-battery-0"). Shards 1–24 never ran in this round: no `battery/raw/set-3`
onward, and no per-id `NOT RUN:`-reason file anywhere under `battery/raw/` for the remaining
71 sets.

## Shard 0 (ran)

| Set (raw dir) | Batch/writer sets folded in | Entries | Holds | Regressed | ci_pinned | needs_gui | blocked_env |
|---|---|---|---|---|---|---|---|
| raw/set-0 | batch-2/W1-fundamentals-seam + batch-2/W2-instrument-identity | 12 | 12 | 0 | 0 | 0 | 0 |
| raw/set-1 | batch-2/W3-research-integrity | 8 | 8 | 0 | 0 | 0 | 0 |
| raw/set-2 | batch-2/W4-workspace-persistence | 7 | 7 | 0 | 0 | 0 | 0 |
| **Shard 0 total** | | **27** | **27** | **0** | **0** | **0** | **0** |

Findings filed by shard 0: none (`findings/rc1-battery-0.json` = `[]`).

## Shards 1–24 (did not run this round)

No raw output exists for any of the 71 remaining sets below (365 ids). No per-id or per-set
`NOT RUN:`-reason file was found under `battery/raw/` for them, so each is listed here with
reason "no raw output — shard did not run this round" (not a product failure; a coverage gap
in this gate round's battery execution).

| Set | Missing/Total | Missing ids |
|---|---|---|
| batch-2/W5-surfaces-and-math | 9/9 | R15-CODE-PLATFORM-053, R15-DATA-007, R15-DATA-009, R15-DATA-010, R15-DATA-011, R15-DATA-031, R15-DATA-042, R15-DATA-043, R15-DATA-100 |
| batch-3/W1-agent-runtime | 9/9 | R15-AGENT-001, R15-AGENT-002, R15-AGENT-003, R15-AGENT-019, R15-AGENT-021, R15-AGENT-022, R15-AGENT-024, R15-AGENT-047, R15-AGENT-054 |
| batch-3/W2-agent-frontend-gate | 7/7 | R15-AGENT-014, R15-AGENT-080, R15-CODE-FRONTEND-003, R15-CODE-FRONTEND-008, R15-CODE-FRONTEND-014, R15-UI-001, R15-UI-002 |
| batch-3/W3-llm-adapters-and-errors | 6/6 | R15-AGENT-004, R15-AGENT-005, R15-AGENT-018, R15-AGENT-027, R15-CODE-AGENT-003, R15-UI-008 |
| batch-3/W4-research-depth | 7/7 | R15-AGENT-012, R15-DATA-045, R15-LIFECYCLE-006, R15-RESEARCH-006, R15-RESEARCH-007, R15-RESEARCH-008, R15-RESEARCH-009 |
| batch-3/W5-india-data-witnesses | 8/8 | R15-AGENT-010, R15-DATA-005, R15-DATA-019, R15-DATA-021, R15-DATA-022, R15-LEAD-002, R15-RESEARCH-011, R15-RESEARCH-013 |
| batch-4/W1-agent-runtime | 9/9 | R15-AGENT-006, R15-AGENT-008, R15-AGENT-009, R15-AGENT-011, R15-DATA-041, R15-DATA-046, R15-LEAD-007, R15-LEAD-008, R15-RESEARCH-005 |
| batch-4/W2-workflow-backtest-feeds | 9/9 | R15-AGENT-015, R15-AGENT-016, R15-CODE-FRONTEND-006, R15-CODE-PLATFORM-002, R15-CODE-PLATFORM-003, R15-CODE-PLATFORM-016, R15-DATA-029, R15-DATA-030, R15-DATA-040 |
| batch-4/W3-chat-runs-mcp | 9/9 | R15-AGENT-013, R15-AGENT-029, R15-CODE-AGENT-002, R15-CODE-FRONTEND-002, R15-CODE-PLATFORM-037, R15-DATA-038, R15-DATA-039, R15-DATA-083, R15-LIFECYCLE-005 |
| batch-4/W4-market-data-gate | 9/9 | R15-DATA-016, R15-DATA-034, R15-DATA-035, R15-DATA-036, R15-DATA-047, R15-DATA-049, R15-DATA-082, R15-LIFECYCLE-004, R15-UI-090 |
| batch-4/W5-panels-screener | 9/9 | R15-CODE-FRONTEND-020, R15-DATA-044, R15-DATA-093, R15-LIFECYCLE-007, R15-UI-003, R15-UI-004, R15-UI-005, R15-UI-006, R15-UI-007 |
| batch-5/W1-india-disclosures-agent-surface | 12/12 | R15-AGENT-020, R15-AGENT-058, R15-AGENT-060, R15-AGENT-062, R15-CODE-RESEARCH-001, R15-DATA-020, R15-DATA-023, R15-DATA-024, R15-DATA-025, R15-DATA-026, R15-DATA-056, R15-DATA-074 |
| batch-5/W2-resolver-market-data | 9/9 | R15-DATA-015, R15-DATA-037, R15-DATA-057, R15-DATA-063, R15-DATA-064, R15-DATA-072, R15-DATA-097, R15-LEAD-009, R15-LEAD-011 |
| batch-5/W3-agent-runtime-chat | 8/8 | R15-AGENT-025, R15-AGENT-026, R15-AGENT-031, R15-AGENT-033, R15-AGENT-040, R15-AGENT-048, R15-RESEARCH-014, R15-UI-054 |
| batch-5/W4-platform-workflow-boundary | 8/8 | R15-AGENT-059, R15-CODE-AGENT-012, R15-CODE-PLATFORM-004, R15-CODE-PLATFORM-005, R15-CODE-PLATFORM-019, R15-CODE-PLATFORM-020, R15-LEAD-001, R15-LEAD-003 |
| batch-5/W5-screener-earnings-sec | 11/11 | R15-CODE-DATA-004, R15-CODE-DATA-006, R15-DATA-028, R15-DATA-032, R15-DATA-067, R15-DATA-110, R15-LIFECYCLE-017, R15-LIFECYCLE-020, R15-UI-045, R15-UI-055, R15-UI-056 |
| batch-6/W1-india-exchange-data | 1/1 | R15-DATA-017 |
| batch-6/W2-delegate-runs-runtime | 1/1 | R15-LEAD-014 |
| batch-6/W3-unattended-platform-chart | 5/5 | R15-AGENT-051, R15-AGENT-052, R15-CODE-FRONTEND-015, R15-LEAD-012, R15-UI-021 |
| batch-6/W4-research-funnel | 5/5 | R15-CODE-RESEARCH-002, R15-RESEARCH-012, R15-RESEARCH-016, R15-RESEARCH-017, R15-RESEARCH-018 |
| batch-6/W5-host-actions-portfolio | 9/9 | R15-AGENT-042, R15-CODE-FRONTEND-007, R15-CODE-FRONTEND-009, R15-CODE-FRONTEND-010, R15-CODE-FRONTEND-011, R15-CODE-FRONTEND-012, R15-CODE-PLATFORM-022, R15-DATA-088, R15-DATA-089 |
| batch-7/W1-india-exchange-data | 7/7 | R15-DATA-014, R15-DATA-027, R15-DATA-050, R15-DATA-060, R15-DATA-076, R15-LEAD-004, R15-LEAD-015 |
| batch-7/W2-delegate-runs-runtime | 12/12 | R15-AGENT-034, R15-AGENT-035, R15-AGENT-036, R15-AGENT-037, R15-AGENT-038, R15-AGENT-039, R15-AGENT-074, R15-CODE-AGENT-010, R15-CODE-AGENT-011, R15-LIFECYCLE-012, R15-LIFECYCLE-013, R15-UI-040 |
| batch-7/W3-unattended-chart-workspace | 10/10 | R15-AGENT-023, R15-CODE-FRONTEND-017, R15-CODE-FRONTEND-019, R15-CODE-PLATFORM-018, R15-DATA-090, R15-UI-020, R15-UI-023, R15-UI-026, R15-UI-031, R15-UI-046 |
| batch-7/W4-research-funnel | 12/12 | R15-DATA-075, R15-RESEARCH-019, R15-RESEARCH-020, R15-RESEARCH-021, R15-RESEARCH-022, R15-RESEARCH-023, R15-RESEARCH-024, R15-RESEARCH-026, R15-RESEARCH-033, R15-RESEARCH-038, R15-UI-038, R15-UI-092 |
| batch-7/W5-agent-writes-portfolio | 9/9 | R15-AGENT-032, R15-AGENT-041, R15-AGENT-043, R15-AGENT-044, R15-UI-017, R15-UI-034, R15-UI-035, R15-UI-036, R15-UI-037 |
| batch-8/W1-sidecar-lifecycle-transport | 7/7 | R15-CODE-PLATFORM-011, R15-LIFECYCLE-010, R15-LIFECYCLE-011, R15-LIFECYCLE-023, R15-RESEARCH-032, R15-UI-012, R15-UI-014 |
| batch-8/W2-provider-readiness-host-actions | 9/9 | R15-AGENT-028, R15-AGENT-055, R15-AGENT-056, R15-AGENT-081, R15-CODE-AGENT-006, R15-UI-013, R15-UI-019, R15-UI-049, R15-UI-057 |
| batch-8/W3-data-error-honesty | 6/6 | R15-AGENT-030, R15-AGENT-061, R15-DATA-081, R15-LEAD-005, R15-UI-029, R15-UI-030 |
| batch-8/W4-resolver-exchange-lanes | 11/11 | R15-AGENT-045, R15-CODE-DATA-002, R15-CODE-DATA-003, R15-DATA-051, R15-DATA-058, R15-DATA-084, R15-DATA-085, R15-DATA-086, R15-LIFECYCLE-019, R15-LIFECYCLE-022, R15-UI-039 |
| batch-8/W5-agent-runtime-research | 6/6 | R15-CODE-AGENT-004, R15-CODE-AGENT-007, R15-CODE-AGENT-016, R15-CODE-RESEARCH-003, R15-LEAD-019, R15-LIFECYCLE-014 |
| batch-9/W1-agent-runtime | 5/5 | R15-AGENT-046, R15-CODE-AGENT-005, R15-CODE-AGENT-008, R15-LIFECYCLE-025, R15-RESEARCH-027 |
| batch-9/W2-research-search-news | 4/4 | R15-CROSS-PLATFORM-002, R15-DATA-094, R15-LIFECYCLE-018, R15-UI-033 |
| batch-9/W3-fundamentals-identity-earnings | 6/6 | R15-DATA-052, R15-DATA-069, R15-LEAD-016, R15-LEAD-022, R15-LEAD-023, R15-UI-015 |
| batch-9/W4-market-lanes-errors-quant | 7/7 | R15-DATA-062, R15-DATA-065, R15-DATA-066, R15-DATA-073, R15-LIFECYCLE-021, R15-UI-051, R15-UI-053 |
| batch-9/W5-frontend-shell | 7/7 | R15-CODE-FRONTEND-016, R15-CROSS-PLATFORM-004, R15-DATA-092, R15-UI-016, R15-UI-052, R15-UI-058, R15-UI-086 |
| batch-10/W1-runtime-backtest | 6/6 | R15-AGENT-050, R15-CODE-PLATFORM-029, R15-LEAD-018, R15-LIFECYCLE-015, R15-UI-010, R15-UI-011 |
| batch-10/W2-catalog-hostactions | 4/4 | R15-AGENT-084, R15-CODE-AGENT-013, R15-CODE-PLATFORM-021, R15-RESEARCH-030 |
| batch-10/W3-fundamentals-bse-cache | 7/7 | R15-DATA-048, R15-DATA-053, R15-DATA-054, R15-DATA-055, R15-DATA-068, R15-DATA-096, R15-LEAD-024 |
| batch-10/W4-screener-routes-statedocs | 6/6 | R15-CROSS-PLATFORM-003, R15-DATA-061, R15-DATA-087, R15-DATA-095, R15-DOCS-016, R15-RESEARCH-025 |
| batch-10/W5-chat-search-workflow | 7/7 | R15-AGENT-063, R15-AGENT-082, R15-AGENT-088, R15-CODE-PLATFORM-017, R15-CODE-RESEARCH-004, R15-RESEARCH-028, R15-UI-027 |
| batch-10/W6-chart-notes-blueprint | 4/4 | R15-DOCS-004, R15-LEAD-026, R15-UI-024, R15-UI-048 |
| batch-10/W7-panels-marketplace | 6/6 | R15-AGENT-053, R15-CODE-PLATFORM-072, R15-DATA-077, R15-UI-018, R15-UI-028, R15-UI-032 |
| batch-10/W8-plugins-dock | 2/2 | R15-AGENT-057, R15-CODE-PLATFORM-012 |
| batch-11/W1-scripts-build | 5/5 | R15-CODE-PLATFORM-026, R15-CODE-PLATFORM-027, R15-CODE-PLATFORM-028, R15-RELEASE-005, R15-RELEASE-006 |
| batch-11/W2-runtime-schema | 2/2 | R15-CODE-AGENT-009, R15-LIFECYCLE-024 |
| batch-11/W3-agent-eval | 1/1 | R15-AGENT-007 |
| batch-11/W4-registry-loop | 2/2 | R15-DATA-071, R15-LIFECYCLE-026 |
| batch-11/W5-data-reference | 1/1 | R15-LEAD-013 |
| batch-11/W6-options-chain | 1/1 | R15-DATA-079 |
| batch-11/W7-preferences | 1/1 | R15-UI-087 |
| batch-11/W8-frontend-visual | 4/4 | R15-CODE-PLATFORM-023, R15-CODE-PLATFORM-025, R15-UI-085, R15-UI-091 |
| unplanned-1 | 1/1 | R15-CODE-AGENT-033 |
| unplanned-2 | 2/2 | R15-AGENT-092, R15-AGENT-093 |
| unplanned-3 | 3/3 | R15-AGENT-090, R15-LEAD-031, R15-LEAD-032 |
| unplanned-4 | 1/1 | R15-CODE-PLATFORM-030 |
| unplanned-5 | 1/1 | R15-DATA-113 |
| unplanned-6 | 1/1 | R15-DOCS-005 |
| unplanned-7 | 1/1 | R15-LEAD-033 |
| unplanned-8 | 2/2 | R15-LEAD-034, R15-LEAD-039 |
| unplanned-9 | 1/1 | R15-RESEARCH-010 |
| unplanned-10 | 1/1 | R15-DATA-115 |
| unplanned-11 | 3/3 | R15-DATA-078, R15-DOCS-018, R15-LEAD-010 |
| unplanned-12 | 1/1 | R15-DATA-116 |
| unplanned-13 | 1/1 | R15-CODE-AGENT-034 |
| unplanned-14 | 1/1 | R15-DATA-114 |
| unplanned-15 | 2/2 | R15-CODE-PLATFORM-013, R15-CODE-PLATFORM-014 |
| unplanned-16 | 1/1 | R15-LEAD-028 |
| unplanned-17 | 1/1 | R15-CODE-PLATFORM-024 |
| unplanned-18 | 3/3 | R15-CODE-DATA-023, R15-DATA-112, R15-DOCS-017 |
| unplanned-19 | 1/1 | R15-RELEASE-007 |

**Total missing across not-run sets: 365** (out of 392 fixed ids; 27 covered by shard 0).

## Battery status: **incomplete**

392 fixed ids at sha; 27 have raw output (shard 0 only); 365 have no raw output across 71
un-run sets (shards 1–24). Per the collation rule, this is reported as `incomplete`, never
`pass`, because at least one fixed id lacks raw output.

## Data-pack section

See `DATAPACK.md` (full detail; not duplicated here). Summary: all 24 manifest slot names
were freshly re-collected this round via the candidate's own sidecar on the seed data profile
(`battery/collected/*.json`, all `"complete": true`; collector log
`logs/rc1-datapack-collect.log`). 45 fixed register entries whose title/repro names a battery
symbol were re-checked against the fresh collection; all held on direct field/`field_meta`
inspection (the "kept, flagged" pattern, not silent value substitution), except entries the
collector's fixed HTTP-route plan cannot reach at all (agent-tool-loop entries, the research-
gate AMAL entry, quarterly-statement/scrip-code/background-warm entries — none of these showed
an adjacent regression in what the collector does reach). Zero regressions, zero new defects.
Findings filed: none (`findings/rc1-datapack.json` = `[]`).
