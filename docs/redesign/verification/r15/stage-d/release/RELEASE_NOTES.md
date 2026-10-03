# Vysted Terminal 0.9.0 - release notes

Release candidate head and launch tag head are the same commit: `1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056` (tags `r15-rc2` and `r15-launch`). Facts below are current at that commit and at the register as committed at `4b460027` (docs-only commits on top of the launch tag; this is where R15-LEAD-143 and R15-LEAD-144 were filed).

## What this release is

Vysted Terminal is a source-available, AI-native finance desktop terminal: a Tauri desktop app (Rust core, Vite + React interface) with a bundled Python data engine, your own API keys, and a plugin architecture. 0.9.0 is the first release after a full end-to-end audit and fix programme (R15 "LAUNCH") that catalogued every promised or discovered defect, fixed 629 of them, and gated the result with a regression check and a final adversarial pass. Final adversarial pass summary: a fresh-context Opus 5.5 pass (battery/drive lanes plus a cross-adversarial keyless + real-user round) admitted 58 new register entries (`R15-FINAL-001..038`, `R15-LEAD-125..144`) after rc1. Every admitted critical and high was fixed and certified by a fresh verifier before this tag: `R15-LEAD-127` (certified, `stage-c/lead127/VERIFY.md`); `R15-FINAL-001..008` plus the rest of the first batch certified at `fix-r1` (26 certified, 2 not certified on the first pass — `R15-FINAL-005` and `R15-FINAL-006`); FINAL-005 and FINAL-006 then certified at `rc2-round2`; `R15-LEAD-136` (not certified at rc2-round2) certified at `rc2-round3`; `R15-LEAD-137` (not certified at rc2-round3) certified together with `R15-LEAD-141` at the rc2 fail-safe round. New mediums and lows are filed for 0.9.1. A carry-forward judge then checked every passing final-pass observation against the rc2 -> launch code diff (`final-pass/CARRY_FORWARD_launch.md`): 26 observation groups carried unchanged, 30 were already re-proved by a later gate, and 4 owed a fresh re-run (a malformed-symbol/census route replay, the portfolio-crypto batch path, and one LLM spot-check); all 4 held when rerun at the launch head (`final-pass/rerun-launch/RERUN.md`). The pass's GUI half (a packaged-app click-through) was **not tested** at the launch head (`DECISIONS_FOR_OPERATOR.md` 5.15); `R15-LEAD-143` and `R15-LEAD-144` (both low) were filed afterward during the release-bundle rehearsal, not by the adversarial pass itself.

## What changed since 0.8.0

- **Trading is removed permanently (decision D81).** Broker connectivity, orders and simulated accounts are gone from the product and will not return. The terminal is a research, data and agent tool; the agent can read data and propose changes to your own hand-kept portfolio, and every data write waits for your review.
- **New licence.** The core is now under PolyForm Strict 1.0.0 plus a commercial licence (see `LICENSING.md`). The plugin contract (`types/plugin.ts`) and the example plugin are Apache-2.0, so plugin authors are never bound by the core licence. Every commit made before the relicensing commit stays available under AGPL-3.0.
- **A long audit-and-fix pass, plus a final adversarial pass.** 629 register entries are fixed, including 17 of the 18 criticals; the remaining critical, R15-DATA-002 (a bare ticker present in both the US and Indian masters binds to the session region; the user-pick fix is merged, the agent-add leg is not), waits on an operator decision (DECISIONS 4.15). A distinct sibling defect on the research and copilot data-fetch path, R15-LEAD-127 (a bare collision ticker served the session region's company in a research brief or MCP tool result, not the DATA-002 surfaces), was found by the final pass and fixed and certified before this tag.
- **First-boot reliability (R15-LEAD-123, R15-LIFECYCLE-001).** The core now waits up to 270 s (45 s x 6) for the bundled data engine to bind and the interface waits up to 300 s, so a cold first launch or a busy machine no longer leaves the session stuck in a failed state. The main event loop no longer freezes for the MCP bind window; confirmed headlessly and on a macOS packaged build, with the Windows packaged check still open (see "Open items" below).
- **Diagnostics.** The app keeps a rotating log under its data directory (`logs/vysted.log`) and Settings offers "Copy diagnostics". The macOS packaged click-through for this is still awaiting manual check (R15-LIFECYCLE-008).
- **Origin protection (R15-CODE-AGENT-001).** The sidecar, including its MCP surface, now rejects a browser request whose `Origin` is not on an allow-list (the app's own origins and the dev server). This is verified live and on the macOS packaged app and `pnpm tauri:dev`; the Windows packaged click-through is the one piece still awaiting manual check (`WINDOWS_MANUAL_CHECK.md` section 1).
- R15-LEAD-116 (high): an explicit BSE pin on a same-ticker, different-company name (for example `FOCUS.BO`, also KALYANI, RAJPUTANA, MAL, SEL, ZEAL) used to serve the NSE company's feed in all five disclosure lanes. Register status: **fixed**. Closure evidence: fixed by 3acd24dc + 3af0502c (fix round A), certified at d3509715 by r15/stage-c/lows/int-9368c62/VERIFY.md (31/34 row checks byte-equal; the 3 shareholding cells differ by pre-existing per-spelling lane non-determinism, filed separately). It is therefore **fixed in 0.9.0** and is not an open item.

## Install notes

- **This build is unsigned.** It carries no Apple Developer ID signature and is not notarized (R15-RELEASE-001). On the Mac that built it, it runs; on any other Mac, Gatekeeper refuses it unless you right-click the app, choose Open, and confirm. If macOS says the app is "damaged", the quarantine flag is the cause: after copying the app to Applications, run `xattr -dr com.apple.quarantine "/Applications/Vysted Terminal.app"`.

  **Operator to confirm:** whether this dmg gets signed and notarized before publishing. If it does, replace this paragraph with a normal install note; the signing and notarization steps are in `docs/redesign/OPERATOR_BRIEFING.md` section 2 step 3. An unsigned install on a machine that already has `vysted-terminal` keychain items from a prior build can also raise a one-time login-keychain consent prompt at first launch (R15-LEAD-143) — this is expected, not a bug; click Deny or Allow as you prefer for your own machine.
- **The first launch can take up to a few minutes.** The bundled data engine is a single-file binary that unpacks itself on every launch; a cold first launch or a busy machine can take well over a minute, and the app waits up to 270 s before it gives up (R15-LEAD-123). Wait for the status chip to turn connected before judging anything. Measured on the verifier's machine, the release build bound the engine at about 92-114 s and reached connected, holding steady past +340 s with live data in its panels (`bundle-rc2b/launch/LAUNCH.md`).
- Platform: macOS on Apple Silicon (`Vysted Terminal_0.9.0_aarch64.dmg`, 228,480,607 bytes, sha256 `9940d41b7ed6725aaabb6bb1709dc48b4f8ec51facd0696e376c68401139bc53`). No Windows or Linux build has been verified for this release; see `WINDOWS_MANUAL_CHECK.md`.
- There is no auto-update path and no published GitHub release pipeline yet (R15-RELEASE-002, -003); update by installing the next dmg.
- **Upgrading from 0.8.0:** the app-side half of this check (install 0.9.0 over an existing 0.8.0 install and confirm your workspace, portfolio and keys survive) is operator-attended; see `HAND_TESTING_GUIDE.md`. A headless, sidecar-side proof of the same upgrade path is being run separately; its result will live at `docs/redesign/verification/r15/stage-d/upgrade-0.8.0/` (not available at the time this note was written).
- Bring your own keys: provider keys are stored in the OS keychain through Settings, never in a file. A keyless local model through Ollama is supported with the limitation below.

## Known limitation - agent chat with a keyless local model

Reproduced verbatim from the operator briefing (`docs/redesign/OPERATOR_BRIEFING.md`, section "Known limitations at rc1 - agent chat with a keyless local model", DECISIONS_FOR_OPERATOR 4.9-4.12):

> ### Known limitations at rc1 — agent chat with a keyless local model
>
> Accepted by you Sat 26 Sep 04:15 IST (Tier-4 sign-off): `LEAD-030`, `LEAD-037`, `LEAD-038` ship `blocked_tier4` as one documented limitation class. `LEAD-035` now carries the SAME status
> (`blocked_tier4` as of `4c6dfe8c`, batch-24 merged `6778f892`) but for a different reason: it is an ESCALATION under your three-failure stop rule, not a fresh-verifier concurrence — batch-24's
> verifier REFUSED certification a fourth time and named a further narrowing-only fix it would certify (§4.10 below has the detail and your two options). No further filter round this release
> for the other three: a fresh "the local model states a figure with no successful tool call behind it" files against this limitation, not as a new fix. Carried verbatim into
> `RELEASE_NOTES.md`, `CURRENT_STATE.md` and this file, per your sign-off (LEAD-035's wording pending your (a)/(b) choice).
>
> - **`R15-LEAD-030`** (high, `blocked_tier4`, fresh verifier concurred in batch 23,
>   `r15/stage-c/batch-23/LEAD-030-CONCURRENCE.md`):
>   > With a keyless local model, the agent can still state an invented price or metric as if a
>   > tool had returned it when the figure is about a company no successful tool call in that turn
>   > covered — one named in the same paragraph as a company whose call succeeded (under a name the
>   > guard cannot map, or never looked up at all), or any company in a turn where no call failed or
>   > no tool was called — and a figure-less fabricated result dump or a code fence left open from
>   > an earlier round can also render, and every shape pinned in eight fix rounds is replaced by an
>   > honest "returned no data" note.
> - **`R15-LEAD-035`** (medium, `blocked_tier4` as of `4c6dfe8c` — an ESCALATION under your
>   three-failure rule, NOT a fresh-verifier concurrence like the other three; batch-24's verifier
>   REFUSED certification a fourth time; this is your call at rc1, §4.10):
>
>   > With a keyless local model, the "don't use tools" detector is a fixed phrase list: an
>   > unrecognised no-tool phrasing keeps the tools, so the agent may still read data and propose a
>   > portfolio change (always held for your review, never applied; under AUTO a watchlist or chart
>   > change does apply) and can occasionally state a price it never fetched, while a data request
>   > that qualifies a no-tool instruction after a comma or in reported speech ("Don't use any
>   > tools, except price_data …", "No tools, other than the price lookup …", "He says don't use
>   > tools, but …") still loses every tool and the agent then usually states an invented price as
>   > if fetched.
>
>   Your two options at rc1 (§4.10): (a) accept this residual as a documented known limitation
>   with the wording above, or (b) authorise one bounded round for the verifier's named guard (a
>   qualifier negative lookahead plus `(?<!says )`, which clears 3 of the 4 remaining over-matches
>   offline with 0 lost strips) on the rc2 line. **The lead recommends (b).**
>
> - **`R15-LEAD-037`** (medium, `blocked_tier4`, concurred on corrected wording):
>   > With a keyless local model, a figure the agent states for a company whose data call succeeded
>   > is not checked against that result at all, so it can give an older bar's value from the same
>   > payload as the current price (2 of 18 live runs, 5-6% off) or a figure that appears nowhere in
>   > the payload (1 of 18: ₹20,820 for a ₹2,082 stock).
> - **`R15-LEAD-038`** (medium, `blocked_tier4`, concurred):
>   > With a keyless local model, when you tell the agent not to use tools and ask for a portfolio
>   > change in the same message, it makes no call and nothing is written or queued, but its reply
>   > can say the change was made or staged for your review and can describe holdings that do not
>   > exist.
>
> Fail-safe (why this ships): `data-write` proposed changes always stage for review — AUTO only auto-applies `panel`/`chart`/`watchlist` kinds (`types/proposed-change.ts:38-46`); a narrated
> write stages nothing (no `tool_use` event); there is no `audit_orders` table any more (D81), so no order row can exist. Figure grounding by provenance
> (`sidecar/services/figure_grounding.py` + `agent_runtime._judge_clause`, `agent_runtime.py:2321`, rules 1/2a/2b/2c/3) replaces an ungrounded figure tied to an errored or never-called
> subject with an honest "returned no data" note. The rule-2c fail-safe (`agent_runtime.py:2378-2383`) fires only in a turn with an errored tool call — **a figure for a subject whose call
> succeeded is not checked at all** (LEAD-037). The shipping no-tool matcher is the closed
> `_NO_TOOL_CUE` list in `sidecar/services/planner.py` (`planner.py:136`, batch 21); batch 24 narrows it further, pending its own concurrence. Post-launch design (`DECISIONS_FOR_OPERATOR.md`
> §4.9–4.12, not built): claim grounding by field/provenance plus a structured no-data turn.

Status note (from `docs/redesign/DECISIONS_FOR_OPERATOR.md` section 4.10, outside the quoted block): the operator's ruling of 07:50 IST 26 Sep records R15-LEAD-035 as ACCEPTED, joining LEAD-030, LEAD-037 and LEAD-038 as one documented known-limitation class of the keyless local-model lane, `blocked_tier4`, with no further rounds this release. The quoted block above is the operator briefing's section as promoted at rc1 and is reproduced unchanged; where it says LEAD-035's wording is pending, 4.10 is the later record.

## Open items

Register state at `4b460027` (entries with status exactly `open`): **0 critical, 0 high, 43 medium, 72 low — 115 in all.** Every item below is filed for 0.9.1 under the operator's gate rule (new mediums and lows are listed as open at 0.9.0 and become the first 0.9.1 batch). See "What this release is" above for the final adversarial pass that produced most of the new entries.

Register totals at `4b460027` (803 entries; the severity-by-status split is in the table):

| Status | critical | high | medium | low | total |
| --- | --- | --- | --- | --- | --- |
| fixed | 17 | 120 | 277 | 215 | 629 |
| open | 0 | 0 | 43 | 72 | 115 |
| needs_gui | 0 | 2 | 1 | 1 | 4 |
| blocked_tier4 | 1 | 11 | 19 | 4 | 35 |
| removed_with_feature | 0 | 1 | 9 | 4 | 14 |
| not_a_defect | 0 | 0 | 6 | 0 | 6 |
| **total** | 18 | 134 | 355 | 296 | 803 |

### Open mediums (43)

| ID | Title |
| --- | --- |
| R15-AGENT-027 | humanize() classifies by HTTP status alone, so users get a next step that cannot work: OpenAI no-credit 429 and free-model shared-pool 429 say 'wait a minute', invalid Gemini/xAI keys (400),... |
| R15-CODE-PLATFORM-072 | Data-source description is hand-maintained in marketplace.ts, disconnected from provider_registry and the plugin contract, and has already drifted (yfinance entry lists 3 keys vs 7 served; n... |
| R15-FINAL-012 | RELIANCE.BO earnings history is two quarters stale against the NSE listing of the same company (latest 2025-12-31 vs 2026-06-30) and its analyst consensus differs (36 vs 26 analysts), with n... |
| R15-FINAL-013 | 'Should I buy Amal Ltd?' on gpt-4o-mini gets a buy lean justified by an industry P/E comparison no tool fetched |
| R15-FINAL-014 | Ollama lane: a tool call leaked as a Python-literal dict (None/True/False) is not rescued; the raw call blob is shown as the assistant reply |
| R15-FINAL-015 | THIRD_PARTY_NOTICES.md lists the wrong version for 56 of 121 main-sidecar Python components because transitive deps are unpinned and the bundle ships what pip resolved at build time |
| R15-FINAL-018 | With the ULTRA slider one user turn fans out into N sequential full ULTRA heavy runs (4 research calls -> ~19 min, ~$1.25, each brief replacing the last) |
| R15-FINAL-019 | Settings SearXNG card tells a user whose Docker/OrbStack is installed but stopped that Docker 'isn't available' and to install it, ignoring docker.cli_present/daemon_running and the sidecar'... |
| R15-FINAL-020 | Keyless web search: the Brave engine (impersonated fetch) gets HTTP 429 while a plain-UA curl from the same host gets 200 in the same minute, so keyless web_search returns zero rows on this... |
| R15-LEAD-061 | strip_model_bibliography misses common bibliography heading variants, so a model-written source list survives beside the verified one |
| R15-LEAD-062 | A Gemini free-tier per-minute 429 (RESOURCE_EXHAUSTED ... retry in Ns) is shown as "out of credit or quota. Add credit or check your plan" |
| R15-LEAD-063 | historyForSend drops the oldest turns once the thread passes 60k chars with no notice to the user or the model |
| R15-LEAD-064 | 20-F ownership lane returns not_applicable with 0 holders for ADRs whose 20-F has a holders table (IBN, HDB) |
| R15-LEAD-065 | FAST research web-only branch (no instrument resolves) awaits _web_round without a time box; only the resolved branch uses asyncio.wait_for |
| R15-LEAD-066 | write_screener_filters with only the documented OR/nested group tree is rejected: schema requires criteria |
| R15-LEAD-067 | Macro search failure renders as an empty "No matching series": the store catches every error and stores []; keyless FRED search is a 502 with an actionable message |
| R15-LEAD-068 | Settings privacy copy over-promises: "Nothing leaves this machine except calls you make to providers you configure" while keyless lanes (Yahoo, NSE/BSE, DDG) call out without configuration |
| R15-LEAD-069 | Screener formula validate accepts a boolean operand in a comparison ("roe > (pe_ratio < 15)", "(pe_ratio > 3) > 0.5") and coerces it |
| R15-LEAD-070 | Analyst ratings swallow a Yahoo rate-limit into an empty 200 list that reads as no coverage |
| R15-LEAD-072 | Heavy/ULTRA brief stopped by its spend ceiling publishes note=None, and the cross-check keeps spending after the breach |
| R15-LEAD-073 | The latest round's tool results are never elided by _fit_to_window, so a multi-result round leaves the answer below the 1/8 reserve |
| R15-LEAD-074 | Scheduled and MCP-run workflows run with no event sink: action.notify_desktop reports notified:true but nothing is shown |
| R15-LEAD-075 | Editing a custom agent silently clears its default_model on save (customSpecToSummary sets defaultModel: null) |
| R15-LEAD-076 | A partially throttled screen shows "No rows matched - loosen a threshold / Reset filters" although most symbols were never evaluated |
| R15-LEAD-078 | Flaky test_research_fast::test_fast_web_round_runs_alongside_a_time_boxed_fan_out: an unstubbed earnings-quality leg makes it timing-dependent |
| R15-LEAD-079 | ReasoningSplitter releases a held reasoning echo in full when an answer follows it (provisional, shard evidence only) |
| R15-LEAD-080 | Agent/MCP compute_greeks and price_option return QuantLib-unit vega/theta/rho unlabelled; the model restated them as per-unit values |
| R15-LEAD-081 | sp500 screen serves S&P 500 member PTC as PTC India Limited (INR) from a fundamentals row written before the LEAD-044 fix; no migration purges it |
| R15-LEAD-082 | Screener top-K round-robin gives currency-less rows their own group slot, so a null-market-cap row displaces a real one |
| R15-LEAD-083 | Earnings drill-down As-of chip shows the client fetch clock and ignores the envelope server as_of |
| R15-LEAD-122 | Screener 'Export CSV' writes the file but shows no saved path, toast or error (the result of downloadCsv is discarded) |
| R15-LEAD-124 | sec-edgar-mcp is killed while still extracting on a cold or busy launch (~91 s) and /sec routes return 501 for the whole session |
| R15-LEAD-126 | The main data engine takes about 100 s to answer /health on an idle warm launch, behind the MCP binds, so a user waits over a minute and a half before any panel loads |
| R15-LEAD-128 | Research brief drops an NSE small cap's price when the 6-month history fetch is slow: price_data fetches history before the quote inside the 6 s box |
| R15-LEAD-129 | README keyless section repeats the false promises R15-UI-052 removed from the app (keyless web research via DuckDuckGo, 'fully offline'); BYOK list omits OpenRouter |
| R15-LEAD-130 | Palette/watchlist autocomplete cannot find a company by former name or BSE scrip code though /resolve binds both |
| R15-LEAD-131 | Identity cross-check flags the correct company as a possible mis-resolution ('&' vs 'and', 0.40); raw BSE '-$' suffix shown as the name on 310 scrips |
| R15-LEAD-135 | Research's news leg still fetches the bare ticker under the session region, so a US name colliding with an Indian ticker carries the Indian namesake's headlines (Halliburton brief under IN t... |
| R15-LEAD-138 | The copilot/MCP fundamentals tool skips the SME exchange-filings fallback: MCP fundamentals VOLERCAR returns ok:false 'No data provider covers...' while REST /fundamentals serves values |
| R15-LEAD-140 | A cold 100-name NSE batch takes ~171 s, over the 120 s client QUOTES_BATCH_TIMEOUT_MS, so the first portfolio refresh of a large cold portfolio aborts (the next refresh is 9.4 s, 100/100) |
| R15-LEAD-142 | Recall regression from the LEAD-136 fix: brand-only and list headlines for the 234 NSE word tickers now drop ('Stocks to buy: Titan, Lenskart, Dabur among Nomura's 17 consumer picks', 'Titan... |
| R15-RESEARCH-022 | A 200-status CAPTCHA/block page from a keyless engine is recorded as a healthy empty answer and resets that engine's circuit breaker, so a blocking engine is never benched and an all-blocked... |
| R15-UI-084 | The agent surface cannot take the full cockpit: the dock width is hard-capped at 1200 px and there is no maximize mode (FR-001 requires 'dominant column or full cockpit') |

### Open lows (72)

| ID | Title |
| --- | --- |
| R15-AGENT-065 | Two documented-deferred copilot/customizability builds remain unbuilt: the 3-pane agent roster panel with hard persona hand-off, and the data-source connector hub (Plugin Manager shows only... |
| R15-AGENT-085 | Plain chat answers carry no citation object and no unverified-claim check: the citation and [unverified] machinery exists only on research briefs and the Equity Overview narrative |
| R15-AGENT-086 | A Delegate run can never be paused for a question: pause_run has no caller (no ask_user tool, no pause route), so the answer route serves a state no run can reach |
| R15-CODE-DATA-018 | Resolution.needs_disambiguation and the DISAMBIGUATION_THRESHOLD re-export are dead second-decision surfaces kept alive only by tests |
| R15-CODE-FRONTEND-031 | Under AUTO the transcript narrates 'Applied:' before the async apply resolves, so a failed apply stays recorded as applied in the chat step line |
| R15-CODE-PLATFORM-045 | Boot path bridges a plugin's panels and commands without checking that loadPlugin succeeded, so an errored plugin still contributes UI |
| R15-CODE-PLATFORM-046 | moduleForPlugin re-implements capability negotiation without the runtime's try/catch, so a throwing getPanels()/getCommands() rejects bootstrapPlugins() mid-loop |
| R15-DATA-098 | The yield curve emits a duplicated first point and extrapolates past the last instrument without saying so when step_days floors to 1 |
| R15-FINAL-025 | DEEP research overran its 180 s wall budget by 79 s (259 s) on the local lane: the final synthesis call is not boxed by the remaining wall |
| R15-FINAL-026 | Screener freshness line prints unrounded float seconds ('quotes 41.64699196815491s ago') |
| R15-FINAL-029 | transform.code size caps are bypassed by sum(list, start): a 25-character expression builds an uncapped list (8.3 GB peak RSS) and keeps running after the 5 s timeout |
| R15-FINAL-032 | A local-model narrative written with markdown-bold headers (**TAKE** / **BULL** ...) collapses to a flat summary + insights; the five typed fields come back empty |
| R15-FINAL-034 | Brief header reads 'web + structured data' directly above the 'Structured data only - no web sources found' banner on a filings-only brief |
| R15-FINAL-036 | CURRENT_STATE.md cites a missing build report, the deleted monte_carlo.py and an absent ConnectCard.tsx, and reports 0.8.0 and 619 vitest / 942 pytest |
| R15-FINAL-038 | MCP discovery file advertises protocol 2025-06-18 while /mcp/status reports 2025-11-25; the Rust sync comment points at a constant that does not exist |
| R15-LEAD-025 | The fundamentals warmer hits openbb-mcp hard at boot with no observed throttling on the default (non-IN) universe warm path |
| R15-LEAD-041 | Earnings estimate detail's analyst count and its EPS triple are read from different upstream fields and disagree: TM shows estimate_analyst_count 1 while the EPS triple is null |
| R15-LEAD-042 | The proposed-change review card and its applied label price a US lot in the session region's currency, not the listing's: {MSFT, 4, 480 USD} under an IN session reads 'Add 4 MSFT @ ₹480 to t... |
| R15-LEAD-047 | A derived EPS (e.g. MSFT) is stamped field_meta status 'ok' with no reason text distinguishing it from a directly-served EPS |
| R15-LEAD-052 | An ALL-CAPS headline still over-matches a 3-character common-word ticker in the non-IN relevance gate |
| R15-LEAD-053 | Direct GET /quotes/TATAMOTORS.NS and .BO still 404 with no rename hint to TMPV, even though /resolve already lists TMPV first for the same query |
| R15-LEAD-054 | sp500.json carries ECHO and VMRK, two symbols absent from the current US resolver master, the same stale-universe-seed class R15-LEAD-049 fixed for nifty50 |
| R15-LEAD-055 | R15-AGENT-053's own regression test (NewsFeedPanel 'publishes the top headline...') flakes under full vitest-suite load: a context-bus publish is asserted synchronously right after a waitFor... |
| R15-LEAD-056 | DOW's (and NICE's) own stripped company-name alias is the common word itself, so the DATA-030 stoplist's anchored-ticker rule never applies and 'Dow Jones falls 300 points' still tags DOW |
| R15-LEAD-057 | Name-alias derivation leaves master-name registry artefacts in place ('amazon com', 'keycorp /new/'), so plain-prose company mentions never tag |
| R15-LEAD-058 | GM and GS (2-letter tickers with no brand token) never pass the non-IN relevance gate on a bare mention |
| R15-LEAD-084 | NSE holiday table ends 2026-12-25; 2027-01-26 (Republic Day) is treated as an IN trading day (D-B9-4 covers the test horizon, not the data) |
| R15-LEAD-085 | Suffixed unknown symbols (QQZZFAKE.NS, XYZNOTATICKER.BO) still return 200, 0 bars, reason null |
| R15-LEAD-086 | The sibling [failed: ...] trailer still rides verbatim assistant history to the provider (_without_step_trailers strips only [tool steps:]) |
| R15-LEAD-087 | Ratio guard still replaces a correct ADS-ratio sentence dated 26-Jun-2026 / Jun-26-2026 with "not available" |
| R15-LEAD-088 | Resolver suggestions for MAZAGONDOCK / RELIANCEIND variants |
| R15-LEAD-089 | Import toast says "Imported settings." for {settings:{fontSize}} when nothing applied |
| R15-LEAD-090 | Cross-check extract still slow before the wall timeout (verdict leg boxed) |
| R15-LEAD-091 | Type-first JSON tool-call text can leak into the visible answer |
| R15-LEAD-092 | _row_value has a twin implementation that can drift |
| R15-LEAD-093 | One doc line still says "the 18" host actions while the others and the catalog say 19 |
| R15-LEAD-094 | sidecar/agents/copilot.json system prompt example reply "Built you a brief on NVDA - it's at the top of the cockpit" teaches an applied-tense claim that conflicts with review mode (local rb1... |
| R15-LEAD-095 | Bond pricer display currency fixed at mount; region switch while open keeps USD |
| R15-LEAD-096 | leading_token reads a negated COMPLETE sentence as complete |
| R15-LEAD-097 | A scrip with one trade inside 52 weeks keeps a forward-fill-derived provider 52w low unflagged when it is within the 10% tolerance |
| R15-LEAD-098 | The announcements cache key includes limit and the raw symbol form, so callers that differ in limit or .NS suffix refetch the full history |
| R15-LEAD-099 | save_screen overwrites the user's live screener draft without disclosing it; Undo does not restore the draft |
| R15-LEAD-100 | _us_isin caches a definite ISIN miss for the life of the process |
| R15-LEAD-101 | CONTRIBUTING.md says 'Python 3.13+' but the build requires exactly 3.13 |
| R15-LEAD-102 | Ollama adapter catch-all humanizes internal exceptions as an Ollama error |
| R15-LEAD-103 | Onboarding local-model recommendation collapses any sidecar failure to 'Couldn't reach the local engine' |
| R15-LEAD-104 | Perplexity/Sonar ResearchSource builders drop published_at |
| R15-LEAD-105 | OpenRouter chat URL literal in research lanes |
| R15-LEAD-106 | SEC company search is a raw substring match |
| R15-LEAD-107 | add_chart_drawing: a non-empty bogus panelId bypasses the open-chart fallback |
| R15-LEAD-108 | BLUEPRINT says 12 AI agents; 13 first-party agents ship |
| R15-LEAD-109 | /earnings/{sym}/estimates maps a yfinance 429 to 502 provider_error 'unexpected response', while /fundamentals/{sym}/ratings maps the same throttle to 429 rate_limited |
| R15-LEAD-110 | A listed 1994 JPM 10-K opens as 502 'unexpected response' (sec-edgar-mcp get_filing_sections NoneType) instead of degrading to the raw filing text |
| R15-LEAD-111 | clearSearch does not bump searchGeneration; late 501 paints error under emptied SEC search field |
| R15-LEAD-112 | 200 F&O bhavcopy with truncated PK zip raises BadZipFile out of fetch_latest_fo, no walk-back |
| R15-LEAD-113 | Stale 'client-side mathjs' comments in node-registry.ts:185-190 and code-node-run.ts header |
| R15-LEAD-114 | nse_bhavcopy.py:36-40 docstring says the NSE master is '~2,675 symbols' and that SME (SM/ST) rows are 'outside the master'; the master is now 3506 rows including 571 SM |
| R15-LEAD-115 | The quarterly-gap TTM reason always says 'a quarter of the trailing year' is unfiled, which understates the gap for fresh listings with only one or two quarters ever filed |
| R15-LEAD-117 | FOCUS&exchange=BSE answers venue_not_covered with a note claiming FOCUS is not listed on BSE (BSE 543312 exists, a different company) |
| R15-LEAD-118 | Shareholding percentages differ by symbol spelling for the same scrip/quarter/filing (e.g. FOCUS vs FOCUS.BO vs 543312) |
| R15-LEAD-119 | The vitest coverage ratchet never gets committed: thresholds read lines 0 while measured coverage is about 81.4 |
| R15-LEAD-120 | Bare 2-letter ticker absent from the company name (KO / Coca-Cola) still fails the non-IN relevance gate; _entity_signals credits a ticker mention only for len(symbol)>=3 |
| R15-LEAD-121 | llama3.1:8b prints USD portfolio holdings with the rupee sign although each holding carries currency:'USD' (IN default region) |
| R15-LEAD-125 | After the data engine dies or fails to start, panels and chat show their own generic copy; only the status chip names the reason |
| R15-LEAD-132 | NSE EOD warm stamps a holiday (2 Oct) as the trade date on 1 Oct's bhavcopy rows |
| R15-LEAD-133 | Never-installed Ollama is told 'start Ollama' and the guided setup with the install link never opens |
| R15-LEAD-134 | The 8 s FAST web-round box is shorter than the keyless chain's 6 s per-engine deadlines; Mojeek is never reached and a timeout is reported as 'no web backend' |
| R15-LEAD-139 | SUMAX/QUALIANCE /fundamentals is still a 404 whose body carries action 'Check the symbol or series id.' beside the correct typed not-covered detail |
| R15-LEAD-143 | An unsigned 0.9.0 release launch raises a login-keychain SecurityAgent consent prompt at boot when vysted-terminal keychain items from another build exist; VYSTED_DATA_DIR isolates the data... |
| R15-LEAD-144 | A double-suffixed spelling (RELIANCE.NS.NS) is normalised to the known listing by /fundamentals (200, NSE filings fallback, P/E and market cap typed null) but 404s on /quotes; five slash-con... |
| R15-LIFECYCLE-040 | The Tauri-Rust MCP spawn (the Windows deadlock fix) has never been exercised inside a launched packaged app; CI builds the bundle and smoke-tests the raw binaries, but no packaged cold boot... |
| R15-UI-068 | DataTable, 'the ONE table primitive', has no loading/empty slot and its sort headers are not keyboard-operable, so panels hand-roll skeleton tables and four surfaces still hand-roll data tab... |

### Awaiting manual check (needs_gui, 4)

These could not be shown on the rig and wait for a person to click through the packaged app (see `HAND_TESTING_GUIDE.md` and `WINDOWS_MANUAL_CHECK.md`).

| ID | Severity | Awaiting manual check |
| --- | --- | --- |
| R15-CODE-AGENT-001 | high | Windows half only — macOS packaged and `pnpm tauri:dev` both confirmed live (every panel loads, no webview 403). Remaining: launch the Windows packaged app and confirm the same. |
| R15-LIFECYCLE-008 | high | No diagnostics exist and a shipped build persists no log at all: every Rust, sidecar and MCP line goes to process stdout (no console at all on a Windows release build), so a user with a problem has no record. Packaged click-through on "Copy diagnostics" still needed on both platforms. |
| R15-UI-022 | medium | Chart drawing tools cannot place what the user clicks: anchors snap to the bar close, clicks past the last bar commit invisible drawings, Text always reads 'label', and Lock is a dead control. |
| R15-DOCS-024 | low | MCP_INTEGRATION.md's Claude Desktop (mcp-remote) setup has never been demonstrated end to end, and its claim that tools appear in Claude Desktop's slash picker as /vysted__price_data is unverified. |

`blocked_tier4` entries (35) wait on an operator decision, not on code; they are listed in `BACKLOG_0.9.1.md`. Four of them are the signed-off local-model limitation quoted below.

## Build and verification

- Built from `1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056`. Gates at this head: ci-local exit 0 (vitest 2048, cargo 32, pytest 4013 with the skip), sidecar smoke test exit 0 (13 agents, toolCount 39), Gate 8 8 passed (`r15/stage-c/rc2-failsafe/VERIFY.md`).
- Production bundle: `Vysted Terminal_0.9.0_aarch64.dmg`, built and launch-checked from this same commit (`r15/stage-d/bundle-rc2b/BUILD.md`, `.../launch/LAUNCH.md`). 228,480,607 bytes, sha256 `9940d41b7ed6725aaabb6bb1709dc48b4f8ec51facd0696e376c68401139bc53`, unsigned.
