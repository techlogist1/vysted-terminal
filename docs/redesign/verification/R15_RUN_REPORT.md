<!-- backfilled 24 Sep 2026 from journals + run-state; numbers traceable per row -->

# R15 LAUNCH — run report

Status right now: **run in progress — no `r15-*` tag yet; the fallback release line is
`r13-bedrock` @ `6a40f83`.** Stage C batch 10 is in flight (8 writers running); the rc1 gate
workflow has not started.

## Gate table

| # | Gate | Status | Evidence | Date |
|---|---|---|---|---|
| 1 | Truth | **HOLD** | `vysted-r15-run-state.md` decisions R15-D1..D6 + `r15/stage0/`; commit `38ded25b` "Gate 1 holds" | 04:57 IST 23 Sep |
| 2 | Census closed | **HOLD** (adjudicated after 2 BLOCKED passes) | `R15_GATE2.md` (three fresh-context Opus verifiers); register 887 raw → 603 entries + 76 rejections at close; commit `99e2ae38` | BLOCKED 13:28, BLOCKED (narrower) 14:17, HOLDS 15:00 — all IST 23 Sep |
| 3-7 | not individually named | **not recorded** | `vysted-r15-run-state.md` never defines Gates 3-7 by name or status — the "Next action" sequence goes straight from Gate 2 (census) to Stage C fix batches and then to Gate 8 at rc1, with no separate Gate 3-7 checkpoint narrated anywhere in the header or loop log. Gate identities beyond 1/2/8 live only in `R15_BRIEF.md`, which this backfill is barred from reading. | — |
| 8 | Safety — rewritten (SCOPE CHANGE, 03:46 IST 23 Sep): prove no order/broker/simulated-account path exists anywhere and the tracked portfolio is intact | **QUEUED, not started** | `r15/tooling/rc1-gate.js` (committed `b47ed2d`, re-routed `0a7a643`); run-state ledger line 30: "QUEUED — rc1 gate workflow... Not started." Interim per-batch proof exists (e.g. batch 1's fresh verifier checked Gate 8 on :52300: 88 OpenAPI paths, 0 broker/order/kill/audit hits, all 22 former routes 404) but no run-wide rc1 verdict has been produced. | not run as of 24 Sep 23:24 IST |

## Stages

**A — reconcile + relicense.** `wf_aa843beb-8ad` (worktree/registration salvage scout, 7.8min) →
`wf_351041f4-938` (license writer+reviewer, iso-stack rebuild + Ollama local-lane proof, 17.8min)
→ `wf_e5b785bd-002` (num_ctx fix + refute-planner, 34.6min). Outcome: relicensed to PolyForm
Strict 1.0.0 + commercial (`0c63d46`), isolated stack rebuilt from source on :52152-54, num_ctx
fix (`d328089`), Gate 1 holds 04:57 IST 23 Sep. Closed L9-L12.

**B — census.** Refute waves `wf_338a3672-c14` (W1, 6 Opus) + `wf_f9150967-7cf` (W2-W6, 29 Opus) →
Stage B items 1-3 `wf_6a0f9c02-a2e` (75 agents) → items 4-6 `wf_e5222ca0-412` (77/78 agents) → Gate
2 workflow across 3 attempts (`wf_94189615-7df` BLOCKED, `wf_a8d56de8-9b4` BLOCKED narrower,
`wf_079d13fa-9ac` HOLDS). Outcome: 887 raw findings → 603 register entries + 76 rejections, 23/23
intent chunks, 1,032/1,032 promises assessed, coverage map 101 surfaces/288 cells. Gate 2 HOLDS
15:00 IST 23 Sep. Closed L12-L19.

**C — fix batches 1-10.** Per `R15_RUN_LOG.md` Waves table; `stage-c/batch-N/{PLAN.md,
VERDICTS.json,VERDICTS.md}` per batch.

| Batch | Merge sha | Planned | Certified | needs_gui | Not certified | Merged (IST) |
|---|---|---|---|---|---|---|
| 1 (trading removal) | `a122dbf6` | full-repo removal, not a fix count | Gate 8 rewritten-proof pass | 0 | 0 | 23 Sep 16:33 |
| 2 | `806a90ca` | 40 (16 crit + 24 high) | 37 | 0 | 3 (DATA-005, DATA-014, AGENT-001) | 23 Sep 18:47 |
| 3 | `c81d879b` | 40 | 38 | 0 | 2 (DATA-020, RESEARCH-005) | 23 Sep 21:07 |
| 4 | `dcbe7bae` | 52 | 45 | 2 (UI-009, UI-025) | 3 (DATA-015, DATA-020, DATA-032) | 24 Sep 00:01 |
| 5 | `1574ed8e` | 58 | 48 | 2 (CODE-AGENT-001, LIFECYCLE-008) | AGENT-052 + residuals; LEAD-010 regression fixed post-hoc `7ae5117` | 24 Sep 03:03 |
| 6 (harness-stall failure, recovered) | `5e147317` | 60 planned, 22 delivered before the stall | 21 | 0 | 3 open (incl. AGENT-046, RESEARCH-024) | 24 Sep 15:34 |
| 7 | `e81c9e7c` | 55 | 50 | 1 (UI-022) | 4 (AGENT-045 + LEAD-005/AGENT-046/CP-021 not delivered) | 24 Sep 17:53 |
| 8 | `68bb7aa4` | 47 | 39 | 1 (LIFECYCLE-001) | 7 | 24 Sep 20:06 |
| 9 | `6b702305` | 45 | 29 | 2 (UI-083, UI-050) | 14 | 24 Sep 22:44 |
| 10 | **IN FLIGHT** | 56 of 88 open (0/2 highs, 56/86 mediums) | — | — | — | writers dispatched 22:47, not yet merged |

**D — docs wave drafts.** `wf_31f149cf-57d` (20 agents, 29.3min, 2.8M tokens). 5 drafts revised
after Fable critics (README, RELEASE_RUNBOOK, OPERATOR_BRIEFING, RELEASE_NOTES,
CURRENT_STATE+BLOCKERS); `SECRETS_SCAN` 0 flagged real; `DEPS_LICENCES` 6 flagged (frozendict
LGPLv3 bundled in the main + openbb-mcp sidecars); `LICENCE_CHECK` 1 mismatch (CLAUDE.md's stale
AGPL line); 17 open questions across 6 sections. Committed `5f1ddaae`, 24 Sep 23:18. **Drafts are
not promoted** — `mode:'refresh'` reruns before rc2, then the lead promotes.

**E — not started.** rc1 gate workflow (`r15/tooling/rc1-gate.js`): Gate 8 re-proof, regression
suite assembly (ci-local + smoke + scenario harness + scripted owner-drive + battery of fixed
names), a GUI round for the needs_gui set, a fresh adversarial verifier, tag `r15-rc1` + push,
then hygiene prune (writer worktrees). Lows (208 of 221 still open) roll into rc2 with the Stage D
refresh. Source: run-state ledger line 30, "QUEUED... Not started."

## Register now

Current snapshot: commit `6b91b8fa` "batch-10 register adjudication" (batch-9's verdicts applied;
batch-10's own writers have not yet reported). `vysted-r15-register.json`'s own declared counts:
**887 raw findings → 630 entries + 76 rejections** (16 critical / 112 high / 281 medium / 221 low).

| Severity | fixed | open | needs_gui | removed_with_feature | blocked_tier4 | not_a_defect | total |
|---|---|---|---|---|---|---|---|
| critical | 16 | 0 | 0 | 0 | 0 | 0 | 16 |
| high | 101 | 2 | 4 | 1 | 4 | 0 | 112 |
| medium | 181 | 86 | 4 | 9 | 0 | 1 | 281 |
| low | 10 | 207 | 0 | 4 | 0 | 0 | 221 |
| **total** | **308** | **295** | **8** | **14** | **4** | **1** | **630** |

Operator-attended items:
- **blocked_tier4 (4):** `R15-RELEASE-001..004` — unsigned desktop bundles, no GitHub release
  pipeline, dead auto-updater, CI never run on `004`. `docs/redesign/DECISIONS_FOR_OPERATOR.md`
  §2.8-2.11.
- **open, high, funded-lane (2):** `R15-AGENT-007` (no agent eval loop), `R15-AGENT-017` (shipped
  default chat model returns `content_filter` with zero tokens) — both routed around because the
  default provider lanes are unfunded. `DECISIONS_FOR_OPERATOR.md` §2.1.
- **needs_gui (8):** `R15-CODE-AGENT-001`, `R15-LIFECYCLE-001`, `R15-LIFECYCLE-008`, `R15-UI-009`,
  `R15-UI-022`, `R15-UI-025`, `R15-UI-050`, `R15-UI-083` — pending the GUI round in Stage E.

## Where the evidence lives

- Header + loop log: `docs/redesign/verification/vysted-r15-run-state.md`
- Register: `docs/redesign/verification/vysted-r15-register.json` (+ `.md` view)
- Gate 2 evidence packet: `docs/redesign/verification/R15_GATE2.md`
- Stage C per-batch plans/verdicts: `docs/redesign/verification/r15/stage-c/batch-{1..10}/`
- Lows pre-triage: `docs/redesign/verification/r15/stage-c/lows-triage/`
- Stage D docs wave: `docs/redesign/verification/r15/stage-d/`
- Decision logs: `docs/redesign/DECISIONS.md` (D1-D81), `docs/redesign/DECISIONS_FOR_OPERATOR.md`
- Batch summaries: `CHANGELOG.md` — trading-removed D81 (line 310), batch 2 (279), batch 3 (234),
  batch 4 (190), batch 5 (141), batch 6 (109), batch 7 (79), batch 8 (47), batch 9 (7)
- Spend ledger: `docs/redesign/verification/r15/spend-ledger.jsonl`
- Workflow journals: `…/3e7ae14d-d48a-4882-8a75-f7608754c23f/subagents/workflows/<runId>/journal.jsonl`
  (this session) and `…/5df12ac0-f23e-48c6-b614-80321cbbfb31/subagents/workflows/<runId>/journal.jsonl`
  (prior session, 19 Sep)
