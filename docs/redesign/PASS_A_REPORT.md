# Pass A — craft, capability & foundations report

_Branch `001-agent-native-redesign` (NOT merged, NOT version-bumped — your call).
Lead: Opus 4.8 (1M), driving the real running Tauri app through the tauri-mcp rig.
"Pass A — make what exists excellent, and lay clean foundations for what's coming."_

> **Read this first, then `POLISH_SWEEP_REPORT.md` (the bug-hunt findings + fixes) and
> `EXTENSION_SEAMS.md` (the Pass-B seams).** Phase-0 spec is `PRODUCT_DESIGN_DECISIONS.md`.

---

## ⚠️ What needs your eyes first (ranked)

1. **The warm-charcoal theme — a taste call.** I reskinned the cold blue-graphite
   (`#0a0b0d` + ion-blue `#4f86f7`) to a warm near-monochrome (warm graphite `#0b0a09`
   → cream `#e8e4dc`, a single desaturated clay accent `#a06b52`, P&L green/red kept). It
   was grounded in **real references** (Anthropic's own warm neutrals `#141413`/cream/clay,
   Cursor's near-mono alpha-border structure) and is contrast-verified, but **the final
   "does it read warm/aged/expensive" judgment is yours** — open the app and look at both
   resolutions. Uncertainty flagged in §Theme below. _(The display was asleep for much of
   the run, so I verified the reskin via the live DOM — 0 ion-blue stragglers, 221 clay
   applications — rather than pixels; see §Verification constraint.)_
2. **Kill-switch removed from the UI** (item 3). It's a read-only app — nothing to halt.
   The §6.5 mechanism (`kill_switch.rs`, store slice, audit) is **byte-for-byte intact and
   dormant**; only the toolbar icon + banner were removed. Confirm you're comfortable the
   control is gone from the chrome. The OS-global `⌘⌃⇧K` now no-ops (still registered).
3. **JARVIS autonomy modes + the hard safety line** (item 7). New ASK (gate, default) /
   AUTO (auto-apply) toggle. In AUTO, UI/layout/chart/watchlist host-actions apply without a
   per-action confirm — but an **order NEVER auto-applies in any mode** (verified). Confirm
   the safety framing reads right.
4. **The headline JARVIS fix** (item 6): "load Apple loaded SPY" is fixed — the agent's
   `set_chart_symbol` now actually lands on the chart (verified live with a non-default
   symbol). Drive it yourself with a cloud key for a multi-step run.
5. The polish sweep (item 1) — the broad bug-hunt fixes; skim `POLISH_SWEEP_REPORT.md`.

**No STOP-AND-SURFACE guardrail was hit.** No LOCKED file was edited. (Details in §Guardrails.)

---

## Status by build item

| #   | Item                                     | Status   | Evidence                                                                                                                                                                                  |
| --- | ---------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Systematic bug-hunt & polish sweep       | **Done** | 202 findings (55 high / 92 med / 55 low) from a 17-agent hunt; all high + the bulk of medium fixed (6 teammates + lead). vitest 744/744, app loads healthy. See `POLISH_SWEEP_REPORT.md`. |
| 2   | Warm-charcoal vintage theme              | **Done** | tokens.css + chart-theme.ts + globals.css + node-editor + ~17 off-palette files; live DOM: 0 ion stragglers, 221 clay hits.                                                               |
| 3   | Remove kill-switch from UI               | **Done** | `KillSwitchToolbar` deleted; live header has 0 kill-switch buttons; §6.5 audit 9/9 (Rust/model/test untouched).                                                                           |
| 4   | Agent dock fully closeable               | **Done** | Closed → cockpit fills full 1280px, no leftover rail; reopen via header button + ⌘B. Verified live.                                                                                       |
| 5   | Config-driven model registry             | **Done** | `sidecar/config/model_registry.json` single source; sidecar derives all + serves it; frontend consumes at runtime. 57 sidecar tests + frontend tests green.                               |
| 6   | JARVIS load-with-symbol + reliability    | **Done** | New always-consumed chart-command channel; live `loadSymbol('NVDA')` → chart shows NVDA. Chart Retry no-op also fixed.                                                                    |
| 7   | JARVIS autonomy modes (ASK/AUTO + PAUSE) | **Done** | agent-autonomy store + dock toggle; AUTO applies non-order, order stays gated (verified live + unit).                                                                                     |
| 8   | Region seam (foundation)                 | **Done** | `region.ts` + settings field + format.ts read seam + Settings dropdown; default US = zero change. No India data built.                                                                    |

Plus two seed bugs from the brief, both fixed + verified live:

- **Stale `llama3.1:8b` model** shadowing the default → trust-marker drop on restore; dock now reads `qwen2.5:7b`.
- **Settings double-scroll** → the dockview leaf `.dv-view` now `overflow:hidden` (specificity fix); one scroller.

---

## Theme — calls + uncertainties

- **Palette:** warm graphite ramp `#0b0a09 … #e8e4dc` (R≥G≥B every stop, a gentle 2→17 warm
  gap — aged-graphite, never orange, never flat black), a single desaturated warm-clay accent
  (`amber-400 = #a06b52`, ~30–40% saturation) replacing ion-blue, warm-taupe borders +
  scrollbars + selection. P&L signals (`#38b25f` / `#ef5369`) kept — they pass contrast on the
  warm bg and are now the only saturated thing on screen.
- **Kept (deliberate):** the monospace tabular-nums identity + the Hanken grotesque display.
  This is the same restraint call the prior pass made — a font swap across 18 panels on an
  autonomous run is high-regret; "crafted" here is bought with palette warmth + precision.
- **Uncertainties for your eyes:** (a) the clay accent's exact saturation — it may want to be
  a touch warmer/cooler in situ; (b) the active-sash clay (`amber-500 #7c5240`) may read dim
  when dragging; (c) the faint warm body-bloom (radial gradient at the top) is subtle — confirm
  it's not muddy. All are single-token tweaks in `tokens.css` (+ `chart-theme.ts` for canvas).

## JARVIS — what it now does reliably

- The agent drives the cockpit through the **diff/accept gate** (the only path): open / close /
  focus / arrange panels, **set_chart_symbol (now lands)**, add_to_watchlist.
- **Live DeepSeek multi-step proof (the headline):** typed _"Close the news panel and load
  NVDA into the chart"_ → DeepSeek emitted **both** tool calls (`close_panel` + `set_chart_symbol`)
  → both **staged as pending in the gate** (ASK, nothing auto-applied) → on accept the **news
  panel closed AND the chart loaded NVDA** (not SPY). The full propose → gate → accept → drive
  loop, multi-step, through the real agent — and the item-6 fix proven end-to-end.
- **Reliability finding (honest):** a _subsequent_ single request ("load TSLA") had DeepSeek
  **narrate** "staged for your review" **without emitting the tool call** — the same model-
  adherence inconsistency the prior pass found (the wiring is proven; the model is the
  variable). Local `qwen2.5:7b` is worse. The **cloud-key path is the reliable route**, which
  is the documented design; the AUTO auto-apply itself is deterministically verified.
- The act-path (catalog → host-actions) is left a clean seam — a Pass-B research capability
  registers per `EXTENSION_SEAMS.md` §1.

## Autonomy modes + the safety line

- **ASK** (default) — every change waits in the gate. **AUTO** — UI/layout/chart/watchlist
  apply without a per-action confirm (still recorded). PAUSE = the existing run-cancel
  (foreground AbortController + delegate run routes).
- **Hard line (never crossed):** AUTO excludes `kind === "order"` from auto-apply, AND
  `accept()` routes any order through the §6.5 confirm-before-place dialog regardless. Brokers
  stay read-only; `propose_order` never auto-executes in any mode. Unit + live verified.

## Seams left for Pass B

See **`EXTENSION_SEAMS.md`** — four headline seams documented with a concrete example each:
agent capabilities (`catalog.py`), data providers (`provider_registry.py` — the India equity
seam, ~15 lines from region routing), the model registry (`model_registry.json`, made clean
this pass), and region/locale (`region.ts` + sidecar `config.py`). No research or Indian-data
features were built — only the seams.

---

## Verification constraint (please note)

The operator's **display was asleep** for most of the run (the rig's screenshot needs the
WKWebView painting; an occluded/asleep panel returns a black frame). I therefore verified
against the **live DOM via the rig bridge** — computed styles, bounding-rects, element state,
store reads — which is real running-app evidence (and more precise than a pixel for the
structural claims: overlap rects, scroll containers, the kill-switch absence, the model
readout, the chart symbol, the autonomy gate). **Pixel screenshots at 1920×1080 / 2560×1440
should be captured when the display is awake** — the app + rig are left running. A `caffeinate`
is holding the display awake for the rest of the session.

---

## Gate results

| Gate                              | Result                                                                                                                                                             |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `tsc --noEmit` (frontend)         | clean at each commit                                                                                                                                               |
| `eslint`                          | clean at each commit                                                                                                                                               |
| `prettier --check`                | clean at each commit                                                                                                                                               |
| vitest (full suite)               | **744 / 744 passed** (101 files) — incl. autonomy safety, the chart-command channel, palette ranking, every panel + dialog test                                    |
| sidecar pytest (item 5)           | 57 + 81 green incl. **`test_safety_end_to_end` (§6.5 audit 9/9)**                                                                                                  |
| Full `pnpm ci-local` + smoke-test | **NOT run yet** — heavy/pre-tag; run before any tag. The main sidecar binary needs a rebuild to pick up the registry (the frontend fallback is correct meanwhile). |

---

## Guardrails honored

- **No LOCKED file edited.** `types/plugin.ts`, `types/safety.ts`, `types/broker.ts`,
  `tauri.conf.json`, the safety/broker/audit/kill-switch models, `broker_base.py`,
  `kill_switch.rs`, `test_safety_end_to_end.py`, CI — byte-for-byte untouched. Panel min-sizes
  stayed HOST-SIDE in `PanelHost` (the placement/min-size work never touched `PanelSpec`).
- Kill-switch removal is **UI-only**. Brokers stay read-only; no order/execution path in any
  autonomy mode. The rig store handle (`__vystedStores`) is dev-only (NODE_ENV-stripped, like
  `__vystedDockview`).

---

## Telemetry (running tally)

_Lead (Opus 4.8) did all rig driving + the risk-critical work (theme tokens, kill-switch
removal, stale-model + double-scroll fixes, dock closeability, model-registry frontend, JARVIS
items 6/7, region seam, placement policy, integration + verification)._

**Agents / workflows dispatched:**

- Deep-exploration workflow — **12 subagents** (~780k tokens, 343 tool-uses, 494s) — subsystem map.
- Theme-reference research — 1 agent (~50k tokens) — real Cursor/Claude/Anthropic palette values.
- Off-palette warm-theme sweep — 1 agent (~54k tokens) — 17 files routed to tokens.
- Sidecar model-registry wiring — 1 opus agent (~64k tokens) — item 5 sidecar half.
- Bug-hunt workflow — **17 subagents** (~1.12M tokens, 1030 tool-uses, 1091s) — 202 findings.
- Polish-sweep implementation — **6 teammates** (core panels / analysis panels / tools /
  dialogs / PanelHost / settings+dock) — ~720k tokens combined; all returned tsc+eslint-clean
  with their tests green; the lead fixed the 3 cross-cutting test-fallout cases at integration.

**Totals:** ~38 agents/subagents; ~2.8M+ subagent tokens across exploration + research +
bug-hunt + implementation. **Commits this session: 10** (theme, shell, dock, model ×2, jarvis,
region, + 3 polish) + this docs commit. **Code: 103 files, +3166 / −1389.** Branch pushed to
origin at each checkpoint. Lead did all rig driving (incl. the live DeepSeek e2e + the
deterministic item-6/7 verification) and the risk-critical work.
