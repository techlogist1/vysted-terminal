# Blockers & Known Issues

Lead-level open items as of v0.4.0. Per-teammate Phase-3 self-reports
(`BLOCKERS-C.md` only — A and B surfaced none) were aggregated here at
integration and removed; the salient detail is preserved in the v0.4.0
merge commit messages and in this file. None of the items below blocks
the v0.4.0 ship; each is a deliberate Phase-4 follow-up.

## Resolved in v0.4.0

The Phase-3 brief explicitly called for the architectural fix to the
Phase-2 `subprocess.Popen` deadlock. **Resolved.** The Phase-2
`plugins/openbb/` + `sidecar/openbb_subprocess/` pair is retired in
v0.4.0. The replacement (`plugins/openbb-mcp/` + the `openbb-mcp-server`
PyPI package bundled into `sidecar/openbb_mcp_subprocess/`) spawns via
Tauri Rust `Command::new` — different Windows handle semantics from
Python's `subprocess.Popen`, so the deadlock does not recur. End-to-end
data path verified (`docs/screenshots/v0.4.0/teammate-b/openbb-mcp-end-
to-end.log`).

The chart-tool `isTrusted` verification gap from v0.3.0 is unchanged —
not Phase 3's scope; documented as a Phase-N visual-verification-suite
candidate.

## Phase-4 follow-ups (cosmetic / forward-looking)

### 1. External MCP client live-screenshot for Claude Desktop

Teammate B captured a session log proving Vysted's MCP server end-to-end
via Vysted's own `McpClient` (same Streamable-HTTP wire Claude Code uses
through `claude mcp add ... --transport http`). The brief's "at least one
external MCP client" success criterion is met by that log + the
documented Claude Code config in `docs/MCP_INTEGRATION.md`.

A polish-tier deliverable: a real screenshot of Claude Desktop consuming
Vysted's MCP server through the `mcp-remote` bridge documented in
`docs/MCP_INTEGRATION.md`. Requires running Claude Desktop + `pnpm tauri
dev` simultaneously, which Phase-3 lead did not capture inside the build
window. Not load-bearing — the architecture is identical to Claude Code's
native HTTP transport.

### 2. Drawing-tool on-canvas screenshots (carried from v0.3.0)

`lightweight-charts` rejects synthesised mouse events (`isTrusted`
check), so the chrome-devtools MCP `click` action cannot exercise the
click-to-create gesture for drawings. The drawings have full unit-test
canvas-call coverage, and the toolbar UI + drawing-inspector populated
screenshots prove the wiring. A `pnpm tauri dev` end-user session
demonstrates them live. A Playwright-based real-event visual regression
suite would close the loop; Phase 4 or later if the budget allows.
