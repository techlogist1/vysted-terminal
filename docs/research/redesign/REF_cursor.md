# REF: Cursor — what "Cursor for finance" should copy

Research reference for the Vysted Terminal redesign. The thesis: Cursor won by
**inverting the IDE** — the AI agent became a co-equal primary surface, not a
sidebar bolted onto an editor — while still letting hand-coders work directly.
A finance terminal can run the same play: the agent as a primary surface
alongside panels, serving both power traders who drive panels directly and
novices who just talk to it. Below, each Cursor pattern is mapped to a concrete
Vysted implication (panels-not-files, symbols/portfolios-not-code).

Source dates: Cursor 2.0 (Oct 2025, agent-first architecture), Cursor 3 (Apr
2026, agent-first interface + Agents Window). Where Cursor has *regressed*
(auto-apply without diff review) it is called out as an anti-pattern to avoid.

---

## 1. The agentic-IDE inversion: agent as co-equal PRIMARY surface

### What Cursor did
Cursor's whole arc is a deliberate demotion of the editor. Cursor 2.0/3 was
"rebuilt from scratch around agents": the **Agents Window is now the primary
surface for agent interaction, with the classic editor available as a
complement** — "a unified workspace for building software with agents," not "an
IDE with AI features." The IDE is explicitly positioned as a **fallback**, not
the default. ([InfoQ][infoq], [DigitalApplied 2.0][da20])

Critically, this is not "chat got bigger." It's a layout-level inversion:
- **All agents surface in one sidebar** — local agents, cloud agents, and ones
  kicked off from mobile/web/Slack/GitHub/Linear — managed centrally. ([InfoQ][infoq])
- You **toggle to the editor** (`Cmd+E` toggles Agent layout; `Cmd+Shift+P →
  Open Editor Window`, or run both side-by-side) rather than the editor being
  ever-present. ([Cursor shortcuts][ks], [DigitalApplied 3][da3])
- A **redesigned Diffs view** lets you "review and commit changes, manage PRs
  without leaving Cursor" — the review surface is first-class, not a popup. ([DigitalApplied 3][da3])

The under-recognized point: even before v2/v3, Cursor never made the agent feel
like a plugin. It was always reachable by a single keystroke from anywhere
(`Cmd+L`, `Cmd+K`, `Cmd+I`), each landing you in a *different* agent surface
tuned to a different intent (see §2). The inversion was the endgame of a design
that treated the agent as a peer of the editor from day one.

### Vysted implication
- **Make the agent a primary surface, not the AI sidebar it is today.** Vysted's
  current `ChatSidebar.tsx` is the bolted-on-sidebar pattern Cursor moved *past*.
  The redesign target: an **Agent surface that can take the full cockpit** (or a
  dominant column) and that *opens panels as its output* — the way Cursor's
  agent opens files/diffs. Panels are to Vysted what files are to Cursor.
- **One keystroke, agent anywhere.** From any panel (Chart, Watchlist, Equity
  Overview), a single hotkey drops the user into the agent with that panel's
  symbol/context already attached (the §6 context-pill model).
- **A central "Agents" rail.** Cursor's single sidebar listing all running
  agents maps directly onto Vysted's existing multi-agent roster
  (`sidecar/agents/*.json` — Buffett, Dalio, Druckenmiller, Researcher,
  Strategy Critic, the new Copilot). A left rail showing *running* agent
  sessions (a backtest critic, a research run, a screener sweep) with their
  status is the finance analogue of Cursor's agents sidebar. Vysted already has
  the workflow/backtest/critic substrate (Phase 4–5) — it lacks the *surface*
  that makes those feel co-equal with panels.
- **The panel grid is the "fallback editor."** dockview cockpit = the IDE that
  the agent-first surface complements. Keep it excellent for hand-users, but
  stop treating it as the only home screen.

---

## 2. Chat / Cmd-K inline / Composer / Agent — four modes, four intents

Cursor's most copyable idea is that "talk to the AI" is **not one mode** — it's
four, each mapped to a distinct intent and bound to a distinct keystroke. This
is what lets one app serve a spectrum of users without a settings toggle.

| Cursor mode | Keystroke | Intent | Writes? | Scope |
|---|---|---|---|---|
| **Chat** | `Cmd+L` | Ask / explore / explain — "why is this failing?" | No (read-only by default; @-mentions, semantic search, MCP tools) | Conversation |
| **Cmd-K inline** | `Cmd+K` | Surgical edit *right where the cursor is* — select, describe, accept diff | Yes, after accept | Single location / selection |
| **Composer** | `Cmd+I` | Multi-file creation — plans, creates new files, runs commands | Yes, multi-file | Project |
| **Agent / Background** | `Cmd+I` + `Cmd+.` mode menu; cloud handoff | Autonomous, multi-step, grabs its own context, runs in parallel (up to 8, git-worktree isolated) | Yes, autonomous | Repo(s), async |

([PromptWarrior][pw], [CursorForPMs][pm], [Cursor shortcuts][ks], [DigitalApplied 2.0][da20])

Key design properties:
- **Cmd-K is "precision," Chat is "exploration," Composer is "creation," Agent
  is "delegation."** Beginners are told to default to Agent ("you won't have to
  manually select any context and hardly have to understand anything about the
  code"); power users mix all four. ([PromptWarrior][pw])
- **`Cmd+.` opens a Mode Menu** to switch the active mode in place; `Cmd+/` loops
  through models. Mode is a fast, keyboard-reachable axis — not buried in
  settings. ([Cursor shortcuts][ks])
- **Background/cloud agents** run in isolated cloud VMs; you can hand a session
  local→cloud (keep working offline) and pull it back local for hands-on
  testing. Cloud agents "generate demos and screenshots for human review before
  implementation." ([InfoQ][infoq])

### Vysted implication
Map the four modes onto finance verbs. This is the spine of the redesign:

- **Chat (`Cmd+L`) → Ask.** Read-only Q&A over the workspace: "why is NVDA down
  3%?", "explain this earnings miss", "what's the correlation between these two
  positions?" No mutation of panels/portfolio. This is roughly today's
  ChatSidebar — keep it, but make it *one of four*, not *the* AI feature.
- **Cmd-K inline → Surgical panel edit.** Cursor over a panel, hit `Cmd+K`:
  "add VWAP and a 200-EMA to this chart", "add a P&L column to this watchlist",
  "filter this screener to mid-caps with rising revenue." It mutates *that
  panel's* config and shows a preview/diff before applying (§4). The finance
  analogue of "select a function, describe the change."
- **Composer → Build a workspace / strategy.** Multi-panel, multi-step
  composition: "build me a semiconductor cockpit — chart NVDA vs SOXX, an
  earnings panel, an analyst-ratings panel, and a screener for the supply
  chain." Composer *creates panels* the way Cursor creates files. This is also
  the natural home for **strategy composition** (Vysted's node editor +
  workflow engine) — Plan Mode (§3) drives a backtest pipeline.
- **Agent / Background → Delegate research & monitoring.** Long-running,
  async, parallel: a Strategy Critic backtest, a multi-name research sweep, a
  "watch for these conditions and alert me" monitor. Vysted's sidecar already
  runs these as agent runtimes; what's missing is the **background-agent
  surface** — a list of running sweeps with status, plus the local↔"keep
  running while I close the app" handoff (sidecar is local, but a session can
  persist server-side per the agent runtime). Cursor's "generate a
  demo/screenshot for review" → a research run produces a **reviewable
  briefing/diff of the portfolio impact** before anything executes.

The §6.5 safety layer maps cleanly: Chat/Ask and Cmd-K-on-data are read-only;
anything that **places an order** is the equivalent of Composer/Agent writing to
disk and MUST go through the confirm-and-place gate (the finance "accept the
diff"). Never auto-apply an order — see §4 anti-pattern.

---

## 3. Progressive complexity: minimal by default, surfaces appear as you go deeper

Cursor's complexity is *layered*, not *flattened*. A first-time user can be
productive with essentially one feature, and the surface area grows only as the
user reaches for it.

- **Default layer = Tab.** Cursor Tab (autocomplete) is the zero-friction entry:
  "use it when you know what you want and just need it written faster." It
  predicts *next edit and where you'll jump*, not just next characters, across a
  272K-token codebase context — but the user just presses `Tab`. 400M+
  requests/day. No mode selection, no context picking. ([Neon][neon], [Rudrank][tab])
- **Next layer = three keystrokes.** The "three essential shortcuts" framing
  (`Cmd+K`, `Cmd+L`, `Cmd+I`) is *explicitly taught as the whole product* to
  beginners — "designed to reduce friction between thinking and coding." Most
  users never need more. ([ExplainThis][et])
- **Deeper layers reveal themselves:** @-mentions (type `@` → menu appears),
  Plan Mode, Review→Find Issues, MCP servers, Rules files, background/cloud
  agents, multi-agent orchestration. None of these are on the default screen;
  they appear when you type the trigger or reach the workflow that needs them.
- **The context ring** (a visual budget indicator next to the prompt) only
  *matters* once you're doing heavy context work — invisible cognitive load
  until you need it. ([Cursor mentions docs][mentions])

### Vysted implication
- **Define Vysted's "Tab."** What is the zero-config, always-on, one-gesture
  finance primitive? Strong candidate: **inline AI annotations on hover/select**
  — hover a candle and get a one-line "earnings gap, +4 ATR move"; select two
  watchlist rows and a ghost "compare" affordance appears. The user does nothing
  but look; the intelligence is ambient. This is the finance Tab.
- **Teach three keystrokes, not thirty panels.** A new user should learn `Ask`,
  `Edit-this-panel`, `Build-me-a-workspace` and be fully productive. The
  Bloomberg-style command mnemonics (the function-code firehose) are the *deep*
  layer, revealed via command palette (§5), never the front door.
- **Minimal cockpit by default.** Ship a single AAPL-anchored starter cockpit
  (the canonical 5-panel shape exists already), not an empty grid or a wall of
  every plugin. Plugins/panels (Macro, SEC, Earnings, Quant, Tradesa) appear as
  *additional tabs the agent or user opens*, never preloaded — matching the
  visual convention already codified in CLAUDE.md.
- **A context-budget indicator** belongs on the agent surface once a research
  run pulls in many symbols/filings — copy Cursor's context ring so power users
  can see and prune what the agent is reasoning over (filings, price history,
  positions, news), but keep it invisible for a one-symbol question.

---

## 4. The apply / diff / accept interaction model — Vysted's trust spine

This is the single most important pattern to copy *correctly*, because Cursor's
own community documents the cost of getting it wrong.

### What worked (copy this)
- **Red/green inline diffs** for every modification — a clear before/after,
  shown *in place*. ([Cursor forum][forum])
- **Per-change Apply/Accept controls** — "each change / each location" had its
  own Apply button; users reviewed "file by file, chunk by chunk" and could
  "accept what I wanted, and reject what I didn't." ([Cursor forum][forum])
- **A hard preview→applied boundary.** Changes were "preview/pending" until
  approved — "one click away from approving or discarding," approved *before*
  committed to disk. Keyboard: `Cmd+Return` accept all, `Cmd+Backspace` reject
  all, plus per-hunk controls. ([Cursor forum][forum], [Cursor shortcuts][ks])
- Why it mattered (their words): "It felt safe to let the Agent work because I
  was always one click away." Without it, "logic is broken until I've already
  absorbed a huge diff." The granular review *is* the human-in-the-loop model. ([Cursor forum][forum])

### What broke (the anti-pattern — do NOT copy)
Recent Cursor versions started **auto-applying edits without the diff/approval
UI**, showing diffs only in the chat panel after the fact. The community
reaction was severe: users call per-change Apply "your best UX advantage" and
frame auto-apply as contradicting production-code safety practice. ([Cursor forum regression][reg], [Cursor forum][forum])

### Vysted implication
- **Every agent-proposed mutation gets a reviewable diff before it lands.** A
  panel-config change shows old→new (indicators added, columns changed,
  screener filters). A *portfolio* change shows the position delta. A workspace
  build shows the panels-to-be-created as a stageable list. Accept-all /
  reject-all / per-item, keyboard-driven.
- **For order placement this is non-negotiable and already half-built.** The
  §6.5 `confirm_and_place` gate *is* the "accept the diff" boundary for the
  highest-stakes mutation. Make its UI look and feel like Cursor's diff-accept:
  a clear preview (symbol, side, qty, est. cost, P&L impact), an explicit accept,
  an append-only audit on accept. **Never** add an auto-apply / "YOLO" path for
  orders — Cursor's regression is the cautionary tale; finance has real money
  on the line where Cursor only had a git revert.
- **Preview→applied must be a hard, visible state.** Pending panel/portfolio
  changes render in a distinct "ghost/diff" treatment until accepted, mirroring
  Cursor's pending-vs-on-disk separation.

---

## 5. Keyboard-first, command palette, context pills

Cursor is a keyboard instrument. The mouse is optional.

- **Three load-bearing shortcuts** (`Cmd+K` edit, `Cmd+L` chat, `Cmd+I` agent)
  let you "ask for help or make changes without leaving the keyboard,
  maintaining your train of thought." ([ExplainThis][et])
- **Command palette** (`Cmd+Shift+P`) is the universal escape hatch — every
  action, including "Open Editor Window," is reachable by typing. ([Cursor shortcuts][ks], [DigitalApplied 3][da3])
- **Mode/model are keyboard axes:** `Cmd+.` mode menu, `Cmd+/` loop models,
  `Cmd+E` toggle agent layout, `Cmd+B` toggle file explorer. ([Cursor shortcuts][ks], [PMs][pm])
- **Add-to-context shortcuts:** `Cmd+Shift+L` add selection to Chat,
  `Cmd+Shift+K` add selection to Edit. Selection → context is one gesture. ([Cursor shortcuts][ks])
- **Context pills:** referenced files/symbols/docs attach to the prompt as
  removable chips; the user sees exactly what the agent will reason over.

### Vysted implication
- **Vysted already has a Bloomberg-grade keyboard story to lean into** — a
  finance terminal *expects* keyboard-first. Bind the four-mode spine to stable
  global hotkeys (Ask / Edit-panel / Build / Delegate) and make a **command
  palette the front door to the deep layer**: every panel type, every plugin
  command, every symbol jump, every agent — fuzzy-searchable. This is where the
  Bloomberg function-code muscle memory lives without cluttering the default UI.
- **Selection → context in one gesture.** Select rows in the Watchlist, a region
  on the Chart, a line in an earnings table → one hotkey attaches it to the
  agent as a context pill. This is the finance `Cmd+Shift+L`.
- **Mode/model/agent as keyboard axes.** `Cmd+.` to switch which agent persona
  is active (Buffett vs Dalio vs Researcher vs Strategy Critic), `Cmd+/` to
  switch LLM provider (Vysted is BYOK multi-provider — this maps perfectly).

---

## 6. @-mentions and making the agent workspace-aware

Cursor's context system is what makes the agent feel like it *knows your
project*. Two halves: **explicit @-mentions** (user-supplied context) and
**ambient indexing/rules** (the agent finds its own context).

### Explicit @-mentions (the menu that appears when you type `@`)
([Cursor mentions docs][mentions], [DataLakehouse][dlh])
- **@Files / @Folders** — pin specific files/dirs.
- **@Code / @Symbols** — a specific function/class/variable; granular focus.
- **@Codebase** — semantic search over the *whole* project ("the most powerful
  @-mention"); the agent retrieves the relevant files itself.
- **@Docs** — official library docs, plus user-added docs indexed by URL.
- **@Git** — `@Commit` (diff of working state), `@Branch` (diff with main).
- **@Terminals** — terminal output as context.
- **@Past Chats** — prior conversations.
- **@Browser / @Web** — web/page content.

The philosophy: "if you're not sure which files matter, skip it — Agent finds
relevant files through its own search." Explicit when you want precision,
ambient when you don't. ([Cursor mentions docs][mentions])

### Ambient workspace-awareness
- **Codebase indexing** — the project is semantically indexed so @Codebase and
  Agent search work; Tab pulls current file + open tabs + recent edits +
  project structure. ([Neon][neon], [eastondev][east])
- **Rules files** (`.cursorrules` / project rules) — durable, project-scoped
  instructions injected into every relevant prompt. The agent's *standing
  orders*.
- **MCP servers** — external tools/data the agent can call.
- **Context ring** — visual budget across system prompt, tools, rules, MCP,
  subagents, summarized history, active exchange; auto-compresses older context
  when full. ([Cursor mentions docs][mentions])

### Vysted implication
Translate @-mentions into a **finance context vocabulary**. This is a concrete,
high-leverage spec:
- **@Symbol** (AAPL, BTC/USDT) — the finance @File. The atomic context unit.
- **@Portfolio / @Position** — pin holdings / a specific position; the agent
  reasons over real P&L. (Read-only into Ask; gated for any mutation.)
- **@Panel** — "this chart with its indicators," "this screener with its
  filters" — the finance @Symbols, pinning a *configured panel* as context.
- **@Watchlist** — a named symbol set as one pill (Vysted persists watchlists —
  Phase 10).
- **@Filing / @Docs** — SEC filings (Vysted has SEC EDGAR + XBRL), earnings
  transcripts, broker docs. Direct analogue of @Docs; index by ticker/CIK.
- **@News** — articles + sentiment already in the News panel.
- **@Workspace** — the whole cockpit state (the finance @Codebase): "what's on
  my screen right now and how does it relate?"
- **@Macro / @Screen / @Backtest** — macro series (FRED/ECB/IMF/WB), a screener
  result set, a backtest run as context.

Ambient awareness, finance edition:
- **Index the workspace**, not just files: open panels, watched symbols, current
  positions, recent interactions — so the agent answers "why is *my screen* red"
  without the user pinning anything. This is Vysted's codebase index.
- **Rules files → a `.vystedrules` / standing-context per workspace:** the
  user's risk tolerance, base currency, time horizon, "never suggest leverage,"
  preferred indicators, benchmark. The agent's standing orders — injected into
  every agent turn. High-value and currently absent.
- **MCP is already the architecture** (Vysted runs openbb-mcp, sec-edgar-mcp).
  Frame these to the user as the agent's "tools," Cursor-style, so its
  capabilities are legible.
- **Context pills are removable, visible, and finance-typed** — the user always
  sees the agent is reasoning over `@AAPL @MyPortfolio @SPY-chart @Q3-10Q` and
  can drop any of them. Pair with a finance context ring once a research sweep
  pulls in dozens of filings/series.

---

## 7. Serving BOTH hand-users and agent-leaners as first-class

This is the explicit tension Cursor lives in and the one Vysted must resolve.
Cursor's stated design accommodates **two personas in one app**:
- **Agent-delegators** — run multiple autonomous agents in parallel; manage a
  team, review and direct rather than type. (Novices live here too: "much easier
  to use Agent — you won't have to select context or understand the code.")
- **Hands-on editors** — switch to the full IDE for "precise, synchronous
  control when needed." ([InfoQ][infoq], [PromptWarrior][pw])

The honest part: the community *feels the seam*. "Agent-first needs ambient,
background autonomy. Code-first needs precise, synchronous control." Cursor
serves both but users report friction at the boundary. The lesson for Vysted is
not "it's solved" — it's **make the switch between the two a single, fast,
non-destructive gesture**, and make sure neither persona is a second-class
citizen. ([InfoQ][infoq])

How Cursor keeps both first-class:
- **Same context, both modes.** Agents and the editor share project context;
  what the agent knows, the hand-user sees, and vice versa.
- **Non-destructive handoff.** local↔cloud, agent↔editor — you move a session,
  you don't lose it.
- **The diff is the meeting point.** Agent proposes, human reviews in the *same*
  diff surface a hand-editor would use. Neither persona is locked out of the
  other's view.

### Vysted implication
- **Two front doors, one workspace.** A novice opens Vysted and *talks*: "show
  me how Apple's doing" → the agent builds the cockpit (Composer behavior). A
  power trader opens Vysted and *drives*: drags panels, sets indicators, places
  orders by hand. Both manipulate the *same* dockview workspace and the *same*
  portfolio — the agent's actions and the human's actions are the same kind of
  object. Don't build a "simple mode" and a "pro mode" as separate apps; build
  one workspace with a low-floor agent door and a high-ceiling panel door.
- **The diff/confirm surface is the shared meeting point.** When the agent
  proposes a panel build, a screener, or (gated) an order, it shows up in the
  same review surface a hand-user would touch — so the power user can take over
  mid-flight and the novice can just hit accept.
- **Non-destructive mode switching.** `Cmd+E`-style toggle between "agent takes
  the cockpit" and "panels take the cockpit," and the ability to hand a
  long-running research/backtest agent to the background while you trade by hand
  — without killing it. Vysted's sidecar + agent runtime already supports
  long-running sessions; the *surface* for "send to background / bring forward"
  is the missing piece.
- **Make neither persona feel bolted-on.** Today Vysted is panel-first with a
  chat sidebar — the agent-leaner is second-class. The redesign should reach
  parity: a novice who never touches a panel directly should still feel the
  product was built for them, because the agent is a primary surface that
  *renders into panels* on their behalf.

---

## Anti-patterns Cursor teaches by negative example
- **Auto-apply without a diff** destroys trust — users called the per-change
  Apply Cursor's "best UX advantage" and revolted when it was removed. For
  Vysted's order path this isn't UX, it's safety. ([Cursor forum][forum], [Cursor regression][reg])
- **Opaque consumption/credits.** Cursor's Auto-mode credit opacity drew
  complaints. Vysted is BYOK — keep provider/model/cost legible (which provider,
  which model, est. tokens) on the agent surface. ([Substack dissection][shambhavi])
- **Feeling the seam between modes.** Don't ship the agent surface and the panel
  cockpit as two apps; the friction Cursor's users report comes from a hard
  boundary. Shared context + shared diff surface + non-destructive switch are
  the mitigations.

---

## Sources
- [InfoQ — Cursor 3 Introduces Agent-First Interface][infoq]
- [DigitalApplied — Cursor 2.0 Agent-First Architecture Guide][da20]
- [DigitalApplied — Cursor 3 Agents Window / Design Mode Guide][da3]
- [DigitalApplied — Cursor 3 Deep Dive: Agents + Composer (Plan Mode)][da3deep]
- [The Prompt Warrior — The 3 Cursor AI Modes (Chat, Composer, Agent)][pw]
- [Cursor for PMs — Using Cursor's Interface][pm]
- [Cursor Docs — Keyboard Shortcuts][ks]
- [ExplainThis — The Three Essential Cursor Shortcuts][et]
- [Cursor Docs — Prompting agents / @-mentions][mentions]
- [DataLakehouseHub — Context Management Strategies for Cursor][dlh]
- [eastondev — Cursor Codebase Indexing & @ Symbol guide][east]
- [Neon — Meet Cursor Tab][neon]
- [Rudrank — Exploring Cursor: Autocompletion with Tab][tab]
- [Cursor Forum — Bring back per-change Apply + inline diff review][forum]
- [Cursor Forum — Regression: AI edits applying without Diff/Approval][reg]
- [Product with Shambhavi — AI Agent Products Dissected: Cursor and Replit][shambhavi]

[infoq]: https://www.infoq.com/news/2026/04/cursor-3-agent-first-interface/
[da20]: https://www.digitalapplied.com/blog/cursor-2-0-agent-first-architecture-guide
[da3]: https://www.digitalapplied.com/blog/cursor-3-agents-window-design-mode-complete-guide
[da3deep]: https://www.digitalapplied.com/blog/cursor-3-deep-dive-agents-composer-review-2026
[pw]: https://www.thepromptwarrior.com/p/the-3-cursor-ai-modes
[pm]: https://www.cursorforpms.com/fundamentals/interface
[ks]: https://cursor.com/docs/reference/keyboard-shortcuts
[et]: https://www.explainthis.io/en/ai/cursor-guide/1-3-basic-commands
[mentions]: https://cursor.com/docs/context/mentions
[dlh]: https://datalakehousehub.com/blog/2026-03-context-management-cursor/
[east]: https://eastondev.com/blog/en/posts/dev/20260115-cursor-codebase-index-guide/
[neon]: https://neon.com/blog/tab-coding-cursor
[tab]: https://rudrank.com/exploring-cursor-autocompletion-with-tab
[forum]: https://forum.cursor.com/t/bring-back-per-change-apply-inline-diff-review-you-re-throwing-away-your-best-ux-advantage/160856
[reg]: https://forum.cursor.com/t/regression-ai-edits-applying-automatically-without-diff-approval-ui/154887
[shambhavi]: https://productwithshambhavi.substack.com/p/ai-agent-products-dissected-cursor
