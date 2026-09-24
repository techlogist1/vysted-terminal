<!-- DRAFT at f444479031d7d493b7955b9af041d18e7c7a40cc by the Stage D docs wave; refresh before rc2 -->

# Stage D docs-and-scans index

- **Sha:** f444479031d7d493b7955b9af041d18e7c7a40cc
- **Mode:** draft
- **Cap:** 6
- **Collated (UTC):** 2026-09-24 17:46:03

## Files

| File | Lane | Status | Critic findings | Open questions for the lead |
|---|---|---|---|---|
| README.draft.md | readme | REVISED | 9 (wrong 6, missing 2, stale 0, unverifiable 1) — [critic/README.md](critic/README.md) | Keep the "no release pipeline / unsigned" framing verbatim at rc2 or soften once R15-RELEASE closes; 7 vs 8-provider framing (OpenRouter); whether 0.9.0 bump lands before rc2 (still 0.8.0 at f444479); whether ci-local's bare-python precondition gets fixed in package.json itself. |
| RELEASE_RUNBOOK.draft.md | runbook | REVISED | 11 (wrong 4, missing 6, stale 0, unverifiable 1) — [critic/RELEASE_RUNBOOK.md](critic/RELEASE_RUNBOOK.md) | No rc1 ci-local/sidecar-build/smoke-test log exists yet — steps 3-5 rest on a Stage C proxy, not a real run; dmg filename pattern unverified; §10 Windows entirely NEEDS-MANUAL-CHECK; rollback-.dmg-on-hand unknown; confirm R15-RELEASE-001/002/003/004 still open before promoting. |
| OPERATOR_BRIEFING.draft.md | briefing | REVISED | 10 (wrong 7, missing 1, stale 2, unverifiable 0) — [critic/OPERATOR_BRIEFING.md](critic/OPERATOR_BRIEFING.md) | R15-LEAD-022 status (run-state says fixed pending batch-10, register still says open); R15-UI-083/UI-050 needs_gui reclassification not yet in the register; batch-10's 11-id blocked_tier4 reclassification not yet landed; batch-10 evidence dir does not exist at this sha (placeholder only). |
| RELEASE_NOTES.draft.md | notes | REVISED | 14 (wrong 11, missing 3, stale 0, unverifiable 0) — [critic/RELEASE_NOTES.md](critic/RELEASE_NOTES.md) | Fixed/"what changed for you" built by cross-referencing CHANGELOG batch-2..9 prose against the register — batch-9 frontend-shell items described as delivered in CHANGELOG but still open in the register were omitted, re-check at rc2; whether DECISIONS_FOR_OPERATOR §2.1/§2.2 belong in a public release body; no independent source for the "Windows unverified" line (inferred); re-run both VERIFY cross-checks at rc2; whether to strip the two VERIFY comments before publishing. |
| CURRENT_STATE.draft.md + CURRENT_STATE.draft.diff + BLOCKERS.draft.md + BLOCKERS.draft.diff | state | REVISED | 11 (wrong 6, missing 3, stale 2, unverifiable 0) — [critic/STATE.md](critic/STATE.md) | Vitest/pytest/cargo-test counts unverified this wave (stale pre-R15 619/942 figures still cited with VERIFY markers) — re-run pnpm ci-local before rc2; safety-UI-screenshots BLOCKERS item mostly moot (4/5 components absent) but a DisclaimerFlow-only ask is new, confirm framing; T4-ccxt/T4-bare-commandids/T4-kite-manifest line left untouched pending lead split; R15-AGENT-064 grouped at the end of the medium subsystem list (cosmetic ordering only). |
| SECRETS_SCAN.md + SECRETS_SCAN.json | secrets | DONE | n/a (scan; 0 real_or_unknown, 0 pushed_real_or_unknown) | None — R15_BRIEF*/local/ excluded from tree at this sha (absent); gitleaks/trufflehog not installed, not cross-validated. |
| DEPS_LICENCES.md + DEPS_LICENCES.json | deps | DONE | n/a (scan; 0 mismatches scored, 5 flagged rows) | r-efi's LGPL branch is UEFI-only, target-gated off real build targets — confirm the lead treats it as non-bundled; 9 distinct AGPL/GPL/LGPL packages compile directly into the openbb-mcp/sec-edgar-mcp/main-sidecar PyInstaller binaries — legal-review item against the PolyForm Strict core, not resolved here. |
| LICENCE_CHECK.md | licence | DONE | n/a (scan; 1 mismatch, 1 Tier-1) | CLAUDE.md:57-58 still says "AGPL-3.0 + commercial dual license" — stale since the 23 Sep 2026 relicense to PolyForm Strict 1.0.0 + commercial; fix already drafted in docs/redesign/CLAUDE_MD_PROPOSAL.md:76, tracked at DECISIONS_FOR_OPERATOR.md §3.4; AGENT_TOOLUSE_PLAN.md still reads AGPL-3.0 throughout (dated, pre-relicense, out of D83 scope) — worth a one-line superseded-note. |

## How to promote at rc2

1. Run this workflow with mode `refresh` first, at the promotion sha.
2. For each `.draft.md`: strip line 1 (the `<!-- DRAFT ... -->` header) and everything from the line `<!-- critic-footer -->` down.
3. Apply to target paths:
   - `README.draft.md` → `README.md`
   - `RELEASE_RUNBOOK.draft.md` → `docs/RELEASE_RUNBOOK.md`
   - `OPERATOR_BRIEFING.draft.md` → `docs/redesign/OPERATOR_BRIEFING.md`
   - `RELEASE_NOTES.draft.md` → the GitHub release body + the `CHANGELOG.md` v0.9.0 section
   - `CURRENT_STATE.draft.md` / `CURRENT_STATE.draft.diff` → `docs/CURRENT_STATE.md`
   - `BLOCKERS.draft.md` / `BLOCKERS.draft.diff` → `BLOCKERS.md`
4. The two `.draft.diff` files apply with `patch -p1` from the repo root.
