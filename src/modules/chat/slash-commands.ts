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

/* -------------------------------------------------------------------------- *
 * Curated slash registry (FR-100, SC-023)
 * -------------------------------------------------------------------------- *
 * The composer renders an inline picker from `SLASH_COMMANDS` and consumes the
 * `dispatch` shape to either compose a prompt for the agent or fire a gated
 * frontend action. This registry is intentionally separate from the legacy
 * `parseSlashCommand` verbs above: those drive raw plumbing (`/ask`, `/agent`,
 * `/provider`, `/key`), while these are the curated, discoverable research and
 * workspace verbs surfaced in the picker. The composer (lead-owned) decides
 * whether to route an input through this registry or the legacy parser.
 */

/** A direct frontend action a slash command can request (still lead-gated). */
export type SlashAction =
  | "chart"
  | "watch"
  | "portfolio"
  | "layout"
  | "sources"
  | "clear"
  | "export"
  | "screener";

/**
 * How a curated slash command resolves once invoked:
 * - ``prompt`` composes a natural-language prompt sent to the active agent
 *   (the agent maps it to the right tool, e.g. ``/deep`` → ``deep_research``).
 * - ``action`` requests a direct frontend action; the composer remains the
 *   gate that actually performs it (open a panel, switch layout, …).
 */
export type SlashDispatch =
  | { kind: "prompt"; template: (args: string) => string }
  | { kind: "action"; action: SlashAction };

/** A single curated slash command surfaced in the inline picker. */
export interface SlashCommandDef {
  /** The bare verb, no leading slash (e.g. ``"research"``). */
  trigger: string;
  /** Short label shown in the picker row. */
  title: string;
  /** One-line description of what the command does. */
  description: string;
  /** Optional argument-shape hint shown after the trigger (e.g. ``"<q>"``). */
  argHint?: string;
  /** How the command resolves once invoked. */
  dispatch: SlashDispatch;
}

/**
 * The curated slash command set surfaced in the composer's inline picker. The
 * order here is the stable "empty query" order shown when the user has typed
 * only ``/``. Keep the legacy plumbing verbs (`/ask`, `/agent`, …) out of this
 * list — they live in `parseSlashCommand` and aren't part of the curated UX.
 */
export const SLASH_COMMANDS: SlashCommandDef[] = [
  {
    trigger: "research",
    title: "Research",
    description: "Run a standard research pass on a question or ticker.",
    argHint: "<q>",
    dispatch: { kind: "prompt", template: (args) => `research ${args}` },
  },
  {
    trigger: "deep",
    title: "Deep research",
    description: "Go deeper — the agent maps this to a full deep-research run.",
    argHint: "<q>",
    dispatch: { kind: "prompt", template: (args) => `/deep — go deeper on ${args}` },
  },
  {
    trigger: "compare",
    title: "Compare",
    description: "Compare two tickers or entities side by side.",
    argHint: "<a> <b>",
    dispatch: { kind: "prompt", template: (args) => `compare ${args}` },
  },
  {
    trigger: "chart",
    title: "Chart",
    description: "Load a ticker into the chart panel at an optional timeframe.",
    argHint: "<ticker> [tf]",
    dispatch: { kind: "action", action: "chart" },
  },
  {
    trigger: "screener",
    title: "Screener",
    description: "Screen the universe with a natural-language filter.",
    argHint: "<nl>",
    dispatch: { kind: "prompt", template: (args) => `screen for ${args}` },
  },
  {
    trigger: "watch",
    title: "Watch",
    description: "Add a ticker to the watchlist.",
    argHint: "<ticker>",
    dispatch: { kind: "action", action: "watch" },
  },
  {
    trigger: "portfolio",
    title: "Portfolio",
    description: "Open the portfolio panel.",
    dispatch: { kind: "action", action: "portfolio" },
  },
  {
    trigger: "layout",
    title: "Layout",
    description: "Switch to a named workspace layout.",
    argHint: "<name>",
    dispatch: { kind: "action", action: "layout" },
  },
  {
    trigger: "export",
    title: "Export",
    description: "Export the current view or conversation.",
    argHint: "[fmt]",
    dispatch: { kind: "action", action: "export" },
  },
  {
    trigger: "sources",
    title: "Sources",
    description: "Show the sources behind the latest answer.",
    dispatch: { kind: "action", action: "sources" },
  },
  {
    trigger: "clear",
    title: "Clear",
    description: "Clear the current conversation.",
    dispatch: { kind: "action", action: "clear" },
  },
];

/** Lower-case trigger → def lookup for `parseSlashInvocation`. */
const SLASH_BY_TRIGGER = new Map(SLASH_COMMANDS.map((cmd) => [cmd.trigger, cmd]));

/**
 * Score a curated command against a (lower-cased) picker query. Prefix matches
 * outrank substring matches, and shorter triggers win the tie (so ``/c`` floats
 * ``chart`` toward ``compare``/``clear`` deterministically by length). Returns
 * ``null`` when the trigger doesn't contain the query at all.
 *
 * Mirrors the prefix-wins ranking style of `buildPaletteCorpus`'s fuzzy weights
 * without pulling in the palette's scoring machinery — this registry is small
 * enough that a prefix/substring score with a length tiebreak is sufficient.
 */
function scoreSlash(trigger: string, query: string): number | null {
  if (query.length === 0) {
    return 0;
  }
  const idx = trigger.indexOf(query);
  if (idx < 0) {
    return null;
  }
  // Prefix (idx === 0) gets the high band; substrings get the low band. Within
  // a band, an earlier match position and a shorter trigger rank higher.
  const band = idx === 0 ? 1000 : 0;
  return band - idx * 10 - trigger.length;
}

/**
 * Decide whether the inline picker should be open for the current composer
 * input and, if so, the ranked curated commands to show.
 *
 * The picker is open while the user is still typing the *command name* — that
 * is, the input starts with ``/`` and has no space yet. Once a space is typed
 * the user is entering arguments, so the picker closes (the composer can show a
 * different affordance). The empty ``/`` case opens the picker with the full
 * list in stable order. Ranking is case-insensitive: prefix matches first,
 * then substring matches.
 */
export function matchSlash(input: string): {
  open: boolean;
  query: string;
  matches: SlashCommandDef[];
} {
  if (!input.startsWith("/") || /\s/.test(input)) {
    return { open: false, query: "", matches: [] };
  }
  const query = input.slice(1).toLowerCase();
  if (query.length === 0) {
    return { open: true, query, matches: [...SLASH_COMMANDS] };
  }
  const matches = SLASH_COMMANDS.map((cmd) => ({ cmd, score: scoreSlash(cmd.trigger, query) }))
    .filter((entry): entry is { cmd: SlashCommandDef; score: number } => entry.score !== null)
    .sort((a, b) => b.score - a.score)
    .map((entry) => entry.cmd);
  return { open: true, query, matches };
}

/**
 * Parse a *completed* curated invocation (``/cmd args``) into the matched
 * command def and its raw argument string. Returns ``null`` unless the input is
 * a leading-slash line whose first token is a known curated trigger — so a bare
 * ticker like ``/AAPL`` (no matching trigger) resolves to ``null`` here, leaving
 * the composer free to route it elsewhere.
 */
export function parseSlashInvocation(input: string): { cmd: SlashCommandDef; args: string } | null {
  const trimmed = input.trim();
  if (!trimmed.startsWith("/")) {
    return null;
  }
  const [head, ...rest] = trimmed.slice(1).split(/\s+/);
  const cmd = SLASH_BY_TRIGGER.get(head.toLowerCase());
  if (!cmd) {
    return null;
  }
  return { cmd, args: rest.join(" ").trim() };
}
