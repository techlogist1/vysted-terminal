<!-- DRAFT at 4d893147def983623de681effd1bfbae2e7441c5 by the Stage D docs wave; refresh before rc2 -->

# Vysted Terminal 0.9.0

## What changed for you

- Workspaces autosave through one gated, debounced pipeline instead of several ad hoc
  paths; a saved workspace now restores your portfolios, watchlist and notes correctly
  even if a panel in the saved layout no longer exists, and research spaces save under
  any name you give them.
- The AI assistant's automatic ("AUTO") actions are now scoped to panel, chart and
  watchlist changes only — anything that writes data or changes a setting always stops
  for your review first, with typed step-by-step notices instead of guessed status text
  in the transcript.
- A ticker you pick from the command palette (Cmd/Ctrl-K) loads straight into the chart,
  and the chat's focused-symbol handling is more consistent with what's on screen.
- Sidecar connection problems (a dead or restarting local data engine) now surface as
  plain-language errors instead of hanging requests or silent failures, and each panel
  fails independently instead of taking the rest of the window down with it.
- Model/provider setup tells you why a key or connection failed, and a banner tells you
  when your selected model can't be reached; a working key you add now replaces a dead
  keyless default instead of silently coexisting with it.
- Chart drawings are now correctly scoped per symbol and timeframe, and indicator
  overlays no longer duplicate on repeated loads.
- Portfolio quote failures now show a staleness indicator instead of a wrong number, and
  the portfolio CSV export now carries a currency column and no longer mixes currencies
  in Weight %.
- Several research- and data-quality issues in Indian-market coverage (BSE/NSE
  identity, corporate disclosures, fundamentals cross-checked against exchange filings)
  were corrected; see Fixed below for the grouped list.
- Tickers on other foreign exchanges (BHP.AX, 0700.HK, 7203.T, VOD.L) now resolve
  instead of reading as delisted.

<!-- VERIFY: this list is still drawn only from the batch-2..batch-9 items this wave could
cross-check against FACTS.md's per-batch certification tallies line by line. Batches 10-22
merged on top of these (see Fixed and Part B) and certified well over 100 further entries,
including a per-currency portfolio-risk view, an EOD option-chain panel, provider fallback
order and start-layout preferences, and keybinding-conflict grouping — these are real,
shipped, verifier-approved code at this sha, but this wave did not re-derive which of them
belong in a user-facing "what changed" summary versus Fixed's register-grouped list.
Re-run this pass against each batch-10..22 VERDICTS.md's certified-id list at rc2. -->

## Removed: trading

Vysted Terminal no longer has any trading surface. Removed permanently, not deferred:
broker connectivity (all adapters), order placement and the order-review dialog, the
simulated paper-trading account and the live/paper mode switch, the kill switch, the
append-only order audit log, and every broker plugin.

**What stays:** your own tracked portfolio — manual holdings, cost basis, P&L on real
prices, CSV export, notes and watchlists — and everything the AI assistant does with it,
still gated behind your review before anything is written.

**If you used a broker connection before this release:** nothing is deleted
automatically. Your local `audit_log.db` (order/paper-trade history, default location
`~/.vysted-terminal/audit_log.db` unless you set a custom data directory) and any broker
API keys or tokens stored in your OS keychain are left in place — the app no longer
reads or writes any of it, but removing them from disk is a manual step. To clean up by
hand: delete your `audit_log.db`, and remove every keychain entry whose account starts
with `broker:` (including the onboarding entry `broker:_meta:first-launch-tos`, which is
not tied to any specific broker) — Keychain Access on macOS, Credential Manager on
Windows, or your secret-service keyring (e.g. GNOME Keyring / Seahorse) on Linux.

## Licence change

Vysted Terminal is source-available under **PolyForm Strict 1.0.0**, not open-source.
You can download, install and run it, and use it for any noncommercial purpose, without
asking. Commercial use, modifying it, or redistributing it (original or modified) needs
a commercial licence — see `COMMERCIAL_LICENSE.md`. The commercial terms and contact
address are placeholders for this release; commercial licensing is not yet available.
Everything committed before the relicensing commit stays available under the original
AGPL-3.0 terms it was released under; relicensing only changes terms for new work going
forward.

The plugin contract (`types/plugin.ts`, `types/plugin-runtime.ts`) and the bundled
example plugin are separately licensed under **Apache-2.0**, so a plugin you write
against just that surface isn't bound by the PolyForm Strict or commercial terms.

## Fixed

**Market data & instrument identity:** exchange-suffixed (.NS/.BO) and renamed India
tickers now resolve consistently across venues; tickers on other foreign exchanges
(BHP.AX, 0700.HK, 7203.T, VOD.L) now resolve instead of reading as delisted; a single
"same instrument" rule drives autocomplete, renames and cross-venue matching;
non-finite and unrealistic prices are rejected instead of displayed; a quote with no
timestamp no longer masquerades as fresh; SME/Emerge listing coverage was corrected;
quote freshness now follows the instrument's own exchange calendar, and a missing NSE
archive day is no longer mistaken for a holiday.

**Fundamentals & disclosures:** ownership, share-basis, EPS/P/E and revenue figures are
now cross-checked against the exchange filing before being shown; BSE and NSE corporate
disclosures (promoter pledge, bulk/block/SAST deals, corporate actions, FII/DII flows)
are surfaced as their own data and agent capabilities; undated news no longer sorts
ahead of dated news; background India-fundamentals warming now strips the Emerge (SME)
"-SM" suffix before the correctness gate runs, instead of gating on the bare symbol.

**Research:** cross-checking and reflection no longer marks an unverified claim as
agreed; source citations keep append-only numbering with model-added bibliography
entries stripped out; news about a different company no longer leaks into a research
brief; crashed research steps and failed page visits are reported as errors instead of
silently dropped; a ticker followed by a number is no longer misread as a foreign index
code; a leaked tool-call JSON fragment no longer runs on without a separator into the
citation guard's own replacement text.

**AI assistant & agent tools:** an in-flight tool call is cancelled cleanly when you
close the chat stream; when the assistant hits its tool-call limit it no longer leaves
calls half-done; dropped screener criteria and portfolio-edit failures are reported
instead of silently ignored; a compound multi-step task is planned before it runs;
unattended (Delegate) runs now have spend and time limits, save progress, and can be
resumed; a stray "[tool steps: …]" trailer stored inside the chat history is no longer
echoed back by a keyless local model as if it were its own reasoning.

**Charts, watchlist & portfolio:** indicator overlays no longer stack on repeated loads;
drawings are correctly scoped to symbol and timeframe; watchlist and compare-symbol
entries resolve through one consistent resolver;
a corrupted saved workspace is quarantined instead of breaking startup, and autosave
failures are surfaced instead of failing silently.

**Platform & sidecar:** the local data engine's connection status is now accurate in
both directions (it notices both disconnects and reconnects); a spawn failure or crash
is reported with its cause instead of a generic error; each panel has its own error
boundary so one panel's failure doesn't take down the window; the data cache is cleared
automatically on a version change.

<!-- VERIFY: the batch-2..batch-9 lines above are cross-checked against FACTS.md's final
open-high/open-medium/needs_gui lists at this sha. The three added lines (Emerge "-SM"
warming fix, the ratio-guard separator fix, the chat-history trailer echo fix) are each
individually confirmed certified — R15-LEAD-034, R15-LEAD-031, R15-LEAD-033 respectively,
named as certified in batch-18's and batch-17's own VERDICTS.md headers. Everything else
batches 10-22 certified (batch-10: 50 of 56 certified; batch-11: 18 of 26; batch-12: 19;
batch-13: 2; batch-16: 2; batch-17: 1 more beyond LEAD-031; batch-18: 2) is NOT yet
itemized here — those batches' VERDICTS.md files were not read entry-by-entry this pass.
Do that full pass at rc2 before treating this Fixed list as complete; batch-22 and
batch-23 additionally carry a "block" verdict overall (only batch-22's W1 lane merged, at
`c155e5ad` — see Part B), so nothing from either should be added without checking which
entries, if any, that partial merge actually certified. -->

## Known limitations

- **Builds are not code-signed.** macOS installs are blocked by Gatekeeper and Windows
  installs by SmartScreen; you'll need to right-click → Open (macOS) or click "More
  info" → "Run anyway" (Windows) to launch an unsigned build.
- **No auto-update.** There is no release pipeline producing signed update artifacts yet,
  so the in-app updater has nothing to check against — each release is a manual
  download.
- **Windows is unverified for this release.** CI has not had a passing run on this
  branch, so none of the three target platforms (Windows, macOS, Linux) currently has a
  verified green build from this exact branch; only macOS gets an additional manual
  clean-profile check before tagging.
- **Nine fixes still need a hands-on check in the desktop app.** Each passes automated
  checks, but it runs behind trusted mouse or keyboard events, or the macOS webview, and
  an automated tool cannot drive those. The nine are: CSV export from Watchlist and
  Portfolio on macOS; drawing placement, the Text label and drawing lock on the chart;
  the Notes Link popover; Notes slash-menu row height; brief export to .md, PDF and PNG
  files; maximising the agent dock; launch no longer freezing while MCP binds; the
  on-disk log file in a packaged build; and the sidecar refusing requests from other
  browser origins. Two manual checks have never been run: the documented Claude Desktop
  MCP setup, and the Windows MCP-spawn fix inside a launched packaged app.
- **Other open issues are low-severity.** One medium issue remains open: the "don't use
  tools" detector described below. The remaining gaps are accepted and documented:
  signing, the release pipeline, CI, extensibility, webview hardening and a few stale
  docs.
- **On the shipped default model (DeepSeek V4 Flash via OpenRouter) asking the assistant
  to edit your portfolio can come back as a content-filter refusal with no action
  taken;** pick another model in Settings if you hit it.
- **Deep research falls back to the keyless search engines** if Docker/OrbStack isn't
  running (it backs the local SearXNG search instance); the brief is labelled
  `keyless-fallback` when this happens. Start Docker/OrbStack first if you want full
  research depth.
- **If macOS denies the keychain read on first launch, the terms dialog and onboarding
  don't appear and no error is shown;** allow keychain access and relaunch.
- **Native web search on non-Anthropic providers has no per-run cap or spend meter.**

### Known limitations at rc1 — agent chat with a keyless local model

With a keyless local model (llama3.1:8b via Ollama), the agent can fabricate a figure, or
claim a completed write, when it has no tool result to ground the claim. No further
filter round is planned this release; each shape below is a documented, accepted
limitation of the local-model lane, not an open defect.

- **Invented figures for a company no successful call covered this turn.** With a
  keyless local model, the agent can still state an invented price or metric as if a
  tool had returned it when the figure is about a company no successful tool call in
  that turn covered — one named in the same paragraph as a company whose call succeeded
  (under a name the guard cannot map, or never looked up at all), or any company in a
  turn where no call failed or no tool was called — and a figure-less fabricated result
  dump or a code fence left open from an earlier round can also render, while every
  shape pinned in eight fix rounds is replaced by an honest "returned no data" note.
  (Accepted limitation.)
- **A stale bar, or an invented figure, for a company whose call succeeded.** With a
  keyless local model, a figure the agent states for a company whose data call succeeded
  is not checked against that result at all, so it can give an older bar's value from
  the same payload as the current price (2 of 18 live runs, 5-6% off) or a figure that
  appears nowhere in the payload (1 of 18: ₹20,820 for a ₹2,082 stock). (Accepted
  limitation.)
- **A false "done" or "staged" reply when tools are withheld and a write is asked for.**
  With a keyless local model, when you tell the agent not to use tools and ask for a
  portfolio change in the same message, it makes no call and nothing is written or
  queued, but its reply can say the change was made or staged for your review and can
  describe holdings that do not exist. (Accepted limitation.)
- **The "don't use tools" phrase detector both under- and over-matches.** An
  unrecognised no-tool phrasing keeps the tools, so the agent may still read data and
  propose a portfolio change (always held for your review, never applied; under AUTO a
  watchlist or chart change does apply) and can occasionally state a price it never
  fetched; a data request that only qualifies tool use (for example "other than price
  data", "for the math, but do fetch", "tools you don't need", "twice", "I never said
  don't use tools") loses every tool instead, and the agent then usually states an
  invented price as if fetched. (Still open at this sha — a narrowing-only fix for the
  over-match half is in its final batch, and the residual joins the known limitations
  above on that batch's verifier concurrence; confirmed at the tag.)

**Fail-safe.** A portfolio write never auto-applies regardless of any of the above:
`data-write` changes always stage for your review, and AUTO skips review only for
`panel`, `chart` and `watchlist` kinds. Figure grounding runs by provenance
(`sidecar/services/figure_grounding.py` + `agent_runtime._judge_clause`, rules
1/2a/2b/2c/3, with the 2c fail-safe gated on an errored tool call in that turn) — it is
what closes every shape pinned above, and its structural gap (an ok-subject figure isn't
checked at all, and an errored-only trigger misses no-call turns) is what the first two
limitations describe. A false "done" reply (the third) is contained by the review
queue, because a portfolio write needs a real tool call and a narrated one stages
nothing. The fourth is the phrase detector named next. The shipping "don't use tools"
matcher is the closed `_NO_TOOL_CUE` phrase list in `sidecar/services/planner.py`
(around line 136).

<!-- PART B: CHANGELOG v0.9.0 section -->

## v0.9.0 — R15: trading removed, relicensed, Stage C fix batches (2026-09-23 – 2026-09-26)

**Scope:** the R15 census-and-repair cycle on `004-r4-experience-rebuild`, from base tag
`r13-bedrock`. Trading was removed from the product permanently (D81, operator Tier-4
sign-off), the core was relicensed AGPL-3.0 → PolyForm Strict 1.0.0 + commercial (D83),
and the R15 register — 887 raw findings, closed to 603 entries at D84's Gate-2
adjudication, grown to **652 entries** at this sha as further lead-found `R15-LEAD-*`
entries were admitted during Stage C (16 critical / 116 high / 293 medium / 227 low,
plus 76 rejections) — was worked down across 22 Stage-C batches plus an rc1 gate round,
each merged `--no-ff` from an isolated integrator worktree and each independently
verified fresh-context before merge
(`docs/redesign/verification/r15/stage-c/batch-N/VERDICTS.md`). By this sha: 391 entries
`fixed`, 206 `open`, 25 `blocked_tier4` (operator-attended, §4 below), 14
`removed_with_feature` (trading, D81), 11 `needs_gui`, 5 `not_a_defect`. Of the 206 open,
exactly **one** is critical/high/medium severity — `R15-LEAD-035` (medium, agent-tools,
see the Known-limitations section above) — the remaining 205 open entries are low
severity. No `r15-rc1` tag exists yet at this sha; a first rc1 gate run (`R15_GATE_RC1.md`,
round 1) **FAILED** against an earlier candidate and drove several of the batch-12..22
fix rounds — the gate has not been re-run to a pass at this sha. Stage D (this wave)
drafts release collateral read-only, beside the fix batches, at a pinned sha.

**Batches (merge commits, first-parent, newest first per `git log --first-parent
--merges`):**

- `c155e5ad` Stage C batch 22 — **W1 lane only**; the batch's overall verifier verdict was
  `block`, so only the non-blocking W1 worktree merged (see Known limitations above for
  the class this batch's fabrication work bears on)
- `86ae79c4` Stage C batch 21 — fabrication-guard hardening (approve; 0 new register
  entries certified this batch; closes every batch-20 escape bar one narrow tilde-fence
  regression, see LEAD-036)
- `1abef99b` Stage C batch 20 — fabrication-guard hardening (approve; 0 certified)
- `ec7f7cd6` Stage C batch 19 — fabrication-guard hardening (approve; 0 certified;
  closes the batch-18 escapes)
- `ebc5ed41` Stage C batch 18 — citation/history-trailer and Emerge-SME warming fixes
  (approve; 2 certified: `R15-LEAD-033`, `R15-LEAD-034`)
- `292ba53a` Stage C batch 17 — citation guard seeded from history, humanised tool
  names, cross-line dump drop, partial tool-call marker hold (approve; `R15-LEAD-031`
  certified)
- `d64640d2` Stage C batch 16 — ratio-guard class qualifier, untraced tool-citation
  guard, bounded `adr_ratio` lookup (approve; 2 certified)
- `74ee3468` Stage C batch 15 — ADR ratio grounded from the SEC 20-F cover page,
  marker-based depositary guard (approve; 0 certified, no regression)
- `17301f54` Stage C batch 14 — `tool_result` SSE event and grader; ADR ratio guard
  second pass (approve; `R15-CODE-AGENT-033` certified, `R15-AGENT-090` not certified)
- `a217a529` Stage C batch 13 — Public Suffix List check, live universe-count docs,
  ratio guard partial (approve; 2 certified)
- `ef33c7f6` Stage C batch 12 — rc1 refutation-audit reopenings and gate findings
  (approve; 19 certified, 3 not certified: `R15-RESEARCH-007`, `R15-DOCS-017`,
  `R15-AGENT-090`)
- `57897778` rc1 gate — fix rounds 1-2, addressing `R15_GATE_RC1.md` round-1 blockers
- `4097dac4` Stage C batch 11 — build recipe/gates, runtime phases and schema versions,
  agent eval harness, registry/deep-crawl loop, reference data, option chain, provider
  preferences, contrast, per-currency portfolio risk (approve; 18 of 26 certified)
- `f407107f` Stage C batch 10 — runtime/backtest integrity, catalog and host actions,
  fundamentals truth, screener and state docs, chat and search, chart defaults and
  notes, marketplace and panels, plugin lifecycle (approve; 50 of 56 certified)
- `6b702305` Stage C batch 9 — agent runtime identity + budget, research/search/news,
  fundamentals identity + earnings, market lanes + errors + quant, frontend shell (29
  certified)
- `68bb7aa4` Stage C batch 8 — sidecar lifecycle/transport, provider readiness,
  data-error honesty, resolver/exchange lanes, agent runtime/research (39 certified)
- `e81c9e7c` Stage C batch 7 — exchange-filed India fundamentals, durable delegate
  runs, unattended workflows, chart/workspace integrity, research funnel, agent-write
  Undo (50 certified, 1 needs GUI, 4 open)
- `5e147317` Stage C batch 6 — India Emerge lanes, runtime tool-call identity, research
  funnel, host-action intents, quant pool, panel bus keys (21 certified, 3 open) +
  quant-pool leak fix
- `1574ed8e` Stage C batch 5 — India exchange lanes, resolver masters, runtime liveness
  and memory, workflow control flow, sidecar boundary, screener and earnings (48
  certified, 2 need GUI, 6 open) + LEAD-010 regression fix
- `dcbe7bae` Stage C batch 4 — context admission, Gemini/xAI lanes, workflows, Delegate
  output, market-data gate, panels (45 certified, 2 need GUI, 3 open)
- `c81d879b` Stage C batch 3 — agent runtime, AUTO gate, LLM adapters, research depth,
  India witnesses (38 certified, 2 open)
- `806a90ca` Stage C batch 2 — critical + high data/research/workspace fixes (37
  certified, 3 reopened)
- `a122dbf6` feat(d81) — remove trading from the product (Stage C batch 1)

**Not yet merged at this sha:** Stage C batch 23 (integrator branch left unmerged — its
own verifier verdict was `block`, and the disposition/concurrence work for
`R15-LEAD-030/035/037/038` ran alongside it instead of inside it); Stage C batch 24 (in
flight, not tracked at this sha; it carries the named narrowing-only fix for
`R15-LEAD-035`'s over-match half).

<!-- VERIFY: CHANGELOG.md itself only carries a full per-batch narrative section through
batch-17 at this sha (plus the trading-removal and rc1-gate-round-1 headings) — batches
18-22's one-line summaries above come from each batch's own VERDICTS.md header, not from
a CHANGELOG.md section, because none exists yet for those five batches. That's a real gap
for the lead to close (a CHANGELOG.md entry per batch) before or at rc2, not something
this wave can write on their behalf. -->

**Decisions (D-numbers since `r13-bedrock`, full text and rationale in
`docs/redesign/DECISIONS.md`):**

- **D81** — trading removed from the product permanently (operator Tier-4 sign-off);
  reverses BLUEPRINT §2 (locked) and touches the §6.5 safety surface, allowed only by
  this explicit sign-off.
- **D82** — OpenAI-direct run spend cap set to $8.00, enforced structurally in
  `scripts/r15/vy.py`.
- **D83** — core relicensed AGPL-3.0 → PolyForm Strict 1.0.0 in one dedicated commit
  before the session's first push; plugin contract + example plugin carved out under
  Apache-2.0; every pre-relicense commit stays AGPL-3.0.
- **D84** — Gate 2 (R15 census) adjudicated closed: 887 raw findings → 603 entries with
  every raw id traceable to an admit, refute or removal.
- **D85–D92** — trading-removal-plan riders: first-launch terms dialog survives
  rewritten (no kill-switch promise); the planner keeps `buy`/`sell` edit signals and
  drops order-phrase signals; "paper portfolio" becomes "portfolio" everywhere;
  BLUEPRINT keeps the §6.5 section number retitled; `registry_v0_6_5.py` deleted;
  R15-LIFECYCLE-002 (workspace restore never drops user data on an unknown panel)
  shipped in the same batch as the removal; the India EOD-only data error no longer
  suggests connecting a broker; no automatic purge of leftover broker secrets/audit
  history (operator decision, tracked as DECISIONS_FOR_OPERATOR §3.1).

No further D-numbers were added between D92 and this sha.

**Register at this sha:** 16 critical (0 open), 116 high (0 open), 293 medium (1 open:
`R15-LEAD-035`), 227 low (205 of them still open); 11 entries need hands-on GUI
verification (listed in Known limitations above); 25 are `blocked_tier4`
(operator-attended — release signing/pipeline/CI plus MCP-server extensibility, webview
CSP, plugin data-contribution model, first-party-panels-bypass-plugin, a few stale doc
claims, and three of the four `R15-LEAD-*` local-model items above (030, 037, 038; 035
is still `open`); tracked in `docs/redesign/DECISIONS_FOR_OPERATOR.md` §2.8–§2.21 and
§4).

**Carried forward / not yet done at this sha:**

- Version still reads `0.8.0` across every source-of-truth file (`package.json`,
  `src-tauri/Cargo.toml`, `src-tauri/tauri.conf.json`, `sidecar/app.py`,
  `src/lib/plugin-bootstrap.ts` `HOST_VERSION`, `src-tauri/Cargo.lock`) — bump all six
  together before tagging `v0.9.0`, per CLAUDE.md's "Versioning & process" gotcha. A
  version-bump branch (`worktree-agent-r15-version-0.9.0`) is prepared separately from
  this refresh; it merges right after the `r15-rc1` tag, not before.
- No code-signing, no release workflow, no auto-updater wiring
  (`DECISIONS_FOR_OPERATOR.md` §2.8–§2.10) — all Tier-4, blocked on the operator.
- CI has never had a green run on `004-r4-experience-rebuild` (§2.6, §2.11, §2.17) — the
  3-OS `build`/`lint`/`test` workflows exist (`push` restricted to `main`,
  `pull_request` unrestricted) but nothing has exercised them on this branch yet.
- `sidecar/services/agent_tools/registry_v0_6_5.py`, the kill switch, the append-only
  order audit log, and 17 trading-only sidecar test files are deleted, not stubbed
  (D81/D89).
- The rc1 gate has run once (round 1, FAIL, against an earlier candidate sha) and has
  not been re-run to a verdict at this sha; round 2 launches once batch-24 merges.
  Confirm the gate's final verdict, and any tag name/sha, at the tag.

**Verification snapshot:**

<!-- fill at rc2: ci-local / smoke / rc gate round-2 results -->

<!-- refresh f4444790 to 4d89314: register grew from 626 to 652 entries and open critical/high/medium fell from 117 (3 high + 114 medium) to 1 (R15-LEAD-035 only) as batches 10-22 merged; rewrote Known limitations' local-model section with the now-binding blocked_tier4 wording for LEAD-030 (clause struck per the batch-23 disposition verifier)/037/038 and the still-open LEAD-035 pending batch-24 concurrence, plus the fail-safe/shipping-matcher pointers; extended Part B's batch list through batch-22 (block verdict, W1-only merge) and flagged batch-23 (blocked, unmerged) and batch-24 (in flight); added three individually-certified Fixed lines (LEAD-031/033/034) and flagged the rest of batches 10-22's certifications as an open rc2 task rather than guessing; updated needs_gui from 6 to the 11 FACTS lists, with titles; corrected the version-bump note to say the prepared branch lands after the r15-rc1 tag; noted the rc1 gate round-1 FAIL and that round 2 is pending batch-24. -->

<!-- critic-footer -->

## Critic findings applied

1. applied: replaced the "Eleven fixes" bullet with the critic's "Nine fixes" bullet (Part A Known limitations), verified each needs_gui note against the register JSON at the sha (R15-CODE-AGENT-001, UI-083, UI-084, LIFECYCLE-001, LIFECYCLE-008, UI-009, UI-025, UI-050, UI-022) and dropped the false `/mcp` no-auth-check disclosure; DOCS-024/LIFECYCLE-040 correctly excluded as they are not fixes.
2. applied: deleted the "still fail to resolve" bullet, added the LEAD-022 fix to What-changed and to Fixed › Market data; verified `R15-LEAD-022 fixed` in the register and `sidecar/services/yfinance_provider.py:219-222` at the sha.
3. applied: removed the "locked drawing can't be deleted" clause from What-changed and Fixed › Charts; verified R15-UI-022 is `needs_gui` in the register with the locked-delete check listed as pending GUI verification (`batch-7/VERDICTS.md:156-166`).
4. applied: rewrote the LEAD-030/037/038 bullets to the verbatim sentences from `batch-23/LEAD-030-CONCURRENCE.md:118-123` (with the "figures for companies whose call succeeded are grounded" clause struck, confirmed present in source) and `batch-23/DISPOSITION-CONCURRENCE.md:313-320`, keeping bold lead-ins outside the quoted text.
5. applied: dropped register ids/status tokens from Part A (LEAD-030/037/038 → "Accepted limitation", LEAD-035 → prose wording without the id), rewrote the "Open issues remain" bullet per the critic's replacement text, and removed the internal `DECISIONS_FOR_OPERATOR.md` §2 pointer from Part A.
6. applied: "three of the four `R15-LEAD-*` local-model items above (030, 037, 038; 035 is still `open`)"; verified against the register JSON (`blocked_tier4` LEAD ids = 030/037/038, LEAD-035 = open).
7. applied: "227 low (205 of them still open)"; verified open-by-severity from the register JSON = `{low: 205, medium: 1}`.
8. applied: rewrote the fail-safe paragraph to say the structural gap is what the first two limitations describe, the third is contained by the review queue (a narrated write stages nothing), and the fourth is the phrase detector.
9. verified instead: the critic's own fix text defers full itemization of batches 10-16's 92 certified entries to rc2 ("do that full pass at rc2... drop both VERIFY comments once that is done"); the existing VERIFY comments already state this gap accurately, so no draft rewrite was made in this pass — itemizing 92 entries from six VERDICTS.json files is the rc2 task the finding itself describes, not a revise-now fix.
10. applied: added "The commercial terms and contact address are placeholders for this release; commercial licensing is not yet available." to the Licence section; verified `COMMERCIAL_LICENSE.md:1-4` (STATUS: DRAFT) and `:63` (placeholder address) at the sha.
11. applied: added the two missing bullets (macOS keychain TOS-hydrate failure; native web-search spend meter gap) to Known limitations; verified R15-UI-044 and R15-AGENT-049 are `blocked_tier4` in the register.
12. applied: "(2026-09-23 – 2026-09-26)"; verified `c155e5ad` (batch 22) merged 2026-09-26 via `git log --first-parent --merges`.
13. applied: "Stage C batch 24 (in flight, not tracked at this sha; it carries the named narrowing-only fix for `R15-LEAD-035`'s over-match half)"; verified `git ls-tree --name-only <sha> docs/redesign/verification/r15/stage-c/` lists batch-2..batch-23 only, no batch-24.
