import { describe, expect, it } from "vitest";

import { examplePlugin } from "./index";
import manifest from "./manifest.json";

import type { PluginManifest } from "../../types/plugin-runtime";

describe("example plugin", () => {
  it("manifest matches the plugin instance identity", () => {
    const typed = manifest as PluginManifest;
    expect(typed.id).toBe(examplePlugin.pluginId);
    expect(typed.version).toBe(examplePlugin.version);
    expect(typed.name).toBe(examplePlugin.pluginName);
  });

  it("declares contributesData and contributesCommands", () => {
    expect(examplePlugin.capabilities.contributesData).toBe(true);
    expect(examplePlugin.capabilities.contributesCommands).toBe(true);
  });

  it("getDataSources returns at least one DataSource with a stable id", () => {
    const sources = examplePlugin.getDataSources?.() ?? [];
    expect(sources.length).toBeGreaterThan(0);
    expect(sources[0].id).toBe("example-prices");
    expect(sources[0].kinds).toContain("equity");
  });

  it("getCommands returns at least one CommandSpec wired to executeCommand", () => {
    const commands = examplePlugin.getCommands?.() ?? [];
    expect(commands.length).toBeGreaterThan(0);
    expect(commands[0].commandId).toBe("example.hello");
  });

  it("healthCheck is `unavailable` before initialize and `healthy` after", async () => {
    await examplePlugin.shutdown();
    const before = await examplePlugin.healthCheck();
    expect(before.status).toBe("unavailable");

    await examplePlugin.initialize({
      dataDir: "/tmp/example",
      settings: {},
      sidecarBaseUrl: "http://127.0.0.1:0",
      hostVersion: "0.3.0",
      secrets: {},
    });
    const after = await examplePlugin.healthCheck();
    expect(after.status).toBe("healthy");

    await examplePlugin.shutdown();
  });

  it("executeCommand handles the hello command and rejects unknown ids", async () => {
    const ok = await examplePlugin.executeCommand?.("example.hello", undefined);
    expect(ok?.ok).toBe(true);
    const fail = await examplePlugin.executeCommand?.("does.not.exist", undefined);
    expect(fail?.ok).toBe(false);
    expect(fail?.error).toContain("unknown command");
  });
});
