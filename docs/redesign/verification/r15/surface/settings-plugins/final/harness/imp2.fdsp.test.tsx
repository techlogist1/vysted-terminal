import { vi, test } from "vitest";
import fs from "fs";
import { render, fireEvent, cleanup, within, act } from "@testing-library/react";
import { invokeShim, KEYCHAIN, INVOKES, FETCHES, sleep, text } from "./mocks";

vi.mock("@tauri-apps/api/core", () => ({ invoke: (cmd: string, args?: Record<string, unknown>) => invokeShim(cmd, args) }));

import { SettingsPanel, buildSettingsExport } from "@/components/SettingsPanel";
import { useProviderKeysStore } from "@/store/provider-keys";
import { useSearchSettingsStore } from "@/store/search-settings";
import { useSettingsStore } from "@/store/settings";
import { useKeybindingsStore, matchesEvent } from "@/store/keybindings";
import { useWorkspaceStore } from "@/store/workspace";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModulesStore } from "@/store/modules";


test("imports ok", () => { console.log("loaded", typeof SettingsPanel, typeof matchesEvent); });
