# AC-5 — MCP surface: tool count, dict returns, Origin guard (final-adv-maintainer, d38b5d1a)

- /mcp/status on the bundle binary (:52820) and source (:52825): ready=true, toolCount=39 (AC-5/mcp-status.txt). The smoke test (scripts/smoke-test-sidecars.mjs:850) logs `toolCount` from the same route and asserts ready; FastMCP `list_tools` over the wire returns 39 names (AC-5/mcp-client.txt), equal to G8-1's in-process `mcp_list_tools` (39). No order/broker tool.
- Tool calls over a real FastMCP client: every successful call returns structured content of type dict (6/6), including the list-shaped `list_agents` wrapped as `{"agents": [...]}`; an unknown symbol returns is_error with a message, no 500 (AC-5/mcp-client*.txt).
- Origin guard (AC-5/origin-probes.txt), /mcp/, /mcp/status, /health: `http://evil.example`, `null`, `http://127.0.0.1:5174`, `http://localhost:5173.evil.example` → 403 `origin not allowed`; no Origin, `tauri://localhost`, `http://localhost:5173` → 200. Exact-match on the tuple at sidecar/app.py:289-295 — no prefix/suffix confusion.
- Note: the release binary still allow-lists the dev origins `http://localhost:5173`/`http://127.0.0.1:5173`; any local process serving on :5173 can drive the sidecar. That is inside R15-CODE-AGENT-001's scope (needs_gui); evidence attached there, not re-filed.

GUI half (the webview's own Origin reaching /mcp) stays with R15-CODE-AGENT-001 in NEEDS_GUI.md.

VERDICT AC-5: pass
