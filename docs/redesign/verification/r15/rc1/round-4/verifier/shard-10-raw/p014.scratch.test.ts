const setSecretMock = vi.hoisted(() => vi.fn(async (_a: string, _v: string) => undefined));
const store = vi.hoisted(() => new Map<string, string>());
const getSecretMock = vi.hoisted(() => vi.fn(async (a: string) => store.get(a) ?? null));
const deleteSecretMock = vi.hoisted(() => vi.fn(async (a: string) => { store.delete(a); }));
vi.mock("@/lib/keychain", async () => {
  const actual: any = await vi.importActual("@/lib/keychain");
  return { ...actual, getSecret: getSecretMock, setSecret: vi.fn(async (a: string, v: string) => { store.set(a, v); }), deleteSecret: deleteSecretMock };
});
vi.mock("@/lib/sidecar-client", async () => {
  const actual: any = await vi.importActual("@/lib/sidecar-client");
  return { ...actual, sidecarGet: vi.fn(async () => ({ newsapi: "ok" })) };
});
import { CATALOG_BY_ID } from "@/lib/marketplace";
import { pluginHost } from "@/lib/plugin-bootstrap";
import { PluginRuntime } from "@/lib/plugin-runtime";
import { resetMarketplaceStoreForTests, useMarketplaceStore } from "@/store/marketplace";
import { usePluginsStore } from "@/store/plugins";

function fresh() {
  resetMarketplaceStoreForTests();
  usePluginsStore.setState({ plugins: [], dataSources: [], agents: [], nodes: [], runtime: null } as any);
  store.clear();
  const runtime = new PluginRuntime({
    hostVersion: "0.8.0", host: pluginHost,
    resolveSecrets: async (ids: string[]) => { const r: Record<string,string> = {}; for (const id of ids) { const v = store.get(id); if (v) r[id] = v; } return r; },
  } as any);
  usePluginsStore.getState().attachRuntime(runtime);
  return runtime;
}
const ACC = "plugin-secret:vysted-news:newsapi_key";

it("active plugin: configure delivers the NEW secret value to initialize; a re-key delivers the second value", async () => {
  fresh();
  await useMarketplaceStore.getState().install("vysted-news");
  const init = vi.spyOn(CATALOG_BY_ID["vysted-news"].discovered.instance, "initialize");
  await useMarketplaceStore.getState().configure("vysted-news", { newsapi_key: "first" });
  await useMarketplaceStore.getState().configure("vysted-news", { newsapi_key: "second" });
  console.log("INIT_SECRETS", JSON.stringify(init.mock.calls.map((c: any) => c[0].secrets)));
  expect(init).toHaveBeenCalledTimes(2);
  expect(init.mock.calls[0][0].secrets[ACC]).toBe("first");
  expect(init.mock.calls[1][0].secrets[ACC]).toBe("second");
  expect(useMarketplaceStore.getState().stateFor("vysted-news").runtimeState).toBe("active");
  init.mockRestore();
});

it("disabled plugin: configure does NOT start it", async () => {
  fresh();
  await useMarketplaceStore.getState().install("vysted-news");
  await useMarketplaceStore.getState().disable("vysted-news");
  const init = vi.spyOn(CATALOG_BY_ID["vysted-news"].discovered.instance, "initialize");
  await useMarketplaceStore.getState().configure("vysted-news", { newsapi_key: "k" });
  console.log("DISABLED_STATE", useMarketplaceStore.getState().stateFor("vysted-news").runtimeState, init.mock.calls.length);
  expect(init).not.toHaveBeenCalled();
  init.mockRestore();
});
