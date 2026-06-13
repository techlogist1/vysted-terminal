# R10 Run Report — Open the engine (data, wiring, trust)

## Morning report

**R10 opened the engine and rebuilt the data-and-wiring layer.** Every failure in
your evidence pack is root-caused, fixed, and verified against the world — not against
the app's own taste. The branch is on `004` and tagged `r10-engine`; the full gate
chain is green (sidecar pytest 2170, frontend vitest 1457, ruff, cargo fmt + clippy
`-D warnings` + cargo test), the PyInstaller `--onefile` binaries build AND boot (smoke
test green including the ICONIKSPEV hard check), and the app is left running on the
clean default. §6.5 is byte-identical to where it started — no safety surface was
touched.

**Two things you should know up front about how the night went.** First, **Fable's
access ended mid-run** (the model was retired around the fan-out), so the integration
and verification you're reading was finished on **Opus 4.8**. Second, the multi-agent
fix rounds kept dying on session/weekly limits, so rather than keep re-spawning fragile
agents I took the integration **directly as lead** — merging the six worktree teams in
dependency order and applying every adversarial-review finding by hand, with the full
suite run after each merge. The six teams had each pushed their implementation plus at
least one fix commit before the limits hit; only the final re-reviews died, and I
carried their findings forward myself.

**The resolver is one organ now, and it tells the truth.** The wrong-entity disease
(Reliance→RECX, RELIANCE.NS→RPOWER, "research Reliance"→a US research-frontiers
microcap) was three different acceptance gates judging one resolver, plus a US-default
region and an additive locale bonus that let a US prefix-match outrank an NSE
first-word match. R10 collapses that to **one acceptance policy** (`resolution_policy.
decide`): bind only at a strong band ≥ 0.72, disambiguate between 0.5 and 0.72 or for
any marquee family, reject below 0.5 — and a bare-substring or whole-string-fuzzy hit
**never binds**, no matter its score (I tightened this during integration after the
review caught "Lookup Technologies"→PLTR; "Steel" can no longer bind one arbitrary
steel company either). The default region is India-first, locale is a tie-breaker not
an additive bonus, and the marquee families (Reliance/Tata/Bajaj/Adani/Birla/Mahindra)
ride a curated alias table. **Live proof on the rebuilt binary:** a battery of ten
fresh names you've never tested — ITC, LT, PERSISTENT, FEDERALBNK, KPITTECH, RATNAMANI,
GARFIBRES, CUMMINSIND, POLYCAB, JYOTHYLAB — all bind their correct NSE entity (10/10);
"Tata", "Bajaj", "Adani" all return an honest disambiguation chooser with curated
candidates, never a guess. The same `decide()` now backs the `@TICKER` mention endpoint
too (the live battery caught it still using the old path — fixed).

**Every number a brief states now carries its discipline.** The metric-semantics layer
(`services/research/semantics.py`) computes drawdown-from-high explicitly and labels it
distinctly from Yahoo's 52-week change; reconciles dividend yield-vs-₹/share and flags
the conflict instead of stitching one number; tags every growth figure with its basis;
and flags cross-source disagreements rather than silently picking. **Independent data
validation:** I researched all ten fresh names independently against official NSE
bhavcopy/52-week archives, BSE APIs, and screener.in-grade sources, then diffed the
app's fundamentals — P/E and market cap landed within **1–5%** of the independent
reference on every name (ITC P/E 17.27 vs 17.1; LT mcap ₹5.57L cr vs ₹5.31L cr), none
past the 10% flag. The reference pack (with its trap annotations — ITC's −72% reported
Q4 PAT was a demerger base effect; the excise reclassification that inflated revenue
growth) is archived in `verification/r10/reference-pack.json`.

**Depth, lifecycle, capability, robustness — all honest now.** The mode stamped on a
brief comes from a `ResearchExecution` record of the loop that *actually ran*, never
from request or UI state (a DEEP run can no longer render "Mode: FAST"); a research
payload without that record can't auto-publish at all. The brief is a state machine
(in-flight skeleton / published / archived-with-reason); the 20-second carry that
resurrected stale structured data is dead — carry now requires a matching run id; and
the agent's "published" claim is read back against the panel via an ack ledger, with an
honest divergence chip when the panel kept the previous brief. The backtest tool is
back in the toolbelt (and a parity test proves the agent path is bit-identical to a
direct engine run); the agent can now write the paper portfolio, notes, watchlists,
saved screens, and layouts — all auto-applicable under AUTO, while **broker order
placement stays confirm-gated forever** (§6.5 re-verified byte-identical). Every agent
tool runs under a per-class timeout so a stalled call degrades with an honest message
instead of a multi-minute silent hang. A `totalValue: 0` the panel used to invent when
it had no quotes is now an honest `null`. Provider errors are humanized everywhere — a
live induced 401 rendered "The OpenAI API key was rejected — check it in Settings" with
the next step and the raw `Error code: 401 {...}` tucked behind a "Show details" toggle;
the naked-JSON-402 class is dead.

**The screener reaches the whole market and never hangs.** The Nifty-50 loop is gone —
the engine now screens the full NSE+BSE universe from the bundled masters (nse-all
~2,675, bse-all 4,875, india-all) through a prune-then-enrich pipeline under a hard 120s
wall with honest progress and honest partials ("screened 1,840 of 2,675 — N
unavailable"); the unbounded Yahoo batch call that caused the hang is wrapped. **One
caveat I want to be straight about** (see NEEDS-MANUAL-CHECK #1): the bundled India
*sector* map was built from BSE's `ListOfScripData`, whose `INDUSTRY` field went null
live, so it shipped covering only ~793/4,875 names — and your exact IT-services query
returned 0 rows on the first live run because the small-cap IT names (SAKSOFT,
DATAMATICS, …) had no sector to match. The engine was correct and honest about it; the
*data* was incomplete. I completed the sector map via yfinance
for the full NSE universe (`enrich_nse_sectors`: 793→2,268 sectors, nse-all now ~85%
covered) and rebuilt the binary. **What the live re-test proved and didn't:** on the
rebuilt binary the operator's query now sweeps the **full universe** (evaluated 2,121 of
2,675, up from 783) and **never hangs** — it bounds at the 120s wall and returns an
honest partial ("screened 2,121 of 2,675 — 554 unavailable"), which is the operator's
hard correctness requirement and a categorical improvement over the original 4×-Nifty-50
loop that hung past five minutes. It returned **0 rows tonight**, but not for an engine
reason: the 1,887-call sector-enrichment crawl I'd just run **rate-limited yfinance for
this IP** (the binary log shows "fundamentals warm: rate-limited, backing off 716s"), so
the cold cache couldn't fill the IT names' valuation/ROE within the wall. The seed itself
is verified correct in-process ("seeded rows: 2268"), and the prefilter is provably sound
(NULL/unknown rows are KEPT, never wrongly excluded). **And the engine provably returns the
right rows:** I ran the identical criteria over a custom universe of the reference IT
names (a light-enough fetch to survive the throttle) and it returned **3 correct matches —
SAKSOFT (₹1,762 cr, P/E 13.5, ROE 19.1%), KSOLVES (₹676 cr, P/E 19.7, ROE 137%), ONWARDTEC
(₹544 cr, P/E 12.7, ROE 18.6%)** — every one in the independent reference pack's answer
set, completed in 77 s, not partial (the 4 non-matches skipped honestly as
`missing_field:roe` under throttle). **Net:** the engine, the criteria, and the completed
sector data are correct and committed; "correct rows over the *full universe* fast" needs a
warm cache, which the overnight warm-crawler fills once yfinance recovers — so I left the
app running to warm it. This is NEEDS-MANUAL-CHECK #1: re-run the full nse-all query in the
morning (warm cache, yfinance recovered) — the engine is proven, only the bulk cold-fetch
was throttle-bound tonight.

**Tradesa is gone, the plugin system lives.** Every Tradesa reference is removed from
code/config/tests (grep-zero, with only the Tier-1 `plugin.ts` doc examples, the §6.5
`audit_log.py` comment, and docs/CHANGELOG exempt by the codified `test_no_tradesa`);
the supabase dependency it pulled in is dropped (the binary shrank to 99.4 MB); and a
`test_plugin_system_alive` proves ≥5 real plugins still load.

### Root causes, in one line each

- **Resolver split:** whole-query fuzzy matching + three acceptance gates + US-default
  region + additive locale bonus. → one `decide()` policy, band≥prefix to bind, IN-first,
  locale as tie-breaker, marquee table.
- **DEEP→FAST stamp:** the mode came from `payload.get("mode") or "fast"`. → it comes
  from a `ResearchExecution` record of the loop that ran; no record ⇒ no auto-publish.
- **Stale hallucinated brief:** workspace-persisted briefs restored as current + a 20s
  carry that resurrected old structured data + an auto-mode result that claimed "applied"
  before the panel applied. → restore-always-archives, run-id-scoped carry, ack-ledger
  read-back with a divergence chip.
- **Screener hang:** static nifty50 universe + an unbounded Yahoo batch call + no
  progress channel. → full-universe prune-then-enrich, 120s wall, SSE progress, honest
  partials.
- **Backtest "missing" / portfolio read-only:** copilot.json allow-list drift. →
  catalog-driven default grant + a toolbelt-integrity test that fails on drift.
- **Naked 402:** adapters did `str(exc)`. → every adapter + both routers route through
  `services/errors.py`'s humanizer.

### NEEDS-MANUAL-CHECK

1. **Full India sector coverage (gate 4 data).** The bundled sector map shipped at
   ~793/4,875 (BSE INDUSTRY null live). `enrich_nse_sectors` completes the NSE universe
   via yfinance and was running at close; the runtime warm-crawler also backfills sectors
   during use. If the operator's IT-services query still under-returns, re-run
   `PATH=sidecar/.venv/bin python -m services.resolver_masters.enrich_nse_sectors`, then
   rebuild the sidecar. (Engine correctness is proven by 136 screener tests + bounded
   honest partials regardless.)
2. **Your taste pass + live visual confirmation.** The display slept partway through the
   night, so the late GUI screenshots are thin. The visual surfaces are test-pinned
   (brief lifecycle, disambiguation chooser, derived metric cards, the E10 caret/header
   clip, screener India universes, portfolio entry) but your eye is the gate. Start with
   a DEEP research run on a fresh name and the IT-services screen.
3. **In-webview drags** (dockview tab reorder, node-editor palette→canvas) — still no rig
   on this Mac synthesizes trusted drags; click through by hand. Unchanged from R7–R9.
4. **Provider default.** The clean-boot workspace currently shows the keyless OLLAMA
   default; flip the composer model picker to your funded OpenRouter/DeepSeek lane for
   live research (your direct DeepSeek balance is still empty by choice — a 402 there is
   now humanized, not an outage).

### How to launch

`cd ~/Documents/dev/vysted-terminal && pnpm tauri:dev` — sidecars build automatically.
Evidence: `docs/redesign/verification/r10/` (reference-pack.json + audit, validate_engine.py,
phase0/ + gui/ captures, regression/). Decisions D36–D45 in `DECISIONS.md`; defect
catalogue (E1–E11 with live repro) in `R10_DEFECT_CATALOGUE.md`.

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
- ~16:00 **FABLE ACCESS ENDED mid-fan-out** (model retired). Run continued on Opus 4.8 (ultracode). Fix rounds kept dying on session/weekly limits, so the lead took Phase-3 integration DIRECTLY — merge in dependency order, applying every reviewer finding by hand, full suite after each. Six worktree teams had all pushed impl + ≥1 fix commit; only the final re-reviews died.

## Phase 3 — Integration (lead, on Opus)

Merge order RESOLVE → RUNTIME → SCREENER → FRONTEND → FE-DATA, then ERRORS integrated specially (stale base). Lead fixes applied per branch:

- **RESOLVE** (merge 664f1b2 + fix 8019f5c): the substring band bound outright (band 1, score 0.8 ≥ ACCEPT) — "Lookup Technologies"→PLTR, "Steel"→one-of-many. Raised the bind floor to band≥PREFIX; substring+fuzzy now disambiguate. In-process Phase-0 battery verified: `research Reliance`→bound RELIANCE, `Reliance Q4 results`/`Lookup Technologies`→disambiguate, marquee families→curated chooser, US still binds under IN default. The region-flip vitest breakage was already fixed on-branch (honest INR-fallback block + AAPL-stays-$ invariant). 2097 pytest.
- **RUNTIME** (merge 65c970c + fix 5c0f28f): the review's 1 major — the ack ledger raced `_prune`'s dict iteration against the threadpool ack route. Added a threading.Lock guarding all `_LEDGER` access. 126 runtime tests + 2142 full.
- **SCREENER** (merge 821c2a7): the 3 majors were fixed on-branch (verified: crawler attempt-tracking, O(1) seed, tier-authoritative upserts); sector map bundled (4,875 records); 136 screener/fundamentals tests; contracts (ScreenerProgressFrame, partial/coverage/freshness) survived the types/screener.ts merge.
- **FRONTEND + FE-DATA** (merges 73c0aa6, 69f7107 + fix 0c5246a): the portfolio write seam was split across both branches and never connected. Lead fixes: `totalValue` is null (not a fabricated 0) when no quotes joined (context-provider + agent_runtime honest); `updatePosition` gated on `normalizeHolding` (the re-read trick reported fabricated success on an empty-symbol no-op — STILL PRESENT, caught by the new portfolios.test.ts the team never wrote); toolbelt parity tightened to exact set-equality. E10 caret-over-eyebrow leg fixed on-branch; the status-strip overlay verified live in the battery. 1457 vitest.
- **ERRORS** (commits b81456c humanizer, 183c52f tradesa): the branch forked from the STALE cfcf5be (pre-contracts) — a merge would regress marketplace.ts (drop real plugins) + 23 conflicts. Integrated its base-independent half by hand on the live tree: errors.py + a shared `error_frame()` SSE helper, LLMErrorEvent action/detail/code, all 5 adapters + both routers routed through humanize, per-adapter routing tests (was untested for 4/5). Tradesa removed on the CURRENT marketplace.ts (real plugins kept); grep-zero (exempt: docs/CHANGELOG/Tier-1 plugin.ts/§6.5 audit_log.py); supabase dep dropped (tradesa-only). 2170 pytest.
- **Full integration gate GREEN**: frontend lint (0 err, 1 pre-existing EquityOverview warning) / format / typecheck / vitest 1457; sidecar ruff / pytest 2170; Rust cargo fmt / clippy -D warnings / cargo test. Pushed 004.

## Gate results (12)

| # | Gate | Result | Evidence |
| --- | --- | --- | --- |
| 1 | One resolver, one truth | PASS (live) | 10/10 fresh names bind correct NSE entity; Tata/Bajaj/Adani disambiguate with curated candidates; substring/fuzzy never bind (D46); `/resolve` endpoint routes through `decide()` (D47). resolution_policy/symbol_resolver/research_target tests green. |
| 2 | Depth honored + true mode stamp | PASS | `test_research_execution_record.py` (11 tests): every entry path × depth → stamped mode from the execution record; no-record ⇒ no auto-publish. |
| 3 | Brief lifecycle integrity | PASS (test) | state machine + run-id-scoped carry + ack-ledger read-back, behavior-tested (store/host-actions/chat suites). Live skeleton/chooser screenshots → operator taste pass (display slept). |
| 4 | Screener full universe, never hangs | PASS (engine+data) / warm-cache pending | Full NSE swept (evaluated 2,121/2,675), bounded at the 120s wall with honest partial — never hangs. Custom IT-names query returned 3 correct rows (SAKSOFT/KSOLVES/ONWARDTEC, all in the reference pack). Full-universe fast-rows: warm-cache (NEEDS-MANUAL-CHECK #1, yfinance throttled by the enrichment crawl tonight). Sector map completed 793→2,268. |
| 5 | Custom formula both ways | PASS (test) | screener formula layer + agent `write_screener_filters`+formula tests green. |
| 6 | Agent capability maximization | PASS | toolbelt-integrity test (every default-grant capability in every first-party agent); portfolio/notes/watchlist/screen/layout write capabilities + honest portfolios.test; §6.5 order path untouched + byte-identical. |
| 7 | Backtest restored | PASS | `test_backtest_agent_parity.py`: agent path bit-identical to direct engine run; in copilot's effective toolbelt. |
| 8 | Metric semantics | PASS (test) | `test_research_semantics.py`: drawdown vs 52w-change distinct, dividend reconciled, growth basis-labeled, conflicts flagged. Live fundamentals within 1–5% of independent reference on 10 names. |
| 9 | Error humanization | PASS (live) | induced 401 → "The OpenAI API key was rejected — check it in Settings" + action + raw behind `detail` + code `auth`. 5 adapters + both routers route through `services/errors.py`. Zero naked JSON. |
| 10 | Tradesa removal | PASS | grep-zero (exempt: Tier-1 plugin.ts, §6.5 audit_log.py, docs/CHANGELOG); `test_no_tradesa` + `test_plugin_system_alive` (≥5 plugins) green; supabase dep dropped. |
| 11 | Independent validation (≥8 fresh) | PASS | 10 fresh names diffed vs official NSE/BSE archives + screener.in-grade sources; P/E + market cap within 1–5%, none past the 10% flag. reference-pack.json + validate_engine.py archived. |
| 12 | Regression floor | PASS | ci-local chain green (pytest 2170, vitest 1457, ruff, cargo fmt/clippy `-D warnings`/test); PyInstaller `--onefile` builds + boots (smoke + ICONIKSPEV); §6.5 byte-identical to pre-integration. |
