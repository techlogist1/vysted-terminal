# R15 stage-c lows — remaining register (collated)

Generated 07:23 IST. BASE 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2 (earlier lows writers branched from ebc5ed4194f9362422c3178c27d4cdf946428968).
All branch heads below were verified against origin via `git fetch --prune` + `git ls-remote origin <branch>` at collation time. **Mismatches: none** — every reported head_sha matched origin for all 11 branches.

## fixed_untested (24)

| id | partition/set | branch | head | commit | files |
|---|---|---|---|---|---|
| R15-CODE-RESEARCH-005 | P1 | worktree-agent-lows-CN-r15-code-research-005-4c6dfe8 | 113ab130 | 84c912e6,3f8dffa4 | 15 |
| R15-CODE-AGENT-031 | P1 | worktree-agent-lows-CN-r15-code-agent-031-4c6dfe8 | 695e934a | 65859b92 | 7 |
| R15-CODE-DATA-019 | P1 | worktree-agent-lows-CN-r15-code-data-019-4c6dfe8 | 31aa053b | a1539309 | 7 |
| R15-LIFECYCLE-035 | P2 | worktree-agent-lows-CN-r15-lifecycle-035-4c6dfe8 | 954ffa89 | 3da1e972 | 3 |
| R15-CODE-FRONTEND-027 | P2 | worktree-agent-lows-CN-r15-code-frontend-027-4c6dfe8 | cba8df9f | f8d6594f | 13 |
| R15-AGENT-077 | P3 | worktree-agent-lows-CN-r15-agent-077-4c6dfe8 | 80f8d7a2 | ef9e04cd | 7 |
| R15-DATA-102 | P3 | worktree-agent-lows-CN-r15-data-102-4c6dfe8 | 09d8da83 | 94185b4d | 11 |
| R15-DOCS-025 | new-lows | worktree-agent-lows-NEW-drafted-4c6dfe8 | abcee383 | 48314633 | 1 |
| R15-CODE-PLATFORM-078 | new-lows | worktree-agent-lows-NEW-drafted-4c6dfe8 | abcee383 | 79682cda | 2 |
| R15-CODE-PLATFORM-079 | new-lows | worktree-agent-lows-NEW-drafted-4c6dfe8 | abcee383 | 31ece664 | 1 |
| R15-CODE-FRONTEND-038 | new-lows | worktree-agent-lows-NEW-drafted-4c6dfe8 | abcee383 | d4bd1c5f | 2 |
| R15-CODE-PLATFORM-080 | new-lows | worktree-agent-lows-NEW-drafted-4c6dfe8 | abcee383 | 4a0141c8 | 1 |
| R15-CODE-FRONTEND-033 | deferred-A | worktree-agent-lows-DEF-A-4c6dfe8 | 8113ddc1 | 97d2f1f0 | 1 (test-only) |
| R15-CROSS-PLATFORM-012 | deferred-B | worktree-agent-lows-DEF-B-4c6dfe8 | af933bcc | b0e27eb2 | 7 |
| R15-UI-082 | deferred-B | worktree-agent-lows-DEF-B-4c6dfe8 | af933bcc | 6afc62b5 | 3 |
| R15-UI-073 | deferred-B | worktree-agent-lows-DEF-B-4c6dfe8 | af933bcc | f791982d | 10 |
| R15-UI-071 | deferred-B | worktree-agent-lows-DEF-B-4c6dfe8 | af933bcc | 730d482e | 3 |
| R15-UI-068 | deferred-B | worktree-agent-lows-DEF-B-4c6dfe8 | af933bcc | 451a91f7 | 2 (primitive half only; see split below) |
| R15-LEAD-036 | P3 | worktree-agent-lows-LEAD-036-4c6dfe8 | 8315c857 | 500cd050 | 3 |

All of the above: written as source, not run (off-lane rule) — untested pending integration.

## deferred_feature (2)

| id | partition/set | branch | note |
|---|---|---|---|
| R15-AGENT-085 | deferred-A | worktree-agent-lows-DEF-A-4c6dfe8 | Inseparable per PARTITION.json (spans runtime-catalog + llm-chat sets, neither merged yet). Size: ~0.5–1 day post-merge. Built nothing. |
| R15-UI-068 (port half) | deferred-B | worktree-agent-lows-DEF-B-4c6dfe8 | 5 hand-rolled tables still bypass the DataTable primitive (ScreenerResultsTable, WatchlistPanel, EarningsCalendarPanel, BacktestResultView, brief-blocks); register's 6th file (AuditLogViewer.tsx) doesn't exist at BASE. Size: ~4 days total. Built nothing. |

## not_a_defect_proposed / concur_not_defect (6)

| id | source | branch | note |
|---|---|---|---|
| R15-AGENT-065 | writer (DEF-A) | worktree-agent-lows-DEF-A-4c6dfe8 | CURRENT_STATE.md already carries the Deferred caveat; BLUEPRINT.md makes no contradicting claim. No diff. |
| R15-AGENT-086 | writer (DEF-A) | worktree-agent-lows-DEF-A-4c6dfe8 | pause_run gone; ask_user-driven pause/resume already documented accurately. Matches register's already_fixed note. No diff. |
| R15-CODE-FRONTEND-031 | writer (DEF-A) | worktree-agent-lows-DEF-A-4c6dfe8 | enqueue already returns {id, outcome}; duplicated predicate already deleted. No diff. |
| R15-LEAD-025 | refuter (static trace, no branch) | — | Warm-loop openbb calls are already throttled (Semaphore(1), jitter, circuit-breaker). Optional: merge W4's pin test; file any real boot-time load as a new entry. |
| R15-CODE-PLATFORM-045 | refuter (static trace, no branch) | — | Bridge only happens post-active; every reported failure path pre-empts attach. One latent residual unreachable by any shipped plugin today (optional hardening noted). |
| R15-CODE-PLATFORM-046 | refuter (static trace, no branch) | — | moduleForPlugin throw is caught by loadPlugin/runtime.detach on both paths; only cosmetic leftover (open panels not closed). Optional code-quality cleanup only. |

## tier4 (1)

| id | branch | reason |
|---|---|---|
| R15-DOCS-026 | worktree-agent-lows-NEW-drafted-4c6dfe8 | Fix requires editing the locked CLAUDE.md (Tier-1). Recommendation recorded, nothing touched. |

---

## Branch grouping for the partition candidates (lead's default — re-cuttable)

**P1** (CN branches of P1 entries + deferred-A):
- worktree-agent-lows-CN-r15-code-research-005-4c6dfe8
- worktree-agent-lows-CN-r15-code-agent-031-4c6dfe8
- worktree-agent-lows-CN-r15-code-data-019-4c6dfe8 *(partition tag inferred, not explicit in source — re-check)*
- worktree-agent-lows-DEF-A-4c6dfe8

**P2** (CN branches of P2 entries + deferred-B):
- worktree-agent-lows-CN-r15-lifecycle-035-4c6dfe8
- worktree-agent-lows-CN-r15-code-frontend-027-4c6dfe8
- worktree-agent-lows-DEF-B-4c6dfe8

**P3** (CN branches of P3 entries + new-lows and LEAD-036):
- worktree-agent-lows-CN-r15-agent-077-4c6dfe8
- worktree-agent-lows-CN-r15-data-102-4c6dfe8
- worktree-agent-lows-NEW-drafted-4c6dfe8
- worktree-agent-lows-LEAD-036-4c6dfe8

Refuter verdicts (R15-LEAD-025, R15-CODE-PLATFORM-045, R15-CODE-PLATFORM-046) carry no branch — verified by static trace only, REFUTE.md committed in the main worktree at d6daad0a (not pushed).

## Branch verification (git ls-remote origin, post fetch --prune)

All 11 reported branches present on origin with heads matching the writer-reported head_sha exactly. No mismatches, no missing branches.
