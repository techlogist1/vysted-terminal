# R8 Run Report — Cleanliness & Truth pass

## Morning report

**The truth pass shipped.** Every failure in your evidence pack is root-caused, fixed, regression-tested, and re-verified on the live app. The research engine now tells the truth: a run binds ONE validated instrument at the top and threads it everywhere (the run that researched "CMTL" while you asked about Reliance, and the run that passed your whole focus sentence into `vysted://fundamentals/...`, are both structurally impossible now — your actual failing briefs are preserved as regression payloads and there are tests that replay them). Results-filing PDFs are genuinely read: I drove a live deep run on Route Mobile and the brief came back with revenue ₹1,130.90 crores and the ₹11/share FY26 dividend (3×₹3 interim + ₹2 final) cited to the May-7 outcome PDF itself; a companion run surfaced PAT ₹114.43 crore, "+~90% YoY," from the exchange feeds. Junk can't count as coverage anymore (entity gate + quality ladder + a filing-title rule so another company's filing can't ride a snippet mention), citations are verified after synthesis (out-of-range markers stripped; a bounded LLM spot-audit softens unsupported claims, sampling web-cited figures first), the SAKSOFT brief's P/E now comes from the same call the panel makes (13.962709 on both sides, byte-identical), and the wall-clock guards degrade instead of aborting — the thin-name ICONIKSPEV deep run completed cleanly with 8 sources and no banner gibberish. "heavy:3 angles" and "per-round wall-clock guard" can never reach a rendered brief again; tests pin it.

**One settings truth.** The legacy "Web search" section — and its docker snippet — is deleted. The Research tier section is the only surface; old workspace blobs migrate (native→t1, local-searxng→t2, byok-exa→t3 with an Exa-direct sub-mode that keeps your existing key working). The sidecar resolves search through ONE path: explicit tier → mapped legacy headers → default that uses your READY managed SearXNG before flooring to keyless. The "SearXNG green but runs claim no web backend" class is dead (pytest-pinned matrix), a stopped t2 instance degrades to keyless instead of going dark, and an explicit t2/t3 choice now suppresses the model's native search.

**The composer is the Claude reference** — a plus button bottom-left opening a Context/Scope/Route-to/Slash menu, a proper 28px send control that morphs to stop, affordant chips, an animated accent on the live depth stop, and a measured collapse ladder so nothing overlaps at any dock width. The proportion law (docs/redesign/R8_PROPORTION_LAW.md) now governs every surface: watchlist price/change columns are collision-proof tracks with drop priorities, provider chips have designed short forms ("YF EOD"), the chart symbol input fits SAKSOFT.NS, the notes toolbar has one icon ladder, AAPL no longer wears a ₹ sign, the stuck autocomplete is fixed, nothing renders under 11px (plugins included), and user chat messages sit at body size in a quiet container.

**Personas have hands.** Every first-party agent gets Copilot's host actions at load time (catalog-derived, test-pinned); I watched Benjamin Graham on DeepSeek open the Equity Overview pre-loaded with INFY and deliver a Graham-voice verdict. A persona pinned to an unkeyed provider no longer produces dead runs. open_panel carries a symbol. Narration stayed grounded everywhere I checked — the agent told me the chart was "still showing ICONIKSPEV" when it was, and proposed cleaning up a cramped layout instead of pretending it was fine.

**Safety re-verified live (§6.5):** with autonomy on AUTO, panel-opens auto-applied while my test order proposal stayed pending behind the confirm-before-place dialog — "I never execute orders directly" — and was rejected without placing anything.

### Decisions, defects, evidence

- `docs/redesign/DECISIONS.md` D14–D25 (D25: explicit-t2-down degrades to keyless — same privacy class, honest backend id).
- `docs/redesign/verification/R8_DEFECT_CATALOGUE.md` — every defect with root cause file:line.
- `docs/redesign/verification/r8/` — 60+ captures, the archived gate briefs (`brief-*.json`, `gate1-*.json`), and your original failing payloads (`regression-brief-cmtl.json`, `regression-brief-saksoft.json`).
- Five team reports: `R8_TRACK_{RESEARCH,SETTINGS,COMPOSER,PROPORTION,SEAMS}_REPORT.md`.

### NEEDS-MANUAL-CHECK

1. **In-webview drags** (dockview tab reorder, node-editor palette→canvas) — still no rig on this Mac can synthesize trusted drags; click through by hand.
2. **Your taste pass** over the governed surfaces — the law held everywhere I audited, but taste is yours.
3. **Dockview tab fragments**: with very many tabs open, a squeezed tab can still render 2–3 characters beside the overflow chip ("Ma", "Bri"). The overflow menu and tooltips work; a dockview `minimumTabWidth`-style fix is the follow-up.
4. **FRED keyless error copy** names the `FRED_API_KEY` env var — honest but dev-flavored; reword to Settings language when convenient.
5. **The ULTRA cross-check on slow models** can exceed its 240s lane on DeepSeek and skips honestly ("Skipped to stay within the run's time budget.") — if you want it to always run, give the ultra profile a bigger wall in `depth.py`.
6. **A 5-query T3 A/B** (sonar vs native) remains your call from R7 — unchanged by this pass.

### How to launch

`cd ~/Documents/dev/vysted-terminal && pnpm tauri:dev` — sidecars build automatically (cold first boot of the onefile sidecar is ~60s; the Rust core now waits 45s×2 instead of false-flagging). The app is left running on the clean default workspace; your gate-battery workspace (briefs and all) is archived as `__autosave__.vysted-workspace.bak-r8-gates`.

---

## Telemetry (phases 3-5)

| Phase | Window | Agents | Notes |
|-------|--------|--------|-------|
| 3 — build fan-out | 20:15-21:45 | 5 worktree teams (A 502k tok/199 tools, B 289k/106, C 257k/89, D 343k/174, E 267k/95) | All five PASSED their gates in-worktree and pushed; lead merged serially with full-suite integration runs after each merge (pytest 1911→1947→1978, vitest 1355→1366→1378) |
| 4 — lead fix loop | 21:45-23:30 | lead + live rig | Post-merge live drive found and fixed: B's flagged native-search gate (agent_runtime t2/t3 suppression + test); persona provider pin demoting on missing key; false "no key" flash during boot probe; designed short model form at the short collapse step; compound provider ids; tradesa-v2 sub-11px floor; the main-sidecar 15s wait (Rust, false "did not come up" + missing FR-025 endpoint file on ~60s cold boots); disclosures fetch window too shallow (results filing at feed index 14 vs limit 12) + results-first ranking; keyword-salad queries unbound (prefix-fallback resolution + query schema steering); explicit-t2-down degrading to keyless (gate 6 semantics, D25) |
| 5 — gate battery + adversarial audit | 23:30-00:40 | lead + 2 verification workflows (5+3 fresh-context verifiers) | Research gates driven through the real composer (trusted CGEvent/AppleScript rig after the socket bridge wedged — root cause found: socket contact during webview boot wedges the plugin permanently; recipe in LESSONS). Each published brief archived from the autosave blob as a regression artifact. Final adversarial audit: ROUTE + SAKSOFT briefs PASS citation spot-audit; RELIANCE audit caught snippet-level filing leakage + one mis-citation → three more engine fixes (filing-title gate, web-cited claim priority in citecheck, humanized cross-check skip reason) |

## Gate evidence (verification/r8/)

1. **ROUTE Q4 FY26** — PASS. Across final-engine runs: PAT ₹114.43 Cr "+~90% YoY" cited to the exchange filings (gate1-route-brief-v2.json); revenue ₹1,130.90 Cr + FY26 dividend ₹11/share (3×₹3 interim + ₹2 final) cited to the May-7 outcome PDF, which is IN the sources (brief-1781111791960.json); a PAT-focused deep run read ₹109.32 Cr attributable-to-owners FROM the PDF and honestly declined to fabricate the YoY base (brief-1781112438711.json). Zero junk sources, zero debug strings, markers in range.
2. **Reliance binds RELIANCE** — PASS. brief-1781110636600.json: symbol RELIANCE, 40 sources, fundamentals leg ok (P/E 21.1) via vysted://fundamentals/RELIANCE; header/tools/title agree. (The CMTL regression payload from the operator's blob is preserved beside it.)
3. **SAKSOFT structured truth** — PASS. brief-1781110916873.json: heavy depth, symbol SAKSOFT, P/E 13.962709 in the brief's leg — byte-identical to the panel path (GET /fundamentals/SAKSOFT.NS → 13.962709); vysted:// URLs carry only clean symbols; zero focus text anywhere.
4. **Banner/body consistency + citation spot-audit** — PASS. ICONIKSPEV FAST (brief-1781111829012.json): body cites no web domains, banner claims none — consistent, with a human note. Fresh-context citation audit: ROUTE deep PASS, SAKSOFT heavy PASS (all markers in range, claims plausibly supported, entity-relevant sources).
5. **Thin-name graceful depth** — PASS. ICONIKSPEV deep (brief-1781110893357.json): completed with 8 sources, markers in range, NO guard abort, NO debug strings, no note.
6. **One search truth** — PASS. Settings shows a single Research section (31-settings-postmerge.png; legacy section + docker snippet deleted); routing matrix pytest-pinned (29 tests incl. READY-manager-never-bypassed and t2-down→keyless degradation); live teardown/setup cycle exercised via /search/searxng/* (container ends READY).
7. **Composer spec** — PASS. 32-composer-plus-menu.png (plus menu with Context/Scope/Route-to/Slash sections); send/stop morph + queue chips exercised live during the gate battery (queued prompts drained serially); meta-row collapse ladder test-pinned (280px anchor) + live narrow captures.
8. **Proportion sweep** — PASS with notes. Final-build captures 50-final-1400-*.png + battery screenshots: watchlist columns collision-free with YF/EOD short-form chips, settings governed, notes icon ladder, INR-correct equity overview. Known-remaining (logged): dockview tabs can still fragment to 2-3 chars at extreme tab counts beside the overflow chip; FRED keyless error copy names an env var; both filed as polish follow-ups, not truth defects.
9. **Persona parity** — PASS. 34-graham-parity-deepseek.png: Benjamin Graham (DeepSeek) opened Equity Overview loaded with INFY and delivered a Graham-voice take; loader-level parity + open_panel symbol arg test-pinned.
10. **Gate chain** — ci-local EXIT 0 at tag tip (lint/format/types/clippy/ruff/vitest/cargo/pytest), smoke test incl. ICONIKSPEV hard check, §6.5 live wiring (52-order-safety-pending.png: with AUTO on, panel-opens auto-applied while the order proposal stayed PENDING behind the confirm-before-place dialog; rejected cleanly).

---

## Telemetry (running)

| Phase | Window | Agents | Notes |
|-------|--------|--------|-------|
| 0 — orientation | 18:30-18:55 | 12-reader recon workflow (~986k tok, 412 tool uses) | R7 docs read; tree clean at 0171f65 = origin/004; graph fresh (built ca34d420, one docs commit behind); sidecars force-rebuilt (exit 0); 5 legacy worktrees identified and left alone |
| 1 — live drive | 18:55-20:10 | lead + rig | Operator's autosave restored the CMTL failure on screen (captured); rig = tauri-mcp socket (IIFE-only evaluate_script; dockview tabs need pointerdown) + Quartz capture via sidecar venv python; 25 captures into verification/r8/; SAKSOFT ULTRA run reproduced focus-contamination live (brief.symbol = the whole focus sentence — saved as regression-brief-saksoft.json); /resolve probes confirmed the mechanism (clean query → RELIANCE @1.0; contaminated → ok:False); /disclosures probes confirmed the May-7 ROUTE results meeting + attachment PDFs are already ingested; SPY chart panel showed "Failed to load price history" while /history/SPY served 64 bars (investigate) |
| 2 — build fan-out | 20:15 | 5 worktree teams dispatched | A research-truth, B settings-truth, C composer/chat, D proportion sweep, E agent seams — disjoint partitions per D24; R8_DEFECT_CATALOGUE.md + R8_PROPORTION_LAW.md written as their common law |

## Phase log

- 18:30 orientation: required docs read; git clean at origin head; caffeinate armed; operator's stale dev stack (from their day of driving) stopped cleanly.
- 18:40 recon workflow (12 parallel readers, file:line maps) + lead deep-reads of iter.py/deep.py/fast.py/research entry: five WS1 root causes CONFIRMED IN CODE before the app was even launched (focus-contamination at iter.py:580+243; PDF rejection at extract.py:225; junk-source accumulation at deep.py:321; guard aborts at deep.py:75/iter.py:428; note debug strings at iter.py:432/656). SearXNG bypass confirmed at web_search.py:132 (legacy "native" default never autodetects the READY manager).
- 18:55 app launched (fresh sidecars, cleared webview caches). Boot screenshot shows the operator's autosaved CMTL brief — query "Reliance Industries Limited", symbol "CMTL", 92 sources, note "heavy:3 angles" — preserved at r8/regression-brief-cmtl.json.
- 19:10-20:10 drive: all panels opened + captured (02-15); chat send verified (16); both settings surfaces captured (17/18 — legacy docker snippet vs R7 tiers with SearXNG green at 8888); narrow-width captures (21/22) show the watchlist column collision + truncation disease; live SAKSOFT ULTRA run (20/23/24/25) reproduced the focus-contamination + "HEAVY:3 ANGLES" banner + "APIs returned null" claim; the run's chart narration WAS grounded (SAKSOFT.NS loaded with RSI/SMA/Volume — 25) but the symbol input clipped to "SAKSO". Equity overview showed ₹ on AAPL market cap + a stuck autocomplete dropdown (19).
- 20:15 build fan-out dispatched (5 teams). Defect catalogue: docs/redesign/verification/R8_DEFECT_CATALOGUE.md. Decisions D14-D24 appended to DECISIONS.md.
- 20:25 lead de-risk checks while teams build: SPY chart failure NOT reproducible (transient provider hiccup; honest Retry state worked) — D11 closed as transient. GATE-1 DE-RISKED: the real ROUTE outcome PDF (nsearchives, 3.9MB/22pp) fetches with plain browser headers and pypdf extracts the figures verbatim — "Profit for the period/year … 114.43", "1,130", "dividend … aggregates to ₹11/- per equity share".

## Gate → verification procedure (planned)

1. ROUTE deep research surfaces Q4 FY26 (PAT ≈114.4 Cr, rev ≈1,130.9 Cr, div ₹11) correctly cited → live ULTRA/DEEP run via composer on rebuilt stack; inspect brief + sources.
2. "Reliance" binds RELIANCE; header/tools/title agree → live deep run; assert brief.symbol + vysted:// calls (autosave blob + dev steps).
3. SAKSOFT structured queries return real fundamentals matching panel; no focus text in vysted:// → live ULTRA run; blob assert symbol clean; P/E matches equity panel.
4. FAST banner/body never contradict; citation spot-audit passes → live FAST run on ICONIKSPEV + deep brief marker audit.
5. Zero debug strings; thin-name deep run completes gracefully → ICONIKSPEV deep run; grep brief for guard/heavy strings.
6. SearXNG live → used; stopped → keyless engages with honest banner; one settings surface → /search/searxng teardown+setup cycle + runs in both states; Settings shows single surface.
7. Composer spec (plus, send/stop, chips, depth animation, no narrow overlap) → rig screenshots default + narrow.
8. Full-app sweep zero clipping at default + narrow → re-run the panel sweep at 1396 + 960 + narrowed panels; fresh-context vision verifiers over captures.
9. Persona parity (Graham drives panels); agent-opened equity arrives loaded → live persona run via lens switch + host action; equity command assert.
10. Full gate chain (ci-local) + PyInstaller boot + smoke (ICONIKSPEV hard check) + §6.5 live wiring re-verify → scripted.
