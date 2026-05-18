# Phase 8 — Bug Catalog (Living Document)

**Sprint:** Phase 8 — Claude-Code-driven deep audit against the v0.7.0 surface.
**Baseline commit:** `005a8d0` (housekeeping `5325528` on top of v0.7.0 release
commit `3f4c9de`).
**Sprint window opened:** 2026-05-18.

This document is updated progressively as audit dimensions surface findings.
Skeleton first; commit per dimension as findings land. If the session dies or
auto-compacts, the catalog survives in git history and is the canonical
re-orientation surface (`git log -- docs/PHASE_8_BUG_CATALOG.md` shows the
order of arrival).

---

## How to use this document

Every audit dimension (L1–L11 lead + T1–T5 teammates) appends findings to its
own section using a single canonical entry format:

```
### Finding <prefix>-<id>: <title> [S<severity>] [status: <state>]

**Repro:** <minimum steps to surface the issue>
**Impact:** <what the user sees / what's broken / what's at risk>
**Suggested fix:** <one paragraph — the specific intervention>
**Files:** <path:line references>
**Notes:** <optional caveats, links to related findings, etc.>
```

- `<prefix>` is the audit dimension tag: `UC1`–`UC5` for the use-case exercise,
  `L3`/`L4`/`L5`/`L6` for the lead audit dimensions producing findings here,
  `L8`–`L11` for the lead's concurrent dimensions, `T1`–`T5` for teammate
  audits (cross-referenced — primary detail lives in their own doc), `X` for
  cross-cutting / audit-introduced findings.
- `<id>` is a short stable slug (`fastmcp-runtime`, `kill-switch-toggle-react-warn`,
  etc.) chosen at write-time. Numbering is fine too (`UC1-01`, `UC1-02`).
- Severity `S1`–`S4` per the scheme below.
- Status starts `open`; transitions to `fixed <sha>` / `hot-patched <sha>` /
  `deferred-S3` / `deferred-S4` / `no-repro` / `wontfix` as the fix loop
  progresses.

The **Fix log** at the bottom maps each commit SHA back to its finding(s) for
easy audit during the morning operator review.

---

## Severity scheme

| Level  | Definition                                                                              | Action this sprint                |
| ------ | --------------------------------------------------------------------------------------- | --------------------------------- |
| **S1** | Blocks ship — broken UC flow, runtime crash, §6.5 violation, contract violation, gate-bypass | **Fix this sprint** (mandatory)   |
| **S2** | Visible-to-user bug, broken non-load-bearing feature, hot-patch-worthy audit finding    | Fix if cheap (<30 min, no Tier-1) |
| **S3** | Polish, technical debt, low-impact UX defect, strict-lint-mode noise                    | BLOCKERS.md → v0.8.x backlog      |
| **S4** | Carry-forward to Phase 9 manual Mac test / Phase 10 launch ops / v1.x                   | BLOCKERS.md → matching section    |

**Automatic-S1 categories** (any finding here is S1 regardless of triviality):

- §6.5 architectural drift (L5 findings)
- Tier-1 LOCKED file would be modified (route via BLOCKERS.md → next phase)
- Gate that should have caught a class of bug doesn't (L4 findings on a missed
  gate)
- Plugin contract Tier-1 (`types/plugin.ts`) violation
- Runtime crash on sidecar-tool exercise

## Tag-selection criterion

Tier-2 decision deferred to end of fix loop. Count of S1 fixes (`git log --oneline
v0.7.0..HEAD | grep -c '^[a-f0-9]\+ fix(phase-8/'`) determines the tag prefix:

- **0 S1 fixes** → `v0.7.1` (audit-only release; value is the documentation +
  meta-verification proof + carry-forward list)
- **1+ S1 fixes** → `v0.8.0` (substantial S1 fixes shipped)

---

## §10 UC1 — Solo Founder's Quant Day

Exercise: Tradesa V2 wrapper panels (READ-ONLY) → AI Risk Analyst review →
backtest a strategy.

_(empty — L2 fills as the exercise runs)_

## §10 UC2 — Research Workflow

Exercise: cmd+K → "Research XYZ" → AI Researcher pulls data → chart + news in
adjacent panels → backtest dividend strategy → save workspace.

_(empty — L2 fills)_

## §10 UC3 — Earnings Playbook

Exercise: node-editor workflow → AI thesis per earnings name → alert on entry
trigger → desktop notification → review thesis.

_(empty — L2 fills; Phase 7 F8 desktop-notification bridge is the new
load-bearing surface here)_

## §10 UC4 — Academic Researcher

Exercise: custom agent → workflow pulls SEC + sentiment → outputs to chart →
workspace becomes reproducible dissertation methodology.

_(empty — L2 fills; v0.7.0 sec-edgar-mcp `--collect-data=edgar` is the new
load-bearing surface)_

## §10 UC5 — Macro Thesis Watcher

Exercise: yield curves + central bank tracker + commodity dashboard → AI Macro
Researcher monitors news → notifications on thesis-confirming events.

_(empty — L2 fills; Phase 6 macro module is the substrate)_

---

## L3 — Sidecar runtime-gap findings

Smoke-test catches BOOT crashes; this dimension catches RUNTIME crashes
(sidecar boots, dies on first tool call because of dynamic file path that only
resolves at runtime). Scans for `importlib.resources`, `pkgutil.get_data`,
`__file__`-relative path joins, `pkg_resources.resource_*` in the main
sidecar + openbb-mcp + sec-edgar-mcp + their transitive deps.

_(empty — L3 fills)_

## L4 — Meta-verification gate findings

Deliberate breakages on a throwaway branch; each gate must fail loud with a
clear error. Detail lives in `docs/PHASE_8_GATE_VERIFICATION.md`; any gate
that DIDN'T fire when it should have → finding here as automatic-S1.

_(empty — L4 fills)_

## L5 — §6.5 architectural drift

Grep-based audit of the broker-execution surface. Per CLAUDE.md "Defense-in-
depth for safety-critical surfaces": type-level gate + DB-enforced invariant +
grep-able audit check. This dimension is the grep-able audit; any finding is
automatic-S1.

**Audit complete — zero findings, architectural surface clean.**

Patterns checked (each grep + manual analysis):

1. **New public methods on `broker_base.py`?** No. Public surface = 11 documented members:
   - Properties: `mode`, `read_only`, `connected`, `state()`
   - State mutators (all audit-logged): `set_mode`, `set_read_only`, `connect`
   - Read-only: `account_info`
   - Order entry: `propose_order` (sync), `confirm_and_place` (async — sole `_place_confirmed` caller)
   - Order management: `cancel_order`

   _Note: my plan-doc listed `set_position_limits` as expected — that method does not exist; per-broker position limits are enforced at `propose_order` time via the per-adapter `CAPABILITIES` / position-limit class var. Spec misremember on my part, not a finding._

2. **New `_place_confirmed` call sites outside `confirm_and_place`?** No. Single production call site at `sidecar/services/broker_base.py:365` (inside `confirm_and_place`). All other matches are either definitions in the 7 per-broker overrides, docstrings, the test audit suite (`test_safety_end_to_end.py::test_audit_2_no_bypass_path_to_place_confirmed`), or comments. The grep-time audit at `test_safety_end_to_end.py:178` runs a recursive grep + filters out signatures + comments and asserts the suspicious-call-sites list is empty.

3. **New `audit_orders` UPDATE/DELETE write paths?** No. Only matches are intentional test paths at `tests/test_audit_log.py:141,156` and `tests/test_safety_end_to_end.py:268,274` that explicitly verify the SQLite triggers fire and raise `IntegrityError`. The append-only DDL (`sidecar/models/audit_log.py::AUDIT_LOG_DDL`) plus `PRAGMA query_only=ON` on the reader connection enforce the invariant; tests prove it.

4. **New backend-internal `confirm_and_place(human_confirmed=True)` paths with no UI surface?** No. All non-test matches resolve to `sidecar/routers/brokers.py:225` (the UI route handler) which passes `human_confirmed=request.human_confirmed` — the value comes from the UI POST body, not a backend hardcode. All other matches are inside the `sidecar/tests/` tree.

5. **New imports of broker internals from outside the broker package?** No. All matches are allowed callers:
   - `sidecar/routers/brokers.py:46,47,48` — the broker router
   - `sidecar/services/brokers/{registry,oanda,kite,ib,dhan,ccxt_exec,angelone,alpaca}.py` — inside-package adapters
   - `sidecar/tests/*` — test suite
   - `sidecar/services/audit_log.py:156` — false-positive match on a docstring quoting `from services.audit_log import` as text, not an actual import.

**§6.5 architectural invariants are intact 10 releases after the v0.5.0 audit.**

### Adjacent observation (NOT a §6.5 finding — separate dimension)

`brokers_registry.bootstrap_default_adapters()` only registers the 3 India
brokers (Dhan, AngelOne, Kite). The 4 non-India adapters (Alpaca, IB, OANDA,
ccxt-exec) exist as classes and are imported in
`sidecar/services/brokers/__init__.py` but no production code path
instantiates + registers them. The `registry.py` docstring claims "Other
teammates' adapters (Alpaca, IB, OANDA, ccxt-*) are wired through their own
`bootstrap_*` entrypoints" — those entrypoints do not exist. This is not a
§6.5 violation (safety enforcement is upstream of registry membership) but
**may surface as a UC1/L9 broker-connect finding**: any `/brokers/<non-India-
id>/...` request would raise `KeyError`. Recorded below in the cross-cutting
section for L9 to confirm at exercise time.

## L6 — Performance baseline anomalies

Detail lives in `docs/PHASE_8_PERF_BASELINE.md`. Findings here are
**anomalous** measurements only — a panel that takes 30 s to render, a
sidecar that 5×'es its memory in 60 s of polling, etc. Baseline numbers
themselves belong in the perf doc, not here.

_(empty — L6 fills if anomalies surface)_

## L8 — BYOK AI-agent end-to-end

Per-provider verification of the chat sidebar + tool-use round trip.

_(empty — L8 fills)_

## L9 — Broker connect + §6.5 cycle

Paper-mode broker exercise (whatever credentials are available on the
operator's machine) + failure-state UX for the brokers without credentials.
The full §6.5 propose → confirm → place → cancel cycle must produce an audit
log entry visible in the Audit Log panel.

_(empty — L9 fills)_

## L10 — Workflow + backtest cross-cutting

Every workflow template in the registry must run. Strategy Critic comments.
Equity curve. Trade log.

_(empty — L10 fills)_

## L11 — Accessibility + keyboard nav

Tab nav, screen-reader sanity, color-contrast WCAG AA spot-check on dark
theme.

_(empty — L11 fills)_

---

## Teammate cross-references (T1–T5)

Each teammate's audit has a dedicated doc. Findings here are 1-line
cross-references with severity + status; primary detail lives in the
teammate's doc.

### T1 — Visual regression (`docs/PHASE_8_VISUAL_REGRESSION_REPORT.md`)

_(empty — populated at I1 merge time)_

### T2 — Python sidecar audit (`docs/PHASE_8_SIDECAR_AUDIT.md`)

_(empty — populated at I1 merge time)_

### T3 — Rust audit (`docs/PHASE_8_RUST_AUDIT.md`)

_(empty — populated at I1 merge time)_

### T4 — Plugin contract + plugin runtime (`docs/PHASE_8_PLUGIN_AUDIT.md`)

_(empty — populated at I1 merge time)_

### T5 — Coverage + docs truth-alignment (`docs/PHASE_8_COVERAGE_AND_DOCS_AUDIT.md`)

_(empty — populated at I1 merge time)_

---

## Cross-cutting / audit-introduced findings (X)

Findings that don't slot cleanly into any single audit dimension — usually
discovered while pursuing another dimension and recorded here so they don't
get lost.

### Finding X-broker-bootstrap-india-only [S? — confirm at L9] [status: open]

**Repro:** `sidecar/services/brokers/registry.py::bootstrap_default_adapters`
only registers `DhanAdapter`, `AngelOneAdapter`, `KiteAdapter`. The 4
non-India adapters (`AlpacaAdapter`, `IBAdapter`, `OandaAdapter`,
`CcxtExecutionAdapter`) are imported in `services/brokers/__init__.py:27-33`
but never instantiated + registered by any production code path. The
`registry.py` docstring (lines 13-14, 97-103) implies these adapters have
their own `bootstrap_*` entrypoints; `grep -rn 'def bootstrap_' sidecar/
services/brokers/` returns only `bootstrap_default_adapters`.

**Impact:** At sidecar startup, a `POST /brokers/alpaca/connect` (or `/ib/`,
`/oanda/`, `/ccxt-*/`) would raise `KeyError: no broker adapter registered
for id='alpaca'` via `brokers_registry.get`. UC1 paper-mode broker connect
through Alpaca is the most likely operator path; L9 will exercise.

**Suggested fix:** Either (a) extend `bootstrap_default_adapters` to register
all 7 broker classes guarded by a feature flag per broker, OR (b) make the
broker-connect router lazy-register on first request when the broker's
plugin is enabled. (b) is closer to the plugin-architecture spirit but is
more invasive; (a) is one-commit cheap.

**Files:**
- `sidecar/services/brokers/registry.py:97-112` — `bootstrap_default_adapters`
- `sidecar/services/brokers/__init__.py:27-33` — adapter class imports

**Notes:** Severity deferred to L9. If L9 confirms the broker-connect UX
gracefully degrades ("broker not bootstrapped — connect through the broker
plugin first" or similar), S3. If L9 sees a raw `KeyError` 500 response or a
React crash, S2 (or S1 if it blocks UC1 entirely).

---

## Fix log

Commit SHA → finding ID(s) mapping. Each S1 fix lands as one commit with
message `fix(phase-8/<finding-id>): <summary>`; this section lists them in
the order they shipped.

| Commit SHA | Finding ID(s) | One-line summary |
| ---------- | ------------- | ---------------- |
| _(empty)_  | _(empty)_     | _(empty)_        |

---

## Sprint summary (filled at G1 / handoff time)

- **Audit dimensions completed:** _(N / 9)_
- **Total findings:** S1: _N_ • S2: _N_ • S3: _N_ • S4: _N_
- **Fix outcomes:** S1 fixed: _N_ • S2 hot-patched: _N_ • S3 deferred: _N_ •
  S4 deferred: _N_
- **Tag shipped:** _(v0.7.1 or v0.8.0)_ at commit _(SHA)_
- **Tier-1 lock status:** _types/plugin.ts diff vs v0.7.0 = (empty / non-empty)_
- **§6.5 audit status at tag:** _9/9 PASS_
- **CI status at tag:** _green on N/3 OSes_
- **Sprint wall-time:** _(hours)_

---

*Living document — update progressively, never batch.*
