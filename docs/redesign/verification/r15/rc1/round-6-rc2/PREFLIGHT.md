# rc1-preflight, gate round 6-rc2

- Candidate: ace7dd768c3b809b0e72b20b20cfc94eea2368bd, ancestor of 004-r4-experience-rebuild (local 004 = 9c25499c, 2 docs/chore commits ahead; origin/004 = ace7dd76). Newest r15 tag: r15-rc1. No worktree-agent-rc1-* worktree for this round; older rc1 branches exist (not ours).
- Worktree: scratchpad/rc1-round-6-rc2-cand, HEAD ace7dd76 (git worktree add --detach).
- pnpm install --frozen-lockfile: EXIT=0 (logs/preflight-install.log).
- node scripts/ensure-all-sidecars.mjs (no --force): EXIT=0, all three binaries built fresh 05:06-05:09 (logs/preflight-sidecars-1.log).
- Seed: scratchpad/rc1-round-6-rc2-seed-data from vysted-iso/data (sqlite .backup x7, workspaces, searxng, notes, resolver_masters; keystore {"secrets": {}, "migrated": true} 0600; no audit_log.db).
- Shared stack: vysted-iso/pids.json did not exist and ports 52152-54 were free (prior stack shut down 04:44); no listed pid killed. Orphan sleeps 91869/91872/91875 (02:41, ppid 1) left untouched. Booted openbb 52153 (sleep 47367), edgar 52154 (sleep 47365), main from worktree sidecar/ on vysted-iso/data 52152 (sleep 47368); new pids.json written. /health ok v0.9.0, openbb-mcp available (fundamentals provider reads "yfinance (openbb-mcp failing)").
- Env: llama3.1:8b present; /search/status tier t1_keyless available; /search/searxng/status degraded (engines blocked: CAPTCHA/rate limit, container running); disk 119Gi free; idle 494 s; frontmost Finder.
- Register (JSON direct): fixed 593, open 81, blocked_tier4 35, needs_gui 11, removed_with_feature 14, not_a_defect 6 (740). Open critical/high = 0; open medium = 28.
- sec-edgar-mcp bound 52154 after ~90 s cold start (pid 47380); /sec/filings/AAPL -> 422 (route live, not 501). /mcp/status ready, toolCount 39.
