# Vysted Rebuild R3 Spec — rebuild the experience on a working engine

> Branch `003-vysted-rebuild`. This is a **decision document**, not a survey. It
> synthesizes the R3 Phase-0 research (serving-models, deep-research-ux,
> cmdk-palette, rich-editor, company-overview, design-language, oss-reuse) and the
> R3 code/audit findings (stale-code register, failure-modes, four engine maps,
> verification recipe) into an executable plan. It RECONCILES with and OVERRIDES
> the prior `docs/redesign/REBUILD_SPEC.md` where R3 decisions have moved:
>
> - **Accent is INDIGO `#818cf8`** (the prior spec's teal/`--accent-rgb` picks are
>   dead — indigo is final).
> - **Mark-only brand, NO text wordmark.**
> - **Keyless research default is re-confirmed from live serving data below** — it
>   is **NOT** assumed-minimax and **NOT** the stale `deepseek-v4-flash`-as-thinking
>   read the prior spec carried. R3 serving research re-classifies
>   `deepseek/deepseek-v4-flash` as **non-thinking by default** (the inverse of v4
>   Pro) and the fastest/cheapest genuinely-served model on OpenRouter. See §2.
> - **The words "fallback" and "Tongyi" are removed from deep-research settings
>   entirely** — the whole Tongyi backend is deleted, not relabeled.
>
> The ENGINE + DATA layer is world-class and **stays**. The EXPERIENCE layer is
> rebuilt from scratch on top of it.

---

## 1. Thesis, scope, floor

**Thesis.** Vysted today passes machine gates but feels vintage and jargon-heavy,
and breaks on small things: a screener that says "Top 100" and returns 506; a
prominent deep-research engine ("Tongyi") that never runs and badges itself
"using fallback"; the entire agent/provider/autonomy/persona control stack hidden
behind a collapsed sliders icon; no symbol autocomplete in the chart; a plain
`<textarea>` for notes. The **engine** — FastAPI sidecar + provider registry,
§6.5 safety, dockview + workspace-blob persistence, Kite read-only OAuth, the
copilot tool loop + capability catalog, the IterResearch/Heavy deep-research
harness with its wall guards, the deterministic typed-block brief renderer, BYOK
keychain flow, MCP-on-both-sides — is strong and **stays byte-for-byte where it is
load-bearing**. We rebuild the **surface**: agent composer, command palette,
research presentation, clickable company overview, a hackable screener, a real
notes editor, visual/motion polish — so Vysted becomes the comfortable go-to the
way Obsidian is for notes and Cursor is for code.

**KEEP — do not rebuild.** The FastAPI sidecar + `provider_registry`; the §6.5
safety layer; dockview + the `SerializedWorkspace` persistence model; Kite
read-only OAuth; the copilot tool loop + capability catalog
(`sidecar/services/agent_tools/catalog.py` is the one source of truth); the
IterResearch + Heavy + deep harness in `sidecar/services/research/` _with its
existing per-round/per-run wall guards_; the deterministic typed-block brief
renderer (`src/modules/research/brief-blocks.tsx`); the auto-publish event
(`agent_runtime._auto_publish_event`); BYOK keychain flow; the model registry as
the single source of truth.

**FLOOR — sacred, verified every milestone.**

- **§6.5 safety audit reads 9/9 at every milestone.** No exceptions, no "we'll
  re-green it later."
- **Tier-1 LOCKED files stay byte-for-byte untouched:** `types/plugin.ts`,
  `types/safety.ts`, `types/broker.ts`, the safety/broker/audit/kill-switch models
  (`sidecar/models/{safety,broker,audit_log,kill_switch}.py`),
  `sidecar/services/broker_base.py`, `src-tauri/src/kill_switch.rs`,
  `sidecar/tests/test_safety_end_to_end.py`, `src-tauri/tauri.conf.json`, the CI
  workflows (`.github/workflows/`).
- **Orders never auto-apply.** Every mutation routes the proposed-changes
  diff/accept gate; AUTO mode auto-applies non-order changes only, orders always
  queue.
- **Brokers read-only.** GET-only routes, duck-typed to `account_info()` /
  `*_info` seams; no §6.5 ABC change.
- **Secrets keychain-only, per-request, never logged, never shell-extracted.**
  Header for read-only plugins, never the body; sidecar cannot read the keychain.
- **Route around locked files** via Tauri 2 core + `capabilities/*.json` — never
  edit a locked file to reach a feature; log the reroute in the commit.
- **No merge to main. No version bump — stays `0.8.0`** across `package.json`,
  `Cargo.toml`, `tauri.conf.json`, sidecar `app.py FastAPI(version=…)`,
  `HOST_VERSION`.

---

## 2. RESEARCH MODEL DECISION

**Authoritative serving rule (non-negotiable).** A model's OpenRouter listing page
is **not** proof it serves. The authoritative confirmation that a model is
serveable as a default is **a keyed chat completion driven THROUGH the live app**
— keychain → per-request header → sidecar → OpenRouter → a non-empty `choices[0]`
— performed in the verification phase (§7 step 15). Listing pages, weekly-token
counts, and provider-count badges are evidence, not proof. Tongyi was "listed"
and dead; we do not repeat that mistake by trusting a catalog row.

**Verified live OpenRouter shortlist (June 2026), ranked:**

| Slug                                  | In/Out ($/1M) | Ctx  | Thinking default?                                            | Serving confidence                                                       |
| ------------------------------------- | ------------- | ---- | ------------------------------------------------------------ | ------------------------------------------------------------------------ |
| `deepseek/deepseek-v4-flash`          | $0.10/$0.20   | 1M   | **NO** (thinking opt-in via `"thinking":{"type":"enabled"}`) | **HIGH** — 3.04T wkly tokens, 14+ providers, ~145 tok/s, 1.3s TTFT       |
| `minimax/minimax-m3`                  | $0.30/$1.20   | 1M   | **NO**                                                       | **HIGH** — 938B wkly tokens, purpose-built long-horizon agentic, 1M ctx  |
| `qwen/qwen3.6-flash`                  | $0.19/$1.13   | 1M   | **NO**                                                       | **HIGH** — 24.9B wkly, fast tool-calling                                 |
| `moonshotai/kimi-k2.6`                | $0.68/$2.80   | 262K | hybrid — **off** via `"thinking":{"type":"disabled"}`        | **HIGH** — 21 providers, 427B wkly, Toolathlon 50%, MCPMark 55.9%        |
| `deepseek/deepseek-v4-pro`            | $0.44/$0.87   | 1M   | **YES** (`reasoning_effort` high)                            | **HIGH serving, DISQUALIFIED as default** — thinking-default = hang risk |
| `alibaba/tongyi-deepresearch-30b-a3b` | —             | —    | —                                                            | **CONFIRMED DEAD** — zero provider serving, unrouted. Delete on sight.   |

### Decisions

- **Keyless/low-cost DEFAULT → `deepseek/deepseek-v4-flash`.**
  - **Rationale.** R3 serving research re-classifies it as **non-thinking by
    default** (thinking is opt-in, the inverse of v4 Pro) — so it is safe as a
    keyless default with no param surgery and no hang risk. It is the fastest
    (~145 tok/s) and cheapest ($0.10/$0.20, ~$0.02/run) genuinely-served
    non-thinking model on OpenRouter, with 14+ providers and 3T+ weekly tokens
    proving real serve depth. The April "no endpoints" issue was AkashML-specific,
    not a global routing failure.
  - **HARD RULE.** The keyless default MUST be a **non-thinking-by-default**
    model. This rule is why the dead Tongyi slug and `deepseek-v4-pro` are both
    barred from the default slot.
  - **Verification gate.** Before this ships as default, run the §7-step-15 keyed
    completion through the live app. If v4-flash exhibits tool-call schema errors
    in the finance loop, the documented swap-down is `minimax/minimax-m3` (HIGH
    serving, non-thinking, purpose-built agentic) — change the registry default
    JSON only (see insertion points below).

- **POWER deep-research → `deepseek/deepseek-v4-pro`.**
  - **Rationale.** Strongest open-weight intelligence on the board (AA #2), 1M
    context, 1.41T weekly tokens. Use ONLY for long-horizon Heavy runs where
    quality beats speed, and ONLY with `"thinking":{"type":"disabled"}`
    hardcoded in the invoke path — otherwise it reproduces the multi-minute hang.
  - **Verification gate.** Keyed completion with explicit thinking-disabled param
    before enabling as the Heavy-mode power slot.

- **TOOL-CALLER for MCP-heavy steps → `moonshotai/kimi-k2.6`.**
  - **Rationale.** Toolathlon doubled (27.8→50%), MCPMark 55.9%, 21 providers,
    Claude Code is its third-largest OpenRouter consumer. 262K context is
    sufficient per tool-call turn. Non-thinking requires
    `"thinking":{"type":"disabled"}` in the request.
  - **Verification gate.** Keyed completion in-app with a tool schema sent.

> Note on stale wiring: the prior `REBUILD_SPEC.md` and `OnboardingFlow.tsx`
> diverge — onboarding force-set `deepseek-v4-flash` while the registry default was
> `minimax/minimax-m3`. R3 resolves the collision IN FAVOR of `deepseek-v4-flash`
> as the registry default (it is the confirmed non-thinking, fastest, cheapest
> served model), so onboarding and the registry now agree on a single value.

### Exact code insertion points — swap the default

The OpenRouter registry default and the agent last-resort fallback are
independent strings; both must move together to stay in sync.

| Insertion point               | File:Line                                                                                                       | Change                                                                                                                                            |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| OpenRouter registry default   | `sidecar/config/model_registry.json:61`                                                                         | `"default_model": "minimax/minimax-m3"` → `"deepseek/deepseek-v4-flash"` (JSON-only, no code change)                                              |
| Onboarding override           | `src/components/OnboardingFlow.tsx:61,359`                                                                      | `OPENROUTER_DEFAULT_MODEL` → `"deepseek/deepseek-v4-flash"` so onboarding == registry (or delete the override and let the registry default stand) |
| Agent last-resort fallback    | `sidecar/services/agent_runtime.py:319`                                                                         | the `"gpt-4.1-mini"` literal is the provider-less last resort; leave unless the registry has no default for a provider                            |
| Known-models lists (lockstep) | `sidecar/config/model_registry.json:63-72`, `src/store/model-selection.ts:52`, `src/store/llm-providers.ts:101` | keep `deepseek/deepseek-v4-flash` (now the default); add `minimax/minimax-m3` as the documented swap-down                                         |
| Migration note (keep)         | `src/lib/workspace.ts:147-148`                                                                                  | re-word: the keyless default is now `deepseek/deepseek-v4-flash`; preserve the migration guard for older blobs carrying `minimax/minimax-m3`      |

### Exact code insertion points — mid-call wall guard

The audit found the per-LLM-call 60s guard (`deep_research.py:38`,
`_LLM_CALL_TIMEOUT_SECS=60.0`) is applied only when research is invoked via
`_run_native`/`_run_tongyi`. The loop helpers call the injected `llm_call` with no
timeout, so workflow-node and direct-test call paths are unguarded.

- **Insertion:** `sidecar/services/research/deep.py:105-112`, inside `_safe_llm`.
  Wrap `await llm_call(messages)` in `asyncio.wait_for(..., timeout=_LLM_CALL_TIMEOUT_SECS)`
  where `_LLM_CALL_TIMEOUT_SECS` is a new module-level constant in `deep.py`
  (parallel to the one in `deep_research.py`). This applies the guard universally
  across both `deep.py` and `iter.py` loops (iter imports `_safe_llm` from deep),
  both native and (post-deletion, irrelevant) backends, both direct and
  tool-invoked calls. On timeout, route to `abort_synthesize` (never a bare
  `TimeoutError`), consistent with the existing per-round guard.

---

## 3. STALE-CODE REMOVAL REGISTER

This is the operator's #1 ask. Every item was read in code; `file:line` is exact.
Severity: **kills-trust** > confusing > cosmetic.

### Surface 1 — Screener universe label

| file:line                                      | What                                         | Superseded by / collides with                                                         | Sev         | Remediation                 |
| ---------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------- | ----------- | --------------------------- |
| `src/modules/screener/ScreenerPanel.tsx:18`    | `sp500: "S&P 500 (Top 100)"`                 | `sidecar/services/screener_universes/sp500.json:3` label `"S&P 500"`, **506 symbols** | kills-trust | Re-label `sp500: "S&P 500"` |
| `src/modules/screener/ScreenerPanel.tsx:16-17` | comment "100 largest-weight … Phase 9.5 nit" | snapshot is 506 symbols                                                               | confusing   | Delete the comment          |

### Surface 2 — Tongyi / "fallback" deep-research (delete end-to-end)

The whole Tongyi backend is dead: `TONGYI_SLUG` is unrouted, so `resolve_model`
**always** returns `FALLBACK_SLUGS[0] = "minimax/minimax-m3"`. The option is
prominent and every user string says it "falls back to a live Qwen-A3B" while the
code runs minimax-m3. Both the option and the word "fallback" are banned.

| file:line                                                                                                             | What                                                                                       | Sev         | Remediation                                                                              |
| --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ----------- | ---------------------------------------------------------------------------------------- |
| `src/components/SettingsPanel.tsx:932-937`                                                                            | Tongyi `EngineOption` radio + "Falls back to a live Qwen-A3B…"                             | kills-trust | **Delete the entire `EngineOption`.** Leave only "Native (IterResearch)"                 |
| `src/components/SettingsPanel.tsx:873-970`                                                                            | whole `DeepResearchSection` (probe + "Tongyi routing OK"/"using fallback" + `~$/run`)      | kills-trust | Collapse to a static "Native" note OR remove the section; remove the probe call          |
| `src/components/SettingsPanel.tsx:908,915`                                                                            | status strings `"using fallback"` + amber tone                                             | kills-trust | Delete — the banned word                                                                 |
| `src/components/SettingsPanel.tsx:869,923,936`                                                                        | docstring + hint + description narrating Tongyi-vs-Qwen-A3B                                | confusing   | Delete                                                                                   |
| `src/store/settings.ts:40-44,89,286`                                                                                  | `DeepResearchBackend = "native" \| "tongyi"`; default; "Qwen-A3B" doc; migration branch    | kills-trust | Narrow type to `"native"`; drop `"tongyi"`; drop the migration branch reading `"tongyi"` |
| `src/lib/hardware-fit.ts:60-77`                                                                                       | `tongyi:{usingFallback,resolvedModel}` probe shape + `probeDeepResearch`                   | confusing   | Delete `probeDeepResearch` + the `tongyi`/`usingFallback` types                          |
| `src/modules/chat/ChatSidebar.tsx:604-608,649`                                                                        | forwards BYOK key "when Tongyi selected" (`deepResearchBackend === "tongyi"`)              | confusing   | Delete the `=== "tongyi"` branch + key-forwarding                                        |
| `sidecar/config.py:175-192`                                                                                           | `get/set_request_deep_research` doc "native/tongyi"                                        | cosmetic    | Re-doc native-only (keep ContextVar plumbing if perplexity stays)                        |
| `sidecar/services/research/tongyi.py` (whole file)                                                                    | `TONGYI_SLUG`, `FALLBACK_SLUGS`, `resolve_model`, `PROVENANCE_NOTE`, `estimate_cost_usd`   | kills-trust | **Delete the module** + `__all__` export + importers                                     |
| `sidecar/services/agent_tools/deep_research.py:50-51,134-191,299,324,333-334`                                         | `_run_tongyi`, `_TONGYI_NEEDS_KEY`, `backend=="tongyi"` dispatch, "Qwen-A3B fallback"      | kills-trust | Delete `_run_tongyi` + the dispatch + comments                                           |
| `sidecar/services/agent_tools/catalog.py:295,323-326`                                                                 | `deep_research` `backend` enum `["native","perplexity","tongyi"]` + "Tongyi backends" text | confusing   | Remove `"tongyi"` from enum + description                                                |
| `sidecar/routers/system.py:6,23,50-60,205-250`                                                                        | `_REFERENCE_CANDIDATES` Tongyi card; `/deepresearch/probe` tongyi block                    | confusing   | Drop Tongyi reference candidates; delete (or stub) `/deepresearch/probe`                 |
| `sidecar/services/hardware_fit.py:382`                                                                                | comment "Track C Tongyi"                                                                   | cosmetic    | Re-word                                                                                  |
| `sidecar/services/research/iter.py:7`, `agent_runtime.py:658`                                                         | "Tongyi" comments                                                                          | cosmetic    | Re-word                                                                                  |
| `sidecar/tests/test_tongyi_backend.py` (whole), `test_system_router.py:45-50,235-286`, `test_hardware_fit.py:5,62-97` | assert dead Tongyi behaviour                                                               | confusing   | Delete `test_tongyi_backend.py`; strip Tongyi asserts from the others                    |
| `CLAUDE.md:200-205,229`                                                                                               | documents the dead Tongyi path as live DNA                                                 | confusing   | Rewrite to native-only deep research; drop Tongyi/fallback narration                     |

**Qwen-A3B contradiction.** `SettingsPanel.tsx:869,936`, `store/settings.ts:42`,
`deep_research.py:142,163` all say "Qwen-A3B" but `tongyi.py:48 FALLBACK_SLUGS[0]`
is `minimax/minimax-m3`. Once Tongyi is deleted none survive — but if any text is
kept transitionally it must say minimax-m3, never Qwen-A3B.

### Surface 3 — Round-2 disclosure composer (rebuild inline, don't hide)

| file:line                                                                        | What                                                                                                  | Sev         | Remediation                                                                    |
| -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------ |
| `src/modules/chat/ChatSidebar.tsx:280`                                           | `controlsOpen = useState(false)` — controls collapsed by default                                      | kills-trust | Rebuild controls inline; remove the disclosure gating                          |
| `src/modules/chat/ChatSidebar.tsx:958-1000`                                      | `AnimatePresence` mounting `ModeBar`/`RosterStrip`/`AgentHud`/`BudgetConfig` only when `controlsOpen` | kills-trust | Surface in the composer, not behind disclosure                                 |
| `src/modules/chat/ChatSidebar.tsx:1020-1040`                                     | `SlidersHorizontal` toggle + `aria-expanded`                                                          | kills-trust | Remove once controls are inline                                                |
| `src/modules/chat/ChatSidebar.tsx:277-279,954-956`                               | "collapse into a disclosure … closed by default" comments                                             | confusing   | Delete after rebuild                                                           |
| `src/modules/chat/ChatSidebar.test.tsx:206-208`                                  | test clicks "Agent controls" to open disclosure                                                       | confusing   | Rewrite once controls are inline                                               |
| `src/modules/chat/ChatSidebar.tsx:848` (AgentsRail) vs `:968,1099` (RosterStrip) | **TWO persona/agent pickers** in one sidebar                                                          | kills-trust | Keep ONE roster (fold `RosterStrip` into `AgentsRail` or delete `RosterStrip`) |

### Surface 4 — `deepseek-v4-flash` default-model collision

After §2, the registry default IS `deepseek/deepseek-v4-flash`, so onboarding's
force-set now agrees. Verify the two are equal and remove the divergent comment.

| file:line                               | What                                                      | Sev        | Remediation                                                               |
| --------------------------------------- | --------------------------------------------------------- | ---------- | ------------------------------------------------------------------------- |
| `src/components/OnboardingFlow.tsx:61`  | `OPENROUTER_DEFAULT_MODEL = "deepseek/deepseek-v4-flash"` | (resolved) | Confirm it equals the registry default; keep                              |
| `src/components/OnboardingFlow.tsx:359` | `setModel("openrouter", OPENROUTER_DEFAULT_MODEL)`        | (resolved) | Keep, now consistent; or delete and let registry default stand            |
| `src/lib/workspace.ts:147-148`          | migration comment                                         | cosmetic   | Re-word to "default is deepseek-v4-flash; migrate older minimax-m3 blobs" |

### Surface 5 — Two-mode system with four-mode stale strings

`types/agent-modes.ts:24` defines `AgentMode = "agent" | "delegate"` (2 modes) but
UI/doc strings still say four / ⌥1–⌥4.

| file:line                               | What                                                    | Sev       | Remediation                                            |
| --------------------------------------- | ------------------------------------------------------- | --------- | ------------------------------------------------------ |
| `src/modules/chat/ModeBar.tsx:11`       | doc "four-mode spine … Ask/Edit panel/Build/Delegate"   | confusing | Re-doc "two-mode spine — Agent / Delegate"             |
| `src/modules/chat/ModeBar.tsx:14,30-31` | "⌥1–⌥4" doc + `"Edit panel" ? "Edit"` shortening        | confusing | Delete the `"Edit panel"` branch; fix ⌥-range to ⌥1–⌥2 |
| `src/store/agent-mode.ts:5`             | doc "(⌥1–⌥4)"                                           | cosmetic  | Fix to ⌥1–⌥2                                           |
| `types/agent-modes.ts:93`               | `coerceAgentMode` accepts legacy `"ask"/"edit"/"build"` | cosmetic  | Keep (real migration shim)                             |

### Surface 6 — Dead components / files (never rendered)

| file                                                    | What                                                                 | Sev       | Remediation                                            |
| ------------------------------------------------------- | -------------------------------------------------------------------- | --------- | ------------------------------------------------------ |
| `src/components/PlaceholderPanel.tsx` (whole)           | `createPlaceholderPanel` "Arrives in Phase 1.B" — **zero usages**    | confusing | **Delete the file**                                    |
| `src/modules/integrations/ConnectCard.tsx` (whole)      | old broker ConnectCard, superseded by `broker-connect` + Marketplace | confusing | **Delete** (verify `broker-connect` doesn't import it) |
| `src/lib/integrations/{registry,kite-connect,types}.ts` | integration-spec island, only ConnectCard consumes                   | confusing | Delete with ConnectCard after import check             |

### Surface 7 — Design tokens: stale warm-clay drift (lockstep trap)

`styles/tokens.css` + `src/lib/chart-theme.ts` are correctly zinc + cool-indigo,
but `globals.css` fallbacks/comments still describe the retired warm clay/espresso
palette. CLAUDE.md requires tokens.css + chart-theme.ts + globals.css `--accent-rgb`
to move in lockstep.

| file:line                                     | What                                                                                                                                                                       | Sev       | Remediation                                                                                  |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | -------------------------------------------------------------------------------------------- |
| `src/app/globals.css:3-4`                     | header comment "warm instrument … warm-clay accent"                                                                                                                        | confusing | Rewrite to zinc + cool-indigo                                                                |
| `src/app/globals.css:211-220,226-233,241,252` | dockview/chrome `var(--…, <warm hex>)` fallbacks (`#16140f`, `#100e0c`, `#1a1714`, `#f2efe9`, `#988f7f`, `#b8b0a1`, `#494238`, `#a06b52`, `#7c5240`, `#d6cfc2`, `#332e26`) | confusing | Replace every warm fallback with the matching zinc/indigo literal (lockstep with tokens.css) |
| `src/lib/chart-theme.ts:9,13-15,27,49,66,69`  | comments say "cool-teal"/"teal" (value is indigo `#818cf8`)                                                                                                                | cosmetic  | Re-word "teal" → "cool-indigo"                                                               |

### Surface 8 — Coexisting slash systems & legacy markers

| file:line                                                                                                                                   | What                                                                                                            | Sev       | Remediation                                                                                                              |
| ------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------ |
| `src/modules/chat/slash-commands.ts:106-110,152` + `ChatSidebar.tsx:487-500`                                                                | two slash systems: curated registry (FR-100) **and** legacy `parseSlashCommand` (`/ask`,`/agent`) both consumed | confusing | Fold wanted legacy verbs into the curated registry; drop `parseSlashCommand` + the `/ask /agent` cheat-sheet lines 93-94 |
| `src/components/OnboardingBanner.tsx:12`                                                                                                    | "(Phase 9.5 / Track C)"                                                                                         | cosmetic  | Drop the phase tag                                                                                                       |
| `src/lib/host-actions.ts:131`, `workspace.ts:131,148,244,259-261`, `format.ts:7`, `sidecar-client.ts:212,262`, `desktop-notification.ts:78` | "Phase 1.A/9.5/10", "legacy" comments                                                                           | cosmetic  | Strip phase refs in a cleanup pass                                                                                       |

### REMOVE THIS NOW (ordered by trust impact)

1. **Delete the Tongyi backend end-to-end:** `sidecar/services/research/tongyi.py`
   (file); `_run_tongyi` + dispatch in `deep_research.py:134-191,333-334`; the
   `"tongyi"` enum in `catalog.py:323`; the Tongyi reference candidates +
   `/deepresearch/probe` Tongyi block in `system.py:50-60,205-250`;
   `test_tongyi_backend.py`.
2. **Delete the Tongyi `EngineOption` + the "fallback" probe:** `SettingsPanel.tsx:932-937`
   (option) and `873-970` (probe/status); narrow `DeepResearchBackend` to `"native"`
   in `store/settings.ts:44`; delete `probeDeepResearch` in `hardware-fit.ts:60-77`;
   delete the `=== "tongyi"` key-forward in `ChatSidebar.tsx:604-608,649`.
3. **Set the default model to the served non-thinking pick:**
   `model_registry.json:61` → `"deepseek/deepseek-v4-flash"`; confirm
   `OnboardingFlow.tsx:61` matches.
4. **Re-label the screener universe:** `ScreenerPanel.tsx:18` → `"S&P 500"`; delete
   the false comment at `:16-17`.
5. **Rebuild composer controls inline:** `ChatSidebar.tsx:280,958-1000,1020-1040` —
   remove `controlsOpen` + the `SlidersHorizontal` disclosure; surface
   Mode/Persona/Provider/Autonomy; rewrite `ChatSidebar.test.tsx:206-208`.
6. **Merge the two rosters:** delete `RosterStrip` (`ChatSidebar.tsx:968,1099`) or
   `AgentsRail` (`:848`) — keep one persona picker.
7. **Delete dead files:** `PlaceholderPanel.tsx`; `ConnectCard.tsx` +
   `src/lib/integrations/{registry,kite-connect,types}.ts` (verify first).
8. **Fix four-mode→two-mode strings:** `ModeBar.tsx:11,14,30-31`, `agent-mode.ts:5`.
9. **Re-value the warm-clay fallbacks** in `globals.css:211-252` + the header
   comment `:3-4`; fix "teal" comments in `chart-theme.ts`.
10. **Update `CLAUDE.md:200-205,229`** to native-only deep research; drop "Qwen-A3B"
    strings everywhere any Tongyi text might survive.
11. Drop `tongyi`-adjacent dead known-model ids only if retired (keep
    `deepseek/deepseek-v4-flash`).
12. **Collapse the dual slash-command systems.**

---

## 4. FAILURE-MODE GUARDRAIL TABLE

Each row: the failure, current status, file:line, and the fix that makes it
**impossible** (not merely unlikely).

| #   | Failure mode                                       | Status                       | File:line                                                        | Fix that makes it impossible                                                                                                                                                                                                                                                                                                                                                                                                                             |
| --- | -------------------------------------------------- | ---------------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Enter doesn't send / double-sends                  | **PREVENTED**                | `ChatSidebar.tsx:1316-1349,1371`                                 | `onKeyDown` calls `onSend` on `Enter && !shiftKey` with `preventDefault()` when `!pickerOpen`; the form's `onSubmit` fires only on button click. No change. Keep the explicit `preventDefault` when the rebuild moves the composer.                                                                                                                                                                                                                      |
| 2   | Phantom proposal bar on user-initiated panel opens | **PREVENTED**                | `proposed-changes.ts:56-83`; `ChatSidebar.tsx:386-392`           | `enqueueChange` only fires from `onToolUse` + `enqueueSlashChange`; palette/⌘K opens call `useWorkspaceStore.openPanel` directly. In AUTO, non-order changes auto-`accept()` so the bar renders nothing. Preserve this separation in the rebuild — never route a user open through the proposal pipeline.                                                                                                                                                |
| 3   | Jargon a normal user won't understand              | **NOT prevented**            | `types/agent-modes.ts:24,54-61`; `slash-commands.ts:166-180`     | Reword `hint`/`consequence` in `agent-modes.ts:54-61` to plain English ("Run a longer background task — I'll review when it's done"); rename `/deep heavy` description to "Deeper coverage — explores multiple angles, synthesizes one cited brief." Make impossible via a CI lint: no acronym in toast/empty-state/agent-reply strings unless adjacent to its expansion.                                                                                |
| 4   | Empty News panel on cold boot                      | **NOT prevented**            | `NewsFeedPanel.tsx:161-248`                                      | Add a `useEffect` firing `refresh()` when `sidecarReady` (bootstrap store) flips true; for retries `n<3` show "Sidecar starting up — ~30s" instead of the generic skeleton. Impossible-to-confuse once the cold-boot message is explicit + auto-refresh on ready.                                                                                                                                                                                        |
| 5   | Clipped/cut-off picker menus                       | **PREVENTED**                | `ChatSidebar.tsx:1354-1370`; `SlashCommandPicker.tsx:35`         | Pickers are `absolute bottom-full left-0` (open upward) with `max-h-60 overflow-y-auto`. Keep the upward-anchored, max-height pattern in the rebuilt composer.                                                                                                                                                                                                                                                                                           |
| 6   | No symbol autocomplete in Chart panel              | **NOT prevented**            | `ChartPanel.tsx:1002-1020`                                       | Port the `EquityOverviewPanel` autocomplete: import `autocompleteSymbols` (`equity-overview/api.ts:36`), add `candidates/acOpen/acIndex` state, debounced `useEffect` on `symbolInput`, dropdown overlay above the form. Impossible to type "Apple"→"No data" once autocomplete resolves the ticker.                                                                                                                                                     |
| 7   | Wrong-stock resolution / no clarifying question    | **PARTIALLY prevented**      | `resolve.py:89`; `mentions.ts:176-253`                           | `/resolve` returns `needs_disambiguation` but the frontend never reads it. Fix: in `resolveMention`, when `res.needs_disambiguation === true && res.candidates.length > 1`, return ONLY candidates (not `res.resolved`) so the picker forces a pick. Impossible to silently load the wrong listing.                                                                                                                                                      |
| 8   | Uncloseable / duplicate panels                     | **PREVENTED**                | `workspace.ts:107-127`                                           | Singletons `setActive()` + return; non-singleton chart mints a unique id (intentional). dockview close button is never disabled. No change.                                                                                                                                                                                                                                                                                                              |
| 9   | 502 "empty series" chart flake                     | **PARTIALLY prevented**      | `ChartPanel.tsx:329-357,1196-1203`                               | Error string already shows `(status)`; empty series → "No price data". Add a `<Retry>` button to the error state that bumps the existing `retryNonce` (`:239`) so a transient 502 is one click. Makes the dead-end impossible.                                                                                                                                                                                                                           |
| 10  | Date-change error on chart                         | **NOT verified (stale ref)** | `ChartPanel.tsx:1022-1038`                                       | No date picker exists — timeframe is a button group; `GET /history` sends only `timeframe`. The rebuild MUST NOT reintroduce a free date-range input that can desync; if a range picker is added, validate against `TIMEFRAMES` and clamp server-side.                                                                                                                                                                                                   |
| 11  | Quarterly-statements duplicate-key crash           | **PARTIALLY prevented**      | `EquityOverviewPanel.tsx:208-209`                                | `key={line.label}` collides on duplicate labels ("Other","Total"). Fix: `key={`${line.label}-${index}`}` using the `.map` index. One-character-class change; eliminates the console-error/mis-render.                                                                                                                                                                                                                                                    |
| 12  | "0 sources" research / structured-only briefs      | **PARTIALLY prevented**      | `web_search.py:76-84`; `deep.py:227-251`; `deep_research.py:265` | DDG keyless floor exists but the coverage floor requires `web:True`, so a throttled DDG spins the loop. Fix: when `llm_creds` is None emit an honest "no model configured" brief; when DDG returns `ok:False`, enter a **structured-only brief mode** (`note="Web search unavailable — brief built from structured data only"`) that drops the `web` coverage requirement so the loop synthesizes from structured legs instead of exhausting the budget. |

---

## 5. ENGINE MAP (condensed) — the seams the rebuild hooks into

### Research / Brief / Model

- **Deep harness:** `sidecar/services/research/{deep,iter,fast}.py`. Loop entries:
  `run_iter_research` (`iter.py:187`), `run_heavy_research` (`iter.py:452`),
  `run_deep_research` (`deep.py:387`). Web search + source collection:
  `_run_researcher` (`deep.py:254`), `_record_web` (`deep.py:227-251`) — the
  0-source starve point. Coverage floor `deep.py:51` requires `{price,fundamentals,news,web}`.
- **Wall guards:** `_PER_ROUND_WALL_SECS=90.0` (`deep.py:66`), `_round_wall_limit`
  (`deep.py:69`), per-round `asyncio.timeout` (`deep.py:581`, `iter.py:386`),
  per-LLM-call `_LLM_CALL_TIMEOUT_SECS=60.0` (`deep_research.py:38`). **Gap →**
  add the universal mid-call guard at `deep.py:105-112` (§2).
- **Auto-publish:** `_auto_publish_event` (`agent_runtime.py:455`, called `:799`)
  fires a synthetic `publish_brief` on EITHER markdown OR structured.
- **Brief renderer:** `src/modules/research/brief-blocks.tsx` — `deriveMetrics`
  (`:119`), `parseBodyBlocks` (`:227`), GFM table parse (`:243-258`), `renderInline`
  (`:371`), `renderTickers` (`:337`), `knownTickersOf` (`:546`), `BriefBody`
  (`:573`). Contract: `types/brief.ts` — `BriefStructured` (`:41`),
  `ResearchBriefData` (`:94`).
- **Model registry (single source of truth):** `sidecar/config/model_registry.json`
  — OpenRouter default `:61`, known_models `:63-72`. Live catalog: `GET /llm/models`
  (`routers/llm.py:51`) → `fetch_openrouter_catalog` (`openrouter_catalog.py:71`).
  Deep-research backend selection is authoritative-not-LLM: `agent_runtime.py:661-664`
  → `config.set_request_deep_research` ContextVar → `deep_research.py:328`.
- **Insertion points:** default swap → `model_registry.json:61`; mid-call guard →
  `deep.py:105`; deepen brief (tables/storyline/follow-up) → synthesis prompts at
  `deep.py:354-373`, `iter.py:155-173`, `iter.py:544-565`, plus a
  `follow_up_questions` field on `ResearchBrief` → `types/brief.ts:94` →
  `BriefBody`.

### Screener / Data / Fit

- **Core:** `sidecar/services/screener.py` — `resolve_universe` (`:146`, sp500
  branch `:172-179`), `apply_criteria` (`:319`), `_evaluate_group` recursive AND/OR
  (`:302-316`), `_cached_pair` + `Semaphore(12)` (`:418-454`), `run_screener`
  (`:457`). Universe data: `screener_universes/sp500.json` — label `:3`, **506
  symbols** `:5+`. Grammar: `models/screener.py` — `CriterionGroup` recursive
  (`:159-183`).
- **The label bug:** `ScreenerPanel.tsx:18`. **The formula seam:** the Python
  backend already evaluates arbitrarily nested `CriterionGroup`; the frontend only
  sends a flat OR (`store/screener.ts:140-141`) and has no nesting UI
  (`ScreenerCriteriaBuilder.tsx:286`). Insertion: build the nested-group tree at
  `screener.ts:140-141` + a group-nesting UI at `ScreenerCriteriaBuilder.tsx:286`.
- **Data:** `yfinance_provider.py` — `_yahoo_symbol` (`:65-93`), `get_fundamentals`
  (`:163`), dividendYield `/100` clamp `[0,2]` (`:180-184`), `Fundamentals(symbol=yahoo)`
  (`:192`, the `.NS`-leak source). `provider_registry.py` — `_SCREENER_GRADE_FIELDS`
  (`:200-211`) drives openbb→yfinance fallback.
- **Symbol/name column collision:** `ScreenerResultsTable.tsx` — `key={row.symbol}`
  (`:333`), Symbol cell (`:339`) display the yahoo form (`ROUTE.NS`), so `.NS` leaks
  into the visible column. Fix in the rebuild: render a display label stripped of
  the `.NS`/`.BO` suffix while keeping the routed symbol for `loadSymbolIntoChart`.
- **Fit:** `hardware_fit.py` — `score()` (`:302-377`), `detect_device` (`:203-219`).

### Agent UX / Chart / Overview / Notes / Palette

- **Composer:** `src/modules/chat/ChatSidebar.tsx` — `controlsOpen` (`:280`),
  disclosure block (`:957-1000`), `ModeBar` (`:968`), `RosterStrip` (`:969-976`),
  `AgentHud` (`:977-994`), `AgentsRail` (`:848`), composer (`:1199-1415`),
  `onKeyDown` (`:1341-1349`). Stores: `agent-spaces.ts`, `agent-mode.ts`,
  `agent-autonomy.ts`, `proposed-changes.ts` (auto-apply `:73-83`, double-apply
  claim `:92-96`). Five pinned bugs: BUG-1 provider persistence (`:107-127`), BUG-2
  phantom status (`:386-394,714`), BUG-3 enter-to-send (`:1341-1349`), BUG-4/6
  chart channel (`host-actions.ts:369`, `chart-command.ts:7-9`), BUG-5 double-apply
  (`proposed-changes.ts:92-96`).
- **Chart:** `ChartPanel.tsx` — `TIMEFRAMES` (`:57`), price effect (`:321-364`),
  empty-series guard (`:333-337`), 502 path (`:347-357`), command channel
  (`:697-711`), symbol input no-autocomplete (`:1002-1020`). `chart-command.ts`
  `loadSymbol` (`:59-60`). `host-actions.ts` `loadSymbolIntoChart` (`:123-129`),
  `ensureChartOpen` (`:191-198`).
- **Equity overview:** `EquityOverviewPanel.tsx` — `StatementTable` (`:175-236`),
  duplicate-key TR (`:209`), `doLoad` (`:324-343`), `quickLoad` (`:386-389`),
  panel-context publish (`:280-288`). `api.ts` — `autocompleteSymbols` (`:36-49`),
  `loadEquityOverview` 6-endpoint fan-out (`:69-92`). **No external symbol-injection
  path exists** — the clean insertion is a new `equity-command.ts` store mirroring
  `chart-command.ts` (seq-bump `loadSymbol`) consumed by a panel `useEffect`, plus
  a `host-actions` case `open_equity_overview`.
- **Notes:** `NotesPanel.tsx` — plain `<textarea>` (`:78-85`); `notes.ts`
  `toBundle`/`fromBundle` (`:58-68`); rides the workspace blob (no localStorage, no
  date-scoped key — the "date-change crash" is not in current code; guard against
  reintroducing it).
- **Palette:** `CommandPalette.tsx` (`:64-309`), `rankCorpus` (`:126-160`).
  `command-palette.ts` — `PaletteItemKind` (`:17`), `KIND_WEIGHT`
  (command1.0/panel0.9/symbol0.8/agent0.7, `:24-29`), `buildPaletteCorpus` 4 groups
  (`:84-154`, symbols `:121-130`, agents `:136-151`). Insertion points: AI-ask row
  after the commands loop (`:104`); symbol de-prioritize in the symbols loop
  (`:121-130`); agent-pre-select in group-4 `run()` (`:136-151`).

---

## 6. PER-PILLAR BUILD PLAN

Each pillar: files to create/modify, chosen library (from OSS-reuse research),
failure modes it must make impossible, acceptance criteria.

### (A) From-scratch agent composer + spaces + 5 bug fixes

**Rebuild.** Replace the collapsed-disclosure composer with an inline control
surface. The Mode (Agent/Delegate), Persona (single roster), Provider/Model HUD,
and Autonomy (ASK/AUTO) controls are **always visible** in the composer — no
`controlsOpen`, no `SlidersHorizontal`. One persona picker only.

- **Modify:** `src/modules/chat/ChatSidebar.tsx` (remove `controlsOpen:280`,
  disclosure `:957-1000`, toggle `:1020-1040`; fold `RosterStrip` into `AgentsRail`,
  delete the dead one), `src/modules/chat/ModeBar.tsx` (two-mode doc + ⌥1–⌥2),
  `src/store/agent-mode.ts:5`, `src/modules/chat/ChatSidebar.test.tsx:206-208`.
- **Library:** none new — pure React 19 + Zustand + Framer Motion (already in
  stack). Mode/persona/autonomy stay Zustand stores.
- **5 bug fixes (preserve, do not regress):** BUG-1 provider persistence
  (`GENERIC_AGENT_IDS` + `agentProviderPreference()` `:107-127`); BUG-2 phantom
  status (`:386-394,714` — `setStatusLine(applied ? … : null)`); BUG-3 enter-to-send
  (`:1341-1349` explicit `preventDefault`); BUG-4/6 `set_chart_symbol` →
  always-consumed command channel (`host-actions.ts:369`, `chart-command.ts:7-9`);
  BUG-5 double-apply synchronous claim before `await` (`proposed-changes.ts:92-96`).
- **Make impossible:** FM-2 (phantom proposal — keep the open/proposal separation),
  FM-1 (enter/double-send), FM-3 (jargon — reword Mode/Delegate hints).
- **Acceptance:** a new user sees Mode + Persona + Provider + Autonomy without
  clicking anything; exactly one persona picker; Enter sends, Shift+Enter newlines;
  AUTO mode shows no phantom "review below"; provider survives relaunch;
  `ChatSidebar.test.tsx` passes without opening a disclosure.

### (B) Clickable AI company overview reachable from everywhere + symbol/name column fix

**Build.** An always-visible, grounded company-overview panel that opens from any
ticker surface and renders a 10-section layout (hero strip → AI narrative card →
key-metrics grid → chart → valuation → financials → news+sentiment → peers →
institutional → filings rail). The AI narrative is server-side grounded generation
with a post-gen numeric-validation pass (every number must match the injected
`COMPANY DATA` dict; null fields excluded from the prompt) — `data-chip` spans that
trace each value to its structured field on hover. No buy/sell recommendation.

- **Create:** `src/store/equity-command.ts` (mirror `chart-command.ts` seq-bump
  `loadSymbol`); `src/modules/equity-overview/overview-blocks.tsx` (the 10 sections
  - grounded-narrative renderer + `data-chip`); a sidecar narrative generator
    reusing the grounded prompt shape (numbers injected, validation regex).
- **Modify:** `EquityOverviewPanel.tsx` (consume `equity-command` via `useEffect`;
  fix `StatementTable` key `:209` → `${line.label}-${index}`);
  `src/lib/host-actions.ts` (add `open_equity_overview` case: `openPanel` +
  `equity-command.loadSymbol`); wire every ticker surface (watchlist row, brief
  `$CASHTAG` chip, screener row, palette `> AAPL`, peer comps, news chip) to the
  single `openCompanyOverview(symbol, placement)` entry; placement logic
  split/replace/drawer mirroring `fitLayoutTemplate`. Fix the screener
  symbol/name column `.NS` leak in `ScreenerResultsTable.tsx:339` (display label
  strips `.NS`/`.BO`, routed symbol keeps it).
- **Library:** `lightweight-charts` (in stack) for the price section;
  `lightweight-charts-indicators` (MIT, deepentropy v0.4.0) + the official
  Apache-2.0 plugin-examples for overlays (SMA/VWAP/earnings markers); no new
  charting core. Prefetch on `mouseenter` (100ms debounce).
- **Make impossible:** FM-11 (duplicate-key crash — index-suffixed key);
  number-fabrication (post-gen validation regenerates on any unsourced number);
  symbol/name column confusion (display label decoupled from routed symbol).
- **Acceptance:** clicking a ticker anywhere opens the overview for that symbol with
  no page navigation (`history.pushState` URL only); the AI card renders ≤800ms with
  every number hover-traceable to a field; null sections render `—` (never omitted,
  never fabricated); no React duplicate-key console error on any real company's
  statements; the screener Symbol column shows `RELIANCE` not `RELIANCE.NS` while
  the chart still routes `.NS`.

### (C) Raycast-grade Cmd+K — grouped/scoped, AI-ask row, agents one-keystroke, de-prioritize symbols

**Rebuild.** Section hierarchy over flat ranking. Order: **Ask (forceMount) →
Recent/Frecent → Agents → Actions → Symbols (gated)**. Symbols penalized `0.3×`
unless the query starts with `$`. The Ask row is a forceMount `Command.Item` with
a live-updating label ("Ask anything…" → "Ask: {query}") routing ticker+prose vs
pure research. Scope chip in the input row; Backspace on empty clears scope. Agents
one keystroke from open via `keywords` aliases + a fixed `⌘2` slot.

- **Modify/Create:** `src/store/command-palette.ts` (`buildPaletteCorpus`
  `:84-154` — add the Ask group after commands `:104`; penalize symbols in the
  symbols loop `:121-130` and skip them when `query.trim()===""`; agent pre-select
  in group-4 `run()` `:136-151`; swap `KIND_WEIGHT` agent→0.85, symbol→0.75);
  `src/components/CommandPalette.tsx` (`rankCorpus :126-160` honors the section
  weights + the `__symbol__` penalty; render the Ask forceMount row + a Quick-Start
  forceMount group for empty input).
- **Library:** **cmdk v1.1.1 (MIT)** via the shadcn/ui `<Command>` component
  already in the stack — `Command.Group forceMount` for Ask + Quick Start,
  `shouldFilter={false}` for async symbol search backed by `/resolve/autocomplete`,
  `keywords` for aliases + the `__symbol__` penalty tag, `Command.Empty` as the
  fallback Ask surface. No new dependency.
- **Make impossible:** symbol-noise drowning actions (penalty + empty-query skip);
  "agents are hidden" (Agents group above Actions/Symbols, `⌘2` slot); dead-end
  empty input (Quick-Start forceMount + Ask row).
- **Acceptance:** empty input shows Quick Start + "Ask anything…"; typing a company
  name that matches no ticker lands on the Ask row; `$AAPL` surfaces the symbol,
  bare "Apple" does not flood; Buffett is reachable by typing "buffett"/"value"/
  "moat" or `⌘2`; selecting a result dismisses the palette (trusted-event close
  verified via Playwright).

### (D) Kill Tongyi/"fallback" + best-serving default + mid-call guard

**Delete + swap.** Execute §3 Surface-2 end-to-end (Tongyi module, EngineOption,
probe, "fallback" strings, tests, CLAUDE.md). Settings deep-research shows **only**
"Native (IterResearch)" — no engine radio, no probe, no `$/run`, no "fallback".
Swap the registry default to `deepseek/deepseek-v4-flash` (§2). Add the universal
mid-call wall guard at `deep.py:105`.

- **Delete:** `sidecar/services/research/tongyi.py`,
  `sidecar/tests/test_tongyi_backend.py`.
- **Modify:** `SettingsPanel.tsx:869,873-970,923,936`, `store/settings.ts:40-44,89,286`,
  `lib/hardware-fit.ts:60-77`, `ChatSidebar.tsx:604-608,649`,
  `deep_research.py:50-51,134-191,299,324,333-334`, `catalog.py:295,323-326`,
  `system.py:6,23,50-60,205-250`, `config.py:175-192`,
  `model_registry.json:61`, `OnboardingFlow.tsx:61`, `deep.py:105-112` (guard),
  `CLAUDE.md:200-205,229`, the affected tests.
- **Library:** none.
- **Make impossible:** a user picking an engine that silently runs something else;
  the word "fallback" appearing in any deep-research UI string (CI grep:
  `rg -i "fallback|tongyi" src/components/SettingsPanel.tsx` returns nothing); an
  unguarded LLM call hanging a workflow node.
- **Acceptance:** Settings deep research reads "Native" only; `rg -i tongyi src
sidecar` returns only intentional migration shims (none in UI); the §7-step-15
  keyed completion through the live app returns a non-empty completion on
  `deepseek/deepseek-v4-flash`; a forced slow LLM call aborts to
  `abort_synthesize`, never a bare timeout.

### (E) Research presentation — 0-source floor + tables + follow-up + storyline + clickable tickers + shareable

**Build.** Make the brief read like a polished white paper, not a chat dump.

- **Fix the 0-source floor:** when `llm_creds` is None → honest "no model configured"
  brief; when DDG returns `ok:False` → **structured-only mode** (`note="Web search
unavailable — brief built from structured data only"`, drop the `web` coverage
  requirement) in `deep.py:227-251` + `deep_research.py:265`. Optional broader
  retry query (`symbol + "news"`) in `_run_researcher` (`deep.py:280`).
- **Real tables + storyline + follow-up:** extend the three synthesis prompts
  (`deep.py:354-373`, `iter.py:155-173`, `iter.py:544-565`) to emit a structured
  shape (1-line thesis → key-data markdown table → bull/bear → risks/catalysts →
  `## Follow-up questions`). The table parse already exists in `brief-blocks.tsx:243-258`;
  render markdown tables as real `<table>` with sticky headers and client-sortable
  comparison columns. Add `follow_up_questions` to `ResearchBrief` →
  `types/brief.ts:94` → render 3 follow-up chips that re-invoke `invoke_agent` with
  the prior `run_id` as context seed.
- **Inline citations + sources rail + tiered trust:** add a `[n]` citation parse
  pass in `renderInline` (`brief-blocks.tsx:371`) with hover tooltip (favicon +
  domain + snippet); extend `types/brief.ts` sources to `{id,url,domain,favicon_url,
snippet,fetched_at,tier,confidence}`; a collapsible right-rail sources panel with
  `SEC/Exchange/Analyst/News` tier badges; `confidence` as a categorical
  `sourced/estimated/unverified` dot (never a percentage).
- **Live ticker chips + shareable:** `renderTickers` (`:337`) already chips
  `$CASHTAG` + known-set → `loadSymbolIntoChart`; add a live `+1.2%` delta via a
  thin Zustand subscription (60s cache, `data-price-delta` attr updated in-place).
  Share: serialize `structured` + markdown + sources to clipboard / `.md` via
  Tauri `dialog::save`; "Copy Markdown" + "Export PDF" (`webview print()`) +
  section-level copy on `H2` hover.
- **Create:** `src/modules/research/sources-rail.tsx`,
  `src/modules/research/follow-up-chips.tsx`; **Modify:** `brief-blocks.tsx`,
  `types/brief.ts`, the three synthesis prompts, `deep.py:227-251`, `agent_runtime.py`
  (thread `follow_up_questions` through `_auto_publish_event`).
- **Library:** none new (markdown parse is hand-rolled in `brief-blocks.tsx`;
  tables already parse).
- **Make impossible:** FM-12 (0-source dead-end — structured-only mode + honest
  no-model note); wall-of-pipes tables (real `<table>`); ungrounded ticker chips
  (known-set guard stays).
- **Acceptance:** a keyless install shows a structured-only brief with a clear note,
  never a blank; a keyed deep run renders a thesis + a sortable comparison table +
  bull/bear + a sources rail with tier badges + 3 working follow-up chips; every
  `[n]` is hover-traceable; clicking a `$TICKER` chip loads the chart and shows a
  live delta; "Copy Markdown" round-trips.

### (F) Tiptap/Obsidian-grade notes editor + guard date-change crash

**Rebuild.** Replace the plain `<textarea>` with a markdown-native WYSIWYG editor,
scoped per-stock + general, persisting raw markdown into the workspace blob with an
atomic-write autosave.

- **Library:** **Tiptap v3 (MIT, v3.25.0)** — `@tiptap/react` + `@tiptap/core` +
  `StarterKit` + `@tiptap/markdown` (GFM) + `@tiptap/extension-task-list/task-item`
  - `@tiptap/extension-table(+row/cell/header)` + `@tiptap/extension-mention`
    (re-triggered on `[[` for wikilinks via a `WikiLink` extend + custom
    `renderMarkdown`) + `@tiptap/extension-placeholder` +
    `@tiptap/extension-code-block-lowlight` + `lowlight` + `@floating-ui/dom`. Slash
    menu via `@tiptap/ui-components` `SlashDropdownMenu` (or `@harshtalks/slash-tiptap`).
    Static-export safe: `immediatelyRender: false`, `'use client'` wrapper,
    `shouldRerenderOnTransaction: false`.
- **Create:** `src/modules/notes/StockNotesEditor.tsx` (the Tiptap wrapper),
  `src/modules/notes/wikilink.ts`, `src/modules/notes/note-autosave.ts` (the
  debounce + `isSaving` flag + `pendingMd` overwrite pattern). **Modify:**
  `NotesPanel.tsx:78-85` (swap the textarea for the editor),
  `src/store/notes.ts:58-68` (store raw markdown strings in `bySymbol`/`general`,
  not Tiptap JSON).
- **Persistence:** raw Markdown string in `ws.notes[symbol]`; atomic write =
  debounce 800ms → `isSaving` guard → `pendingMd` last-value-wins → single
  `writeWorkspace`. Never `getJSON()` for the note body.
- **Make impossible:** torn-blob on rapid saves (the `isSaving`/`pendingMd` atomic
  guarantee); the date-change crash class (no date-scoped key is introduced — notes
  stay symbol-scoped/general; if a date field is ever added it must route the same
  atomic-write path, never a raw keystroke disk write).
- **Acceptance:** typing markdown renders live (headings, lists, tasks, tables,
  `[[AAPL]]` wikilinks with typeahead, `/` slash menu, code blocks with
  highlighting); switching symbols loads that symbol's note; two rapid edits never
  corrupt the blob; the note survives relaunch; no SSR/static-export error.

### (G) Screener.in-grade hackable screener + "S&P 500 (Top 100)" fix + custom-formula surface

**Build.** Re-label the universe honestly, expose the nested AND/OR grammar the
backend already evaluates, and add a safe custom-formula leaf evaluator.

- **Fix the label:** `ScreenerPanel.tsx:18` → `"S&P 500"`; delete the `:16-17`
  comment. (The live count `{universeInfo.symbols.length}` already shows 506.)
- **Custom-formula surface:** the Python `CriterionGroup` (`models/screener.py:159-183`)
  already evaluates arbitrary nesting; the frontend only sends flat OR
  (`store/screener.ts:140-141`). Build a group-nesting UI in
  `ScreenerCriteriaBuilder.tsx:286` that constructs a full `CriterionGroup` tree,
  and add per-row arithmetic leaves (e.g. `pe / eps`, `marketCap / 1e9`) evaluated
  client-side by **mathjs (Apache-2.0)** in a hardened scope (disable
  `import/createUnit/evaluate/parse/simplify/derivative/resolve`), run in a Web
  Worker with a budget timeout. **Never use `expr-eval`** — CVE-2025-12735 (CVSS
  9.8 RCE), unmaintained.
- **Create:** `src/modules/screener/formula-eval.ts` (mathjs hardened worker),
  `src/modules/screener/GroupBuilder.tsx` (nested AND/OR UI). **Modify:**
  `ScreenerPanel.tsx`, `ScreenerCriteriaBuilder.tsx`, `store/screener.ts:140-141`.
  Add `industry` as a display column (currently type-only, `ScreenerResultsTable.tsx`).
- **Library:** **mathjs (Apache-2.0, 15k★)** — tree-shaken `evaluate`+`parse`+
  arithmetic (~30KB), AST-based, blocks `eval`/`new Function`.
- **Make impossible:** the "Top 100"/506 lie (label fix); a formula-eval RCE
  (mathjs hardened scope, no `expr-eval`); a formula hanging the UI (Web Worker +
  budget timeout).
- **Acceptance:** the dropdown reads "S&P 500" and the count reads 506; a user
  builds a nested `(ROE > 0.15 AND P/E < 25) OR (FCF yield > 0.05)` screen and it
  evaluates correctly; a custom arithmetic leaf (`marketCap / 1e9 > 100`) filters;
  a malicious formula string cannot escape the sandbox.

### (H) Visual/motion polish + 502 empty-series fix + quarterly duplicate-key crash

**Refine.** The zinc + cool-indigo system is architecturally sound; R3 tightens it
and adds AI-native motion. Accent is **`#818cf8` indigo, final**. Mark-only brand,
no text wordmark.

- **Tokens (modify `styles/tokens.css`, sync `globals.css` `--accent-rgb` +
  `chart-theme.ts` in lockstep):** five-step surface ladder
  (`#0f0f11`→`#141416`→`#1a1a1d`→`#242427`, sunken `#0a0a0c`); border-opacity scale
  (0.05/0.09/0.16/0.35); accent ramp dim `#4f46e5` / base `#818cf8` / bright
  `#a5b4fc`; text ramp primary `#e8e8f0` / secondary `#a1a1aa` / tertiary `#71717a`;
  numeric CSS `font-feature-settings: 'tnum' 1,'zero' 1,'ss01' 1` on all
  price/value elements; 4px spacing base, 28px dense-table rows; Inter (chrome) +
  JetBrains Mono (data).
- **Motion (gated behind `prefers-reduced-motion`):** streaming cursor (2px, 500ms
  step-end, accent); skeleton shimmer (surface-float→overlay, 1.4s, suppressed
  <300ms); agent-state pulse (2.4s, 6px spread, 18%); row-flash on price update
  (120ms, 8% indigo); `sourced/estimated/unverified` dot badges (6px, no animation
  on tables). Kill-switch = stillness, red border, NO glow. Remove gradients on
  chrome; glassmorphism only on overlays/palette (≥85% bg opacity, never on tables/
  chart). Copy pass: strip Bloomberg-era jargon from toasts/empty-states.
- **Fix 502 empty-series:** add `<Retry>` to the chart error state bumping
  `retryNonce` (`ChartPanel.tsx:239,1196-1203`). **Fix quarterly duplicate-key:**
  `EquityOverviewPanel.tsx:209` → `key={`${line.label}-${index}`}`.
- **Modify:** `styles/tokens.css`, `src/app/globals.css:3-4,211-252`,
  `src/lib/chart-theme.ts:9,13-15,27,49,66,69`, `ChartPanel.tsx`,
  `EquityOverviewPanel.tsx:209`; the brand mark stays mark-only (no wordmark).
- **Make impossible:** FM-9 (502 dead-end — one-click retry); FM-11 (duplicate-key);
  palette drift (lockstep token change); a non-state animation shipping (motion
  budget: only streaming-cursor / shimmer / agent-pulse / row-flash / edge-flow are
  permitted).
- **Acceptance:** dark theme at 1920×1080 AND 2560×1440 with populated panels;
  accent is `#818cf8` everywhere (no teal); mark-only header (no text wordmark);
  numeric columns tabular + slashed-zero; a transient 502 is one click to retry; no
  duplicate-key console error; `prefers-reduced-motion` disables all pulses;
  `rg "warm|clay|espresso|teal" src/app/globals.css src/lib/chart-theme.ts` returns
  nothing.

---

## 7. VERIFICATION RUNBOOK

**Sidecar-rebuild-before-verify rule (mandatory).** The sidecar is a PyInstaller
`--onefile` binary; `sidecar/` source changes are invisible until rebuilt. A stale
binary serves old data and makes all data-layer verification meaningless. **After
any `sidecar/` change, before judging any data result:**

```sh
pnpm sidecars:build                      # force-rebuild main + openbb-mcp + sec-edgar-mcp
node scripts/smoke-test-sidecars.mjs     # boot each, poll /health, TCP-probe MCP, assert screener universe 200
```

Then fully quit and relaunch — the old process holds the stale binary in memory.

**Tool-per-surface split.**

- **Playwright MCP** (trusted `isTrusted=true` events) — all clicks/typing/keys:
  composer send, palette open/select/close (Radix dismiss needs trusted events),
  panel tabs, screener run + row→cockpit drill, equity-overview symbol submit via
  autocomplete, chart timeframe (canvas-interactive), Enter-to-send / Shift+Enter,
  `/` slash picker, deep-research toggle, ASK/AUTO pill; console check for React
  duplicate-key errors; network inspector for 200/populated JSON. Point at
  `http://localhost:3000/?sidecar-port=NNNNN`.
- **Native Computer Use (macOS)** — the native menu bar Layout submenu
  (`vysted://menu-layout` → dockview re-arrange), native window chrome, the real
  WKWebView app.
- **tauri-mcp rig + Bash** (`evaluate_script` `isTrusted=false` — React works,
  canvas does NOT) — read Zustand via `window.__vystedStores` (chartCommand,
  autonomy, proposedChanges, settings, symbols, chatHistory, agentMode); `get_logs`;
  direct `curl` to separate real CORS from a 500-without-CORS-headers.

**Bring up + populate.**

```sh
pnpm tauri:mcp                           # tauri dev --features dev-tools (keychain live, rig active)
cat ~/Library/Application\ Support/com.vysted.terminal/mcp-endpoint.json   # → NNNNN sidecar port
```

Populated anchors: watchlist `AAPL, MSFT, NVDA, SPY, QQQ, BTC/USDT, ETH/USDT`;
chart `SPY + indicators + VWAP`; equity overview `AAPL`; news ≥1 headline;
portfolio ≥1 position with P&L. Cold-boot budget: up to ~90s for all three sidecars.

**Screenshot recipe (the rig `screenshot` wedges on an occluded WKWebView — use
the bridge-independent Quartz path):**

```sh
python3 /tmp/rigcap.py /tmp/vysted-1920.png   # resize window to 1920×1080 first
python3 /tmp/rigcap.py /tmp/vysted-2560.png   # then 2560×1440
```

Matches `kCGWindowOwnerName == "vysted-terminal"`. Dark theme, populated state,
both resolutions, store under `docs/screenshots/v0.8.0/<surface>/` — never overwrite.

**Keyed research run (the §2 authoritative serving check — key never touches a
shell).** Set the key via the app UI (Settings → AI Providers) or dev-only
`invoke("keychain_set",{namespace:"vysted:llm:openrouter",value:"sk-or-…"})`. Then
drive a `/research AAPL` prompt via **Playwright** (trusted events) against
`?sidecar-port=NNNNN` — `handleSend` runs in the real webview, reads the key via
`invoke("keychain_get")`, threads it into the sidecar request header. Verify the
completion is non-empty (`deepseek/deepseek-v4-flash` serves) and a brief renders
with structured data + sources. **A listing page is not this check.**

**Ordered sequence.**

```
1.  pnpm sidecars:build
2.  node scripts/smoke-test-sidecars.mjs
3.  pnpm tauri:mcp
4.  cat …/mcp-endpoint.json                       # → NNNNN
5.  curl -s http://127.0.0.1:NNNNN/health
6.  curl -s http://127.0.0.1:NNNNN/quotes/SPY
7.  curl -s http://127.0.0.1:NNNNN/fundamentals/AAPL | python3 -m json.tool   # roe/margin/debt populated
8.  [Playwright] navigate ?sidecar-port=NNNNN
9.  [Playwright] trusted clicks: data panels, screener run, row→cockpit, equity-overview submit, palette select
10. [Playwright] console: zero React duplicate-key errors (StatementTable)
11. [rig evaluate_script] __vystedStores.{chartCommand,proposedChanges,chatHistory,settings}
12. python3 /tmp/rigcap.py /tmp/vysted-1920.png
13. python3 /tmp/rigcap.py /tmp/vysted-2560.png
14. [Computer Use] macOS menu → Layout → each mode → dockview re-arranges
15. [Keychain set + Playwright] /research AAPL → keyed completion serves + brief renders (AUTHORITATIVE model check)
16. rg -i "tongyi|fallback" src sidecar   # must return only intentional migration shims (none in UI)
17. §6.5 audit: pnpm ci-local green + safety suite 9/9
```

**CI floor before any milestone:** `pnpm ci-local` mirrors CI byte-for-byte;
`pnpm format:check` before every push; before any Python commit
`ruff format <files> && ruff format --check sidecar && ruff check sidecar`.

---

## 8. BUILD SEQUENCE (commit-per-deliverable)

Ordered so trust-killers die first, the engine swaps land before the surfaces that
depend on them, and locked-file invariants are re-verified at each step.

1. **`chore(cleanup): delete dead files`** — `PlaceholderPanel.tsx`,
   `ConnectCard.tsx` + `lib/integrations/{registry,kite-connect,types}.ts` (after
   import check). (Surface 6.)
2. **`fix(deep-research): delete Tongyi backend end-to-end`** — `tongyi.py`,
   `_run_tongyi` + dispatch, `catalog.py` enum, `system.py` probe + reference
   candidates, `test_tongyi_backend.py`. (Surface 2, sidecar half.) Rebuild sidecar,
   smoke-test.
3. **`fix(settings): remove Tongyi engine + "fallback" UI, native-only deep research`**
   — `SettingsPanel.tsx`, `store/settings.ts`, `lib/hardware-fit.ts`,
   `ChatSidebar.tsx` key-forward branch. (Surface 2, frontend half.)
4. **`feat(models): default to non-thinking deepseek-v4-flash`** —
   `model_registry.json:61`, `OnboardingFlow.tsx:61` consistency, known-models
   lockstep, `workspace.ts` migration note. (§2 swap.) Rebuild sidecar.
5. **`feat(research): universal mid-call wall guard`** — `deep.py:105-112`
   `_safe_llm` `asyncio.wait_for`. (§2 guard.)
6. **`fix(screener): honest "S&P 500" label`** — `ScreenerPanel.tsx:16-18`.
   (Surface 1.)
7. **`fix(chart): retry on transient 502 + symbol autocomplete`** —
   `ChartPanel.tsx` retry button (`:239`), port `autocompleteSymbols`. (FM-9, FM-6.)
8. **`fix(equity): duplicate-key + external symbol injection`** —
   `EquityOverviewPanel.tsx:209` key, new `equity-command.ts`,
   `host-actions.ts` `open_equity_overview`. (FM-11, Pillar-B seam.)
9. **`fix(chat): rebuild composer controls inline + merge rosters`** —
   `ChatSidebar.tsx` remove `controlsOpen`/disclosure/toggle, one persona picker,
   two-mode strings (`ModeBar.tsx`, `agent-mode.ts`), rewrite the test. (Surface 3,
   Surface 5, Pillar A.) Preserve the 5 bug fixes.
10. **`fix(news): cold-boot message + auto-refresh on sidecar-ready`** —
    `NewsFeedPanel.tsx`. (FM-4.)
11. **`fix(resolve): force disambiguation pick`** — `mentions.ts` consume
    `needs_disambiguation`. (FM-7.)
12. **`style(tokens): zinc + indigo lockstep, kill warm-clay drift`** —
    `tokens.css` five-step ladder + ramps, `globals.css:3-4,211-252` fallbacks +
    `--accent-rgb`, `chart-theme.ts` comments. (Surface 7, Pillar H tokens.)
13. **`feat(ui): AI-native motion + numeric typography`** — streaming cursor,
    shimmer, agent-pulse, row-flash, dot badges, copy de-jargon pass. (Pillar H
    motion, FM-3.)
14. **`feat(palette): grouped/scoped Cmd+K + AI-ask row`** — `command-palette.ts`
    Ask group + symbol penalty + agent weight/pre-select, `CommandPalette.tsx`
    forceMount Ask + Quick Start. (Pillar C.)
15. **`feat(research): structured-only floor + tables + storyline + follow-up`** —
    `deep.py`/`iter.py` synthesis prompts, `deep.py:227-251` floor, `brief-blocks.tsx`
    tables + follow-up chips, `types/brief.ts` follow-up field. (Pillar E core,
    FM-12.)
16. **`feat(research): inline citations + sources rail + live ticker deltas + share`**
    — `sources-rail.tsx`, `renderInline` `[n]`, `types/brief.ts` source fields,
    `data-price-delta`, copy/export. (Pillar E presentation.)
17. **`feat(overview): grounded AI company overview reachable everywhere`** —
    `overview-blocks.tsx` 10 sections + grounded narrative + validation, wire all
    ticker surfaces to `openCompanyOverview`, fix screener `.NS` display leak.
    (Pillar B.)
18. **`feat(notes): Tiptap v3 markdown editor + atomic autosave`** —
    `StockNotesEditor.tsx`, `wikilink.ts`, `note-autosave.ts`, `NotesPanel.tsx`,
    `store/notes.ts` raw-markdown. (Pillar F.)
19. **`feat(screener): nested AND/OR groups + mathjs formula leaves`** —
    `GroupBuilder.tsx`, `formula-eval.ts` (mathjs hardened worker),
    `store/screener.ts:140-141` tree, `industry` column. (Pillar G.)
20. **`docs(claude-md): native-only deep research, indigo, mark-only`** —
    `CLAUDE.md:200-205,229`, drop Qwen-A3B/phase markers across the cleanup files.
    (Surface 8 + doc reconcile.)
21. **`test(verify): live keyed serving check + screenshots + §6.5 9/9`** — run §7
    sequence; capture populated 1920×1080 + 2560×1440 under
    `docs/screenshots/v0.8.0/`; confirm `pnpm ci-local` green and the safety suite
    9/9; `rg -i "tongyi|fallback"` clean in UI.

At every step: §6.5 audit 9/9, Tier-1 LOCKED files untouched, orders never
auto-apply, no merge to main, version stays `0.8.0`.
