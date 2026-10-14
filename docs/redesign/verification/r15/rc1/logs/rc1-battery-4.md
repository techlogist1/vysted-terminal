# rc1-battery-4 — working log (this run)

Shard: REGRESSION BATTERY shard 4 (Sonnet), lane `battery:shard-4`, THIS dispatch's writer sets =
batch-6/W1-W5 + batch-14/W1-w1, per the task's own set/file/entries mapping (set-20..24, set-66).
Candidate `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`, worktree `rc1-cand` (read-only, source build).

## Note on set-file numbering collision (flagging for the lead)

Before starting, `set-20.md`..`set-24.md` already existed on disk from OTHER shard work (batch-6
W3/W4/W5 with a DIFFERENT, older entries list, and batch-7 W1/W2) — not from this task's assigned
entries. `INDEX.json`'s own `batch-6`/`batch-14` entries also differ from this task's entries list
(e.g. INDEX has batch-6/W2 = `["R15-LEAD-014"]`, this task has batch-6/W2 = `["R15-AGENT-053"]`).
This looks like the writer-set-to-entries mapping was re-scoped between rounds and `set-N.md`
filenames got reused across rounds for different content. Per this task's explicit file/entries
mapping (authoritative for this dispatch), I overwrote `set-20.md`..`set-24.md` with the correct
header + entries for batch-6/W1-W5 and created `set-66.md` fresh for batch-14/W1-w1. The prior
`rc1-battery-4` attempt's own work (from an earlier, differently-scoped dispatch, batch-6 W1-W5 at
set-18..22 with 8-15 entries per set) was itself already overwritten by other shards before this
run started — nothing of mine was lost by this overwrite; the debris in `battery/raw/set-20..24/`
from prior attempts (old ids like `R15-AGENT-023`, `DATA-014`, etc.) was left in place since it
does not conflict with my new `<id>.txt` raw files.

## Sidecar

- Reused existing isolated data dir `rc1-data-rc1-battery-4` (from a prior attempt's seed copy;
  same isolation guarantees — no operator data, no audit rows, keyless).
- Boot: `sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52344 --data-dir <own
  copy>` from `rc1-cand/sidecar`, `VYSTED_OPENBB_MCP_PORT=52153` / `VYSTED_SEC_EDGAR_MCP_PORT=52154`
  pointing at the shared read-only MCP stack. Sleep-wrapper pid 2335 (worker pid stable throughout).
- No writes to the shared stack (`:52152`/`:52153`/`:52154`), no writes to `rc1-cand`, no writes to
  the operator's live app-support data dir.

## Sets, in write order

1. `battery/set-20.md` (batch-6/W1-india-exchange-data, 1 entry) — R15-DATA-017 `holds`. Live curl
   against `:52344` for SUMAX/QUALIANCE (NSE-SME) and JNPR disclosures — all 9 calls (3 symbols x 3
   endpoints) 200 with real data, matching the batch-6 (5e14731) SME-routing fix.

2. `battery/set-21.md` (batch-6/W2-delegate-runs-runtime, 1 entry) — R15-AGENT-053 `holds`. Source
   read of `context-provider.ts` `captureTerminalState`: the `else` branch pushing every
   non-modelled panel source into `otherPanels[]` via `genericPanelSummary()` is present exactly as
   the batch-10 closure describes — no source is silently dropped any more.

3. `battery/set-22.md` (batch-6/W3-unattended-platform-chart, 5 entries) — all `holds`.
   PLATFORM-024: `saveTextArtifact` -> real Rust `write_text_atomic`/`write_bytes_atomic` commands
   (registered in `lib.rs`), not just a Blob download. PLATFORM-026: three ensure-*.mjs scripts
   shrank to 14-16 lines over shared `sidecar-specs.mjs`. PLATFORM-028: `vitest.config.ts` includes
   `scripts/**/*.test.mjs`, 4 script test files exist (not run — vitest suites are the heavy lane's).
   PLATFORM-030: live-confirmed `sold = min(abs(intent.quantity), position.quantity)` in
   `backtest_engine.py`, pinned test `test_flat_market_oversell_closes_the_held_quantity_once`
   exists. PLATFORM-032 (`removed_with_feature`): `git show --stat` on the D81 merge confirms
   kill_switch.py/audit_log.py/safety.py/types/safety.ts/AuditLogViewer.tsx/
   OrderConfirmationDialog.tsx are all deleted whole; `src/store/safety.ts` survives at 53 lines
   holding only the TOS-ack slice (the dormant kill-switch slice is gone).

4. `battery/set-23.md` (batch-6/W4-research-funnel, 5 entries) — all `holds`. RESEARCH-034:
   live in-process call `_reflect_says_complete("Price action is not covered yet")` -> `False`
   (was `True`), leading-token read confirmed. RESEARCH-036/040/042 (register status `open`):
   source-confirmed still unfixed exactly as documented (no `_PROMPT_KEYS` drift guard, no
   pre-dispatch cost estimate, no per-brief source-count floor) — matches, not a regression.
   RESEARCH-038: live `CircuitBreaker` call confirms `record_failure()` fires once per engine-turn
   (not per attempt); one bad search leaves the breaker `closed`, a second opens it.

5. `battery/set-24.md` (batch-6/W5-host-actions-portfolio, 9 entries) — 8 `holds`, 1 `needs_gui`.
   UI-044 (`blocked_tier4`): `DisclaimerFlow.tsx` hydrate effect still has no catch — confirmed
   unchanged (operator-adjudicated, no fix round due). UI-046/048/052/054/056/058: all
   source-confirmed matching their respective batch closures exactly (reserved-name filtering,
   chart module-preferences slice, onboarding copy drops the false keyless "web research" +
   "fully private/offline" claims, structured `step_kind==="notice"` replacing the prose
   `DIVERGENCE_RE`, screener store's `frame.event==="error"` branch, versioned `SettingsExport`
   with `appliedAny`-gated import). UI-050: the headless min-h-8/py-1 fix is present; the visual
   clip question needs a live render — `needs_gui`, matching the register's own status. UI-060
   (register status `open`): `BacktestRunEvent.kind` still declares `progress`/`trade` but every
   `_emit()` call site in `backtest_engine.py` only ever constructs `run-start`/`run-complete` —
   matches the documented open/unfixed state.

6. `battery/set-66.md` (batch-14/W1-w1, 1 entry) — R15-AGENT-090 `holds`. 3x live `vy.py invoke
   copilot` runs (ollama/llama3.1:8b, under the local-model lock, one lock hold per run, released
   on completion each time) with the exact original SIFY-ADR prompt: run 1 a tool-arg failure with
   an honest refusal (no fabrication), runs 2-3 both stated the TRUE ratio (6 ordinary shares),
   traced to the real `ads_ratio` field now wired into both `fundamentals` and
   `financial_statements` tool results (`_ads_ratio`/`adr_ratio.lookup`, confirmed independently
   live: returns the correct SEC-20-F-sourced ratio with real provenance). Run 3 additionally
   answered "TTM revenue ₹4,651 cr" without USD conversion when asked for USD — this is a
   completeness gap (didn't answer the currency asked), not the original defect (which was FALSELY
   labeling an INR figure "in USD"); the model correctly used the true reporting currency
   (`financial_currency: INR`, confirmed live via `GET /fundamentals/SIFY`) rather than mislabeling
   it, so not filed as a new finding. 0/3 untraced/fabricated ratio claims — the core defect does
   not reproduce, matching the batch-16 (`d64640d2`) closure.

## Findings

None. All 22 register entries checked this shard returned `holds` (or `needs_gui` for UI-050,
matching its own register status) against the fresh RC1 candidate — no regressions, no chain
failures, no new defects, no gate-8/trading-path issues (trading paths were not touched; PLATFORM-032
confirms the D81 removal is intact and nothing re-added it).

## Sidecar stop

Final action: `kill 2335` (the sleep-wrapper pid). No shared-stack or other-owner process touched.
Local-model lock: acquired/released exactly 3 times (once per `vy.py` run), never held across
tool calls beyond one run each, never left stale.

COVERAGE: 22/22 ids raw; no raw: none.
