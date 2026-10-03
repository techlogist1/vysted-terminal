# Operator Briefing - R15 "LAUNCH" (0.9.0)

True at the launch tag `1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056` (tags `r15-rc2` and `r15-launch`); register and docs read at `4b460027` (docs-only commits on top of the launch tag, where R15-LEAD-143 and R15-LEAD-144 were filed).

## 1. Outcome

Vysted Terminal 0.9.0 is ready for you to publish, with two honest caveats. R15 was an autonomous run that audited the whole product, filed 803 defect entries, and fixed 629 of them; it also removed trading from the product for good (D81) and relicensed the core to PolyForm Strict 1.0.0 plus a commercial licence, with the plugin contract and example plugin staying Apache-2.0. No critical or high entry is open: R15-LEAD-116 (the explicit `FOCUS.BO` pin served the NSE company's feed) is fixed, the boot bug R15-LEAD-123 (a data engine that binds late left the session stuck in a failed state) is fixed and certified, and R15-LEAD-127 (a sibling of R15-DATA-002 on the research/copilot data-fetch path — a bare collision ticker served the wrong region's company in a brief or MCP result) was found by the final adversarial pass and fixed and certified before this tag.

Final adversarial pass summary: a fresh-context Opus 5.5 pass (battery/drive lanes plus a cross-adversarial keyless + real-user round) admitted 58 new register entries after rc1 (`R15-FINAL-001..038`, `R15-LEAD-125..144`). Every admitted critical and high was fixed and certified by a fresh verifier before this tag: R15-LEAD-127 at `stage-c/lead127/VERIFY.md`; R15-FINAL-001..008 at `fix-r1` (26 certified, 2 not certified first pass) and `rc2-round2`; R15-LEAD-136 at `rc2-round3`; R15-LEAD-137 and R15-LEAD-141 at the rc2 fail-safe round. New mediums and lows are filed for 0.9.1. A carry-forward judge then re-checked every passing final-pass observation against the launch-head code (`final-pass/CARRY_FORWARD_launch.md`): 26 carried, 30 already re-proved, 4 freshly rerun — all 4 held (`final-pass/rerun-launch/RERUN.md`). The pass's GUI half was **not tested** at the launch head (`DECISIONS_FOR_OPERATOR.md` 5.15) — this is why the fresh-install, upgrade and GUI-check items in section 6 below are yours to run, not a gap anyone glossed over.

43 medium and 72 low entries are open and filed for 0.9.1 (115 in all). 4 entries are awaiting a human click-through on the packaged app (down from 5 — R15-LIFECYCLE-001, the boot-freeze item, is now fixed), and 35 wait on decisions that only you can make (money, identity, Tier-1 files, or the signed-off local-model limitation).

The two caveats: the build is unsigned and not notarized, so another Mac refuses it until you sign it (step 3 below); and nothing about Windows has been verified (`WINDOWS_MANUAL_CHECK.md`). The production bundle is built from `1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056` as `Vysted Terminal_0.9.0_aarch64.dmg`, 228,480,607 bytes, sha256 `9940d41b7ed6725aaabb6bb1709dc48b4f8ec51facd0696e376c68401139bc53`.

## 2. Public-button sequence

These are the operator-only steps, in order. None of them has been run by an agent. The run did one preparatory thing for step 4: it created the **draft** release `v0.9.0` (unpublished, no tag created; URL `https://github.com/techlogist1/vysted-terminal/releases/tag/untagged-aa0651ce8e3deed21db2`, visible only to repo writers) with the **unsigned** dmg attached. No agent pushes to `main`, creates a `v*` tag, signs, or publishes.

1. **Merge `004-r4-experience-rebuild` to `main`, with a merge commit.** This also gives the 3-OS CI its first ever signal on the branch (R15-RELEASE-004). Full command sequence: `docs/RELEASE_RUNBOOK.md` section 9a.
   ```sh
   git checkout main && git pull origin main
   git merge --no-ff 004-r4-experience-rebuild -m "Merge 004-r4-experience-rebuild: R15 LAUNCH, Vysted Terminal 0.9.0"
   git push origin main
   ```
2. **Tag `v0.9.0` on the merge commit** (never bare `HEAD` from before the merge; the code the final gate evaluated is `1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056`, which the merge commit now contains on `main`).
   ```sh
   git tag -a v0.9.0 -m "v0.9.0 - R15 LAUNCH: trading removed, PolyForm Strict + commercial licence, audit and fix pass"
   git push origin v0.9.0
   ```
3. **Sign and notarize the dmg.** Build from the tagged sha with your Apple credentials in the environment (the next section says what they are), then verify.
   ```sh
   git checkout v0.9.0
   pnpm install --frozen-lockfile
   VYSTED_SKIP_DEV_SIGN=1 node scripts/ensure-all-sidecars.mjs --force
   APPLE_SIGNING_IDENTITY="Developer ID Application: <your name> (<TEAMID>)" \
   APPLE_ID="<apple id email>" APPLE_PASSWORD="<app-specific password>" APPLE_TEAM_ID="<TEAMID>" \
   VYSTED_SKIP_DEV_SIGN=1 pnpm tauri build
   codesign -dv --verbose=4 "src-tauri/target/release/bundle/macos/Vysted Terminal.app"
   spctl -a -vv "src-tauri/target/release/bundle/macos/Vysted Terminal.app"
   xcrun stapler validate "src-tauri/target/release/bundle/dmg/Vysted Terminal_0.9.0_aarch64.dmg"
   shasum -a 256 "src-tauri/target/release/bundle/dmg/Vysted Terminal_0.9.0_aarch64.dmg"
   ```
   Keep `VYSTED_SKIP_DEV_SIGN=1` set for this build too: it only skips the lead's local self-signed dev-signing identity on the three inner sidecar binaries (`docs/RELEASE_RUNBOOK.md` section 4) — unrelated to your Developer ID signing of the outer `.app`/`.dmg`, which `pnpm tauri build` applies itself by reading `APPLE_SIGNING_IDENTITY` (or `bundle.macOS.signingIdentity` in `src-tauri/tauri.conf.json`, a Tier-1 file, not set at this sha). Omitting the env var here would dev-sign the sidecar binaries with the lead's local cert, which is never meant to ship. The current unsigned reference numbers are 228,480,607 bytes / sha256 `9940d41b7ed6725aaabb6bb1709dc48b4f8ec51facd0696e376c68401139bc53` — these will change once you sign and notarize; use the fresh `shasum` output above for the release body, not these.
4. **Replace the unsigned dmg on the existing draft with the signed one.** The draft already exists (created by the run at 01:19 IST 4 Oct against `1fddb2b1`), so this is an upload, not a create:
   ```sh
   gh release upload v0.9.0 "src-tauri/target/release/bundle/dmg/Vysted Terminal_0.9.0_aarch64.dmg" --clobber
   gh release view v0.9.0 --json isDraft,assets --jq '{isDraft, assets:[.assets[]|{name,size}]}'
   ```
   GitHub stores the asset as `Vysted.Terminal_0.9.0_aarch64.dmg` (spaces become dots), so `--clobber` replaces the unsigned one by that name. Update the sha256 line in the release body (`gh release edit v0.9.0 --notes-file <edited body>`) to the signed `shasum` from step 3. If the draft was deleted, recreate it:
   ```sh
   gh release create v0.9.0 --draft --target 1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056 --title "Vysted Terminal 0.9.0" \
     --notes-file docs/redesign/verification/r15/stage-d/release/GITHUB_RELEASE_v0.9.0.md \
     "src-tauri/target/release/bundle/dmg/Vysted Terminal_0.9.0_aarch64.dmg"
   ```
   `--target` creates the draft from the exact commit the gate evaluated, before or after the tag is pushed.
5. **Publish.** Before this, get a real commercial contact address into `LICENSING.md` and `COMMERCIAL_LICENSE.md` (R15-DOCS-002: the placeholder domain has no mail records), because a published release is a public announcement.
   ```sh
   gh release edit v0.9.0 --draft=false
   ```

If you need to pull it back: `gh release delete v0.9.0` (the tag stays unless you also run `git tag -d v0.9.0 && git push origin :refs/tags/v0.9.0`).

## 3. What Apple signing and notarization need from you

An unsigned build is refused by Gatekeeper on every other Mac (it reads "damaged" or "cannot be opened"), so nobody but you can run the dmg without a workaround until it is signed and notarized. To sign and notarize you need Apple Developer Program membership (paid, yearly), a "Developer ID Application" certificate installed in your login keychain on the Mac that builds, and credentials for Apple's notary service: either an Apple ID plus an app-specific password generated at appleid.apple.com, or an App Store Connect API key. Tauri's bundler reads these from the environment: `APPLE_SIGNING_IDENTITY` (the certificate's common name, or `APPLE_CERTIFICATE` and `APPLE_CERTIFICATE_PASSWORD` to import one on CI), and for notarization either `APPLE_ID`, `APPLE_PASSWORD` and `APPLE_TEAM_ID`, or `APPLE_API_ISSUER`, `APPLE_API_KEY` and `APPLE_API_KEY_PATH`. The `APPLE_CERTIFICATE` and `APPLE_API_*` names are confirmed in `node_modules/@tauri-apps/cli/CHANGELOG.md`; the `APPLE_SIGNING_IDENTITY`, `APPLE_ID`, `APPLE_PASSWORD` and `APPLE_TEAM_ID` names are the Tauri 2 documentation's, not found in the local node_modules, so verify them against the Tauri 2 distribution guide before the build. A Windows build needs a separate paid code-signing certificate (R15-RELEASE-001, DECISIONS 2.8); the free SignPath route does not fit PolyForm Strict plus a commercial licence.

## 4. Known limitation - agent chat with a keyless local model

> ### Known limitations at rc1 — agent chat with a keyless local model
>
> Accepted by you Sat 26 Sep 04:15 IST (Tier-4 sign-off): `LEAD-030`, `LEAD-037`, `LEAD-038` ship `blocked_tier4` as one documented limitation class. `LEAD-035` now carries the SAME status
> (`blocked_tier4` as of `4c6dfe8c`, batch-24 merged `6778f892`) but for a different reason: it is an ESCALATION under your three-failure stop rule, not a fresh-verifier concurrence — batch-24's
> verifier REFUSED certification a fourth time and named a further narrowing-only fix it would certify (§4.10 below has the detail and your two options). No further filter round this release
> for the other three: a fresh "the local model states a figure with no successful tool call behind it" files against this limitation, not as a new fix. Carried verbatim into
> `RELEASE_NOTES.md`, `CURRENT_STATE.md` and this file, per your sign-off (LEAD-035's wording pending your (a)/(b) choice).
>
> - **`R15-LEAD-030`** (high, `blocked_tier4`, fresh verifier concurred in batch 23,
>   `r15/stage-c/batch-23/LEAD-030-CONCURRENCE.md`):
>   > With a keyless local model, the agent can still state an invented price or metric as if a
>   > tool had returned it when the figure is about a company no successful tool call in that turn
>   > covered — one named in the same paragraph as a company whose call succeeded (under a name the
>   > guard cannot map, or never looked up at all), or any company in a turn where no call failed or
>   > no tool was called — and a figure-less fabricated result dump or a code fence left open from
>   > an earlier round can also render, and every shape pinned in eight fix rounds is replaced by an
>   > honest "returned no data" note.
> - **`R15-LEAD-035`** (medium, `blocked_tier4` as of `4c6dfe8c` — an ESCALATION under your
>   three-failure rule, NOT a fresh-verifier concurrence like the other three; batch-24's verifier
>   REFUSED certification a fourth time; this is your call at rc1, §4.10):
>
>   > With a keyless local model, the "don't use tools" detector is a fixed phrase list: an
>   > unrecognised no-tool phrasing keeps the tools, so the agent may still read data and propose a
>   > portfolio change (always held for your review, never applied; under AUTO a watchlist or chart
>   > change does apply) and can occasionally state a price it never fetched, while a data request
>   > that qualifies a no-tool instruction after a comma or in reported speech ("Don't use any
>   > tools, except price_data …", "No tools, other than the price lookup …", "He says don't use
>   > tools, but …") still loses every tool and the agent then usually states an invented price as
>   > if fetched.
>
>   Your two options at rc1 (§4.10): (a) accept this residual as a documented known limitation
>   with the wording above, or (b) authorise one bounded round for the verifier's named guard (a
>   qualifier negative lookahead plus `(?<!says )`, which clears 3 of the 4 remaining over-matches
>   offline with 0 lost strips) on the rc2 line. **The lead recommends (b).**
>
> - **`R15-LEAD-037`** (medium, `blocked_tier4`, concurred on corrected wording):
>   > With a keyless local model, a figure the agent states for a company whose data call succeeded
>   > is not checked against that result at all, so it can give an older bar's value from the same
>   > payload as the current price (2 of 18 live runs, 5-6% off) or a figure that appears nowhere in
>   > the payload (1 of 18: ₹20,820 for a ₹2,082 stock).
> - **`R15-LEAD-038`** (medium, `blocked_tier4`, concurred):
>   > With a keyless local model, when you tell the agent not to use tools and ask for a portfolio
>   > change in the same message, it makes no call and nothing is written or queued, but its reply
>   > can say the change was made or staged for your review and can describe holdings that do not
>   > exist.
>
> Fail-safe (why this ships): `data-write` proposed changes always stage for review — AUTO only auto-applies `panel`/`chart`/`watchlist` kinds (`types/proposed-change.ts:38-46`); a narrated
> write stages nothing (no `tool_use` event); there is no `audit_orders` table any more (D81), so no order row can exist. Figure grounding by provenance
> (`sidecar/services/figure_grounding.py` + `agent_runtime._judge_clause`, `agent_runtime.py:2321`, rules 1/2a/2b/2c/3) replaces an ungrounded figure tied to an errored or never-called
> subject with an honest "returned no data" note. The rule-2c fail-safe (`agent_runtime.py:2378-2383`) fires only in a turn with an errored tool call — **a figure for a subject whose call
> succeeded is not checked at all** (LEAD-037). The shipping no-tool matcher is the closed
> `_NO_TOOL_CUE` list in `sidecar/services/planner.py` (`planner.py:136`, batch 21); batch 24 narrows it further, pending its own concurrence. Post-launch design (`DECISIONS_FOR_OPERATOR.md`
> §4.9–4.12, not built): claim grounding by field/provenance plus a structured no-data turn.

Status note (from `docs/redesign/DECISIONS_FOR_OPERATOR.md` section 4.10, outside the quoted block): the operator's ruling of 07:50 IST 26 Sep records R15-LEAD-035 as ACCEPTED, joining LEAD-030, LEAD-037 and LEAD-038 as one documented known-limitation class of the keyless local-model lane, `blocked_tier4`, with no further rounds this release.

## 5. Windows

Nobody has built or run this branch on Windows. The list of what to check on your ROG machine, with R15-CODE-AGENT-001 first, is in `WINDOWS_MANUAL_CHECK.md`.

## 6. Things only you can do

**New since the drafts were written** — these are operator-attended, no computer-use grant covers them, and none were exercised by the final adversarial pass (its GUI half was not tested at the launch head, DECISIONS 5.15):

- **A fresh install and first launch.** Download the dmg onto a clean or representative Mac, install, and launch cold. `HAND_TESTING_GUIDE.md` section 1 is written for exactly this and should be your first stop before anything else in that guide.
- **The 0.8.0-to-0.9.0 upgrade, app side.** Install 0.8.0, create some state (a watchlist, a portfolio position, a note), install 0.9.0 over it, and confirm that state survives. `HAND_TESTING_GUIDE.md` section 2 has the steps. The sidecar half of the same upgrade is proven headless (`docs/redesign/verification/r15/stage-d/upgrade-0.8.0/UPGRADE.md`: PASS — the 0.9.0 sidecar opened a data dir seeded by the 0.8.0 sidecar and no user-created object was lost or changed in meaning). The app half (installed 0.8.0 app replaced by the 0.9.0 dmg) was not tested: launching the unsigned app raised a login-keychain prompt the run must not answer (R15-LEAD-143).
- **R15-LIFECYCLE-008 and R15-UI-022, packaged-app GUI checks.** "Copy diagnostics" in Settings, and the chart drawing tools (anchor placement, Text label, Lock). `HAND_TESTING_GUIDE.md` section 3 has both.

**Everything else awaiting manual check or your decision:**

- 35 `blocked_tier4` entries and the unfunded provider lanes (DECISIONS 2.1): see `BACKLOG_0.9.1.md` section on the Tier-4 bucket.
- Awaiting manual check (4, down from 5 — R15-LIFECYCLE-001 is now fixed): R15-CODE-AGENT-001 (Windows half only), R15-LIFECYCLE-008, R15-UI-022, R15-DOCS-024. See `HAND_TESTING_GUIDE.md` and `WINDOWS_MANUAL_CHECK.md`.
- The power and sleep settings this run used: `PMSET_REVERT.md`.
- Restore the working state for the next session: `docs/redesign/verification/vysted-r15-run-state.md` has the resume prompt.
