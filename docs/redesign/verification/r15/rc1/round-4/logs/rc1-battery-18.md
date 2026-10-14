# rc1-battery-18 — regression battery shard 18, gate round 4

Candidate: `1006c6da694ede5776c3dabbd27b305aeb56b5ad` (verified via `git rev-parse HEAD` in the
scratch worktree before starting). No prior round-4 files under this label existed at start
(checked `battery/`, `findings/`, `logs/` for `rc1-battery-18` — none present); this is a fresh
run, not a resume.

## Setup

- Copied `rc1-round-4-seed-data` → `rc1-round-4-data-battery-18`.
- Booted one sidecar for the whole shard: `sidecar/.venv/bin/python3 main.py --host 127.0.0.1
  --port 52358 --data-dir <own data dir>` detached via `nohup sh -c 'sleep 86400 | ...'`,
  reusing the shared read-only openbb-mcp (:52153) / sec-edgar-mcp (:52154) env vars. `/health`
  confirmed `ok` with `openbb-mcp: available`. Sleep-wrapper pid 3019, worker pid 3022.

## Sets worked (one at a time, table written before moving on)

1. `set-18` (batch-5/W4-platform-workflow-boundary, 8 ids) — all `holds`. Verified live via
   in-process calls into the candidate's own venv (not by reading the diff): `logic_branch`
   truthy/falsy table + an engine run with the un-taken port wired to a live node (status
   `skipped`); an A(slow)/B(fast)/C←B workflow confirming C finishes before A; 60 concurrent
   QuantLib option pricings across two valuation dates (0/30 zero-NPV corruptions in either
   group, vs. 1413/3000 pre-fix); FastMCP `invoke_agent` schema introspection (no `api_key`
   property); `_get_list` against a forced-unreachable backend (`{ok:false,error:...}` for all
   three list tools); `workflow_store.list_workflows()` with one bad row inserted directly into
   sqlite (good row still lists, bad row reported under `unreadable`); MCP/httpx/fastmcp pins
   read from both subprocess requirements files; `data_cache.ensure_build()` across a simulated
   version bump busting a pre-fix cache row.
2. `set-40` (batch-10/W1-runtime-backtest, 6 ids) — 5 `holds`, 1 `ci_pinned` (R15-UI-011, pure
   frontend, no GUI/browser tool available — playwright and tauri-mcp both failed to connect,
   `node`/`npx` not on PATH). Verified live: Anthropic system-block splitting keeping the
   persona prefix byte-identical across a changing terminal preamble; the real captured
   `nemotron_cot.jsonl` fixture replayed through `ReasoningSplitter` (0 chars leaked to the
   answer channel); a 4-buy pyramiding run (quantity=40, one trade row); a 34-run backtest
   store survives an in-memory eviction and a simulated restart, `list_runs()` newest-first;
   live `POST /backtest/run` with `window=0`/`-5`/`""` → clean `422`s (not raw Python errors).
3. `set-56` (batch-12/W1-resolver-and-venue-identity, 1 id) — `holds`. Live `GET
   /history/AMAL.BO?range=1y` returns 255 bars (vs. NSE's 28-bar pre-fix response); sidecar log
   shows `nse_direct`/`nse` explicitly rejecting the `.BO` suffix and falling through to BSE.
4. `set-81` (unplanned-3, 1 id) — `holds`. In-process oversell probe (buy 10, sell -100): sold
   capped at 10, equity = capital − fees exactly.

## Notes

- R15-CODE-PLATFORM-020's register `note` already documents a residual (`GET
  /workflow/saved/{id}` still bare-500s on the same unreadable row that the list route handles
  cleanly) — not re-reported; the entry's fixed behaviour under test (`list_workflows`) holds.
- R15-LEAD-001: verified pins only (both subprocess requirements.txt files match the known-good
  freeze, and `scripts/sidecar-specs.test.mjs` carries matching `--copy-metadata` flags); a full
  clean-venv PyInstaller build is a heavy, minutes-long operation that belongs to the
  sidecar-build lane, not this battery shard.
- R15-UI-010: sidecar half (the more severe part — raw Python exceptions reaching the panel
  header) verified live over HTTP; frontend clamp half confirmed by source read
  (`strategy-picker.tsx:130-185`) and cross-checked against its pinned test
  (`BacktestPanel.test.tsx:464`), not executed.
- No regressions, new defects, chain failures, gate-8 issues, or environment blocks found in
  this shard — `findings/rc1-battery-18.json` is `[]`.

COVERAGE: 16/16 ids raw; no raw: none.

Sidecar stopped at end of shard (`kill 3019`, wrapper pid; worker exits on stdin EOF).
