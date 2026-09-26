<!-- DRAFT written 06:54 IST 26 Sep by the Stage D burst-window handover writer, head `6bc6d378cbbf9cfbefd8d155e027c2dc80214331` on `004-r4-experience-rebuild`. Promoted at the rc1 tag by the lead. -->

# Operator handover — Vysted Terminal, R15 "LAUNCH"

Reader: you, cold, after weeks away. You do not need to remember what this product is or what
this run did — everything below cites the file it came from, opened at this head.

## 1. What this is

Vysted Terminal is a desktop finance terminal: a Tauri (Rust) core, a Vite + React 19 webview,
and a Python FastAPI sidecar that talks to `127.0.0.1` only — a multi-panel market cockpit
(chart, watchlist, news, portfolio, screener, macro, SEC filings, a node-editor/workflow
surface) paired with an AI copilot that can read data and act on the terminal, bring-your-own-keys
for every provider (`docs/redesign/verification/r15/stage-d/README.draft.md`, Overview and BYOK
sections). R15 "LAUNCH" is an autonomous run that census'd every promised or discovered defect
against the running app, fixed them in batches, and gated the result for a release
(`docs/redesign/verification/r15/stage-d/OPERATOR_BRIEFING.draft.md` §1).

What changed in R15, in five lines (`OPERATOR_BRIEFING.draft.md` §1, §2; `RELEASE_NOTES.draft.md`
Part A/B):

- Trading was removed from the product **permanently** (D81) — no broker connection, order
  placement, paper/live account or kill switch anywhere; your own tracked portfolio (manual
  holdings, cost basis, P&L, CSV export) stays and is unaffected.
- The core relicensed from AGPL-3.0 to **PolyForm Strict 1.0.0** + a commercial license; the
  plugin contract and example plugin stay Apache-2.0.
- A register of 887 raw findings closed to **652 entries** (16 critical / 116 high / 293 medium /
  227 low); as of this head, **391 are fixed and open critical/high/medium is zero** — everything
  else open is a low-severity item pending integration, or one of 26 `blocked_tier4` items that
  are yours to decide (§4 below).
- One class of agent-chat defects (a keyless local model can fabricate a figure or a "done"
  claim with no tool result behind it) is now a documented, accepted known limitation, not an
  open bug — detailed in §2 below.
- The version bump to 0.9.0 and code-signing/release pipeline are both still pending — every
  version file at this head still reads `0.8.0` (`OPERATOR_BRIEFING.draft.md` §1), and no
  desktop bundle is signed (§3 below).

## 2. Hand-testing guide

### Launch

**Dev stack** (`OPERATOR_BRIEFING.draft.md` §5): `pnpm tauri:dev` → `pnpm tauri:mcp` →
`tauri dev --features dev-tools`; the webview itself is Vite (`pnpm dev`). `pnpm tauri:dev`'s
`beforeDevCommand` builds any missing/stale sidecar for you.

**The bundle, from a clean profile** (`RELEASE_RUNBOOK.draft.md` §7 — no dedicated env var
exists for a fresh app-data dir; the code resolves it to a fixed OS path, so isolation is done by
overriding `HOME` and launching the bundle binary directly, never via `open`):

```
HOME=<fresh dir> "<bundle>/Contents/MacOS/vysted-terminal"
```

Two caveats from the runbook's own rehearsal (`RELEASE_RUNBOOK.draft.md` §7, sha `64e9470e`, not
this head — re-confirm at the actual release-candidate sha): WKWebView is **not** isolated by
`HOME=` (it still touches your real `~/Library/WebKit/com.vysted.terminal` and
`~/Library/Caches/com.vysted.terminal` — do not delete those files, they're yours); and a
`HOME=`-isolated launch has **no default keychain at all**, so the first-launch terms dialog
never renders under this isolation — that's an artifact of the isolation method, not a pass. The
terms/keychain check needs a separate macOS user account instead (its own login keychain).

### First run and the populated anchors

`CLAUDE.md`'s "Visual verification" anchors (read-only, this project's own instructions):
watchlist `AAPL, MSFT, NVDA, SPY, QQQ, BTC/USDT, ETH/USDT`; chart SPY with indicators and VWAP;
Equity Overview AAPL; News with sentiment; Portfolio with ≥1 position and P&L. Capture dark theme
at both 1920×1080 and 2560×1440 if you screenshot anything; never overwrite an existing shot.

### Things to try (12–20, one per line: area — action → expected result)

1. **ui-panels** — Save a workspace, then load it after a panel it referenced no longer exists →
   the workspace restores your portfolios, watchlist and notes intact instead of rolling back to
   an older blob (`RELEASE_NOTES.draft.md` "What changed for you"; `NAMED_LISTS.md` §UI-and-panels
   lists the old failure, `R15-CODE-FRONTEND-001`, as critical, `fixed` per the register).
2. **ui-panels** — Pick a ticker from the command palette (Cmd/Ctrl-K) → it loads straight into
   the chart (`RELEASE_NOTES.draft.md` "What changed for you").
3. **ui-panels** — Draw a trendline on a chart, switch symbol and timeframe, then switch back →
   the drawing is still scoped correctly, not duplicated or bled onto the wrong symbol
   (`RELEASE_NOTES.draft.md` Fixed › Charts, watchlist & portfolio).
4. **ui-panels** — Export CSV from Watchlist or Portfolio on the packaged app →
   **needs a hands-on check**: `R15-UI-009` is `needs_gui` in the register (`FACTS.md` §Register);
   no automated tool can drive the native save dialog.
5. **ui-panels** — Try placing/locking a drawing, or the Text label tool, on the chart → also
   **needs a hands-on check**: `R15-UI-022` is `needs_gui`, and per `CLAUDE.md`'s own gotcha this
   needs native event injection, not chrome-devtools.
6. **agent-chat** — With the keyless default local model (Ollama, `llama3.1:8b`), ask for a price
   on a company the model has not just looked up in the same turn → **known limitation**
   (`R15-LEAD-030`, `blocked_tier4`): it can still state an invented figure as if a tool returned
   it; every shape pinned across eight fix rounds is otherwise replaced with an honest "returned
   no data" note (`OPERATOR_BRIEFING.draft.md` §3).
7. **agent-chat** — Say "Don't use any tools, except price_data, what's AAPL's price?" (a
   qualified negation) → **known limitation** (`R15-LEAD-035`, `blocked_tier4` as an escalation,
   not a concurrence — your call, §4 below): this phrasing can still strip every tool and the
   model then usually invents a price.
8. **agent-chat** — Ask the assistant to edit your portfolio while telling it not to use tools →
   **known limitation** (`R15-LEAD-038`, `blocked_tier4`): nothing is written or queued, but the
   reply can falsely claim the change was made or staged.
9. **agent-chat** — Ask the assistant (any autonomy mode) to change a portfolio position or a
   setting → it always stages for your review first; only panel/chart/watchlist changes ever
   auto-apply under AUTO (`types/proposed-change.ts:38-46`, `AUTO_APPLIED_KINDS`, cited in
   `OPERATOR_BRIEFING.draft.md` §3 fail-safe). There is no order surface left to attempt at all
   (D81) — this exercises the same fail-safe boundary the removed order-attempt halt used to.
10. **agent-chat** — On the shipped default OpenRouter model (DeepSeek V4 Flash), ask it to edit
    your portfolio → **known limitation**: can come back as a content-filter refusal with no
    action taken; switch models in Settings if you hit it (`RELEASE_NOTES.draft.md` Known
    limitations; `DECISIONS_FOR_OPERATOR.md` §4.2).
11. **research-search** — With Docker/OrbStack stopped, ask for a deep-research brief → research
    silently falls back to the keyless scraper tier; the brief is labelled `keyless-fallback`
    (`RELEASE_NOTES.draft.md` Known limitations; `DECISIONS_FOR_OPERATOR.md` §2.2).
12. **research-search** — Ask for a brief on a foreign-exchange ticker (BHP.AX, 0700.HK, 7203.T,
    VOD.L) → it now resolves instead of reading as delisted (`RELEASE_NOTES.draft.md` "What
    changed for you"; register `R15-LEAD-022` `fixed`, `sidecar/services/yfinance_provider.py`).
13. **research-search** — Ask for a brief on an Indian small-cap name you have not queried before,
    right after a fresh sidecar boot → the first FAST brief may drop the fundamentals card (a
    named, accepted rc1 budget trade-off, `rc1-battery-4:1`) — a repeat brief or the model's own
    follow-up call gets the card (`DECISIONS_FOR_OPERATOR.md` §4.1).
14. **research-search** — Trigger a native web search on a non-Anthropic provider →
    **known limitation**: no per-run cap or spend meter is enforced on that lane
    (`RELEASE_NOTES.draft.md` Known limitations; `R15-AGENT-049`, `blocked_tier4`).
15. **data-smallcaps** — Open Equity Overview for a small/obscure Indian name (e.g. DHANBANK,
    JONJUA) → ownership % now cross-checks the exchange filing instead of passing through a
    disagreeing Yahoo figure as fact (`RELEASE_NOTES.draft.md` Fixed › Fundamentals &
    disclosures).
16. **data-smallcaps** — Look up an SEC filing detail for an accession older than the issuer's
    last 40 filings → no longer fabricates `10-K filed today` with a blank company name (register
    `R15-DATA-007`, critical, `fixed`).
17. **data-smallcaps** — Look up a thinly-traded scrip (near-zero recent volume) → the 52-week
    range and quote freshness now follow the instrument's own exchange calendar instead of
    carrying forward a stale print as "today" (`RELEASE_NOTES.draft.md` Fixed › Market data;
    register `R15-DATA-035`/`R15-DATA-036`, `fixed`).
18. **ui-panels** — Cold-launch the packaged app right after a reboot → **needs a hands-on
    check**: `R15-LIFECYCLE-001` (`needs_gui`) expects the window to paint and take input while
    MCP binds, no beachball for 25–90 s, and `/health` answers first.
19. **agent-chat** — Ask the assistant to place, confirm or execute a trade of any kind →
    there is no broker/order tool anywhere in the tool catalog or routes for it to call (D81) —
    the expected result is that it cannot act on the request at all, only discuss it; this is the
    Gate 8 boundary re-proved at every rc (`OPERATOR_BRIEFING.draft.md` §7's fail-safe framing;
    `docs/redesign/DECISIONS_FOR_OPERATOR.md` §2.3–2.5, closed with the removal).
20. **ui-panels** — Check `vysted.log` for timestamped, rotating lines and that "Copy
    diagnostics" works → **needs a hands-on check**: `R15-LIFECYCLE-008` (`needs_gui`).

## 3. The public-button sequence — operator-only

Quoted and ordered exactly as `docs/redesign/verification/r15/stage-d/RELEASE_RUNBOOK.draft.md`
states it. **Note:** the runbook has no "merge to main" step of its own — releases are tagged
directly off `004-r4-experience-rebuild` once the rc gate passes; the closest thing to a
main-branch step is §9's separate, optional suggestion of opening a draft PR against `main` purely
to get 3-OS CI signal (§2.11/R15-RELEASE-004), which is not part of the tag/release flow itself.
Do not invent a merge-to-main step beyond what is below — unverified: whether you intend to also
land this branch on `main` before or after tagging; the runbook does not say.

**0. Prerequisites (runbook §0).**

```
export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH
source sidecar/.venv/bin/activate
```

**1. Merge the version-bump branch, right after the r15-rc1 tag, never before (runbook §1,
quoting the tracked run-state's own MERGE PLAN note).**

```
git restore CLAUDE.md
git merge --no-ff worktree-agent-r15-version-0.9.0
```

`worktree-agent-r15-version-0.9.0` carries two commits — `517da226` (the version bump to
0.9.0) and `c1e9164c` (the single CLAUDE.md commit) — not yet merged at this head. **NEEDS-MANUAL-CHECK** (runbook §1): re-run the bump's own verification grep once merged, in case a
later commit added a new `0.8.0` occurrence upstream.

**rc gate round 2 must show PASS at the candidate sha before any of the rest of this section
runs** (runbook checklist item; §9: "Do not tag before the rc gate passes"). Confirm the verdict
and sha at the tag — unverified here: round 2's result, since it was still in flight at this
head (`OPERATOR_BRIEFING.draft.md` §1).

**2–5. Install, gate, build (runbook §2–§5).**

```
pnpm install --frozen-lockfile
pnpm ci-local
VYSTED_SKIP_DEV_SIGN=1 pnpm sidecars:build
node scripts/smoke-test-sidecars.mjs
```

**6. Build the macOS bundle (runbook §6).**

```
VYSTED_SKIP_DEV_SIGN=1 pnpm tauri build
```

Produces `.app`/`.dmg` under `src-tauri/target/release/bundle/`. **The bundle is not
distributable until §8 (signing) runs** — ad-hoc/unsealed at this point, `codesign --verify` and
`spctl -a -t exec` both fail (runbook §6).

**7. Clean-profile launch check — the lead, not this handover, per the runbook's own scope note
("The macOS production build is proven from a clean profile later by the lead").** Command is
in §2 above.

**8. Signing and notarization — NEEDS-OPERATOR** (runbook §8, quoting
`DECISIONS_FOR_OPERATOR.md:133-142` verbatim):

> **Blocked:** every desktop bundle ships unsigned on macOS and Windows; a downloaded `.dmg` is
> refused by Gatekeeper as "damaged" and the NSIS installer is flagged by SmartScreen before the
> app ever opens.
>
> **Smallest unblock:** at minimum set `bundle.macOS.signingIdentity: "-"` for an ad-hoc seal
> (turns "damaged" into the Open-Anyway path) — still a `tauri.conf.json` edit, so still needs
> your sign-off even for that minimal step.

Any signing change must land in `tauri.conf.json` **before** re-running §6/§7 — signing happens
inside `pnpm tauri build` itself, not as a separate step against an already-built bundle (runbook
§8 "Ordering note").

**Before this step: NEEDS-OPERATOR — commercial-license contact** (runbook §1b/§9, quoting
`DECISIONS_FOR_OPERATOR.md:230-236`): `COMMERCIAL_LICENSE.md`/`LICENSING.md` name
`commercial@vysted.com`, a domain with no MX or A record — approve a real address and swap it into
both files before any public 0.9.0 announcement, since a GitHub Release is one.

**9. Tag and GitHub release — operator-only** (runbook §9):

```
# operator runs this — <gated-sha> is the sha the rc1 gate round-2 PASS verdict names
git tag -a v0.9.0 <gated-sha> -m "v0.9.0 — <summary>"
git push origin v0.9.0
```

**No release pipeline exists yet** — quoting `DECISIONS_FOR_OPERATOR.md:146-152` verbatim:

> **Blocked:** pushing a `v*` tag produces no Release and no downloadable asset.
>
> **Smallest unblock:** approve adding `.github/workflows/release.yml` (3-OS matrix build via
> `tauri-apps/tauri-action`, `createUpdaterArtifacts: true`, `TAURI_SIGNING_PRIVATE_KEY` wired)
> so `latest.json` + `.sig` are attached; this also unblocks the auto-updater (§2.10).

Until that workflow exists and is approved, pushing the tag alone produces nothing downloadable;
a Release (if you want one now) needs the §6 bundles attached by hand:

```
gh release create v0.9.0 --notes-file <promoted-RELEASE_NOTES-path> <assets from §6>
```

**10. Windows — NEEDS-MANUAL-CHECK** (runbook §10): nobody has verified a Windows build or
install of this branch — the NSIS target, the three PyInstaller sidecars, the `windows-native`
keyring backend and SmartScreen behaviour are all unverified. Windows/Linux CI has never run on
this branch at all (§2.17). Runbook's own marker: "an actual Windows build + install + smoke-test
run, or an explicit decision to ship 0.9.0 macOS/Linux-only pending that verification."

## 4. `DECISIONS_FOR_OPERATOR.md` items, in priority order

Source: `docs/redesign/DECISIONS_FOR_OPERATOR.md`, all sections, read at this head.

1. **§5.1** — AGPL-3.0/GPL packages (openbb-core + 7 others, sec-edgar-mcp, Unidecode) ship
   inside two of the three sidecar binaries. Recommends: (a) keep shipping as separate processes
   plus a third-party notices file (cheapest, defensible). Blocks on: a lawyer's read of whether
   bundling AGPL programs next to the commercially-licensed core needs more than notices, before
   you sell the first commercial license.
2. **§4.10** — `R15-LEAD-035`'s residual is now `blocked_tier4` as an escalation (not a
   concurrence) after a fourth certification failure. Recommends: (b), authorise one more bounded
   fix round for the verifier's named guard on the rc2 line. Blocks on: your (a) accept-as-is vs
   (b) one-more-round choice; not blocking the rc1 gate either way.
3. **§2.8** — every desktop bundle ships unsigned (Gatekeeper/SmartScreen block installs).
   Recommends: at minimum set `bundle.macOS.signingIdentity: "-"` for an ad-hoc seal. Blocks on:
   your sign-off on the `tauri.conf.json` edit, plus paid Apple/Windows signing credentials for a
   real seal.
4. **§2.9** — no GitHub release pipeline; `v0.6.0`..`v0.8.0` have zero installable builds.
   Recommends: approve `.github/workflows/release.yml` (3-OS tauri-action matrix,
   `createUpdaterArtifacts: true`). Blocks on: your sign-off (`.github/` is Tier-1).
5. **§2.10** — the auto-updater is dead end-to-end. Recommends: approve §2.9 first, then the
   `tauri.conf.json` `createUpdaterArtifacts` flag. Blocks on: §2.9 landing first.
6. **§2.11** — CI has never run on `004-r4-experience-rebuild` (655+ commits with zero cross-OS
   signal). Recommends: open a draft PR against `main` (no workflow edit needed) after fixing the
   red lint run on `main`. Blocks on: your process decision to open that PR.
7. **§2.18** — the commercial-license contact `commercial@vysted.com` has no MX/A record.
   Recommends: approve a real contact address before any public 0.9.0 announcement. Blocks on:
   you owning a real inbox.
8. **§5.4** — `CLAUDE.md` still says AGPL-3.0; already fixed on the unmerged version branch
   (`c1e9164c`). Recommends: (a) merge it right after the tag, as already planned. Blocks on:
   your review of that Tier-1 diff before the merge.
9. **§5.5** — Windows is entirely unverified for 0.9.0. Recommends: (a) ship macOS/Linux only and
   say so; do not attach a Windows installer until one real build+smoke-test passes. Blocks on:
   your sign-off to ship without Windows, or your own Windows build before the tag.
10. **§5.8** — the filing-watcher groundwork's evidence folder and two tooling files (41 tracked
    files, naming a banned third-party term) are still in the public tree. Recommends: (a) move
    both under the git-ignored `r15/local/` before the launch tag, via `git rm -r --cached` plus
    one commit. Blocks on: your one-line go-ahead.
11. **§2.1** — your default provider lanes are unfunded (OpenRouter negative, DeepSeek-direct
    $0); your composer lane (`openai`/`gpt-5.6-luna`) is funded. Recommends: top up OpenRouter
    before hand-testing research depth, and restart your dev stack for the `043850c` tool-calling
    fix. Blocks on: you funding the lane.
12. **§2.2** — Docker/OrbStack isn't running, so SearXNG is down and research silently uses the
    keyless scraper. Recommends: start OrbStack before judging research. Blocks on: you starting
    it (see §5 below).
13. **§4.2** — the shipped default chat model (DeepSeek V4 Flash) returns `content_filter` with
    no tool calls on portfolio-write asks. Recommends: fund OpenRouter, eval `glm-5.1` and
    `kimi-k2.6`, ship whichever passes. Blocks on: a funded lane to re-run the eval.
14. **§4.3** — native web search off Anthropic has no per-run cap or spend meter. Recommends:
    fund OpenRouter or supply a reachable Gemini/Anthropic key, then verify the counter lands in
    BudgetGuard. Blocks on: a funded/reachable lane to exercise it live.
15. **§4.4** — dockview tab reorder and node-editor drag-drop have no automated coverage (trusted
    events chrome-devtools can't synthesize). Recommends: once a Playwright suite lands, run it
    in a GUI-attended session or real-display CI. Blocks on: your call on standing up that e2e
    runner.
16. **§2.7** — GUI-rig idle time isn't proof you're away. Recommends: an away-sentinel file
    (`~/.vysted-rig-away`, with an expiry) you create when you leave. Blocks on: your go-ahead —
    not added yet, because it would make every unattended run refuse until you know about it.
17. **§2.12** — no way to add a user-chosen MCP server. Recommends: approve a settings config
    surface + Rust stdio spawn + the existing read-only wrapper audit. Blocks on: a core-
    architecture sign-off (Tier-4).
18. **§2.13** — webview file writes are unconfined and CSP is null. Recommends: approve a
    `write_atomic` path-confinement helper (non-Tier-4) plus a CSP value in `tauri.conf.json`
    (Tier-4). Blocks on: the `tauri.conf.json` half needing your sign-off.
19. **§2.14** — plugin data contribution is declaration-only; no data plugin can actually serve a
    quote. Recommends: pick (a) a resolution seam, or (b) mark the field reserved in
    `types/plugin.ts` + docs. Blocks on: a `types/plugin.ts` contract decision (Tier-1).
20. **§2.15** — first-party panels bypass the plugin model entirely. Recommends: approve either
    wrapping them as bundled plugins, or a recorded spec re-scope. Blocks on: a core-architecture
    call.
21. **§2.16** — the design-token audit runs in no CI workflow. Recommends: approve adding it
    (non-`--report`) to `lint.yml`. Blocks on: a `.github/` edit sign-off.
22. **§2.17** — Windows/Linux CI has never run on `004` at all. Recommends: a `workflow_dispatch`
    trigger, or a draft PR (same fix as §2.11). Blocks on: your process/workflow decision.
23. **§2.19** — docs still say Next.js; the app has shipped Vite since D6. Recommends: land the
    already-queued `CLAUDE_MD_PROPOSAL.md` edit plus the BLUEPRINT.md §2 swap. Blocks on: your
    sign-off (both are Tier-1).
24. **§2.20** — plugin docs describe the retired `panels.ts`/`PLUGIN_COMPANIONS` model; the real
    mechanism is `marketplace.ts`. Recommends: approve the `CLAUDE.md` correction (the rest can
    land independently). Blocks on: your Tier-1 sign-off.
25. **§2.21** — a denied/failed keychain read on first launch leaves the terms dialog and
    onboarding permanently blank with no error (also fires under `HOME=` isolation, §5.10).
    Recommends: approve a `catch` → `setError` on the hydrate effect. Blocks on: sign-off on the
    first-launch disclaimer surface.
26. **§3.1** — orphaned broker secrets/audit history left on a user's disk after upgrade; nothing
    purges them automatically. Recommends: approve a one-time "remove leftover broker
    credentials" step plus a CHANGELOG hand-delete note. Blocks on: your approval — deleting a
    user's secrets automatically is irreversible.
27. **§3.2** — the first-launch terms wording changed to research-only + a license line.
    Recommends: review the exact copy in `src/modules/safety/DisclaimerFlow.tsx` before it ships.
    Blocks on: your read of that copy.
28. **§3.4** — `types/plugin.ts`'s `"trading-bot"` `PluginType` literal and Tradesa-era JSDoc
    examples were left untouched by the removal. Recommends: no default given; your call whether
    to keep them as historical precedent or strip them (a contract change). Blocks on: your
    decision on the Tier-1 file.
29. **§4.5–§4.8** — four small CI edits blocked purely because they touch `.github/` (ruff scope
    widened to `sidecar scripts`; a BLUEPRINT/OpenBB doc correction; a CLA-check workflow; caching
    the sidecar-build step). Recommends: approve all four as written — each cites its own
    low/no-risk rationale. Blocks on: Tier-1 sign-off on each workflow file.
30. **§5.2** — `frozendict` 2.4.7 (LGPL v3) is frozen into two sidecar binaries, pulled in only
    via `yfinance`. Recommends: (a) one notices entry, unmodified + replaceable via the public
    build recipe. Blocks on: your acknowledgement.
31. **§5.3** — `r-efi` and four packages with empty PyPI license metadata: no real gap found
    (their shipped license files are permissive). Recommends: no action beyond listing them in
    the notices file. Blocks on: your acknowledgement only.
32. **§5.6** — the secrets scan found nothing classed `real_or_unknown`. Recommends: no action;
    re-run the same scan at the tag sha. Blocks on: your acknowledgement only.
33. **§5.7** — there is no post-D81 build to roll back to yet; every pre-D81 tag still carries the
    removed trading surface and the old AGPL license. Recommends: (a) from this release on, keep
    each release's `.dmg` + sha256 outside the repo as the next release's rollback target. Blocks
    on: your acknowledgement of the process.
34. **§5.9** — a bundle rehearsal wrote 10 WebKit housekeeping files under your real
    `~/Library/WebKit` and `~/Library/Caches` (caches only, no LocalStorage/IndexedDB touched).
    Recommends: clear those two specific subpaths yourself if you want pre-rehearsal state; WebKit
    recreates them. Blocks on: nothing except whether you want that cache clear.
35. **§5.10** — the rehearsal's two medium findings (terms-dialog skip under `HOME=` isolation;
    unsealed ad-hoc `.app`) are dispositioned as duplicates of §2.21 and §2.8 respectively, not
    new defects. No new decision needed.
36. **Closed / superseded / already-done-and-revertable, one line:** §1.1 (the sacred
    `enrich_nse_sectors.py` fix, committed `7a1cd8f`, revertable), §1.2 (superseded by D81, nothing
    to revert), §1.3 (five never-pushed commits rewritten pre-first-push, nothing to undo on
    `origin`), §1.4 (relicense to PolyForm Strict, your prior decision, revertable by commit
    subject), §2.3–§2.5 (kill switch / paper-live switch / position limits — all closed, removed
    with trading, D81), §2.6 (CI never run on `004`; local `pnpm ci-local` is the standing gate),
    §3.3 (accepted agent-write safety gaps — no durable write record past a 10-minute ledger, no
    AUTO stop beyond reject/cancel — documented, not silently dropped), §3.5–§3.6 (AUTO scope
    tightened to SC-025, and Ollama context admission — both done and revertable in one predicate
    each), §4.9/§4.11/§4.12 (`R15-LEAD-030`/`037`/`038` — already accepted by you as one
    known-limitation class, no further action unless you want to reopen).

## 5. Provider top-ups: OpenRouter and DeepSeek

Source: `docs/redesign/DECISIONS_FOR_OPERATOR.md` §2.1; the run-state header line 4
(register/BUDGET pointers).

- **What's unfunded:** OpenRouter's paid balance is negative, and DeepSeek-direct is at $0
  (figures live in the git-ignored `r15/local/BUDGET.md` — not read by this handover, per the
  off-lane read-ban). Your composer lane, `openai`/`gpt-5.6-luna`, is funded.
- **What the app can't do without it:** the keyless research default and the Tongyi fallback both
  ride the OpenRouter lane — deep research quality degrades to the keyless-fallback tier without
  it (§2.2 below compounds this if Docker is also down). The shipped default chat model eval
  (§4.2) and the native-web-search cap fix (§4.3) both also need a funded OpenRouter lane, or
  another reachable key, to verify.
- **Restart your dev stack after topping up:** it has been running on pre-patch binaries;
  `043850c` fixes a gpt-5.x tool-calling 400 specifically on your composer lane.
- **Where the key goes:** entered in the frontend, stored via the Tauri `keychain_set`/
  `keychain_get`/`keychain_delete` commands (`src-tauri/src/keychain.rs`) — the OS keychain in a
  release build, never a file (`README.draft.md` BYOK section). Settings is the only UI surface
  that touches it; it is never written to `localStorage`/`sessionStorage`/a file in a release
  build.

## 6. Docker and SearXNG start

Source: `docs/redesign/DECISIONS_FOR_OPERATOR.md` §2.2; `docs/redesign/verification/r15/stage0/DOCKER_STATE.md`; `sidecar/services/searxng_manager.py` (module docstring).

- **The command:** start OrbStack (or Docker Desktop) itself — there is no separate manual
  `docker run`/`docker compose` step for you to type. Once a docker daemon is reachable, the
  sidecar's own guided "Unlimited Research" setup in Settings drives the rest itself: it runs
  `docker pull searxng/searxng`, starts a `vysted-searxng` container bound to loopback with a
  generated config, and polls it until `/search?...&format=json` answers — a small state machine
  (`not_installed_docker` → `docker_present_not_setup` → `pulling` → `starting` → `ready`) exposed
  via `routers/search_tiers`, entirely inside the app.
- **What's lost without it:** the sidecar reports `t1_keyless` (`GET /search/status`) and research
  silently runs on the public keyless scraper tier (rate-limited by nature) instead of your own
  unlimited local instance; `GET /search/searxng/status` reports `not_installed_docker` with the
  detail "docker CLI found but the daemon is not running — start Docker/OrbStack." Whether the UI
  itself surfaces this to you is an open census item (§2.2).

## 7. The pmset revert and the caffeinate release

Source: grepped in `docs/redesign/verification/vysted-r15-run-state.md` and
`docs/redesign/verification/R15_RUN_REPORT.md` (the runbook has no `pmset`/`caffeinate` mentions
at all).

- **No `pmset` setting change is recorded anywhere in this run.** The only `pmset` reference on
  disk is a read of `pmset -g log` used once, at 04:01 IST Fri 25 Sep, to confirm an isolated
  sidecar stack had died from no sleep event (run-state line 33) — that is a diagnostic read, not
  a system-settings change, and there is no revert to perform. **Check:** run `pmset -g` yourself
  to see your machine's actual current power settings; nothing in this run should have touched
  them.
- **Caffeinate, as recorded on disk:** the run started with `caffeinate -dimsu -t 86400` as PID
  `52012` (run-state, Stage 0 facts, "Caffeinate armed: PID 52012"). Since then the loop log
  records it being released and re-armed multiple times as the run paused and resumed — e.g. an
  operator-requested pause released PID `52012` (run-state, "OPERATOR-REQUESTED GRACEFUL PAUSE" —
  "caffeinate 52012 released"); a later Mac sleep event killed a caffeinate process, which was
  re-armed with `-dimsu -t 86400` (run-state, "batch 6" entry); and a housekeeping pass at 04:01
  IST Fri 25 Sep re-armed it for 48h as PID `22698` "(~11h left)" at that time (run-state line
  33). No later re-arm event is recorded on disk as of this head's burst-window entry, so the
  **live PID and remaining time are unverified here** — check with `ps -p <pid> -o etime,command`
  against whatever PID your session shows, or just run `caffeinate -dimsu -t 86400 &` yourself if
  you don't see one running. A caffeinate **release** (not a re-arm) is written into the
  as-yet-unrun `final-pass.js` plan as one of its planned run-ending steps (run-state, "TAIL
  SCRIPT AUTHORING" entry) — that script has not executed at this head, so no release from that
  step has happened yet either.

## 8. Where everything lives

| What | Path |
|---|---|
| Defect register (counts authoritative; `register.py status` lags) | `docs/redesign/verification/vysted-r15-register.json` (+ `.md`) |
| Gate sheets | `docs/redesign/verification/R15_GATE_RC1.md`; `docs/redesign/verification/r15/rc1/` (`VERDICT.md`, `FINDINGS.md`, `GATE8.md`, `refutation-audit/`) |
| Run report / run state / run log | `docs/redesign/verification/R15_RUN_REPORT.md`; `docs/redesign/verification/vysted-r15-run-state.md`; `R15_RUN_LOG.md` |
| This run's operator decisions | `docs/redesign/DECISIONS_FOR_OPERATOR.md` (all Tier-4 items); `docs/redesign/DECISIONS.md` (D-numbers); `docs/redesign/verification/r15/stage-d/OPEN_QUESTIONS.md` (operator-only subset) |
| Stage D drafts (this file included) | `docs/redesign/verification/r15/stage-d/` — `README.draft.md`, `RELEASE_RUNBOOK.draft.md`, `OPERATOR_BRIEFING.draft.md`, `RELEASE_NOTES.draft.md`, `CURRENT_STATE.draft.md` + `BLOCKERS.draft.md`, `FACTS.md`, `DEPS_LICENCES.md`, `SECRETS_SCAN.md`, `LICENCE_CHECK.md`, `STAGE_D_INDEX.md` |
| Where Stage D drafts get promoted (`STAGE_D_INDEX.md` "How to promote at rc2") | `README.draft.md` → `README.md`; `RELEASE_RUNBOOK.draft.md` → `docs/RELEASE_RUNBOOK.md`; `OPERATOR_BRIEFING.draft.md` → `docs/redesign/OPERATOR_BRIEFING.md`; `RELEASE_NOTES.draft.md` → the GitHub release body + `CHANGELOG.md`'s `v0.9.0` section; `CURRENT_STATE.draft.md` → `docs/CURRENT_STATE.md`; `BLOCKERS.draft.md` → `BLOCKERS.md`. This file (`OPERATOR_HANDOVER.draft.md`) is promoted the same way, by the lead, at the rc1 tag, per this run's task brief. |
| Stage C fix batches | `docs/redesign/verification/r15/stage-c/batch-<2..24>/` (`PLAN.md`, `VERDICTS.md`; batch-23/24 also carry `LEAD-030-CONCURRENCE.md`/`LEAD-035-CONCURRENCE.md`) |
| Lows (low-severity backlog) | `r15/stage-c/lows-triage/LOWS_TRIAGE.md`; `r15/stage-c/lows/PARTITION.md` |
| The four named operator areas (ui-panels, agent-chat, research-search, data-smallcaps) | `docs/redesign/verification/r15/NAMED_LISTS.md` |
| Per-batch history | `CHANGELOG.md` (trading removal + batches 2–17 + rc1 gate round 1 have full sections; batches 18–24 do not yet, per `RELEASE_NOTES.draft.md`'s own VERIFY note) |

<!-- critic-footer -->
