# Stage 1 Surface Census — Coverage Skeleton

R15 LAUNCH · Stage 0 deliverable. Built from the code (`src/modules`, `src/store`,
`src/lib`, `src/components`, `sidecar/routers`, `src-tauri/src`), not from docs. Every
row in `COVERAGE_SKELETON.json` has a file:line anchor for a claim actually opened in
this pass; anything not yet opened line-by-line is flagged explicitly in its `notes`.

101 surfaces enumerated. Drive-method split: **66 browser** (component/store logic
mountable or unit-testable headlessly, vitest+jsdom or Playwright), **29 api** (a
sidecar GET/POST endpoint is the primary or an equally valid way to exercise the
surface), **6 gui** (genuinely requires a real OS/webview — native drag-drop, a native
menu click, or an OS-global keyboard shortcut).

## Live-stack probe (read-only, as instructed)

`curl --max-time 3 http://127.0.0.1:52052/health` → **connection refused** at the time
of this census (`lsof -iTCP -sTCP:LISTEN` shows nothing on 52052; only the two MCP
subprocess sidecars were up, on 52943/52944, plus a `target/debug/vysted-terminal`
Tauri binary and vitest workers — a `pnpm ci-local` background run was also observed).
The operator's dev stack was not reachable on the port named in the brief at probe
time. No other ports were scanned (out of scope for a read-only census). Every `drive:
api` entry below is therefore based on **reading the router source**
(`sidecar/routers/*.py`), not a confirmed live round-trip — Stage 1 execution should
re-probe before relying on it.

## How to read a row

- **entry** — `file:line` for the panel registration / component / store this session
  actually opened. Multiple anchors are semicolon-separated.
- **states** — states seen in the code (`loading`/`error`/`empty` enums, `data-testid`
  markers) plus, where useful, generic QA states from the brief's vocabulary
  (`overflow`, `offline`, `tenth-item`) that are plausible to manufacture even without
  a literal code branch — call sites don't always branch on "the 10th row," but a list
  surface should still be checked at that scale.
- **drive** — `api` (sidecar GET/POST is the way in), `browser` (vitest/jsdom mount or
  a pure function extractable from the component), `gui` (native OS/webview only).
- **notes** — the load-bearing detail: exact test file if one exists, the exact
  sidecar route, a §6.5 safety caveat, or an explicit "not yet opened, verify in Stage
  1" flag.

## Areas covered

| Area | Surfaces | Notes |
|---|---:|---|
| panels | 17 | every first-party `PanelSpec` from `src/modules/index.ts`'s 19 modules (chat contributes none — it's the shell column, not a panel) |
| composer | 16 | the whole `ChatSidebar.tsx` composer: depth, model, plus-menu, mention/slash pickers, send/stop, queue, agents rail |
| chat-agent | 8 | mode/autonomy/persona, the agent-command bus, delegate runs, streaming transport, markdown rendering, context badge |
| settings | 13 | every section + subsection under `SettingsPanel.tsx` |
| screener | 5 | shell, criteria builder, formula leaf, results table, presets |
| node-editor | 5 | canvas, palette (drag-drop), run overlay, code-node inspector, save dialog |
| charts | 5 | panel, draw/indicators/sync toolbars, timeframe |
| toasts-and-frames | 5 | there is **no toast library** — confirmed by grep; every "toast" is a per-panel inline error row, plus the shared `EmptyState` component, desktop notifications, CSV/export utilities |
| onboarding | 4 | first-run wizard, key banner, ToS/disclaimer flow |
| notes | 4 | panel, toolbar, slash-menu extension, wikilink extension |
| command-palette | 4 | palette shell, Ask-AI row, symbol autocomplete, fuzzy matcher |
| keyboard-shortcuts | 3 | the keymap store, global keydown handlers, the OS-level kill-switch shortcut |
| layouts | 3 | the 4 agent arrange templates, the native macOS Layout menu, workspace save/load |
| safety | 3 | order confirmation dialog, the **dormant** kill switch, disclaimer flow |
| plugins | 2 | Plugin Manager panel, Marketplace panel |
| proposed-changes | 1 | the diff/accept trust gate bar |
| brief | 1 | the research brief's full lifecycle (loading/streaming/populated/error/divergence) |
| portfolio | 1 | the paper-portfolio panel |
| comparison | 1 | three convergent entry points (chart CompareMenu, `/compare`, the `compare` arrange template) sharing one bus |

## Load-bearing findings from this pass

1. **The kill switch has no UI toolbar today.** `src/modules/safety/index.ts:8-12`
   states this explicitly — it was removed in the "agent-native craft pass" because
   this is a read-only app. The mechanism is still live and testable, just not from
   any button: the OS-global `Cmd/Ctrl+Shift+K` shortcut
   (`src-tauri/src/kill_switch.rs:34`, registered at `lib.rs:446`) and the sidecar
   `POST /safety/kill-switch` / `/kill-switch/reset` (`sidecar/routers/safety.py:119,125`).
   `GET /safety/kill-switch/status` (`:142`) is the only read-only probe. A Stage 1 test
   plan that looks for "the kill switch button" will not find one — that is correct,
   not a gap.

2. **No toast/notification library exists.** Grepped for `sonner`/`toast(` across
   `src/` — zero hits. Every panel's "error toast" is actually a local inline error
   row (several carry `data-testid="*-error"`: `option-pricing-error`,
   `greeks-error`, `bond-pricing-error`, `yield-curve-error`, `sec-filings-error`,
   `screener-formula-error`). Treat "toasts" in the Stage 1 plan as this per-panel
   pattern, not a global stack to click through.

3. **Chat is not a dockview panel.** `src/modules/chat/index.ts` registers zero panels
   by design (`panels: []`) — it's the shell's resizable left column
   (`AgentDock`/`ChatSidebar`). A coverage tool that only walks `PanelSpec[]` will
   silently miss the entire composer/agent surface; it has to be censused separately,
   which this skeleton does (the `composer` and `chat-agent` areas).

4. **A meaningful fraction of "browser" surfaces are actually pure-function
   headless-testable without mounting anything**: `composer-collapse.ts`,
   `nextResearchDepth`, `buildPlusMenuSections`, `applyEvent` (workflow run reducer),
   `planLayout`/`fitLayoutTemplate`/`applyLayoutMode`, `screener-expr.ts`,
   `isDivergenceNotice`, `searxngChipMeta`, `buildSettingsExport`,
   `serializeWorkspace`/`deserializeWorkspace`, `market-session.ts`, `fuzzy.ts`,
   `csv.ts`. These are the cheapest, highest-value Stage 1 targets — no DOM, no
   sidecar, existing `.test.ts` files to extend in most cases.

5. **Six surfaces are genuinely GUI-only** and cannot be exercised by this run's
   constraints (no GUI interaction) or by chrome-devtools MCP even in a future run
   (per `CLAUDE.md`'s "chrome-devtools MCP can't synthesize trusted events" gotcha):
   node-palette drag-drop onto the canvas, the chart Draw-menu's actual pointer-drag
   gesture, the native macOS Layout menu, the OS kill-switch shortcut, and OS desktop
   notification delivery. Each has a paired pure-logic entry that *is* headlessly
   testable (the reducer/mapper behind the gesture), called out in its `notes`.

6. **Two surfaces are flagged unresolved, not fabricated**: the exact
   `settings-advanced-layouts` subsection content (`SettingsPanel.tsx:1587`, not read
   past its declaration line in this pass) and whether `provider-health-breaker`
   (`sidecar/routers/system.py:203`) has any frontend surface at all (none found).
   Stage 1 should resolve both before writing tests against them.

## Full table

See `COVERAGE_SKELETON.json` for the machine-readable form (101 entries, schema
`{id, area, surface, entry, states[], drive, notes}`). Rendered summary:

| id | area | surface | drive |
|---|---|---|---|
| panel-chart | panels | Chart panel (PanelSpec + ChartPanel component) | browser |
| panel-watchlist | panels | Watchlist panel | browser |
| panel-news | panels | News panel | api |
| panel-portfolio | portfolio | Portfolio (paper) panel | browser |
| panel-equity-overview | panels | Equity Overview panel | api |
| panel-brief | brief | Research Brief panel (lifecycle) | browser |
| panel-settings | settings | Settings panel shell | browser |
| panel-plugin-manager | plugins | Plugin Manager panel | browser |
| panel-marketplace | plugins | Marketplace panel | browser |
| panel-agent-builder | panels | Agent Builder panel | api |
| panel-node-editor | node-editor | Node Editor canvas | gui |
| node-editor-palette | node-editor | Node palette (draggable node catalog) | gui |
| node-editor-run-overlay | node-editor | Workflow run overlay (SSE run states) | browser |
| node-editor-code-node | node-editor | Code node inspector | browser |
| node-editor-save-dialog | node-editor | Workflow save dialog | browser |
| panel-backtest | panels | Backtest panel | api |
| panel-broker-connect | panels | Broker Connect (connections) panel | api |
| panel-broker-order-entry | panels | Broker Order Entry panel | api |
| panel-audit-log | safety | Audit Log viewer panel | api |
| panel-macro | panels | Macro panel | api |
| panel-sec-filings | panels | SEC Filings panel | api |
| panel-earnings-calendar | panels | Earnings Calendar panel | api |
| panel-analyst-ratings | panels | Analyst Ratings panel | api |
| panel-option-pricer | panels | Option Pricer panel (Quant) | api |
| panel-greeks-dashboard | panels | Greeks Dashboard panel (Quant) | api |
| panel-bond-pricer | panels | Bond Pricer panel (Quant) | api |
| panel-yield-curve | panels | Yield Curve panel (Quant) | api |
| panel-screener | screener | Screener panel shell | api |
| screener-criteria-builder | screener | Screener criteria builder | browser |
| screener-formula-input | screener | Screener formula leaf | browser |
| screener-results-table | screener | Screener results table | browser |
| screener-presets | screener | Screener saved/preset screens | browser |
| panel-notes | notes | Notes panel | browser |
| notes-toolbar | notes | Notes formatting toolbar | browser |
| notes-slash-menu | notes | Notes '/' slash-command menu | browser |
| notes-wikilink-menu | notes | Notes [[wikilink]] suggestion popup | browser |
| composer-mount | composer | Chat composer shell | browser |
| composer-depth-control | composer | Research-depth selector | browser |
| composer-model-control | composer | Inline model/provider picker | browser |
| composer-plus-menu | composer | Composer '+' menu | browser |
| composer-mention-picker | composer | '@' mention picker | browser |
| composer-slash-picker | composer | '/' slash-command picker | browser |
| composer-send-stop-button | composer | Send/Stop button | browser |
| composer-queue | composer | Queued-prompt FIFO chips | browser |
| chat-agents-rail | composer | Running-agents rail (Delegate runs) | api |
| chat-empty-state | composer | Chat dock empty (hero) state | browser |
| chat-suggestion-chips | composer | Suggestion chips | browser |
| chat-error-row | composer | Chat transcript error row | browser |
| chat-message-notices | composer | End-of-stream divergence notice chip | browser |
| chat-plan-view | composer | Agent plan view | browser |
| chat-research-activity | composer | Research step-trace / activity feed | browser |
| chat-budget-config | composer | Delegate budget config | browser |
| proposed-changes-review-bar | proposed-changes | Proposed-changes diff/accept trust gate | browser |
| safety-order-confirmation-dialog | safety | Order confirmation dialog (§6.5) | browser |
| safety-kill-switch | safety | Kill switch (dormant, no UI toolbar) | api |
| safety-disclaimer-flow | onboarding | First-launch ToS / disclaimer flow | browser |
| onboarding-flow | onboarding | First-run onboarding wizard | browser |
| onboarding-banner | onboarding | First-run 'add your AI key' banner | browser |
| command-palette | command-palette | Command palette (cmd+K launcher) | browser |
| command-palette-ask-ai | command-palette | Palette 'Ask AI' free-text row | browser |
| settings-section-nav | settings | Settings section nav | browser |
| settings-providers | settings | AI Providers section (BYOK keys) | browser |
| settings-research | settings | Research section (depth/model tiers + SearXNG) | api |
| settings-searxng | settings | SearXNG managed-instance flow | browser |
| settings-region | settings | Region section | api |
| settings-keybindings | settings | Keybindings remap section | browser |
| settings-advanced-integrations | settings | Advanced > Integrations subsection | browser |
| settings-advanced-layouts | settings | Advanced > Layouts subsection | browser |
| settings-advanced-modules | settings | Advanced > Modules subsection | browser |
| settings-advanced-export-import | settings | Advanced > Export/Import settings | browser |
| settings-advanced-about | settings | Advanced > About subsection | api |
| layouts-arrange-templates | layouts | Agent 'arrange' layout templates (4 modes) | browser |
| layouts-macos-menu-bridge | layouts | Native macOS Layout menu | gui |
| layouts-workspace-save-load | layouts | Save/Load workspace + New Research Space | api |
| comparison-surface | comparison | Symbol comparison (3 convergent entry points) | browser |
| charts-toolbar-draw-menu | charts | Chart toolbar > Draw menu | gui |
| charts-toolbar-indicators-menu | charts | Chart toolbar > Indicators menu | browser |
| charts-toolbar-sync-menu | charts | Chart toolbar > Sync menu | browser |
| charts-timeframe | charts | Chart timeframe/interval selector | api |
| kb-keybindings-store | keyboard-shortcuts | Keybindings default keymap | browser |
| kb-global-handlers | keyboard-shortcuts | Global keydown handlers | browser |
| kb-os-kill-switch-shortcut | keyboard-shortcuts | OS-level kill-switch shortcut | gui |
| generic-empty-state-component | toasts-and-frames | Shared EmptyState component | browser |
| generic-error-frame-pattern | toasts-and-frames | Per-panel inline error text pattern | browser |
| desktop-notification-bridge | toasts-and-frames | OS desktop notification bridge | gui |
| agent-mode-toggle | chat-agent | Agent mode toggle (Agent vs Delegate) | browser |
| agent-autonomy-ask-auto | chat-agent | Autonomy: ASK vs AUTO | browser |
| agent-persona-picker | chat-agent | Persona / active-lens picker | api |
| agent-command-bus | chat-agent | Agent-command bus | browser |
| agent-runs-store | chat-agent | Delegate run lifecycle | api |
| llm-chat-streaming | chat-agent | LLM chat streaming transport | api |
| chat-markdown-render | chat-agent | Chat markdown streaming renderer | browser |
| context-provider-badge | chat-agent | Context badge | browser |
| panel-context-publishers | panels | Per-module panel-context publishers | browser |
| symbol-autocomplete | command-palette | Symbol autocomplete | api |
| fuzzy-search-lib | command-palette | Fuzzy matcher | browser |
| csv-export | toasts-and-frames | CSV export utility | browser |
| export-artifact | toasts-and-frames | Export-conversation / export-artifact flow | browser |
| market-session-indicator | charts | Market-session state | browser |
| hardware-fit-check | onboarding | Local-model hardware-fit scoring | api |
| provider-health-breaker | settings | Provider health / circuit-breaker status | api |

## Explicit gaps / follow-ups for Stage 1

- Re-probe the live sidecar port before trusting any `drive: api` entry — 52052 was
  down at census time.
- Open `SettingsPanel.tsx:1587` (`LayoutsSection`) fully — only its declaration line
  was confirmed in this pass.
- Confirm whether `provider-health-breaker` has any frontend surface at all, or is
  sidecar-internal only.
- `charts-timeframe`'s exact selector component was not pinned to a line — the panel
  file is large; Stage 1 should grep `ChartPanel.tsx` for the interval control before
  writing a test against it.
- Every entry tagged `gui` in this file is out of scope for headless Stage 1/2
  execution under the current hard rules (no GUI interaction) — they need a future
  pass with Playwright/native event injection, not chrome-devtools.
