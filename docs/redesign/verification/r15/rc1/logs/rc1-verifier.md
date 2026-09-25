# rc1-verifier working log

- Candidate 1d6511c89bb27f1785f7af4d2290983b2852d70a (worktree rc1-4097dac-fix-int, clean, FF of 4097dac4).
- 004-r4-experience-rebuild head 29b9ae9b has moved past 4097dac with docs-only commits (36 files, all docs/); candidate is NOT a fast-forward of current 004.
- Own sidecar: source run from the candidate worktree, port 52312, data dir scratchpad/rc1-data-rc1-verifier (cp -R of rc1-seed-data). Sleep pid 18451 (bash wrapper 18449, python 18452). Log scratchpad/rc1-verifier/sidecar.log.
- Spend ledger total est_usd 0.2011 before this role.
- 2026-09-25T04:22:16Z findings/rc1-verifier.json written (22 entries); :20 corrected on recount to 11 of 20 OpenRouter scenario runs ending in upstream error (was 13).
- Gate: ci-local PASS, smoke PASS, Gate 8 no-trading PASS (not refuted), Gate 8 tracked portfolio PASS (round trip + ASK-gated agent write), data packs PASS (24/24 complete; 283 calls = 263x200 + 16x502 BSE-403 env + 4x429).
- FAIL: register (5 open c/h/m + LEAD-010 uncertified), agent scenarios (sc5 reproduces; transcripts incomplete, written 05:26-05:42 IST before fix commit 23f2ab34), owner-drives (india-all replay exposes MANIKA null-mcap-first sort, rc1-verifier:15), battery (160/376 fixed ids no raw; set-12/46 empty; no battery-3/5 findings), fix loop (sc5 + fix-r2-triage:1 open), adversarial sample (14/14 refuted at sha).
- DEFERRED: GUI round (presence.log one line, no vr15-rc1 screenshots); 9 needs_gui ids unchanged.
- 1d6511c8 is not an ancestor of 004-r4-experience-rebuild (29b9ae9b); 23 non-doc files differ. Tag must be exactly this sha or the gate re-runs. Not tagged (verdict FAIL; verifier never tags).
- Wrote R15_GATE_RC1.md and rc1/VERDICT.md. Stopping own sidecar via kill of its sleep pid 18451.
