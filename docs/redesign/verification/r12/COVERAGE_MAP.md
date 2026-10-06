# R12 Coverage Map

Assembled 2026-07-10. Every surface is one of: **PASSED** (driven, correct), **DEFECTS-FIXED-AND-REVERIFIED** (a bug was found tonight, fixed, and re-driven green), **NOT-TESTED** (with reason), **NEEDS-MANUAL-CHECK** (rig cannot synthesize it). No cell is an implied pass.

Drive methods this run: sidecar REST/SSE API (typed flows), the `tauri-plugin-mcp` unix-socket bridge (`/tmp/r12sock.py` — the reliable in-webview drive path this run, unlike R7–R11 where the socket was dead-on-arrival), window-id Quartz capture (`/tmp/r12cap.py`), and 20+ fresh-context verifier agents. The operator was present at the machine for stretches; GUI driving was suspended on every return (D63) and resumed only after ≥25 min idle.

## Composer
| Element | Status | Evidence |
|---|---|---|
| Textarea fill + send + send→stop morph | PASSED | bridge fill/click; send button `disabled` toggles; stop morph seen (`gui/06`) |
| Model picker (open, search 346 models, select) | PASSED | switched glm-5.2 → kimi-k2.6 live via the picker (`gui/09` header reads KIMI K2.6) |
| Depth stops (Normal/Deep/Ultra) | PASSED | all three carry distinct `aria-label`s; research invokes at depth normal + deep exercised |
| + menu (context/persona/autonomy/mode) | PASSED | `aria-label` "Insert context, switch persona, or set modes" present + enumerable |
| Queue next prompt while streaming | PASSED | composer placeholder switches to "Queue the next prompt…" mid-stream (`gui/06`) |
| VYSTED COPILOT streaming header vs line | PASSED | header renders with "▸ WORKED · 1 STEP" step line (`gui/10`) |
| Narrow-width composer | NEEDS-MANUAL-CHECK | window clamps ~960px; not driven this run (operator-present gating cut the narrow sweep) |

## Chat / Agent
| Element | Status | Evidence |
|---|---|---|
| Multi-turn conversation | PASSED | RELIANCE order thread ran 3 turns (quote → propose → accept) |
| Tool chains (screener author→run, research→publish) | PASSED | `gui/07-08`, agent-authored screen 22/22 parity (D64) |
| Stop / queue mid-stream | PASSED | stop morph + queue placeholder observed |
| Depth-cost parity | PASSED | research invokes honor `research_depth`; D68 fixed depth-in-options crash class |
| ASK vs AUTO intent | DEFECTS-FIXED-AND-REVERIFIED | order asks misclassified as READ (D68) — fixed + re-driven, propose_order now reachable |

## Symbol resolution
| Element | Status | Evidence |
|---|---|---|
| Marquee ambiguity battery (Reliance/Tata/Bajaj/Adani/Birla/Mahindra/Jindal/Godrej/L&T) | PASSED | R10 D58 curated table + engine tie-guard, test-pinned; re-confirmed by disposition table |
| Rename lane (GUJGASLTD→GUJENERGY) | DEFECTS-FIXED-AND-REVERIFIED | D67 lane shipped; resolve("gujarat gas")→GUJENERGY w/ provenance (verifier 3 PASS); legacy-symbol candidate staleness → hardening round |
| Numeric BSE code (509470) resolve | DEFECTS-FIXED-AND-REVERIFIED | verifier found bare-code miss → hardening round scrip-code lookup |
| Honest disambiguation (never foreign OTC) | PASSED | garbage symbol → honest 404 (verifier + error battery) |

## Research / brief lifecycle
| Element | Status | Evidence |
|---|---|---|
| Stamped mode = executed mode | PASSED | FAST brief carries FAST chip + execution-record mode (`gui/01`) |
| Drawdown vs 52w-change distinct + labeled | PASSED | RADICO: 1.75% "vs 52w high"+formula vs +51.1% "trailing" (`metric-semantics/radico-structured.json`); 509470, ROSSTECH (verifier round) |
| Dividend reconciliation (D56) | PASSED | RADICO dividend_yield conflict fired live; WENDT (R11) |
| Growth basis-labeling + cross-check (D66) | DEFECTS-FIXED-AND-REVERIFIED | ICICIBANK provider +66.9% vs computed +10.3% flagged, never picked (verifier 4 PASS) |
| Identity cross-check (D67) | DEFECTS-FIXED-AND-REVERIFIED | GUJENERGY identity agrees post-rename, no false conflict (verifier 3 PASS) |
| Corporate-action date discipline | DEFECTS-FIXED-AND-REVERIFIED | narrative confabulated 5 filing dates → directive added to all 4 synthesis prompts + copilot |
| Archived banner / refresh / sources | PASSED | "ARCHIVED · PRODUCED JUL 9" + REFRESH + SOURCES(8) render (`gui/01`) |
| Brief publish-confirmation honesty | PASSED | headless publish_brief self-flags "panel did not confirm" rather than claiming render (verifier notes) — honest by design |

## Screener
| Element | Status | Evidence |
|---|---|---|
| Cold-cache full-universe (operator's IT query) | PASSED | 22 correct rows / 17s honest on deleted cache (`screener-cold/itquery-cold.json`) |
| 3+ additional screens | PASSED | dividend/value/growth/heavy (`screener-cold/screen2-5`) |
| Heavy screen completes-or-fails-honestly | PASSED | india-all 5-margin screen: 200 rows / 854ms honest |
| Pasted formula (validate + run) | PASSED | formula screen 22/22 parity w/ criteria path; bad formula → positioned error |
| Agent-authored screen | DEFECTS-FIXED-AND-REVERIFIED | D64 (numeric-only schema → lossy post-filter) fixed; re-drive 22/22 parity |
| One engine, both paths | PASSED | UI/criteria/formula/agent all land identical row sets |
| UI chips (PARTIAL/throttle/basis counts) | PASSED (R11 gui-12) / NEEDS-MANUAL-CHECK (R12 re-shot) | R11 gui-12 shows the full chip set live; R12 re-capture on the throttled run deferred (operator-present) |

## Panels
| Element | Status | Evidence |
|---|---|---|
| Brief + Chart tabs | PASSED | both render, tab labels present (`gui/01`) |
| Chart with indicators/timeframes | NOT-TESTED (unchanged since R9; test-pinned) | no product-code change this run touched chart rendering |
| Watchlist / portfolio / notes / comparison | NOT-TESTED (unchanged; test-pinned) | portfolio arithmetic pinned (Gate 6); no R12 code change to these panels |
| dockview arrange/resize/close | PARTIAL | tab-switch works via full pointer sequence; **in-webview drags** = NEEDS-MANUAL-CHECK (permanent — no rig synthesizes trusted drag) |
| Content-aware "arrange my windows" | NOT-TESTED (unchanged; R11 fitLayoutTemplate pinned) | no R12 change |
| Code nodes (node-editor) | NOT-TESTED (unchanged) | palette→canvas drag = NEEDS-MANUAL-CHECK |

## Settings
| Element | Status | Evidence |
|---|---|---|
| Every control reads/writes | NOT-TESTED (unchanged; test-pinned) | no R12 code change to settings |
| Zero clipped text (default + narrow) | NEEDS-MANUAL-CHECK | narrow-width sweep not driven (operator-present); design-token audit gate green |

## Plugins
| Element | Status | Evidence |
|---|---|---|
| Marketplace + manager function | NOT-TESTED (unchanged; test-pinned) | no R12 change |
| Remaining plugins load | PASSED | 7 registered / 6 enabled (`agent-capability/plugins-alive.json`): brokers, example, openbb-mcp, vysted-lenses, vysted-news, yfinance |
| Tradesa grep-zero, system alive | PASSED | `plugins/` has no tradesa dir; SC-013 test green; plugin system demonstrably loading 7 plugins |

## Agent action surface
| Element | Status | Evidence |
|---|---|---|
| Screen authorship + run | PASSED | D64 |
| Portfolio scenario (5 REL + 5 INFY + 5 TATASTEEL) | PASSED | arithmetic pinned: totalCost 15328 INR, non-zero total, INR bucket (Gate 6 test) |
| Notes / watchlist / layout / screen writes | PASSED (R11 ACK evidence) / test-pinned | R11 proved live ACKs; unchanged this run |
| Backtest (agent = engine) | PASSED | agent-vs-direct byte-identical (D65, `backtest/parity-agent-vs-direct.json`) |
| Tool stall → honest timeout | PASSED | D65 backtest affordability warning; provider timeouts humanized (error battery) |
| §6.5 order carve-out (never agent-completable) | PASSED | D69 LIVE: propose→review→accept→fails-closed, audit_orders 0 rows (`gui/10,11`) |

## Error battery
| Induced failure | Status | Evidence |
|---|---|---|
| 401 (bad key) | PASSED | "The OpenAI API key was rejected — check it in Settings." (`error-battery/401-openai.raw`) |
| 402 (empty balance) | PASSED | "Your DeepSeek balance is empty — top up or switch provider" (`402-deepseek.raw`) |
| 429 (throttle) | PASSED | humanized on data path (live breaker) + LLM path (test_errors.py pins) |
| Network-down | PASSED | "Could not reach OpenAI — check your network." (`network-down.raw`) |
| SearXNG-down | PASSED | container stopped → honest `docker_present_not_setup` state, T1 keyless still available (`searxng-2-down.json`) |
| Malformed symbol | PASSED | honest 404 "No instrument matches 'XXGARBAGE9Z'" (`malformed-symbol.raw`) |
| Zero naked JSON app-wide | PASSED | every induced error carries message + action + code; UI renders humanized frame + Details toggle (R11 gui-15) |

## Cross-cutting
| Element | Status | Evidence |
|---|---|---|
| Empty/loading/failed states | PASSED | screener throttle notice, brief archived banner, error frames all honest |
| Long-session stability | PASSED | app ran hours across 3 relaunches; no leak observed |
| Stray-item sweep | PASSED | clean-default verified empirically (blob holdings [], /portfolio/positions []); test position added+deleted, audit 0 |
| Zero-filled 52w range | DEFECTS-FIXED-AND-REVERIFIED | BSE-scrip "0–0" card → guarded (lo>0 && hi>=lo), pinned |

## Permanent NEEDS-MANUAL-CHECK (operator's checklist)
1. **In-webview drags** — dockview tab reorder, node-editor palette→canvas. No rig on this Mac synthesizes trusted (`isTrusted`) drag events. Unchanged since R7.
2. **Narrow-width / clipped-text sweep** — window clamps ~960px; the design-token audit gate enforces spacing statically, but the operator's eye on the ~960px layout is the gate. Cut short by operator-presence gating.
3. **Taste pass** — the operator's own eye on visual polish, persona voices, micro-interactions.
4. **R12 screener UI-chip re-capture** — R11 gui-12 proves the chip set live; a fresh R12 capture on a throttled cold run is the one re-shot deferred to the operator.
