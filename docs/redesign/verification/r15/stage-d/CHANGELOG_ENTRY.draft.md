<!-- DRAFT at 6bc6d378cbbf9cfbefd8d155e027c2dc80214331 by the Stage D gap-check pass; refresh before rc2 -->
<!-- Facts sourced only from RELEASE_NOTES.draft.md and FACTS.md (both in this directory), per this task's brief. -->
<!-- To promote: strip this header comment and the trailing "Promotion note" section, then insert the body below
     into CHANGELOG.md immediately above the "## R15 rc1 gate — round 1 (2026-09-25)" heading (newest-first order). -->

## v0.9.0 — R15: trading removed, relicensed, Stage C fix batches (2026-09-23 – 2026-09-26)

**Scope:** the R15 census-and-repair cycle on `004-r4-experience-rebuild`, from base tag
`r13-bedrock`. Trading was removed from the product permanently (D81, operator Tier-4
sign-off), the core was relicensed AGPL-3.0 → PolyForm Strict 1.0.0 + commercial (D83),
and the R15 register — 887 raw findings, closed to 603 entries at D84's Gate-2
adjudication, grown to 652 entries as further lead-found `R15-LEAD-*` entries were
admitted during Stage C (16 critical / 116 high / 293 medium / 227 low, plus 76
rejections) — was worked down across 22 Stage-C batches plus an rc1 gate round, each
merged `--no-ff` from an isolated integrator worktree and each independently verified
fresh-context before merge. As of `4c6dfe8c` (batch 24 merged `6778f892`): 391 entries
`fixed`, 205 `open`, 26 `blocked_tier4` (operator-attended), 14 `removed_with_feature`
(trading, D81), 11 `needs_gui`, 5 `not_a_defect`. Open critical/high/medium is **zero**
— `R15-LEAD-035` (medium, agent-tools) moved to `blocked_tier4` at `4c6dfe8c` as an
escalation under the operator's three-failure rule, not a fresh-verifier concurrence;
the 205 open entries are all low severity. No `r15-rc1` tag exists yet as of this entry;
round 1 of the rc1 gate **FAILED** against an earlier candidate and drove several of the
batch-12..22 fix rounds, and round 2 is running from `4c6dfe8c`.

**What changed for you:**

- Workspaces autosave through one gated, debounced pipeline instead of several ad hoc
  paths; a saved workspace now restores portfolios, watchlist and notes correctly even
  if a panel in the saved layout no longer exists, and research spaces save under any
  name given.
- The AI copilot's automatic ("AUTO") actions are scoped to panel, chart and watchlist
  changes only — anything that writes data or changes a setting always stops for review
  first, with typed step-by-step notices instead of guessed status text.
- A ticker picked from the command palette loads straight into the chart; the chat's
  focused-symbol handling is more consistent with what is on screen.
- Sidecar connection problems (a dead or restarting local data engine) surface as
  plain-language errors instead of hanging requests or silent failures; each panel
  fails independently instead of taking the rest of the window down with it.
- Model/provider setup states why a key or connection failed, and a banner states when
  the selected model cannot be reached; a working key added now replaces a dead
  keyless default instead of silently coexisting with it.
- Chart drawings are correctly scoped per symbol and timeframe; indicator overlays no
  longer duplicate on repeated loads.
- Portfolio quote failures show a staleness indicator instead of a wrong number; the
  portfolio CSV export carries a currency column and no longer mixes currencies in
  Weight %.
- Several research- and data-quality issues in Indian-market coverage (BSE/NSE
  identity, corporate disclosures, fundamentals cross-checked against exchange
  filings) were corrected.

**Removed: trading (D81).** Trading was removed from the product permanently, operator
Tier-4 sign-off. No broker connection, order placement, or paper/live trading account
remains anywhere in the app; the manually tracked Portfolio panel (holdings entered by
hand, P&L, CSV export) is not trading and stays.

**Relicensed (D83).** The core moved from AGPL-3.0 to PolyForm Strict 1.0.0 (free,
noncommercial) plus a commercial license for anything else. The plugin contract and the
example plugin are carved out under Apache-2.0. Every commit before the relicensing
commit remains available under its original AGPL-3.0 terms.

**Decisions (D-numbers since `r13-bedrock`, full text and rationale in
`docs/redesign/DECISIONS.md`):**

- **D81** — trading removed from the product permanently (operator Tier-4 sign-off);
  reverses BLUEPRINT §2 (locked) and touches the §6.5 safety surface.
- **D82** — OpenAI-direct run spend cap set to $8.00, enforced structurally in
  `scripts/r15/vy.py`.
- **D83** — core relicensed AGPL-3.0 → PolyForm Strict 1.0.0; plugin contract + example
  plugin carved out under Apache-2.0; every pre-relicense commit stays AGPL-3.0.
- **D84** — Gate 2 (R15 census) adjudicated closed: 887 raw findings → 603 entries.
- **D85–D92** — trading-removal-plan riders (first-launch terms dialog rewritten with
  no kill-switch promise; planner keeps buy/sell edit signals, drops order-phrase
  signals; "paper portfolio" becomes "portfolio" everywhere; BLUEPRINT §6.5 retitled,
  section number kept; `registry_v0_6_5.py` deleted; workspace restore never drops user
  data on an unknown panel; India EOD-only data error no longer suggests connecting a
  broker; no automatic purge of leftover broker secrets/audit history, operator
  decision).

**Known limitations at rc1 — agent chat with a keyless local model.** With a keyless
local model, the agent can fabricate a figure or claim a completed write when it has no
tool result to ground the claim. Four register entries track this class:
`R15-LEAD-030` (high), `R15-LEAD-035` (medium), `R15-LEAD-037` (medium), `R15-LEAD-038`
(medium) — all `blocked_tier4` as of `4c6dfe8c` (030/037/038 via fresh-verifier
concurrence, 035 via the operator's three-failure escalation rule; see
`DECISIONS_FOR_OPERATOR.md` §4.9–4.12). A portfolio write never auto-applies regardless:
data-write changes always stage for review, and AUTO skips review only for panel, chart
and watchlist changes (`types/proposed-change.ts:38-46`). There is no `audit_orders`
table — D81 removed it with trading. Full wording for each entry is in
`docs/redesign/verification/r15/stage-d/RELEASE_NOTES.draft.md`, "Known limitations at
rc1".

**Carried forward / not yet done at this sha:**

- Version reads `0.8.0` across every source-of-truth file
  (`package.json`, `src-tauri/Cargo.toml`, `src-tauri/tauri.conf.json`, `sidecar/app.py`,
  `src/lib/plugin-bootstrap.ts` `HOST_VERSION`, `src-tauri/Cargo.lock`); a version-bump
  branch (`worktree-agent-r15-version-0.9.0`) is prepared separately and merges right
  after the `r15-rc1` tag.
- No code-signing, no release workflow, no auto-updater wiring — all Tier-4, blocked on
  the operator.
- CI has never had a green run on `004-r4-experience-rebuild`.
- The rc1 gate has run once (round 1, FAIL, against an earlier candidate) and round 2 is
  running from `4c6dfe8c`; confirm the gate's final verdict, and any tag name/sha, at
  the tag.

<!-- Promotion note (strip before landing in CHANGELOG.md): this entry covers the
     release-level v0.9.0 summary only. CHANGELOG.md has no per-batch section for Stage C
     batches 18-22 (RELEASE_NOTES.draft.md sourced those one-liners from each batch's own
     VERDICTS.md header instead, and its own note calls that "a real gap for the lead to
     close... not something this wave can write on their behalf") — this draft does not
     attempt those five per-batch entries either; they remain open (see STAGE_D_GAPS.md
     item 2b). Re-verify the register counts, blocked_tier4 total, and rc1-gate-round-2
     verdict against the sha actually being tagged before pasting this in — the figures
     above are accurate as of `4c6dfe8c` / `4d893147`, not necessarily the rc2 candidate
     sha. -->
