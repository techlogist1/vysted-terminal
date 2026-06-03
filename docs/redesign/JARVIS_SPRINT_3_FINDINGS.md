# JARVIS Sprint 3 — Phase-0 findings & architecture decisions

_The research-EXPERIENCE pass on branch `002-jarvis-intelligence`. The engine is
world-class; this pass makes research **stop telling and start SHOWING** — a
living, visual, terminal-connected brief that beats Perplexity Finance. Phase-0
fan-out: 4 read-only code-seam mappers + 3 frontier web-research agents (793k
subagent tokens). Companion: `JARVIS_SPRINT_3_TELEMETRY.md`, prior
`JARVIS_SPRINT_2_REPORT.md`._

---

## 0. The problem, precisely located

The whole research→brief→chat flow is **LLM-driven**: the agent calls
`research`/`deep_research`, gets the full `ResearchBrief` back **as a tool-result
JSON string that only the model sees**, and must then _remember_ to call the
`publish_brief` host-action with the markdown+sources copied across. On the
default local model (`qwen2.5:7b`, unreliable tool-use) that copy step is the
exact failure behind "the agent feels dead / nothing renders / it dumps an essay
in chat." Three concrete gaps confirmed first-hand via the spike:

1. **The brief is "dead data" without an explicit `publish_brief` tool call** —
   the full brief (incl. the `structured` price/fundamentals/news/filings bundle)
   is serialized into the LLM context only; the frontend never receives it
   directly (`agent_runtime.py:704-716`; `streaming.ts:180-186` carries tool_use
   ARGS, never the RESULT).
2. **The frontend brief contract drops `structured`** — `types/brief.ts`'s
   `ResearchBriefData` has no `structured` field, so even a published brief has
   **nothing to build metric cards from**. The backend assembles + ships it; it
   dies at the TS boundary.
3. **The chat answer renders as raw `whitespace-pre-wrap` text**
   (`ChatSidebar.tsx:793-800`) — a long markdown essay/table shows as a wall of
   asterisks and pipes, with no collapse when a brief was already published.

## 1. The architecture decision — deterministic, not model-dependent

**Principle for this pass: reduce LLM dependence wherever deterministic logic can
do the job.** "Showing not telling" must be robust on a weak model, or it's the
same half-working feature. Two backbone decisions:

### 1a. Auto-publish the brief (the robustness backstop)

When `research`/`deep_research` returns `ok`, the **runtime deterministically
publishes the brief** (carrying the FULL bundle incl. `structured`) instead of
waiting for the model to call `publish_brief`. It rides the **existing
proposed-changes gate** (synthetic `publish_brief` host-action) so AUTO applies it
instantly and review mode queues one accept — the §6.5/constitution gate is
preserved, never bypassed. The model's own `publish_brief` (if it fires) is
idempotent. **Fallback:** if the result is malformed the auto-publish silently
skips (the live research trace still animated; the model can still publish). App
strictly better, never half-rewired.

### 1b. Typed blocks are FRONTEND-DERIVED, not LLM-emitted

The frontier ideal (json-render / A2UI / Portable-Text: _model emits a typed
block array, host renders native components_) is right about the **render model**
but wrong about the **producer** for our weakest target. So the **producer is a
pure deterministic projection** on the frontend:

```
briefToBlocks({ markdown, structured, sources, symbol, mode, note }) -> Block[]
```

This achieves the full wr1 vision — typed blocks, native dark components, no raw
markdown, inline citation chips, metric cards, show-don't-tell — **without
relying on the LLM to emit perfect JSON**, so it's robust on every model and on
every old persisted brief. The existing safe `Markdown` renderer **stays as the
guaranteed fallback** when derivation yields nothing (empty body).

## 2. The typed-block brief schema (Track 1)

A render-agnostic, **frontend-derived** document. Block kinds (subset of the
frontier catalog, tailored to what we can derive deterministically):

| Block       | Source                                                | Render                                                                                                                                  |
| ----------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `headline`  | resolved symbol/name + query + mode + verdict-neutral | title card, kicker `DEEP · NVDA`, provenance + freshness badges                                                                         |
| `metric`    | `structured.price` + `structured.fundamentals`        | metric-card grid: price, change% (green/red caret), P/E fwd, mkt cap, div yield, 52w range, volume — mono tabular, color ONLY the delta |
| `prose`     | markdown paragraphs/headings                          | spans with **ticker chips** (Track 2) + `[n]` citation chips                                                                            |
| `table`     | markdown pipe tables                                  | dense dark table (`divide-y`, right-aligned tabular-nums) — kills the chat wall-of-pipes                                                |
| `keyPoints` | a leading bullet list / "key points" section          | bordered callout card, max ~5                                                                                                           |
| `callout`   | `note` (no-web / budget breach)                       | left accent bar + glyph, tone-styled (honest, never hidden)                                                                             |
| `sources`   | `sources[]`                                           | existing source tray (favicon, domain, excerpt)                                                                                         |

**Visual constitution** (lifted from the reverse-engineered Claude widget rules,
and already congruent with `tokens.css`): two font weights; tabular/mono numerals
for every figure; **NO gradients/shadows/blur** (they flash during stream diffs +
read as consumer infographic); exactly ONE accent (clay) + the green/red signal
reserved for data direction; 1px hairline borders + elevation steps for hierarchy;
staggered entrance opt-in under `prefers-reduced-motion` (reuse `staggerParent`/
`staggerChild` from `lib/motion.ts`). Sparklines: **inline SVG polyline** (no new
dep, no `lightweight-charts`); omitted when no series is in the bundle (the bundle
carries snapshots, not OHLCV — a sparkline is a nice-to-have, never faked).

**Contract change (additive only):** add optional `structured?` to
`ResearchBriefData` (`types/brief.ts`), `briefFromInput` (`host-actions.ts`), the
`isBriefData` validator + workspace serialize/restore, and an optional `structured`
field on the `publish_brief` input schema (`catalog.py`, derived-from-catalog rule
→ run the parity tests). No Tier-1 file touched.

## 3. Clickable terminal connections (Track 2)

Every ticker in the brief (metric-card symbol, prose `$TICKER`/known-symbol token,
table/comparison entity) becomes a **live chip** → `useChartCommandStore
.loadSymbol(symbol)` (the always-consumed `set_chart_symbol` channel; fit-aware;
opens a chart first if none via the existing `ensureChartOpen` pattern; **does NOT
spawn a panel per click**). Detection: resolved symbol + watchlist symbols +
`$TICKER` + uppercase 1–5-char tokens validated against a known set. This is the
"it opens stuff for us" feeling Perplexity can't do.

## 4. Short chat + act-first (Track 3)

- **Short chat:** when a brief was published this turn (derive from
  proposed-changes / a per-message flag), the assistant essay collapses to a
  1–3-sentence summary with a "show full analysis" toggle (`ChatSidebar.tsx`
  ~793). Robust even if the model is verbose. Kills the chat markdown wall.
- **Act-first:** strengthen the copilot prompt — _never ask a clarifying question
  after running research; act on the best interpretation, render the brief, THEN
  offer ONE refinement_ + emit a short summary ("Built you a brief on X — top of
  the cockpit, click any ticker to dig in"). Prompt-level; the felt quality steps
  up on a capable model, but the frontend collapse makes the UX good regardless.

## 5. Fit-aware arrangement (Track 4)

Hybrid (full scope): (1) **deterministic** `fitLayoutTemplate` wrapper that
downgrades panel-heavy templates (`research-cockpit`=4, `macro-scan`=3) to an
**essentials** layout (chart + brief) below a width threshold — bulletproof safety
net, invisible to the agent; (2) **agent-aware** — add `viewport {width,height}`
to the `__terminal__` snapshot (`context-provider.ts`) + prompt guidance so the
agent chooses well and, when it shows essentials only, tells the user "click any
ticker to go deeper." Existing templates stay the fallback. dockview sizing
respects the `api.width>0` guard + `setSize`-after-place pattern from
`default-layout.ts`.

## 6. Deep-engine selector + Tongyi probe (Track 5)

- **Settings control:** `deepResearchBackend: "native" | "tongyi"` in the settings
  store + workspace blob; a `DeepResearchSection` in `SettingsPanel`. Default
  **native** (Tongyi opt-in, never auto-selected). Threaded to the deep_research
  tool via the agent-invoke request → a ContextVar the handler reads as the
  default backend (authoritative, not LLM-dependent), overridable by an explicit
  tool arg.
- **Live routing probe:** `GET /system/deepresearch/probe` reusing
  `tongyi.resolve_model` — honestly reports `routing.live` (slug routable) vs the
  resolved Qwen-A3B fallback + cost estimate + hardware verdict. OpenRouter key
  read from BYOK (per-request header / active creds), **never logged or echoed**.
- **Tongyi verdict (live-confirmed June 2026):** `alibaba/tongyi-deepresearch-30b-a3b`
  is **LISTED-BUT-UNROUTED — 0 endpoints** (the `alibaba` author is now absent
  from the 343-model catalog feed entirely; only the `/endpoints` lookup
  resolves it). Unchanged from Sprint-1. The honest probe is the `/endpoints`
  array length, exactly what `tongyi.py` already checks → resolves to
  `qwen/qwen3-30b-a3b-thinking-2507` (2 live endpoints) today. **No backend code
  change needed; this pass builds the UI + probe + honest reporting around the
  correct existing logic.** The selector shows "Tongyi unavailable on OpenRouter
  right now — using Qwen3-A3B" rather than silently hiding it.

## 7. The floor (every phase, non-negotiable)

§6.5 audit 9/9; Tier-1 LOCKED files byte-for-byte untouched (`types/plugin.ts`,
safety/broker/audit/kill-switch models, `broker_base.py`, `kill_switch.rs`,
`test_safety_end_to_end.py`, `tauri.conf.json`, CI); orders never auto-apply (the
live PENDING-in-AUTO order behavior survives); AUTO auto-applies only
UI/layout/chart/watchlist; brokers read-only; secrets keychain-only, per-request,
never logged. No new pip dep (no PyInstaller `--copy-metadata`/`--collect-data`/
`--add-data` exposure); if deps change, rebuild + smoke the binary. Every fork
keeps a working fallback — the app ends strictly better, fully functional.

**Confidence: 8/10** — the deterministic auto-publish + frontend block derivation
de-risk the weak-model dependency that capped prior passes; the residual unknown
is purely the live-rig pixel pass (mitigated by `caffeinate -dimsu` + the wake
path).
