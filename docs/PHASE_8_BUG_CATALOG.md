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

_(empty — L5 fills)_

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

_(empty — populated opportunistically)_

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
