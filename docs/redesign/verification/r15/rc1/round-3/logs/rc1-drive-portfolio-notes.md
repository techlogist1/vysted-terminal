# rc1-drive-portfolio-notes log

Candidate HEAD verified: `01d6920a300b016ab1ad8aa436ee4e4586f8e336`.

1. Checked `docs/redesign/verification/r15/rc1/round-3/` for prior work under this label:
   none found — first attempt this round.
2. Read `PROMPT_surface_s2.md` OWNER-DRIVE / portfolio-notes section, `COMMON.md`,
   `stage0/ISO_STACK.md`.
3. Read census evidence `docs/redesign/verification/r15/surface/portfolio-notes/EVIDENCE.md`
   (8 raw findings `SURF-PORTFOLIO-NOTES-1..8`) and the register
   (`docs/redesign/verification/vysted-r15-register.json`) for every portfolio/notes entry:
   ~70 fixed, a handful `needs_gui`/`blocked_tier4`, the rest `open` at `low` severity only.
   No open critical/high/medium in this area — consistent with the round's gate criterion.
4. Read the candidate's own current code for the group
   (`src/modules/portfolio/{PortfolioPanel,api}.ts`, `src/store/portfolios.ts`,
   `src/modules/notes/{NotesPanel,NotesToolbar,notes-persistence}.ts`,
   `src/lib/host-actions.ts`, `src/lib/csv.ts`, `sidecar/routers/portfolio.py`). Found the
   architecture changed since the census: portfolio holdings are now fully client-side
   (workspace-blob-owned), the sidecar's `/portfolio/positions` router is GET-only (write
   surface removed, not just gated) — `R15-CODE-PLATFORM-021/022` holds structurally.
5. Copied `rc1-round-3-seed-data` to my own data dir, booted my own sidecar on `127.0.0.1:52324`
   from the candidate worktree's `sidecar/` (source, not the shared :52152 stack). Sleep pid
   86801. `/health` confirmed ok.
6. Ran the candidate's own real-component vitest suites headlessly (this IS the owner-drive:
   the same method the census's jsdom harness used, now shipped inside the repo):
   `PortfolioPanel.test.tsx` + `NotesPanel.test.tsx` + `NotesToolbar.test.tsx` + `notes.test.ts`
   → 65/65 pass. `host-actions.test.ts` → 106/106 pass.
7. Ran the sidecar's intent-gate pytest (`tests/test_b3_runtime_intent_gate.py`) → 194/194 pass
   (R15-AGENT-019 regression class).
8. Curled my own sidecar for live quotes (`RELIANCE.NS`, `TCS.NS` — real EOD data from
   `nse_direct`) and the legacy portfolio ledger route shape (GET 200/POST 405/PUT-DELETE 404).
9. Held the Ollama lock (`mkdir /tmp/vysted-r15-ollama.lock`, acquired on the first try), ran one
   live agent call (`llama3.1:8b`, autonomy `auto`, empty-portfolio context, prompt "Add 10
   shares of INFY.NS at cost 1500 to my portfolio") via `scripts/r15/vy.py`, wrapped in a
   `trap … EXIT INT TERM HUP; rmdir` so the lock releases on success or failure. Result: correct
   `portfolio_add_position` tool_use, `ok:true` ack, 58.5s, $0. Lock confirmed released
   afterward.
10. Cross-checked `src/lib/csv.ts` for the census's formula-injection finding
    (`SURF-PORTFOLIO-NOTES-7`): still unescaped — this matches the register's own
    `R15-UI-079` (open, low, not in this round's fix scope), so not a regression, not a new
    finding.
11. Wrote `COVERAGE.json` (5/5 rows `ok`), `findings/rc1-drive-portfolio-notes.json` (empty —
    no regression, no new defect), `drives/portfolio-notes.md` (scored table + census→rc1
    deltas), and this log.
12. Stopped my sidecar: `kill 86801` (its own sleep pid only).

## Outcome

All 8 census raw findings for this group reproduce as fixed at the candidate. All register
entries for portfolio/notes that should be fixed are fixed, confirmed live (not just by
register status). No regression. No new defect. Three low-cost, unchanged-since-census states
(prompt-injection note content, 100-position render, huge-note perf) were not re-driven —
recorded `NOT TESTED` in `drives/portfolio-notes.md`, not silently skipped.
