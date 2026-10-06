# Vysted Rebuild — Round 3 Report (from-scratch experience rebuild + full audit)

> **Branch:** `003-vysted-rebuild` · **Version:** `0.8.0` (no bump) · **Started:** 2026-06-04
> **Mode:** one continuous autonomous run (ultracode / dynamic workflow orchestration).
> This report is built incrementally and is **brutally honest by mandate** — a real flagged
> bug is worth more than a clean-looking report. Status is tracked in three buckets:
> **VERIFIED WORKING** (driven, not asserted) / **STILL BROKEN** / **NEEDS LOKAVYA'S MANUAL CHECK**.

---

## 0. Safety floor — the sacred baseline (re-checked at every milestone)

| Gate                | Baseline (run start)      | Method                                                                                     |
| ------------------- | ------------------------- | ------------------------------------------------------------------------------------------ |
| §6.5 safety audit   | **9/9 PASSED** (30.28s)   | `sidecar/.venv/bin/python -m pytest sidecar/tests/test_safety_end_to_end.py -v` → 9 passed |
| Tier-1 LOCKED files | untouched (byte-for-byte) | enforced; re-diffed before each commit                                                     |
| Version             | `0.8.0` everywhere        | no bump                                                                                    |

The 9 audits: paper-default, no-bypass-to-place, position-limit, append-only-DB, kill-switch<2s,
AI-order-gate, read-only-mode-raises, disclaimer-flow, static-ip-detection. **This must read 9/9
at every milestone — it is the floor.**

---

## 1. Environment baseline (recon, run start)

- **App was running** (PID 13766, release bundle) but with a **DEAD sidecar** — no python
  process, no listening sidecar port. The running instance could not serve fresh data; live
  verification requires a sidecar rebuild + full relaunch (which this run does).
- **BYOK keys exist in the keychain** (4 `vysted-terminal` entries). Values are never read to a
  shell — so keyed model/research verification is driven **through the live app** (keychain →
  per-request header → sidecar), never by curling a provider with an extracted secret.
- `sidecar/.venv` has the deps; the safety audit + pytest run from there.
- Verification path (from `sidecar-client.ts`): a plain browser fallback honours
  `?sidecar-port=NN` (gated on absence of `__TAURI_INTERNALS__`). So **Playwright** drives the
  web build at `localhost:3000/?sidecar-port=NN` for data/UI surfaces with trusted events; but
  the **keychain `invoke` only works inside the real Tauri webview**, so keyed deep-research runs
  - native menus are driven via the **tauri-mcp rig** against the real app, screenshots via Quartz.
- Mac kept awake for the whole run (`caffeinate -dimsu`).

---

## 2. Lead's independent ground-truth (read the code myself — not trusting prior summaries)

Cross-checked against the Phase-0 evaluator agent (§3). Confirmed by direct read:

- **Composer (`src/modules/chat/ChatSidebar.tsx`, 1495 lines):** the Mode/Lens/Provider/Model
  stack (`ModeBar` + `RosterStrip` + `AgentHud` + `BudgetConfig`) is **hidden behind a
  `controlsOpen` disclosure** (state at :280, rendered :957-1000 behind a `SlidersHorizontal`
  gear). This is the **Round-2 "hide ≠ rebuild" failure verbatim** — the #1 thing to rebuild.
  Counter to the brief's narrative, several pinned bugs _appear already fixed in code_:
  enter-to-send is explicit (:1344-1349), agent spaces exist (:802-847), the slash/mention picker
  opens **upward** and is height-capped (:1354-1370). These are **claims to verify live**, not to
  trust — flagged accordingly.
- **Command palette (`src/components/CommandPalette.tsx`):** a flat fuzzy-ranked list with a
  `KIND_WEIGHT` nudging commands/panels above agents — **not grouped, not scoped**, symbols mixed
  inline as noise. Needs the Raycast-grade grouped + scoped + AI-ask rebuild (Pillar C).
- **Notes (`src/modules/notes/NotesPanel.tsx`):** a plain `<textarea>`. Confirms the Tiptap rebuild.
- **Settled-fix locations (confirmed):** stale label at `ScreenerPanel.tsx:18`
  (`sp500: "S&P 500 (Top 100)"`); Tongyi/"fallback" deep-research section at
  `SettingsPanel.tsx:805-933` + `settings.ts` `DeepResearchBackend = "native" | "tongyi"`;
  StatementTable duplicate-key at `EquityOverviewPanel.tsx:209` (`<tr key={line.label}>`).

---

## 3. Phase 0 — fresh research + ruthless stale-code audit

**Done.** 14 agents (~1.0M tokens, 462 tool-uses, ~20 min) → `docs/redesign/REBUILD_R3_SPEC.md`
(855 lines, a decision document with exact file:line targets, a 21-commit build sequence,
a failure-mode guardrail table, and a verification runbook). The **stale-code register** (the
operator's #1 ask) enumerates 8 surfaces with exact remediations — headline items: the
`"S&P 500 (Top 100)"` label vs the real 506-symbol universe; the **entire Tongyi/"fallback"
deep-research backend** (dead module + EngineOption + probe + "using fallback" strings + tests +
CLAUDE.md narration — delete end-to-end, not relabel); the **Round-2 disclosure composer**
(controls hidden behind a `SlidersHorizontal` gear) + a **second redundant persona picker**
(`RosterStrip` vs `AgentsRail`); dead files (`PlaceholderPanel.tsx`, `ConnectCard.tsx` +
`lib/integrations/*`); four-mode strings on a two-mode system; warm-clay token drift in
`globals.css`; dual slash-command systems.

My critical adjustments to the spec before execution (verified against code, not trusted):

- The spec claims **cmdk is "already in the stack via shadcn/ui"** — it is **NOT** (no
  `components/ui/command.tsx`, `cmdk` absent from `package.json`). cmdk + mathjs + Tiptap all
  need `pnpm add`. Noted; Pillars C/F/G install them.
- Dead-file deletes verified by import-check: `ConnectCard` is imported nowhere (the live module
  is `broker-connect`); `PlaceholderPanel` has zero usages. Safe.

## 4. Research-model decision (live-confirmed)

**Decision (with a hard verification gate).** Registry default today is `minimax/minimax-m3`
(`model_registry.json:61`) but onboarding force-sets `deepseek/deepseek-v4-flash`, so a new user
already effectively runs v4-flash. The R3 serving research re-classifies `deepseek-v4-flash` as
**non-thinking-by-default** (cheapest/fastest genuinely-served, 14+ providers, 3T+ weekly tokens)
— but this **contradicts the prior spec** which called it a hang-risk reasoning model. I will not
resolve a factual model-behavior dispute from listing pages.

**Robust path:** ship the swap to `deepseek/deepseek-v4-flash` _with_ the universal mid-call wall
guard (so a hang is impossible by construction regardless of who's right), then let the
**authoritative keyed completion through the live app** (verification step 15) arbitrate. If
v4-flash exhibits a thinking-phase hang or tool-schema errors in the live finance loop, the
documented one-line swap-down is `minimax/minimax-m3` (both research passes agree it's
non-thinking, serving, purpose-built agentic). POWER deep-research = `deepseek-v4-pro` with
thinking explicitly disabled; TOOL-CALLER = `moonshotai/kimi-k2.6`. **Status: NEEDS live keyed
confirmation** (flagged, not asserted).

## 5. Per-pillar — what shipped

Commit-by-commit (branch `003-vysted-rebuild`, no merge, version 0.8.0 throughout):

1. **`chore(cleanup)`** — deleted dead files (`PlaceholderPanel`, `ConnectCard`, `lib/integrations/*`), import-verified.
2. **`fix(deep-research)`** — deleted the **Tongyi backend end-to-end** in the sidecar (module, `_run_tongyi`, dispatch, catalog enum, `/deepresearch/probe` route, reference candidates re-neutralized to a generic 30B-A3B MoE, orphaned key-ContextVar plumbing, tests). Kept `iter.py`'s honest IterResearch _algorithm_ attribution (not the dead backend).
3. **`fix(settings)`** — native-only deep research; removed the Tongyi `EngineOption`, the routing probe, and every "using fallback"/Qwen-A3B string; narrowed `DeepResearchBackend` → `"native" | "perplexity"` (legacy `tongyi` blobs coerce to native).
4. **`feat(models)`** — default OpenRouter → `deepseek/deepseek-v4-flash` everywhere (resolves the registry-vs-onboarding collision); `minimax/minimax-m3` kept as the documented swap-down; `MODEL_OVERRIDES_VERSION` 2→3. **Final default pending the live keyed test** (§4).
5. **`feat(research)`** — universal mid-call wall guard in `_safe_llm` (`asyncio.wait_for`, 60s) so a hang is impossible for any swapped-in model; regression test.
6. **`fix(equity)`** — statement rows keyed by `label+index` (the duplicate-key crash / likely "6 Next.js errors", FM-11).
7. **`fix(screener)`** — honest **"S&P 500"** label (was "S&P 500 (Top 100)"; the universe is 506).
8. **`fix(chat)` — Pillar A composer rebuilt inline.** Killed the disclosure gear; Mode/Lens/Provider+Model/Autonomy/Deep are all always-visible; deleted orphaned `ModeBar.tsx`; preserved the 5 bug fixes + spaces. 12 tests pass.
9. **`fix(research)` — the keyless 0-sources bug (Pillar E / FM-12).** Root-caused + reproduced: a FAST research strands its web round under `web.{citations,results}` and `_auto_publish_event` read only `payload['sources']` → published 0 sources despite DDG returning 6 real results. Fixed to map the FAST web round into brief sources. **Verified LIVE keyless:** `gather_fast('NVDA'|'AAPL')` → 6 real sources (yahoo/marketbeat/stockanalysis/apple.com), `web_available:true`. Regression tests added.

**Evaluator false-positive caught (verified against code):** the stale-code register claimed `AgentsRail` and `RosterStrip` are "two persona pickers, merge them." Direct read shows `AgentsRail` is the **running-delegate-runs rail** (status/cost/cancel/answer) — not a persona picker. Both kept; one persona picker surfaced inline. Logged here so the register isn't trusted blindly.

_(Pillars B/C/F/G + E-presentation-deepening + H-polish: in progress / see §6 buckets.)_

## 6. Verification — DRIVEN, not asserted

The fresh sidecar was **rebuilt** (`ensure-all-sidecars` → main `vysted-sidecar` rewrote
`src-tauri/binaries/`; MCP sidecars fresh) and **smoke-tested green** (boots, `/health`,
MCP subprocesses survive). The stale release app was killed and the dev app relaunched
(`tauri dev --features dev-tools`) so the **freshly-rebuilt --onefile binary is the one
running** — sidecar live on `127.0.0.1:54977`, `version:0.8.0`, status `ok`. Then driven
three ways (the VERIFICATION_STACK tiers):

**Sidecar (direct `curl`, definitive):**

- `GET /system/deepresearch/probe` → **404** — the Tongyi probe route is gone in the running binary.
- `GET /screener/universe?id=sp500` → `label:"S&P 500", count:506` — the honest label + full universe are live.
- `GET /fundamentals/AAPL` → `provider:yfinance, roe:1.41, dividend_yield:0.0035 (≈0.35% — the fraction unit is CORRECT, not 35%), profit_margin:0.27` — populated + the unit fix holds.

**Sidecar (function-level, the 0-sources fix):** ran the real keyless DDG floor + the real FAST
loop + `_auto_publish_event`. Before: `gather_fast('NVDA'|'AAPL')` → publish carried **0 sources**
despite DDG returning 6 results. After: **6 real sources** (yahoo/marketbeat/stockanalysis/apple.com),
`web_available:true`. Reproduced AND fixed AND re-verified, keyless.

**Web UI (Playwright, trusted `isTrusted` events @ `localhost:3000/?sidecar-port=54977`):**

- **Composer rebuilt inline (Pillar A)** — the accessibility snapshot shows Mode tabs (Agent/Delegate),
  the "Lens" persona combobox (all 13 personas), Deep-research toggle, ASK/AUTO autonomy, and the
  Provider/Model HUD **all always-visible, with NO "Agent controls" disclosure gear**.
- **Clickable company overview populated** — clicking the AAPL chip loaded "Apple Inc. · 310.68 USD ·
  −1.05% · YFINANCE" + the VALUATION grid (Market cap 4.56T, P/E 37.66, Fwd P/E 32.34, PEG 2.53, P/B 42.79).
- **No React duplicate-key warning** in the console on the overview render (the statement-key fix holds).
  The 8 console errors are all environmental/expected (dev `favicon` 404, six unconfigured-broker
  `/plugins/*/config` 404s, and the documented Tauri-`invoke`-undefined-in-Chromium keychain limitation) —
  none from R3 changes.

**Native WKWebView (the rig `evaluate_script`, the real Tauri app — supplemental #2):**
`{hasComposerModeTabs:true, hasPersonaRoster:true, hasDisclosureGear:false}` — the disclosure is
gone in the **real native app**, not just the browser build. Native screenshot
(`verification/r3-native-fullscreen-LIVE.png`) shows the rebuilt composer + the macOS **Layout** menu
present in the menu bar. Evidence: `verification/r3-composer-inline-LIVE.png`,
`r3-overview-aapl-LIVE.png`, `r3-native-fullscreen-LIVE.png`.

### Three buckets (a real flagged item beats a clean report)

**✅ VERIFIED WORKING (driven live):**

- Composer rebuilt inline, disclosure gone — Playwright + native rig + native screenshot.
- Tongyi backend deleted end-to-end — `/deepresearch/probe` 404 live; `rg -i tongyi src sidecar` clean except `iter.py`'s algorithm citation.
- Screener universe honest "S&P 500" / 506 — live API + the frontend label.
- Fundamentals populated + dividend-yield fraction unit correct — live API.
- The keyless **0-sources bug FIXED** — reproduced + fixed + re-verified with real DDG sources.
- Clickable company overview populated from a ticker click; statement render has no duplicate-key crash.
- Mid-call wall guard — unit-proven (a slow call aborts to empty, never hangs).
- §6.5 audit **9/9** at every milestone (re-run after each sidecar cluster); Tier-1 LOCKED files byte-untouched; version 0.8.0; no merge to main.
- Full frontend vitest **898 green**; sidecar test subsets green; smoke-test green.

**❌ STILL BROKEN / NOT BUILT THIS RUN (honest):**

- **Pillars C (⌘K Raycast-grade), F (Tiptap notes), G (screener formula grammar)** — _authored_ as
  integration-ready drafts by a codegen workflow (saved in this run's transcript), but **NOT integrated
  or verified**. The cmdk/Tiptap/mathjs deps are not installed; the ⌘K draft references a
  `@/store/agent-command` seam that must be created. Leaving them un-wired is the honest state — do not
  read them as shipped.
- **Pillar E research deepening beyond 0-sources** (sources rail, inline `[n]` tooltips, follow-up chips,
  storyline, real screener-grade brief tables) — not built.
- **Pillar B AI-narrative section + brief-chip/⌘K entry points** — the clickable seam + screener/watchlist
  wiring shipped; the AI-narrative synthesis section and the remaining entry points are not.
- **Pillar H** (token re-value of the warm-clay `globals.css` fallbacks, AI-native motion, numeric typography) — not built; the indigo accent is already shipped.
- **The "agent asks a clarifying question on an ambiguous free-text query"** (FM-7 deeper form) — the
  @-mention picker already shows candidates, but wiring `needs_disambiguation` into the agent's
  free-text turn needs sidecar agent-context changes — not done.

**⚠️ NEEDS LOKAVYA'S MANUAL CHECK (could not fully verify):**

- **The research-model default (`deepseek/deepseek-v4-flash`)** — the authoritative serving check is a
  **keyed chat completion through the app**, which needs an OpenRouter key in the keychain (the browser
  build can't read the keychain; the keyed path runs only in the native app). I did **not** confirm a
  live keyed completion. If it mis-behaves (thinking-phase slowness / tool-schema errors), the one-line
  swap-down to `minimax/minimax-m3` is staged. **Flagged, not asserted.**
- **The macOS Layout menu modes** — the menu is **present** in the native menu bar (screenshot), but
  clicking each mode needs native Computer Use (not available to the rig, which can't drive native menus).
  Not click-verified.
- **Screener row → overview drill, live populated** — the seam + wiring shipped and typecheck/test-pass,
  but a live click-through needs a warm screener run (cold 506-symbol fundamentals fetch is slow); not
  driven end-to-end live.
- **A live keyed deep-research run rendering a brief with real sources in the UI** — verified the plumbing
  keyless at the sidecar layer; the full keyed UI round-trip needs a key + the native app.

### Evaluator false-positives caught (don't trust the register blindly)

- "Merge the two persona pickers (`AgentsRail` vs `RosterStrip`)" — **wrong**: `AgentsRail` is the
  running-delegate-runs rail, not a persona picker. Kept both; one persona picker surfaced inline.
- "Chart 502 needs a Retry button" — **already present** (`ChartPanel.tsx:1196-1203`, `retryNonce`).
- "cmdk already in the stack via shadcn/ui" — **false**; cmdk is absent (`pnpm add` required for Pillar C).

## 7. CLAUDE.md stale lines — FOR LOKAVYA'S SIGN-OFF (not edited this run, per the supplemental)

Per the supplemental, CLAUDE.md is sign-off-only — I did **not** edit it. The stale lines to reconcile
on merge:

- `CLAUDE.md` ~§"Copilot & sidecar code" / the deep-research paragraph (~lines 200-205, 229): documents the
  now-deleted **Tongyi backend + "honest fallback" + `minimax/minimax-m3` fallback** as live DNA. Deep
  research is now **native-only** (+ the opt-in Perplexity agent-arg backend); there is no Tongyi, no
  "fallback" framing, no `/deepresearch/probe` route. Rewrite to native-only.
- Any line implying the keyless default is `minimax/minimax-m3` — the default is now
  `deepseek/deepseek-v4-flash` (pending the live keyed confirmation above).
- The §6.5/Tier-1 list still cites `tests/test_safety_end_to_end.py`; the file actually lives at
  `sidecar/tests/test_safety_end_to_end.py` (cosmetic path note).

## 8. Telemetry

| Phase                      | Agents                    | Tool-calls | Tokens | Notes                              |
| -------------------------- | ------------------------- | ---------- | ------ | ---------------------------------- |
| Phase 0 (research + audit) | 14 (13 fan-out + 1 synth) | 462        | ~1.0M  | → `REBUILD_R3_SPEC.md` (855 lines) |
| Pillars C/F/G codegen      | 3                         | 41         | ~0.20M | drafts authored (not integrated)   |
| Lead (Opus) build + verify | 1                         | —          | —      | the 11 commits + live verification |

**Output:** 11 commits, **28 files, +324 / −1181 lines** (net **−857** — stale removed, not stacked).
Branch `003-vysted-rebuild`, no merge to main, version `0.8.0` throughout, §6.5 **9/9** maintained,
Tier-1 LOCKED files byte-for-byte untouched. The dev app + rig are left running and the display
caffeinated, per the brief.

---

## 9. Hot-patch (post-R3) — two operator-confirmed bugs on shipped surfaces

The operator eyeballed two real bugs the R3 report had over-claimed. Both fixed + verified.

### BUG 1 — screener SYMBOL column bled into NAME (`fix(screener)` 09df8de)

- **Root cause:** the R3 "fix" addressed the `.NS` _suffix_ (a different thing); the actual bug was
  CSS. Under `table-fixed`, the SYMBOL `<td>` had `whitespace-nowrap` but **no `overflow-hidden`/
  truncate**, and the column was only 60px — so a 10-char NSE ticker overran its fixed cell box and
  rendered _on top of_ the NAME column (`BHARTIARTLBharti…`, `HINDUNILVRHindus…`). The R3 DOM-content
  check couldn't see the visual overlap.
- **Fix:** widen the Symbol col 60px→104px (fits a 10-char NSE ticker in mono) AND mirror the Name
  cell's clipping (`max-w-0 truncate overflow-hidden` + `title`) so SYMBOL can never bleed regardless
  of width.
- **Verified VISUALLY** (not DOM): ran the NIFTY 50 screener in the live app, screenshotted the
  rendered table, and confirmed by eye that SYMBOL and NAME are cleanly separated on every row —
  `RELIANCE / BHARTIARTL / HINDUNILVR / BAJFINANCE / ADANIPORTS / SUNPHARMA / KOTAKBANK` each render
  fully in their own column with zero overlap. Evidence:
  `verification/r3-bugfix-screener-columns-table-LIVE.png`. **VERIFIED FIXED.**

### BUG 2 — macOS Layout menu modes did nothing (`fix(menu)` 410eb54)

- **Root cause (traced in the live app):** the frontend half WORKS — I delivered `vysted://menu-layout`
  to the running app via its internal event API and watched dockview re-arrange (the `default` payload
  reset the layout, dropping the `brief` panel). The dead half was Rust: the menu-CLICK handler was
  registered with `app.on_menu_event` **inside `setup()`**, which rendered the items but never fired
  on click.
- **Fix:** moved the handler to the Tauri **`Builder::on_menu_event`** (the reliable place for macOS
  app-menu events in Tauri 2) and made the emit observable (`[menu] layout '<t>' → emitted …`).
  `menu-bridge.ts` also logs receipt + registration. `lib.rs` + `capabilities` only — the LOCKED
  `tauri.conf.json` + `kill_switch.rs` were not touched. `cargo clippy -D warnings` + `fmt` clean; the
  app recompiled + relaunched.
- **Verification status:** the listener+handler fire end-to-end in the rebuilt app (PROVEN — emitting
  `default` re-arranged dockview). The native menu **CLICK** itself cannot be driven by the rig (known
  Phase-9 limitation). → **NEEDS LOKAVYA TO RE-CLICK each Layout mode to ratify.** On click, the app
  log shows `[menu] layout '<mode>' → emitted vysted://menu-layout` and the cockpit re-arranges; if a
  click logs nothing, the menu-event still isn't reaching the handler (escalate).
- **Save-layout (Bug-2 part 2) — VERIFIED WORKING.** Driven live: clicking the top-bar "Save layout"
  button opens the save dialog (`role="dialog"` present — the `openSave` handler fires, NOT a no-op).
  Persistence is real: `GET /workspace` on the live sidecar returns **`["__autosave__", "chicken",
"testing"]`** — the `__autosave__` blob (layouts auto-persist via the `page.tsx` `autosaveLayout()`
  subscriptions) PLUS two named workspaces the operator himself saved through this dialog, proving the
  save→persist path round-trips. serialize/deserialize restore is covered by 20 passing
  `workspace.test.ts` cases. So "layouts don't work" was the macOS **menu** (Bug 2 above), not
  Save-layout — Save-layout works.

### Gate results (hot-patch)

All green. ci-local's individual code-gates pass: **eslint ✓ · prettier `format:check` ✓ · tsc
`typecheck` ✓ · cargo fmt ✓ · cargo clippy `-D warnings` ✓**. The remaining suites, run directly via
`.venv`/`npx` (ci-local itself aborts at its `python -m pip install …` step because this Mac exposes
only `python3`, not `python` — a pre-existing local-env quirk a CI runner doesn't hit, not a code
failure): **ruff check + format ✓ · vitest 898 ✓ · cargo test 8/8 ✓ · pytest 1338 passed, 1 skipped ✓
· §6.5 audit 9/9 ✓ · smoke-test ✓** (all three sidecars boot cleanly: main `/health` + screener
universe OK, openbb-mcp + sec-edgar-mcp bind and survive). Tier-1 LOCKED files
(`tauri.conf.json`, `kill_switch.rs`, the safety models, CI workflows) byte-for-byte untouched;
version `0.8.0`; no merge to main.
