# Pass B — build telemetry (cumulative)

Running tally of the Pass-B build window (branch `001-agent-native-redesign`).
One section per phase; the lead (Opus 4.8, 1M) appends as each phase closes.

## Running totals

| Metric                   | Value (through B1)                                     |
| ------------------------ | ------------------------------------------------------ |
| Phases complete          | 1 / 6 (B1)                                             |
| Sub-agents dispatched    | 4                                                      |
| Files modified (tracked) | 20 (+561 / −63)                                        |
| Files added              | 12 source/test + 3 data (2 masters JSON, 1 `__init__`) |
| New source LOC           | ~1,640 (5 sidecar modules + 7 test files)              |
| Bundled data added       | 528 KB (US 10,365 + NSE 2,675 instrument masters)      |
| New dependency           | `jugaad-data==0.33.1` (keyless NSE)                    |
| Sidecar binary footprint | 89 MB → 104 MB (≤120 MB budget held)                   |

## Phase B1 — Locale-native data foundation (Pillar A · US11)

**Wall-clock:** single build session, 2026-06-01.

**Sub-agents dispatched (4):**

| Agent                                     | Role                                                           | Reported output tokens |
| ----------------------------------------- | -------------------------------------------------------------- | ---------------------- |
| Explore — frontend region-flow map        | recon (read-only)                                              | n/r                    |
| Explore — rig launch procedure map        | recon (read-only)                                              | n/r                    |
| Build — frontend region wiring            | sidecar-client header + format currency + context + dev-stores | 50,821                 |
| Build — news/screener/macro region-keying | region-keyed feeds + macro/screener defaults                   | 95,481                 |

Lead authored the correctness-critical spine directly (config region, `locale.py`,
`correctness_gate.py`, `india_provider.py`, `symbol_resolver.py`, `provider_registry`
region routing, `resolve_symbol` catalog capability, the ASGI region middleware).

**Files changed (B1):** see `git diff --stat` — 20 modified (+561/−63) + new:
`sidecar/services/{locale,correctness_gate,india_provider,symbol_resolver}.py`,
`sidecar/services/agent_tools/resolve_symbol.py`,
`sidecar/services/resolver_masters/{__init__.py,us_instruments.json,nse_instruments.json}`,
and 7 new test files.

**Tests added:** 44 (locale 9, symbol_resolver 8, correctness_gate 9, india_provider 8,
provider_registry_region 7, region_middleware 4, resolve_symbol_tool 4) — `_quote` fake in
the existing `test_provider_registry` updated to satisfy the new correctness gate.

**Gate results:**

- `pytest` full sidecar suite — **1095 passed**, 0 failed.
- §6.5 `test_safety_end_to_end.py` — **9/9**.
- `pnpm typecheck` 0 · `pnpm lint` clean · `pnpm test` (vitest) **745 passed**.
- `prettier --check .` clean · `ruff format --check` clean · `ruff check` clean.
- `node scripts/smoke-test-sidecars.mjs` — all sidecars booted cleanly.
- Built-binary HTTP verification — India basket via `provider=nse`/INR, US via
  `yfinance`/USD, GOLDBEES routed to NSE with no region header (master hint).
- Tier-1 LOCKED diff — **empty** (byte-for-byte). Order-execution grep — **clean**.
- Rust (cargo fmt/clippy/test) — not re-run; **no Rust files changed** this phase.

**Flagged-uncertainty validations (B1):**

- Keyless India reliability — **resolved**: jugaad-data `stock_df` EOD serves 14/15 basket
  symbols cleanly (GOLDBEES's lone first-call `FileExistsError` is a cache-dir race, fixed
  with `makedirs(exist_ok=True)` + retry); live NSE quote endpoints (NSELive/nsepython) are
  blocked from this host → quotes derived from EOD bars (T+1, as ratified). Correctness gate
  - preference-ordered fallthrough proven to fire (unit + live).
- EODHD/Exa/Perplexity real keys — **not needed for B1** (keyless path only).
