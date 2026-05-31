# Overnight build report — agent-native redesign craft + capability pass

_Branch `001-agent-native-redesign` (NOT merged, NOT version-bumped — your call).
Build window: 2026-05-31 23:30 → 2026-06-01 ~01:00 IST. Lead: Opus 4.8 (1M), driving the
**real running Tauri app** through the tauri-plugin-mcp rig (DOM snapshots, screenshots,
console/IPC, real clicks/fills, and the live agent). Every "verified" claim below was driven
against the real app — nothing asserted from code-reading alone. Closeout HEAD `7b58dac`._

> **Read me first, then `PRODUCT_DESIGN_DECISIONS.md` (the governing Phase-0 spec) and
> `OPERATOR_ATTENTION.md` (the prior P1–P3 closeout, still valid).**

---

## TL;DR

The redesign's P1–P3 was built but had **never been seen render** (the prior context had no
screen capture / GUI driving). This pass put the rig on it, found the real "assembled-not-
crafted" offenders, fixed them, and **built + verified the headline "Jarvis" capability — the
agent driving the cockpit through the diff gate — end-to-end against the live app**.

- **The agent now opens/closes/focuses/arranges panels**, every action routed through the
  propose→accept diff gate. Verified live: "close the news panel" → qwen2.5:7b called the
  tool → a reviewable `News: open → closed` diff appeared → **the panel stayed open until I
  accepted** → on accept the panel actually closed. No auto-apply path (SC-003 holds).
- **The shell is genuinely more minimal-dark.** The biggest offender — a `position:fixed`
  bright-red "Halt All Trading" button overlapping Settings + the model readout at every
  width — is gone, replaced by a quiet octagon-stop icon. Overlap is gone (proven by
  bounding-rect math). The kill-switch banner no longer leaks `subs/p95/max` dev telemetry.
- **Panel overlap is fixed at any size** (proven down to a 90px squeeze). Min panel sizes are
  enforced host-side **without touching the LOCKED `types/plugin.ts`**.
- **Cold-boot dead panels fixed**: Macro/SEC/Earnings/Screener now auto-retry when the
  sidecar binds, matching News/Portfolio.
- **All gates green** for everything touched: `format:check`/`eslint`/`tsc` clean, **vitest
  744 passed**, **§6.5 audit still 9/9** (55 safety tests), catalog/MCP-parity/runtime green.
- **Tier-1 LOCKED files byte-for-byte untouched.** No STOP-AND-SURFACE guardrail was hit —
  one was *avoided by design* (see §"Guardrails").

---

## Phase 0 — the product-design decisions (the notable taste calls)

Full spec in `PRODUCT_DESIGN_DECISIONS.md`. The calls that matter:

1. **"Halt All Trading" was wrong-weighted.** In a read-only app with no live order path, a
   permanent giant red billboard is fear-theater (and it was literally a layout bug —
   `fixed`-positioned, overlapping its neighbours). **Decision: demote to a quiet, neutral
   octagon-stop icon in the header that escalates to red only when fired.** The §6.5 kill
   switch is fully preserved — one click or the OS-global ⌘⌃⇧K away, with a loud fired-state
   banner + reset. This is a *frontend presentation* change; `kill_switch.rs` and the safety
   model are untouched. (Verified: the audit stays 9/9.)
2. **Kill-switch toast leaked developer data.** It rendered a `subs / p95 / max` ms grid.
   **Decision: state the consequence in human terms** ("Trading halted — new orders blocked,
   brokers forced read-only") and drop the latency grid from the user UI (it stays in the
   fire-result + audit for the §6.5 <2s benchmark).
3. **Keep the mono-instrument identity; sharpen, don't reskin.** The palette (cold graphite +
   single ion-blue accent, tabular-nums, mono body + grotesque headings) is coherent. The
   flat feel came from *bugs, cramped density, 9.6px text, and empty defaults* — not the
   typeface. A global font swap across 18 panels on an autonomous run I can't fully eyeball is
   high-regret; "crafted" here is bought with precision. (An explicit, recorded tradeoff.)
4. **Four modes stay, as a switcher** (Cursor-style), with the honest one-line consequence
   line kept ("Reads only — never changes the cockpit").
5. **Persona roster was clutter.** 13 always-on chips scrolling and clipping mid-name → **one
   "Lens" picker**; the 12 personas live one click away.
6. **Agent must *arrange*, not just answer** — the Jarvis thesis. Add `close_panel`,
   `focus_panel`, `arrange_layout` as host-actions, all through the same diff gate.
7. **Panel placement + first-frame**: big content panels belong in the main area, not a
   cramped rail; the first frame should never be a blank "enter a symbol". (Placement policy
   is a documented follow-up — see §"Still rough".)

---

## What got built (per brief item 1–6)

### 1 + 6. Minimal-dark craft pass + product-judgment (shell)  ·  VERIFIED
`src/app/page.tsx`, `StatusChrome.tsx`, `KillSwitchToolbar.tsx`, `OnboardingBanner.tsx`.
- Kill switch: `fixed top-2 right-2 z-50` → **inline** quiet `OctagonX` icon; the overlap is
  gone. **Proven by rect math against the live DOM**: `overlap_ks_settings:false`,
  `overlap_ks_status:false`, `bodyHasHaltText:false`.
- Banner: human consequence copy; `subs/p95/max` grid removed.
- StatusChrome: 9.6px → 11px, clean right-cluster grouping with a divider.
- Settings → icon button matching the kill-switch; onboarding banner wraps the full value
  prop instead of truncating mid-sentence.
- Accessible names / `data-state` / the `kill-switch-banner` testid preserved → §6.5 UI tests
  stay green.

### 2. Jarvis — the agent drives the cockpit through the diff gate  ·  VERIFIED (headline)
`catalog.py` (+3 host-actions), `copilot.json` (tools + prompt), `host-actions.ts`,
`ChatSidebar`/`proposed-changes` gate (kept), real dockview ops.
- New `close_panel` / `focus_panel` / `arrange_layout` capabilities (`read_only=false`,
  `kind=host_action`) — the catalog's only mutating class — wired to real dockview
  (`close` / `setActive` / `maximize` / `resetToDefaultLayout`).
- **Live e2e (real app, qwen2.5:7b):** typed "Close the news panel" in Build mode → the model
  called `close_panel` → the gate showed **"1 PROPOSED CHANGE — REVIEW BEFORE THEY APPLY"**
  with the `− News panel: open / + News panel: closed` diff → **the news panel stayed open**
  (no auto-apply) → I clicked Accept → **`getPanel('news')` became null — the panel actually
  closed.** That is the full propose→gate→accept→drive loop on the real engine.
- Safety: host-actions stay local (not projected to MCP); no `place_/submit_/execute_order`,
  no `auto_approve`. `test_safety_end_to_end` + catalog/MCP-parity suites pass.

### 3. Model for reliable tool-use (Qwen)  ·  VERIFIED + an honest finding
- The local default was **already** `qwen2.5:7b` across `model-selection.ts`, `_resolve_model`,
  and `copilot.json`; the `llama3.1:8b` the UI showed was a **stale workspace-blob override**,
  which cleared on a layout reset — the header + dock now correctly read `qwen2.5:7b`. Fixed
  the one lingering `llama3.1:8b` in `test_llm_ollama.py`.
- **Empirical finding (the brief's "your call from testing"):** qwen2.5:7b's tool-calling is
  **inconsistent**. It called `close_panel` cleanly (full e2e above), but for a multi-step
  request ("open the screener AND set the chart to NVDA") and a second single request ("add
  TSLA to my watchlist") it **narrated the actions in prose** ("I've added TSLA… Proposed
  actions: 1…2…") **instead of emitting tool calls** — so nothing was staged. The diff
  gate + dockview wiring are proven correct; the unreliability is the 7b model.
  - **Recommendation:** keep `qwen2.5:7b` as the local default (it's the best of the two
    models installed — `qwen2.5:7b` + `llama3.1:8b`; `14b` is not installed, so defaulting to
    it would fail), and **the cloud-key path (Anthropic/OpenAI) is the reliable route for
    agent control** — which is the documented design. The keyless-degrade gate is in place.
  - One real UX wrinkle worth a follow-up: when 7b narrates "I've done X" without calling the
    tool, the user is told something happened that didn't. A prompt nudge could reduce the
    false claim, but 7b adherence is fundamentally limited; cloud keys solve it cleanly.

### 4. Overlap / squeeze (app-wide)  ·  VERIFIED
`PanelHost.tsx`, `default-layout` (via host-side map), `WatchlistPanel.tsx`.
- **No content overlap at any size** — proven by driving the rig to squeeze the watchlist to
  **90px** and confirming `adjacentOverlap:[false,false,false]`; the numeric cells now
  `overflow:hidden / text-ellipsis` so Price and Change can never collide (the "73,618.0256%"
  bug), backed by an explicit `<colgroup>`.
- **Host-side minimum panel sizes** via dockview `setConstraints` (applied on add + a deferred
  post-restore sweep that also grows any panel a saved blob restored below its minimum). The
  min map lives in `PanelHost`, **NOT in `PanelSpec`** — `types/plugin.ts` (LOCKED) is
  untouched. (Two engine quirks found + handled: `setSize` bypasses constraints — it's the
  wrong probe; and `requestAnimationFrame` is throttled to a halt on an unfocused WKWebView,
  so the sweep uses `setTimeout`.)

### 5. Sidecar cold-boot + panel auto-retry  ·  IMPLEMENTED + unit-verified
`src/lib/use-sidecar-retry.ts` (new) + Macro/SEC/Earnings/Screener panels.
- New `useRetryOnSidecarReady` hook: bounded backoff + re-arm on the `sidecarStatus`
  connecting/error → connected edge (the same edge I watched fire at this launch). The four
  fetch-once panels that previously sat dead now recover, matching News/Portfolio.
- 78 store/panel tests pass; tsc/eslint clean. **Live cold-boot recovery** (open one of these
  panels *during* the bind window and watch it self-heal) is best confirmed at a real cold
  start — see §"Still rough".

### Item 1b (dock/palette/settings craft) — partial
- DONE: persona roster 13-chips → one **Lens picker** (verified: a `combobox` with 13
  options, value `copilot`).
- DEFERRED (documented follow-ups, not started): panel-placement policy (big panels → main
  area), command-palette title-over-description ranking + the duplicate "Marketplace"/"Open
  Marketplace" command + match highlighting, and the Linear-grade settings consistent-rows
  refactor + Integrations/Marketplace broker de-dup. These are real but lower-impact than the
  headline items; left clean rather than half-wired.

---

## What the rig verified (evidence)

All against the real running app (sidecar :53479, qwen2.5:7b, Ollama up):

| Claim | How verified | Result |
|---|---|---|
| Header overlap gone | live-DOM bounding-rect math | `overlap_ks_settings=false`, `overlap_ks_status=false`, no "Halt All Trading" text |
| Kill switch quiet icon, escalates on fire | DOM + screenshots | armed `OctagonX` icon, `data-state=armed`, tests green |
| Watchlist no overlap at squeeze | forced panel to 90px, read cell rects | `adjacentOverlap=[false,false,false]`, cells clip |
| Min-size `setConstraints` enforces | set min then `setSize(100)` | clamped to 264 (engine honours it) |
| Jarvis: propose → gate → accept → drive | drove the live agent + clicked Accept | diff shown, panel stayed open, then `getPanel('news')===null` |
| qwen tool-use (single) | "close the news panel" | tool called, e2e success |
| qwen tool-use (multi/again) | "open screener + NVDA", "add TSLA" | **narrated, no tool call** (model limit) |
| Model default = qwen2.5:7b | header + dock readout | `Connected · ollama · qwen2.5:7b` |
| Persona declutter | DOM | one `Active persona` combobox, 13 options |
| Command palette | opened + filtered | renders, shortcut badges, fuzzy match (ranking follow-up noted) |
| Marketplace | opened | Kite/Dhan/Angel/Alpaca, "Read-only; no order execution", none pre-installed |

**Screenshots:** clean rig captures of the redesigned cockpit, the header fix, and the live
proposal diff are embedded in the build session (the primary, app-only evidence). One
full-display PNG is saved at `docs/screenshots/redesign-2026-06-01/`. _Constraint: the rig
returns captures to the session rather than to disk, and exact 1920×1080 / 2560×1440 window
framing + per-tag `v<tag>/` files isn't reachable through the rig (the window is fixed-size;
`@tauri-apps/api/window` isn't importable from the webview sandbox). Capture the final per-tag
PNGs at merge — the branch is untagged._

---

## Guardrails

- **No STOP-AND-SURFACE was hit.** One was *avoided by design*: the obvious overlap fix was to
  add `minimumWidth` to `PanelSpec` in `types/plugin.ts` — a LOCKED Tier-1 file. I **rejected
  that** and put the min-size map host-side in `PanelHost` instead. `types/plugin.ts` and the
  whole §6.5 / Tier-1 set are **byte-for-byte untouched**.
- **Brokers stay read-only**; the new agent host-actions are UI actions through the diff gate,
  never a path around the gate / kill-switch / audit. §6.5 audit 9/9.
- **The rig is dev-only** — `dev-tools` Cargo feature + `NODE_ENV` guard intact; dead-stripped
  from the production static export. (One dev-only `window.__vystedDockview` handle was added,
  also `NODE_ENV`-guarded, to let the rig inspect/drive the live layout.)

---

## Gate results (closeout)

- `pnpm format:check` — **PASS** (all files Prettier-clean)
- `pnpm lint` (eslint) — **PASS**
- `pnpm typecheck` (tsc) — **PASS**
- `pnpm test` (vitest) — **PASS, 744 / 744** (102 files)
- Sidecar (venv) — **PASS**: `test_capability_catalog`, `test_mcp_catalog_parity`,
  `test_agent_runtime`, `test_agents_store`, `test_tool_loop_e2e`, `test_mcp_server`,
  `test_agents_router`, `test_schemas`, `test_llm_ollama`, and **`test_safety_end_to_end`
  (55 passed — §6.5 still 9/9)**.
- NOT run (heavy / operator pre-tag): full `pnpm ci-local` (builds all 3 sidecars +
  cargo/clippy/ruff-all/full pytest) and `scripts/smoke-test-sidecars.mjs`. The main sidecar
  binary WAS rebuilt this session (the running app uses the new catalog) and boots healthy;
  the openbb/sec sidecars are unchanged. Run full `ci-local` + smoke before any tag.

---

## Still rough / unverifiable / follow-ups (ranked)

1. **qwen2.5:7b multi-step tool-use is unreliable** (narrates instead of calling) — use a
   cloud key for reliable agent control. Wiring is proven; the model is the limit.
2. **Live cold-boot panel recovery** (item 5) — implemented + unit-tested, but the self-heal
   edge wasn't exercised live (needs a panel open *during* the ~16s bind window at a cold
   start). Low risk: it reuses the proven News/Portfolio pattern.
3. **Panel-placement policy** (big panels → main area) — not built; opening Marketplace/
   Settings can still land in a cramped rail cell. Clean follow-up.
4. **Command palette polish** — title matches should outrank description matches (typing
   "market" surfaces personas above Marketplace); remove the duplicate "Marketplace" command;
   add match highlighting. Not built.
5. **Settings Linear-grade pass** — de-dup Integrations vs Marketplace brokers; consistent
   single-row controls. Not built.
6. **Screenshot framing** — exact 1920×1080 / 2560×1440 per-tag PNGs to be captured at merge
   (see §evidence for why the rig can't frame them).

---

## Gotchas discovered (fold into CLAUDE.md at your discretion — I left CLAUDE.md untouched)

- **dockview `setConstraints` governs interactive sash-drags, not programmatic `setSize`** —
  `setSize` bypasses min/max. Don't use `setSize` to test constraints; and constraints don't
  retroactively grow an under-min panel (grow it explicitly on restore).
- **`requestAnimationFrame` is throttled to a halt on an unfocused/occluded WKWebView** — any
  deferred layout work (e.g. applying constraints after restore) must use `setTimeout`, or it
  silently never runs when the window isn't frontmost. (Same root cause as the
  `focus_window`-before-screenshot rig gotcha.)
- **dockview `fromJSON` restore does not fire `onDidAddPanel` per panel** — sweep `api.panels`
  after restore to apply per-panel host config.
- **The rig's synthetic key events don't trigger app keydown handlers** (⌘K didn't open the
  palette); click the affordance or dispatch a real DOM `click` instead. Canvas/lightweight-
  charts reject untrusted events (known); dockview sash-drag clamping likewise can't be
  rig-driven via synthetic pointer events.
- **A stale `model-selection` override rides the workspace blob** and shadows the default
  model in the UI; resetting the layout clears it.

---

## Telemetry

- **Wall-clock:** build start 2026-05-31 23:30 IST → closeout ~2026-06-01 01:00 IST (~1h30m).
- **Agents dispatched:** 1 exploration workflow (**10 Explore subagents**, 8/10 returned
  structured output; ~860k subagent tokens, 276 tool-uses, 343s) + **1 implementation
  teammate** (cold-boot auto-retry; ~93k tokens, 46 tool-uses, 285s). Lead (Opus) did all
  rig driving, the shell/overlap/Jarvis/model work, integration, and verification.
- **Per-phase:** Phase-0 design (lead+rig) → item 1 shell (lead) → item 4 overlap (lead) →
  item 5 cold-boot (1 teammate) → item 2 Jarvis (lead) → item 3 model (lead) → item 1b dock
  (lead) → verification + gates + report (lead).
- **Code:** 7 commits, **32 files, +2375 / −191**. New files: `use-sidecar-retry.ts`,
  `dev-mcp-bridge.ts`, the two redesign docs, the dev-tools capability template.
- **Branch pushed to origin** (backup) at each checkpoint. **Not merged, not version-bumped.**

---

## What needs your eyes first (ranked)

1. **The kill-switch re-presentation** (loud red → quiet icon). It's a safety-surface
   *presentation* change — confirm it reads right and is still obviously discoverable. (The
   mechanism + audit are untouched; this is the one call most worth your judgment.)
2. **The Jarvis loop** — drive it yourself: Build mode → "close the news panel" → see the
   proposal → accept → watch it close. Then add a cloud key and try a multi-step ("set me up
   to research NVDA") to see reliable multi-tool composition.
3. **The minimal-dark feel overall** — does the shell now read Cursor-grade.
4. **Merge + version bump** — your call (all five version sources still read `0.8.0`).
5. The deferred follow-ups (§"Still rough"), in order.

The app + rig are **left running** for your review.
