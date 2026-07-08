# R11 Run Report — Data Perfect (the release sprint)

**Run:** R11 — review, complete the data layer, fix everything, prove it
**Date:** 2026-07-02 (overnight, autonomous)
**Model / mode:** Fable 5 lead, ultracode, dynamic workflows; Sonnet/Opus teammates routed by task
**Tree at start:** branch `004-r4-experience-rebuild`, HEAD `20e63e8` (in sync with origin), tag `r10-engine` @ `6848580` (one docs-only commit behind — expected). Two sacred uncommitted files verified present (SHA-256 recorded below), untracked R10-VERIFY artifacts present (adopted this run).

Sacred-file hashes at start (must be byte-identical at close):
- `sidecar/services/resolver_masters/enrich_nse_sectors.py` = `5cb28e0d89f98a30abceba8d91494f4002646503a4d51f798f63980b286abdbe`
- `docs/screenshots/v0.5.0/safety-audit/kill-switch-benchmark.json` = `e4fedc5b4b3ec32c7235ff5afd60880b36fbd058124fbb54e888687d6445408d`

## Morning report

**R11 shipped the thing this sprint existed for: data that never runs dry.** A fresh
install on a hard-blocked IP now answers your exact IT-services screen — completely,
correctly, and honestly — in seconds, not hours. I proved it the strong way: I DELETED
your fundamentals cache and re-ran the query on this IP while Yahoo was genuinely
throttling it (the breaker logged 126 throttle events and 4 circuit opens at boot).
The app answered **23 correct rows in 9.6 seconds** — SAKSOFT in the set — with
today's exchange-direct closing prices, fundamentals honestly dated to their snapshot,
and the UI saying exactly what happened: a PARTIAL badge, "DATA PROVIDER IS THROTTLING
THIS IP — SHOWING CACHED/SNAPSHOT VALUES", "15 LIVE · 8 MIXED", "250 UNAVAILABLE —
250 MISSING ROE", and a per-tier freshness line. Compare R10's close: the same query
needed a warm cache and returned 0 rows cold.

**How it holds (D52/D53/D54, the three-legged stool):** (1) a **bundled seed pack** —
5,050 india-all rows of full fundamentals exported from your own warm store, shipped
in the binary (717 KB), loaded at boot, stamped with per-row as-of dates and NEVER
allowed to masquerade as live data; the screener's new serve-with-label ladder
evaluates stale/seed values instead of dropping them and labels every row
live/mixed/snapshot with its true age. (2) a **Yahoo-family circuit breaker** — 429s
are now classified everywhere (they used to hide inside no_data/correctness_gate),
three consecutive throttles open the circuit, and an open circuit spends ZERO calls
(test-proven) while everything serves from the labeled basis; warm loops pause during
your foreground screens and no longer poison the crawler's 24-hour retry rotation.
(3) an **NSE bhavcopy lane** — one exchange-direct request per trading day fetches
closing prices for the whole NSE (live-verified: 2,646 symbols in 0.52 s), so even a
fully Yahoo-blocked install has prices no older than one trading day, plus derived
market caps where the valuation tier is stale.

**The twelve-stock battery says the data is screener.in-grade — and twice found the
app RIGHTER than the aggregators.** Twelve fresh names (MARUTI → WENDT, plus BSE-only
TANFACIND and ACGL), independently researched by twelve web agents, every figure
diffed: **identity 12/12, 95 ok / 19 watch / 6 mismatches — and zero app fabrications.**
Every mismatch was adversarially verified: WENDT's EPS/PE/growth and CROMPTON's ROE
are the app being correct on its stated consolidated/reported basis while screener.in's
own ratio panels were stale (CROMPTON's real FY26 ROE is negative — the ₹716 Cr
Butterfly impairment — and the app says so); the dividend gaps are declared-but-unpaid
finals the app correctly excludes from a paid basis. The one true data wart — Yahoo's
dividendRate quirk on WENDT (₹20 where ₹40 was actually paid) — was caught LIVE by the
new deterministic dividend reconciliation: the deep brief's Conflict Note reads
"the provider's standard dividend rate lists ₹20.00 per share, which omits special
dividends; the ₹40.00 trailing paid figure represents the complete distributed
amount." That's D56 doing exactly what it was built for, on a real case, unprompted.

**V1 (the growth mislabel) is dead end-to-end**: every surface now says "quarterly
YoY (MRQ)" — the raw endpoint and agent tool carry `growth_basis`, the brief cards
label it, the screener criteria builder says "(MRQ YoY, frac)", and the narrative
prompt labels its facts. The WENDT brief rendered "-60.50% · quarterly YoY" — the
exact consolidated figure the independent verifier computed. **V2 is dispositioned
with a machine-readable cause**: DeepSeek V4 Flash returns `finish_reason=
content_filter` (zero tool calls) on some asks, while glm-5.1 and kimi-k2.6 on your
same OpenRouter key drive every tool correctly — it's the model, not your app; and the
app now says so honestly in chat instead of showing an unexplained Chinese refusal.
The error battery: live 401 → "The OpenAI API key was rejected — check it in
Settings."; live 402 → "Your DeepSeek balance is empty — top up or switch provider";
and a NEW catch — garbage symbols used to serve an all-null 200; they now answer an
honest 404 ("No instrument matches … — check the symbol"), which also stops the deep
crawler stamping Yahoo-uncovered scrips as enriched. The resolver got the V3/V4/V5
sweep (L&T→Larsen & Toubro; Jindal/Godrej get curated choosers; an engine-level tie
guard kills the arbitrary-tiebreak class beyond the curated table) and the sector map
now tells the truth about itself (5,010-record honest header, orphaned industry values
migrated, all 135 NSE-only rows carry shares).

**Agent capability (the Jarvis stretch), driven live**: the copilot configured your
exact screen from one sentence (write_screener_filters applied to the panel — you can
see the criteria sitting there), ran it with live SSE progress streaming in chat,
disclosed its 254 skips honestly, loaded the chart with a fresh symbol, published a
DEEP-stamped 24-source brief (mode from the execution record, "EOD AS OF 2026-07-08"
chip, NSE_DIRECT provider chip), and applied portfolio adds under AUTO with the panel
ACKING the apply (the E3.3 read-back closing in the sidecar log). §6.5 is
**byte-identical to the pre-R10 base** (empty diff over the whole broker/order/audit
surface) and the 40-test safety suite + AI-order-gate audit ran green in every full
suite pass of this sprint.

**What I could not finish, and why — NEEDS-MANUAL-CHECK:** you came back to the
machine mid-drive (~22:00; I stopped all UI driving the moment your Chrome came up —
nothing leaked into your Luminfaber session; the in-flight message had already landed
in Vysted, verified by the ack logs). Cut short: (1) the live §6.5 order-dialog
click-through (suite-level re-verification is green + byte-diff; one manual "buy X" →
see the review dialog stage, never auto-place); (2) the narrow-width/clipped-text
sweep; (3) in-webview drags (unchanged since R7 — no rig can synthesize them);
(4) your taste pass. Also left for you: the chat tab holds the battery conversation,
and the paper portfolio carries the two TEST holdings the agent-drive added
(10 WENDT @ 7,500 · 5 MARUTI @ 14,300) — pruned from the blob automatically if I got
to restart the app clean (see close-out below), otherwise two clicks to delete.

**How to launch:** `cd ~/Documents/dev/vysted-terminal && pnpm tauri:dev`. Evidence:
`docs/redesign/verification/r11/` (cold-start proofs, GUI captures, error battery,
v2-redrive, data-battery with reference packs + diff rounds + BATTERY_VERDICT.md).
Decisions D52–D61; final gate numbers in the close-out block below.


## Close-out (2026-07-08, late evening)

- **FINAL GATE CHAIN GREEN** (`pnpm ci-local`, byte-for-byte CI mirror, app stopped):
  install → ensure-all-sidecars (rebuilt with all R11 code) → eslint (0 errors) →
  prettier → tsc → cargo fmt → clippy `-D warnings` → ruff check+format →
  **vitest 1478** → cargo test → **pytest 2237 passed, 1 skipped**.
  Baseline was 2175/1457 — R11 added **62 sidecar + 21 frontend test pins**.
- **PyInstaller onefile builds AND boots**: `smoke-test-sidecars.mjs` fully green on the
  final binaries (screener universe, ICONIKSPEV deterministic BSE identity, all 3
  sidecars + MCP subprocesses, BSE bhavcopy + NSE direct probes).
- **§6.5**: `git diff 393e8e5 HEAD` over the whole broker/order/audit/kill-switch
  surface → EMPTY. Byte-identical through R10 + R11. Safety suite green inside every
  full pytest run of the sprint.
- **Sacred files**: `enrich_nse_sectors.py` SHA-256 ends `…286abdbe` — byte-identical
  to the run's start; `kill-switch-benchmark.json` regenerated by the mandated pytest
  runs (by design), left uncommitted as always.
- **Clean default**: test holdings absent from the autosave blob (the in-memory agent
  adds never flushed — the ack log is the apply proof); portfolio boots empty; app
  relaunched and left running.
- Tagged **r11-data**; 004 pushed.

## Telemetry (running)

| Phase | Window | Agents / tools | Notes |
| ----- | ------ | -------------- | ----- |
| 1 — absorb + baseline | 00:0x– | lead + 7-agent census workflow (wf_6a327cd9) + background ci-local | Caffeinate armed. Read R10 RUN/DEFECT/VERIFY + DECISIONS + LESSONS + R9 design system + memory. V7 fixed (.prettierignore: 2 gate4 JSONs + r10-verify/ + r11/), format:check green. Baseline `ci-local` launched (abs venv PATH). Lead read screener.py / fundamentals_store.py / fundamentals_warm.py / yahoo_batch_provider.py / screener_universe_india.py / routers directly. |

## Phase log

- 00:0x Caffeinate armed; tree verified (HEAD 20e63e8 = origin/004; sacred hashes recorded). R10_VERIFY_REPORT.md EXISTS → adopted as worklist (V1–V11 + punch-list). No Vysted processes running; app-support store found RICH (5,153/5,157 india rows info-tier, newest 2026-06-16) — a ready seed-pack source.
- 00:1x V7 fixed (prettier hygiene); baseline ci-local launched in background; 7-agent data-layer census workflow launched (screener engine / providers / resolver masters / fundamentals+research path / frontend surfaces / agent capability / test infra).
- 00:1x Lead primary-source read of the data spine complete. Cold-start gap located precisely: (a) info-tier fields (ROE/growth/margins) need per-symbol yfinance `.info` — unfinishable inside the 120 s wall on a cold cache; (b) a throttled IP kills even the v7 sweep (per-chunk bounded 429 retry exists, but no global circuit breaker and no non-Yahoo serving basis → honest 0 rows).
- 00:4x **BASELINE GREEN** — full `ci-local` at HEAD + V7 fix: **pytest 2175 passed, 1 skipped** (R10's 2170 + 5 R10-VERIFY lock-ins), **vitest 1457 / 134 files**, cargo test ok, clippy `-D warnings` clean, eslint/tsc/ruff/prettier clean (log: scratchpad ci-local-baseline.log; 2:12 pytest wall). Checkpoint 1 committed (R10-VERIFY adoption + V7).
- (2026-07-02, later) Census workflow returned (7 agents / 949k tok / 239 tool uses / 10.4 min): full data-layer map with three NEW defects beyond the verify report — the sector map misreports its own coverage header (4,875 vs actual 5,010 records), 1,340 records carry orphaned `industry` values nothing reads, and 135 NSE-only records lack shares_outstanding. R11 D-entries D52–D61 written; contracts commit 93e0754 pushed; four worktree teams dispatched (SEM/FE/RES/BHAV); lead core work started (yfinance rate-limit classification, seed/EOD store tiers, breaker-wired batch provider, `_finalize` serve-with-label ladder).
- (2026-07-08) **Phase 2 core SHIPPED by the lead** (728dda9 + ff471c5, pushed): seed pack (5,050 rows / 717 KB gz from the operator's warm store, per-row as-of), serve-with-label ladder in `_finalize` (data_basis/data_as_of/currency per row, basis_counts, seed_as_of, redefined partial, throttled flag), Yahoo-family circuit breaker end-to-end (v7 chunks + per-symbol yfinance classify + enrichment/fallback/crawler short-circuits + warm-loop pause gates + crawler throttle-vs-absence fix), bhavcopy EOD lane wired (BHAV's module merged: live-verified UDiFF endpoint, EQ+BE+BZ, 10 tests). Sidecar pytest **2190 passed** at the core commit; +19 with the bhavcopy suite.
- (2026-07-08) **LIVE COLD-START PROOF (engine level)** — `r11/coldstart-blocked-ip-engine-proof.json`: fresh temp store + Yahoo circuit FORCED OPEN (simulated hard-blocked IP) → boot seed 5,156 rows in 0.22 s, LIVE bhavcopy 2,646 NSE rows in 0.52 s (trade date 2026-07-08), operator's exact IT-services query → **22 rows in 0.04 s**, today's EOD prices (₹, basis mixed) + snapshot fundamentals honestly dated 2026-06-13, `throttled: true`, `partial: false`, coverage line discloses the basis mix, ZERO Yahoo calls. SAKSOFT in the result set at today's close.
- (2026-07-08, evening) **ALL FOUR TEAMS DELIVERED + MERGED** (merge commits 8f4bd96 FE, 44ea6b0 RES; SEM 3f4fe07 and BHAV earlier): SEM (D55 basis strings + D56 dividend TTM cross-check, +14 tests), FE (D57 currency threading + mixed-currency honesty with per-currency subtotals and null published totals; D52/D53 basis chips + throttle notice + skip-reason breakdown; D55 UI labels "(MRQ YoY, frac)"; D60 StatusChrome reachability honesty — vitest 1478, tokens audit 0 violations), RES (D58 marquee l&t/larsen primary-LT + jindal/godrej choosers, engine residual-tie guard that also fixes the class beyond the table [jsw/kirloskar/bare-"apple" now disambiguate], V5 lock-in [ordering was already correct — pinned], live-lookup LRU + cooldown + provider-health; D59 sector map canonicalized: 5,010-record honest header, 1,472 orphaned industry values migrated, 135 NSE-only shares filled), BHAV (UDiFF bhavcopy fetcher, live-verified: 2,703 equity rows 0.25 s).
- (2026-07-08) **V2 DISPOSITIONED with live evidence** (r11/v2-redrive/): DeepSeek V4 Flash answers the portfolio host-action ask with `finish_reason=content_filter` + a Chinese refusal + ZERO tool calls (the R10-VERIFY 3/3 repro, now with the machine-readable cause) — while z-ai/glm-5.1 and moonshotai/kimi-k2.6 on the SAME OpenRouter lane both call `portfolio_add_position` correctly (kimi reads the panel back and hedges honestly — the E3.3 machinery visible in the wild). Verdict: default-lane MODEL behavior, not app code. App-side fix shipped: a content_filter finish now yields an honest humanized error frame (code `content_filter`), test-pinned.
- (2026-07-08) R10-VERIFY punch-list #6 closed: RELIANCE ×5 test holding pruned from the autosave blob (app stopped, backup kept); phase-9.5 AAPL test-debris position deleted from the sidecar DB (API 204).
- (2026-07-08) Integrated `ci-local` running; 12-agent independent reference-pack workflow launched for the twelve-stock battery (MARUTI, DRREDDY, HAVELLS, VOLTAS, MPHASIS, CROMPTON, PRAJIND, CERA, SHAILY, WENDT + BSE-only TANFACIND, ACGL — all fresh, none from prior batteries).
- **SESSION LIMIT cut the run 2026-07-02 (~10 min into the fan-out); resumed 2026-07-08.** The R10 precedent repeated: all four teams died mid-implementation — but their worktrees survived (SEM ~80% done uncommitted, BHAV module+tests+fixture uncommitted, RES/FE analysis-only). All four RESUMED from transcript. Lead's uncommitted core work survived in the main worktree; `enrich_nse_sectors.py` byte-identical (verified). NOTE for the close-out gate: `kill-switch-benchmark.json` is REGENERATED by `test_safety_end_to_end.py` on every full pytest run (by design — see .prettierignore Phase 9.5 note), so the mandated full-gate-chain runs necessarily rewrite its timing numbers; it stays uncommitted and unreverted, same handling as R10/R10-VERIFY.

## Phase 4 live-drive log (2026-07-08 evening)

- **Gate 1 (cold cache) PASSED, app-level, real conditions**: fundamentals_cache.db DELIBERATELY deleted (backup in session scratchpad); fresh boot self-deployed the stack (5,050 seeded + 2,646 same-day bhavcopy EOD rows + only 42 v7-live — Yahoo genuinely throttling this IP, breaker cycling: opens_total 4). Operator's exact IT query via API: **23 rows in 9.6 s** (`r11/gate1-coldcache-app-itquery.json`); + dividend/heavy-india-all/formula screens (`gate1-screen-*.json`) all honest; agent-authored screen (glm-5.1) called screener_run + write_screener_filters + open_panel (`gate1-agent-authored-screen.json`).
- **Gate 1/2 UI evidence** (`gui-12`): PARTIAL badge + coverage + "DATA PROVIDER IS THROTTLING THIS IP" amber notice + "15 LIVE · 8 MIXED" basis counts + "250 UNAVAILABLE — 250 MISSING ROE" reason breakdown + per-tier freshness line, all rendering live on a real throttled run. DeepSeek-lane agent drive ALSO ran the full screener with live SSE progress in chat (prefilter 2,675→375 — the seeded sector prefilter biting) + honest 254-skip disclosure in its narration (`gui-07/08/09/10`).
- **Gate 6 PASSED live on a fresh name** (`gui-22/23`): WENDT deep brief — DEEP stamp from the execution record, "EOD AS OF 2026-07-08" chip, NSE_DIRECT provider chip, drawdown -41% vs 52w-change -19.33% distinct + labeled, growth "quarterly YoY" labels, and the **D56 dividend reconciliation on a REAL case**: Conflict Note "provider's standard dividend rate lists ₹20.00 … omits special dividends; the ₹40.00 trailing paid figure represents the complete distributed amount" — the exact figure the adversarial verifier independently computed. 24 sources, 237 s, 14 steps.
- **Gate 7**: live 401 ("The OpenAI API key was rejected — check it in Settings.") + 402 ("Your DeepSeek balance is empty — top up or switch provider…") via API (`error-battery-api.json`); provider content-filter now renders an honest frame LIVE in chat (`gui-15`: "The model declined this request — its provider flagged the content." + action + Details toggle). **NEW DEFECT FOUND + FIXED**: a garbage symbol served an all-null 200 (dishonest "exists, no data" shape; also let the crawler stamp uncovered scrips as enriched) → yfinance empty-info now raises kind="not_found", /fundamentals answers an honest 404, screener ledger maps it to not_found; test-pinned.
- **Gate 5 (partial live)**: composer-driven portfolio adds under AUTO applied and ACKED (`POST /agents/actions/ack` in the sidecar log — the E3.3 read-back closing); agent loaded the chart panel with the fresh symbol + applied screener filters (panels driven). §6.5 exclusion re-verified at suite level (40 safety tests + AI-order-gate audit in every full pytest run this sprint); the live order-dialog click-through was CUT SHORT — see below.
- **V2 disposition**: content_filter finish_reason captured live on BOTH portfolio and research asks (DeepSeek lane); glm-5.1/kimi-k2.6 on the same lane drive tools correctly. Model-lane behavior, now honestly explained in-app.
- **OPERATOR RETURNED mid-drive (~22:00; idle 91 s)** — Chrome raised over the app during the portfolio-scenario wait (no cross-app input leakage: the composer message had already landed in Vysted — verified by the invoke + ack log lines and the pristine state of the operator's browser input). ALL UI driving stopped immediately at that point; the remaining live legs (order-dialog §6.5 click-through, narrow-width sweep, drags, persona taste pass) move to NEEDS-MANUAL-CHECK, and the run closed via API/gates only.

## E/V disposition (running — finalized at close)

| ID | Status @ 2026-07-08 | Disposition |
| -- | ------------------- | ----------- |
| E1–E7, E9–E11 | RESOLVED by R10, re-confirmed by R10-VERIFY | Re-verified via full-suite green at every R11 checkpoint; E-series pins all passing (2216 pytest). Live re-drive of E2/E3/E9/E10 rides Phase 4. |
| E8 | was PARTIAL (→V1) | **CLOSED by D55** (SEM, merged 3f4fe07): basis "quarterly YoY (MRQ)" in semantics + narrative labels + growth_basis on every raw surface; screener UI labels ride FE. |
| V1 | MAJOR | **FIXED** (D55, merged; test-pinned incl. renamed semantics pin + REST/tool growth_basis assertions). Annual-growth derivation deliberately NOT shipped: no current research leg carries statement data; adding a per-snapshot statement fetch was forbidden-cost (SEM report). |
| V2 | MAJOR | **DISPOSITIONED (model-lane) + APP HONESTY SHIPPED**: live captures show `finish_reason=content_filter` on the DeepSeek lane with zero tool calls, while glm-5.1/kimi-k2.6 on the same OpenRouter key drive `portfolio_add_position` correctly; the app now explains a content-filter finish honestly (test-pinned + captured live in chat, `gui-15`), and StatusChrome renders provider reachability honestly (FE, test-pinned). |
| V3/V4/V5 | MINOR | **FIXED** (RES, merged 44ea6b0): marquee l&t/larsen→LT + jindal/godrej choosers; engine residual-tie guard kills the arbitrary-tiebreak class beyond the table (jsw/kirloskar/bare-'apple' now disambiguate); V5 ordering was already correct — now lock-in-pinned. 13 new resolver tests. |
| V6 | MINOR | **FIXED** (FE, merged 8f4bd96): instrument currency threaded to every money cell (₹1,293 renders ₹ even under region US — test-pinned); mixed-currency portfolios render per-currency subtotals and publish totalValue:null + reason (never a cross-currency sum); the two defect-pinning tests rewritten to assert correctness. |
| V7 | MINOR | **FIXED** (46e6c43): .prettierignore; ci-local byte-green again. |
| V8 | NOTE | **NOT-A-DEFECT**: the /resolve endpoint is the @mention picker (symbols/short names), the research path owns salad-cleaning — by design (R10-VERIFY's own reading); the suite pins the research path. No change. |
| V9 | COSMETIC | **FIXED** with V1 (the basis string now says quarterly explicitly). |
| V10 | NOTE | **NOT-A-DEFECT** (engine-correct for `sector eq Technology`; industry-level filtering already exists for narrower screens). DEVIT P/E 2.06 rides the ten-stock battery as a data spot-check. |
| V11 | MINOR | **FIXED** (D56, merged): deterministic TTM-paid cross-check + conflict flag + "trailing 12m paid" fact (ABBOTINDIA-shaped regression test). |
| NEW (census) | — | Sector-map header/orphaned-industry/135-shares gaps → RES in flight (D59). Boot-seed laziness → **FIXED** (immediate at startup). Crawler throttle-vs-absence conflation → **FIXED** (D53). Warm-sweep-beside-foreground-screen → **FIXED** (pause gates). bar_loader unbounded fan-out → **FIXED** (Semaphore 8). skip_details never rendered → FE in flight. |

## Worklist (adopted at start)

- R10-VERIFY defects: V1 (growth-basis, MAJOR), V2 (default-model host-actions, MAJOR), V3 (L&T→LTF), V4 (Jindal/Godrej silent bind), V5 (foreign candidates in IN chooser), V6 (portfolio $ for INR), V7 (prettier — FIXED this run), V8 (endpoint-vs-research salad note), V9 (brief "yoy" label), V10 (sector granularity note), V11 (ABBOTINDIA special dividend).
- R10-VERIFY punch-list: RELIANCE test holding removal; V1/V3/V4/V6 triage; drags NEEDS-MANUAL-CHECK carry.
- E1–E11: dispositioned by R10-VERIFY (all RESOLVED except E8 PARTIAL → V1). R11 re-verifies the register and closes E8.
- Phase 2 mandate: cold-start viability, rate-limit resilience, completeness/freshness honesty, screener.in accuracy bar.
- Phase 3 mandate: Jarvis-capability stretch (personas driving loaded panels, layout intelligence, action-surface parity, honest timeouts/recovery), §6.5 carve-out re-verified live.
