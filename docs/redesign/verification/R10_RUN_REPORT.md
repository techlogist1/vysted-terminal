# R10 Run Report — Open the engine (data, wiring, trust)

(Morning report lands here at close.)

---

## Telemetry (running)

| Phase | Window | Agents | Notes |
| ----- | ------ | ------ | ----- |
| Plan (plan mode) | 22:0x–22:4x | 3 Explore (~3 reports) + 2 Plan agents + lead | Docs/memory read; tree clean = origin/004 @393e8e5; graph fresh; root causes confirmed IN SOURCE before GO (resolver fuzzy factory, mode-from-payload, 20s carry + auto-mode "applied" lie, screener unbounded batch, copilot allow-list drift, no error humanizer); operator GO |
| 0 — repro + foundation | 22:4x– | lead | Caffeinate armed; r9 briefs archived (7d12ccc); RESOLVER CLASS REPRODUCED STATICALLY: `research Reliance`→REFR 0.798, `Reliance Q4 results`→FRLCY 0.686, `Reliance Industries Q4 FY26 results`→LNKS 0.712 (binds at research's 0.5 floor, questions at agent's 0.72 — the two-organs split); RECX="Recreatives Industries, Inc." (us master), RPOWER="Reliance Power Limited" (nse master); live autosave blob carries an identity-less brief (query='', symbol=None) — archived as r10/regression/; sidecars force-rebuilding |

## Phase log

- 22:0x plan mode: R9/R8/R7 reports + DECISIONS + LESSONS + design system read; 3 Explore agents mapped resolution/research/brief, screener/toolbelt/portfolio, errors/Tradesa/actions; 2 Plan agents designed the one-resolver+lifecycle and screener-universe+capability architectures; key facts verified directly in source (copilot.json missing run_custom_backtest + quant four; auto-publish mode default; Tier B symbol=""; region-or-US default; nifty50.json=50 rows).
- 22:4x GO. Tasks #1–#10 opened. Caffeinate 28800s armed. r9 stray briefs committed (7d12ccc).
- 22:4x Phase-0 static repro (sidecar venv python, no app needed): the wrong-entity factory pinned live (table in R10_DEFECT_CATALOGUE.md E1); marquee silent-bind confirmed ("Tata"→TCS clamped 1.0, "Bajaj"→BAJFINANCE 1.0); thresholds split confirmed (0.5 research vs 0.72 agent vs 0.6 fuzzy floor).
- 22:4x Stale-brief provenance: live `__autosave__.vysted-workspace` brief has query='' symbol=None mode=FAST — restores as-current on every boot; the ₹2,088 artifact itself already overwritten (no provenance trail exists — that IS defect E3.1). Blob archived to verification/r10/regression/.
- 22:5x R10_DEFECT_CATALOGUE.md (E1–E11) written; DECISIONS D36–D45 appended; sidecar force-rebuild running in background.
