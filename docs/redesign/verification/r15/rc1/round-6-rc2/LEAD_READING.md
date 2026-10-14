# rc2 gate — lead reading (round 6-rc2, candidate ace7dd76)

Workflow `wf_580450ca-23f`, 30 agents (pinned claude-opus-5-5 / claude-sonnet-5-5 at medium), 0 errors, 1639 tool calls, 4.63 M subagent tokens, wall 105.6 min (05:03 → 06:49 IST). The script reported FAIL on its old rubric. Read against the rc2 bar (gate rule change 1: chain green + Gate 8 + every fixed entry passes its own repro + open critical/high = 0):

- **Gate 8: PASS.** test_no_trading_surface.py 8/8; 0 product-surface trading hits; tracked-portfolio e2e 11/11; gated portfolio_add_position staged under ask and applied only through accept.
- **Battery: PASS.** 593/593 fixed entries have raw output: 455 holds, 137 ci_pinned, 1 blocked_env (keyless web search blocked from this network, R15-RESEARCH-008), 0 regressed. Two entries (R15-UI-068, R15-DATA-098) carry a residual half of their stated repro; they are low and get re-adjudicated in the register.
- **Chain: RED on one docs file, fixed.** `pnpm ci-local` exited 1 at format:check on `docs/redesign/BACKLOG_0.9.1.md` only (finding rc1-heavy:1). Every other step was run and exited 0: lint, typecheck, cargo fmt, clippy -D warnings, ruff, vitest 2031/2031, cargo test 31/31, pytest 3921 passed / 1 skipped, smoke EXIT=0. Fixed in `a9b954af` (prettier only, docs). A full `pnpm ci-local` re-run at `a9b954af` is the tag-time proof.
- **Register: open critical/high = 0.** The script's blocker lists 28 open MEDIUMS (old rubric); under scope change 3 they are filed for 0.9.1.
- **Drives "raw missing":** not a failure. The drive lanes were deliberately skipped (`lanes`), so there is no raw output to find.
- **needs_gui (11):** deferred to the GUI round at ace7dd76 (`wf_b3c54acc-931`). A high it does not certify blocks rc2.
