/**
 * Slash-command parser for the chat sidebar composer.
 *
 * The user types ``/ask <prompt>``, ``/agent buffett <prompt>``,
 * ``/provider anthropic``, or ``/key set anthropic`` and the composer
 * dispatches based on the parsed shape. Free-form text without a leading
 * ``/`` is treated as a continuation of the current agent (or raw chat if
 * none).
 *
 * The parser is intentionally narrow and pure — no Zustand reads, no Tauri
 * calls. The composer wires the action handlers to stores; the parser just
 * tells it which action.
 */

export type SlashCommand =
  /** Raw chat with the default provider (no agent). */
  | { kind: "ask"; prompt: string }
  /** Invoke a specific agent. */
  | { kind: "agent"; agentId: string; prompt: string }
  /** Switch the default LLM provider. */
  | { kind: "provider"; providerId: string }
  /** Open the BYOK key entry dialog for the given provider. */
  | { kind: "key-set"; providerId: string }
  /** Clear the current conversation. */
  | { kind: "clear" }
  /** Show the inline help cheat-sheet. */
  | { kind: "help" }
  /** Plain prompt continuation; the composer routes it per the current agent. */
  | { kind: "raw"; prompt: string };

export interface SlashParseError {
  kind: "error";
  message: string;
}

export type SlashParseResult = SlashCommand | SlashParseError;

/** Parse a single composer input line into a typed command. */
export function parseSlashCommand(input: string): SlashParseResult {
  const trimmed = input.trim();
  if (trimmed.length === 0) {
    return { kind: "error", message: "empty input" };
  }
  if (!trimmed.startsWith("/")) {
    return { kind: "raw", prompt: trimmed };
  }
  const [head, ...rest] = trimmed.slice(1).split(/\s+/);
  const args = rest.join(" ").trim();
  switch (head.toLowerCase()) {
    case "ask":
      if (!args) {
        return { kind: "error", message: "usage: /ask <prompt>" };
      }
      return { kind: "ask", prompt: args };
    case "agent": {
      const split = args.split(/\s+/);
      const agentId = split.shift() ?? "";
      const prompt = split.join(" ").trim();
      if (!agentId) {
        return { kind: "error", message: "usage: /agent <id> <prompt>" };
      }
      if (!prompt) {
        return { kind: "error", message: "usage: /agent <id> <prompt>" };
      }
      return { kind: "agent", agentId, prompt };
    }
    case "provider":
      if (!args) {
        return { kind: "error", message: "usage: /provider <id>" };
      }
      return { kind: "provider", providerId: args };
    case "key": {
      // ``/key set <provider>`` — only the ``set`` sub-verb is wired today.
      const split = args.split(/\s+/);
      const sub = split.shift() ?? "";
      const providerId = split.join(" ").trim();
      if (sub !== "set" || !providerId) {
        return { kind: "error", message: "usage: /key set <provider>" };
      }
      return { kind: "key-set", providerId };
    }
    case "clear":
      return { kind: "clear" };
    case "help":
      return { kind: "help" };
    default:
      return { kind: "error", message: `unknown command: /${head}` };
  }
}

/** Inline cheat-sheet rendered by the ``/help`` command. */
export const SLASH_HELP_LINES = [
  "/ask <prompt> — raw chat with the default provider",
  "/agent <id> <prompt> — invoke a specific agent with focused-panel context",
  "/provider <id> — switch the default provider (anthropic, openai, …)",
  "/key set <provider> — store a BYOK API key in the OS keychain",
  "/clear — clear the current conversation",
  "/help — show this cheat-sheet",
] as const;
