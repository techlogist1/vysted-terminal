# Feature Specification: Agent-Native Finance Workspace (the redesign)

**Feature Branch**: `001-agent-native-redesign`

**Created**: 2026-05-30

**Status**: Draft — Pass A redesign spec + **Pass B agent-native research layer authored & operator-ratified**
(clarify resolved 2026-06-01) + **Pass C R4 experience-layer execution spec authored 2026-06-05**
(US18–US25, FR-112–130, SC-026–039; detail in `docs/redesign/REBUILD_R4_SPEC.md` + the four R4 supporting
docs). Awaiting operator review before the phased build. **No implementation in the spec windows.**

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
cockpit" (FR-032): the _one extension model_ and _populated first-run_ are not in tension because the
first-party features **are** plugins — pre-installed ones.

- **First-party panels, data providers, and agents ship PRE-INSTALLED as built-in plugins.** They are
  delivered through the **same** unified extension model as everything else (FR-050/FR-053) — they are
  not a separate hardcoded path — but they are **bundled and enabled by default** so first run is
  populated out of the box (FR-032). "Built-in" describes _distribution_ (pre-installed, enabled,
  removable like any plugin), not a _privileged registration path_: a first-party plugin loads through
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
  creds. Kite remains the canonical _reference_ broker plugin (FR-052) — available to install, not
  pre-installed.
- **Net effect on acceptance:** FR-032's populated first-run is satisfied by the pre-installed
  first-party plugin set (panels + the keyless data plugin + the default agent); SC-013's "no broker
  registered at boot / installable-and-removable through the marketplace" is unaffected because brokers
  are explicitly excluded from the pre-installed set.

### Session 2026-06-01 (Pass B — operator ratification of the agent-native research layer)

Pass B extends the spec with the **agent-native research layer** — six pillars: (A) locale-native data

- symbol resolution + multi-source fallback, (B) fast + deep research with the B+A output (cockpit +
  cited brief), (C) three-tier web search (native / BYOK / local), (D) JARVIS capability-completeness +
  smart-arrangement + resourcefulness, (E) `/` and `@` commands, (F) multi-portfolio + the `get_portfolio`
  fix. Added: **US11–US17**, **FR-060–FR-111**, **SC-016–SC-025**, the Pass-B entities/assumptions, and
  the **Open Product Decisions — Pass B** list. Grounding: `docs/redesign/PASS_B_RESEARCH.md` (a 42-agent,
  adversarially-verified research pass). The twelve open product decisions were surfaced to the operator
  and **ratified as follows** (every recommendation accepted):

1. **v1 locale scope** → **US + India, both first-class & deep**; GLOBAL best-effort. (FR-060)
2. **India data default** → **keyless jugaad-data / NSE-Bhavcopy pre-installed** (zero-key, T+1 EOD);
   yfinance is the correctness-gated **US** default and last-resort for India (documented `#2612`/`#2055`);
   Angel One SmartAPI / Dhan / Zerodha + EODHD/Twelve Data are optional BYOK upgrades. (FR-064)
3. **`get_portfolio` fix** → **the portfolio panel publishes its active-portfolio holdings to the
   panel-context bus; the agent reads that** — single source of truth = the frontend multi-portfolio
   store; no sidecar SQLite mirror. (FR-110/111)
4. **JARVIS posture v1** → **prompt-driven assembly** ("research X" → cockpit); fully-anticipatory
   pre-loading is a later enhancement. (US15)
5. **Web-search default tier** → **native-on-your-key default** + honest fallback prompt (BYOK/local) for
   the ~4 providers without native search; per-search cost surfaced + a per-run search cap. (FR-081)
6. **Default BYOK search backend** → **Exa**, with Tavily/Linkup as alternates. (FR-083)
7. **Deep-research depth + trigger** → FAST default + explicit **`/deep` & "go deeper"**; budgets
   **rounds=3 (max 5), wall=120s (max 300s)**, abort→synthesize. (FR-072)
8. **BYOK deep backend** → **ship Perplexity Sonar deep-research as an optional, opt-in-per-run DEEP
   engine** (cost shown, never auto-selected). (FR-073)
9. **Research output layout** → ship **single-focus / research-cockpit / compare** templates (macro-scan
   recommended) with the **brief as a real dockview panel**. (FR-074/091)
10. **Slash/@ command set** → ship the **curated 11 slash + 9 @** set; `@analyst`/`@quant` as
    **prompt-prefix routing** to existing personas; custom `.vysted/commands/` deferred to v2. (FR-100/101)
11. **Local Tier-3 search** → **BYO SearXNG URL + autodetect `localhost:8080`** in v1; bundled Docker
    one-click deferred. (FR-084)
12. **Constitution amendment** → **ratified**: add **Principle VIII — Locale-Native & Correct, Everywhere**
    (the "McDonald's principle" + correctness-non-negotiable + resourcefulness/never-dead-end); constitution
    **1.0.0 → 1.1.0**.

Every Pass-B pillar preserves the §6.5 boundary, Tier-1 LOCKED files, read-only brokers, paper-default,
kill-switch, append-only audit, and the diff/accept gate **byte-for-byte** (FR-012/055/094); no LOCKED
file is touched.

### Session 2026-06-05 (Pass C — R4 experience-layer execution spec authored)

Pass C is the **executable experience-layer rebuild spec** — authored in a dedicated spec window from a
20-agent codebase + live-research recon, to be run by a separate build window. It **extends** (does not
reopen) Pass A/B and the Constitution; the full treatment + four supporting docs (design language,
stale-code register, failure-mode matrix, build sequence) live under `docs/redesign/`. It adds **US18–US25,
FR-112–130, SC-026–039** (appended below — see "Pass C — R4 Experience-Layer Execution"). Highlights:

- **Agent-as-OS spine** (the ranked-#1 pillar): three coherent speeds — FAST (bare `@TICKER` → instant
  LLM-free cockpit), ORCHESTRATED (propose a panel set + ask-when-unsure, via the §6.5 bar), DEEP (one
  research path); continuous situational awareness + re-read-after-mutation; host-action completeness
  (screener-filter write, drawings, save-workspace) — all registered in the catalog, all §6.5-gated.
- **Coherence audit:** collapse the 5 research paths + 3 triggers into ONE model; model-swap preserves
  context on every path; Enter sends everywhere; one mode system; no hardcoded-should-be-dynamic; fix
  TS↔Python brief contract drift.
- **Original design language** ("Cold Instrument" — OKLCH zinc + one rationed cool-indigo, no neon/glow),
  applied via the historical token names (zero-churn); **market-session awareness** (0% today) + shared
  state primitives so every surface renders empty/loading/error/market-closed/symbol-not-found/stale.
- **Feature builds** (R3 orphans rebuilt fresh, deps installed): ⌘K Raycast-grade palette (cmdk), Tiptap
  notes (markdown canonical blob, atomic write), screener formula-grammar (mathjs-in-Worker — **never
  expr-eval**, CVE-2025-12735), research-presentation deepening + company-overview AI narrative
  (numbers-from-structured-only + numeric-verification pass), client-side shareable briefs (md/PNG/PDF).
- **Screener performance:** full S&P 500 in single-digit seconds cold / sub-second warm via the Yahoo v7
  batch quote endpoint + async + caching + warm precompute, with a **visible skip ledger** (no silent
  drops). **Four bugs** fixed/confirmed with rendered-pixel / trusted-event / native proof.

Pass C preserves the §6.5 boundary, Tier-1 LOCKED files, read-only brokers, paper-default, kill-switch,
append-only audit, and the diff/accept gate **byte-for-byte** (FR-012/039/127/SC-039); no LOCKED file is
touched; no version bump; branch only. **No Constitution amendment** — Pass C is entirely an application
of Principles I–VIII (no new principle), so the constitution stays **1.1.0**.

---

## User Scenarios & Testing _(mandatory)_

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
order; verification is the product. Copying Cursor's diff/accept _correctly_ (and
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
ships in **P1 on the _existing_ shell** — today's dockview cockpit and chrome — so the agent-first
experience is usable _before_ any reskin. This story (US6) — the minimal-dark visual rebuild, the
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

---

### User Story 11 — Locale-native data, everywhere (the "McDonald's principle") (Priority: P1 — Pass B)

A user in India says "set me up to look at Tata Steel" (or "GOLDBEES") and the terminal serves
**correct NSE/BSE data, in INR, on IST market hours, with Indian news sources** — the same product,
locally shaped. A user in the US gets US tickers, USD, US market hours, US sources. There are **no
symbol dead-ends**: a free-text name or ticker resolves to the right instrument wherever it lists,
the data comes from a locale-appropriate source, and if the first source fails the system **falls
through to another** — saying "unavailable" (with a reason) only when every configured source has
failed. The terminal **never shows wrong, stale, or glitchy data** behind a populated surface.

**Why this priority**: Correctness is non-negotiable for a research product — wrong data is fatal —
and locale-native coverage is what lets the product be "Perplexity Finance, but better" for a user
_anywhere_, not a US-first tool with an India bolt-on. It is the foundation the research engine and
JARVIS rest on (a brief built on wrong data is worse than no brief). The motivating defect (GOLDBEES
dead-ended; yfinance is documented-unreliable for Indian tickers — `PASS_B_RESEARCH.md` §A.1) is a
correctness bug, not a polish item.

**Independent Test**: With region=IN, a basket including GOLDBEES, TATASTEEL, RELIANCE, NIFTYBEES
resolves and loads correct quotes/history from a locale-appropriate source (or returns an honest,
human "unavailable + why"); with region=US, AAPL/MSFT/SPY load from US sources; in both, every
served value carries its provider as provenance and no value is fabricated or stale-shown-as-live.
Fully testable as a scripted symbol basket → resolved instrument + provenance-tagged data (or honest
unavailable), with zero raw-JSON dead-ends.

**Acceptance Scenarios**:

1. **Given** region=IN, **When** the user asks for an Indian instrument by name or ticker (incl. an
   ETF like GOLDBEES), **Then** it resolves to the correct NSE/BSE instrument and loads correct data
   from a locale-appropriate source, denominated/formatted for IN (INR, IST, en-IN), with provenance.
2. **Given** a data source fails or returns an empty/invalid response, **When** the system fetches,
   **Then** it falls through the preference-ordered provider chain and serves the first valid result
   (provenance-tagged) — or, only if all sources fail, a human "unavailable" message naming what would
   unlock it (a key, a source), never raw JSON and never wrong data.
3. **Given** a new data source declared as a plugin (exchanges, data types, region it serves),
   **When** installed/enabled/configured via the marketplace, **Then** the registry resolves through
   it by standard model key + preference order with zero per-source UI code (FR-034/035/053).
4. **Given** a value would be stale (after-hours, cache-served) or synthetic/paper, **When** it is
   shown, **Then** it is labeled as such (staleness/provenance badge), never presented as live/real.

---

### User Story 12 — Fast research builds the cockpit and writes the brief (B+A) (Priority: P1 — Pass B)

The user says "research NVDA." Without twenty questions, JARVIS resolves the symbol, pulls
**structured data** (price, fundamentals, recent filings, news) from the providers in parallel, runs
**one light web-search round** for context, **arranges a coherent cockpit** (chart center with
sensible default indicators, fundamentals beside it, news/filings below), and drops a **synthesized
written brief** — a Perplexity-style answer with inline `[n]` citations and a sources tray — as a
panel inside the cockpit. Quick (target seconds, not minutes). The edge over Perplexity Finance: it
combines the _actual_ structured filings/financials (with provenance) with web context, in a terminal
that builds itself.

**Why this priority**: This is the flagship JARVIS experience and the product's reason to beat
Perplexity Finance — the agent doesn't just answer, it builds the research workspace. Fast research
on by default is the "research this" path most users use most.

**Independent Test**: "research <ticker>" composes a multi-panel cockpit (chart + default indicators,
fundamentals, news/filings) and a brief panel with ≥K cited sources, every structured number
provenance-tagged, in under the fast-research latency target — testable as a scripted research call →
resulting workspace state + brief + citations. Not everything dumped in one tile.

**Acceptance Scenarios**:

1. **Given** a configured provider + (where needed) a search backend, **When** the user asks to
   research a company, **Then** JARVIS arranges the research-cockpit layout (not one tile), loads the
   chart with sensible default indicators for the asset class, and pulls fundamentals + news + filings
   — each value provenance-tagged.
2. **Given** the structured + web data is gathered, **When** JARVIS synthesizes, **Then** it writes a
   brief panel with inline `[n]` citations and a sources tray (favicon/title/domain/snippet), labeled
   with mode (FAST), source count, and cost.
3. **Given** the cockpit + brief are built, **When** the user manipulates a panel by hand or asks a
   follow-up, **Then** the agent modifies the existing cockpit (does not start over) and the change
   rides the diff/accept gate (US4) / autonomy mode.
4. **Given** a data source fails mid-research, **When** JARVIS continues, **Then** it falls through to
   another source (Pillar A) and the brief notes any gap honestly — it does not fabricate or dead-end.

---

### User Story 13 — Deep research (go deeper), budget-bounded (Priority: P2 — Pass B)

When fast isn't enough, the user invokes deep research ("go deeper" on a brief, or `/deep`). JARVIS
runs a multi-round search→read→reflect→search-again loop across many sources until coverage is
satisfied or a **hard budget** (rounds / wall-clock / tokens / spend) is hit — at which point it
synthesizes immediately from what it has (never times out into nothing). Optionally, a user with a
deep-research API key (e.g. Perplexity Sonar) can route deep mode through that backend, explicitly and
with cost shown. The output is the same B+A shape: a richer cockpit + a longer cited brief, with a
visible step log.

**Why this priority**: Deep research is the thorough, opt-in counterpart to fast — it depends on fast
existing first, and (like Delegate, US9) autonomous multi-round spend is a safety surface that must be
bounded. P2 because it builds on US12.

**Independent Test**: A deep-research run loops across multiple sources and either satisfies a coverage
floor (≥1 source each for price/fundamentals/news/web) or aborts at its budget ceiling — and in both
cases produces a synthesized brief (never a bare timeout); the step log and cost-so-far are visible;
the BYOK deep backend, if configured, is opt-in per run.

**Acceptance Scenarios**:

1. **Given** deep mode, **When** the loop runs, **Then** it is bounded by a hard ceiling
   (rounds/wall/tokens/spend, wired to the BudgetGuard, FR-026), and the first breach forces immediate
   synthesis from gathered context with a stated reason — not an error, not a silent overrun.
2. **Given** a configured deep-research backend key, **When** the user opts into the paid path for a
   run, **Then** the estimated cost is shown first, the path is explicit (never auto-selected), and
   citations carry provenance ("via <backend>").
3. **Given** a deep run, **When** it proceeds, **Then** the agents rail / brief shows live step log,
   sources-so-far, and cost-so-far.

---

### User Story 14 — Web search, three tiers of freedom (Priority: P1 — Pass B)

The user is never forced into a subscription to get web grounding. **Native (default):** if their
model supports server-side web search on their existing key (Anthropic/OpenAI/Gemini/Groq/xAI), JARVIS
rides it. **BYOK search API (optional power):** they can add an Exa/Tavily/etc. key for better
retrieval. **Local (optional, total privacy):** they can point at a local SearXNG so nothing leaves
the machine. Each backend is a marketplace plugin; the user picks their tier. When the active model
has no native search (DeepSeek, local Ollama, bare Qwen/Llama), JARVIS says so honestly and routes to
a configured BYOK/local backend rather than failing or silently degrading.

**Why this priority**: Web search underpins both research tiers and the "fast research" default. The
freedom thesis (ride your own key; don't force subscriptions) is core to the BYOK/local-first
identity. P1 because research can't ground without it.

**Independent Test**: With each supported provider, JARVIS performs a grounded search using only the
user's existing key where native search exists (citations returned), and gracefully routes to a
configured BYOK/local backend (with an honest prompt) where it doesn't; each search backend
installs/configures as a marketplace plugin exposing a common search interface; locale-aware domain
preferences apply.

**Acceptance Scenarios**:

1. **Given** an active model with native search, **When** JARVIS needs web context, **Then** it uses
   the provider's native search on the user's key, returns normalized citations, and respects a
   per-run search cap (cost-aware).
2. **Given** an active model with no native search, **When** JARVIS needs web context, **Then** it
   surfaces an honest prompt and uses the configured BYOK or local search backend — never failing
   silently or fabricating.
3. **Given** a configured search plugin, **When** it runs, **Then** locale-aware domain preferences
   apply (US vs IN source sets) and results carry source URLs.
4. **Given** a local (SearXNG) backend, **When** selected, **Then** web search runs without data
   leaving the machine.

---

### User Story 15 — JARVIS does every obvious action, with taste, and never dead-ends (Priority: P1 — Pass B)

The agent can do every obvious thing a user would expect of a finance copilot — open/close/focus/
arrange panels (with smart layout judgment), apply/remove chart indicators, load any symbol
(locale-aware, resourceful), set timeframes, pull fundamentals/filings/news, compare tickers, run
fast/deep research, and manage portfolios — all by name. When asked to "set up" or "research"
something it makes good layout + indicator + data choices on its own (a thoughtful cockpit, not
everything in one tile, not asking the user how to arrange). When a path fails it tries another route
and succeeds, or fails cleanly with a human message — it **never gives up and prints raw JSON**. Every
mutating action routes through the diff/accept gate; AUTO mode skips per-action confirm for
UI/layout/chart/watchlist only — never an order; §6.5 is never bypassed.

**Why this priority**: This is the north-star JARVIS feeling, and it is all-or-nothing: a single
missing obvious action, a bad arrangement, or one raw-JSON dead-end breaks the illusion of an
effortless, anticipatory assistant. The three sub-pillars — capability completeness, smart-defaults
judgment, resourcefulness — are each first-class.

**Independent Test**: A capability-completeness audit shows every enumerated obvious action is
reachable by the agent and by hand; a "research X"/"set up Y" request produces a coherent
named-template cockpit with sensible default indicators (not one tile); a deliberately-hard symbol
(GOLDBEES) is handled by fallthrough or an honest message (zero raw-JSON dead-ends); every mutating
action is gated (orders never auto-applied; §6.5 audit clean).

**Acceptance Scenarios**:

1. **Given** any obvious finance action (arrange/close/focus panels, set/remove indicators, load
   symbol, set timeframe, pull fundamentals/filings/news, compare, research, portfolio), **When** the
   user asks for it in natural language, **Then** the agent performs it via a catalog capability —
   none is agent-unreachable or hand-unreachable.
2. **Given** "research X" / "set me up to look at Y", **When** the agent composes the cockpit,
   **Then** it picks a sensible named layout template and default indicators for the asset class on
   its own (a thoughtful arrangement), without asking the user how to arrange.
3. **Given** a load/research path fails, **When** the agent recovers, **Then** it tries another
   source/route and succeeds, or returns a human message naming the cause — never raw JSON, never
   wrong data.
4. **Given** any agent mutation, **When** proposed, **Then** it routes through the diff/accept gate;
   AUTO auto-applies only UI/layout/chart/watchlist; an order never auto-applies in any mode and always
   routes through §6.5 confirm-before-place (FR-010/011/012).

---

### User Story 16 — `/` and `@` commands in the agent panel (Priority: P2 — Pass B)

Inside the agent panel the user has a clean, fast command surface: **slash-commands** (`/research`,
`/deep`, `/compare`, `/chart`, `/screener`, `/watch`, `/portfolio`, `/layout`, `/export`, `/sources`,
`/clear`) for structured actions, and **`@`-mentions** (`@TICKER`, `@INDEX`, `@chart`, `@news`,
`@filings`, `@watchlist`, `@portfolio`, `@analyst`, `@quant`) to reference instruments, surfaces,
scopes, and sub-specialists — orthogonally composable (`/compare @AAPL @MSFT`). Inline fuzzy
autocomplete, locale-aware ticker resolution, keyboard-driven.

**Why this priority**: This makes agent interaction powerful and fast for the hands-on user (the
OpenCode/Cursor grammar reborn for finance), but it is a UX layer on top of the capability surface
(US15) and the research engine — so P2.

**Independent Test**: Typing `/` shows the slash picker (fuzzy, keyboard-nav, mnemonic shown); each
command executes its action; typing `@` shows the mention picker (instruments resolve locale-aware,
showing `[exchange: price chg%]`); a mention injects the correct context; `/cmd @entity` composes.

**Acceptance Scenarios**:

1. **Given** the agent composer, **When** the user types `/`, **Then** a fuzzy, keyboard-navigable
   slash picker appears and the selected command runs its action (e.g. `/research` opens the research
   flow).
2. **Given** the composer, **When** the user types `@`, **Then** a mention picker appears; `@TICKER`
   resolves locale-aware (NSE for an IN session) and injects that instrument's context; `@panel`/
   `@scope` injects the right surface/scope.
3. **Given** a composed `/compare @A @B`, **When** submitted, **Then** intent (compare) and scope
   (A, B) resolve together.

---

### User Story 17 — Multi-portfolio truth: the agent reads the real portfolio (Priority: P1 — Pass B)

The user manages multiple named portfolios in the UI (create/rename/switch/delete, manual holdings —
shipped in Pass A.2.0). When they ask JARVIS "how's my portfolio doing," the agent answers from the
**same portfolio the UI shows** — the active multi-portfolio store — never from a stale or divergent
source. Switching the active portfolio changes what the agent reads.

**Why this priority**: Correctness (Pillar A's mandate applied to the user's own data). The agent
answering from a stale/wrong portfolio is a trust-breaking correctness bug — small surface, critical
impact. P1.

**Independent Test**: With ≥2 portfolios, the agent's `get_portfolio` (and any portfolio-aware answer)
returns exactly the active portfolio's holdings/P&L as shown in the UI; creating/switching/editing a
portfolio in the UI changes the agent's read with zero divergence.

**Acceptance Scenarios**:

1. **Given** a multi-portfolio store with an active portfolio, **When** the agent reads the portfolio,
   **Then** it returns the active portfolio's real holdings (symbol/quantity/cost/asset-class) + P&L
   as shown in the UI — not a divergent or empty source.
2. **Given** the user switches the active portfolio, **When** the agent next reads, **Then** it
   reflects the newly-active portfolio.
3. **Given** a manual edit to holdings in the UI, **When** the agent reads, **Then** the change is
   reflected (single source of truth).

---

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

**Pass B edge cases:**

- **Symbol resolves to multiple instruments across exchanges** (e.g. "Reliance" → RELIANCE.NS vs
  .BO vs a US ADR). Resolution ranks by user locale; below a confidence threshold the agent surfaces
  a disambiguation choice rather than silently acting on the wrong instrument.
- **Active model has no native web search** (DeepSeek / local Ollama / bare Qwen/Llama). The agent
  routes to a configured BYOK/local search backend with an honest prompt; it never fabricates web
  context or fails silently.
- **All data sources fail for a symbol.** Honest "unavailable" with the reason and what would unlock
  it (a key/source) — never raw JSON, never a fabricated value (the GOLDBEES-class defect).
- **Deep-research budget exhausted mid-loop.** Synthesize immediately from gathered context with a
  stated reason (abort→synthesize), never a bare timeout/error.
- **After-hours / stale / paper data.** Labeled as stale/synthetic (badge), never shown as live/real.
- **Native search per-search billing.** A per-run search cap prevents runaway cost during multi-round
  research; cost-so-far is legible.
- **Indian ticker via yfinance returns "possibly delisted" / silently-wrong OHLC** (documented
  `#2612`/`#2055`). The correctness gate rejects it and the registry falls through to a locale-
  appropriate source; yfinance is never the trusted India primary.

## Requirements _(mandatory)_

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
  not merely surfaced as mnemonics. (FR-031 _teaches_ shortcuts; FR-039 lets the user _rebind_ them,
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

### Functional Requirements — Locale-native data, resolution & fallback (Pass B / Pillar A)

- **FR-060**: Region MUST drive the user-local shape of the product — ticker/exchange resolution,
  currency, market hours, number/date formatting, and default news/data sources — so the terminal is
  natively local wherever the user is. This extends the Pass-A region seam (`region.ts` / `settings` /
  `format.ts`) into the sidecar (a `get_region()` read threaded through the provider registry, news,
  screener, and macro handlers). The v1 locale set is **US + India (both first-class & deep); GLOBAL
  best-effort** `[RESOLVED 2026-06-01]`.
- **FR-061**: The system MUST resolve a free-text name or ticker to a concrete instrument (ticker,
  exchange, region, asset class) via a **keyless-first resolver** (bundled US + NSE/BSE instrument
  masters + a live keyless lookup), locale-ranked, with disambiguation surfaced when confidence is low
  ("Tata Steel" → TATASTEEL on NSE for an IN session; "GOLDBEES" → the NSE gold ETF).
- **FR-062**: Data retrieval MUST be fault-tolerant and **never dead-end**: the registry resolves by
  standard model key + preference order (FR-035) and MUST fall through to the next provider on a
  missing-key / empty / invalid response, serving the first valid, provenance-tagged result — and MUST
  surface an honest, human "unavailable" (naming what would unlock it) ONLY when all configured sources
  fail. Raw JSON dumped at the user is a defect.
- **FR-063**: The system MUST NOT present wrong, stale, or glitchy data as correct. A **correctness
  gate** MUST reject a provider response (advancing to the next) on empty/null data, non-positive price,
  exchange-calendar-aware staleness, a returned-symbol mismatch, or missing required fields; anomalous
  values surface a data-quality warning rather than silent display; stale/cache-served and
  synthetic/paper values are labeled (FR-041). **yfinance MUST NOT be trusted for `.NS`/`.BO` tickers
  without this gate** (documented `#2612`/`#2055`).
- **FR-064**: Each data source MUST be a marketplace plugin (FR-050/053) declaring the exchanges, data
  types, and region(s) it serves, configured/keyed via the credentials hub (FR-034). The keyless India
  equity default ships pre-installed as the **keyless jugaad-data / NSE-Bhavcopy default** (zero-key,
  T+1 EOD); Angel One/Dhan/Zerodha + EODHD/Twelve Data are optional BYOK upgrades `[RESOLVED 2026-06-01]`;
  yfinance remains the keyless US default; brokers stay none-pre-installed and read-only (FR-051).
- **FR-065**: Every served value MUST carry provenance (the provider that served it), and locale-shaped
  output (currency, market-hours-aware freshness, locale formatting) MUST be correct for the active
  region — e.g. an NSE quote denominated in INR with IST session context, never an ET-anchored VWAP
  applied to NSE data.

### Functional Requirements — Research engine: fast + deep + B+A output (Pass B / Pillar B)

- **FR-070**: The system MUST provide a **fast research** path (default-on) that, from a single
  instruction ("research X" / "set up Y"), resolves the symbol, pulls structured data (price,
  fundamentals, filings, news) from providers in parallel, runs one light web-search round, synthesizes,
  and produces the B+A output (FR-074) — targeting an interactive latency of **≤15s typical**
  `[RESOLVED 2026-06-01]`.
- **FR-071**: The system MUST provide an opt-in **deep research** path ("go deeper" / `/deep`) that runs
  a multi-round search→read→reflect→search-again loop until a coverage floor (≥1 source each for
  price/fundamentals/news/web context) is met or a hard budget is hit.
- **FR-072**: Deep research MUST be bounded by a hard, user-visible ceiling on rounds, wall-clock,
  tokens, and spend, wired to the existing BudgetGuard (FR-026); the first breach MUST force **immediate
  synthesis from gathered context** with a stated reason (abort→synthesize) — never a silent overrun,
  never a bare timeout. Defaults: **rounds=3 (max 5), wall=120s (max 300s)**; trigger is **explicit
  `/deep` + "go deeper"** (not auto-detect) `[RESOLVED 2026-06-01]`.
- **FR-073**: The system MAY support a **BYOK deep-research backend** (e.g. Perplexity Sonar) as an
  explicit, opt-in-per-run DEEP path with estimated cost shown before starting; it MUST NEVER be
  auto-selected, and its citations MUST carry provenance ("via <backend>"). **Perplexity Sonar ships as
  an optional, opt-in-per-run DEEP engine** `[RESOLVED 2026-06-01]`.
- **FR-074**: Research output MUST be **B+A**: it BUILDS the workspace (arranges a coherent
  named-template cockpit, FR-090/091) AND drops a **synthesized written brief panel** — markdown with
  inline `[n]` citations, a sources tray (title/domain/snippet), and a metadata header (mode FAST|DEEP,
  source count, cost) — inside it; the brief is a **real dockview panel** `[RESOLVED 2026-06-01]`.
  Structured numbers in the brief MUST be provenance-tagged; web claims MUST be cited
  (FR-040).
- **FR-075**: Each research run MUST be **step-logged** (plan/tool/search/compress/reflect/synthesize
  records with latency + status), and the step log + cost-so-far MUST be inspectable.

### Functional Requirements — Web search, three tiers of freedom (Pass B / Pillar C)

- **FR-080**: The system MUST support web search across **three user-selectable tiers**, each a
  marketplace search-source plugin conforming to a common search interface: (1) **native** — the active
  model's server-side web search on the user's existing key; (2) **BYOK search API**; (3)
  **local/private**. The user picks their tier; no tier requires a subscription beyond the user's own
  keys.
- **FR-081**: The native tier MUST be the default where the active model supports server-side web search
  (Anthropic/OpenAI/Gemini/Groq/xAI), riding the user's existing key and returning normalized citations;
  a **per-run search cap** MUST bound per-search billing during multi-round research. The default is
  **native-on-your-key + honest fallback** `[RESOLVED 2026-06-01]`.
- **FR-082**: Where the active model has **no native web search** (DeepSeek, local Ollama, bare
  Qwen/Llama), the system MUST surface an honest prompt and route to a configured BYOK or local backend
  — it MUST NOT fail silently or fabricate web context.
- **FR-083**: The BYOK search tier MUST ship at least one best-in-class finance-suitable backend —
  **Exa** (default), with Tavily/Linkup as alternates `[RESOLVED 2026-06-01]`; backends MUST
  support locale-aware domain preferences (US vs IN source sets).
- **FR-084**: The local tier MUST allow web search with **no data leaving the machine** (SearXNG-class),
  via auto-detect + a configurable local URL: **BYO SearXNG URL + autodetect `localhost:8080`** in v1
  (bundled Docker one-click deferred) `[RESOLVED 2026-06-01]`.

### Functional Requirements — JARVIS completeness, smart arrangement & resourcefulness (Pass B / Pillar D)

- **FR-090**: The agent capability catalog MUST be **complete** for every obvious finance action so none
  is agent-unreachable: open/close/focus/arrange panels, apply/remove chart indicators, load any symbol
  (locale-aware), set timeframe, pull fundamentals/filings/news, compare instruments, run fast/deep
  research, and read/manage portfolios. Every such capability MUST also be reachable by hand (FR-005).
  New capabilities register once in the catalog and project to the internal copilot + external MCP by
  the same name (FR-020).
- **FR-091**: The agent MUST arrange the cockpit with **built-in taste**: `arrange_layout` MUST offer
  **named templates** (at least single-focus, research-cockpit, compare; macro-scan recommended) and the
  agent MUST pick a sensible template + default indicators for the asset class **on its own** when asked
  to "research"/"set up" — composing a thoughtful cockpit, not dumping everything in one tile, and not
  asking the user how to arrange.
- **FR-092**: The system MUST apply **sensible default indicators per asset class** (equity daily:
  SMA50/200 + volume + RSI14; intraday: EMA9/21 + session-VWAP locale-anchored; ETF/index: + RS-line;
  crypto: EMA50/200 + week-VWAP + RSI, with OI/funding when a derivatives feed is available), centered
  and legible — via a `set_chart_indicators` host-action through the existing chart-command channel;
  indicators stay server-computed (canvas reads `chart-theme.ts`, never CSS vars).
- **FR-093**: The agent MUST be **resourceful and never dead-end**: on a failed path it MUST try an
  alternate source/route (Pillar A fallback) and succeed, or fail cleanly with a human message — it MUST
  NOT give up and print raw JSON or show wrong data (the GOLDBEES-class defect).
- **FR-094**: Every agent-mutating capability added by Pass B (arrange / indicators / research-driven
  panel changes / etc.) MUST route through the existing **diff/accept gate** (FR-010); AUTO autonomy MAY
  skip per-action confirm for **UI/layout/chart/watchlist ONLY** and MUST NEVER auto-apply an order; the
  §6.5 boundary MUST NEVER be bypassed in any mode; brokers stay read-only; Tier-1 LOCKED files stay
  byte-for-byte untouched (FR-012/055).

### Functional Requirements — `/` and `@` command surface (Pass B / Pillar E)

- **FR-100**: The agent panel MUST provide a **slash-command surface** (inline fuzzy autocomplete,
  keyboard-driven) covering at least: `/research`, `/deep`, `/compare`, `/chart`, `/screener`, `/watch`,
  `/portfolio`, `/layout`, `/export`, `/sources`, `/clear` — the **curated set ships in v1**; custom
  `.vysted/commands/` deferred to v2 `[RESOLVED 2026-06-01]`.
- **FR-101**: The agent panel MUST provide an **@-mention surface** (inline fuzzy picker) covering
  instruments (`@TICKER`/`@INDEX`, locale-aware resolution showing `[exchange: price chg%]`), surfaces
  (`@chart`/`@news`/`@filings`/`@terminal`), scopes (`@watchlist`/`@portfolio`), and sub-specialist
  routing (`@analyst`/`@quant`, implemented as **prompt-prefix routing to existing personas** in v1)
  `[RESOLVED 2026-06-01]`.
- **FR-102**: Slash intent and @ scope MUST be **orthogonally composable** (`/compare @AAPL @MSFT`); a
  ticker MUST NOT be a slash command; the surfaces MUST not conflict with the §6.5 gate (a `/research` or
  any command that triggers a mutation still routes through the diff/accept gate).

### Functional Requirements — Multi-portfolio truth (Pass B / Pillar F)

- **FR-110**: The agent's portfolio read (the `get_portfolio` capability and any portfolio-aware answer)
  MUST return the **active portfolio from the real multi-portfolio store the UI shows**
  (`src/store/portfolios.ts` via the workspace blob) — never a stale or divergent source. **Fix: the
  portfolio panel publishes active-portfolio holdings to the panel-context bus, which the agent reads**
  (single source of truth = the frontend store) `[RESOLVED 2026-06-01]`.
- **FR-111**: Switching/creating/editing the active portfolio in the UI MUST change what the agent reads
  (single source of truth), with zero divergence; synthetic/paper values stay labeled (FR-041).

### Key Entities _(data/contracts involved — conceptual, not implementation)_

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

**Pass B entities:**

- **Region / Locale Profile** — the active region (US / IN / …) driving ticker/exchange resolution,
  currency, market hours, formatting, and default news/data sources; read frontend (`region.ts` /
  `settings`) + sidecar (`get_region`).
- **Symbol Resolution** — a free-text/ticker query resolved to `(ticker, exchange, region, asset_class)`
  with a confidence + disambiguation candidates; cached; locale-ranked.
- **Data Source Plugin** — a provider declaring the exchanges, data types, and region(s) it serves + its
  credential shape; registered in the provider registry; carries provenance on results; the data slice of
  the one extension model (FR-053/064).
- **Research Run / Brief** — a fast or deep research invocation with a mode (FAST/DEEP), a step log,
  gathered sources, a budget (deep), and a synthesized cited brief (the B+A output panel).
- **Search Backend** — a marketplace search-source plugin (native / BYOK / local) implementing a common
  `search(query, options) → {results, citations}` interface, with locale-aware domain preferences.
- **Layout Template** — a named cockpit arrangement (single-focus / research-cockpit / compare /
  macro-scan) the agent picks by query intent; the taste behind `arrange_layout`.
- **Slash Command / Mention** — the agent-panel command grammar: `/commands` (intent) + `@mentions`
  (scope), orthogonally composable.

## Success Criteria _(mandatory)_

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

**Pass B — JARVIS-AGI experience & pillar criteria:**

- **SC-016** _(coherent cockpit, unprompted)_: "research X" composes a coherent multi-panel cockpit on
  its own — a **named layout template (not one tile)** with the chart carrying asset-class default
  indicators, fundamentals + news/filings panels, and a brief panel with **≥3 cited sources** — for a
  representative ticker basket, 100% of the time.
- **SC-017** _(no symbol dead-ends across locales)_: a US + India basket (incl. GOLDBEES, TATASTEEL,
  NIFTYBEES, RELIANCE) each resolves and loads from a locale-appropriate source **OR** returns an honest
  human "unavailable + why" — **0 raw-JSON dead-ends, 0 wrong/stale values shown as live** (audit).
- **SC-018** _(fast research latency)_: fast research completes within the latency target (recommend
  **≤15s typical**) for a representative ticker — structured pull + web round + synthesis + arrangement
  included.
- **SC-019** _(data is never wrong)_: for the test basket, **100% of served values carry provenance**,
  stale/synthetic values are labeled, and the correctness gate + fallback chain admit **0 fabricated
  values** (audit).
- **SC-020** _(native search coverage + honest fallback)_: native web search works on the
  native-capable providers (Anthropic/OpenAI/Gemini/Groq/xAI) using **only the user's existing key**
  (citations returned); the rest (DeepSeek/Ollama/bare Qwen/Llama) route to a configured BYOK/local
  backend with an honest prompt — **0 silent failures, 0 fabricated web context**.
- **SC-021** _(deep research is bounded)_: a deep-research run satisfies the coverage floor **or** aborts
  at its rounds/wall/token/spend ceiling, and in **both** cases produces a synthesized brief (never a
  bare timeout) — 100% of the time; cost-so-far + step log visible.
- **SC-022** _(capability completeness)_: an audit shows **every** enumerated obvious action
  (arrange/close/focus, set/remove indicators, load symbol locale-aware, set timeframe,
  fundamentals/filings/news, compare, fast/deep research, portfolio) is reachable by the internal agent
  **and** by hand — **0 obvious actions missing**.
- **SC-023** _(/@ surface resolves)_: every shipped slash command executes its action; `@TICKER` resolves
  locale-aware to the correct instrument; `@panel`/`@scope` inject the correct context; `/cmd @entity`
  composes.
- **SC-024** _(portfolio truth)_: for ≥2 portfolios, the agent's portfolio read **equals** the active
  portfolio shown in the UI across create/switch/edit, with **0 divergence**.
- **SC-025** _(Pass-B mutations stay gated; §6.5 untouched)_: every Pass-B agent mutation
  (arrange/indicators/research-driven panel changes) is gated 100% (diff/accept; AUTO only for
  UI/layout/chart/watchlist; orders never auto-applied); the §6.5 audit stays **9/9**; Tier-1 LOCKED
  files are byte-for-byte untouched (audit-grep).

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

**Pass B assumptions:**

- Pass B builds on the **four Pass-A seams** (capability catalog, provider registry, model registry,
  region) + the **Pass A.2.0 multi-portfolio store** + the **JARVIS host-actions/autonomy** + the warm
  theme — these are kept and consumed, **not rebuilt or re-derived** (`EXTENSION_SEAMS.md`,
  `PASS_A_REPORT.md`, `PASS_A20_REPORT.md`, `PASS_B_RESEARCH.md`).
- **yfinance is documented-unreliable for Indian tickers** (`#2612` "possibly delisted" + `#2055`
  silent wrong OHLC, both won't-fix); it stays the US keyless default but is gated/last-resort for
  India. Keyless India data (jugaad-data / NSE-Bhavcopy-class) ships pre-installed; broker (Angel
  One/Dhan/Zerodha) + EODHD/Twelve Data are BYOK upgrades. _(See clarify.)_
- **Native LLM web search is "billable to the user's key"** (per-search fees), not free; only ~5 of the
  supported providers offer it; the BYOK + local tiers exist for the rest.
- **Locale scope for v1 is US + India deep** _(pending clarify)_; GLOBAL is best-effort.
- The **§6.5 boundary, Tier-1 LOCKED files, read-only brokers, paper-default, kill-switch, append-only
  audit, and the diff/accept gate are untouched** by every Pass-B pillar; any pillar that appears to
  require touching a LOCKED file is a **stop-and-surface**, routed around (FR-012/055/094).

## Open Product Decisions _(flagged for operator review — clarify step)_

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

### Open Product Decisions — Pass B _(flagged for operator review — clarify step; recommendations grounded in `PASS_B_RESEARCH.md`)_

> **✅ All twelve resolved 2026-06-01 (operator ratification) — every recommendation was ratified. See
> Clarifications → Session 2026-06-01 for the canonical record.** The list below is retained as the
> rationale trail; the corresponding `[NEEDS CLARIFICATION]` markers in FR-060–FR-111 are now
> `[RESOLVED 2026-06-01]`.

These were the genuine Tier-4 / product-scope forks Pass B did not settle by itself. The
recommendation is given; the operator ratified each at clarify.

1. **v1 locale scope** (FR-060) — _Recommend:_ **US + India both first-class & deep** (Perplexity Finance
   already covers India; the only way to beat it there is going deeper). GLOBAL best-effort. Alt: US-first,
   India v2.
2. **India data default** (FR-064) — _Recommend:_ **keyless jugaad-data / NSE-Bhavcopy pre-installed** (zero
   key, T+1 EOD) + yfinance gated/last-resort; Angel One SmartAPI / Dhan / Zerodha + EODHD/Twelve Data as
   BYOK upgrades. Alt: require a BYOK broker/EODHD key for India.
3. **`get_portfolio` fix approach** (FR-110) — _Recommend:_ the **portfolio panel publishes active-portfolio
   holdings to the panel-context bus**, which the agent reads (single source of truth = the frontend store).
   Alt: mirror to sidecar SQLite, or add a `/agent/portfolio` route.
4. **Web-search default tier** (FR-081) — _Recommend:_ **native-on-your-key default** + honest fallback
   prompt (BYOK/local) for the ~4 providers without native search; surface per-search cost. Alt: require a
   BYOK search key for everyone / local-first default.
5. **BYOK search default pick** (FR-083) — _Recommend:_ **Exa** (best-in-class for finance; $10 free credits)
   with Tavily/Linkup as alternates. (Bing dead; Brave free tier gutted.)
6. **Local Tier-3 search** (FR-084) — _Recommend:_ **BYO SearXNG URL + autodetect `localhost:8080`** in v1;
   defer a bundled Docker one-click. Alt: ship the Docker Compose one-click now / defer Tier 3.
7. **Deep-research depth + trigger** (FR-072) — _Recommend:_ FAST default + explicit **`/deep` & "go deeper"**;
   budgets **rounds=3 (max 5), wall=120s (max 300s)**; abort→synthesize. Alt: always-ask / auto-detect by
   query complexity.
8. **Perplexity Sonar deep backend** (FR-073) — _Recommend:_ **optional, opt-in per run** (cost shown, never
   auto-selected). Alt: native loop only / defer.
9. **Research output layout** (FR-074) — _Recommend:_ ship the **research-cockpit / single-focus / compare**
   templates (macro-scan recommended) with the **brief as a real dockview panel**. Alt: brief as a slide-in
   drawer; fewer templates v1 (compare needs a shared time-axis lock — evaluate cost).
10. **Slash/@ command set** (FR-100/101) — _Recommend:_ ship the **curated 11 slash + 9 @** set; custom
    `.vysted/commands/` deferred to v2; `@analyst`/`@quant` as **prompt-prefix routing** to existing personas
    in v1 (not new sub-agents).
11. **JARVIS posture v1** (US15) — _Recommend:_ **prompt-driven assembly** ("research X" → cockpit), lower
    failure surface; fully-anticipatory pre-loading is a later enhancement. Alt: fully anticipatory in v1.
12. **Constitution amendment** — _Recommend:_ add a principle **"VIII. Locale-Native & Correct, Everywhere"**
    (locale-native "McDonald's principle" + correctness-non-negotiable + resourcefulness/never-dead-end);
    MINOR bump (1.0.0 → 1.1.0), operator-ratified per Governance. Alt: keep 7 principles (treat as an
    application of Principles V/VI).

---

## Pass C — R4 Experience-Layer Execution (US18–US25, FR-112–130, SC-026–039)

> Added 2026-06-05 (see Clarifications → Session 2026-06-05). The **authoritative detail** is
> `docs/redesign/REBUILD_R4_SPEC.md` (master) + `R4_DESIGN_LANGUAGE.md`, `R4_STALE_CODE_REGISTER.md`,
> `R4_FAILURE_MODE_MATRIX.md`, `R4_BUILD_SEQUENCE.md`. This appendix is the canonical id index so the
> requirements live in Spec Kit. IDs extend the consumed ranges (US1–17, FR-001–111, SC-001–025) with no
> collision. All comply with the Constitution v1.1.0 and preserve §6.5 + Tier-1 LOCKED files byte-for-byte.

### User Stories

- **US18 (P1)** Agent-as-OS — drives the whole app at three speeds (FAST/ORCHESTRATED/DEEP) with live
  situational awareness; every mutation via the §6.5 bar.
- **US19 (P1)** One coherent app — collapsed research, context-preserving model-swap, Enter-sends, one mode
  system, no hardcoded-should-be-dynamic.
- **US20 (P2)** ⌘K Raycast-grade palette · **US21 (P2)** Tiptap notes · **US22 (P2)** Screener
  formula-grammar · **US23 (P2)** Research presentation + overview narrative + shareable briefs.
- **US24 (P1)** Screener returns the full universe in seconds with zero silent skips.
- **US25 (P2)** Original design language + graceful states everywhere + teach-the-agent first-run +
  per-research-space memory.

### Functional Requirements

- **FR-112** Three agent speeds: FAST (bare `@TICKER`/quick command → default cockpit instantly, LLM-free),
  ORCHESTRATED (propose a panel set + ask-when-unsure, routed through the §6.5 bar), DEEP (one research path).
- **FR-113** Continuous situational awareness (live open-panels/focused-symbol/viewport every turn; "this"
  resolves focus) + mandatory re-read of app state after any mutating action.
- **FR-114** Host-action completeness for obvious app-driving verbs (write screener filters, drawings,
  save-workspace, remove-from-watchlist, plan-stageable indicators/close/focus); each catalog-registered +
  §6.5-gated (orders never auto-apply, never FAST).
- **FR-115** Research collapses to ONE user-facing model (one entry; "go deeper" escalates in place;
  mode/angles/backend internal; 0 redundant user-visible triggers; one deep loop; Perplexity opt-in-per-run
  or removed).
- **FR-116** One interaction language: model-swap preserves context on every path; Enter sends in every
  composer; one mode system.
- **FR-117** No hardcoded-that-should-be-dynamic; no TS↔Python contract drift; the stale-code register is
  executed.
- **FR-118** Locale-aware market-session awareness (US+India first-class) on every price surface
  (open/pre/after/closed/last-close@tz), combined with staleness/provenance; a closed price never shown live.
- **FR-119** Every interactive element + data surface renders its full state set via shared primitives;
  0 silent `—` / raw-JSON dead-ends / silent skips.
- **FR-120** Raycast-grade ⌘K palette (grouped/scoped Ask-AI/Agents/Actions/Panels/Symbols; agents ranked
  above symbols; symbols gated; free-text AI-ask routes to the agent).
- **FR-121** Tiptap/Obsidian-grade notes (per-stock+general; markdown canonical blob via atomic write;
  slash/tables/wikilinks/markdown round-trip; `.md` share).
- **FR-122** Screener formula-grammar (nested AND/OR `CriterionGroup` editor + mathjs-in-Worker formula leaf
  — **never expr-eval**; agent-configurable via host action).
- **FR-123** Research presentation deepening (tables, ask-a-follow-up, storyline; clickable deduplicated
  source-type-badged sources rail with inline `[n]` hover/jump, broken-citations-shown).
- **FR-124** Company-overview AI narrative (The-Take→business→storyline→balanced bull/bear→risks, typed
  blocks beside metric cards; numbers from structured only + post-generation numeric-verification pass;
  cite-every-claim; no buy/sell rec).
- **FR-125** Shareable briefs, client-side only (markdown copy/export; PNG via html-to-image oklch-safe;
  PDF via window.print()+print stylesheet, jsPDF fallback; no backend/hosted link).
- **FR-126** Screener returns the full universe in seconds (batch quote endpoint + async + caching tiers +
  warm precompute; cold ≤ single-digit seconds for S&P 500, sub-second warm) with a visible skip ledger;
  0 silently dropped symbols.
- **FR-127** The four named bugs (screener column overlap, 502 empty-series, date-change crash, macOS Layout
  menu) fixed/confirmed with rendered-pixel / trusted-event / native proof.
- **FR-128** The original "Cold Instrument" design language applied (OKLCH zinc+indigo re-value into
  historical token names, 3-place canvas lockstep; type/spacing/unified-motion tokens; elevation-by-luminance
  with no neon/glow; warm-clay fallbacks purged; accent ≤5% of pixels).
- **FR-129** First-run teaches the agent's power (interactive "try this" chips that run); keyboard-first
  navigation throughout.
- **FR-130** Session restore + per-research-space agent memory (typed research-space field; per-space agent
  context persisted in the workspace blob, restored on reopen).

### Success Criteria

- **SC-026** Three speeds demonstrated with pixel proof (FAST opens a cockpit with no model call;
  ORCHESTRATED proposes+asks via the §6.5 bar; DEEP is the one path); 100% of mutations gated.
- **SC-027** "tell me more about this" resolves the focused symbol 100%; host-action completeness audit
  (screener-filter/drawings/save reachable by agent and hand); re-read-after-mutation holds.
- **SC-028** Exactly one research entry; 0 user-visible mode/angles/backend knobs; one deep loop (audit).
- **SC-029** Model swap preserves context on every path; Enter sends in every composer; one mode system (audit).
- **SC-030** Every matrix surface renders its full state set incl market-closed + symbol-not-found; 0 silent
  `—`/raw-JSON/silent-skips (visual audit, US+India).
- **SC-031** ⌘K groups+scopes; agents rank above symbols; AI-ask routes; symbols gated (no >3k flood) — pixel proof.
- **SC-032** Notes round-trips markdown; atomic write survives a mid-save crash; `.md` share opens correctly.
- **SC-033** Screener nested AND/OR + formula leaf evaluate; agent writes filters; expr-eval absent (audit).
- **SC-034** Full S&P 500 screen cold ≤ single-digit seconds / warm sub-second, <5% skips ALL itemized
  (no silent drop) — measured live.
- **SC-035** Research sources deduplicated+clickable across both legs; overview narrative passes the
  numeric-verification pass with 0 fabricated numbers; brief exports md/PNG/PDF and each artifact opens correctly.
- **SC-036** Each of the four bugs has saved visual/behavioral proof (header gap at narrow width; 502→clean
  empty; no date-crash under synced toggle; menu switches modes).
- **SC-037** Design language applied: contrast floors measured (body ≥4.5:1, large/non-text ≥3:1); no
  neon/glow; warm-clay fallbacks `rg`-clean; populated screenshots at both 1920×1080 and 2560×1440 saved.
- **SC-038** First-run "try this" chips run; per-research-space agent memory persists across relaunch.
- **SC-039** The floor holds at every milestone: §6.5 audit 9/9; Tier-1 LOCKED byte-for-byte untouched;
  orders never auto-apply; keyless-first intact; `pnpm ci-local` + smoke-test green (audit-grep).

### Open Product Decisions — Pass C _(flagged for operator; recommendation-first — see `REBUILD_R4_SPEC.md` §10)_

1. **India realtime BYOK** — _Recommend:_ R4 stays keyless-Yahoo-default + documents the ladder; broker-WS
   (Kite/Upstox) + EODHD are a separate later track. (Alt: pull broker-WS into R4.)
2. **Branch** — _Recommend:_ cut a fresh `004` off `003-vysted-rebuild`. (Either permitted.)
3. **Accent value** — _Recommend:_ adopt the OKLCH-refined ~12–15%-desaturated cool-indigo (hue unchanged);
   one-line revert to the exact ratified `#818cf8` if preferred.
4. **Sidecar Python-dep tolerance for the perf fix** — _Recommend:_ pure-`httpx` first; allow
   `curl_cffi`/`yahooquery` only if the PyInstaller `--onefile` binary still builds + boots (smoke-test green).
5. **Deep-research escalation UX** — _Recommend:_ explicit "go deeper" + auto-escalate on clear signals
   within the budget; never an auto-paid backend. (Alt: pure auto-detect / always-ask.)
