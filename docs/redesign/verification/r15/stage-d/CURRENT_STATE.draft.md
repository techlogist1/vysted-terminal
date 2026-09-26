<!-- DRAFT at 4d893147def983623de681effd1bfbae2e7441c5 by the Stage D docs wave; refresh before rc2 -->
# Vysted Terminal — Current State (as of 4d89314, 0.9.0 candidate)

> An honest inventory of what exists today, written to anchor the "Cursor for
> finance" redesign. It records the working foundation worth keeping and, just
> as deliberately, the scaffolding, dead wiring, and unverified surfaces that
> the redesign should not mistake for done. Sourced from a subsystem-by-
> subsystem read of the live code at `main` HEAD `3123e7c` (Phase 10 handoff),
> the Phase-10 handoff report, and `BLOCKERS.md`. The standing honesty caveat:
> the codebase is **green on every machine-checkable gate** (`pnpm ci-local`
> exit 0, 619 vitest, 942 pytest, §6.5 9/9 — **stale, pre-R15; see §0.0**)
> and **unproven on most
> human-checkable ones** — live UX, populated visuals, and any BYOK
> round-trip are unverified because the harness cannot drive the WKWebView with
> real data and macOS screen capture failed mid-Phase-10.
> **This description of the codebase is itself pre-R15.** §0.0 immediately
> below is the current top-of-file truth (R15: trading removed, relicensed,
> Stage C register remediation); §0, §0.5 and §0.x further down stay as
> labelled history of the redesign's earlier windows. Any specific claim in
> the body below §0.0 that conflicts with §0.0 is superseded by it.

---

## 0.0 R15 state (as of 4d89314, 0.9.0 candidate)

> This section is the current top-of-file truth. §0, §0.5 and §0.x below are
> kept as historical record of the pre-R15 redesign lineage and are not
> rewritten here.

**Version.** This candidate targets **0.9.0**. The version-of-truth files
(`package.json`, `src-tauri/Cargo.toml`, `src-tauri/tauri.conf.json`,
`sidecar/app.py` `FastAPI(version=...)`, `HOST_VERSION` in
`src/lib/plugin-bootstrap.ts`) are still literally `0.8.0` at this sha and
mutually consistent with each other — `0.9.0` lands when the prepared version
branch (`worktree-agent-r15-version-0.9.0`) merges, right after the `r15-rc1`
tag — confirmed at the tag.

**Trading removed permanently (D81, `a122dbf6`, 23 Sep 2026).** No broker
connectivity, order placement, simulated/paper account, kill switch or
append-only order-audit log exists anywhere in the product — surfaces, agent
tools, routes or docs. Confirmed at this sha: no broker/Kite service code
remains under `sidecar/` or `src/` (only incidental instrument-name string
matches in the resolver master data and a stray display-label entry), no
`autobahn` dependency anywhere, and the safety UI components
(`KillSwitchToolbar`, `OrderConfirmationDialog`, `AuditLogViewer`,
`BrokerConnectPanel`) no longer exist in the tree — only the DisclaimerFlow
module (`DisclaimerFlow.tsx`, its test and `index.ts`) remains under
`src/modules/safety/`, covering first-launch terms, not order safety. The user's own tracked
portfolio (manual holdings, cost bases, P&L on real prices, CSV export,
notes, watchlists) is unaffected and stays, riding the same proposed-changes
trust gate as before. Full detail: §0.x below and
`docs/redesign/verification/r15/stage-c/REMOVAL_PLAN.md`.

**Relicensed.** The core is now **PolyForm Strict 1.0.0** (`LICENSE`, first
heading `# PolyForm Strict License 1.0.0`) plus a commercial license
(`COMMERCIAL_LICENSE.md`) for dual-licensing; `package.json`'s `license`
field reads `SEE LICENSE IN LICENSE`. The plugin contract
(`types/plugin.ts`, `types/plugin-runtime.ts`) and the example plugin
(`plugins/example/*`, including `example.test.ts` and `manifest.json`) are
carved out under **Apache-2.0** (`LICENSE-APACHE`, present at this sha; see
`LICENSING.md`) so third-party plugin
authors are not bound by the strict core license.

**Frontend is Vite 8 + React 19** since `8c2f9ab9` (2026-06-10, "migrate
Next.js -> Vite 8 + React 19 (WS1)"); there is no `next` dependency or
binary at this sha (`package.json` `"dev": "vite"`, `"build": "vite build"`).
Next.js references below §0.0 are pre-migration history.

**R15 Stage C remediation (batches 2–22, after the D81 batch-1 trading
removal; batch-23 blocked/unmerged; batch-24 merged `6778f892` as of
`4c6dfe8c`).** A
census-driven register (`docs/redesign/verification/vysted-r15-register.json`)
recorded 887 raw findings → **652** register entries (76 rejected) across
critical/high/medium/low severity — the entry count grew from the 626 this
section cited at an earlier draft as later batches split/added entries. The
register's own `counts` field is authoritative (never `register.py status`,
which recomputes from census merges and lags): raw=887, entries=652,
rejections=76, critical=16, high=116, medium=293, low=227. At this sha:

| Severity | Entries | Fixed | Open | Needs GUI | Removed w/ feature | Blocked Tier-4 | Other          |
| -------- | ------- | ----- | ---- | --------- | ------------------ | -------------- | -------------- |
| critical | 16      | 16    | 0    | —         | —                  | —              | —              |
| high     | 116     | 105   | 0    | 4         | 1                  | 6              | —              |
| medium   | 293     | 258   | 0    | 5         | 9                  | 16             | 5 not_a_defect |
| low      | 227     | 12    | 205  | 2         | 4                  | 4              | —              |

(Table is the `4c6dfe8c` state: `R15-LEAD-035` moved medium Open→Blocked
Tier-4, one row changed from this section's `4d893147` capture, 258/1/16
→258/0/16. Sums: fixed=391, open=205, needs_gui=11, removed_with_feature=14,
blocked_tier4=26, not_a_defect=5 — matches the register `counts` field
exactly.) All 16 critical entries are fixed. **Open critical/high/medium is
now exactly zero, as of `4c6dfe8c`** (`R15-LEAD-035`, medium, subsystem
`agent-tools`, agent-write no-tool-cue detector, moved to `blocked_tier4`
that sha — see "Known limitations" below for the disposition, which is an
escalation to the operator, not a certified fix); the
205 open low entries and the 26 blocked_tier4 ids are enumerated in
`BLOCKERS.md` "R15 open items". Per-batch plans and certified verdicts live
under `docs/redesign/verification/r15/stage-c/batch-2` through `batch-22`
(each a `PLAN.md` + `VERDICTS.md` pair, all `approve` except batch-22 and
batch-23 = `block`); batch-23's int branch went unmerged (a fresh verifier's
LEAD-035 stop-rule refusal). **Update as of `4c6dfe8c`:** batch-24 (LEAD-035's
named narrowing-only fix) merged as `6778f892` (int `d1290f66`) and its dir
is now tracked at `docs/redesign/verification/r15/stage-c/batch-24/`
(`PLAN.md`, `VERDICTS.json`, `VERDICTS.md`, `LEAD-035-CONCURRENCE.md`,
`verifier-evidence/`, `writer-evidence/`) — its own verdict is `approve` (the
branch narrows only and regresses nothing), but `R15-LEAD-035` itself is
`not_certified` a fourth time; see "Known limitations" below. Batch merge commits
are listed in `CHANGELOG.md` under the "R15 Stage C" headings; the batch-1
removal-plan riders are D81–D92 (D83 records the relicense), and per-batch
decisions from batch 3 on carry `D-B<n>-<k>` ids in
`docs/redesign/DECISIONS.md` (D81 through D92, 12 new decisions since the
`r13-bedrock` tag).
Full open-item detail (grouped by subsystem, plus the open Tier-4 operator
decisions) is in `BLOCKERS.md` "R15 open items".

**Known limitations at rc1 — agent chat with a keyless local model.**
Operator-accepted (Tier-4 sign-off, DECISIONS_FOR_OPERATOR.md §4.9–4.12): one
known-limitation class ships as a documented limitation of the keyless
local-model lane, not a bug held open — with a keyless local model the agent
can fabricate a figure, or claim a completed write, when it has no tool
result to ground the claim; no further filter round runs this release.

- **R15-LEAD-030** (high) — `blocked_tier4`, a fresh verifier concurred in
  batch-23 (`docs/redesign/verification/r15/stage-c/batch-23/LEAD-030-CONCURRENCE.md`):
  > With a keyless local model, the agent can still state an invented price or
  > metric as if a tool had returned it when the figure is about a company no
  > successful tool call in that turn covered — one named in the same
  > paragraph as a company whose call succeeded (under a name the guard
  > cannot map, or never looked up at all), or any company in a turn where no
  > call failed or no tool was called — and a figure-less fabricated result
  > dump or a code fence left open from an earlier round can also render,
  > while every shape pinned in eight fix rounds is replaced by an honest
  > "returned no data" note.

  (The batch-23 disposition verifier struck the original sentence's clause
  "figures for companies whose call succeeded are grounded against the tool
  result" — the guard never checks a figure for a subject whose call
  succeeded; wording above reflects the strike, per
  `docs/redesign/verification/r15/stage-c/batch-23/DISPOSITION-CONCURRENCE.md`.)
- **R15-LEAD-035** (medium) — `blocked_tier4` as of `4c6dfe8c`, under the
  operator's three-failure rule — an ESCALATION, not a fresh-verifier
  concurrence. Batch-24 (merge `6778f892`) shipped the named narrowing-only
  fix; it holds as a strict subset (0 new strips on 97 phrasings, 0
  over-strips on the 67 pinned no-tool phrasings, the 7 previously
  over-matched data prompts now call `price_data` live 21/21), but the entry
  failed certification a fourth time — 4 of 18 fresh qualified-negation data
  requests still lose every tool, and the local model then states an
  invented price in 6/8 live runs. The fresh verifier REFUSED the
  `blocked_tier4` concurrence and named a further narrowing-only guard (a
  qualifier negative lookahead plus `(?<!says )`) it would certify
  (`stage-c/batch-24/LEAD-035-CONCURRENCE.md` §3). Verifier's accurate wording
  for the shipping code (`d1290f66`, §4 of that file), verbatim:
  > With a keyless local model, the "don't use tools" detector is a fixed
  > phrase list: an unrecognised no-tool phrasing keeps the tools, so the
  > agent may still read data and propose a portfolio change (always held for
  > your review, never applied; under AUTO a watchlist or chart change does
  > apply) and can occasionally state a price it never fetched, while a data
  > request that qualifies a no-tool instruction after a comma or in reported
  > speech ("Don't use any tools, except price_data …", "No tools, other than
  > the price lookup …", "He says don't use tools, but …") still loses every
  > tool and the agent then usually states an invented price as if fetched.

  `DECISIONS_FOR_OPERATOR.md` §4.10 carries the operator's two options at
  rc1: (a) accept the residual as documented with the wording above, or (b)
  authorise one bounded round for the named guard on the rc2 line — the lead
  recommends (b).
- **R15-LEAD-037** (medium) — `blocked_tier4`, the batch-23 disposition
  verifier concurred:
  > With a keyless local model, a figure the agent states for a company whose
  > data call succeeded is not checked against that result at all, so it can
  > give an older bar's value from the same payload as the current price (2
  > of 18 live runs, 5-6% off) or a figure that appears nowhere in the
  > payload (1 of 18: ₹20,820 for a ₹2,082 stock).
- **R15-LEAD-038** (medium) — `blocked_tier4`, the batch-23 disposition
  verifier concurred:
  > With a keyless local model, when you tell the agent not to use tools and
  > ask for a portfolio change in the same message, it makes no call and
  > nothing is written or queued, but its reply can say the change was made
  > or staged for your review and can describe holdings that do not exist.

The fail-safe is **figure grounding by provenance**
(`sidecar/services/figure_grounding.py` + `agent_runtime._judge_clause`,
rules 1/2a/2b/2c/3 — the 2c fail-safe is gated on an errored tool call, which
is the structural gap LEAD-030/037 describe). The shipping no-tool-instruction
matcher is the closed cue list `_NO_TOOL_CUE` in
`sidecar/services/planner.py:139` (closed in batch-21, narrowed once more by
batch-24's closed-tail lookahead plus `(?<!said )(?<!say )`, merge `6778f892`
as of `4c6dfe8c`) — the narrowing shipped, but the entry it targets is still
`blocked_tier4`, not certified, per the LEAD-035 entry above. A portfolio write never
auto-applies regardless of this class: `data-write` changes always stage for
review, and AUTO skips review only for `panel`, `chart` and `watchlist`
(`types/proposed-change.ts:38-46`); there is no `audit_orders` table any more
(D81), so no order row can exist either way.

**Test-count claims elsewhere in this document are stale.** §1's "619
vitest, 942 pytest, §6.5 9/9" and the matching §7 row predate the D81 removal
(which deleted the §6.5 order-safety tests, `test_safety_end_to_end.py` and
`test_safety_router.py`, along with the feature) and Stage C batches 2–22
(which changed others; `DECISIONS_FOR_OPERATOR.md` §2.6 separately records a
`pnpm ci-local` baseline of "pytest 2507 passed / 1 skipped, vitest 1504 in
135 files, cargo 13" at an earlier R15 pause point, not re-verified at this
sha). This Stage D wave did not run the heavy test lanes (`pnpm ci-local`,
`pytest`, `vitest`) against this sha, so current pass counts are unverified
here.

<!-- VERIFY: current vitest/pytest/cargo-test pass counts at 4d89314 — run `pnpm ci-local` (or `pnpm test` / `cd sidecar && pytest`) and update §1 + §7 with the real numbers -->

---

## 0.x Trading removed (D81, 23 Sep 2026)

> **Everything below this notice that describes brokers, orders, the kill
> switch, or the append-only audit log is historical — it describes a
> capability that no longer exists.** D81 (operator Tier-4 sign-off, 23 Sep 2026) removed trading from the product permanently: no broker
> connectivity, order placement or simulated account exists anywhere —
> surfaces, agent tools, routes or docs. The kill switch and the append-only
> audit log went with it (their only purpose was gating and recording order
> placement). What survives untouched: the user's own tracked portfolio
> (manual holdings, cost bases, P&L on real prices, CSV export, notes,
> watchlists) and everything the agent does with it, riding the same
> proposed-changes gate as before. Full inventory, evidence and rationale:
> `docs/redesign/verification/r15/stage-c/REMOVAL_PLAN.md`. Current-state
> model for what remains: `docs/SAFETY_ARCHITECTURE.md`.

## 0. Foundation update (2026-05-31, branch `001-agent-native-redesign`)

> The body below is the **pre-redesign baseline** (2026-05-30). The redesign's
> **foundation window** has since landed on `001-agent-native-redesign` (not on
> `main`). It does **not** build the user-facing P1/P2/P3 phases, but it closes
> the documented copilot/catalog/runtime gaps the baseline records. Full detail +
> gate results: **`docs/redesign/FOUNDATION_BUILD_REPORT.md`** (not in tree at
> this sha — `git ls-tree -r` at `4d89314` has no match). Deltas that
> supersede statements below:
>
> - **Single capability catalog** (`sidecar/services/agent_tools/catalog.py`) is
>   now the one source of truth; `TOOL_SCHEMAS`, the custom-agent allow-list, and
>   the external MCP surface all derive from it (Constitution Principle II).
> - **§4 "~11 registered handlers unreachable" → CLOSED.** Every registered,
>   agent-intended handler has a schema (SC-006); 27 internal capabilities.
> - **§4 "Gemini multi-round likely broken" → FIXED** (tool name threaded onto
>   the tool-result message; SC-005).
> - **§11/§4 "custom-agent allow-list stale" → RECONCILED** to the catalog
>   (`KNOWN_TOOL_IDS` is derived; 0 unresolvable tools).
> - **§3.7 MCP "11 hand-maintained tools" → PROJECTED from the catalog** (26
>   tools; same names/schemas as the internal copilot; `readOnlyHint` from
>   `read_only`; standing SC-004 parity audit). A `news` tool now serves both
>   surfaces.
> - **§3.4 "manifest↔instance + `requiredHostVersion` checks documented but not
>   implemented" → IMPLEMENTED** (rejected at load, surfaced); **`PluginConfig`
>   secret resolution** is now keychain-backed (FR-054/SC-015).
> - **§1 "`shell:allow-open` probably denied" → GRANTED.**
> - **§2 boot-path `.expect()` panics → HARDENED** (port-0 sentinel + temp-dir
>   fallback; the app no longer panics with no window).
> - **§4 "shipped default routes to absent Ollama" → GATED**: a keyless provider
>   must be reachable before the first agent call (no silent failure).
>
> §6.5 LOCKED files + `types/plugin.ts` are **byte-for-byte untouched**; the §6.5
> audit stays 9/9.

---

## 0.5 Agent-native redesign — P1–P3 shipped (2026-05-31, branch `001-agent-native-redesign`)

> The user-facing redesign (P1/P2/P3) has now landed on the branch (not `main`).
> Full per-FR/SC accounting + gate results: **`docs/redesign/P1_P3_BUILD_REPORT.md`**
> (not in tree at this sha — `git ls-tree -r` at `4d89314` has no match).
> Deltas that supersede the baseline below:
>
> - **P1 — agent-centric experience (US1–US4).** A four-mode agent spine
>   (Ask / Edit-panel / Build / Delegate, ⌥1–4) with the agent as a co-equal
>   primary surface alongside the hand-driven cockpit. **Every agent-proposed
>   mutation routes through a diff/accept trust gate** (`src/store/proposed-changes.ts`)
>   — the write surface is the catalog's 19 host actions (`open_panel`/
>   `set_chart_symbol`/`add_to_watchlist`/the tracked-portfolio, note, screen and
>   layout writers/`set_region`; no order action exists, D81) — none auto-apply
>   under ASK autonomy (SC-003). Offer-both onboarding preserves the keyboard
>   cockpit.
> - **P2 — framework + visual + marketplace (US5–US7, US10).** Minimal-dark
>   "cold-instrument" shell (re-valued tokens; `chart-theme.ts` mirrors them),
>   teaching command palette + status chrome (FR-033). The **plugin marketplace
>   is the primary extensibility model**: data, panels, agents are all
>   install/enable/configure/remove entries (`src/lib/marketplace.ts`). First-party
>   pre-installed (yfinance + news keyless); the broker entries that shipped here
>   were removed with trading (D81). MCP-as-framework for external
>   tools (FR-025; static-import compiled-in plugins are governed here, genuinely-
>   external load is the stdio-MCP path).
> - **P3 — data + durable agents (US8/US9, FR-033–042).** The **provider-shaped
>   data registry** (`provider_registry.py`) resolves by standard model key +
>   preference order (not the asset-class chain); every result carries its serving
>   provider as provenance (FR-035/040). A **BYOK credentials hub** is the
>   marketplace config form rendered generically from each entry's
>   `credentialFields` (SC-007: 0 per-source UI) — news is now a first-party data
>   plugin (`plugins/vysted-news`) with an OPTIONAL NewsAPI key sent as the
>   `X-Vysted-Newsapi-Key` header from the keychain (FR-036). The granular
>   broker reads that shipped here (FR-042/SC-012) were removed with trading (D81).
>   **Durable Delegate runs** (`run_manager.py` + `runs_store.py` + `budget_guard.py`,
>   `routers/runs.py`) run detached, survive the launching connection, and are
>   bounded by a **BudgetGuard** (tokens/spend/wall/steps) whose first breach
>   aborts the run with a stated reason + resumable checkpoint (SC-008); the agents
>   rail shows live cost-so-far. **Cursor-grade settings + remappable keybindings**
>   (`src/store/settings.ts` + `keybindings.ts`) persist in the workspace blob
>   (FR-038/039/SC-011).
>
> `types/plugin.ts` remained **byte-for-byte untouched**. (The safety/broker models
> and the §6.5 order audit this window also left untouched were removed later with
> trading, D81.)

---

## 1. Executive summary — what the app IS today

- A **Tauri 2.x desktop terminal** (Rust core + Next.js 16 static-export
  frontend + Python 3.13 FastAPI sidecar + two bundled MCP subprocesses) that is
  **local-first and bring-your-own-keys**: no Vysted backend, no account, no
  telemetry. Everything lives under the OS app-data dir + the OS keychain.
- A **multi-panel cockpit** (dockview layout engine) with ~20 first-party
  modules: Chart (50 server-computed indicators + 10 drawing tools),
  Watchlist, News (RSS + optional NewsAPI, VADER sentiment), Portfolio (manual,
  SQLite), Equity Overview, plus Phase-6 analysis panels — Macro, SEC Filings,
  Earnings, Analyst Ratings, Screener, Quant (QuantLib) — and Phase-4/5
  Backtest, Node Editor (workflow), Agent Builder.
- A **real agentic AI copilot** (Phase 10): the tool-use loop in the sidecar is
  now live — adapters send provider-native `tools=` schemas, the model calls
  read/host-action tools, and the loop iterates up to 6 rounds. 13 first-party
  agents (a terminal-aware `copilot` router + 12 investor personas) plus
  user-authored custom agents.
- **BYOK across 7 LLM providers** (Anthropic, OpenAI, Gemini, Groq, Ollama,
  DeepSeek, xAI — five adapters; DeepSeek/xAI ride the OpenAI adapter via
  base-url override). Keys never persist; they ride the request and are read
  from the OS keychain on demand.
- **No broker layer.** Trading — broker connectivity, order placement, the
  simulated paper account, the kill switch, the append-only order audit log —
  was removed permanently (D81, 23 Sep 2026). See §0.x above. The prose below
  the removal notice describes the broker layer as it existed before D81;
  none of it is reachable today.
- A **plugin platform**: one serializable Tier-1 contract (`types/plugin.ts`,
  six capabilities) + a pure-TS runtime. **Five plugins are pre-installed and
  enabled by default** (`vysted-example`, `openbb-mcp`, `vysted-lenses`,
  `vysted-news`, `vysted-yfinance` — see §3.4; `tradesa-v2` no longer exists
  in the tree at this sha, superseding this section's earlier "three plugins,
  tradesa-v2 the only one with panels" description); the seven broker plugins
  that used to exist are also gone (D81). Plugins are still static-import
  compiled-in (no filesystem/marketplace loader yet); install/enable/
  configure/remove state is tracked per plugin.
- **Vysted speaks MCP on both sides**: as a _client_ it proxies two bundled MCP
  subprocesses (openbb-mcp fundamentals/macro, sec-edgar-mcp filings) into plain
  REST routes; as a _server_ it re-exposes 11 of its own endpoints as MCP tools
  for external clients (Claude Desktop / Code).
- **Ships unsigned, no release pipeline, version strings stuck at `0.8.0`**
  (still true at this sha — targets `0.9.0`; see §0.0 and `BLOCKERS.md`
  "R15 open items" for the open release-pipeline decisions)
  despite Phase 8/9/9.5/10 merged to `main`. The auto-updater is configured but
  produces no artifacts. Distribution today is "download the CI artifact."

---

## 2. Architecture at a glance

Three processes, one machine, loopback only. The Tauri Rust core owns the OS
surface (windowing, keychain, sidecar lifecycle, dynamic port assignment —
there is no kill-switch shortcut any more, D81). The Next.js frontend is a
static export served as files by the core — there is **no Node server at
runtime**. The Python FastAPI sidecar is the data + AI compute brain; it
binds `127.0.0.1` on an OS-assigned port. Two MCP subprocesses are separate
PyInstaller binaries the core spawns and supervises.

```
                       ┌──────────────────────────────────────────────┐
                       │  Tauri Rust core  (src-tauri/src/lib.rs)       │
   OS keychain ◀──────▶│  • keychain_set/get/delete                     │
   (keyring v3)        │  • pick_free_port → SidecarPort(u16)           │
                       │  • spawns + reaps 3 sidecars  • auto-updater   │
                       └───┬───────────────┬───────────────────┬────────┘
        get_sidecar_port,  │ Rust Command  │ Rust Command      │ shell.sidecar
        keychain_*,        │ (env handoff) │ (env handoff)     │ (--port,--data-dir)
        get_*_mcp_port     │               │                   │
   (Tauri IPC invoke)      ▼               ▼                   ▼
 ┌──────────────────┐  ┌──────────┐   ┌──────────────┐   ┌─────────────────────────┐
 │ Next.js frontend │  │ openbb-  │   │ sec-edgar-   │   │  Python FastAPI sidecar │
 │ (static export,  │  │ mcp      │   │ mcp          │   │  (sidecar/app.py)       │
 │  WKWebView)      │  │ subproc  │   │ subproc      │   │  ~107 HTTP routes,      │
 │  Zustand stores  │  │ :PORT    │   │ :PORT        │   │  1 WS, 1 MCP mount      │
 │  dockview panels │  └────▲─────┘   └──────▲───────┘   │                         │
 │  ChatSidebar     │       │ Streamable-HTTP│ (MCP)     │  binds 127.0.0.1:<port> │
 └────────┬─────────┘       └────────────────┴───────────┤  CORS *  (loopback)     │
          │  HTTP/SSE/WS over 127.0.0.1:<sidecar-port>    │                         │
          └──────────────────────────────────────────────▶  /quotes /history ...   │
                                                           │  /agents /llm/chat ... │
                                          external MCP ───▶│  /mcp  (FastMCP, 11    │
                                          (Claude Code)    │        tools, ASGI)    │
                                                           └─────────────────────────┘
```

**Layer model.** Frontend → sidecar HTTP only (no panel reads a provider API or
the keychain directly). Sidecar routers → `services/` providers (routers never
import a concrete provider; they go through `provider_registry` or a domain
module). Secrets cross the boundary **renderer-reads-keychain → secret in
request → sidecar holds in memory for the request only** — the sidecar
**cannot** read the OS keychain; only Rust can.

**Port assignment + handoff.** `pick_free_port()` binds `127.0.0.1:0`, reads
the OS-chosen port, releases it (a narrow unguarded TOCTTOU window), and stores
`SidecarPort(u16)`. The two MCP subprocesses are spawned first **on parallel
threads** and `join`ed before the main sidecar spawns, so their
`VYSTED_*_MCP_PORT` env vars are settled — the _entire_ MCP handshake is an env
var, no IPC negotiation. The frontend learns the sidecar port via
`get_sidecar_port` and `/health`-probes with backoff (120s deadline) before
declaring connected.

**Fragility flags at the boundary.** The main-sidecar spawn + `app_data_dir`
resolve + `create_dir_all` all `.expect()` → any failure **panics the app at
boot with no UI**. The MCP children, by contrast, never panic — they
`register_unavailable` (port 0) and degrade gracefully (openbb→yfinance,
sec→501). The `wait_for_port` main-sidecar readiness check is fire-and-forget
logging; nothing blocks the UI on readiness, so the frontend tolerates a
not-yet-up sidecar.

---

## 3. Subsystems

### 3.1 Desktop core & lifecycle (Tauri / Rust)

`src-tauri/src/main.rs` is a 5-line shim into `lib.rs` + four modules
(`diag_log.rs`, `keychain.rs`, `openbb_mcp.rs`, `sec_edgar_mcp.rs`) —
`kill_switch.rs` was deleted with trading (D81); no global-shortcut plugin is
registered any more.
Three Tauri plugins registered: `shell`, `updater`, `notification`. Single
window: 1280×832, dark theme, `dragDropEnabled: false` (load-bearing —
`true` installs an OS drag-drop handler that swallows in-webview HTML5 drag
events, which broke dockview tab reorder + node-editor palette drop on
macOS WKWebView too). `security.csp` is `null`.

**Keychain (`keychain.rs`).** Three async commands — `keychain_set` / `get`
(`NoEntry`→`Ok(None)`) / `delete` (idempotent) — service name
`"vysted-terminal"`, account = namespaced secret id. `keyring` v3 platform
features `["apple-native","windows-native","sync-secret-service","crypto-rust"]`
are load-bearing (default-features build silently no-ops `set_password`). The
roundtrip unit test **skips silently** with no usable credential store, so
headless-runner keychain behaviour is unverified by CI.

**Auto-updater — plumbed at config only, non-functional end-to-end.** Registered
in Rust, endpoint + minisign pubkey in `tauri.conf.json`, but
`createUpdaterArtifacts: false` and **no frontend code calls the updater** (zero
`.check()`/`downloadAndInstall` usages in `src/`). Flag as incomplete.

Rust commands exposed: `get_sidecar_port`, `keychain_set/get/delete`,
`get_openbb_mcp_port`, `get_sec_edgar_mcp_port` (0 = unavailable).
`RunEvent::Exit` reaps the main sidecar + both MCP children via `child.kill()`
— but PyInstaller `--onefile` re-execs a worker, so `kill()` on the
bootloader **may orphan the worker** (documented for Node smoke scripts;
unverified for the Rust path).

### 3.2 Sidecar app & endpoints (FastAPI)

One app built by `create_app()` in `sidecar/app.py`. **28 router modules,
~111 HTTP routes** (grep count of `@router.get/post/put/delete/patch(` across
`sidecar/routers/` at this sha; up from the earlier-draft "24 router modules,
~107 routes" — R15 added `data_sources`, `disclosures`, `resolve`, `runs`,
`search_status`, `search_tiers` and `system` among others, and removed
`tradesa_v2`, D81) + 1 WebSocket + 1 mounted MCP sub-app. CORS fully permissive
(`*`) — justified because the sidecar binds loopback only (but **the bind itself
is `main.py`/uvicorn's job, not enforced in `app.py`**). A single
`ProviderError → HTTP 502` exception handler; SSE (`text/event-stream`,
`data: {json}\n\n`) is the streaming convention for `/llm/chat`,
`/agents/{id}/invoke`, `/backtest/run`, `/workflow/run` (the encode helpers are
**duplicated verbatim** across four routers, two unused). `version="0.8.0"` is a
hardcoded literal at `app.py:329` — a separate source of truth that has drifted
before (`/health` now derives from `request.app.version`).

The v0.5.0/v0.6.0 runtime-extension aggregators (`app.py:191,205`) are called
at build time (`app.py:368,374`) but are **live no-op stubs** per their own
docstrings — dead scaffolding kept for per-release-stamp parity. Quotes/crypto
are thread-offloaded
(`asyncio.to_thread`); **`/history/{symbol}` is NOT** — it calls the blocking
provider synchronously on the request thread (a real event-loop-blocking
asymmetry). Caching is per-router, not centralized.

**Full endpoint inventory** (full mounted paths; "Service" = delegate):

| Method              | Path                                                                                       | Purpose                                          | Service / notes                                                            |
| ------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------ | -------------------------------------------------------------------------- |
| GET                 | `/health`                                                                                  | Liveness (Tauri polls on launch)                 | `provider_registry.active_providers()`; version from `request.app.version` |
| GET                 | `/quotes/{symbol}`                                                                         | Single latest quote                              | `provider_registry.get_quote` via `asyncio.to_thread`                      |
| GET                 | `/quotes`                                                                                  | Batch quotes (`?symbols=`)                       | fan-out `asyncio.gather`; failed symbols silently skipped                  |
| GET                 | `/history/{symbol}`                                                                        | OHLCV (`?timeframe=&range=&asset_class=`)        | `provider_registry.get_history` — **NOT thread-offloaded**                 |
| GET                 | `/crypto/exchanges`                                                                        | Supported ccxt exchanges                         | `ccxt_provider.SUPPORTED_EXCHANGES`                                        |
| GET                 | `/crypto/ticker`                                                                           | REST ticker (`?exchange=&symbol=`)               | `ccxt_provider.get_ticker` via thread                                      |
| GET                 | `/crypto/history`                                                                          | OHLCV (`?exchange=&symbol=&timeframe=`)          | `ccxt_provider.get_ohlcv` via thread                                       |
| WS                  | `/crypto/stream`                                                                           | Live ticker WebSocket                            | `ccxt_provider.watch_ticker` (ccxt.pro)                                    |
| GET                 | `/indicators`                                                                              | List supported indicator keys                    | declared before `/{symbol}` so it matches first                            |
| GET                 | `/indicators/{symbol}`                                                                     | Compute indicators (`?indicators=`)              | `indicators.compute`; unknown key → 400                                    |
| GET                 | `/fundamentals/{symbol}`                                                                   | Valuation ratios + profile                       | `provider_registry.get_fundamentals`                                       |
| GET                 | `/fundamentals/{symbol}/income` `/balance` `/cashflow`                                     | Financial statements                             | `provider_registry.get_*_statement`                                        |
| GET                 | `/fundamentals/{symbol}/ratings`                                                           | Aggregated analyst rating                        | `provider_registry.get_analyst_rating`                                     |
| GET                 | `/fundamentals/{symbol}/ratings/history` `/price-target-history` `/individual`             | Extended ratings                                 | `analyst_ratings_extended` + `data_cache` (TTL 6h)                         |
| GET                 | `/news`                                                                                    | RSS+NewsAPI news, VADER sentiment, symbol-tagged | `news_provider.fetch_news` + `sentiment.score_text`                        |
| GET                 | `/macro/search` `/catalog`                                                                 | Catalog search / featured                        | `macro_router` (FRED/ECB/IMF/world-bank)                                   |
| GET                 | `/macro/{series_id}`                                                                       | Macro series (`?provider=`)                      | new dispatcher (`MacroSeriesExtended`) or legacy openbb-mcp path           |
| GET                 | `/sec/status`                                                                              | sec-edgar-mcp readiness                          | only `/sec` route that works when subprocess down                          |
| GET                 | `/sec/filings/search` `/filings` `/filings/{accession}[/sections]` `/insider/{identifier}` | EDGAR filings + insider                          | `sec_filings_provider`; **501** when subprocess unbound                    |
| GET                 | `/earnings/upcoming` `/{symbol}/history` `/surprises` `/estimates`                         | Earnings calendar/history                        | `earnings_provider` + `data_cache` (6h/24h TTLs)                           |
| POST                | `/screener/run`                                                                            | Run screener (`ScreenerRequest`)                 | `screener.run_screener`; universe failure → 502, unknown → 400             |
| GET                 | `/screener/universe`                                                                       | Resolve universe (`?id=`)                        | `screener.resolve_universe`; `custom` → 400                                |
| GET/POST/PUT/DELETE | `/portfolio/positions[/{id}]`                                                              | Manual positions CRUD                            | `portfolio_db` (SQLite); 201/204/404                                       |
| POST                | `/quant/option/price` `/option/greeks` `/bond/price` `/yield-curve`                        | QuantLib pricing                                 | `services.quant.*`; `ValueError` → 400                                     |
| POST                | `/backtest/run`                                                                            | SSE `BacktestRunEvent`                           | `backtest_engine.run_backtest` + `bar_loader`; cached                      |
| GET                 | `/backtest/strategies` `/runs` `/runs/{id}`                                                | Strategy + run catalog                           | in-memory `backtest_store`                                                 |
| POST                | `/workflow/run`                                                                            | SSE `WorkflowRunEvent`                           | `workflow_engine.run_workflow`                                             |
| POST/GET/DELETE     | `/workflow/save` `/saved[/{id}]`                                                           | Workflow persistence                             | `workflow_store`                                                           |
| GET                 | `/agents`                                                                                  | List first-party agents                          | `agent_runtime.list_agents()` (custom NOT merged)                          |
| POST                | `/agents/{agent_id}/invoke`                                                                | SSE `LLMStreamEvent`                             | `agent_runtime.invoke_agent`; 404 if unknown                               |
| GET/POST/PUT/DELETE | `/custom-agents[/{id:path}]`                                                               | Custom-agent CRUD                                | `agents_store` (SQLite); 409 collision; `custom:` prefix enforced          |
| GET                 | `/llm/providers`                                                                           | BYOK provider catalog                            | `services.llm.list_provider_info`                                          |
| POST                | `/llm/keys/validate`                                                                       | Probe a key                                      | transport error → `{ok:false}` (never raises)                              |
| POST                | `/llm/chat`                                                                                | SSE `LLMStreamEvent`                             | `adapter.stream_chat`; unknown provider → 400                              |
| —                   | _(none — the broker and safety routes were removed, D81, 23 Sep 2026)_                     | No broker, order or kill-switch route exists     | see §0.x                                                                   |
| —                   | _(none — `tradesa-v2` no longer exists at this sha)_                                       | No Tradesa/bot-mirror route exists                | the plugin dir was replaced by `vysted-lenses`/`vysted-news`/`vysted-yfinance`, see §3.4 |
| GET/POST/DELETE     | `/plugins[/{id}/config]`                                                                   | Persisted plugin configs                         | `plugins_store` (SQLite)                                                   |
| GET/POST/DELETE     | `/workspace[/{name}]`                                                                      | Workspace blob persistence                       | `workspace_store`; opaque JSON                                             |
| GET                 | `/mcp/status` `/openbb-mcp/status`                                                         | Vysted MCP + openbb-mcp readiness                | `mcp_server.tool_count()` / `openbb_mcp_provider.status()`                 |
| (JSON-RPC)          | `/mcp/`                                                                                    | FastMCP Streamable-HTTP transport                | mounted sub-app for external MCP clients                                   |

### 3.3 Market-data & analytics services

All under `sidecar/services/`. `provider_registry.py` resolves by **standard
model key** (`quote`, `ohlcv`, `fundamentals`, `income_statement`, …), walking
installed providers in **preference order** until one succeeds — `asset_class`
is a resolution _hint_ layered on top, not the dispatch switch (FR-035/053; a
`ProviderDeclaration` table — id, model-keys served, preference rank,
credential/availability gate, region gate — is the single source of truth, and
`active_providers()` at `/health` derives from it rather than being
hand-maintained). `get_quote`/`get_history` stay **synchronous** (ccxt/yfinance
providers, wrapped in `asyncio.to_thread`); openbb-backed methods stay `async`
— two resolvers (sync/async) share one declaration table and the same
preference-order fallthrough. For region `IN`, three keyless providers
outrank the broad default on `quote`/`ohlcv`: `nse_direct` (rank 15,
exchange-direct EOD, the anti-bot curl_cffi lane), `nse` (rank 20,
jugaad-data), `bse` (rank 25, the micro-cap EOD default for groups NSE never
listed) — IN fundamentals still fall through to yfinance (no region-scoped
fundamentals provider exists).

- **`yfinance_provider.py`** — the no-key default for equities, region-gated:
  for `IN` requests `nse_direct`/`nse`/`bse` (ranks 15/20/25) all rank ahead
  of it for `quote`/`ohlcv`, so it only serves as the IN fallback (fundamentals
  and any other region still hit it first). Load-bearing details: `BRK.B`→
  `BRK-B` rewrite; **dividend-yield divided by 100** (yfinance 1.3.0 returns a
  percentage, the contract wants a fraction — a silent corruption risk if
  upstream changes); aggregate rating reads only the single most-recent
  recommendation row.
- **`ccxt_provider.py`** — ccxt (sync REST) + ccxt.pro (async WS). Exchanges:
  bybit, binance, kraken, coinbase. Backs `/crypto/*`.
- **`openbb_mcp_provider.py`** (conditional) — richer fundamentals/macro via the
  openbb-mcp subprocess over Streamable-HTTP. Port 0/unset → `is_available()`
  False → registry falls back. **Whether the binary ships in a given build is
  unverified from service code alone.**
- **`news_provider.py`** — RSS (Yahoo, MarketWatch, per-symbol Yahoo; always on)
  - NewsAPI (BYOK `NEWSAPI_KEY` only). Shared pooled `httpx.AsyncClient` (the
    cold-start TLS-cascade fix). No caching — re-fetches live every request.
- **`sentiment.py`** — VADER lexicon (a deliberate Tier-3 choice: FinBERT would
  drag `torch` into the bundle). Coarse, "at a glance," **not finance-grade** —
  flagged honestly in the docstring.
- **`earnings_provider.py`** — yfinance calendar/estimates/surprises. Fiscal
  period **inferred from calendar month** (best-effort, UI-only); EPS stddev is
  an approximation `(high−low)/4`. Router-side caching.
- **`analyst_ratings_extended.py`** — yfinance has **no individual-analyst
  names** (firm used as label), **no real price-target timeline** (often a single
  synthetic "Consensus" anchor row). Honest degeneracy baked in.
- **`sec_filings_provider.py`** (conditional) — sec-edgar-mcp subprocess. Narrow
  form coverage (10-K/10-Q/8-K/DEF 14A/3/4/5); extractors heavily defensive
  against upstream shape drift. Caches via `data_cache`.
- **`screener.py` + `screener_universes/` + `screener_universe_india.py`** —
  fan-out filter engine. Universes: `sp500` (full S&P 500 — 503 symbols, a
  static snapshot dated 2026-09-24), `nifty50` (50), `crypto-top50` (50,
  reseeded from the bundled snapshot on cache expiry — a live "refresh from
  ccxt" worker still does **not exist**), `nse-all` (every NSE master row as
  `SYMBOL.NS` — 3,506 symbols: EQ 2,584 + ETF 351 + SM 571, SM = NSE Emerge),
  `bse-all` (BSE master rows with STATUS == "Active" as `SYMBOL.BO` — 5,042
  symbols), `india-all` (the union of the two, NSE listing preferred when a
  symbol is dual-listed — 5,891 symbols), `custom`. The three India
  universes resolve from the same bundled resolver-master JSON the symbol
  resolver reads (offline, deterministic). Criteria support **nested AND/OR**
  via `CriterionGroup` (`models/screener.py`, `combinator: "and"|"or"`) — OR-
  grouping is no longer reserved/unimplemented.
- **`services/macro/`** — four in-process providers (FRED requires
  `FRED_API_KEY`; ECB/IMF/world-bank keyless). Hand-curated `_FEATURED` catalogs;
  full catalog browsing deferred. `fred-mcp-server` turned out to be Node.js →
  pivoted to in-process `fredapi`.
- **`services/quant/`** — in-process QuantLib (Tier-3: quality over bundle size).
  Options (BS/binomial/MC; **MC Greeks not computed**), Greeks, bonds, yield
  curve (synthetic `VYSTED-IBOR`, not SOFR/ESTR). `monte_carlo.py`
  (Asian/barrier) is **not wired to any endpoint**.
- **`indicators.py`** — pure pandas/numpy, **49 indicators + volume_profile**
  (50). Frontend never computes an indicator; the sidecar does.
- **`data_cache.py`** — generic SQLite TTL cache, **TTL-per-`get`**, stale rows
  **not auto-evicted**. Notably uncached: news, quotes/history/equity-fundamentals
  through the registry, all quant pricing.
- **`bar_loader.py`** — daily-bar loader for the backtest engine; per-symbol
  `ProviderError` degrades to empty series.

**Documented-but-unimplemented "richer later" hooks:** openbb-mcp
earnings/analyst enrichment, ccxt crypto-top50 refresh, individual analyst
names/accuracy, real price-target timelines, full SEC form coverage, full macro
catalog, surface vol/yield curves, HTTP wiring for path-dependent MC.

### 3.4 Plugin system

`types/plugin.ts` (**Tier-1, highest blast radius**) — a deliberately
framework-free serializable contract: four fixed sections (identity, lifecycle,
six-boolean `capabilities`, optional getters) + six capabilities
(`contributesData/Panels/Commands/Agents/Nodes`, `supportsControlPlane`).
`PanelSpec.component` is a **string id** resolved host-side (keeps the contract
serializable). Negotiation checks the _flag_, not the method.

`PluginRuntime` (`src/lib/plugin-runtime.ts`, pure TS): discover → loadPlugin
(honors persisted `enabled:false`) → collect contributions through
`callIfFlagged` (a buggy getter emits `errored`, returns `[]`) → 30s health
poll. **Honesty flag:** `PLUGIN_DEVELOPMENT.md` claims the runtime asserts
manifest↔instance id/version match + checks `requiredHostVersion` — **none of
those checks exist** in the code. Aspirational doc.

**`BUNDLED_PLUGINS`/`PLUGIN_COMPANIONS` are gone from the code at this sha —
this whole model changed since an earlier draft of this section, and CLAUDE.md
+ `PLUGIN_DEVELOPMENT.md` are now stale describing it (filed as
`R15-DOCS-015`, `blocked_tier4`, `DECISIONS_FOR_OPERATOR.md` §2.20).**
`src/lib/plugin-bootstrap.ts` no longer defines either symbol (confirmed by
grep at this sha). The catalog is now `CATALOG_ROWS: CatalogRow[]` in
`src/lib/marketplace.ts:59` — one row per plugin, each pairing a
`MarketplaceEntry` (name/category/description/icon/`preinstalled`/
`credentialFields`) with the `DiscoveredPlugin` (manifest + instance).
`plugin-bootstrap.ts` derives panels/commands per plugin instance from the
runtime (`moduleForPlugin`, `:134`) instead of a static companion map. Five
plugins are registered, all `preinstalled: true` (populated on first run):

| Bundled plugin (`pluginId`) | Type              | Capabilities (true)            | Status                                                                                                       |
| ---------------------------- | ----------------- | ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `vysted-yfinance`            | data-source        | data                            | The no-key equity+fundamentals default. `plugins/yfinance/`.                                                                      |
| `openbb-mcp`                 | data-source        | data                            | Declares DataSources; `healthCheck` probes `/openbb-mcp/status`. Data actually flows through sidecar routes, not the plugin.      |
| `vysted-lenses`               | agent-collection   | agents                          | **Contributes a real agent** — the "Quant Tutor" persona (`plugins/vysted-lenses/index.ts`), merged into the persona roster via `collectAgents()`; a genuinely runnable plugin-sourced agent, gated by the same §6.5-successor host-action enforcement as any first-party agent. |
| `vysted-news`                | data-source        | data                            | RSS keyless + optional BYOK NewsAPI key (`newsapi_key`, sent as `X-Vysted-Newsapi-Key`); `plugins/vysted-news/`.                   |
| `vysted-example`             | data-source        | data, commands, control-plane   | Pedagogical; proves contract end-to-end. Working.                                                                                  |

**`tradesa-v2` (the read-only Tradesa bot-mirror wrapper, 7 panels, the
`/tradesa-v2/*` REST proxy) no longer exists in the tree at this sha** —
`plugins/tradesa-v2/`, `sidecar/routers/tradesa_v2.py` and every
tradesa-specific service/model are gone (confirmed: `git ls-tree`/
`git cat-file -e` both fail for these paths at `4d89314`). **No bundled
plugin contributes panels any more** — all five capability blocks above have
`contributesPanels: false`; the companion-map mechanism this section used to
describe (`tradesa-v2` as "the only bundled plugin exercising panels") has no
live consumer.

**`contributesAgents` is now exercised** (`vysted-lenses`'s Quant Tutor) —
this closes the gap an earlier draft of this section flagged.
`contributesNodes` remains **unexercised** by any bundled plugin.

### 3.5 Broker layer — removed (D81, 23 Sep 2026)

No broker layer exists. See §0.x. The Kite Connect OAuth read-only path,
the paper-mode synthetic account, the granular reads (`positions`/`holdings`/
`margins`), and the Kite static-IP UX this section used to describe are all
deleted, not merely unreachable.

### 3.6 Safety architecture — now the agent-write model (D81, 23 Sep 2026)

The execution-safety layer this section used to describe (the eight
BLUEPRINT §6.5 order non-negotiables, `test_safety_end_to_end.py`) existed
only to gate broker order placement and was removed with the feature. What
remains — the proposed-changes trust gate over the 19 surviving host actions
— is documented in `docs/SAFETY_ARCHITECTURE.md`, current as of this
removal. `sidecar/tests/test_no_trading_surface.py` pins that no order,
broker or simulated-account path exists anywhere.

### 3.7 MCP integration (both sides, both real)

**As client:** two MCP subprocesses (`openbb-mcp-server==1.4.0` + 6 OpenBB
extensions; `sec-edgar-mcp==1.0.8`), each its own PyInstaller binary with a
**separate venv** (openbb-core strict-pins `fastapi<0.129`/`uvicorn<0.41`,
incompatible with the main sidecar's 0.136/0.46), spawned by Rust
`app.shell().sidecar(...)` (NOT `subprocess.Popen` — the v0.4.0 fix for a Windows
`_MEIPASS`+anyio+handle-inheritance deadlock). Each `main.py` is a thin launcher:
parse `--port`, start a raw-`os.read` stdin-EOF watchdog, rewrite `sys.argv` to
`--transport streamable-http`, delegate to the upstream `main()`. The provider
seam is a **REST proxy, not MCP passthrough** — `openbb_mcp_provider` /
`sec_filings_provider` expose the same surface a yfinance provider would, so the
registry swap is one line. `mcp_client.py` (lazy session, reconnect-on-error,
generation-counter race guard) supports http + stdio, but **only http has a real
consumer** (stdio is dead code reserved for filesystem plugins).

**As server:** `mcp_server.py` is a real FastMCP 3.x server mounted at `/mcp`
over Streamable-HTTP. **11 tools** (`get_quote/history/fundamentals/news/
macro_series`, `list_agents`, `invoke_agent` — collapses the SSE stream into one
unary string, `list_workspaces`, `get_workspace`, `run_workflow`,
`list_workflows`). **Architecture: protocol adapter, zero logic duplication** —
each tool is a thin shim calling the sidecar's own HTTP endpoint via an
in-process `httpx.ASGITransport` bound by `bind_app(app)`. Every tool returns a
`dict` (FastMCP rejects bare lists). A subtle lifespan invariant:
`get_streamable_http_app()` is cached because the SAME instance must drive both
the mount and the parent lifespan, or every request raises "Task group is not
initialized." No authentication (loopback only, by design); external-client
config is a manual copy-paste flow (Claude Desktop needs `mcp-remote`).

**Fragilities:** subprocess cold-bind is the dominant one — ~34s isolated on
M1, worse under concurrent `_MEI*` extraction disk-I/O contention; budget raised
to `MCP_PORT_WAIT_SECS=45 × 2 = 90s`; the true fix (`--onedir`) is deferred. Doc
drift: protocol version (`2025-06-18` code vs `2025-11-25` in `types/mcp.ts`),
tool count (`MCP_INTEGRATION.md` says 9, code ships 11). No `/sec-edgar-mcp/status`
route (asymmetric with openbb). The smoke-test gate now TCP-probes bind but does
**not** verify endpoint data (`/agents` count > 0).

### 3.8 Frontend shell, layout & state

Next.js 16 App Router **static export** (`output:"export"`), served as files by
the core — no Node server. SSR-safety rests on one invariant: **`PanelHost`
returns a loading placeholder until modules register** (dockview is not
SSR-safe; module registration runs in a `page.tsx` `useEffect` that never fires
during prerender). **Dark theme only** — `<html className="dark">` hard-coded, no
toggle (light theme is a Tier-4 BLOCKER until v1.1).

**dockview** is the chosen layout engine (Tier-3). A `VystedModule` bundles
`panels`/`commands`/`panelComponents`/`commandHandlers`; `useModulesStore` holds
modules + an `enabled` map; `PanelHost` builds the `componentId → Component` map
and mounts `DockviewReact`. **`collectPanelComponents` does a flat
`Object.assign` — two modules with the same component id silently collide
(last wins), no guard.** Default layout: Chart over Equity Overview (left),
Watchlist/News/Portfolio stacking right, AI Assistant far-right column.

**20 first-party modules** hard-listed in `src/modules/index.ts` (edit-once-
per-phase so parallel work doesn't contend). Plugins bridge into the _same_
registry via `moduleForPlugin` (id `plugin:<id>`) — no second registry.

**Workspace blob persistence:** `SerializedWorkspace` round-trips layout +
`enabledModules` + `chartDrawings?` + `defaultProviderId?` + `watchlist?`
through `/workspace` as one opaque blob (sidecar stores it verbatim, never
validates). Open index signature → new fields need no sidecar change but
**require editing four call-sites** (interface, `serializeWorkspace`,
`deserializeWorkspace` with an older-blob guard, `autosaveLayout`) — duplicated
payload assembly, kept in lockstep by hand. Restore is defensive: an
unknown-component guard skips to default rather than letting `fromJSON` throw;
`enabled` map rolls back on a throwing restore; disposed-api guards for
StrictMode/HMR. Autosave debounced 1500ms; **failures silently swallowed**.

**Theme tokens — names are historical, not literal:** `amber-*` renders CORAL
(`#d97757`), `charcoal-*` renders ESPRESSO, `brass-*`/`sage-*` are warm
NEUTRALS. Names kept so 80+ files reskin by re-valuing `tokens.css` alone.
**Canvas can't read CSS vars** → the chart palette is hand-mirrored in
`src/lib/chart-theme.ts`; a reskin must change **both** or canvas drifts (3
values, incl. a forbidden cyan, had silently drifted pre-Phase-10).

**Zustand stores:** workspace, modules, app (sidecar URL+status —
**computed but not surfaced** in the header), symbols (watchlist, single source
of truth, default 6 symbols SPY/QQQ/BTC-USDT/ETH-USDT/NVDA/AAPL — differs from
the canonical 7-symbol visual protocol), command-palette, panel-context
(pub/sub bus feeding the chat sidebar). cmd+K is substring match only — no
fuzzy, no ranking, no recents.

### 3.9 Panels — market (Chart / Equity Overview / Watchlist / News / Portfolio / Screener)

| Module          | Panel                          | Singleton        | Endpoints                                                       |
| --------------- | ------------------------------ | ---------------- | --------------------------------------------------------------- |
| chart           | `ChartPanel.tsx` (~1150 lines) | no (multi-chart) | `/history/{symbol}`, `/indicators/{symbol}`                     |
| equity-overview | `EquityOverviewPanel.tsx`      | yes              | `/quotes`, `/fundamentals` + `/income/balance/cashflow/ratings` |
| watchlist       | `WatchlistPanel.tsx`           | yes              | `/quotes` (batch), `/crypto/ticker` (per crypto)                |
| news            | `NewsFeedPanel.tsx`            | yes              | `/news`                                                         |
| portfolio       | `PortfolioPanel.tsx`           | yes              | `/portfolio/positions` CRUD, `/quotes/{symbol}`                 |
| screener        | `ScreenerPanel.tsx`            | yes              | `/screener/run`, `/screener/universe`                           |

**Chart** is the heaviest panel: `lightweight-charts` candlesticks, 8-step
timeframe, 50-indicator multi-select (server-computed; frontend never computes
one), 10 drawing tools (`ISeriesPrimitive`, click-to-create, serializable
`DrawingSpec` per-panel store), comparison overlay (failures silently swallowed),
three cross-chart sync slices (crosshair/range/symbol). **isTrusted limitation:**
drawing/pan/zoom gestures are gated by lightweight-charts on trusted events —
chrome-devtools MCP synthesised events are rejected, so canvas-interactive
features **cannot be visually regression-tested** (only data models + toolbar
wiring). Equity Overview fans out 6 parallel calls with graceful partial
failure. Watchlist polls 5s. News auto-retries with exponential backoff
(self-heals the ~30s cold-boot sidecar bind). Portfolio computes P&L
client-side; honest edge cases (`null` for zero-cost-basis, divides by
resolved-cost). Screener: client-side sort with null-last pinning.

### 3.10 Panels — analysis (Macro / SEC / Earnings / Analyst / Quant / Backtest / Node Editor / Agent Builder / Chat / Integrations)

All data stores call `sidecarGet` (GET) or a `fetch`-based POST/SSE consumer;
none use `localStorage`. Notable surfaces:

- **Backtest** — schema-driven params form from `GET /backtest/strategies`; SSE
  run stream; "Open in Strategy Critic" drops a `/agent strategy_critic` line
  into the chat composer (BLUEPRINT Use Case 2, end-to-end unverified).
- **Node Editor** — `@xyflow/react` 12.x; HTML5 DnD palette→canvas (why
  `dragDropEnabled:false` is required); 10 built-in nodes unioned with plugin
  nodes; config schema lives host-side (NodeSpec stays locked/serializable). A
  **second workflow consumer** (`store/workflow.ts`) exists with a
  desktop-notification-intent slice that has **no found dispatcher** — treat as
  unwired.
- **Agent Builder** — sidecar-backed custom-agent CRUD; `custom:` prefix
  enforced.
- **Chat sidebar** (`ChatSidebar.tsx`) — the most cross-cutting surface (6+
  stores). Default agent `copilot`; bare text routes to it; clickable persona
  chip roster; `/ask` raw escape hatch. `executeHostAction` maps copilot tool
  calls to `ProposedChange` entries (`set_chart_symbol`/`open_panel`/
  `add_to_watchlist` and the rest of `HOST_ACTION_NAMES`, `src/lib/
host-actions.ts` — 19 host actions total), staged through the diff/accept
  review bar (§5); the `panel`/`chart`/`watchlist` kinds apply without a
  per-action confirmation under AUTO autonomy (`AUTO_APPLIED_KINDS`,
  `types/proposed-change.ts`) — `data-write`/`settings` always wait — there is
  no order kind any more (D81). BYOK key resolved from the **agent's**
  `defaultProvider` (not the UI default), read from keychain on demand.
  `defaultModelFor` **hard-codes one model per provider** (may drift).
- **Integrations** (`ConnectCard.tsx`) — no `index.ts`, rendered inside
  `SettingsPanel`; one dialog drives any `IntegrationSpec`. There is no broker
  integration any more (D81); the surviving entries are data/agent plugins.

### 3.11 Agent personas

13 first-party agents under `sidecar/agents/*.json` (read-only, discovered at
import, validated against `_schema.json` draft-07, count hard-asserted by three
tests). 12 investor personas (Buffett, Graham, Lynch, Munger, Marks, Klarman,
Dalio, Druckenmiller, Soros, Researcher, Portfolio Advisor, Strategy Critic) +
the Phase-10 `copilot` router. Each persona's prompt is 1.5–4 KB; only `copilot`
(ollama/`qwen2.5:7b`) and `researcher` (openai) deviate from anthropic default.
The `sidecar/agents/` dir is bundled via an explicit `--add-data` (it has no
`__init__.py`; was silently dropped for 3 releases — Phase 8 finding).

**Plugin-contributed agents (new since an earlier draft of this section):**
the `vysted-lenses` plugin's `contributesAgents: true` capability adds a 14th
persona, "Quant Tutor" (`plugins/vysted-lenses/index.ts`), merged into the
roster via the plugin runtime's `collectAgents()` — genuinely runnable, its
`tools` allow-list gated the same as any first-party agent (§3.4). The 13-agent
count above is specifically the `sidecar/agents/*.json` roster and stays
accurate as that figure; the user-visible persona roster is 13 + this one
plugin agent at this sha.

**Custom agents:** CRUD'd via `/custom-agents`, SQLite store, `custom:` prefix
required. **Caveat — the custom-agent tool allow-list is stale + out of sync:**
`KNOWN_TOOL_IDS` lists only 5 tools (`price_data, fundamentals, news,
backtest_summary, macro`), but first-party agents bypass the allow-list and
legitimately use tools (`screener_run`, `set_chart_symbol`) that **a custom
agent cannot select** (`broker_portfolio`, this section's third example, is
gone — D81). Worse, `news`/`macro` pass custom validation but **are not keys
in `TOOL_SCHEMAS`** — so a custom agent allow-listing them never resolves
the tool. A real, unfixed inconsistency.

### 3.12 Build, CI & distribution

Three PyInstaller `--onefile` sidecars built from a clean checkout (no binary
committed): `vysted-sidecar` (89 MB), `vysted-openbb-mcp-sidecar` (49 MB),
`vysted-sec-edgar-mcp-sidecar` (81 MB). Bundle-inclusion flags
(`--hidden-import` / `--copy-metadata` / `--collect-all` / `--collect-data` /
`--add-data`) are load-bearing — each maps to a real shipped-and-crashed
regression. Ensure scripts are **staleness-aware** (binary older than its source
auto-rebuilds; editing the build recipe invalidates the binary).

**Two standing pre-tag gates:** `pnpm ci-local` (mirrors CI byte-for-byte:
install → ensure-all-sidecars → eslint → prettier → tsc → cargo fmt → clippy -D
→ ruff 0.15.12 → vitest → cargo test → pytest) **and**
`scripts/smoke-test-sidecars.mjs` (spawns each built binary, polls `/health`,
TCP-probes MCP bind, tree-kills on exit — catches the `PackageNotFoundError`-at-
startup class that `cargo test` can't, since it never runs the binary).
`ci-local` does **not** run the smoke test or `tauri build`.

**Distribution is partly stubbed:** bundles built **unsigned** (no signing/
notarization anywhere → Gatekeeper/SmartScreen will trip); auto-updater
configured but `createUpdaterArtifacts:false` → no signed artifacts/`latest.json`;
**no release/publish workflow exists** (CI only runs on push/PR + uploads
ephemeral artifacts). **Version sources stuck at `0.8.0`** (`package.json`,
`Cargo.toml`, `tauri.conf.json`, `app.py`, `HOST_VERSION`) despite Phase
8/9/9.5/10 merged, D81 and Stage C batches 2-22 — this R15 candidate targets
`0.9.0` (§0.0); `0.9.0` lands when the prepared version branch merges, right
after the `r15-rc1` tag — confirmed at the tag.

### 3.13 Persistence & BYOK (see §6 for the consolidated model)

---

## 4. The copilot today (load-bearing for the redesign)

The copilot is an **agentic tool-use loop running entirely in the sidecar**,
invoked over SSE. This is the Phase-10 unlock: the loop in
`agent_runtime.invoke_agent` already existed but was **dead** — no adapter ever
sent a `tools=` schema, so no model ever called a tool. Phase 10 made it live.

**The loop (`agent_runtime.py:341`).** Resolve spec → resolve provider/model
(override → agent default → hardcoded per-provider fallback table) → coerce
history (last 10 turns) → `tool_ids = list(spec.tools)` → build per-invocation
local tools → compose `[system, context preamble, …history, user]` → `while
True`: stream from `adapter.stream_chat(messages, model, api_key,
tool_ids=tool_ids)`; yield `tool_use` events to the UI; on `done` with tools
fired and `rounds < 6` swallow the terminator and loop; reconstruct the
assistant tool-call turn, dispatch every pending tool, append one `role="tool"`
result per call, increment, loop. **Hard cap `_MAX_TOOL_ROUNDS = 6.`** Errors
never crash the stream — a structured "tool not available" surfaces and the
model recovers.

**The keystone — `agent_tools/schemas.py`.** `TOOL_SCHEMAS` is one
provider-neutral `{tool_id: {description, input_schema}}` catalog. Three
serialisers project it natively: `anthropic_tools`, `openai_tools` (also Groq /
Ollama / DeepSeek / xAI), `gemini_tools`. **Every adapter MUST
`kwargs.pop("tool_ids")`** — forwarding it to the SDK breaks the call (confirmed
all five pop it). **To add a tool you need all three:** a registered handler, a
`TOOL_SCHEMAS` entry, and the id in some agent's allow-list — or it is invisible
to every model.

**Context injection (terminal awareness).** The frontend captures a structured
`__terminal__` snapshot (focused symbol/timeframe/indicators, watchlist,
portfolio, open panels) and sends it on agent calls. Two paths surface it: a
terse system preamble (`_render_terminal_preamble`, with the deixis line —
"when the user says 'this'/'it', they mean {focusedSymbol}… never invent figures
— call a tool") and two on-demand pull tools (`get_terminal_state`,
`get_portfolio`).

**Host-action tools drive the terminal.** `open_panel`, `set_chart_symbol`,
`add_to_watchlist` and the rest of `HOST_ACTION_NAMES` (`src/lib/
host-actions.ts` — 19 host actions total) are per-invocation closures that
return a _synthetic_ success — the **real UI work happens frontend-side** in
`ChatSidebar.executeHostAction`, dispatched off the streamed `tool_use` event
as a staged `ProposedChange` (not the synthetic result; the `host_action`
payload on the wire is effectively dead today). The change waits in the
diff/accept review bar (§5) unless its kind is one of `AUTO_APPLIED_KINDS`
(`panel`/`chart`/`watchlist`, `types/proposed-change.ts`) under AUTO
autonomy — `data-write`/`settings` always wait. There is no order host action
any more — no broker connection exists to place one against (D81).

**Personas.** 13 first-party agents (§3.11). `copilot` is the terminal-aware
default whose allow-list is the broadest (14 tool ids incl. all host actions).

**Provider/model (BYOK).** `get_provider` is a synchronous stateless factory; 7
provider ids → 5 adapters (DeepSeek/xAI ride OpenAI via base-url override). Keys
never held on the adapter — passed per call, read frontend-side from the
keychain.

**The `TOOL_SCHEMAS` catalog — but only ~10 of the ~40+ registered
capabilities are reachable this way** (the current catalog size and the
27-tool reachability figure are tracked in `sidecar/services/agent_tools/
catalog.py`, the single source of truth per §0). No `broker_portfolio` or
`propose_order` tool exists any more (D81):

| Tool id                                                                                                                                                                                                                        | What it does                                                         | Reachable by an agent?                                      |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------- | ----------------------------------------------------------- |
| `price_data`                                                                                                                                                                                                                   | ≤90 OHLCV bars + latest quote                                        | yes                                                         |
| `fundamentals`                                                                                                                                                                                                                 | valuation ratios + profile                                           | yes                                                         |
| `backtest_summary`                                                                                                                                                                                                             | digest a cached BacktestResult                                       | yes                                                         |
| `screener_run`                                                                                                                                                                                                                 | run the screener                                                     | yes                                                         |
| `macro_series`                                                                                                                                                                                                                 | one macro series (schema omits required `provider`; handler rejects) | yes                                                         |
| `earnings_history`                                                                                                                                                                                                             | past earnings (≤12 quarters)                                         | yes                                                         |
| `analyst_history`                                                                                                                                                                                                              | rating-change history                                                | yes                                                         |
| `sec_filings_list`                                                                                                                                                                                                             | filings index (degrades if sec-edgar down)                           | yes                                                         |
| `get_terminal_state` / `get_portfolio`                                                                                                                                                                                         | snapshot reads                                                       | yes (runtime-resolved)                                      |
| `open_panel` / `set_chart_symbol` / `add_to_watchlist` / the tracked-portfolio, note, screen and layout writers / `set_region`                                                                                                 | host actions (19 total)                                              | yes (runtime-resolved)                                      |
| `macro_search`, `earnings_upcoming`, `earnings_estimates`, `analyst_individual`, `price_target_history`, `sec_filing_content`, `sec_insider_transactions`, `price_option`, `compute_greeks`, `price_bond`, `yield_curve_value` | registered handlers, callable over REST                              | **NO — no `TOOL_SCHEMAS` entry → invisible to every model** |

**Material catalog gap:** ~11 registered handlers (the entire QuantLib quartet,
extended earnings/analyst/SEC tools, macro search) have no schema entry and are
**unreachable through the LLM loop** — the schema is the only thing that produces
a `tool_use` block.

**Honest copilot caveats:**

- **Shipped default routes to Ollama `qwen2.5:7b`** — a local model that may not
  be installed; without a running daemon the default agent fails at first call
  unless the user overrides. It is also the agent doing the most tool
  orchestration, on the smallest model.
- **Gemini multi-round tool use is likely broken** — Gemini keys
  `function_response` by tool _name_ read from `metadata["name"]`, but the runtime
  appends tool-result messages with only `tool_call_id` and no `name` → every
  result serialises `name=""`. Single-text Gemini calls are fine. OpenAI-family +
  Anthropic key by id and are correct.
- **Live answers are proven only against a mocked provider**
  (`test_tool_loop_e2e.py`). A real answer needs a BYOK key. Anthropic/OpenAI/Groq
  are higher confidence; Gemini/Ollama are confidence-6-7.

---

## 5. Safety & Tier-1 locks — what must NOT break in the redesign

The BLUEPRINT §6.5 execution-safety layer this section used to describe was
removed permanently with trading (D81, 23 Sep 2026) — see §0.x and
`docs/SAFETY_ARCHITECTURE.md`. What remains as Tier-1 and must not break:

1. **`types/plugin.ts`** — the serializable plugin contract. Any change is Tier-4
   (blocks to operator). It has held through all six capabilities without a
   change; the `"trading-bot"` `PluginType` literal and its Tradesa-shaped
   JSDoc examples are BLOCKED-FOR-OPERATOR, not reopened by D81.
2. **The proposed-changes trust gate** (`src/store/proposed-changes.ts`,
   `src/lib/host-actions.ts`) — every agent-proposed mutation over the 19
   surviving host actions stages through the same diff/accept flow the
   removed order kind used to ride.
3. **The renderer-reads-keychain → secret-in-request invariant** — the sidecar
   cannot read the OS keychain; only Rust can. Never log/echo/persist a secret.
4. **Read-only-wrapper enforcement for data-source/trading-bot-shaped
   plugins** — three independent layers: no write methods on the provider
   surface (audit-tested), no non-GET routes (audit-tested),
   `supportsControlPlane: false`. (Tradesa V2, this rule's original worked
   example, no longer exists in the tree at this sha — see §3.4; the rule
   itself is the standing contract for any future plugin of that shape.)
5. **No order, broker or simulated-account path exists anywhere** — pinned by
   `sidecar/tests/test_no_trading_surface.py` (D81's Gate 8).

---

## 6. Persistence & local-first model

**No cloud, no account, no sync, no telemetry.** State lives in exactly three
places with a clean ownership split. `get_data_dir()` reads `VYSTED_DATA_DIR`
(set by the core via `--data-dir`), falling back to `~/.vysted-terminal` outside
Tauri.

| Surface                                                                        | Owner      | Backing store                  | Location                                       |
| ------------------------------------------------------------------------------ | ---------- | ------------------------------ | ---------------------------------------------- |
| Workspace blob (layout, modules, drawings, default provider, watchlist)        | Sidecar    | `<name>.vysted-workspace` JSON | `get_data_dir()/workspaces/`                   |
| BYOK secrets (LLM keys, MCP endpoints, plugin secrets, first-launch-terms ack) | Tauri Rust | OS credential store            | macOS Keychain / Win Cred Mgr / Secret Service |
| Portfolio positions (manually tracked — no broker connection)                  | Sidecar    | SQLite `positions`             | `get_data_dir()/portfolio.db`                  |
| Upstream-data TTL cache                                                        | Sidecar    | SQLite `cache` (WAL)           | `get_data_dir()/data_cache.db`                 |

There is no order audit log any more (D81); the append-only `audit_orders`
table and `audit_log.db` existed only to record order placement. A user who
upgraded from a pre-D81 install may still have a stale `audit_log.db` on
disk — nothing reads it — see the UNSURE item in
`docs/redesign/DECISIONS_FOR_OPERATOR.md`.

**The sidecar owns all filesystem persistence so the frontend never needs file
access** — it reaches persistence only through `/workspace`, `/portfolio`
over loopback. The workspace blob is **opaque JSON** the sidecar stores
verbatim (never validates); name safety is a `^[A-Za-z0-9 _-]+$` regex. An
`__autosave__` slot holds the last session; restore skips cleanly to the
bundled default on an unknown-component reference rather than corrupting the
grid.

**BYOK invariant:** secrets never touch disk/`localStorage`/cookies. The only
frontend path is `src/lib/keychain.ts` (`setSecret`/`getSecret`/`deleteSecret`
→ Tauri `invoke`). Namespaces: `llm-provider:<id>`, `mcp-server:<id>`,
`plugin-secret:<pluginId>:<key>`, first-launch-terms ack (there is no
per-broker namespace any more, D81). The `provider-keys` store tracks
**presence only** (`configured|missing|unknown`), never the value. **BYOK is
effectively Tauri-only** — outside the shell `getSecret` rejects →
`"unknown"`, no localStorage fallback by design.

**Honest gaps:** **no DB migrations anywhere** (all three SQLite stores use
`CREATE TABLE IF NOT EXISTS` — adding a column to an existing install would not
migrate); workspace blobs are server-unvalidated (corruption caught only at
`fromJSON` on the client); autosave is best-effort (a transient failure silently
fails to persist until the next layout change); `data_cache` stale rows are never
auto-evicted.

---

## 7. Consolidated status — works / buggy / deferred

Reference HEAD `3123e7c` (Phase 10); superseded at this sha (`4d89314`,
0.9.0 candidate — see §0.0 for the R15 delta this table does not yet fully
reflect subsystem-by-subsystem). **Last release tag `v0.8.0`; Phase
8/9/9.5/10 + R15 sit on `main`/`004-r4-experience-rebuild` unreleased/
untagged (no `r15-*` tag exists yet at this sha, per `git tag`).** "Works"
below almost always means "automated gates pass against mocks," **not**
"live/visually validated by a human."

| Item                                                                                   | Status                                                                                                          | Source                                                                         |
| -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `pnpm ci-local` (full CI parity)                                                       | **Stale figures** — pre-R15 (619 vitest, 6 cargo, 942 pytest); a later R15 pause point recorded "pytest 2507 passed/1 skipped, vitest 1504 in 135 files, cargo 13" (`DECISIONS_FOR_OPERATOR.md` §2.6), also not re-verified at this sha; see §0.0 | PHASE_10_HANDOFF §"Gate results"; <!-- VERIFY: re-run ci-local at 4d89314 --> |
| Agent-write safety model (§6.5)                                                        | **Works** — Gate 8 no-trading test green; see §0.x, SAFETY_ARCHITECTURE                                         | SAFETY_ARCHITECTURE                                                            |
| All 3 sidecar binaries spawn + bind                                                    | **Works** — `smoke-test-sidecars.mjs` exit 0 (freshness + bind probe)                                           | PHASE_10_HANDOFF                                                               |
| Static-export build                                                                    | **Works** — `pnpm build` (`vite build`) per prior tags; not re-run at this sha                                  | PHASE_10_HANDOFF                                                               |
| Copilot agentic tool loop                                                              | **Works against a mocked provider** (`test_tool_loop_e2e.py`); live answers unverified                          | PHASE_10_HANDOFF §2; CLAUDE.md                                                 |
| 5 core data panels + 50 indicators + dockview + workspace save/load                    | **Works** (mature, prior tags) — but reskinned in Phase 10, so visuals re-verify                                | §15; CHANGELOG                                                                 |
| Phase-6 analysis panels (macro/SEC/earnings/analyst/screener/quant)                    | **Works** (tests); backend liveness unverified from frontend                                                    | §11                                                                            |
| Persisted watchlist + defaultProviderId                                                | **Works** — ride the workspace blob, survive relaunch                                                           | PHASE_10_HANDOFF §5                                                            |
| "Claude after dark" reskin                                                             | **Builds**; every panel's rendered appearance is operator-eyeball                                               | PHASE_10_HANDOFF §4                                                            |
| MCP cold-bind latency                                                                  | **Buggy/fragile** — 34s isolated, worse under I/O contention; mitigated (45s×2, graceful fallback), not crash   | BLOCKERS Phase 9.5 UC1                                                         |
| openbb/sec-edgar `_MEIPASS` deadlock root cause                                        | **Buggy** — worked around at the supervisor, NOT actually fixed                                                 | BLOCKERS carry-forward #7                                                      |
| Smoke-test endpoint-data gap                                                           | **Buggy** — binds-but-empty-data still passes the gate                                                          | BLOCKERS S2 #8                                                                 |
| `contributesAgents` / `contributesNodes` plugin paths                                  | `contributesAgents` exercised by `vysted-lenses` (Quant Tutor); `contributesNodes` **unexercised**                                                                             | §8                                                                             |
| Gemini multi-round tool use                                                            | **Likely broken** — `function_response` keyed by empty name                                                     | §4                                                                             |
| Plugin manifest↔instance + `requiredHostVersion` checks                                | **Documented but not implemented**                                                                              | §8                                                                             |
| Custom-agent tool allow-list                                                           | **Stale/out of sync** — 5 ids; `news`/`macro` not in `TOOL_SCHEMAS`                                             | §11                                                                            |
| Trading (broker connectivity, orders, simulated account)                               | **Removed permanently (D81, 23 Sep 2026)** — not deferred, not dead code; deleted                               | §0.x; SAFETY_ARCHITECTURE                                                      |
| Copilot roster depth (`/agents/roster`, 3-pane panel, `delegate_to_persona`)           | **Deferred**                                                                                                    | BLOCKERS Phase-10 #5                                                           |
| Customizability follow-ups (connector hub, panel gallery, saved screens)               | **Deferred** — DataSource registry currently inert                                                              | BLOCKERS Phase-10 #6                                                           |
| `--onedir` MCP packaging (true cold-bind fix)                                          | **Deferred** — needs `tauri build`-verifiable change ci-local can't check                                       | BLOCKERS Phase 9.5                                                             |
| Light theme                                                                            | **Deferred to v1.1** — dark-only ships                                                                          | BLOCKERS S2 #10                                                                |
| Launch ops (signing, updater wiring, channels, landing page, LICENSE flip, TOS dialog) | **Mostly deferred** (Phase 7 → still open)                                                                      | BLOCKERS v0.7.0→Phase 10                                                       |
| `auto_export`/auto-updater end-to-end                                                  | **Non-functional** — `createUpdaterArtifacts:false`, no frontend caller, no release workflow                    | §1, §14                                                                        |
| Version strings (`0.8.0` everywhere)                                                   | **Stale, open** — 0.9.0 candidate target (§0.0); files still 0.8.0, bump lands with the prepared version branch right after the `r15-rc1` tag                          | §3.12; §0.0                                                                    |
| mypy/lint debt, a11y gaps, Linux transitive advisories                                 | **Known debt** — see BLOCKERS S2/S3/S4                                                                          | BLOCKERS                                                                       |
| R15 register remediation (critical/high/medium/low)                                    | **16/16 critical fixed; 105/116 high; 258/293 medium; 12/227 low** — open critical/high/medium is **0** as of `4c6dfe8c` (R15-LEAD-035 moved to `blocked_tier4`, an escalation not a concurrence, see §0.0); 205 open low, 26 blocked_tier4, 11 needs_gui | §0.0; `vysted-r15-register.json`; `BLOCKERS.md`                                |
| Licence (PolyForm Strict 1.0.0 core + Apache-2.0 plugin contract + commercial)         | **Works** — `LICENSE`/`LICENSE-APACHE`/`COMMERCIAL_LICENSE.md` present at this sha                              | §0.0                                                                           |

**Bottom line:** green on every machine-checkable gate as of the stale
pre-R15 run cited above (re-run pending, §0.0), unproven on every
human-checkable one. The §6.5 order-execution layer no longer exists (D81);
§6.5 now names the agent-write safety model, i.e. the proposed-changes trust gate
(§5) over the 19 surviving host actions, including the tracked portfolio. The
standing fragility to watch is MCP cold-bind contention (worked around, not
root-fixed); R15 Stage C register remediation is summarized in §0.0.

---

## 8. What the redesign keeps vs rebuilds

The "Cursor for finance" redesign should treat this codebase as a **strong
foundation with a thin, dated experience layer** — keep the substrate, rebuild
the surface and the agent-centrality.

### KEEP (the working foundation — do not rebuild)

- **The sidecar + data layer.** ~111 REST routes (post-D81), the `provider_registry`
  dispatch seam, yfinance/ccxt/news/VADER/macro/QuantLib/49-indicators, the
  data-cache, the SSE convention. This is the data brain; it works and is broadly
  tested. The redesign consumes it, it does not replace it.
- **The agent-write safety model, intact.** Tier-1 LOCKED. The proposed-changes
  trust gate over the 19 host actions is the most trustworthy asset — preserve
  it and run `test_no_trading_surface.py` as a hard gate on any touch (§5).
  There is no broker connectivity, order placement or simulated account to
  preserve — that layer was removed permanently (D81, 23 Sep 2026).
- **dockview panels + the workspace-blob persistence model.** The layout engine,
  the module registry, the opaque-blob round-trip, the unknown-component restore
  guard, the local-first ownership split (sidecar files + OS keychain). The
  _arrangement_ may change; the persistence + SSR-safe mounting mechanics are
  hard-won and should survive.
- **The manually tracked portfolio.** Local holdings, cost bases, P&L on real
  prices, CSV export, notes and watchlists, and everything the agent does with
  them (staged through the same trust gate). There is no broker connection
  behind it and never will be again (D81) — keep the ledger, do not reopen
  execution.
- **The copilot tool loop + tool-schema contract.** The `invoke_agent` loop,
  `TOOL_SCHEMAS` + per-provider serialisers, the `tool_ids`-pop contract, the
  metadata-carried assistant tool-call turn, host-action execution, and
  terminal-state context injection. This is the spine of the agent experience —
  built once, working, and load-bearing. Keep the mechanism; expand the catalog.
- **BYOK + MCP-on-both-sides plumbing.** The keychain-mediated secret flow and
  the dual MCP role (proxy-in + serve-out) are real and reusable.

### REBUILD (the experience + agent-centrality + MCP-as-framework)

- **The experience / UI.** The shell is "a data viewer with a raw LLM chat
  bolted on" (Phase-10's own framing). The dark-only, header-less, command-
  palette-as-substring-match shell with no connection indicator and no light
  theme is the surface to rethink for an agent-first, "Cursor for finance"
  posture. Keep dockview as an engine; rebuild the chrome, the entry points, and
  the information hierarchy around the copilot.
- **Agent-centrality.** Today the copilot is one panel among 18. The redesign
  should promote it to the primary interaction model — but first **close the
  catalog gap** (~11 registered tools are invisible to every model for lack of a
  `TOOL_SCHEMAS` entry), **fix the Gemini multi-round break**, **reconcile the
  custom-agent allow-list** with the real catalog, and **resolve the default
  agent** (the shipped `copilot` defaults to an Ollama model that may not exist).
  The deferred roster depth (`/agents/roster`, 3-pane panel,
  `delegate_to_persona`) is the natural first build.
- **MCP-as-framework.** Today MCP is plumbing (two proxied subprocesses + a
  serve-out surface with a manual copy-paste external-client flow). A
  "Cursor for finance" thesis likely wants MCP as the _extension framework_ —
  the inert DataSource/connector registry, the dead stdio transport reserved for
  filesystem plugins, and the missing marketplace/signing/loader are where this
  becomes real. The contract supports it; the wiring does not exist yet.
- **The plugin runtime's missing guarantees.** Before leaning on plugins as the
  extension story, implement the manifest↔instance + `requiredHostVersion`
  checks the docs already claim, and wire `PluginConfig.secrets`. The
  read-only-wrapper rule stays as the contract for future data-source plugins
  (§5); there are no broker plugins left to decide the fate of (D81).
- **Distribution.** Unsigned, no release pipeline, stale version strings, a
  non-functional updater. A shippable product needs signing/notarization, the
  updater wired (`createUpdaterArtifacts:true` + a publish workflow), and the
  version-of-truth drift closed.

**One-line redesign thesis:** keep the sidecar, the agent-write safety model,
the panels, the persistence model, the tracked portfolio, and the copilot tool
loop; rebuild the shell into an agent-first experience, promote MCP from
plumbing to extension framework, and close the copilot's catalog/provider gaps
that quietly cap what the agent can do today. Trading is not part of this
product any more (D81) — nothing here should reopen it.
<!-- refresh f444479 to 4d89314: register table + Stage C remediation section rebuilt for batches 2-22 (652 entries, was 626; open critical/high/medium now just R15-LEAD-035, was 3 high + 114 medium); added the operator-accepted "Known limitations at rc1 — agent chat with a keyless local model" subsection (LEAD-030/035/037/038 verbatim wording per the binding Tier-4 sign-off); corrected the plugin-system description throughout (§1, §3.2, §3.4, §5, §3.11) — tradesa-v2 no longer exists in the tree, replaced by vysted-lenses/vysted-news/vysted-yfinance (BUNDLED_PLUGINS/PLUGIN_COMPANIONS also gone, replaced by marketplace.ts CATALOG_ROWS; contributesAgents now exercised by vysted-lenses); router/route counts refreshed (24→28 routers, ~107→~111 routes); §7 status table and sha references updated -->
<!-- refresh 4d893147 to 4c6dfe8c (Stage D LEAD-035 disposition pass): batch 24 merged
`6778f892` — its named narrowing-only fix holds as a strict subset but LEAD-035 failed
certification a fourth time; the verifier REFUSED `blocked_tier4` concurrence and named a
further narrowing-only guard it would certify. The lead applied `blocked_tier4` under the
three-failure rule as an escalation (not a concurrence) at `4c6dfe8c`. Updated: the R15
Stage C remediation intro, the severity table (medium open 1→0, blocked_tier4 15→16;
totals 206→205 open, 25→26 blocked_tier4), the batch-24-tracked-now note, the LEAD-035
Known-limitations entry (now the batch-24 verifier's `d1290f66`-accurate wording, verbatim,
plus the operator's (a)/(b) options at DECISIONS §4.10), the fail-safe/shipping-matcher
paragraph (line number + narrowing noted, entry status unchanged), and the §7 summary
table's register-remediation row. -->
<!-- critic-footer -->
## Critic findings applied

1. applied — §3.3 `provider_registry.py` paragraph and yfinance bullet restored verbatim to the at-sha model-key/preference-order text.
2. applied — §3.3 screener bullet restored verbatim to the at-sha 503-symbol `sp500` + India-universe + nested AND/OR text.
3. applied — host-action count "18"→"19" fixed at every occurrence; `HOST_ACTION_NAMES` (`src/lib/host-actions.ts`) pointer restored in both the Chat sidebar and "Host-action tools drive the terminal" paragraphs.
4. applied — both paragraphs restored to state that `executeHostAction` stages a `ProposedChange` and that only `AUTO_APPLIED_KINDS` (`panel`/`chart`/`watchlist`) skip review under AUTO.
5. applied — no `.draft.md` change needed; the diff-generation commands already `tail -n +2` the draft before diffing, so the regenerated `CURRENT_STATE.draft.diff`/`BLOCKERS.draft.diff` no longer add the DRAFT marker line to root `BLOCKERS.md`.
6. applied — §0.0 "Version" paragraph, §3.12, and the §7 "Version strings" row now say `0.9.0` lands when the prepared version branch merges right after `r15-rc1`, matching `BLOCKERS.draft.md`.
7. applied (in `BLOCKERS.draft.md`) — see that file's footer.
8. applied (in `BLOCKERS.draft.md`) — see that file's footer.
9. applied — §7 `contributesAgents`/`contributesNodes` row now says `contributesAgents` is exercised by `vysted-lenses` (Quant Tutor); `contributesNodes` stays unexercised.
10. applied — §3.2 now cites `app.py:329` for `version="0.8.0"` and `app.py:191,205` (called at `:368,374`) for the v0.5.0/v0.6.0 aggregators.
11. applied — §3.12 "despite … Stage C batches 2-9" corrected to "2-22".
12. applied — §8 KEEP "~94 REST routes" corrected to "~111 REST routes".
13. applied (in `BLOCKERS.draft.md`) — see that file's footer.
14. applied (in `BLOCKERS.draft.md`) — see that file's footer.
15. applied (in `BLOCKERS.draft.md`) — see that file's footer.
16. applied — the two `docs/redesign/FOUNDATION_BUILD_REPORT.md`/`P1_P3_BUILD_REPORT.md` pointers in this file now note "(not in tree at this sha — `git ls-tree -r` at `4d89314` has no match)"; the four `docs/PHASE_*` pointers this finding also covers live in `BLOCKERS.draft.md` and are fixed there.
17. applied — module count "~18 first-party"/"18 first-party modules" corrected to "~20"/"20" (§1, §3.8); `lib.rs` "+ three modules" corrected to "+ four modules (`diag_log.rs`, `keychain.rs`, `openbb_mcp.rs`, `sec_edgar_mcp.rs`)" (§3.1).
