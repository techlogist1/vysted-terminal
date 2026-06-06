# R5 — Overnight Build Report (Experience-Layer Redesign)

> R5 pass. Branch `004-r4-experience-rebuild`. Lead: Opus 4.8 (ultracode). Base: `e087ccb` (Phase 0).
> Prior R4 Session-3 report preserved at `OVERNIGHT_BUILD_REPORT_R4S3.md`. Version frozen `0.8.0`; no merge to main.

## Outcome in three honest buckets

### ✅ VERIFIED (real-app screenshot, AAPL loaded — see `verification/COMPARISON_R5.html`)

| Surface              | Proof                                                                |
| -------------------- | -------------------------------------------------------------------- |
| Equity overview (#1) | `r5/r5-02-equity-aapl.png`, `r5/r5-06-equity-statements.png`         |
| Notes (#2)           | `r5/r5-05-notes.png`                                                 |
| ⌘K palette (#3)      | `r5/r5-03-cmdk-palette.png`                                          |
| Composer (#4)        | `r5/r5-05-notes.png` (bottom-left)                                   |
| Left dock (#5)       | `r5/r5-07-cockpit-overview.png`                                      |
| One scale (#6)       | code-grep gate: 0 `text-[…]`/`rounded-[…]`/off-grid in changed files |

### ⚠️ NEEDS-MANUAL-CHECK

- **Keychain re-prompt (#7).** Fix shipped (`pnpm tauri:dev` re-signs the debug binary with a stable
  self-signed identity each rebuild; `scripts/macos-dev-setup.sh` sets the partition list). Cannot be
  screenshot-proven — the operator runs the one-time cert creation (`docs/redesign/KEYCHAIN_DEV_SIGNING.md`),
  clicks "Always Allow" once, and confirms no re-prompt across a rebuild. `tauri.conf.json` (Tier-1) untouched.

### ❌ BROKEN

- None outstanding. One defect was found and fixed during verification (statement snake_case labels, #1a).

## What shipped (per surface)

- **Phase 0 (lead foundation, `e087ccb`):** `group-heading-style` @utility (fixes invisible ⌘K headers),
  `.notes-prose` (locks Tiptap output to the type scale), `EmptyState` dense variant, Button off-grid fix,
  PRODUCT_DESIGN_DECISIONS §11–§16, R5 component inventory + craft checklist.
- **Data panels:** shared `src/components/DataTable.tsx` (right-aligned tabular numerics, period columns,
  grouped sections, 3 tiers, graceful nulls, sortable/sticky/action-col); unified `src/lib/format.ts`
  (`formatUnit` K/M/B/T/Q — the missing-B fix, `formatPrice`, precision-safe `groupDigits`); equity-overview
  rebuilt as a Bloomberg-grade statement; screener/watchlist/analyst×2/sec×2/portfolio migrated; earnings
  unified; per-module formatters deleted. `humanizeLineLabel` (lead follow-up) kills statement snake_case.
- **Notes:** `NotesToolbar.tsx` (all controls, amber-active, `useSyncExternalStore` for active state);
  `.notes-prose`; border-only popovers; export/persistence/wikilinks preserved.
- **⌘K palette:** composed empty state; empty-query Recent + curated Suggested; sans input; off-scale fixes;
  truncation + fixed-filter preserved.
- **Composer + dock:** input+send one unit with reserved glyph gutter; toolbar density h-8→h-9; hero empty
  state fills the column (mt-auto/mb-auto + distributed chips).
- **Layout:** dock 380→310 (min 320→280), chart fraction 0.55→0.60, chat-sidebar floor 280.
- **Consistency sweep:** 37 `text-[…]` + 1 `rounded-[…]` + ~38 off-grid values → tokens across
  Settings/Onboarding/Plan/Research/DataBadges.
- **Keychain:** runbook + setup script + `tauri:dev` re-sign wrapper + CLAUDE.md gotcha.
- **Systemic fix (lead):** `src/lib/utils.ts` `cn` made scale-aware (`extendTailwindMerge`) — the
  unconfigured tailwind-merge was silently dropping the custom font sizes across ~90 files (a root cause of
  the "inconsistent sizing" prior passes fought).

## Verification gates

- `tsc --noEmit`: clean. `eslint .`: 0 errors (1 pre-existing exhaustive-deps warning). `prettier --check`:
  clean. `vitest`: **1062/1062** pass (the previously-failing EmptyState tier test now passes via the cn fix).
- No Rust/Python source changed this pass → cargo/clippy/ruff/pytest gates unaffected; sidecars present & fresh
  (no Python delta), confirmed via the staleness-aware ensure.

## Autonomous decisions (Tier 2/3)

- Full data-panel standardization (all 7 tabular panels), not equity-overview-only — per §6 "one system".
- Phase 0 narrowed to the cross-cutting files lead must own (globals.css, button, EmptyState); `DataTable`
  - `format.ts` went with their sole consumer (data-panels) so the API was designed by its caller.
- `docs/redesign/verification/*.html` added to `.prettierignore` (generated artifacts).
- Notes needed **zero** new deps — StarterKit v3 already bundles `@tiptap/extension-link` + lists.

## Multi-agent telemetry

| Agent / phase      | Model  | Output tokens | Tool uses | Wall (s) |
| ------------------ | ------ | ------------- | --------- | -------- |
| Explore (9-way)    | mixed  | 607,784       | 333       | 522      |
| data-panels        | opus   | 299,388       | 192       | 2,131    |
| consistency        | sonnet | 124,926       | 104       | 579      |
| notes              | opus   | 119,840       | 58        | 528      |
| chat-experience    | opus   | 107,331       | 43        | 350      |
| palette            | sonnet | 77,225        | 36        | 418      |
| keychain           | sonnet | 63,115        | 44        | 328      |
| layout             | sonnet | 61,276        | 26        | 194      |
| **Teammate total** |        | **~1.46M**    | **836**   | —        |

- 7 teammates, file-disjoint, isolation:worktree; all merged clean (3-way, no conflicts).
- One stale-base hazard observed and neutralized: the Agent tool reused prior-session worktree branches
  (`worktree-agent-palette`/`-notes`) on stale bases; the mandated `git reset --hard e087ccb` first-step
  fixed it. The `notes` teammate correctly **refused to clobber** the stale `worktree-agent-notes` and
  published to its harness branch instead — integrated from there.

## Carry-forward

- #7 keychain: operator one-time cert + Always-Allow + rebuild confirmation.
- `humanizeLineLabel` is equity-local; if other panels later surface raw API keys, promote it to a shared util.
- Consider a lint rule forbidding arbitrary `text-[…]` in new commits (the scale is now fully enforced).
