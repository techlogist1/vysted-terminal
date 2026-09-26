# RESULT — lows-deferred-A

Base: 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2
Branch: worktree-agent-lows-DEF-A-4c6dfe8
Writer role: R15 burst window, WRITER (Sonnet), cross-set deferred lows.
Off-lane rule honored throughout: no pytest/vitest/cargo/pnpm ci-local/typecheck/tsc/eslint/rig/app/model was run. `python3 -m py_compile` and `ruff` N/A (no Python source changed). `pnpm exec prettier` could not run in this worktree (no `node_modules` — a fresh worktree checkout, installing deps is off-lane); the one test edit was hand-matched to the surrounding file's existing style (2-space indent, `it(...)` block shape) instead.

## R15-AGENT-065

- outcome: not_a_defect_proposed
- commit: (none — no diff)
- test: (none)
- files: docs/CURRENT_STATE.md (read only), docs/BLUEPRINT.md (read only)
- note: The fix_shape asked only to confirm BLUEPRINT.md carries the same Deferred caveat as CURRENT_STATE.md (no code fix). At BASE, CURRENT_STATE.md already documents both builds as Deferred in three places — the table rows at docs/CURRENT_STATE.md:839-840 ("Copilot roster depth (`/agents/roster`, 3-pane panel, `delegate_to_persona`)" -> Deferred, BLOCKERS Phase-10 #5; "Customizability follow-ups (connector hub, panel gallery, saved screens)" -> Deferred, BLOCKERS Phase-10 #6) and the REBUILD prose at :905 ("The deferred roster depth ... is the natural first build."). `grep -n "roster\|connector hub\|data-source\|persona hand-off" docs/BLUEPRINT.md` returns no hit that claims either build exists or is shipped — BLUEPRINT.md makes no contradicting claim for CURRENT_STATE.md to be reconciled against, so there is nothing to edit there. The register's own note already reaches the same place: the underlying code facts (no `/agents/roster` route, no `delegate_to_persona`, PluginManagerPanel shows only a count) are unchanged and undisputed; the only live question is a roadmap-vs-defect classification the operator already settled once in the register's `note` field ("A documented, deliberately deferred build ... is a roadmap item, not a defect"). No code or doc diff to make.

## R15-AGENT-085

- outcome: deferred_feature
- commit: (none — build nothing per rule)
- test: (none written — this is a size estimate, not an implementation)
- files (read only): types/brief.ts, src/modules/equity-overview/EquityOverviewPanel.tsx, src/modules/chat/ChatSidebar.tsx, sidecar/services/agent_runtime.py, sidecar/agents/copilot.json
- note: Confirmed the gap is real at BASE — citation/`[unverified]` machinery exists only for brief.ts's `BriefSource`/`structured` contract and the Equity Overview narrative (`NarrativeSection` at EquityOverviewPanel.tsx:335+ renders "verified against"/"grounded in" + a `[unverified]` token); ChatSidebar.tsx's `/sources` command only opens BriefPanel, and a plain tool-grounded chat answer carries no per-turn sources footer. Per PARTITION.json's own `deferred` entry for this id: "Inseparable: a per-turn tool-provenance stream event spans agent_runtime.py (runtime-catalog) and types/ai.ts + streaming.ts + ChatSidebar.tsx (llm-chat); the alternative close (scope Constitution Principle VI to briefs/narratives) is a spec/constitution decision. Run after both merge." That dependency still holds in this isolated BASE worktree — the runtime-catalog and llm-chat sets have not landed here, so touching agent_runtime.py's round/streaming loop and the wire contract in isolation risks colliding with that concurrent work on the same risk-critical file (opus-owned per CLAUDE.md model assignment). The fix itself is a genuine new subsystem, not a low-sized diff: (1) a new stream-event shape carrying per-turn tool id + provider + as-of, threaded through agent_runtime.py's round loop, (2) a wire-contract addition in types/ai.ts + services/streaming.ts, (3) a new sources-footer renderer in ChatSidebar.tsx reusing the brief's source-chip component, (4) tests across both the sidecar stream and the frontend render path. Size estimate: M (roughly 0.5-1 day for one focused writer, once the two prerequisite sets are merged) — building nothing here per the "feature build, not a low fix" rule.

## R15-AGENT-086

- outcome: not_a_defect_proposed
- commit: (none — no diff)
- test: (none)
- files: sidecar/services/run_manager.py (read), sidecar/routers/runs.py (read), sidecar/services/agent_tools/catalog.py (read)
- note: `pause_run` as a named function is gone from run_manager.py; the only `"paused"` reference left is the driver setting the status inline at run_manager.py:316. The module docstring (run_manager.py:23-34, "Human-in-the-loop (FR-028)") already states the current mechanism accurately: an `ask_user` capability the model calls, which stops the turn and parks the run `paused` with the question (citing R15-CODE-AGENT-011 by name at :26), resumed by `answer_run`. `ask_user` is a registered capability in catalog.py:1201 and is referenced by run_manager.py at :173 and :294. This matches the register's own triage note verbatim ("Fixed under a different id (CODE-AGENT-011) in batch 7; pause_run as a named function is gone, the driver sets 'paused' inline") — reasserted at this sha, no diff.

## R15-CODE-FRONTEND-031

- outcome: not_a_defect_proposed
- commit: (none — no diff)
- test: (none)
- files: src/store/proposed-changes.ts (read), src/modules/chat/ChatSidebar.tsx (read)
- note: `enqueue` already returns `{ id: string; outcome: Promise<ChangeOutcome> }` (src/store/proposed-changes.ts:80, :101-130) rather than only an id. Both ChatSidebar.tsx call sites narrate from the resolved outcome, not synchronously: `enqueueSlashChange` (:604-621) does `void outcome.then((status) => setStatusLine(...changeOutcomeLine(id, status)))`, and the tool-call handler (:1022-1042) does `void outcome.then((status) => appendToolStep(assistantId, changeOutcomeLine(id, status)))`. `grep -n autoApplies src/modules/chat/ChatSidebar.tsx` returns nothing — the duplicated auto-apply predicate the fix_shape named for deletion is already gone. Matches the register's triage note ("The duplicated auto-apply predicate the fix_shape named is gone too: no autoApplies import remains in ChatSidebar.tsx") — reasserted at this sha, no diff.

## R15-CODE-FRONTEND-033

- outcome: fixed_untested
- commit: 97d2f1f0 "test(host-actions): pin arrange_layout focus alias resolution (R15-CODE-FRONTEND-033)"
- test: src/lib/host-actions.test.ts — new `it("arrange_layout pattern=focus resolves a panel ALIAS, matching focus_panel", ...)` using the "screener" -> "screener-panel" alias (never run per the off-lane rule; written as source only)
- files: src/lib/host-actions.test.ts
- note: The source fix itself was already present at BASE — the `arrange_layout` intent parser (host-actions.ts:973-982) already computes `target: resolvePanelToken(panel) ?? null` exactly like `focus_panel` does (:970-972), and the apply-time `focus` branch (host-actions.ts:~1600) already reads `intent.target` via `findOpenPanel(intent.target)` rather than looking the panel up by raw id. No source diff was needed or made. The register's own residual note flagged the real gap: no test pinned the alias case, because the two existing tests both use `panel: "chart"` whose alias equals its registered id (host-actions.test.ts:103,114), so a lookup-by-raw-id bug would never fail them. Added the P7 pin using `screener` (alias) vs `screener-panel` (registered id) — mirrors the existing `open_panel('screener')` alias test (host-actions.test.ts:126-140) applied to `arrange_layout`+`focus`. This is a test-only diff (`fix_shape`'s "pin with the P7 test"), acceptance test written as source per the off-lane rule, not run.

## Summary

| id | outcome | commit |
|---|---|---|
| R15-AGENT-065 | not_a_defect_proposed | — |
| R15-AGENT-085 | deferred_feature (size M) | — |
| R15-AGENT-086 | not_a_defect_proposed | — |
| R15-CODE-FRONTEND-031 | not_a_defect_proposed | — |
| R15-CODE-FRONTEND-033 | fixed_untested (test-only) | 97d2f1f0 |

No order-safety-surface file was touched. No Tier-1 locked file was touched. Nothing in `docs/redesign/verification/R15_BRIEF*.md` or `docs/redesign/verification/r15/local/` was read. The banned word was not written.
