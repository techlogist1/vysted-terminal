# rc1-verifier working log (gate round 3)

- 2026-09-26 23:00:59 IST start. Candidate worktree HEAD = 5ff9be041180c1c316ad48ceb120a23549a7575a. No previous rc1-verifier round-3 files found (fresh start).
- Own sidecar: source of the candidate worktree, port 52312, data dir scratchpad/rc1-round-3-data-rc1-verifier (cp -R of rc1-round-3-seed-data), sleep pid 7900 (worker 7901). /health ok, openbb-mcp available.
- 2026-09-26 23:11:07 Gate 8 own probes: openapi 101 paths, 0 order/broker/kill/audit routes (verifier/gate8/openapi-paths.txt); catalog=TOOL_SCHEMAS=KNOWN_TOOL_IDS=56, MCP 40, no order-shaped id (tools-own.txt); rg sweeps rg-*.txt all classified false positive/disclaimer/historical; Settings sections Providers/Research/Region/Keybindings/Advanced; terms text first-launch-terms.txt; gated add on llama3.1:8b staged not applied, ledger unchanged (agent-01*, pf-03); order attempt under auto: refused, no tool call (agent-02*); frontend accept of place_order/submit_order fails closed (frontend-gate-probe.run.log); safety diff vs r13-bedrock 36 paths, 2 identical, 34 differing all with rows + full diff (SAFETY_SURFACE_ROWS.tsv, safety-surface.diff); no audit_orders table in any data db.
- 2026-09-26 23:34:36 Ran the owner-drive spot checks on :52312.
  - Screener agrees with the drive: 08b zero-result 49/1/0, 06/07 return 422, 02 formula error.
  - Failure-inducer data061 agrees: /quotes/ZZZZNOTREAL returns 404 not_found.
  - Onboarding resolve agrees: zomato resolves to ETERNAL with the rename.
  - onboarding-stranger round 3 has no raw output, so the item is a harness gap.
- 2026-09-26 23:34:36 Adversarial sample.
  - DATA-005 and LEAD-026: the own repros do not reproduce, so neither refutation stands.
  - DATA-016: the own repro does not reproduce.
  - New HIGH adjacent: ADR P/B is served ok on a mixed basis. P/S is withheld for the same reason (yfinance_provider.py:420 _MIXED_BASIS_RATIOS). Evidence: verifier/sample/DATA-005-adjacent-pb-vs-ps.txt.
  - Lows: LEAD-026 suffixed/untraded reason null, DAL 52w dates ok while the values are withheld, TM EPS, workflow 500, workspace 404, unknown-symbol statements returning 200 empty.
- 2026-09-26 23:34:36 Classified all 850 rg sweep hits (verifier/gate8/rg-classified.tsv), 0 UNCLASSIFIED. Checked the data packs: 24 collected, all 200. Battery raw covers 27 of 392. Probed CODE-DATA-023 and could not reproduce it (fixed-uncertified).
- 2026-09-26 23:34:36 Wrote docs/redesign/verification/R15_GATE_RC1.md, which replaces the round-2 sheet (preserved in git at 3cd62b02). Also wrote round-3/VERDICT.md and round-3/findings/rc1-verifier.json (24 entries). Verdict FAIL. Tag sha if a later round passes: 5ff9be041180c1c316ad48ceb120a23549a7575a (never tagged).
- 2026-09-26 23:34:42 Stopped own sidecar: kill 7900 (sleep); worker 7901 exited via stdin-EOF watchdog.
