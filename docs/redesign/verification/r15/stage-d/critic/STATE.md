<!-- CRITIC of CURRENT_STATE.draft.md, CURRENT_STATE.draft.diff, BLOCKERS.draft.md, BLOCKERS.draft.diff at f444479031d7d493b7955b9af041d18e7c7a40cc -->

# Critic — STATE (Fable, stage-d-critic-state)

Sha: `f444479031d7d493b7955b9af041d18e7c7a40cc`. Inputs: the four draft files under
`docs/redesign/verification/r15/stage-d/`. Targets: `docs/CURRENT_STATE.md`, `BLOCKERS.md`.

## Verdict: REVISE

Findings 1–6 would mislead the next maintainer or make a CI step fail. The rest are
one-line corrections. Counts: wrong 6, missing 3, stale 2, unverifiable 0 (11 total).

## Findings

1. **wrong** — CURRENT_STATE §0.0, "R15 Stage C remediation" paragraph (draft line ~79):
   "batch merge commits are listed … and as D82 through D92 in `docs/redesign/DECISIONS.md`".
   Evidence: `git show f4444790:docs/redesign/DECISIONS.md` lines 142–152 — D82 = OpenAI
   spend cap, D83 = relicense commit `0c63d46`, D84 = Gate 2 adjudication, D85–D92 = Stage C
   **removal-plan (batch 1, D81) riders**; a second D85 row at line 153 records the
   `a122dbf` merge. Batch 3/4 decisions are `D-B3-1` (line 163) and `D-B4-1`, not D-numbers.
   Nothing in D82–D92 records batches 2–9. Fix: replace the clause with "the batch-1
   removal-plan riders are D85–D92 (D83 records the relicense); per-batch decisions from
   batch 3 on carry `D-B<n>-<k>` ids in `DECISIONS.md`".

2. **wrong** — CURRENT_STATE §7 "Bottom line" (draft line ~904): "§6.5 itself no longer
   exists — it was removed with trading (D81)". Evidence: DECISIONS.md D88 (line 148)
   "BLUEPRINT keeps the §6.5 section number for the agent-write safety model, retitled";
   `git show f4444790:docs/SAFETY_ARCHITECTURE.md` line 1 is
   `# Vysted Terminal — Agent-Write Safety (BLUEPRINT §6.5)`; the draft's own §7 row
   "Agent-write safety model (§6.5) — **Works**" and §3.6 heading contradict the sentence.
   Fix: "the §6.5 order-execution layer no longer exists (D81); §6.5 now names the
   agent-write safety model, i.e. the proposed-changes trust gate (§5) over the 18 host
   actions".

3. **wrong (makes `pnpm format:check` / CI lint fail)** — both diffs. The drafts pass
   prettier only because `docs/redesign/verification/r15/` is ignored
   (`git show f4444790:.prettierignore` line 73); the promoted targets are not ignored.
   Command (repo cwd, PATH per brief): `node_modules/.bin/prettier --check <sha copies>` →
   "All matched files use Prettier code style!" exit 0; the same on the patched copies →
   `[warn] CS.patched.md`, `[warn] BL.patched.md`, exit 1 (prettier 3.8.3, repo
   `.prettierrc`). `prettier --write` delta: (a) both files gain a leading blank line
   (CS diff hunk 1 `+` blank before the title; BL diff hunk 1 first `+` line) — delete it;
   (b) §0.0 severity table (draft lines 67–72) is unpadded — prettier pads every column;
   (c) §7 table (draft lines 872–900): the two appended rows and the edited cells widen the
   Status/Source columns, so every row re-pads, and a blank line is required between the
   table and `**Bottom line:**` (draft line 901); (d) BLOCKERS item 3 continuation
   (draft lines 166–167) must be indented 5 spaces, not 3. Fix: run
   `node_modules/.bin/prettier --write` on the two patched copies and regenerate both
   `.diff` files from them; the `.draft.md` files then match.

4. **missing** — BLOCKERS "R15 open items" → "Open Tier-4 decisions" closing parenthetical
   (draft lines 72–75) accounts for 1.2/2.3/2.4/2.5/3.5/3.6 and nothing else, so DFO §3.1,
   §3.2, §3.3 vanish. Evidence: `git show f4444790:docs/redesign/DECISIONS_FOR_OPERATOR.md`
   lines 179 (3.1 "approve a one-time 'remove leftover broker credentials' step + CHANGELOG
   note"), 195 (3.2 "review the exact copy in `src/modules/safety/DisclaimerFlow.tsx`
   before it ships — flagged Tier-4 by R15-UI-041"), 205 (3.3 accepted gaps, tracked as
   R15-CODE-FRONTEND-013 / -008). All three are open (FACTS §decisions closed=False). Fix:
   add a sub-list "Open non-Tier-4 operator items" with 3.1, 3.2, 3.3 and their verbatim
   unblock lines, and mention them in the parenthetical.

5. **missing** — CURRENT_STATE §0.0 "Version" paragraph and the §1 edit both send the reader
   to `BLOCKERS.md` "R15 open items" for the 0.9.0 bump, but the BLOCKERS draft's R15
   section has no such item (`grep -n -i '0\.9\.0\|bump' BLOCKERS.draft.md` → only the two
   header lines 5/11 and unrelated 304/424). Fix: add a bullet under "R15 open items":
   "**0.9.0 bump not made** — `package.json:3`, `src-tauri/Cargo.toml:3`,
   `src-tauri/tauri.conf.json:4`, `sidecar/app.py:327`, `src/lib/plugin-bootstrap.ts:37`
   are `0.8.0` (FACTS §versions); after editing run
   `cargo update -p vysted-terminal --offline --manifest-path src-tauri/Cargo.toml`
   (CLAUDE.md §Versioning) and grep for stale `0.8.0` strings".

6. **stale** — CURRENT_STATE §7 row "Static-export build — **Works** — `next build`
   compiles" (draft line 878) and the untouched §1/§2/§3.8 Next.js claims (lines 195, 259,
   549). Evidence: `git show f4444790:package.json` has no `next` dependency; line 8
   `"dev": "vite"`, `"build": "vite build"`, line 82 `"vite": "^8.0.16"`, line 68
   `@vitejs/plugin-react`; `vite.config.ts` exists at the sha; migration commit
   `8c2f9ab9 2026-06-10 feat(shell): migrate Next.js -> Vite 8 + React 19 (WS1)`. There is
   no `next` binary to run, so the row names a command that does not exist. §0.0 claims to
   be the current top-of-file truth and does not mention it. Fix: §7 row → "`pnpm build`
   (`vite build`) — **Works** per prior tags; not re-run at this sha"; add one sentence to
   §0.0: "Frontend is Vite 8 + React 19 since `8c2f9ab9` (2026-06-10); Next.js references
   below are pre-migration history." (CLAUDE.md at the sha also still says Next.js — Tier-1,
   queue via `docs/redesign/CLAUDE_MD_PROPOSAL.md`, not this draft.)

7. **wrong** — CURRENT_STATE §0.0 "Trading removed" paragraph: "only
   `src/modules/safety/DisclaimerFlow.tsx` remains under `src/modules/safety/`".
   Evidence: `git ls-tree f4444790 src/modules/safety/` → `DisclaimerFlow.test.tsx`,
   `DisclaimerFlow.tsx`, `index.ts`. Fix: "only the DisclaimerFlow module
   (`DisclaimerFlow.tsx`, its test and `index.ts`) remains".

8. **wrong** — CURRENT_STATE §0.0 "Test-count claims" paragraph: "Stage C batches 2–9
   (which deleted the §6.5 safety-model tests along with the feature …)". Evidence:
   `git show --stat a122dbf6` (batch 1, the D81 merge) deletes
   `sidecar/tests/test_safety_end_to_end.py` (509 lines) and `test_safety_router.py`;
   batches 2–9 did not. Fix: attach the parenthetical to D81: "the D81 removal (which
   deleted the §6.5 order-safety tests) and Stage C batches 2–9 (which changed others)".

9. **stale** — CURRENT_STATE header blockquote, draft line 14 (a paragraph the diff edits):
   "any BYOK/live-broker round-trip are unverified". No broker exists (D81; §0.0 two lines
   later). Fix: "any BYOK round-trip".

10. **wrong** — CURRENT_STATE §7, "Version strings" row source cell (edited by the diff,
    draft line 898) cites "§14"; the neighbouring `auto_export` row cites "§1, §14" and
    other rows "§15"/"§11"/"§8". The document's headings run §0.0–§8 (`grep '^## '`); the
    version/updater text lives in §3.12 (draft lines 686–692). Fix: "§3.12; §0.0" for the
    edited row (the other pre-existing dangling anchors are optional cleanup).

11. **missing** — CURRENT_STATE §0.0 "Relicensed" paragraph names only `types/plugin.ts` and
    `plugins/example` as the Apache-2.0 carve-out. Evidence:
    `git show f4444790:LICENSING.md` lines 46–50 also list `types/plugin-runtime.ts` and the
    example's `example.test.ts` + `manifest.json`; DECISIONS.md D83 says the same. A plugin
    author reading this would think importing `plugin-runtime.ts` is Strict territory. Fix:
    "(`types/plugin.ts`, `types/plugin-runtime.ts`, `plugins/example/*` — see
    `LICENSING.md`)".

## Checked and correct

- Line 1 of both `.draft.md` files is exactly
  `<!-- DRAFT at f444479031d7d493b7955b9af041d18e7c7a40cc by the Stage D docs wave; refresh before rc2 -->`.
- Both diffs apply cleanly to the files at the sha: `patch --dry-run` exit 0 for
  `docs/CURRENT_STATE.md` (898 lines) and `BLOCKERS.md` (637 lines); each `.draft.md` minus
  line 1 is byte-identical to sha-file + diff (`diff` empty).
- No section deleted wholesale: every struck item keeps its heading and a CLOSED note;
  BLOCKERS pre-sha items already closed by D81 without strike-through (Phase 9 #2, S1 #1–2,
  S2 #5) carry their own CLOSED text at the sha and were correctly left alone.
- Every strike-through names `a122dbf6`, which is an ancestor of the sha and a real merge
  (`git log -1` shows two parents) whose stat deletes `plugins/brokers/kite/*`,
  `plugins/brokers/oanda/*`, `sidecar/services/brokers/{kite,oanda}.py`,
  `sidecar/requirements.txt` (−20 lines incl. autobahn), `src/modules/safety/{AuditLogViewer,
  OrderConfirmationDialog}.tsx`, `src/modules/broker-connect/*`,
  `sidecar/tests/test_safety_end_to_end.py`. `7a1cd8f` touches only
  `sidecar/services/resolver_masters/enrich_nse_sectors.py`; `043850c` is the gpt-5.x fix;
  both are ancestors.
- Register counts equal FACTS and the register JSON `counts` block (887/626/76;
  16/112/279/219); the §0.0 severity × status table sums row-wise (112 = 100+3+4+1+4,
  279 = 153+114+2+9+1, 219 = 10+205+4). The 114 open-medium ids in the BLOCKERS grouping
  match the register exactly, per `subsystem` field, 30 subsystems, 0 mismatches; 3 open
  high, 6 `needs_gui`, 4 `blocked_tier4` ids match; 0 open critical.
- The 12 Tier-4 items listed equal FACTS §decisions (tier4 ∧ ¬closed); unblock lines are
  verbatim from `DECISIONS_FOR_OPERATOR.md` at the sha.
- Product facts: no trading anywhere (`test_no_trading_surface.py` present; no
  `autobahn`/`oandapyV20` outside that test; no KillSwitchToolbar/OrderConfirmationDialog/
  AuditLogViewer/BrokerConnectPanel under `src/`); portfolio stays; licence = PolyForm
  Strict 1.0.0 (`LICENSE` heading) + `COMMERCIAL_LICENSE.md` + `LICENSE-APACHE` +
  `LICENSING.md` all present; `package.json` `license: SEE LICENSE IN LICENSE`; target
  0.9.0 with all five version sources still `0.8.0` and consistent; three
  `externalBin` sidecars; the draft does not claim a macOS production build.
- 18 host actions: `git grep -c 'kind="host_action"' f4444790 -- sidecar/services/agent_tools/catalog.py` → 18.
- MCP `--onedir` still open: no `onedir` in `src-tauri/tauri.conf.json` or `scripts/`
  except a hint string in `scripts/smoke-test-sidecars.mjs:843`.
- Workflows at the sha are `build.yml`, `lint.yml`, `test.yml` only (no `release.yml`),
  matching the 2.9/2.11 text. Commands cited (`pnpm ci-local`, `pnpm test`,
  `cd sidecar && pytest`, `git revert 7a1cd8f`, `smoke-test-sidecars.mjs`) exist in
  `package.json` scripts / `scripts/` at the sha.
- No key, token or keystore content: secret-shape grep (sk-/AKIA/ghp_/PRIVATE KEY/xox/AIza/
  Bearer) over all four files → 0 matches.
