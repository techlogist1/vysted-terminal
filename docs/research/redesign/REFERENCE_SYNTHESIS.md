# Reference Synthesis — "Cursor for finance" redesign

This is the bridge from the five reference studies (`REF_cursor`, `REF_openbb`,
`REF_fincept`, `REF_mcp`, `REF_landscape`) to the Spec Kit **specify** phase. It
maps the strongest lesson from each reference onto a concrete Vysted design
decision, organized by theme. It is opinionated by design — where the references
disagree or hedge, this doc picks.

**The one-line thesis the spec must internalize:** the redesign is not "add a
chat box" and it is not literally "Cursor for finance" (that analogy invites the
wrong, verifiability-based scoring — `REF_landscape §2`). It is **invert the
terminal around the agent** — the agent becomes a co-equal primary surface that
*drives the dense panel cockpit* — while keeping the hand-driven cockpit
first-class and keeping every mutation behind a Cursor-style review gate. Under
that surface, the sidecar becomes a **single capability catalog projected to N
consumers** (internal Copilot + external MCP clients) the OpenBB way. Positioning
copy leads with **"the AI-native, extensible finance workspace,"** never "Cursor
for finance."

The competitive frame that forces urgency (`REF_landscape §3.1`): **Fincept is a
near-clone of Vysted's stated positioning** — AGPL+commercial, named-investor
agents, BYOK/local-LLM, 100+ connectors, node editor, MCP. The agents-and-license
combo is *already cloned* and is therefore table stakes, not a moat. Vysted's
defensible white space is the **six-capability plugin contract on a web stack +
dual-mode agent UX done right + a teaching command palette + local-first
verification**. Every theme below should be read as "build the moat, not the
table stakes."

---

## Theme 1 — Agent-centrality & dual-mode UX

**Lesson.** The win is a *layout-level inversion*, not a bigger chat panel.
Cursor rebuilt the IDE so the Agents Window is the primary surface and the editor
is the complement (`REF_cursor §1`). "Talk to the AI" is not one mode — it is
**four intents bound to four keystrokes**: Ask (read-only Q&A), inline Edit
(surgical change to the thing under the cursor), Composer (multi-object
creation), Agent/Background (autonomous, async, parallel) (`REF_cursor §2`). The
two personas — agent-delegators (novices live here) and hands-on drivers — must
both be first-class, sharing one workspace, one context, and one review surface;
the friction Cursor users feel is at the seam, so the switch between them must be
a single non-destructive gesture (`REF_cursor §7`). The dominant failure mode to
avoid is the **"conversation trap"**: pure chat is the wrong primary surface for
complex manipulable work — the agent does the ambiguous upfront work, then *hands
off to the dense, manipulable cockpit* (`REF_landscape §4.3`). Ask-vs-Agent is now
a shipped convention (Copilot, ChatGPT), and its known pitfall is *mode
discoverability* — Copilot buries the switch in a tiny dropdown and "developers
pick the wrong one half the time" (`REF_landscape §4.2`).

**Who does it well.** Cursor (the four-mode spine, the agents rail, the
non-destructive local↔cloud handoff). OpenBB Copilot is the proven *finance*
instance of "agent reads/writes the dashboard widgets via function calling"
(`REF_landscape §4.3`) — i.e. agent-drives-cockpit is shipped, not speculative.
Fincept's `SuperAgent` triage router (LLM classifies intent → routes to persona,
keyword fallback offline) is a clean degradation pattern (`REF_fincept §2.2`).

**Vysted implication.**
- **Promote the agent from `ChatSidebar.tsx` to a primary surface** that can take
  a dominant column or the full cockpit and that **opens panels as its output** —
  panels are to Vysted what files are to Cursor. This is the single largest UX
  change in the redesign.
- **Ship the four-mode spine mapped to finance verbs**, each on a stable global
  hotkey: **Ask** (read-only Q&A over the workspace — roughly today's chat, but
  one of four), **Edit-this-panel** (Cmd-K over a panel: "add VWAP + 200-EMA",
  "add a P&L column", "filter this screener to mid-caps"), **Build** (Composer:
  "build me a semiconductor cockpit" → creates panels; also the home for
  node-editor/workflow strategy composition), **Delegate** (Background: a Strategy
  Critic backtest, a multi-name research sweep, a condition monitor). Do **not**
  ship a "simple mode" and a "pro mode" as two apps — one workspace, low-floor
  agent door + high-ceiling panel door.
- **Add an Agents rail** listing *running* sessions (a backtest critic, a research
  sweep, a screener run) with status — the finance analogue of Cursor's agents
  sidebar. The sidecar already runs these (Phase 4–5); what is missing is the
  surface that makes them feel co-equal with panels, plus "send to background /
  bring forward" controls.
- **Agent populates, user manipulates.** The agent's job is to open panels, set
  the chart, load the watchlist, stage an order — then *step back*. Never force a
  trader to "scan ten things at once" inside a transcript.
- **Make mode obvious and consequence-explained at the point of use** (avoid the
  Copilot hidden-dropdown trap). Mode/persona/provider are keyboard axes (Cursor's
  `Cmd+.` / `Cmd+/`): `Cmd+.` switches the active persona (Buffett / Dalio /
  Researcher / Strategy Critic), `Cmd+/` switches BYOK provider.

---

## Theme 2 — Minimal-dark design language & the trust spine

**Lesson.** Keep Bloomberg's **grammar and density**; reject its
**discoverability tax** (`REF_landscape §1`). Bloomberg's moat is the deterministic
command grammar (`TICKER · function-code · <GO>`) and keyboard determinism — *not*
the black/amber chrome, the 86-page manual, or friction-as-prestige. "Bloomberg
can monetize pain because it already won; a challenger that ships pain just
loses." Density is a *feature* for the target user (a trader scanning ten live
surfaces does not want whitespace), but onboarding must be progressive.

Complexity must be **layered, not flattened** (`REF_cursor §3`): a first-time user
is productive with essentially one gesture (Cursor's Tab), the next layer is three
taught keystrokes, and deep surfaces (MCP servers, rules files, background agents,
the context ring) reveal themselves only when the user reaches the workflow that
needs them.

The **apply/diff/accept interaction is the trust spine** and the single most
important pattern to copy *correctly* (`REF_cursor §4`). Red/green inline diffs,
per-change accept/reject, a hard preview→applied boundary, keyboard-driven. Cursor
*regressed* by auto-applying without the diff — its community revolted and called
per-change Apply "your best UX advantage." For finance this is not UX, it is
safety: there is no `git revert` on a placed order. Finance also has a **low
hallucination tolerance with a regulatory edge** — trust collapses non-linearly
past ~30% error, and the literature converges on **enforced source citations + a
verifiable audit trail** as the agent-era stand-in for coding's compiler
(`REF_landscape §4.4, §5`).

**Who does it well.** Cursor (inline diffs, layered complexity, Tab as the
zero-friction floor). Superhuman (the command palette that *teaches its own
shortcuts* — the antidote to the 86-page manual, `REF_landscape §4.1`). Fincept's
`SecureStorage.h` threat-model honesty is exemplary (`REF_fincept §3.2`).

**Vysted implication.**
- **Dark-only, token-driven, density-with-progressive-disclosure.** Vysted already
  has the token system (`tokens.css`) and the "Claude after dark" palette where
  token *names* are historical (amber renders coral, etc.) — re-skin via tokens,
  remembering canvas (`chart-theme.ts`) is single-sourced separately. Light theme
  stays a Tier-4 BLOCKER until v1.1 (per the visual convention).
- **Define Vysted's "Tab"** — the zero-config, always-on, one-gesture finance
  primitive. Strong candidate: **inline AI annotations on hover/select** (hover a
  candle → "earnings gap, +4 ATR move"; select two watchlist rows → a ghost
  "compare" affordance). Ambient intelligence; the user does nothing but look.
- **Teach three keystrokes, not thirty panels.** A new user learns Ask /
  Edit-panel / Build and is productive. The Bloomberg function-code firehose is
  the *deep* layer, lived in the command palette, never the front door.
- **Minimal starter cockpit by default** — the canonical AAPL-anchored 5-panel
  shape, not an empty grid or a wall of every plugin. Plugins open as *additional
  tabs the agent or user opens*.
- **Every agent-proposed mutation gets a reviewable diff before it lands.** Panel
  config (old→new indicators/columns/filters), portfolio (position delta),
  workspace build (a stageable list of panels-to-create). Accept-all / reject-all
  / per-item, keyboard-driven, with a distinct "ghost/diff" treatment for pending
  state. **The §6.5 `confirm_and_place` gate IS the "accept the diff" boundary for
  orders** — make its UI look and feel like Cursor's diff-accept (symbol, side,
  qty, est. cost, P&L impact, explicit accept, append-only audit on accept).
  **Never** ship an auto-apply / "YOLO" order path — Cursor's regression is the
  cautionary tale, and finance has real money on the line.
- **Mandatory citation-on-claim in the chat surface** + provenance on every data
  response (which provider served it). This is the verification surface that
  substitutes for coding's compiler, paired with the existing audit log.

---

## Theme 3 — MCP-as-universal-tool-layer / app-as-framework

**Lesson (the headline).** Build **one tool catalog projected to N consumers**.
OpenBB's thesis — "connect once, consume everywhere" — is exactly Vysted's
MCP-as-framework goal stated by a mature codebase: one set of route/provider
definitions projects into Python, REST, MCP, CLI, Excel, and Workspace with zero
per-surface re-authoring (`REF_openbb §0, §4, §7`). The keystone is
**`FastMCP.from_fastapi(app)`** — every REST route becomes an MCP tool
automatically, no hand-written shims (`REF_openbb §7.3`). OpenBB ships **no agent
runtime, no LLM abstraction, no per-vendor tool schemas** — it exposes tools +
skills + prompts over MCP and lets the *client's* agent drive (`REF_openbb §6`).

Vysted's reality today (`REF_mcp §4`): **two divergent tool surfaces** — the
internal `agent_tools` catalog (`schemas.py::TOOL_SCHEMAS` + per-vendor
serializers, consumed by Copilot + personas) and the external `mcp_server.py`
FastMCP tools (hand-written shims, consumed by Claude Code/Desktop/Cursor). They
overlap but are not unified, with an embarrassing asymmetry: the external surface
can `invoke_agent` but can't run the screener or read fundamentals by the same
names. The MCP primitives split is **tools (model-controlled) / resources
(app-controlled) / prompts (user-controlled)**, but most clients consume **tools**
far more reliably — so lead with tools, add a *small* resource + prompt layer as
progressive enhancement, never make a capability reachable *only* via resource or
prompt (`REF_mcp §1`). At scale, **dynamic tool discovery** (start disabled,
`available_categories` / `activate_tools` per session) fights context bloat — but
ship a flat catalog now and just *tag domains from day one* so discovery drops in
later with no rewrite (`REF_mcp §6`, `REF_openbb §7.3`).

**Who does it well.** OpenBB (`from_fastapi`, `openapi_extra["mcp_config"]`
per-route control, progressive discovery, skills-as-resources, server-prompts as
encoded workflows, `to_llm()` serializer, AGPL-3.0 — same license family). Fincept
exposes generic **DataHub tools** (`datahub_list_topics / peek /
subscribe_briefly`) that let an agent observe *any* live stream by topic name — a
genuinely clever "reason about a volatile feed, not a snapshot" primitive
(`REF_fincept §5.3`).

**Vysted implication.**
- **Unify the two tool surfaces into one capability catalog, two adapters.** The
  catalog (`agent_tools` registry + `TOOL_SCHEMAS`) is the single source of truth;
  the internal adapter (`agent_runtime` → anthropic/openai/gemini shapes) and the
  external adapter (FastMCP) are two *renderers* of it. Adding `price_data` once
  makes it visible to Copilot **and** Claude Code. One `read_only` flag drives both
  the internal mutation gate **and** the MCP `readOnlyHint` annotation.
- **Adopt `FastMCP.from_fastapi(app)`** and delete the per-tool httpx shims; keep
  hand-written tools only for genuinely non-REST ones (`invoke_agent`, which
  aggregates an SSE stream). Caveat: PyInstaller `--onefile` drops entry-point
  metadata, so keep *discovery* an explicit static-import map — it's the
  *registration shape* that ports, not entry-point discovery (`REF_openbb §1.4`).
- **Broaden external coverage to all eight domains** (quotes, charts, screener,
  fundamentals, portfolio, news, quant, brokers) and **tag every tool with a
  domain from day one** so OpenBB-style discovery drops in around ~25–30 tools.
- **Derive the agent-tool schema from the route OpenAPI** — kill the third
  hand-maintained copy (the CLAUDE.md gotcha: "add a handler AND a `TOOL_SCHEMAS`
  entry AND an agent allow-list — all three"). One route → derived JSON-Schema →
  per-vendor transform.
- **Add a stdio entrypoint + a port-discovery file** (`<appdata>/vysted/mcp.json`)
  so Vysted is a framework Claude Code can spawn headless or attach to live —
  keep Streamable-HTTP stateless at `/mcp` for the in-app path. **Loopback = no
  auth; any non-loopback bind = auth + Tier-4 block-and-ask** (`REF_mcp §2, §5`).
- **Ship skills + server-prompts over MCP** (Strategy Critic, per-agent playbooks,
  `equity_workup` / `macro_regime` / `portfolio_review`) — projects Vysted's
  research-lab IP to any external agent for free.
- **Keep owning the agent loop** — unlike OpenBB, Vysted's self-contained,
  offline-of-an-external-agent, BYOK positioning *justifies* an in-house runtime.
  The lesson is one tool *surface*, not "delete the loop." (Consider Fincept's
  DataHub generic `subscribe_briefly` tool as a later addition once a pub/sub bus
  exists — §Theme 4.)

---

## Theme 4 — Data-connector / plugin architecture

**Lesson.** OpenBB's **standard-model-as-contract** is the cleanest known answer
to interchangeable data providers (`REF_openbb §1`): a small set of standard
Pydantic models is the cross-provider contract; a provider implements by
*subclassing* the standard model (provider wire-name aliases + provider-only
extra fields); one `Provider` object registers `{standardModelName → fetcher}`
with `credentials`, `website`, `instructions`; the registry resolves *by model
name + preference order*, not by an `if asset_class == "crypto"` chain. Load is
**fault-tolerant** (a bad provider warns, never crashes the registry) and every
result envelope carries **provenance** (`provider`, `warnings`) plus a `to_llm()`
serializer. `extra="allow"` is **load-bearing** — it's what lets providers extend
shapes without contract churn (keep `extra="forbid"` only on safety-critical
models: orders, audit log) (`REF_openbb §2, §8`).

Fincept's surprise is the **universal data hub**: its 117 connectors are not just
finance APIs — they include relational DBs (Postgres, Snowflake), NoSQL, time-
series (kdb+, ClickHouse), cloud storage (S3, GCS), file formats (Parquet, Avro),
streaming (Kafka, MQTT, gRPC), open banking (Plaid), and alt-data (RavenPack)
(`REF_fincept §1, §3.1`). The UX pattern: a connector declares `credential_fields[]`
(label, type, `secret: true`) and the host renders/masks/tests the form — **zero
per-connector UI code**. The **DataHub** (a typed in-process pub/sub bus with a
`<family>:<sub>:<id>` topic grammar + a `TopicPolicy` rate/coalesce layer,
retire-on-completion for per-run topics) is "the biggest single architectural idea
worth lifting" (`REF_fincept §5.2, §6`).

**Who does it well.** OpenBB (the provider/standard-model/fetcher pattern, the
discriminated-union merge, provenance, `to_llm()`). Fincept (universal-connector
breadth, schema-driven config dialog, the DataHub bus + symbol-group panel
linking + lazy panel factories, `REF_fincept §5.1`). Both warn: **breadth without
depth is a trap** — Fincept's 55 screens include thin LLM-prose panels; Vysted's
"no Phase 2 / full-scope" DNA should resist breadth-for-breadth (`REF_fincept §1`).

**Vysted implication.**
- **Give the plugin `DataSource` capability a `Provider`-shaped registration**:
  `{standardModelKey → fetcher}` + `credentials` + `website` + `instructions`, so
  the BYOK UI renders from the plugin object. **Resolve the registry by model key
  + preference order**, replacing the current dispatch-by-hardcoded-`if`
  (`provider_registry.py`). Promote `DataSourceKind` into a typed standard-model
  key so two plugins serving the same kind are genuinely interchangeable.
- **Add `provider` + `extra="allow"` to non-safety `sidecar/models/`** and a
  `to_llm()`-style compact serializer on the result path. Do **not** build
  OpenBB's full `make_dataclass` param-merge engine yet — premature until a second
  same-kind plugin lands (Tier-3 decision flagged for that moment).
- **Build the universal data connector** (DBs / S3 / Kafka / Parquet, not just
  curated feeds) into the plugin `data` capability — directly on Vysted's "the
  data isn't the limit" positioning, and a place Fincept proves breadth is
  achievable with a flat self-registering registry. Pick depth where Vysted
  already has it (macro/SEC/QuantLib) and let plugins fill the long tail.
- **Schema-driven config dialog from `credential_fields[]`** for *all* data
  sources (generalize the broker `BrokerProfile` pattern) — zero per-source UI.
- **Seriously consider the DataHub bus** as the redesign's data backbone: a typed
  pub/sub with topic grammar + policy layer would decouple producers from panels,
  give the agent a *uniform observation surface* over every live stream (the
  `subscribe_briefly` tool), enable **symbol-group panel linking** (change ticker
  in one linked panel → all follow — a high-value UX feature Vysted lacks), and
  bound memory via retire-on-completion. Fits the plugin `data` + `agents`
  capabilities cleanly. **Keep the typed `VystedPlugin` contract for UI/data
  extensibility — do not collapse to MCP-only the way Fincept did** (you can't
  ship a panel over MCP; that's the gap Fincept never closed).
- **Fault-tolerant plugin load** (a plugin that fails `initialize()` degrades to
  "unavailable", never takes down the sidecar) + **lazy panel factories** +
  **per-instance UUID state** (portable straight from Fincept's dock router).

---

## Theme 5 — Credentials / BYOK hub

**Lesson.** Credential keys are **owned and declared by the provider** (OpenBB
auto-namespaces `api_key` → `fmp_api_key`), so the BYOK UI renders "this provider
needs key X, get it at `<website>`, here are `<instructions>`" directly from the
provider object (`REF_openbb §5`). A `require_credentials = False` opt-out keeps
the "missing key" UX honest for free sources (yfinance needs none). **Least
privilege at query time**: pass a provider *only* its own declared keys
(`filter_credentials`), never the whole keychain — the same shape as Vysted's
v0.6.5 Tradesa "secret in request header" flow. Fincept generalizes a declarative
`CredentialField` enum (ApiKey, ApiSecret, AuthCode, ClientCode, TotpSecret,
Environment…) so every broker's different login dance is expressed *declaratively*
(`REF_fincept §3.2, §4`), and adds **import/export of connections** for
portability across machines.

**Do NOT regress** to either reference's storage: OpenBB stores keys in plaintext
`user_settings.json`; Fincept uses AES-GCM-on-SQLite with a machine-ID-derived key
crackable by any same-user process. **Vysted's OS keychain (Tauri Rust
`keychain_set/get/delete`, renderer-reads-then-passes-in-request) is strictly
better — keep it** (`REF_openbb §5`, `REF_fincept §3.2, §7`). The MCP corollary:
**credentials ride request headers, never tool/body args, never logged or echoed**
(`test_response_never_echoes_credentials`); external agents inherit *the user's*
entitlements, never a superset (`REF_mcp §5`).

**Who does it well.** OpenBB (provider-declared keys, `require_credentials`
opt-out, per-query least-privilege). Fincept (declarative credential-field enums +
per-broker auto-login + schema-driven dialog + import/export). Both are *honest
about storage threat models* — copy the honesty, not the storage.

**Vysted implication.**
- **Build a single BYOK/credentials hub** where every provider/broker/connector
  declares `credential_fields[]` (label, type, `secret`, `website`,
  `instructions`, `require_credentials`) and the host renders/masks/tests the form
  generically — one hub for LLM keys, data-provider keys, broker creds, and
  user-wired connectors. The plugin `data` and broker contracts both carry this
  declaration.
- **Keep OS-keychain storage; never regress** to file or machine-ID-derived AES.
  Maintain a written threat model for the keychain → request-header flow.
- **Least-privilege at use**: a provider/plugin receives only its declared keys,
  via request headers, never the whole keychain, never the tool schema.
- **Add import/export of wired-up connections** — low-cost, on-positioning for a
  local-first BYOK app (move your data sources between machines).
- **Keep provider/model/cost legible** on the agent surface (which provider, which
  model, est. tokens) — Cursor's Auto-mode credit opacity drew complaints; BYOK
  makes legibility free and is a differentiator (`REF_cursor` anti-patterns).

---

## Theme 6 — Feature breadth to prioritize

**Lesson.** Fincept's breadth (55 screens, 117 connectors, 22 brokers, 37 agent
configs) is its most impressive axis but **much of it is thin** — geopolitics /
maritime / relationship-map panels lean on LLM prose over hard data, and its agent
READMEs list files that don't exist (`REF_fincept §0, §1`). Breadth-for-breadth is
a trap. The genuinely high-value, *transferable* pieces are concentrated:

1. **The durable-agent layer** — ~2.6 kLOC of clean Python (`finagent_core/
   agentic/`): SQLite-checkpointed **resumable tasks** `(task_id, step,
   state_blob)`, a **BudgetGuard** (token/$/wall-clock/step ceilings, first breach
   aborts — a §6.5-adjacent safety primitive for *agent spend*), a **Reflexion**
   post-step critic (`continue | replan | question | done`), **HITL
   pause-for-question**, and a **scheduler** (cron-ish DSL) (`REF_fincept §2.3`).
   This is precisely the upgrade path for Vysted's single-turn-ish loop.
2. **The `IBroker` + `BrokerProfile` contract** — one abstract interface,
   declarative profile driving all UI, advanced methods **default to
   `"Not supported"`** (a thin broker implements ~10 methods, a rich one overrides
   40+), shared close-all/cancel-all/margin-estimate fallbacks in the base
   (`REF_fincept §4`). The ergonomics to copy — but Fincept has **no append-only
   audit, no type-gated execution, `place_order` on the same interface as
   `get_quotes`** — so steal the shape, **keep Vysted's §6.5 defense-in-depth**.
3. **Personas-as-JSON-with-a-rubric** — the quality lever is the *structured
   analyst rubric* ("every section required: MOAT / RETURNS ON CAPITAL /
   VALUATION"), not bespoke Python per investor. Validates Vysted's declarative
   agent design — invest in rubric depth, not persona code (`REF_fincept §2.1`).
4. **Same output contract across capable vs weak backends** (Fincept's
   `deepagents` ↔ `FinceptOrchestrator` split: tool-calling model and prompt-loop
   model produce the *identical* output schema) — critical for BYOK, where a weak
   local Ollama must produce the same-shaped result as Claude, just lower quality
   (`REF_fincept §2.2`).

Landscape sharpens the prioritization (`REF_landscape §5`): the moat is the
**plugin platform + dual-mode UX + teaching palette + local-first verification** —
*not* the agents/license. Lead breadth where Vysted has *real data depth* (macro,
SEC, QuantLib already shipped) and let plugins fill the long tail.

**Vysted implication (priority order for the spec to scope).**
- **P0 — the dual-mode agent surface + four-mode spine + diff/accept gate**
  (Themes 1–2). This is the redesign; everything else supports it.
- **P0 — unify the tool catalog + `FastMCP.from_fastapi` + stdio entrypoint**
  (Theme 3). The framework story, and it de-risks the agent surface by giving it
  one coherent toolset.
- **P1 — the durable-agent layer** (resumable tasks + **BudgetGuard** + Reflexion
  critic + HITL + scheduler). BudgetGuard is the §6.5-adjacent must-have:
  autonomous agent spend needs a hard token/$/wall/step ceiling the same way
  broker execution needs the kill switch (~150 LOC). Without it, "Delegate" mode
  is unsafe to ship.
- **P1 — the command palette as the teaching deep-layer front door** (Bloomberg
  grammar reborn, Superhuman teach-its-own-shortcuts) — fuzzy-search every panel,
  plugin command, symbol jump, agent.
- **P1 — provider-shaped data registry + universal connector + schema-driven
  credentials hub** (Themes 4–5).
- **P2 — DataHub pub/sub bus + symbol-group panel linking** (Theme 4) — high
  architectural value, but larger; sequence after the agent surface lands.
- **P2 — broker plugin contract in the `IBroker`/`BrokerProfile` shape**, behind
  §6.5, with the `propose_order`-not-`place_order` invariant carried to every
  consumer (internal + MCP).
- **Resist** thin LLM-prose panels (geopolitics/maritime-style), breadth-for-
  breadth, and any marketing-doc-as-engineering-doc drift (audit doc claims
  against the tree at release — Vysted's living-doc discipline is the antidote).

---

## Top 10 design decisions the spec should make

1. **Invert the terminal around the agent.** The agent is a co-equal **primary
   surface** that opens panels as its output; the dockview cockpit is the
   first-class complement, not the only home screen. Retire the bolted-on
   `ChatSidebar` model. (Theme 1)

2. **Ship the four-mode spine on stable global hotkeys — Ask / Edit-panel / Build
   / Delegate** — mapped to finance verbs, with mode/persona/provider as visible
   keyboard axes. One workspace, two front doors (low-floor agent, high-ceiling
   panels); never two separate apps. Make mode obvious and consequence-explained
   at the point of use. (Theme 1)

3. **The diff/accept gate is the trust spine and is non-negotiable.** Every
   agent-proposed mutation (panel config, portfolio, workspace build, and
   especially orders) renders as a reviewable preview→applied diff: accept-all /
   reject-all / per-item, keyboard-driven. The §6.5 `confirm_and_place` gate IS
   the order-diff boundary. **No auto-apply path for orders, ever.** (Theme 2)

4. **One capability catalog, two adapters.** Unify the internal `agent_tools`
   catalog and the external MCP surface into a single source of truth; the Copilot
   adapter and the FastMCP adapter are two renderers. One `read_only` flag drives
   both the internal mutation gate and the MCP `readOnlyHint`. Tag every tool with
   a domain from day one. (Theme 3)

5. **Adopt `FastMCP.from_fastapi(app)` + add a stdio entrypoint + a port-discovery
   file.** Delete the per-tool httpx shims (keep only non-REST `invoke_agent`);
   broaden external coverage to all eight domains. This is the "app as framework"
   move. Loopback = no auth; any non-loopback bind = Tier-4 block-and-ask.
   (Theme 3)

6. **Provider-shaped, model-keyed data registry + `extra="allow"` + provenance.**
   A plugin contributes `{standardModelKey → fetcher}` with `credentials` /
   `website` / `instructions`; resolve by model key + preference order, not
   `if asset_class`. Every result carries its `provider`. Defer the
   `make_dataclass` merge engine until a second same-kind plugin lands. (Theme 4)

7. **Build the universal data connector + a schema-driven BYOK/credentials hub.**
   Any source (finance API, Postgres, S3, Kafka, Parquet, broker) declares
   `credential_fields[]` and the host renders/masks/tests generically. **Keep the
   OS keychain — never regress to file or machine-ID-AES storage.** Least-privilege
   at use (only declared keys, via request headers). (Themes 4–5)

8. **Ship the durable-agent layer with a BudgetGuard before "Delegate" mode goes
   live.** SQLite-checkpointed resumable tasks + token/$/wall/step hard ceiling +
   Reflexion critic + HITL pause-for-question + scheduler. BudgetGuard is the
   §6.5-adjacent safety primitive for autonomous spend; "Delegate" is unsafe
   without it. (Theme 6)

9. **Command palette as the teaching deep-layer.** Bloomberg's deterministic
   command grammar reborn as a Cmd-K palette that *teaches its own mnemonics*
   (Superhuman pattern) — fuzzy-search every panel, plugin command, symbol jump,
   and agent. Keep density + grammar; reject the discoverability tax. Minimal
   AAPL-anchored starter cockpit; plugins open as tabs, never preloaded.
   (Themes 1–2)

10. **Verification is the product, and the moat is the platform — position
    accordingly.** Mandatory citation-on-claim + provenance + append-only audit +
    §6.5 safety = the compiler-substitute finance lacks. Lead positioning with
    **"the AI-native, extensible finance workspace"** (never "Cursor for
    finance"); the differentiator is the **six-capability plugin contract on a web
    stack + dual-mode UX + teaching palette + local-first BYOK privacy** — *not*
    the named-investor agents or the license, which Fincept already cloned.
    (Themes 2, 6 / `REF_landscape §5`)

---

### Cross-reference quick map

| Theme | Primary refs |
|---|---|
| 1 — Agent-centrality & dual-mode UX | `REF_cursor §1,2,7` · `REF_landscape §4` |
| 2 — Minimal-dark design & trust spine | `REF_cursor §3,4` · `REF_landscape §1,4.4,5` |
| 3 — MCP-as-universal-tool-layer | `REF_openbb §0,4,6,7` · `REF_mcp` (whole) |
| 4 — Data-connector / plugin architecture | `REF_openbb §1,2,8` · `REF_fincept §1,5` |
| 5 — Credentials / BYOK hub | `REF_openbb §5` · `REF_fincept §3,4` · `REF_mcp §5` |
| 6 — Feature breadth to prioritize | `REF_fincept §2,4,6` · `REF_landscape §3,5` |
