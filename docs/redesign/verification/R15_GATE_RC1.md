# R15 gate: rc1

**Verdict: FAIL.** Do not tag rc1.

- **Verifier:** rc1-verifier (Opus 5.5, xhigh), a fresh adversarial pass. Checked on 2026-09-25 (UTC).
- **Candidate sha:** `1d6511c89bb27f1785f7af4d2290983b2852d70a` (branch `worktree-agent-rc1-4097dac-fix-int`, worktree clean).
- **Evidence root:** `docs/redesign/verification/r15/rc1/verifier/rc1-verifier-evidence/` (abbreviated to `EV/` below).
- **Findings:** `docs/redesign/verification/r15/rc1/findings/rc1-verifier.json` (22 entries).
- **Excerpts behind each line:** `docs/redesign/verification/r15/rc1/VERDICT.md`.

## Gate items

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Register criterion | **FAIL** | `EV/register-census.txt`, `EV/lead028-open.txt`: 5 c/h/m entries are open (R15-AGENT-017 high; R15-AGENT-049, R15-LEAD-028, R15-RELEASE-007, R15-UI-088 medium), and R15-LEAD-010 (high) is `fixed` but certified nowhere. Beyond that, 14 certified entries fail when re-run (item 12). |
| 2 | Gate 8: no trading path | **PASS** | `EV/openapi-paths.txt` has 111 routes: no order, broker, kill-switch or audit route, and the only portfolio route is `GET /portfolio/positions`. `EV/tool-lists.json` has 56 catalog and 40 MCP tools, none for orders or brokers. `EV/rg-summary.txt` and `EV/rg-code-hits-a.txt`: every code hit is a negation or a false positive. Also checked: the TOS text, the Settings sections, and that the kill switch and audit log are deleted. One inert residue: `EV/gate8-plugins-list.json` (a low finding). |
| 3 | Gate 8: tracked portfolio | **PASS** | `EV/portfolio-roundtrip.json` (the real PortfolioPanel against my sidecar, with only Tauri IPC stubbed): add with cost basis, blob read back, P&L against live quotes, CSV path, delete, read back. `EV/agent-01-add-position.jsonl` and `EV/agent-02-proposed-action.json`: llama3.1:8b under ASK proposes a write; the store, blob and ledger stay unchanged until it is accepted, then the blob reads back TCS. |
| 4 | ci-local | **PASS** | `r15/rc1/fix-r2/ci-local.log` run 1 at the sha rebuilt the stale vysted-sidecar. Every stage is clean. vitest 1825/1825, cargo 19, pytest 3150 passed and 1 skipped, `EXIT=0`. The final run 2 also gave `EXIT=0` at 02:59:52Z. |
| 5 | smoke | **PASS** | `r15/rc1/fix-r2/smoke.log` at the sha: `SMOKE_EXIT=0` at 02:55:29Z. 3 sidecars, 13 agents, mcp toolCount 40. |
| 6 | Agent scenarios | **FAIL** | `r15/rc1/scenarios/*.jsonl` were written between 05:26 and 05:42 IST, after 4097dac4 (04:55) but before the first fix-round commit 23f2ab34 (07:11) and the candidate (08:15). 11 of 20 OpenRouter runs end in "Upstream error from Nvidia: Service temporarily ..." with no answer. ollama-sc1 is 0 bytes. sc3 (portfolio) and sc4 (SMR revenue) never completed on either lane. `EV/unclosed-sc5-sify-llama.jsonl`: at the sha the SIFY ADR ratio is still fabricated ("1:2"; the truth is 1:6). |
| 7 | Owner-drives | **FAIL** | Raw evidence exists for all 8 groups under `surface/*/rc1/`. My spot-checks hold for settings-plugins (`EV/drive-spot-settings-plugins.txt`), the screener zero-evaluated case (`EV/drive-spot-screener-zero.json`) and the portfolio panel (item 3). But replaying the screener drive found a missed defect: `EV/drive-spot-screener-india-all.json` and `EV/new-manika-sort-custom.json` rank a null-market-cap row first in a market_cap-desc sort. The drive's own raw output at 4097dac4 is misordered too (MOTHERSON 1.7T above RELIANCE 16.5T), yet the drive scored it "ok". |
| 8 | Fixed-name battery | **FAIL** | `r15/rc1/battery/raw/**`: 160 of 376 fixed ids have no raw output (1 critical, 48 high, 109 medium, 2 low). raw set-12 and set-46 are empty. set-37, 45, 55 and 57 are absent from the numbering. `r15/rc1/findings/` has rc1-battery-0, 1, 2, 4, 6 and 7 but no file for workers 3 and 5. |
| 9 | Data packs | **PASS** | `r15/rc1/battery/collected/*.json`: 24 of 24 packs report `complete: True`. Of the 283 calls, 263 returned 200; the 16 × 502 are BSE shareholding HTTP 403, reproduced at the sha in `EV/datapack-shareholding-probe.txt` (environment), and 4 are 429s. The rc1-datapack:1 fix holds at the sha: SIFY and VERTEX P/E are unavailable, with the stated reason. |
| 10 | Fix loop closed | **FAIL** | Two items are not closed. rc1-scenarios:5 (high) reproduces at the sha. rc1-fix-r2-triage:1 (medium; the WIT revenue estimate is labelled USD but is in INR, `EV/fixr2-triage1-wit-estimates.json`) is open and the fix loop gave it no disposition. For the rest: I concur with the rejections of rc1-scenarios:1-4 and rc1-drive-portfolio-notes:2. rc1-drive-onboarding-stranger:1 did not reproduce in 2 of 2 runs, which cannot prove it closed. I accept the Tier-4 deferral of rc1-battery-4:1 (DECISIONS_FOR_OPERATOR.md §4.1). |
| 11 | GUI round | **DEFERRED** | `r15/rc1/gui/presence.log` has one line (03:18:04Z, idle=6609, front=Ghostty). `docs/screenshots/vr15-rc1/` does not exist, so no id is GUI-certified. The code fixes are present for all 9 ids (spot-checked). |
| 12 | Adversarial sample | **FAIL** | All 14 of the 14 refuted certified entries still fail when re-run at the sha. See `EV/inproc-refutations.txt`, `EV/data002.txt`, `EV/data043.txt`, `EV/agent003-rerun.txt`, `EV/probes-059-068-090.txt`, `EV/lead010-cold.txt`, `EV/docs017-018.txt` and `EV/code-excerpts.txt`. |

Overall: six items FAIL (1, 6, 7, 8, 10, 12). Four PASS (2, 3, 4, 5), and item 11 is an allowed DEFERRED (needs_gui). An allowed DEFERRED does not rescue a FAIL, so the gate is **FAIL**.

## Blockers

1. **Open c/h/m register entries.**
   - Open: R15-AGENT-017 (high), R15-AGENT-049, R15-LEAD-028, R15-RELEASE-007, R15-UI-088.
   - Fixed but uncertified: R15-LEAD-010 (high). It is also refuted.
2. **Certified entries that fail when re-run.** Each is a regression finding in `rc1-verifier.json`.
   - critical: R15-RESEARCH-002
   - high: R15-DATA-002, R15-AGENT-019, R15-AGENT-003, R15-RESEARCH-007, R15-UI-090, R15-LEAD-010
   - medium: R15-DATA-043, R15-AGENT-027, R15-DATA-068, R15-DATA-059, R15-DOCS-017
   - low: R15-DOCS-018, R15-CODE-PLATFORM-013
3. **rc1-scenarios:5 is not closed** (high). At the sha, llama3.1:8b states the SIFY ADR ratio as 1:2 with no tool field behind it.
4. **rc1-fix-r2-triage:1 is open with no disposition** (medium). The WIT revenue estimate of 244,246,846,490 is labelled USD but is in INR.
5. **New defect** (rc1-verifier:15, medium): the screener's currency grouping sorts on an empty fundamentals currency, so a null-market-cap row ranks first. This breaks R15-UI-006's rule that missing values sort last.
6. **The evidence chain has gaps.**
   - The battery has no raw output for 160 fixed ids.
   - The scenario suite is incomplete (11 of 20 OpenRouter runs errored upstream; sc3 and sc4 never completed) and predates the fix rounds.

## needs_gui (these stay needs_gui)

R15-CODE-AGENT-001, R15-LIFECYCLE-001, R15-LIFECYCLE-008, R15-UI-009, R15-UI-022, R15-UI-025, R15-UI-050, R15-UI-083, R15-UI-084

## Sha to tag

`1d6511c89bb27f1785f7af4d2290983b2852d70a` is the only tree this gate evaluated. The verdict is FAIL, so it must not be tagged as rc1, and I never tag.

`004-r4-experience-rebuild` has moved on to `29b9ae9b`. That head is **not** a descendant of this sha: it is 4097dac4 plus docs-only commits, and it lacks the fix-round code (23 non-doc files differ). The tagged tree must therefore be exactly this sha, or the gate re-runs. The same applies to any later fix round, and to merging this sha into 004.
