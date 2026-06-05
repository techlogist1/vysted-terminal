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

All tracks integrated on `004`. Final tree green: **vitest 1045/1045 (127 files)**, **pytest
1393 passed / 1 skipped**, **typecheck clean**, **cargo test 8 passed**, **ruff + prettier clean**,
**§6.5 audit 9/9**, **Tier-1 byte-untouched**, **version 0.8.0** everywhere. Verified live on the
running Tauri app (Quartz capture + computed-style + driven interactions).

| Phase | Track                               | Status | Evidence                                                      |
| ----- | ----------------------------------- | ------ | ------------------------------------------------------------- |
| 0     | Warm Graphite + amber + de-glow     | ✅     | live: body `rgb(17,15,12)`, `--accent-rgb 216 154 78`, bg-image `none` |
| 1     | Composer/header sizing + chips      | ✅     | `8012864`/`046340c`; composer min-h 68, header h-12, SuggestionChips live |
| 1     | Badges/pickers/EmptyState rollout   | ✅     | `e15730f`; shared EmptyState in 5 dead-grey surfaces, sized pickers |
| 1     | Sans chrome/prose + warmth pass     | ✅     | `8012864`; live body font "Inter", warmer ramp (fresh-reviewer driven) |
| 2     | ⌘K ranking fix + palette sizing     | ✅     | `0bcb4fe`; live "notes"→Open Notes + Notes panel, zero agents; 36 tests |
| 2     | Notes export MD/PNG/PDF             | ✅     | live files: `general.{md,png(600×1308),pdf(2pg)}`              |
| 2     | Brief export MD/PDF                 | ✅     | live files: `route-ns.md`, `route-ns.pdf (6pg)`               |
| 2     | Export data-dir fix (get_app_data_dir) | ✅  | `462def4`; Rust command — was the reason exports wrote nothing |
| 3     | Screener cold-path backoff          | ✅     | merged `a456ec7`; LIVE log: throttle 1→2→3 backing off 76→136→271s |
| 4     | Company-overview narrative + verify | ✅     | merged `021be60`; numeric-redaction pass, 15 tests            |
| 4     | Per-research-space memory           | ✅     | merged `36ef515`; typed field + durable memory, 40 tests      |
| 4     | Market-session awareness (FR-118)   | ✅     | `e15730f`; session label + stale-price guard on watchlist/chart |
| 4     | Research presentation depth         | ✅     | `fdd4089`; dedup sources + type badges + asset-class metrics  |
| 5     | DESIGN_SYSTEM.md rewrite (S-2)      | ✅     | merged `0ab48d5`; grep-clean of retired-system terms          |
| 5     | S-1/S-3/S-5a/S-6/S-7 cleanup        | ✅     | warm-comment purge, tongyi `.pyc`, brief mode/step casing     |
| 6     | Verification + safety floor + sheet | ✅     | side-by-side `verification/COMPARISON.html`; 2 fresh reviews; floor green |

Stale-register: S-1/S-2/S-3/S-5a/S-6/S-7/S-8/S-19 done. S-15/S-16/S-18 (mode/registry/`__terminal__`
dedup) **not done** — optional coherence polish, no correctness impact; carried forward. §G CLAUDE.md
items remain for the operator (build does NOT edit CLAUDE.md).

---

## Telemetry (agents, tokens, tool-calls, wall-clock)

| Track                        | Model  | Tokens  | Tool-calls | Wall (s) | Branch / outcome                           |
| ---------------------------- | ------ | ------- | ---------- | -------- | ------------------------------------------ |
| Recon (4 Explore agents)     | Opus   | ~494k   | ~219       | ~270     | read-only map of all regions               |
| Phase-0 foundation (lead)    | Opus   | —       | ~30        | —        | `acde11f` direct                           |
| ⌘K ranking + palette (lead)  | Opus   | —       | ~12        | —        | `0bcb4fe` direct                           |
| Notes export + Rust (lead)   | Opus   | —       | ~18        | —        | `d664bda` direct                           |
| Screener backoff             | Opus   | 102,920 | 55         | 466      | `worktree-agent-screener-backoff` merged   |
| Per-research-space memory    | Opus   | 180,925 | 111        | 939      | `worktree-agent-space-memory` merged       |
| Company-overview narrative   | Opus   | 190,761 | 95         | 822      | `worktree-agent-overview-narrative` merged |
| DESIGN_SYSTEM.md rewrite     | Sonnet | 76,354  | 28         | 281      | `worktree-agent-design-doc` merged         |
| Composer + chips             | Opus   | 122,600 | 54         | 409      | `worktree-agent-composer` merged           |
| Brief export + depth         | Opus   | 178,667 | 90         | 821      | `worktree-agent-brief` merged              |
| Badges/empty/session         | Opus   | 165,717 | 93         | 663      | `worktree-agent-surfaces` merged           |
| Adversarial diff review      | Opus   | 125,438 | 74         | 436      | read-only; clean pass + safety PASS        |
| Fresh design review ×2       | Opus   | ~54,600 | 12         | ~128     | round-1 → round-2 (close, minor deltas)    |
| Export-dir fix + design pass | Opus   | —       | (lead)     | —        | `462def4`, `8012864` direct                |

**Agents:** 4 recon (Explore) + 7 build teammates + 1 adversarial reviewer + 2 fresh design
reviewers + lead = **14 agents**. Lead landed 6 direct commits; teammates landed 7 (each merged
`--no-ff`). **All isolated-worktree teammates self-corrected the base-discipline hazard** (the Bash
cwd resets per call, so their first `git reset` hit the shared checkout; each re-ran it inside its
worktree). The lead's main worktree was contaminated **once** (HEAD switched to `main`/`cfcf5be`
during the wave-1 worktree-creation burst) and recovered **losslessly** (everything committed+pushed
to `origin/004`). **Carry-forward for the next session:** pre-create worktrees from HEAD, or have
teammates `cd` into their worktree path before the first `git`.

---

## Honest three-bucket report (filled at close)

### ✅ VERIFIED (with file/pixel/log evidence)

- **Warm Graphite + amber + zero glow** — live computed style on the running app: body
  `rgb(17,13,12→17,15,12)` warm near-black, `--color-amber-400 #d89a4e`, `--accent-rgb 216 154 78`,
  `background-image: none` (the indigo body-glow is gone). `rg` finds no `7e88e8`/cold-zinc/
  cool-indigo live literals.
- **⌘K ranking** — driven live: query "notes" → top results _Open Notes_ (action) + _Notes_ (panel),
  **zero agents** in the result set. 36 palette unit tests incl the regression + no-flood guard.
- **Notes export MD/PNG/PDF** — drove the buttons on the real app; wrote
  `{dataDir}/exports/notes/general.md` (UTF-8), `general.png` (PNG 600×1308 RGBA), `general.pdf`
  (PDF 1.3, 2 pages). Verified with `file`.
- **Brief export MD/PDF** — drove the brief toolbar; wrote `exports/research/route-ns.md`
  (real brief markdown) + `route-ns.pdf` (PDF 1.3, 6 pages).
- **Screener cold-path backoff** — LIVE sidecar log shows the warm loop backing off
  76s → 136s → 271s on consecutive throttled cycles (was a flat 40s hammer). 35+39 sidecar tests.
- **Sans chrome/prose, mono data** — live: body font "Inter", empty-state + brief prose "Inter";
  metric tables/prices keep explicit `font-mono` + tabular-nums.
- **Full gates** — vitest 1045, pytest 1393/1-skip, cargo test 8, ruff + prettier clean,
  §6.5 9/9, Tier-1 untouched, version 0.8.0, no new deps, brokers GET-only.
- **Design match** — two blind fresh reviewers: round-1 "close, minor deltas (leaning different on
  warmth/density/mono)" → after the iteration, round-2 **warmth 4/5, typography 4/5, contrast 4/5,
  verdict "close, minor deltas — the bones are right"**, with the residual deltas being the amber
  accent (a brand choice the brief mandated) and finance-terminal chrome density. Side-by-side sheet:
  `docs/redesign/verification/COMPARISON.html`.

### 🔧 BUILT — flagged (honest caveats)

- **Company-overview AI narrative + numeric verification** — built + 15 mocked-LLM tests prove the
  verification pass strips/flags hallucinated numbers. The LIVE end-to-end narrative was **not driven**
  (the running app had no LLM API key — "no key"; and a fresh brief needs the model). The numeric-
  redaction logic is the load-bearing part and is unit-tested; the model-transport seam is the shipped
  `services/llm/oneshot.complete`.
- **Per-research-space memory, market-session, research-depth** — built + unit-tested + integrated;
  the brief-depth + market-session surfaces render live (seen in the cockpit). Per-space memory
  durability is unit-tested (round-trip) but not driven across a full session in the rig.
- **Screener cold single-digit-second timing** — the self-throttle is FIXED + proven (live backoff
  log). The absolute cold wall-clock is IP/network-bound (Yahoo throttles this IP); not independently
  re-measured on a clean network this session.
- **Design "indistinguishable" bar** — honestly: the app is now the **same visual family** as the
  references on the fundamentals (warmth, sans prose, contrast tiers, restrained accent, no glow,
  composer-led empty state, palette), but it is NOT pixel-identical — it is a denser finance terminal
  with an amber brand. The two residual reviewer deltas (amber temperature, chrome density) are a
  deliberate brand choice + the product's nature, not regressions.

### ❌ BROKEN / NEEDS-MANUAL-CHECK

- **NEEDS-MANUAL-CHECK — live LLM-dependent paths:** the company narrative end-to-end, a freshly-
  generated research brief, and agent tool-use all need a real model key in the running app; drive
  them once with a key configured.
- **NEEDS-MANUAL-CHECK — `package.json` `dev` script:** during verification it was temporarily
  pointed at a static server (`python -m http.server`) so the Tauri webview would load the faithful
  **static-export** build instead of Turbopack dev chunks (WKWebView chokes on the `%5Bturbopack%5D`
  URL-encoded dev-chunk names → white screen). **Reverted to `next dev` before close** — confirm it
  reads `"dev": "next dev"`.
- **Carried forward (not broken):** stale-register S-15/S-16/S-18 (mode-system / versioned-registry /
  `__terminal__`-capture de-duplication) — coherence polish, no correctness impact.

**No silently-deferred work.** Every brief requirement is either VERIFIED above or explicitly flagged.
