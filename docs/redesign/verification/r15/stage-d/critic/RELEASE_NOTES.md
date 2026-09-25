<!-- CRITIC of RELEASE_NOTES.draft.md at 4d893147def983623de681effd1bfbae2e7441c5 -->

# Critic: RELEASE_NOTES.draft.md

**Verdict: REVISE.** 13 findings: 8 wrong, 3 missing, 2 stale, 0 unverifiable. Part A tells users that nine fixed defects are still live, including a false security disclosure about `/mcp`. It says foreign tickers still fail, although that fix is certified. It presents a `needs_gui` item as fixed. It does not quote the binding local-model wording verbatim, and it carries register ids and status tokens. Part B miscounts the local-model `blocked_tier4` items.

All claims were read at sha `4d893147def983623de681effd1bfbae2e7441c5` (`git show <sha>:<path>`, `git grep <pat> <sha> --`). Register numbers come from the register JSON (`docs/redesign/verification/vysted-r15-register.json`), parsed with python.

## Findings

1. **wrong — Part A › Known limitations, the "Eleven fixes still need hands-on verification" bullet (lines 146-158).** The heading calls these items fixes, but the bullet then describes each one as a live bug. For 9 of the 11, the fix has landed and passed headless verification; only the GUI check is pending. The register `note` of each `needs_gui` entry says so:
   - R15-CODE-AGENT-001: "an evil Origin and the null Origin get 403". The code agrees: `sidecar/app.py:289-321` has `ALLOWED_ORIGINS` and an `_OriginGuardMiddleware` that returns 403 "origin not allowed".
   - R15-UI-083: "Save .md/PDF/PNG buttons exist" (`src/modules/research/BriefPanel.test.tsx:23-37`).
   - R15-UI-084: a "maximize takes the full cockpit" test passes (`src/store/agent-dock.test.ts:35`).
   - R15-LIFECYCLE-001: "boot returns at once" pin passes.
   - R15-LIFECYCLE-008: `/system/diagnostics` + logTail verified live.
   - R15-UI-009: downloadCsv now goes through saveTextArtifact.
   - R15-UI-025: no window.prompt remains, and eslint bans it.
   - R15-UI-050: rows are now min-h-8.
   - R15-UI-022: the click path is pinned in vitest.

   The remaining two, R15-DOCS-024 and R15-LIFECYCLE-040, are not fixes at all. Each is a manual demonstration that has never been run ("still_reproduces").

   The "/mcp answers any browser Origin with no auth check" line is a false public security disclosure.

   **Fix:** replace the bullet with: "**Nine fixes still need a hands-on check in the desktop app.** Each passes automated checks, but it runs behind trusted mouse or keyboard events, or the macOS webview, and an automated tool cannot drive those. The nine are: CSV export from Watchlist and Portfolio on macOS; drawing placement, the Text label and drawing lock on the chart; the Notes Link popover; Notes slash-menu row height; brief export to .md, PDF and PNG files; maximising the agent dock; launch no longer freezing while MCP binds; the on-disk log file in a packaged build; and the sidecar refusing requests from other browser origins. Two manual checks have never been run: the documented Claude Desktop MCP setup, and the Windows MCP-spawn fix inside a launched packaged app."

2. **wrong — Part A › Known limitations, the "Tickers on non-Indian foreign exchanges … still fail to resolve" bullet (lines 159-160).** R15-LEAD-022 is `fixed` in the register. `batch-9/VERDICTS.md:109-111` reads "**LEAD-022: certified.** These all price and match Yahoo chart meta: BHP.AX 61.02 AUD, 0700.HK 438.4 HKD, 7203.T, VOD.L, SAP.DE". The code confirms it: `sidecar/services/yfinance_provider.py:219-222` passes a known non-Indian suffix through unchanged. **Fix:** delete the bullet. Add to Fixed › Market data: "tickers on other foreign exchanges (BHP.AX, 0700.HK, 7203.T, VOD.L) now resolve instead of reading as delisted."

3. **wrong — Part A › What changed (lines 23-25) and Fixed › Charts (lines 110-111): "a locked drawing can't be deleted (by accident)" is presented as fixed.** The drawing lock belongs to R15-UI-022, which is `needs_gui`. Its title ends "…and Lock is a dead control", and its note lists "(4) a locked drawing's row delete control is disabled and the drawing survives a click on it" as a pending GUI check. That is not certified work. It also contradicts the draft's own needs_gui list (line 148). **Fix:** remove the locked-drawing clause from both lines. The per-symbol and per-timeframe scoping (R15-UI-020, certified at `batch-7/VERDICTS.md:156`) and the indicator-overlay fix (R15-UI-023, `batch-7:166`) stay.

4. **wrong — Part A › "Known limitations at rc1 — agent chat with a keyless local model" (lines 178-200): the binding wording is not verbatim.** The lead rule requires the LEAD-030, LEAD-037 and LEAD-038 sentences word for word. The draft instead moves "With a keyless local model" into the intro paragraph, changes LEAD-030's "the agent can still state" to "The agent can state", and starts LEAD-037 and LEAD-038 mid-sentence ("A figure the agent states…", "When you tell the agent…"). The sources are `batch-23/LEAD-030-CONCURRENCE.md:118-123` and `batch-23/DISPOSITION-CONCURRENCE.md:313-320`. **Fix:** make each bullet body exactly:
   - LEAD-030: "With a keyless local model, the agent can still state an invented price or metric as if a tool had returned it when the figure is about a company no successful tool call in that turn covered — one named in the same paragraph as a company whose call succeeded (under a name the guard cannot map, or never looked up at all), or any company in a turn where no call failed or no tool was called — and a figure-less fabricated result dump or a code fence left open from an earlier round can also render, while every shape pinned in eight fix rounds is replaced by an honest "returned no data" note."
   - LEAD-037 and LEAD-038: the `DISPOSITION-CONCURRENCE.md:313-320` sentences, including their "With a keyless local model, " openings.

   Bold lead-ins may stay outside the quoted sentence.

5. **wrong — Part A contains register ids and jargon.** Part A is the GitHub release body for users, so it should carry none. The draft has:
   - `R15-LEAD-030` / `R15-LEAD-037` / `R15-LEAD-038` with `blocked_tier4` (lines 190, 195, 200);
   - `R15-LEAD-035` with "still `open`" (line 208);
   - "register-wide", "operator-blocked gap" and "everything else above critical/high/medium severity" (lines 163-166);
   - a pointer to the internal `docs/redesign/DECISIONS_FOR_OPERATOR.md §2` (line 167).

   **Fix:**
   - Drop the ids and status tokens from Part A; Part B already carries them.
   - Replace each "(`R15-LEAD-0xx`, `blocked_tier4`)" with nothing, or with "(accepted limitation)".
   - LEAD-035 becomes "(a fix for the over-matching half is in final testing; confirmed at the tag)".
   - Lines 161-167 become: "Other open issues are low-severity. One medium issue remains open: the "don't use tools" detector described below. The remaining gaps are accepted and documented: signing, the release pipeline, CI, extensibility, webview hardening and a few stale docs."

   The code pointers for the fail-safe and the matcher (lines 215-221) are mandated and stay.

6. **wrong — Part B › Register at this sha (lines 342-346): the 25 `blocked_tier4` entries are said to include "the four `R15-LEAD-*` local-model items above".** The register counts only three: FACTS.md:129 lists R15-LEAD-030, -037 and -038 as `blocked_tier4`, and R15-LEAD-035 is `open` (FACTS.md:125). Line 340 of the same paragraph itself says LEAD-035 is open. **Fix:** "…and three of the four `R15-LEAD-*` local-model items above (030, 037, 038; 035 is still `open`)".

7. **wrong — Part B › Register at this sha (line 341): "227 low (most of the 205 remaining open entries)".** A python pass over the register gives open by severity = `{('low','open'): 205, ('medium','open'): 1}`. So every one of the 205 remaining open entries is low, not "most". **Fix:** "227 low (205 of them still open)".

8. **wrong — Part A › Known limitations › Fail-safe (lines 218-220): "its structural gap … is exactly what the four limitations above describe".** Figure grounding checks figures only. LEAD-038 is a narrated write with no figure involved; its containment is the review queue, which needs a real tool call (FACTS.md:186). LEAD-035 is the phrase matcher. **Fix:** "…is what the first two limitations describe. A false "done" reply (the third) is contained by the review queue, because a portfolio write needs a real tool call and a narrated one stages nothing. The fourth is the phrase detector named next."

9. **missing — Part A › What changed and Fixed: nothing certified in batches 10-16 is listed.** Their `VERDICTS.json` `certified` arrays hold 50 + 18 + 19 + 2 + 1 + 2 = **92** entries: batch-10 50, batch-11 18, batch-12 19, batch-13 2, batch-14 1, batch-16 2. Examples are the option chain (R15-DATA-079, `batch-11/VERDICTS.md:28`), the agent-dock maximise, CODE-AGENT-033 and RESEARCH-007. Together with LEAD-022 from batch-9 (finding 2), 92 of the 391 fixed entries are absent. The draft admits this in HTML comments, but the release body a user reads is incomplete. **Fix:** at rc2, itemise from `git show <sha>:docs/redesign/verification/r15/stage-c/batch-{10..16}/VERDICTS.json` → `.certified`, grouped under the existing Fixed headings. Drop both VERIFY comments once that is done.

10. **missing — Part A › Licence change: no warning that the commercial licence cannot be obtained yet.** The section sends commercial users to `COMMERCIAL_LICENSE.md`, but that file is marked "**STATUS: DRAFT.** Commercial terms and pricing below are placeholders" (`COMMERCIAL_LICENSE.md:3`). Its contact is a "placeholder address" (`:63`), and R15-DOCS-002 ("commercial license contact has no working inbox", `DECISIONS_FOR_OPERATOR.md:231`) is `blocked_tier4`. **Fix:** add "The commercial terms and contact address are placeholders for this release; commercial licensing is not yet available."

11. **missing — Part A › Known limitations: two user-facing `blocked_tier4` gaps are absent.**
    - R15-UI-044 (`DECISIONS_FOR_OPERATOR.md:257-260`): "a denied/failed macOS keychain read during first-launch TOS hydrate leaves the TOS dialog (and onboarding) permanently unrendered with no error shown".
    - R15-AGENT-049 (`:379`): "native web search has no per-run cap or spend meter off Anthropic". This is BYOK spend.

    **Fix:** add these two bullets:
    - "If macOS denies the keychain read on first launch, the terms dialog and onboarding don't appear and no error is shown; allow keychain access and relaunch."
    - "Native web search on non-Anthropic providers has no per-run cap or spend meter."

12. **stale — Part B heading (line 225): "(2026-09-23 – 2026-09-25)".** `git log --first-parent --merges --format='%h %ad' --date=short r13-bedrock..<sha>` gives `c155e5ad 2026-09-26` (batch 22). **Fix:** "(2026-09-23 – 2026-09-26)", or end the range at "confirmed at the tag".

13. **stale — Part B › Not yet merged (lines 306-307): batch 24 "only `PLAN.md` exists in its dir at this sha".** At the sha, batch-24 has no tracked dir: `git ls-tree --name-only <sha> docs/redesign/verification/r15/stage-c/` lists batch-2 to batch-23 only, which FACTS.md:151 confirms. The PLAN.md is in an untracked live dir. **Fix:** "Stage C batch 24 (in flight, not tracked at this sha; it carries the named narrowing-only fix for `R15-LEAD-035`'s over-match half)".

## Checked and correct

- **Line 1 marker:** exact.
- **Grep checks:** `grep -ci laya` gives 0 and `grep -ci 'low-latency'` gives 0. The draft contains no key, token or keystore content; the updater pubkey in `tauri.conf.json` is not reproduced.
- **Trading removal:**
  - No trading surface is described as a feature.
  - `sidecar/services/kill_switch.py`, `src-tauri/src/kill_switch.rs`, `sidecar/models/audit_log.py` and `registry_v0_6_5.py` are all absent at the sha.
  - The default `~/.vysted-terminal/audit_log.db` path is correct (`a122dbf6^:sidecar/models/audit_log.py:12`).
  - The `broker:_meta:first-launch-tos` key is dead: the terms ack moved to `KEYCHAIN_NAMESPACES.appMeta("first-launch-terms")` (`src/modules/safety/DisclaimerFlow.tsx:6`; D85).
  - "17 trading-only test files" is correct: `git diff --name-status a122dbf6^1 a122dbf6 -- sidecar/tests` shows 18 deletions, of which 17 are `test_*.py` plus `gen_audit_trail.py`.
- **Licence:**
  - PolyForm Strict: can run and use noncommercially; modification, redistribution and commercial use need the commercial licence. Every pre-relicense commit stays AGPL-3.0.
  - The Apache-2.0 carve-out covers `types/plugin.ts`, `types/plugin-runtime.ts` and the example plugin.
  - Source: `LICENSING.md` at the sha.
- **Fail-safe:**
  - The AUTO kinds `panel`/`chart`/`watchlist` are in `types/proposed-change.ts:38-46`.
  - `sidecar/services/figure_grounding.py` exists, and `_judge_clause` is at `sidecar/services/agent_runtime.py:2321`.
  - Rule 1, rule 3 and the 2c FAIL-SAFE appear at `agent_runtime.py:2331-2378`.
  - `_NO_TOOL_CUE` is at `sidecar/services/planner.py:136`.
  - LEAD-035's still-open wording follows the lead rule: `stage-c/batch-24/` holds only `PLAN.md` and no `LEAD-035-CONCURRENCE.md`.
- **Fixed-line sample:** 27 ids behind the Fixed and What-changed lines were checked, and each is certified in a batch VERDICTS.md:
  - DATA-006, 033, 042, 070; RESEARCH-001, 002, 003; CODE-FRONTEND-004 (batch-2)
  - UI-002, UI-008, AGENT-002, AGENT-003, AGENT-080 (batch-3)
  - UI-004 (batch-4)
  - DATA-023, DATA-024 (batch-5)
  - UI-020, UI-023, DATA-090, AGENT-043 (batch-7)
  - LIFECYCLE-010, 011, 022, 023 (batch-8)
  - LEAD-031 (batch-17)
  - LEAD-033, LEAD-034 (batch-18)

  The data-cache clear on a version change is backed by `sidecar/tests/test_data_cache.py:136-146` (`ensure_build`).
- **Known limitations:**
  - The DeepSeek V4 Flash content-filter limitation matches R15-AGENT-017 (`blocked_tier4`; default in `src/lib/workspace.ts:189`).
  - The `keyless-fallback` label is at `sidecar/services/agent_tools/deep_research.py:430-434`.
  - Unsigned builds, no release pipeline and a dead updater (endpoint `releases/latest/download/latest.json`, `createUpdaterArtifacts: false`) match R15-RELEASE-001, 002 and 003.
  - CI triggers are push `main` + `pull_request`, with 3 workflows × 3 OS.
- **Part B:**
  - All 23 first-party merge hashes and subjects match `git log --first-parent --merges`, and the per-batch tallies for batches 2-22 match the merge subjects and VERDICTS.md. That includes batch-11's "18 of 26", whose 26 comes from the CHANGELOG's "26 open entries … planned".
  - Batch 19 "closes the batch-18 escapes" and batch 21's tilde-fence regression match their VERDICTS.
  - Batch-22 is `block` with a W1-only merge.
  - D81-D92 match `docs/redesign/DECISIONS.md` (D82 `PAID_USD_CAP = 7.50` under the $8.00 cap). Note that DECISIONS.md itself carries two rows numbered D85; this is not the draft's error.
  - Register counts (652; 391/206/25/14/11/5; 16/116/293/227; 76 rejections) match the JSON `counts` field.
  - The six 0.8.0 version sources and "the version branch merges right after the r15-rc1 tag" are correct, and nothing claims r15-rc1 exists.
  - `R15_GATE_RC1.md` exists at `docs/redesign/verification/`.
  - Every path the draft names exists at the sha, or is absent where the draft says it was deleted.
