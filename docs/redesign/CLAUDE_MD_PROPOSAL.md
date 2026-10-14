# Proposed CLAUDE.md updates after R7 (sign-off-only file — apply on review)

## Stack section

- Frontend line: replace "Next.js 16 (App Router, **static export**)" with
  "Vite 8 + React 19 + TypeScript (single-page shell: `index.html` + `src/main.tsx`;
  static build to `out/`)". JetBrains Mono is self-hosted via `@fontsource`
  (`--font-jetbrains-mono` defined in `styles/tokens.css`).
- Dev server is `vite` on `127.0.0.1:5173` (tauri.conf.json devUrl matches; strictPort).

## Gotchas → Frontend

- Vite watcher must ignore `.claude/**`, `out/**`, `sidecar/**`, `src-tauri/**`,
  `graphify-out/**` (vite.config.ts) or teammate-worktree commits reload the app mid-session.
- The tauri-plugin-mcp socket bridge WEDGES (hangs, not refuses) after Vite HMR re-runs the
  bridge init — restart the dev stack after any frontend change before driving the rig.
- WKWebView serves STALE JS through location.reload(); live-verifying a frontend change
  needs a full stack restart with `rm -rf ~/Library/Caches/vysted-terminal ~/Library/WebKit/vysted-terminal`.
- The arrangeable-panel map in `src/lib/layout-templates.ts` must use REGISTERED module ids
  (screener registers `screener-panel`, not `screener`) — drifted ids mint duplicate panels.
  `applyPlan` now MOVES already-open panels to their planned positions (real splits).

## Gotchas → Copilot & sidecar

- Frontend CONTROL keys riding invocation `options` (research_depth, deepResearchBackend,
  modelWebSearch, history) must never reach adapter kwargs — `routers/llm.py` filters for
  raw chat; `agent_runtime` pops on the agent path. Adding a new control key = add it in
  BOTH places.
- The composer depth slider publishes `config.set_request_research_depth` (task-local);
  the research tool's depth default reads it; an explicit model-passed depth wins.
- Search tiers: `t1_local | t2_searxng | t3_hosted` ride headers
  `X-Vysted-Research-Tier` / `X-Vysted-Search-Engine` / `X-Vysted-Openrouter-Key`
  (middleware → ContextVars in `sidecar/config.py`). Legacy trio unchanged.
- `transform.code` is the 11th built-in workflow node (restricted ast evaluator,
  `services/workflow_nodes/code_node.py`) — keep the frontend mathjs lane and the Python
  lane grammar-compatible (arithmetic/comparison/boolean/abs|min|max|round|sum|sqrt|floor|ceil).
- The hand-written MCP-only workflow tools now include `save_workflow` (listed in
  `_RUNTIME_ONLY` of test_mcp_catalog_parity).
- Keyless India: BSE master is REAL (4,873 rows incl. SME; regenerate via
  `resolver_masters/regenerate_bse_master.py`); bse_provider routes by scrip code;
  `nse_direct` (rank 15) sits above jugaad for IN; disclosures live under `/disclosures/*`.

## Versioning & process

- macOS dev signing: the "Vysted Terminal Dev Signing" identity disappeared from the login
  keychain during R7 — until `scripts/macos-dev-setup.sh` is re-run, every recompiled dev
  binary is ad-hoc and the FIRST keychain read at boot blocks on a SecurityAgent prompt
  (the always-mounted chat surface refreshes provider keys at mount). Re-create the cert
  before any long autonomous run.

## R8 proposal — sidecar spawn gotcha line

The Gotchas line "After spawn, call `crate::wait_for_port` (port `0` → routes fall back /
501, graceful degrade)" should now read "After spawn, call `crate::wait_for_port_with_retries`
(45s × 2 — the budget a cold `--onefile` extraction actually needs; port `0` → routes fall
back / 501, graceful degrade)". R8 removed the flat-15s `wait_for_port` wrapper after it
false-flagged healthy cold boots ("Python sidecar did not come up") and skipped the FR-025
endpoint file; the main sidecar now shares the MCP subprocesses' retry budget.

## R13 proposal — smoke-test line (attended-safe pre-flight)

The Verification-gates line for `node scripts/smoke-test-sidecars.mjs` should now read: "...
spawns each built sidecar on an ephemeral port, TCP-probes MCP binds, and asserts
`/health` version + `/agents` count + `/mcp/status`; its pre-flight is ATTENDED-SAFE (reaps
only its own PID ledger from a prior crashed run — never a blanket `vysted-*` name match, so
it never touches the operator's running app)."

## 2026-09-23 proposal — relicense (Tier-4 sign-off given)

The Decision authority §1 "Locked" line currently reads:

> Stack; AGPL-3.0 + commercial dual license; MCP server in v1.0.

It should read:

> Stack; PolyForm Strict 1.0.0 + commercial license (relicensed 23 Sep 2026); MCP server
> in v1.0.

Context: the operator relicensed the core from AGPL-3.0 to PolyForm Strict 1.0.0 (public,
noncommercial-only) + commercial license (the only other path), with the plugin contract
(`types/plugin.ts`, `types/plugin-runtime.ts`) and the example plugin
(`plugins/example/*`) carved out under Apache-2.0 so third-party plugin authors are never
blocked. Every commit before the relicensing commit remains AGPL-3.0. See `LICENSING.md`
and `docs/redesign/DECISIONS_FOR_OPERATOR.md` §1.4 for the full record.

## 2026-09-23 proposal — trading removed (D81, operator Tier-4 sign-off)

Full evidence and inventory: `docs/redesign/verification/r15/stage-c/REMOVAL_PLAN.md`.
Exact edits queued for `CLAUDE.md`:

- **Layout:** `src-tauri/` drops "kill-switch" from its one-line description (no
  `kill_switch.rs` any more). `plugins/` becomes "(openbb-mcp, yfinance, vysted-news,
  vysted-lenses, example)" — the `brokers` entry is gone.
- **Decision authority, Tier 1:** the ⚠️ sentence

  > ⚠️ The redesign vision **changes some locked decisions** (e.g. broker order execution
  > moves to deferred/out-of-scope) — such reversals are Tier-4: surface to the operator,
  > do not bake in silently.

  becomes:

  > Trading (broker connectivity, orders, simulated accounts) was removed permanently by
  > D81 (23 Sep 2026, operator Tier-4 sign-off).

- **Tier-1 invariants:** replace the four §6.5 bullets (append-only audit log, type gate +
  grep check, kill-switch, read-only trading-wrapper layers) with one line: "§6.5
  agent-write safety model (`docs/SAFETY_ARCHITECTURE.md`) — proposed-changes gate,
  read-intent strip, no-trading invariant pinned by
  `sidecar/tests/test_no_trading_surface.py`."
- **Plugin contract:** "Read-only trading-wrapper plugins" becomes "Read-only wrapper
  plugins"; the three-layer rule itself (no mutating methods, GET-only router,
  `supportsControlPlane=false`) is unchanged.
- **Gotchas → Copilot & sidecar code:** drop "orders still never auto-apply" from the
  research-auto-publish bullet ("Rides the existing proposed-changes gate (never bypasses
  §6.5; orders still never auto-apply)" → "Rides the existing proposed-changes gate (never
  bypasses §6.5)").
- **Gotchas → Broker & credentials:** rename the section to "Gotchas → Credentials." Delete
  the "Kite Connect read-only login runs in the SIDECAR" bullet and the "Granular broker
  reads" bullet in full — no broker exists to read from. In the BYOK secrets bullet, change
  "a header for read-only plugins, never the body" to "a header for plugins that need one,
  never the body."
- **Gotchas → Frontend:** add one line: "`deserializeWorkspace` restores non-layout slices
  (holdings, watchlist, notes) independently of the dockview layout — an unknown panel
  reference never costs user data (R15-LIFECYCLE-002)."
- **Reference docs:** drop the `docs/BROKER_INTEGRATIONS.md` mention from the
  `docs/MCP_INTEGRATION.md, docs/SIDECAR_API.md, docs/PLUGIN_DEVELOPMENT.md,
docs/BROKER_INTEGRATIONS.md, docs/DESIGN_SYSTEM.md` list (it is now a one-paragraph
  removal note, not a live per-subsystem reference).

Not queued here (Tier-1, blocked-for-operator, no CLAUDE.md text change proposed): the
`types/plugin.ts` `"trading-bot"` `PluginType` literal and its Tradesa-shaped JSDoc
examples — see `docs/redesign/DECISIONS_FOR_OPERATOR.md` §3.4.
