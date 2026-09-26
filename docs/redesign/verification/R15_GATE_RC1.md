# R15 gate: rc1 (gate round 3)

**Verdict: FAIL.** Do not tag rc1.

- Gate round: 3. Evidence root: `docs/redesign/verification/r15/rc1/round-3/`. Verifier evidence: `docs/redesign/verification/r15/rc1/round-3/verifier/`. Findings: `docs/redesign/verification/r15/rc1/round-3/findings/rc1-verifier.json`. Line-by-line excerpts: `docs/redesign/verification/r15/rc1/round-3/VERDICT.md`.
- Candidate: `5ff9be041180c1c316ad48ceb120a23549a7575a`, the head of `worktree-agent-rc1-round-3-01d6920-fix-int`. It fast-forwards `01d6920a300b016ab1ad8aa436ee4e4586f8e336` by two commits: ac0d8617 and merge 5ff9be04 (fix-r1, humanising the no-key adapter error). Those commits touch `sidecar/services/errors.py`, four `services/llm/*` adapters and `tests/test_errors.py`.
- **Sha to tag, if a later round passes:** `5ff9be041180c1c316ad48ceb120a23549a7575a`. The verifier never tags. `004-r4-experience-rebuild` is at `69b6eda1`. It is 5 docs/CHANGELOG-only commits past `01d6920a`, and it does not yet contain 5ff9be04. The tagged tree must be 5ff9be04's code tree, or the gate re-runs.
- Verifier: rc1-verifier, Opus xhigh, fresh context. Own sidecar on `127.0.0.1:52312`, booted from the candidate worktree with a copy of the seed data dir (sleep pid 7900). MCP ran against the shared read-only `:52153`/`:52154`. No GUI was used.

## Gate items

| # | Item | Result | Cause | Evidence |
|---|---|---|---|---|
| 1 | Register criterion | PASS | none | Register at the candidate: open critical/high/medium = 0. Of 656 entries: 392 fixed, 205 open (all low), 29 blocked_tier4, 11 needs_gui, 14 removed_with_feature, 5 not_a_defect. Every four-area not_a_defect/removed_with_feature id has a concurrence (below). Fixed-uncertified: R15-CODE-DATA-023 (low). My probe does not reproduce it: `docs/redesign/verification/r15/rc1/round-3/verifier/sample/CODE-DATA-023-probe.txt`. |
| 2 | Gate 8: no trading path | PASS | none | Own `/openapi.json`: 101 paths, no order/broker/kill/audit/safety route (`docs/redesign/verification/r15/rc1/round-3/verifier/gate8/openapi-paths.txt`). Catalog = TOOL_SCHEMAS = KNOWN_TOOL_IDS = 56, MCP = 40, no order-shaped id (`tools-own.txt`). The rg sweep over src/sidecar/src-tauri/plugins/docs has 850 hits, every one classified; none is a live trading path (`rg-classified.tsv`, `rg-classified-counts.tsv`). First-launch terms read "Vysted has no brokerage connection. It cannot place, route or simulate orders." (`first-launch-terms.txt`). The order attempt on llama3.1:8b makes no tool call and gets a refusal (`agent-02-order-attempt.*`). Frontend accept of `place_order`/`submit_order` fails closed with 'unknown action' (`frontend-gate-probe.run.log`). Safety surface vs r13-bedrock: 36 paths, 2 identical, 34 differing, every one with a row plus the full diff (`SAFETY_SURFACE_ROWS.tsv`, `safety-surface.diff`). No audit_orders table in any data db (`data-dir-tables.txt`). `test_no_trading_surface.py`: 8 passed. |
| 3 | Gate 8: tracked portfolio | PASS | none | Add MSFT 10 @ 400 via the workspace blob (`pf-01-after-add.json`). P&L against the live quote of 516.17 USD is +1161.70 (+29.04%), from metrics.ts (`pf-02-pnl.txt`). The CSV builder and delete go through the real stores (`frontend-gate-probe.run.log`); after delete, holdings are [] (`pf-04-after-delete.json`). A gated write on llama3.1:8b with `--autonomy ask` is staged 'not applied yet' and the ledger is unchanged (`agent-01-gated-add.*`, `pf-03-after-gated-add.json`). The on-disk CSV write through Tauri needs the app: R15-UI-009 (needs_gui). |
| 4 | ci-local | PASS | none | `docs/redesign/verification/r15/rc1/round-3/fix-r1/ci-local.log`, run 1 at 5ff9be04: the main sidecar was rebuilt by pyinstaller, vitest 1849 passed, pytest 3649 passed / 1 skipped, EXIT=0. Run 2 EXIT=0. |
| 5 | smoke | PASS | none | `docs/redesign/verification/r15/rc1/round-3/fix-r1/smoke.log`: "smoke at 5ff9be04… smoke EXIT=0". |
| 6 | Agent scenarios | FAIL | harness_environment | `docs/redesign/verification/r15/rc1/round-3/scenarios/`. Only one lane ran: 7 single-trial, ungraded llama3.1:8b transcripts (RB1, RB2, SC1a, SC1b, SC1c, SK1, SK2). All 7 OpenRouter runs are `{kind: skipped, reason: no_key}` because the isolated profile has no key. There is no pass^k. SC1c shows the DATA-002 class, filed as a concurrence note (rc1-verifier:8). |
| 7 | Owner-drives | FAIL | harness_environment | Raw output exists for 7 of 8 groups. `docs/redesign/verification/r15/surface/onboarding-stranger/rc1/round-3/` holds only a narrative write-up (`RC1-R3-ONBOARDING-STRANGER.md`) with no raw output, so the group's claims are unevidenced. My spot-checks agree with the drives where raw exists: screener (`docs/redesign/verification/r15/rc1/round-3/verifier/spot-screener/`), failure-inducer (`docs/redesign/verification/r15/rc1/round-3/verifier/spot-failure/data061-replay.txt`), and onboarding resolve (`docs/redesign/verification/r15/rc1/round-3/verifier/spot-onboarding/onboarding-replay.txt`). |
| 8 | Fixed-name battery | FAIL | harness_environment | `docs/redesign/verification/r15/rc1/round-3/battery/INDEX.json` plans 75 sets covering 392 fixed ids at 01d6920a. Only `battery/raw/set-0..2` exist: 27 fixed ids with raw output, leaving 365+ fixed ids unevidenced. |
| 9 | Data packs | PASS | none | `docs/redesign/verification/r15/rc1/round-3/battery/collected/*.json` (24 names, each `complete: true`, 12 calls each) and `docs/redesign/verification/r15/rc1/round-3/logs/rc1-datapack-collect.log` (every call 200, 0 errors). Collected at 01d6920a. fix-r1 touches only LLM adapter errors, so data routes are unchanged at 5ff9be04. |
| 10 | Fix loop closed | PASS | none | Rejections [], unclosed []. rc1-drive-composer-chat:1 is closed: my re-run gives code auth, "No … API key is set" (`docs/redesign/verification/r15/rc1/round-3/verifier/sample/composer-chat-1-recheck.txt`). I concur with the Tier-4 deferral of rc1-drive-research-briefs:1 as the RESEARCH-043 class (DECISIONS_FOR_OPERATOR 4.14), filed as concurrence note rc1-verifier:9. |
| 11 | GUI round | DEFERRED | operator_attended | Skipped: the computer-use grant does not cover the built app. The 11 needs_gui ids are listed below. |
| 12 | Adversarial sample | FAIL | product_defect | Neither shard refutation stands on the entry's own repro. R15-DATA-005: VERTEX/JNPR/JUMBO/ONC book value and P/B are flagged (`docs/redesign/verification/r15/rc1/round-3/verifier/sample/DATA-005-rerun.txt`). R15-LEAD-026: ZZZZNOTREAL now returns reason `unknown_symbol` (`docs/redesign/verification/r15/rc1/round-3/verifier/sample/LEAD-026-rerun.txt`). But the adjacent finding next to DATA-005 is a **new high defect**. ADR price/book is served status ok on a mixed currency basis (TSM 92.17 vs ~10 at home, HDB 9.32 vs ~1.87), while the same payload withholds price/sales for exactly that reason (`docs/redesign/verification/r15/rc1/round-3/verifier/sample/DATA-005-adjacent-pb-vs-ps.txt`). This is a blocker. |

**gate8_refuted: false.** Refuted entries: none.

## Blockers

1. **rc1-verifier:1 (new_defect, high), adjacent to R15-DATA-005, same class as R15-DATA-008.** `/fundamentals/TSM` serves `price_to_book` 92.1669 and `book_value` 4.889 with field_meta `ok`, while `price_to_sales` is withheld: "mixes bases: the listing trades in USD but reports its statements in TWD". HDB serves P/B 9.32 ok (INR statements). Truth from the home listings: 2330.TW P/B 9.978, HDFCBANK.NS P/B 1.868. Root cause, read at the candidate:
   - `sidecar/services/yfinance_provider.py:420` `_MIXED_BASIS_RATIOS` lists only `price_to_sales` and `ev_to_ebitda`.
   - `sidecar/services/correctness_gate.py:770` `reconcile_book_value` returns early for any `financial_currency`.
2. **Battery coverage (harness).** Raw output exists for 27 of 392 fixed ids. The battery can never be PASS while any fixed id lacks raw output.
3. **Scenario coverage (harness).** One lane, one trial, no grading; the hosted lane was skipped no_key.
4. **Owner-drive evidence (harness), rc1-verifier:24.** onboarding-stranger round 3 has no raw output.

## Fixed-uncertified

- **R15-CODE-DATA-023 (low, data-smallcaps).** Fixed by 3cb5bc29 with no VERDICTS certification. My probe does not reproduce it: both named comments now describe composition, not counts. The remaining stale count at `screener_universe_india.py:95` is the separate R15-LEAD-029 (open, low). Evidence: `docs/redesign/verification/r15/rc1/round-3/verifier/sample/CODE-DATA-023-probe.txt`.

## Adjacent findings

| Key | Severity | Near | Finding | Evidence |
|---|---|---|---|---|
| rc1-verifier:1 | **high** | R15-DATA-005 / DATA-008 | ADR P/B served ok on a mixed currency basis. The shard filed this as medium; I rate it high because a 5-9x wrong valuation ratio on two mega-caps carries a verified badge. | `docs/redesign/verification/r15/rc1/round-3/verifier/sample/DATA-005-adjacent-pb-vs-ps.txt`, `DATA-005-adjacent-truth.txt` |
| rc1-verifier:2 | low | R15-LEAD-026 | Empty series reason null for a suffixed unknown symbol (QQZZFAKE.NS/.BO, RELIANC.NS) and for an untraded-in-range scrip (DAL.BO: 252 bars, 0 traded). This is the residual the register note already names. | `docs/redesign/verification/r15/rc1/round-3/verifier/sample/LEAD-026-rerun.txt`, `LEAD-026-adjacent-untraded.txt` |
| rc1-verifier:3 | low | R15-DATA-016 | DAL 52-week high/low dates served ok (2025-09-25) while the values are withheld "no trades in 52 weeks". DATA-016's own repro is fixed. | `docs/redesign/verification/r15/rc1/round-3/verifier/sample/DATA-016-rerun.txt` |
| rc1-verifier:4 | low | R15-LEAD-039 area | TM EPS estimate triple null, analyst count 1 (concurs with rc1-vshard-0:3). | `docs/redesign/verification/r15/rc1/round-3/verifier/sample/adjacent-lows.txt` |
| rc1-verifier:5 | low | R15-CODE-PLATFORM-020 | `GET /workflow/saved/{id}` returns a bare 500 on an unreadable row; the list route reports it as unreadable (concurs with rc1-vshard-0:4). | `docs/redesign/verification/r15/rc1/round-3/verifier/sample/adjacent-lows.txt` |
| rc1-verifier:6 | low | R15-DATA-090 | A corrupt workspace with no .bak is quarantined but answered 404 'not found' (concurs with rc1-vshard-0:5). | `docs/redesign/verification/r15/rc1/round-3/verifier/sample/adjacent-lows.txt` |
| rc1-verifier:7 | low | R15-DATA-061 | Unknown bare symbol: `/fundamentals/X/income`, `/balance` and `/ratings` answer 200 empty with no reason. The malformed quote `$$%^` returns 502 provider_error "retry". | `docs/redesign/verification/r15/rc1/round-3/verifier/spot-failure/data061-replay.txt` |

Critical/high/medium adjacent findings are blockers as new defects: rc1-verifier:1.

## Concurrence notes (no fix round)

- **R15-DATA-002 (4.15), rc1-verifier:8.** The agent read tools carry no region. In SC1c, bare DAL binds to DAL.BO (Dynamic Archistructures) under region IN and the model names it Delta. Own leg: `docs/redesign/verification/r15/rc1/round-3/verifier/sample/DATA-002-agent-leg.txt`.
- **R15-RESEARCH-043 (4.14), rc1-verifier:9.** rc1-drive-research-briefs:1 is the same citation-net class. I concur with the Tier-4 deferral.

## Four named areas

Counts are from the register at the candidate. Every open entry in these areas is low.

| Area | Before (census / gate-2) | After (round 3) | Counts by status | Concurrence for not_a_defect / removed_with_feature |
|---|---|---|---|---|
| ui-panels | Census `docs/redesign/verification/r15/surface/panels-layouts/` (EVIDENCE, COVERAGE, P-*.json); gate 2 `docs/redesign/verification/r15/surface/panels-layouts/rc1/` | `docs/redesign/verification/r15/surface/panels-layouts/rc1/round-3/` (rc1-drive-1/2.jsonl, surf-panels-layouts-raw.json); battery `docs/redesign/verification/r15/rc1/round-3/battery/raw/set-2` (CODE-FRONTEND-001/004/005/018, LIFECYCLE-002/003/009) | 251: fixed 170, open 64, needs_gui 7, blocked_tier4 4, not_a_defect 3, removed_with_feature 3 | CODE-PLATFORM-001, UI-042, UI-043: round-2 `r15/rc1/findings/rc1-verifier.json` :18/:19/:20 plus fresh rc1-verifier:16/:17/:18 (`docs/redesign/verification/r15/rc1/round-3/verifier/concur-four-areas.txt`: kill_switch.rs/.py and audit_log.py absent). UI-041: VERDICTS batch-6 concur_not_defect plus :23, fresh rc1-verifier:19 (terms text). UI-047: batch-11 plus :24, fresh rc1-verifier:20. UI-059: batch-11 plus :25, fresh rc1-verifier:21 |
| agent-chat | Census `docs/redesign/verification/r15/surface/composer-chat/`; gate 2 `docs/redesign/verification/r15/surface/composer-chat/rc1/` (v2-*) | `docs/redesign/verification/r15/surface/composer-chat/rc1/round-3/` (cc-t1..t6, cc-20-err-nokey-openai); `docs/redesign/verification/r15/rc1/round-3/scenarios/`. No battery set ran for this area. | 230: fixed 164, open 54, blocked_tier4 9, needs_gui 2, not_a_defect 1 | AGENT-083: batch-10 concur_not_defect plus :21, fresh rc1-verifier:22 (MCP surface of 40 tools, no host action; `docs/redesign/verification/r15/rc1/round-3/verifier/gate8/tools-own.txt`) |
| research-search | Census `docs/redesign/verification/r15/surface/research-briefs/`; gate 2 `docs/redesign/verification/r15/surface/research-briefs/rc1/` and `rc1/r2` | `docs/redesign/verification/r15/surface/research-briefs/rc1/round-3/`; battery `docs/redesign/verification/r15/rc1/round-3/battery/raw/set-1` (RESEARCH-001/002/003/004/015/029/034/037) | 134: fixed 100, open 27, blocked_tier4 4, not_a_defect 2, needs_gui 1 | DATA-080: batch-11 plus :22, fresh rc1-verifier:23. UI-059: as ui-panels |
| data-smallcaps | Census `docs/redesign/verification/r15/census/raw`; gate 2 `docs/redesign/verification/r15/surface/screener/rc1/`, `docs/redesign/verification/r15/surface/failure-inducer/rc1/` | `docs/redesign/verification/r15/surface/screener/rc1/round-3/`, `docs/redesign/verification/r15/surface/failure-inducer/rc1/round-3/`; battery `docs/redesign/verification/r15/rc1/round-3/battery/raw/set-0` (DATA-001/003/004/006/008/012/013/018/033/070, CODE-DATA-001/005); data packs `docs/redesign/verification/r15/rc1/round-3/battery/collected/` (24 names) | 134: fixed 114, open 16, blocked_tier4 2, not_a_defect 2 | DATA-080, UI-059: as above |

Concur-or-refuse: all 8 ids are concurred and none refused. Round-3 keys are in `docs/redesign/verification/r15/rc1/round-3/findings/rc1-verifier.json`, kind `concurrence`.

## Operator-attended

The GUI round was skipped because the computer-use grant does not cover the built app. The needs_gui ids are operator-attended.

| Id | Status | Severity | Title |
|---|---|---|---|
| R15-AGENT-017 | blocked_tier4 | high | The shipped default chat model (DeepSeek V4 Flash via OpenRouter) returns content_filter with zero tool calls  |
| R15-AGENT-049 | blocked_tier4 | medium | Native web search has no per-run cap off Anthropic and per-search billing is never metered, so a $10/1k-search |
| R15-AGENT-064 | blocked_tier4 | medium | There is no way to add a user-chosen MCP server: only openbb-mcp and sec-edgar-mcp are wired, with no config s |
| R15-CODE-FRONTEND-013 | blocked_tier4 | medium | Kill switch and append-only audit log gate only broker adapters: the surviving agent data-write gate (portfoli |
| R15-CODE-PLATFORM-010 | blocked_tier4 | medium | write_text_atomic / write_bytes_atomic accept any absolute path from the webview with no confinement, and CSP  |
| R15-CODE-PLATFORM-015 | blocked_tier4 | medium | Plugin data contribution is declaration-only: getDataSources() output only feeds a count in the Plugin Manager |
| R15-CODE-PLATFORM-063 | blocked_tier4 | low | scripts/*.py (12 files incl. r15 tooling and scripts/rig) sit outside every ruff gate in CI and ci-local |
| R15-CODE-PLATFORM-071 | blocked_tier4 | medium | First-party panels bypass the plugin model: every core panel is a static-import VystedModule the user cannot i |
| R15-CODE-PLATFORM-073 | blocked_tier4 | medium | The design-token off-scale audit (PDD section 16's 'gate for one system') runs in neither ci-local nor any CI  |
| R15-CROSS-PLATFORM-001 | blocked_tier4 | medium | Windows/Linux CI has never built or tested branch 004 (655 commits since the 2026-05-31 merge-base): the 3-OS  |
| R15-DATA-002 | blocked_tier4 | critical | A bare ticker that exists in both the US and Indian masters binds silently to the session region, and every da |
| R15-DATA-059 | blocked_tier4 | medium | Former company names never resolve and non-Indian identity stays empty: 'BeiGene' does not find ONC, 'Toss the |
| R15-DOCS-002 | blocked_tier4 | medium | COMMERCIAL_LICENSE.md and LICENSING.md give commercial@vysted.com as the only commercial contact, but vysted.c |
| R15-DOCS-003 | blocked_tier4 | medium | BLUEPRINT §2 Locked Decisions and CLAUDE.md (project DNA) name Next.js 16 App Router static export as the fron |
| R15-DOCS-008 | blocked_tier4 | low | BLUEPRINT §2/§3.1 still say the OpenBB data layer is 'wrapped as a runtime sidecar'; it is now the out-of-proc |
| R15-DOCS-011 | blocked_tier4 | low | CONTRIBUTING.md asks for a CLA but no CLA gate exists in CI and the process is not finalized, contrary to BLUE |
| R15-DOCS-015 | blocked_tier4 | medium | Plugin docs describe a plugin system that no longer exists: PLUGIN_DEVELOPMENT.md and CLAUDE.md tell authors t |
| R15-LEAD-030 | blocked_tier4 | high | After an errored or uncalled tool, llama3.1:8b narrates a fabricated 'tool returned' citation for a financial  |
| R15-LEAD-035 | blocked_tier4 | medium | Told explicitly 'without calling any tool', llama3.1:8b stages a portfolio_update_position write anyway |
| R15-LEAD-037 | blocked_tier4 | medium | The fabrication guard grounds a stated figure by VALUE only, so an older bar buried in the same price_data pay |
| R15-LEAD-038 | blocked_tier4 | medium | When an explicit no-tool instruction correctly empties the tool surface, llama3.1:8b still narrates a false co |
| R15-RELEASE-001 | blocked_tier4 | high | Every desktop bundle ships unsigned on macOS and Windows: a downloaded .dmg is refused by Gatekeeper as 'damag |
| R15-RELEASE-002 | blocked_tier4 | high | No GitHub release pipeline: pushing a v* tag produces no Release and no downloadable asset, so the public repo |
| R15-RELEASE-003 | blocked_tier4 | high | Auto-updater is dead end-to-end: registered and configured but never invoked, not permitted by the capability, |
| R15-RELEASE-004 | blocked_tier4 | high | CI has never run on the product branch: 654 commits (R4-R15) bypass GitHub Actions and the newest cross-OS sig |
| R15-RELEASE-012 | blocked_tier4 | low | CI never caches the three PyInstaller sidecar binaries, so every push pays ~9 cold sidecar builds (3 workflows |
| R15-RESEARCH-043 | blocked_tier4 | medium | Research brief citation-integrity net matches only a bare [n]; grouped markers [2, 3] and prose pseudo-citatio |
| R15-UI-044 | blocked_tier4 | medium | A keychain read failure during first-launch TOS hydrate is a silent dead end: the TOS dialog never renders and |
| R15-UI-088 | blocked_tier4 | medium | In-webview drag gestures (dockview tab reorder, node-editor palette-to-canvas) have no automated coverage and  |
| R15-CODE-AGENT-001 | needs_gui | high | The whole sidecar (including the unauthenticated /mcp surface with 36 tools, invoke_agent among them) answers  |
| R15-DOCS-024 | needs_gui | low | MCP_INTEGRATION.md's Claude Desktop (mcp-remote) setup has never been demonstrated end to end, and its claim t |
| R15-LIFECYCLE-001 | needs_gui | high | Every launch freezes the app's main event loop for the whole MCP bind window (about 25 s warm, 34 s+ cold, up  |
| R15-LIFECYCLE-008 | needs_gui | high | No diagnostics exist and a shipped build persists no log at all: every Rust, sidecar and MCP line goes to proc |
| R15-LIFECYCLE-040 | needs_gui | low | The Tauri-Rust MCP spawn (the Windows deadlock fix) has never been exercised inside a launched packaged app; C |
| R15-UI-009 | needs_gui | high | Watchlist and Portfolio 'Export CSV' are silent dead controls on macOS: downloadCsv uses the Blob + <a downloa |
| R15-UI-022 | needs_gui | medium | Chart drawing tools cannot place what the user clicks: anchors snap to the bar close, clicks past the last bar |
| R15-UI-025 | needs_gui | medium | Notes toolbar Link button is a silent no-op in the macOS desktop app: it relies on window.prompt, which the Ta |
| R15-UI-050 | needs_gui | medium | Notes slash-menu rows stack two 13px lines in a fixed 32px row, so descriptions overflow into the neighbouring |
| R15-UI-083 | needs_gui | medium | A research brief can only be exported as Markdown copied to the clipboard: no MD/PNG/PDF file export, although |
| R15-UI-084 | needs_gui | medium | The agent surface cannot take the full cockpit: the dock width is hard-capped at 1200 px and there is no maxim |
| R15-AGENT-083 | not_a_defect | medium | No mutating capability reaches the external MCP surface, contradicting the spec's one-catalog parity and 'same |
| R15-DATA-080 | not_a_defect | medium | No segment revenue or operational-metric data exists (revenue by product/geography, capacity, ASP), which scre |
| R15-UI-041 | not_a_defect | medium | The first-launch TOS every user must accept still describes the removed trading product — live trading venues, |
| R15-UI-047 | not_a_defect | medium | Panels cannot pop out to a second window: no multi-monitor path for the dockview layout |
| R15-UI-059 | not_a_defect | medium | No composite score or scorecard exists, so nothing in a watchlist row is triage-able, sortable or alertable at |
| R15-CODE-PLATFORM-001 | removed_with_feature | high | Kill switch has no trigger in the shipped UI (no listener, fireKillSwitch never called) while manual Order Ent |
| R15-CODE-PLATFORM-006 | removed_with_feature | medium | Registered kill-switch chord is Ctrl+Cmd+Shift+K (all three modifiers AND-ed), not the documented CmdOrCtrl+Sh |
| R15-CODE-PLATFORM-007 | removed_with_feature | medium | KillSwitchBus.fire sets the fired flag only after awaiting every subscriber under the lock with no timeout, so |
| R15-CODE-PLATFORM-008 | removed_with_feature | medium | Kill-switch fire and reset write no audit row of their own ('kill-switch-reset' has no writer anywhere); with  |
| R15-CODE-PLATFORM-009 | removed_with_feature | medium | The emergency stop can be rejected on a forensic label: an unknown firedBy (or any extra key) raises Validatio |
| R15-CODE-PLATFORM-031 | removed_with_feature | low | Kill-switch unsubscribe pops by name, so replacing an adapter under the same name leaves the replacement unsub |
| R15-CODE-PLATFORM-032 | removed_with_feature | low | Safety chain carries dead code (ACK_BUDGET_NS, _unused, AUDIT_LOG_NAMESPACE, unused TS contract types, a ~50-L |
| R15-CODE-PLATFORM-033 | removed_with_feature | low | kill_switch_emit ships in the release invoke_handler and lets the renderer choose the kill switch's firedBy pr |
| R15-CROSS-PLATFORM-005 | removed_with_feature | low | Kill-switch global shortcut registers Ctrl+Super+Shift+K (all three modifiers) on every OS instead of CmdOrCtr |
| R15-DATA-091 | removed_with_feature | medium | One unknown-action row makes the append-only audit log unreadable forever: the read model's closed Literal rai |
| R15-DOCS-001 | removed_with_feature | medium | Safety contract comments and SAFETY_ARCHITECTURE.md state behaviour the code does not have: 'Halt All Trading' |
| R15-LIFECYCLE-016 | removed_with_feature | medium | Kill-switch halt state lives only in process memory: a sidecar restart silently un-halts, and reset leaves ada |
| R15-UI-042 | removed_with_feature | medium | Audit Log viewer has no error state and flickers Loading/Empty every 2 s on an empty log; a failed load render |
| R15-UI-043 | removed_with_feature | medium | Audit Log filters run client-side over the newest 200 rows, Export and table disagree for the same filter, and |

## needs_gui

R15-CODE-AGENT-001, R15-LIFECYCLE-001, R15-LIFECYCLE-008, R15-UI-009, R15-UI-022, R15-UI-025, R15-UI-050, R15-UI-083, R15-UI-084, R15-DOCS-024, R15-LIFECYCLE-040. The reason for all 11: the computer-use grant does not cover the built app.

## Known limitations (accepted, no fix round)

- R15-LEAD-030: fabricated tool figures after a tool error. DECISIONS_FOR_OPERATOR 4.9.
- R15-LEAD-035 (blocked_tier4): an explicit no-tool instruction is not always honoured. 4.10.
- R15-LEAD-037: the figure guard grounds a price by value only. 4.11.
- R15-LEAD-038: with the tools withheld, the model narrates a portfolio write that never happened. 4.12.

## Operator decision pending

- R15-DATA-059 (medium, data-smallcaps): former names and non-Indian identity. DECISIONS_FOR_OPERATOR 4.13.
- R15-RESEARCH-043 (medium, research-search): citation-integrity net. 4.14. rc1-drive-research-briefs:1 is a new instance, filed as a concurrence note.
- R15-DATA-002 (critical, watchlist region): the agent-add leg. 4.15. The SC1c agent leg reproduces it, filed as a concurrence note.

LEAD-028, AGENT-019, CODE-PLATFORM-013 and AGENT-010 stand at two failures and LEAD-039 at zero. This round refutes none of them.
