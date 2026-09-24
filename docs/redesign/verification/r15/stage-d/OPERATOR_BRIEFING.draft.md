<!-- DRAFT at f444479031d7d493b7955b9af041d18e7c7a40cc by the Stage D docs wave; refresh before rc2 -->

# Operator Briefing — R15 "LAUNCH"

Draft written while you were away; promoted to `docs/redesign/OPERATOR_BRIEFING.md` by the
lead at rc2 — this file is not that document yet. Source: this wave's own
`docs/redesign/verification/r15/stage-d/FACTS.md` plus the files it and this brief name, all
read at sha `f444479031d7d493b7955b9af041d18e7c7a40cc` on `004-r4-experience-rebuild`.

## 1. State in one paragraph

Vysted Terminal is a desktop (Tauri + Next.js + Python sidecar) finance terminal being
verified end-to-end by an autonomous run called **R15 "LAUNCH"**: a census of every promised
or discovered defect, then fix batches ("Stage C"), then a release-candidate gate. Every
version file (`package.json:3`, `src-tauri/Cargo.toml:3`, `src-tauri/tauri.conf.json:4`,
`sidecar/app.py:327`, `src/lib/plugin-bootstrap.ts:37`, `src-tauri/Cargo.lock:5487`) still
reads **0.8.0** and agrees with itself; **0.9.0 (the intended release number) has not been
written into any source-of-truth file yet**, only into run planning docs under
`docs/redesign/verification/r15/census/`. R15 found 887 raw defect candidates, adjudicated to
a register of 626 entries (16 critical / 112 high / 279 medium / 219 low) plus 76 rejections.
Trading was removed from the product entirely (decision D81, §2) and the licence changed to
PolyForm Strict 1.0.0. As of this sha: all 16 criticals and 100 of 112 highs are fixed; a
ninth Stage C batch just merged; a tenth is in flight on the ~85 mediums left once batch 9's 29
certifications are applied to the register (it still shows 114 open at this sha, §3) plus the
Tier-4-only entries; no release-candidate tag exists yet (`r13-bedrock` is the newest
`r13-`/`r15-` tag reachable from this sha). Nothing has shipped to you.

## 2. What shipped (each line: one Stage C batch, its merge commit, the tally)

"Certified live" below means a fresh reviewer re-verified the fix works, not just that a
writer claimed it; "needs_gui" means the automated suite can't prove it and a human click-
through is required (see §4); numbers are each batch's own `VERDICTS.md` tally line.

- **Batch 1 — trading removed from the product (D81)** — `a122dbf6` `feat(d81)`. Deleted
  every order/broker/paper-account/live-vs-paper path; the user's own tracked portfolio
  (holdings, cost basis, P&L, notes, watchlists) stays. CHANGELOG.md: "R15 Stage C — trading
  removed (D81, 2026-09-23)".
- **Relicense** — `0c63d465` `chore(license): relicense core to PolyForm Strict 1.0.0`. Core
  moved AGPL-3.0 → PolyForm Strict 1.0.0 (noncommercial-use) + a commercial licence; the
  plugin contract (`types/plugin.ts`) and the example plugin stay Apache-2.0 so third-party
  plugin authors are never blocked by the core licence (`docs/redesign/DECISIONS_FOR_OPERATOR.md`
  §1.4). Whether your own personal trading counts as "noncommercial" under this licence is
  unresolved — a question for a lawyer, not this run.
- **Batch 2** — `806a90ca`, critical/high data-research-workspace. 37 certified, 3 not
  certified (DATA-005, DATA-014, AGENT-001).
- **Batch 3** — `c81d879b`, agent runtime/AUTO gate/LLM adapters/research depth/India
  witnesses. 38 certified, 2 not certified (DATA-020, RESEARCH-005).
- **Batch 4** — `dcbe7bae`, context admission/Gemini-xAI lanes/workflows/market-data gate.
  45 certified, 2 needs_gui, 3 stayed open.
- **Batch 5** — `1574ed8e`, India exchange lanes/resolver/runtime liveness/screener-earnings.
  48 certified, 2 needs_gui, 6 not certified (LEAD-010, DATA-017, CODE-PLATFORM-018,
  AGENT-052, AGENT-051, CODE-FRONTEND-015).
- **Batch 6** — `5e147317`, India Emerge/tool-call identity/research funnel/quant pool. 21
  certified (`VERDICTS.md:64`).
- **Batch 7** — `e81c9e7c`, India fundamentals/durable Delegate runs/chart integrity/Undo. 52
  claimed, 50 certified, 1 needs_gui (UI-022), 1 not certified (AGENT-045); LEAD-005,
  AGENT-046, CODE-PLATFORM-021 undelivered, stayed open.
- **Batch 8** — `68bb7aa4`, sidecar lifecycle/provider readiness/data-error honesty. 47
  planned, 39 certified, 1 needs_gui (LIFECYCLE-001), 7 not certified (residuals DATA-061/
  UI-053/RESEARCH-027, partial UI-015, undelivered AGENT-046/CODE-AGENT-008/CODE-PLATFORM-021).
- **Batch 9** — `6b702305`, tool-call identity/research brief contract/fundamentals truth/
  keyboard shell. 45 planned, 29 certified, 14 not certified (see §3). The batch's own
  writeup names UI-083/UI-050 as reclassified to needs_gui, but the register at this sha
  still lists both `open`; batch 10 has not applied this flip yet (§3).

Register adjudication (Sonnet subagent, commit `a288397`, itself the batch-9 workflow's own
adjudicator step) applied **batch 8's** `VERDICTS.json` (39 → fixed @ `68bb7aa4`, LIFECYCLE-001
→ needs_gui) and registered three new leads mined from its VERDICTS.md
(`R15-LEAD-021/022/023`) into `docs/redesign/verification/vysted-r15-register.json`: 626
entries, `{fixed: 279, open: 322, needs_gui: 6, removed_with_feature: 14, blocked_tier4: 4,
not_a_defect: 1}`. **Batch 9's own 29 certifications above are not yet in this register at
this sha** — they land when the batch-10 adjudicator runs (in flight, §5). Every count in §3
below is read directly from the register file as committed, which is one batch behind the
code that just merged.

## 3. What is open and why

**Register counts (severity × status)**, from `vysted-r15-register.json` at this sha:

| severity | fixed | open | needs_gui | removed_with_feature | blocked_tier4 | not_a_defect |
|---|---|---|---|---|---|---|
| critical (16) | 16 | 0 | – | – | – | – |
| high (112) | 100 | 3 | 4 | 1 | 4 | – |
| medium (279) | 153 | 114 | 2 | 9 | – | 1 |
| low (219) | 10 | 205 | – | 4 | – | – |

"removed_with_feature" = named the deleted trading surface, closed with D81. "blocked_tier4"
= fix touches a locked file or needs money/identity (§4). "needs_gui" = needs a human
click-through (§4).

**Open critical: none.**

**Open high (3 in the register, 2 real)**:
- `R15-AGENT-007` (agent-runtime), `R15-AGENT-017` (llm-adapters) — open because your
  default provider lanes are unfunded; DECISIONS_FOR_OPERATOR §2.1. These need you.
- `R15-LEAD-022` (resolver) — certified fixed in batch 9 (merge `6b702305`; `VERDICTS.md:109`
  "LEAD-022: certified."). Still shows `open` in the register at this sha and flips at the
  batch-10 adjudication (§2). Needs nobody.

**Open medium (114 in the register at this sha)**. The register has not yet absorbed batch 9's
adjudication (§2): of the 114, **28 are already certified fixed by batch 9** and only await the
batch-10 register flip, **14 are batch-9 residuals** with a specific reason on record, and the
remaining **72 are genuinely unattempted**.

**(a) Certified fixed by batch 9, awaiting the batch-10 register flip (28)** —
`VERDICTS.json.certified` at merge `6b702305` (excludes `R15-LEAD-022`, a high, counted in
"Open high" above), grouped by subsystem:
- market-data-providers-1 (5): LEAD-016, LEAD-023, DATA-066, DATA-073, LIFECYCLE-021
- frontend-panels-shell-chrome (4): CROSS-PLATFORM-004, DATA-092, UI-058, UI-086
- macro-quant (2): UI-051, UI-053
- market-data-providers-2 (2): DATA-062, DATA-065
- plugins (2): DATA-094, UI-033
- agent-runtime (2): CODE-AGENT-008, LIFECYCLE-025
- frontend-stores (2): CODE-FRONTEND-016, UI-016
- one each: DATA-069 (market-data-providers-3), UI-015 (error-layer), DATA-052 (resolver),
  CODE-AGENT-005 (llm-adapters), AGENT-046 (agent-tools-catalog-ledger), RESEARCH-027
  (research-depth-iter-deep), LIFECYCLE-018 (research-retrieval-relevance), CROSS-PLATFORM-002
  (research-extraction-synthesis), UI-052 (frontend-panels-agent-shell)

Three of these — UI-053, UI-015, RESEARCH-027 — were batch-8 residuals with a reason on record
(UI-053: the IMF SDMX provider itself returns 204/404, not a code bug; UI-015: partial fix kept
open; RESEARCH-027: 2 of 5 cold runs still exceeded the 15 s budget). Batch 9 tried again and
certified a fix for all three; they belong in this group now, not among the residuals below.

**(b) Batch-9 residuals with a specific reason on record (14)**, from the batch that tried and
didn't certify them:
- RESEARCH-028, AGENT-082, DATA-068 — integrator-declared partial, second leg undelivered.
- DATA-048/054/055, UI-032 — fix leg landed but doesn't hold (UI-032: upstream sec-edgar-mcp
  1.0.8 `search_companies` swallows failures).
- DATA-061 — batches 8 and 9 both hit it: `kind=None` still leaks raw upstream text on
  `/macro` and `/history` slash ids (openbb-mcp 422 payloads).
- UI-028 (rho units), AGENT-063 (BTC/USDT news alias), UI-027 (`conflicts()` raw-string
  compare), AGENT-088 (10-char ticker cap), UI-018 (screener/marketplace delete unconfirmed),
  AGENT-049 (no live native-search lane) — fresh-class cases surfaced but not fixed.

**(c) Not yet attempted (72), by subsystem** — the input list batch 10 (in flight — §5) is
mining per the run-state IN-FLIGHT ledger:
- market-data-providers-1 (9): CROSS-PLATFORM-003, DATA-053/071/077/078/079, DOCS-018,
  LEAD-013, LIFECYCLE-026
- scripts-build (9): CODE-PLATFORM-026/027/028/073, CROSS-PLATFORM-001, DOCS-002,
  RELEASE-005/006/007
- plugins (8): AGENT-057, CODE-PLATFORM-012/013/014/015/071/072, DOCS-015
- frontend-panels-shell-chrome (6): DOCS-003/004/005, UI-047/085/087
- backtest (5): CODE-PLATFORM-029/030, LIFECYCLE-015, UI-010/011
- frontend-panels-data-surfaces (4): UI-024, UI-091, UI-050, UI-083 (batch 9's own writeup
  proposed reclassifying UI-050/083 to `needs_gui`; not applied in the register at this
  sha — `docs/redesign/verification/r15/stage-c/batch-10/` is absent from the tree)
- fundamentals-profile (4): DATA-080/095/096, UI-059
- rust-core (3): CODE-PLATFORM-010/024/025
- agent-tools-catalog-ledger (2): AGENT-083, CODE-AGENT-013
- frontend-panels-agent-shell (2): AGENT-053, UI-084
- host-actions-proposed-changes (2): AGENT-084, DOCS-016
- portfolio (2): CODE-PLATFORM-021/023
- safety-audit (2): CODE-FRONTEND-013, UI-044
- screener (2): DOCS-017, RESEARCH-025
- workspace-layout (2): LIFECYCLE-024, UI-088
- one each: CODE-AGENT-009 (agent-runtime), RESEARCH-030 (disclosures-witnesses), UI-048
  (frontend-stores), AGENT-050 (llm-adapters), LEAD-018 (llm-adapters-and-errors), DATA-087
  (macro-quant), AGENT-064 (mcp-servers), CODE-RESEARCH-004 (research-retrieval-relevance),
  DATA-059 (resolver), CODE-PLATFORM-017 (workflow-engine)

(All ids carry the `R15-` prefix, dropped above for space.) Per the run-state IN-FLIGHT
ledger, batch 10 plans to reclassify a Tier-4-only subset — DOCS-003, AGENT-064,
CODE-PLATFORM-015/071/010/073, DOCS-015/002, CODE-FRONTEND-013, UI-044, CROSS-PLATFORM-001 —
to `blocked_tier4` with a DECISIONS_FOR_OPERATOR entry instead of fixing them. All 11 are
confirmed `open` in the register at this sha; `docs/redesign/verification/r15/stage-c/batch-10/`
does not exist in the tree yet, so this reclassification is planned, not applied.

**needs_gui (6, register-confirmed)** and **blocked_tier4 (4, `R15-RELEASE-001..004`,
release-infrastructure)** — see §4 for what each needs.

**Lows backlog:** 219 total, 10 fixed, 4 removed with the trading feature, 205 open. A
pre-triage pass (`docs/redesign/verification/r15/stage-c/lows-triage/LOWS_TRIAGE.md`) already
read all 206 collated low entries and sharpened each into a verdict + fix shape: **199
still_reproduces** (each with a size estimate S/M/L, an acceptance test, a file list), **5
already_fixed** (verify-only, names the incidental fix commit), **1 not_a_defect_proposed**,
**1 duplicate_of**. This is the input the lows fix batches read from — the lows themselves
are untouched code so far.

## 4. Operator-attended list — things only you can do

**Open DECISIONS_FOR_OPERATOR items** (`docs/redesign/DECISIONS_FOR_OPERATOR.md`; number,
what's blocking, smallest unblock, undo if it turns out wrong):

- **§2.1 Provider lanes unfunded** — OpenRouter's balance is negative, DeepSeek-direct is $0.
  Unblock: top up one, restart the dev stack (`043850c` fixed a gpt-5.x tool-calling 400 on
  your composer lane; stack predates it). No undo — funding, not code.
- **§2.2 Docker/OrbStack not running** — SearXNG is down, research falls back to the keyless
  scraper tier (`t1_keyless`). Unblock: start OrbStack before judging research depth.
- **§2.6/§2.11 CI has never run green** — workflows trigger only on `push:main` +
  `pull_request`, so `004-r4-experience-rebuild` fires nothing; the last `main` run is red;
  `pnpm ci-local` is the real local gate (green at baseline: 2507 pytest / 1504 vitest / 13
  cargo, all linters clean). Unblock: fix the red `main` lint run, then open a draft PR for
  this branch (no workflow edit needed — `pull_request` already fires the 3-OS matrix).
- **§2.7 GUI rig: idle time isn't proof you're away** — the rig refuses under 900 s idle, but
  sitting still reading also produces idle time. Proposed unblock (not built, needs your
  sign-off — it makes unattended runs refuse until adopted): an away-sentinel file (e.g.
  `~/.vysted-rig-away`, with an expiry) required in addition to idle.
- **§2.8 (`R15-RELEASE-001`) Unsigned desktop bundles** — Gatekeeper calls the `.dmg`
  "damaged," SmartScreen flags the installer. Blocked: fix touches locked
  `src-tauri/tauri.conf.json` and needs paid credentials (Apple Developer ID + notarization,
  Windows code-signing cert). Smallest unblock: `bundle.macOS.signingIdentity: "-"` for an
  ad-hoc seal — still your sign-off, still the locked file.
- **§2.9/§2.10 (`R15-RELEASE-002/003`) No release pipeline, updater dead end-to-end** — tags
  `v0.6.0`..`v0.8.0` have no installable builds; the updater is wired but never invoked.
  Blocked: needs a new `.github/workflows/release.yml` plus `createUpdaterArtifacts: true` in
  `tauri.conf.json` (both Tier-1). Smallest unblock: approve the release workflow (3-OS matrix
  via `tauri-apps/tauri-action`, `TAURI_SIGNING_PRIVATE_KEY`), then the one config flag; the
  consumer-side `app.updater()?.check()` call isn't Tier-4.
- **§3.1 User-side leftovers after trading removal** — old order/paper-trade audit rows
  (`~/.vysted-terminal/audit_log.db`) and orphaned broker keychain secrets
  (`broker:<id>:api_key|api_secret|access_token|client_id`) are unread by any code but left in
  place (auto-deleting a user's secrets/history is destructive). Unblock: approve a one-time
  purge step plus a CHANGELOG note on deleting them by hand.
- **§3.2 First-launch terms rewrite** — body changed from broker-connection framing to
  research-only framing (no kill-switch line, adds a licence line); sat on the former §6.5
  safety surface. Review the copy in `src/modules/safety/DisclaimerFlow.tsx` before it ships.
- **§3.4 `types/plugin.ts` (locked contract)** — still carries a `"trading-bot"` `PluginType`
  literal + broker JSDoc examples, left as-is on purpose (removing is contract-breaking).
  Your call: keep as precedent or remove. Also queued: CLAUDE.md edits in
  `docs/redesign/CLAUDE_MD_PROPOSAL.md`; `COMMERCIAL_LICENSE.md:36-48`'s broker clause needs
  no change unless you want it gone.
- **§3.3 Accepted safety gaps (not silently dropped)** — no durable audit trail for
  agent-applied writes past the 10-min `action_ledger` TTL (`R15-CODE-FRONTEND-013`); no AUTO
  stop control beyond rejecting a staged change or cancelling a run (`R15-CODE-FRONTEND-008` —
  register status `fixed`: batch 9 closed the entry's order-kind predicate, moot after D81; its
  own note says the core gap it was tracking — no explicit whitelist, no UI copy naming which
  kinds auto-apply — stays open, so this id is not a live tracker for the gap any more).
  No fix proposed — stated in `docs/SAFETY_ARCHITECTURE.md`, yours to weigh.

**needs_gui (6) — the rc1 gate's GUI round tries these unattended on a packaged `--debug`
build when the Mac is idle ≥ 1500 s (§5); yours only if it defers them.** Condensed from the
register's own note field on each entry; two are marked below as ones the unattended rig
plausibly can't clear itself:
- `R15-CODE-AGENT-001` (mcp-servers) — packaged app + `pnpm tauri:dev`: every panel loads,
  sidecar log shows no 403 for the webview's own origin (headless already confirms evil/null
  Origin gets 403, webview origins get 200).
- `R15-LIFECYCLE-001` (rust-core) — **likely needs you**: its GUI check is a packaged *cold
  launch after a reboot* (register note), which the rig doesn't perform. Confirms: window
  paints and accepts input during the 25-90 s MCP bind window (no beachball), data engine
  answers `/health` before binds finish, a renamed sidecar binary reds the status chip at
  once, a killed sidecar flips it to "Sidecar error."
- `R15-LIFECYCLE-008` (rust-core) — packaged app: `<data-dir>/logs/vysted.log` gets
  timestamped `[sidecar]`/`[vysted]`/MCP lines and rotates; Settings "Copy diagnostics"
  previews then copies correctly.
- `R15-UI-009` (frontend-panels-data-surfaces) — packaged macOS app: Export CSV in
  Watchlist/Portfolio/Screener shows the saved path and the file exists under
  `<app data>/exports/csv/` (WKWebView blocks the old Blob-download path).
- `R15-UI-022` (frontend-panels-data-surfaces) — **likely needs you**: its GUI check
  explicitly requires *native event injection, not chrome-devtools* (register note); the rig's
  only tooling here is computer-use plus a Quartz capture script (tauri-mcp/Playwright are not
  connected to this run), not confirmed equivalent. Confirms: a chart drawing clicked
  mid-candle renders at the clicked price, a click past the last bar places a visible drawing,
  Text shows the typed label, a locked drawing's delete stays disabled.
- `R15-UI-025` (frontend-panels-data-surfaces) — packaged app: select note text, click Link;
  an inline URL popover appears and applying it sets the link (WKWebView has no
  `window.prompt`, which the old code needed).

**Keychain dev-signing setup** (`docs/redesign/KEYCHAIN_DEV_SIGNING.md`) — solved 2026-06-11:
dev builds store secrets in a git-ignored local file (`<app-data-dir>/dev-keystore.json`,
mode `0600`) instead of the OS keychain, so `pnpm tauri:dev` rebuilds raise zero keychain
dialogs. OPERATOR-ATTENDED one-time step: the first dev boot migrates existing keychain
secrets into that file (one final dialog, never again). Release builds still use the real OS
keychain, unchanged.

**Provider funding and OrbStack** — already covered as §2.1/§2.2: fund OpenRouter or
DeepSeek-direct before hand-testing chat/research; start OrbStack before judging research
depth (SearXNG needs it, its absence fails silently to a lower-quality search tier).

## 5. How to relaunch

**Run the app on this code:** `pnpm tauri:dev` (→ `pnpm tauri:mcp` → `tauri dev --features
dev-tools`, `package.json`). A packaged `.app`/installer build is out of scope for this wave
— proven from a clean profile separately by the lead.

**Resume the R15 run itself:** `docs/redesign/verification/vysted-r15-run-state.md`,
rewritten at every checkpoint, carries a literal "Resume prompt" block to paste into a fresh
session. At this sha its "Next action" is Stage C **batch 10** (run `wf_54334d97-0e6`, in
flight), then a queued **rc1 gate workflow**
(`docs/redesign/verification/r15/tooling/rc1-gate.js`): re-proves no trading surface exists,
assembles the regression suite, drives `needs_gui` items through the GUI rig unattended when
the Mac is idle, and ends in `R15_GATE_RC1.md` naming a tag sha — the lead tags `r15-rc1` and
pushes, the workflow itself does neither. The lows (§3) go to rc2 alongside Stage D (this
wave).

## 6. Where every evidence file is

All paths verified present at this sha via `git cat-file -e` / `git ls-tree`, except the two
rows marked below.

| What | Path |
|---|---|
| R15 mandate (do not read per this wave's own restriction) — on disk only, git-ignored (`.gitignore:65`), never in any commit | `docs/redesign/verification/R15_BRIEF*.md` |
| Run state (header + resume prompt) | `docs/redesign/verification/vysted-r15-run-state.md` |
| Run report / log | `docs/redesign/verification/R15_RUN_REPORT.md`, `R15_RUN_LOG.md` |
| Defect register (machine + human view) | `docs/redesign/verification/vysted-r15-register.json`, `.md` |
| Stage 0 facts (worktree/branch reconciliation) | `docs/redesign/verification/r15/stage0/RECONCILE_MANIFEST.md` |
| Census — promised/opportunity ledgers | `docs/redesign/verification/r15/census/PROMISE_LEDGER.md`, `OPPORTUNITY_LEDGER.md` |
| Trading-removal plan (D81) | `docs/redesign/verification/r15/stage-c/REMOVAL_PLAN.md` |
| Stage C batch 2-9 plan / verdicts (each has both files) | `docs/redesign/verification/r15/stage-c/batch-<2..9>/PLAN.md`, `VERDICTS.md` |
| Stage C batch 10 (in flight; not present at this sha) | `docs/redesign/verification/r15/stage-c/batch-10/` |
| Lows pre-triage | `docs/redesign/verification/r15/stage-c/lows-triage/LOWS_TRIAGE.md` |
| rc1 gate result | not present at this sha — the rc1 gate workflow is queued, not started |
| This wave's own output — untracked at this sha; the collator commits it | `docs/redesign/verification/r15/stage-d/` |
| Decisions log (Tier-3, autonomous) | `docs/redesign/DECISIONS.md` |
| Decisions for you (Tier-4) | `docs/redesign/DECISIONS_FOR_OPERATOR.md` |
| Keychain dev-signing runbook | `docs/redesign/KEYCHAIN_DEV_SIGNING.md` |
| CLAUDE.md edits queued for your review | `docs/redesign/CLAUDE_MD_PROPOSAL.md` |
| Build-time history / per-batch CHANGELOG sections | `CHANGELOG.md` |

## 7. What R15 decided on its own that you may want to revisit

Everything below already happened; each line is one-step undoable if you disagree
(`docs/redesign/DECISIONS_FOR_OPERATOR.md` §1 and §3.5/3.6):

- **§1.1** — committed the previously-"sacred" fix in `enrich_nse_sectors.py` (a real bug:
  code iterated dict keys on a `{exchange, instruments:[...]}` master, enriched nothing).
  Undo: `git revert 7a1cd8f`.
- **§1.3** — rewrote 5 local never-pushed commits once, before R15's first push, to strip a
  verbatim copy of the private brief and a client name (nothing on public `origin` touched,
  no force-push). Undo: nothing on `origin`; to publish the brief, remove it from
  `.gitignore` and commit.
- **§1.4** — relicensed core AGPL-3.0 → PolyForm Strict 1.0.0 + commercial licence, per your
  own given decision 23 Sep 2026 (listed here as a standing-rule reversal, not R15's own
  call). Undo: `git revert 0c63d465`.
- **§3.5 (D-B3-1)** — tightened AUTO-autonomy back down: auto-applies only
  `panel`/`chart`/`watchlist`; data writes and settings always stage for review (per spec
  SC-025/FR-094, after a docs rewrite had drifted AUTO wider). Undo: flip `autoApplies` in
  `types/proposed-change.ts`.
- **§3.6 (D-B4-1)** — caps tool-result text reaching the model per round (elides oldest once
  over the window estimate); on Ollama also subsets tool schemas by domain cue words, instead
  of silent head-truncation. Undo: have `LLMProvider.context_window` return `None` for Ollama.

<!-- critic-footer -->

## Critic findings applied

1. applied — §2's `a288397` paragraph rewritten: it applies batch 8's verdicts (not batch 8
   and 9), and now says explicitly that batch 9's 29 certifications are not yet in the
   register at this sha and that every §3 count is one batch behind the merged code.
2. applied — §3's open-medium section rewritten into (a) 28 mediums certified by batch 9 and
   awaiting the batch-10 flip (listed, with UI-053/UI-015/RESEARCH-027 moved here and their
   batch-8 history kept as a note), (b) the unchanged 14 batch-9 residuals with reasons, (c)
   the 72 genuinely unattempted regrouped by subsystem with (a) and (b) removed.
3. applied — §1's "~114 open mediums" line now reads "~85 mediums left once batch 9's 29
   certifications are applied (it still shows 114 open at this sha)".
4. applied — §3's "Open high (3)" reworded to "(3 in the register, 2 real)"; LEAD-022 marked
   certified fixed in batch 9 and needing nobody; the dangling "see open_questions" pointer
   removed (the draft has no such section).
5. applied — §6 table: the R15_BRIEF row now says on disk only, git-ignored (`.gitignore:65`),
   never in any commit; the stage-d row now says untracked at this sha, collator commits it;
   the header line softened to except the two marked rows.
6. applied — §5's rc1-gate.js path corrected to
   `docs/redesign/verification/r15/tooling/rc1-gate.js` (the bare `r15/tooling/...` path does
   not exist at this sha).
7. applied — §5's "tags `r15-rc1`, pushes" replaced: the workflow ends in `R15_GATE_RC1.md`
   naming a tag sha; the lead tags and pushes, not the workflow (no `git tag`/`git push` site
   in `rc1-gate.js`).
8. applied — the needs_gui block retitled to say the rc1 gate's GUI round tries these
   unattended when idle ≥ 1500 s and they're the operator's only if deferred; LIFECYCLE-001
   and UI-022 marked "likely needs you" per their own register notes (cold launch after a
   reboot; native event injection, rig tooling not confirmed equivalent).
9. applied — §3.3's `R15-CODE-FRONTEND-008` line now notes its register status is `fixed`
   (the order-kind predicate closed after D81) while its own note says the core AUTO-stop gap
   stays open, so the id isn't a live tracker for that gap any more.
10. applied — both `<!-- VERIFY -->` markers replaced with the stated facts: batch 10 has not
    applied the UI-050/083 needs_gui flip at this sha, and the 11-id Tier-4 reclassification is
    confirmed still `open` in the register with `batch-10/` absent from the tree — planned, not
    applied.
