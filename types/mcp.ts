/**
 * Vysted Terminal — MCP server + client types.
 *
 * Phase 3 wires Vysted to the Model Context Protocol on both sides:
 *
 * - As a SERVER: the sidecar mounts a FastMCP app at `/mcp` over the
 *   Streamable-HTTP transport (MCP protocol revision 2025-11-25). External
 *   MCP clients (Claude Desktop via the `mcp-remote` bridge, Claude Code
 *   natively) consume Vysted's data + agent surface through this.
 *
 * - As a CLIENT: the sidecar's `McpClient` connects to external MCP servers
 *   (the first real consumer is `openbb-mcp-server` 1.4.0, spawned as a
 *   Tauri Rust subprocess — the architectural fix for the Phase-2 Windows
 *   `subprocess.Popen` deadlock).
 *
 * Types here capture the wire shape both sides agree on. The MCP spec
 * defines more — request envelopes, capability negotiation, JSON-RPC IDs —
 * but those stay inside the FastMCP / official MCP SDK. This file only
 * surfaces what Vysted callers need to type-check.
 */

// ---------------------------------------------------------------------------
// External server config (Vysted-as-client)
// ---------------------------------------------------------------------------

/** Transport an MCP client uses to reach an external MCP server. */
export type McpTransport = "stdio" | "http";

/**
 * Connection details for an external MCP server Vysted will consume.
 * Persisted via the keychain (`KEYCHAIN_NAMESPACES.mcpServer`) for any
 * fields containing credentials; the rest live in plugin config.
 */
export interface McpServerConfig {
  /** Stable identifier, e.g. `"openbb-mcp"`, `"github-mcp"`. */
  id: string;
  /** Display name in the plugin manager and settings UI. */
  label: string;
  transport: McpTransport;
  /**
   * HTTP endpoint URL for Streamable-HTTP transport. Required when
   * `transport === "http"`.
   */
  endpoint?: string;
  /** Local command path for stdio transport. Required when `transport === "stdio"`. */
  command?: string;
  /** Command-line args (stdio only). */
  args?: string[];
  /** Environment variables (stdio only); secret values resolved at spawn time. */
  env?: Record<string, string>;
}

// ---------------------------------------------------------------------------
// Tool definitions (mirror the MCP spec's `Tool` shape)
// ---------------------------------------------------------------------------

/**
 * One tool an MCP server exposes. Mirrors the MCP spec's `Tool` object so
 * type-shape matches what FastMCP / the MCP SDK produce and consume.
 */
export interface McpToolDef {
  /** Stable tool identifier, e.g. `"get_quote"`. */
  name: string;
  /** Human-readable description shown to the LLM. */
  description?: string;
  /** JSON Schema for the tool's input arguments. */
  inputSchema: McpJsonSchema;
}

/** Subset of JSON Schema FastMCP emits — kept open via `unknown` to avoid type drift. */
export type McpJsonSchema = Record<string, unknown>;

/** One MCP tool call result. `content` follows the MCP spec's content-block shape. */
export interface McpToolCallResult {
  /** Whether the tool reported an error. MCP spec keeps this on the response, not the transport. */
  isError?: boolean;
  /** Content blocks; text blocks are the primary form, but tools may emit other kinds. */
  content: McpContentBlock[];
}

/** One content block in an MCP tool result. */
export type McpContentBlock =
  | { type: "text"; text: string }
  | { type: "image"; data: string; mimeType: string }
  | { type: "resource"; resource: { uri: string; mimeType?: string; text?: string } };

// ---------------------------------------------------------------------------
// Vysted MCP server (Vysted-as-server)
// ---------------------------------------------------------------------------

/**
 * Health / readiness payload returned by `GET /mcp/status` (a thin Vysted
 * convenience endpoint sitting next to the FastMCP-managed `/mcp` route).
 * Lets the plugin manager UI surface "MCP server: ready" without speaking
 * the JSON-RPC handshake.
 */
export interface VystedMcpStatus {
  ready: boolean;
  /** Number of tools currently registered (data + agents). */
  toolCount: number;
  /** Streamable-HTTP endpoint relative to the sidecar root. Always `"/mcp"` in v0.4.0. */
  endpoint: string;
  /** MCP protocol revision the server speaks (e.g. `"2025-11-25"`). */
  protocolVersion: string;
}
