# R12 Run Report — The Finisher

## Morning report (read this first)

**R12 removed the question mark and finished the machine.** The unknown gap run turned out to be **two** runs, not one: after R10 closed, a read-only R10-VERIFY census was adopted (commit 46e6c43), then a full R11 DATA PERFECT sprint (D52–D61) shipped the cold-start data layer and tagged `r11-data` at HEAD. I proved this from the repo, not the relayed claim — and re-ran the entire gate chain to confirm R12 started exactly where R11 said it left off: pytest 2237/1, vitest 1478/134, full chain green, no drift, sacred files byte-identical. That baseline held; R10 and R11's work was preserved, never relitigated.

**Then the data trust was hardened against the world, and it held.** The cold-cache screener — the wound R10 closed and R11 healed — was re-proven from a deliberately deleted fundamentals cache on this real, throttling IP: the operator's exact IT-services query returned **22 correct rows in 17 seconds**, SAKSOFT in the set, with an honest PARTIAL badge and per-tier freshness. Four more screens (dividend, value, growth, a deliberately heavy 5-margin india-all sweep) all completed-or-failed honestly, sub-second. The pasted-formula path and the agent-authored path both returned the identical 22-row set through the one engine. An induced provider throttle (via the D53 rig-trippable route) degraded honestly — 22 rows, throttled flag, coverage reported, no hang — and recovered on reset.

**A ten-stock accuracy battery against live web sources found real defects the pipeline had never seen — and every one is now fixed and re-verified.** Ten fresh names (none from any prior battery: SBIN, ICICIBANK, BHARTIARTL, DEEPAKNTR, RADICO, GUJGASLTD, RUBYMILLS, MOL, and BSE-only 509470 / 503229), each independently researched by its own web agent and diffed figure-by-figure by a fresh-context auditor: **142 ok / 61 watch / 13 mismatch / 1 flagged "fabrication" — zero true app fabrications.** The mismatches were not noise; they were the app's data layer being wrong in ways worth fixing:

- The "fabrication" was **real**: the app's brief on Gujarat Gas described a demerger that actually happened — the company was **renamed Gujarat Gas → Gujarat Energy, symbol GUJGASLTD → GUJENERGY, effective July 1** (eight days before the run), and the app was serving the stale identity while yfinance's own payload already carried the new name. → **D67**: an NSE symbol-change lane (live-verified against nsearchives) + an identity cross-check that flags a canonical-vs-provider name disagreement, wired into every research path.
- **Growth numbers wrong on their own claimed basis**: ICICIBANK's provider revenue growth read +66.9% where the exchange statements say +2%; SBIN's earnings growth had a sign flip; RADICO was off on both legs. → **D66**: a deterministic quarterly-YoY cross-check that recomputes from the company's own statements and flags a conflict (both values, both bases, the quarter labels) — never silently substituting.
- **A research narrative confabulated five specific filing dates** for a corporate action, one chronologically impossible. → the narrative synthesis prompts (all four) and the copilot prompt now forbid stating uncited dates/filing numbers/record dates.
- **The order-review dialog was unreachable from chat** because "buy 5 shares of X" classified as a read intent, which stripped the order tool. → **D68**: order verbs added to the intent classifier. Fail-closed, so it was never a safety hole — but the designed prepare→review→confirm UX was dead, and now it works.
- Plus: an agent screener capability gap (**D64** — the tool schema documented only numeric filters, so the model swept everything and post-filtered lossily), a backtest that reported a confident all-zero result when the position size was unaffordable (**D65** — now discloses "N signals skipped"), and a BSE-scrip "52-week range 0–0" card that read as fabricated data (now guarded).

**The §6.5 safety carve-out was proven live — R11's cut-short crown jewel.** Under both glm-5.2 and kimi-k2.6, driven through the terminal's own bridge: "buy 5 RELIANCE" → the copilot calls propose_order → the review bar renders "BUY 5 RELIANCE.NS (MARKET) — ROUTES TO THE CONFIRM-BEFORE-PLACE DIALOG · NOTHING IS PLACED AUTOMATICALLY" → an explicit human ACCEPT → the order **fails closed** ("no broker adapter registered") → and `audit_orders` stayed at **zero rows** through the entire flow. The agent can prepare an order and a human can accept it, and it still cannot be placed in-app. That is the safety model working exactly as designed, shown rather than asserted.

**Every E1–E11 and V1–V11 entry is dispositioned, and the two R11 fixes that shipped without a test now have one.** The disposition table (r12/DISPOSITION_TABLE.md) carries all 33 entries: 28 RESOLVED with a grep-verified pin, 3 NOT-A-DEFECT with rationale, and the two pin gaps (crawler throttle-vs-absence, bar_loader Semaphore(8)) closed by a dedicated worktree.

## Ten-stock battery diff summary

| Symbol | Cap | Identity | ok/watch/mismatch | Disposition of mismatches |
|---|---|---|---|---|
| SBIN | large | ✓ | 14/8/2 | growth (D66, live drift) |
| ICICIBANK | large | ✓ | 18/7/1 | revenue growth +66.9% vs +2% → D66 conflict fires |
| BHARTIARTL | large | ✓ | 16/7/0 | clean |
| DEEPAKNTR | mid | ✓ | 19/3/0 | clean (growth near-correct, no false conflict) |
| RADICO | mid | ✓ | 14/6/2 | growth both legs → D66 |
| GUJGASLTD | mid | rename | 7/10/2+1 | renamed→GUJENERGY (D67); narrative dates (fixed) |
| RUBYMILLS | small | ✓ | 19/5/1 | filing-status claim (narrative discipline) |
| MOL | small | ✓ | 13/5/0 | clean |
| 509470 (Bombay Oxygen) | micro | ✓ (re-driven) | — | prior collection contaminated; re-drive clean; raw-.BO junk-row → hardening |
| 503229 (Simplex Realty) | micro | ✓ (re-driven) | — | prior contaminated; re-drive clean; growth-scaling → hardening |

Re-validation on two additional fresh names (AARTIIND, ROSSTECH) confirmed D66 agrees-and-stays-silent when provider ≈ statements and flags only genuine divergence.

## Disposition table

See `r12/DISPOSITION_TABLE.md` — 33 entries, 28 pinned-RESOLVED, 3 NOT-A-DEFECT, 0 dropped. Five R10 hand-fixes all confirmed test-pinned.

## Action-surface audit

See the COVERAGE_MAP.md "Agent action surface" section — screen authorship (D64), portfolio scenario (Gate 6 pin), backtest agent=engine parity (D65), tool-stall honesty, and the §6.5 live carve-out (D69) all proven by driving, not reading.

## Loop telemetry

- Lead: Fable 5 advisor-orchestrator (never spawned a Fable teammate). Teammates: Sonnet 5 (readers, battery collectors, narrative fix, test pins) and Opus 4.8 (growth, identity, hardening — risk-adjacent). Every reader/collector self-reported its model; routing confirmed (no silent Fable inheritance).
- Workflows: Phase-A census (7 agents), battery reference packs (11), battery collect+diff (20), fix-verification (6). Plus standalone teammates for disposition, pins, growth, identity, narrative, hardening.
- Checkpoints committed + pushed at every green boundary (41ab707 … and on). Strategy changes logged in the run-state (workflow-args string bug, stdin-EOF watchdog, operator-presence re-sequencing).

## NEEDS-MANUAL-CHECK (your checklist)

In-webview drags (permanent — no rig synthesizes trusted drags); the ~960px narrow-width / clipped-text sweep; a fresh R12 re-shot of the screener throttle chips (R11 gui-12 proves them live); and the taste pass. See R12_HAND_TESTING_GUIDE.md.

## Final gate chain

- **Full `ci-local` GREEN** (byte-for-byte CI mirror, R12 HEAD, sidecars rebuilt with all R12 code): install → ensure-all-sidecars → eslint (0 errors, 1 pre-existing EquityOverview warning carried since R10) → prettier → tsc → cargo fmt → clippy `-D warnings` → ruff check+format → **vitest 1481 / 134 files** → cargo test → **pytest 2311 passed / 1 skipped**. Baseline at R12 start was 2237 / 1478 — R12 added **74 sidecar + 3 frontend test pins** across D64–D68, the growth/identity/narrative/hardening fixes, and the 2 R11 pin-gap closures.
- **PyInstaller `--onefile` BUILDS AND BOOTS — all three sidecars** (`r12/regression/onefile-boot-proof.md`): ensure-all-sidecars rebuilt the main onefile binary (105 MB, ≤120 MB target); spawned on a throwaway port it answered `/health` in 20 s, resolved **ICONIKSPEV → Iconik Sports And Events Ltd, BSE, conf 1.0** (the deterministic hard check), and served a live nifty50 screener (27 rows) with the R11 seed pack loaded and the Yahoo circuit breaker cycling — the whole cold-start data stack functions inside the release artifact. The two MCP sidecars (openbb-mcp 49 MB, sec-edgar-mcp 81 MB — byte-identical to R11's already-smoke-tested June-14 builds since R12 changed only the main sidecar) were spawned on throwaway ports with `--no-watchdog` and both booted, bound their ports, and survived without crash (the MCP contract; no `PackageNotFound`/`ModuleNotFound`/traceback). This is the `smoke-test-sidecars.mjs` contract run as a **surgical manual equivalent** — every check (3-binary boot, ICONIKSPEV, MCP survival) on my own throwaway-port processes, deliberately WITHOUT the script's kill-all-vysted pre-flight so the operator's live app was never disturbed. The canonical script is available for an away-window formality; the substance is proven.
- **§6.5 byte-identical**: `git diff 393e8e5 HEAD` over the whole broker/order/audit/kill-switch surface → **0 lines**, byte-identical through R10 + R11 + R12. No R12 commit touched any order/broker/execution path (D70).
- **Sacred files**: `enrich_nse_sectors.py` SHA-256 ends `…286abdbe` — byte-identical to R11's record; `kill-switch-benchmark.json` regenerated by the mandated pytest runs (by design), left uncommitted. One accidental commit-slip of enrich mid-run was caught and reverted (ccf4e76), working bytes never touched.

## Decisions this run

D62 (Phase A truth), D63 (operator-presence protocol), D64 (agent screener capability), D65 (backtest affordability honesty), D66 (growth cross-check), D67 (symbol-rename lane + identity cross-check), D68 (order-intent classification), D69 (§6.5 live proof), D70 (order-surface scope clarification ack), plus the narrative date-discipline + fundamentals symbol-grounding + 52w-range-guard + 5 hardening fixes. Full text in `docs/redesign/DECISIONS.md`.

## Close-out

Tagged **r12-finisher**; branch 004 pushed. Version stays 0.8.0, no merge to main. The five legacy pre-R12 worktree branches were left untouched; the R12 agent branches (growth/identity/narrative/pins/hardening) are pushed as recovery checkpoints. App relaunched on a clean default workspace and left running.
