# Pass B — build telemetry (cumulative)

Running tally of the Pass-B build window (branch `001-agent-native-redesign`).
One section per phase; the lead (Opus 4.8, 1M) appends as each phase closes.

## Running totals

| Metric                | Value (through B3 code)                                         |
| --------------------- | --------------------------------------------------------------- |
| Phases complete       | 2.9 / 6 (B1, B2 done; B3 code done, live Exa validation paused) |
| Sub-agents dispatched | 4 (B1) + 3 recon + 5 (B2) + 5 (B3) = 17                         |
| New tests             | 44 (B1) + 34 (B2) + ~95 (B3) ≈ 173                              |
| Test suite            | sidecar 1185 + web_search 5 · vitest green · §6.5 9/9           |
| New dependency        | `jugaad-data==0.33.1` (keyless NSE)                             |
| Commits               | 9fcb146·5e9ea9a (B1) · bb29fd6 (B2) · B3 pending                |

## Phase B3 — Web search, three tiers (Pillar C · US14) — CODE DONE, paused at Exa key

**Orchestration:** 5-agent dynamic workflow (`pass-b3-build`, 367,351 output tokens) over
file-isolated units — search-core interface+registry+normalizer, Exa BYOK backend, SearXNG
local backend, native-search injection across all 4 LLM adapters + citation normalizer,
frontend tier/key wiring. Lead owned: catalog `web_search` + `research` domain, the
`web_search` handler, agent-runtime native dispatch + per-run search cap, the Exa/SearXNG/tier
per-request contextvars + middleware, the registry↔searxng class-name/region fix.

**Built (FR-080–084, SC-020):** three-tier search — (1) **native** on the user's key for
Anthropic/OpenAI/Gemini/Groq/xAI (adapter injection + max_uses cap, tool withheld so search
isn't double-run); (2) **BYOK Exa** (locale domain allow-lists US/IN); (3) **local SearXNG**
(autodetect + BYO URL, nothing leaves the machine). Honest fallback (FR-082) when nothing is
configured — never fabricates a source. Per-run search cap (FR-081). Citations normalized to
{url,title,excerpt}. Secrets ride per-request headers → contextvars, process-memory-only.

**Gates green:** full sidecar 1185 + 5; §6.5 9/9; vitest/typecheck/lint/format clean; Tier-1
LOCKED empty; order-grep clean. All BYOK/native HTTP **mocked** in tests.

**PAUSED → operator stop #2:** the Exa BYOK path must be validated against the **real Exa key**
(demo tokens don't cover it; never mocked for the gate). Native-search live validation
additionally needs a native-capable LLM key. See report.

## Phase B2 — JARVIS capability completeness + 2 seamlessness fixes (Pillar D · US15)

**Orchestration:** 3 parallel recon agents (B2 cockpit + B2 indicators + B3 search surface)
then a **5-agent dynamic workflow** (`pass-b2-build`, 252,547 output tokens) over file-isolated
units — compare_symbols handler, indicator-presets, layout-templates, chart-command channel,
completeness audit. Lead owned catalog + host-actions + registry integration and reviewed
every diff. **Did NOT run a parallelizable phase lead-only** (per operator correction).

**Built (FR-090–094, SC-016/022/025):** `compare_symbols` (read), `set_chart_indicators`
(host_action) + per-asset-class presets, `arrange_layout` named templates (single-focus /
research-cockpit / compare / macro-scan), chart-command indicator+comparison channel,
`indicators` domain, SC-022 completeness audit.

**Two operator-reported seamlessness fixes folded in (lead):**

- AUTO chart-open silently failed → `set_chart_symbol`/`set_chart_indicators` ensureChartOpen()
  (by component); copilot narration de-coupled from "confirm in the proposal bar".
- Default provider not persisting → added the missing `useLLMProvidersStore` autosave
  subscription in page.tsx.

**Rig-verified live:** AUTO + set_chart_symbol on an empty cockpit → chart opens + loads
(Bug 1 fixed, reproduced-then-fixed); `research-cockpit` on NVDA → multi-panel cockpit +
MA(50/200)+RSI+MACD+Volume preset (SC-016, screenshot `b2-research-cockpit-NVDA.png`); Bug 2
restore live-verified (DeepSeek default persisted across reload). §6.5 9/9, Tier-1 LOCKED empty.

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
