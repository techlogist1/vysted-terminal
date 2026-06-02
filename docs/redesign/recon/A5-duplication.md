# Recon — A5:duplication

I now have confirmed findings. The empty-state JSX is varied phrasing/styling (per-panel one-liners) — that's trivial 1-line repeats, not worth flagging per the project rule. The AgentHud (54-62) and SettingsPanel (843-850) have **identical 8-line catalog-merge logic** (live → knownModels → static fallback → map to options). That's a real duplication. Let me do one final confirmation of the `_register_v0_6_5` stub being a true no-op and verify the workspace finding count for the SSE encoders. I have enough to write the blueprint.

The duplications are confirmed. Producing the blueprint.

---

# Duplication Audit — Vysted Terminal (read-only blueprint for lead)

## (1) Findings — what exists today, file:line precise

**D1 — Provider/model lists STILL triplicated (highest payoff; the aa4b193 collapse was incomplete).**
The same 8-provider × (defaultModel + knownModels) table exists in **three** places that must hand-sync or drift:

- `sidecar/config/model_registry.json` (lines 3-77) — the declared _single source of truth_ (its own `_comment` says the frontend tables are "an offline fallback only").
- `src/store/llm-providers.ts:40-108` — `DEFAULT_PROVIDERS` (id/label/requiresKey/defaultBaseUrl/defaultModel/knownModels).
- `src/store/model-selection.ts:23-32` (`DEFAULT_MODEL_BY_PROVIDER`) **and** `:39-55` (`KNOWN_MODELS_BY_PROVIDER`) — a _second_ frontend copy of the same defaultModel + knownModels data, byte-identical to `DEFAULT_PROVIDERS` (anthropic `claude-opus-4-8`, openrouter 6-model list, etc.).

So the frontend alone holds the list **twice** (`llm-providers` + `model-selection`), and the sidecar a third time. aa4b193 added the _live_ `model-catalog.ts` store but left both static tables. The two frontend copies are already consumed independently: `llm-providers` via `DEFAULT_PROVIDERS`/`provider-keys.ts:50,61`; `model-selection` via `KNOWN_MODELS_BY_PROVIDER` in `AgentHud.tsx:58` and `SettingsPanel.tsx:846`, plus `DEFAULT_MODEL_BY_PROVIDER` in `resolveModel` (`model-selection.ts:95`) and `workspace.test.ts:187`. **No live-catalog conflict** — both are correctly used only as pre-fetch fallbacks — but the two static copies _will_ drift (e.g. someone edits one openrouter list, not the other).

**D2 — SSE `_encode_event` / `_encode_event_dict` duplicated across 4 routers (2 dead).**

- `sidecar/routers/llm.py:143-150` — `_encode_event` + `_encode_event_dict` (both used: encode + error/done frames at `:132-133`).
- `sidecar/routers/agents.py:86-91` — verbatim copy (both used: `:75-76,87`).
- `sidecar/routers/workflow.py:116-121` — `_encode_event` uses `model_dump_json(by_alias=True, exclude_none=True)`; `_encode_event_dict` (`:120`) marked `# pragma: no cover - kept for parity` — **dead, zero call sites**.
- `sidecar/routers/backtest.py:138-143` — same as workflow; `_encode_event_dict` (`:142`) **dead**.

Two encode flavors exist: plain `model_dump()` (llm/agents, `LLMStreamEvent`) vs `model_dump_json(by_alias, exclude_none)` (workflow/backtest). The `_encode_event_dict` (dict→frame) helper is genuinely shared logic; the two unused copies are pure dead code.

**D3 — `main.py` re-implements `app.py`'s three registration helpers instead of calling them.**

- `sidecar/app.py:131-170` defines `_register_v0_5_0_runtime_extensions`, `_register_v0_6_0_runtime_extensions`, `_register_v0_6_5_runtime_extensions`; `create_app` calls them (`:260,266,271`).
- `sidecar/main.py:53-68` inside `_register_runtime_extensions` **inlines the identical bodies** (`backtest_strategies.register_all()` + `agent_tools.register_v0_5_0_tools()`; `register_v0_6_0_tools()` + `registry_v0_6_0.register_v0_6_0_nodes()`; `registry_v0_6_5.register_v0_6_5_tools()`) rather than importing+calling the three named helpers. Two copies of the per-release registration list that must stay in lockstep when a phase's tool set changes.

**D4 — Catalog-merge "live → knownModels → static-map → option[]" duplicated verbatim in two components.**

- `src/modules/chat/AgentHud.tsx:54-62`
- `src/components/SettingsPanel.tsx:843-850`

Both compute: `info.knownModels?.length ? info.knownModels : (KNOWN_MODELS_BY_PROVIDER[p] ?? [])`, then `modelOptions?.length ? modelOptions : fallback.map(id => ({id, label:id}))`, then hand off to `buildModelGroups`. Same 3-tier fallback ladder, two sites. `model-options.ts` already exists as the home for this; only the _grouping_ half was extracted, not the _resolution_ half.

**D5 — Compact-magnitude / number formatting re-implemented in screener (and earnings), bypassing region-aware `format.ts`.**

- `src/lib/format.ts` exports `formatCompactMoney`, `formatCompactNumber`, `formatPercent` — region/locale-aware (`activeLocale()`, `activeCurrency()`).
- `src/modules/screener/ScreenerResultsTable.tsx:35-56` re-implements `fmtMarketCap` (T/B/M), `fmtNumber`, `fmtVolume` (M/K) with hardcoded `"en-US"` and bare numerics — duplicates the abbreviation ladder in `format.ts:39-48` and ignores region.
- `src/modules/earnings/EarningsCalendarPanel.tsx:33` and `analyst-ratings/IndividualAnalystTable.tsx:31` hardcode `toLocaleString("en-US", …)` — same locale-bypass, lighter.

This is the one functional-bug duplication: a non-US region renders correct currency in portfolio but `en-US` grouping in screener/earnings.

**NOT duplications (checked, excluded):**

- **Workspace payload assembly** — _already collapsed_. `buildWorkspacePayload` (`workspace.ts:149-178`) is the single source; `serializeWorkspace:185` and `autosaveLayout:430` both call it. The lead's note is stale — no action.
- **Analyst-ratings aggregation** across `yfinance_provider.py:209`, `openbb_mcp_provider.py:476`, `provider_registry.py:360`, `fundamentals.py:67` — these are _provider adapters_ with different upstream shapes behind one registry seam. Correct pattern, not duplication.
- Per-panel empty-state JSX (`"No … yet"`, em-dash cells) — varied 1-liners, trivial; project rule says leave it.

## (2) Exact change plan

**D1 (frontend list de-dup):** Make `model-selection.ts` _derive_ from `llm-providers.ts` instead of re-declaring. In `src/store/model-selection.ts`, delete `DEFAULT_MODEL_BY_PROVIDER` (23-32) and `KNOWN_MODELS_BY_PROVIDER` (39-55); replace with derived readers off `DEFAULT_PROVIDERS`:

```ts
import { DEFAULT_PROVIDERS } from "@/store/llm-providers";
export const DEFAULT_MODEL_BY_PROVIDER = Object.fromEntries(
  DEFAULT_PROVIDERS.map((p) => [p.id, p.defaultModel ?? "—"]),
) as Record<LLMProviderId, string>;
export const KNOWN_MODELS_BY_PROVIDER = Object.fromEntries(
  DEFAULT_PROVIDERS.map((p) => [p.id, p.knownModels ?? []]),
) as Record<LLMProviderId, readonly string[]>;
```

Consumers (`AgentHud:58`, `SettingsPanel:846`, `resolveModel:95`, tests) keep working unchanged — same exported names/shapes. This leaves **one** frontend copy (`DEFAULT_PROVIDERS`) + the JSON. (Generating the frontend table _from_ `model_registry.json` at build time is the full fix but needs a codegen step + build wiring — out of scope for a de-dup pass; collapsing 3→2 with zero new build infra is the right altitude.)

**D2:** Create `sidecar/routers/_sse.py` with one `encode_sse(payload: dict) -> bytes` (`f"data: {json.dumps(payload)}\n\n".encode()`) plus a thin `encode_event(event, *, by_alias=False)` that branches between `model_dump()` and `model_dump_json(by_alias=True, exclude_none=True)`. In `llm.py`/`agents.py` import and drop the two local defs; in `workflow.py`/`backtest.py` import `encode_event(..., by_alias=True)` and **delete both dead `_encode_event_dict`** (`workflow.py:120-121`, `backtest.py:142-143`). Net: 4 sites → 1 module, 2 dead funcs gone.

**D3:** In `sidecar/main.py:53-68`, replace the inlined bodies with imports+calls of the three `app.py` helpers (`from app import _register_v0_5_0_runtime_extensions, _register_v0_6_0_runtime_extensions, _register_v0_6_5_runtime_extensions`) — or, cleaner, add one `app.register_all_runtime_extensions()` in `app.py` that `create_app` and `main.py` both call. Keep `workflow_nodes.register_all()` (main-only, by design — `main.py:46`) outside it.

**D4:** Add to `src/lib/model-options.ts`:

```ts
export function resolveModelOptions(
  info: LLMProviderInfo | undefined,
  provider: LLMProviderId,
  liveModels: LLMModelOption[] | undefined,
): LLMModelOption[] {
  /* the 8-line ladder */
}
```

Call it in `AgentHud.tsx:54-62` and `SettingsPanel.tsx:843-850`, deleting both inline blocks.

**D5:** In `ScreenerResultsTable.tsx`, delete `fmtMarketCap`/`fmtVolume` (35-41, 51-56), import `formatCompactMoney`/`formatCompactNumber` from `@/lib/format`; keep `fmtNumber` only if a fixed-digit need isn't covered (it isn't — leave it, but switch its `"en-US"` to `activeLocale` via a `format.ts` `formatFixed` export if you want region-correctness). Convert `EarningsCalendarPanel.tsx:33` and `IndividualAnalystTable.tsx:31` to `format.ts` helpers.

## (3) Risks + safe fallback

- **D1:** Circular import risk (`model-selection` ↔ `llm-providers`). `llm-providers` does _not_ import `model-selection`, so the one-way import is safe; if a cycle ever appears, fallback is to keep the literals but add a `model-list.test.ts` asserting all three tables match `model_registry.json` (drift _guard_ instead of de-dup).
- **D2:** `by_alias`/`exclude_none` divergence is load-bearing (the Gemini `metadata["name"]` pairing in CLAUDE.md). Keep the two flavors as one branched function — do **not** unify llm/agents onto `by_alias=True`. Fallback: leave llm/agents untouched, only kill the 2 dead `_encode_event_dict`.
- **D3:** Import-time side-effect ordering — `app.py` helpers are idempotent (overwrite-by-id, per their docstrings) so re-call order is safe. Fallback: a one-line module-level guard is unnecessary; if anything breaks, revert `main.py` only.
- **D4/D5:** Pure refactor, no behavior change for US. D5 _changes_ screener output for non-US regions (en-US → region locale) — that's a fix, but flag it; fallback is to pass explicit `"en-US"` into the shared helper to preserve byte-identical output if the operator wants zero visual change.
- None of D1–D5 touch any Tier-1 locked file (verified: no edits to safety/broker/plugin/kill_switch/CI/tauri.conf).

## (4) Verification

- **D1:** `pnpm vitest run src/store/model-selection.test.ts src/lib/workspace.test.ts src/store/provider-keys.test.ts` (consume both tables); add an assertion that `Object.keys(DEFAULT_MODEL_BY_PROVIDER)` matches `DEFAULT_PROVIDERS.map(p=>p.id)`. Then `pnpm typecheck`.
- **D2:** `cd sidecar && python -m pytest tests/test_llm_router.py tests/test_agents_router.py tests/test_workflow_router.py tests/test_backtest_router.py -q` (run in background per CLAUDE.md long-cmd rule). `curl -sN -X POST http://127.0.0.1:<port>/llm/chat -d @payload.json` → assert `data: {…}\n\n` framing unchanged; `ruff check sidecar`.
- **D3:** `cd sidecar && python -m pytest tests/test_agent_runtime.py tests/test_agents_router.py tests/test_mcp_server.py -q` (roster/tool counts); then `python -c "import main; main._register_runtime_extensions(); from services import agent_tools; print(len(agent_tools.registry()))"` matches pre-change count. Gold gate: `node scripts/smoke-test-sidecars.mjs` (binary path `main.py` exercises — `cargo test` won't).
- **D4:** `pnpm vitest run src/lib/model-options.test.ts`; rig check — `mcp__tauri-mcp__screenshot` of AgentHud + Settings model dropdowns showing populated live catalog (must show real models, not empty per the visual-verification rule).
- **D5:** `pnpm vitest run` for screener/earnings; set region≠US in settings, rig-screenshot screener market-cap column showing locale grouping (proves the bug is fixed, not just moved).
- **Full gate before any tag:** `pnpm ci-local` (mirrors CI byte-for-byte) + `node scripts/smoke-test-sidecars.mjs`.

**Ranking (payoff):** D1 (3-way list drift, finance-critical model ids) > D5 (live region bug) > D2 (4 sites + dead code) > D3 (2 registration copies, boot-path drift) > D4 (2-site UI ladder).
