import { beforeEach, describe, expect, it, vi } from "vitest";

import { KEYCHAIN_NAMESPACES, deleteSecret, getSecret, setSecret } from "@/lib/keychain";

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
