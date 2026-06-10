# R9 Track A — Tier collapse: three research tiers become two

Branch: `worktree-agent-r9-tiers` from 004 HEAD. Partition is EXCLUSIVE — touch only the
files below. Push every concrete deliverable (each push is a recovery checkpoint).

## The model (exact)

- **`tier_a` — "Unlimited (Local)"**: managed SearXNG (existing one-click manager) as
  retrieval + WHATEVER chat model is active running our research loop. Default tier.
  When SearXNG is not READY, retrieval silently falls back to the keyless engines with
  `backend="keyless-fallback"` on the result/brief (the UI renders an honest nudge banner
  off that id — Team C owns the banner; you own the id). No "keyless tier" exists in any
  user-facing enum anymore.
- **`tier_b` — "Hosted research model"**: an internet-native research model via OpenRouter
  owns research at ALL depth stops regardless of the chat model. Per-stop model config
  (defaults below, user-swappable). Chat stays on the user's chat model; ONLY research
  routes to the research model. Requires the OpenRouter key (existing keychain lane,
  `X-Vysted-Openrouter-Key` header, never logged/persisted).
- **KILL ENTIRELY**: the BYOK hosted-scraper tier — `sidecar/services/search/hosted.py`
  (OpenRouter web-plugin search backend), `sidecar/services/search/exa.py`, the
  `byok-exa` / exa-direct lanes in headers/middleware/registry, their tests. Delete, don't
  stub. Keyless engines (`keyless.py`, `ddg.py`, `brave.py`, `mojeek.py`, breakers,
  pacing) STAY as code — they are the invisible fallback.

## Tier B per-stop defaults (verified live on OpenRouter 2026-06-11; lead may re-pin at integration — build model-agnostic)

| Stop | Model | Verified price |
|---|---|---|
| NORMAL | `perplexity/sonar` | $1/M in, $1/M out, $5/1k searches |
| DEEP | `perplexity/sonar-reasoning-pro` | $2/M in, $8/M out, $5/1k searches |
| ULTRA | `perplexity/sonar-deep-research` | $2/M in, $8/M out, $5/1k searches, $3/M reasoning |

Picker alternates (same per-stop slots): `perplexity/sonar-pro`, `perplexity/sonar-pro-search`,
`openai/o4-mini-deep-research`, `openai/o3-deep-research`, `x-ai/grok-4.3`. Store pricing
hints WITH the models in one frontend constant so Settings (Team D) renders them.

## Files you own

Sidecar: `services/search/registry.py` (drop exa/hosted builders), `services/search/hosted.py`
+ `exa.py` (DELETE), `services/agent_tools/web_search.py` (the ONE resolution path),
`services/agent_tools/research.py` (depth+tier routing at the tool boundary),
`services/agent_tools/deep_research.py` (Tier B lane: per-stop model dispatch via OpenRouter
chat-completions; citations from annotations → sources), `services/llm/native_search.py`
(keep; expose `native_search_available(provider, model)` + a callable channel for Team B's
cross-verify — INTERFACE, push early), `config.py` (ContextVars: research tier +
per-stop model map; keep depth ctx as-is), `app.py` middleware (header parsing),
`routers/search_tiers.py` (SearXNG routes stay — they're now core; remove t3 bits),
sidecar tests for all of the above.
Frontend: `src/store/search-settings.ts` (new enum `tier_a | tier_b`, `researchModels`
{normal,deep,ultra}, migration: native/t1_local/local-searxng/t2_searxng→tier_a;
t3_hosted/t3-exa-direct→tier_b when an OpenRouter key is configured else tier_a),
`src/lib/search-headers.ts`, `src/lib/workspace.ts` (searchSettings migrate on
deserialize, guard older blobs).

DO NOT touch: `SettingsPanel.tsx` (Team D builds the UI on your store contract — push the
store contract within your first hour), `services/research/*` + `extract.py` (Team B),
`src/modules/*`.

## Rules

1. **Resolution truth (extends R8 D20/D25):** explicit tier_b + key → research-model lane;
   tier_a → SearXNG READY ? searxng : keyless-fallback (honest backend id, never an error
   state); legacy headers map per migration. A stopped SearXNG NEVER yields "no web
   backend". Pin the matrix in pytest (extend R8's 29-test matrix, don't shrink it).
2. **Routing regardless of chat model:** with tier_b configured, a DEEP run on a
   deepseek-v4-flash chat session routes research to the research model. Evidence: research
   steps + brief carry `backend="research-model:<model-id>"`. Test-pinned.
3. **Native-search suppression:** tier_b ignores chat-model native search entirely (reuse
   R8's explicit-tier suppression). tier_a: native search compounds (Team B consumes your
   interface; you guarantee detection + invocation utilities work per provider).
4. **Depth-cost parity:** depth ContextVar must be readable ONLY by research tools. Add a
   pytest asserting non-research tool calls (e.g. arrange_layout) produce byte-identical
   LLM requests at normal vs ultra (system prompt, tools schema, messages).
5. Config migration is graceful and logged once (deprecation note in run log, not a user
   error). Old blobs keep working.
6. ULTRA on sonar-deep-research can take minutes — set the Tier B ultra lane wall-clock
   generously (≥360s) and stream progress steps honestly.

## Gates (in-worktree before push-final)

`PATH=sidecar/.venv/bin:$PATH` — ruff check+format sidecar, full pytest, vitest for your
frontend files, `node scripts/audit-design-tokens.mjs --report` (no NEW violations from
you). Write `docs/redesign/R9_TRACK_TIERS_REPORT.md` (what shipped, decisions, test
counts, NEEDS-MANUAL-CHECK).
