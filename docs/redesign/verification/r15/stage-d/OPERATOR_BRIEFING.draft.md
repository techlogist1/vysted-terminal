<!-- DRAFT refreshed at 82d3d083 25 Sep 2026 17:35 IST by the handover pre-refresh; the at-tag refresh is a delta; promoted to docs/redesign/OPERATOR_BRIEFING.md at rc2 -->

# Operator Briefing — R15 "LAUNCH"

This is a draft written while you were away. The lead promotes it to
`docs/redesign/OPERATOR_BRIEFING.md` at rc2; until then it is not that document. Every fact below
was re-read from disk at sha `82d3d083` on `004-r4-experience-rebuild`. The sources are the
run-state (`docs/redesign/verification/vysted-r15-run-state.md`), the register JSON, each batch's
`VERDICTS.json`, `r15/rc1/`, `r15/stage-c/lows/PARTITION.md` and
`docs/redesign/DECISIONS_FOR_OPERATOR.md`. Lines marked "(at the rc1 tag: …)" are the ones the
at-tag refresh changes.

## 1. State in one paragraph

Vysted Terminal is a desktop finance terminal: a Tauri shell, a Vite + React webview and a Python
sidecar. An autonomous run called **R15 "LAUNCH"** is verifying it end to end. It takes a census
of every promised or discovered defect, then runs fix batches ("Stage C"), then release-candidate
gates. At this sha, seventeen Stage C batches are merged (the last is `292ba53a`, 16:50 IST 25
Sep). The register holds 646 entries: 388 are fixed, and exactly one critical/high/medium entry is
open, `R15-LEAD-030`. The first rc1 gate round failed at 09:57 IST 25 Sep and no tag was cut.
Round 2 waits on batch 18, which is in flight for LEAD-030 and two new mediums. Trading is out of
the product for good (D81), and the core licence is PolyForm Strict 1.0.0 plus a commercial
licence. Every version file still reads **0.8.0** (`package.json:3`, `src-tauri/Cargo.toml:3`,
`src-tauri/tauri.conf.json:4`, `sidecar/app.py:329`, `src/lib/plugin-bootstrap.ts:38`); 0.9.0 is
written at Stage D. The newest tag is still `r13-bedrock`, and nothing has shipped to you. (at
the rc1 tag: the newest tag becomes `r15-rc1`, and "round 2 waits" becomes the round-2 result.)

## 2. What shipped (each line: one Stage C batch, its merge commit, the tally)

"Certified" means a fresh verifier re-proved the claim on the running app, not only that the
writer said it works. "needs_gui" means the automated suite cannot prove it and a human
click-through is required (§4). Tallies come from each batch's own
`r15/stage-c/batch-N/VERDICTS.json`. Ids drop the `R15-` prefix.

- **Relicense** — `0c63d465`. The core moved from AGPL-3.0 to PolyForm Strict 1.0.0
  (noncommercial) plus a commercial licence. The plugin contract (`types/plugin.ts`) and the
  example plugin stay Apache-2.0 (`DECISIONS_FOR_OPERATOR.md` §1.4).

| Batch | Merge | Scope | Certified | needs_gui | Not certified |
|---|---|---|---|---|---|
| 1 | `a122dbf6` | trading removed from the product (D81) | removal proved: 0 broker/order/kill/audit routes, all 22 former routes 404 | 0 | 0 |
| 2 | `806a90ca` | critical/high data, research, workspace | 37 | 0 | 3 (DATA-005, DATA-014, AGENT-001) |
| 3 | `c81d879b` | agent runtime, AUTO gate, LLM adapters, research depth | 38 | 0 | 2 (DATA-020, RESEARCH-005) |
| 4 | `dcbe7bae` | context admission, Gemini/xAI lanes, workflows, market-data gate | 45 | 2 (UI-009, UI-025) | 3 |
| 5 | `1574ed8e` | India exchange lanes, resolver, runtime liveness | 48 | 2 (CODE-AGENT-001, LIFECYCLE-008) | 6 |
| 6 | `5e147317` | India Emerge lanes, tool-call identity, research funnel (22 delivered after a harness stall) | 21 | 0 | 3; UI-041 concurred not a defect |
| 7 | `e81c9e7c` | India fundamentals, durable Delegate runs, chart integrity | 50 | 1 (UI-022) | 4 |
| 8 | `68bb7aa4` | sidecar lifecycle, provider readiness, data-error honesty | 39 | 1 (LIFECYCLE-001) | 7 |
| 9 | `6b702305` | tool-call identity, research brief contract, fundamentals truth | 29 | 2 (UI-050, UI-083) | 14 |
| 10 | `f407107f` | runtime and backtest integrity, catalog and host actions, plugin lifecycle | 50 | 1 (UI-084) | 4 (CODE-AGENT-009, UI-091, DATA-071, LEAD-013); AGENT-083 concurred not a defect |
| 11 | `4097dac4` | build recipe and gates, schema versions, agent eval, option chain | 18 | 0 | 2 (LEAD-028, RELEASE-007); UI-047, UI-059, DATA-080 concurred out of scope |
| 12 | `ef33c7f6` | the 13 entries the rc1 refutation audit reopened, plus gate findings | 19 | 0 | 3 (RESEARCH-007, DOCS-017, AGENT-090) |
| 13 | `a217a529` | source tiers via the Public Suffix List, live universe counts, ADR ratio guard | 2 | 0 | 2 (AGENT-090, CODE-AGENT-033) |
| 14 | `17301f54` | tool_result stream event and grader; ADR ratio guard, second pass | 1 | 0 | 1 (AGENT-090) |
| 15 | `74ee3468` | ADR ratio grounded from the SEC 20-F cover page (strongest-tier root cause) | 0 | 0 | 1 (AGENT-090) |
| 16 | `d64640d2` | ratio-guard class qualifier, tool-citation guard, bounded ADR lookup | 2 (AGENT-090, LEAD-032) | 0 | 1 (LEAD-030) |
| 17 | `292ba53a` | citation guard across turns, partial tool-call marker hold | 1 (LEAD-031) | 0 | 1 (LEAD-030) |

- **rc1 gate fix rounds** — `57897778`, merged with the round-1 evidence. They fixed a leftover
  broker line in an old handoff doc, statement currency labels, a leaked tool-call tail and the
  overlay cache. The chain was green at `1d6511c8`: vitest 1825, cargo 19, pytest 3150 + 1
  skipped, smoke 3/3.
- **Batch 18** — in flight: step 1 is a strongest-tier root cause of LEAD-030 (run
  `wf_116e8cdf-429`), then step 2 is the batch. (at the rc1 tag: add its merge commit and tally.)

The register is one step behind the code: batch 17's LEAD-031 certification is applied at batch
18's adjudication.

## 3. What is open and why

**Register counts (severity × status)**, derived from `vysted-r15-register.json` at this sha. It
was last written at `3483b699`; its declared totals are 887 raw findings, 646 entries and 76
rejections.

| severity | fixed | open | needs_gui | blocked_tier4 | removed_with_feature | not_a_defect | total |
|---|---|---|---|---|---|---|---|
| critical | 16 | 0 | 0 | 0 | 0 | 0 | 16 |
| high | 105 | 1 | 4 | 5 | 1 | 0 | 116 |
| medium | 256 | 0 | 5 | 13 | 9 | 5 | 288 |
| low | 11 | 205 | 2 | 4 | 4 | 0 | 226 |
| total | 388 | 206 | 11 | 22 | 14 | 5 | 646 |

The status names mean:
- "removed_with_feature": the entry named the deleted trading surface and was closed with D81.
- "blocked_tier4": the fix touches a locked file or needs money, identity or a GUI runner (§4).
- "needs_gui": the fix needs a human click-through (§4).
(at the rc1 tag: re-derive this table at the tag sha.)

**Open critical: none. Open medium: none in the register** (two new mediums are waiting to be
filed; see below).

**The rc1 residual: what stands between here and the rc1 tag.**

- **`R15-LEAD-030` (high, agent-chat).** After a tool errors or is never called, the local model
  (llama3.1:8b) can write a made-up "the X tool returned …" citation with a financial figure that
  no tool result carries. The register opened it from the batch-14 and batch-15 verifiers'
  sightings, for example a fake "$1320 m" TTM revenue dump after a `SIFY.NS` tool error. Its
  history:
  - Batch 16 (`50399b67`) added a guard that replaces a citation of a tool with no ok result.
    Not certified: a humanised tool name ("Price Data: {…}") escaped live; a dump that opens on
    the line after the replaced citation escaped; and a follow-up turn's true citation of an
    earlier turn's tool was wrongly replaced.
  - Batch 17 (`4b6acb6b`) seeded the ok-tool set from the chat history, matched humanised names
    and dropped cross-line dumps. It fixed every batch-16 escape, but was not certified a second
    time: a true sentence that mentions the errored tool beside a true figure from another tool
    ("The fundamentals tool returned an error, so I used financial statements, which shows
    revenue of ₹4,411 cr.") is replaced whole and the figure is lost. That problem was already in
    the base. A minor camelCase escape ("PriceData") also remains. The branch was still strictly
    better than the base: 2 offline probe failures against 9.
  - Batch 18 step 1 (running) is one strongest-tier agent, per routing change 5: two Opus
    attempts failed. Its spec is a structural guard that replaces only a clause attributing a
    figure or dump to a non-ok tool, never the whole sentence, with a live bar of 0/8 fabricated
    and 0/8 true citations replaced. If it also fails, a fresh verifier adjudicates the entry with
    a written rationale and records it in `DECISIONS_FOR_OPERATOR.md`; it is never dropped
    silently.
- **`R15-LEAD-033` (medium, agent-chat), filed from a verifier observation (`701751b9`).** The
  "[tool steps: …]" trailer is stored inside the assistant message text (`withTrailer` in
  `src/store/chat-history.ts`), so the model echoes it into a later answer.
- **`R15-LEAD-034` (medium, data-smallcaps), filed the same way.** Background fundamentals
  warming passes bare screener symbols to the correctness gate, which never strips yfinance's
  `-SM` Emerge infix. So every NSE SME symbol fails the gate as a symbol mismatch. The mechanism
  was confirmed from code; no raw log survived, so the writer must reproduce it first.
- LEAD-033 and LEAD-034 sit in `r15/stage-c/LEAD_FOUND.json` and enter the register at batch
  18's adjudication. The rc1 criterion counts them.
- **`R15-LEAD-031` (low)** was certified in batch 17 and still reads open until that same
  adjudication.
- (at the rc1 tag: replace this block with how each entry closed.)

**needs_gui (11): each waits for a human click-through.** The check for each is in §4.

**blocked_tier4 (22), grouped by the decision each waits on** (row numbers are sections of
`DECISIONS_FOR_OPERATOR.md`):

| Waits on | Entries | Rows |
|---|---|---|
| Money and identity for releases: signing certificates, a release workflow, the updater, CI on this branch | RELEASE-001, RELEASE-002, RELEASE-003, RELEASE-004 (high) | 2.8–2.11 |
| A funded provider lane | AGENT-017 (high: the shipped default model returns `content_filter`), AGENT-049 (native search has no cap or spend meter) | 4.2, 4.3 |
| An e2e runner call (Playwright against a real window) | UI-088 (drag gestures untested) | 4.4 |
| A Tier-1 CI workflow edit under `.github/` | CODE-PLATFORM-073 (token audit), CROSS-PLATFORM-001 (Windows/Linux CI), CODE-PLATFORM-063 (ruff over `scripts/`), RELEASE-012 (sidecar build cache), DOCS-011 (CLA check + CLA text) | 2.16, 2.17, 4.5, 4.8, 4.7 |
| A CLAUDE.md or BLUEPRINT §2 Locked-row edit | DOCS-003 (docs name Next.js; the app ships Vite), DOCS-015 (retired plugin-panel model in docs), DOCS-008 (OpenBB described as an in-process wrap) | 2.19, 2.20, 4.6 |
| Plugin contract or core architecture | CODE-PLATFORM-015 (plugin data contribution is declaration-only), CODE-PLATFORM-071 (first-party panels bypass the plugin model), AGENT-064 (no user-chosen MCP server) | 2.14, 2.15, 2.12 |
| `tauri.conf.json` CSP and file-write confinement | CODE-PLATFORM-010 | 2.13 |
| The first-launch terms surface and the accepted agent-write gaps | UI-044 (keychain read failure blocks onboarding), CODE-FRONTEND-013 (no durable record of agent writes) | 2.21, 3.3 |
| A business identity (a real commercial-licence inbox) | DOCS-002 | 2.18 |

**Lows.** 226 in total: 11 fixed, 4 removed with trading, 4 blocked_tier4, 2 needs_gui and **205
open**. The lows pre-triage (`r15/stage-c/lows-triage/LOWS_TRIAGE.md`) sharpened each into a fix
shape and an acceptance test. The partition (`r15/stage-c/lows/PARTITION.md`, base `4097dac4`,
patched `dd7b98e9`) places them for three concurrent write runs:

| Partition | Writer sets | Entries | Verify-only |
|---|---|---|---|
| P1 | 9 | 63 | 1 (CODE-FRONTEND-033) + AGENT-065 proposed not a defect |
| P2 | 9 | 64 | 1 (UI-082) |
| P3 | 9 | 67 | 2 (AGENT-086, CODE-FRONTEND-031) |

- Outside the partitions are 5 inseparable lows that span several sets: AGENT-085,
  CROSS-PLATFORM-012, UI-068, UI-071 and UI-073. They run as a serial set after the three
  partitions merge.
- LEAD-031 (fixed in batch 17) is the one open low placed nowhere.
- The write runs launch at the batch-18 merge with up to 16 writers each. Writers stay in their
  own worktrees and run focused tests only. Integration runs after the rc1 tag, one partition at
  a time, each partition rebased onto the rc1 head and checked by a fresh verifier.

## 4. Operator-attended list — things only you can do

Row numbers are sections of `docs/redesign/DECISIONS_FOR_OPERATOR.md`, which gives, for each
row, what is blocked, the smallest unblock and the undo.

**Money and provider lanes**
- **§2.1: the default provider lanes are unfunded.** OpenRouter's paid balance is negative and
  DeepSeek-direct is at $0; the figures are in the git-ignored `r15/local/BUDGET.md`. Your composer
  lane (`openai` / `gpt-5.6-luna`) is funded. Top up OpenRouter before hand-testing research,
  because the keyless research default rides it. Restart your dev stack as well: `043850c` fixes
  the gpt-5.x tool-calling 400 on your lane.
- **§4.2 `R15-AGENT-017`: the shipped default chat model** (DeepSeek V4 Flash via OpenRouter)
  returns `content_filter` on ordinary portfolio-write asks. Once the lane is funded, run the eval
  loop's portfolio-write scenario against `glm-5.1` and `kimi-k2.6`, and ship whichever passes as
  the default.
- **§4.3 `R15-AGENT-049`: the native-search lane.** Native web search off Anthropic has no per-run
  cap, and BudgetGuard never sees its cost. Closing this needs a live native-search lane: a funded
  OpenRouter lane or a reachable Gemini or Anthropic key.
- **§2.2: OrbStack.** Docker/OrbStack is not running, so SearXNG is down and research silently
  falls back to the keyless scraper tier. Start OrbStack before judging research depth.

**The e2e runner**
- **§4.4 `R15-UI-088`.** Dockview tab reorder and the node-editor's palette-to-canvas drop have no
  automated coverage. The fix is a Playwright suite run against a real window, which needs your
  call on an e2e runner and where its tests live, and then a GUI-attended run to certify it.

**The filing-watcher model groundwork**
- The measured candidate model peaked at an 11.3 GiB memory footprint on this 16 GiB Mac, per
  `time -l`. Weigh that before anything runs it alongside the app. The verdict for this release
  is not worth fine-tuning.
- **Folder choice:** its measurement folder `docs/redesign/verification/r15/laya/` sits in the
  public verification tree today. One line from you moves it under the git-ignored
  `docs/redesign/verification/r15/local/` instead.

**Licence wording**
- **§3.4: the commercial-licence broker sentence.** `COMMERCIAL_LICENSE.md:36-48` still says the
  licensee "is responsible for their own broker relationship". It is still true, so no change is
  required; dropping it is your call.
- **§3.2: the first-launch terms.** They now say research-only and carry a licence line (PolyForm
  Strict noncommercial or a commercial licence). Review the copy in
  `src/modules/safety/DisclaimerFlow.tsx` before it ships.
- **CLAUDE.md.** Its Locked-decisions line still says "AGPL-3.0 + commercial dual license". The
  fix is queued in `docs/redesign/CLAUDE_MD_PROPOSAL.md` for the single CLAUDE.md commit at
  Stage D.
- Whether your own personal trading counts as "noncommercial" under PolyForm Strict is a question
  for a lawyer, not for this run.
- The bundled copyleft packages (AGPL openbb and sec-edgar-mcp binaries, LGPL frozendict in two
  sidecars) are listed as facts in `r15/stage-d/OPEN_QUESTIONS.md` §2. They were checked at
  `f4444790` and are re-scanned at the Stage D refresh.

**Signing and release (Tier-1 files plus credentials)**
- **§2.8 `R15-RELEASE-001`: unsigned bundles.** Gatekeeper calls the `.dmg` damaged, and
  SmartScreen flags the installer. The blueprint's Windows route was the SignPath Foundation free
  OSS tier, but that tier needs an OSI licence without commercial dual-licensing, and the 23 Sep
  PolyForm Strict + commercial relicense does not qualify (per the register's root cause for
  RELEASE-001). Windows signing therefore needs a paid certificate or another route. On macOS, the
  minimum is `bundle.macOS.signingIdentity: "-"` in the Tier-1 `tauri.conf.json`; Developer ID
  plus notarization needs a paid Apple account.
- **§2.9 `R15-RELEASE-002`:** approve a `.github/workflows/release.yml` (tauri-action 3-OS
  matrix).
- **§2.10 `R15-RELEASE-003`:** then set `createUpdaterArtifacts: true`.
- **§2.11 `R15-RELEASE-004` and §2.6: CI has never run on this branch,** and the last `main` run
  is red. Open a draft PR for `004-r4-experience-rebuild`; that needs no workflow edit.
  `pnpm ci-local` is the real local gate meanwhile.

**The Tier-1 CI edits the four blocked lows need** (§4.5–4.8; each is a file only you may touch)
- **§4.5 CODE-PLATFORM-063:** widen ruff from `sidecar` to `sidecar scripts` in
  `.github/workflows/lint.yml:87-89`, and mirror that in `package.json`'s `ci-local`.
- **§4.6 DOCS-008:** reword the Locked row at `docs/BLUEPRINT.md:55`, and the §3.1 sentence at
  `:84`, to describe the `openbb-mcp` subprocess.
- **§4.7 DOCS-011:** add a CLA-check workflow under `.github/workflows/` and finalise the CLA text
  that `CONTRIBUTING.md:95` points to. This is low-risk while contributions stay closed.
- **§4.8 RELEASE-012:** add an `actions/cache` step around `ensure-all-sidecars` in `build.yml`,
  `test.yml` and `lint.yml`.

**Secrets and leftovers**
- **§3.1 purge of trading leftovers.** These are orphaned OS-keychain broker secrets
  (`broker:<id>:api_key|api_secret|access_token|client_id`) and old audit rows in
  `~/.vysted-terminal/audit_log.db`. No code reads them, and nothing purged them, because deleting
  a user's secrets automatically is irreversible. Approve a one-time purge step, or a CHANGELOG
  note on removing them by hand.
- The Stage D history secrets scan at `f4444790` found 0 real or unknown secrets. It reruns at the
  Stage D refresh.

**Keychain dev signing** (`docs/redesign/KEYCHAIN_DEV_SIGNING.md`)
- Solved on 11 Jun 2026: debug builds keep secrets in a git-ignored
  `<app-data-dir>/dev-keystore.json` (mode `0600`) instead of the OS keychain, so `pnpm tauri:dev`
  rebuilds raise no keychain dialogs. Release builds use the real keychain, unchanged.
- One-time step: the first dev boot migrates existing keychain secrets into that file, with one
  final dialog.
- `CLAUDE.md`'s keychain gotcha still describes the older self-signed-certificate route
  (`scripts/macos-dev-setup.sh`). Reconcile the two in the single CLAUDE.md commit.

**Other rows still open**
- §2.7: an away-sentinel for the GUI rig.
- §3.3: the accepted agent-write gaps. There is no durable record of agent writes past the
  10-minute ledger, and no AUTO stop control beyond reject or run-cancel.
- §3.4: the `"trading-bot"` `PluginType` literal in the locked `types/plugin.ts`.
- §4.1: how FAST research handles an uncached Indian name's first brief. The recommendation is
  (a) accept the honest drop for rc1, then (c) show provider values flagged "exchange filings not
  yet checked".
- §2.12–2.21: the architecture and docs items grouped in §3.

**needs_gui (11): a human click-through on the packaged app.** The rig's computer-use grant does
not cover the built app (`com.vysted.terminal`), so none of these was tried unattended in rc1
round 1. Each check below is condensed from the entry's register note.
- `CODE-AGENT-001` (high): in the packaged app and in `pnpm tauri:dev`, every panel loads and the
  sidecar log shows no 403 for the webview's own origin.
- `LIFECYCLE-001` (high): on a packaged **cold launch after a reboot**, the window paints and
  takes input while the MCP children bind (no beachball for 25–90 s), and `/health` answers first.
  A renamed sidecar binary turns the status chip red; a killed sidecar shows "Sidecar error".
- `LIFECYCLE-008` (high): in the packaged app, `<data-dir>/logs/vysted.log` gets timestamped
  `[sidecar]`/`[vysted]`/MCP lines and rotates, and Settings "Copy diagnostics" previews and then
  copies.
- `UI-009` (high): in the packaged macOS app, Export CSV in Watchlist, Portfolio and Screener
  shows the saved path, and the file exists under `<app data>/exports/csv/`.
- `UI-022` (medium): this needs **native event injection, not chrome-devtools**. A drawing clicked
  mid-candle renders at the clicked price; a click past the last bar places a visible drawing;
  Text shows the typed label; a locked drawing's delete stays disabled.
- `UI-025` (medium): in the packaged app, select note text and click Link; an inline URL popover
  appears and applying it sets the link.
- `UI-050` (medium): in the Notes slash menu, check whether a two-line row still clips (visual
  only).
- `UI-083` (medium): a settled research brief's PDF and PNG export renders correctly in the
  WKWebView.
- `UI-084` (medium): open the agent dock, maximise it, and confirm it spans the cockpit at 2560
  wide; un-maximise it and confirm the prior width returns.
- `DOCS-024` (low): in a real Claude Desktop session over mcp-remote/stdio, invoke a Vysted tool
  and capture what the slash picker shows.
- `LIFECYCLE-040` (low): launch the packaged bundle on each platform, Windows included, and record
  the cold-boot MCP-spawn check in `docs/redesign/DECISIONS.md`.

## 5. How to relaunch

**Run the app on this code.** `pnpm tauri:dev` runs `pnpm tauri:mcp`, which runs `tauri dev
--features dev-tools` (`package.json`). The webview is Vite (`pnpm dev` = `vite`). The three
sidecar binaries (main, openbb-mcp, sec-edgar-mcp) must exist first:
- `pnpm sidecars:build` rebuilds all three by force, via `scripts/ensure-all-sidecars.mjs`.
- The ensure scripts also rebuild any binary older than its source.
- `node scripts/smoke-test-sidecars.mjs` boots each built binary and polls `/health`.
- `pnpm ci-local` is the full local gate, mirroring CI step for step.
A packaged bundle from a clean profile is a Stage D step and has not been built in this run.

**The local-model lane.** Ollama with `llama3.1:8b` is the model the run's live agent bars use;
the ADR-ratio and tool-citation checks in batches 12–17 ran on it. The run drives it through `scripts/r15/vy.py invoke --provider ollama --model
llama3.1:8b` against an isolated sidecar, never your own data dir or keychain. The lane proof and
the model comparison (qwen2.5:7b, llama3.1:8b, qwen3:8b) are in
`docs/redesign/verification/r15/stage0/LOCAL_LANE_PROOF.md`. The lane is single-owner: the rc1
gate script holds a local-model lock, so only one workflow drives the model at a time.

**Keychain dev signing.** See `docs/redesign/KEYCHAIN_DEV_SIGNING.md` and §4. Dev builds use the
dev keystore file, so after the first boot's migration dialog there is nothing to sign or
re-approve.

**Resume the R15 run itself.** The run-state (`docs/redesign/verification/vysted-r15-run-state.md`)
is rewritten at every checkpoint and carries a literal "Resume prompt" block to paste into a fresh
session. Its "Next action" line at this sha:
1. Batch 18 step 1 (running), then step 2.
2. Lead merge and adjudication to 0 open critical/high/medium.
3. The three lows write runs (`r15/tooling/lows-waves.js`, `mode:'write'`, P1/P2/P3).
4. rc1 gate round 2 (`docs/redesign/verification/r15/tooling/rc1-gate.js`), once no writer is
   running tests. The gate ends in `R15_GATE_RC1.md` naming a tag sha; the lead tags and pushes,
   not the workflow.
5. `r15-rc1`.
6. Lows integration, one partition at a time.
7. Stage D.
8. `r15-rc2`.
9. The one small build from the judge panel's top survivor.
10. `r15-rc3`.
11. One final adversarial pass.
12. `r15-launch`.
(at the rc1 tag: drop the steps already done.)

## 6. Where every evidence file is

Every path below was checked present at this sha, except the two rows marked "not on disk".

| What | Path |
|---|---|
| R15 mandate: on disk only, git-ignored, never in any commit; not read by this refresh | `docs/redesign/verification/R15_BRIEF*.md` |
| Run state (header, in-flight ledger, loop log, resume prompt) | `docs/redesign/verification/vysted-r15-run-state.md` |
| Run report / run log | `docs/redesign/verification/R15_RUN_REPORT.md`, `R15_RUN_LOG.md` |
| Defect register (machine view + human view) | `docs/redesign/verification/vysted-r15-register.json`, `.md` |
| Leads waiting to be filed (LEAD-033/034) | `docs/redesign/verification/r15/stage-c/LEAD_FOUND.json` |
| Stage 0 facts and the local-lane proof | `docs/redesign/verification/r15/stage0/RECONCILE_MANIFEST.md`, `LOCAL_LANE_PROOF.md` |
| Census: promise and opportunity ledgers; Gate 2 | `docs/redesign/verification/r15/census/PROMISE_LEDGER.md`, `OPPORTUNITY_LEDGER.md`; `docs/redesign/verification/R15_GATE2.md` |
| Trading-removal plan (D81) | `docs/redesign/verification/r15/stage-c/REMOVAL_PLAN.md` |
| Stage C batches 2–17: plan and verdicts (batches 14–17 also `verifier-evidence/`) | `docs/redesign/verification/r15/stage-c/batch-<2..17>/PLAN.md`, `VERDICTS.json`, `VERDICTS.md` |
| Stage C batch 18 (in flight; not on disk at this sha) | `docs/redesign/verification/r15/stage-c/batch-18/` |
| rc1 gate round 1: sheet, verdict excerpts, findings, Gate 8, fix rounds | `docs/redesign/verification/R15_GATE_RC1.md`; `docs/redesign/verification/r15/rc1/` (`VERDICT.md`, `FINDINGS.md`, `GATE8.md`, `fix-r1/`, `fix-r2/`, `verifier/`) |
| rc1 refutation audit | `docs/redesign/verification/r15/rc1/refutation-audit/REFUTATION_AUDIT.md` |
| Lows pre-triage and partition | `docs/redesign/verification/r15/stage-c/lows-triage/LOWS_TRIAGE.md`; `docs/redesign/verification/r15/stage-c/lows/PARTITION.md` |
| Filing-watcher model groundwork (verdict, measurements) | `docs/redesign/verification/r15/laya/` |
| Ranked backlog; judge panel output (not on disk at this sha) | `docs/redesign/verification/r15/invent/BACKLOG.md`; `docs/redesign/verification/r15/invent/PANEL.md` |
| Workflow scripts and their plans (`stage-c-batch.js`, `rc1-gate.js`, `lows-waves.js`) | `docs/redesign/verification/r15/tooling/` |
| Stage D drafts and scans (this file included) | `docs/redesign/verification/r15/stage-d/` |
| Decisions log (autonomous) / decisions for you (Tier-4) | `docs/redesign/DECISIONS.md` / `docs/redesign/DECISIONS_FOR_OPERATOR.md` |
| Keychain dev-signing runbook | `docs/redesign/KEYCHAIN_DEV_SIGNING.md` |
| CLAUDE.md edits queued for your review | `docs/redesign/CLAUDE_MD_PROPOSAL.md` |
| Per-batch history | `CHANGELOG.md`: sections for the trading removal and batches 2–11; batches 12–17 and the rc1 fix rounds have no section yet |

## 7. What R15 decided on its own that you may want to revisit

These are the decisions made since the earlier draft (`f4444790`, 24 Sep 22:47 IST), taken from
the run-state's in-flight ledger and loop log and from `docs/redesign/DECISIONS.md`. Everything
below already happened, and where an undo exists it is named. The earlier items (§1.1 the
committed `enrich_nse_sectors.py` fix, §1.3 the one-time rewrite of never-pushed commits, §1.4 the
relicense, §3.5 D-B3-1 the AUTO scope, §3.6 D-B4-1 context admission) stand as before in
`DECISIONS_FOR_OPERATOR.md`.

1. **Batch 11 ran before the rc1 gate.** After batch 10, 22 fixable highs and mediums remained,
   and the rc1 criterion is that critical, high and medium are all closed. Tier-4 and funded-lane
   items stayed excluded.
2. **The batch-10 S&P 500 regeneration was reverted** (`d5370601`). The shipped US seed pack
   lacked 40 of the 503 new names. Batch 11 then shipped and certified LEAD-013 properly.
3. **D-B10-1: the external MCP surface is read-only in 0.9.** Host actions stay in-app behind
   the proposed-changes gate, and AGENT-083 was concurred not a defect on that basis. Opening the
   surface later is your call.
4. **D-B11-1..10** are recorded in `DECISIONS.md`. The ones with product effect:
   - D-B11-3 (superseding D-B10-8): a partial price series makes the registry try the next lane.
   - D-B11-7: provider fallback fires only on a classified failure before any answer text.
   - D-B11-9: portfolio risk metrics are computed per currency bucket, with rf = 0 labelled.
5. **After rc1 round 1 failed, the refutation audit ran before any re-plan,** because a 100%
   refutation rate was itself suspect. The audit upheld all 14 refutations. The gate rubric then
   restored the not-a-defect concurrence requirement (`3c51ac3c`), and every verifier gained the
   rule "certify the claim, not only the repro" (`f1a2682d`).
6. **Three entries became operator-attended rather than code work** (`bc3e64fe`): AGENT-017 and
   AGENT-049 need a funded or reachable lane, and UI-088 needs an e2e runner (§4.2–4.4).
7. **A batch merges even when one entry is not certified,** because nothing is tagged between
   batches and the entry stays open in the register. This happened to AGENT-090 in batches 12–15
   and to LEAD-030 in batches 16 and 17. Batch 17's verifier also measured its branch as strictly
   better than the base. After two failed Opus attempts on the same
   entry, one strongest-tier agent takes the root cause (routing change 5). AGENT-090 then
   certified in batch 16. If LEAD-030 still fails, it goes to a fresh verifier's written
   adjudication, recorded in `DECISIONS_FOR_OPERATOR.md`.
8. **rc1 round 2 runs without a GUI round** (`skip_gui`), because the rig's computer-use grant
   does not cover the built app. All needs_gui entries are listed as yours (§4).
9. **The filing-watcher model groundwork** stopped at 339 agreed items, against an aim of 1,000,
   rather than invent data or add a non-R15 source. Its folder stays in the public verification
   tree until you choose otherwise (§4).
10. **Lows buckets:** the 4 lows that need Tier-1 files became blocked_tier4 with rows 4.5–4.8,
    the 2 GUI-only lows became needs_gui, and the 5 inseparable lows run as one serial set after
    the partitions (`3483b699`).
11. **§4.1 FAST research:** fix round 2 made a timed-out exchange-filing overlay still land in
    the cache, so the second brief gets the card. The first-brief drop is left as the honest
    degrade for rc1 and is yours to decide.

(at the rc1 tag: add any decision batch 18 or gate round 2 records.)

<!-- critic-footer -->

## Critic findings applied

The Stage D critic reviewed the `f4444790` draft and made ten findings. This refresh re-derived
every number from disk at `82d3d083`, so the findings about stale register counts no longer apply
as written. Their status now:

1. superseded — the `a288397` "register one batch behind" paragraph. The register now lags the
   code by one entry only (LEAD-031), and §2 says so.
2. superseded — the open-medium breakdown (28 / 14 / 72). The register shows 0 open mediums, and
   §3 now describes the rc1 residual instead.
3. superseded — the "~85 mediums left" line in §1. It is gone.
4. superseded — "Open high (3 in the register, 2 real)". There is now 1 open high (LEAD-030):
   AGENT-007 and LEAD-022 are fixed, and AGENT-017 is blocked_tier4.
5. carried forward — §6's R15_BRIEF row still says on disk only, git-ignored and never committed.
   The Stage D folder is committed now, so its "untracked" note is dropped.
6. carried forward — §5 uses the full `docs/redesign/verification/r15/tooling/rc1-gate.js` path.
7. carried forward — §5 says the gate names a tag sha and the lead tags and pushes, not the
   workflow.
8. revised — the needs_gui block. rc1 round 1 deferred its GUI round, so all 11 checks are yours.
   The "cold launch after a reboot" (LIFECYCLE-001) and "native event injection" (UI-022) markers
   are kept.
9. revised — the CODE-FRONTEND-008 note. It is fixed in the register. The AUTO-stop gap it once
   tracked is stated directly in §4 under §3.3, beside CODE-FRONTEND-013 (blocked_tier4).
10. superseded — both markers about batch 10's planned flips. Batch 10 merged, and both flips are
    applied: UI-050 and UI-083 are needs_gui, and the 11 Tier-4-only ids are blocked_tier4.
