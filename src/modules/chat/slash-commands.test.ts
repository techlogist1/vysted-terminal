import { describe, expect, it } from "vitest";

import {
  matchSlash,
  parseSlashCommand,
  parseSlashInvocation,
  SLASH_COMMANDS,
} from "./slash-commands";

describe("parseSlashCommand", () => {
  it("returns an error for empty input", () => {
    expect(parseSlashCommand("")).toEqual({ kind: "error", message: "empty input" });
    expect(parseSlashCommand("   ")).toEqual({ kind: "error", message: "empty input" });
  });

  it("classifies plain text as a raw prompt continuation", () => {
    expect(parseSlashCommand("what is the moat")).toEqual({
      kind: "raw",
      prompt: "what is the moat",
    });
  });

  it("parses /ask with a prompt", () => {
    expect(parseSlashCommand("/ask is AAPL cheap?")).toEqual({
      kind: "ask",
      prompt: "is AAPL cheap?",
    });
  });

  it("returns an error for /ask without a prompt", () => {
    expect(parseSlashCommand("/ask")).toEqual({
      kind: "error",
      message: "usage: /ask <prompt>",
    });
  });

  it("parses /agent <id> <prompt>", () => {
    expect(parseSlashCommand("/agent buffett is AAPL cheap?")).toEqual({
      kind: "agent",
      agentId: "buffett",
      prompt: "is AAPL cheap?",
    });
  });

  it("returns an error when /agent is missing the id or prompt", () => {
    expect(parseSlashCommand("/agent")).toEqual({
      kind: "error",
      message: "usage: /agent <id> <prompt>",
    });
    expect(parseSlashCommand("/agent buffett")).toEqual({
      kind: "error",
      message: "usage: /agent <id> <prompt>",
    });
  });

  it("parses /provider <id>", () => {
    expect(parseSlashCommand("/provider anthropic")).toEqual({
      kind: "provider",
      providerId: "anthropic",
    });
  });

  it("parses /key set <provider>", () => {
    expect(parseSlashCommand("/key set anthropic")).toEqual({
      kind: "key-set",
      providerId: "anthropic",
    });
  });

  it("rejects /key without a sub-verb", () => {
    expect(parseSlashCommand("/key")).toEqual({
      kind: "error",
      message: "usage: /key set <provider>",
    });
    expect(parseSlashCommand("/key get anthropic")).toEqual({
      kind: "error",
      message: "usage: /key set <provider>",
    });
  });

  it("recognises /clear and /help", () => {
    expect(parseSlashCommand("/clear")).toEqual({ kind: "clear" });
    expect(parseSlashCommand("/help")).toEqual({ kind: "help" });
  });

  it("flags unknown commands", () => {
    expect(parseSlashCommand("/sell-aapl")).toEqual({
      kind: "error",
      message: "unknown command: /sell-aapl",
    });
  });
});

describe("matchSlash", () => {
  it("opens the picker on a bare slash with the full list in stable order", () => {
    const result = matchSlash("/");
    expect(result.open).toBe(true);
    expect(result.query).toBe("");
    expect(result.matches).toEqual(SLASH_COMMANDS);
  });

  it("is closed when the input does not start with a slash", () => {
    const result = matchSlash("research AAPL");
    expect(result.open).toBe(false);
    expect(result.matches).toEqual([]);
  });

  it("closes once a space is typed (arguments, not command name)", () => {
    const result = matchSlash("/research AAPL");
    expect(result.open).toBe(false);
    expect(result.matches).toEqual([]);
  });

  it("ranks a prefix match first: /res -> /research", () => {
    const result = matchSlash("/res");
    expect(result.open).toBe(true);
    expect(result.matches[0]?.trigger).toBe("research");
  });

  it("is case-insensitive", () => {
    expect(matchSlash("/RES").matches[0]?.trigger).toBe("research");
  });

  it("ranks prefix matches above substring matches", () => {
    // "art" is a substring of "chart" but a prefix of nothing — chart still
    // surfaces, and any prefix match would outrank it.
    const result = matchSlash("/art");
    expect(result.open).toBe(true);
    expect(result.matches.map((c) => c.trigger)).toContain("chart");
  });

  it("still lists commands for a ticker-shaped slash like /AAPL (no space yet)", () => {
    // The picker stays open while typing a command name even if nothing matches
    // a known trigger — the composer decides what to do on a non-match.
    const result = matchSlash("/AAPL");
    expect(result.open).toBe(true);
    expect(result.matches).toEqual([]);
  });
});

describe("parseSlashInvocation", () => {
  it("parses a completed invocation into the def and its args", () => {
    const parsed = parseSlashInvocation("/chart NVDA 1d");
    expect(parsed?.cmd.trigger).toBe("chart");
    expect(parsed?.args).toBe("NVDA 1d");
  });

  it("parses an argless command with an empty args string", () => {
    const parsed = parseSlashInvocation("/portfolio");
    expect(parsed?.cmd.trigger).toBe("portfolio");
    expect(parsed?.args).toBe("");
  });

  it("is case-insensitive on the trigger", () => {
    expect(parseSlashInvocation("/Compare AAPL MSFT")?.cmd.trigger).toBe("compare");
  });

  it("returns null for a ticker-shaped slash (not a known trigger)", () => {
    expect(parseSlashInvocation("/AAPL")).toBeNull();
  });

  it("returns null when the input is not a slash command", () => {
    expect(parseSlashInvocation("research AAPL")).toBeNull();
  });
});

describe("SLASH_COMMANDS registry", () => {
  it("contains all 12 curated commands", () => {
    expect(SLASH_COMMANDS).toHaveLength(12);
    expect(SLASH_COMMANDS.map((c) => c.trigger).sort()).toEqual(
      [
        "chart",
        "clear",
        "compare",
        "deep",
        "deep heavy",
        "export",
        "layout",
        "portfolio",
        "research",
        "screener",
        "sources",
        "watch",
      ].sort(),
    );
  });

  it("has unique triggers", () => {
    const triggers = SLASH_COMMANDS.map((c) => c.trigger);
    expect(new Set(triggers).size).toBe(triggers.length);
  });

  it("assigns the correct dispatch kind to each command", () => {
    const kindOf = (trigger: string) =>
      SLASH_COMMANDS.find((c) => c.trigger === trigger)?.dispatch.kind;
    // Prompt-composing research verbs.
    expect(kindOf("research")).toBe("prompt");
    expect(kindOf("deep")).toBe("prompt");
    expect(kindOf("compare")).toBe("prompt");
    expect(kindOf("screener")).toBe("prompt");
    // Direct frontend actions.
    expect(kindOf("chart")).toBe("action");
    expect(kindOf("watch")).toBe("action");
    expect(kindOf("portfolio")).toBe("action");
    expect(kindOf("layout")).toBe("action");
    expect(kindOf("export")).toBe("action");
    expect(kindOf("sources")).toBe("action");
    expect(kindOf("clear")).toBe("action");
  });

  it("maps action commands to the right SlashAction", () => {
    const actionOf = (trigger: string) => {
      const dispatch = SLASH_COMMANDS.find((c) => c.trigger === trigger)?.dispatch;
      return dispatch?.kind === "action" ? dispatch.action : undefined;
    };
    expect(actionOf("chart")).toBe("chart");
    expect(actionOf("watch")).toBe("watch");
    expect(actionOf("portfolio")).toBe("portfolio");
    expect(actionOf("layout")).toBe("layout");
    expect(actionOf("export")).toBe("export");
    expect(actionOf("sources")).toBe("sources");
    expect(actionOf("clear")).toBe("clear");
  });

  it("composes prompt templates the agent maps to its tools", () => {
    const template = (trigger: string) => {
      const dispatch = SLASH_COMMANDS.find((c) => c.trigger === trigger)?.dispatch;
      return dispatch?.kind === "prompt" ? dispatch.template : undefined;
    };
    expect(template("research")?.("AAPL moat")).toBe("research AAPL moat");
    expect(template("deep")?.("NVDA supply chain")).toBe("/deep — go deeper on NVDA supply chain");
    expect(template("compare")?.("AAPL MSFT")).toBe("compare AAPL MSFT");
    expect(template("screener")?.("low PE high growth")).toBe("screen for low PE high growth");
  });
});
