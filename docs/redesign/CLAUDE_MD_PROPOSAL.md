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
