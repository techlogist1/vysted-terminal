import { describe, expect, it } from "vitest";

import { parseSlashCommand } from "./slash-commands";

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
