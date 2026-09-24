<!-- DRAFT at f444479031d7d493b7955b9af041d18e7c7a40cc by the Stage D docs wave; refresh before rc2 -->

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
- Chart drawings are now correctly scoped per symbol and timeframe, indicator overlays
  no longer duplicate on repeated loads, and a locked drawing can't be deleted by
  accident.
- Portfolio quote failures now show a staleness indicator instead of a wrong number, and
  the portfolio CSV export now carries a currency column and no longer mixes currencies
  in Weight %.
- Several research- and data-quality issues in Indian-market coverage (BSE/NSE
  identity, corporate disclosures, fundamentals cross-checked against exchange filings)
  were corrected; see Fixed below for the grouped list.

<!-- VERIFY: this list is drawn only from register entries the batch-by-batch fresh-context
verification (VERDICTS.md) certified and that do not appear in FACTS.md's still-open
register lists at this sha; it omits real, coded batch-9 frontend/shell work (keyboard
remap system, destructive-action confirms, viewport-aware layout templates, settings
export/import, onboarding copy) because the register still lists those entries open at
this sha, not because the code isn't there — recheck the register at rc2, this may move
several of those into "What changed for you". -->

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
a commercial licence — see `COMMERCIAL_LICENSE.md`. Everything committed before the
relicensing commit stays available under the original AGPL-3.0 terms it was released
under; relicensing only changes terms for new work going forward.

The plugin contract (`types/plugin.ts`, `types/plugin-runtime.ts`) and the bundled
example plugin are separately licensed under **Apache-2.0**, so a plugin you write
against just that surface isn't bound by the PolyForm Strict or commercial terms.

## Fixed

**Market data & instrument identity:** exchange-suffixed (.NS/.BO) and renamed India
tickers now resolve consistently across venues; a single "same instrument" rule drives
autocomplete, renames and cross-venue matching; non-finite and unrealistic prices are
rejected instead of displayed; a quote with no timestamp no longer masquerades as fresh;
SME/Emerge listing coverage was corrected; quote freshness now follows the instrument's
own exchange calendar, and a missing NSE archive day is no longer mistaken for a
holiday.

**Fundamentals & disclosures:** ownership, share-basis, EPS/P/E and revenue figures are
now cross-checked against the exchange filing before being shown; BSE and NSE corporate
disclosures (promoter pledge, bulk/block/SAST deals, corporate actions, FII/DII flows)
are surfaced as their own data and agent capabilities; undated news no longer sorts
ahead of dated news.

**Research:** cross-checking and reflection no longer marks an unverified claim as
agreed; source citations keep append-only numbering with model-added bibliography
entries stripped out; news about a different company no longer leaks into a research
brief; crashed research steps and failed page visits are reported as errors instead of
silently dropped; a ticker followed by a number is no longer misread as a foreign index
code.

**AI assistant & agent tools:** an in-flight tool call is cancelled cleanly when you
close the chat stream; when the assistant hits its tool-call limit it no longer leaves
calls half-done; dropped screener criteria and portfolio-edit failures are reported
instead of silently ignored; a compound multi-step task is planned before it runs;
unattended (Delegate) runs now have spend and time limits, save progress, and can be
resumed.

**Charts, watchlist & portfolio:** indicator overlays no longer stack on repeated loads;
drawings are correctly scoped to symbol and timeframe and a locked drawing can't be
deleted; watchlist and compare-symbol entries resolve through one consistent resolver;
a corrupted saved workspace is quarantined instead of breaking startup, and autosave
failures are surfaced instead of failing silently.

**Platform & sidecar:** the local data engine's connection status is now accurate in
both directions (it notices both disconnects and reconnects); a spawn failure or crash
is reported with its cause instead of a generic error; each panel has its own error
boundary so one panel's failure doesn't take down the window; the data cache is cleared
automatically on a version change.

<!-- VERIFY: each line above groups only register entries whose batch VERDICTS.md
certified them (cross-checked against FACTS.md's final open-high/open-medium/needs_gui
lists at this sha, which excluded roughly half of the entries a batch's own CHANGELOG
scope note describes as "delivered" — several batch-8/batch-9 fundamentals, market-data
and frontend-shell items are still open per the register and are deliberately left out
above). Re-run this cross-check against the register at rc2 before publishing, in case
later closeout work certified more of them. -->

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
- **Six fixes still need hands-on verification in the desktop app:** CSV export on
  macOS, the Notes Link button, chart drawing placement, the launch-time freeze while
  the MCP helpers bind, the persisted log file, and the sidecar's cross-origin policy.
- **Tickers on non-Indian foreign exchanges (BHP.AX, 0700.HK, 7203.T, VOD.L) still fail
  to resolve** — the symbol lookup mangles the exchange suffix.
- **Open issues remain**, concentrated in market-data provider edge cases, the
  frontend/shell chrome, the plugin surface, build scripts, and company-fundamentals
  coverage; three higher-severity issues remain in the agent runtime, the LLM provider
  adapters and the symbol resolver.
- **On the shipped default model (DeepSeek V4 Flash via OpenRouter) asking the assistant
  to edit your portfolio can come back as a content-filter refusal with no action
  taken;** pick another model in Settings if you hit it.
- **Deep research falls back to the keyless search engines** if Docker/OrbStack isn't
  running (it backs the local SearXNG search instance); the brief is labelled
  `keyless-fallback` when this happens. Start Docker/OrbStack first if you want full
  research depth.

<!-- PART B: CHANGELOG v0.9.0 section -->

## v0.9.0 — R15: trading removed, relicensed, Stage C fix batches (2026-09-23 – 2026-09-24)

**Scope:** the R15 census-and-repair cycle on `004-r4-experience-rebuild`, from base tag
`r13-bedrock`. Trading was removed from the product permanently (D81, operator Tier-4
sign-off), the core was relicensed AGPL-3.0 → PolyForm Strict 1.0.0 + commercial
(D83), and the R15 register (887 raw findings → 603 entries at D84, 626 by this sha
after 23 lead-found `R15-LEAD-*` entries were admitted during Stage C; 16 critical / 112
high / 279 medium / 219 low, plus 76 rejections) was worked down in nine Stage C batches, each
merged `--no-ff` from an isolated integrator worktree and each independently verified
fresh-context before merge (`docs/redesign/verification/r15/stage-c/batch-N/VERDICTS.md`).
All 16 criticals are certified fixed; 3 highs and 114 mediums remain open (see the
register cross-reference below). Stage D (this wave) drafts release collateral
read-only, beside the fix batches, at a pinned sha.

**Batches (merge commits, first-parent):**

- `a122dbf6` feat(d81): remove trading from the product (Stage C batch 1)
- `806a90ca` fix(r15): Stage C batch 2 — 40 critical/high entries (37 certified, 3 reopened)
- `c81d879b` fix(r15): Stage C batch 3 — 40 critical/high entries (38 certified, 2 open)
- `dcbe7bae` fix(r15): Stage C batch 4 — 52 high entries (45 certified, 2 need GUI, 3 open)
- `1574ed8e` fix(r15): Stage C batch 5 — 58 high/medium entries (48 certified, 2 need GUI,
  6 open) + LEAD-010 regression fix
- `5e147317` fix(r15): Stage C batch 6 — 22 delivered high/medium entries (21 certified,
  3 open) + quant-pool leak fix
- `e81c9e7c` fix(r15): Stage C batch 7 — 55 high/medium entries (50 certified, 1 needs
  GUI, 4 open)
- `68bb7aa4` merge(r15): Stage C batch 8 — 39 certified live (sidecar lifecycle/transport,
  provider readiness, data-error honesty, resolver/exchange lanes, agent runtime/research)
- `6b702305` merge(r15): Stage C batch 9 — 29 certified live (agent runtime identity +
  budget, research/search/news, fundamentals identity + earnings, market lanes + errors +
  quant, frontend shell)

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

**Register at this sha:** 16 critical (0 open), 112 high (3 open: agent runtime, LLM
adapters, resolver), 279 medium (114 open), 219 low (205 open); 6 entries need hands-on
GUI verification; 4 are blocked on the operator (release signing/pipeline/CI, tracked in
`docs/redesign/DECISIONS_FOR_OPERATOR.md` §2.8–2.11).

**Carried forward / not yet done at this sha:**

- Version still reads `0.8.0` across every source-of-truth file (`package.json`,
  `src-tauri/Cargo.toml`, `src-tauri/tauri.conf.json`, `sidecar/app.py`,
  `src/lib/plugin-bootstrap.ts` `HOST_VERSION`, `src-tauri/Cargo.lock`) — bump all six
  together before tagging `v0.9.0`, per CLAUDE.md's "Versioning & process" gotcha.
- No code-signing, no release workflow, no auto-updater wiring
  (`DECISIONS_FOR_OPERATOR.md` §2.8–2.10) — all Tier-4, blocked on the operator.
- CI has never had a green run on `004-r4-experience-rebuild` (§2.6, §2.11) — the 3-OS
  `build`/`lint`/`test` workflows exist (`push` restricted to `main`, `pull_request`
  unrestricted) but nothing has exercised them on this branch yet.
- `sidecar/services/agent_tools/registry_v0_6_5.py`, the kill switch, the append-only
  order audit log, and 17 trading-only sidecar test files are deleted, not stubbed
  (D81/D89).

**Verification snapshot:**

<!-- fill at rc2: ci-local / smoke / rc gate results -->

<!-- critic-footer -->

## Critic findings applied

1. applied — replaced with the six named fixes and their desktop-verification hooks (Known limitations).
2. applied — deleted the rotating-log / redacted-Settings-export clause from Fixed / Platform & sidecar.
3. applied — replaced with the certified R15-DATA-042 CSV currency-column fix (What changed for you).
4. applied — narrowed to exchange-suffixed (.NS/.BO) and renamed India tickers (Fixed / Market data); added the open non-Indian-foreign-exchange limitation (Known limitations).
5. applied — replaced with the certified exchange-calendar and NSE-archive fixes (Fixed / Market data).
6. applied — "workspace cache" corrected to "data cache" (Fixed / Platform & sidecar).
7. applied — deleted the unsourced research-spend-display clause (Fixed / AI assistant).
8. applied — replaced the operator-environment note with the certified default-model content-filter limitation (Known limitations).
9. applied — "this file's" corrected to "CLAUDE.md's" (Part B / Carried forward).
10. applied — "quietly degrades" corrected to name the keyless-fallback brief label (Known limitations).
11. applied — D91 (India EOD-only error copy) added to the D85–D92 rider list.
12. applied — added the 603→626 bridge (23 lead-found R15-LEAD-* entries) next to the register count (Part B / Scope).
13. applied — rewrote the broker cleanup instructions: `broker:_meta:first-launch-tos` is not former-broker-specific, added Linux secret-service keyring, and made the audit_log.db path conditional on a custom data dir.
14. applied — stripped the jargon phrases named (fundamentals witnessing, witness source, leading verdict token, off-entity news, deep/ultra research pass, capped final round, delegate/checkpointing) throughout Part A; register-id-free prose already held. The two `<!-- VERIFY -->` comments are left in place per this wave's own rule that an unverifiable/conditional claim stays wrapped rather than asserted — stripping them is the lead's job at rc2 promotion, not this revision pass.
