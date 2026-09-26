<!-- DRAFT at 6bc6d378cbbf9cfbefd8d155e027c2dc80214331 by the Stage D gap-check pass; refresh before rc2 -->
<!-- Facts sourced only from RELEASE_NOTES.draft.md and FACTS.md (both in this directory), per this task's brief. -->
<!-- To promote: strip this header comment and the trailing "Promotion note" section, then insert the body below
     into CHANGELOG.md immediately above the "## R15 rc1 gate — round 1 (2026-09-25)" heading (newest-first order). -->

## v0.9.0 — R15: trading removed, relicensed, Stage C fix batches (2026-09-23 – 2026-09-26)

**Scope:** the R15 census-and-repair cycle on `004-r4-experience-rebuild`, from base tag
`r13-bedrock`. Trading was removed from the product permanently (D81, operator Tier-4
sign-off), the core was relicensed AGPL-3.0 → PolyForm Strict 1.0.0 + commercial (D83),
and the R15 register — 887 raw findings, closed to 603 entries at D84's Gate-2
adjudication, grown to 652 entries as further lead-found `R15-LEAD-*` entries were
admitted during Stage C (16 critical / 116 high / 293 medium / 227 low, plus 76
rejections) — was worked down across 22 Stage-C batches plus an rc1 gate round, each
merged `--no-ff` from an isolated integrator worktree and each independently verified
fresh-context before merge. As of `4c6dfe8c` (batch 24 merged `6778f892`): 391 entries
`fixed`, 205 `open`, 26 `blocked_tier4` (operator-attended), 14 `removed_with_feature`
(trading, D81), 11 `needs_gui`, 5 `not_a_defect`. Open critical/high/medium is **zero**
— `R15-LEAD-035` (medium, agent-tools) moved to `blocked_tier4` at `4c6dfe8c` as an
escalation under the operator's three-failure rule, not a fresh-verifier concurrence;
the 205 open entries are all low severity. No `r15-rc1` tag exists yet as of this entry;
round 1 of the rc1 gate **FAILED** against an earlier candidate and drove several of the
batch-12..22 fix rounds, and round 2 is running from `4c6dfe8c`.

**What changed for you:**

- Workspaces autosave through one gated, debounced pipeline instead of several ad hoc
  paths; a saved workspace now restores portfolios, watchlist and notes correctly even
  if a panel in the saved layout no longer exists, and research spaces save under any
  name given.
- The AI copilot's automatic ("AUTO") actions are scoped to panel, chart and watchlist
  changes only — anything that writes data or changes a setting always stops for review
  first, with typed step-by-step notices instead of guessed status text.
- A ticker picked from the command palette loads straight into the chart; the chat's
  focused-symbol handling is more consistent with what is on screen.
- Sidecar connection problems (a dead or restarting local data engine) surface as
  plain-language errors instead of hanging requests or silent failures; each panel
  fails independently instead of taking the rest of the window down with it.
- Model/provider setup states why a key or connection failed, and a banner states when
  the selected model cannot be reached; a working key added now replaces a dead
  keyless default instead of silently coexisting with it.
- Chart drawings are correctly scoped per symbol and timeframe; indicator overlays no
  longer duplicate on repeated loads.
- Portfolio quote failures show a staleness indicator instead of a wrong number; the
  portfolio CSV export carries a currency column and no longer mixes currencies in
  Weight %.
- Several research- and data-quality issues in Indian-market coverage (BSE/NSE
  identity, corporate disclosures, fundamentals cross-checked against exchange
  filings) were corrected.

**Removed: trading (D81).** Trading was removed from the product permanently, operator
Tier-4 sign-off. No broker connection, order placement, or paper/live trading account
remains anywhere in the app; the manually tracked Portfolio panel (holdings entered by
hand, P&L, CSV export) is not trading and stays.

**Relicensed (D83).** The core moved from AGPL-3.0 to PolyForm Strict 1.0.0 (free,
noncommercial) plus a commercial license for anything else. The plugin contract and the
example plugin are carved out under Apache-2.0. Every commit before the relicensing
commit remains available under its original AGPL-3.0 terms.

**Decisions (D-numbers since `r13-bedrock`, full text and rationale in
`docs/redesign/DECISIONS.md`):**

- **D81** — trading removed from the product permanently (operator Tier-4 sign-off);
  reverses BLUEPRINT §2 (locked) and touches the §6.5 safety surface.
- **D82** — OpenAI-direct run spend cap set to $8.00, enforced structurally in
  `scripts/r15/vy.py`.
- **D83** — core relicensed AGPL-3.0 → PolyForm Strict 1.0.0; plugin contract + example
  plugin carved out under Apache-2.0; every pre-relicense commit stays AGPL-3.0.
- **D84** — Gate 2 (R15 census) adjudicated closed: 887 raw findings → 603 entries.
- **D85–D92** — trading-removal-plan riders (first-launch terms dialog rewritten with
  no kill-switch promise; planner keeps buy/sell edit signals, drops order-phrase
  signals; "paper portfolio" becomes "portfolio" everywhere; BLUEPRINT §6.5 retitled,
  section number kept; `registry_v0_6_5.py` deleted; workspace restore never drops user
  data on an unknown panel; India EOD-only data error no longer suggests connecting a
  broker; no automatic purge of leftover broker secrets/audit history, operator
  decision).

**Known limitations at rc1 — agent chat with a keyless local model.** With a keyless
local model, the agent can fabricate a figure or claim a completed write when it has no
tool result to ground the claim. Four register entries track this class:
`R15-LEAD-030` (high), `R15-LEAD-035` (medium), `R15-LEAD-037` (medium), `R15-LEAD-038`
(medium) — all `blocked_tier4` as of `4c6dfe8c` (030/037/038 via fresh-verifier
concurrence, 035 via the operator's three-failure escalation rule; see
`DECISIONS_FOR_OPERATOR.md` §4.9–4.12). A portfolio write never auto-applies regardless:
data-write changes always stage for review, and AUTO skips review only for panel, chart
and watchlist changes (`types/proposed-change.ts:38-46`). There is no `audit_orders`
table — D81 removed it with trading. Full wording for each entry is in
`docs/redesign/verification/r15/stage-d/RELEASE_NOTES.draft.md`, "Known limitations at
rc1".

**Carried forward / not yet done at this sha:**

- Version reads `0.8.0` across every source-of-truth file
  (`package.json`, `src-tauri/Cargo.toml`, `src-tauri/tauri.conf.json`, `sidecar/app.py`,
  `src/lib/plugin-bootstrap.ts` `HOST_VERSION`, `src-tauri/Cargo.lock`); a version-bump
  branch (`worktree-agent-r15-version-0.9.0`) is prepared separately and merges right
  after the `r15-rc1` tag.
- No code-signing, no release workflow, no auto-updater wiring — all Tier-4, blocked on
  the operator.
- CI has never had a green run on `004-r4-experience-rebuild`.
- The rc1 gate has run once (round 1, FAIL, against an earlier candidate) and round 2 is
  running from `4c6dfe8c`; confirm the gate's final verdict, and any tag name/sha, at
  the tag.

## R15 Stage C — batch 24: no-tool cue narrowed to a closed tail (R15-LEAD-035, fourth round; not certified, escalated under the three-failure rule) (2026-09-26)

**Scope:** exactly one entry, R15-LEAD-035 (medium, agent-chat) — the narrowing-only closed-tail
fix the batch-23 disposition verifier named and said it would certify
(`docs/redesign/verification/r15/stage-c/batch-24/PLAN.md`). One writer set, W1 (Sonnet; the
fix was fully specified to the character, no root-causing left). Base `1db862d0`, merged
`--no-ff` on `worktree-agent-batch-24-int`, merge `6778f892`.

- **R15-LEAD-035 (not certified a fourth time).** The four shipping `_NO_TOOL_CUE` alternatives
  are kept byte-for-byte; a closed-tail lookahead (a clause end, or one of a fixed set of
  trailing words/phrases such as "please," "at all," "for this one") plus a reported-speech
  guard (`(?<!said )(?<!say )`) are added so a qualifier after the cued object no longer forces
  a strip. The change is a strict subset of the shipping regex (0 new strips across 97 classified
  phrasings) and clears all 7 of the batch-23 over-strip prompts, which now call `price_data`
  live 21/21 (18/21 stating the correct current price, 3/21 an older bar from the same payload —
  the R15-LEAD-037 residual, not this entry). A fresh-context re-test still found 4 qualified-
  negation/reported-speech phrasings — e.g. "He says don't use tools, but please fetch the
  TCS.NS price" — that lose the whole tool surface, and live the model invented a price in 6 of
  8 such runs.
- **Disposition: escalated to `blocked_tier4` under the operator's three-failure rule** (not a
  fresh-verifier concurrence — the verifier's own ruling on this round was REFUSE,
  `stage-c/batch-24/LEAD-035-CONCURRENCE.md`). Briefing wording, verbatim (the batch-24
  verifier's, accurate for `d1290f66`): "With a keyless local model, the 'don't use tools'
  detector is a fixed phrase list: an unrecognised no-tool phrasing keeps the tools, so the
  agent may still read data and propose a portfolio change (always held for your review, never
  applied; under AUTO a watchlist or chart change does apply) and can occasionally state a
  price it never fetched, while a data request that qualifies a no-tool instruction after a
  comma or in reported speech ('Don't use any tools, except price_data …', 'No tools, other
  than the price lookup …', 'He says don't use tools, but …') still loses every tool and the
  agent then usually states an invented price as if fetched." `DECISIONS_FOR_OPERATOR.md` §4.10
  carries the operator's two rc1/rc2 options; the lead recommends authorising one further
  bounded round.

**Verifier:** fresh-context. `pnpm ci-local` exited 0 (vitest 1831 passed, pytest 3596 passed 1
skipped, clippy/ruff clean); the smoke test exited 0. No test was deleted or weakened. No
frontend or Rust file changed; `planner.py` stays free of catalog/agent-loop imports.

## R15 Stage C — batch 23: a further no-tool matcher rejected as a regression, not merged (R15-LEAD-035); R15-LEAD-030/037/038 adjudicated (2026-09-26)

**Scope:** exactly one writer entry, R15-LEAD-035 (medium, agent-chat), the third and declared
final filter round (`docs/redesign/verification/r15/stage-c/batch-23/PLAN.md`). One writer set,
W1 (Opus). Base `014bb7f1`. **Verdict: block — not merged.** Alongside the writer round, a
fresh verifier separately adjudicated three standing entries via `LEAD-030-CONCURRENCE.md` and
`DISPOSITION-CONCURRENCE.md`.

- **R15-LEAD-035 (not certified; regression; not merged).** W1's rewritten no-tool cue
  (clause-scoped NEG→VERB→OBJECT grammar, a double-negative guard, an interrogative exemption,
  and a closed from-given object list) fixed every batch-21/22 miss and over-match the writer
  tested, but the fresh-context verifier found 7 further keep-surface phrasings — a scoping
  adverb ("blindly," "twice," "again"), a relative clause ("you don't need"), or a trailing
  named exclusion ("the search tools") — that still lost the entire tool surface; live, the
  model then stated an invented price as fetched on all 7 (e.g. INFY.NS ₹443.85 against a real
  1000.2). Nothing from this round merges; the diagnosis and a bounded closed-tail fix idea
  carry into batch 24.
- **R15-LEAD-030 adjudicated `blocked_tier4` (CONCUR, corrected wording).** A fresh verifier
  concurred with `blocked_tier4` after an eighth non-certification, but ruled the standing
  DECISIONS 4.9 wording understates the residual and must be replaced. Corrected briefing
  wording, verbatim: "With a keyless local model, the agent can still state an invented price
  or metric as if a tool had returned it when the figure is about a company no successful tool
  call in that turn covered — one named in the same paragraph as a company whose call succeeded
  (under a name the guard cannot map, or never looked up at all), or any company in a turn where
  no call failed or no tool was called — and a figure-less fabricated result dump or a code
  fence left open from an earlier round can also render, while figures for companies whose call
  succeeded are grounded against the tool result and every shape pinned in eight fix rounds is
  replaced by an honest 'returned no data' note." The verifier separately struck the clause
  "figures for companies whose call succeeded are grounded against the tool result" as false
  (see R15-LEAD-037 below); the guard never checks a figure for a subject whose own call
  succeeded.
- **R15-LEAD-037 adjudicated `blocked_tier4` (concurred on corrected wording).** Briefing
  wording, verbatim: "With a keyless local model, a figure the agent states for a company whose
  data call succeeded is not checked against that result at all, so it can give an older bar's
  value from the same payload as the current price (2 of 18 live runs, 5-6% off) or a figure
  that appears nowhere in the payload (1 of 18: ₹20,820 for a ₹2,082 stock)."
- **R15-LEAD-038 adjudicated `blocked_tier4` (concurred).** Briefing wording, verbatim: "With a
  keyless local model, when you tell the agent not to use tools and ask for a portfolio change
  in the same message, it makes no call and nothing is written or queued, but its reply can say
  the change was made or staged for your review and can describe holdings that do not exist."

**Verifier:** fresh-context, live llama3.1:8b on a source sidecar (127.0.0.1:52310); `pnpm
ci-local` green (3471 passed, 1 skipped) after one formatting fix. The batch-22 W1 gains held
with zero new regressions on every b17-b21 probe line. Nothing certifies and nothing merges
this batch; the harm check across 141 live runs found the portfolio DB and `audit_orders` both
untouched throughout (0 rows).

## R15 Stage C — batch 22: unclosed-fence fix and short-name/initialism aliases merged (R15-LEAD-030, R15-LEAD-036); a wider no-tool matcher rejected as a regression (R15-LEAD-035) (2026-09-26)

**Scope:** R15-LEAD-030 (high, eighth round) and R15-LEAD-035 (medium, second round) open after
adjudication; R15-LEAD-036 (low) rides W1 on the same file
(`docs/redesign/verification/r15/stage-c/batch-22/PLAN.md`). Two disjoint writer sets, W1
(Opus) and W2 (Sonnet). Base `93ba12da`. **Verdict: block** — only W1 merged, as `c155e5ad`
(pre-verifier-fix head `da25a6a9`); W2 (`ca609488`) was rejected and never merged.

- **W1 item 1 — unclosed fence at end of stream (fixes a batch-21 regression).**
  `_fence_body` now drops the last line only when the stream actually saw a closer, so a fence
  still open when the round ends is judged as a complete unit instead of silently losing its
  last body line as if it were the closer.
- **W1 item 2 — short-name and initialism aliases.** A subject's alias set now also includes
  initialisms built from its resolved company name (SBI, L&T, HDFC-style forms), every
  distinctive name token rather than only the first, and names read from a call's own result
  payload (`name`/`longName`/`shortName`) and from a `resolve_symbol` call's query text;
  initialisms match case-sensitively to avoid colliding with ordinary English words ("it,"
  "us," "and").
- **W1 item 3 — rule 2c, fail-safe by design.** In any turn with at least one errored call, an
  ungrounded figure not attached to a known-ok subject is now replaced regardless of whether the
  guard recognizes the naming form used, trading one accepted true-line flip (a subjectless
  general-knowledge figure in an errored turn) for closing every not-yet-seen alias escape.
- **R15-LEAD-030 not certified an eighth time.** An uncalled or unrecognised name sharing a
  paragraph with an ok subject still inherits that subject and streams (e.g. "Tata Motors last
  traded at ₹702.10" beside an ok TCS sentence), and a fence opened in an earlier round still
  renders its replacement note inside the still-open fence marker.
- **W2's rewritten `_NO_TOOL_CUE` matcher — reviewed and blocked before merge.** It stripped the
  entire tool surface on ordinary data requests such as "Don't forget to use the tools to get
  the latest TCS.NS price," after which the model fabricated and narrated prices as fetched (6
  of 6 such live prompts); rejected as a regression against base, not merged.

**Verifier:** fresh-context Opus. Integrator `pnpm ci-local` green (3456 passed, 1 skipped),
smoke green. The W1-only candidate showed no regression against base on any probe (fresh set
BAD 4 vs base's BAD 8); R15-LEAD-030 and R15-LEAD-036 both improved with no regression but
neither certifies; R15-LEAD-035 is a certified regression, blocked.

## R15 Stage C — batch 21: negative-acknowledgement ordering, company-name subject aliases, CommonMark fences (R15-LEAD-030, R15-LEAD-036); an explicit no-tool cue added to the planner, first attempt (R15-LEAD-035) (2026-09-25)

**Scope:** R15-LEAD-030 (high, seventh round) and R15-LEAD-035 (medium) open after
adjudication; R15-LEAD-036 (low) rides W1 on the same file
(`docs/redesign/verification/r15/stage-c/batch-21/PLAN.md`). Two disjoint writer sets, W1
(Opus, `agent_runtime.py`/`figure_grounding.py`) and W2 (Sonnet, `planner.py`). Base
`4d9a7324`, merged `--no-ff` on `worktree-agent-batch-21-int`, merge `86ae79c4`.

- **W1 gap 1 (LEAD-030).** The `_NEGATIVE` acknowledgement exemption in `_judge_clause` now
  only fires when the clause carries no ungrounded figure, so "Although the `price_data` tool
  failed, I can tell you that SBIN.NS's latest close was ₹742.35." is replaced instead of
  streaming a live-observed fabrication.
- **W1 gap 2 (LEAD-030).** A subject's alias set now includes its resolved company name and
  short forms (read via the resolver's private master functions) plus any distinctive token the
  user's own text used this turn, and an ungrounded figure naming no subject of its own inherits
  the nearest preceding subject mentioned in the same paragraph — closing the "Infosys last
  traded at ₹1,233.65" class with TCS ok and INFY errored.
- **W1 gap 3 (LEAD-036).** Fence recognition generalised from backtick-only to CommonMark
  tilde and backtick fences of any matching run length, closing most tilde-fence cases.
- **W2 (LEAD-035, first attempt).** A `_NO_TOOL_CUE` pattern added to `planner.classify_intent`
  returns a positive "no-tool" read signal; a runtime hunk in `_resolve_tool_surface` empties
  the tool surface server-side whenever that signal fires, in every mode.
- **R15-LEAD-030 not certified a seventh time.** An errored subject named only by a common
  short form or abbreviation absent from the alias set (SBI, Airtel, L&T) still streams in a
  mixed turn, and — a new regression — an unclosed fence at end of stream drops its last body
  line as if it were the closer, so a fabricated figure inside an unclosed tilde block now
  leaks where base replaced it.
- **R15-LEAD-035 not certified.** The closed phrase list still misses "Answer without any
  tools" (no verb), "Do not call a tool" (the article "a" is unmatched), and curly-apostrophe
  "Don't use any tools" (U+2019; the pattern accepted ASCII only); live, the model called
  `get_portfolio` or streamed a raw tool-call JSON fragment on these phrasings.
- **R15-LEAD-036 not certified**, for the same unclosed-fence regression as LEAD-030.

**Verifier:** fresh-context Opus. `pnpm ci-local` exited 0 (3420 passed, 1 skipped); smoke
passed. Fresh offline cases: base left 9 of 20 BAD, the branch 1 of 20; a second 13-case set
went from 8 BAD to 3. Live llama3.1:8b bar run on a source sidecar; true controls did not
regress.

## R15 Stage C — batch 20: figure grounding by provenance replaces shape-matching (R15-LEAD-030, R15-LEAD-036, not certified a sixth time); R15-LEAD-035 filed and deferred (2026-09-25)

**Scope:** R15-LEAD-030 (high) open after adjudication, with R15-LEAD-036 (low) riding the same
file; R15-LEAD-035 (medium, agent-chat) filed from batch-19's residuals but explicitly deferred
this batch (`docs/redesign/verification/r15/stage-c/batch-20/PLAN.md`). One writer set, W1 —
routed to Fable at high effort after five Opus rounds narrowed but did not close the class.
Base `d685a4be`, merged `--no-ff` on `worktree-agent-batch-20-int`, merge `1abef99b`.

- **New module `sidecar/services/figure_grounding.py`.** A per-turn grounded-value set seeded
  from every non-assistant, non-system-prompt message plus every tool result payload (numeric
  leaves, including scaled figures inside display strings such as "₹12.1 lakh cr"), with a
  precision-matched grounding test and derivations (sum/difference/product/quotient/percent
  change) from pairs of user/context values only.
- **The streaming guard's judgment rewritten from shape-matching to provenance.** An
  all-errored turn replaces any unit carrying an ungrounded figure; a mixed turn replaces a
  figure cited to an errored/uncalled tool, or attached to an errored call's subject; a figure
  that is grounded, or attached to an ok subject, streams unchanged.
- **Block-level holding generalised** to fenced code, tables, lists and multi-line JSON, so a
  multi-line result is judged and replaced as one unit rather than line by line; a replaced
  fenced block loses its fence markers (R15-LEAD-036, backtick fences only this round).
- **R15-LEAD-030 not certified a sixth time.** Two named implementation gaps, not new shapes:
  the `_NEGATIVE` acknowledgement exemption in `_judge_clause` returns before the grounding
  check runs, so "Although the `price_data` tool failed, I can tell you that SBIN.NS's latest
  close was ₹742.35." streamed live (truth 983.0); and rule 2b matches an errored call's
  subject by ticker only, so a company name ("Infosys") in a mixed turn is not recognised.
- **R15-LEAD-036 not certified**, for the same reason on a fresh CommonMark tilde fence (only
  backtick fences were recognised).
- **R15-LEAD-035 deferred**, on the lead's instruction restricting this batch to one writer on
  the streaming guard; its fix lives in `sidecar/services/planner.py`, owned by an unmerged
  lows-wave branch this batch does not touch.

**Verifier:** fresh-context Opus. Integrator `pnpm ci-local` green (3385 passed, 1 skipped),
smoke green; focused re-run gave 288 passed. Closes every batch-19 escape and the pre-existing
"the news data shows" false positive: on 19 fresh offline cases the branch left 6 BAD against
14 on base, with no true control regressing.

## R15 Stage C — batch 19: colon-bound result blocks and all-errored-turn detection (R15-LEAD-030, not certified a fifth time) (2026-09-25)

**Scope:** the one open critical/high/medium entry after adjudication, R15-LEAD-030 (high,
agent-chat) (`docs/redesign/verification/r15/stage-c/batch-19/PLAN.md`). One writer set, W1
(Opus). Base `c5a6ade8`, merged `--no-ff` on `worktree-agent-batch-19-int`, merge `ec7f7cd6`.

- **Colon binding.** A sentence ending in `:` now binds its following paragraph into the same
  guarded unit, so a JSON/prose dump on the next paragraph after a kept intro sentence is judged
  together with that intro rather than streaming unguarded.
- **All-errored-turn detection.** A new `errored_tools` set on `_TurnState`, filled wherever a
  round's tool result is not ok, lets the guard replace a result-shaped block in a turn with no
  ok tool at all even when no sentence directly cites a tool.
- **R15-LEAD-030 not certified a fifth time.** The fix closes both batch-18 escapes plus 6
  fresh fabricated shapes (a chunked fenced dump, all-errored bold bullets, a numbered `=` list,
  an inline "I get: {...}", an all-errored fenced dump, and the plan's own unfenced case) —
  base streams all of them. Two escapes remain, both pre-existing on base: a code-fenced dump
  attributed to a named errored/uncalled tool is never seen as result-shaped, and an
  all-errored markdown table or an annotated bullet list fails the result-line pattern. A new
  over-replacement also appeared: a genuine restatement of the user's own figures after an
  error is now wrongly replaced by the all-errored branch.

**Verifier:** fresh-context Opus. `ruff format --check`/`ruff check` clean; full sidecar pytest
gave 3330 passed, 1 skipped. Live llama3.1:8b bar on a source sidecar: 0 fabricated blocks
streamed and 0 true figures removed across 9 fresh prompts, though the fabricated shapes above
were confirmed via the offline relay rather than reproduced live this round.

## R15 Stage C — batch 18: NSE Emerge '-SM' identity fix (R15-LEAD-034) and trailer-echo strip (R15-LEAD-033) certified; R15-LEAD-030 clause-level attribution rewrite merged, title claim still open (2026-09-25)

**Scope:** the three open critical/high/medium entries after adjudication —
R15-LEAD-030 (high, agent-chat), R15-LEAD-033 (medium, agent-chat), R15-LEAD-034 (medium,
data-smallcaps) (`docs/redesign/verification/r15/stage-c/batch-18/PLAN.md`). Two writer sets,
disjoint files. W1 (Opus) continued from `origin/worktree-agent-batch-18-W1@ecdd223e` (5
commits on `292ba53a`). Merged `--no-ff` on `worktree-agent-batch-18-int` (base `08908883`)
plus one verifier fix (`24bff097`) for a reviewer-blocking regression in the W1 branch, merge
`ebc5ed41`.

- **W1 — R15-LEAD-030 (not certified).** `_tool_reference` moves to clause-level attribution: a
  reference regex canonicalises snake/spaced/hyphen/Title/camel-cased tool ids to one catalog
  id, a sentence is split at clause breaks before its first dump opener, and a clause is
  replaced only when a non-ok reference is cited in attribution form or the clause carries a
  figure/dump with every reference in it non-ok. The reviewer's blocking regression (6 true
  sentences wrongly replaced, e.g. "According to news reports from Reuters, AAPL rose 3% to
  $190.") was fixed in `24bff097` by narrowing the lead-in alternative to three forms
  (backticked id, bare snake_case id, or a humanised id followed by "tool"/"result(s)"/etc). Two
  escapes remain, identical on base and therefore not regressions: a fabricated result dump
  after a non-attribution mention of an errored tool ("After calling the `financial_statements`
  tool for SIFY's annual revenue, I get: …"), and a generic "Here are the results:" bullet list
  with no tool reference at all.
- **W1 — R15-LEAD-033 (certified).** `cited_tools` is now seeded from the chat history's
  `[tool steps: …]` trailer *before* that trailer is stripped from the verbatim assistant turns
  sent to the provider in `_coerce_history`, so a keyless local model no longer echoes the
  bookkeeping trailer as its own prose while cross-turn tool citations are still recognised.
- **W2 — R15-LEAD-034 (certified).** `correctness_gate._SUFFIX_RE` now strips an NSE Emerge
  `-SM` infix immediately before the exchange suffix (`(?:-SM)?[.\-](NS|BO|BSE)$`), so a bare
  Emerge symbol request (e.g. `INSPIRE` against a returned `INSPIRE-SM.NS`) passes
  `symbols_match` in every caller (`validate_quote`/`validate_series`/`validate_fundamentals`),
  not only the warm crawler; a real-vs-real identity check (`SUMAX` vs `OTHER-SM.NS`) still
  fails, and non-Emerge suffixes (`SMR.NS`) are untouched.

**Verifier:** fresh-context Opus. `ruff format --check`/`ruff check sidecar` clean; full sidecar
pytest gave 3319 passed, 1 skipped. No GUI-only surface; no frontend or Rust file changed. Two
entries certified (R15-LEAD-033, R15-LEAD-034); R15-LEAD-030 not certified, its two remaining
escapes reproducing identically on base.

<!-- Promotion note (strip before landing in CHANGELOG.md): this entry covers the
     release-level v0.9.0 summary, and the seven per-batch sections immediately above cover
     Stage C batches 18-24 (drafted this task; batch-23 was NOT merged — see its section — so
     it carries no merge sha). At promotion, insert the v0.9.0 summary at the top of
     CHANGELOG.md (above the existing "batch 17" section) and the seven batch sections
     immediately below it, in the newest-first order they already appear here (24, 23, 22, 21,
     20, 19, 18), so batch 18 lands directly above the existing "batch 17" heading. Re-verify
     the register counts, blocked_tier4 total, and rc1-gate-round-2 verdict against the sha
     actually being tagged before pasting any of this in — the figures in the v0.9.0 summary
     above are accurate as of `4c6dfe8c` / `4d893147`, not necessarily the rc2 candidate sha. -->
