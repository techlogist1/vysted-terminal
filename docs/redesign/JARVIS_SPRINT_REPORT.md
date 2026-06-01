# JARVIS Sprint — final report

_Overnight autonomous sprint on branch **`002-jarvis-intelligence`** (off
`001-agent-native-redesign`, base `fcd6fcf`). Authored 2026-06-02 by the lead (Opus 4.8,
1M). Not merged to main; version not bumped. Companion docs:
[`JARVIS_SPRINT_FINDINGS.md`](JARVIS_SPRINT_FINDINGS.md) (Phase-0 decisions + fork log),
[`JARVIS_SPRINT_TELEMETRY.md`](JARVIS_SPRINT_TELEMETRY.md)._

---

## 0. Honest self-assessment — does it feel like JARVIS now?

**Materially closer, in the two ways that mattered most: it no longer feels dead, and it no
longer makes you pick a mode.** The headline complaints are fixed at the root:

- **"The agent feels DEAD and STUCK — research fires and nothing happens"** → **fixed and
  rig-verified.** A deep/fast research run now streams a live, animated "RESEARCHING" trace
  (plan → search → gather → reflect → synthesize) with per-step icons, real latencies, a live
  elapsed timer, and a brewing scanline — the sci-fi "it's working" feel. The cognition was
  always real (the sidecar emitted steps); it was being thrown away. Now it's surfaced live.
- **"It must GET me, not make me hit-and-try"** → the four modes (Ask/Edit/Build/Delegate) are
  collapsed into ONE inferred **Agent** surface: the sidecar infers read vs edit vs build from
  your words and gates accordingly — no mode-picking, and the AUTO-vs-Build contradiction is
  gone. Delegate stays distinct (its BudgetGuard is a safety surface). The copilot now biases to
  action (best guess + adjust, no "please rephrase" / "let me check" stalls) and decomposes
  compound requests into one sequence. Ad-hoc "put the chart here, news there" arrangements land.
- **The brain got a real upgrade** — one OpenRouter key now brokers every provider with
  cheapest-capable routing, and a frontier deep-research path (Tongyi via OpenRouter, Qwen-A3B
  fallback) is wired and gated by a hardware fit-scorer that correctly refuses to pretend this
  16 GB M1 can host a 30B model.

**Where it's honestly NOT yet fully JARVIS:** the _behavioral_ quality of multi-step and
intent on THIS machine is capped by the default local model (`qwen2.5:7b`, whose tool-use is
unreliable). The mechanisms are all in place and the safe paths are wired; the _felt_
intelligence steps up sharply the moment a capable model is configured (Anthropic/OpenAI key,
or the new OpenRouter broker). That's a configuration gap, not a code gap — and the fit-scorer +
broker now make crossing it a one-key action. I did not embed OpenCode (it would have inverted
the §6.5 architecture — see §3); the in-house reasoning we built instead is the right call.

The spine held: **every track is strictly additive, the §6.5 audit is 9/9, and the Tier-1 LOCKED
files are byte-for-byte untouched.** The app at the end of the night is strictly better and fully
functional — nothing is half-rewired.

---

## 1. What shipped, per track

### Track A — Aliveness (the live research surface) · commit `ba517ca`

**Shipped:** a new `research_step` SSE event; a per-tool-dispatch step-sink in the runtime that
runs a long tool as a task and drains its steps onto an `asyncio.Queue`, re-emitting each
`ResearchStep` as a live event **while the tool runs** (interleaved before the terminal `done`);
both `deep_research` and FAST `research` now forward steps (FAST emits a plan/tool/search/
synthesize trace too, so the default mode also feels alive); a `ResearchActivity` React surface
(spinning radar, per-kind icons, live elapsed timer, per-step latency, a brewing scanline;
collapses to a compact "Researched in Ns · M steps" trace when done).

**The bug it fixed:** `deep_research._run_native` passed `on_step=steps.append` — a **dead local
list** — and the tool ran the entire ≤120s loop as one silent round, returning only the final
brief. The live-emit infrastructure existed; nothing forwarded it.

**Verified:** sidecar e2e test proving `research_step` events stream interleaved before `done`;
vitest for the store logic; typecheck. **RIG-VERIFIED** on the live app — see §4.

### Track E — Smart brain (OpenRouter broker + in-house planner) · commit `5131758`

**Shipped:** **OpenRouter** as a unified BYOK provider (one key, all upstreams) riding the
OpenAI adapter via base-url override (like deepseek/xai) — with OpenRouter attribution headers +
**cheapest-capable provider routing** (`extra_body.provider sort:price`; `require_parameters`
when tools are sent so multi-round tool use never routes to a tools-dropping provider).
**`services/planner.py`** — the OpenCode fallback: `classify_intent` (deterministic NL→intent,
no LLM) + `decompose` (LLM-backed compound decomposition, graceful single-step fallback).

**Verified:** OpenRouter dispatch + headers + routing-block tests; 22 planner tests; 259-test
targeted sweep; typecheck. `classify_intent` is live-wired into Track B; `decompose` is a tested
utility (see Fork §4.3 — preamble-driven decomposition shipped instead of a redundant pre-pass).

### Track D — Hardware fit-scorer · commit `0e4d6c0`

**Shipped:** `services/hardware_fit.py` — injectable device probe (Apple Metal budget =
66%/75% of unified RAM; CPU heuristic otherwise) + a pure scorer (weights from GGUF file size or
params×quant; KV per token sized on **active** params for MoE so a 30B-A3B isn't over-counted;
GREEN/MARGINAL/RED bands; `ctx_max` solver). `GET /system/hardware` (device + scored ollama
models + reference candidates). A Settings "Hardware & local models" card. `can_run_locally()` is
the gate Track C's Tongyi decision reuses.

**Verified:** 17 tests (incl. 16 GB→remote and 64 GB→local auto-promotion); **live curl on this
machine** returned correct verdicts (see §5). Settings card typechecked; live render in §4.

### Track C — Research engine whole (SearXNG fix + Tongyi-remote) · commit `5cb6207`

**Shipped:** fixed the **SearXNG autodetect** — it probed `/healthz` (which SearXNG has no
endpoint for) then `/config` (proves up, not JSON-capable); replaced with the **capability
probe** `/search?format=json` (200+results = usable, 403 = JSON-disabled with an actionable
message), multi-port (8888→8080), BYO-URL, 6 s timeout. A **Tongyi-remote** deep backend
(`services/research/tongyi.py`) that reuses our deep loop (so the live step-log still feeds Track
A) but binds the LLM to OpenRouter's Tongyi model — runtime-probed (the slug is listed-but-
unrouted today) with a live Qwen-A3B fallback; opt-in + BYOK, never auto-selected. A Settings
one-command local-SearXNG setup hint.

**Verified:** 50+ tests (probe/403, resolve/fallback/handler) + catalog parity. **LIVE-VERIFIED
end-to-end against a real `searxng/searxng` container** (OrbStack): the fixed autodetect found it
in 1.96 s and an absent URL failed in 0.01 s; a real query returned cited results.

### Track B — Competence (inferred intent + arrange + act-first) · commit `98a1ba8`

**Shipped:** collapsed Ask/Edit/Build → ONE inferred **`agent`** mode (kept **Delegate**); the
sidecar infers intent (`classify_intent`) and applies the read-only gate iff the intent is a
read — the old Ask safety line, no picker, and **the AUTO-vs-Build contradiction is gone**.
Legacy modes fold to `agent` on restore. **Custom arrange** — `arrange_layout pattern='custom'` +
a `panels` list (names or `{panel,direction,reference}`) so "one panel here, one there" lands on
the existing generic plan engine. The copilot prompt now biases to action (no stalls) and
decomposes compound requests into one host-action sequence.

**Verified:** sidecar inference-gate tests (read→read-only, build→host-actions); `planCustom` /
`resolvePanelToken` tests; updated mode tests; **854 vitest + full sidecar agent/catalog sweep**;
typecheck. AUTO-vs-Build contradiction confirmed-then-killed (the Phase-0 baseline screenshot
showed it live).

---

## 2. Phase-0 architecture decisions (the why) — see FINDINGS §2

| Fork                         | Decision                                  | Why                                                                                                                                                                             |
| ---------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| OpenCode as reasoning engine | **FALLBACK** — in-house planner           | It owns the agent loop by design; its permission gate would sit _upstream_ of §6.5, inverting the safety architecture. The valuable part (planning) is cheap to build in-house. |
| OpenRouter as broker         | **ADOPT**                                 | Clean OpenAI drop-in; 5 edits, no LOCKED files; cheapest-capable routing.                                                                                                       |
| SearXNG                      | **ADOPT** (client existed; fixed)         | Genuinely local + keyless; the autodetect was silently broken. Live-verified.                                                                                                   |
| Tongyi local on 16 GB        | **REMOTE** (fit-scorer-gated)             | 30B-A3B MoE holds all params resident; smallest sane quant (17.6 GB) > 16 GB and blows the 10.6 GiB Metal budget.                                                               |
| Tongyi via OpenRouter        | **Probed + Qwen-A3B fallback**            | The live OpenRouter API shows the Tongyi slug listed but unrouted (0 endpoints) today.                                                                                          |
| Multi-step planning          | **Preamble-driven** (not an LLM pre-pass) | `classify_intent` wired for the gate; `decompose` would be a redundant 2nd decomposition + latency, unverifiable on the local model. (Fork §4.3)                                |

**Every fallback kept the app working and the floor intact.** Nothing ambitious-but-unverified
was committed as load-bearing; each is logged for you in FINDINGS §4.

---

## 3. Gate results (the floor)

- **Tier-1 LOCKED files vs base `fcd6fcf`: EMPTY diff** — `types/plugin.ts`, `types/safety.ts`,
  `types/broker.ts`, the safety/broker/audit/kill-switch models, `broker_base.py`,
  `kill_switch.rs`, `test_safety_end_to_end.py`, `tauri.conf.json`, CI — all byte-for-byte
  untouched.
- **§6.5 safety audit: 9/9 PASS** — incl. test*audit_2 (no bypass to `_place_confirmed`) and
  test_audit_6 (the AI-order grep gate: no `place*/submit\_/execute_order`, no `auto_approve`
  anywhere in the tree). Orders never auto-apply; AUTO auto-applies UI/layout/chart/watchlist
  only; brokers read-only.
- **No new pip dependency** in any track (all on existing httpx/fastapi/openai-SDK/stdlib) — no
  PyInstaller `--copy-metadata`/`--collect-data`/`--add-data` exposure to audit.
- **`pnpm ci-local`**: _result recorded in §6 once the background run completes._
- **`smoke-test-sidecars.mjs`**: _result recorded in §6._

---

## 4. Rig evidence (live app, dark, populated)

_Captured on the live Tauri app (tauri-mcp rig, M1 native res); see §6 for the consolidated
post-rebuild pass._

- **Track A — RIG-VERIFIED:** the `ResearchActivity` surface rendered live in the agent dock — an
  amber "⊚ RESEARCHING" panel with a ticking elapsed timer (12 s), all five steps (Planning
  820 ms → Searching 1430 ms → Gathering data 610 ms → Assessing coverage 540 ms → Writing the
  brief, spinning) and the animated scanline — alongside a populated, dark, **live-data** cockpit
  (SPY 759.59 +0.51% / QQQ +0.81% with YFINANCE·LIVE badges; NVDA news, POSITIVE +0.70 sentiment)
  and a "Connected" header. Real-shaped data injected via the dev store bridge (the same store
  action the live SSE path drives); the backend streaming is independently pytest-proven.
- **AUTO-vs-Build contradiction (Phase-0 baseline):** the pre-change screenshot captured it live
  — Build mode "you review before anything opens" beside AUTONOMY=AUTO "applies UI changes
  without asking." Track B removes the mode picker, so the contradiction no longer exists.
- **Track B — RIG-VERIFIED on the rebuilt binary (pixel + DOM):** the mode bar now shows exactly
  **`Agent ⌥1` + `Delegate ⌥2`** (no Ask/Edit/Build); the store defaults to `agent`; the empty
  state reads "Mode: Agent — Reads, edits, or builds from your words. UI changes apply on review
  (or instantly in AUTO); orders always need review" and the composer "Describe what you want —
  JARVIS infers whether…". The §6.5 order line is explicit; the AUTO-vs-Build contradiction is gone.
- **Tracks D + E — LIVE on the rebuilt `--onefile`:** `GET /system/hardware` on the running
  sidecar returned the correct M1 verdicts (qwen2.5:7b/llama3.1:8b GREEN ctx 12288; Tongyi-30B
  RED); `GET /llm/providers` now lists `openrouter` among the 8 providers. (Proves the new code
  runs in the shipped binary, not just under pytest.)

---

## 5. The fit-scorer's verdict on THIS M1

Detected: **Apple M1 Pro (`MacBookPro18,3`), 16.0 GiB unified, ~10.6 GiB Metal GPU budget, 6P+2E
cores, macOS 26.3, arm64.** Ollama 0.24 up with `qwen2.5:7b` + `llama3.1:8b`.

| Candidate                                    | Verdict               | Gate decision                 |
| -------------------------------------------- | --------------------- | ----------------------------- |
| `qwen2.5:7b` (Q4_K_M)                        | 🟢 GREEN (ctx ≤ 12 K) | enable local                  |
| `llama3.1:8b` (Q4_K_M)                       | 🟢 GREEN (ctx ≤ 12 K) | enable local                  |
| Tongyi-DeepResearch-30B-A3B (IQ3_S / Q4_K_M) | 🔴 RED                | **force remote** (OpenRouter) |
| Llama-class 14B (Q4_K_M)                     | 🔴 RED (conservative) | remote                        |

**Verdict: this travel rig earns the small local models for light tool work, but not a frontier
deep-research model — exactly why Track C routes Tongyi remote.** On a 32 GB+ box the same code
auto-promotes Tongyi to local (gpu_fit drops to ~0.4 → GREEN) with no change.

---

## 6. Verification snapshot + what's left running

- **Branch:** `002-jarvis-intelligence`, pushed to origin. 9 track/doc commits + this report.
  Not merged to main; version untouched.
- **`pnpm ci-local`: PASS (exit 0)** — the full CI mirror, green end-to-end: install
  `--frozen-lockfile` → ensure-all-sidecars (clean **rebuild of the main sidecar with all five
  tracks**; the two MCP sidecars fresh/skipped) → eslint → prettier `--check` → tsc → cargo fmt
  `--check` → **cargo clippy `-D warnings`** → ruff check + format → **vitest 854 passed** →
  cargo test → **pytest 1288 passed** (1 deprecation warning). _(The first two attempts failed
  only because this background shell lacks a bare `python` on PATH — the script assumes it;
  resolved by putting the project venv on PATH. Not a code failure.)_
- **`smoke-test-sidecars.mjs`: PASS** — the freshly-rebuilt binaries boot cleanly: main sidecar
  `/health` OK + the screener-universe endpoint OK (proves the new code RUNS in the `--onefile`
  binary, not just under pytest); openbb-mcp + sec-edgar-mcp bound and survived the settle window.
- **Final rig pass (rebuilt binary, all five tracks): DONE** — the app is relaunched on the
  freshly-built `--onefile` (main sidecar on `:52479`, both MCP children bound). Verified live:
  the mode bar = `Agent ⌥1` + `Delegate ⌥2` (Track B, pixel + DOM); `/system/hardware` returns the
  correct M1 verdicts (Track D); `/llm/providers` lists `openrouter` (Track E); Track A's
  `ResearchActivity` surface was rig-verified earlier in the session. App + rig left running for
  you (display nudged awake with `caffeinate` for the capture; it may sleep again — re-nudge if a
  screenshot returns black). _Note: a live "research NVDA → streamed steps" end-to-end demo
  depends on a reliable tool-calling model; the default local `qwen2.5:7b` is unreliable, so the
  live stream is best seen with a capable model configured — the backend streaming itself is
  pytest-proven and the surface is rig-proven via real-shaped data._

### Carry-forwards / logged for you (FINDINGS §4)

1. **OpenCode** as an opt-in, sandboxed read-only research planner (deny-all + `plan` agent +
   reasoning-part streaming) — never on the §6.5 path. A feature spike, not core infra.
2. **`decompose()`** → a visible "plan-then-execute" surface (plan in the activity log, steps
   staged in the gate) once a capable model is the default.
3. **Tongyi on OpenRouter** — relisted-availability probe already in place; promotes automatically
   when OpenRouter routes the slug again.
4. **Local SearXNG auto-launch/bundle** from the Tauri core (fragile under PyInstaller + needs
   process lifecycle mgmt) — the autodetect + BYO-URL + one-command setup ship now; auto-bundling
   is the follow-up.
5. **Compare dual-panel axis-lock** — NOT attempted this sprint (the chart-command channel is
   singleton; a `Map<panelId,…>` refactor is ~1 afternoon per the Phase-0 map). Logged, not done,
   to protect the budget for the five core tracks; the overlay compare still works today.
6. **Native-citation emission validation** — the citation normalizers (5 providers) ship + are
   unit-tested; live validation needs a real provider key (not available this sprint).

### The honest caps

- Behavioral quality of intent/multi-step on this box is gated by the local model's tool-use
  reliability; configure a capable model (or the new OpenRouter key) to feel the full step-up.
- BYOK live round-trips (OpenRouter, Exa, Perplexity, native search) are unit-tested against
  mocks + the real wire format, but not live-validated (no keys available overnight).
