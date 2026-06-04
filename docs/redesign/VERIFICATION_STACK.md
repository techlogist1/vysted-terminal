# Verification stack — driving the live Vysted app like a human

The redesign verification work needs to drive the **real running app** (not
self-report from code/tests). Vysted is a Tauri desktop app: a Rust core hosting
a **WKWebView** (macOS) — *not* Chromium — with a Python sidecar. That shapes
which tools can verify which surfaces. We use three tiers.

## Tier 1 — Playwright MCP (`@playwright/mcp`) — the web UI

**For:** driving the Next.js UI with **trusted (`isTrusted`) events**, DOM
queries, network inspection, and console capture. This is the right tool for
clicks/typing/keyboard that must behave like a real user — including
canvas-interactive surfaces (chart drag/pan, drawings, node-editor palette→canvas)
that the tauri-mcp `evaluate_script` bridge **cannot** synthesise as trusted
(its dispatched events report `isTrusted=false`).

- **Package:** `@playwright/mcp@latest` (the maintained Microsoft package). NOT
  `@modelcontextprotocol/server-playwright` (deprecated).
- **Config:** committed in the project **`.mcp.json`** (`playwright` server), so
  it is shared/version-controlled. It is **project-scoped**, which means it shows
  `⏸ Pending approval` until the operator approves it once on the next `claude`
  launch (the same trust gate `tauri-mcp` rides — a security feature, not a
  failure). It connected cleanly via `claude mcp add` before being moved to
  project scope, proving the package + command resolve.
- **Caveat:** Playwright drives a Chromium it launches — it loads the **web build**
  of the UI (`pnpm dev` / the static export), not the Tauri WKWebView. So it
  verifies UI behaviour + the React/state/network layer, but anything that only
  exists inside the Tauri shell (native menus, OS keychain, the sidecar spawned by
  the Rust core) needs Tier 2/3.

## Tier 2 — Native Computer Use — the macOS shell surfaces

**For:** native surfaces no in-webview tool can reach — the **macOS menu bar**
(the `install_layout_menu` Layout modes), window chrome, OS-level
keyboard/focus, and the real Tauri-hosted webview (the actual shipped shell, with
the sidecar live).

- **Availability:** native Computer Use is a **macOS research preview**, **Max
  plan**, requires Claude Code **≥ v2.1.85**. This machine is on **v2.1.162** — the
  version threshold is met.
- **Caveat (load timing):** MCP servers AND native Computer Use tools are
  resolved at **session start**. A server/tool added or approved *mid-session*
  connects but its tools are **not surfaced to the already-running agent** — they
  appear only in a **fresh** session. So a session that needs Tier 1/2 tools must
  be started *after* the servers are approved.

## Tier 3 — tauri-mcp + Bash + sidecar — everything scriptable

**For:** the broad middle — driving the **real Tauri webview** via `evaluate_script`
(dispatched events work on React; `isTrusted=false`, so not for canvas), reading
the console via `get_logs`, capturing populated screenshots via Quartz
(`/tmp/rigcap.py`, bridge-independent — the tauri-mcp `screenshot` tool wedges the
bridge), and hitting sidecar endpoints directly with `curl` to separate a real
CORS issue from a 500-without-CORS-headers.

- This is what was available **in-session** for the Part 3 verification pass below
  (Tier 1/2 tools were added/approved but, per the load-timing caveat, were not
  surfaced to the running session). Surfaces needing **trusted canvas events**,
  the **native menu**, or a **keyed LLM research call** are flagged in
  `HANDOFF_VERIFIED.md` as "needs the next-session stack or a manual check"
  rather than reported as verified.

## One-time setup (operator)

```sh
# Already committed in .mcp.json — just approve on next launch:
claude            # approve the project-scoped `playwright` + `tauri-mcp` servers
# Then start a FRESH session so the tools surface to the agent.
```
