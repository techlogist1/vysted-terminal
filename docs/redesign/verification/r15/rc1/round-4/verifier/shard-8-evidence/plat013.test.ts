import { describe, it, expect } from "vitest";
import { useModulesStore } from "@/store/modules";
import { PERSISTED_SLICES, serializeWorkspace } from "@/lib/workspace";
import { CATALOG_BY_ID } from "@/lib/marketplace";
import { moduleForPlugin, enabledByDefault } from "@/lib/plugin-bootstrap";

const slice = PERSISTED_SLICES.find((s) => s.key === "enabledModules")!;
const bridge = (id: string, on: boolean) => {
  const mod = moduleForPlugin(CATALOG_BY_ID[id]!)!;
  useModulesStore.getState().appendModules([mod]);
  useModulesStore.getState().setModuleEnabled(mod.id, on);
  return mod.id;
};

describe("R15-CODE-PLATFORM-013 verifier shard 8", () => {
  const ids = Object.keys(CATALOG_BY_ID).filter((id) => moduleForPlugin(CATALOG_BY_ID[id]!));
  it("lists bridgeable plugins", () => { console.log("bridgeable:", ids.join(","), "defaults:", ids.map((i) => `${i}=${enabledByDefault(i)}`).join(",")); expect(ids.length).toBeGreaterThan(0); });
  it.each(ids)("literal: restoring an older blob with plugin:%s=false keeps a re-enabled plugin on", (id) => {
    const key = bridge(id, true);
    slice.restore({ enabledModules: { [key]: false, news: false } } as never);
    const e = useModulesStore.getState().enabled;
    console.log("restore", id, e[key], e.news);
    expect(e[key]).toBe(true);
    expect(e.news).toBe(false);
  });
  it.each(ids)("fresh: settings-import/reset never flips plugin:%s either way", (id) => {
    const key = bridge(id, false);
    useModulesStore.getState().setEnabledMap({ ...useModulesStore.getState().enabled, [key]: true });
    expect(useModulesStore.getState().enabled[key]).toBe(false);
    useModulesStore.getState().setEnabledMap({});
    expect(useModulesStore.getState().enabled[key]).toBe(false);
    bridge(id, true);
    useModulesStore.getState().setEnabledMap({});
    expect(useModulesStore.getState().enabled[key]).toBe(true);
  });
  it("fresh: the serialized blob carries no plugin:* flag", () => {
    const blob = slice.read() as { enabledModules: Record<string, boolean> };
    console.log("blob keys", Object.keys(blob.enabledModules));
    expect(Object.keys(blob.enabledModules).some((k) => k.startsWith("plugin:"))).toBe(false);
  });
});
