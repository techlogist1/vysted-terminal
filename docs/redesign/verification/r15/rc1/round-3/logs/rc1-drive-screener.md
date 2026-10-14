# rc1-drive-screener — working log (gate round 3)

- Verified candidate HEAD: `01d6920a300b016ab1ad8aa436ee4e4586f8e336`.
- No prior round-3 files for this label existed at start (fresh start, not a resume).
- Confirmed `src/store/screener.ts`, `src/modules/screener/*`, `sidecar/routers/screener.py`,
  `sidecar/services/screener*.py` are byte-identical between the candidate worktree and the main
  operator worktree (only `.pyc` mtimes differ) — code citations are candidate-accurate.
- Copied `rc1-round-3-seed-data` → `rc1-round-3-data-screener`; booted own sidecar on `:52322`
  from `rc1-round-3-cand/sidecar` (source run), `VYSTED_OPENBB_MCP_PORT=52153`,
  `VYSTED_SEC_EDGAR_MCP_PORT=52154`; sleep pid 72201; `/health` ok. Stopped it (`kill 72201`) at
  the end of the drive.
- Read register (`vysted-r15-register.json`) for every screener-tagged entry: 81 hits, all but
  6 low-severity open ones (`R15-CODE-DATA-019/020`, `R15-CODE-FRONTEND-033/035`,
  `R15-CODE-PLATFORM-067`, `R15-LEAD-025/029`, `R15-DATA-102/103/107/108`, `R15-LIFECYCLE-033`,
  `R15-UI-068/069/071/076`) — none of the open lows are in this group's user-facing surface
  (they're code-internal/platform/other-panel), so none block this drive.
- Read census `EVIDENCE.md` first (7 `broken`/`partial` findings, all now `fixed` in the
  register) and `PROMPT_surface_s2.md`'s screener section for method/scope.
- Drove: universe picker (6 ids + custom 400 + bogus 422), the exact default panel-mount
  criteria (cold then warm), formula validate (bad char / unknown field / boolean-coercion),
  pagination (limit 200 vs 1000 on an india-all wide screen, limit 1001→422), zero-result screen,
  OR-group, custom bare Indian tickers, nse-all sector+mcap screen, a pasted-formula nse-all run,
  and the known-not-re-filed div-by-zero formula — all against the shared read-only stack
  `:52152` (screener endpoints are query-only, no user-data mutation).
- One live agent drive under the Ollama lock (got `/tmp/vysted-r15-ollama.lock` immediately,
  held via a `trap ... EXIT` wrapper, released on completion — 228.5s, my own sidecar `:52322`):
  `write_screener_filters` via `vy.py invoke copilot` on llama3.1:8b — confirmed against the
  `_normalise_tool_args` code fix in `agent_runtime.py`.
- Ran the candidate's own screener vitest suite (`pnpm vitest run src/modules/screener
  src/store/screener.test.ts`, backgrounded, ~3s) as a chain check: 6 files / 87 tests, all pass
  (census had 4/41 — suite grew, no regression).
- Noted but did not re-force: the circuit-open leg for bare-ticker resolution (shared stack's
  Yahoo breaker was closed throughout this drive window; forcing it open would affect other
  roles sharing `:52152` and is out of scope for a read-only owner-drive).
- Wrote `surface/screener/rc1/round-3/COVERAGE.json` (5/5 rows scored `ok`, all with evidence),
  `rc1/round-3/drives/screener.md` (scored table + census deltas), this log, and an empty
  findings array (`rc1/round-3/findings/rc1-drive-screener.json`) — nothing survived as a new
  defect or regression.
