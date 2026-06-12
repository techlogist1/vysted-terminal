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
- 23:1x Phase 1 contracts committed (556aa3f): ResearchExecution, BriefExecution/disambiguation/derived legs, india universe ids + honest-coverage block + SSE frame, data-write/settings kinds. Full vitest green, targeted pytest green, format/typecheck green.
- 23:3x Six track briefs committed (0e2446e) and the fan-out workflow launched (wf_3d774b10-8d4): 6 worktree teams (resolve, runtime, screener, fe-brief, fe-data sonnet, errors sonnet), each impl → fresh-context adversarial review → bounded fix rounds.
- 23:4x Phase-0 LIVE round on the rebuilt running stack (sidecar :60298, CONNECTED · OpenRouter · DeepSeek V4 Flash): E1 CONFIRMED LIVE — /resolve binds `research Reliance` → REFR 0.798, needs_disambiguation:false, region defaulted US; Q4-salad ranks LNKS over RELIANCE. Screener nifty50 probe returned in 2.9s on the warm precompute (the hang needs cold cache + Yahoo throttle — the unbounded batch call is the structural truth; the warm loop was observed rate-limited at boot). E10 CAPTURED: streamed text overdraws the "VYSTED COPILOT" author label mid-stream + status strip overlays the context row (r10/phase0/01-streaming-t2.png; clean after stream completes in 02). Portfolio panel HAS a manual-entry row (symbol/qty/cost-basis/class/note + Add) — E6 is purely the missing agent capability.
- Phase 0 closed. E2's live half deliberately rides the gate battery (source evidence conclusive; saves spend for the validation battery).
- 00:1x Reference-data workflow returned (12 agents, 604k tok, 213 tool uses, 26.5min): 10 stock packs sourced from official NSE bhavcopy/52-week archives + BSE APIs + screener.in cross-checks, with trap annotations (ITC Q4 PAT −72.4% reported = demerger base effect, +6.1% adjusted; excise reclassification inflating revenue growth — exactly the semantics-layer test cases). IT-screen ground truth: 31 verified matches + near-misses. Committed 94bd814.
- 00:52 SESSION LIMIT cut the fan-out mid-flight (R9 precedent): runtime PASSED r1; resolve/screener/errors had fix-r1 done but re-reviews died; fe-data died at review r3; fe-brief died entering fix r1. 23 agents, 3.87M tok, 1,900 tool uses to that point.
- 14:46 Operator returned post-reset; fan-out RESUMED from the journal (same run id wf_3d774b10-8d4; cached agents replay, dead ones re-run). First-run review verdicts logged: runtime pass; resolve 1 blocker (region-flip vitest breakage in money formatting — fix landed) + the _clean_tokens verb-strip minor (new bind class, will not ship); screener 3 majors (crawler wedge, 4.19s boot seed, stale-field non-clearing) + BSE bulk INDUSTRY dead live (sector map 793/4,875 — prune-may-only-widen keeps correctness); fe-brief majors (swallowed portfolio write failures); fe-data lead-snippets wrong (lead wires saved-screens persistence at merge); errors FORKED STALE (pre-contracts base — needs rebase + the marketplace/keychain edits that only exist on the new base).
