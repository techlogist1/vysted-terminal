import { writeFileSync } from "node:fs";
import { it, vi, beforeEach } from "vitest";
import { render, fireEvent, act, cleanup } from "@testing-library/react";

const kc = new Map<string, string>();
const meta = new Map<string, string>();
const log: string[] = [];
let denyKeychain = false;
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async (cmd: string, args: Record<string, string>) => {
    log.push(`${cmd} ${args?.account ?? args?.key ?? ""}`);
    if (cmd.startsWith("keychain_") && denyKeychain) throw new Error("User interaction is not allowed.");
    if (cmd === "keychain_get") return kc.get(args.account) ?? null;
    if (cmd === "keychain_set") { kc.set(args.account, args.secret); return null; }
    if (cmd === "keychain_delete") { kc.delete(args.account); return null; }
    if (cmd === "app_meta_get") return meta.get(args.key) ?? null;
    if (cmd === "app_meta_set") { meta.set(args.key, args.value); return null; }
    return null;
  }),
}));
const opened: string[] = [];
vi.mock("@tauri-apps/plugin-shell", () => ({ open: vi.fn(async (u: string) => { opened.push(u); }) }));

import { OnboardingBanner } from "@/components/OnboardingBanner";
import { DisclaimerFlow } from "@/modules/safety/DisclaimerFlow";
import { OnboardingFlow } from "@/components/OnboardingFlow";
import { useSafetyStore } from "@/store/safety";
import { useOnboardingStore } from "@/store/onboarding";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModelSelectionStore } from "@/store/model-selection";
import { useProviderKeysStore } from "@/store/provider-keys";
import { __resetProviderProbeCacheForTests } from "@/lib/provider-validation";
import { useSymbolsStore } from "@/store/symbols";
import { modelForProvider } from "@/store/model-selection";
import { DEFAULT_CHART_SYMBOL } from "@/store/chart-drawings";

const OUT = process.env.FP_OUT ?? "/tmp/fp-onb.json";
const out: Record<string, unknown> = {};
const txt = (el: Element | null) => (el?.textContent ?? "").replace(/\s+/g, " ").trim().slice(0, 3000);
const wait = (ms: number) => act(async () => { await new Promise((r) => setTimeout(r, ms)); });
const body = () => txt(document.body);
const btn = (re: RegExp) => Array.from(document.querySelectorAll("button")).find((b) => re.test(b.getAttribute("aria-label") || b.textContent || ""));
const fetches: string[] = [];
const realFetch = globalThis.fetch;
let stubOllamaDown = false;
globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
  const u = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
  if (stubOllamaDown && u.includes("/system/ollama/status")) {
    fetches.push(`${init?.method ?? "GET"} ${u.replace(/^http:\/\/127\.0\.0\.1:\d+/, "")} -> STUB running:false`);
    return new Response(JSON.stringify({ running: false, endpoint: "http://127.0.0.1:11434", models: [] }), { status: 200, headers: { "Content-Type": "application/json" } });
  }
  const r = await realFetch(input, init);
  let extra = "";
  if (u.includes("/llm/keys/validate")) extra = " " + (await r.clone().text()).slice(0, 160) + " req=" + String(init?.body).replace(/sk-[^"]*/g, "<fake>");
  fetches.push(`${init?.method ?? "GET"} ${u.replace(/^http:\/\/127\.0\.0\.1:\d+/, "")} -> ${r.status}${extra}`);
  return r;
}) as typeof fetch;

function resetStores() {
  cleanup();
  useSafetyStore.setState({ firstLaunchTosAcked: false });
  useOnboardingStore.setState({ seen: null, bannerDismissed: null, forceOpen: false, forceStep: null });
  __resetProviderProbeCacheForTests();
}
const shell = () => render(<><OnboardingBanner /><DisclaimerFlow /><OnboardingFlow /></>);
const snap = (k: string, extra: Record<string, unknown> = {}) => {
  out[k] = { text: body(), tos: !!document.querySelector('[data-testid="first-launch-tos-dialog"]'), onboarding: !!document.querySelector('[data-testid="onboarding-flow"]'), banner: !!document.querySelector('[role="status"]'), kc: [...kc.keys()], meta: Object.fromEntries(meta), opened: [...opened], defaultProvider: useLLMProvidersStore.getState().defaultProviderId, ...extra };
};
beforeEach(() => { fetches.length = 0; });

it("stranger first run on a clean profile", async () => {
  out.defaults = { chart: DEFAULT_CHART_SYMBOL, watchlist: useSymbolsStore.getState().entries.map((e) => e.symbol), defaultProvider: useLLMProvidersStore.getState().defaultProviderId, ollamaModel: modelForProvider("ollama") };
  // T1 first boot
  resetStores(); shell(); await wait(4000);
  snap("T1_first_boot", { fetches: [...fetches] });
  // T2 accept terms
  const accept = document.querySelector('[data-testid="first-launch-tos-accept"]') as HTMLElement | null;
  if (accept) { await act(async () => { fireEvent.click(accept); }); }
  await wait(1500);
  snap("T2_after_accept");
  // T3 escape on welcome
  await act(async () => { fireEvent.keyDown(document.activeElement ?? document.body, { key: "Escape" }); });
  await wait(500);
  snap("T3_after_escape");
  // T4 cloud path
  const cloud = btn(/Add a key/); if (cloud) await act(async () => { fireEvent.click(cloud); }); await wait(800);
  const input = document.querySelector('input[aria-label="OpenRouter API key"]') as HTMLInputElement | null;
  const save = () => btn(/Save & continue|Validating/) as HTMLButtonElement | undefined;
  const cloudState: Record<string, unknown> = { stepText: body(), saveDisabledEmpty: save()?.disabled };
  if (input) {
    fireEvent.change(input, { target: { value: "   " } }); await wait(100);
    cloudState.saveDisabledWhitespace = save()?.disabled;
    const getKey = btn(/Get a key/); if (getKey) await act(async () => { fireEvent.click(getKey); }); await wait(300);
    fireEvent.change(input, { target: { value: "sk-or-v1-" + "0".repeat(40) + "notarealkey" } });
    await act(async () => { fireEvent.submit(input.closest("form")!); }); await wait(4000);
    cloudState.fakeKey = body();
    fireEvent.change(input, { target: { value: "sk-or-v1-" + "0".repeat(40) + "notarealkey  \n" } });
    await act(async () => { fireEvent.submit(input.closest("form")!); }); await wait(4000);
    cloudState.fakeKeyTrailing = body();
    cloudState.kcAfter = [...kc.keys()];
    cloudState.providerAfter = useLLMProvidersStore.getState().defaultProviderId;
  }
  cloudState.fetches = [...fetches]; cloudState.opened = [...opened];
  out.T4_cloud = cloudState;
  const back = btn(/^Back$/); if (back) await act(async () => { fireEvent.click(back); }); await wait(600);
  // T5 local path
  fetches.length = 0;
  const local = btn(/Set up local AI/); if (local) await act(async () => { fireEvent.click(local); }); await wait(500);
  const localLoading = body();
  await wait(5000);
  snap("T5_local", { loadingText: localLoading.slice(0, 300), fetches: [...fetches] });
  const use = btn(/^\s*Use /); if (use) await act(async () => { fireEvent.click(use); }); await wait(1500);
  snap("T5_done", { model: modelForProvider("ollama") });
  const start = btn(/Start exploring/); if (start) await act(async () => { fireEvent.click(start); }); await wait(800);
  snap("T5_closed");
  // T6 relaunch with the same keychain + app-meta
  resetStores(); fetches.length = 0; shell(); await wait(4000);
  snap("T6_relaunch", { fetches: [...fetches] });
  // T7 CTA re-open at the local step after seen
  await act(async () => { useOnboardingStore.getState().open("local"); }); await wait(4000);
  await wait(4000); snap("T7_cta_local");
  // T8 skip path on a second clean profile
  resetStores(); kc.clear(); meta.clear(); opened.length = 0;
  useLLMProvidersStore.setState({ defaultProviderId: "ollama" });
  shell(); await wait(3000);
  const acc2 = document.querySelector('[data-testid="first-launch-tos-accept"]') as HTMLElement | null;
  if (acc2) await act(async () => { fireEvent.click(acc2); }); await wait(1200);
  const skip = btn(/Skip/); if (skip) await act(async () => { fireEvent.click(skip); }); await wait(1000);
  snap("T8_skip");
  // T9 banner: keyless default whose model is not pulled
  resetStores(); fetches.length = 0;
  useModelSelectionStore.getState().setModel("ollama", "llama3.1:70b-not-pulled-xyz");
  shell(); await wait(5000);
  snap("T9_banner_not_pulled", { fetches: [...fetches] });
  const dismiss = btn(/^\s*Dismiss\s*$/); if (dismiss) await act(async () => { fireEvent.click(dismiss); }); await wait(500);
  snap("T9_banner_dismissed");
  // T10 Ollama-not-running branch (status STUBBED running:false; everything else real)
  resetStores(); stubOllamaDown = true; useModelSelectionStore.getState().setModel("ollama", "qwen3:8b");
  shell(); await wait(2500);
  await act(async () => { useOnboardingStore.getState().open("local"); }); await wait(5000);
  snap("T10_ollama_down_stub", { fetches: [...fetches] });
  const recheck = btn(/re-check/); stubOllamaDown = false;
  if (recheck) await act(async () => { fireEvent.click(recheck); }); await wait(4000);
  snap("T10_recheck_up");
  // T11 keychain denied on a third clean profile
  resetStores(); kc.clear(); meta.clear(); denyKeychain = true;
  const errs: string[] = [];
  const onRej = (e: PromiseRejectionEvent | unknown) => errs.push(String((e as { reason?: unknown }).reason ?? e));
  process.on("unhandledRejection", onRej);
  shell(); await wait(4000);
  snap("T11_keychain_denied", { unhandled: errs });
  process.off("unhandledRejection", onRej);
  denyKeychain = false;
  out.invokeLog = log;
  writeFileSync(OUT, JSON.stringify(out, null, 2));
}, 110_000);
