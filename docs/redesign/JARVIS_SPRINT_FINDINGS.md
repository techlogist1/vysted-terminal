# JARVIS Sprint — Phase 0 findings & architecture decisions

_The de-risking record for the overnight JARVIS intelligence sprint (branch
`002-jarvis-intelligence`, off `001-agent-native-redesign`). Phase 0 maps the **as-built**
Pass-B reality, spikes the four external integrations (OpenCode, OpenRouter, SearXNG,
Tongyi-DeepResearch), and records the verified path + fallback for every risky fork.
Authored 2026-06-02._

---

## 0. The non-negotiable floor (every phase, every fork)

- The existing **agent loop** (`sidecar/services/agent_runtime.py invoke_agent`) + the
  **§6.5 safety gate** are the spine and the executor. Never replaced, never bypassed,
  never routed around. Every agent mutation rides the **diff/accept gate**
  (`src/store/proposed-changes.ts`); orders are hard-excluded at the enqueue chokepoint and
  **never auto-apply in any mode**. AUTO auto-applies UI/layout/chart/watchlist only.
- **§6.5 audit stays 9/9.** Tier-1 LOCKED files byte-for-byte untouched (`types/plugin.ts`,
  `types/safety.ts`, `types/broker.ts`, the safety/broker/audit/kill-switch models,
  `broker_base.py`, `kill_switch.rs`, `test_safety_end_to_end.py`, `tauri.conf.json`, CI).
  Brokers read-only. Secrets in OS keychain, per-request, never logged.
- **Lossless quality:** every irreversible change must be verified working or we take the
  fallback and log the ambitious path. The app ends the night **strictly better and fully
  functional** — a clean partial win beats an ambitious break.

---

## 1. As-built reality (first-hand, confirmed at branch HEAD `fcd6fcf`)

**Pass B (B1–B6) already shipped.** The kickoff handoff (`PASS_B_BUILD_HANDOFF.md`)
described the plan; the git log + the tree confirm it landed. So a great deal of what the
sprint brief frames as "to build" already exists — the sprint's job is to make it **feel
alive and competent**, and to add the **keyless/frontier research paths + a model broker +
a hardware fit-scorer** on top.

### The agent + research spine (exists)

- **Agent loop:** `sidecar/services/agent_runtime.py` — `invoke_agent` tool-use loop,
  `_MAX_TOOL_ROUNDS=6`, streams `LLMStreamEvent` over SSE.
- **Capability catalog (single source of truth):** `sidecar/services/agent_tools/catalog.py`
  → `schemas.py` (`TOOL_SCHEMAS`), `registry_v0_6_0.py`/`registry_v0_6_5.py` wiring,
  `models/custom_agent.KNOWN_TOOL_IDS`, MCP surface. Parity gates:
  `test_capability_catalog.py`, `test_mcp_catalog_parity.py`.
- **Research engine:** `sidecar/services/research/` — `fast.py` (228 L, ≤15s loop),
  `deep.py` (566 L, BudgetGuard-bounded deep loop), `perplexity.py` (316 L, Sonar opt-in),
  `models.py`. Agent-tool handlers: `agent_tools/{deep_research,research,web_search}.py`.
- **Search backends:** `sidecar/services/search/` — `base.py` (interface), `registry.py`,
  `exa.py` (BYOK), `searxng.py` (220 L — **client exists**), plus `llm/native_search.py`
  (native-on-key). So SearXNG, Exa, Perplexity, and native search are all already wired as
  backends.
- **Brief output:** `src/modules/research/BriefPanel.tsx` + `src/store/brief.ts` — holds the
  **final** `ResearchBriefData` (query, mode FAST|DEEP, markdown, sources, sourceCount,
  webAvailable, createdAt), persisted in the workspace blob.

### The mode / autonomy / gate axes (exists)

- **Modes (intent axis):** `src/store/agent-mode.ts` + `types/agent-modes` — four modes
  Ask / Edit / Build / Delegate (⌥1–4), ride the workspace blob; server-side filters Ask to
  read-only tools.
- **Autonomy (confirmation axis):** `src/store/agent-autonomy.ts` — `ask | auto`, orthogonal
  to modes. AUTO auto-applies UI/layout/chart/watchlist, **never an order** (excluded in
  `proposed-changes.ts` + re-routed by `accept()`).
- **Host actions + gate:** `src/lib/host-actions.ts`, `src/store/proposed-changes.ts`,
  `ChatSidebar` `executeHostAction`. Chart channel: `src/store/chart-command.ts`.

### Providers / models (exists; no OpenRouter yet)

- `sidecar/config/model_registry.json` — single source of truth: anthropic, openai, gemini,
  groq, ollama, deepseek, xai. **No `openrouter`** → greenfield. deepseek/xai already ride
  the OpenAI adapter via `default_base_url` override — the exact template for OpenRouter.
- **ollama is running on this machine** (`127.0.0.1:11434`) — local-model paths are testable.

### Verification capability in this environment

- Sidecar logic: `sidecar/.venv/bin/python` (3.13.13, fastapi 0.136.1, pytest 9.0.3) — run
  pytest + uvicorn + curl directly (no binary rebuild needed for logic).
- Frontend logic: vitest + tsc.
- Rig: `pnpm tauri:mcp` (= `tauri dev --features dev-tools`) drives the live app; pre-built
  sidecar binaries exist (main rebuilt 2026-06-01). **Python changes need a binary rebuild
  to show in the rig** — rebuild + smoke at milestones, curl/pytest for logic in between.

---

## 2. Phase-0 spike verdicts (per external integration)

> Resolved from the Phase-0 workflow (`ws1wyq5b2`, 8 agents, 615k tokens, ~4.5 min) +
> first-hand checks. Each verdict cites the verified path and the fallback.

### 2.1 OpenCode as a supervised reasoning engine — **VERDICT: FALLBACK**

OpenCode (`opencode serve` + `@opencode-ai/sdk`) is technically embeddable — server mode,
reasoning/tool parts over SSE, and a `deny|ask|allow` permission gate resolved over HTTP all
exist. **But it owns the agent loop by design** (Vercel AI SDK `streamText`: LLM→tool→feed-
back, synchronous). Embedding it means two competing loops + two safety gates, with
OpenCode's gate sitting _upstream_ of ours — which **inverts the §6.5 architecture** (our gate
must be the unconditional chokepoint, never downstream of an external resolver). Its tools are
coding-shaped; the only §6.5-safe config (`permission: deny` + custom finance tools routed to
our gate) is also the config where it contributes nothing but reasoning we can produce in-house.

**Verified path (taken):** strengthen our OWN intent/multi-step planning directly — an
in-house **planner pass** in the existing loop that emits a proposed step list our existing
diff/accept gate approves. No new process, no provider duplication, zero §6.5-bypass risk.
**Ambitious path (logged for operator):** OpenCode as an opt-in, sandboxed **read-only
research planner** (`plan` agent + deny-all + reasoning-part streaming), never near §6.5.
See fork log §4.1.

### 2.2 OpenRouter as the model broker — **VERDICT: ADOPT**

Clean OpenAI drop-in: `base_url=https://openrouter.ai/api/v1`, `Authorization: Bearer`,
optional `HTTP-Referer`/`X-Title`. SSE + tool-calling are OpenAI-shaped (re-send `tools` every
turn — already our rule; ignore `: OPENROUTER PROCESSING` keep-alive comments; surface
mid-stream `error` events). Adding it = **5 edits + 1 test, zero LOCKED files** — rides the
OpenAI adapter via base-url override exactly like deepseek/xai. Direct-provider BYOK stays the
fallback. **Cheapest-capable** = cache `/models` at boot, filter by `supported_parameters`
(incl. `tools`) + `context_length`, sort by effective price, then send
`provider:{sort:"price", require_parameters:true, max_price:{…}, data_collection:"deny"}`.
Read the response `model` + `X-Generation-Id` for the supervised audit trail.

### 2.3 SearXNG (local keyless web search) — **VERDICT: ADOPT (client exists; fix + verify)**

The SearXNG backend, three-tier dispatch, BYO-URL setting, and per-request header threading
are **already built and tested** (`sidecar/services/search/searxng.py`, `registry.py`,
`config.py`, `search-headers.ts`). Two concrete gaps Track C fixes:

1. **Autodetect probes `/healthz`** — but SearXNG core has **no `/healthz`** (upstream issue
   #4026). The correct probe is `GET /search?q=test&format=json` (200+JSON = usable; 403 =
   up-but-JSON-disabled, surface the `settings.yml` fix). Also probe `8888` (pip default) then
   `8080` (Docker default).
2. **JSON format + limiter** — a real instance needs `search.formats: [html, json]` and
   `server.limiter: false` + `public_instance: false` (the latter drops the Redis/Valkey dep).
   **Verified path (taken):** fix the probe, document/ship a one-command local-SearXNG setup
   (OrbStack/Docker `searxng/searxng`, ~200 MB), live-verify autodetect + a real search end-to-end
   during the sprint. **Ambitious path (logged):** auto-launch/bundle a SearXNG instance from the
   Tauri core — fragile under PyInstaller + needs process lifecycle mgmt; log as follow-up.

### 2.4 Tongyi-DeepResearch fit on this M1 (16GB) — **VERDICT: REMOTE (forced by fit-scorer)**

Local 30B-A3B does **not** fit 16 GB: the MoE holds **all** 30.5B params resident (the "A3B" is
a throughput number, not a memory number); smallest sane quant Q4 ≈ 17.6 GB > 16 GB, and even
Q2/Q3 (which technically load) blow the ~10.6 GiB Metal GPU budget → swap/CPU-thrash AND
lobotomize the agentic reliability that is the model's whole point. **Verified path:** route
Tongyi via OpenRouter (depends on §2.2). **Correction from the live API:** the slug
`alibaba/tongyi-deepresearch-30b-a3b` is **listed but currently unreachable** (0 live endpoints;
absent from live `/models`). So Track C wires it as a **runtime-probed** target
(`GET /models/.../endpoints → endpoints != []`) with a live fallback to
`qwen/qwen3-30b-a3b-thinking-2507` (closest A3B analog, reasoning + tools) → then
`qwen/qwen3-235b-a22b-thinking-2507`. The fit-scorer auto-promotes to **local** Tongyi on a
32 GB+ rig (gpu_fit drops to ~0.4 → GREEN) with no code change.

### 2.5 Hardware fit-scorer verdict for this M1 — **VERDICT: BUILD (Track D)**

Detected: **MacBook Pro M1 Pro (`MacBookPro18,3`), 16 GiB unified, 6P+2E cores, macOS 26.3**,
Metal GPU budget **≈10.6 GiB** (66% of RAM < 36 GB). Ollama 0.24.0 up with `qwen2.5:7b`
(4.68 GB Q4_K_M) + `llama3.1:8b` (4.92 GB Q4_K_M) — both **viable locally at ≤8–12K context**
(GREEN at ≤8K, MARGINAL at 32K). The scorer (concrete formula in hand: weights from GGUF file
size + KV-per-token × ctx + overhead, vs `gpu_budget = ram×0.66` and `ram - 4 GB reserve`;
GREEN/MARGINAL/RED bands; `ctx_max` solver; MoE sized on **total** params) runs at sidecar boot,
caches the device profile, and gates every heavy local path. On THIS box it forces local-Tongyi
→ remote and caps local ollama models to their `ctx_max`.

---

## 3. The five tracks — plan & fork decisions

Dependency graph: **A** (independent, highest-value) → **D** (independent, gates C) →
**E** (OpenRouter + in-house planner — feeds B's multi-step & C's remote-Tongyi) → **C**
(needs E) → **B** (needs E's planner). Build order: **A → E → D → C → B**, each committed as a
coherent chunk and rig/test-verified before the next.

- **A — Aliveness (the J):** the live-step infra already exists (`deep.run_deep_research(on_step=…)`)
  but the steps are **discarded** (`deep_research.py` collects them into a dead local list and
  returns only the final brief; the `deep_research` tool blocks for up to 120s as one silent
  tool round). Fix: a new `LLMResearchStepEvent` SSE event, thread `on_step` →
  `agent_runtime` → SSE → a **live animated "thinking/working" surface** in the chat dock (the
  BriefPanel `StepLog` exists but is post-hoc only). No spine-replacement, no LOCKED file.
- **E — Smart brain:** add **OpenRouter** as a BYOK provider (§2.2) + a cheapest-capable model
  selector; build an **in-house planner pass** (the OpenCode fallback, §2.1) that decomposes a
  compound request into a proposed step list the existing gate approves. Spine supervises;
  OpenRouter brokers; the planner reasons — never bypassing the loop or §6.5.
- **D — Hardware fit-scorer:** `sidecar/services/hardware_fit.py` per §2.5 + a settings surface
  - an agent-readable capability so the app degrades gracefully and enables heavy local paths
    only where the device earns it.
- **C — Research engine whole:** fix the SearXNG autodetect probe + ship local-SearXNG setup
  (§2.3, live-verified); add a **Tongyi-remote** deep backend via OpenRouter (probed + Qwen-A3B
  fallback, §2.4), gated by the fit-scorer. Exa/native/Perplexity stay the BYOK/opt-in upgrades.
- **B — Competence:** collapse Ask/Edit/Build into ONE inferred-intent surface (keep Delegate +
  its BudgetGuard); an **intent layer** (loose language → right action first try); **multi-step**
  via E's planner; **arrange** (a `custom` layout plan so "one here, one there" lands — the
  dockview/`applyPlan` layer already supports arbitrary positions); **stop over-confirming**
  (make the auto-apply gate mode-aware so AUTO genuinely auto-applies UI without a proposal bar
  and the AUTO-vs-Build contradiction dies with the mode picker). Compare dual-panel axis-lock:
  the chart-command channel is singleton → a `Map<panelId,…>` refactor (~1 afternoon) is
  tractable; attempt if time allows, else log.

---

## 4. Fork log (where the fallback was taken)

_(Each entry: the fork, the ambitious path, why the fallback was taken, what was logged for
the operator. Appended as forks are hit.)_

### 4.1 OpenCode embedding → in-house planner (Phase 0)

- **Fork:** use OpenCode (`opencode serve`) as the supervised reasoning engine for B's
  intent/multi-step/arrange, vs. strengthen our own loop.
- **Fallback taken:** in-house planner pass in the existing loop.
- **Why:** OpenCode owns the agent loop by design and its permission gate would sit _upstream_
  of §6.5 — running it on/near the execution path inverts the safety architecture (a Tier-4
  risk to the floor). The §6.5-safe config reduces it to a pure reasoner we can replicate
  in-house at zero new-process cost. A clean partial win (our own smarter planner) beats an
  ambitious break (two competing loops/gates).
- **Logged for operator:** OpenCode as an OPT-IN, sandboxed **read-only research planner**
  (`plan` agent + `permission:deny` + reasoning-part streaming for display only), never wired
  to order execution or the trading wrapper. A future feature spike, not core infra.

### 4.2 Tongyi local weights → remote via OpenRouter (Phase 0)

- **Fork:** run Tongyi-DeepResearch-30B-A3B locally vs. via OpenRouter.
- **Fallback taken:** remote via OpenRouter, gated by the fit-scorer (auto-promotes to local on
  32 GB+ hardware).
- **Why:** the MoE needs all 30.5B params resident; smallest sane quant (Q4 ≈17.6 GB) exceeds
  this 16 GB box and blows the ~10.6 GiB Metal budget — local would swap/thrash and degrade the
  agentic reliability that is the model's whole value. Not verifiable-working locally → take the
  remote path that IS verifiable.
- **Logged for operator:** the live OpenRouter API shows the Tongyi slug **unreachable today**
  (0 endpoints) — wired as a runtime-probed target with a live Qwen-A3B fallback; revisit when
  OpenRouter relists it (a boot/cron `/endpoints` probe promotes it automatically).

### 4.3 Multi-step: preamble-driven decomposition vs. an LLM pre-pass (Track B)

- **Fork:** wire `planner.decompose()` (the LLM compound-decomposer) as a live PRE-PASS in
  `invoke_agent` vs. drive multi-step through the model itself via the prompt.
- **Decision taken:** the deterministic half of the planner — `classify_intent` — IS live-wired
  (it gates read-only vs. mutating server-side, the mode-collapse spine). For decomposition, the
  copilot preamble now explicitly instructs the model to decompose a compound request and emit
  the whole host-action sequence in one turn; the existing loop already supports a batch of tool
  calls per round + the diff/accept gate batches them. A capable model (via the OpenRouter broker)
  decomposes reliably this way.
- **Why not the LLM pre-pass:** a `decompose()` pre-pass would be a SECOND decomposition (redundant
  with the model's own, since the preamble already instructs it) and adds an LLM round-trip's
  latency to every compound build. Verifying it _improves_ behavior also needs a live capable model
  (the local qwen-7b tool-use is unreliable) — so a live pre-pass couldn't be cleanly verified
  tonight. Per the floor (verified-working > ambitious-unverified), I shipped the preamble path
  (verifiable) and kept `decompose()` as a **tested, exported planner utility** ready for an
  explicit-plan surface.
- **Logged for operator:** wire `decompose()` to a visible "plan-then-execute" surface (the plan
  rendered in the activity log, steps staged in the gate) when a capable model is the default — a
  follow-up that makes the in-house planning _visible_, not just reliable.
