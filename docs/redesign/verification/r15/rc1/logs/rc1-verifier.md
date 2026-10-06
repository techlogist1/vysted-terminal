# rc1-verifier working log (fresh adversarial gate verifier, Opus 5.5)

Candidate under test: `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2` (committed 2026-09-26 06:01:18 +0530).
Branch 004 is now at 8ca67fe6. `git diff --name-only 4c6dfe8c HEAD` lists only files under docs/, so the tagged tree must be 4c6dfe8c.
Scratch: `$S/rc1-verifier-g2` (S = session scratchpad). Evidence: `docs/redesign/verification/r15/rc1/verifier/g2/`.
I did not read any other agent's conclusions: PREFLIGHT, GATE8, REGRESSION, SCENARIOS, OWNER_DRIVE, drives/*.md, BATTERY, battery/INDEX.*, battery/set-*.md, DATAPACK, datapack.json, FINDINGS.*, fix-r*/PLAN.md, INTEGRATION, RECHECK, GUI_ROUND, other logs/*.md or DECISIONS.
A previous attempt of this role left logs/rc1-verifier.md (10:44). I did not read it. I renamed it to `logs/rc1-verifier.prior-attempt-2026-09-26T1044.md` to preserve it.

## Setup
- The rc1-cand worktree stayed read-only. I made a `git archive 4c6dfe8c` export at `$G/cand`, with node_modules linked per entry (the .vite caches excluded), the sidecar/.venv symlinked, and the src-tauri/binaries copied from rc1-cand. rc1-cand's binaries were built 06:08-06:10 IST, after the last sidecar commit (227c1e25, 04:48) and after the candidate commit. The smoke freshness gate agreed.
- My own sidecar ran on :52312 from `$G/cand/sidecar`, data dir `$S/rc1-data-rc1-verifier` (seed copy), with the shared MCP ports :52153/:52154 for reads only. It started at 17:31:54 IST with sleep pid 87149, which I killed at the end; I checked that :52312 was free afterwards. A stale attempt on :52312 had been serving fix-int source; I killed it by its own sleep pid (13475) and rebooted from the export.
- The shared stack :52152-4 was never restarted or written through. I did not touch the operator's app or his Application Support directory. I did not use OpenAI-direct.
- Local-model calls took the lock at /tmp/vysted-r15-ollama.lock (mkdir, trap release), one call per hold.

## Gate 8 (re-proved live)
- G8-1: I took the route list from my own GET /openapi.json (openapi-paths.txt). tools.py gave the tool lists: catalog 56, TOOL_SCHEMAS 56, KNOWN_TOOL_IDS 56, MCP projected 32, live MCP 40. None is trading-shaped. I ran rg sweeps over src, sidecar, src-tauri, plugins and docs (rg-*.txt) and classified the hits: 0 product-surface. What remains is historical records, the D81 removal notes, and false positives (margin as in gross margin, "leverage" in prose, keychain migration keys).
- G8-2: POST/PUT on /orders, /brokers/kite/*, /safety/kill-switch*, /audit-log and /margins all return 404. /portfolio/positions returns 405, because the legacy ledger is read-only (g8-order-paths.txt). An order attempt on llama3.1:8b under ask produced one staged data write (portfolio_add_position, not applied) and the refusal text "cannot assist with buying or selling of shares" (g8-order-attempt.*).
- G8-3: in a jsdom harness against :52312, accept of place_order, submit_order and propose_order each returned "failed" (unknown action) and left the ledger unchanged (g8-portfolio-steps.json).
- G8-4: there is no audit_orders table in any data-dir DB, before or after the run (datadir-tables-*.txt).
- G8-5: diffing the safety surface against r13-bedrock, every differing path has a row and a reason (safety-surface.tsv, 36 rows). The surface diff from the candidate to HEAD is empty.
- Tracked portfolio: add AAPL and RELIANCE.NS with cost basis, then save and read back from the sidecar: 2 rows. P&L equals (price - cost) x qty against live quotes: AAPL 805.35 USD, RELIANCE.NS 1260 INR. The CSV export path works (the non-Tauri fallback, 3 lines). Deleting AAPL leaves [RELIANCE.NS] on read-back. The gated llama write (TCS 5 @ 3500) stages under ask, and accept applies it: 2 rows on read-back.
- Known lows seen again: rc1-gate8:1/2/3. The CSV carries raw floats, and llama invented cost_basis 0 on the order-attempt write. They are staged, not applied.

## Chain
- ci-local: `$G/ci.sh` ran on the export. The stages match pnpm ci-local after install: lint (eslint plus the design-token audit), format:check, typecheck, cargo fmt, clippy -D warnings, ruff check, ruff format --check, vitest (152 files / 1831 tests), cargo test (19), pytest (3596 passed, 1 skipped). EXIT=0 at 12:13:39Z (verifier/g2/ci-local.log). The deviations were forced by the read-only rule: no `pnpm install --frozen-lockfile` (node_modules linked from rc1-cand), and no ensure-all-sidecars rebuild (binaries from rc1-cand, freshness-gated). The lane's own logs/ci-local.log is from 25 Sep at a different sha, so it is not evidence for this candidate.
- smoke: node scripts/smoke-test-sidecars.mjs on the export gave SMOKE_EXIT=0 at 12:16:39Z. All 3 sidecars booted. Health 0.8.0, 13 agents, MCP ready with 40 tools, ICONIKSPEV resolved, BSE and NSE probes ok (verifier/g2/smoke.log).

## Scenarios (raw transcripts only)
- 33 files: 20 OpenRouter (or-*), all written 25 Sep 05:26-05:31, and 13 llama. Of the llama files, 7 are from 25 Sep and 6 from 26 Sep 06:32-06:46: rb4-arrange, sk4-sify-v2, sk3-elcidin-v2, rb2-portfolio, sk1-amal-v2, sc1-tcs-pe-a.
- Agent-runtime commits between the 25 Sep transcripts and the candidate include 4bc0bd3e, 51464b15, 227c1e25, 2e8593eb, 4ee83499 and 26dc3aab. So the hosted-lane transcripts do not evidence 4c6dfe8c, and the self-consistency property (sc*-b and -thread) has no candidate-era run.
- In the 6 candidate-era runs, the rb2 and rb4 writes were correctly staged-not-applied with an honest "awaiting your review". sk4-sify-v2 says "6 ordinary shares" right after "not available", and misconverts ₹4,651 cr to about $57.65M. sk3-elcidin-v2 states an impossible 52w-low/current relation. sk1-amal-v2 says the P/E is unavailable after calling price_data rather than fundamentals. sc1-tcs-pe-a prints an unrounded 15.151735. These are local-lane model weaknesses (the LEAD-030/037 class) and are filed as notes.

## Owner drives
- All 8 groups have evidence under surface/<group>/rc1/ written after the candidate: composer-chat 8 files, failure-inducer 10, onboarding-stranger 6, panels-layouts 10, portfolio-notes 3, research-briefs 14, screener 7, settings-plugins 1 (a 4c6dfe8c re-drive section appended to rc1-redrive.md).
- I spot-checked 2 on my own sidecar and both match: screener (spot-screener-07.json) and panels-layouts (spot-panels-layouts.txt).

## Battery (raw only)
I walked rc1/battery/raw/** for the 391 fixed ids (390 certified by stage-c plus CODE-DATA-023, which has no stage-c row).
- 76 ids have no raw file: AGENT-006 AGENT-009 AGENT-013 AGENT-015 AGENT-025 AGENT-029 AGENT-031 AGENT-050 AGENT-051 AGENT-058 AGENT-059 AGENT-088 CODE-AGENT-002 CODE-AGENT-012 CODE-AGENT-033 CODE-DATA-002 CODE-DATA-003 CODE-FRONTEND-001 CODE-FRONTEND-002 CODE-FRONTEND-005 CODE-FRONTEND-006 CODE-FRONTEND-007 CODE-FRONTEND-016 CODE-FRONTEND-017 CODE-FRONTEND-018 CODE-FRONTEND-019 CODE-FRONTEND-020 CODE-PLATFORM-002 CODE-PLATFORM-003 CODE-PLATFORM-005 CODE-PLATFORM-011 CODE-PLATFORM-019 CODE-PLATFORM-037 CODE-RESEARCH-001 CROSS-PLATFORM-004 DATA-077 DATA-083 DATA-093 DATA-097 LEAD-001 LEAD-003 LEAD-007 LEAD-008 LEAD-009 LEAD-011 LEAD-031 LIFECYCLE-002 LIFECYCLE-003 LIFECYCLE-005 LIFECYCLE-007 LIFECYCLE-010 LIFECYCLE-013 LIFECYCLE-022 RESEARCH-014 RESEARCH-023 RESEARCH-032 RESEARCH-033 UI-003 UI-005 UI-007 UI-011 UI-013 UI-017 UI-019 UI-024 UI-026 UI-027 UI-028 UI-031 UI-034 UI-035 UI-036 UI-037 UI-040 UI-049 UI-057
- 84 ids have raw output only from before 2026-09-26 06:01 (the candidate commit): AGENT-001 AGENT-002 AGENT-003 AGENT-004 AGENT-011 AGENT-014 AGENT-018 AGENT-021 AGENT-024 AGENT-036 AGENT-037 AGENT-039 AGENT-041 AGENT-043 AGENT-054 AGENT-056 AGENT-061 AGENT-080 AGENT-081 AGENT-084 CODE-AGENT-007 CODE-AGENT-011 CODE-AGENT-013 CODE-AGENT-016 CODE-FRONTEND-003 CODE-FRONTEND-008 CODE-FRONTEND-009 CODE-FRONTEND-010 CODE-FRONTEND-011 CODE-FRONTEND-012 CODE-FRONTEND-014 CODE-PLATFORM-021 CODE-PLATFORM-029 CODE-PLATFORM-053 CODE-PLATFORM-072 CODE-RESEARCH-002 CODE-RESEARCH-003 CODE-RESEARCH-004 DATA-003 DATA-011 DATA-014 DATA-031 DATA-042 DATA-075 DATA-081 DATA-085 DATA-089 DOCS-004 DOCS-005 DOCS-016 LEAD-002 LEAD-005 LEAD-012 LEAD-014 LEAD-015 LEAD-019 LIFECYCLE-009 LIFECYCLE-012 LIFECYCLE-014 RESEARCH-006 RESEARCH-008 RESEARCH-009 RESEARCH-010 RESEARCH-012 RESEARCH-013 RESEARCH-017 RESEARCH-018 RESEARCH-019 RESEARCH-021 RESEARCH-022 RESEARCH-026 RESEARCH-027 RESEARCH-030 RESEARCH-037 UI-001 UI-021 UI-023 UI-029 UI-030 UI-032 UI-038 UI-039 UI-085 UI-092
- CODE-DATA-023: raw/set-71/CODE-DATA-023_probe.txt shows the comments describing composition only. `git grep` at 4c6dfe8c finds no stale counts in screener_universe_india.py or models/screener.py, so it holds.

## Data packs (raw only)
battery/collected/*.json: 24 names, complete=true. 14 (P1-P14) were collected 26 Sep 06:31-06:39 on :52313, after the candidate. 10 (P15-P20, S1-S4) were collected 25 Sep 05:32-05:39, before b4585d7a (earnings currency), aa76a7ea (scrip-code gate), 6a9a48ef (US former names) and 6a82064d (screener currency sort). Shareholding returns 502 on 17 of 24 names, which is my new finding rc1-verifier:1 (BSE SHP 403 with plain httpx).

## Fix loop
rc1-drive-research-briefs:2 reproduces at 4c6dfe8c (fixloop-briefs2-citecheck.txt). The r1 and r2 fixes live only on fix-int (81fbfe91), and round-2's recheck says they do not certify either. My concurrence with each triage rejection is in findings/rc1-verifier.json (keys rc1-verifier:26-30; the four-area concurrences are keys 18-25).

## Adversarial sample (my own re-runs at 4c6dfe8c)
- Refuted: AGENT-019, AGENT-093, DATA-002 (code-level), DATA-113, LEAD-028, DATA-064, DATA-059, AGENT-053, RESEARCH-015. The evidence is in the adj-*/spot-* files.
- Plausible, code-level only: CODE-PLATFORM-013 (setEnabledMap({}) on reset) and AGENT-010 (no explicit yf.Search timeout).
- Round-2 shard claims I did not re-run, listed as open questions: CODE-FRONTEND-002, AGENT-045, DATA-112, DATA-066, UI-090 and the RESEARCH-024 news-lane adjacent.
- New: the BSE SHP 403 (high) and the MCP /workspaces 404 (high).

## Time line (UTC, from date)
- 12:08:23 ci start. 12:13:39 ci EXIT=0.
- 12:14:14 smoke start. 12:16:39 SMOKE_EXIT=0.
- 12:18 AGENT-019 probe. 12:19:18 live refutation probes. 12:20:42 AGENT-093 probe. 12:22:57 shareholding probe. 12:23:20 BSE SHP probe. 12:26:02 RESEARCH-015 probe.
- Sidecar stopped after the probes.
