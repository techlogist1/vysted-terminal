<!-- DRAFT written 06:54 IST 26 Sep by the Stage D burst-window handover writer, head `6bc6d378cbbf9cfbefd8d155e027c2dc80214331` on `004-r4-experience-rebuild`; corrected 07:00 IST 26 Sep by the handover reviewer (critic/OPERATOR_HANDOVER.md). Promotion target: unverified — `STAGE_D_INDEX.md` "How to promote at rc2" names none for this file; the lead picks one. -->

# Operator handover — Vysted Terminal, R15 "LAUNCH"

Reader: you, cold, after weeks away. You do not need to remember what this product is or what
this run did. Every fact below cites the file it came from; anything that could not be checked
is marked `unverified:` with what would verify it.

## 1. What this is

Vysted Terminal is a desktop finance terminal: a Tauri app that pairs a multi-panel market
cockpit (charts, watchlist, news, portfolio, screener, macro, SEC filings, a node-editor/workflow
surface) with an AI copilot that can read data and drive the terminal. A Rust core, a Vite +
React frontend and a Python FastAPI sidecar talk to each other over `127.0.0.1` only, with
bring-your-own-keys for every AI provider (`docs/redesign/verification/r15/stage-d/README.draft.md`,
intro and BYOK). R15 "LAUNCH" is an autonomous run that verified it end to end: a census of every
promised or discovered defect, then fix batches ("Stage C"), then release-candidate gates
(`docs/redesign/verification/r15/stage-d/OPERATOR_BRIEFING.draft.md` §1).

What changed in R15, in five lines (`OPERATOR_BRIEFING.draft.md` §1–§3; `FACTS.md` §Register):

- Trading is out of the product for good (D81): 0 broker/order/kill/audit routes left, all 22
  former routes 404 (`OPERATOR_BRIEFING.draft.md` §2). Your tracked portfolio stays.
- The core licence is PolyForm Strict 1.0.0 plus a commercial licence; the plugin contract and
  example plugin stay Apache-2.0.
- The register holds 652 entries (887 raw; 16 critical / 116 high / 293 medium / 227 low).
  Status split: 391 fixed, 205 open (all low), 26 `blocked_tier4`, 11 `needs_gui`, 14 removed
  with trading, 5 not a defect. Open critical/high/medium: zero (register JSON, read directly).
  The 205 open lows are written on pushed branches but not yet integrated
  (`OPERATOR_BRIEFING.draft.md` §3 "Lows").
- One known-limitation class, verbatim from `FACTS.md` "Known limitations at rc1": "with a
  keyless local model the agent can fabricate a figure, or claim a completed write, when it has
  no tool result to ground the claim; no further filter round this release". You accepted
  `R15-LEAD-030`/`037`/`038` as that class on Sat 26 Sep 04:15 IST; `R15-LEAD-035` carries the
  same status as an escalation still awaiting your (a)/(b) choice (`OPERATOR_BRIEFING.draft.md`
  §3; §4 item 2 below).
- Every version file still reads `0.8.0`; the 0.9.0 bump sits unmerged on
  `worktree-agent-r15-version-0.9.0` (`517da226`, `c1e9164c`; `git merge-base --is-ancestor
  517da226 HEAD` fails at this head). No `r15-*` tag exists (`git tag --list 'r15*'` is empty);
  rc1 gate round 1 was FAIL (`R15_GATE_RC1.md:3`); unverified: round 2's verdict (the briefing
  §1 records it in flight as `wf_4ed38558-4d0`).

## 2. Hand-testing guide

### Launch

**Dev stack** (`OPERATOR_BRIEFING.draft.md` §5): `pnpm tauri:dev` → `pnpm tauri:mcp` →
`tauri dev --features dev-tools`; the webview is Vite (`pnpm dev`). `pnpm tauri:dev`'s
`beforeDevCommand` builds any missing or stale sidecar itself.

**The bundle, from a clean profile** (`RELEASE_RUNBOOK.draft.md` §7). No env var exists for a
fresh app-data dir; it resolves to a fixed OS path, so isolation overrides `HOME` and launches the
bundle binary directly, never via `open`:

```
HOME=<fresh dir> "<bundle>/Contents/MacOS/vysted-terminal"
```

Two caveats from the rehearsal (`RELEASE_RUNBOOK.draft.md` §7, sha `64e9470e`, not the release
candidate): WKWebView is **not** isolated by `HOME=` (it still writes your real
`~/Library/WebKit/com.vysted.terminal` and `~/Library/Caches/com.vysted.terminal`; the runbook
says do not delete those files), and a `HOME=` launch has **no default keychain**, so the
first-launch terms dialog never renders there. That result is inconclusive, not a pass. The
terms/keychain check needs a separate macOS user account.

### First run and the populated anchors

`CLAUDE.md` "Visual verification": watchlist `AAPL, MSFT, NVDA, SPY, QQQ, BTC/USDT, ETH/USDT`;
chart SPY with indicators and VWAP; equity overview AAPL; news with sentiment; portfolio with ≥1
position and P&L. Capture dark theme at both 1920×1080 and 2560×1440; never overwrite an existing
shot.

### Things to try (area — action → expected result)

1. **ui-panels** — Save a named workspace, then add holdings or notes, then load that workspace →
   your later portfolios, watchlist and notes are not rolled back to save-time (register
   `R15-CODE-FRONTEND-001`, critical, `fixed`; `NAMED_LISTS.md` §UI and panels).
2. **ui-panels** — Pick a ticker from the command palette (Cmd/Ctrl-K) → it loads straight into
   the chart (`RELEASE_NOTES.draft.md` "What changed for you").
3. **ui-panels** — Draw on a chart, switch symbol and timeframe, switch back → drawings stay
   scoped to their symbol and timeframe; indicator overlays do not stack on repeated loads
   (`RELEASE_NOTES.draft.md` Fixed › Charts, watchlist & portfolio).
4. **ui-panels** — Export CSV from Watchlist or Portfolio in the packaged app → **needs a
   hands-on check**: `R15-UI-009` (high) is `needs_gui` (`FACTS.md` §Register); the briefing's
   expected result is the saved path shown under `<app data>/exports/csv/`
   (`OPERATOR_BRIEFING.draft.md` §4).
5. **ui-panels** — Place a drawing, click past the last bar, use the Text label, delete a locked
   drawing → **needs a hands-on check**: `R15-UI-022` (medium, `needs_gui`) needs native event
   injection, not chrome-devtools (`OPERATOR_BRIEFING.draft.md` §4).
6. **agent-chat** — With a keyless local model (the run's live bars used Ollama `llama3.1:8b`,
   `OPERATOR_BRIEFING.draft.md` §5; the README names `qwen2.5:7b` as the default), ask for a
   price on a company no tool call in that turn covered → **known limitation** `R15-LEAD-030`
   (high, `blocked_tier4`), wording verbatim from `FACTS.md`:
   > With a keyless local model, the agent can still state an invented price or metric as if a
   > tool had returned it when the figure is about a company no successful tool call in that
   > turn covered — one named in the same paragraph as a company whose call succeeded (under a
   > name the guard cannot map, or never looked up at all), or any company in a turn where no
   > call failed or no tool was called — and a figure-less fabricated result dump or a code
   > fence left open from an earlier round can also render, while figures for companies whose
   > call succeeded are grounded against the tool result and every shape pinned in eight fix
   > rounds is replaced by an honest "returned no data" note.

   `FACTS.md` records that the batch-23 disposition verifier struck the clause "figures for
   companies whose call succeeded are grounded against the tool result" (see `R15-LEAD-037`).
7. **agent-chat** — Say "Don't use any tools, except price_data, what's AAPL's price?" → **known
   limitation** `R15-LEAD-035` (medium, `blocked_tier4` as an escalation, not a concurrence; your
   call, §4 item 2), verbatim from `FACTS.md`:
   > With a keyless local model, the "don't use tools" detector is a fixed phrase list: an
   > unrecognised no-tool phrasing keeps the tools, so the agent may still read data and propose
   > a portfolio change (always held for your review, never applied; under AUTO a watchlist or
   > chart change does apply) and can occasionally state a price it never fetched, while a data
   > request that qualifies a no-tool instruction after a comma or in reported speech ("Don't use
   > any tools, except price_data …", "No tools, other than the price lookup …", "He says don't
   > use tools, but …") still loses every tool and the agent then usually states an invented
   > price as if fetched.
8. **agent-chat** — Tell the agent not to use tools and ask for a portfolio change in the same
   message → **known limitation** `R15-LEAD-038` (medium, `blocked_tier4`), verbatim from
   `FACTS.md`:
   > With a keyless local model, when you tell the agent not to use tools and ask for a
   > portfolio change in the same message, it makes no call and nothing is written or queued,
   > but its reply can say the change was made or staged for your review and can describe
   > holdings that do not exist.
9. **agent-chat** — Ask the assistant (any autonomy mode) to change a portfolio position or a
   setting → it stages for your review; AUTO applies only `panel`, `chart` and `watchlist`
   kinds (`types/proposed-change.ts:38-42`, `AUTO_APPLIED_KINDS`; `DECISIONS_FOR_OPERATOR.md`
   §3.5).
10. **agent-chat** — On the shipped default OpenRouter model (DeepSeek V4 Flash), ask it to edit
    your portfolio → **known limitation**: can come back as a content-filter refusal with no
    action taken; pick another model in Settings (`RELEASE_NOTES.draft.md` Known limitations;
    `DECISIONS_FOR_OPERATOR.md` §4.2).
11. **research-search** — With Docker/OrbStack stopped, ask for a deep-research brief → it falls
    back to the keyless search engines and the brief is labelled `keyless-fallback`
    (`RELEASE_NOTES.draft.md` Known limitations; `DECISIONS_FOR_OPERATOR.md` §2.2).
12. **research-search** — Ask about a foreign-exchange ticker (BHP.AX, 0700.HK, 7203.T, VOD.L) →
    it resolves instead of reading as delisted (`RELEASE_NOTES.draft.md`; register
    `R15-LEAD-022`, high, `fixed`, file `sidecar/services/resolver.py`).
13. **research-search** — Ask for a FAST brief on an Indian name the process has not seen yet →
    the first brief may show no fundamentals card ("pulled 2/4 data sources"); the second brief
    and the model's own follow-up call get it. The lead recommends accepting this for rc1; it is
    your decision (`DECISIONS_FOR_OPERATOR.md` §4.1).
14. **research-search** — Trigger native web search on a non-Anthropic provider → **known
    limitation**: no per-run cap or spend meter (`RELEASE_NOTES.draft.md` Known limitations;
    `R15-AGENT-049`, `blocked_tier4`).
15. **data-smallcaps** — Open Equity Overview for an Indian listing → ownership, share-basis,
    EPS/P/E and revenue are cross-checked against the exchange filing before being shown
    (`RELEASE_NOTES.draft.md` Fixed › Fundamentals & disclosures).
16. **data-smallcaps** — Open an SEC filing detail for an accession outside the issuer's last 40
    filings → it no longer renders as `10-K` filed today with a blank company name (register
    `R15-DATA-007`, critical, `fixed`).
17. **data-smallcaps** — Open a 1y chart of a BSE-only name → no poisoned trading day from a
    bhavcopy fetched before publication, and no per-day whole-market re-parse (register
    `R15-DATA-035`/`R15-DATA-036`, high, `fixed`).
18. **ui-panels** — Cold-launch the packaged app right after a reboot → **needs a hands-on
    check**: `R15-LIFECYCLE-001` (high, `needs_gui`): the window paints and takes input while
    MCP binds, no beachball for 25–90 s, `/health` answers first (`OPERATOR_BRIEFING.draft.md`
    §4).
19. **agent-chat** — Ask the assistant to place, confirm or execute a trade → there is no order
    surface to act on: trading was removed (D81), 0 broker/order/kill/audit routes remain and all
    22 former routes 404 (`OPERATOR_BRIEFING.draft.md` §2); `DECISIONS_FOR_OPERATOR.md`
    §2.3–§2.5 are closed with the removal. unverified: the exact wording of the chat reply — no
    file read here records it.
20. **ui-panels** — Check `vysted.log` gets timestamped lines and rotates, and "Copy diagnostics"
    works → **needs a hands-on check**: `R15-LIFECYCLE-008` (high, `needs_gui`).

## 3. The public-button sequence — operator-only

Ordered as `docs/redesign/verification/r15/stage-d/RELEASE_RUNBOOK.draft.md`'s checklist, with its
commands copied exactly. The runbook assigns §0–§7 to the lead and §8–§9 (plus the licence-contact
swap) to you; the "Who" of each step is given so you can see what is yours. The runbook has **no
merge-to-main step**: §1 merges the version branch "into the release-candidate branch", and the
only `main` mention is `DECISIONS_FOR_OPERATOR.md` §2.11's optional draft PR for CI signal. unverified:
whether you intend to land this branch on `main` before or after tagging.

**0. Prerequisites (runbook §0; Who: whoever runs §3).**

```
export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH
source sidecar/.venv/bin/activate
```

**Gate.** rc gate round 2 verdict PASS at the candidate sha, confirmed at the tag (runbook
checklist, second line; §9: "Do not tag before the rc gate passes"). unverified: round 2's result.

**1. Version bump (runbook §1; Who: lead).** Merge `worktree-agent-r15-version-0.9.0` (`517da226`
bump + `c1e9164c` the single `CLAUDE.md` commit) right after the r15-rc1 tag, never before. The
runbook gives no command block; it quotes the run-state's plan: "MERGE PLAN (right after the
r15-rc1 tag): `git restore CLAUDE.md` first (the branch carries a held local hunk;
`scratchpad/claude-md-local.diff` keeps a copy), then `merge --no-ff`". Note that `git restore
CLAUDE.md` discards any uncommitted `CLAUDE.md` edit in the working tree. Then re-run the runbook
§1 `0.8.0` grep on the merged tree.

**2–5. Install, gate, build, smoke (runbook §2–§5; Who: lead).**

```
pnpm install --frozen-lockfile
```

```
pnpm ci-local
```

```
VYSTED_SKIP_DEV_SIGN=1 pnpm sidecars:build
```

```
node scripts/smoke-test-sidecars.mjs
```

**6. macOS bundle (runbook §6; Who: lead).**

```
VYSTED_SKIP_DEV_SIGN=1 pnpm tauri build
```

Without §8 the bundle is ad-hoc and unsealed: `codesign --verify --deep --strict` and
`spctl -a -t exec` both exit 1. "The dmg is not distributable until §8 runs."

**7. Clean-profile launch check (runbook §7; Who: the lead).** Command in §2 above.

**8. Signing and notarization — NEEDS-OPERATOR** (runbook §8, quoting
`DECISIONS_FOR_OPERATOR.md:133-142`; the "Why Tier-4" paragraph is omitted here):

> **Blocked:** every desktop bundle ships unsigned on macOS and Windows; a downloaded `.dmg`
> is refused by Gatekeeper as "damaged" and the NSIS installer is flagged by SmartScreen
> before the app ever opens.
>
> **Smallest unblock:** at minimum set `bundle.macOS.signingIdentity: "-"` for an ad-hoc seal
> (turns "damaged" into the Open-Anyway path) — still a `tauri.conf.json` edit, so still needs
> your sign-off even for that minimal step.

Signing is read from `tauri.conf.json` inside `pnpm tauri build`, so any signing change lands
**before** re-running §6, and §6 and §7 are both re-run afterwards (runbook §8 "Ordering note").

**Commercial-licence contact — NEEDS-OPERATOR, before §9** (runbook checklist and §9;
`DECISIONS_FOR_OPERATOR.md` §2.18): `COMMERCIAL_LICENSE.md`/`LICENSING.md` name
`commercial@vysted.com`, a domain with no MX or A record. Approve a real address and swap it into
both files before any public 0.9.0 announcement; a GitHub Release is one.

**9. Tag and GitHub release — operator-only** (runbook §9):

```
# operator runs this — <gated-sha> is the sha the rc1 gate round-2 PASS verdict names
git tag -a v0.9.0 <gated-sha> -m "v0.9.0 — <summary>"
git push origin v0.9.0
```

No release pipeline exists (runbook §9, quoting `DECISIONS_FOR_OPERATOR.md:146-152`; "Why
Tier-4" omitted):

> **Blocked:** pushing a `v*` tag produces no Release and no downloadable asset.
>
> **Smallest unblock:** approve adding `.github/workflows/release.yml` (3-OS matrix build via
> `tauri-apps/tauri-action`, `createUpdaterArtifacts: true`, `TAURI_SIGNING_PRIVATE_KEY`
> wired) so `latest.json` + `.sig` are attached; this also unblocks 2.10.

Until then a Release needs the §6 bundles attached by hand, with the promoted release notes as the
body (runbook §1b):

```
gh release create v0.9.0 --notes-file <promoted-path> <assets from §6>
```

The runbook also flags, before tagging, that CI has never run on this branch (§2.11) and that
real 3-OS signal is advisable.

**10. Windows — NEEDS-MANUAL-CHECK** (runbook §10): nobody has built or installed this branch on
Windows; the NSIS target, the three sidecars, the `windows-native` keyring backend and SmartScreen
behaviour are unverified, and Windows/Linux CI has never run here (§2.17). The runbook's marker:
"an actual Windows build + install + smoke-test run, or an explicit decision to ship 0.9.0
macOS/Linux-only pending that verification."

**11. Rollback understood before cutting** (runbook §11): no pre-D81 tag is a rollback target
(they carry the removed trading surface and the AGPL licence); rollback means pulling the Release
(`gh release delete v0.9.0`) or fixing forward on this branch. See also §5.7 in §4 below.

## 4. `DECISIONS_FOR_OPERATOR.md` items, in priority order

Source: `docs/redesign/DECISIONS_FOR_OPERATOR.md`, every `###` section (1.1–1.4, 2.1–2.21,
3.1–3.6, 4.1–4.12, 5.1–5.10), read at this head.

1. **§5.1** — AGPL-3.0/GPL packages (eight `openbb-*` packages, `sec-edgar-mcp`, `Unidecode`) ship
   inside two of the three sidecar binaries. Recommends (a): keep shipping them as separate
   programs plus a third-party notices file. Get a lawyer's read before selling the first
   commercial licence.
2. **§4.10** — `R15-LEAD-035` is `blocked_tier4` as an escalation (not a concurrence) after a
   fourth certification failure. Your call at rc1: (a) accept the residual with the verifier's
   wording, or (b) authorise one bounded round for the verifier's named guard on the rc2 line;
   the lead recommends (b). Per the briefing §4 it does not block the rc1 gate either way.
3. **§2.8** — every desktop bundle ships unsigned. Smallest unblock: `bundle.macOS.signingIdentity:
   "-"` (a `tauri.conf.json` edit needing your sign-off); a real seal needs paid Apple/Windows
   credentials.
4. **§2.18** — `commercial@vysted.com` has no MX/A record. Approve a real address before any
   public 0.9.0 announcement.
5. **§2.9** — no GitHub release pipeline; `v0.6.0`..`v0.8.0` have zero installable builds. Approve
   `.github/workflows/release.yml`.
6. **§2.10** — the auto-updater is dead end-to-end. Approve §2.9 first, then the
   `createUpdaterArtifacts` flag in `tauri.conf.json`.
7. **§5.5** — Windows is unverified for 0.9.0. Recommends (a): ship macOS artifacts only and say
   Windows is unverified; attach no Windows installer until one attended build and smoke test
   passes. Option (b): build and smoke-test on your Windows machine before the tag.
8. **§5.8** — the filing-watcher groundwork's evidence folder (41 tracked files) and its two
   tooling files are in the public tree and name a third-party package the release must not
   mention. Recommends (a): move both under the git-ignored `r15/local/` before the launch tag
   (`git rm -r --cached` plus one commit); do not rewrite pushed history.
9. **§5.4** — `CLAUDE.md` still states AGPL-3.0; fixed in `c1e9164c` on the unmerged version
   branch. Recommends (a): merge right after the tag as planned; review that Tier-1 diff first.
10. **§2.11** — CI has never run on `004-r4-experience-rebuild` (654 commits, per §2.11). Smallest
    unblock: open a draft PR (no workflow edit) after fixing the red lint run on `main`.
11. **§2.17** — Windows/Linux CI has never run on `004` (655+ commits). Approve a
    `workflow_dispatch` trigger or a draft PR.
12. **§2.6** — the same CI fact recorded at the 19 Sep pause: workflows trigger only on
    `push: main` + `pull_request`; `pnpm ci-local` is the standing gate meanwhile.
13. **§2.1** — your default provider lanes are unfunded (OpenRouter negative, DeepSeek-direct $0);
    your composer lane (`openai`/`gpt-5.6-luna`) is funded. Top up OpenRouter before hand-testing
    research depth and restart your app for the `043850c` fix (§5 below).
14. **§2.2** — Docker/OrbStack is not running, so SearXNG is down and research silently uses the
    keyless scraper. Start OrbStack before judging research (§6 below).
15. **§4.2** — the shipped default chat model (DeepSeek V4 Flash) returns `content_filter` with
    zero tool calls on portfolio-write asks. Fund OpenRouter, eval `glm-5.1` and `kimi-k2.6`,
    ship whichever passes.
16. **§4.3** — native web search off Anthropic has no per-run cap or spend meter. Needs a funded
    OpenRouter lane or a reachable Gemini/Anthropic key to verify the BudgetGuard counter.
17. **§4.1** — FAST research drops an uncached Indian name's fundamentals card on the first
    brief. Options (a) accept, (b) a ~12 s box for Indian listings, (c) show provider values
    flagged "exchange filings not yet checked"; recommends (a) for rc1 and (c) after it.
18. **§4.4** — dockview tab reorder and node-editor drag-drop have no automated coverage. Once a
    Playwright suite lands, run it in a GUI-attended session or real-display CI.
19. **§3.2** — the first-launch terms now read research-only plus a licence line. Review the exact
    copy in `src/modules/safety/DisclaimerFlow.tsx` before it ships.
20. **§2.21** — a denied/failed keychain read on first launch leaves the terms dialog and
    onboarding blank with no error (also triggered by `HOME=` isolation, §5.10). Approve a
    `catch` → `setError` on the hydrate effect.
21. **§3.1** — orphaned broker keychain secrets, the old terms ack, `audit_log.db` rows and seven
    broker plugin-store rows stay on users' disks; nothing purges them. Recommends approving a
    one-time "remove leftover broker credentials" step plus a CHANGELOG hand-delete note.
22. **§3.3** — accepted agent-write safety gaps, for your review: no durable record of agent
    writes past the 10-minute action ledger; no AUTO stop beyond rejecting a staged change or
    cancelling a Delegate run.
23. **§3.4** — Tier-1 items left untouched, your call: the `"trading-bot"` `PluginType` literal
    and Tradesa-era JSDoc in `types/plugin.ts`; the queued `CLAUDE.md` edits in
    `docs/redesign/CLAUDE_MD_PROPOSAL.md`; an optional drop of the broker-relationship clause in
    `COMMERCIAL_LICENSE.md:36-48` (no change required).
24. **§2.12** — no way to add a user-chosen MCP server. Approve a settings config surface, a Rust
    stdio spawn and the existing read-only wrapper audit on it.
25. **§2.13** — webview file writes are unconfined and CSP is null. Approve a `write_atomic`
    path-confinement helper (not Tier-4) plus a CSP value in `tauri.conf.json`.
26. **§2.14** — plugin data contribution is declaration-only. Pick (a) a `provider_registry`
    resolution seam or (b) mark `DataSource.realtime`/`subscribe` reserved in `types/plugin.ts`.
27. **§2.15** — first-party panels bypass the plugin model. Approve wrapping them as bundled
    plugins, or a recorded FR-050 re-scope.
28. **§2.16** — the design-token audit runs in no CI workflow. Approve adding its non-`--report`
    run to `lint.yml`.
29. **§2.19** — BLUEPRINT §2 and `CLAUDE.md` still name Next.js; the app ships Vite. Approve the
    queued `CLAUDE_MD_PROPOSAL.md` edit plus the BLUEPRINT §2 swap.
30. **§2.20** — plugin docs describe the retired `panels.ts`/`PLUGIN_COMPANIONS` model; the real
    mechanism is `marketplace.ts`. Approve the `CLAUDE.md` correction.
31. **§4.5–§4.8** — four CI/doc edits blocked because they touch Tier-1 files: ruff scope to
    `sidecar scripts` (§4.5), the BLUEPRINT OpenBB row (§4.6), a CLA-check workflow (§4.7),
    caching the sidecar build in CI (§4.8). Each recommends landing as written.
32. **§2.7** — GUI-rig idle time is not proof you are away. Recommends an away-sentinel file
    (`~/.vysted-rig-away`, with an expiry); not added without you.
33. **§5.2** — `frozendict` 2.4.7 (LGPL v3) is frozen into two sidecars via `yfinance`.
    Recommends (a): one notices entry.
34. **§5.3** — `r-efi` and four packages with empty licence metadata: no licence gap found.
    Acknowledge only.
35. **§5.6** — the secrets scan found nothing classed `real_or_unknown`. Re-run it at the tag sha.
36. **§5.7** — no post-D81 build exists to roll back to. Recommends (a): from this release on,
    keep each release's `.dmg` + sha256 outside the repo; do not reinstall the `com.vysted.desk`
    copy as a rollback.
37. **§5.9** — the rehearsal wrote 10 WebKit housekeeping files under your real `~/Library`
    (caches only). Clear the two named subpaths yourself if you want the earlier state.
38. **§5.10** — the rehearsal's two medium findings ride §2.21 and §2.8; no new decision.
39. **Signed off 26 Sep 04:15 IST** (`OPERATOR_BRIEFING.draft.md` §3): **§4.9, §4.11, §4.12**
    (`R15-LEAD-030`/`037`/`038`), one known-limitation class. A new instance of "the local model
    states a figure with no ok tool call behind it" files against that class, not as a fix.
40. **Done or closed, revert if you disagree:** §1.1 (`enrich_nse_sectors.py` fix committed as
    `7a1cd8f`, `git revert 7a1cd8f`), §1.2 (superseded by D81, nothing to revert), §1.3 (five
    never-pushed commits rewritten before the first push, nothing to undo on `origin`), §1.4
    (relicense to PolyForm Strict, your decision, revert by the named commit subject), §2.3–§2.5
    (closed, removed with trading, D81), §3.5 (AUTO scope back to SC-025, revertable in one
    predicate), §3.6 (Ollama context admission, revertable).

## 5. Provider top-ups: OpenRouter and DeepSeek

Source: `docs/redesign/DECISIONS_FOR_OPERATOR.md` §2.1, §4.2, §4.3; `README.draft.md` BYOK.

- **What's unfunded:** OpenRouter's paid balance is negative and DeepSeek-direct is at $0. The
  figures live in the git-ignored `r15/local/BUDGET.md` (not read for this handover). Your
  composer lane, `openai`/`gpt-5.6-luna`, is funded.
- **What you lose without it:** the keyless research default and the Tongyi fallback both ride
  the OpenRouter lane (§2.1). The default-chat-model eval (§4.2) and the native-search cap check
  (§4.3) both need a funded OpenRouter lane or another reachable key.
- **Restart your app after topping up:** your dev stack had been running since 13 Sep on
  pre-patch binaries; `043850c` repairs the gpt-5.x tool-calling 400 on your lane (§2.1).
- **Where the key goes:** entered in the frontend and stored through the Tauri
  `keychain_set`/`keychain_get`/`keychain_delete` commands (`src-tauri/src/keychain.rs`): the OS
  keychain in a release build, a git-ignored `dev-keystore.json` under the app data directory in
  a debug build only. The frontend's keychain wrapper (`src/lib/keychain.ts`) is the only path
  that touches credentials and never uses `localStorage`/`sessionStorage`/cookies
  (`README.draft.md` BYOK).

## 6. Docker and SearXNG start

Source: `docs/redesign/DECISIONS_FOR_OPERATOR.md` §2.2;
`docs/redesign/verification/r15/stage0/DOCKER_STATE.md` (recorded 23 Sep 03:44 IST);
`sidecar/services/searxng_manager.py` module docstring.

- **The one action:** start OrbStack (or Docker Desktop). DOCKER_STATE recorded `orb status` →
  `Stopped` on 23 Sep; unverified: its state now (`orb status` would verify). With a reachable
  daemon, the app's guided "Unlimited Research" flow (exposed via `routers.search_tiers`) runs
  `docker pull searxng/searxng`, starts a `vysted-searxng` container bound to loopback with a
  generated `settings.yml`, and waits until `/search?q=…&format=json` answers; states run
  `not_installed_docker` → `docker_present_not_setup` → `pulling` → `starting` → `ready` (or
  `error`). No manual `docker run` is documented.
- **What you lose without it:** `GET /search/status` reports tier `t1_keyless` and research
  silently runs on the public keyless scraper (rate-limited by nature);
  `GET /search/searxng/status` reports `not_installed_docker` with "docker CLI found but the
  daemon is not running — start Docker/OrbStack". Whether the UI surfaces this is an open census
  item (§2.2).

## 7. The pmset revert and the caffeinate release

Source: `docs/redesign/verification/vysted-r15-run-state.md` (grepped for `pmset` and
`caffeinate`); `R15_RUN_REPORT.md` and the runbook have no `pmset` mention.

- **No `pmset` setting change is recorded.** The run-state's only `pmset` fact is a read of
  `pmset -g log` at 04:01 IST Fri 25 Sep, used to confirm that an isolated stack and caffeinate
  `47158` died with no sleep event (run-state line 33). There is no revert on record. Check with
  `pmset -g` yourself.
- **Caffeinate, as recorded:** armed at the start as PID `52012` (`caffeinate -dimsu -t 86400`,
  run-state Stage 0 facts); released in L8 "OPERATOR-REQUESTED GRACEFUL PAUSE" ("caffeinate
  52012 released"); after the Mac slept during batch 6 (L26), re-armed with `-dimsu -t 86400`;
  at 04:01 IST Fri 25 Sep "re-armed for 48 h as pid 22698 beside 34805 (~11 h left)" (line 33;
  the "~11 h left" belongs to `34805`). No later caffeinate event is recorded. unverified: which
  caffeinate is alive now (`pgrep -fl caffeinate` would verify). A caffeinate release is planned
  as a run-ending stage of `r15/tooling/final-pass.js` (line 63), which runs after `r15-rc3`; no
  `r15-*` tag exists at this head.

## 8. Where everything lives

| What | Path |
|---|---|
| Defect register (use the JSON's `counts`/`entries`; `register.py status` lags) | `docs/redesign/verification/vysted-r15-register.json` (+ `.md`) |
| Gate sheets | `docs/redesign/verification/R15_GATE_RC1.md`; `docs/redesign/verification/r15/rc1/` (`VERDICT.md`, `FINDINGS.md`, `GATE8.md`, `refutation-audit/`) |
| Run report / run state / run log | `docs/redesign/verification/R15_RUN_REPORT.md`; `docs/redesign/verification/vysted-r15-run-state.md`; `docs/redesign/verification/R15_RUN_LOG.md` |
| Operator decisions | `docs/redesign/DECISIONS_FOR_OPERATOR.md`; `docs/redesign/DECISIONS.md` (D-numbers); `docs/redesign/verification/r15/stage-d/OPEN_QUESTIONS.md` |
| Stage D drafts and scans (this file included) | `docs/redesign/verification/r15/stage-d/` |
| Promotion targets (`STAGE_D_INDEX.md` "How to promote at rc2") | `README.draft.md` → `README.md`; `RELEASE_RUNBOOK.draft.md` → `docs/RELEASE_RUNBOOK.md`; `OPERATOR_BRIEFING.draft.md` → `docs/redesign/OPERATOR_BRIEFING.md`; `RELEASE_NOTES.draft.md` → the GitHub release body + `CHANGELOG.md`'s `v0.9.0` section; `CURRENT_STATE.draft.md` → `docs/CURRENT_STATE.md`; `BLOCKERS.draft.md` → `BLOCKERS.md`. None is listed for this file. |
| Stage C fix batches | `docs/redesign/verification/r15/stage-c/batch-<2..24>/` (`PLAN.md`, `VERDICTS.md`; batch-23 adds `LEAD-030-CONCURRENCE.md`, `DISPOSITION-CONCURRENCE.md`; batch-24 adds `LEAD-035-CONCURRENCE.md`) |
| Lows | `docs/redesign/verification/r15/stage-c/lows-triage/LOWS_TRIAGE.md`; `docs/redesign/verification/r15/stage-c/lows/PARTITION.md` |
| The four named areas | `docs/redesign/verification/r15/NAMED_LISTS.md` |
| Per-batch history | `CHANGELOG.md`: trading removal, batches 2–17 and rc1 gate round 1; batches 18–24 have no section yet (`OPERATOR_BRIEFING.draft.md` §6) |

<!-- critic-footer -->
