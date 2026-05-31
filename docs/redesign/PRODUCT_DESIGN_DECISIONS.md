# Product Design Decisions — Vysted Terminal (agent-native redesign, craft pass)

_The considered-product spec. Written 2026-05-31 after walking the **real running app**
with the tauri-mcp rig (DOM snapshots, screenshots, console/IPC). This governs the craft +
capability pass that follows. Every surface below was decided like a senior product designer,
benchmarked against Linear (settings, restraint), Cursor (agent-first, mode switching,
keyboard-first), Bloomberg (legible density), and Raycast (command flow). Where a decision
reverses something currently shipped, the reasoning is stated. Build to this doc._

Reference render state walked: branch `001-agent-native-redesign`, dev build with `dev-tools`,
sidecar healthy on :61865, Ollama up with `qwen2.5:7b` + `llama3.1:8b`.

---

## 0. The core diagnosis

The app is **not** flat because of its palette or its monospace identity — those are a
coherent, deliberate "cold instrument" system (graphite `#0a0b0d`, single ion-blue accent
`#4f86f7`, tabular-nums, mono body + Hanken-grotesque headings). It reads "assembled, not
crafted" because of six concrete things, every one of which I saw render:

1. **A floating bug.** The red "Halt All Trading" button is `position: fixed` and literally
   overlaps the Settings gear and the model indicator in every screenshot, at every layout.
2. **Alarmism.** That button is huge, bright red, and says "Halt All Trading" — in a
   **read-only app with no execution path**, that is loud, misleading, and wrong-weighted.
3. **Squeeze/overlap.** Panels have no minimum sizes; squeezed narrow, the Watchlist's
   price and change collide into "73,618.0256%" and ticker labels truncate to one letter.
4. **Cramped density done wrong.** The agent dock crams a 13-chip horizontally-scrolling
   persona roster (cut off mid-name), provider/model selectors, budget spinners, and a
   context line into a tight column. Dense ≠ crafted; this is cluttered.
5. **A weak first frame.** The default center tab is **Equity Overview showing an empty
   "enter a symbol" state**. The first thing a user sees is a blank.
6. **Developer data in user UI.** The kill-switch confirmation renders a `subs / p95 / max`
   latency grid — instrument-bench telemetry leaking into a user-facing toast.

The craft pass fixes these and sharpens hierarchy/spacing/states — it does **not** swap the
font or re-palette. (Reasoning under §2.)

---

## 1. Shell chrome — the top toolbar

**Current:** `VYSTED TERMINAL · Agent · Open panel ⌘K · Save layout · …spacer… · ●Connected
ollama·model · [Halt All Trading] · ⚙Settings`. The kill-switch button floats `fixed top-2
right-2 z-50`, escaping the header flex and overlapping Settings + the model text. Status text
is `text-[0.6rem]` (9.6px).

**Decisions:**

- **Kill switch → quiet icon, not a red billboard.** Replace the "Halt All Trading"
  destructive button with a **small, neutral icon button** (octagon/power glyph) living
  inline in the header's right cluster, tooltip _"Kill switch — halt & force read-only
  (⌘⌃⇧K)"_. It is **cool-neutral at rest** and escalates to red **only when armed/fired**.
  Rationale: §6.5 mandates an always-available kill switch (audit #5), and it stays fully
  functional + discoverable (icon + tooltip + the OS-global ⌘⌃⇧K + the reset flow + the fired
  banner). But the app ships **read-only with no live order path**, so a permanent red
  "Halt All Trading" billboard is fear-theater and mis-weights the visual hierarchy. The
  control earns prominence **when there is something to halt**, not before. _(Frontend
  presentation only — `kill_switch.rs` and the safety model are untouched; this is not a
  §6.5 weakening, it is a §6.5-preserving re-presentation.)_
- **Stop the overlap.** The kill-switch control moves **into the header flex flow** (between
  status and Settings), not `fixed`. Nothing in the header may overlap at any window width.
- **Status chrome legibility.** Bump the connection/provider/model readout off 9.6px to a
  legible size (~11px), keep the colored dot semantics (green connected / amber connecting /
  red error), keep the model indicator (Cursor shows the active model — it's good), but make
  the cluster a clean right-aligned group with real gaps and graceful truncation, not a
  cramped run that collides with the next control.
- **Labels.** "Open panel ⌘K" is fine. "Save layout" is fine. Keep the wordmark restrained.

## 2. Typography & palette — what we deliberately do NOT change

**Decision: keep the mono-body + grotesque-heading + ion-accent system. Sharpen, don't
swap.** A finance terminal benefits from monospaced tabular numerals (alignment across every
price/stat — Bloomberg's logic), the palette is already a restrained single-accent cold-dark,
and a global font swap across 18 panels on an autonomous run I cannot fully eyeball is high
regret for uncertain reward. "Crafted" here is bought with **precision**: deliberate use of
the existing `charcoal-100/200/300/400/500` text ramp for real hierarchy (today everything
trends one weight), honest spacing rhythm, and removing clutter — not a typeface. Where prose
benefits (empty states, dialog/onboarding copy), the Hanken grotesque (`--font-serif`,
already loaded) may be used. This is a real tradeoff, recorded honestly.

## 3. Kill-switch toast / banner

**Current:** banner shows `KILL SWITCH FIRED`, a free-form reason, and a `subs / p95 / max`
ms grid. **Decision:** the user-facing banner states the **consequence in human terms** —
_"Trading halted. New orders blocked; all brokers forced read-only. Press Reset to resume."_
**Remove the subs/p95/max latency grid** from the user UI. The latency numbers remain captured
in the fire result + audit (the §6.5 benchmark is untouched), but they are bench telemetry, not
user information. Keep the Reset affordance and the persistent muted reminder while fired.

## 4. The four modes

**Current:** Ask / Edit panel / Build / Delegate as a tab row with a one-line consequence
under it (⌥1–4). **Decision: keep four modes, present as a cleaner segmented switcher.** The
four modes are the right model (Cursor's Ask/Agent escalation, generalized) and the
consequence line ("Reads only — never changes the cockpit") is excellent honest framing —
**keep it**. Refine the visual: a true segmented control with a clear active fill, subtle
⌥1–4 hints, inactive states dimmed — not browser-tab chrome. Modes are a _switcher_, not tabs.

## 5. Agent dock

**Current:** header · mode switcher · **13-chip horizontal persona roster (cut off)** ·
provider/model selects · (Delegate) budget spinners · context line · transcript · composer.
Resizable 320–1200px, default 460px.

**Decisions:**

- **Demote the persona roster to a picker.** Replace the always-visible, horizontally-
  scrolling 13-chip strip with a single **"Vysted Copilot ▾"** selector (a popover listing
  all personas with their one-line philosophy). Cursor shows _one_ model picker, not 13
  always-on chips. Copilot is the default and the star; the 12 investor personas are a power
  feature one click away, not permanent clutter. This reclaims the dock's vertical budget and
  removes the cut-off-mid-name ugliness.
- **Keep** the provider/model selectors, the Delegate budget block (Delegate-only, relabel
  "Budget ceiling — first breach aborts the run"), the `CONTEXT: …` awareness line (it proves
  the agent reads the terminal — a signature of the product), and the empty-state copy. Tidy
  spacing and contrast on all of them.
- **Composer** stays; keep the Delegate-mode exception (can keep typing while a background run
  proceeds).

## 6. Jarvis-real — the agent drives the cockpit

**Current:** four host-actions (`open_panel`, `set_chart_symbol`, `add_to_watchlist`,
`propose_order`) route through the diff/accept gate (`proposed-changes.ts` → `host-actions.ts`).
The gate is correct and is the **only** path; `propose_order` never auto-places (§6.5).

**Decision: the agent must also be able to _arrange_ the cockpit, through the same gate.** Add
host-actions — **`close_panel`, `focus_panel`, and `arrange_layout`** (a small set of named
layout patterns / "focus this panel") — wired to real dockview actions (close, `setActive`,
re-tile). Every one of them:

- is registered in the capability catalog as `read_only=false, kind="host_action"` (the same
  class as the existing four — these are the catalog's only mutating capabilities);
- **routes through the diff/accept gate** — proposed with an old→new description, never
  auto-applied (SC-003 holds: 100% of mutations gated);
- is reachable by the `copilot` agent (added to its tools allow-list);
- never touches the §6.5 surface (no `place_/submit_/execute_order`, no `auto_approve`) — the
  audit grep stays clean.

This is the "Jarvis" unlock: _"open a chart for NVDA and a news panel next to it, close the
screener"_ → the agent proposes the panel moves → the user sees old→new → accepts → the
**dockview layout actually changes**. No auto-apply path, ever.

## 7. Panel placement policy

**Observed:** opening Marketplace dropped it into a cramped right-rail cell, squeezing News to
a sliver. **Decision:** classify panels by weight. **Primary-content panels** (Settings,
Marketplace, Plugin Manager, Agent Builder, Node Editor, Backtest, Chart, Equity Overview, and
the analysis panels) open into the **main/center group**. **Rail panels** (Watchlist, News,
Portfolio) belong in the side stack. `open_panel` (and the agent's arrange actions) respect
this so a panel never lands somewhere unusable.

## 8. Default cockpit / first run

**Decisions:**

- **Chart is the front center tab by default** (it's the visual anchor), not the empty Equity
  Overview "enter a symbol" state. The watchlist ships populated (SPY/QQQ/BTC/…); keep that.
- **No blank first frame.** Where a panel has no data yet, show an **inviting, specific empty
  state** (what it does + one action), never a bare line. The center should never greet a
  new user with emptiness.
- **Onboarding banner**: fix the truncated copy ("…stay in you…"). One clean line, clear
  value prop, one CTA ("Set up a provider"), dismissible. Don't cut the sentence.

## 9. Settings (Linear benchmark)

**Current:** 8 stacked sections (AI Providers, Preferences, Keybindings, Integrations,
Layouts, Modules, Export/Import, About) in one long scroll, mixed internal layouts, modals
that break scroll context.

**Decisions (scoped to what materially raises the bar tonight):**

- **De-duplicate brokers.** The "Integrations" section duplicates the Marketplace's broker
  list. Per the redesign thesis (marketplace = the single extensibility model), **brokers
  live in the Marketplace**; Settings → Integrations either redirects to it or is removed.
  One source of truth.
- **Consistent rows.** Every setting is one row: label + sub-hint + a single control, uniform
  height/padding/radius. Kill the mix of bespoke card styles. This alone reads far more
  "Linear."
- **Keep** AI Providers (keys), Preferences (default agent/provider/model, palette behavior,
  starter cockpit, appearance), Keybindings (remap + conflict detection — already good),
  Layouts, Modules, Export/Import, About. Don't over-engineer a left-nav tonight; a clean,
  grouped, scannable single column with strong section headers is the pragmatic Linear-grade
  win. (A searchable left-rail is a noted follow-up, not tonight's scope.)

## 10. Command palette (Raycast benchmark)

**Current:** Raycast-style modal, fuzzy ranking (subsequence), shortcut badges, descriptions.
Genuinely decent. **Issues:** (a) title matches don't outrank description matches — typing
"market" surfaces personas (Howard **Marks**, Graham's "Mr. **Market**") above the actual
Marketplace; (b) two redundant commands ("Marketplace" + "Open Marketplace") both open the
same panel; (c) no match-highlighting; (d) the `paletteRecentsEnabled` setting is unwired.

**Decisions:** weight **title/name matches above description matches** so the obvious result
wins; **remove the duplicate** marketplace command; add **character-level match highlighting**
(small, high-craft touch). Recents wiring is a noted follow-up if time allows. Keep the
teaching shortcut badges.

## 11. Overlap / squeeze (app-wide)

**Decision:** panels get **enforced minimum sizes** so they cannot be squeezed into overlap,
and content **reflows** gracefully below that. Critically, the min-size config lives
**host-side** (PanelHost / a component→min map / dockview `addPanel` constraints), **not** in
`PanelSpec` (`types/plugin.ts` is a LOCKED Tier-1 file — see Guardrails). The Watchlist table
gets an explicit colgroup so price/change never collide; ticker truncates with an ellipsis but
numbers stay put. Verified by driving the rig through many resize configurations — **no
overlap at any size.**

## 12. Sidecar cold-boot + panel recovery

**Observed live:** the sidecar's `:61865/health` failed repeatedly during the cold-boot window,
then connected (~a few seconds) and panels populated — the recovery path works for News /
Portfolio (backoff retry) and Watchlist (5s poll). **But Macro, SEC, Earnings, and Screener
fetch once on mount and sit dead** if the sidecar wasn't bound yet. **Decision:** every
fetch-once panel **auto-retries when the sidecar transitions to connected** (subscribe to
`useAppStore.sidecarStatus` and/or a shared retry gate), matching News/Portfolio. Loading
shows a "waiting for data" state, errors offer Retry, and nothing stays permanently dead after
a cold start. (The Rust bind path already degrades gracefully via the port-0 sentinel + 120s
frontend probe; the real gap is the four dead panels.)

## 13. Model for reliable tool-use

**Decision:** the local default is **`qwen2.5:7b`** (already the default in
`model-selection.ts`, `_resolve_model`, and `copilot.json` — the `llama3.1:8b` seen in the UI
was a stale persisted override in the restored workspace blob, not the default). Finish the
swap: clear the lingering reference in the test, keep `llama3.1:8b` only as a selectable
alternative, and **empirically verify via the rig that qwen2.5:7b actually fires the
panel-control tools** (open/close/arrange) in a multi-step instruction. Cloud keys
(Anthropic/OpenAI) remain the high-reliability route. Keyless first-run with no Ollama model
degrades gracefully (reachability gate already present) — the onboarding nudge stays clear.

## 14. Empty / loading / error states (standing requirement)

Every surface: a **specific, inviting empty state** (what it is + one action), **skeleton or
explicit "waiting" loading** (never a blank), and **errors that offer Retry** with a human
message. No half-baked dead-ends.

---

## Guardrails honored (hard)

- **`types/plugin.ts` is LOCKED** — min-sizes for the overlap fix go **host-side**, never into
  `PanelSpec`. The explorer's suggested "add `minimumWidth` to PanelSpec" is **rejected** on
  this basis.
- **§6.5 / Tier-1 safety files** (`broker_base.py`, `kill_switch.rs`, the safety/broker/audit
  models, `test_safety_end_to_end.py`, `tauri.conf.json`, CI) are **byte-for-byte untouched**.
  Kill-switch changes are frontend presentation only.
- **Brokers stay read-only**; the new agent host-actions are **UI actions through the diff
  gate**, never a path around the gate / kill-switch / audit. SC-003 (100% gated) holds.
- **The rig stays dev-only** (feature flag + `NODE_ENV` guards intact).

## Ranked for the operator's eyes (first → last)

1. Kill-switch re-presentation (loud red → quiet icon) — a safety-surface _presentation_
   change; confirm it reads right and the control is still obviously discoverable.
2. Agent-drives-cockpit through the gate — the headline capability; eyeball a real
   propose→accept→layout-change.
3. The minimal-dark craft pass overall — does it now feel Cursor-grade.
4. Overlap fix across resize configs.
5. Cold-boot panel recovery.
