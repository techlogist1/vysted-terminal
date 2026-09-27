# rc1 round-4 log — rc1-drive-portfolio-notes

- Confirmed candidate worktree HEAD == `1006c6da694ede5776c3dabbd27b305aeb56b5ad`.
- Confirmed shared stack healthy (`:52152/health` ok).
- `cp -R` seed data → `rc1-round-4-data-rc1-drive-portfolio-notes`.
- Booted own sidecar on `:52324` from `<cand>/sidecar` source (`main.py`, venv
  python3.13), detached via `nohup sh -c "sleep 86400 | python3 main.py ..."`,
  sleep-wrapper pid 71586, worker pid 71589. `/health` ok within ~10s.
- Read census `EVIDENCE.md`/`COVERAGE.json` and (context-only, not evidence)
  round-3's `drives/portfolio-notes.md` + `findings/rc1-drive-portfolio-notes.json`
  (empty `[]`) to know what to re-verify.
- Ran `vitest run` (detached, polled) on the real portfolio+notes component
  tests → 91/91 passed (`01-vitest-panels.txt`).
- Ran `vitest run src/lib/host-actions.test.ts` → 106/106 passed
  (`02-vitest-host-actions.txt`).
- curl'd the sidecar's legacy `/portfolio/positions` ledger (GET/POST/PUT/DELETE)
  and live `/quotes` (RELIANCE.NS, TCS.NS, BTC/USDT) — files `03`-`09b`.
- BTC/USDT bare-path probe (no `asset_class` param) came back `502`; traced it
  to my own probe omitting the query param the real panel always sends
  (`api.ts:82`), confirmed by re-probing with `?asset_class=crypto` → priced
  correctly via `ccxt:binance`. Not a finding.
- Ran the sidecar's intent-gate pytest suite → 194/194 passed
  (`10-pytest-intent-gate.txt`).
- Local-model lane: acquired `/tmp/vysted-r15-ollama.lock` (immediate), ran one
  `vy.py invoke copilot` add-position call under `trap ... rmdir` (61.7s, lock
  released clean), then reacquired (immediate) and ran the delete-TCS
  regression-check call (40.6s, lock released clean). Both `$0.00`.
- Delete-TCS call produced a tool_use (fixed vs. census) with a hallucinated
  `position_id: "<nil>"` (no `--context` passed) and sidecar `ok:true`; traced
  through `host-actions.ts` to confirm the real resolve/apply path fails closed
  on this exact shape (`resolveHolding` → `problem`, `apply()` →
  `fail(problem)`), independently proven by drive #2's passing "unmatched
  target is an honest null" case. Logged as a note, not a finding.
- Code-read confirmed two known-open lows unchanged (not regressions, not new):
  CSV formula-injection (`R15-UI-079`) and no-currency-field agent snapshot
  (`R15-AGENT-091`).
- Stopped sidecar: `kill 71586` (wrapper) then `kill 71589` (worker — the
  wrapper's exit did not close the worker's stdin pipe the way the sleep|binary
  pattern usually does, so a direct kill was needed). Confirmed `:52324`
  unreachable after.
- Wrote `drives/portfolio-notes.md`, `findings/rc1-drive-portfolio-notes.json`
  (empty — no new/regressed defects survived), this log.
