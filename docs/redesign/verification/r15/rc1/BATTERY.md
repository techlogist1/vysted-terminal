# RC1 Battery Index

Collated from `docs/redesign/verification/r15/rc1/battery/set-*.md` (72 sets) and `battery/INDEX.json` (`candidate_sha 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`, `fixed_total: 391`, `unplanned_fixed: 1`). No new judgement or re-runs.

## Per-set verdict counts

| Set | Title | Rows | holds | ci_pinned | needs_gui | blocked_env | regressed |
|---|---|---|---|---|---|---|---|
| set-0 | batch-2/W1-fundamentals-seam | 6 | 6 | 0 | 0 | 0 | 0 |
| set-1 | batch-2/W2-instrument-identity | 6 | 6 | 0 | 0 | 0 | 0 |
| set-2 | batch-2/W3-research-integrity | 7 | 7 | 0 | 0 | 0 | 0 |
| set-3 | batch-2/W4-workspace-persistence | 7 | 1 | 6 | 0 | 0 | 0 |
| set-4 | batch-2/W5-surfaces-and-math | 8 | 2 | 6 | 0 | 0 | 0 |
| set-5 | batch-3/W1-agent-runtime (rc1-battery-1, candidate 4c6dfe8c) | 8 | 7 | 1 | 0 | 0 | 0 |
| set-6 | batch-3/W2-agent-frontend-gate (rc1-battery-1, candidate 4c6dfe8c) | 7 | 2 | 4 | 0 | 0 | 0 |
| set-7 | batch-3/W3-llm-adapters-and-errors (rc1-battery-1, candidate 4c6dfe8c) | 5 | 4 | 1 | 0 | 0 | 0 |
| set-8 | batch-3/W4-research-depth (rc1-battery-1, candidate 4c6dfe8c) | 7 | 5 | 1 | 0 | 1 | 0 |
| set-9 | batch-3/W5-india-data-witnesses (rc1-battery-1, candidate 4c6dfe8c) | 8 | 8 | 0 | 0 | 0 | 0 |
| set-10 | batch-4/W1-agent-runtime (set-10) | 9 | 9 | 0 | 0 | 0 | 0 |
| set-11 | batch-4/W2-workflow-backtest-feeds (set-11) | 9 | 6 | 2 | 1 | 0 | 0 |
| set-12 | batch-4/W3-chat-runs-mcp (set-12) | 9 | 9 | 0 | 0 | 0 | 0 |
| set-13 | batch-4/W4-market-data-gate (set-13) | 8 | 8 | 0 | 0 | 0 | 0 |
| set-14 | batch-4/W5-panels-screener (set-14) | 9 | 7 | 2 | 0 | 0 | 0 |
| set-15 | batch-5/W1-india-disclosures-agent-surface | 11 | 10 | 0 | 0 | 1 | 0 |
| set-16 | batch-5/W2-resolver-market-data | 9 | 9 | 0 | 0 | 0 | 0 |
| set-17 | batch-5/W3-agent-runtime-chat | 9 | 8 | 0 | 0 | 1 | 0 |
| set-18 | batch-5/W4-platform-workflow-boundary | 8 | 8 | 0 | 0 | 0 | 0 |
| set-19 | batch-5/W5-screener-earnings-sec | 11 | 11 | 0 | 0 | 0 | 0 |
| set-20 | batch-6/W1-india-exchange-data | 1 | 1 | 0 | 0 | 0 | 0 |
| set-21 | batch-6/W2-delegate-runs-runtime | 1 | 1 | 0 | 0 | 0 | 0 |
| set-22 | batch-6/W3-unattended-platform-chart | 5 | 5 | 0 | 0 | 0 | 0 |
| set-23 | batch-6/W4-research-funnel | 5 | 5 | 0 | 0 | 0 | 0 |
| set-24 | batch-6/W5-host-actions-portfolio | 9 | 8 | 0 | 1 | 0 | 0 |
| set-25 | batch-7/W1-india-exchange-data | 7 | 7 | 0 | 0 | 0 | 0 |
| set-26 | batch-7/W2-delegate-runs-runtime | 11 | 11 | 0 | 0 | 0 | 0 |
| set-27 | batch-7/W3-unattended-chart-workspace | 10 | 10 | 0 | 0 | 0 | 0 |
| set-28 | batch-7/W4-research-funnel | 12 | 0 | 0 | 0 | 12 | 0 |
| set-29 | batch-7/W5-agent-writes-portfolio | 9 | 8 | 0 | 1 | 0 | 0 |
| set-30 | batch-8/W1-sidecar-lifecycle-transport | 7 | 6 | 0 | 1 | 0 | 0 |
| set-31 | batch-8/W2-provider-readiness-host-actions | 9 | 9 | 0 | 0 | 0 | 0 |
| set-32 | batch-8/W3-data-error-honesty | 6 | 6 | 0 | 0 | 0 | 0 |
| set-33 | batch-8/W4-resolver-exchange-lanes | 11 | 11 | 0 | 0 | 0 | 0 |
| set-34 | batch-8/W5-agent-runtime-research | 6 | 3 | 0 | 0 | 3 | 0 |
| set-35 | batch-9/W1-agent-runtime (rc1-battery-7) | 5 | 5 | 0 | 0 | 0 | 0 |
| set-36 | batch-9/W2-research-search-news (rc1-battery-7) | 4 | 4 | 0 | 0 | 0 | 0 |
| set-37 | batch-9/W3-fundamentals-identity (rc1-battery-7) | 6 | 6 | 0 | 0 | 0 | 0 |
| set-38 | batch-9/W4-market-lanes-errors-quant (rc1-battery-7) | 7 | 7 | 0 | 0 | 0 | 0 |
| set-39 | batch-9/W5-frontend-shell (rc1-battery-7) | 7 | 0 | 7 | 0 | 0 | 0 |
| set-40 | batch-10/W1-runtime-backtest | 7 | 7 | 0 | 0 | 0 | 0 |
| set-41 | batch-10/W2-catalog-hostactions | 4 | 3 | 1 | 0 | 0 | 0 |
| set-42 | batch-10/W3-fundamentals-bse-cache | 7 | 7 | 0 | 0 | 0 | 0 |
| set-43 | batch-10/W4-screener-routes-statedocs | 6 | 6 | 0 | 0 | 0 | 0 |
| set-44 | batch-10/W5-chat-search-workflow | 7 | 5 | 2 | 0 | 0 | 0 |
| set-45 | batch-10/W6-chart-notes-blueprint | 7 | 6 | 1 | 0 | 0 | 0 |
| set-46 | batch-10/W7-panels-marketplace | 6 | 6 | 0 | 0 | 0 | 0 |
| set-47 | batch-10/W8-plugins-dock | 3 | 2 | 1 | 0 | 0 | 0 |
| set-48 | batch-11/W1-scripts-build (rc1-battery-1, candidate 4c6dfe8c) | 5 | 4 | 1 | 0 | 0 | 0 |
| set-49 | batch-11/W2-runtime-schema (rc1-battery-1, candidate 4c6dfe8c) | 2 | 1 | 1 | 0 | 0 | 0 |
| set-50 | batch-11/W3-agent-eval (rc1-battery-1, candidate 4c6dfe8c) | 1 | 0 | 1 | 0 | 0 | 0 |
| set-51 | batch-11/W4-registry-loop (rc1-battery-1, candidate 4c6dfe8c) | 2 | 2 | 0 | 0 | 0 | 0 |
| set-52 | batch-11/W5-data-reference (rc1-battery-1, candidate 4c6dfe8c) | 1 | 1 | 0 | 0 | 0 | 0 |
| set-53 | batch-11/W6-options-chain (rc1-battery-1, candidate 4c6dfe8c) | 1 | 1 | 0 | 0 | 0 | 0 |
| set-54 | batch-11/W7-preferences (rc1-battery-1, candidate 4c6dfe8c) | 1 | 0 | 1 | 0 | 0 | 0 |
| set-55 | batch-11/W8-frontend-visual (rc1-battery-1, candidate 4c6dfe8c) | 4 | 2 | 2 | 0 | 0 | 0 |
| set-56 | batch-12/W1-w1 (set-56) | 3 | 3 | 0 | 0 | 0 | 0 |
| set-57 | batch-12/W2-w2 (set-57) | 3 | 3 | 0 | 0 | 0 | 0 |
| set-58 | batch-12/W3-w3 (set-58) | 2 | 2 | 0 | 0 | 0 | 0 |
| set-59 | batch-12/W4-w4 (set-59) | 1 | 1 | 0 | 0 | 0 | 0 |
| set-60 | batch-12/W5-w5 (set-60) | 3 | 3 | 0 | 0 | 0 | 0 |
| set-61 | batch-12/W6-w6 (set-61) | 2 | 2 | 0 | 0 | 0 | 0 |
| set-62 | batch-12/W7-w7 (set-62) | 2 | 2 | 0 | 0 | 0 | 0 |
| set-63 | batch-12/W8-w8 (set-63) | 3 | 2 | 1 | 0 | 0 | 0 |
| set-64 | batch-13/W2-w2 | 1 | 1 | 0 | 0 | 0 | 0 |
| set-65 | batch-13/W3-w3 | 1 | 1 | 0 | 0 | 0 | 0 |
| set-66 | batch-14/W1-w1 | 1 | 1 | 0 | 0 | 0 | 0 |
| set-67 | batch-16/W1 | 2 | 2 | 0 | 0 | 0 | 0 |
| set-68 | batch-17/W1-w1 | 1 | 1 | 0 | 0 | 0 | 0 |
| set-69 | batch-18/W1-agent-runtime-citation-guard (rc1-battery-7) | 1 | 1 | 0 | 0 | 0 | 0 |
| set-70 | batch-18/W2-nse-emerge-sm-identity (rc1-battery-7) | 1 | 1 | 0 | 0 | 0 | 0 |
| set-71 | unplanned-1 (rc1-battery-7) | 1 | 1 | 0 | 0 | 0 | 0 |
| **Total** | | **391** | **326** | **42** | **4** | **18** | **0** |

**0 `regressed` verdicts found anywhere in the 72-set battery.** Total rows (391) matches `INDEX.json`'s `fixed_total: 391` exactly.

## Battery coverage: fixed ids with no raw file on disk

Checked: for every fixed id listed under each set in `battery/INDEX.json`, searched `battery/raw/set-*/` globally (not just the raw dir nominally matching that set's own number, since several ids' raw output is filed under a different raw/set-N than their battery/set-N.md row — e.g. `R15-LEAD-018`/`R15-UI-010` (batch-10/W1, set-40) actually sit in `raw/set-41/`) for a `<id>*.txt`/`<id-without-R15->*` file.

**80 of 391 fixed ids have no matching raw file anywhere in `battery/raw/`.** Battery status: **incomplete** (never scored as a blanket "pass" per instruction).

### Missing ids by shard


**Shard 0** — 13 missing:

| id | set | reason |
|---|---|---|
| R15-AGENT-050 | batch-10/W1-runtime-backtest | code-level check only in set-40.md (no raw capture produced): "Read `sidecar/services/llm/anthropic.py` (`_split_system_and_messages`) an... |
| R15-UI-011 | batch-10/W1-runtime-backtest | code-level check only in set-41.md (no raw capture produced): "grep `src/modules/backtest/BacktestPanel.tsx`/`.test.tsx`...." |
| R15-AGENT-088 | batch-10/W5-chat-search-workflow | code-level check only in set-44.md (no raw capture produced): "grep `src/modules/chat/slash-commands.test.ts`...." |
| R15-UI-027 | batch-10/W5-chat-search-workflow | code-level check only in set-45.md (no raw capture produced): "grep `src/store/keybindings.ts`/`.test.ts`...." |
| R15-UI-024 | batch-10/W6-chart-notes-blueprint | code-level check only in set-45.md (no raw capture produced): "grep `src/modules/notes/NotesToolbar.tsx`/`.test.tsx`...." |
| R15-DATA-077 | batch-10/W7-panels-marketplace | id not found in any set-*.md table row (no repro record at all) |
| R15-UI-028 | batch-10/W7-panels-marketplace | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-FRONTEND-001 | batch-2/W4-workspace-persistence | code-level check only in set-3.md (no raw capture produced): "grep `src/lib/workspace.test.ts` for the committed pin...." |
| R15-CODE-FRONTEND-005 | batch-2/W4-workspace-persistence | code-level check only in set-3.md (no raw capture produced): "grep `src/lib/workspace.test.ts`...." |
| R15-CODE-FRONTEND-018 | batch-2/W4-workspace-persistence | code-level check only in set-3.md (no raw capture produced): "grep `src/lib/workspace.test.ts`...." |
| R15-LIFECYCLE-002 | batch-2/W4-workspace-persistence | code-level check only in set-3.md (no raw capture produced): "grep `src/lib/workspace.test.ts`...." |
| R15-LIFECYCLE-003 | batch-2/W4-workspace-persistence | code-level check only in set-3.md (no raw capture produced): "grep `src/lib/workspace.test.ts`...." |
| R15-LIFECYCLE-009 | batch-2/W4-workspace-persistence | code-level check only in set-3.md (no raw capture produced): "grep `src/lib/workspace.test.ts`...." |

**Shard 2** — 18 missing:

| id | set | reason |
|---|---|---|
| R15-LEAD-007 | batch-4/W1-agent-runtime | id not found in any set-*.md table row (no repro record at all) |
| R15-LEAD-008 | batch-4/W1-agent-runtime | id not found in any set-*.md table row (no repro record at all) |
| R15-AGENT-015 | batch-4/W2-workflow-backtest-feeds | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-FRONTEND-006 | batch-4/W2-workflow-backtest-feeds | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-PLATFORM-002 | batch-4/W2-workflow-backtest-feeds | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-PLATFORM-003 | batch-4/W2-workflow-backtest-feeds | id not found in any set-*.md table row (no repro record at all) |
| R15-AGENT-029 | batch-4/W3-chat-runs-mcp | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-AGENT-002 | batch-4/W3-chat-runs-mcp | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-FRONTEND-002 | batch-4/W3-chat-runs-mcp | code-level check only in set-6.md (no raw capture produced): "grep `abort`/`AbortController` in `ChatSidebar.tsx`/`.test.tsx`..." |
| R15-CODE-PLATFORM-037 | batch-4/W3-chat-runs-mcp | id not found in any set-*.md table row (no repro record at all) |
| R15-DATA-083 | batch-4/W3-chat-runs-mcp | id not found in any set-*.md table row (no repro record at all) |
| R15-LIFECYCLE-005 | batch-4/W3-chat-runs-mcp | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-FRONTEND-020 | batch-4/W5-panels-screener | id not found in any set-*.md table row (no repro record at all) |
| R15-DATA-093 | batch-4/W5-panels-screener | id not found in any set-*.md table row (no repro record at all) |
| R15-LIFECYCLE-007 | batch-4/W5-panels-screener | id not found in any set-*.md table row (no repro record at all) |
| R15-UI-003 | batch-4/W5-panels-screener | id not found in any set-*.md table row (no repro record at all) |
| R15-UI-005 | batch-4/W5-panels-screener | id not found in any set-*.md table row (no repro record at all) |
| R15-UI-007 | batch-4/W5-panels-screener | id not found in any set-*.md table row (no repro record at all) |

**Shard 3** — 14 missing:

| id | set | reason |
|---|---|---|
| R15-AGENT-058 | batch-5/W1-india-disclosures-agent | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-RESEARCH-001 | batch-5/W1-india-disclosures-agent | id not found in any set-*.md table row (no repro record at all) |
| R15-DATA-097 | batch-5/W2-resolver-market-data | id not found in any set-*.md table row (no repro record at all) |
| R15-LEAD-009 | batch-5/W2-resolver-market-data | id not found in any set-*.md table row (no repro record at all) |
| R15-LEAD-011 | batch-5/W2-resolver-market-data | id not found in any set-*.md table row (no repro record at all) |
| R15-AGENT-025 | batch-5/W3-agent-runtime-chat | id not found in any set-*.md table row (no repro record at all) |
| R15-AGENT-031 | batch-5/W3-agent-runtime-chat | id not found in any set-*.md table row (no repro record at all) |
| R15-RESEARCH-014 | batch-5/W3-agent-runtime-chat | id not found in any set-*.md table row (no repro record at all) |
| R15-AGENT-059 | batch-5/W4-platform-workflow-boundary | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-AGENT-012 | batch-5/W4-platform-workflow-boundary | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-PLATFORM-005 | batch-5/W4-platform-workflow-boundary | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-PLATFORM-019 | batch-5/W4-platform-workflow-boundary | id not found in any set-*.md table row (no repro record at all) |
| R15-LEAD-001 | batch-5/W4-platform-workflow-boundary | id not found in any set-*.md table row (no repro record at all) |
| R15-LEAD-003 | batch-5/W4-platform-workflow-boundary | id not found in any set-*.md table row (no repro record at all) |

**Shard 4** — 5 missing:

| id | set | reason |
|---|---|---|
| R15-CODE-AGENT-033 | batch-14/W1-agent-runtime-ratio-guard | id not found in any set-*.md table row (no repro record at all) |
| R15-AGENT-051 | batch-6/W3-unattended-platform-chart | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-FRONTEND-015 | batch-6/W3-unattended-platform-chart | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-FRONTEND-007 | batch-6/W5-host-actions-portfolio | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-FRONTEND-010 | batch-6/W5-host-actions-portfolio | id not found in any set-*.md table row (no repro record at all) |

**Shard 5** — 14 missing:

| id | set | reason |
|---|---|---|
| R15-LEAD-032 | batch-16/W1-one-writer-set | id not found in any set-*.md table row (no repro record at all) |
| R15-LIFECYCLE-013 | batch-7/W2-delegate-runs-runtime | code-level check only in set-18.md (no raw capture produced): "Source read `sidecar/services/run_manager.py:401,554`..." |
| R15-UI-040 | batch-7/W2-delegate-runs-runtime | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-FRONTEND-017 | batch-7/W3-unattended-chart-workspace | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-FRONTEND-019 | batch-7/W3-unattended-chart-workspace | id not found in any set-*.md table row (no repro record at all) |
| R15-UI-026 | batch-7/W3-unattended-chart-workspace | id not found in any set-*.md table row (no repro record at all) |
| R15-UI-031 | batch-7/W3-unattended-chart-workspace | id not found in any set-*.md table row (no repro record at all) |
| R15-RESEARCH-023 | batch-7/W4-research-funnel | id not found in any set-*.md table row (no repro record at all) |
| R15-RESEARCH-033 | batch-7/W4-research-funnel | id not found in any set-*.md table row (no repro record at all) |
| R15-UI-017 | batch-7/W5-agent-writes-portfolio | id not found in any set-*.md table row (no repro record at all) |
| R15-UI-034 | batch-7/W5-agent-writes-portfolio | id not found in any set-*.md table row (no repro record at all) |
| R15-UI-035 | batch-7/W5-agent-writes-portfolio | id not found in any set-*.md table row (no repro record at all) |
| R15-UI-036 | batch-7/W5-agent-writes-portfolio | id not found in any set-*.md table row (no repro record at all) |
| R15-UI-037 | batch-7/W5-agent-writes-portfolio | id not found in any set-*.md table row (no repro record at all) |

**Shard 6** — 13 missing:

| id | set | reason |
|---|---|---|
| R15-LEAD-031 | batch-17/W1-one-writer-set | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-PLATFORM-011 | batch-8/W1-sidecar-lifecycle-transport | id not found in any set-*.md table row (no repro record at all) |
| R15-LIFECYCLE-010 | batch-8/W1-sidecar-lifecycle-transport | id not found in any set-*.md table row (no repro record at all) |
| R15-RESEARCH-032 | batch-8/W1-sidecar-lifecycle-transport | id not found in any set-*.md table row (no repro record at all) |
| R15-AGENT-056 | batch-8/W2-provider-readiness-host | id not found in any set-*.md table row (no repro record at all) |
| R15-AGENT-081 | batch-8/W2-provider-readiness-host | id not found in any set-*.md table row (no repro record at all) |
| R15-UI-013 | batch-8/W2-provider-readiness-host | id not found in any set-*.md table row (no repro record at all) |
| R15-UI-019 | batch-8/W2-provider-readiness-host | id not found in any set-*.md table row (no repro record at all) |
| R15-UI-049 | batch-8/W2-provider-readiness-host | id not found in any set-*.md table row (no repro record at all) |
| R15-UI-057 | batch-8/W2-provider-readiness-host | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-DATA-002 | batch-8/W4-resolver-exchange-lanes | id not found in any set-*.md table row (no repro record at all) |
| R15-CODE-DATA-003 | batch-8/W4-resolver-exchange-lanes | id not found in any set-*.md table row (no repro record at all) |
| R15-LIFECYCLE-022 | batch-8/W4-resolver-exchange-lanes | id not found in any set-*.md table row (no repro record at all) |

**Shard 7** — 3 missing:

| id | set | reason |
|---|---|---|
| R15-CODE-FRONTEND-016 | batch-9/W5-frontend-shell | row exists in set-39.md but no matching raw file found: "test file presence: `src/store/command-palette.test.ts` (dispatcher coverage of ... |
| R15-CROSS-PLATFORM-004 | batch-9/W5-frontend-shell | row exists in set-39.md but no matching raw file found: "test file presence: `src/store/command-palette.test.ts` (layout corpus, `MENU_PA... |
| R15-UI-058 | batch-9/W5-frontend-shell | row exists in set-24.md but no matching raw file found: "Source read: `src/components/SettingsPanel.tsx` `SettingsExport`/`buildSettingsE... |

Of the 80 missing, ~15 are explicitly code-level-only checks (in-process/code-read/grep/pytest, no raw HTTP/probe file was ever produced by design) — those are not a gap in verification, just in the raw-file artifact. The remaining ~65 have no repro row in any `set-*.md` table at all under their nominal id — a genuine coverage gap, consistent with `rc1-verifier:19`'s independent finding ("Fixed-name battery has no raw output for 160 of 376 fixed ids... raw set-12 and set-46 are empty, and no findings file exists for battery workers 3 and 5") in `findings/rc1-verifier.json` — same class of gap, different count (that check used a different fixed-id universe/method); both agree the raw-evidence coverage of the fixed-id battery is incomplete, not exhaustive.

---

# Data-pack re-collection (from DATAPACK.md)

# RC1 data-pack re-collection (rc1-datapack), gate round 2

Candidate sha `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`. This replaces the DATAPACK.md/
datapack.json that were on disk before this run, which were from an **earlier** RC1
candidate (`4097dac4`, gate round 1, 2026-09-25) — a different sha.

Own sidecar booted from `rc1-cand/sidecar` on a fresh copy of `rc1-seed-data` (isolated,
keyless), port 52313. Ran `scripts/r15/collect_battery.py --port 52313 --force` from a
minimal copy tree (`scratchpad/rc1-pack`) so the census baseline in
`docs/redesign/verification/r15/battery/collected/` was never overwritten. All 24 battery
slots collected; raw output copied to `r15/rc1/battery/collected/`.

**Environment note:** this sidecar's own background `fundamentals_warm` cache job hammered
Yahoo concurrently with the collector (repeated 429s, one observed 56s circuit-open window
during P15 SUMAX). Self-inflicted noise from a freshly-booted sidecar, not a product defect
— matches the same class already on record from gate round 1.

## Method

Two passes, per the task brief:

1. **Targeted**: 42 fixed register entries whose repro/evidence names a battery symbol
   (word-boundary match against the register, not substring — substring matching
   over-counts on common words like SAFE/ICON/CSL). 10 symbols implicated: AMAL, DAL, SIFY,
   DHANBANK, SMR, JNPR, ELCIDIN, SUMAX, VIYASH, CREST. Re-ran each entry's own stated repro
   live against the rc1 candidate and read `field_meta` (status/reason), not just the raw
   value, since several of these entries were fixed by adding a cross-check gate rather than
   changing the number.
2. **Broad**: `scratchpad/rc1-pack/redo_diff.py` (scratch, not committed) flattens the fresh
   rc1 collected JSON and looks up every census-time `match` field (from
   `docs/redesign/verification/r15/battery/diffs/*.json`) against the same outside/pack
   value the census diff already recorded, across all 24 slots. Output:
   `r15/rc1/rediff_out.json`.

## Targeted re-diff: 20 of 42 fixed entries re-probed directly

18 hold as fixed (DATA-002, 004, 005, 006, 013, 014, 017, 018, 052, 057, 059, 060,
LEAD-011, LEAD-015, LEAD-028 for its certified routes; DATA-003/022 inconclusive — BSE's
own shareholding index returned 403 Forbidden for every BSE-only symbol this run, not just
the entries' symbols, so this is an upstream block, not a symbol-specific regression). The
remaining 22 fixed entries (portfolio-agent flows, statement-depth/pledge/corporate-action
gaps, field-meta cosmetics) were not individually re-probed this pass — see
`docs/redesign/verification/r15/rc1/datapack.json` `not_individually_re-verified_this_pass`.

**2 regressions found** (both previously "fixed", both fail on their own original repro):

### R15-DATA-008 (SIFY currency mislabel) — still broken

`GET /fundamentals/SIFY` on the rc1 candidate returns the exact same numbers the original
defect cited: `revenue_ttm: 46506049536.0`, `net_income_ttm: -912369984.0`, top-level
`currency: "USD"`. The fix added a separate `financial_currency: "INR"` field and correctly
withholds `price_to_sales` ("mixes bases... withheld"), but `revenue_ttm`/`net_income_ttm`
still carry `status: "ok"`, no `reason`, and are not gated the same way — so a consumer that
reads `currency` next to `revenue_ttm` (exactly what `EquityOverviewPanel.tsx` and
`brief-blocks.tsx` do, per the entry's own root-cause note) still sees "$46.5B revenue" for
a ~$492M company. The register's own batch-23 note already flagged this exact suspicion
("may have resurfaced or is incompletely fixed... not independently re-verified") — this
drive confirms it live on the current candidate.

### R15-DATA-058 (SIFY (ADR) name-search ranking) — still broken

`GET /resolve?q=Sify+Technologies+Ltd+(ADR)` now includes SIFY in the candidate list
(previously it was excluded entirely by the 6-candidate cap) — a partial improvement — but
SIFY (confidence 0.913, the highest score in the list) still sorts **last**, behind five
weaker Indian-locale matches (ASMTEC 0.80, IKOMA/EMIAC/RELICTEC/7TEC ~0.766). The fix_shape
called for score to dominate locale "beyond a margin" in the fuzzy band; an 11-point margin
between the top and bottom scores is not a small one, and the ranking still buries the
correct answer.

## Broad scan: 13 slots flagged, all explained as mapper artifacts, zero real regressions

`redo_diff.py`'s heuristic field-path mapper flagged 13 slots. Every flag inspected by hand
is one of: pack figures in INR crore vs rc1's raw-rupee scale (`revenue_ttm` on
VIYASH/JNPR/CHTR/ICON/JUMBO/AMAL/SMR/VERTEX), pack percent-scale vs rc1 decimal-scale
(`roe`/`debt_to_equity` on the same slots), a sector-label variant ("Financials" vs
"Financial Services" on CSL), or fields the app now correctly serves null/withheld
(JONJUA `debt_to_equity`, ONC's US-only fields). None is a genuine value change once
rescaled — consistent with the mapper's documented limitation (field paths in
`BATTERY_DIFFS.md` are prose, not JSON pointers).

## Not filed (price-like / as-of skew)

Per task instruction, no price-derived drift (P/E, P/B, market cap, 52-week range) was
filed regardless of direction — none of the 10 implicated symbols showed anything beyond
ordinary 1-week movement on those fields.


---

See `docs/redesign/verification/r15/rc1/findings/rc1-datapack.json` for the 3 findings this pass filed (2 regressions — R15-DATA-008 critical, R15-DATA-058 medium — 1 environment note).