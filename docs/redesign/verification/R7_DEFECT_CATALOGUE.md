# R7 Defect Catalogue — built from the real screen (2026-06-10, pre-build)

Method: live app (dev build, sidecar connected, DeepSeek key live), driven via the
tauri-plugin-mcp rig; real-pixel captures in `verification/r7/`; four vision-agent
sweeps over 29 captures; direct sidecar-API probes. Items marked LIVE were exercised,
not inferred. Vision-agent findings from downscaled images are marked (V) and get
re-verified per-surface during the build.

## A. Dead / half-wired controls (LIVE)

| ID | Defect | Evidence |
|----|--------|----------|
| A1 | ⌘K agent entry (Warren Buffett) sends the literal query text ("warren") as a USER CHAT MESSAGE instead of cleanly switching agent; lens chip then shows raw lowercase id `warren`; chat header still says VYSTED COPILOT | 40-after-warren-click.png |
| A2 | Ticker search by company name is dead in the UI: typing "Route Mobile" into watchlist Add-symbol shows NO suggestions — yet `GET /resolve/autocomplete?q=Route+Mobile` returns ROUTE @ 0.98 even in US region. Frontend never calls/renders autocomplete | 41-route-mobile-search.png + live API capture |
| A3 | Duplicate Chart tab: live `openPanel('chart')` is singleton-correct now (1 tab), but the operator's SAVED workspace blob can still carry a legacy duplicate → needs a layout-state migration/reset on load | live tab-count probe |
| A4 | Composer has no stop button; no prompt queue (typing mid-run is possible but send during run is unhandled) | composer inspection |

## B. The agent speaks telemetry, not language (LIVE)

| ID | Defect | Evidence |
|----|--------|----------|
| B1 | Narration trace fully expanded by default: "✓ RESEARCHED 335 · 7 STEPS" + per-step ms timings ("27m25ms", "5879ms") ABOVE the prose answer | 41-route-mobile-search.png |
| B2 | Joined-segment typography bug: "…for a Buffett-style look.Set SPY up…" (missing space after period — same class as "dive.The") | 41-route-mobile-search.png |
| B3 | Raw engine telemetry leaks into the Brief panel UI: "PER-ROUND WALL-CLOCK GUARD: ROUND EXCEEDED 30S" rendered as a banner | 01-tab-Brief.png |
| B4 | Brief header is cryptic chrome: "DEEP SPY 59 SOURCES · 0.9 USE …" + "WEB + STRUCTURED DATA EOD AS OF…" stacked rows | 01-tab-Brief.png |
| B5 | Narration grounding unverified: "→Applied: Arrange the single focus layout" claims need live re-check against actual layout results (the known fake-split/false-narration bug class) | 41-… + mandate |

## C. Data layer (LIVE, sidecar API)

| ID | Defect | Evidence |
|----|--------|----------|
| C1 | ICONIKSPEV resolves with contradictory master data: exchange "NSE" but yahoo_symbol "ICONIKSPEV.BO", confidence 0.6 — master-data quality is the resolution-bug root (ICONIKSPEV→APCL class) | /resolve capture |
| C2 | ICONIKSPEV history: `bars: [], provider: "none", reason: null` — BSE bhavcopy provider can't serve it (no scrip-code routing; the seeded BSE master still has 2 placeholder rows — `regenerate_bse_master.py` was never run against the live master), and the honest `in_eod_only` reason misfires because region_hint misses it | /history capture |
| C3 | No NSE corporate announcements / results filings / shareholding-pattern ingestion anywhere; no announcements surface in panels or research | repo + API survey |
| C4 | Keyless web search rides a throttled DDG floor (known); engine rotation/circuit breakers absent | search service read |

## D. Design-system enforcement failures (V = vision sweep; representative, NOT the worklist)

| ID | Defect | Evidence |
|----|--------|----------|
| D1 | Node editor leaks near-WHITE unstyled @xyflow zoom/lock controls + default minimap/handles/edges (the canonical enforcement failure) | 17-node-editor.png (V, high confidence — known) |
| D2 | Chart panel: 3 stacked toolbar rows of cryptic abbreviations (1m…1mo SYNC CX ZM SY / DRAW TREND H-LINE V-LINE RAY RECT ELLIPSE FIB RETR FIB EXT CHANNEL TEXT / COMPARE) — no progressive disclosure | 01-tab-Chart.png LIVE |
| D3 | Indicator wall: flat always-visible grid of ~25 indicators consumes ~40% of chart panel height | 01-tab-Chart.png LIVE |
| D4 | Composer: 4 stacked chrome rows (Agent/Delegate/LENS · +DEEP GO ALL OUT · ASK AUTO · PROVIDER/model/send) around one input | 01-tab-Chart.png LIVE |
| D5 | Header model label truncates: "DEEPSEEK-V4-FLA…"; tab strip truncates mid-word ("Equi", "Sc…") with bare ">18" overflow | LIVE captures |
| D6 | Greeks dashboard: huge dead whitespace right of a small table | 25-greeks.png (V) |
| D7 | Backtest trade table truncates prices mid-number (max-w-0 class bug) | 18-backtest.png (V, matches inventory §3) |
| D8 | Empty states across portfolio/equity-overview/earnings/analyst/screener are bare prose or spinners, not composed EmptyState | 12/13/28/29/30 (V) |
| D9 | Marketplace micro-text ~8.8px illegible; settings micro-checkbox rows | 15-marketplace.png (V) + inventory |
| D10 | Settings: provider rows inconsistent (status text/button alignment), "OpenRouter (broker)" mislabel, wall-of-rows without disclosure | 01-tab-Settings.png LIVE |
| D11 | Palette: agent rows show name+desc but truncation behavior + group headers need enforcement; footer keycaps present | 02-palette-*.png |
| D12 | Lens chip renders raw agent id ("warren") instead of display name | LIVE |

## E. Architecture / engine (from mandate + studies)

| ID | Item |
|----|------|
| E1 | Next.js shell → Vite (audit: zero blockers; 1 next/font import, 2 app files) |
| E2 | Research engine: loop paradigms already adapted (iter.py/deep.py); MISSING: T1 hardened keyless search tier (multi-engine rotation, curl_cffi, circuit breakers, scrubbing), T2 one-click SearXNG via Docker (daemon confirmed available), T3 OpenRouter web-search server tool (Firecrawl default / Exa) + sonar lane, N/D/U depth router, finance source-prioritization, A/B |
| E3 | Tongyi on OpenRouter: DELISTED (live check 2026-06-10) — keep out of picker |
| E4 | React duplicate-key warnings (known floor item; reproduce during build) |
| E5 | Micro-cap chart 502 class: now manifests as empty-bars/provider-none (C2) — fix is real BSE coverage + honest reason |
