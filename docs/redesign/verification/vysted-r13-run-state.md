# R13 DATA BEDROCK — run state

Single source of truth for the R13 autonomous run. Updated at every loop boundary. Any fresh context resumes from here.

## Mission (compressed)
Any NSE+BSE symbol → complete screener.in-grade profile + real research at every depth, or an honest per-field account. Six fronts: (1) profile contract w/ provenance+staleness, (2) foreign witness (independent second primary source for small-cap fundamentals; fix + pin 509470 institutions, promoter drift, declared-vs-TTM dividends), (3) entity-anchored retrieval (kill KSE/Karachi collision class by construction), (4) filings floor (exchange filings as guaranteed research floor), (5) cross-source numeric sanity (junk-aggregator rejection; refine bank Conflict Note presentation), (6) depth integrity on long tail. Phase C: Jarvis verification reflex (read-back before claim, input skepticism, cross-turn self-consistency) + sustained owner-drive. 8 acceptance gates, ≥12-name hostile battery (fresh names only), tag r13-bedrock at close.

## Hard rules in force
- Version 0.8.0, branch 004, no merge to main, push at green checkpoints, tag r13-bedrock at end.
- Sacred: `sidecar/services/resolver_masters/enrich_nse_sectors.py` byte-identical sha256 `5cb28e0d89f98a30abceba8d91494f4002646503a4d51f798f63980b286abdbe` (VERIFIED at run start, matches R11_RUN_REPORT record). Never commit/revert/format/touch. Stage explicit paths, never `git add -A` over sidecar/services.
- `docs/screenshots/v0.5.0/safety-audit/kill-switch-benchmark.json`: uncommitted, unreverted; working bytes change on every full pytest by design — NOT a finding.
- Keychain chapter closed (dev keystore). §6.5 order boundary: paper-portfolio writes agent-completable; broker ORDER placement never — re-verify live before close (surface byte-identical, audit_orders zero rows).
- Lead = Fable 5 orchestrator only; never spawn Fable teammate. Lead-death: commit at nearest green checkpoint, write state here, END.
- No-progress rule: same failure signature twice ⇒ strategy change. KSE is repro + closing regression check, never a primary gate. Battery excludes ALL prior battery names + ROUTE, SAKSOFT, ICONIKSPEV, 509470.
- Small known items to decide (silence is failure): MCP cold-bind ~34s (--onedir real fix vs affirm workaround), EquityOverview eslint warning kill, run smoke-test-sidecars.mjs end-to-end once (fix kill-all pre-flight if unsafe), date-stamp battery reference packs.

## Phase status
- [x] Caffeinate armed (PID 3695, -dims, run-scoped)
- [x] Tree adjudicated CLEAN: HEAD 7a7f7fd = origin/004; tag r12-finisher @ 14d05b6 + 2 docs-only commits after (247d35b, 7a7f7fd) = expected pattern. Two sacred files M-uncommitted as expected.
- [x] Sacred file hash verified byte-identical.
- [x] Vitest baseline: 1481 passed / 134 files, 0 skips (matches R12 close).
- [x] Pytest baseline: 2311 passed / 1 skipped (live-key conditional) in 172s — matches R12 close exactly.
- [x] Sidecar rebuild x3: all three built + dev-signed (`ensure-all-sidecars --force` clean).
- [x] App booted on fresh binaries (sidecar 63294, openbb 63295, sec-edgar 63296); composer on funded lane (OPENROUTER · Kimi K2.6, CONNECTED).
- [x] Phase A doc reads complete (2 workflow schema-failures + 2 placeholder-junk "test" returns re-run as plain agents — all 8 landed).
- [x] KSE repro NORMAL + DEEP done by lead's own hands (r13/kse-repro/01-10.png); ULTRA in flight. Root causes → D72 (triad). Subtle-wrong triad → D73, evidence r13/subtle-wrong/repro-evidence.json.
- [x] Phase C baseline evidence live: agent narrated broken lane as world-absence (10-deep-followup.png); kept-previous-brief note contradicting panel (05/06-*.png).
- NOTE: KIRIINDUS, TIRUMALCHM, ORIENTBELL, GOKEX, IOC, PFC consumed as probe names — add to battery exclusions.
- [ ] Phase B fronts 1–6
- [ ] Phase C Jarvis reflex + owner-drive
- [ ] Battery ≥12 hostile fresh names
- [ ] Gates 1–8 with evidence; tag r13-bedrock

## Loop log
- L0 (run start): truth pass. Nothing unexpected in tree. Baselines green (pytest 2311/1, vitest 1481/134). Sidecars rebuilt x3. R12's left-running app stack found on port 5173 (expected per R12 close-out) — killed Vysted-only PIDs, relaunching on fresh binaries.
- L0b: Phase A reads complete except retrieval scout (re-running; first workflow had 2 schema failures + 2 placeholder-junk returns — re-ran as plain-text agents).
- L6 (~17:15) OPERATOR PRESENT (D75): private-session capture caught + deleted immediately; GUI SUSPENDED; idle monitor armed (bg loop, relaunch on its 10-min timeout notifications until ≥1500s idle fires); LESSONS updated (presence check per-GUI-leg). API-only continues: searxfloor + panel MERGED (e8ea28f, 9e5744e); Jarvis landed (3 commits, 2422/1 + 1492/135) — verifier running; headless battery collector dispatched (12 primary names, REST+gather_fast, polite). QUEUED for operator-away ≥25min: KSE in-app 3-depth UI drive + screenshots, Phase C induction drives (publish read-back, seeded scalar, cross-turn contradiction), owner multi-step drive, §6.5 re-verify click-through, smoke-test-sidecars.mjs canonical run (kills processes — also needs away), narrow-width sweep item.
- L5 (~17:10): KSE RESURRECTION half-proven live: profile front COMPLETE in-app (dense metric grid, honest structured-only banner, D56 dividend conflict note rendering live). Research front exposed D74: up-but-empty SearXNG (vysted-searxng container, dead upstreams, HTTP 200 empties) resolved as t2 and starved ALL retrieval — the operator's actual mechanism. Fix dispatched (worktree-agent-searxfloor: ok-empty t2 cross-checks keyless floor); broken container deliberately left running as the live testbed. PANEL landed (worktree-agent-panel: honest coverage UI, eslint kill, conflict tiers, generic derived rendering; vitest 1493, lint 0 warnings) — verifier dispatched. Jarvis still implementing. NOTE for Jarvis/types: BriefDerivedMetrics TS interface doesn't name ownership/dividend fact fields (generic loop handles wire; cosmetic gap).
- L4 (~16:55): RETRIEVAL verifier MERGE (all 6 claims confirmed; all 4 rewritten regression tests intent-preserved; round-1 generic-dims tradeoff accepted as deliberate; iter.py:433 comment nit). Merged retrieval a969d3e. B1 COMPLETE on 004: spine 9a3616e + witness 45b43be + retrieval a969d3e. Full chain running on merged tree. WIREUP teammate dispatched (worktree-agent-wireup: fast.py ownership_exchange+dividend_declared attach + iter.py comment fix + integration tests).
- L3 (~16:40): WITNESS verifier MERGE-WITH-FIXES (BSE lane live-confirmed + generalizes to GEE; ownership + declared-dividend legs correct-but-INERT pending fast.py wire — the cross-partition item witness itself flagged). Merged witness 45b43be (types/data.ts auto-merged). RETRIEVAL landed (6 commits, suite 2339/1) — verifier running, priority hunt = the 4 rewritten regression tests. PLAN: after retrieval merges → dedicated small wire-up task (fast.py attach ownership_exchange + dividend_declared, exact patch in witness+verifier reports) BEFORE Jarvis; then full chain + sidecar rebuild + KSE resurrection drive; then Jarvis (Opus) + Panel (Sonnet) on merged base.
- L2 (~15:55): SPINE verified by fresh-context Opus adversarial verifier — MERGE verdict, all 5 claims confirmed, zero regressions (caller sweep neutral-or-better; flake confirmed pre-existing at base; quote path tolerant via suffix-strip symbols_match). Phase A docs committed 8437737; spine merged --no-ff 9a3616e. Sacred files still M-uncommitted. Targeted integration pytest running. Awaiting witness + retrieval.
- L1 (Phase A close / Phase B dispatch, ~15:20): D71–D73 logged. KSE repro complete at NORMAL (33s, on-entity Moneycontrol/ET sources, empty panel body) + DEEP (60s planning round overran 90s slice → "No findings"; recovery pass pulled BSE filings honestly) + ULTRA-forced in flight. Dispatched 3 Opus worktree implementers in parallel: SPINE (worktree-agent-spine: _yahoo_symbol BSE fix, husk honesty, registry null-shell, correctness bounds, field_meta contract), WITNESS (worktree-agent-witness: BSE shareholding lane, ownership_check.py, D56 direction+declared upgrade, conflict kinds), RETRIEVAL (worktree-agent-retrieval: identity enrichment ISIN/industry/bse_code, entity-anchored queries, collision-proof relevance, filings floor, depth tuning). Disjoint file partitions briefed explicitly; each pushes its own branch.
- Pending after B1 merges: SONNET panel work (EquityOverview per-field coverage UI + eslint warning + conflict presentation tiers), Jarvis runtime (Phase C), battery, small items (--onedir decision, smoke-test canonical run, date-stamped reference packs).

## Jarvis (Phase C) design — decided from runtime scout, brief-ready
Runtime facts (scout, file:line in agent's report): invoke loop streams narration live per round; host-action tool results are LOCALLY SYNTHESIZED optimistic ("status: dispatched") before the frontend even receives the event; ack plumbing exists ONLY for publish_brief (host-actions.ts:1419, proposed-changes.ts:143 → action_ledger); divergence notice _publish_divergence_notices (agent_runtime.py:884-928) is end-of-stream bolt-on with HARDCODED text "The panel kept the previous, richer brief." (910-912) — tonight's contradiction mechanism: per-call notices fire even for calls superseded by a later successful publish in the same turn; kept_previous also fires from the 0-sources shrink-guard branch (host-actions.ts:1092-1117) and stale_run (brief.ts:198-211).
1. READ-BACK BEFORE CLAIM: extend acks to every HOST_ACTION_TOOLS id (frontend accept() acks per action; sidecar action_ledger is generic already); runtime hook at agent_runtime.py:1351-1363 (after tool-result append, before next stream_chat): poll ledger within grace window, inject REAL outcome into the tool-result so the NEXT narration is grounded; rebuild divergence detail from actual ack payload (run_id/symbol/source_count/created_at — name what's on screen); suppress/supersede notices for intra-turn superseded publishes. Keep the shrink-guard; fix its notice text.
2. INPUT SKEPTICISM: per-field reasons, 3 layers — fundamentals fetch classifies error vocab (provider_error/not_published/rate_limited), snapshot_structured leg wrapper carries it, semantics._value + BriefDerivedValue gains optional `reason` (+types/brief.ts mirror) + prompt_block renders it; copilot.json instruction: never claim world-absence unless reason=not_published. Consumes SPINE's field_meta. Seeded-absurd-scalar flagging rides SPINE's correctness bounds → "withheld" reasons reach narration.
3. SELF-CONSISTENCY: client-side claims ledger (option a — consistent with researchSpaces convention, no request-contract change): workspace researchSpaces gain claims[] {symbol, metric, value, statedAt} recorded deterministically from published brief metrics/quote cards; threaded via context_snapshot; _render_terminal_preamble renders "Prior stated values this session"; system-prompt instruction to reconcile contradictions openly. No LLM parsing.
Sequencing: Phase C toucher waits for B1 merge (fast.py=RETRIEVAL, semantics.py=WITNESS ownership until then). types/brief.ts triple-touch (WITNESS kind, JARVIS reason, PANEL consumption) — lead merges in that order.

## Phase A findings (adjudicated)
- The three subtle-wrong cases (509470 institutions 8.455% vs ~0.06%; promoter ~2.5pp drift; declared-vs-TTM dividends) and the "bank Conflict Note noise" are NOT recorded in R12 docs — they are R12-lead judgment carried via the R13 prompt. Must REPRODUCE live in Phase A, not cite records.
- Bank-revenue conflict-note literal text: sidecar/services/research/semantics.py:237 (_growth_leg) — D66 fires on banks BY DESIGN (revenue-line definitional). Noise fix = presentation tier (definitional-expected vs genuine), keep the check.
- R12 doc discrepancy (adjudicated, no action): run-report says "clean default relaunched", run-state says "left on operator's live session" — run-state is later + specific; the leftover stack I found matches it.
- smoke-test-sidecars.mjs canonical run: CONFIRMED never executed (R12 did surgical equivalent). R13 must run it (kill-all pre-flight is fine — no operator session tonight; still check HIDIdleTime first).
- MCP cold-bind ~34s / MCP_PORT_WAIT_SECS=45 / --onedir: repo-level deferred item in CLAUDE.md + BLOCKERS.md, untouched by R12.

## Architecture map (from scouts — key hooks for Phase B)
- Resolver: sidecar/services/symbol_resolver.py resolve() → Instrument{symbol,name,exchange,region,asset_class,yahoo_symbol,score,band,rename} — NO ISIN (BSE master has it, drops at load), no legal-name/industry/description. Rename lane nse_symbol_change.py carries old→new (former names, NSE only). resolution_policy: bind≥0.72, disamb 0.5–0.72.
- yfinance single mapping point: services/yfinance_provider.py get_fundamentals() :229-320; heldPercentInstitutions/Insiders raw at :317-318; dividend_yield [0,2] clamp :262-270; junk-name guard :127-147.
- PROMOTER data: exchange-direct lane ALREADY EXISTS — services/nse_provider.py:605 get_shareholding_master() + services/corporate_disclosures.py:354-384 get_shareholding() → ShareholdingPattern(promoter_percent from pr_and_prgrp; FII/DII only from XBRL) — disclosures/agent-tool surface only, NOT wired to EquityOverview or cross-checks. THE FOREIGN WITNESS SEED.
- Bhavcopy lane: nse_bhavcopy.py → fundamentals_warm.bhavcopy_refresh_once → fundamentals_store.upsert_eod_batch(provider='nse-bhavcopy') — feeds SCREENER tiering only, not EquityOverview.
- Conflict machinery (semantics.py derive_semantics: D56 dividend, D66 growth, mcap 5%, D67 identity) runs ONLY on research/brief path — never the /fundamentals/{symbol} endpoint the panel calls.
- correctness_gate.validate_fundamentals = symbol-identity only, ZERO numeric plausibility bounds.
- EquityOverview: 6-call Promise.allSettled (api.ts:79-102), panel-level ProvenanceBadge only (not per-field), FIELD_GROUPS hidden-if-all-null (silent blanks risk).
- Depth driving: UI radios shift with model name (re-measure); non-GUI path = tool-arg "use your research tool at ultra depth" + sidecar FastAPI. Deep-research backend via config ContextVar, separate from depth.

## Worklist (from Phase A reads; grows)
1. KSE repro + root cause (needs app up + retrieval scout map).
2. Front 2 foreign witness: wire shareholding exchange-direct lane into fundamentals cross-checks; reproduce 3 subtle-wrong cases live first.
3. Front 1 profile contract: Instrument+ISIN/industry/description; per-field provenance+staleness; panel honesty (no silent blanks).
4. Front 3 entity-anchored retrieval: query construction from full identity (needs scout map).
5. Front 4 filings floor: exchange-filings retrieval lane as research floor.
6. Front 5 numeric sanity: bounds in correctness_gate + cross-source reconciliation + bank-note presentation tier (semantics.py:237).
7. Front 6 depth integrity long-tail.
8. Small items: --onedir decision, EquityOverview eslint warning, canonical smoke-test run, date-stamped reference packs.
9. Rig: WKWebView cache clear after frontend edits; explicit-path staging only; worktree-agent-* branches for writers.

## Battery SELECTED (r13/battery/BATTERY_MANIFEST.md + 17 reference packs, collected 2026-07-10)
P1-P12: BMW, BABA, META, NHL, GEE, CDG(→Jujhar Logistics, renamed 2026-07-02!), BI, SIL, UFO, PML, TI, RBA. Spares S1-S5: TCI, ADOR, PVP, APEX(declared-vs-paid probe), DEN(zero-dividend honesty probe). 6 BSE-only, 13/17 sub-₹2,000cr, collision class rampant (BMW/BABA/META/NHL/TI/RBA/TCI/SIL/BI/CDG), masters-verified, exclusions attested. Packs are date-stamped with as-of on every value + world_gaps for genuine absences (satisfies the date-stamp small-item).

## Battery exclusion list (complete, from sweep)
ROUTE, SAKSOFT, ICONIKSPEV, 509470, KSE(repro-only) + RELIANCE, TATASTEEL, CMTL, INFY, AAPL, MSFT, NVDA, SPY, QQQ, BTC/ETH-USDT, TCS, HDFCBANK, HINDUNILVR, M&M, RPOWER, RUBYMILLS, SRF, COFORGE, ASIANPAINT, ABBOTINDIA, ASTRAL, CARTRADE, FINEORG, HOMEFIRST, KSCL, NESTLEIND, SUNPHARMA, SUPREMEIND, TITAN, KSOLVES, ONWARDTEC, CUMMINSIND, GARFIBRES, ITC, JYOTHYLAB, POLYCAB, FRLCY, ACGL, CERA, CROMPTON, DRREDDY, HAVELLS, MARUTI, MPHASIS, PRAJIND, SHAILY, TANFACIND, VOLTAS, WENDT, 503229, BHARTIARTL, DEEPAKNTR, GUJGASLTD/GUJENERGY, ICICIBANK, MOL, RADICO, SBIN, AARTIIND, ROSSTECH, SIMPLXREA, CIPLA, RECX, DEVIT, LTIM, LTTS, PLTR, REFR, TCS + lower-confidence r8/r9 brief names (AERPACE, BELRISE, BSOFT, CEENIK, CLF, ELANGO, EXIDEIND, JG, PARLEIND, PRIMIND, RAIN, RAMCOIND, REFEX, REGIS, RELCHEMQ, ROIUF, SANSTAR, ASAN, ASIAN, ASIAPAK, BANSTEA, CORONA, INTENTECH, KSB, LNKS, MARSONS, PROTEAN, RANASUG, SAIA, SAKHTISUG, SIS, TAKE, TARSONS, TMCV) + KSOLVES/ONWARDTEC. Battery names must clear this list.
