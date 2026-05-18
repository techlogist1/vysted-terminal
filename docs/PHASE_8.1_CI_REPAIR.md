# Phase 8.1 — CI/CD Repair Sprint

**Tag:** none (CI-hygiene sprint, no version bump).
**Scope:** `.github/workflows/` audit + root-cause fix. No code, no contract,
no §6.5 changes. Tier-1 LOCKED surfaces untouched.

## Why this sprint existed

Phase 8 shipped `v0.8.0` (release commit `5bed299`) with the handoff doc
listing `CI green on all 3 OSes at tag commit (post-tag verification)` as
**pending**. The verification was never closed out: between `5325528`
(housekeeping commit, 2026-05-17) and `f45019f` (handoff polish), every
push fired three workflows × three OSes = 9 jobs, and the lint job was
red on every one of them. 48 failed-job notifications hit the operator's
Gmail inbox in roughly a single ~30-minute Phase-8 sprint window. The
operator asked for a clean repair, not a silence-the-notifications patch.

## Discovery

| Workflow                      | Status before                         | After    |
| ----------------------------- | ------------------------------------- | -------- |
| `.github/workflows/lint.yml`  | 🔴 16/20 fail (chronic)               | 🟢 green |
| `.github/workflows/build.yml` | 🟢 20/20 green                        | 🟢 green |
| `.github/workflows/test.yml`  | 🟢 18/20 green, 2 Windows-only flakes | 🟢 green |

Failed step on every red `lint` run, all three OSes: **Prettier (#13)**.
Failure signature, identical across the streak:

```
[warn] docs/PHASE_8_BUG_CATALOG.md
[warn] docs/PHASE_8_COVERAGE_AND_DOCS_AUDIT.md
[warn] docs/PHASE_8_GATE_VERIFICATION.md
[warn] docs/PHASE_8_HANDOFF.md
[warn] docs/PHASE_8_PERF_BASELINE.md
[warn] docs/PHASE_8_PLUGIN_AUDIT.md
[warn] docs/PHASE_8_RUST_AUDIT.md
[warn] docs/PHASE_8_SIDECAR_AUDIT.md
[warn] docs/PHASE_8_VISUAL_REGRESSION_REPORT.md
[warn] Code style issues found in 9 files. Run Prettier with --write to fix.
```

## Root cause

Nine Phase-8 audit documents were committed by audit teammates without
`pnpm format` ever being run on them. `.prettierignore` correctly excludes
`docs/BLUEPRINT.md` (manually formatted) but **does not** exclude these
nine — they are legitimately in Prettier's scope and just never got
written through it. Every push since landed them in CI's `format:check`
trip-wire.

Idempotency note: `prettier --write docs/PHASE_8_BUG_CATALOG.md` had to
run **twice** to converge — a known prettier markdown bug around the
sequence `ccxt-_)` where the first write produces output that the second
write re-formats to `ccxt-\_)`. The other eight docs converged in one
pass. After both passes, `pnpm format:check` reports a fully clean tree.

## What was fixed

Single content commit:

```
fix(ci): prettier-format 9 Phase 8 audit docs to clear lint workflow
```

Touches: the nine `docs/PHASE_8_*.md` files. No workflow YAML edits.
No CI-config edits. No code edits. Diff is 357 insertions / 252
deletions, all formatting-only (line wraps, table column alignment,
escaped underscores, blank lines around list items).

## What was deliberately not fixed

- **`test.yml` Windows-only flakes** (2 single-run failures, in
  `b0137bf` and `8fb8101`, on doc-only commits, surrounded by green
  runs). One was the `test_audit_5_kill_switch_under_2s` perf assertion
  (max_ack_ms=4626 ms vs 2000 ms budget on Windows runner under load).
  The other was a Vitest `WatchlistPanel publisher` 5 s timeout.
  Architectural — Windows-runner timing variance against strict perf
  thresholds. Fixing either would touch `test_safety_end_to_end.py`
  (Tier-1 LOCKED §6.5 surface) or relax test budgets. Out of CI-hygiene
  scope. Phase 9+ candidate.
- **Workflow consolidation.** All three workflows duplicate ~80 % of
  their setup steps (pnpm + Node + Python + Rust + Linux build deps +
  macOS rustup quirk + `ensure-all-sidecars`). A composite action or
  reusable workflow could DRY this. Out of scope — preemptive refactor,
  not root-cause fix.
- **Local working-tree noise from pytest regeneration of
  `docs/screenshots/v0.5.0/safety-audit/kill-switch-benchmark.json`.**
  Same regeneration as v0.7.0 commit `005a8d0` already handled.
  Local-only; never staged. The file in the repo (the v0.5.0 audit
  baseline) is correct.

## Workflows removed

None. All three earn their place — cross-platform desktop app needs
lint/build/test on three OSes. 9 jobs/push is the right shape.

## Phase-8.1 lesson (CLAUDE.md addition)

A new gotcha was appended documenting that tag commits ship green CI,
not pending verification. The existing gotcha ("`pnpm ci-local` before
every tag commit") is reinterpreted as a hard gate: if `ci-local` is
skipped or fails at tag time, the tag is invalid — fix CI first, re-tag
if necessary. At minimum, `pnpm format:check` (≤5 s) before every push
to `main`; it is the cheapest step in `ci-local` and would have caught
this in zero time during the Phase-8 sprint.

See CLAUDE.md "Gotchas" → new entry under the existing
`pnpm ci-local` and smoke-test entries.

## Verification at end of sprint

- `pnpm format:check` — green locally.
- `node scripts/smoke-test-sidecars.mjs` — green locally (after PATH
  augmented with `~/.cargo/bin` in the PowerShell session; the bash
  subshell's `$HOME` resolves to a sandboxed Microsoft-Store path
  distinct from the Windows-user home).
- `pnpm ci-local` — **3 local-env-only pytest failures** in
  `tests/test_safety_end_to_end.py::test_audit_{1,2,6}`. Root cause:
  the pnpm-spawned subshell on this Windows machine lacks
  `C:\Program Files\Git\usr\bin` on PATH, so `subprocess.run(["grep",
...])` calls inside the §6.5 audit greps `FileNotFoundError` on
  `grep`. CI's Windows runner ships git-bash on PATH out of the box,
  so the same tests pass green in `test.yml` (verified on `f45019f`
  and prior tips). Since the diff for this sprint is 9 markdown files
  - 2 doc files only (zero code, zero contract, zero §6.5), local
    pytest gaps cannot regress any of these tests. Filed as a follow-up
    local-env note in `~/.claude/projects/.../memory/`.
- `gh run list --branch main --limit 5` on the new tip — all three
  workflows × three OSes green (verified post-push).

## Files / commits

- Fix commit: `fix(ci): prettier-format 9 Phase 8 audit docs to clear lint workflow`
- Docs commit: `docs(phase-8.1): CI repair sprint report + CLAUDE.md gotcha`
- Workflow files inspected: `.github/workflows/{lint,build,test}.yml`
- Source of failure: 9 × `docs/PHASE_8_*.md`
- CLAUDE.md addition: under the existing `pnpm ci-local` gotcha section
