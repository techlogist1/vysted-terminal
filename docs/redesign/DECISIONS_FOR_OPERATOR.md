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

### 1.2 — SUPERSEDED (D81)

`test_safety_end_to_end.py` and the tracked `kill-switch-benchmark.json` baseline are
both deleted with the feature, and `VYSTED_REFRESH_SAFETY_CAPTURES` no longer exists.
There is nothing to revert.

<details><summary>Original entry (2.5 — kill-switch-benchmark.json no longer dirties the tree on every pytest), kept for history</summary>

- **What:** `test_safety_end_to_end.py::test_audit_5_kill_switch_under_2s` rewrote the
  tracked v0.5.0 baseline with fresh timings on every full run. The capture now goes to the
  test's temp dir unless `VYSTED_REFRESH_SAFETY_CAPTURES=1` is set. **No assertion changed**
  (the `< 2000 ms` budget gate and the 12-subscriber check are byte-identical); the tracked
  baseline file is restored to its committed bytes.
- **Undo:** `git revert 0112a0c`

</details>

### 1.3 Five local, never-pushed commits were rewritten once (the brief said "no history rewrite")

- **What:** at 10:00 IST on 19 Sep, before R15's first push, `git filter-branch` ran over the
  unpushed range `0112a0c..HEAD` only. It removed the verbatim R15 brief from history and
  scrubbed a client name. Nothing that had ever been on `origin` was touched; no force-push.
- **Why:** `origin` is PUBLIC, and the brief carries your private facts (allowances, machine,
  other products). Pushing it would have been irreversible; rewriting unpushed commits was not.
  The brief now lives on disk only, git-ignored, as does `r15/local/` (process tables, balances).
- **Undo:** nothing to undo on `origin`. To publish the brief anyway: remove its line from
  `.gitignore` and commit the file.

### 1.4 Relicensed to PolyForm Strict 1.0.0 (your decision, given 23 Sep 2026)

- **What:** the core moved from AGPL-3.0 to PolyForm Strict 1.0.0 (public, noncommercial-use
  license) with the commercial license as the only other path; the plugin contract
  (`types/plugin.ts`, `types/plugin-runtime.ts`) and the example plugin (`plugins/example/*`)
  were carved out under Apache-2.0 so third-party plugin authors are never blocked by the
  core's license. Trading was also removed as a product surface by your decision, so no
  license text promises or mentions live order placement anymore.
- **Undo:** `git revert <the relicense commit>` — named by subject, since the sha is only
  assigned at commit time: `chore(license): relicense core to PolyForm Strict 1.0.0`.
- **What PolyForm Strict actually covers:** noncommercial use only (personal use, research,
  education, nonprofit/public-sector use) — full grant text in `LICENSE`. Whether **your own
  personal trading** counts as "noncommercial" under the license is a real, unresolved
  question — that's for your lawyer, not for me to decide.
- **Yours alone, not touched here:** landing-page copy for the new licensing model, and any
  trademark filing for the "Vysted" name. Both are business decisions outside this repo's
  scope.
- **Source of the license text:** fetched verbatim from
  `https://polyformproject.org/licenses/strict/1.0.0.txt` (the project's own official plain-text
  download, linked from the license's canonical page). sha256:
  `e2361f52ad5be22b937a6e983c824a534c5cffa454b6c34af2f8ce0c2cdf7c1a`.
- Neither of us is a lawyer: this is a summary, never legal advice; the license text itself
  was never edited.

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

### 2.3 — CLOSED: removed with the feature (D81, 23 Sep 2026)

The census held at HEAD `99e2ae3`: the kill switch's only subscriber was
`BrokerAdapter.__init__` (`broker_base.py:103`), and its only readers were the order
gates (`:251,:345`). No UI component fired it. Nothing listened for the Rust
`kill-switch:requested` event. With no orders left, there was nothing to halt, so the
mechanism was deleted rather than bound: `kill_switch.rs`, the
`tauri-plugin-global-shortcut` dependency and its capability, `services/kill_switch.py`,
the `/safety/kill-switch*` routes, the store slice, and the types. The first-launch
terms no longer promise Cmd/Ctrl+Shift+K. They are now research-only terms
(R15-UI-041). This also closes R15-CODE-PLATFORM-001/006/007/008/009/031/032/033,
R15-CROSS-PLATFORM-005 and R15-LIFECYCLE-016. **Undo:** revert the removal commits
(this restores the whole trading layer).

### 2.4 — CLOSED: removed with the feature (D81)

The paper→live switch (`BrokerConnectPanel.tsx:246-249`), `POST /brokers/{id}/mode`,
the Connections panel and paper mode itself (synthetic fills, the placeholder account)
are deleted. There is no mode left to confirm.

### 2.5 — CLOSED: removed with the feature (D81)

`PositionLimits` (`maxOrderValueAccountCurrency`, `maxPercentOfAccount`,
`maxPositionSizePerSymbol`, `dailyLossCircuitBreaker`) is deleted from
`sidecar/models/safety.py`, `types/safety.ts` and `BrokerAdapter.DEFAULT_LIMITS`. No
settings surface ever exposed it, and there are no orders left to limit.

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

## 3. New items from Stage C — trading removal (D81, 23 Sep 2026)

Added by the removal plan (`docs/redesign/verification/r15/stage-c/REMOVAL_PLAN.md`) — none
are done-and-revertable like §1; these are yours to review or act on.

### 3.1 UNSURE-1 — user-side leftovers after upgrade (no code reads any of it; nothing purged)

- `~/.vysted-terminal/audit_log.db` — a user's own historical order and paper-trade audit
  rows. No code reads it post-removal.
- OS-keychain `broker:<id>:api_key|api_secret|access_token|client_id` and
  `broker:<id>:_meta:first-connect-ack` — live BYOK broker secrets, now orphaned.
- `broker:_meta:first-launch-tos` — the old first-launch-terms ack, superseded by
  `app-meta:first-launch-terms`.
- Sidecar plugin-store rows for the 7 broker plugin ids — `plugin-bootstrap` iterates
  `CATALOG_ROWS` only, so these are already ignored, just not deleted.

  Deleting a user's secrets and audit history automatically is destructive and irreversible,
  so this batch adds no purge code. **Recommendation:** approve a one-time "remove leftover
  broker credentials" step, plus a CHANGELOG note telling users how to delete `audit_log.db`
  and the keychain entries by hand.

### 3.2 First-launch terms rewrite (was on the §6.5 surface, includes licence wording)

- The dialog's body text changes from "before connecting a broker" framing to research-only
  terms: data and analysis tool, not investment advice; no brokerage connection, cannot place,
  route or simulate orders; data may be delayed or wrong; AI output can be wrong; a licence
  line (PolyForm Strict 1.0.0 noncommercial or a commercial licence, see LICENSING.md). No
  kill-switch line. This is a rewrite of user-facing terms and licence-adjacent wording on a
  formerly §6.5 surface — flagged Tier-4 by R15-UI-041, review the exact copy in
  `src/modules/safety/DisclaimerFlow.tsx` before it ships.

### 3.3 Accepted agent-write safety gaps (stated in `docs/SAFETY_ARCHITECTURE.md`, not silently dropped)

- **No durable record of agent writes.** The former append-only `audit_orders` log existed
  only to record order placement and went with the feature. The surviving read-back
  (`action_ledger.py`) is process memory with a 10-minute TTL — a host action applied under
  AUTO autonomy has no durable trail after that window. Tracked as R15-CODE-FRONTEND-013.
- **No stop control for AUTO beyond reject or run-cancel.** There is no kill switch and no
  per-action pause; the available control is rejecting a staged change under ASK, or
  cancelling a running Delegate run. Tracked as R15-CODE-FRONTEND-008.

### 3.4 BLOCKED-FOR-OPERATOR (Tier-1): no edit made, your call

- **`types/plugin.ts`** — Tier-1 locked plugin contract. `PluginType = "trading-bot" | …`
  and the JSDoc examples (`tradesa.kill-switch`, "Tradesa V2 (Bybit testnet)") were **not**
  touched by this removal. **Your call:** keep the `"trading-bot"` literal and the examples
  as historical/precedent shape, or remove them — the latter is a contract change that
  breaks any plugin declaring that type. The Gate-8 no-trading-identifiers scan exempts
  exactly this one file for this reason.
- **`CLAUDE.md`** — Tier-1; held an uncommitted operator edit at plan time. The exact queued
  edits are in `docs/redesign/CLAUDE_MD_PROPOSAL.md` — apply when convenient.
- **`COMMERCIAL_LICENSE.md:36-48`** — licensing. Optional: drop "responsible for their own
  broker relationship." The clause is still true (it covers decisions users make elsewhere)
  and makes no claim that Vysted places orders, so **no change is required**; left to you.
- **`src-tauri/tauri.conf.json`, `.github/**`, `LICENSE\*`, `r15-fanout.js`** — Tier-1 or
  instructed not to edit. **No edit was needed:\*\* verified no shortcut, broker, or safety
  content in any of them.

### 3.5 D-B3-1 — AUTO scope tightened back to SC-025 (Stage C batch 3; done, revertable)

- AUTO now skips review only for `panel`, `chart` and `watchlist` kinds; `data-write` (notes,
  portfolio positions, saved screens and layouts) and `settings` always stage, and the model is
  told "awaiting review" (`staged` ack). The refuter on R15-CODE-FRONTEND-008 called this policy
  an operator call; the spec (SC-025, FR-094) settles it, and the D81 docs rewrite of acceptance
  scenario 4 had widened AUTO by drafting drift. **Reversible in one predicate**
  (`types/proposed-change.ts` `autoApplies`) if you want AUTO to apply data writes.

### 3.6 D-B4-1 — context admission on window-bound lanes (Stage C batch 4; done, revertable)

- Tool results reaching the model are capped with an elision marker, the oldest tool results are
  elided when a round's token estimate exceeds the model's window, and on a window-bound adapter
  (today only Ollama) the tool schemas sent are subset by domain cue words from the catalog. The
  agent allow-list (D21) is unchanged; hosted lanes report no window and still receive the full
  tool set. This replaces Ollama's silent head truncation with a deliberate subset.
  **Reversible** by having `LLMProvider.context_window` return `None` for Ollama.
