# JARVIS Sprint 3 — final report ("the research-experience pass")

_Autonomous pass on branch **`002-jarvis-intelligence`** (base `2397260`). Authored by the
lead (Opus 4.8, 1M). Not merged to main; version untouched. Companion docs:
[`JARVIS_SPRINT_3_FINDINGS.md`](JARVIS_SPRINT_3_FINDINGS.md) (Phase-0 architecture),
[`JARVIS_SPRINT_3_TELEMETRY.md`](JARVIS_SPRINT_3_TELEMETRY.md). Rig evidence captured on the
live, awake Tauri app (tauri-mcp; `caffeinate -dimsu` held the display awake the whole pass),
dark + populated + REAL data, via OpenRouter → Claude Sonnet 4.6._

---

## 0. Honest self-assessment — does research now SHOW instead of tell, and does it feel like JARVIS?

**Yes, materially — and it's rig-proven on real live runs, not mocked.** The research ENGINE was
already world-class; this pass fixed the PRESENTATION, and the headline is now true: ask "research
NVDA" and a **typed-block visual brief** lands at the top of the cockpit — a price hero with a
color-coded change, a **metric-card grid** (market cap / P-E / fwd P-E / PEG / P-B / beta / volume)
from live yfinance data, a Snapshot table, an Investment Thesis, cited sources — with the chart
loaded beside it. The chat reply collapsed to a one-line pointer ("Built you a brief on NVDA…").
Ask "research the top 10 India stocks" and you get a **clickable comparison table** of all ten
NSE blue-chips in INR with sectors and 6-month change — every ticker a live chip. Clicking a chip
drives the chart. Nothing dumped a wall of asterisks; the depth lives in the rendered brief, and
the terminal connections are the thing Perplexity Finance can't do.

**Why it holds up (the architecture bet):** every visible surface is **deterministic, not
model-dependent**. The brief AUTO-PUBLISHES from the research result (the runtime emits the
host-action — it doesn't wait for a weak model to call `publish_brief`); the typed blocks are
DERIVED on the frontend from the data; the chat COLLAPSES whenever a brief publishes regardless of
how verbose the model is. So "show, don't tell" survives the unreliable local model and steps up on
a capable one — which is exactly what the rig showed on Claude Sonnet.

**Act-first is fixed:** "research NVDA" and "research top 10 India stocks" both ACTED immediately —
resolved, pulled data, arranged the cockpit, published the brief — with no "what do you mean?"
stall. The India query even decomposed itself (screener → resolve each → fundamentals + price for
the top 10 in parallel).

**Where it's honestly not 100%:** (1) the FAST brief's PROSE is still the model's job (the FAST
research tool returns data, not narrative), so on a model that ignores the prompt the brief shows
metric cards + table but a thinner narrative — the metrics never depend on the model, the prose
does; (2) Tongyi-DeepResearch remains **listed-but-unrouted on OpenRouter** (0 endpoints,
re-confirmed live this pass) so the deep-engine selector + probe ship + honestly report the
Qwen3-A3B fallback — the UI is real and honest, the upstream model just isn't routing yet; (3)
clicking an Indian `$TICKER` chip loads the bare symbol — the chart's `.NS` resolution is a
data-layer follow-up, the chip + command channel are proven.

**The spine held: every track is additive, the §6.5 audit is 9/9, the Tier-1 LOCKED files are
byte-for-byte untouched, and every fork kept a working fallback.**

---

## 1. Per-track — shipped + rig evidence

| Track                                       | Shipped                                                                                                                                                                                                                                                                                                                           | Rig evidence (live, populated, real data)                                                                                                                                                                                                                                                                                                                                                  |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **1 — visual typed-block brief**            | `brief-blocks.tsx`: `BriefBody` renders a metric-card grid (`deriveMetrics` from `structured`, color-coded green/red) + heading/prose/list/**table** blocks parsed from the synthesis markdown. `structured` threaded through the brief contract. The old markdown-dump renderer is gone (the block parser is a strict superset). | **RIG-VERIFIED:** the live NVDA brief rendered the metric-card grid — NVDA chip + `222.82` + green `▲ +1.02 (+0.46%)` + YFINANCE/EOD badges, then MARKET CAP 5.40T · P/E 34.12 · FWD P/E 17.64 · PEG 0.69 · PRICE/BOOK 34.43 · BETA 2.24 · VOLUME 192.21M; Snapshot table; Investment Thesis; Sources(10). The India brief rendered a dense INR comparison table of all 10 NSE blue-chips. |
| **2 — clickable connections**               | Every ticker = a live chip → `loadSymbolIntoChart` (the always-consumed chart-command channel; fit-aware, no panel-per-click). Detection: `$CASHTAG` + the known-set (resolved/watchlist/structured) — precise, no false positives.                                                                                               | **RIG-VERIFIED:** clicking the NVDA chip fired the chart-command (`seq 2→3`, symbol NVDA, `fired:true`); the chart panel consumes it. The India brief's 10 company tickers all chip (RELIANCE/HDFCBANK/TCS/…). The chart auto-loaded RELIANCE.NS via NSE.                                                                                                                                  |
| **3 — short chat + act-first**              | Deterministic brief auto-publish in the runtime; the chat collapses a published-brief reply to a ~220-char lead + "show full analysis" toggle; copilot prompt biases act-first + replies short + writes `$TICKER` cashtags.                                                                                                       | **RIG-VERIFIED:** the NVDA chat reply collapsed to "Built you a brief on NVDA… **$NVDA @ $222.82** (+0.46%) — ~$5.4T market cap." + toggle. Both queries acted with no clarifying-question stall; the India query decomposed into screener + per-stock fundamentals.                                                                                                                       |
| **4 — fit-aware arrangement**               | `fitLayoutTemplate` downgrades panel-heavy templates below a width threshold (research-cockpit → chart+brief essentials; macro-scan → single-focus); `viewport` added to the `__terminal__` snapshot + prompt guidance.                                                                                                           | Unit-verified (4 fit tests: wide keeps research-cockpit; narrow → chart+brief essentials; macro-scan → single-focus; width-0 → no downgrade). On the rig's 2560×1664 display the full research-cockpit correctly applied (no downgrade).                                                                                                                                                   |
| **5 — deep-engine selector + Tongyi probe** | Settings "Deep research engine" card (Native / Tongyi, opt-in + BYOK, never auto-selected); live `GET /system/deepresearch/probe`; selection threaded to the deep_research tool via a config ContextVar.                                                                                                                          | **RIG-VERIFIED:** the Settings card rendered both engines + the live probe honestly read **"using fallback · Tongyi unavailable on OpenRouter right now — using qwen/qwen… · ~$0.03/run"** (the OpenRouter key resolved the probe live).                                                                                                                                                   |

## 2. Fallbacks taken (every fork kept a working path)

1. **Typed blocks FRONTEND-DERIVED, not LLM-emitted** — the frontier ideal (model emits a typed
   block array) is fragile on a weak model; deriving blocks from the data is robust on every model,
   and the markdown body is the guaranteed fallback.
2. **Brief auto-publish, not model-only** — the runtime publishes deterministically so a weak model
   that never calls `publish_brief` still gets a brief; the model's own publish is idempotent.
3. **Metric cards via seed-then-merge** — FAST returns no markdown, so the auto-publish seeds
   `structured` and `briefFromInput` preserves it across the model's prose-publish (rather than a
   fragile single path).
4. **Tongyi → honest Qwen-A3B fallback** — the slug is unrouted; the probe + runtime resolve to the
   live fallback and SAY so (no silent pretend).
5. **Ticker chips: precision over recall** — `$CASHTAG` + known-set only (a wrong chip loading a junk
   symbol is worse than a missing one); the prompt nudges `$TICKER` for broad coverage.
6. **Dividend-yield correctness guard** — drop an implausible (≥25%) yield rather than show the known
   yfinance unit-quirk value on a trust surface.

## 3. Gates (the floor)

- **§6.5 safety audit: 9/9** (`test_safety_end_to_end.py`, 9 passed, ~30s).
- **Tier-1 LOCKED files vs base `2397260`: EMPTY diff** (`types/plugin.ts`, `types/safety.ts`,
  `types/broker.ts`, the safety/broker/audit/kill-switch models, `broker_base.py`,
  `kill_switch.rs`, `test_safety_end_to_end.py`, `tauri.conf.json`, CI).
- **No new pip dependency** — the probe uses the shipped `httpx`; the block deriver + auto-publish
  are pure stdlib + existing modules. No PyInstaller `--copy-metadata`/`--collect-data`/`--add-data`
  exposure.
- **Orders never auto-apply** — the auto-publish emits only `publish_brief` (a UI mutation); the
  order exclusion in `proposed-changes` is untouched; the live PENDING-in-AUTO behavior survives.
- **Secrets** — the OpenRouter key rides the probe header / foreground request only, never logged,
  echoed, or persisted (asserted by `test_deepresearch_probe_never_echoes_the_key`); never extracted
  to the shell.
- **Sidecar rebuilt + smoke-tested** — `smoke-test-sidecars.mjs`: PASS (all sidecars boot cleanly;
  proves the new auto-publish + probe + backend-ContextVar code RUNS in the shipped `--onefile`
  binary, not just under pytest; MCP children bound).
- **`pnpm ci-local`** (full CI mirror): **PASS** (875 vitest, 8 cargo, 1326 pytest; see §5).

## 4. Rig evidence (live, awake, populated)

Captured on the live Tauri app (`tauri dev --features dev-tools`), display held awake with
`caffeinate -dimsu`; all shots dark, populated, REAL data via OpenRouter → Claude Sonnet 4.6
(autonomy AUTO). Sequence:

1. **Track 5 — Settings "Deep research engine":** both engines rendered (Native selected; Tongyi
   opt-in), probe read "using fallback · Tongyi unavailable on OpenRouter right now — using
   qwen/qwen… · ~$0.03/run". Default model Claude Sonnet 4.6 (343 tool-capable); region India.
2. **"research NVDA":** live trace (resolve → 4/4 data sources → 6 web sources → synthesize) →
   chart loaded NVDA (yfinance EOD) → the **metric-card brief** auto-published (after the
   metric-card + chip-precision + div-yield-guard fixes) + short chat ("$NVDA @ $222.82 (+0.46%)…").
3. **Chip click:** clicking the NVDA chip bumped the chart-command (`seq 2→3`, symbol NVDA).
4. **"research the top 10 India stocks":** decomposed (screener → resolve → fundamentals/price ×10)
   → chart loaded RELIANCE.NS via NSE → a **clickable INR comparison table** of all 10 blue-chips
   (RELIANCE/HDFCBANK/TCS/BHARTIARTL/ICICIBANK/INFY/SBIN/LICI/HINDUNILVR…) with sectors + 6mo change.

_(Per the rig wake-path rule: `list_windows` timed out once during a next-dev recompile; the
caffeinated display + a focus + a bounded wait recovered the bridge each time — no black-screen
loss.)_

## 5. Verification snapshot + what's left running

- **Branch `002-jarvis-intelligence`**, coherent per-track commits (Phase-0 findings; Track 1+2;
  Track 3; Track 4; Track 5; rig-driven refinements; this report). Not merged to main; version
  untouched.
- **`pnpm ci-local`: PASS (exit 0)** — the full CI mirror green end-to-end: install
  `--frozen-lockfile` → ensure-all-sidecars → eslint → prettier → tsc → cargo fmt → clippy
  `-D warnings` → ruff → **875 vitest (112 files)** → **8 cargo** → **1326 pytest (1 skipped)**.
- **`smoke-test-sidecars.mjs`: PASS** on the rebuilt binary.
- App + rig **left running, display kept awake** (`caffeinate -dimsu`).
