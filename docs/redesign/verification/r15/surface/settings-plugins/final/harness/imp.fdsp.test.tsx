import { vi, test } from "vitest";
import { invokeShim } from "./mocks";
vi.mock("@tauri-apps/api/core", () => ({ invoke: (cmd: string, args?: Record<string, unknown>) => invokeShim(cmd, args) }));
test("imp settings", async () => { const t = Date.now(); await import("@/components/SettingsPanel"); console.log("SettingsPanel", Date.now() - t); });
test("imp modules", async () => { const t = Date.now(); await import("@/modules"); console.log("modules", Date.now() - t); });
test("imp rtl", async () => { const t = Date.now(); await import("@testing-library/react"); console.log("rtl", Date.now() - t); });
