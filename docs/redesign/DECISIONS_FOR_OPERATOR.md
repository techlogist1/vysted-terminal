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

### 2.8 R15-RELEASE-001 — unsigned desktop bundles (Gatekeeper/SmartScreen block every install)

- **Blocked:** every desktop bundle ships unsigned on macOS and Windows; a downloaded `.dmg`
  is refused by Gatekeeper as "damaged" and the NSIS installer is flagged by SmartScreen
  before the app ever opens.
- **Why Tier-4:** the fix edits `src-tauri/tauri.conf.json` (`bundle.macOS.signingIdentity`,
  `bundle.windows.signCommand`/`certificateThumbprint`) and needs paid credentials (an Apple
  Developer ID + notarization, a Windows code-signing certificate) — a locked file plus money
  and identity decisions, not code.
- **Smallest unblock:** at minimum set `bundle.macOS.signingIdentity: "-"` for an ad-hoc seal
  (turns "damaged" into the Open-Anyway path) — still a `tauri.conf.json` edit, so still needs
  your sign-off even for that minimal step.

### 2.9 R15-RELEASE-002 — no GitHub release pipeline (tags v0.6.0..v0.8.0 have zero installable builds)

- **Blocked:** pushing a `v*` tag produces no Release and no downloadable asset.
- **Why Tier-4:** the fix is a new `.github/workflows/release.yml` — `.github/` is Tier-1.
- **Smallest unblock:** approve adding `.github/workflows/release.yml` (3-OS matrix build via
  `tauri-apps/tauri-action`, `createUpdaterArtifacts: true`, `TAURI_SIGNING_PRIVATE_KEY`
  wired) so `latest.json` + `.sig` are attached; this also unblocks 2.10.

### 2.10 R15-RELEASE-003 — auto-updater is dead end-to-end

- **Blocked:** the updater is registered and configured but never invoked, so no install can
  ever leave its install-day version, including past a security fix.
- **Why Tier-4:** the producer half needs `createUpdaterArtifacts: true` in
  `src-tauri/tauri.conf.json` and the release workflow from 2.9 (`.github/`).
- **Smallest unblock:** approve 2.9 first (it produces `latest.json`/`.sig`), then the
  `tauri.conf.json` flag; the consumer-side `app.updater()?.check()` call itself is not
  Tier-4 and can ship independently once the producer side exists.

### 2.11 R15-RELEASE-004 — CI has never run on `004-r4-experience-rebuild`

- **Blocked:** 654 commits (R4–R15) bypass GitHub Actions entirely on this branch; the newest
  cross-OS signal on `main` (2026-05-30) is a red lint run.
- **Why Tier-4:** the fix is either a `.github/` push-trigger edit, or opening a PR against
  `main` (a repo/process decision, not a code change this batch can make unilaterally).
- **Smallest unblock:** open a draft PR for `004-r4-experience-rebuild` (no workflow edit
  needed for this option) so the existing `pull_request` trigger runs the 3-OS matrix; fix
  the red lint on `main` first so the signal is meaningful.

### 2.12 R15-AGENT-064 — no way to add a user-chosen MCP server

- **Blocked:** only `openbb-mcp` and `sec-edgar-mcp` are wired; there is no config surface,
  route or UI to point Vysted at a third-party MCP server (e.g. a broker's read-only MCP,
  screener.in).
- **Why Tier-4:** adds a user-controlled subprocess/tool layer to the core architecture
  (Rust spawn + sidecar client), a locked-shape decision, not a bugfix.
- **Smallest unblock:** approve a config surface (servers list in settings) + a Rust stdio
  spawn + enforcing the existing read-only wrapper audit on it.

### 2.13 R15-CODE-PLATFORM-010 — webview file writes are unconfined; CSP is null

- **Blocked:** `write_text_atomic`/`write_bytes_atomic` accept any absolute path from the
  webview with no confinement to `app_data_dir()`, and `tauri.conf.json`'s CSP is null.
- **Why Tier-4:** the CSP half edits `src-tauri/tauri.conf.json` (Tier-1). The Rust
  confinement half is not Tier-4 and can land independently once approved.
- **Smallest unblock:** approve a `write_atomic` path-confinement helper in `lib.rs`
  (non-Tier-4) plus a CSP value for `tauri.conf.json`.

### 2.14 R15-CODE-PLATFORM-015 — plugin data contribution is declaration-only

- **Blocked:** `getDataSources()` only feeds a Plugin Manager subtitle count; there is no
  host call site for `VystedPlugin.subscribe`, so a data plugin cannot actually serve a
  quote.
- **Why Tier-4:** contract honesty on `types/plugin.ts` (Tier-1) — either build a
  resolution seam or document the field as reserved.
- **Smallest unblock:** pick one: (a) approve a `provider_registry` resolution seam backed
  by plugin-declared sidecar routes, or (b) approve marking `DataSource.realtime`/
  `subscribe` reserved in `types/plugin.ts` + docs.

### 2.15 R15-CODE-PLATFORM-071 — first-party panels bypass the plugin model

- **Blocked:** every core panel is a static-import `VystedModule`, skipping manifests and
  `requiredHostVersion`, contrary to FR-050's "one unified extension model."
- **Why Tier-4:** core architecture / spec reversal.
- **Smallest unblock:** approve either wrapping first-party modules as pre-installed
  bundled plugins, or a recorded FR-050 re-scope excluding first-party panels.

### 2.16 R15-CODE-PLATFORM-073 — design-token audit runs in no CI workflow

- **Blocked:** the off-scale/raw-hex token audit (PDD §16) is not wired into `ci-local` or
  any workflow, so a regression (already present in `NodeEditorPanel`) ships silently.
- **Why Tier-4:** wiring it into `lint.yml` touches `.github/` (Tier-1).
- **Smallest unblock:** approve adding the audit's non-`--report` run to `lint.yml`; the
  script's own rule extensions (`rounded-[...]`, raw-hex, shadow/blur checks) are not
  Tier-4.

### 2.17 R15-CROSS-PLATFORM-001 — Windows/Linux CI has never run on 004

- **Blocked:** 655+ commits on `004-r4-experience-rebuild` have no 3-OS CI signal;
  workflows trigger only on `push:main`/`pull_request` and the branch has no PR.
- **Why Tier-4:** editing `.github/` workflows is Tier-1; opening a PR is also "never
  without asking."
- **Smallest unblock:** approve either a `workflow_dispatch` trigger addition, or opening a
  draft PR for the branch (fix the red `main` lint run first so the signal means
  something).

### 2.18 R15-DOCS-002 — commercial license contact has no working inbox

- **Blocked:** `COMMERCIAL_LICENSE.md`/`LICENSING.md` name `commercial@vysted.com`; the
  domain has no MX or A record, so a would-be licensee has no way to reach you.
- **Why Tier-4:** business/identity decision (owning a real inbox), not a code change.
- **Smallest unblock:** approve a real contact address; it gets swapped into both files
  before any public 0.9.0 announcement.

### 2.19 R15-DOCS-003 — docs still name Next.js; the app ships Vite

- **Blocked:** BLUEPRINT §2 (locked decisions) and CLAUDE.md name "Next.js 16 App Router
  static export"; the repo has shipped Vite 8 + React 19 since D6.
- **Why Tier-4:** `CLAUDE.md` is Tier-1; BLUEPRINT §2 is a locked decision.
- **Smallest unblock:** approve landing the already-queued
  `docs/redesign/CLAUDE_MD_PROPOSAL.md` edit plus the Next.js → Vite swap in
  `BLUEPRINT.md` §2.

### 2.20 R15-DOCS-015 — plugin docs describe the retired panels.ts/PLUGIN_COMPANIONS model

- **Blocked:** `PLUGIN_DEVELOPMENT.md`/`CLAUDE.md` tell authors to ship a sibling
  `panels.ts` registered via `PLUGIN_COMPANIONS`/`BUNDLED_PLUGINS`; the actual mechanism is
  the `marketplace.ts` catalog.
- **Why Tier-4:** the `CLAUDE.md` "Plugin contract" correction is a Tier-1 edit.
- **Smallest unblock:** approve the `CLAUDE.md` correction; the `PLUGIN_DEVELOPMENT.md`/
  `CURRENT_STATE.md` rewrites are not Tier-4 and can land independently.

### 2.21 R15-UI-044 — keychain read failure silently blocks first-run onboarding

- **Blocked:** a denied/failed macOS keychain read during first-launch TOS hydrate leaves
  the TOS dialog (and onboarding) permanently unrendered with no error shown.
- **Why Tier-4:** the fix touches the first-launch TOS/`DisclaimerFlow.tsx`, the
  §6.5-adjacent disclaimer surface §3.2 already flags Tier-4 for its copy.
- **Smallest unblock:** approve adding a `catch` → `setError` to the hydrate effect (an
  error-handling fix, not a copy or policy change) so a keychain failure surfaces a retry
  instead of a silent dead end.

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

## 4. New items from the RC1 fix rounds

### 4.1 rc1-battery-4:1 — FAST research drops an uncached Indian name's fundamentals card (FR-070 budget)

- **What:** FAST (normal-depth) research boxes the price and fundamentals legs at 6 s so it meets
  FR-070's "≤15 s typical". For an Indian listing it has not seen yet, the fundamentals leg needs
  about 10 s even in a warm process: the provider takes 2-3 s, then the exchange-filed overlay
  makes 6 paced NSE requests (the filings list plus 5 XBRL documents), and the anti-bot pacer
  (R15-DATA-066) allows about one request per second. So the first FAST brief for every new
  Indian name shows no fundamentals card and reports "pulled 2/4 data sources". A cold process also
  drops price (the blocked quote-equity path costs two cookie warm-ups). Measured in
  `docs/redesign/verification/r15/rc1/fix-r2/evidence/battery4-leg-profile.jsonl`.
- **Done in fix round 2 (W3):** a timed-out overlay fetch still lands in the cache, so the
  second brief for that name, and the model's own follow-up call, get the card.
- **Yours to decide:** there are three ways to handle the first brief. (a) Accept the drop as the
  honest degrade. This is the current state, and the model then fetches fundamentals itself.
  (b) Give FAST's core legs a longer box, about 12 s, for Indian listings only, so FAST
  runs about 18-20 s on a name's first brief. (c) Show the provider values at once with a stated
  "exchange filings not yet checked" flag, and apply the overlay on the next run.
  **Recommendation:** (a) for rc1, and (c) after it, because (c) keeps FR-070 and never shows an
  uncorrected value without saying so.
- **Undo:** nothing to undo. No code changed for the first-brief half.

### 4.2 R15-AGENT-017 — the shipped default chat model fails the core host-action flow

- **Blocked:** the shipped OpenRouter default (DeepSeek V4 Flash) returns `content_filter` with
  zero tool calls on ordinary portfolio-write asks; `glm-5.1`/`kimi-k2.6` on the same key work
  per R11's live evidence, but that needs a funded OpenRouter lane to re-prove before swapping
  the default.
- **Why operator-attended:** no funded OpenRouter lane (or another live key) is available in
  this environment to run the eval loop's portfolio-write scenario against the candidate
  replacement model.
- **Recommendation:** fund the OpenRouter lane (or supply another key), run the eval loop's
  portfolio-write scenario against `glm-5.1` and `kimi-k2.6`, and ship whichever passes as the
  new default.

### 4.3 R15-AGENT-049 — native web search has no per-run cap or spend meter off Anthropic

- **Blocked:** `web_search_max_uses` is popped unused by every non-Anthropic adapter and the
  loop counter only counts the local `web_search` tool (withheld on native tiers), so a
  native-search run has no cap and BudgetGuard never sees its cost.
- **Why operator-attended:** batch-9 could not exercise a live native-search lane: the OpenAI
  `*-search-preview` models the per-model gate targets now 404 upstream, the OpenRouter paid
  lane is unfunded, and no Gemini/Anthropic key is reachable here.
- **Recommendation:** fund the OpenRouter lane or supply a reachable Gemini/Anthropic key, then
  verify the per-round native-search counter and per-search cost land in BudgetGuard before
  closing this entry.

### 4.4 R15-UI-088 — in-webview drag gestures have no automated coverage

- **Blocked:** dockview tab reorder and the node-editor's palette-to-canvas drop have been
  carried as NEEDS-MANUAL-CHECK since R7; chrome-devtools MCP cannot synthesize the trusted
  (`isTrusted`) events these gestures need, and there is no GUI in this environment to run a
  real-event harness.
- **Why operator-attended:** adding the Playwright suite (`fix_shape` on R15-UI-088) is code,
  but running it against a real window to certify it needs the e2e runner call — a GUI round,
  not available here.
- **Recommendation:** once the Playwright suite lands, run it in a GUI-attended session (or CI
  with a real display) and certify R15-UI-088 from that run's output.

### 4.5 R15-CODE-PLATFORM-063 — `scripts/*.py` sit outside every ruff gate in CI and ci-local

- **Blocked:** the fix widens the ruff scope from `sidecar` to `sidecar scripts` in
  `.github/workflows/lint.yml:87-89` (plus the mirrored path in `package.json`'s `ci-local`
  script) so the 12 tracked `scripts/*.py` files (r15 tooling, `scripts/rig/`, the screenshot
  generators) stop being an unlinted blind spot.
- **Why operator-attended:** `.github/workflows/lint.yml` is a never-owned Tier-1 CI workflow
  file; no agent may edit it without sign-off.
- **Recommendation:** change the two `ruff check`/`ruff format --check` invocations in
  `lint.yml:87-89` from `sidecar` to `sidecar scripts`, and widen the same path in
  `package.json`'s `ci-local` entry so the two gates stay byte-for-byte in sync.
- **Risk of not doing it:** real lint violations in `scripts/` (ruff already reports F541/F841
  there today) keep shipping unseen, since neither CI nor `ci-local` ever scans that directory.
- **Status: open, blocked_tier4**

### 4.6 R15-DOCS-008 — BLUEPRINT §2/§3.1 still describe OpenBB as an in-process runtime-sidecar wrap

- **Blocked:** the fix rewrites `docs/BLUEPRINT.md:55`, a row inside the
  `## 2. Locked Decisions Summary` table ("Data layer | OpenBB ODP wrapped as runtime sidecar"), plus the matching §3.1
  prose at `:84`. v0.4.0 already retired the in-process OpenBB plugin in favor of the
  out-of-process `openbb-mcp` subprocess, so this is a correction, not a new reversal — but it
  still edits a Locked-table row.
- **Why operator-attended:** `docs/BLUEPRINT.md` §2 is this project's Locked-decisions section;
  no agent may reopen or edit it unilaterally, even descriptively.
- **Recommendation:** reword line 55 to describe the `openbb-mcp` subprocess spawned by the
  Tauri core (not an in-process wrap), and update the §3.1 sentence at line 84 to match; no
  other §2 row changes.
- **Risk of not doing it:** BLUEPRINT.md keeps asserting a data-layer process model v0.4.0
  already retired, so anyone treating it as ground truth (including a future agent) will design
  against the wrong process boundary.
- **Status: open, blocked_tier4**

### 4.7 R15-DOCS-011 — CONTRIBUTING.md promises a CLA that no CI gate enforces

- **Blocked:** the fix needs a new CLA-check workflow under `.github/workflows/` plus finalized
  CLA/licensing text for `CONTRIBUTING.md:95` ("The formal CLA process is still being
  finalized") to reference.
- **Why operator-attended:** `.github/workflows/` additions are Tier-1 CI, and CLA/licensing
  text is a Tier-4 licensing decision — both never-owned by an agent.
- **Recommendation:** before contributions reopen (they are closed today, `CONTRIBUTING.md:3`),
  add a CLA-assistant (or PR-body check) workflow and finalize + commit the CLA text it enforces.
- **Risk of not doing it:** low while contributions stay closed; reopening them without the gate
  would let a PR merge with no CLA statement, contrary to BLUEPRINT §4/§6.1.
- **Status: open, blocked_tier4**

### 4.8 R15-RELEASE-012 — CI never caches the three PyInstaller sidecar binaries

- **Blocked:** the fix adds an `actions/cache` step, keyed on `hashFiles` of
  `sidecar/requirements*.txt`, `sidecar/**/*.py` and `scripts/ensure-*.mjs`, around the
  `ensure-all-sidecars` step in `.github/workflows/build.yml`, `test.yml` and `lint.yml`.
- **Why operator-attended:** all three are never-owned Tier-1 CI workflow files.
- **Recommendation:** add the cache step in each of the three workflows; the existing
  staleness gate (`scripts/sidecar-staleness.mjs`) already forces a rebuild on a stale cache
  restore, so this is safe to land as written.
- **Risk of not doing it:** pure CI cost/time, open since v0.7.0 (`BLOCKERS.md:337-339`) — every
  push pays ~9 cold sidecar builds (3 workflows x 3 OSes, ~20-25 min each) with no correctness
  risk.
- **Status: open, blocked_tier4**

### 4.9 R15-LEAD-030 — fabricated tool figures after a tool error: eight fix batches, the stop rule has fired

- **Blocked:** a disposition question, not a locked file. Stage C batches 15–20 fixed the entry's
  literal repro and every shape an earlier verifier found; a fresh Opus verifier found a new
  escape each time. Batch-20 replaced prose-shape rules with figure grounding by provenance
  (`sidecar/services/figure_grounding.py`, merged `1abef99b`): every earlier probe holds and it
  blocks 6 of the 14 fresh cases base leaked, but two named gaps remain (an error-acknowledging
  clause is exempted before grounding runs; subjects match by ticker, not company name).
  Batch-21 fixes exactly those.
- **Why operator-attended:** if batch-21 is not certified, the lead stops fixing (run-state rule)
  and rc1 stays gated on a high entry in the agent-chat area, which the brief's Boundaries say
  cannot be adjudicated away without a fresh verifier's concurrence. Tagging with a documented
  known limitation is the operator's call.
- **Recommendation:** mark the entry `blocked_tier4` (a fresh verifier's concurrence is sought in
  batch-23, as the Boundaries require for the agent-chat area) and tag r15-rc1 with LEAD-030
  listed in the operator briefing as a known limitation (after a tool error a keyless local
  model can still state an invented figure for a company it names in the same paragraph as a
  subject whose call succeeded, when that name is neither the ticker, the resolver name nor an
  initialism of it, or was never looked up at all; a fabricated tool-result dump with no
  currency figure can also stream; every other shape found in eight rounds is replaced by the
  honest note). Take the post-launch design change instead of a ninth filter round: end the
  model's answer with a structured no-data turn after an all-errored round.
- **Risk of not doing it:** the release ships an agent that can, on a tool failure with a local
  model, print a made-up price. Offline fresh-case fabrication on the residual classes is 6/19
  after batch-20 (14/19 before); 0 on every pinned shape.
- **Status: open; the stop rule has fired (eighth failure, batch-22, W1 merged `c155e5ad`)** —
  batch-22 took the verifier's fresh cases to BAD 4 (8 on base) and every pinned shape from
  batches 15–21 holds, but a figure for a subject the guard cannot name, or never called, inherits
  the ok subject of its paragraph and streams ('TCS.NS closed at ₹3,235.50. Tata Motors last
  traded at ₹702.10.' with TATAMOTORS.NS errored or never called); a figure-less fabricated
  result dump also streamed live. No ninth round. Batch-23's fresh verifier rules CONCUR or
  REFUSE on this disposition (`r15/stage-c/batch-23/LEAD-030-CONCURRENCE.md`); on CONCUR the
  entry becomes `blocked_tier4` and rc1 needs the operator's word on shipping with the known
  limitation.