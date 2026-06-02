# Recon — A1:persistence-bug

The diagnosis is fully confirmed. The frontend resolves `provider`/`model` and passes them to the sidecar as overrides (sidecar `_resolve_provider_id` honors the override at line 256-257). So the sidecar honors whatever the frontend sends. The break is entirely on the frontend: the user's persisted `defaultProviderId` is the LOWEST-priority fallback, masked by the active `copilot` agent's pinned `defaultProvider: "ollama"`.

Let me do one last confirmation on whether `agentForCall` for raw chat keeps `activeAgentId` (copilot) — yes, line 452-453 confirms: raw chat with an active agent uses `activeAgentId` (copilot), so `agentSpec` is copilot, so `copilot.defaultProvider` wins. I now have everything. Let me write the blueprint.

I have completed the full round-trip trace. Here is the blueprint.

---

# Default Provider/Model Persistence — Re-Diagnosis Blueprint

## (1) Findings — what exists today (file:line precise)

**The prior "Bug 2 / missing autosave subscription" fix is REAL and PRESENT — it is not the bug.** The default-provider DOES persist to disk:

- `src/lib/workspace.ts:159` — `buildWorkspacePayload` writes `defaultProviderId: useLLMProvidersStore.getState().defaultProviderId` into the blob.
- `src/app/page.tsx:110-114` — autosave subscription on `defaultProviderId` exists and fires.
- `SettingsPanel.tsx:211` and `:904` — both default-provider controls also call `autosaveLayout()` directly.
- `src/lib/workspace.ts:220-222` — `deserializeWorkspace` restores it via `setDefaultProviderId`.

So `defaultProviderId` **does** survive reload into the `llm-providers` store. Distrusting the prior fix was correct in spirit, but the persistence link is intact.

**THE REAL BREAK — agent-default masks the session default (UI-default vs agent-default split-brain):**

- `ChatSidebar.tsx:108` — `DEFAULT_AGENT_ID = "copilot"`.
- `ChatSidebar.tsx:190` — `activeAgentId` defaults to `copilot` on every session; not persisted (it's `useState`, resets each reload to `copilot`).
- `sidecar/agents/copilot.json:41` — **`"defaultProvider": "ollama"`** (a hard pin).
- `ChatSidebar.tsx:471-474` (send path) and `:226-232` (HUD display) resolve:
  `provider = providerOverride ?? agentSpec.defaultProvider ?? defaultProviderId`.

Because the active agent is always `copilot` and `copilot.defaultProvider = "ollama"` is truthy, the user's persisted `defaultProviderId` (e.g. DeepSeek) is the **lowest-priority fallback and is NEVER reached**. `providerOverride` is a per-session `useState` (`:192`) that resets to `null` every reload. So: set DeepSeek as default → reload → `copilot` active → `ollama` wins. The "Default provider" setting is effectively dead for any session running a first-party agent. The sidecar honors the override faithfully (`agent_runtime.py:256-257 _resolve_provider_id` = `override or spec.default_provider`), so the break is 100% frontend resolution-order.

**Secondary break — Default MODEL restore prune (latent, bites non-static models):**

- The "Default model" picker (`SettingsPanel.tsx:927`) writes via `useModelSelectionStore.setModel(defaultProviderId, value)` → `overrides[provider]`. Values come from the LIVE catalog (`model-catalog.ts`).
- On restore, `workspace.ts:252-258` gates on `modelOverridesV === 1` (fine), then `setOverrides` → `pruneRestoredOverrides` → `isKnownModel` (`model-selection.ts:63-87`). For any provider except OpenRouter, a restored model **not in the static `KNOWN_MODELS_BY_PROVIDER` list is silently dropped** to the per-provider default. DeepSeek's live ids (`deepseek-chat`/`deepseek-reasoner`) happen to match, so DeepSeek's model survives — but e.g. an OpenAI `gpt-4o`, a Gemini `gemini-2.0-flash`, or any newer model picked from the live dropdown is pruned on reload. This is a real persistence bug for the default-model picker that the static allow-list causes.
- Even when the model survives, it only matters if the provider survives — which (per the primary break) it usually doesn't for `copilot`.

## (2) Exact change plan

**Edit A — make the persisted session default win over a first-party agent's generic pin (the core fix).** The agent's `defaultProvider` should only override when it is a _deliberate, agent-specific_ choice, not the boilerplate `copilot` pin. Two viable approaches; pick A1 (minimal, safe):

- **A1 (preferred): make `copilot` defer to the session default.** Treat `copilot` (the generic assistant) as having no provider preference so the user's setting flows through.
  - `sidecar/agents/copilot.json:41` — the schema (`_schema.json:8`) _requires_ `defaultProvider`, so you cannot remove it. Instead, in `ChatSidebar.tsx`, define `const GENERIC_AGENT_IDS = new Set(["copilot"])` and change BOTH resolution sites:
    - `:226-232`: `(GENERIC_AGENT_IDS.has(activeAgent?.id ?? "") ? undefined : activeAgent?.defaultProvider) ?? defaultProviderId`
    - `:471-474`: same guard against `agentSpec?.id`.
  - Rationale: persona agents (Buffett=anthropic, researcher=openai) keep their deliberate pin; the generic copilot honors the user's chosen default. This is the smallest blast-radius fix and matches the FR-004 intent comment at `:464`.

- **A2 (alternative, broader): persist `activeAgentId` + a true "session provider default."** Larger; only if the operator wants the HUD provider pick itself to persist. Add `activeAgentId` and `providerOverride` to the blob. Heavier; defer unless asked.

**Edit B — stop the live-catalog default-MODEL prune from dropping valid picks.** In `model-selection.ts`, `isKnownModel` must not prune a model the user explicitly picked from the live catalog. Options:

- **B1 (preferred):** Widen the trust: in `deserializeWorkspace`, the `modelOverridesV === 1` marker already proves the blob was written by a current build — so the prune is redundant defense against the legacy `llama3.1:8b` bug. Change `model-selection.ts:121` `setOverrides` to NOT prune (pass through), OR add a `setOverrides(overrides, { trusted: true })` path called from `workspace.ts:257` that skips `pruneRestoredOverrides`. Keep the prune only for untrusted/legacy blobs (which are already dropped wholesale by the `modelOverridesV` gate at `:252`, so in practice the prune never sees a legacy blob — making it pure collateral damage on live picks).
- **B2 (narrower):** In `isKnownModel`, extend the OpenRouter exemption to "any provider with a live catalog cached" — query `useModelCatalogStore` for the provider's live ids and treat those as known. More correct but couples the stores.

Recommend **B1** (the `modelOverridesV` gate already discharges the legacy-shadowing risk the prune was built for).

**No edits to any Tier-1 locked file.** `copilot.json`, `ChatSidebar.tsx`, `model-selection.ts`, `workspace.ts` are all non-locked.

## (3) Risks + safe fallback

- **A1 risk:** a user who _wants_ copilot on ollama loses the implicit pin. Fallback: the HUD provider override (`:675`) and the persisted `defaultProviderId` both still let them pick ollama; and if `defaultProviderId` is never set it still defaults to `"ollama"` (`llm-providers.ts:130`), so out-of-box behavior is unchanged. Net: strictly more correct.
- **B1 risk:** a model id that genuinely vanished from a provider could be restored and 404 at call time. Fallback: the call surfaces the provider error in the status line (`ChatSidebar.tsx:488-493`); the HUD always shows the selected id (`model-options.ts:29-32` injects it), so the user can re-pick. Acceptable — better than silently reverting the user's explicit choice.
- **Regression risk on persona agents:** A1 must NOT touch persona pins. Verify the `GENERIC_AGENT_IDS` set contains only `copilot`.

## (4) Verification (exact)

**vitest (frontend, fast):**

- `pnpm vitest run src/lib/workspace.test.ts src/store/model-selection.test.ts src/modules/chat/ChatSidebar.test.tsx`
- Add a `ChatSidebar` test: set `useLLMProvidersStore.setState({ defaultProviderId: "deepseek" })`, active agent `copilot`, no HUD override → assert `effectiveProvider === "deepseek"` (today it returns `"ollama"`; the test will FAIL pre-fix, proving the bug, PASS post-fix).
- Add a `model-selection`/`workspace` test: write `modelOverrides: { openai: "gpt-4o" }` + `modelOverridesV: 1`, `deserializeWorkspace`, assert `modelFor("openai") === "gpt-4o"` (FAILs today via prune, PASSes post-B1).

**Manual round-trip (rig, tauri-mcp):**

1. `mcp__tauri-mcp__start_session`; open Settings → set Default provider = DeepSeek, Default model = a live id.
2. `evaluate_script`: read `useLLMProvidersStore.getState().defaultProviderId` → `"deepseek"`.
3. Reload (`navigate` reload / restart). After `restoreLastSessionOrDefault`, re-read store → still `"deepseek"`.
4. `evaluate_script` the ChatSidebar `effectiveProvider` (exposed via dev bridge) or read the model HUD label → must show DeepSeek, not Ollama.
5. Send a turn; confirm the SSE `beginAssistant({ providerId })` (`ChatSidebar.tsx:529`) carries `deepseek`.

**curl (sidecar honors override — sanity only):**

- `curl -s "http://127.0.0.1:<port>/llm/models?provider=deepseek" -H "X-LLM-Key: <key>"` → confirm live ids returned match what the picker offered.

**In short:**

- The prior "missing autosave subscription" fix is present and working — `defaultProviderId` _does_ persist. That was a misdiagnosis of the real failure.
- Real break: `copilot.json` pins `defaultProvider: "ollama"`, and `ChatSidebar` resolves `agent.defaultProvider ?? defaultProviderId`, so the active copilot agent permanently masks the user's persisted session default (`ChatSidebar.tsx:108,190,471-474`).
- Secondary break: the live-catalog default-MODEL pick is pruned on restore by the static `isKnownModel` allow-list (`model-selection.ts:63-121`), even though the `modelOverridesV` gate already makes the prune redundant.
- Fix: have generic `copilot` defer to the session default (Edit A1), and skip the prune for trusted (`modelOverridesV===1`) restores (Edit B1). No Tier-1 file touched.

Confidence: 9/10 on the primary break (copilot pin masks session default — directly traced and matches both symptom halves). 7/10 that the secondary model-prune is also user-visible (depends on whether the specific provider's live ids overlap the static list; DeepSeek's do, so for a pure-DeepSeek repro only Edit A is load-bearing).
