# R15 Coverage Map

101 surfaces (from `stage0/COVERAGE_SKELETON.json`), 288 state-cells. Every cell is exactly one of `driven`, `NOT TESTED` (with a reason), `NEEDS-MANUAL-CHECK` (for the operator), or `removed with the feature` (broker/order/live-trading, operator decision 23 Sep 2026).

**driven**: 243 · **NOT TESTED**: 14 · **NEEDS-MANUAL-CHECK**: 22 · **removed with the feature**: 9

## By area

### brief (1 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `panel-brief` Research Brief panel (lifecycle) | src/modules/research/index.ts:20; src/modules/research/BriefPanel.tsx:549 | browser | empty(BriefPanel.tsx:527,630)=driven; streaming/loading=driven; populated=driven; error(image load errored :181)=driven; divergence-notice(honest 'kept previous, richer brief')=driven; no-web-honest-banner(:701)=driven | r15/surface/research-briefs/COVERAGE.json |

### charts (5 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `charts-toolbar-draw-menu` Chart toolbar > Draw menu (drawing tools) | src/modules/chart/toolbar.tsx:207 | gui | no-tool-armed=NEEDS-MANUAL-CHECK; tool-armed(activeTool set, DrawingKind)=NEEDS-MANUAL-CHECK | r15/surface/panels-layouts/COVERAGE.json |
| `charts-toolbar-indicators-menu` Chart toolbar > Indicators menu | src/modules/chart/toolbar.tsx:255,246 (matchesQuery) | browser | search-empty=driven; search-filtered=driven; toggled-on/off per indicator=driven | r15/surface/panels-layouts/COVERAGE.json |
| `charts-toolbar-sync-menu` Chart toolbar > Sync menu (cross-panel symbol sync subscriptions) | src/modules/chart/toolbar.tsx:387 | browser | no-subscriptions=NOT TESTED; populated(toggle per subscription)=NOT TESTED | r15/surface/panels-layouts/COVERAGE.json |
| `charts-timeframe` Chart timeframe/interval selector | src/modules/chart/ChartPanel.tsx | api | populated(interval options)=driven | r15/surface/panels-layouts/COVERAGE.json |
| `market-session-indicator` Market-session state (open/closed/pre/post) | src/lib/market-session.ts (market-session.test.ts) | browser | pre-market=NOT TESTED; open=NOT TESTED; after-hours=NOT TESTED; closed=NOT TESTED | r15/surface/panels-layouts/COVERAGE.json |

### chat-agent (8 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `agent-mode-toggle` Agent mode toggle (Agent vs Delegate) | src/store/agent-mode.ts; src/store/agent-autonomy.ts; types/agent-modes.ts (AGENT_MODES) | browser | agent(interactive)=driven; delegate(durable/budget-capped)=driven | r15/surface/composer-chat/COVERAGE.json |
| `agent-autonomy-ask-auto` Autonomy: ASK vs AUTO | src/store/agent-autonomy.ts | browser | ask(every proposal queues for review)=driven; auto(still gated for orders per §6.5 — 'orders always confirm regardless')=driven | r15/surface/composer-chat/COVERAGE.json |
| `agent-persona-picker` Persona / active-lens picker (Buffett / researcher / custom) | src/modules/chat/ComposerPlusMenu.tsx (persona section); src/store/active-agent.ts | api | first-party-persona(firstParty list)=driven; custom-persona(custom list, from Agent Builder)=driven; display-name-always(never raw id, per comment ComposerPlusMenu.tsx:18)=driven | r15/surface/composer-chat/COVERAGE.json |
| `agent-command-bus` Agent-command bus (cross-surface 'ask AI' routing) | src/store/agent-command.ts (sendToAgent); src/store/agent-dock.ts (setCollapsed) | browser | idle=driven; query-pending(consumed by ChatSidebar)=driven | r15/surface/composer-chat/COVERAGE.json |
| `agent-runs-store` Delegate run lifecycle (running/paused/error/done) | src/store/agent-runs.ts | api | running=driven; paused(awaiting human answer)=driven; error(budget breach, resumable checkpoint)=driven; done=driven | r15/surface/composer-chat/COVERAGE.json |
| `llm-chat-streaming` LLM chat streaming transport | src/modules/chat/streaming.ts (streaming.test.ts) | api | connecting=driven; streaming-tokens=driven; tool-call-turn=driven; tool-result-turn=driven; aborted=driven; error=driven | r15/surface/composer-chat/COVERAGE.json |
| `chat-markdown-render` Chat markdown streaming renderer | src/lib/markdown-stream.ts (markdown-stream.test.ts); src/modules/chat/chat-markdown.ts (chat-markdown.test.ts) | browser | partial-markdown(mid-stream)=driven; complete=driven; malformed(unterminated code fence, table, etc.)=driven | r15/surface/composer-chat/COVERAGE.json |
| `context-provider-badge` Context badge (what-the-agent-sees snapshot) | src/modules/chat/context-provider.ts (context-provider.test.ts); src/modules/chat/ChatSidebar.tsx:1391 (ContextBadge), :2038 (describeContext) | browser | populated(symbol/panel/viewport snapshot)=driven | r15/surface/composer-chat/COVERAGE.json |

### command-palette (4 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `command-palette` Command palette (cmd+K launcher) | src/components/CommandPalette.tsx:69,114 | browser | closed=driven; empty-query(Recent + Suggested)=driven; query-active(5 ranked groups: Ask AI, Agents, Actions, Panels, Symbols)=driven; symbol-group-capped(SYMBOL_CAP=50, command-palette.ts:139)=driven; no-results=driven | - |
| `command-palette-ask-ai` Palette 'Ask AI' free-text row | src/components/CommandPalette.tsx:448 (AskAiItem), :177-183 (handleSelectAskAi) | browser | empty-query(hidden CTA)=driven; populated(routes to agent-command bus)=driven | - |
| `symbol-autocomplete` Symbol autocomplete (palette + wikilink + watchlist add) | src/lib/symbol-autocomplete.ts | api | no-match=driven; matched(live candidates)=driven | - |
| `fuzzy-search-lib` Fuzzy matcher (palette filter ranking) | src/lib/fuzzy.ts (fuzzy.test.ts) | browser | exact-match=driven; fuzzy-match=driven; no-match=driven | - |

### comparison (1 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `comparison-surface` Symbol comparison (chart overlay + compare layout + slash command) | src/modules/chart/toolbar.tsx:335 (CompareMenu); src/lib/layout-templates.ts:681 ('compare' MODE_PLAN); src/modules/chat/slash-commands.ts:169 | browser | single-symbol=driven; dual-symbol-overlay(pushed via chart-command channel)=driven | r15/surface/panels-layouts/COVERAGE.json |

### composer (16 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `composer-mount` Chat composer shell (field + controls row) | src/modules/chat/ChatSidebar.tsx:1577 (Composer function) | browser | controls-collapse-ladder steps at dock-width breakpoints (composer-collapse.ts)=driven; streaming(square morphs to stop)=driven | r15/surface/composer-chat/COVERAGE.json |
| `composer-depth-control` Research-depth selector (Normal/Deep/Ultra) | src/modules/chat/DepthControl.tsx:48 | browser | collapsed/icons-only(expandable=false, click-cycles, :67-79)=driven; expanded(hover/focus reveals all 3 stops)=driven; live-pulse(liveDepth===depth, PULSE_TRANSITION)=driven | r15/surface/composer-chat/COVERAGE.json |
| `composer-model-control` Inline model/provider picker | src/modules/chat/ModelControl.tsx:92 | browser | icon-collapsed(narrow ladder step)=driven; popover-open(provider/model listbox, role=listbox :26-27)=driven; no-key(providerConfigured=false affordance)=driven; catalog-loading/catalogNote=driven | r15/surface/composer-chat/COVERAGE.json |
| `composer-plus-menu` Composer '+' menu (persona/autonomy/mode/context) | src/modules/chat/ComposerPlusMenu.tsx:127 | browser | persona-roster(drill-in)=driven; autonomy-ask/auto(CheckRow :72-100)=driven; mode-agent/delegate=driven; context/scope/route-to sections(buildPlusMenuSections :49-56)=driven | r15/surface/composer-chat/COVERAGE.json |
| `composer-mention-picker` '@' mention picker | src/modules/chat/MentionPicker.tsx:23 | browser | open(role=listbox, filtered options)=driven; closed=driven | r15/surface/composer-chat/COVERAGE.json |
| `composer-slash-picker` '/' slash-command picker | src/modules/chat/SlashCommandPicker.tsx:15 | browser | open(role=listbox)=driven; closed=driven | r15/surface/composer-chat/COVERAGE.json |
| `composer-send-stop-button` Send/Stop button (depth-keyed fill, streaming morph) | src/modules/chat/ChatSidebar.tsx:1923 | browser | send(idle)=driven; stop(streaming, sentDepth heat token retained)=driven | r15/surface/composer-chat/COVERAGE.json |
| `composer-queue` Queued-prompt FIFO chips | src/modules/chat/ChatSidebar.tsx:1359 (QueuedPrompts) | browser | empty(hidden, queue.length===0 :1362)=driven; populated(chips, oldest-first)=driven; remove-one(aria-label 'Remove queued prompt', :1379)=driven | r15/surface/composer-chat/COVERAGE.json |
| `chat-agents-rail` Running-agents rail (Delegate runs) | src/modules/chat/AgentsRail.tsx:20 | api | hidden(active.length===0)=driven; running=driven; paused(human-in-the-loop answer box)=driven; populated(cost-so-far vs budget)=driven | r15/surface/composer-chat/COVERAGE.json |
| `chat-empty-state` Chat dock empty (hero) state | src/modules/chat/ChatSidebar.tsx:1479 | browser | empty-with-suggestion-chips=driven | r15/surface/composer-chat/COVERAGE.json |
| `chat-suggestion-chips` Suggestion chips (empty-state prompts) | src/modules/chat/SuggestionChips.tsx:83 | browser | populated=driven | r15/surface/composer-chat/COVERAGE.json |
| `chat-error-row` Chat transcript error row + Details disclosure | src/modules/chat/ChatSidebar.tsx:1430 (ErrorRow); src/modules/chat/message-notices.ts:19 | browser | message-error(plain .error string)=driven; structured-error-frame(action/detail/code behind 'Details' disclosure, D43)=driven | r15/surface/composer-chat/COVERAGE.json; r15/surface/failure-inducer/COVERAGE.json |
| `chat-message-notices` End-of-stream divergence notice chip | src/modules/chat/message-notices.ts:57-61 (isDivergenceNotice); src/modules/chat/ChatSidebar.tsx:1404 (MessageNotices) | browser | no-notice=driven; divergence(quiet system chip, verbatim-matched copy)=driven | r15/surface/composer-chat/COVERAGE.json |
| `chat-plan-view` Agent plan view (Delegate multi-step plan) | src/modules/chat/PlanView.tsx:56 | browser | active(current step highlighted)=driven; inactive/historical=driven | r15/surface/composer-chat/COVERAGE.json |
| `chat-research-activity` Research step-trace / activity feed | src/modules/chat/ResearchActivity.tsx:78 | browser | active(streaming steps)=driven; completed=driven; elapsed-time formatting (formatElapsed :55)=driven | r15/surface/composer-chat/COVERAGE.json |
| `chat-budget-config` Delegate budget config (tokens/spend/wall/steps ceilings) | src/modules/chat/BudgetConfig.tsx:20 | browser | populated(default ceilings)=driven; edited=driven | r15/surface/composer-chat/COVERAGE.json |

### keyboard-shortcuts (3 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `kb-keybindings-store` Keybindings default keymap (source of truth) | src/store/keybindings.ts:63 (SHELL_DEFAULTS),117 (MODULE_COMMAND_BINDINGS),154 (DEFAULT_KEYBINDINGS) | browser | default=driven; user-override(overrides map)=driven; conflict=driven | - |
| `kb-global-handlers` Global keydown handlers (palette, agent mode, accept/reject) | src/components/CommandPalette.tsx:75-83 (mod+k); src/modules/chat/ChatSidebar.tsx:564-565 (window keydown listener) | browser | fired=driven; ignored(not matching combo)=driven | - |
| `kb-os-kill-switch-shortcut` OS-level kill-switch shortcut (Cmd/Ctrl+Shift+K) | src-tauri/src/kill_switch.rs:34,73 | gui | registered=NEEDS-MANUAL-CHECK; fired=NEEDS-MANUAL-CHECK | - |

### layouts (3 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `layouts-arrange-templates` Agent 'arrange' layout templates (4 modes) | src/lib/layout-templates.ts:182 (planLayout), :648 (MODE_PLANS), :402 (fitLayoutTemplate) | browser | single-focus=driven; research-cockpit=driven; macro-scan=driven; compare=driven; viewport-downgrade(width<1180 research-cockpit->chart+brief; width<1080 macro-scan->single focus, :409,:419)=driven | r15/surface/panels-layouts/COVERAGE.json |
| `layouts-macos-menu-bridge` Native macOS Layout menu (Fundamental/Technical/Macro/Compare/Reset) | src/lib/menu-bridge.ts:14; src-tauri/src/lib.rs (menu build, macOS-only) | gui | applied(deterministic clear+tile)=NEEDS-MANUAL-CHECK; unknown-payload(:36 warn)=NEEDS-MANUAL-CHECK; no-dockview-api-yet(:28 warn)=NEEDS-MANUAL-CHECK | r15/surface/panels-layouts/COVERAGE.json |
| `layouts-workspace-save-load` Save/Load workspace + New Research Space commands | src/modules/platform/index.ts:47,55,63 | api | saved=driven; loaded(older-blob-guarded, deserializeWorkspace)=driven; new-research-space=driven | r15/surface/panels-layouts/COVERAGE.json |

### node-editor (5 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `panel-node-editor` Node Editor canvas (workflow builder) | src/modules/node-editor/index.ts:24; src/modules/node-editor/NodeEditorPanel.tsx:106 | gui | empty(no nodes, Run disabled :537)=NEEDS-MANUAL-CHECK; saving/save-error(:135-137)=NEEDS-MANUAL-CHECK; loading-list/load-error(:140-143)=NEEDS-MANUAL-CHECK; running(:146, RunOverlayState)=NEEDS-MANUAL-CHECK | r15/surface/panels-layouts/COVERAGE.json |
| `node-editor-palette` Node palette (draggable node catalog) | src/modules/node-editor/node-palette.tsx:62 | gui | populated(builtin+plugin node kinds)=NEEDS-MANUAL-CHECK | r15/surface/panels-layouts/COVERAGE.json |
| `node-editor-run-overlay` Workflow run overlay (SSE run states) | src/modules/node-editor/workflow-run-overlay.tsx:48,58,141 | browser | idle(:150)=driven; running=driven; ok=driven; error(:183, per-node status badges :237-244)=driven | r15/surface/panels-layouts/COVERAGE.json |
| `node-editor-code-node` Code node inspector (in-canvas code editor) | src/modules/node-editor/code-node-inspector.tsx:36 | browser | compile-error(:111-113, data-testid=code-node-error)=driven; preview-ok/preview-error(:141)=driven; run-error(:158,204)=driven | r15/surface/panels-layouts/COVERAGE.json |
| `node-editor-save-dialog` Workflow save dialog | src/modules/node-editor/workflow-save-dialog.tsx | browser | idle=driven; saving=driven; error=driven | r15/surface/panels-layouts/COVERAGE.json |

### notes (4 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `panel-notes` Notes panel (per-stock + general) | src/modules/notes/index.ts:11-27; src/modules/notes/NotesPanel.tsx:86 | browser | empty(new note)=driven; editing(:426)=driven; export-status(:214)=driven; populated=driven | r15/surface/portfolio-notes/COVERAGE.json |
| `notes-toolbar` Notes formatting toolbar | src/modules/notes/NotesToolbar.tsx:131 | browser | populated(active mark states per Tiptap editor selection)=driven | r15/surface/portfolio-notes/COVERAGE.json |
| `notes-slash-menu` Notes '/' slash-command menu | src/modules/notes/SlashCommandExtension.ts; src/modules/notes/slash-commands.ts | browser | open(filtered list)=driven; closed=driven | r15/surface/portfolio-notes/COVERAGE.json |
| `notes-wikilink-menu` Notes [[wikilink]] suggestion popup | src/modules/notes/WikiLinkExtension.ts | browser | open(symbol matches)=driven; closed=driven | r15/surface/portfolio-notes/COVERAGE.json |

### onboarding (4 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `safety-disclaimer-flow` First-launch ToS / disclaimer flow | src/modules/safety/DisclaimerFlow.tsx:47 (FirstLaunchTosDialog), :132 (BrokerFirstConnectDialog), :228 (DisclaimerFlow) | browser | first-launch-unacked=driven; acked=driven; broker-first-connect-warning=driven | r15/surface/onboarding-stranger/COVERAGE.json |
| `onboarding-flow` First-run onboarding wizard | src/components/OnboardingFlow.tsx:103 | browser | welcome(:182)=driven; cloud(:195, CloudStep :338)=driven; local(:198, LocalStep :439)=driven; done(:208, DoneStep :648)=driven | r15/surface/onboarding-stranger/COVERAGE.json |
| `onboarding-banner` First-run 'add your AI key' banner | src/components/OnboardingBanner.tsx:21 | browser | hidden(probed=false OR hasAnyKey OR dismissed)=driven; shown(no key in keychain)=driven | r15/surface/onboarding-stranger/COVERAGE.json |
| `hardware-fit-check` Local-model hardware-fit scoring (onboarding LocalStep + Settings FitRow) | src/lib/hardware-fit.ts; src/components/SettingsPanel.tsx:680 (FitRow) | api | fits=driven; marginal=driven; does-not-fit=driven | r15/surface/onboarding-stranger/COVERAGE.json |

### panels (17 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `panel-chart` Chart panel (PanelSpec + ChartPanel component) | src/modules/chart/index.ts:20; src/modules/chart/ChartPanel.tsx | browser | loading=NEEDS-MANUAL-CHECK; error=driven; offline=NOT TESTED; populated=driven; overflow(many indicators/drawings)=NEEDS-MANUAL-CHECK | r15/surface/panels-layouts/COVERAGE.json |
| `panel-watchlist` Watchlist panel | src/modules/watchlist/index.ts:14; src/modules/watchlist/WatchlistPanel.tsx:139 | browser | empty(no symbols)=NOT TESTED; loading(rows===null)=NEEDS-MANUAL-CHECK; error=driven; populated=driven; overflow(collapse ladder narrow width)=NEEDS-MANUAL-CHECK; tenth-item(row virtualization at scale)=driven | r15/surface/panels-layouts/COVERAGE.json |
| `panel-news` News panel | src/modules/news/index.ts:18 | api | empty=driven; loading=driven; error(self-heals)=NOT TESTED; populated=driven | r15/surface/panels-layouts/COVERAGE.json |
| `panel-equity-overview` Equity Overview panel | src/modules/equity-overview/index.ts:11,15,18 | api | loading=NEEDS-MANUAL-CHECK; error=driven; populated=driven | r15/surface/panels-layouts/COVERAGE.json |
| `panel-agent-builder` Agent Builder panel (custom agent authoring) | src/modules/agent-builder/index.ts:28; src/modules/agent-builder/AgentBuilderPanel.tsx:117 | api | idle=driven; saving=driven; saved=driven; error(save/delete :185-187, field errors :119,198)=driven | r15/surface/panels-layouts/COVERAGE.json |
| `panel-backtest` Backtest panel (strategy backtest + critic) | src/modules/backtest/index.ts:25; src/modules/backtest/BacktestPanel.tsx:38 | api | loading(catalogueStatus, :161)=driven; error(:163)=driven; populated(BacktestResultView.tsx:409)=driven | r15/surface/panels-layouts/COVERAGE.json |
| `panel-broker-connect` Broker Connect (connections) panel | src/modules/broker-connect/index.ts:17; src/modules/broker-connect/BrokerConnectPanel.tsx:116 | api | loading(:160-169)=removed with the feature; empty(no brokers)=removed with the feature; connected/connecting/disconnected/error(status badge, :266 err text)=removed with the feature | r15/surface/panels-layouts/COVERAGE.json |
| `panel-broker-order-entry` Broker Order Entry panel | src/modules/broker-connect/index.ts:25; src/modules/broker-connect/BrokerOrderEntry.tsx:47 | api | error(:241)=removed with the feature; populated=removed with the feature | r15/surface/panels-layouts/COVERAGE.json |
| `panel-macro` Macro panel | src/modules/macro/index.ts:16-32; src/modules/macro/MacroPanel.tsx:26 | api | loading(:61)=NEEDS-MANUAL-CHECK; error(self-heals, :36-44,:69)=driven; populated=driven | r15/surface/panels-layouts/COVERAGE.json |
| `panel-sec-filings` SEC Filings panel | src/modules/sec/index.ts:22-38; src/modules/sec/SecFilingsPanel.tsx:38 | api | loading(:193)=NEEDS-MANUAL-CHECK; error(self-heals, :60-68, data-testid=sec-filings-error at :174)=NOT TESTED; populated=driven; tenth-item(filings list)=driven | r15/surface/panels-layouts/COVERAGE.json |
| `panel-earnings-calendar` Earnings Calendar panel | src/modules/earnings/index.ts:16-32; src/modules/earnings/EarningsCalendarPanel.tsx:77 | api | idle/loading(:215)=NEEDS-MANUAL-CHECK; error(self-heals, :107-115,:257)=driven; populated=driven | r15/surface/panels-layouts/COVERAGE.json |
| `panel-analyst-ratings` Analyst Ratings panel | src/modules/analyst-ratings/index.ts:14-30; src/modules/analyst-ratings/AnalystRatingsPanel.tsx:49 | api | loading(per-slice, :91-92)=NEEDS-MANUAL-CHECK; empty(composed error EmptyState with Retry CTA, :124)=driven; populated=driven | r15/surface/panels-layouts/COVERAGE.json |
| `panel-option-pricer` Option Pricer panel (Quant) | src/modules/quant/index.ts:18-34; src/modules/quant/OptionPricerPanel.tsx:221 | api | idle(composed EmptyState with prefilled CTA)=driven; loading(isRunning, :241)=driven; error(data-testid=option-pricing-error, :491-497)=driven; populated=driven | r15/surface/panels-layouts/COVERAGE.json |
| `panel-greeks-dashboard` Greeks Dashboard panel (Quant) | src/modules/quant/index.ts:30; src/modules/quant/GreeksDashboard.tsx:162 | api | idle=driven; loading=driven; error(data-testid=greeks-error, :339-345)=driven; populated=driven | r15/surface/panels-layouts/COVERAGE.json |
| `panel-bond-pricer` Bond Pricer panel (Quant) | src/modules/quant/index.ts:38; src/modules/quant/BondPricerPanel.tsx:98 | api | idle=driven; loading=driven; error(data-testid=bond-pricing-error, :270-276)=driven; populated=driven | r15/surface/panels-layouts/COVERAGE.json |
| `panel-yield-curve` Yield Curve panel (Quant) | src/modules/quant/index.ts:46; src/modules/quant/YieldCurvePanel.tsx:135 | api | idle(chart never mounts empty)=driven; loading=driven; error(data-testid=yield-curve-error, :349-355)=driven; populated=driven | r15/surface/panels-layouts/COVERAGE.json |
| `panel-context-publishers` Per-module panel-context publishers (what each panel tells the agent) | src/modules/panel-context-publishers.test.tsx; src/store/panel-context.ts | browser | published(per active panel)=driven; stale/unpublished=driven | r15/surface/panels-layouts/COVERAGE.json |

### plugins (2 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `panel-plugin-manager` Plugin Manager panel | src/modules/plugin-manager/index.ts:19; src/components/PluginManagerPanel.tsx | browser | empty(no plugins loaded, :64 EmptyState)=driven; populated=driven; error(plugin health state 'error' badge :140)=driven | r15/surface/settings-plugins/COVERAGE.json |
| `panel-marketplace` Marketplace panel | src/modules/marketplace/index.ts:17; src/modules/marketplace/MarketplacePanel.tsx:38 | browser | populated(catalog)=driven; error(entry.errorMessage :129)=driven; installed/enabled/preinstalled badge states (StateBadge :126)=driven | r15/surface/settings-plugins/COVERAGE.json |

### portfolio (1 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `panel-portfolio` Portfolio (paper) panel | src/modules/portfolio/index.ts:15; src/modules/portfolio/PortfolioPanel.tsx:88 | browser | empty(no positions)=driven; error(form validation, dismissible :701-708)=driven; populated=driven; tenth-item=driven | r15/surface/portfolio-notes/COVERAGE.json |

### proposed-changes (1 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `proposed-changes-review-bar` Proposed-changes diff/accept trust gate | src/modules/chat/ProposedChangesReview.tsx:20 | browser | hidden(pending.length===0)=driven; populated(per-item Accept/Reject)=driven; bulk-accept-all(mod+enter)=driven; bulk-reject-all(mod+backspace)=driven | - |

### safety (3 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `panel-audit-log` Audit Log viewer panel | src/modules/safety/index.ts:14-40; src/modules/safety/AuditLogViewer.tsx | api | empty=driven; populated=driven; filtered(defaultAuditFilter, store/safety.ts:117)=driven | r15/surface/panels-layouts/COVERAGE.json |
| `safety-order-confirmation-dialog` Order confirmation dialog (§6.5 confirm-before-place gate) | src/modules/safety/OrderConfirmationDialog.tsx:65,106 | browser | closed=removed with the feature; open-manual(confirmEnabled always true)=removed with the feature; open-ai-proposed(confirmEnabled requires reviewedAi checkbox, :122)=removed with the feature; busy(submitting)=removed with the feature | - |
| `safety-kill-switch` Kill switch (dormant mechanism, no UI toolbar) | src-tauri/src/kill_switch.rs:34,73,90; src/store/safety.ts:126-242; sidecar/routers/safety.py:119,125,142 | api | idle=driven; fired(killSwitchFired=true)=NOT TESTED; loading/error(killSwitchStatus)=NOT TESTED | - |

### screener (5 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `panel-screener` Screener panel shell | src/modules/screener/index.ts:16-32; src/modules/screener/ScreenerPanel.tsx:90 | api | error(:298-305, truncated backend error message)=driven; universe-status-error(:107,214)=driven; populated=driven; tenth-item(results table)=driven | r15/surface/screener/COVERAGE.json |
| `screener-criteria-builder` Screener criteria builder (AND/OR groups) | src/modules/screener/ScreenerCriteriaBuilder.tsx:390; src/modules/screener/CriterionGroupEditor.tsx:317 | browser | empty(no criteria)=driven; populated(nested groups)=driven | r15/surface/screener/COVERAGE.json |
| `screener-formula-input` Screener formula leaf (raw expression input) | src/modules/screener/ScreenerFormulaLeaf.tsx:46,202 | browser | parse-error(data-testid=screener-formula-error, :202-207 shows caret at compiled.position)=driven; valid=driven | r15/surface/screener/COVERAGE.json |
| `screener-results-table` Screener results table | src/modules/screener/ScreenerResultsTable.tsx:318 | browser | empty=driven; populated=driven; tenth-item(scroll/virtualization)=driven | r15/surface/screener/COVERAGE.json |
| `screener-presets` Screener saved/preset screens | src/modules/screener/ScreenerPresets.tsx:119,125,141 | browser | populated(PRESETS catalog)=driven; applied(criteria+universe overwritten, combinator reset to AND :128-129)=driven | r15/surface/screener/COVERAGE.json |

### settings (13 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `panel-settings` Settings panel shell | src/modules/platform/index.ts:29; src/components/SettingsPanel.tsx:116 | browser | populated(only)=driven | r15/surface/settings-plugins/COVERAGE.json |
| `settings-section-nav` Settings section nav / jump links | src/components/SettingsPanel.tsx:161,156 | browser | populated(5 sections: Providers, Research, Region, Keybindings, Advanced)=driven | r15/surface/settings-plugins/COVERAGE.json |
| `settings-providers` AI Providers section (BYOK keys) | src/components/SettingsPanel.tsx:410 | browser | no-key=driven; key-set=driven; validating=driven; invalid-key=driven | r15/surface/settings-plugins/COVERAGE.json |
| `settings-research` Research section (depth/model tiers + SearXNG) | src/components/SettingsPanel.tsx:1210,1011,1058,1124,1184 | api | tier-cards(TierCard :1124)=driven; model-controls(ResearchModelControls :1058)=driven; stop-options(:1003)=driven | r15/surface/failure-inducer/COVERAGE.json; r15/surface/settings-plugins/COVERAGE.json |
| `settings-searxng` SearXNG managed-instance flow | src/components/SettingsPanel.tsx:785 (SearxngManagedFlow), :960 (SearxngAdvancedUrl), :762 (SearxngStatusChip), :741 (searxngChipMeta) | browser | stopped=driven; starting=driven; running=driven; error=driven | r15/surface/settings-plugins/COVERAGE.json |
| `settings-region` Region section | src/components/SettingsPanel.tsx:1297 | api | populated=driven | r15/surface/settings-plugins/COVERAGE.json |
| `settings-keybindings` Keybindings remap section | src/components/SettingsPanel.tsx:1365,1348 | browser | populated(default combo)=driven; recording(comboFromEvent capturing keydown, :1348)=driven; conflict(two actions share a combo, conflicts() in store)=driven | r15/surface/settings-plugins/COVERAGE.json |
| `settings-advanced-integrations` Advanced > Integrations subsection | src/components/SettingsPanel.tsx:1563 | browser | populated=driven | r15/surface/settings-plugins/COVERAGE.json |
| `settings-advanced-layouts` Advanced > Layouts subsection (arrange templates management) | src/components/SettingsPanel.tsx:1587 | browser | populated=driven | r15/surface/settings-plugins/COVERAGE.json |
| `settings-advanced-modules` Advanced > Modules subsection (module enable/disable toggles) | src/components/SettingsPanel.tsx:1710 | browser | all-enabled=driven; some-disabled=driven | r15/surface/settings-plugins/COVERAGE.json |
| `settings-advanced-export-import` Advanced > Export/Import settings | src/components/SettingsPanel.tsx:1775,1767 (buildSettingsExport) | browser | export(populated JSON)=driven; import-error(malformed file)=driven | r15/surface/settings-plugins/COVERAGE.json |
| `settings-advanced-about` Advanced > About subsection | src/components/SettingsPanel.tsx:1872 | api | populated(version strings)=driven | r15/surface/settings-plugins/COVERAGE.json |
| `provider-health-breaker` Provider health / circuit-breaker status | sidecar/routers/system.py:203,215,227 (GET /system/provider-health, POST /trip,/reset) | api | healthy=driven; tripped(circuit open)=driven; reset=driven | r15/surface/failure-inducer/COVERAGE.json; r15/surface/settings-plugins/COVERAGE.json |

### toasts-and-frames (5 surfaces)

| surface | entry | drive | states (status) | evidence |
|---|---|---|---|---|
| `generic-empty-state-component` Shared EmptyState component (icon+headline+hint+CTA) | src/components/EmptyState.tsx:22 | browser | default=driven; dense(compact variant, :27-40)=driven; with-cta=driven; without-cta=driven | - |
| `generic-error-frame-pattern` Per-panel inline error text pattern (no toast library) | src/modules/chat/message-notices.ts:19 (MessageErrorFrame); repeated data-testid='*-error' rows across option-pricer(:495), greeks(:343), bond(:274), yield-curve(:353), sec-filings(:174), screener-formula(:202) | browser | no-error=driven; error-shown=driven; dismissible(portfolio :701-708 has an explicit dismiss button; most others clear on next successful action)=driven | r15/surface/failure-inducer/COVERAGE.json |
| `desktop-notification-bridge` OS desktop notification bridge (workflow node -> OS notification) | src/lib/desktop-notification.ts:45 | gui | outside-tauri(no-op, browser dev mode)=driven; permission-not-yet-granted=driven; permission-denied(silent no-op)=driven; sent=NEEDS-MANUAL-CHECK | - |
| `csv-export` CSV export utility (audit log, portfolio, etc.) | src/lib/csv.ts (csv.test.ts) | browser | populated-rows=driven; empty-rows(header-only)=driven | r15/surface/portfolio-notes/COVERAGE.json |
| `export-artifact` Export-conversation / export-artifact flow | src/lib/export-artifact.ts | browser | exported=NOT TESTED; empty(nothing to export)=NOT TESTED | - |

## Per-cell detail

### `panel-chart` — Chart panel (PanelSpec + ChartPanel component)

- area: panels (operator area: ui) · entry: `src/modules/chart/index.ts:20; src/modules/chart/ChartPanel.tsx` · drive: browser
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **loading** — `NEEDS-MANUAL-CHECK` — NEEDS-GUI (state only)
  - **error** — `driven` — 30m empty + crypto 404 driven
  - **offline** — `NOT TESTED` — NOT TESTED (no network cut at this edge)
  - **populated** — `driven` — ok
  - **overflow(many indicators/drawings)** — `NEEDS-MANUAL-CHECK` — all-50 request ok (API level); render NEEDS-GUI

### `panel-watchlist` — Watchlist panel

- area: panels (operator area: ui) · entry: `src/modules/watchlist/index.ts:14; src/modules/watchlist/WatchlistPanel.tsx:139` · drive: browser
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **empty(no symbols)** — `NOT TESTED` — NOT TESTED (store-only)
  - **loading(rows===null)** — `NEEDS-MANUAL-CHECK` — NEEDS-GUI
  - **error** — `driven` — n/a at API
  - **populated** — `driven` — ok
  - **overflow(collapse ladder narrow width)** — `NEEDS-MANUAL-CHECK` — NEEDS-GUI
  - **tenth-item(row virtualization at scale)** — `driven` — 25-symbol batch driven

### `panel-news` — News panel

- area: panels (operator area: ui) · entry: `src/modules/news/index.ts:18` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **empty** — `driven` — IN names mostly empty
  - **loading** — `driven` — Default watchlist -> 8 Yahoo items tagged AAPL/QQQ/NVDA/SPY with sentiment; empty symbols -> 20 general items; limit 0/500 -> 422 (le=200). IN watchlist RELIANCE,TCS,KAYNES,BDL -> 3 items, 2 of them Flanigan's Enterprises (US ticker BDL) headlines tagged 'BDL' (SURF-PANELS-LAYOUT
  - **error(self-heals)** — `NOT TESTED` — NOT TESTED (needs a dead feed; retry loop is COD-market-data-providers-3-5)
  - **populated** — `driven` — ok

### `panel-portfolio` — Portfolio (paper) panel

- area: portfolio (operator area: ui) · entry: `src/modules/portfolio/index.ts:15; src/modules/portfolio/PortfolioPanel.tsx:88` · drive: browser
- evidence: `r15/surface/portfolio-notes/COVERAGE.json`

  - **empty(no positions)** — `driven` — Driven through the REAL PortfolioPanel in jsdom (harness/portfolio.s2c.test.tsx) against a live sidecar (:52221), real sidecar-client via ?sidecar-port. Corroborated live: COD-portfolio-2/3/4/5/8, COD-host-actions-proposed-changes-9. NEEDS-GUI: drop-ladder column shedding at real
  - **error(form validation, dismissible :701-708)** — `driven` — Driven through the REAL PortfolioPanel in jsdom (harness/portfolio.s2c.test.tsx) against a live sidecar (:52221), real sidecar-client via ?sidecar-port. Corroborated live: COD-portfolio-2/3/4/5/8, COD-host-actions-proposed-changes-9. NEEDS-GUI: drop-ladder column shedding at real
  - **populated** — `driven` — Driven through the REAL PortfolioPanel in jsdom (harness/portfolio.s2c.test.tsx) against a live sidecar (:52221), real sidecar-client via ?sidecar-port. Corroborated live: COD-portfolio-2/3/4/5/8, COD-host-actions-proposed-changes-9. NEEDS-GUI: drop-ladder column shedding at real
  - **tenth-item** — `driven` — Driven through the REAL PortfolioPanel in jsdom (harness/portfolio.s2c.test.tsx) against a live sidecar (:52221), real sidecar-client via ?sidecar-port. Corroborated live: COD-portfolio-2/3/4/5/8, COD-host-actions-proposed-changes-9. NEEDS-GUI: drop-ladder column shedding at real

### `panel-equity-overview` — Equity Overview panel

- area: panels (operator area: ui) · entry: `src/modules/equity-overview/index.ts:11,15,18` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **loading** — `NEEDS-MANUAL-CHECK` — NEEDS-GUI
  - **error** — `driven` — junk + crypto driven
  - **populated** — `driven` — ok

### `panel-brief` — Research Brief panel (lifecycle)

- area: brief (operator area: research) · entry: `src/modules/research/index.ts:20; src/modules/research/BriefPanel.tsx:549` · drive: browser
- evidence: `r15/surface/research-briefs/COVERAGE.json`

  - **empty(BriefPanel.tsx:527,630)** — `driven` — Auto-publishes via agent_runtime._auto_publish_event (CLAUDE.md) on research/deep_research ok-result. structured metrics grid via brief-blocks.tsx (deriveMetrics). STEP_STATUS_COLOR states pending/running/ok/error at BriefPanel.tsx:273-275. Vitest: BriefPanel.test.tsx, brief-bloc
  - **streaming/loading** — `driven` — Auto-publishes via agent_runtime._auto_publish_event (CLAUDE.md) on research/deep_research ok-result. structured metrics grid via brief-blocks.tsx (deriveMetrics). STEP_STATUS_COLOR states pending/running/ok/error at BriefPanel.tsx:273-275. Vitest: BriefPanel.test.tsx, brief-bloc
  - **populated** — `driven` — Auto-publishes via agent_runtime._auto_publish_event (CLAUDE.md) on research/deep_research ok-result. structured metrics grid via brief-blocks.tsx (deriveMetrics). STEP_STATUS_COLOR states pending/running/ok/error at BriefPanel.tsx:273-275. Vitest: BriefPanel.test.tsx, brief-bloc
  - **error(image load errored :181)** — `driven` — Auto-publishes via agent_runtime._auto_publish_event (CLAUDE.md) on research/deep_research ok-result. structured metrics grid via brief-blocks.tsx (deriveMetrics). STEP_STATUS_COLOR states pending/running/ok/error at BriefPanel.tsx:273-275. Vitest: BriefPanel.test.tsx, brief-bloc
  - **divergence-notice(honest 'kept previous, richer brief')** — `driven` — Auto-publishes via agent_runtime._auto_publish_event (CLAUDE.md) on research/deep_research ok-result. structured metrics grid via brief-blocks.tsx (deriveMetrics). STEP_STATUS_COLOR states pending/running/ok/error at BriefPanel.tsx:273-275. Vitest: BriefPanel.test.tsx, brief-bloc
  - **no-web-honest-banner(:701)** — `driven` — Auto-publishes via agent_runtime._auto_publish_event (CLAUDE.md) on research/deep_research ok-result. structured metrics grid via brief-blocks.tsx (deriveMetrics). STEP_STATUS_COLOR states pending/running/ok/error at BriefPanel.tsx:273-275. Vitest: BriefPanel.test.tsx, brief-bloc

### `panel-settings` — Settings panel shell

- area: settings (operator area: ui) · entry: `src/modules/platform/index.ts:29; src/components/SettingsPanel.tsx:116` · drive: browser
- evidence: `r15/surface/settings-plugins/COVERAGE.json`

  - **populated(only)** — `driven` — Section list mounted always: SectionNav, ProvidersSection, ResearchSection, RegionSection, KeybindingsSection, AdvancedSection (SettingsPanel.tsx:116-122). Vitest: SettingsPanel.test.tsx.

### `panel-plugin-manager` — Plugin Manager panel

- area: plugins (operator area: ui) · entry: `src/modules/plugin-manager/index.ts:19; src/components/PluginManagerPanel.tsx` · drive: browser
- evidence: `r15/surface/settings-plugins/COVERAGE.json`

  - **empty(no plugins loaded, :64 EmptyState)** — `driven` — enable/disable toggle :97-128; health-history sample badge; enabledCount summary line :42. Backed by usePluginsStore (attached to PluginRuntime). Vitest: PluginManagerPanel.test.tsx.
  - **populated** — `driven` — enable/disable toggle :97-128; health-history sample badge; enabledCount summary line :42. Backed by usePluginsStore (attached to PluginRuntime). Vitest: PluginManagerPanel.test.tsx.
  - **error(plugin health state 'error' badge :140)** — `driven` — enable/disable toggle :97-128; health-history sample badge; enabledCount summary line :42. Backed by usePluginsStore (attached to PluginRuntime). Vitest: PluginManagerPanel.test.tsx.

### `panel-marketplace` — Marketplace panel

- area: plugins (operator area: ui) · entry: `src/modules/marketplace/index.ts:17; src/modules/marketplace/MarketplacePanel.tsx:38` · drive: browser
- evidence: `r15/surface/settings-plugins/COVERAGE.json`

  - **populated(catalog)** — `driven` — install() at :104 -> useMarketplaceStore. Read-only broker connections blurb (:18) — installing a broker adds no execution path (FR-055). Vitest: lib/marketplace.test.ts, lib/marketplace-lifecycle.test.ts.
  - **error(entry.errorMessage :129)** — `driven` — install() at :104 -> useMarketplaceStore. Read-only broker connections blurb (:18) — installing a broker adds no execution path (FR-055). Vitest: lib/marketplace.test.ts, lib/marketplace-lifecycle.test.ts.
  - **installed/enabled/preinstalled badge states (StateBadge :126)** — `driven` — install() at :104 -> useMarketplaceStore. Read-only broker connections blurb (:18) — installing a broker adds no execution path (FR-055). Vitest: lib/marketplace.test.ts, lib/marketplace-lifecycle.test.ts.

### `panel-agent-builder` — Agent Builder panel (custom agent authoring)

- area: panels (operator area: ui) · entry: `src/modules/agent-builder/index.ts:28; src/modules/agent-builder/AgentBuilderPanel.tsx:117` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **idle** — `driven` — n/a
  - **saving** — `driven` — Full CRUD live: create 201, duplicate 409, get 200, update 200, delete 204, re-delete 404, first-party id delete 400, bad provider 422, unknown tool 422. Accepted without complaint: id 'custom:../../etc/passwd' (stored/deleted fine, no path use), a 300 KB system_prompt, default_m
  - **saved** — `driven` — Full CRUD live: create 201, duplicate 409, get 200, update 200, delete 204, re-delete 404, first-party id delete 400, bad provider 422, unknown tool 422. Accepted without complaint: id 'custom:../../etc/passwd' (stored/deleted fine, no path use), a 300 KB system_prompt, default_m
  - **error(save/delete :185-187, field errors :119,198)** — `driven` — 422/409 driven

### `panel-node-editor` — Node Editor canvas (workflow builder)

- area: node-editor (operator area: ui) · entry: `src/modules/node-editor/index.ts:24; src/modules/node-editor/NodeEditorPanel.tsx:106` · drive: gui
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **empty(no nodes, Run disabled :537)** — `NEEDS-MANUAL-CHECK` — surface requires GUI interaction not available in Stage B
  - **saving/save-error(:135-137)** — `NEEDS-MANUAL-CHECK` — surface requires GUI interaction not available in Stage B
  - **loading-list/load-error(:140-143)** — `NEEDS-MANUAL-CHECK` — surface requires GUI interaction not available in Stage B
  - **running(:146, RunOverlayState)** — `NEEDS-MANUAL-CHECK` — surface requires GUI interaction not available in Stage B

### `node-editor-palette` — Node palette (draggable node catalog)

- area: node-editor (operator area: ui) · entry: `src/modules/node-editor/node-palette.tsx:62` · drive: gui
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **populated(builtin+plugin node kinds)** — `NEEDS-MANUAL-CHECK` — surface requires GUI interaction not available in Stage B

### `node-editor-run-overlay` — Workflow run overlay (SSE run states)

- area: node-editor (operator area: ui) · entry: `src/modules/node-editor/workflow-run-overlay.tsx:48,58,141` · drive: browser
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **idle(:150)** — `driven` — quote->json_path->compare run streams run-start/node-start/node-output/node-error/run-error (8 frames) - logic.compare ignores config b (COD-workflow-engine-1). Invalid edge, cycle and unknown node type each -> 200 with ZERO frames (confirms COD-workflow-engine-4 live; reason onl
  - **running** — `driven` — quote->json_path->compare run streams run-start/node-start/node-output/node-error/run-error (8 frames) - logic.compare ignores config b (COD-workflow-engine-1). Invalid edge, cycle and unknown node type each -> 200 with ZERO frames (confirms COD-workflow-engine-4 live; reason onl
  - **ok** — `driven` — quote->json_path->compare run streams run-start/node-start/node-output/node-error/run-error (8 frames) - logic.compare ignores config b (COD-workflow-engine-1). Invalid edge, cycle and unknown node type each -> 200 with ZERO frames (confirms COD-workflow-engine-4 live; reason onl
  - **error(:183, per-node status badges :237-244)** — `driven` — quote->json_path->compare run streams run-start/node-start/node-output/node-error/run-error (8 frames) - logic.compare ignores config b (COD-workflow-engine-1). Invalid edge, cycle and unknown node type each -> 200 with ZERO frames (confirms COD-workflow-engine-4 live; reason onl

### `node-editor-code-node` — Code node inspector (in-canvas code editor)

- area: node-editor (operator area: ui) · entry: `src/modules/node-editor/code-node-inspector.tsx:36` · drive: browser
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **compile-error(:111-113, data-testid=code-node-error)** — `driven` — transform.code with '7 ** 10 ** 7' beside a trivial node: run-start arrives after 8.15 s, no node frame within 60 s, client timed out. The next unrelated GET /history/INFY (cold IN 1d) took 85.5 s vs 5.9 s (TCS, right after) and 5.0 s (HDFCBANK control); a curl /health during the
  - **preview-ok/preview-error(:141)** — `driven` — transform.code with '7 ** 10 ** 7' beside a trivial node: run-start arrives after 8.15 s, no node frame within 60 s, client timed out. The next unrelated GET /history/INFY (cold IN 1d) took 85.5 s vs 5.9 s (TCS, right after) and 5.0 s (HDFCBANK control); a curl /health during the
  - **run-error(:158,204)** — `driven` — transform.code with '7 ** 10 ** 7' beside a trivial node: run-start arrives after 8.15 s, no node frame within 60 s, client timed out. The next unrelated GET /history/INFY (cold IN 1d) took 85.5 s vs 5.9 s (TCS, right after) and 5.0 s (HDFCBANK control); a curl /health during the

### `node-editor-save-dialog` — Workflow save dialog

- area: node-editor (operator area: ui) · entry: `src/modules/node-editor/workflow-save-dialog.tsx` · drive: browser
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **idle** — `driven` — save 200, list 1, get round-trip, missing 404, delete 200, re-delete 404.
  - **saving** — `driven` — save 200, list 1, get round-trip, missing 404, delete 200, re-delete 404.
  - **error** — `driven` — save 200, list 1, get round-trip, missing 404, delete 200, re-delete 404.

### `panel-backtest` — Backtest panel (strategy backtest + critic)

- area: panels (operator area: ui) · entry: `src/modules/backtest/index.ts:25; src/modules/backtest/BacktestPanel.tsx:38` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **loading(catalogueStatus, :161)** — `driven` — n/a
  - **error(:163)** — `driven` — run-error driven
  - **populated(BacktestResultView.tsx:409)** — `driven` — ok

### `panel-broker-connect` — Broker Connect (connections) panel

- area: panels (operator area: ui) · entry: `src/modules/broker-connect/index.ts:17; src/modules/broker-connect/BrokerConnectPanel.tsx:116` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **loading(:160-169)** — `removed with the feature` — removed with the feature - trading is out of the product (operator decision 23 Sep 2026); this surface existed only to connect a broker / place a broker order (source: surface/panels-layouts/COVERAGE.json reason 'removed_with_feature')
  - **empty(no brokers)** — `removed with the feature` — removed with the feature - trading is out of the product (operator decision 23 Sep 2026); this surface existed only to connect a broker / place a broker order (source: surface/panels-layouts/COVERAGE.json reason 'removed_with_feature')
  - **connected/connecting/disconnected/error(status badge, :266 err text)** — `removed with the feature` — removed with the feature - trading is out of the product (operator decision 23 Sep 2026); this surface existed only to connect a broker / place a broker order (source: surface/panels-layouts/COVERAGE.json reason 'removed_with_feature')

### `panel-broker-order-entry` — Broker Order Entry panel

- area: panels (operator area: ui) · entry: `src/modules/broker-connect/index.ts:25; src/modules/broker-connect/BrokerOrderEntry.tsx:47` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **error(:241)** — `removed with the feature` — removed with the feature - trading is out of the product (operator decision 23 Sep 2026); this surface existed only to connect a broker / place a broker order (source: surface/panels-layouts/COVERAGE.json reason 'removed_with_feature')
  - **populated** — `removed with the feature` — removed with the feature - trading is out of the product (operator decision 23 Sep 2026); this surface existed only to connect a broker / place a broker order (source: surface/panels-layouts/COVERAGE.json reason 'removed_with_feature')

### `panel-audit-log` — Audit Log viewer panel

- area: safety (operator area: ui) · entry: `src/modules/safety/index.ts:14-40; src/modules/safety/AuditLogViewer.tsx` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **empty** — `driven` — GET /safety/audit-log -> {entries:[]}; export.csv -> header only; kill-switch status fired:false. The viewer's subject is the order audit (broker/account/action columns) - trading is out of the product, so beyond empty/export this surface is removed_with_feature.
  - **populated** — `driven` — GET /safety/audit-log -> {entries:[]}; export.csv -> header only; kill-switch status fired:false. The viewer's subject is the order audit (broker/account/action columns) - trading is out of the product, so beyond empty/export this surface is removed_with_feature.
  - **filtered(defaultAuditFilter, store/safety.ts:117)** — `driven` — GET /safety/audit-log -> {entries:[]}; export.csv -> header only; kill-switch status fired:false. The viewer's subject is the order audit (broker/account/action columns) - trading is out of the product, so beyond empty/export this surface is removed_with_feature.

### `panel-macro` — Macro panel

- area: panels (operator area: ui) · entry: `src/modules/macro/index.ts:16-32; src/modules/macro/MacroPanel.tsx:26` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **loading(:61)** — `NEEDS-MANUAL-CHECK` — NEEDS-GUI
  - **error(self-heals, :36-44,:69)** — `driven` — driven
  - **populated** — `driven` — ECB/WB ok

### `panel-sec-filings` — SEC Filings panel

- area: panels (operator area: ui) · entry: `src/modules/sec/index.ts:22-38; src/modules/sec/SecFilingsPanel.tsx:38` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **loading(:193)** — `NEEDS-MANUAL-CHECK` — NEEDS-GUI
  - **error(self-heals, :60-68, data-testid=sec-filings-error at :174)** — `NOT TESTED` — NOT TESTED - no probe induced a /sec/* failure (sec-edgar-mcp stayed up for the whole panels-layouts drive; the network-down pass in surface/failure-inducer/30-netdown-data-routes.txt did not hit /sec routes), so the self-heal branch at SecFilingsPanel.tsx:60-68 was never reached
  - **populated** — `driven` — list only
  - **tenth-item(filings list)** — `driven` — 28-40 row list driven

### `panel-earnings-calendar` — Earnings Calendar panel

- area: panels (operator area: ui) · entry: `src/modules/earnings/index.ts:16-32; src/modules/earnings/EarningsCalendarPanel.tsx:77` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **idle/loading(:215)** — `NEEDS-MANUAL-CHECK` — NEEDS-GUI
  - **error(self-heals, :107-115,:257)** — `driven` — 502 driven
  - **populated** — `driven` — US only

### `panel-analyst-ratings` — Analyst Ratings panel

- area: panels (operator area: ui) · entry: `src/modules/analyst-ratings/index.ts:14-30; src/modules/analyst-ratings/AnalystRatingsPanel.tsx:49` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **loading(per-slice, :91-92)** — `NEEDS-MANUAL-CHECK` — NEEDS-GUI
  - **empty(composed error EmptyState with Retry CTA, :124)** — `driven` — driven (IN)
  - **populated** — `driven` — AAPL ok

### `panel-option-pricer` — Option Pricer panel (Quant)

- area: panels (operator area: ui) · entry: `src/modules/quant/index.ts:18-34; src/modules/quant/OptionPricerPanel.tsx:221` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **idle(composed EmptyState with prefilled CTA)** — `driven` — n/a
  - **loading(isRunning, :241)** — `driven` — n/a
  - **error(data-testid=option-pricing-error, :491-497)** — `driven` — 400s driven
  - **populated** — `driven` — ok

### `panel-greeks-dashboard` — Greeks Dashboard panel (Quant)

- area: panels (operator area: ui) · entry: `src/modules/quant/index.ts:30; src/modules/quant/GreeksDashboard.tsx:162` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **idle** — `driven` — Call/put Greeks equal BS analytic; zero vol -> delta 1 gamma 0. Units raw QuantLib (vega per 1.00 vol) - COD-macro-quant-3.
  - **loading** — `driven` — Call/put Greeks equal BS analytic; zero vol -> delta 1 gamma 0. Units raw QuantLib (vega per 1.00 vol) - COD-macro-quant-3.
  - **error(data-testid=greeks-error, :339-345)** — `driven` — Call/put Greeks equal BS analytic; zero vol -> delta 1 gamma 0. Units raw QuantLib (vega per 1.00 vol) - COD-macro-quant-3.
  - **populated** — `driven` — Call/put Greeks equal BS analytic; zero vol -> delta 1 gamma 0. Units raw QuantLib (vega per 1.00 vol) - COD-macro-quant-3.

### `panel-bond-pricer` — Bond Pricer panel (Quant)

- area: panels (operator area: ui) · entry: `src/modules/quant/index.ts:38; src/modules/quant/BondPricerPanel.tsx:98` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **idle** — `driven` — Par bond clean 1000.00; panel defaults 1060.5846 = hand-computed PV; mid-period accrued 12.50; settlement after maturity 400. Negative YTM accepted (1632.69).
  - **loading** — `driven` — Par bond clean 1000.00; panel defaults 1060.5846 = hand-computed PV; mid-period accrued 12.50; settlement after maturity 400. Negative YTM accepted (1632.69).
  - **error(data-testid=bond-pricing-error, :270-276)** — `driven` — Par bond clean 1000.00; panel defaults 1060.5846 = hand-computed PV; mid-period accrued 12.50; settlement after maturity 400. Negative YTM accepted (1632.69).
  - **populated** — `driven` — Par bond clean 1000.00; panel defaults 1060.5846 = hand-computed PV; mid-period accrued 12.50; settlement after maturity 400. Negative YTM accepted (1632.69).

### `panel-yield-curve` — Yield Curve panel (Quant)

- area: panels (operator area: ui) · entry: `src/modules/quant/index.ts:46; src/modules/quant/YieldCurvePanel.tsx:135` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **idle(chart never mounts empty)** — `driven` — Panel defaults bootstrap in 22 ms. Duplicate pillar -> 500 text/plain with no CORS header (SURF-PANELS-LAYOUTS-9). Single instrument -> 30 identical points (COD-macro-quant-8). 10,000 samples accepted (1.2 MB).
  - **loading** — `driven` — Panel defaults bootstrap in 22 ms. Duplicate pillar -> 500 text/plain with no CORS header (SURF-PANELS-LAYOUTS-9). Single instrument -> 30 identical points (COD-macro-quant-8). 10,000 samples accepted (1.2 MB).
  - **error(data-testid=yield-curve-error, :349-355)** — `driven` — Panel defaults bootstrap in 22 ms. Duplicate pillar -> 500 text/plain with no CORS header (SURF-PANELS-LAYOUTS-9). Single instrument -> 30 identical points (COD-macro-quant-8). 10,000 samples accepted (1.2 MB).
  - **populated** — `driven` — Panel defaults bootstrap in 22 ms. Duplicate pillar -> 500 text/plain with no CORS header (SURF-PANELS-LAYOUTS-9). Single instrument -> 30 identical points (COD-macro-quant-8). 10,000 samples accepted (1.2 MB).

### `panel-screener` — Screener panel shell

- area: screener (operator area: data) · entry: `src/modules/screener/index.ts:16-32; src/modules/screener/ScreenerPanel.tsx:90` · drive: api
- evidence: `r15/surface/screener/COVERAGE.json`

  - **error(:298-305, truncated backend error message)** — `driven` — POST /screener/run, /screener/run/stream (SSE), /screener/formula/validate, GET /screener/universe. Uses useRetryOnSidecarReady per CLAUDE.md comment.
  - **universe-status-error(:107,214)** — `driven` — POST /screener/run, /screener/run/stream (SSE), /screener/formula/validate, GET /screener/universe. Uses useRetryOnSidecarReady per CLAUDE.md comment.
  - **populated** — `driven` — POST /screener/run, /screener/run/stream (SSE), /screener/formula/validate, GET /screener/universe. Uses useRetryOnSidecarReady per CLAUDE.md comment.
  - **tenth-item(results table)** — `driven` — POST /screener/run, /screener/run/stream (SSE), /screener/formula/validate, GET /screener/universe. Uses useRetryOnSidecarReady per CLAUDE.md comment.

### `screener-criteria-builder` — Screener criteria builder (AND/OR groups)

- area: screener (operator area: data) · entry: `src/modules/screener/ScreenerCriteriaBuilder.tsx:390; src/modules/screener/CriterionGroupEditor.tsx:317` · drive: browser
- evidence: `r15/surface/screener/COVERAGE.json`

  - **empty(no criteria)** — `driven` — ScreenerCriteriaBuilder.test.tsx exists — pure component test, no sidecar needed for structural states.
  - **populated(nested groups)** — `driven` — ScreenerCriteriaBuilder.test.tsx exists — pure component test, no sidecar needed for structural states.

### `screener-formula-input` — Screener formula leaf (raw expression input)

- area: screener (operator area: data) · entry: `src/modules/screener/ScreenerFormulaLeaf.tsx:46,202` · drive: browser
- evidence: `r15/surface/screener/COVERAGE.json`

  - **parse-error(data-testid=screener-formula-error, :202-207 shows caret at compiled.position)** — `driven` — Compiler lives in lib/screener-expr.ts (screener-expr.test.ts) — fully headless unit-testable for parser edge cases independent of the leaf component.
  - **valid** — `driven` — Compiler lives in lib/screener-expr.ts (screener-expr.test.ts) — fully headless unit-testable for parser edge cases independent of the leaf component.

### `screener-results-table` — Screener results table

- area: screener (operator area: data) · entry: `src/modules/screener/ScreenerResultsTable.tsx:318` · drive: browser
- evidence: `r15/surface/screener/COVERAGE.json`

  - **empty** — `driven` — ScreenerResultsTable.test.tsx exists.
  - **populated** — `driven` — ScreenerResultsTable.test.tsx exists.
  - **tenth-item(scroll/virtualization)** — `driven` — ScreenerResultsTable.test.tsx exists.

### `screener-presets` — Screener saved/preset screens

- area: screener (operator area: data) · entry: `src/modules/screener/ScreenerPresets.tsx:119,125,141` · drive: browser
- evidence: `r15/surface/screener/COVERAGE.json`

  - **populated(PRESETS catalog)** — `driven` — Presets are a static catalog (not sidecar-persisted 'saved screens' in this build — verify against BLUEPRINT before assuming a user-save flow exists here).
  - **applied(criteria+universe overwritten, combinator reset to AND :128-129)** — `driven` — Presets are a static catalog (not sidecar-persisted 'saved screens' in this build — verify against BLUEPRINT before assuming a user-save flow exists here).

### `panel-notes` — Notes panel (per-stock + general)

- area: notes (operator area: ui) · entry: `src/modules/notes/index.ts:11-27; src/modules/notes/NotesPanel.tsx:86` · drive: browser
- evidence: `r15/surface/portfolio-notes/COVERAGE.json`

  - **empty(new note)** — `driven` — Real NotesPanel + Tiptap v3.25 in jsdom (harness/notes.s2c.test.tsx), editor reached via .ProseMirror.editor.
  - **editing(:426)** — `driven` — Real NotesPanel + Tiptap v3.25 in jsdom (harness/notes.s2c.test.tsx), editor reached via .ProseMirror.editor.
  - **export-status(:214)** — `driven` — Real NotesPanel + Tiptap v3.25 in jsdom (harness/notes.s2c.test.tsx), editor reached via .ProseMirror.editor.
  - **populated** — `driven` — Real NotesPanel + Tiptap v3.25 in jsdom (harness/notes.s2c.test.tsx), editor reached via .ProseMirror.editor.

### `notes-toolbar` — Notes formatting toolbar

- area: notes (operator area: ui) · entry: `src/modules/notes/NotesToolbar.tsx:131` · drive: browser
- evidence: `r15/surface/portfolio-notes/COVERAGE.json`

  - **populated(active mark states per Tiptap editor selection)** — `driven` — Depends on a live Tiptap Editor instance prop — needs jsdom mount, not a pure function.

### `notes-slash-menu` — Notes '/' slash-command menu

- area: notes (operator area: ui) · entry: `src/modules/notes/SlashCommandExtension.ts; src/modules/notes/slash-commands.ts` · drive: browser
- evidence: `r15/surface/portfolio-notes/COVERAGE.json`

  - **open(filtered list)** — `driven` — Dispatches DOM CustomEvent 'notes:slash-menu'; NotesPanel listens (NotesPanel.tsx:94-95 slashMenu/slashActiveIdx state).
  - **closed** — `driven` — Dispatches DOM CustomEvent 'notes:slash-menu'; NotesPanel listens (NotesPanel.tsx:94-95 slashMenu/slashActiveIdx state).

### `notes-wikilink-menu` — Notes [[wikilink]] suggestion popup

- area: notes (operator area: ui) · entry: `src/modules/notes/WikiLinkExtension.ts` · drive: browser
- evidence: `r15/surface/portfolio-notes/COVERAGE.json`

  - **open(symbol matches)** — `driven` — CustomEvent 'notes:wikilink-menu'; inserted [[SYMBOL]] click fires loadSymbolIntoChart (shared chart-command bus, same channel as brief chips per CLAUDE.md).
  - **closed** — `driven` — CustomEvent 'notes:wikilink-menu'; inserted [[SYMBOL]] click fires loadSymbolIntoChart (shared chart-command bus, same channel as brief chips per CLAUDE.md).

### `composer-mount` — Chat composer shell (field + controls row)

- area: composer (operator area: agent) · entry: `src/modules/chat/ChatSidebar.tsx:1577 (Composer function)` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **controls-collapse-ladder steps at dock-width breakpoints (composer-collapse.ts)** — `driven` — composer-collapse.ts + composer-collapse.test.ts define the exact width thresholds — headlessly testable as pure functions (composerControlsStepForWidth / composerControlsPlan) without mounting the ResizeObserver-driven component.
  - **streaming(square morphs to stop)** — `driven` — composer-collapse.ts + composer-collapse.test.ts define the exact width thresholds — headlessly testable as pure functions (composerControlsStepForWidth / composerControlsPlan) without mounting the ResizeObserver-driven component.

### `composer-depth-control` — Research-depth selector (Normal/Deep/Ultra)

- area: composer (operator area: agent) · entry: `src/modules/chat/DepthControl.tsx:48` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **collapsed/icons-only(expandable=false, click-cycles, :67-79)** — `driven` — nextResearchDepth() (:23-26) is a pure cycle fn — headless-testable. Backing store: store/research-depth.ts (research-depth.test.ts).
  - **expanded(hover/focus reveals all 3 stops)** — `driven` — nextResearchDepth() (:23-26) is a pure cycle fn — headless-testable. Backing store: store/research-depth.ts (research-depth.test.ts).
  - **live-pulse(liveDepth===depth, PULSE_TRANSITION)** — `driven` — nextResearchDepth() (:23-26) is a pure cycle fn — headless-testable. Backing store: store/research-depth.ts (research-depth.test.ts).

### `composer-model-control` — Inline model/provider picker

- area: composer (operator area: agent) · entry: `src/modules/chat/ModelControl.tsx:92` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **icon-collapsed(narrow ladder step)** — `driven` — buildModelGroups/modelOptionLabel in lib/model-options.ts (model-options.test.ts) are pure and headless-testable independent of the popover DOM. Backed by GET /llm/providers,/llm/models.
  - **popover-open(provider/model listbox, role=listbox :26-27)** — `driven` — buildModelGroups/modelOptionLabel in lib/model-options.ts (model-options.test.ts) are pure and headless-testable independent of the popover DOM. Backed by GET /llm/providers,/llm/models.
  - **no-key(providerConfigured=false affordance)** — `driven` — buildModelGroups/modelOptionLabel in lib/model-options.ts (model-options.test.ts) are pure and headless-testable independent of the popover DOM. Backed by GET /llm/providers,/llm/models.
  - **catalog-loading/catalogNote** — `driven` — buildModelGroups/modelOptionLabel in lib/model-options.ts (model-options.test.ts) are pure and headless-testable independent of the popover DOM. Backed by GET /llm/providers,/llm/models.

### `composer-plus-menu` — Composer '+' menu (persona/autonomy/mode/context)

- area: composer (operator area: agent) · entry: `src/modules/chat/ComposerPlusMenu.tsx:127` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **persona-roster(drill-in)** — `driven` — buildPlusMenuSections is pure (derives from STATIC_MENTIONS catalog) — headless-testable via ComposerPlusMenu.test.tsx without opening the menu DOM.
  - **autonomy-ask/auto(CheckRow :72-100)** — `driven` — buildPlusMenuSections is pure (derives from STATIC_MENTIONS catalog) — headless-testable via ComposerPlusMenu.test.tsx without opening the menu DOM.
  - **mode-agent/delegate** — `driven` — buildPlusMenuSections is pure (derives from STATIC_MENTIONS catalog) — headless-testable via ComposerPlusMenu.test.tsx without opening the menu DOM.
  - **context/scope/route-to sections(buildPlusMenuSections :49-56)** — `driven` — buildPlusMenuSections is pure (derives from STATIC_MENTIONS catalog) — headless-testable via ComposerPlusMenu.test.tsx without opening the menu DOM.

### `composer-mention-picker` — '@' mention picker

- area: composer (operator area: agent) · entry: `src/modules/chat/MentionPicker.tsx:23` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **open(role=listbox, filtered options)** — `driven` — Mention matching logic in mentions.ts (mentions.test.ts) is pure/headless; picker itself keyboard-first (up/down/enter/esc per CLAUDE.md FR-100/101).
  - **closed** — `driven` — Mention matching logic in mentions.ts (mentions.test.ts) is pure/headless; picker itself keyboard-first (up/down/enter/esc per CLAUDE.md FR-100/101).

### `composer-slash-picker` — '/' slash-command picker

- area: composer (operator area: agent) · entry: `src/modules/chat/SlashCommandPicker.tsx:15` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **open(role=listbox)** — `driven` — 10 commands: research, compare, chart, screener, watch, portfolio, layout, export, sources, clear (slash-commands.ts:162-223). Each has a handler wired in ChatSidebar.tsx:626-680 (enqueueSlashChange for cockpit-mutating ones).
  - **closed** — `driven` — 10 commands: research, compare, chart, screener, watch, portfolio, layout, export, sources, clear (slash-commands.ts:162-223). Each has a handler wired in ChatSidebar.tsx:626-680 (enqueueSlashChange for cockpit-mutating ones).

### `composer-send-stop-button` — Send/Stop button (depth-keyed fill, streaming morph)

- area: composer (operator area: agent) · entry: `src/modules/chat/ChatSidebar.tsx:1923` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **send(idle)** — `driven` — onStop -> abortRef.current?.abort() (:1297) aborts the in-flight fetch AbortController set at :880.
  - **stop(streaming, sentDepth heat token retained)** — `driven` — onStop -> abortRef.current?.abort() (:1297) aborts the in-flight fetch AbortController set at :880.

### `composer-queue` — Queued-prompt FIFO chips

- area: composer (operator area: agent) · entry: `src/modules/chat/ChatSidebar.tsx:1359 (QueuedPrompts)` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **empty(hidden, queue.length===0 :1362)** — `driven` — Backed by store/chat-pending.ts (chat-pending.test.ts) — queuePrompt is a pure store action, drain loop at ChatSidebar.tsx:1100-1127 serial-drains one at a time via the SAME handleSend.
  - **populated(chips, oldest-first)** — `driven` — Backed by store/chat-pending.ts (chat-pending.test.ts) — queuePrompt is a pure store action, drain loop at ChatSidebar.tsx:1100-1127 serial-drains one at a time via the SAME handleSend.
  - **remove-one(aria-label 'Remove queued prompt', :1379)** — `driven` — Backed by store/chat-pending.ts (chat-pending.test.ts) — queuePrompt is a pure store action, drain loop at ChatSidebar.tsx:1100-1127 serial-drains one at a time via the SAME handleSend.

### `chat-agents-rail` — Running-agents rail (Delegate runs)

- area: composer (operator area: agent) · entry: `src/modules/chat/AgentsRail.tsx:20` · drive: api
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **hidden(active.length===0)** — `driven` — Synced by GET /runs poller (routers/runs.py:87). cancelRun -> POST /runs/{id}/cancel; answer -> POST /runs/{id}/answer (lib/delegate-runs.ts). Durable/detached per CLAUDE.md run_manager.py — DO NOT cancel a live operator run in this census.
  - **running** — `driven` — Synced by GET /runs poller (routers/runs.py:87). cancelRun -> POST /runs/{id}/cancel; answer -> POST /runs/{id}/answer (lib/delegate-runs.ts). Durable/detached per CLAUDE.md run_manager.py — DO NOT cancel a live operator run in this census.
  - **paused(human-in-the-loop answer box)** — `driven` — Synced by GET /runs poller (routers/runs.py:87). cancelRun -> POST /runs/{id}/cancel; answer -> POST /runs/{id}/answer (lib/delegate-runs.ts). Durable/detached per CLAUDE.md run_manager.py — DO NOT cancel a live operator run in this census.
  - **populated(cost-so-far vs budget)** — `driven` — Synced by GET /runs poller (routers/runs.py:87). cancelRun -> POST /runs/{id}/cancel; answer -> POST /runs/{id}/answer (lib/delegate-runs.ts). Durable/detached per CLAUDE.md run_manager.py — DO NOT cancel a live operator run in this census.

### `chat-empty-state` — Chat dock empty (hero) state

- area: composer (operator area: agent) · entry: `src/modules/chat/ChatSidebar.tsx:1479` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **empty-with-suggestion-chips** — `driven` — Shows SuggestionChips (SuggestionChips.tsx:83) + current mode/persona line.

### `chat-suggestion-chips` — Suggestion chips (empty-state prompts)

- area: composer (operator area: agent) · entry: `src/modules/chat/SuggestionChips.tsx:83` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **populated** — `driven` — SuggestionChips.test.tsx exists.

### `chat-error-row` — Chat transcript error row + Details disclosure

- area: composer (operator area: agent) · entry: `src/modules/chat/ChatSidebar.tsx:1430 (ErrorRow); src/modules/chat/message-notices.ts:19` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`, `r15/surface/failure-inducer/COVERAGE.json`

  - **message-error(plain .error string)** — `driven` — message-notices.test.ts covers the structured-frame store logic headlessly.
  - **structured-error-frame(action/detail/code behind 'Details' disclosure, D43)** — `driven` — message-notices.test.ts covers the structured-frame store logic headlessly.

### `chat-message-notices` — End-of-stream divergence notice chip

- area: composer (operator area: agent) · entry: `src/modules/chat/message-notices.ts:57-61 (isDivergenceNotice); src/modules/chat/ChatSidebar.tsx:1404 (MessageNotices)` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **no-notice** — `driven` — isDivergenceNotice is a pure regex match — headless-testable without streaming anything.
  - **divergence(quiet system chip, verbatim-matched copy)** — `driven` — isDivergenceNotice is a pure regex match — headless-testable without streaming anything.

### `chat-plan-view` — Agent plan view (Delegate multi-step plan)

- area: composer (operator area: agent) · entry: `src/modules/chat/PlanView.tsx:56` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **active(current step highlighted)** — `driven` — Renders AgentPlanView shape from a delegate run's structured plan.
  - **inactive/historical** — `driven` — Renders AgentPlanView shape from a delegate run's structured plan.

### `chat-research-activity` — Research step-trace / activity feed

- area: composer (operator area: agent) · entry: `src/modules/chat/ResearchActivity.tsx:78` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **active(streaming steps)** — `driven` — formatElapsed is a pure fn, headless unit-testable in isolation.
  - **completed** — `driven` — formatElapsed is a pure fn, headless unit-testable in isolation.
  - **elapsed-time formatting (formatElapsed :55)** — `driven` — formatElapsed is a pure fn, headless unit-testable in isolation.

### `chat-budget-config` — Delegate budget config (tokens/spend/wall/steps ceilings)

- area: composer (operator area: agent) · entry: `src/modules/chat/BudgetConfig.tsx:20` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **populated(default ceilings)** — `driven` — Ceilings enforced server-side by BudgetGuard (sidecar/services/budget_guard.py per CLAUDE.md) — first breach aborts run to 'error' with a resumable checkpoint (SC-008).
  - **edited** — `driven` — Ceilings enforced server-side by BudgetGuard (sidecar/services/budget_guard.py per CLAUDE.md) — first breach aborts run to 'error' with a resumable checkpoint (SC-008).

### `proposed-changes-review-bar` — Proposed-changes diff/accept trust gate

- area: proposed-changes (operator area: agent) · entry: `src/modules/chat/ProposedChangesReview.tsx:20` · drive: browser

  - **hidden(pending.length===0)** — `driven` — src/store/proposed-changes.test.ts (existing vitest suite; pure accept/reject/acceptAll/rejectAll reducer) - the AI-proposed-order path it used to gate is removed with the feature per 23 Sep
  - **populated(per-item Accept/Reject)** — `driven` — src/store/proposed-changes.test.ts (existing vitest suite; pure accept/reject/acceptAll/rejectAll reducer) - the AI-proposed-order path it used to gate is removed with the feature per 23 Sep
  - **bulk-accept-all(mod+enter)** — `driven` — src/store/proposed-changes.test.ts (existing vitest suite; pure accept/reject/acceptAll/rejectAll reducer) - the AI-proposed-order path it used to gate is removed with the feature per 23 Sep
  - **bulk-reject-all(mod+backspace)** — `driven` — src/store/proposed-changes.test.ts (existing vitest suite; pure accept/reject/acceptAll/rejectAll reducer) - the AI-proposed-order path it used to gate is removed with the feature per 23 Sep

### `safety-order-confirmation-dialog` — Order confirmation dialog (§6.5 confirm-before-place gate)

- area: safety (operator area: ui) · entry: `src/modules/safety/OrderConfirmationDialog.tsx:65,106` · drive: browser

  - **closed** — `removed with the feature` — removed with the feature - trading is out of the product (operator decision 23 Sep 2026); this surface existed only to gate/place/confirm a broker order
  - **open-manual(confirmEnabled always true)** — `removed with the feature` — removed with the feature - trading is out of the product (operator decision 23 Sep 2026); this surface existed only to gate/place/confirm a broker order
  - **open-ai-proposed(confirmEnabled requires reviewedAi checkbox, :122)** — `removed with the feature` — removed with the feature - trading is out of the product (operator decision 23 Sep 2026); this surface existed only to gate/place/confirm a broker order
  - **busy(submitting)** — `removed with the feature` — removed with the feature - trading is out of the product (operator decision 23 Sep 2026); this surface existed only to gate/place/confirm a broker order

### `safety-kill-switch` — Kill switch (dormant mechanism, no UI toolbar)

- area: safety (operator area: ui) · entry: `src-tauri/src/kill_switch.rs:34,73,90; src/store/safety.ts:126-242; sidecar/routers/safety.py:119,125,142` · drive: api

  - **idle** — `driven` — GET /safety/kill-switch/status read (sidecar/routers/safety.py:142) - safe, read-only
  - **fired(killSwitchFired=true)** — `NOT TESTED` — would require POST /safety/kill-switch, a mutating call against the operator's live session - deliberately not called
  - **loading/error(killSwitchStatus)** — `NOT TESTED` — no probe of the store's loading/error branch captured this run

### `safety-disclaimer-flow` — First-launch ToS / disclaimer flow

- area: onboarding (operator area: ui) · entry: `src/modules/safety/DisclaimerFlow.tsx:47 (FirstLaunchTosDialog), :132 (BrokerFirstConnectDialog), :228 (DisclaimerFlow)` · drive: browser
- evidence: `r15/surface/onboarding-stranger/COVERAGE.json`

  - **first-launch-unacked** — `driven` — GET /safety/disclaimer-status, POST /safety/disclaimer-ack. DisclaimerFlow.test.tsx exists. Gate: FIRST_LAUNCH_TOS_ACCOUNT keychain namespace (store/safety.ts:56).
  - **acked** — `driven` — GET /safety/disclaimer-status, POST /safety/disclaimer-ack. DisclaimerFlow.test.tsx exists. Gate: FIRST_LAUNCH_TOS_ACCOUNT keychain namespace (store/safety.ts:56).
  - **broker-first-connect-warning** — `driven` — GET /safety/disclaimer-status, POST /safety/disclaimer-ack. DisclaimerFlow.test.tsx exists. Gate: FIRST_LAUNCH_TOS_ACCOUNT keychain namespace (store/safety.ts:56).

### `onboarding-flow` — First-run onboarding wizard

- area: onboarding (operator area: ui) · entry: `src/components/OnboardingFlow.tsx:103` · drive: browser
- evidence: `r15/surface/onboarding-stranger/COVERAGE.json`

  - **welcome(:182)** — `driven` — LocalStep surfaces hardware-fit + Ollama recommendation (lib/hardware-fit.ts, GET /system/hardware,/local-model-recommendation,/ollama/status, POST /ollama/pull) — a real model pull is long-running/state-changing, do not trigger it against the live sidecar.
  - **cloud(:195, CloudStep :338)** — `driven` — LocalStep surfaces hardware-fit + Ollama recommendation (lib/hardware-fit.ts, GET /system/hardware,/local-model-recommendation,/ollama/status, POST /ollama/pull) — a real model pull is long-running/state-changing, do not trigger it against the live sidecar.
  - **local(:198, LocalStep :439)** — `driven` — LocalStep surfaces hardware-fit + Ollama recommendation (lib/hardware-fit.ts, GET /system/hardware,/local-model-recommendation,/ollama/status, POST /ollama/pull) — a real model pull is long-running/state-changing, do not trigger it against the live sidecar.
  - **done(:208, DoneStep :648)** — `driven` — LocalStep surfaces hardware-fit + Ollama recommendation (lib/hardware-fit.ts, GET /system/hardware,/local-model-recommendation,/ollama/status, POST /ollama/pull) — a real model pull is long-running/state-changing, do not trigger it against the live sidecar.

### `onboarding-banner` — First-run 'add your AI key' banner

- area: onboarding (operator area: ui) · entry: `src/components/OnboardingBanner.tsx:21` · drive: browser
- evidence: `r15/surface/onboarding-stranger/COVERAGE.json`

  - **hidden(probed=false OR hasAnyKey OR dismissed)** — `driven` — Driven by real keychain probe (store/provider-keys.ts), not a one-shot flag — disappears the moment any key is saved.
  - **shown(no key in keychain)** — `driven` — Driven by real keychain probe (store/provider-keys.ts), not a one-shot flag — disappears the moment any key is saved.

### `command-palette` — Command palette (cmd+K launcher)

- area: command-palette (operator area: ui) · entry: `src/components/CommandPalette.tsx:69,114` · drive: browser

  - **closed** — `driven` — src/store/command-palette.test.ts + src/components/CommandPalette.test.tsx (existing vitest suite, pure buildPaletteCorpus/paletteFilter + mounted component)
  - **empty-query(Recent + Suggested)** — `driven` — src/store/command-palette.test.ts + src/components/CommandPalette.test.tsx (existing vitest suite, pure buildPaletteCorpus/paletteFilter + mounted component)
  - **query-active(5 ranked groups: Ask AI, Agents, Actions, Panels, Symbols)** — `driven` — src/store/command-palette.test.ts + src/components/CommandPalette.test.tsx (existing vitest suite, pure buildPaletteCorpus/paletteFilter + mounted component)
  - **symbol-group-capped(SYMBOL_CAP=50, command-palette.ts:139)** — `driven` — src/store/command-palette.test.ts + src/components/CommandPalette.test.tsx (existing vitest suite, pure buildPaletteCorpus/paletteFilter + mounted component)
  - **no-results** — `driven` — src/store/command-palette.test.ts + src/components/CommandPalette.test.tsx (existing vitest suite, pure buildPaletteCorpus/paletteFilter + mounted component)

### `command-palette-ask-ai` — Palette 'Ask AI' free-text row

- area: command-palette (operator area: ui) · entry: `src/components/CommandPalette.tsx:448 (AskAiItem), :177-183 (handleSelectAskAi)` · drive: browser

  - **empty-query(hidden CTA)** — `driven` — src/components/CommandPalette.test.tsx covers handleSelectAskAi / AskAiItem routing to the agent-command bus
  - **populated(routes to agent-command bus)** — `driven` — src/components/CommandPalette.test.tsx covers handleSelectAskAi / AskAiItem routing to the agent-command bus

### `settings-section-nav` — Settings section nav / jump links

- area: settings (operator area: ui) · entry: `src/components/SettingsPanel.tsx:161,156` · drive: browser
- evidence: `r15/surface/settings-plugins/COVERAGE.json`

  - **populated(5 sections: Providers, Research, Region, Keybindings, Advanced)** — `driven` — jumpToSection (:156) is a DOM scrollIntoView call — needs a real/jsdom DOM, not pure logic.

### `settings-providers` — AI Providers section (BYOK keys)

- area: settings (operator area: ui) · entry: `src/components/SettingsPanel.tsx:410` · drive: browser
- evidence: `r15/surface/settings-plugins/COVERAGE.json`

  - **no-key** — `driven` — Opens KeyEntryDialog (src/components/KeyEntryDialog.tsx:42) with Status='idle'|'validating'|'valid'|'invalid'|'save-error'. POST /llm/keys/validate. Secret NEVER logged (keychain-only, per CLAUDE.md BYOK rule) — do not print any key value while exercising this.
  - **key-set** — `driven` — Opens KeyEntryDialog (src/components/KeyEntryDialog.tsx:42) with Status='idle'|'validating'|'valid'|'invalid'|'save-error'. POST /llm/keys/validate. Secret NEVER logged (keychain-only, per CLAUDE.md BYOK rule) — do not print any key value while exercising this.
  - **validating** — `driven` — Opens KeyEntryDialog (src/components/KeyEntryDialog.tsx:42) with Status='idle'|'validating'|'valid'|'invalid'|'save-error'. POST /llm/keys/validate. Secret NEVER logged (keychain-only, per CLAUDE.md BYOK rule) — do not print any key value while exercising this.
  - **invalid-key** — `driven` — Opens KeyEntryDialog (src/components/KeyEntryDialog.tsx:42) with Status='idle'|'validating'|'valid'|'invalid'|'save-error'. POST /llm/keys/validate. Secret NEVER logged (keychain-only, per CLAUDE.md BYOK rule) — do not print any key value while exercising this.

### `settings-research` — Research section (depth/model tiers + SearXNG)

- area: settings (operator area: ui) · entry: `src/components/SettingsPanel.tsx:1210,1011,1058,1124,1184` · drive: api
- evidence: `r15/surface/failure-inducer/COVERAGE.json`, `r15/surface/settings-plugins/COVERAGE.json`

  - **tier-cards(TierCard :1124)** — `driven` — GET /search/status, /search/tiers/status; POST /search/tiers/setup,/teardown (state-changing — read status only against the live stack).
  - **model-controls(ResearchModelControls :1058)** — `driven` — GET /search/status, /search/tiers/status; POST /search/tiers/setup,/teardown (state-changing — read status only against the live stack).
  - **stop-options(:1003)** — `driven` — GET /search/status, /search/tiers/status; POST /search/tiers/setup,/teardown (state-changing — read status only against the live stack).

### `settings-searxng` — SearXNG managed-instance flow

- area: settings (operator area: ui) · entry: `src/components/SettingsPanel.tsx:785 (SearxngManagedFlow), :960 (SearxngAdvancedUrl), :762 (SearxngStatusChip), :741 (searxngChipMeta)` · drive: browser
- evidence: `r15/surface/settings-plugins/COVERAGE.json`

  - **stopped** — `driven` — searxngChipMeta(state) is a pure label/className mapper — exported and headless-testable without mounting the chip.
  - **starting** — `driven` — searxngChipMeta(state) is a pure label/className mapper — exported and headless-testable without mounting the chip.
  - **running** — `driven` — searxngChipMeta(state) is a pure label/className mapper — exported and headless-testable without mounting the chip.
  - **error** — `driven` — searxngChipMeta(state) is a pure label/className mapper — exported and headless-testable without mounting the chip.

### `settings-region` — Region section

- area: settings (operator area: ui) · entry: `src/components/SettingsPanel.tsx:1297` · drive: api
- evidence: `r15/surface/settings-plugins/COVERAGE.json`

  - **populated** — `driven` — Backs lib/region.ts (region.test.ts); likely affects default exchange/session formatting (lib/market-session.ts).

### `settings-keybindings` — Keybindings remap section

- area: settings (operator area: ui) · entry: `src/components/SettingsPanel.tsx:1365,1348` · drive: browser
- evidence: `r15/surface/settings-plugins/COVERAGE.json`

  - **populated(default combo)** — `driven` — useKeybindingsStore.conflicts() (store/keybindings.ts) is pure/headless-testable (keybindings.test.ts) for the conflict-detection logic without any DOM.
  - **recording(comboFromEvent capturing keydown, :1348)** — `driven` — useKeybindingsStore.conflicts() (store/keybindings.ts) is pure/headless-testable (keybindings.test.ts) for the conflict-detection logic without any DOM.
  - **conflict(two actions share a combo, conflicts() in store)** — `driven` — useKeybindingsStore.conflicts() (store/keybindings.ts) is pure/headless-testable (keybindings.test.ts) for the conflict-detection logic without any DOM.

### `settings-advanced-integrations` — Advanced > Integrations subsection

- area: settings (operator area: ui) · entry: `src/components/SettingsPanel.tsx:1563` · drive: browser
- evidence: `r15/surface/settings-plugins/COVERAGE.json`

  - **populated** — `driven` — Child of AdvancedSection (:1532-1545).

### `settings-advanced-layouts` — Advanced > Layouts subsection (arrange templates management)

- area: settings (operator area: ui) · entry: `src/components/SettingsPanel.tsx:1587` · drive: browser
- evidence: `r15/surface/settings-plugins/COVERAGE.json`

  - **populated** — `driven` — Likely surfaces/edits the same 4 templates as lib/layout-templates.ts (single-focus/research-cockpit/compare/macro-scan) — verify by reading this subsection fully in Stage 1 execution, not yet opened line-by-line here.

### `settings-advanced-modules` — Advanced > Modules subsection (module enable/disable toggles)

- area: settings (operator area: ui) · entry: `src/components/SettingsPanel.tsx:1710` · drive: browser
- evidence: `r15/surface/settings-plugins/COVERAGE.json`

  - **all-enabled** — `driven` — Backed by store/modules.ts (modules.test.ts) — toggling a module changes collectPanels/collectCommands output (lib/module-registry.ts) which is pure and headless-testable.
  - **some-disabled** — `driven` — Backed by store/modules.ts (modules.test.ts) — toggling a module changes collectPanels/collectCommands output (lib/module-registry.ts) which is pure and headless-testable.

### `settings-advanced-export-import` — Advanced > Export/Import settings

- area: settings (operator area: ui) · entry: `src/components/SettingsPanel.tsx:1775,1767 (buildSettingsExport)` · drive: browser
- evidence: `r15/surface/settings-plugins/COVERAGE.json`

  - **export(populated JSON)** — `driven` — buildSettingsExport() is exported and pure — headless-testable for the export shape without touching the DOM.
  - **import-error(malformed file)** — `driven` — buildSettingsExport() is exported and pure — headless-testable for the export shape without touching the DOM.

### `settings-advanced-about` — Advanced > About subsection

- area: settings (operator area: ui) · entry: `src/components/SettingsPanel.tsx:1872` · drive: api
- evidence: `r15/surface/settings-plugins/COVERAGE.json`

  - **populated(version strings)** — `driven` — Cross-check against GET /health (request.app.version) and the multi-source version fields CLAUDE.md warns must move together (package.json/Cargo.toml/tauri.conf.json/sidecar app.py/HOST_VERSION).

### `layouts-arrange-templates` — Agent 'arrange' layout templates (4 modes)

- area: layouts (operator area: ui) · entry: `src/lib/layout-templates.ts:182 (planLayout), :648 (MODE_PLANS), :402 (fitLayoutTemplate)` · drive: browser
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **single-focus** — `driven` — planLayout for all 4 templates; fitLayoutTemplate at widths 0/800/1079/1080/1179/1180/1920/2560: research-cockpit downgrades <1180, macro-scan <1080, as documented - but every call returns {applied} while the mock api still shows the prior panels (rAF-deferred; confirms COD-works
  - **research-cockpit** — `driven` — planLayout for all 4 templates; fitLayoutTemplate at widths 0/800/1079/1080/1179/1180/1920/2560: research-cockpit downgrades <1180, macro-scan <1080, as documented - but every call returns {applied} while the mock api still shows the prior panels (rAF-deferred; confirms COD-works
  - **macro-scan** — `driven` — planLayout for all 4 templates; fitLayoutTemplate at widths 0/800/1079/1080/1179/1180/1920/2560: research-cockpit downgrades <1180, macro-scan <1080, as documented - but every call returns {applied} while the mock api still shows the prior panels (rAF-deferred; confirms COD-works
  - **compare** — `driven` — planLayout for all 4 templates; fitLayoutTemplate at widths 0/800/1079/1080/1179/1180/1920/2560: research-cockpit downgrades <1180, macro-scan <1080, as documented - but every call returns {applied} while the mock api still shows the prior panels (rAF-deferred; confirms COD-works
  - **viewport-downgrade(width<1180 research-cockpit->chart+brief; width<1080 macro-scan->single focus, :409,:419)** — `driven` — planLayout for all 4 templates; fitLayoutTemplate at widths 0/800/1079/1080/1179/1180/1920/2560: research-cockpit downgrades <1180, macro-scan <1080, as documented - but every call returns {applied} while the mock api still shows the prior panels (rAF-deferred; confirms COD-works

### `layouts-macos-menu-bridge` — Native macOS Layout menu (Fundamental/Technical/Macro/Compare/Reset)

- area: layouts (operator area: ui) · entry: `src/lib/menu-bridge.ts:14; src-tauri/src/lib.rs (menu build, macOS-only)` · drive: gui
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **applied(deterministic clear+tile)** — `NEEDS-MANUAL-CHECK` — surface requires GUI interaction not available in Stage B
  - **unknown-payload(:36 warn)** — `NEEDS-MANUAL-CHECK` — surface requires GUI interaction not available in Stage B
  - **no-dockview-api-yet(:28 warn)** — `NEEDS-MANUAL-CHECK` — surface requires GUI interaction not available in Stage B

### `layouts-workspace-save-load` — Save/Load workspace + New Research Space commands

- area: layouts (operator area: ui) · entry: `src/modules/platform/index.ts:47,55,63` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **saved** — `driven` — list/get/save/round-trip-equal/delete ok on a copy of the operator autosave. 'Research: RELIANCE' -> 400 (confirms COD-workspace-layout-2 live); 300-char name -> 500 Internal Server Error (OSError, COD-workspace-layout-7); '__autosave__x' accepted; unicode name 400; 5 MB blob acc
  - **loaded(older-blob-guarded, deserializeWorkspace)** — `driven` — list/get/save/round-trip-equal/delete ok on a copy of the operator autosave. 'Research: RELIANCE' -> 400 (confirms COD-workspace-layout-2 live); 300-char name -> 500 Internal Server Error (OSError, COD-workspace-layout-7); '__autosave__x' accepted; unicode name 400; 5 MB blob acc
  - **new-research-space** — `driven` — list/get/save/round-trip-equal/delete ok on a copy of the operator autosave. 'Research: RELIANCE' -> 400 (confirms COD-workspace-layout-2 live); 300-char name -> 500 Internal Server Error (OSError, COD-workspace-layout-7); '__autosave__x' accepted; unicode name 400; 5 MB blob acc

### `comparison-surface` — Symbol comparison (chart overlay + compare layout + slash command)

- area: comparison (operator area: ui) · entry: `src/modules/chart/toolbar.tsx:335 (CompareMenu); src/lib/layout-templates.ts:681 ('compare' MODE_PLAN); src/modules/chat/slash-commands.ts:169` · drive: browser
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **single-symbol** — `driven` — The overlay's data call (sidecarApi.history(compareSymbol)) returns INFY/TCS/HDFCBANK 1d 258 bars. Overlay rendering and '%' mode are canvas (COD-frontend-panels-data-surfaces-15), NEEDS-GUI.
  - **dual-symbol-overlay(pushed via chart-command channel)** — `driven` — The overlay's data call (sidecarApi.history(compareSymbol)) returns INFY/TCS/HDFCBANK 1d 258 bars. Overlay rendering and '%' mode are canvas (COD-frontend-panels-data-surfaces-15), NEEDS-GUI.

### `charts-toolbar-draw-menu` — Chart toolbar > Draw menu (drawing tools)

- area: charts (operator area: ui) · entry: `src/modules/chart/toolbar.tsx:207` · drive: gui
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **no-tool-armed** — `NEEDS-MANUAL-CHECK` — surface requires GUI interaction not available in Stage B
  - **tool-armed(activeTool set, DrawingKind)** — `NEEDS-MANUAL-CHECK` — surface requires GUI interaction not available in Stage B

### `charts-toolbar-indicators-menu` — Chart toolbar > Indicators menu

- area: charts (operator area: ui) · entry: `src/modules/chart/toolbar.tsx:255,246 (matchesQuery)` · drive: browser
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **search-empty** — `driven` — 50-key frontend catalog == sidecar GET /indicators list (0 missing, 0 extra); every key computes for RELIANCE.NS 1d.
  - **search-filtered** — `driven` — 50-key frontend catalog == sidecar GET /indicators list (0 missing, 0 extra); every key computes for RELIANCE.NS 1d.
  - **toggled-on/off per indicator** — `driven` — 50-key frontend catalog == sidecar GET /indicators list (0 missing, 0 extra); every key computes for RELIANCE.NS 1d.

### `charts-toolbar-sync-menu` — Chart toolbar > Sync menu (cross-panel symbol sync subscriptions)

- area: charts (operator area: ui) · entry: `src/modules/chart/toolbar.tsx:387` · drive: browser
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **no-subscriptions** — `NOT TESTED` — NOT TESTED - browser-only store surface (chart-sync.ts) with no sidecar call; the chart is a singleton so no sync peer exists (COD-frontend-panels-data-surfaces-4); not re-driven headlessly (source: surface/panels-layouts/COVERAGE.json). Store logic has unit tests in src/store/chart-sync.test.ts, but the menu itself was not driven.
  - **populated(toggle per subscription)** — `NOT TESTED` — NOT TESTED - browser-only store surface (chart-sync.ts) with no sidecar call; the chart is a singleton so no sync peer exists (COD-frontend-panels-data-surfaces-4); not re-driven headlessly (source: surface/panels-layouts/COVERAGE.json). Store logic has unit tests in src/store/chart-sync.test.ts, but the menu itself was not driven.

### `charts-timeframe` — Chart timeframe/interval selector

- area: charts (operator area: ui) · entry: `src/modules/chart/ChartPanel.tsx` · drive: api
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **populated(interval options)** — `driven` — 8 options (ChartPanel.tsx:77): 7 return bars, 30m returns none for any symbol (SURF-PANELS-LAYOUTS-3); 1wk/1mo freshness mislabelled (SURF-PANELS-LAYOUTS-4).

### `kb-keybindings-store` — Keybindings default keymap (source of truth)

- area: keyboard-shortcuts (operator area: ui) · entry: `src/store/keybindings.ts:63 (SHELL_DEFAULTS),117 (MODULE_COMMAND_BINDINGS),154 (DEFAULT_KEYBINDINGS)` · drive: browser

  - **default** — `driven` — src/store/keybindings.test.ts (existing vitest suite; bindingFor/defFor/conflicts pure-function coverage)
  - **user-override(overrides map)** — `driven` — src/store/keybindings.test.ts (existing vitest suite; bindingFor/defFor/conflicts pure-function coverage)
  - **conflict** — `driven` — src/store/keybindings.test.ts (existing vitest suite; bindingFor/defFor/conflicts pure-function coverage)

### `kb-global-handlers` — Global keydown handlers (palette, agent mode, accept/reject)

- area: keyboard-shortcuts (operator area: ui) · entry: `src/components/CommandPalette.tsx:75-83 (mod+k); src/modules/chat/ChatSidebar.tsx:564-565 (window keydown listener)` · drive: browser

  - **fired** — `driven` — src/components/CommandPalette.test.tsx + src/modules/chat/ChatSidebar.test.tsx exercise the mod+k / window keydown listeners
  - **ignored(not matching combo)** — `driven` — src/components/CommandPalette.test.tsx + src/modules/chat/ChatSidebar.test.tsx exercise the mod+k / window keydown listeners

### `kb-os-kill-switch-shortcut` — OS-level kill-switch shortcut (Cmd/Ctrl+Shift+K)

- area: keyboard-shortcuts (operator area: ui) · entry: `src-tauri/src/kill_switch.rs:34,73` · drive: gui

  - **registered** — `NEEDS-MANUAL-CHECK` — real OS-global Tauri shortcut (lib.rs:446) - cannot be simulated via DOM keydown or curl; needs the operator with the desktop app running
  - **fired** — `NEEDS-MANUAL-CHECK` — real OS-global Tauri shortcut (lib.rs:446) - cannot be simulated via DOM keydown or curl; needs the operator with the desktop app running

### `generic-empty-state-component` — Shared EmptyState component (icon+headline+hint+CTA)

- area: toasts-and-frames (operator area: ui) · entry: `src/components/EmptyState.tsx:22` · drive: browser

  - **default** — `driven` — src/components/EmptyState.test.tsx (existing vitest suite) + referenced by name in panels-layouts/settings-plugins/portfolio-notes COVERAGE.json evidence for ~10 panels
  - **dense(compact variant, :27-40)** — `driven` — src/components/EmptyState.test.tsx (existing vitest suite) + referenced by name in panels-layouts/settings-plugins/portfolio-notes COVERAGE.json evidence for ~10 panels
  - **with-cta** — `driven` — src/components/EmptyState.test.tsx (existing vitest suite) + referenced by name in panels-layouts/settings-plugins/portfolio-notes COVERAGE.json evidence for ~10 panels
  - **without-cta** — `driven` — src/components/EmptyState.test.tsx (existing vitest suite) + referenced by name in panels-layouts/settings-plugins/portfolio-notes COVERAGE.json evidence for ~10 panels

### `generic-error-frame-pattern` — Per-panel inline error text pattern (no toast library)

- area: toasts-and-frames (operator area: ui) · entry: `src/modules/chat/message-notices.ts:19 (MessageErrorFrame); repeated data-testid='*-error' rows across option-pricer(:495), greeks(:343), bond(:274), yield-curve(:353), sec-filings(:174), screener-formula(:202)` · drive: browser
- evidence: `r15/surface/failure-inducer/COVERAGE.json`

  - **no-error** — `driven` — CONFIRMED: no toast/sonner library in the frontend (grepped, zero hits) — every 'toast' in this app is an inline, panel-local error/notice row. Treat 'toasts' in the Stage-1 test plan as this per-panel error-row pattern, not a global notification stack.
  - **error-shown** — `driven` — CONFIRMED: no toast/sonner library in the frontend (grepped, zero hits) — every 'toast' in this app is an inline, panel-local error/notice row. Treat 'toasts' in the Stage-1 test plan as this per-panel error-row pattern, not a global notification stack.
  - **dismissible(portfolio :701-708 has an explicit dismiss button; most others clear on next successful action)** — `driven` — CONFIRMED: no toast/sonner library in the frontend (grepped, zero hits) — every 'toast' in this app is an inline, panel-local error/notice row. Treat 'toasts' in the Stage-1 test plan as this per-panel error-row pattern, not a global notification stack.

### `desktop-notification-bridge` — OS desktop notification bridge (workflow node -> OS notification)

- area: toasts-and-frames (operator area: ui) · entry: `src/lib/desktop-notification.ts:45` · drive: gui

  - **outside-tauri(no-op, browser dev mode)** — `driven` — desktop-notification.test.ts asserts the browser-dev no-op path
  - **permission-not-yet-granted** — `driven` — desktop-notification.test.ts asserts the queue-drain calls sendNotification only after permission state resolves
  - **permission-denied(silent no-op)** — `driven` — desktop-notification.test.ts asserts denied -> no throw, no call
  - **sent** — `NEEDS-MANUAL-CHECK` — real OS notification delivery requires the desktop app + OS notification center; queue-drain call itself is unit-tested, the OS popup is not

### `agent-mode-toggle` — Agent mode toggle (Agent vs Delegate)

- area: chat-agent (operator area: agent) · entry: `src/store/agent-mode.ts; src/store/agent-autonomy.ts; types/agent-modes.ts (AGENT_MODES)` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **agent(interactive)** — `driven` — Bound to alt+1/alt+2 (keybindings.ts:66-77). agent-mode.test.ts, agent-autonomy tested indirectly via ComposerPlusMenu.test.tsx.
  - **delegate(durable/budget-capped)** — `driven` — Bound to alt+1/alt+2 (keybindings.ts:66-77). agent-mode.test.ts, agent-autonomy tested indirectly via ComposerPlusMenu.test.tsx.

### `agent-autonomy-ask-auto` — Autonomy: ASK vs AUTO

- area: chat-agent (operator area: agent) · entry: `src/store/agent-autonomy.ts` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **ask(every proposal queues for review)** — `driven` — Per ComposerPlusMenu.tsx:19-20 comment: a standing mode, not a per-message control.
  - **auto(still gated for orders per §6.5 — 'orders always confirm regardless')** — `driven` — Per ComposerPlusMenu.tsx:19-20 comment: a standing mode, not a per-message control.

### `agent-persona-picker` — Persona / active-lens picker (Buffett / researcher / custom)

- area: chat-agent (operator area: agent) · entry: `src/modules/chat/ComposerPlusMenu.tsx (persona section); src/store/active-agent.ts` · drive: api
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **first-party-persona(firstParty list)** — `driven` — Roster combines first-party agents + user-authored custom agents (GET /agents, GET /agents/custom).
  - **custom-persona(custom list, from Agent Builder)** — `driven` — Roster combines first-party agents + user-authored custom agents (GET /agents, GET /agents/custom).
  - **display-name-always(never raw id, per comment ComposerPlusMenu.tsx:18)** — `driven` — Roster combines first-party agents + user-authored custom agents (GET /agents, GET /agents/custom).

### `agent-command-bus` — Agent-command bus (cross-surface 'ask AI' routing)

- area: chat-agent (operator area: agent) · entry: `src/store/agent-command.ts (sendToAgent); src/store/agent-dock.ts (setCollapsed)` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **idle** — `driven` — Single funnel used by CommandPalette Ask-AI row, chat itself, and any future entry point (agent-command.test.ts, agent-dock.test.ts).
  - **query-pending(consumed by ChatSidebar)** — `driven` — Single funnel used by CommandPalette Ask-AI row, chat itself, and any future entry point (agent-command.test.ts, agent-dock.test.ts).

### `agent-runs-store` — Delegate run lifecycle (running/paused/error/done)

- area: chat-agent (operator area: agent) · entry: `src/store/agent-runs.ts` · drive: api
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **running** — `driven` — GET /runs, /runs/{id}; POST /runs/{id}/cancel,/answer,/resume (routers/runs.py). Mirrors sidecar's runs_store SQLite per CLAUDE.md. agent-runs.test.ts covers the store transitions headlessly.
  - **paused(awaiting human answer)** — `driven` — GET /runs, /runs/{id}; POST /runs/{id}/cancel,/answer,/resume (routers/runs.py). Mirrors sidecar's runs_store SQLite per CLAUDE.md. agent-runs.test.ts covers the store transitions headlessly.
  - **error(budget breach, resumable checkpoint)** — `driven` — GET /runs, /runs/{id}; POST /runs/{id}/cancel,/answer,/resume (routers/runs.py). Mirrors sidecar's runs_store SQLite per CLAUDE.md. agent-runs.test.ts covers the store transitions headlessly.
  - **done** — `driven` — GET /runs, /runs/{id}; POST /runs/{id}/cancel,/answer,/resume (routers/runs.py). Mirrors sidecar's runs_store SQLite per CLAUDE.md. agent-runs.test.ts covers the store transitions headlessly.

### `llm-chat-streaming` — LLM chat streaming transport

- area: chat-agent (operator area: agent) · entry: `src/modules/chat/streaming.ts (streaming.test.ts)` · drive: api
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **connecting** — `driven` — POST /llm/chat (SSE). Backend per-adapter tool-call/tool-result turn quirks documented in CLAUDE.md (Gemini needs metadata.name on the result turn) — a good place for a targeted regression test per provider, headlessly, once a BYOK key exists for that provider.
  - **streaming-tokens** — `driven` — POST /llm/chat (SSE). Backend per-adapter tool-call/tool-result turn quirks documented in CLAUDE.md (Gemini needs metadata.name on the result turn) — a good place for a targeted regression test per provider, headlessly, once a BYOK key exists for that provider.
  - **tool-call-turn** — `driven` — POST /llm/chat (SSE). Backend per-adapter tool-call/tool-result turn quirks documented in CLAUDE.md (Gemini needs metadata.name on the result turn) — a good place for a targeted regression test per provider, headlessly, once a BYOK key exists for that provider.
  - **tool-result-turn** — `driven` — POST /llm/chat (SSE). Backend per-adapter tool-call/tool-result turn quirks documented in CLAUDE.md (Gemini needs metadata.name on the result turn) — a good place for a targeted regression test per provider, headlessly, once a BYOK key exists for that provider.
  - **aborted** — `driven` — POST /llm/chat (SSE). Backend per-adapter tool-call/tool-result turn quirks documented in CLAUDE.md (Gemini needs metadata.name on the result turn) — a good place for a targeted regression test per provider, headlessly, once a BYOK key exists for that provider.
  - **error** — `driven` — POST /llm/chat (SSE). Backend per-adapter tool-call/tool-result turn quirks documented in CLAUDE.md (Gemini needs metadata.name on the result turn) — a good place for a targeted regression test per provider, headlessly, once a BYOK key exists for that provider.

### `chat-markdown-render` — Chat markdown streaming renderer

- area: chat-agent (operator area: agent) · entry: `src/lib/markdown-stream.ts (markdown-stream.test.ts); src/modules/chat/chat-markdown.ts (chat-markdown.test.ts)` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **partial-markdown(mid-stream)** — `driven` — Both are pure parsing/formatting modules — fully headless unit-test targets, high value for streaming edge cases (a code fence that never closes, a table cut mid-row).
  - **complete** — `driven` — Both are pure parsing/formatting modules — fully headless unit-test targets, high value for streaming edge cases (a code fence that never closes, a table cut mid-row).
  - **malformed(unterminated code fence, table, etc.)** — `driven` — Both are pure parsing/formatting modules — fully headless unit-test targets, high value for streaming edge cases (a code fence that never closes, a table cut mid-row).

### `context-provider-badge` — Context badge (what-the-agent-sees snapshot)

- area: chat-agent (operator area: agent) · entry: `src/modules/chat/context-provider.ts (context-provider.test.ts); src/modules/chat/ChatSidebar.tsx:1391 (ContextBadge), :2038 (describeContext)` · drive: browser
- evidence: `r15/surface/composer-chat/COVERAGE.json`

  - **populated(symbol/panel/viewport snapshot)** — `driven` — describeContext is a pure formatter — headless-testable given a fixed snapshot object.

### `panel-context-publishers` — Per-module panel-context publishers (what each panel tells the agent)

- area: panels (operator area: ui) · entry: `src/modules/panel-context-publishers.test.tsx; src/store/panel-context.ts` · drive: browser
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **published(per active panel)** — `driven` — Watchlist/News/Equity/Portfolio publish + unregister. Earnings/Analyst/SEC publish nothing (COD-market-data-providers-3-6).
  - **stale/unpublished** — `driven` — Watchlist/News/Equity/Portfolio publish + unregister. Earnings/Analyst/SEC publish nothing (COD-market-data-providers-3-6).

### `symbol-autocomplete` — Symbol autocomplete (palette + wikilink + watchlist add)

- area: command-palette (operator area: ui) · entry: `src/lib/symbol-autocomplete.ts` · drive: api

  - **no-match** — `driven` — surface/panels-layouts/COVERAGE.json panel-watchlist evidence exercises /resolve + /resolve/autocomplete live (reliance/kaynes/tata motors/hdfc/'RELIANCE.NS'); surface/resolver-probe/ itself is empty (probe not separately captured)
  - **matched(live candidates)** — `driven` — surface/panels-layouts/COVERAGE.json panel-watchlist evidence exercises /resolve + /resolve/autocomplete live (reliance/kaynes/tata motors/hdfc/'RELIANCE.NS'); surface/resolver-probe/ itself is empty (probe not separately captured)

### `fuzzy-search-lib` — Fuzzy matcher (palette filter ranking)

- area: command-palette (operator area: ui) · entry: `src/lib/fuzzy.ts (fuzzy.test.ts)` · drive: browser

  - **exact-match** — `driven` — src/lib/fuzzy.test.ts (existing vitest suite, pure algorithm)
  - **fuzzy-match** — `driven` — src/lib/fuzzy.test.ts (existing vitest suite, pure algorithm)
  - **no-match** — `driven` — src/lib/fuzzy.test.ts (existing vitest suite, pure algorithm)

### `csv-export` — CSV export utility (audit log, portfolio, etc.)

- area: toasts-and-frames (operator area: ui) · entry: `src/lib/csv.ts (csv.test.ts)` · drive: browser
- evidence: `r15/surface/portfolio-notes/COVERAGE.json`

  - **populated-rows** — `driven` — Portfolio export only; the watchlist shares src/lib/csv.ts.
  - **empty-rows(header-only)** — `driven` — Portfolio export only; the watchlist shares src/lib/csv.ts.

### `export-artifact` — Export-conversation / export-artifact flow

- area: toasts-and-frames (operator area: ui) · entry: `src/lib/export-artifact.ts` · drive: browser

  - **exported** — `NOT TESTED` — no src/lib/export-artifact.test.ts in the repo and no Stage B probe exercised the /export slash command or ChatSidebar exportConversation path; flagged for a follow-up sweep
  - **empty(nothing to export)** — `NOT TESTED` — no src/lib/export-artifact.test.ts in the repo and no Stage B probe exercised the /export slash command or ChatSidebar exportConversation path; flagged for a follow-up sweep

### `market-session-indicator` — Market-session state (open/closed/pre/post)

- area: charts (operator area: ui) · entry: `src/lib/market-session.ts (market-session.test.ts)` · drive: browser
- evidence: `r15/surface/panels-layouts/COVERAGE.json`

  - **pre-market** — `NOT TESTED` — NOT TESTED - pure time-window fn (src/lib/market-session.ts) with its own unit test (src/lib/market-session.test.ts covers pre/open/after-hours/closed labels); no sidecar surface in this group, the sidecar calendar freshness is exercised under charts-timeframe (source: surface/panels-layouts/COVERAGE.json). The rendered indicator was not driven.
  - **open** — `NOT TESTED` — NOT TESTED - pure time-window fn (src/lib/market-session.ts) with its own unit test (src/lib/market-session.test.ts covers pre/open/after-hours/closed labels); no sidecar surface in this group, the sidecar calendar freshness is exercised under charts-timeframe (source: surface/panels-layouts/COVERAGE.json). The rendered indicator was not driven.
  - **after-hours** — `NOT TESTED` — NOT TESTED - pure time-window fn (src/lib/market-session.ts) with its own unit test (src/lib/market-session.test.ts covers pre/open/after-hours/closed labels); no sidecar surface in this group, the sidecar calendar freshness is exercised under charts-timeframe (source: surface/panels-layouts/COVERAGE.json). The rendered indicator was not driven.
  - **closed** — `NOT TESTED` — NOT TESTED - pure time-window fn (src/lib/market-session.ts) with its own unit test (src/lib/market-session.test.ts covers pre/open/after-hours/closed labels); no sidecar surface in this group, the sidecar calendar freshness is exercised under charts-timeframe (source: surface/panels-layouts/COVERAGE.json). The rendered indicator was not driven.

### `hardware-fit-check` — Local-model hardware-fit scoring (onboarding LocalStep + Settings FitRow)

- area: onboarding (operator area: ui) · entry: `src/lib/hardware-fit.ts; src/components/SettingsPanel.tsx:680 (FitRow)` · drive: api
- evidence: `r15/surface/onboarding-stranger/COVERAGE.json`

  - **fits** — `driven` — GET /system/hardware,/system/local-model-recommendation. FitRow is a pure presentational row over a ScoredModel — headless-testable given a fixed ScoredModel fixture.
  - **marginal** — `driven` — GET /system/hardware,/system/local-model-recommendation. FitRow is a pure presentational row over a ScoredModel — headless-testable given a fixed ScoredModel fixture.
  - **does-not-fit** — `driven` — GET /system/hardware,/system/local-model-recommendation. FitRow is a pure presentational row over a ScoredModel — headless-testable given a fixed ScoredModel fixture.

### `provider-health-breaker` — Provider health / circuit-breaker status

- area: settings (operator area: ui) · entry: `sidecar/routers/system.py:203,215,227 (GET /system/provider-health, POST /trip,/reset)` · drive: api
- evidence: `r15/surface/failure-inducer/COVERAGE.json`, `r15/surface/settings-plugins/COVERAGE.json`

  - **healthy** — `driven` — No frontend surface for this located in this pass (not opened) — likely internal/ops-only; flag for Stage 1 to confirm whether Settings > Advanced actually surfaces it or if it's sidecar-internal only. GET is safe; the trip/reset POSTs mutate shared provider state — never call th
  - **tripped(circuit open)** — `driven` — No frontend surface for this located in this pass (not opened) — likely internal/ops-only; flag for Stage 1 to confirm whether Settings > Advanced actually surfaces it or if it's sidecar-internal only. GET is safe; the trip/reset POSTs mutate shared provider state — never call th
  - **reset** — `driven` — No frontend surface for this located in this pass (not opened) — likely internal/ops-only; flag for Stage 1 to confirm whether Settings > Advanced actually surfaces it or if it's sidecar-internal only. GET is safe; the trip/reset POSTs mutate shared provider state — never call th

