# rc1-battery-8 — regression battery shard 8 (round 5)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98 (verified `git rev-parse HEAD` at cand
worktree). Own sidecar booted from candidate source on :52348, data dir copied fresh from
`rc1-round-5-seed-data` into `rc1-round-5-data-rc1-battery-8`. Sleep-wrapper pid 47042 (killed);
worker pid 47045 killed directly after the sleep-close didn't end it (uvicorn doesn't read
stdin) — confirmed port free before finishing.

No prior round-5 files existed for this label at start (checked `battery/`, `battery/raw/`,
`findings/`, `logs/` — set-23/21/78 absent); this is a fresh run, not a resume.

## Sets

- **set-78 (batch-28/W5-opus)**: DATA-053, DATA-114, LEAD-044, LEAD-045 — all live-curlable
  against my own sidecar (or, for LEAD-045, a direct outside-world probe). All 4 holds. LEAD-044
  in particular re-ran the actual register repro live (`POST /screener/run` universe=sp500 under
  an `X-Vysted-Region: IN` header) and got the correct US entities (Halliburton/Carnival/
  IDEX/Arch Capital) for the four collision tickers the register named — a strong positive
  regression check, not just a source read.
- **set-21 (batch-6/W3-unattended-platform-chart)**: AGENT-051, AGENT-052, CODE-FRONTEND-015,
  LEAD-012. Three are GUI-driven (panel focus) with no browser session available (NO GUI role
  rule) — verified by tracing the exact cited mechanism in source instead of judging from the
  diff (confirmed the specific comparison/lookup that used to be wrong is now correct). LEAD-012
  is shell-checkable (python version resolution) and was run live. All 4 holds.
- **set-23 (batch-6/W5-host-actions-portfolio)**: 9 entries, all host-actions.ts/portfolios.ts
  frontend logic or the portfolio sidecar router. No GUI, and vitest is out of scope for this
  role (heavy lane owns it) even though several of these were originally certified via a vitest
  proof file (P3-P7b). Verified instead by tracing each named mechanism through the current
  source: resolveHolding's refusal-on-ambiguous-lot, portfolioId-bound describe/apply/undo, the
  single shared `parseHostAction` feeding both describe and apply, save_screen writing its own
  recipe before saving, write_screener_filters actually calling runScreener on run:true, the
  sidecar portfolio router now GET-only with the write-ledger client deleted, and normalizeHolding
  now rejecting (not coercing) invalid quantity/cost. All 9 holds.

## Notes

- No source-check was used as a substitute for a live probe where a live probe was possible
  (set-78's 4 entries and LEAD-012 all ran live commands). For the GUI-only/vitest-only
  entries in set-21/set-23, no live repro path existed under this role's constraints (no GUI,
  no vitest), so the raw file states that plainly and gives the source-level trace as the best
  available verification, per each entry's cited mechanism rather than a generic diff read.
- No regressions found. 0 findings.

COVERAGE: 17/17 ids raw; no raw: none.
