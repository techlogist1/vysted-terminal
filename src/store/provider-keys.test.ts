import { beforeEach, describe, expect, it, vi } from "vitest";

import { useProviderKeysStore } from "@/store/provider-keys";

const invokeMock = vi.hoisted(() => vi.fn());

vi.mock("@tauri-apps/api/core", () => ({
  invoke: invokeMock,
}));

describe("useProviderKeysStore", () => {
  beforeEach(() => {
    invokeMock.mockReset();
    useProviderKeysStore.setState({ status: {}, probed: false });
  });

  it("probes every provider and records configured/missing", async () => {
    // keychain_get returns a key only for anthropic.
    invokeMock.mockImplementation((_cmd: string, args: { account: string }) =>
      Promise.resolve(args.account === "llm-provider:anthropic" ? "sk-test" : null),
    );
    await useProviderKeysStore.getState().refresh();
    const { status, probed } = useProviderKeysStore.getState();
    expect(probed).toBe(true);
    expect(status.anthropic).toBe("configured");
    expect(status.openai).toBe("missing");
  });

  it("hasAnyKey is true only when a key-requiring provider is configured", async () => {
    invokeMock.mockResolvedValue(null);
    await useProviderKeysStore.getState().refresh();
    expect(useProviderKeysStore.getState().hasAnyKey()).toBe(false);

    // A configured key-requiring provider flips it true.
    useProviderKeysStore.setState((s) => ({ status: { ...s.status, openai: "configured" } }));
    expect(useProviderKeysStore.getState().hasAnyKey()).toBe(true);
  });

  it("a configured no-key provider (ollama) does not count as having an AI key", () => {
    useProviderKeysStore.setState({ status: { ollama: "configured" }, probed: true });
    expect(useProviderKeysStore.getState().hasAnyKey()).toBe(false);
  });

  it("treats a keychain error as 'unknown', never throwing", async () => {
    invokeMock.mockRejectedValue(new Error("no tauri"));
    await useProviderKeysStore.getState().refresh();
    expect(useProviderKeysStore.getState().status.anthropic).toBe("unknown");
    expect(useProviderKeysStore.getState().hasAnyKey()).toBe(false);
  });

  it("refreshOne updates a single provider", async () => {
    invokeMock.mockResolvedValue("sk-x");
    await useProviderKeysStore.getState().refreshOne("groq");
    expect(useProviderKeysStore.getState().status.groq).toBe("configured");
  });
});
