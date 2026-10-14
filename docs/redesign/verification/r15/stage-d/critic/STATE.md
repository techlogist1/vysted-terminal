<!-- CRITIC of CURRENT_STATE.draft.md, CURRENT_STATE.draft.diff, BLOCKERS.draft.md, BLOCKERS.draft.diff at 4d893147def983623de681effd1bfbae2e7441c5 -->

# Critic: STATE (Opus, stage-d-critic-state)

**Verdict: REVISE.** 17 findings: wrong 11, missing 0, stale 6, unverifiable 0.

The main problem: `CURRENT_STATE.draft.diff` does not start from the file at the sha. It **reverts four R15 doc fixes
that already landed on `docs/CURRENT_STATE.md`**: R15-DOCS-016/017/018 (`f10fb8ce`, `bbfc64bd`, `190b380e`, `3cb5bc29`)
and the batch-10 host-action count fix (`6c5b49d3`). It puts back the stale pre-redesign text that those commits removed
(findings 1-4). The draft looks as if it was rebuilt on an older copy of the file. Both diffs apply cleanly. The
register table, the known-limitations wording and the licence facts are correct.

All paths and lines below are at `4d893147` (`git show 4d893147:<path>`).

## Findings

1. **wrong**: CURRENT_STATE §3.3, draft lines 488-498 (diff hunk `@@ -317,30 +484,16 @@`).
   - **What is wrong:** the draft replaces the at-sha `provider_registry` paragraph with the pre-redesign text:
     "single dispatch point (routing by `asset_class`) … equity → yfinance". It also strips the region-gating from the
     yfinance bullet.
   - **Evidence:** the dispatch is model-key and preference-order based.
     - `sidecar/services/provider_registry.py:91` has `class ProviderDeclaration`.
     - `:166` has `id="nse_direct"`.
     - `:370` has "Walk SYNC providers for `model_key` in preference order".
     - The at-sha text was put there by `190b380e` "document the IN provider chain, region-qualify yfinance
       (R15-DOCS-018)" and `f10fb8ce`.
   - **Fix:** drop those `-`/`+` lines from the hunk and keep the at-sha §3.3 paragraph and yfinance bullet verbatim.

2. **wrong**: CURRENT_STATE §3.3 screener bullet, draft lines 520-523.
   - **What is wrong:** the draft says "`sp500` (**only top 100**) … AND-only criteria; OR-grouping reserved". This
     reverts the R15-DOCS-017 fix.
   - **Evidence:**
     - `sidecar/models/screener.py:36-38` defines the `nse-all`, `bse-all` and `india-all` universes.
     - `sidecar/models/screener.py:181` has `combinator: Literal["and", "or"]`.
     - `sidecar/services/screener_universe_india.py` exists.
     - The fix commits are `bbfc64bd` and `3cb5bc29`.
   - **Fix:** keep the at-sha screener bullet (503-symbol sp500, the India universes, nested AND/OR).

3. **wrong**: the host-action count "18" appears throughout CURRENT_STATE: draft lines 237, 608, 741, 847, 880, 916,
   1022 and 1041.
   - **Evidence:**
     - `src/lib/host-actions.ts:74-94` has `HOST_ACTION_NAMES` with 19 names, ending in `set_region`.
     - `git show 4d893147:sidecar/services/agent_tools/catalog.py | grep -c 'kind="host_action"'` returns `19`.
     - The at-sha file already said 19 (`6c5b49d3`).
   - **Fix:** use "19" everywhere and restore the `HOST_ACTION_NAMES` (`src/lib/host-actions.ts`) pointer.

4. **wrong**: CURRENT_STATE §3.10 Chat sidebar (draft lines 739-742) and §4 "Host-action tools drive the terminal"
   (draft lines 846-853).
   - **What is wrong:** the draft says `executeHostAction` "maps copilot tool calls to live store mutations". It drops
     the at-sha statement that host actions are staged as `ProposedChange` entries and that only
     `AUTO_APPLIED_KINDS` (`panel`/`chart`/`watchlist`) skip review under AUTO. The draft's own §0.0 (lines 155-158)
     states that rule.
   - **Evidence:** `types/proposed-change.ts:38-46` (`AUTO_APPLIED_KINDS`, `autoApplies`). The at-sha wording came
     from `f10fb8ce` (R15-DOCS-016).
   - **Fix:** keep both at-sha paragraphs verbatim.

5. **wrong**: `BLOCKERS.draft.diff` line 4 adds
   `+<!-- DRAFT at 4d893147… by the Stage D docs wave; refresh before rc2 -->` as line 1 of the repo's `BLOCKERS.md`.
   - **Evidence:** I applied the diff to a copy of `BLOCKERS.md` at the sha and got a file byte-identical to
     `BLOCKERS.draft.md`, marker included. `CURRENT_STATE.draft.diff`, by contrast, correctly leaves the marker out:
     the patched copy differs from the draft only by line 1.
   - **Fix:** remove that `+` line from the BLOCKERS diff and make the hunk header `@@ -1,9 +1,267 @@`. Otherwise
     promoting the diff with `patch` ships a DRAFT marker in root `BLOCKERS.md`.

6. **wrong**: CURRENT_STATE §0.0 "Version", draft lines 33-35.
   - **What is wrong:** the draft says the bump "has not been made yet; it is an open pre-tag item". The lead note
     says 0.9.0 lands when the prepared version branch (`worktree-agent-r15-version-0.9.0`) merges, right after the
     `r15-rc1` tag. `BLOCKERS.draft.md:25-27` already says that. As written, the two docs contradict each other, and
     the reader would bump before tagging.
   - **Fix:** use the BLOCKERS sentence ("`0.9.0` lands when the prepared version branch … merges, right after the
     `r15-rc1` tag — confirmed at the tag"). Mirror it in §3.12 (draft line 804) and the §7 "Version strings" row
     (line 1013).

7. **wrong**: BLOCKERS 4.12, draft lines 186-188.
   - **What is wrong:** "§6.5 successor confirms `/portfolio/positions` and `audit_orders` stay untouched" implies
     that an `audit_orders` table exists.
   - **Evidence:**
     - `docs/redesign/DECISIONS_FOR_OPERATOR.md:629-631`: "There is no `audit_orders` table any more: D81 removed it".
     - The FACTS fail-safe bullet says the same.
     - The CURRENT_STATE draft line 158 says the same.
   - **Fix:** "(nothing is written or queued: `/portfolio/positions` stays `[]` and the review queue stays empty; there
     is no `audit_orders` table, D81)".

8. **wrong**: BLOCKERS 4.11, draft lines 180-182.
   - **What is wrong:** "the figure guard grounds a price by value only, not by ok-subject provenance, so a stale bar
     (or, once, an invented figure outside the payload) can pass". This contradicts the concurred wording, which says
     such a figure "is not checked against that result at all"
     (`docs/redesign/verification/r15/stage-c/batch-23/DISPOSITION-CONCURRENCE.md:313-316`). The disposition verifier
     proved the guard never checks a figure for a subject whose call succeeded, which is why that clause was struck
     from LEAD-030.
   - **Fix:** "a figure the agent states for a company whose data call succeeded is not checked against that result at
     all, so a stale bar's value or a figure absent from the payload can pass as the current price".

9. **stale**: CURRENT_STATE §7 row "`contributesAgents` / `contributesNodes` plugin paths — **Unexercised**", draft
   line 1002 (re-added at diff line 523).
   - **Evidence:** this contradicts the draft's own §3.4 (line 592, "`contributesAgents` is now exercised") and
     `plugins/vysted-lenses/index.ts:23` (`contributesAgents: true`).
   - **Fix:** "`contributesAgents` exercised by `vysted-lenses` (Quant Tutor); `contributesNodes` **unexercised**".

10. **stale**: CURRENT_STATE §3.2, draft lines 430-436. The draft edited this paragraph but kept its dead pointers.
    - **Evidence:**
      - `version="0.8.0"` is at `sidecar/app.py:329`, not `:161`.
      - The runtime-extension aggregators are `_register_v0_5_0_…`/`_register_v0_6_0_…` at `app.py:191,205`, called
        at `:368,374`. The draft names "v0.6.0/v0.6.5 … `app.py:131,145`".
      - The v0.6.5 registry was deleted (D89, `docs/redesign/DECISIONS.md:149`).
    - **Fix:** `app.py:329`; "v0.5.0/v0.6.0 aggregators (`app.py:191,205`)".

11. **stale**: CURRENT_STATE §3.12, draft line 803: "despite … D81 and Stage C batches 2-9". The draft's own §0.0 says
    batches 2-22 merged, with batch-23 unmerged.
    - **Fix:** "Stage C batches 2-22".

12. **stale**: CURRENT_STATE §8 KEEP, draft line 1036: "~94 REST routes (post-D81)".
    - **Evidence:** this contradicts §3.2's "~111".
      `git grep -h -E '@router\.(get|post|put|delete|patch)\(' 4d893147 -- 'sidecar/routers/*.py' | wc -l` returns
      `111`, over 28 router modules.
    - **Fix:** "~111 REST routes".

13. **wrong**: BLOCKERS "Phase-5.1 / 6.0 follow-ups" item 1, draft lines 842-845.
    - **What is wrong:** the draft attributes the removal of all four components, KillSwitchToolbar included, to
      `a122dbf6`.
    - **Evidence:**
      - `git log --diff-filter=D -- '*KillSwitchToolbar.tsx'` returns `c9790593 feat(shell): remove kill-switch UI`.
      - `git show --stat a122dbf6` deletes only OrderConfirmationDialog, AuditLogViewer and BrokerConnectPanel.
    - **Fix:** "(D81, `a122dbf6`; KillSwitchToolbar earlier in `c9790593`)".

14. **wrong**: BLOCKERS draft lines 333, 523, 591 and 718 cite "`183c52fe`/`9aaa64f7`, 'E11'" as the Tradesa removal.
    - **Evidence:** `git merge-base --is-ancestor 9aaa64f7 4d893147` gives rc=1. `9aaa64f7` is only on
      `worktree-agent-r10-errors`. `183c52fe` ("complete Tradesa V2 removal (E11)") is an ancestor.
    - **Fix:** cite `183c52fe` only.

15. **wrong**: BLOCKERS 4.6, draft line 159: "the §3.1 sentence at `:84`".
    - **Evidence:** `docs/BLUEPRINT.md:84` is "Code signing pipeline integration …". The OpenBB §3.1 sentence is `:87`
      ("OpenBB ODP wrapped — gives 100+ data providers"). The draft carried the error from
      `DECISIONS_FOR_OPERATOR.md` §4.6.
    - **Fix:** `:87`, and note that the source line number is off.

16. **stale**: dead doc pointers.
    - **Draft-authored:** BLOCKERS line 596 points at `docs/PHASE_6.5_HANDOFF.md`. At the sha the file is
      `docs/archive/PHASE_6.5_HANDOFF.md`.
    - **Carried over:**
      - BLOCKERS 316 `docs/PHASE_8_PERF_BASELINE.md`, 331 `docs/PHASE_8_VISUAL_REGRESSION_REPORT.md` and 480
        `docs/PHASE_8_BUG_CATALOG.md` are all under `docs/archive/` now.
      - CURRENT_STATE lines 197 and 230 name `docs/redesign/FOUNDATION_BUILD_REPORT.md` and
        `docs/redesign/P1_P3_BUILD_REPORT.md`. Neither exists anywhere in the tree (`git ls-tree -r` has no match).
    - **Fix:** repoint the four to `docs/archive/`, and mark the two build reports "(not in tree at this sha)".

17. **stale**: counts in CURRENT_STATE that the refresh left alone.
    - **Evidence:**
      - §1 line 280 says "~18 first-party modules" and §3.8 line 667 says "18". `src/modules/index.ts`
        `vystedModules` lists 20.
      - §3.1 line 388 says "three modules" beside `lib.rs`. `src-tauri/src/lib.rs:3-6` declares four: `diag_log`,
        `keychain`, `openbb_mcp` and `sec_edgar_mcp`.
    - **Fix:** 20 modules; four modules (add `diag_log.rs`).

## Checked and correct

- **Diffs apply:** `patch --dry-run` on copies of both files at the sha returns rc=0 for both diffs. Applying the
  CURRENT_STATE diff reproduces the draft minus the line-1 marker. The four BLOCKERS headings the diff removes are
  renamed to struck-through or MOOT forms, not deleted. No section is deleted wholesale.
- **Line 1:** the required DRAFT marker on both `.draft.md` files.
- **Register:** the §0.0 severity × status table matches the register JSON at the sha cell by cell:
  - critical: 16 fixed.
  - high: 105 fixed / 6 blocked / 4 needs_gui / 1 removed.
  - medium: 258 / 1 open / 5 needs_gui / 9 removed / 15 blocked / 5 not_a_defect.
  - low: 12 fixed / 205 open / 2 / 4 / 4.
  - The `counts` field: raw 887 / entries 652 / rejections 76.
  - The only open critical/high/medium entry is R15-LEAD-035.
  - `R15-AGENT-007` and `R15-LEAD-022` are fixed; `R15-AGENT-017` is blocked_tier4.
  - The 11 needs_gui ids and their subsystems match.
- **Known limitations wording:**
  - LEAD-037 and LEAD-038 match `DISPOSITION-CONCURRENCE.md:313-320` verbatim.
  - LEAD-030 is `LEAD-030-CONCURRENCE.md:118-123` with the struck clause removed. It is identical to
    `RELEASE_NOTES.draft.md`.
  - LEAD-035 falls back to the lead-note text correctly: `batch-24/LEAD-035-CONCURRENCE.md` does not exist yet.
  - The fail-safe (`figure_grounding.py`, `agent_runtime._judge_clause` at `agent_runtime.py:2321`, the 2c gate at
    `:2378`) and the matcher (`_NO_TOOL_CUE`, `planner.py:136`, blame `2e8593eb`, merged in batch 21 `86ae79c4`) are
    both named correctly.
- **Version:** 0.8.0 in all version-of-truth files (`sidecar/app.py:329`, `src/lib/plugin-bootstrap.ts:38`).
- **Tags:** `v0.8.0` and `r13-bedrock` are ancestors, and no `r15*` tag exists.
- **Licence:**
  - `LICENSE` is PolyForm Strict 1.0.0.
  - The Apache-2.0 carve-out list is at `LICENSING.md:44-52` (`types/plugin.ts`, `types/plugin-runtime.ts`,
    `plugins/example/*`).
  - The relicense commit is `0c63d465`, subject "chore(license): relicense core to PolyForm Strict 1.0.0".
- **Trading removal:**
  - `a122dbf6` (2026-09-23) deletes Kite, OANDA, `kill_switch.rs`, `test_safety_end_to_end.py` and
    `test_safety_router.py`.
  - `kiteconnect` and `oandapyV20` were pinned at `a122dbf6^`. Neither they nor autobahn is in any requirements file
    at the sha.
  - `src/modules/safety/` holds only `DisclaimerFlow{.tsx,.test.tsx}` and `index.ts`.
  - `test_no_trading_surface.py` and `test_no_tradesa.py` exist.
- **Plugins:**
  - `CATALOG_ROWS` is at `marketplace.ts:59`, with 5 rows, all `preinstalled: true`.
  - Every plugin has `contributesPanels: false`.
  - `plugins/vysted-lenses` has `contributesAgents: true` (Quant Tutor).
  - `plugins/example` has data + commands + controlPlane.
  - `plugin-bootstrap.ts` has no `BUNDLED_PLUGINS`/`PLUGIN_COMPANIONS`; `moduleForPlugin` is at `:134`.
- **Other code facts:**
  - 28 router modules and 111 routes.
  - Vite migration `8c2f9ab9` (2026-06-10).
  - D81-D92 and D83 (relicense) are in `DECISIONS.md:141-152`.
  - `action_ledger.py` exists.
- **Commits and pointers:**
  - `7a1cd8f` and `043850c` exist.
  - `lint.yml:87-89` holds the ruff step.
  - `CONTRIBUTING.md:95` holds the CLA sentence.
  - `BLUEPRINT.md:55` holds the OpenBB row.
- **Commands:** `cargo update -p vysted-terminal --offline --manifest-path src-tauri/Cargo.toml`, `pnpm ci-local`,
  `pnpm test`, `pnpm build` (= `vite build`), `pnpm sidecars:build`, `pnpm sec-edgar-mcp-sidecar:build` and
  `pnpm tauri dev` all resolve against the `package.json` scripts at the sha.
- **Hygiene:** a case-insensitive grep for the banned name finds 0 hits in all four files. The banned phrase also has
  0 hits. The secret-shape grep has 0 hits.
