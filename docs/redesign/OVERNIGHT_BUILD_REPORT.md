# Vysted R4 — Session 3 Build Report (plan + telemetry + honest status)

> **Branch:** `004-r4-experience-rebuild` · **Version frozen** `0.8.0` · **No merge to main.**
> **Mandate:** match the reference screenshots (`docs/redesign/references/`) in feel, fix every
> broken interaction, finish the Tier-C tail, keep the §6.5 safety floor 9/9 and Tier-1 LOCKED
> files byte-untouched. Design authority: `docs/redesign/PRODUCT_DESIGN_DECISIONS.md`.

Status legend: ☐ not started · ◐ in progress · ✅ verified (evidence) · 🔧 built, flagged · ❌ broken.

---

## The plan (phase-wise, each phase carries its own verification)

### Phase 0 — Foundation: Warm Graphite + amber + de-glow (LEAD, direct) ✅

Re-value the design system from cold-zinc/indigo to warm-graphite/amber; remove the body glow;
lockstep the 3 color sources; purge cold/clay comments; S-1/S-3/S-5a cleanup.

- **Files:** `styles/tokens.css`, `src/app/globals.css`, `src/lib/chart-theme.ts`,
  `NodeEditorPanel.tsx` grid color, `brief-blocks.tsx` comment, removed tongyi `.pyc`.
- **Verify:** `rg` finds zero `7e88e8`/cold-zinc literals outside intended; typecheck green;
  later — live computed-style read on the running app shows warm bg + amber `--accent-rgb`.

### Phase 1 — Design application + sizing pass (parallel, per region)

Apply PRODUCT_DESIGN_DECISIONS §4/§5/§8/§9 to every chrome/control region: grow the composer,
header, ⌘K palette, ticker search, pills/chips, data badges; install the 3 contrast tiers;
build the shared `<EmptyState>` and replace every dead-grey void.

- **Tracks (teammates):** (a) shell+header+composer, (b) ⌘K palette UI sizing, (c) pills/chips/
  badges + mention/slash pickers, (d) empty-states shared component + rollout, (e) research/brief
  reading column + equity-overview chrome.
- **Verify:** rig screenshots of each surface at 1920×1080 + 2560×1440, side-by-side vs reference;
  fresh design-review subagent; typecheck + vitest + format.

### Phase 2 — Broken interactions (parallel)

- **⌘K ranking** (`src/store/command-palette.ts`): match-quality dominates group offset; exact/
  prefix boost; cap per-group; "notes" ranks the Notes panel first. Verify by typing queries.
- **Notes export** (`NotesPanel.tsx` + Tauri): MD/PNG/PDF each write a real file via a Tauri
  binary-write command (PNG/PDF can't use browser download in WKWebView). Verify each file opens.
- **Brief export** (`BriefPanel.tsx`): add MD + PDF export mirroring notes. Verify both open.
- **Verify:** drive each in the real app; produce the file; screenshot evidence.

### Phase 3 — Screener cold-path backoff (sidecar)

`sidecar/services/screener.py _warm_loop`: exponential backoff + jitter on a 429 cycle; reset on
success; never sustain the throttle. Verify cold-batch timing on a clean network + unit tests.

### Phase 4 — Tier-C feature tail (parallel)

Research presentation depth (asset-class metrics, dedup'd sources rail + source-type badges,
in-place follow-up polish, table render); company-overview AI narrative + numeric-verification
pass; market-session awareness (FR-118) surfacing on quotes/chart; teach-the-agent first-run
suggestion chips; per-research-space agent memory (typed field + store + agent context).

- **Verify:** drive each; sidecar tests; rig screenshots of populated state.

### Phase 5 — Stale-code register remainder

S-2 (rewrite `docs/DESIGN_SYSTEM.md` to Warm Graphite), S-6/S-7 (brief mode/step casing↔wire),
S-8 (asset-class metric branch — folds into Phase 4), S-15/S-16/S-18/S-19 unify, S-17 stageable
actions, S-10/S-14 model/backend review. §G CLAUDE.md items → operator (build does NOT edit).

### Phase 6 — Verification & close

Kill stale Vysted procs only (never Claude/Cursor); rebuild sidecar `--onefile` + smoke-test;
clean build + reload; rig screenshots populated; side-by-side comparison sheet under
`docs/redesign/verification/`; fresh design reviewer can't tell apart; adversarial diff review;
safety floor (§6.5 9/9, Tier-1 untouched, brokers read-only, keyless-first, version 0.8.0);
three-bucket honest report. Push to 004. No merge.

---

## Live status board

| Phase | Track                               | Status | Evidence                                              |
| ----- | ----------------------------------- | ------ | ----------------------------------------------------- |
| 0     | Warm Graphite + amber + de-glow     | ✅     | rg-clean of cold literals; typecheck (pending result) |
| 1     | Shell/header/composer sizing        | ☐      |                                                       |
| 1     | ⌘K palette UI sizing                | ☐      |                                                       |
| 1     | Pills/chips/badges/pickers          | ☐      |                                                       |
| 1     | Empty-state component + rollout     | ☐      |                                                       |
| 1     | Research/overview reading column    | ☐      |                                                       |
| 2     | ⌘K ranking fix                      | ☐      |                                                       |
| 2     | Notes export MD/PNG/PDF             | ☐      |                                                       |
| 2     | Brief export MD/PDF                 | ☐      |                                                       |
| 3     | Screener cold-path backoff          | ☐      |                                                       |
| 4     | Research presentation depth         | ☐      |                                                       |
| 4     | Company-overview narrative + verify | ☐      |                                                       |
| 4     | Market-session awareness            | ☐      |                                                       |
| 4     | Teach-the-agent first-run           | ☐      |                                                       |
| 4     | Per-research-space memory           | ☐      |                                                       |
| 5     | Stale-code remainder                | ☐      |                                                       |
| 6     | Verification + safety floor         | ☐      |                                                       |

---

## Telemetry (agents, tokens, tool-calls, wall-clock, files/lines)

_Appended as tracks complete._

| Track                     | Model | Agents     | Tokens | Tool-calls | Wall (s) | Branch       | Files/lines |
| ------------------------- | ----- | ---------- | ------ | ---------- | -------- | ------------ | ----------- |
| Phase-0 foundation (lead) | Opus  | 0 (direct) | —      | ~30        | —        | 004 (direct) | 5 files     |
| Recon (4 Explore agents)  | Opus  | 4          | —      | —          | —        | read-only    | 0           |

---

## Honest three-bucket report (filled at close)

### ✅ VERIFIED

_pending_

### 🔧 BUILT — flagged

_pending_

### ❌ BROKEN / NEEDS-MANUAL-CHECK

_pending_
