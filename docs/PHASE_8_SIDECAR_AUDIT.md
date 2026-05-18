# Phase 8 Sidecar Audit — T2 (CVE / Dead-code / Strict Lint + Type)

**Date:** 2026-05-18
**Baseline commit:** `947d297e9fd091727c4f229d07df19ddef8ed28f`
**Branch:** `worktree-agent-a17b77ac0c03d6a04`
**Auditor:** Phase 8 Teammate T2 (Sonnet 4.6)

## Severity scheme

| Level | Meaning |
|-------|---------|
| S1 | Broken at runtime, security-critical, CRITICAL/HIGH CVE in a reachable code path |
| S2 | Real bug surface (incorrect error handling, edge case), MEDIUM CVE, dead module that the registry references, wrong type signature with observable semantic consequence |
| S3 | Strict-lint noise, LOW CVE, dead helper inside a live module |
| S4 | Cosmetic / style-only |

---

## Angle 1 — CVE / Yanked / Advisory Scan

### Tooling used

```
pip-audit 2.10.0
pip-audit -r sidecar/requirements.txt --format json
pip index versions <pkg>   # yanked-package check for all direct + key transitive deps
```

### Findings

---

### Finding T2-cve-autobahn: autobahn 19.11.2 — CVE-2020-35678 (redirect header injection) [S3] [status: open]

**Tool:** pip-audit 2.10.0
**Detection:**
```
pip-audit -r sidecar/requirements.txt
Found 1 known vulnerability in 1 package

autobahn 19.11.2  →  PYSEC-2020-25 / CVE-2020-35678 / GHSA-gwp7-vqr5-h33h
  "Autobahn|Python before 20.12.3 allows redirect header injection."
  Fix: upgrade to >= 20.12.3
```
**Impact:** `autobahn` is a **transitive** dependency pulled in by `kiteconnect==5.2.0`. The CVE is a WebSocket handshake redirect header injection — an attacker who controls the WebSocket server URL could inject arbitrary HTTP headers via a crafted redirect. Severity downgraded to **S3** because:
1. The Kite adapter (`sidecar/services/brokers/kite.py`) does **not** use `KiteTicker` (Zerodha's WebSocket streaming class that uses autobahn). The adapter uses only the REST session (`kiteconnect.KiteConnect`) for order placement, positions and account queries. Grep for `KiteTicker` across the whole sidecar returns no results.
2. The sidecar connects only to `api.kite.trade` (Zerodha's TLS-verified endpoint) — no attacker-controlled WebSocket endpoint.
3. The attack requires MITM on a WebSocket connection; loopback-only sidecar transport adds another layer.

**Suggested fix path:** Pin `autobahn>=20.12.3` in `requirements.txt` (or add a constrained transitive pin comment). Verify `kiteconnect==5.2.0` still resolves cleanly with the newer autobahn. Non-blocking for shipping.
**Files:** `sidecar/requirements.txt:40` (kiteconnect transitive)

---

### Yanked package list

No yanked packages detected among direct dependencies. All versions queried via `pip index versions` show INSTALLED versions still present in the available-versions list.

Notable observations:
- `oandapyV20==0.7.2`: Last release 2021. No CVEs in the PyPI advisory database. Per CLAUDE.md BLOCKERS.md note this is a known maintenance concern. Advisory DB clean; OANDA SDK maintenance risk is pre-documented.
- `dhanhq==2.1.0`: INSTALLED version confirmed present in PyPI release list. No advisories.
- `google-genai>=2.4.0` (floor pin, not exact): Currently resolves to 2.4.0 in audit environment. No advisories.

---

## Angle 2 — Dead-code Scan

### Tooling used

```
vulture sidecar/ --min-confidence 80
ruff check sidecar/ --select F401,F811
```

### Findings

---

### Finding T2-dead-earnings-ternary: Always-`None` ternary in `earnings_provider.py` [S2] [status: open]

**Tool:** vulture 2.16 (100% confidence: "unsatisfiable 'ternary' condition")
**Detection:**
```
sidecar\services\earnings_provider.py:253: unsatisfiable 'ternary' condition (100% confidence)
```
The flagged line is:
```python
eps_stddev = _num(row.get("growth")) if False else None
```
**Impact:** The condition `if False` is a hard-coded dead branch. `eps_stddev` is **always assigned `None`** at line 253, regardless of the DataFrame contents. The comment at line 255 ("Some yfinance versions provide a stddev-like column called `epsTrend`...") suggests the original intention was to compute `eps_stddev` from the `"growth"` column of the estimate frame. The computation is silently skipped. This means `EarningsEvent.eps_estimate_stddev` is always computed from the high/low approximation fallback (line 258–259) rather than from actual analyst estimate dispersion data when available. This is a **silent data quality regression** — data consumers (the Strategy Critic agent, any model that uses stddev for volatility estimation) receive a cruder estimate than the underlying data permits.

**Suggested fix path:** Replace `if False else None` with the actual condition (presumably `if "growth" in row.index and pd.notna(row["growth"])` or similar). The original developer left a `# TODO` shape here — the fix is restoring the intended expression.
**Files:** `sidecar/services/earnings_provider.py:253`

---

### Known false-positive list (import-time registration)

vulture did not flag any production-code entries for `agent_tools`. The following patterns are confirmed import-time-registered tools, expected to appear unused to static analysis:

- `sidecar/services/agent_tools/backtest_summary.py` — registers `backtest_summary` at import time; `__init__.py`'s `_backtest_summary_mod` import (line 103, `# noqa: F401`) is the load-bearing side-effect import.
- `sidecar/services/agent_tools/registry_v0_6_0.py`, `registry_v0_6_5.py` — invoked from `register_v0_6_0_tools()` / `register_v0_6_5_tools()` aggregators.

**All vulture findings in `tests/` are pytest-fixture unused-variable patterns** — `temp_data_dir`, `available_provider`, `register_nodes`, etc. These are fixtures injected by pytest for their side effects (e.g., `tmp_path`-derived dirs, monkeypatching). They are valid pytest patterns, not dead code. Count: ~200 test-only false positives suppressed.

The single **ruff F401/F811** scan returned clean (`All checks passed!`) on the full sidecar including tests.

---

## Angle 3 — Strict Lint + Type Audit

### Tooling used

```
ruff check sidecar/ --select B,S,FAST,RUF   (targeted bug-class rules)
ruff check sidecar/ --select ALL --ignore ANN,D,COM,TD,FIX,ERA,EM,TRY,G,PERF,PTH,SIM,CPY,ISC,FA,TCH,PIE,N,T201,PLC0415  (broad strict, noise-reduced)
mypy sidecar/ --ignore-missing-imports --exclude "tests/" --no-error-summary
mypy version: 2.1.0
```

**PLC0415 (import-not-at-top-level) ignored:** The deferred-import pattern in `app.py`, `main.py`, and the subprocess mains is intentional — it prevents circular imports and lazy-loads optional subsystems. This is documented in `agent_tools/__init__.py` and consistent with the phase-6 refactor pattern.

### Genuine-bug findings

---

### Finding T2-mypy-llm-override: `stream_chat` async-generator/coroutine override mismatch in 4 LLM providers [S2] [status: open]

**Tool:** mypy 2.1.0 `--ignore-missing-imports --exclude tests/`
**Detection:**
```
sidecar\services\llm\openai.py:49: error: Return type "AsyncIterator[...]" of "stream_chat"
  incompatible with return type "Coroutine[Any, Any, AsyncIterator[...]]"
  in supertype "services.llm.base.LLMProvider"  [override]
```
Same error in `anthropic.py:82`, `groq.py:38`, `ollama.py:51`.

**Impact:** The ABC `LLMProvider.stream_chat` is declared `async def ... -> AsyncIterator[LLMStreamEvent]`. An `async def` that returns `AsyncIterator` has the runtime type of a `Coroutine[Any, Any, AsyncIterator[...]]` — mypy's complaint is correct. The concrete implementations use `async def` with `yield` inside (making them `AsyncGenerator`, a subtype of `AsyncIterator`). At runtime this works because Python resolves `async def` + `yield` to an `AsyncGenerator` object, but the ABC's declared return type creates a mypy-level mismatch that could mislead future maintainers or type-checking consumers. The risk is that a future caller awaits `stream_chat(...)` expecting an `AsyncIterator` object directly, rather than iterating with `async for`. If any of the four providers is ever called directly (rather than through the router's `async for` loop), it would behave unexpectedly.

**Suggested fix path:** Change the ABC declaration from `async def stream_chat(...) -> AsyncIterator[...]` to a plain `def stream_chat(...) -> AsyncIterator[...]` (without `async`) — an `AsyncGenerator` returned from the implementations is an `AsyncIterator`. Alternatively, annotate the ABC return type as `AsyncGenerator[LLMStreamEvent, None]`. The router code that iterates with `async for` would be unaffected either way.
**Files:** `sidecar/services/llm/base.py:42`, `sidecar/services/llm/openai.py:49`, `sidecar/services/llm/anthropic.py:82`, `sidecar/services/llm/groq.py:38`, `sidecar/services/llm/ollama.py:51`

---

### Finding T2-mypy-macro-provider-literal: Macro providers pass untyped `str` where `MacroProvider` Literal required — 4 files, ~50 call sites [S2] [status: open]

**Tool:** mypy 2.1.0
**Detection (representative sample):**
```
sidecar\services\macro\world_bank_provider.py:48: error: Argument "provider" to "MacroCatalogEntry"
  has incompatible type "str"; expected "Literal['fred', 'ecb', 'imf', 'world-bank']"  [arg-type]
sidecar\services\macro\fred_provider.py:283: error: Argument "frequency" to "MacroSeriesExtended"
  has incompatible type "str | None"; expected "Literal['daily', 'weekly', 'monthly', 'quarterly', 'annual', 'other'] | None"  [arg-type]
sidecar\services\macro\fred_provider.py:285: error: Argument "seasonal_adjustment" to "MacroSeriesExtended"
  has incompatible type "str | None"; expected "Literal['seasonally-adjusted', 'not-adjusted', 'not-applicable'] | None"  [arg-type]
```
Affects `world_bank_provider.py` (~13 sites), `imf_provider.py` (~11 sites), `fred_provider.py` (~14 sites), `ecb_provider.py` (~11 sites).

**Impact:** All four macro provider modules define a module-level `PROVIDER = "<literal string>"` as a bare `str` constant. Pydantic model fields (`MacroCatalogEntry.provider`, `MacroSeriesExtended.provider`, etc.) expect `MacroProvider = Literal["fred", "ecb", "imf", "world-bank"]`. At runtime, Pydantic 2.x validates field values even for `Literal` types — so if a provider module accidentally misspells its `PROVIDER` constant (e.g. `"world_bank"` vs `"world-bank"`), Pydantic would raise `ValidationError` at object construction time. The `frequency` and `seasonal_adjustment` mismatch in `fred_provider.py` is the same pattern: API responses return raw strings from FRED's enum domain but are not validated against the Literal before constructing Pydantic models. In practice, FRED always returns valid enum strings — but the type error means any change to FRED's response schema would silently construct an invalid model rather than raising at the boundary.

**Suggested fix path:** Add explicit type annotations: `PROVIDER: MacroProvider = "world-bank"` (and similarly for all four providers). For `frequency`/`seasonal_adjustment` in FRED provider: either add a cast (`cast(MacroFrequency, freq)`) with a comment, or add a validation step before construction. Fix is mechanical and low-risk — the `MacroProvider` Literal already covers all four valid values.
**Files:** `sidecar/services/macro/world_bank_provider.py:37`, `sidecar/services/macro/imf_provider.py`, `sidecar/services/macro/fred_provider.py`, `sidecar/services/macro/ecb_provider.py`

---

### Finding T2-mypy-oanda-broker-id: `OandaAdapter.BROKER_ID` typed as `ClassVar[str]` conflicts with base class `Literal` union [S2] [status: open]

**Tool:** mypy 2.1.0
**Detection:**
```
sidecar\services\brokers\oanda.py:61: error: Incompatible types in assignment
  (expression has type "str", base class "BrokerAdapter" defined the type as
  "Literal['dhan', 'angelone', 'kite', 'alpaca', 'ib', 'oanda', 'ccxt-bybit',
  'ccxt-binance', 'ccxt-kraken', 'ccxt-coinbase']")  [assignment]
```
**Impact:** `OandaAdapter.BROKER_ID: ClassVar[str] = "oanda"` is annotated as `ClassVar[str]` but the base class expects a `Literal` union. The broker registry (`services/brokers/registry.py`) maps broker IDs to adapter classes — a runtime typo in `BROKER_ID` would route to the wrong adapter. The type annotation weakening (using `str` instead of `BrokerId`) means mypy cannot catch such a regression. The other broker adapters (dhan, kite, etc.) appear to use `ClassVar` without an explicit type, letting mypy infer the narrower literal — OANDA explicitly widens to `str`, losing that narrowing.

**Suggested fix path:** Change `BROKER_ID: ClassVar[str] = "oanda"` to `BROKER_ID: ClassVar = "oanda"` (let mypy narrow to `Literal["oanda"]`) or `BROKER_ID: ClassVar[BrokerId] = "oanda"`.
**Files:** `sidecar/services/brokers/oanda.py:61`

---

### Finding T2-ruff-stale-noqa: Stale `# noqa: BLE001` directives across 6 routers/services [S4] [status: open]

**Tool:** ruff check `RUF100`
**Detection:**
```
sidecar\routers\agents.py:72: RUF100 Unused `noqa` directive (unused: `BLE001`)
sidecar\routers\backtest.py:71: RUF100 Unused `noqa` directive (unused: `BLE001`)
sidecar\routers\brokers.py:132: RUF100 Unused `noqa` directive (non-enabled: `ANN202`)
sidecar\routers\brokers.py:166: RUF100 Unused `noqa` directive (unused: `BLE001`)
sidecar\routers\earnings.py:72: RUF100 Unused `noqa` directive (unused: `BLE001`)
sidecar\openbb_mcp_subprocess\main.py:42,49: RUF100 Unused `noqa: BLE001`
```
`BLE001` is not in the CI ruff config's `select` list (`E`, `F`, `I`, `UP`, `B`), so the suppression directives are non-operational noise.
**Impact:** Cosmetic — stale suppression directives accumulate and mislead future maintainers.
**Suggested fix path:** Remove the `# noqa: BLE001` comments that are not in the enabled rule set, or add `BLE001` to the `select` list if blind-exception catching should be enforced.
**Files:** `sidecar/routers/agents.py:72`, `sidecar/routers/backtest.py:71`, `sidecar/routers/brokers.py:132,166`, `sidecar/routers/earnings.py:72`, `sidecar/openbb_mcp_subprocess/main.py:42,49`

---

### Finding T2-ruff-fast002: FastAPI `Query()` parameters not using `Annotated` pattern — 9 sites [S4] [status: open]

**Tool:** ruff FAST002
**Detection (representative):**
```
sidecar\routers\history.py:17:5: FAST002 FastAPI dependency without `Annotated`
sidecar\routers\indicators.py:41:5: FAST002 FastAPI dependency without `Annotated`
sidecar\routers\tradesa_v2.py:178:5: FAST002 FastAPI dependency without `Annotated`
```
7 additional sites across `macro.py`, `news.py`, `quotes.py`, `screener.py`.
**Impact:** FAST002 is a forward-compatibility style warning. FastAPI still supports the old `param = Query(...)` style; the `Annotated[type, Query(...)]` style is preferred from FastAPI ≥ 0.95.0. No runtime impact.
**Suggested fix path:** Migrate to `Annotated` pattern as a batch cleanup task.
**Files:** `sidecar/routers/history.py:17`, `sidecar/routers/indicators.py:41,46`, `sidecar/routers/macro.py:73`, `sidecar/routers/news.py:67,71`, `sidecar/routers/quotes.py:26`, `sidecar/routers/screener.py:52`, `sidecar/routers/tradesa_v2.py:178,192,211,225,226,281,372`

---

### Strict-mode noise summary (S3/S4, not enumerated individually)

- **S608 false positive** (`audit_log.py:189`): ruff flags the f-string SQL in `export_csv` as potential SQL injection. Analysis: `where_clause` is always either `""` or the hard-coded literal `"WHERE timestamp_ms BETWEEN ? AND ?"` — never user-supplied. Parameters are always bound via the parameterized `params` tuple. This is a false positive; the actual read-only connection (`PRAGMA query_only=ON`) adds a second layer. Suppress with `# noqa: S608` + a comment.
- **S110** (`try/except/pass` without logging): Present in `main.py:39`, `openbb_mcp_subprocess/main.py:49`, `sec_edgar_mcp_subprocess/main.py:48`, `analyst_ratings_extended.py:162,278`, `brokers/alpaca.py:296`, `brokers/registry.py:92`. Most are intentional "parent process is gone → exit" patterns or SDK-level retry guards. Legitimate uses should be suppressed with rationale comments; the `analyst_ratings_extended.py` uses should be reviewed individually for logging coverage.
- **D (docstrings)**, **ANN (annotations)**, **E501 (line length >100)**: Not enumerated individually — strict-mode noise across the codebase. Ruff's CI config (`sidecar/ruff.toml`) already selects `E,F,I,UP,B` and passes cleanly; ALL-mode adds ~80 additional noise findings not worth cataloging here.

---

## Summary

| Severity | Count |
|----------|-------|
| S1 | 0 |
| S2 | 4 |
| S3 | 1 (CVE, transitive, unreachable code path) |
| S4 | 2 (stale noqa + FAST002 batch) |
| **Total** | **7** |

### Top-priority recommendations

1. **[S2] T2-dead-earnings-ternary** — `earnings_provider.py:253` `if False` hardcodes `eps_stddev = None`. Restore the intended growth-column read. This is the only production S2 with a direct data quality impact on a user-facing model (Strategy Critic uses `eps_estimate_stddev`).

2. **[S2] T2-mypy-llm-override** — `LLMProvider.stream_chat` ABC return type is `Coroutine[..., AsyncIterator]` (because it's `async def`) but all four implementations are async generators. Fix the ABC annotation to remove the `async` keyword (or use `AsyncGenerator`). Low-risk mechanical fix, closes a semantic contract gap that could cause confusion if the LLM layer is extended.

3. **[S2] T2-mypy-macro-provider-literal** — Add `MacroProvider` type annotation to `PROVIDER` constants in all four macro providers; add casts for `frequency`/`seasonal_adjustment` in `fred_provider.py`. Prevents a future provider ID typo from silently passing through Pydantic validation.

4. **[S3] T2-cve-autobahn** — Pin `autobahn>=20.12.3` as an explicit transitive constraint. CVE-2020-35678 is unreachable from this codebase's usage of `kiteconnect` (no `KiteTicker` usage), but the pin is cheap insurance and documents the intentional decision.

5. **[S2] T2-mypy-oanda-broker-id** — Change `BROKER_ID: ClassVar[str]` to `ClassVar` in `OandaAdapter` to restore mypy's ability to narrow to `Literal["oanda"]`.
