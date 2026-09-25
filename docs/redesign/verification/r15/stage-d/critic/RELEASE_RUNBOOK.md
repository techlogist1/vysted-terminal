<!-- CRITIC of RELEASE_RUNBOOK.draft.md at 4d893147def983623de681effd1bfbae2e7441c5 -->

# Critic: RELEASE_RUNBOOK.draft.md (target `docs/RELEASE_RUNBOOK.md`)

**Verdict: REVISE.** 11 findings: 5 wrong, 3 missing, 2 stale, 1 unverifiable. Four of them would mislead the
person cutting the release or make a step fail: #3 (the post-bump grep check fails on the real bump), #4 (the
prepared version branch and the tag order are not mentioned), #5 (signing comes after the build it has to change),
and #7 (the rollback rebuilds the AGPL trading-era v0.8.0).

All reads are at `S=4d893147def983623de681effd1bfbae2e7441c5` (`git show S:<path>`) unless a finding says otherwise.
Scratch: `scratchpad/stage-d-4d89314/crit-v080.txt` (the grep output for #3).

## Findings

1. **wrong (low)**: §0, line 29: "`package.json:22`" and "bare ... `pip`".
   Evidence: `git show S:package.json | grep -n ci-local` returns `20:    "ci-local": ...`. The chain calls
   `python -m pip install ...`, never a bare `pip`.
   Fix: write `package.json:20`, and drop `pip` from the list of bare commands (the list becomes `python`, `pytest`,
   `cargo`, `ruff`, `node`, run as `python -m pip`).

2. **stale**: §0, lines 47-49: "`scripts/ensure-sidecar.mjs`'s `targetTriple()` (`:29-34`) ... 'could not
   determine host target triple'".
   Evidence: at S, `scripts/ensure-sidecar.mjs` is a 14-line wrapper (`:9-14`) with no `targetTriple`. The function
   is `scripts/sidecar-specs.mjs:190-195`, and it throws `"could not determine host target triple from \`rustc
   -vV\`"` (`:193`). The draft's own §4 (lines 334-335) already cites `sidecar-specs.mjs :190-195`, so the two
   sections contradict each other.
   Fix: change the citation to "`scripts/sidecar-specs.mjs` `targetTriple()` (`:190-195`)" and quote the full error
   string.

3. **wrong**: §1, lines 115-118, 135-162, and the VERIFY comment at 160-162. It says the post-bump residual is
   "exactly 93", and it classes `src/store/marketplace.test.ts:46` as "not a bump target".
   Evidence: the prepared bump commit `517da226 chore(release): bump version to 0.9.0` (branch
   `worktree-agent-r15-version-0.9.0`) changes 8 files, not 6. Besides the five sources and `Cargo.lock`, it also
   changes `README.md:53` ("version strings sit at `0.8.0` pending a release cut") and
   `src/store/marketplace.test.ts:46`. Its message says the fixture was bumped because "its comment says it matches
   HOST_VERSION" (`S:src/store/marketplace.test.ts:43-44`). Running the draft's own grep against that commit
   (`git grep -n '0\.8\.0' 517da226 -- . <same excludes> | wc -l`) returns **91**, not 93. The VERIFY check would
   therefore flag the real bump as wrong. `README.md:53` is also a statement about current state, not
   "historical/narrative" (line 139).
   Fix: move `README.md:53` and `src/store/marketplace.test.ts:46` into the bump list, and state the post-bump
   residual as 91 (99 minus 8). Alternatively, say "the residual equals what `517da226` leaves, and none of the
   bumped lines". Mark "confirmed at the tag" if the branch changes before it merges.

4. **missing**: §1, §9 and the Checklist. The runbook never mentions the prepared version branch or the order of
   the release.
   Evidence: the branch `worktree-agent-r15-version-0.9.0` exists (`git log --oneline -3` gives `c1e9164c docs: the
   single CLAUDE.md commit for the 0.9.0 release`, then `517da226 chore(release): bump version to 0.9.0`, on top of
   `3d64ca17`). `517da226` is not in S (`git merge-base --is-ancestor` fails). The lead note says 0.9.0 lands by
   merging that branch right after the r15-rc1 tag. The runbook tells the lead to hand-edit five files, which would
   duplicate or conflict with that branch. §9 also:
   - tags whatever HEAD happens to be (`git tag -a v0.9.0 -m ...`, with no commit named);
   - never requires the rc gate to pass first, although `S:docs/redesign/verification/R15_GATE_RC1.md:3` reads
     "**Verdict: FAIL.** Do not tag rc1." and `:51-55` insists the tagged tree be exactly the tree the gate
     evaluated;
   - never says that `r15-rc1` does not exist yet (`git tag --list 'r15*'` returns nothing).
   Fix:
   - Replace §1's hand-edit instruction with "merge `worktree-agent-r15-version-0.9.0` (`517da226` + `c1e9164c`)
     right after the r15-rc1 tag", and keep the five-file list only as the audit of what that commit touches.
   - Add a checklist step before §9: "rc gate round 2 verdict PASS at the candidate sha (confirmed at the tag)".
   - Write the tag command as `git tag -a v0.9.0 <gated-sha> -m ...`.

5. **missing**: order of §6 and §8. Signing is a decision placed after the build it changes.
   Evidence: macOS signing and notarization happen inside `tauri build`. The identity is read from
   `tauri.conf.json > bundle > macOS > signingIdentity`, and the docs say "After setting these environment
   variables, rerun your Tauri build or bundle command" (https://v2.tauri.app/distribute/sign/macos/, Notarization
   section). At S, `S:src-tauri/tauri.conf.json` has no `signingIdentity` (the grep for it returns no line). If the
   operator approves §2.8, even the minimal `"-"`, the §6 `.app`/`.dmg` and the §7 launch check are already out of
   date.
   Fix: put the §8 decision before §6, or add to §8: "if any signing change lands, re-run §6 and §7; APPLE_* notary
   credentials are build-time env, never committed".

6. **missing**: §7 and §9. Two operator items that gate a public release are not in the runbook.
   Evidence:
   - `S:docs/redesign/DECISIONS_FOR_OPERATOR.md:231-237` §2.18 (R15-DOCS-002): the commercial-licence contact has
     no MX, and a real address "gets swapped into both files before any public 0.9.0 announcement". A GitHub Release
     is such an announcement.
   - `:257-265` §2.21 (R15-UI-044): "a denied/failed macOS keychain read during first-launch TOS hydrate leaves the
     TOS dialog (and onboarding) permanently unrendered". This is exactly the release-`.app` keychain path §7 walks
     through (lines 423-452).
   Fix:
   - Add a NEEDS-OPERATOR line to §9 and the checklist: "§2.18 commercial contact replaced in `LICENSING.md` and
     `COMMERCIAL_LICENSE.md` before publishing".
   - Add to §7: "if macOS shows a keychain prompt, choose Allow. A Deny leaves a blank first run with no error
     (R15-UI-044, §2.21, Tier-4 open). That is this known bug, not a sign that the terms check passed."

7. **wrong**: §11, lines 609-614: "Restoring the previous tag's build: `git checkout v0.8.0` ... into a clean
   worktree and re-run §2-§6".
   Evidence:
   - `git ls-tree --name-only v0.8.0 plugins/ sidecar/services/` lists `plugins/brokers`, `plugins/tradesa-v2`,
     `sidecar/services/broker_base.py`, `sidecar/services/brokers`, `sidecar/services/kill_switch.py` and
     `sidecar/services/tradesa_v2_provider.py`. That is the trading surface D81 removed permanently (`a122dbf6`).
   - `git show v0.8.0:LICENSE | head -1` gives `GNU AFFERO GENERAL PUBLIC LICENSE`, not PolyForm Strict 1.0.0.
   - Rebuilding v0.8.0 as a rollback would re-ship broker/order code under the old licence.
   - `git checkout <tag>` also does not create a worktree.
   Fix: delete the "re-run §2-§6 from v0.8.0" path. Rollback becomes (a) pull the Release (as written), and (b) fix
   forward on `004-r4-experience-rebuild`, or rebuild from the pre-bump commit on that branch. State that no pre-D81
   tag (v0.8.0 and earlier) is an acceptable rollback target, because each contains the removed trading surface and
   the AGPL licence. If an older tree must be inspected, use `git worktree add <dir> <ref>`.

8. **stale**: §3, lines 232-255, the `<!-- fill -->` comments at §4 (342-343) and §5 (378-379). The draft says the
   closest real gate evidence is the batch-9 per-gate re-run (1683 vitest), that this "is not a literal `pnpm
   ci-local` invocation", and that no logged smoke output exists.
   Evidence: newer tracked records of literal full runs exist at S:
   - `S:docs/redesign/verification/R15_GATE_RC1.md:18`: "ci-local | **PASS** | ... vitest 1825/1825, cargo 19,
     pytest 3150 passed and 1 skipped, `EXIT=0`".
   - `R15_GATE_RC1.md:19`: "smoke | **PASS** | ... `SMOKE_EXIT=0` ... 3 sidecars, 13 agents, mcp toolCount 40" (at
     `1d6511c8`).
   - `stage-c/batch-16/VERDICTS.md:11`: "ran `pnpm ci-local` at 7b65b217 ... CI_EXIT=0 (3271 passed, 1 skipped)".
   - `batch-22/VERDICTS.md:13-16`: "ci-local `CI_EXIT=0` (3456 passed, 1 skipped) ... smoke: `SMOKE_EXIT=0`".
   - `batch-23/VERDICTS.md:13-15`: "ci2 `CI_EXIT=0` (3471 passed, 1 skipped) ... smoke `SMOKE_EXIT=0`".
   The log files themselves are not tracked; `git ls-tree` finds no `smoke`/`ci-local` log under `r15/stage-c`.
   Fix: cite the batch-23 integrator chain (ci2 CI_EXIT=0, 3471 pytest passed, SMOKE_EXIT=0 at `9aa9fb6c`) and the
   rc1 sheet's items 4-5 as the latest recorded green runs. Say they are integration-branch runs, not the release
   candidate, and drop the batch-9 table.

9. **wrong (low)**: §1b.
   - Line 169: "one of 17 Stage-C batch headings". `git show S:CHANGELOG.md | grep -c '^## R15 Stage C — batch'`
     gives **16** (batch 2 to 17). FACTS line 152's "17" has the same slip.
   - Line 181: "drop ... this section's own critic footer". `RELEASE_NOTES.draft.md` has no critic footer. Its
     trailing block is a `<!-- refresh f4444790 to 4d89314: ... -->` comment (its line 372), plus `<!-- fill at
     rc2 -->` markers.
   Fix: write "16 Stage-C batch headings". Change the promotion instruction to "drop line 1's DRAFT marker and the
   trailing `<!-- refresh ... -->` comment; fill or remove every `<!-- fill at rc2 -->`".

10. **wrong (low)**: §4, lines 297-299: log lines `[ensure-<name>] building ...`.
    Evidence: `S:scripts/sidecar-specs.mjs:236` defines ``const tag = `[ensure-${spec.name.replace(/^vysted-/, "")}]` ``,
    so the real prefixes are `[ensure-sidecar]`, `[ensure-openbb-mcp-sidecar]` and `[ensure-sec-edgar-mcp-sidecar]`.
    Searching a log for `[ensure-vysted-sidecar]` finds nothing.
    Fix: say "`<name>` without its `vysted-` prefix" and list the three tags.

11. **unverifiable**: §3, lines 237-239: "per the lead note ... per the lead note, no `r15-rc1` tag exists yet".
    Evidence: "the lead note" is a workflow prompt, not a repo file. Once this is promoted to `docs/RELEASE_RUNBOOK.md`,
    no reader can check it.
    Fix: cite repo evidence instead: `git tag --list 'r15*'` (empty at S), `R15_GATE_RC1.md:3` for the FAIL, and
    `DECISIONS_FOR_OPERATOR.md` §4.9-4.12 (`:483-647`) for the LEAD dispositions. Write "confirmed at the tag" for
    anything still unknown.

## Checked and correct

- Line 1 is exactly `<!-- DRAFT at 4d893147def983623de681effd1bfbae2e7441c5 by the Stage D docs wave; refresh before rc2 -->`.
- Version sources match FACTS `version_occurrences`: `package.json:3`, `src-tauri/Cargo.toml:3`,
  `src-tauri/tauri.conf.json:4`, `sidecar/app.py:329`, `src/lib/plugin-bootstrap.ts:38` and `Cargo.lock:5486-5487`,
  all `0.8.0`. The seven other `Cargo.lock` hits (`281,290,758,2426,2443,3351,3368`) and `package.json:77` (a
  prettier plugin) match. The pre-bump grep count of 99 (55 prose, 44 source) reproduces at S. The CLAUDE.md
  "Versioning & process" quote (`CLAUDE.md:274-279`) is verbatim.
- `hostSatisfies` (`plugin-runtime.ts:151-157`), `checkCompatibility` (`:403,411`), the doc comment at `:133`, and
  the three manifests' `requiredHostVersion: "0.8.0"` all match. Treating the pins as a minimum host version is
  correct.
- The non-bump fixture lines (`test_data_cache.py`, `test_schema_version.py`, `SettingsPanel.test.tsx:886` with no
  version assertion, `plugin-agents.test.ts:77`, `MarketplacePanel.test.tsx:40`, `workspace.test.ts:1574`) are as
  described.
- The `ci-local` chain is verbatim (from `package.json:20`), and `lint` is `eslint . && node
  scripts/audit-design-tokens.mjs`. CI pins pnpm `10.32.1` and python `"3.13"`: `test.yml:32,41`,
  `build.yml:36,45`, `lint.yml:32,41`. `lint.yml:71` runs `pnpm lint`, so the token audit now runs in CI too. That
  makes DECISIONS §2.16's "not wired into `ci-local` or any workflow" itself stale, which is not the runbook's
  problem.
- §0 local probe: `which` shows `python` and `pytest` not found, and `python3` at `/opt/homebrew/bin/python3`.
  `sidecar/.venv/bin/python --version` gives `Python 3.13.13`, and that venv has `pip`, `pytest`, `ruff` and
  `pyinstaller`. `pnpm --version` gives `10.32.1`, and `rustc -vV` gives `host: aarch64-apple-darwin`.
- `sidecars:build = node scripts/ensure-all-sidecars.mjs --force`. `ensure-all-sidecars.mjs` loops `SIDECAR_SPECS`
  and exits 1 on the first failure (`:19-27`). `signDevBinary` is called after the copy (`sidecar-specs.mjs:307`).
  `VYSTED_SKIP_DEV_SIGN` is honoured at `macos-dev-sign.mjs:38`, and the `[dev-sign] signed` log is at `:45`.
  `IGNORE_FILE` is at `sidecar-staleness.mjs:41`, and `assertAllFresh` reads `spec.stale` (`sidecar-specs.mjs:206-210`).
  Register: `R15-CODE-PLATFORM-026`, `R15-RELEASE-005`, `-006` and `R15-CROSS-PLATFORM-002` are `fixed`;
  `R15-CROSS-PLATFORM-001` and `R15-RELEASE-001..004` are `blocked_tier4`. Register `counts` is 652 entries.
- Three PyInstaller sidecars, `externalBin` at `tauri.conf.json:40-44`, `beforeBuildCommand` at `:10`, `targets`
  `["deb","appimage","nsis","app","dmg"]` (`:32`), and `createUpdaterArtifacts: false` (`:45`).
- Smoke test: `assertAllFresh` is imported at `:80`, `_assertAllFresh` is at `:857-859` and is called at `:873`. The
  messages `[smoke] FAILURES:` (`:891`), exit 1 (`:898`) and `[smoke] all sidecars booted cleanly.` (`:900`) match.
  The script's header states it is attended-safe and uses its PID ledger.
- §7 keychain facts: `keychain.rs:6-10,37-45` (release uses the OS keychain, service `vysted-terminal`; dev uses
  `dev-keystore.json`), `Entry::new(SERVICE, account)` (`:68`), and the `app-meta:` namespace (`keychain.ts:42,100-101`).
  The `security find-/delete-generic-password -s vysted-terminal -a app-meta:...` commands target the right items,
  and `find` without `-w`/`-g` prints no secret. The `DisclaimerFlow.tsx:4-6,35` licence line (PolyForm Strict
  1.0.0 or commercial) is quoted verbatim. The RC1_GATE_PLAN phase-5 quote matches (`:21`).
- DECISIONS quotes for §2.8, §2.9, §2.10 and §2.11 (`:133-172`) are verbatim, and each NEEDS-OPERATOR or
  operator-only item in the draft maps to one of them. Nothing claims that signing, notarization, a release
  pipeline or an updater exists: all three are described as blocked. The macOS clean-profile proof is assigned to
  the lead, not this wave.
- `v0.8.0` is an annotated tag on `f45019f6` with message `v0.8.0 — Phase 8 deep audit`. CHANGELOG `:7`, `:209`,
  `:669`, `:760` and `:1008` match, and there is no `## v0.8.0` heading.
- `Cargo.toml:34` keyring features; `test_search_extract.py:467` has `encoding="utf-8"`; the
  `test_tests_encoding.py` docstring names R15-CROSS-PLATFORM-002.
- Hygiene: `grep -i -c laya` gives 0, and the phrase banned by scope change 2 is absent. No trading feature is
  described or proposed; the only hit is the CHANGELOG heading "trading removed". No key, token or keystore content
  appears; `TAURI_SIGNING_PRIVATE_KEY` occurs only as a quoted variable name.
