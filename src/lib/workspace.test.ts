import type { SerializedDockview } from "dockview";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useModulesStore } from "@/store/modules";
import { useWorkspaceStore } from "@/store/workspace";

// The sidecar client reaches into Tauri's `invoke`; stub it so `getSidecarBaseUrl`
// resolves without a desktop runtime.
vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:51763"),
}));

import {
  deserializeWorkspace,
  loadWorkspace,
  saveWorkspace,
  serializeWorkspace,
  type SerializedWorkspace,
} from "@/lib/workspace";

/** A minimal fake dockview layout — `toJSON`/`fromJSON` round-trip its state. */
function createFakeDockviewApi(initial: SerializedDockview) {
  let layout = initial;
  return {
    toJSON: () => layout,
    fromJSON: (next: SerializedDockview) => {
      layout = next;
    },
    get current() {
      return layout;
    },
  };
}

const LAYOUT_A = { grid: { root: "a" }, panels: { chart: {} } } as unknown as SerializedDockview;
const LAYOUT_B = { grid: { root: "b" }, panels: { news: {} } } as unknown as SerializedDockview;

describe("workspace serialization", () => {
  beforeEach(() => {
    useModulesStore.setState({ modules: [], enabled: {} });
    useWorkspaceStore.setState({ name: "default", dockviewApi: null });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("serializeWorkspace captures the dockview layout and the enabled map", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    useModulesStore.setState({ enabled: { chart: true, news: false, platform: true } });

    const workspace = serializeWorkspace("research");

    expect(workspace).toEqual({
      name: "research",
      layout: LAYOUT_A,
      enabledModules: { chart: true, news: false, platform: true },
    });
  });

  it("round-trips: serialize then deserialize restores the layout and enabled map", () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    useModulesStore.setState({ enabled: { chart: true, news: false, platform: true } });

    const saved = serializeWorkspace("research");

    // Mutate the live state away from what was saved...
    fakeApi.fromJSON(LAYOUT_B);
    useModulesStore.setState({ enabled: { chart: false, news: true, platform: true } });
    useWorkspaceStore.setState({ name: "scratch" });

    // ...then deserialize and assert the saved state is restored exactly.
    deserializeWorkspace(saved);

    expect(fakeApi.current).toEqual(LAYOUT_A);
    expect(useModulesStore.getState().enabled).toEqual(saved.enabledModules);
    expect(useWorkspaceStore.getState().name).toBe("research");
  });

  it("serializeWorkspace throws when the dockview layout is not ready", () => {
    expect(() => serializeWorkspace("research")).toThrow(/not ready/);
  });

  it("saveWorkspace POSTs the serialized workspace to the sidecar", async () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_A);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });
    useModulesStore.setState({ enabled: { chart: true, platform: true } });

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 200 }));

    await saveWorkspace("research");

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("http://127.0.0.1:51763/workspace");
    expect(init?.method).toBe("POST");
    const body = JSON.parse(init?.body as string) as {
      name: string;
      workspace: SerializedWorkspace;
    };
    expect(body.name).toBe("research");
    expect(body.workspace.layout).toEqual(LAYOUT_A);
    expect(body.workspace.enabledModules).toEqual({ chart: true, platform: true });
  });

  it("loadWorkspace fetches from the sidecar and applies the workspace", async () => {
    const fakeApi = createFakeDockviewApi(LAYOUT_B);
    useWorkspaceStore.setState({ dockviewApi: fakeApi as never });

    const stored: SerializedWorkspace = {
      name: "research",
      layout: LAYOUT_A,
      enabledModules: { chart: true, news: false, platform: true },
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(stored), { status: 200 }),
    );

    await loadWorkspace("research");

    expect(fakeApi.current).toEqual(LAYOUT_A);
    expect(useModulesStore.getState().enabled).toEqual(stored.enabledModules);
    expect(useWorkspaceStore.getState().name).toBe("research");
  });

  it("saveWorkspace rejects an empty name", async () => {
    await expect(saveWorkspace("   ")).rejects.toThrow(/name is required/);
  });
});
