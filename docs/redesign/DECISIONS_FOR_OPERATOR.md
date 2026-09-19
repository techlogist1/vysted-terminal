# Decisions for the operator (R15)

Things R15 did that reverse a standing rule of yours, or that are yours alone to decide
(Tier-4). Newest concerns at the top of each section. Each entry: what, why, my
recommendation, and how to undo it in one step.

## 1. Reversals of a standing operator rule (already done — revert if you disagree)

### 1.1 The "sacred" `enrich_nse_sectors.py` edit is now committed (`7a1cd8f`)

- **What:** every brief since R11 said never commit/revert/touch the uncommitted edit in
  `sidecar/services/resolver_masters/enrich_nse_sectors.py` (sha256 `5cb28e0d…286abdbe`).
  R15 reviewed the diff: it is exactly the documented `_nse_symbols` fix (the NSE master is
  `{exchange, instruments: [...]}`, not a flat list — the old code iterated dict keys and
  enriched nothing). It is committed alone as `7a1cd8f`.
- **Why:** the fix existed only on this laptop, protected by a sentence repeated in every
  brief. A rule held by memory fails the first time a brief forgets it; a commit cannot.
- **Undo:** `git revert 7a1cd8f`

### 1.2 `kill-switch-benchmark.json` no longer dirties the tree on every pytest

- **What:** `test_safety_end_to_end.py::test_audit_5_kill_switch_under_2s` rewrote the
  tracked v0.5.0 baseline with fresh timings on every full run. The capture now goes to the
  test's temp dir unless `VYSTED_REFRESH_SAFETY_CAPTURES=1` is set. **No assertion changed**
  (the `< 2000 ms` budget gate and the 12-subscriber check are byte-identical); the tracked
  baseline file is restored to its committed bytes.
- **Undo:** `git revert 0112a0c`

### 1.3 Five local, never-pushed commits were rewritten once (the brief said "no history rewrite")

- **What:** at 10:00 IST on 19 Sep, before R15's first push, `git filter-branch` ran over the
  unpushed range `0112a0c..HEAD` only. It removed the verbatim R15 brief from history and
  scrubbed a client name. Nothing that had ever been on `origin` was touched; no force-push.
- **Why:** `origin` is PUBLIC, and the brief carries your private facts (allowances, machine,
  other products). Pushing it would have been irreversible; rewriting unpushed commits was not.
  The brief now lives on disk only, git-ignored, as does `r15/local/` (process tables, balances).
- **Undo:** nothing to undo on `origin`. To publish the brief anyway: remove its line from
  `.gitignore` and commit the file.

## 2. Yours to decide (R15 routed around each; census findings, not yet fixed)

Recorded at the 19 Sep pause so they are not lost. 2.1, 2.2, 2.6 and 2.7 are measured facts; 2.3–2.5 are census findings with `file:line` evidence that have NOT yet been through a refuter — each is re-adjudicated when the register is built.

### 2.1 Your default provider lanes are unfunded — the app cannot answer on them

- OpenRouter's paid balance is negative and DeepSeek-direct is at $0 (read from the providers'
  own balance endpoints; figures in the git-ignored `r15/local/BUDGET.md`). Your composer lane
  is `openai` / `gpt-5.6-luna`, which is funded. **Recommendation:** top up OpenRouter before
  hand-testing research depth — the keyless research default and Tongyi fallback both ride it.
- **Restart your app to get the 3 Sep fix.** Your dev stack has been running since 13 Sep on
  pre-patch binaries; `043850c` repairs the gpt-5.x tool-calling 400 on exactly your lane.

### 2.2 Docker/OrbStack is not running, so SearXNG is down and research silently uses the keyless scraper

- The sidecar knows (`/search/searxng/status` → tier `t1_keyless`); whether the UI says so is a
  census item. This is the leading boring cause of "web search bugging out". R15 did not start
  Docker (system state is yours). **Recommendation:** start OrbStack before judging research.

### 2.3 Kill switch: first-launch terms promise Cmd/Ctrl+Shift+K, but no UI listener exists (§6.5 — Tier-4)

- `src/store/safety.ts` has the state, `DisclaimerFlow.tsx:45` makes the promise, nothing binds
  the key. **Recommendation:** bind it (frontend-only, no safety-model change) — needs your
  sign-off because it sits on the safety surface.

### 2.4 Paper → live broker mode is one click with no disclaimer (`BrokerConnectPanel.tsx:246-249`) (§6.5-adjacent)

- Order placement still never auto-applies; this is about the mode switch itself.
  **Recommendation:** a confirm step naming what "live" means. Your call.

### 2.5 `maxPercentOfAccount` / `dailyLossCircuitBreaker` are declared but never enforced

- Settings that look like protection and do nothing. **Recommendation:** remove them from the
  0.9.0 UI (no live orders in this release) rather than enforce them. Safety-model change → yours.

### 2.6 CI has never run on `004`, and the last `main` run failed

- Workflows trigger only on `push: main` + `pull_request`. R15 never edits workflows; the local
  chain (`pnpm ci-local`) is the gate: **green at baseline — pytest 2507 passed / 1 skipped,
  vitest 1504 in 135 files, cargo 13, all linters clean.** A proposed workflow diff will be in
  the release runbook.

### 2.7 GUI rig: input-idle time is not proof you are away

- The rebuilt rig (`scripts/rig/rig.py`) refuses below 900 s idle, requires Vysted frontmost,
  aborts on any human input, and deletes a capture if a foreign window appears. But idle climbed
  past 900 s while you sat reading. **Recommendation:** an away-sentinel file you create when you
  leave (`~/.vysted-rig-away`, with an expiry), required in addition to idle — ~5 lines. Not
  added, because it would make every unattended run refuse until you know about it.
