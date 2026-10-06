<!-- DRAFT at 4d893147def983623de681effd1bfbae2e7441c5 by the Stage D docs wave; refresh before rc2 -->

# Operator Briefing — R15 "LAUNCH"

This is a draft written while you were away. The lead promotes it to `docs/redesign/OPERATOR_BRIEFING.md` at rc2; until then it is not that document. Every fact below was re-read from disk
at sha `4d893147` on `004-r4-experience-rebuild`: `r15/stage-d/FACTS.md` first (not re-derived), then the run-state, register JSON, each batch's `VERDICTS.md`, `DECISIONS_FOR_OPERATOR.md`
and `KEYCHAIN_DEV_SIGNING.md`. "Round 2" below means the rc1 gate's second run; no `r15-rc1` tag exists yet.

## 1. State in one paragraph

Vysted Terminal is a desktop finance terminal: a Tauri shell, a Vite + React webview and a Python sidecar. **R15 "LAUNCH"** is an autonomous run verifying it end to end: a census of every
promised or discovered defect, then fix batches ("Stage C"), then release-candidate gates. At sha `4c6dfe8c`, 23 Stage C batches have reached a first-parent merge (newest `6778f892`, batch
24); batch 23 closed without merging (its fix regressed and was dropped). The register holds 652 entries: 391 fixed, and **zero** critical/high/medium entries open. `R15-LEAD-035` (medium)
is now `blocked_tier4` alongside its three siblings (`LEAD-030`, `LEAD-037`, `LEAD-038`) — but as an ESCALATION under the operator's three-failure rule, not a fresh-verifier concurrence like
the other three: batch-24's verifier REFUSED certification a fourth time and named a further narrowing-only fix it would certify. This is now your call at rc1 (§3, §4.10). rc1 gate round 1
failed at 09:57 IST 25 Sep, no tag was cut; round 2 launched from `4c6dfe8c` (run `wf_4ed38558-4d0`) now that the register reads 0 open critical/high/medium.
Trading is out of the product for good (D81); the core licence is PolyForm Strict 1.0.0 plus a commercial licence, the plugin contract and example plugin stay Apache-2.0. Every version file
still reads **0.8.0** (`package.json:3`, `src-tauri/Cargo.toml:3`, `src-tauri/tauri.conf.json:4`, `sidecar/app.py:329`, `src/lib/plugin-bootstrap.ts:38`); a version branch bumping to 0.9.0 +
a single `CLAUDE.md` commit is prepared on its own branch (head confirmed at the tag), merging right after `r15-rc1`, not before. Newest tag: still `r13-bedrock`; nothing has shipped to
you. <!-- fill at rc2: newest tag, round-2 result -->

## 2. What shipped (one line per batch: merge commit, scope, tally)

"Certified" means a fresh verifier re-proved the claim on the running app. "needs_gui" means a human click-through is required (§4). Ids drop the `R15-` prefix.

- **Trading removed (D81)** — `a122dbf6`, Stage C batch 1: 0 broker/order/kill/audit routes left,
all 22 former routes 404.
- **Relicense** — `0c63d465`: AGPL-3.0 → PolyForm Strict 1.0.0 (noncommercial) + a commercial
licence; `types/plugin.ts` and the example plugin stay Apache-2.0.

| Batch | Merge | Scope | Certified | needs_gui | Not certified |
|---|---|---|---|---|---|
| 2 | `806a90ca` | critical/high data, research, workspace | 37 | 0 | 3 |
| 3 | `c81d879b` | agent runtime, AUTO gate, LLM adapters, research depth | 38 | 0 | 2 |
| 4 | `dcbe7bae` | context admission, Gemini/xAI lanes, workflows, market-data gate | 45 | 2 | 3 |
| 5 | `1574ed8e` | India exchange lanes, resolver, runtime liveness | 48 | 2 | 6 |
| 6 | `5e147317` | India Emerge lanes, tool-call identity, research funnel | 21 | 0 | 3 |
| 7 | `e81c9e7c` | India fundamentals, durable Delegate runs, chart integrity | 50 | 1 | 4 |
| 8 | `68bb7aa4` | sidecar lifecycle, provider readiness, data-error honesty | 39 | 1 | 7 |
| 9 | `6b702305` | tool-call identity, research brief contract, fundamentals truth | 29 | 2 | 14 |
| 10 | `f407107f` | runtime/backtest integrity, catalog and host actions, plugin lifecycle | 50 | 1 | 4 |
| 11 | `4097dac4` | build recipe and gates, schema versions, agent eval, option chain | 18 | 0 | 2 |
| 12 | `ef33c7f6` | rc1 refutation-audit reopenings, gate findings | 19 | 0 | 3 |
| 13 | `a217a529` | source tiers (Public Suffix List), live universe counts, ADR ratio guard | 2 | 0 | 2 |
| 14 | `17301f54` | tool_result stream event/grader; ADR ratio guard pass 2 | 1 | 0 | 1 |
| 15 | `74ee3468` | ADR ratio grounded from the SEC 20-F cover page | 0 | 0 | 1 |
| 16 | `d64640d2` | ratio-guard class qualifier, citation guard, bounded ADR lookup | 2 | 0 | 1 (LEAD-030) |
| 17 | `292ba53a` | citation guard across turns, partial tool-call marker hold | 1 (LEAD-031) | 0 | 1 (LEAD-030) |
| 18 | `ebc5ed41` | figure-guard fixes | 2 (LEAD-033, LEAD-034) | 0 | 1 (LEAD-030, 4th time) |
| 19 | `ec7f7cd6` | colon binding, all-errored result blocks | 0 | 0 | 1 (LEAD-030, 5th time) |
| 20 | `1abef99b` | figure grounding by provenance (new `figure_grounding.py`) | 0 | 0 | 2 (LEAD-030, 6th time; LEAD-036) |
| 21 | `86ae79c4` | short-name aliases, unclosed-fence handling, no-tool cue (server-side) | 0 | 0 | 3 (LEAD-030, 7th; LEAD-035; LEAD-036) |
| 22 | `c155e5ad` (W1 only) | figure-grounding residuals, rule-2c fail-safe | 0 | 0 | LEAD-030 (8th, stop rule fired); LEAD-035 W2 rejected as a regression |

- **Batch 23 — not merged.** Its LEAD-035 fix regressed on qualified negations (7/7 live prompts
fabricated a price); the stop rule fired a third time and the branch was dropped, so batch-21's closed-list matcher still ships. Its verifier instead **concurred** `LEAD-030` →
`blocked_tier4` (broader wording, `535307c8`) and filed two new mediums, `LEAD-037`/`LEAD-038` (§3). Disposition concurrence `4fd3cbfd` (141 live runs): LEAD-038 CONCUR, LEAD-037 CONCUR on
corrected wording, LEAD-035 REFUSED with a named narrowing-only fix; `1db862d0` applied it (LEAD-037/038 → `blocked_tier4`, LEAD-035 stays `open`).
- **Batch 24 — merged `6778f892` (int `d1290f66`).** One entry, one change: a closed-tail
lookahead plus `(?<!said )(?<!say )` on `LEAD-035`'s `_NO_TOOL_CUE` regex
(`sidecar/services/planner.py`, narrowing-only, pinned in `test_b3_runtime_intent_gate.py`).
The fresh verifier found the narrowing HOLDS as a strict subset (0 new strips on 97
phrasings, 0 over-strips on the 67 pinned no-tool phrasings, the 7 previously over-matched
data prompts now call `price_data` live 21/21) but did **not certify** — LEAD-035's fourth
certification failure: 4 of 18 fresh qualified-negation data requests still lose every tool
(a comma before "except"/"other than"; reported speech "He says don't use tools, but …") and
the local model then states an invented price in 6/8 live runs. The verifier **REFUSED** the
`blocked_tier4` concurrence and instead named a further narrowing-only guard (a qualifier
negative lookahead plus `(?<!says )`) that clears 3 of the 4 offline with 0 lost strips and
that it would certify (`stage-c/batch-24/LEAD-035-CONCURRENCE.md` §3). Under your three-
failure stop rule (pacing change 4), the lead set `LEAD-035` to `blocked_tier4` at `4c6dfe8c`
— an escalation to you, not a concurrence-based adjudication (§3, §4.10).
- **Version branch** `worktree-agent-r15-version-0.9.0` (launched `c8d807a6`, run `wf_1d24a3f2-c0e`;
branch head — `517da226` bump + `c1e9164c` the single `CLAUDE.md` commit — not yet merged at this sha, confirmed at the tag): 0.9.0 everywhere + the single `CLAUDE.md` commit, queued to merge
right after `r15-rc1`. CHANGELOG.md covers batches 2–17 + trading removal + gate round 1; 18–24 have no section yet.

## 3. What is open and why

**Register counts (severity × status)** at this sha: severity totals from the register JSON's own `counts` field; the status split from its `entries[].status` (sums equal `counts`; never
`register.py status`, which recomputes from census merges and lags):

| severity | fixed | open | needs_gui | blocked_tier4 | removed_with_feature | not_a_defect | total |
|---|---|---|---|---|---|---|---|
| critical | 16 | 0 | 0 | 0 | 0 | 0 | 16 |
| high | 105 | 0 | 4 | 6 | 1 | 0 | 116 |
| medium | 258 | 0 | 5 | 16 | 9 | 5 | 293 |
| low | 12 | 205 | 2 | 4 | 4 | 0 | 227 |
| total | 391 | 205 | 11 | 26 | 14 | 5 | 652 |

(Table is the `4c6dfe8c` state: `R15-LEAD-035` moved medium `open`→`blocked_tier4`, so medium
`open` 1→0/`blocked_tier4` 15→16 and the totals move 206→205 `open`/25→26 `blocked_tier4`
versus this section's `4d893147` capture.)

Open critical/high/medium: **none**, as of `4c6dfe8c`.

### Known limitations at rc1 — agent chat with a keyless local model

Accepted by you Sat 26 Sep 04:15 IST (Tier-4 sign-off): `LEAD-030`, `LEAD-037`, `LEAD-038` ship `blocked_tier4` as one documented limitation class. `LEAD-035` now carries the SAME status
(`blocked_tier4` as of `4c6dfe8c`, batch-24 merged `6778f892`) but for a different reason: it is an ESCALATION under your three-failure stop rule, not a fresh-verifier concurrence — batch-24's
verifier REFUSED certification a fourth time and named a further narrowing-only fix it would certify (§4.10 below has the detail and your two options). No further filter round this release
for the other three: a fresh "the local model states a figure with no successful tool call behind it" files against this limitation, not as a new fix. Carried verbatim into
`RELEASE_NOTES.md`, `CURRENT_STATE.md` and this file, per your sign-off (LEAD-035's wording pending your (a)/(b) choice).

- **`R15-LEAD-030`** (high, `blocked_tier4`, fresh verifier concurred in batch 23,
`r15/stage-c/batch-23/LEAD-030-CONCURRENCE.md`):
  > With a keyless local model, the agent can still state an invented price or metric as if a
  > tool had returned it when the figure is about a company no successful tool call in that turn
  > covered — one named in the same paragraph as a company whose call succeeded (under a name the
  > guard cannot map, or never looked up at all), or any company in a turn where no call failed or
  > no tool was called — and a figure-less fabricated result dump or a code fence left open from
  > an earlier round can also render, and every shape pinned in eight fix rounds is replaced by an
  > honest "returned no data" note.
- **`R15-LEAD-035`** (medium, `blocked_tier4` as of `4c6dfe8c` — an ESCALATION under your
  three-failure rule, NOT a fresh-verifier concurrence like the other three; batch-24's verifier
  REFUSED certification a fourth time; this is your call at rc1, §4.10):
  > With a keyless local model, the "don't use tools" detector is a fixed phrase list: an
  > unrecognised no-tool phrasing keeps the tools, so the agent may still read data and propose a
  > portfolio change (always held for your review, never applied; under AUTO a watchlist or chart
  > change does apply) and can occasionally state a price it never fetched, while a data request
  > that qualifies a no-tool instruction after a comma or in reported speech ("Don't use any
  > tools, except price_data …", "No tools, other than the price lookup …", "He says don't use
  > tools, but …") still loses every tool and the agent then usually states an invented price as
  > if fetched.

  Your two options at rc1 (§4.10): (a) accept this residual as a documented known limitation
  with the wording above, or (b) authorise one bounded round for the verifier's named guard (a
  qualifier negative lookahead plus `(?<!says )`, which clears 3 of the 4 remaining over-matches
  offline with 0 lost strips) on the rc2 line. **The lead recommends (b).**
- **`R15-LEAD-037`** (medium, `blocked_tier4`, concurred on corrected wording):
  > With a keyless local model, a figure the agent states for a company whose data call succeeded
  > is not checked against that result at all, so it can give an older bar's value from the same
  > payload as the current price (2 of 18 live runs, 5-6% off) or a figure that appears nowhere in
  > the payload (1 of 18: ₹20,820 for a ₹2,082 stock).
- **`R15-LEAD-038`** (medium, `blocked_tier4`, concurred):
  > With a keyless local model, when you tell the agent not to use tools and ask for a portfolio
  > change in the same message, it makes no call and nothing is written or queued, but its reply
  > can say the change was made or staged for your review and can describe holdings that do not
  > exist.

Fail-safe (why this ships): `data-write` proposed changes always stage for review — AUTO only auto-applies `panel`/`chart`/`watchlist` kinds (`types/proposed-change.ts:38-46`); a narrated
write stages nothing (no `tool_use` event); there is no `audit_orders` table any more (D81), so no order row can exist. Figure grounding by provenance
(`sidecar/services/figure_grounding.py` + `agent_runtime._judge_clause`, `agent_runtime.py:2321`, rules 1/2a/2b/2c/3) replaces an ungrounded figure tied to an errored or never-called
subject with an honest "returned no data" note. The rule-2c fail-safe (`agent_runtime.py:2378-2383`) fires only in a turn with an errored tool call — **a figure for a subject whose call
succeeded is not checked at all** (LEAD-037). The shipping no-tool matcher is the closed
`_NO_TOOL_CUE` list in `sidecar/services/planner.py` (`planner.py:136`, batch 21); batch 24 narrows it further, pending its own concurrence. Post-launch design (`DECISIONS_FOR_OPERATOR.md`
§4.9–4.12, not built): claim grounding by field/provenance plus a structured no-data turn.

**`blocked_tier4` (25), grouped by what it waits on** (rows = `DECISIONS_FOR_OPERATOR.md` §):

| Waits on | Entries | Rows |
|---|---|---|
| Local-model known limitation (above) | LEAD-030 (high), LEAD-037, LEAD-038 (medium) | 4.9, 4.11, 4.12 |
| Money/identity for releases (signing, release workflow, updater, CI) | RELEASE-001..004 (high) | 2.8–2.11 |
| A funded provider lane / an e2e runner call | AGENT-017 (high), AGENT-049 (medium) / UI-088 (medium) | 4.2–4.4 |
| A Tier-1 `.github/`, `tauri.conf.json` or BLUEPRINT-Locked-row edit | CODE-PLATFORM-073, CROSS-PLATFORM-001, CODE-PLATFORM-063, RELEASE-012, DOCS-011, DOCS-003, DOCS-015, DOCS-008, CODE-PLATFORM-010 | 2.13, 2.16, 2.17, 2.19, 2.20, 4.5–4.8 |
| Plugin contract, core architecture, or a business identity | CODE-PLATFORM-015, CODE-PLATFORM-071, AGENT-064, DOCS-002 | 2.12, 2.14, 2.15, 2.18 |
| First-launch terms surface / agent-write gaps | UI-044, CODE-FRONTEND-013 | 2.21, 3.3 |

**Lows.** 227 total: 12 fixed, 4 removed with trading, 4 blocked_tier4, 2 needs_gui, **205 open** (integration pending). Pre-triage (`r15/stage-c/lows-triage/LOWS_TRIAGE.md`) sharpened 199
into a fix shape + acceptance test (5 already-fixed verify-only, 1 not-a-defect, 1 duplicate). The partition (`r15/stage-c/lows/PARTITION.md`) split the 199 into three writer sets (P1/P2/P3,
~63-67 each) plus 5 inseparable lows as a serial set after. **The three write waves are DONE** — 184 fixed, 7 could-not-fix, 3 proposed not-a-defect, each on its own pushed branch — but
**not yet integrated**: the register still shows them `open` because merge + a fresh verifier per partition is queued for right after the `r15-rc1` tag, rebased onto the tagged head, one
partition at a time. `LEAD-031` (low, certified batch 17) is already `fixed` in the register and sits in no partition.

## 4. Operator-attended list — things only you can do

Row numbers are `DECISIONS_FOR_OPERATOR.md` §, which states the smallest unblock and the undo for each.

**Money and provider lanes**
- **§2.1** default lanes unfunded: OpenRouter negative, DeepSeek-direct $0 (`r15/local/BUDGET.md`,
git-ignored); your composer lane (`openai`/`gpt-5.6-luna`) is funded. Top up OpenRouter before hand-testing research (the keyless default rides it) and restart your dev stack — `043850c`
fixes the gpt-5.x tool-calling 400 on your lane.
- **§4.2 `AGENT-017`:** the shipped default chat model (DeepSeek V4 Flash) returns `content_filter`
on portfolio-write asks. Once funded, eval `glm-5.1` and `kimi-k2.6`; ship whichever passes.
- **§4.3 `AGENT-049`:** native web search off Anthropic has no cap/spend meter; needs a funded
OpenRouter lane or a reachable Gemini/Anthropic key.
- **§2.2** OrbStack not running → SearXNG down, research silently uses the keyless scraper tier —
start OrbStack before judging research (R15 never starts Docker).

**The e2e runner**
- **§4.4 `UI-088`.** Dockview tab reorder and node-editor drag-drop have no automated coverage;
needs your call on an e2e runner (Playwright against a real window) + a GUI-attended run.

**LEAD-035 disposition (new this refresh)**
- **§4.10 `LEAD-035`.** Now `blocked_tier4` at `4c6dfe8c` as an escalation, not a concurrence
(batch-24's verifier REFUSED certification a fourth time). Your call: (a) accept the residual as
documented with the verifier's wording (§3 above), or (b) authorise one bounded round for the
verifier's named guard (`(?<!says )` plus a qualifier negative lookahead) on the rc2 line. The
lead recommends (b) — the over-match makes the local model invent prices on explicit data
requests, the worse of the two failure modes. Not blocking the rc1 gate either way (already 0
open critical/high/medium); this decides only whether the wording in the release docs is final
or whether one more narrowing round runs before rc2.

**The filing-watcher model groundwork.** A candidate local-model route peaked at an 11.3 GiB footprint on this 16 GiB Mac; verdict for this release is not worth fine-tuning. Its measurement
folder still sits inside the public `r15/` tree — the folder name is withheld here by a standing naming ban (the lead has the path); one line from you moves it under the git-ignored
`r15/local/`.

**Licence wording**
- **§3.4** `COMMERCIAL_LICENSE.md:36-48`'s "responsible for their own broker relationship" clause
is still true; dropping it is your call. **§3.2** first-launch terms now say research-only + a licence line — review `src/modules/safety/DisclaimerFlow.tsx`. **`CLAUDE.md`**'s Locked-
decisions line still says "AGPL-3.0 + commercial dual license"; fix queued in `docs/redesign/CLAUDE_MD_PROPOSAL.md`, applied with the version-branch merge. Whether your own trading counts as
"noncommercial" under PolyForm Strict is a lawyer question, not this run's. Bundled copyleft (AGPL openbb/sec-edgar-mcp, LGPL frozendict in two sidecars) is listed in
`r15/stage-d/OPEN_QUESTIONS.md` §2, re-scanned each refresh.

**Signing and release.** **§2.8 `RELEASE-001`:** unsigned bundles block installs; free SignPath OSS needs an OSI licence without commercial dual-licensing, which neither the old AGPL +
commercial dual licence nor PolyForm Strict + commercial meets — Windows needs a paid certificate or another route. The macOS minimum, `bundle.macOS.signingIdentity: "-"` (ad-hoc seal:
"damaged" becomes Open-Anyway), is **not set** in `src-tauri/tauri.conf.json` at this sha — it is a one-line Tier-1 edit awaiting your sign-off. Developer ID + notarization needs a paid
Apple account. **§2.9–2.10
`RELEASE-002/003`:** approve `.github/workflows/release.yml` (tauri-action 3-OS matrix), then set `createUpdaterArtifacts: true`. **§2.11/2.6 `RELEASE-004`:** CI has never run here and
`main`'s last run is red — open a draft PR (no workflow edit needed); `pnpm ci-local` is the real gate meanwhile.

**Four Tier-1 CI edits the blocked lows need:** **§4.5** widen ruff to `sidecar scripts` (`lint.yml`); **§4.6** reword the OpenBB Locked row + §3.1 in `BLUEPRINT.md`; **§4.7** add a
CLA-check workflow + finalise the CLA text; **§4.8** cache `ensure-all-sidecars` output in `build/test/lint.yml`.

**Secrets, leftovers and dev signing.** **§3.1** orphaned OS-keychain broker secrets + old `~/.vysted-terminal/audit_log.db` rows — nothing reads or auto-purges them (irreversible); approve
a one-time purge or a CHANGELOG hand-delete note (this refresh's secrets scan found 0 real/unknown). **Keychain dev signing** (`docs/redesign/KEYCHAIN_DEV_SIGNING.md`): debug builds keep
secrets in a git-ignored `<app-data-dir>/dev-keystore.json` (mode `0600`) instead of the OS keychain, so `pnpm tauri:dev` rebuilds raise no dialogs; release builds use the real keychain
unchanged, one migration dialog on first dev boot; `CLAUDE.md`'s gotcha still describes the older self-signed-certificate route, reconciled in the single CLAUDE.md commit.

**Other open rows:** §2.7 an away-sentinel for the GUI rig; §3.3 no durable agent-write record past a 10-minute ledger, no AUTO stop beyond reject/cancel; §3.4 the `"trading-bot"`
`PluginType` literal in locked `types/plugin.ts`; §4.1 FAST research's uncached-Indian-name first-brief drop (recommendation: accept for rc1); §2.12–2.21 the architecture/docs items above.

**needs_gui (11): a human click-through on the packaged app** — no computer-use grant covers it. `CODE-AGENT-001` (high) every panel loads, no 403 on the webview's own origin ·
`LIFECYCLE-001` (high) a **cold launch after a reboot** paints/takes input while MCP binds (no beachball 25–90s), `/health` answers first · `LIFECYCLE-008` (high) `vysted.log` gets
timestamped lines + rotates, "Copy diagnostics" works · `UI-009` (high) Export CSV shows the saved path under `<app data>/exports/csv/` · `UI-022` (medium, needs **native event injection,
not chrome-devtools**) drawings, click-past-last-bar, Text label, locked-drawing delete · `UI-025` (medium) Link popover on selected note text · `UI-050` (medium) Notes slash-menu row
clipping · `UI-083` (medium) brief PDF/PNG export in WKWebView · `UI-084` (medium) agent-dock maximise at 2560 wide · `DOCS-024` (low) a real Claude Desktop session's slash picker ·
`LIFECYCLE-040` (low) cold-boot MCP-spawn check per platform, recorded in `DECISIONS.md`.

## 5. How to relaunch

**Run the app on this code.** `pnpm tauri:dev` → `pnpm tauri:mcp` → `tauri dev --features dev-tools`; the webview is Vite (`pnpm dev`). `pnpm tauri:dev` builds any missing or stale sidecar
itself (its `beforeDevCommand` in `tauri.conf.json` runs `node scripts/ensure-all-sidecars.mjs && pnpm dev`); `pnpm sidecars:build` forces a full rebuild of all three
(`scripts/ensure-all-sidecars.mjs --force`); `node scripts/smoke-test-sidecars.mjs` boots each and polls `/health`; `pnpm ci-local` mirrors CI step for step. A one-off packaged-bundle
rehearsal from a clean profile is queued for the heavy lane when batch 24 is not using it; the production bundle itself is proven from a clean profile by the lead on the integrated head,
before `r15-rc2` — not proven at this sha.

**The local-model lane.** Ollama with `llama3.1:8b` is what the run's live agent bars use, driven via
`python3 scripts/r15/vy.py invoke <agent> "<prompt>" --provider ollama --model llama3.1:8b --port <isolated sidecar port>` (`agent` and `prompt` are required positionals; `--port` defaults
to `52152`) against an isolated sidecar, never your own data dir or keychain. Proof + comparison: `docs/redesign/verification/r15/stage0/LOCAL_LANE_PROOF.md`. Single-owner lock: one
workflow at a time.

**Resume the run.** `docs/redesign/verification/vysted-r15-run-state.md` is rewritten at every checkpoint with a literal "Resume prompt" block. Its order from here: batch 24 merge (**done**,
`6778f892`) → adjudicate (**done**: LEAD-035 → `blocked_tier4` at `4c6dfe8c`, but as an escalation under the three-failure rule, not a concurrence — your call stays open at §3/§4.10) → 0 open
critical/high/medium (**done**) → rc1 gate round 2 (`skip_gui:true`, `max_fix_rounds:2`) — **in flight**, run `wf_4ed38558-4d0` launched from `4c6dfe8c` → tag `r15-rc1`, push, hygiene
prune, merge the version branch, handover → then, in parallel: lows integration P1/P2/P3 (serially among themselves, one fresh verifier each on the rc1 head, then the 5-item serial set) and
the GUI round as its own workflow on the rig, docs promoted as results land → the production bundle from a clean profile on the integrated head → Stage D promoted → `r15-rc2` → the panel's
one small top-survivor build → `r15-rc3` → one final adversarial pass → `r15-launch`. <!-- fill at rc2: steps already done -->

## 6. Where every evidence file is

| What | Path |
|---|---|
| R15 mandate — never read by this refresh | `docs/redesign/verification/R15_BRIEF*.md` |
| Run state / run report / run log | `docs/redesign/verification/vysted-r15-run-state.md`, `R15_RUN_REPORT.md`, `R15_RUN_LOG.md` |
| Defect register | `docs/redesign/verification/vysted-r15-register.json`, `.md` |
| Stage 0 facts, local-lane proof, census, Gate 2 | `r15/stage0/RECONCILE_MANIFEST.md`, `LOCAL_LANE_PROOF.md`; `r15/census/PROMISE_LEDGER.md`, `OPPORTUNITY_LEDGER.md`; `R15_GATE2.md` (paths under `docs/redesign/verification/`) |
| Trading-removal plan (D81) | `docs/redesign/verification/r15/stage-c/REMOVAL_PLAN.md` |
| Stage C batches 2–23: plan/verdicts/disposition | `r15/stage-c/batch-<2..23>/` (`PLAN.md`, `VERDICTS.md`; batch-23 also `LEAD-030-CONCURRENCE.md`, `DISPOSITION-CONCURRENCE.md`); batch-24 has no tracked dir at this sha |
| rc1 gate round 1 | `docs/redesign/verification/R15_GATE_RC1.md`; `r15/rc1/` (`VERDICT.md`, `FINDINGS.md`, `GATE8.md`, `refutation-audit/`) |
| Lows pre-triage, partition | `r15/stage-c/lows-triage/LOWS_TRIAGE.md`; `r15/stage-c/lows/PARTITION.md` |
| Ranked backlog, judge panel, workflow scripts | `r15/invent/BACKLOG.md`, `PANEL.md`; `r15/tooling/` (paths under `docs/redesign/verification/`) |
| Stage D drafts and scans (this file included) | `docs/redesign/verification/r15/stage-d/` |
| Decisions / operator decisions / CLAUDE.md queue / keychain runbook | `docs/redesign/DECISIONS.md`, `DECISIONS_FOR_OPERATOR.md`, `CLAUDE_MD_PROPOSAL.md`, `KEYCHAIN_DEV_SIGNING.md` |
| Per-batch history | `CHANGELOG.md`: trading removal + batches 2–17 + rc1 gate round 1; batches 18–24 have no section yet |

All paths above were confirmed present at this sha with `git cat-file -e`, except the R15_BRIEF row (deliberately unread) and batch-24 (untracked at this sha).

## 7. What R15 decided on its own that you may want to revisit

Everything below already happened; where an undo exists it is named. Earlier items (relicense, AUTO scope SC-025, context admission, the D-B10/D-B11 series, the refutation audit) stand as
recorded in `DECISIONS_FOR_OPERATOR.md` §1, §3.5–3.6 and `DECISIONS.md`.

1. **Your own three-strikes stop rule (pacing change 4, 04:15 IST Sat 26 Sep) was applied twice:**
any entry failing certification three times stops and goes to `DECISIONS_FOR_OPERATOR.md`, whatever its severity — this fired for `LEAD-030` (eight rounds; the lead's own earlier stop
rule had already fired once) and `LEAD-035` (three, at batch 23). Batch 22's and 23's `LEAD-035` fixes were both built, tested and rejected as regressions (each over-matched, stripping tools
from an explicit data request and fabricating a price). One further bounded round (batch 24) built the batch-23 verifier's own named narrowing-only fix — it holds as a strict subset with
0 new strips, but still failed certification a **fourth** time (4 of 18 fresh qualified-negation data requests still lose every tool); the lead set `LEAD-035` to `blocked_tier4` at `4c6dfe8c`
per the standing three-strikes recommendation, escalating the residual and the verifier's next-named fix to you rather than running a fifth round unauthorised.
2. **A fresh verifier's concurrence, not the adjudicator alone, disposes an agent-chat high/medium
to `blocked_tier4`** — `LEAD-030` needed this after its eighth round; `LEAD-037`/`038` (filed in batch 23) went straight to a concurrence request, since they share the class. **`LEAD-035` is
the exception:** its verifier has now REFUSED concurrence four times running, so the lead applied `blocked_tier4` on the three-strikes rule alone, without a concurrence — flagged to you as
such rather than presented as adjudicated.
3. **The filing-watcher groundwork's measurement folder stays in the public tree** until you say
otherwise (§4) — no release document names it, per a standing naming ban.
4. **The version bump + the single `CLAUDE.md` commit are one branch,** merged right after
`r15-rc1`, not folded into any Stage C batch — keeps every batch's diff scoped.
5. **A production-bundle rehearsal runs opportunistically on the heavy lane** whenever batch 24
isn't using it, ahead of the real Stage D bundle step.

<!-- refresh 82d3d08 to 4d89314: header to the required format; carried through batches 18-22
(merged), the unmerged batch-23, the disposition/concurrence docs and the in-flight batch-24; register 646/388-fixed/1-open-high → 652/391-fixed/1-open-medium (LEAD-035); LEAD-030/037/038
now blocked_tier4 as an accepted known-limitation class (verbatim wording, LEAD-030's clause struck per sign-off); added version-branch/bundle-rehearsal notes; redacted the filing-watcher
folder name; dropped the critic-footer; trimmed to the 300-line cap. -->

<!-- refresh 4d893147 to 4c6dfe8c (Stage D LEAD-035 disposition pass): batch 24 merged
(`6778f892`) — its named narrowing-only fix holds as a strict subset but LEAD-035 failed
certification a fourth time; the verifier REFUSED `blocked_tier4` concurrence and named a
further narrowing-only guard it would certify. The lead applied `blocked_tier4` under the
three-failure rule as an escalation (not a concurrence) at `4c6dfe8c`. Updated: §1 state
paragraph (0 open critical/high/medium, gate round 2 in flight as `wf_4ed38558-4d0`); §2's
batch table/prose (batch 24 outcome, no longer "in flight"); §3's register-count table (medium
open 1→0, blocked_tier4 15→16; totals 206→205 open, 25→26 blocked_tier4) and the LEAD-035
known-limitation bullet (now the batch-24 verifier's `d1290f66`-accurate wording, verbatim);
added a §4 operator-attended bullet for the (a)/(b) choice at DECISIONS §4.10; §5's resume-run
chain marked each step done through gate round 2 in flight; §7 items 1-2 corrected for the
fourth failure and the concurrence-less disposition. Every other section unchanged. -->

<!-- critic-footer -->

## Critic findings applied

1. applied — §6 table + confirmed-present line: batch-24 is untracked at this sha (`git cat-file -e` confirmed missing); batch range narrowed to 2–23, batch-24 called out separately.
2. applied — fail-safe paragraph rewritten: verified at `agent_runtime.py:2378-2383` that the rule-2c fail-safe fires only `if ctx.errored and (attached is None or attached not in
   ctx.ok_subjects)`, so an ungrounded figure for a subject whose call succeeded falls through unchecked and streams; struck the "ok-subject figures are grounded" clause and added the
   LEAD-037 cross-reference.
3. applied — verified `src-tauri/tauri.conf.json` at the sha has no `signingIdentity` key anywhere; rewrote to say it is not set and is a pending Tier-1 edit.
4. applied — verified `c8d807a6` is a run-state note, and the actual bump (`517da226`) + `CLAUDE.md` commit (`c1e9164c`) live on `worktree-agent-r15-version-0.9.0`, unmerged; reworded both
   occurrences.
5. applied — verified batch-20 `VERDICTS.md` has two "not certified" headings (LEAD-030, LEAD-036) and batch-21 `VERDICTS.md:6-7` names three (LEAD-030, LEAD-035, LEAD-036); corrected the
   counts to 2 and 3.
6. applied (reworded, per the finding's second option) — verified run-state.md:13's pacing-change-4 block states the three-strikes rule as the operator's own instruction; reworded the §7
   item to attribute it to the operator rather than to R15, and noted the lead's own earlier stop rule for LEAD-030.
7. applied — verified `scripts/r15/vy.py:276-283`: `invoke` requires positional `agent` and `prompt` plus `--provider`; `--port` defaults to 52152 (`:305`); corrected the command line.
8. applied — verified `tauri.conf.json`'s `beforeDevCommand` runs `ensure-all-sidecars.mjs` before `pnpm dev`, so `tauri:dev` self-builds; `sidecars:build` only forces a rebuild. Reworded.
9. applied — verified run-state.md:13: the rehearsal runs "on the heavy lane whenever batch-24's chain is not using it"; the production bundle is proven later by the lead on the integrated
   head. Reworded §5's bundle line; §7 item 5 already matched this and needed no change.
10. applied — verified run-state.md:13: lows P1/P2/P3 + the GUI round run in parallel after the tag, not as a strict chain; reworded the "Resume the run" sequence.
11. applied — verified `planner.py:136` (`_NO_TOOL_CUE = re.compile(`), not ~130; corrected inline with finding 2's rewrite.
12. applied — verified the register JSON's `R15-LEAD-031` entry has `status: "fixed"` with closure evidence at `292ba53a`; corrected the stale "sits in no partition, closed at the next
    adjudication" wording.
13. applied — verified `DECISIONS_FOR_OPERATOR.md`'s §2.2 recommendation ("start OrbStack before judging research"); appended it.
14. applied — the relicense (PolyForm Strict + commercial) and the pre-relicense licence (AGPL-3.0 + commercial, per `CLAUDE.md:57` at the sha) both carry a commercial dual licence, so
    neither ever met SignPath OSS's condition; folded into finding 3's rewrite rather than a separate edit.
15. applied — verified the register JSON's `counts` field (`raw/entries/rejections/critical/high/medium/low`) carries no status breakdown; the status columns are a recompute from
    `entries[].status`. Reworded the table's source line.
