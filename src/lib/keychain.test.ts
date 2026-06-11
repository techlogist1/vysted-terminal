import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  KEYCHAIN_NAMESPACES,
  deleteSecret,
  devKeystoreMigrationAccounts,
  getSecret,
  migrateDevKeystore,
  setSecret,
} from "@/lib/keychain";

const invokeMock = vi.hoisted(() => vi.fn());

vi.mock("@tauri-apps/api/core", () => ({
  invoke: invokeMock,
}));

describe("KEYCHAIN_NAMESPACES", () => {
  it("builds stable llm-provider ids", () => {
    expect(KEYCHAIN_NAMESPACES.llmProvider("anthropic")).toBe("llm-provider:anthropic");
    expect(KEYCHAIN_NAMESPACES.llmProvider("openai")).toBe("llm-provider:openai");
  });

  it("builds stable mcp-server ids", () => {
    expect(KEYCHAIN_NAMESPACES.mcpServer("openbb")).toBe("mcp-server:openbb");
  });

  it("builds plugin-secret ids that include the plugin id and key", () => {
    expect(KEYCHAIN_NAMESPACES.pluginSecret("openbb-mcp", "fmp-api-key")).toBe(
      "plugin-secret:openbb-mcp:fmp-api-key",
    );
  });

  it("builds broker:<id>:<field> ids for Phase 5 broker credentials", () => {
    expect(KEYCHAIN_NAMESPACES.broker("alpaca", "api_key")).toBe("broker:alpaca:api_key");
    expect(KEYCHAIN_NAMESPACES.broker("kite", "access_token")).toBe("broker:kite:access_token");
    expect(KEYCHAIN_NAMESPACES.broker("_meta", "first-launch-tos")).toBe(
      "broker:_meta:first-launch-tos",
    );
  });
});

describe("keychain wrappers", () => {
  beforeEach(() => {
    invokeMock.mockReset();
  });

  it("setSecret invokes keychain_set with account + secret", async () => {
    invokeMock.mockResolvedValueOnce(undefined);
    await setSecret("llm-provider:anthropic", "sk-test");
    expect(invokeMock).toHaveBeenCalledWith("keychain_set", {
      account: "llm-provider:anthropic",
      secret: "sk-test",
    });
  });

  it("getSecret returns the stored value when present", async () => {
    invokeMock.mockResolvedValueOnce("sk-existing");
    const value = await getSecret("llm-provider:openai");
    expect(value).toBe("sk-existing");
    expect(invokeMock).toHaveBeenCalledWith("keychain_get", {
      account: "llm-provider:openai",
    });
  });

  it("getSecret returns null when no value is stored", async () => {
    invokeMock.mockResolvedValueOnce(null);
    expect(await getSecret("llm-provider:groq")).toBeNull();
  });

  it("getSecret normalizes undefined to null", async () => {
    invokeMock.mockResolvedValueOnce(undefined);
    expect(await getSecret("llm-provider:groq")).toBeNull();
  });

  it("deleteSecret invokes keychain_delete with the account", async () => {
    invokeMock.mockResolvedValueOnce(undefined);
    await deleteSecret("llm-provider:gemini");
    expect(invokeMock).toHaveBeenCalledWith("keychain_delete", {
      account: "llm-provider:gemini",
    });
  });
});

describe("migrateDevKeystore (R9 dev keystore)", () => {
  it("invokes keychain_migrate with the candidate account list and returns the report", async () => {
    invokeMock.mockResolvedValueOnce({ backend: "dev-keystore", migrated: 2, already_done: false });
    const report = await migrateDevKeystore();
    expect(report).toEqual({ backend: "dev-keystore", migrated: 2, already_done: false });
    const [cmd, args] = invokeMock.mock.calls.at(-1)!;
    expect(cmd).toBe("keychain_migrate");
    const accounts = (args as { accounts: string[] }).accounts;
    // The four named items the operator listed are always swept.
    expect(accounts).toContain("llm-provider:deepseek");
    expect(accounts).toContain("llm-provider:openrouter");
    expect(accounts).toContain("broker:_meta:first-launch-tos");
    expect(accounts).toContain("app-meta:onboarding-complete");
    // No duplicates (the assembler dedupes via a Set).
    expect(new Set(accounts).size).toBe(accounts.length);
  });

  it("swallows a migration failure (denied dialog) and returns null — never breaks boot", async () => {
    invokeMock.mockRejectedValueOnce(new Error("user denied"));
    await expect(migrateDevKeystore()).resolves.toBeNull();
  });

  it("the candidate list covers every LLM provider id", () => {
    const accounts = devKeystoreMigrationAccounts();
    for (const id of [
      "anthropic",
      "openai",
      "gemini",
      "groq",
      "ollama",
      "deepseek",
      "xai",
      "openrouter",
    ]) {
      expect(accounts).toContain(`llm-provider:${id}`);
    }
  });
});
