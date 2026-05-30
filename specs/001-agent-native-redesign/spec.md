# Feature Specification: Agent-Native Finance Workspace (the redesign)

**Feature Branch**: `001-agent-native-redesign`

**Created**: 2026-05-30

**Status**: Draft — for operator review (Window 1: understand + spec; no build)

**Last amended**: 2026-05-31 — (a) operator amendment: the plugin marketplace is the **primary
extensibility model** (brokers, data providers/connectors, panels, and agents are all marketplace
plugins; no hardcoded default broker); (b) operator clarification: first-party panels, data providers,
and agents ship **pre-installed as built-in plugins** (bundled + enabled by default so first run is
populated), brokers ship with **none** pre-installed, and the keyless data default (yfinance) is a
pre-installed data plugin. See Clarifications → Sessions 2026-05-31 / 2026-05-31b, US10, FR-050–FR-055.

**Input**: Reframe Vysted Terminal as an open-source, AI-native finance workspace —
"Cursor for finance" as the internal design metaphor, **not** the external tagline.
Keep the working foundation (sidecar + data layer, dockview panels + persistent
layouts, §6.5 safety, Kite read-only + BYOK keychain, the copilot tool loop); rebuild
the **experience** into a hybrid, two-co-equal-mode app: a dense pro command-station
**and** an agent-first JARVIS that drives the terminal for a novice. Put the agent at
the center as a primary surface, and expose every capability as MCP tools so Vysted is
both a product and a framework others build finance agents on.

> Grounding: this spec is built on `docs/CURRENT_STATE.md` (the honest baseline),
> `docs/research/redesign/REFERENCE_SYNTHESIS.md` (Cursor/OpenBB/Fincept/MCP/landscape
> study), and `.specify/memory/constitution.md` (the seven principles). It describes
> **what** and **why**, never **how**. `[NEEDS CLARIFICATION]` markers flag open
> product decisions consolidated in §"Open Product Decisions" for operator review.

---

## Clarifications

### Session 2026-05-30 (operator ratification)

- **Broker order-execution scope** (reverses BLUEPRINT §2 Locked) → **Defer execution.**
  Read-only broker data only; the §6.5 execution machine stays dormant (paper-default,
  never live). Live execution becomes a separate, later, ratified track. This Tier-4
  reversal of the §2 Locked decision is hereby operator-ratified.
- **Redesign ambition / v1 cut** → **Full agent-first shell, phased.** P1 (US1–US4:
  dual-mode agent surface + four-mode spine + diff/accept gate) is the redesign core; P2
  (US5–US7: MCP-as-framework + unified catalog + new shell) follows; P3 (US8–US9: data
  hub + durable agents) after. One coherent, sequenced build — not a parallel "simple app."
- **MCP-as-framework depth** → **Also build the plugin marketplace.** Beyond unifying the
  capability catalog + auto-deriving the MCP surface + a stdio entrypoint / port-discovery
  file, the **filesystem plugin loader + marketplace + signing** are pulled INTO this
  redesign (NOT deferred). Vysted-as-a-framework is a first-class goal of the build.
- **Default agent / first-run provider** → **Offer both at first run.** Onboarding presents
  either a cloud BYOK key (Anthropic/OpenAI/…) **or** a guided local-model (Ollama) setup;
  the user picks. No silent default to a possibly-absent local model.
- **External positioning / tagline** → **Confirmed.** "Cursor for finance" stays an **internal
  design metaphor only**; external/public positioning leads with **"the AI-native, extensible
  finance workspace."** Operator-ratified.
- **DataHub pub/sub + symbol-group panel linking** → **Defer.** Keep the provider-shaped data
  registry (US8) in this redesign; sequence the typed pub/sub bus **and** symbol-group panel
  linking as a later track. The visible payoff being deferred is **symbol-group panel linking**
  (change the ticker in one linked panel → all linked panels follow). Operator-ratified.

### Session 2026-05-31 (operator amendment — plugin-marketplace extensibility)

This amendment **sharpens** (does not reopen) the 2026-05-30 decisions; the six ratified
clarifications above stand byte-for-byte, except the kept-foundation assumption is updated per the
Kite bullet below.

- **Plugin marketplace = the primary extensibility model** → **Everything is a marketplace
  plugin.** Beyond the 2026-05-30 "include marketplace" decision, the marketplace is not merely the
  MCP-framework distribution channel — it is the app's **primary extension spine**. **Brokers, data
  providers/connectors, panels, and agents are all delivered as install/enable/configure/remove
  marketplace plugins** (like Cursor extensions), not hardcoded first-class citizens. This is a
  whole-app extensibility rebuild, not a tweak. (See US10, FR-050, FR-053.)
- **No hardcoded default broker** → The host MUST NOT bootstrap any broker at boot;
  `bootstrap_default_adapters()` (today boot-registers Dhan/Angel/Kite — `CURRENT_STATE.md` §3.5) is
  **retired as the broker entry path**. A user installs the broker(s) they want from the
  marketplace and supplies BYOK creds. The seven dead-wired broker plugins (§3.4) become real,
  installable reference plugins (or are rebuilt as such), not dead fixtures. (See FR-051.)
- **Kite = the first reference broker plugin** → The working Kite read-only OAuth logic is **kept
  but repackaged** as the reference broker marketplace plugin — not rebuilt, not a hardcoded
  default. The kept-foundation assumption is updated accordingly. (See FR-052; Assumptions.)
- **Marketplace trust depends on real plugin-runtime guarantees** → the manifest↔instance id/
  version checks, `requiredHostVersion` checks, and `PluginConfig` secret resolution that
  `CURRENT_STATE.md` §3.4 records as documented-but-absent MUST become real. (See FR-054.)
- **Safety stays host-enforced, never plugin-delegated** (HARD GUARDRAIL) → no plugin may bypass
  the §6.5 boundary; the host enforces paper-default, read-only, kill switch, position limits, the
  diff/accept gate, and append-only audit; plugins plug INTO them and cannot opt out. The Tradesa-V2
  read-only plugin is the working precedent (§5: three enforcement layers). Tier-1 LOCKED files and
  §6.5 invariants stay byte-for-byte untouched. (See FR-055.)

### Session 2026-05-31b (operator clarification — first-party features ship pre-installed as built-in plugins)

This clarification **sharpens** (does not reopen) the unified-extension-model decisions above. It
reconciles "everything is a marketplace plugin" (FR-050/US10) with "first run is a populated starter
cockpit" (FR-032): the *one extension model* and *populated first-run* are not in tension because the
first-party features **are** plugins — pre-installed ones.

- **First-party panels, data providers, and agents ship PRE-INSTALLED as built-in plugins.** They are
  delivered through the **same** unified extension model as everything else (FR-050/FR-053) — they are
  not a separate hardcoded path — but they are **bundled and enabled by default** so first run is
  populated out of the box (FR-032). "Built-in" describes *distribution* (pre-installed, enabled,
  removable like any plugin), not a *privileged registration path*: a first-party plugin loads through
  the same runtime, manifest↔instance + `requiredHostVersion` checks, and §6.5 gate as a third-party
  one (FR-054/FR-055). The dogfooding principle (Constitution V) is satisfied because first-party
  features exercise the real contract.
- **The keyless data default ships as a pre-installed data plugin.** The no-key equity default
  (yfinance) is delivered as a bundled, enabled data-provider plugin so the terminal serves real data
  on first launch with zero credentials — the "works out of the box" guarantee. It is the reference
  pre-installed instance of the data slice of the one extension model (FR-053).
- **Brokers ship with NONE pre-installed.** No broker is bundled-and-enabled at first run; this is the
  same statement as FR-051's "no broker is hardcoded or registered at boot," now also covering the
  pre-installed set: the user installs the broker(s) they want from the marketplace and supplies BYOK
  creds. Kite remains the canonical *reference* broker plugin (FR-052) — available to install, not
  pre-installed.
- **Net effect on acceptance:** FR-032's populated first-run is satisfied by the pre-installed
  first-party plugin set (panels + the keyless data plugin + the default agent); SC-013's "no broker
  registered at boot / installable-and-removable through the marketplace" is unaffected because brokers
  are explicitly excluded from the pre-installed set.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — The novice talks to the terminal (agent-driven cockpit) (Priority: P1)

A first-time, finance-curious user opens Vysted, types or says "show me how Nvidia is
doing," and the agent **drives the terminal for them**: it opens a chart on NVDA, sets
a sensible timeframe, opens an equity-overview panel, pulls fundamentals and recent
news, and narrates a plain-language read — citing its sources and naming the data
provider. The user then says "compare it to AMD," and the agent stages a comparison.
The user never had to know a function code, a panel name, or a ticker convention. At
any moment they can reach out and grab a panel by hand.

**Why this priority**: This is the redesign's reason to exist — the "ease (talk to it)"
half of the hybrid thesis, and the largest single UX change (promote the agent from one
panel among 18 to a primary surface whose output is the cockpit). Without it there is no
"AI-native" product, only the existing data viewer.

**Independent Test**: With a BYOK key configured, a user who has never seen the app can,
through conversation alone, end up with a populated multi-panel cockpit for a chosen
company and a cited explanation — without touching a panel control. Fully testable as a
scripted conversation → resulting workspace state + rendered panels + citations.

**Acceptance Scenarios**:

1. **Given** a fresh workspace and a configured provider, **When** the user asks the
   agent about a company in natural language, **Then** the agent opens the relevant
   panels (chart, overview, news), sets the symbol/timeframe, and returns a narrated,
   source-cited summary — with each data claim attributable to a named provider.
2. **Given** the agent has populated the cockpit, **When** the user issues a follow-up
   ("now add a 200-day average", "compare to AMD"), **Then** the agent modifies the
   existing panels (it does not start over), and the change is surfaced as a reviewable
   action (see US4).
3. **Given** the agent is mid-explanation, **When** the user clicks into a panel and
   manipulates it by hand, **Then** the manipulation is honored immediately and the
   agent's subsequent context reflects the new hand-driven state (one shared context).
4. **Given** no provider key is configured, **When** the user first interacts with the
   agent, **Then** onboarding guides them to configure a provider before the agent
   attempts a call (no silent failure against an absent local model).

---

### User Story 2 — The pro drives by hand (dense command-station preserved) (Priority: P1)

A finance-literate user ignores the agent and works the terminal directly: opens a
screener, filters to mid-cap semis, charts a result with VWAP + two indicators, pulls
the 10-K, checks the options chain in the quant panel, and arranges a 6-panel cockpit —
all by keyboard and pointer, through a command palette that teaches its own shortcuts.
Every capability the agent can invoke is reachable by hand, and nothing about the
agent-first posture slows the expert down.

**Why this priority**: The "complexity (full terminal underneath)" half of the hybrid
thesis. The expert is the credibility audience (research-lab voice) and must remain
first-class; the failure mode to avoid is a chat app that buried the terminal.

**Independent Test**: A user can complete a full analysis workflow (screen → chart →
fundamentals → filing → quant) using only the command palette + panels, with zero agent
turns, and persist the resulting workspace across relaunch.

**Acceptance Scenarios**:

1. **Given** the command palette, **When** the user types a partial command/symbol/panel
   name, **Then** fuzzy-ranked results appear with their keyboard mnemonic shown, and
   selecting one performs the action.
2. **Given** a populated cockpit built by hand, **When** the user relaunches the app,
   **Then** the exact layout, enabled modules, drawings, and watchlist are restored.
3. **Given** any capability the agent exposes, **When** the user looks for it in the
   palette/menus, **Then** it is reachable by hand under a discoverable name.

---

### User Story 3 — The four-mode agent spine (Priority: P1)

The agent is not one chat box but **four intents on stable hotkeys**, mapped to finance
verbs: **Ask** (read-only Q&A over the workspace), **Edit-panel** (a surgical change to
the panel in focus — "add VWAP + 200-EMA", "add a P&L column", "filter to mid-caps"), and
**Build** (compose multiple panels/a workflow — "build me a semiconductor cockpit"), and
**Delegate** (an autonomous background task — a backtest critique, a multi-name research
sweep, a condition monitor). The current mode, the active persona, and the active
provider/model are always visible and switchable by keyboard.

**Why this priority**: Mode discoverability is the known failure of "Ask-vs-Agent" UIs
(users pick wrong half the time). Making the intents explicit, visible, and consequence-
labeled at the point of use is what makes agent-centrality usable rather than a trap.

**Independent Test**: Each mode is independently exercisable: Edit-panel changes only the
focused panel; Build stages a multi-panel result; Delegate runs in the background and
appears in an agents rail with status; Ask never mutates. Mode/persona/provider switches
are observable in the UI state.

**Acceptance Scenarios**:

1. **Given** a focused chart, **When** the user invokes Edit-panel and asks for an
   indicator, **Then** only that chart's configuration changes (scoped to the focus).
2. **Given** Build mode, **When** the user asks for a themed cockpit, **Then** a
   stageable set of panels-to-create is proposed (not auto-applied — see US4).
3. **Given** Delegate mode, **When** the user launches a background task, **Then** it
   appears in an agents rail with live status and can be brought to the foreground or
   cancelled, and it is bounded by a hard budget (see FR-026).
4. **Given** any mode, **When** the user switches persona or provider via keyboard,
   **Then** the change is reflected immediately and visibly.

---

### User Story 4 — The diff/accept trust gate (Priority: P1)

Every change an agent proposes — a panel re-configuration, a portfolio edit, a
multi-panel build, and **especially** an order — is presented as a **reviewable
preview→applied diff**: the user sees old→new, accepts or rejects all or per-item, by
keyboard, before anything lands. For orders, this gate **is** the §6.5
`confirm_and_place` boundary (symbol, side, quantity, estimated cost, P&L impact,
explicit accept, append-only audit on accept). There is no auto-apply path for orders,
ever.

**Why this priority**: This is the trust spine. Finance has no `git revert` on a placed
order; verification is the product. Copying Cursor's diff/accept *correctly* (and
refusing its auto-apply regression) is non-negotiable and is a constitutional principle.

**Independent Test**: An agent-proposed mutation never alters state until the user
accepts; rejecting leaves state unchanged; accepting an order writes exactly one
append-only audit row and respects paper-mode/kill-switch/read-only/position-limit
checks.

**Acceptance Scenarios**:

1. **Given** the agent proposes a panel/portfolio/build change, **When** it is presented,
   **Then** the user sees a clear old→new diff with per-item and bulk accept/reject, and
   no state changes before acceptance.
2. **Given** the agent proposes an order, **When** the review dialog appears, **Then** it
   shows symbol/side/qty/est-cost/P&L-impact, requires explicit human confirmation, and
   on accept routes through the existing §6.5 `confirm_and_place` path (paper by default).
3. **Given** the kill-switch is active or read-only mode is on, **When** any order is
   proposed, **Then** placement is blocked and the block is explained.

---

### User Story 5 — Vysted as an MCP framework (one catalog, many consumers) (Priority: P2)

An external agent (Claude Code, or any MCP client) connects to Vysted and drives the
**same** capabilities the built-in copilot uses — quotes, charts, screener, fundamentals,
portfolio, news, quant, brokers (read-only) — because there is **one capability catalog**
projected to both the internal agent and the external MCP surface. A developer can build
a finance agent or trade-bot on Vysted without re-implementing data access. Read-only is
the default; mutations carry the same gate everywhere.

**Why this priority**: The framework story is the durable differentiator (the moat is the
platform, not the agent roster). It also de-risks the agent surface by giving it one
coherent, complete toolset — and it closes the real current gap where the internal and
external tool surfaces have diverged.

**Independent Test**: A capability added once is callable by both the internal copilot and
an external MCP client by the same name with the same `read_only` semantics; an external
client can complete a read-only analysis end-to-end over MCP.

**Acceptance Scenarios**:

1. **Given** a new capability is registered once, **When** an external MCP client lists
   tools, **Then** it appears with a domain tag and a `read_only` annotation matching the
   internal gate.
2. **Given** an external MCP client, **When** it drives quotes/charts/screener/
   fundamentals/portfolio/news/quant/brokers-read, **Then** every domain is reachable by
   the same tool names the internal copilot uses.
3. **Given** the catalog, **When** the internal copilot is asked to use any capability,
   **Then** there is no capability reachable to one consumer but not the other.
4. **Given** a loopback bind, **When** a client connects, **Then** no auth is required; a
   non-loopback bind is a Tier-4 block-and-ask (out of scope here).

---

### User Story 6 — Minimal-dark shell + teaching command palette (Priority: P2)

The shell is redesigned in a minimal, dark, low-chrome language (Cursor-like), superseding
the warm "Claude after dark" palette. It is simple by default — a new user learns a few
keystrokes — and progressively complex: the command palette is the deep front door
(Bloomberg's command grammar reborn) and **teaches its own mnemonics** as the user works.
A minimal, populated starter cockpit is the default; plugins/panels open as tabs the user
or agent opens, never preloaded en masse. A persistent, legible status surface shows
sidecar connection, active provider/model, and running agents.

**Why this priority**: The current shell is "a data viewer with a raw LLM chat bolted on";
the look and information hierarchy must be rebuilt around the agent for the product to read
as AI-native. Density with progressive disclosure is the constitutional UX principle.

**Phasing note (the behavioral leap is P1; the visual leap is P2)**: Agent-centrality (US1–US4)
ships in **P1 on the *existing* shell** — today's dockview cockpit and chrome — so the agent-first
experience is usable *before* any reskin. This story (US6) — the minimal-dark visual rebuild, the
redesigned command palette, and the status chrome — is the **visual leap and lands in P2**. P1 puts
the new behavior on the old skin; P2 delivers the new skin. This is deliberate, not a surprise.

**Independent Test**: A first-run user reaches productivity through ≤3 taught gestures; the
palette fuzzy-ranks and surfaces shortcuts; the shell renders dark-only with a visible
connection/provider/agents status that today is "computed but not surfaced."

**Acceptance Scenarios**:

1. **Given** first run, **When** the app opens, **Then** a minimal populated starter
   cockpit appears (not an empty grid, not every plugin), with the agent surface present.
2. **Given** the command palette, **When** the user performs an action, **Then** its
   keyboard mnemonic is surfaced so the user learns it for next time.
3. **Given** any session, **When** the user looks at the chrome, **Then** sidecar
   connection state, active provider/model, and any running background agents are visible.

---

### User Story 7 — One unified, complete capability catalog (Priority: P2)

The internal `agent_tools` catalog and the external MCP server become **one source of
truth**: every terminal capability is a catalog entry with a domain tag and a `read_only`
flag, rendered to the internal copilot and the external MCP adapter by transformation, not
by hand-maintained duplication. The current gaps are closed: every registered handler that
should be agent-reachable has a schema entry (today ~11 do not), the custom-agent
allow-list reflects the real catalog, and multi-round tool use works across all supported
providers.

**Why this priority**: This is the substrate the agent-centric experience and the framework
both stand on. The current divergence quietly caps what the agent can do (e.g. the entire
QuantLib quartet is invisible to every model) and is a correctness liability.

**Independent Test**: Every catalog entry is reachable by the internal loop and the external
MCP surface; a parity check shows no capability missing from either; multi-round tool use
succeeds on each supported provider with a representative two-step task.

**Acceptance Scenarios**:

1. **Given** the catalog, **When** a parity audit runs, **Then** internal-reachable and
   MCP-exposed tool sets match (modulo intentionally-internal items), each tagged by domain
   and `read_only`.
2. **Given** a multi-round task, **When** run on each supported provider, **Then** the agent
   completes the tool→result→tool chain correctly (closing the current Gemini break).
3. **Given** a custom agent, **When** the user selects allowed tools, **Then** the choices
   match the real catalog and every selectable tool resolves.

---

### User Story 8 — Provider-shaped data registry + BYOK/credentials hub (Priority: P3)

Data providers, brokers, and user-wired connectors all declare their credentials and shape
declaratively; the host renders a single BYOK/credentials hub from those declarations
(label, type, secret, where-to-get-it, instructions, optional "needs no key"). The data
registry resolves by a standard model key + preference order (not a hardcoded
`if asset_class` chain), so two sources serving the same kind are interchangeable, and every
result carries its provider as provenance. Secrets stay in the OS keychain, least-privilege
at use. Connections can be exported/imported across machines.

**Why this priority**: This makes "the data isn't the limit" real and turns the inert
DataSource capability into a working extension surface — but it sits on top of the agent
experience and framework, so it is sequenced after them.

**Independent Test**: A new data source declared via the contract appears in the credentials
hub with a generated form, resolves through the registry by model key, and tags its results
with provenance — with no per-source UI code.

**Acceptance Scenarios**:

1. **Given** a provider declaration, **When** the credentials hub renders, **Then** its
   form (fields, masking, get-key link, instructions, no-key opt-out) appears generically.
2. **Given** two sources of the same kind, **When** the registry resolves a request, **Then**
   it picks by preference order and the result names the provider that served it.
3. **Given** configured connections, **When** the user exports then imports on another
   machine, **Then** the wired sources are restored (secrets via the keychain, not the file).

---

### User Story 9 — Durable agents with a budget guard (Delegate, safely) (Priority: P3)

Background ("Delegate") agent runs are durable and bounded: a long task checkpoints its
progress (so it can resume), is governed by a **hard ceiling on tokens / spend / wall-clock
/ steps** (a BudgetGuard whose first breach aborts the run), can pause to ask the user a
question (human-in-the-loop), and can be scheduled. The agents rail shows status, cost-so-
far, and the budget.

**Why this priority**: "Delegate" mode is unsafe to ship without a spend ceiling — autonomous
agent spend is a safety surface the same way order execution is. It is P3 because it depends
on the agent surface (US1/US3) existing first.

**Independent Test**: A background run that would exceed its configured budget aborts at the
ceiling with a clear reason and a preserved checkpoint; a paused run resumes; cost-so-far is
visible throughout.

**Acceptance Scenarios**:

1. **Given** a Delegate run with a budget, **When** the run reaches the token/$/wall/step
   ceiling, **Then** it aborts on first breach with the breach reason and a resumable
   checkpoint, never silently overrunning.
2. **Given** a run that needs a decision, **When** it hits an HITL question, **Then** it
   pauses and surfaces the question in the agents rail without losing progress.
3. **Given** the agents rail, **When** a background task runs, **Then** its status, cost-so-
   far, and budget are visible and it can be cancelled.

---

### User Story 10 — Everything is a marketplace plugin (the extension spine) (Priority: P2)

A user opens the plugin marketplace and treats it as the app's front door for capability: they
browse, **install** a broker (say Kite), **enable** it, **configure** it with their BYOK
credentials, use it, and later **remove** it — with zero host code change and no app rebuild. The
same install/enable/configure/remove lifecycle governs **data providers/connectors, panels, and
agents**: brokers are not special, and **no broker (or any extension) is hardcoded or registered at
boot**. The marketplace, not a bootstrap function, is how the terminal gains a broker, a data
source, a panel, or an agent.

**Why this priority**: The 2026-05-30 clarification already pulled the marketplace/loader/signing
INTO this redesign; this story makes the marketplace the **primary** extensibility model rather than
a side channel. Today the opposite is true — `bootstrap_default_adapters()` hardcodes three brokers
at boot and the seven `plugins/brokers/` plugins are dead-wired (`CURRENT_STATE.md` §3.4/§3.5).
Unifying every extension (brokers, data, panels, agents) behind one marketplace is what makes
"Vysted as a framework" real and keeps the surface honest (one extension model, not two parallel
ones). It sequences with the P2 marketplace workstream; the granular phase order is not load-bearing
(operator-indifferent — one long sequential build). _(Numbered after US9 to avoid renumbering the
ratified P1–P3 stories; its P2 priority is independent of doc position.)_

**Independent Test**: A broker absent from the app can be installed, enabled, BYOK-configured,
exercised (read-only), and removed entirely through the marketplace — with no broker registered at
boot and no host code change — and the same lifecycle visibly governs a data-source plugin, a panel
plugin, and an agent plugin.

**Acceptance Scenarios**:

1. **Given** a fresh install with no broker present, **When** the user installs and enables a broker
   plugin from the marketplace and supplies BYOK creds, **Then** the broker connects and serves
   read-only data plug-and-play — with nothing broker-specific having been compiled in or registered
   at boot.
2. **Given** an enabled broker plugin, **When** the user removes it from the marketplace, **Then**
   its capabilities, panels, and credential forms disappear cleanly and no boot-time registration
   re-adds it.
3. **Given** the marketplace, **When** the user inspects data providers/connectors, panels, and
   agents, **Then** each is an install/enable/configure/remove extension under the **same** model as
   brokers (not a separate hardcoded path).
4. **Given** a plugin declaring an incompatible `requiredHostVersion` or a manifest↔instance id/
   version mismatch, **When** the host loads it, **Then** it is rejected and surfaced — never
   silently loaded (see FR-054).
5. **Given** any installed plugin (broker or otherwise), **When** it attempts a write/execution or
   any state mutation, **Then** the host §6.5 gate governs it (paper-default, read-only, kill switch,
   position limits, diff/accept, append-only audit); the plugin cannot opt out (see FR-055).

### Edge Cases

- **No provider configured / local model absent.** First agent use must route to onboarding,
  never fail silently against an uninstalled Ollama model (the current shipped default).
- **Sidecar not yet bound / MCP cold-bind (~34s).** The shell must show a connecting state
  and degrade gracefully (data panels retry; MCP-backed features fall back), never block boot
  or panic. (Current boot path `.expect()`-panics on main-sidecar spawn failure — to be
  hardened.)
- **Agent proposes a mutation while kill-switch active / read-only / paper-mode.** The diff
  gate must block placement and explain, not present an acceptable order.
- **Conflicting hand + agent edits.** Hand manipulation wins immediately; the agent's next
  turn sees the new state (one shared context).
- **Provider that returns no key-less data / partial provider failure.** Surface "needs a
  key" or partial results with provenance; never fabricate data behind a populated surface.
- **External MCP client requests a mutating tool.** Same gate as internal; read-only by
  default; a mutation requires the same confirmation path.
- **Workspace blob from an older version / unknown component.** Restore must skip to the
  bundled default rather than corrupting the grid (current behavior — preserve it).
- **Plugin incompatible with the host (manifest↔instance id/version mismatch / unmet
  `requiredHostVersion`).** The runtime must reject it at load and surface why — never silently load
  an incompatible plugin (today these checks are documented but absent — §3.4).
- **A broker (or any) plugin attempts a write/execution path.** The host §6.5 gate governs it
  regardless of plugin code (paper-default, read-only, kill switch, position limits, diff/accept,
  append-only audit are all host-enforced); the plugin cannot opt out.

## Requirements *(mandatory)*

### Functional Requirements — Agent-centric experience

- **FR-001**: The agent MUST be a primary, co-equal surface (not a bolted-on sidebar) able
  to occupy a dominant column or the full cockpit, whose actions **open and arrange panels**
  as its output.
- **FR-002**: The agent MUST be terminal-aware — it can read the focused symbol/timeframe/
  indicators, watchlist, portfolio, and open panels, and can open panels, set symbols, edit
  the watchlist, and stage actions.
- **FR-003**: The system MUST present the agent as four explicit intents on stable global
  hotkeys — **Ask** (read-only), **Edit-panel** (focused-panel change), **Build** (multi-
  panel/workflow), **Delegate** (background) — with the active mode visible at all times.
- **FR-004**: The active persona and active provider/model MUST be visible and switchable by
  keyboard at any time.
- **FR-005**: Every capability invocable by the agent MUST also be reachable by hand (palette/
  menus/panels); no agent-only capability.
- **FR-006**: After an ambiguous request, the agent MUST do the upfront work and then hand off
  to the manipulable cockpit — it MUST NOT require the user to do complex multi-object analysis
  inside the chat transcript.
- **FR-007**: Hand manipulation MUST take effect immediately and update the shared context the
  agent reads on its next turn.

### Functional Requirements — Trust gate & safety

- **FR-010**: Every agent-proposed mutation (panel config, portfolio, multi-panel build, order)
  MUST be presented as a preview→applied diff with per-item and bulk accept/reject, keyboard-
  driven; **no** mutation lands before acceptance.
- **FR-011**: Order proposals MUST route through the existing §6.5 `confirm_and_place` boundary
  (paper-mode default, position limits, read-only/kill-switch checks, append-only audit on
  accept); there MUST be no auto-apply / "YOLO" order path.
- **FR-012**: The §6.5 invariants and Tier-1 LOCKED files (`docs/CURRENT_STATE.md` §3.6/§5) MUST
  be preserved byte-for-byte unless an operator-ratified Tier-4 change is made; the audit suite
  is a hard gate on any touch.
- **FR-013**: Read-only MUST be the default for every consumer (internal and external); any
  mutation is explicit, gated, and audited.

### Functional Requirements — MCP-as-framework & unified catalog

- **FR-020**: The system MUST maintain a **single capability catalog** as the source of truth,
  projected to (a) the internal copilot adapter(s) and (b) the external MCP server, by
  transformation — no hand-maintained duplicate tool surfaces.
- **FR-021**: Each catalog entry MUST carry a domain tag and a `read_only` declaration; the
  `read_only` flag MUST drive both the internal mutation gate and the external MCP read-only
  annotation.
- **FR-022**: The external MCP surface MUST cover all primary domains (quotes, charts, screener,
  fundamentals, portfolio, news, quant, brokers-read) by the same tool names the internal copilot
  uses, so external agents can build on Vysted.
- **FR-023**: The catalog MUST be complete — every registered handler intended to be agent-
  reachable MUST have a schema entry (closing the current ~11-handler gap), and the custom-agent
  allow-list MUST reflect the real catalog.
- **FR-024**: Multi-round tool use MUST work on every supported provider for a representative
  two-step task (closing the current Gemini multi-round break).
- **FR-025**: External MCP access MUST be loopback-only without auth in this scope; any non-
  loopback exposure is a Tier-4 block-and-ask and is out of scope here. The framework MUST be
  attachable by an external agent (a documented connection path; a discovery file is desirable).

### Functional Requirements — Durable agents (Delegate)

- **FR-026**: Background ("Delegate") agent runs MUST be bounded by a hard, user-visible ceiling
  on tokens, spend, wall-clock, and steps; the first breach MUST abort the run with a stated
  reason — autonomous spend is a safety surface.
- **FR-027**: A background run MUST be visible in an agents rail with status and cost-so-far, and
  be cancellable and bring-to-foreground-able.
- **FR-028**: A long run SHOULD checkpoint progress so it can resume, and SHOULD be able to pause
  for a human-in-the-loop question without losing progress.

### Functional Requirements — Shell, data & credentials

- **FR-030**: The shell MUST be minimal-dark, low-chrome, keyboard-first, dark-only (light theme
  remains deferred), superseding the warm "Claude after dark" palette; the canvas palette and CSS
  tokens MUST be re-skinned together.
- **FR-031**: The command palette MUST fuzzy-rank panels, commands, symbols, and agents, and MUST
  surface the keyboard mnemonic for actions it performs (teach-its-own-shortcuts).
- **FR-032**: First run MUST present a minimal, populated starter cockpit (not empty, not every
  plugin) with the agent surface present; additional panels/plugins open as tabs on demand.
- **FR-033**: The chrome MUST surface sidecar connection state, active provider/model, and running
  background agents (today computed but not surfaced).
- **FR-034**: Every data provider, broker, and user-wired connector MUST declare its credentials
  and shape declaratively; a single BYOK/credentials hub MUST render/mask/test forms generically
  from those declarations (including a "needs no key" opt-out and a get-key link/instructions). These
  provider/broker/connector declarations are the data-source/broker slice of the **one** marketplace
  extension model (FR-050/FR-053), not a parallel mechanism.
- **FR-035**: The data registry MUST resolve by a standard model key + preference order (replacing
  the hardcoded asset-class dispatch); every result MUST carry its serving provider as provenance.
- **FR-036**: Secrets MUST remain in the OS keychain, least-privilege at use (a provider receives
  only its declared keys, via request, never the whole keychain), never logged/echoed/persisted;
  storage MUST NOT regress to plaintext files or machine-ID-derived encryption.
- **FR-037**: Configured connections SHOULD be exportable/importable across machines (secrets via
  the keychain, not the export file).
- **FR-038**: The system MUST provide a dedicated settings/preferences surface where effectively
  **every** user-facing preference is configurable — at minimum: keybindings, the default agent/
  persona, the default provider/model and the provider **preference order**, command-palette
  behavior, panel defaults, starter-cockpit composition, and any theming knobs available within the
  dark-only constraint. The depth target is **Cursor-grade**: prefer exhaustive configurability over
  a minimal preferences pane. Settings MUST persist locally (consistent with the local-first /
  no-cloud model) and be exportable/importable alongside the connections export in FR-037.
- **FR-039**: Keyboard shortcuts/keybindings MUST be **user-remappable** from the settings surface —
  not merely surfaced as mnemonics. (FR-031 *teaches* shortcuts; FR-039 lets the user *rebind* them,
  which the terminal cannot do today.) Conflicting bindings MUST be detected and surfaced; remaps
  persist locally and travel with the settings export (FR-038).

### Functional Requirements — Verification & provenance

- **FR-040**: Agent claims that assert facts MUST carry citations; data responses MUST carry
  provenance (which provider served them); the active provider/model/cost MUST be legible on the
  agent surface.
- **FR-041**: The system MUST NOT present fabricated or placeholder data as real; unverified or
  paper/synthetic values MUST be labeled as such (e.g. paper-mode synthetic balances).

### Functional Requirements — Broker read surface (read-only)

- **FR-042**: The read-only broker surface MUST return **genuine granular data from the live
  connected account** — distinct, real **positions, holdings, P&L, and margins** — rather than
  aliasing them all to a single account summary (today `/positions`, `/holdings`, `/margins` all
  return the same `AccountSummary`, and the granular `*_info` reads do not exist —
  `docs/CURRENT_STATE.md` §3.5). This is **net-new read implementation**, not relabeling.
  Synthetic / paper / disconnected values (e.g. the paper-mode ₹1,000,000 placeholder account) MUST
  be clearly labeled per FR-041. Scope stays **read-only**: no write/execution path is added and the
  §6.5 execution boundary (FR-011/FR-012) is untouched. The live connected account is reached through
  an **installed broker plugin** (FR-051/FR-052), not a boot-registered adapter; the phase in which
  these granular reads land is left **unsequenced** (operator-indifferent — one long sequential build).

### Functional Requirements — Plugin marketplace & unified extension model

- **FR-050**: The plugin marketplace MUST be the app's **primary extensibility model**: brokers, data
  providers/connectors, panels, and agents are all delivered as marketplace plugins the user can
  **install, enable, configure, and remove** — one unified extension model, not hardcoded first-class
  citizens and not two parallel mechanisms. The marketplace is the front door through which the
  terminal gains a capability.
- **FR-051**: No broker is hardcoded or registered at boot. The host MUST NOT bootstrap any
  broker adapter at startup — `bootstrap_default_adapters()` (today boot-registers Dhan/Angel/Kite,
  `CURRENT_STATE.md` §3.5) is **retired as the broker entry path**. A user installs/enables the
  broker(s) they want (Kite, Dhan, Bybit, …) from the marketplace, supplies BYOK creds, and the
  broker works plug-and-play. The seven existing `plugins/brokers/` plugins (today dead-wired — §3.4)
  MUST become real, installable reference plugins, or be rebuilt as such; they are no longer dead
  fixtures.
- **FR-052**: The working Kite read-only OAuth logic (the one genuine end-to-end BYOK broker path —
  §3.5) MUST be **kept and repackaged as the first reference broker plugin** — not rebuilt from
  scratch and not a hardcoded default. It becomes the canonical example every other broker plugin
  follows.
- **FR-053**: The provider-shaped data registry (FR-034/FR-035) and the plugin contract MUST describe
  **one** unified extension model, not two parallel ones: a data provider/connector's declarative
  credential+shape declaration **is** the data-source slice of the marketplace plugin model, and the
  registry resolves across installed provider plugins by standard-model key + preference order. No
  capability gains a bespoke registration path outside this model.
- **FR-054**: The plugin-runtime guarantees the marketplace depends on MUST be **real** (today
  documented-but-absent — `CURRENT_STATE.md` §3.4): the runtime MUST enforce manifest↔instance
  id/version checks, MUST check `requiredHostVersion` and refuse an incompatible plugin (surfaced, not
  silently loaded), and MUST provide working `PluginConfig` secret resolution (today effectively a
  no-op). The marketplace cannot be trustworthy without these.
- **FR-055**: **HARD GUARDRAIL — safety stays host-enforced, never plugin-delegated.** A broker (or
  any) plugin MUST NOT be able to bypass the §6.5 boundary: paper-mode default, read-only enforcement,
  the kill switch, position limits, the diff/accept gate, and append-only audit are all enforced by
  the **host**; plugins plug INTO them and cannot opt out. The Tradesa-V2 read-only plugin is the
  working precedent (`CURRENT_STATE.md` §5: three independent enforcement layers — no write methods on
  the provider surface, no non-GET routes, `supportsControlPlane: false`). Tier-1 LOCKED files
  (`types/plugin.ts`, the §6.5 LOCKED set) and every §6.5 invariant stay byte-for-byte untouched
  (FR-012).

### Key Entities *(data/contracts involved — conceptual, not implementation)*

- **Capability** — one terminal action (read or mutate) with: id, human description, input shape,
  output shape, **domain tag**, **read_only flag**, and the consumers it projects to (internal
  copilot + external MCP). The single source of truth replacing today's two divergent surfaces.
- **Agent / Persona** — a named agent with a system prompt/rubric, a default provider/model, and an
  allow-list drawn from the Capability catalog. Includes the terminal-aware router ("copilot") and
  the investor personas; user-authored custom agents conform to the same shape.
- **Agent Run** — an invocation with a mode (Ask/Edit/Build/Delegate), a context snapshot, a
  message/tool transcript, and (for Delegate) a budget, cost-so-far, checkpoint, and status.
- **Proposed Mutation (Diff)** — a previewed change (panel config, portfolio edit, build set, or
  order) with old→new state, per-item accept/reject, and an applied/append-only-audit outcome.
- **Provider / Connector** — a data source, broker, or user-wired connector declaring
  `credential_fields[]` (label, type, secret, website, instructions, require_credentials), a
  standard-model key it serves, and a preference rank. Carries provenance on results. **Delivered as
  a marketplace plugin** under the one extension model (FR-050/FR-053), not a boot-registered adapter.
- **Workspace** — the persistent cockpit blob (layout, enabled modules, drawings, watchlist,
  default provider) round-tripped through the sidecar; restore-safe against older/unknown shapes.
- **Settings / Preferences** — the local, exportable bundle of user preferences: keybindings,
  default agent/persona, default provider/model + provider preference order, command-palette
  behavior, panel and starter-cockpit defaults, and theming knobs (within the dark-only constraint).
  Persisted locally; round-trips via export/import alongside connections.
- **Plugin** — the six-capability `VystedPlugin` contract (Tier-1, unchanged) contributing data,
  panels, commands, agents, nodes, control-plane. It is the **unit of marketplace distribution**
  (install/enable/configure/remove) and the **single model** through which brokers, data providers/
  connectors, panels, and agents enter the app — no hardcoded boot registration. Loads only after the
  host's manifest↔instance + `requiredHostVersion` checks pass; receives only its declared secrets
  via `PluginConfig`; and gains no path around the host §6.5 gate (FR-054/FR-055).
- **Marketplace / Extension lifecycle** — the install→enable→configure→remove lifecycle and listing
  surface for plugins: the front door for gaining a broker, data source, panel, or agent. Enforces
  host-side compatibility (manifest↔instance, `requiredHostVersion`) and never grants a plugin a path
  around the §6.5 safety boundary.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user with a configured provider can reach a populated, multi-panel,
  source-cited cockpit for a company **through conversation alone**, with zero manual panel
  controls, in under 2 minutes.
- **SC-002**: A finance-literate user can complete a full screen→chart→fundamentals→filing→quant
  workflow **with zero agent turns**, entirely by command palette + panels, and persist it across
  relaunch.
- **SC-003**: 100% of agent-proposed mutations are blocked from changing state until explicit
  acceptance; 100% of accepted orders produce exactly one append-only audit row and honor paper-
  mode/kill-switch/read-only/position-limit checks. No auto-apply order path exists (audit-grep).
- **SC-004**: A capability added once is reachable by **both** the internal copilot and an external
  MCP client by the same name with matching read_only semantics; a parity audit reports zero
  unintended divergence.
- **SC-005**: Multi-round tool use succeeds on **every** supported provider for a representative
  two-step task (no provider-specific multi-round break).
- **SC-006**: 0 registered, agent-intended capability handlers lack a catalog/schema entry (down
  from ~11 today); the custom-agent allow-list contains 0 unresolvable tools.
- **SC-007**: A new data source added via the contract appears in the credentials hub and resolves
  through the registry with **0 lines of per-source UI code**; every data result names its provider.
- **SC-008**: A Delegate run that would exceed its budget aborts at the ceiling 100% of the time
  with a stated reason and a resumable checkpoint; cost-so-far is visible throughout.
- **SC-009**: First-run users reach productivity within ≤3 taught gestures; the command palette
  surfaces a shortcut for ≥90% of palette-performed actions.
- **SC-010**: No user data leaves the machine except through an explicitly user-wired outbound
  connector; secrets never appear in logs, responses, files, or `localStorage` (audited).
- **SC-011**: Every enumerated preference category (keybindings, default agent/persona, default
  provider/model + preference order, palette behavior, panel defaults, starter-cockpit composition,
  theming knobs) is configurable from the settings surface; a remapped keybinding persists across
  relaunch; and a settings export re-imports on another machine with zero loss.
- **SC-012**: For a live connected broker, the read surface returns **distinct, real** positions,
  holdings, P&L, and margins (not aliased to a single summary); synthetic/paper/disconnected values
  are labeled as such; and no write/execution code path exists on the broker read surface
  (audit-grep; §6.5 untouched).
- **SC-013**: A broker can be **installed, enabled, configured (BYOK), and removed entirely through
  the marketplace with zero host code change**, and **no broker adapter is registered at boot**
  (audit: the boot path registers no broker; `bootstrap_default_adapters()` is retired as the broker
  entry path). The same install/enable/configure/remove lifecycle governs a data-source, a panel, and
  an agent plugin.
- **SC-014**: A marketplace plugin **cannot place or write anything that bypasses the host safety
  gate** — no plugin code path reaches order placement or any state mutation outside the §6.5
  boundary (audit-grep, mirroring SC-003/SC-012; §6.5 untouched).
- **SC-015**: The plugin runtime **enforces its guarantees**: a manifest↔instance id/version mismatch
  and a `requiredHostVersion` violation are each **rejected at load** (no silent load of an
  incompatible plugin), and a plugin's declared secrets **resolve through `PluginConfig`** at use (no
  out-of-band credential fetch) — closing the documented-but-absent gaps of §3.4.

## Assumptions

- The existing foundation is **kept and consumed, not rebuilt**: the FastAPI sidecar + ~107 data
  routes + provider registry, dockview panels + workspace-blob persistence, the §6.5 safety layer
  (Tier-1 LOCKED), **the Kite read-only OAuth logic — kept but repackaged as the first reference
  broker marketplace plugin, no longer a hardcoded boot-registered adapter (FR-052)**, BYOK keychain,
  and the copilot tool loop + tool-schema contract (`docs/CURRENT_STATE.md` §8).
- **The plugin marketplace is the primary extensibility model.** Brokers, data providers/connectors,
  panels, and agents are all delivered as install/enable/configure/remove marketplace plugins;
  **no broker (or other extension) is hardcoded or bootstrapped at boot** — `bootstrap_default_adapters()`
  is retired as the broker entry path (FR-050/FR-051). The provider-shaped data registry (US8) and
  the plugin contract are **one** extension model, not two parallel ones (FR-053). Safety remains
  **host-enforced** across every plugin: no plugin can opt out of the §6.5 gate (FR-055), and Tier-1
  LOCKED files + §6.5 invariants stay byte-for-byte untouched.
- **Broker order execution is out of scope** for this redesign (read-only broker data only; the
  §6.5 execution machine stays dormant, paper-default, never live-validated). This **reverses a
  prior BLUEPRINT §2 Locked decision** and is **operator-ratified (2026-05-30)** — see Clarifications.
- The **Tradesa plugin is a separate track**, not part of this redesign's scope.
- BYOK is required for live agent answers; a default that depends on an uninstalled local model is
  treated as a defect to fix in onboarding, not an assumption to preserve.
- "Cursor for finance" is an **internal design metaphor only**; external positioning leads with
  "the AI-native, extensible finance workspace."
- Dark-only ships; light theme stays deferred to a later release.
- This window (Window 1) delivers understanding + tooling + this spec; **no implementation**. Plan/
  tasks/implement are a later window after operator review.

## Open Product Decisions *(flagged for operator review — clarify step)*

These are genuine Tier-4 / product-scope decisions the spec does not settle by itself. The
recommendation is given; the operator ratifies.

1. **Broker order-execution scope** `[RESOLVED 2026-05-30 → DEFER]` — The vision defers order execution;
   BLUEPRINT §2 **locked** "global broker execution in v1.0." Reversing a Locked decision is Tier-4.
   _Recommendation:_ defer execution for the redesign; keep read-only broker data + the dormant,
   paper-default §6.5 machine; re-scope execution as a later, separately-ratified track.
2. **Redesign ambition / v1 cut** `[RESOLVED 2026-05-30 → FULL SHELL, PHASED]` — Is the redesign a **full shell rebuild**
   around the agent (chrome, entry points, information hierarchy, four-mode spine, diff gate) with
   the P2/P3 stories (MCP-framework, data hub, durable agents) sequenced after — or a tighter first
   cut? _Recommendation:_ P1 stories (US1–US4) are the redesign MVP; P2 (US5–US7) next; P3 (US8–US9)
   after — one coherent agent-first shell, not a parallel "simple app."
3. **MCP-as-framework depth in this redesign** `[RESOLVED 2026-05-30 → INCLUDE MARKETPLACE]` — Unify
   the catalog + auto-derive the MCP surface from the REST app + add a stdio entrypoint + a
   port-discovery file, **AND** build the filesystem plugin **marketplace/installer/signing**
   loader **in this redesign**. _Operator decision (overrides the original "defer marketplace"
   recommendation):_ pull the marketplace/loader/signing forward — Vysted-as-a-framework is
   first-class in this build. (Adds a plugin-distribution/signing workstream; sequence within P2.)
4. **Default agent / first-run provider** `[RESOLVED 2026-05-30 → OFFER BOTH]` — The shipped copilot defaults to a
   local Ollama model that may be absent (fails on first call). What is the first-run default — (a)
   onboarding requires choosing/entering a BYOK cloud provider, (b) ship a guided local-model setup,
   or (c) both? _Recommendation:_ (a) — first-run onboarding requires a working provider; no silent
   local-model default.
5. **External positioning / tagline** `[RESOLVED 2026-05-30 → CONFIRMED]` — Lead external/public
   positioning with "the AI-native, extensible finance workspace"; "Cursor for finance" stays an
   **internal design metaphor only**. _Operator-ratified — see Clarifications._
6. **DataHub pub/sub + symbol-group panel linking** `[RESOLVED 2026-05-30 → DEFER]` — Keep the
   provider-shaped data registry (US8) in this redesign; sequence the typed pub/sub bus **and**
   symbol-group panel linking as a later track. The visible payoff being deferred is **symbol-group
   panel linking** (change the ticker in one linked panel → all linked panels follow).
   _Operator-ratified — see Clarifications._
