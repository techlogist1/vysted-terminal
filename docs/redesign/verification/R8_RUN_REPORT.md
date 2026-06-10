# R8 Run Report — Cleanliness & Truth pass

(Morning report lands here at the end of the run.)

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
