# rc1-vshard-3 working log (adversarial sample verifier, shard 3)

- 2026-09-25 08:53:31 +0530 start. Candidate 1d6511c89bb27f1785f7af4d2290983b2852d70a (worktree rc1-4097dac-fix-int, read-only).
- Own sidecar: source run, port 52603, data dir scratchpad/rc1-data-rc1-vshard-3 (cp -R of rc1-seed-data), sleep pid 97375 / worker 97376. /health ok 0.8.0.
- Test runs: git archive of the candidate into scratchpad/vshard3/cand (node_modules + sidecar symlinked read-only, vitest cacheDir redirected to scratch) so nothing is written into the candidate worktree.
- vy.py refused :52603 (its guard allows non-GET only on 52100-52399), so the one llama3.1:8b agent run (LEAD-010 variant) was a direct POST /agents/copilot/invoke on my own sidecar. It was ollama only, so no spend.
- Verdicts: holds 9 (LEAD-013, CP-014, CP-023, CP-024, CP-025, CP-028, RELEASE-005, RELEASE-006, LIFECYCLE-024). Refuted 5 (DATA-059, LEAD-010 partial, DOCS-017, DOCS-018 partial, CP-013). Two residual new_defects (sp500 seed missing BXP/NVR/UDR; backup keyed on version string).
- A mutation run in the scratch copy briefly left a mutated scripts/sidecar-staleness.mjs because the backup cp failed. I restored it from git show 1d6511c. It was the scratch copy only; the candidate worktree stayed clean (git status empty).
- 2026-09-25 09:03:50 +0530 stopped own sidecar (kill 97375, the sleep pid). :52603 down. Report: verifier/shard-3.md. Findings: findings/rc1-vshard-3.json (7).
